import discord  # isort:skip
import typing  # isort:skip

import asyncio

from redbot.core.utils.chat_formatting import bold, error, warning
from redbot.core.utils.predicates import MessagePredicate, ReactionPredicate

from .cogsutils import CogsUtils

__all__ = ["Captcha"]


def _(untranslated: str):
    return untranslated


class Captcha:
    """
    Captcha for an member in a text channel.
    Thanks to Kreusada for this code! (https://github.com/Kreusada/Kreusada-Cogs/blob/master/captcha/)
    """

    def __init__(
        self,
        cogsutils,
        member: discord.Member,
        channel: discord.TextChannel,
        limit: typing.Optional[int] = 3,
        timeout: typing.Optional[int] = 60,
        why: typing.Optional[str] = "",
    ):
        self.cogsutils = cogsutils

        self.member: discord.Member = member
        self.guild: discord.Guild = member.guild
        self.channel: discord.TextChannel = channel
        self.why: str = why

        self.limit: int = limit
        self.timeout: int = timeout

        self.message: discord.Message = None
        self.code: str = None
        self.running: bool = False
        self.tasks: list = []
        self.trynum: int = 0
        self.escape_char = "\u200B"

    async def realize_challenge(self) -> None:
        is_ok = None
        timeout = False
        try:
            while is_ok is not True:
                if self.trynum > self.limit:
                    break
                try:
                    self.code = self.generate_code()
                    await self.send_message()
                    this = await self.try_challenging()
                except TimeoutError:
                    timeout = True
                    break
                except self.AskedForReload:
                    self.trynum += 1
                    continue
                except TypeError:
                    continue
                except self.LeftGuildError:
                    leave_guild = True
                    break
                if this is False:
                    self.trynum += 1
                    is_ok = False
                else:
                    is_ok = True
            await CogsUtils().delete_message(self.message)
            failed = self.trynum > self.limit
        except self.MissingPermissions as e:
            raise self.MissingPermissions(e)
        except Exception as e:
            if hasattr(self.cogsutils.cog, "log"):
                self.cogsutils.cog.log.error(
                    "An unsupported error occurred during the captcha.", exc_info=e
                )
            raise self.OtherException(e)
        finally:
            if timeout:
                raise TimeoutError()
            if failed:
                return False
            if leave_guild:
                raise self.LeftGuildError("User has left guild.")
            return True

    async def try_challenging(self) -> bool:
        """Do challenging in one function!"""
        self.running = True
        try:
            received = await self.wait_for_action()
            if received is None:
                raise self.LeftGuildError("User has left guild.")
            if hasattr(received, "content"):
                # It's a message!
                try:
                    await received.delete()
                except discord.HTTPException:
                    pass
                error_message = ""
                try:
                    state = await self.verify(received.content)
                except self.SameCodeError:
                    error_message += error(
                        bold(_("Code invalid. Do not copy and paste.").format(**locals()))
                    )
                    state = False
                else:
                    if not state:
                        error_message += warning("Code invalid.")
                if error_message:
                    await self.channel.send(error_message, delete_after=3)
                return state
            else:
                raise self.AskedForReload("User want to reload Captcha.")
        except TimeoutError:
            raise TimeoutError()
        finally:
            self.running = False

    def generate_code(self, put_fake_espace: typing.Optional[bool] = True):
        code = self.cogsutils.generate_key(
            number=8,
            existing_keys=[],
            strings_used={
                "ascii_lowercase": False,
                "ascii_uppercase": True,
                "digits": True,
                "punctuation": False,
            },
        )
        if put_fake_espace:
            code = self.escape_char.join(list(code))
        return code

    def get_embed(self) -> discord.Embed:
        """
        Get the embed containing the captcha code.
        """
        embed_dict = {
            "embeds": [
                {
                    "title": _("Captcha").format(**locals())
                    + _(" for {self.why}").format(**locals())
                    if not self.why == ""
                    else "",
                    "description": _(
                        "Please return me the following code:\n{box(str(self.code))}\nDo not copy and paste."
                    ).format(**locals()),
                    "author": {
                        "name": f"{self.member.display_name}",
                        "icon_url": self.member.display_avatar
                        if self.is_dpy2
                        else self.member.avatar_url,
                    },
                    "footer": {
                        "text": _("Tries: {self.trynum} / Limit: {self.limit}").format(**locals())
                    },
                }
            ]
        }
        embed = self.cogsutils.get_embed(embed_dict)["embed"]
        return embed

    async def send_message(self) -> None:
        """
        Send a message with new code.
        """
        await CogsUtils().delete_message(self.message)
        embed = self.get_embed()
        try:
            self.message = await self.channel.send(
                embed=embed,
                delete_after=900,  # Delete after 15 minutes.
            )
        except discord.HTTPException:
            raise self.MissingPermissions("Cannot send message in verification channel.")
        try:
            await self.message.add_reaction("🔁")
        except discord.HTTPException:
            raise self.MissingPermissions("Cannot react in verification channel.")

    async def verify(self, code_input: str) -> bool:
        """Verify a code."""
        if self.escape_char in code_input:
            raise self.SameCodeError
        if code_input.lower() == self.code.replace(self.escape_char, "").lower():
            return True
        else:
            return False

    async def wait_for_action(self) -> typing.Union[discord.Reaction, discord.Message, None]:
        """Wait for an action from the user.
        It will return an object of discord.Message or discord.Reaction depending what the user
        did.
        """
        self.cancel_tasks()  # Just in case...
        self.tasks = self._give_me_tasks()
        done, pending = await asyncio.wait(
            self.tasks,
            timeout=self.timeout,
            return_when=asyncio.FIRST_COMPLETED,
        )
        self.cancel_tasks()
        if len(done) == 0:
            raise TimeoutError()("User didn't answer.")
        try:  # An error is raised if we return the result and when the task got cancelled.
            return done.pop().result()
        except asyncio.CancelledError:
            return None

    def cancel_tasks(self) -> None:
        """Cancel the ongoing tasks."""
        for task in self.tasks:
            task: asyncio.Task
            if not task.done():
                task.cancel()

    def _give_me_tasks(self) -> typing.List:
        def leave_check(u):
            return u.id == self.member.id

        return [
            asyncio.create_task(
                self.cogsutils.bot.wait_for(
                    "reaction_add",
                    check=ReactionPredicate.with_emojis(
                        "🔁", message=self.message, user=self.member
                    ),
                )
            ),
            asyncio.create_task(
                self.cogsutils.bot.wait_for(
                    "message",
                    check=MessagePredicate.same_context(
                        channel=self.channel,
                        user=self.member,
                    ),
                )
            ),
            asyncio.create_task(self.cogsutils.bot.wait_for("user_remove", check=leave_check)),
        ]

    class MissingPermissions(Exception):
        pass

    class AskedForReload(Exception):
        pass

    class SameCodeError(Exception):
        pass

    class LeftGuildError(Exception):
        pass

    class OtherException(Exception):
        pass

from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator  # isort:skip
import discord  # isort:skip
import typing  # isort:skip
import typing_extensions  # isort:skip

import datetime
from dataclasses import dataclass
from io import BytesIO

import aiohttp
import dateutil
import pytz

from apscheduler.triggers.cron import CronTrigger
from cron_descriptor import CasingTypeEnum, ExpressionDescriptor

from .views import SnoozeView

_ = Translator("Reminders", __file__)

try:
    from typing import TypeAlias
except ImportError:
    from typing_extensions import TypeAlias
Content: TypeAlias = typing.Dict[
    str, typing.Union[str, typing.Dict[str, typing.Union[str, typing.Dict[str, str]]]]
]
Data: TypeAlias = typing.Dict[
    str, typing.Union[str, int, bool, Content, typing.Dict[str, typing.Union[int, str]]]
]

# Add Snooze View, add message interaction, add intervals, add rules, add converter...s


@dataclass(frozen=False)
class Interval:
    type: str
    value: typing.Optional[typing.Dict[str, int]]

    def to_json(self) -> typing.Dict[str, typing.Union[str, typing.Dict[str, int]]]:
        if self.type in ["sample", "cron"]:
            return {"type": self.type, "value": self.value}
        else:
            return {"type": self.type}

    @classmethod
    def from_json(
        cls, data: typing.Dict[str, typing.Union[str, typing.Dict[str, int]]]
    ) -> typing_extensions.Self:
        if data["type"] in ["sample", "cron"]:
            return cls(type=data["type"], value=data["value"])
        else:
            return cls(type=data["type"], value=None)

    def next_trigger(
        self,
        last_expires: datetime.datetime = datetime.datetime.now(datetime.timezone.utc),
        utc_now: datetime.datetime = datetime.datetime.now(datetime.timezone.utc),
        timezone: str = "UTC",
    ) -> typing.Optional[datetime.datetime]:
        if self.type == "sample":
            repeat_delta = dateutil.relativedelta.relativedelta(**self.value)
            next_expires_at = last_expires + repeat_delta
        elif self.type == "cron":
            tz = pytz.timezone(timezone)
            cron_trigger = CronTrigger.from_crontab(self.value, timezone=tz)
            next_expires_at = cron_trigger.get_next_fire_time(previous_fire_time=last_expires, now=utc_now.astimezone(tz))
            if next_expires_at is None:
                return None
            next_expires_at = next_expires_at.astimezone(datetime.timezone.utc)
        while next_expires_at < utc_now:
            next_expires_at += repeat_delta
        return None


@dataclass(frozen=False)
class Reminder:
    cog: commands.Cog
    user_id: int

    id: int
    jump_url: str
    snooze: bool
    me_too: bool

    content: Content  # {"type": ..., "title": None, "text": None, "embed": ..., "message_author": {"display_name": ..., "display_avatar": ..., "mention": ...}, "image_url": ..., "command": ..., "invoker": ...}
    destination: typing.Optional[int]  # channel or dm
    target: typing.Optional[typing.Dict[str, typing.Union[int, str]]]

    created_at: datetime.datetime
    expires_at: datetime.datetime
    last_expires_at: typing.Optional[datetime.datetime]
    next_expires_at: datetime.datetime
    interval: typing.Optional[Interval]

    def __eq__(self, other: "Reminder") -> bool:
        return (self.next_expires_at or datetime.datetime.now(tz=datetime.timezone.utc)) == (
            other.next_expires_at or datetime.datetime.now(tz=datetime.timezone.utc)
        )

    def __lt__(self, other: "Reminder") -> bool:
        return (self.next_expires_at or datetime.datetime.now(tz=datetime.timezone.utc)) < (
            other.next_expires_at or datetime.datetime.now(tz=datetime.timezone.utc)
        )

    def __le__(self, other: "Reminder") -> bool:
        return (self.next_expires_at or datetime.datetime.now(tz=datetime.timezone.utc)) <= (
            other.next_expires_at or datetime.datetime.now(tz=datetime.timezone.utc)
        )

    def __gt__(self, other: "Reminder") -> bool:
        return (self.next_expires_at or datetime.datetime.now(tz=datetime.timezone.utc)) > (
            other.next_expires_at or datetime.datetime.now(tz=datetime.timezone.utc)
        )

    def __ge__(self, other: "Reminder") -> bool:
        return (self.next_expires_at or datetime.datetime.now(tz=datetime.timezone.utc)) >= (
            other.next_expires_at or datetime.datetime.now(tz=datetime.timezone.utc)
        )

    def to_json(self, clean: bool = True) -> Data:
        data = {
            "id": self.id,
            "jump_url": self.jump_url,
            "snooze": self.snooze,
            "me_too": self.me_too,
            "content": self.content,
            "destination": self.destination,
            "target": self.target,
            "created_at": int(self.created_at.timestamp()),
            "expires_at": int(self.expires_at.timestamp()),
            "last_expires_at": int(self.next_expires_at.timestamp()),
            "next_expires_at": int(self.next_expires_at.timestamp()),
            "interval": self.interval.to_json() if self.interval is not None else self.interval,
        }
        if clean:
            for attr in [
                "snooze",
                "me_too",
                "destination",
                "target",
                "interval",
                "last_expires_at",
            ]:
                if not getattr(self, attr):
                    del data[attr]
        return data

    @classmethod
    def from_json(cls, cog: commands.Cog, user_id: int, data: Data) -> typing_extensions.Self:
        return cls(
            cog=cog,
            user_id=user_id,
            id=data["id"],
            jump_url=data["jump_url"],
            snooze=data.get("snooze", False),
            me_too=data.get("me_too", False),
            content=data["content"],
            destination=data.get("destination"),
            target=data.get("target"),
            created_at=datetime.datetime.fromtimestamp(
                int(data["created_at"]), tz=datetime.timezone.utc
            ),
            expires_at=datetime.datetime.fromtimestamp(
                int(data["expires_at"]), tz=datetime.timezone.utc
            ),
            last_expires_at=datetime.datetime.fromtimestamp(
                int(data["last_expires_at"]), tz=datetime.timezone.utc
            )
            if data.get("last_expires_at") is not None
            else None,
            next_expires_at=datetime.datetime.fromtimestamp(
                int(data["next_expires_at"]), tz=datetime.timezone.utc
            ),
            interval=Interval.from_json(data["interval"])
            if data.get("interval") is not None
            else None,
        )

    def __str__(
        self, utc_now: datetime.datetime = datetime.datetime.now(tz=datetime.timezone.utc)
    ) -> str:
        and_every = ""
        if self.interval is not None:
            if self.interval.type == "sample":
                and_every = _(", and then **every {interval}**").format(
                    interval=self.cog.get_interval_string(
                        dateutil.relativedelta.relativedelta(**self.interval.value)
                    )
                )
            elif self.interval.type == "cron":
                descriptor = ExpressionDescriptor(
                    expression=self.interval.value,
                    verbose=True,
                    casing_type=CasingTypeEnum.LowerCase,
                    locale_location="en",
                    use_24hour_time_format=True
                )
                and_every = _(", and then **{interval}**").format(interval=descriptor.get_full_description())
        interval_string = self.cog.get_interval_string(
            int(self.expires_at.timestamp() - utc_now.timestamp())
        )
        if interval_string != "just now":
            interval_string = f"in {interval_string}"
        return (
            _(
                "{state}Okay, I will execute this command{destination_mention} **{interval_string}** ({timestamp}){and_every}. [Reminder **#{reminder_id}**]"
            ) if self.content["type"] == "command" else (
                _(
                    "{state}Okay, I will say {this}{destination_mention} **{interval_string}** ({timestamp}){and_every}. [Reminder **#{reminder_id}**]"
                ) if self.content["type"] == "say" else _(
                    "{state}Okay, I will execute this command{destination_mention} **{interval_string}** ({timestamp}){and_every}. [Reminder **#{reminder_id}**]"
                )
            )
        ).format(
            state=f"{'[Snooze] ' if self.snooze else ''}{'[Me Too] ' if self.me_too else ''}",
            target_mention=self.target["mention"] if self.target is not None else _("you"),
            this=(
                _("this message")
                if self.content["type"] == "message"
                else _("this")  # (_("this command") if self.content["type"] == "command" else _("this"))
            )
            if self.content["type"] != "text" or self.content["text"] is not None
            else "that",
            destination_mention=(_(" in {destination_mention}").format(destination_mention=destination.mention) if (destination := self.cog.bot.get_channel(self.destination)) is not None else _(" in {destination} (Not found.)".format(destination=self.destination))) if self.destination is not None else "",
            interval_string=interval_string,
            timestamp=f"<t:{int(self.expires_at.timestamp())}:F>",
            and_every=and_every,
            reminder_id=self.id,
        )

    def get_info(self) -> str:
        if self.interval is not None and self.interval.type == "cron":
            descriptor = ExpressionDescriptor(
                expression=self.interval.value,
                verbose=True,
                casing_type=CasingTypeEnum.Sentence,
                locale_location="en",
                use_24hour_time_format=True
            )
        return _(
            "• **Next Expires at**: {expires_at_timestamp} ({expires_in_timestamp})\n"
            "• **Created at**: {created_at_timestamp} ({created_in_timestamp})\n"
            "• **Interval**: {interval}\n"
            "• **Title**: {title}\n"
            "• **Content type**: `{content_type}`\n"
            "• **Content**: {content}\n"
            "• **Destination**: {destination}\n"
            "• **Jump URL**: {jump_url}\n"
        ).format(
            expires_at_timestamp=f"<t:{int(self.next_expires_at.timestamp())}:F>",
            expires_in_timestamp=self.cog.get_interval_string(
                self.next_expires_at, use_timestamp=True
            ),
            created_at_timestamp=f"<t:{int(self.created_at.timestamp())}:F>",
            created_in_timestamp=self.cog.get_interval_string(self.created_at, use_timestamp=True),
            interval=_("No interval.")
            if self.interval is None
            else (
                _("Advanced interval.")
                if self.interval.type == "advanced"
                else (
                    (
                        f"{descriptor.get_full_description()}."
                    ) if self.interval.type == "cron" else (
                        _("every {interval_string}").format(
                            interval_string=self.cog.get_interval_string(
                                dateutil.relativedelta.relativedelta(**self.interval.value)
                            )
                        )
                    )
                )
            ),
            title=self.content.get("title") or _("Not provided."),
            content_type=self.content["type"],
            content=(
                (
                    (
                        f"{self.content['text'][:200]}..."
                        if len(self.content["text"]) > 200
                        else self.content["text"]
                    )
                    if self.content["text"] is not None
                    else _("No content.")
                )
                if self.content["type"] in ["text", "say"]
                else (
                    f"Message {self.content['message_jump_url']}."
                    if self.content["type"] == "message"
                    else f"Command `[p]{self.content['command']}` executed with your privilege rights."
                )
            ),
            destination=_("In DMs")
            if self.destination is None
            else destination.mention
            if (destination := self.cog.bot.get_channel(self.destination)) is not None
            else f"{self.destination} (Not found.)",
            jump_url=self.jump_url,
        )

    async def save(self) -> None:
        if self.user_id not in self.cog.cache:
            self.cog.cache[self.user_id] = {}
        self.cog.cache[self.user_id][self.id] = self
        data = self.to_json()
        await self.cog.config.user_from_id(self.user_id).set_raw("reminders", self.id, value=data)
        return self

    async def delete(self) -> None:
        try:
            del self.cog.cache[self.user_id][self.id]
        except KeyError:
            pass
        await self.cog.config.user_from_id(self.user_id).clear_raw("reminders", self.id)

    def to_embed(
        self,
        utc_now: datetime.datetime = datetime.datetime.now(datetime.timezone.utc),
        embed_color: typing.Optional[discord.Color] = discord.Color.green(),
    ) -> discord.Embed:
        delayed = int(
            utc_now.timestamp() - (self.last_expires_at or self.next_expires_at).timestamp()
        )
        if delayed <= 60:
            delayed = 0
        embed: discord.Embed = discord.Embed(
            title=f"🔔 {'(Delayed) ' if delayed else ''}{'[Snoozed] ' if self.snooze else ''}{'[Me Too] ' if self.me_too else ''}{'Repeating ' if self.next_expires_at is not None else ''}Reminder #{self.id}! 🔔",
            url=self.jump_url,
            color=embed_color,
        )
        if (
            self.destination is not None
            and (self.target is None or self.target["id"] != self.user_id)
            and (user := self.cog.bot.get_user(self.user_id))
        ):
            embed.set_author(name=user.display_name, icon_url=user.display_avatar)
        embed.add_field(
            name="\u200B",
            value=f"[Jump to the original message.]({self.jump_url}) • Created the <t:{int(self.created_at.timestamp())}:F>.",
            inline=False,
        )
        interval_string = self.cog.get_interval_string(
            int(
                (self.last_expires_at or self.next_expires_at).timestamp()
                - self.created_at.timestamp()
            )
        )
        if interval_string != "just now":
            interval_string += " ago"
        if self.content["type"] == "text":
            embed.description = _(
                "You asked me to remind you about {this}, {interval_string}.\n\n"
            ).format(
                this="this" if self.content["text"] else "that", interval_string=interval_string
            )
        else:  # message
            embed.description = _(
                "You asked me to remind you about [this message]({message_jump_url}) from {author_mention} ({author_id}), {interval_string}.\n\n"
            ).format(
                message_jump_url=self.content["message_jump_url"],
                author_mention=self.content["message_author"]["mention"],
                author_id=self.content["message_author"]["id"],
                interval_string=interval_string,
            )
        if self.content.get("title") is not None:
            embed.description += f"# **{self.content['title']}**\n\n"
        if self.content["text"]:
            embed.description += f">>> {self.content['text']}"
        if self.content.get("image_url") is not None:
            embed.set_image(url=self.content["image_url"])
        footer = ""
        if delayed:
            footer += _(
                "This was supposed to send {interval_string} ago. I might be having network or server issues, or perhaps I just started up. Sorry about that!\n\n"
            ).format(interval_string=self.cog.get_interval_string(delayed))
        if self.next_expires_at is not None:
            footer += _("Next trigger in {interval_string}.").format(
                interval_string=self.cog.get_interval_string(self.next_expires_at)
            )
        embed.set_footer(text=footer or None)
        return embed

    async def process(
        self,
        utc_now: datetime.datetime = datetime.datetime.now(datetime.timezone.utc),
        testing: bool = False,
    ) -> None:
        if not testing:
            self.last_expires_at = self.next_expires_at
            timezone = (await self.cog.config.user_from_id(self.user_id).timezone()) or "UTC"
            if self.interval is not None:
                self.next_expires_at = self.interval.next_trigger(
                    last_expires=self.last_expires_at, utc_now=utc_now, timezone=timezone
                )
            else:
                self.next_expires_at = None
        if (user := self.cog.bot.get_user(self.user_id)) is None:
            if not testing:
                await self.delete()
            raise RuntimeError(
                f"User {self.user_id} not found for the reminder {self.user_id}#{self.id}@{self.content['type']}. The reminder has been deleted."
            )
        if self.destination is None:
            destination: discord.abc.Messageable = await user.create_dm()
        elif (destination := self.cog.bot.get_channel(self.destination)) is None:
            if not testing:
                await self.delete()
            raise RuntimeError(
                f"Destination {self.destination} not found for the reminder {self.user_id}#{self.id}@{self.content['type']}. The reminder has been deleted."
            )
        if not self.content:
            if not testing:
                await self.delete()
            raise RuntimeError(
                f"No content in the reminder {self.user_id}#{self.id}@{self.content['type']}. The reminder has been deleted."
            )
        if self.content["type"] == "command":
            if (invoker := self.cog.bot.get_user(self.content["command_invoker"])) is None:
                if not testing:
                    await self.delete()
                raise RuntimeError(
                    f"Command invoker not found for the reminder {self.user_id}#{self.id}@{self.content['type']}. The reminder has been deleted."
                )
            context: commands.Context = await self.cog.cogsutils.invoke_command(
                author=invoker, channel=destination, command=self.content["command"]
            )
            if not context.valid:  # don't delete the reminder (cog unloaded for example)
                raise RuntimeError(
                    f"Command not found for the reminder {self.user_id}#{self.id}@{self.content['type']}. The reminder has not been deleted."
                )
            elif not await context.command.can_run(
                context
            ):  # to prevent an user with important permissions a time to execute dangerous command with a reminder
                if not testing:
                    await self.delete()
                raise RuntimeError(
                    f"The invoker can't execute the command for the reminder {self.user_id}#{self.id}@{self.content['type']}. The reminder has been deleted."
                )
        else:
            if self.content["type"] == "text":
                embeds = [self.to_embed(utc_now=utc_now)]
            else:
                embeds = []
            if self.content.get("embed") is not None:
                e = discord.Embed.from_dict(self.content["embed"])
                e.set_author(
                    name=self.content["message_author"]["display_name"],
                    icon_url=self.content["message_author"]["display_avatar"],
                )
                e.color = None
                embeds.append(e)
            files = []
            if self.content.get("files"):
                for file_name, file_url in self.content["files"].items():
                    async with aiohttp.ClientSession() as session:
                        async with session.get(file_url) as r:
                            file_content = await r.read()
                    files.append(discord.File(BytesIO(file_content), filename=file_name))
            try:
                reference = None
                if self.content["type"] == "text":
                    if self.content["type"] == "message" and destination.id == int(
                        self.content["message_jump_url"].split("/")[-2]
                    ):
                        if (
                            message := destination.get_partial_message(
                                int(self.content["message_jump_url"].split("/")[-1])
                            )
                        ) is not None:
                            reference = message
                    elif destination.id == int(self.jump_url.split("/")[-2]):
                        if (
                            message := destination.get_partial_message(
                                int(self.jump_url.split("/")[-1])
                            )
                        ) is not None:
                            reference = message
                    view = SnoozeView(cog=self.cog, reminder=self)
                    message = await destination.send(
                        embeds=embeds,
                        files=files,
                        content=self.target["mention"] if self.target is not None else None,
                        allowed_mentions=discord.AllowedMentions(
                            everyone=True, users=True, roles=True, replied_user=False
                        ),
                        view=view,
                        reference=reference,
                    )
                    view._message = message
                else:  # type `say`
                    message = await destination.send(
                        content=self.content["text"],
                        embeds=embeds,
                        files=files,
                        # allowed_mentions=discord.AllowedMentions(
                        #     everyone=True, users=True, roles=True, replied_user=False
                        # ),
                    )
            except discord.HTTPException:
                if not testing:
                    await self.delete()
                raise RuntimeError(
                    f"The message was not sent correctly for the reminder {self.user_id}#{self.id}@{self.content['type']}. The reminder has been deleted."
                )
            if self.next_expires_at is None and not testing:
                await self.delete()
            return context if self.content["type"] == "command" else message

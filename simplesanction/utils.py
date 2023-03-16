from .AAA3A_utils import CogsUtils  # isort:skip
from redbot.core.i18n import Translator  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import asyncio

from redbot.core.commands.converter import parse_timedelta
from redbot.core.utils.predicates import MessagePredicate

if not CogsUtils().is_dpy2:
    from dislash import ActionRow, Button, ButtonStyle

_ = Translator("SimpleSanction", __file__)


class utils:
    async def emojis(self) -> typing.Tuple:
        buttons = [
            "userinfo_button",
            "warn_button",
            "ban_button",
            "softban_button",
            "tempban_button",
            "kick_button",
            "mute_button",
            "mutechannel_button",
            "tempmute_button",
            "tempmutechannel_button",
            "close_button",
        ]
        buttons_one = ActionRow(
            Button(
                style=ButtonStyle.grey,
                label="UserInfo",
                emoji="ℹ️",
                custom_id="userinfo_button",
                self=self,
            ),
            Button(
                style=ButtonStyle.grey,
                label="Warn",
                emoji="⚠️",
                custom_id="warn_button",
                self=self,
            ),
            Button(
                style=ButtonStyle.grey,
                label="Ban",
                emoji="🔨",
                custom_id="ban_button",
                self=self,
            ),
            Button(
                style=ButtonStyle.grey,
                label="SoftBan",
                emoji="🔂",
                custom_id="softban_button",
                self=self,
            ),
            Button(
                style=ButtonStyle.grey,
                label="TempBan",
                emoji="💨",
                custom_id="tempban_button",
                self=self,
            ),
        )
        buttons_two = ActionRow(
            Button(
                style=ButtonStyle.grey,
                label="Kick",
                emoji="👢",
                custom_id="kick_button",
                self=self,
            ),
            Button(
                style=ButtonStyle.grey,
                label="Mute",
                emoji="🔇",
                custom_id="mute_button",
                self=self,
            ),
            Button(
                style=ButtonStyle.grey,
                label="MuteChannel",
                emoji="👊",
                custom_id="mutechannel_button",
                self=self,
            ),
            Button(
                style=ButtonStyle.grey,
                label="TempMute",
                emoji="⏳",
                custom_id="tempmute_button",
                self=self,
            ),
            Button(
                style=ButtonStyle.grey,
                label="TempMuteChannel",
                emoji="⌛",
                custom_id="tempmutechannel_button",
                self=self,
            ),
        )
        buttons_three = ActionRow(
            Button(
                style=ButtonStyle.grey,
                label="Close",
                emoji="❌",
                custom_id="close_button",
                self=self,
            )
        )
        return buttons, buttons_one, buttons_two, buttons_three

    async def reason_ask(self, reason, actual_reason_required, title, description, actual_color, user, actual_timeout) -> str:
        if reason is not None:
            return reason
        if not actual_reason_required:
            return "not"
        embed: discord.Embed = discord.Embed()
        embed.title = f"{title}"
        embed.description = f"{description}"
        embed.color = actual_color
        embed.set_author(
            name=user.name,
            url=user.display_avatar if CogsUtils().is_dpy2 else user.avatar_url,
            icon_url=user.display_avatar if CogsUtils().is_dpy2 else user.avatar_url,
        )
        message = await self.send(embed=embed)
        try:
            pred = MessagePredicate.same_context(self)
            msg = await self.bot.wait_for("message", timeout=actual_timeout, check=pred)
            if msg.content.lower() == "cancel":
                await CogsUtils().delete_message(message)
                await CogsUtils().delete_message(msg)
                raise TimeoutError()
            if msg.content.lower() == "not":
                reason = "not"
                return reason
            await CogsUtils().delete_message(message)
            await CogsUtils().delete_message(msg)
            if reason is None:
                reason = msg.content
                return reason
        except asyncio.TimeoutError:
            await self.send(_("Timed out, please try again."))
            raise TimeoutError()

    async def duration_ask(self, duration, title, description, actual_color, user, actual_timeout) -> str:
        if duration is not None:
            return duration
        embed: discord.Embed = discord.Embed()
        embed.title = f"{title}"
        embed.description = f"{description}"
        embed.color = actual_color
        embed.set_author(
            name=user,
            url=user.display_avatar if CogsUtils().is_dpy2 else user.avatar_url,
            icon_url=user.display_avatar if CogsUtils().is_dpy2 else user.avatar_url,
        )
        message = await self.send(embed=embed)
        try:
            pred = MessagePredicate.same_context(self)
            msg = await self.bot.wait_for("message", timeout=actual_timeout, check=pred)
            if msg.content.lower() == "cancel":
                await CogsUtils().delete_message(message)
                await CogsUtils().delete_message(msg)
                raise TimeoutError()
            await CogsUtils().delete_message(message)
            await CogsUtils().delete_message(msg)
            duration = msg.content
            return duration
        except asyncio.TimeoutError:
            await self.send(_("Timed out, please try again."))
            raise TimeoutError()

    async def confirmation_ask(self, confirmation, title, description, actual_color, user, reason, duration, actual_timeout) -> bool:
        if confirmation:
            embed: discord.Embed = discord.Embed()
            embed.title = f"{title}"
            embed.description = f"{description}"
            embed.color = actual_color
            embed.set_author(
                name=user,
                url=user.display_avatar if CogsUtils().is_dpy2 else user.avatar_url,
                icon_url=user.display_avatar if CogsUtils().is_dpy2 else user.avatar_url,
            )
            if reason == "not":
                embed.add_field(
                    inline=False,
                    name="Reason:",
                    value=_("The reason was not given."),
                )
            else:
                embed.add_field(inline=False, name="Reason:", value=f"{reason}")
            if duration is not None:
                if duration != "Infinity":
                    embed.add_field(
                        inline=False,
                        name=_("Duration:"),
                        value=f"{parse_timedelta(duration)}",
                    )
                else:
                    embed.add_field(
                        inline=False,
                        name=_("Duration:"),
                        value=_("Infinity"),
                    )
            return await CogsUtils(bot=self.bot).ConfirmationAsk(self=self, embed=embed)

    async def finish_message(self, finish_message, title, description, actual_thumbnail, actual_color, user, show_author, duration, reason) -> discord.Message:
        if not finish_message:
            return
        embed: discord.Embed = discord.Embed()
        embed.title = f"{title}"
        embed.description = _(
            "This tool allows you to easily sanction a server member.\nUser mention: {user.mention} - User ID: {user.id}"
        ).format(user=user)
        embed.set_thumbnail(url=actual_thumbnail)
        embed.color = actual_color
        embed.set_author(
            name=user,
            url=user.display_avatar if CogsUtils().is_dpy2 else user.avatar_url,
            icon_url=user.display_avatar if CogsUtils().is_dpy2 else user.avatar_url,
        )
        if show_author:
            embed.set_footer(
                text=self.author,
                icon_url=self.author.display_avatar
                if CogsUtils().is_dpy2
                else self.author.avatar_url,
            )
        embed.add_field(
            inline=False,
            name=f"{description}",
            value=_("If an error has occurred, it will be displayed below."),
        )
        if reason is not None:
            embed.add_field(name=_("Reason:"), value=f"{reason}")
        if duration is not None:
            if duration != "Infinity":
                embed.add_field(
                    inline=False,
                    name=_("Duration:"),
                    value=f"{parse_timedelta(duration)}",
                )
            else:
                embed.add_field(
                    inline=False,
                    name=_("Duration:"),
                    value=_("Infinity"),
                )
        return await self.send(embed=embed)

from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import asyncio

from dataclasses import dataclass

from redbot.core.commands.converter import parse_timedelta
from redbot.core.utils.predicates import MessagePredicate

_ = Translator("SimpleSanction", __file__)


@dataclass(frozen=True)
class Action:
    key: str
    cog: commands.Cog

    label: str
    emoji: str

    cog_required: typing.Optional[str]
    command: str
    warn_system_command: typing.Optional[str]

    duration_ask_message: typing.Optional[str]
    reason_ask_message: typing.Optional[str]
    confirmation_ask_message: typing.Optional[str]
    finish_message: typing.Optional[str]

    def to_json(self) -> typing.Dict[str, typing.Any]:
        return {
            v: getattr(self, v)
            for v in dir(self)
            if not v.startswith("_") and v not in ["to_json", "process"]
        }

    async def process(self, ctx: commands.Context, member: discord.Member, duration: typing.Optional[str] = None, reason: typing.Optional[str] = "The reason was not given.", finish_message_enabled: typing.Optional[bool] = True, reason_required: typing.Optional[bool] = True, confirmation: typing.Optional[bool] = False, show_author: typing.Optional[bool] = True, fake_action: typing.Optional[bool] = False) -> bool:
        if (await self.cog.config.guild(ctx.guild).warn_system_use()) and self.warn_system_command is not None:
            cog_required = "WarnSystem"
        else:
            cog_required = self.cog_required
        if cog_required is not None and not ctx.bot.get_cog(cog_required):
            await ctx.send(
                _(
                    "The cog `{cog_required}` is not loaded. Please load it, with the command `{prefix}load {cog_required_lowered}`."
                ).format(prefix=ctx.prefix, cog_required=cog_required, cog_required_lowered=cog_required.lower())
            )
            return False
        if duration is None and self.duration_ask_message is not None:
            duration_message = await ctx.send(_(self.duration_ask_message).format(member=member, duration=str(parse_timedelta(duration)) if duration is not None else None, reason=reason, channel=ctx.channel))
            try:
                pred = MessagePredicate.same_context(ctx)
                msg = await ctx.bot.wait_for("message", timeout=60, check=pred)
                await self.cog.cogsutils.delete_message(duration_message)
                await self.cog.cogsutils.delete_message(msg)
                if msg.content.lower() == "cancel":
                    return
                duration = msg.content
            except asyncio.TimeoutError:
                await ctx.send(_("Timed out, please try again."))
                return
        if reason is None:
            if self.reason_ask_message is not None and reason_required:
                reason_message = await ctx.send(_(self.reason_ask_message).format(member=member, duration=str(parse_timedelta(duration)) if duration is not None else None, reason=reason, channel=ctx.channel))
                try:
                    pred = MessagePredicate.same_context(ctx)
                    msg = await ctx.bot.wait_for("message", timeout=60, check=pred)
                    await self.cog.cogsutils.delete_message(reason_message)
                    await self.cog.cogsutils.delete_message(msg)
                    if msg.content.lower() == "cancel":
                        return
                    reason = _("The reason was not given.") if reason == "not" else msg.content
                except asyncio.TimeoutError:
                    await ctx.send(_("Timed out, please try again."))
                    return
            else:
                reason = _("The reason was not given.")
        if not confirmation and self.confirmation_ask_message is not None and not await self.cog.cogsutils.ConfirmationAsk(ctx, content=_(self.confirmation_ask_message).format(member=member, duration=str(parse_timedelta(duration)) if duration is not None else None, reason=reason, channel=ctx.channel)) and not ctx.assume_yes:
            await self.cog.cogsutils.delete_message(ctx.message)
            return
        if finish_message_enabled and self.finish_message is not None:
            embed: discord.Embed = discord.Embed()
            embed.title = f"Sanction a Member - {self.emoji} {self.label}"
            embed.description = _(
                "This cog allows you to easily sanction a server member.\nMember mention: {member.mention} - Member ID: {member.id}"
            ).format(member=member)
            embed.set_thumbnail(url=await self.cog.config.guild(ctx.guild).thumbnail())
            embed.color = await ctx.embed_color()
            embed.set_author(
                name=member.display_name,
                url=member.display_avatar,
                icon_url=member.display_avatar,
            )
            if show_author:
                embed.set_footer(
                    text=ctx.author,
                    icon_url=ctx.author.display_avatar,
                )
            embed.add_field(
                name="\u200B",
                value=_(self.finish_message).format(member=member, duration=str(parse_timedelta(duration)) if duration is not None else None, reason=reason, channel=ctx.channel),
                inline=False,
            )
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
            finish_message = await ctx.send(embed=embed)
        else:
            finish_message = None
        if not fake_action:
            if (await self.cog.config.guild(ctx.guild).warn_system_use()) and self.warn_system_command is not None:
                command = self.warn_system_command
            else:
                command = self.command
            command = command.format(member=member, duration=str(parse_timedelta(duration)) if duration is not None else None, reason=reason, channel=ctx.channel)
            await self.cog.cogsutils.invoke_command(
                author=ctx.author,
                channel=ctx.channel,
                command=command,
                prefix=ctx.prefix,
                message=ctx.message,
            )
        if finish_message is not None:
            try:
                await finish_message.add_reaction("✅")
            except discord.HTTPException:
                pass

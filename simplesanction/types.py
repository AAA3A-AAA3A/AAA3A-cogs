from AAA3A_utils import CogsUtils  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import asyncio
from dataclasses import dataclass

from redbot.core.commands.converter import parse_timedelta
from redbot.core.utils.predicates import MessagePredicate

_: Translator = Translator("SimpleSanction", __file__)


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
            if not v.startswith("_") and v not in ("to_json", "process")
        }

    async def process(
        self,
        ctx: commands.Context,
        interaction: typing.Optional[discord.Interaction],
        member: discord.Member,
        duration: typing.Optional[str] = None,
        reason: typing.Optional[str] = "The reason was not given.",
        finish_message_enabled: typing.Optional[bool] = True,
        reason_required: typing.Optional[bool] = True,
        confirmation: typing.Optional[bool] = False,
        show_author: typing.Optional[bool] = True,
        fake_action: typing.Optional[bool] = False,
    ) -> bool:
        if (
            (await self.cog.config.guild(ctx.guild).use_warn_system())
            and self.warn_system_command is not None
            and ctx.bot.get_cog("WarnSystem") is not None
        ):
            use_warn_system = True
        else:
            use_warn_system = False
            if self.cog_required is not None and not ctx.bot.get_cog(self.cog_required):
                if interaction is not None:
                    await interaction.response.defer()
                await ctx.send(
                    _(
                        "The cog `{cog_required}` is not loaded. Please load it, with the command `{prefix}load {cog_required_lowered}`."
                    ).format(
                        prefix=ctx.prefix,
                        cog_required=self.cog_required,
                        cog_required_lowered=self.cog_required.lower(),
                    )
                )
                return False

        if interaction is not None:
            extra_params_inputs = {}
            if duration is None and self.duration_ask_message is not None:
                extra_params_inputs["duration"] = discord.ui.TextInput(
                    label="Duration",
                    style=discord.TextStyle.short,
                    required=True,
                    placeholder=_("The sanction duration."),
                )
            if reason is None and self.reason_ask_message is not None:
                extra_params_inputs["reason"] = discord.ui.TextInput(
                    label="Reason",
                    style=discord.TextStyle.paragraph,
                    required=False,
                    placeholder=_("The reason was not given."),
                )
            if extra_params_inputs:
                modal = discord.ui.Modal(
                    title=f"{self.emoji} {self.label}", custom_id="SimpleSanction"
                )
                modal.on_submit = lambda modal_interaction: modal_interaction.response.defer()
                [modal.add_item(text_input) for text_input in extra_params_inputs.values()]
                await interaction.response.send_modal(modal)
                if await modal.wait():
                    return  # timeout
                if duration is None and self.duration_ask_message is not None:
                    duration = extra_params_inputs["duration"].value
                if reason is None and self.reason_ask_message is not None:
                    reason = extra_params_inputs["reason"].value or _("The reason was not given.")
            else:
                await interaction.response.defer()
        else:
            if duration is None and self.duration_ask_message is not None:
                duration_message = await ctx.send(
                    _(self.duration_ask_message).format(
                        member=member,
                        duration=str(parse_timedelta(duration)) if duration is not None else None,
                        reason=reason,
                        channel=ctx.channel,
                    )
                )
                try:
                    pred = MessagePredicate.same_context(ctx)
                    msg = await ctx.bot.wait_for("message", timeout=60, check=pred)
                    await CogsUtils.delete_message(duration_message)
                    await CogsUtils.delete_message(msg)
                    if msg.content.lower() == "cancel":
                        return
                    duration = msg.content
                except asyncio.TimeoutError:
                    await ctx.send(_("Timed out, please try again."))
                    return
            if reason is None:
                if self.reason_ask_message is not None and reason_required:
                    reason_message = await ctx.send(
                        _(self.reason_ask_message).format(
                            member=member,
                            duration=str(parse_timedelta(duration))
                            if duration is not None
                            else None,
                            reason=reason,
                            channel=ctx.channel,
                        )
                    )
                    try:
                        pred = MessagePredicate.same_context(ctx)
                        msg = await ctx.bot.wait_for("message", timeout=60, check=pred)
                        await CogsUtils.delete_message(reason_message)
                        await CogsUtils.delete_message(msg)
                        if msg.content.lower() == "cancel":
                            return
                        reason = _("The reason was not given.") if reason == "not" else msg.content
                    except asyncio.TimeoutError:
                        await ctx.send(_("Timed out, please try again."))
                        return
                else:
                    reason = _("The reason was not given.")

        if (
            not confirmation
            and self.confirmation_ask_message is not None
            and not await CogsUtils.ConfirmationAsk(
                ctx,
                content=_(self.confirmation_ask_message).format(
                    member=member,
                    duration=str(parse_timedelta(duration)) if duration is not None else None,
                    reason=reason,
                    channel=ctx.channel,
                ),
            )
            and not ctx.assume_yes
        ):
            await CogsUtils.delete_message(ctx.message)
            return

        if finish_message_enabled and self.finish_message is not None:
            embed: discord.Embed = discord.Embed()
            embed.title = f"Sanction Member - {self.emoji} {self.label}"
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
                value=(
                    _(self.finish_message).format(
                        member=member,
                        duration=str(parse_timedelta(duration)) if duration is not None else None,
                        reason=reason,
                        channel=ctx.channel,
                    )
                    + _(
                        "\n*The command may have failed. If so, an error will be displayed below.*"
                    )
                ),
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
            command = self.warn_system_command if use_warn_system else self.command
            command = command.format(
                member=member,
                duration=str(parse_timedelta(duration)) if duration is not None else None,
                reason=reason,
                channel=ctx.channel,
            )
            context = await CogsUtils.invoke_command(
                bot=ctx.bot,
                author=ctx.author,
                channel=ctx.channel,
                command=command,
                prefix=ctx.prefix,
                message=ctx.message,
            )
            if not context.valid:
                raise commands.UserFeedbackCheckFailure(_("This command doesn't exist."))
            elif not await discord.utils.async_all(
                [check(context) for check in context.command.checks]
            ):
                raise commands.UserFeedbackCheckFailure(
                    _("You can't execute this command, in this context.")
                )

        if finish_message is not None:
            try:
                await finish_message.add_reaction("✅")
            except discord.HTTPException:
                pass

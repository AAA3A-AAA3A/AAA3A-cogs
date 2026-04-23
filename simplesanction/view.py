import asyncio
import typing

import discord

from AAA3A_utils import CogsUtils
from redbot.core import commands
from redbot.core.commands.converter import parse_timedelta
from redbot.core.i18n import Translator

from .constants import ACTIONS_DICT

if typing.TYPE_CHECKING:
    from .types import Action

_: Translator = Translator("SimpleSanction", __file__)


class SimpleSanctionView(discord.ui.View):
    def __init__(
        self,
        cog: commands.Cog,
        member: discord.Member,
        duration: str | None = None,
        reason: str | None = "The reason was not given.",
        finish_message_enabled: bool | None = True,
        reason_required: bool | None = True,
        confirmation: bool | None = False,
        show_author: bool | None = True,
        fake_action: bool | None = False,
    ) -> None:
        super().__init__(timeout=180)
        self.cog: commands.Cog = cog
        self.ctx: commands.Context = None

        self.member: discord.Member = member
        self.duration: str | None = duration
        self.reason: str | None = reason

        self.finish_message_enabled: bool | None = finish_message_enabled
        self.reason_required: bool | None = reason_required
        self.confirmation: bool | None = confirmation
        self.show_author: bool | None = show_author
        self.fake_action: bool | None = fake_action

        self._message: discord.Message = None
        self._ready: asyncio.Event = asyncio.Event()

    async def start(self, ctx: commands.Context) -> discord.Message:
        self.ctx: commands.Context = ctx
        embed = await self.get_embed()
        for key, value in ACTIONS_DICT.items():
            button = discord.ui.Button(
                style=discord.ButtonStyle.secondary,
                label=value["label"],
                emoji=value["emoji"],
                custom_id=key,
            )
            button.callback = self._callback
            self.add_item(button)
        self._message: discord.Message = await self.ctx.send(embed=embed, view=self)
        self.cog.views[self._message] = self
        await self._ready.wait()
        return self._message

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id not in [self.ctx.author.id] + list(self.ctx.bot.owner_ids):
            await interaction.response.send_message(
                _("You are not allowed to use this interaction."),
                ephemeral=True,
            )
            return False
        return True

    async def on_timeout(self) -> None:
        for child in self.children:
            child: discord.ui.Item
            if hasattr(child, "disabled") and not (
                isinstance(child, discord.ui.Button) and child.style == discord.ButtonStyle.url
            ):
                child.disabled = True
        try:
            await self._message.edit(view=self)
        except discord.HTTPException:
            pass
        self._ready.set()

    @discord.ui.button(style=discord.ButtonStyle.danger, emoji="✖️", custom_id="close_page")
    async def close_page(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        try:
            await interaction.response.defer()
        except discord.errors.NotFound:
            pass
        self.stop()
        await CogsUtils.delete_message(self._message)
        self._ready.set()

    async def get_embed(self) -> discord.Embed:
        embed: discord.Embed = discord.Embed(
            title=_("Sanction Member"),
            color=await self.ctx.embed_color(),
        )
        embed.description = _(
            "This tool allows you to easily sanction a server member.\nMember mention: {member.mention} - Member ID: {member.id}",
        ).format(member=self.member)
        embed.set_thumbnail(url=await self.cog.config.guild(self.ctx.guild).thumbnail())
        embed.color = await self.ctx.embed_color()
        embed.set_author(
            name=self.member.display_name,
            url=self.member.display_avatar,
            icon_url=self.member.display_avatar,
        )
        if self.show_author:
            embed.set_footer(
                text=self.ctx.author,
                icon_url=self.ctx.author.display_avatar,
            )
        embed.add_field(
            inline=False,
            name="Possible actions:",
            value=" - ".join(
                [f"{action.emoji} {action.label}" for action in self.cog.actions.values()],
            ),
            # value=f"ℹ️ UserInfo - ⚠️ Warn - 🔨 Ban - 🔂 SoftBan - 💨 TempBan\n👢 Kick - 🔇 Mute - 👊 MuteChannel - ⏳ TempMute\n⌛ TempMuteChannel - ❌ Cancel",
        )
        if self.reason is not None:
            embed.add_field(inline=False, name=_("Reason:"), value=f"{self.reason}")
        if self.duration is not None:
            embed.add_field(
                inline=False,
                name=_("Duration:"),
                value=f"{parse_timedelta(self.duration)}",
            )
        return embed

    async def _callback(self, interaction: discord.Interaction):
        if self.fake_action:
            await interaction.response.send_message(
                _(
                    "You are using this command in Fake mode, so no action will be taken, but I will pretend it is the case.",
                ),
                ephemeral=True,
            )
        # else:
        #     await interaction.response.defer()
        action: Action = self.cog.actions[interaction.data["custom_id"]]
        await action.process(
            self.ctx,
            interaction=interaction,
            member=self.member,
            duration=self.duration,
            reason=self.reason,
            finish_message_enabled=self.finish_message_enabled,
            reason_required=await self.cog.config.guild(self.ctx.guild).reason_required(),
            confirmation=self.confirmation,
            show_author=self.show_author,
            fake_action=self.fake_action,
        )

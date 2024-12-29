from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator  # isort:skip
import discord  # isort:skip

from redbot.core.utils.chat_formatting import box

_: Translator = Translator("RumbleNotifier", __file__)


class RumbleNotifierView(discord.ui.View):
    def __init__(self, cog: commands.Cog) -> None:
        super().__init__(timeout=None)
        self.cog: commands.Cog = cog

        self.unsuscribe.label = _("Unsuscribe")
        self.suscribe.label = _("Suscribe")

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if (
            await self.cog.bot.cog_disabled_in_guild(cog=self.cog, guild=interaction.guild)
            or not await self.cog.bot.allowed_by_whitelist_blacklist(who=interaction.user)
            or not await self.cog.config.guild(interaction.guild).enabled()
            or not (channels_ids := await self.cog.config.guild(interaction.guild).channels())
            or (
                interaction.channel.id not in channels_ids
                and interaction.channel.category_id not in channels_ids
            )
            or (role_id := await self.cog.config.guild(interaction.guild).role()) is None
            or (role := interaction.guild.get_role(role_id)) is None
            or not await self.cog.config.guild(interaction.guild).suscribing()
        ):
            await interaction.response.send_message(
                _("You are not allowed to use this interaction."), ephemeral=True
            )
            return False
        if not (
            interaction.guild.me.guild_permissions.manage_roles
            and role.is_assignable()
            and role < interaction.guild.me.top_role
        ):
            await interaction.response.send_message(
                _(
                    "I don't have the required permissions to assign the role. Please contact an administrator."
                ),
            )
            return False
        return True

    @discord.ui.button(
        emoji="✖️",
        label="Unsuscribe",
        style=discord.ButtonStyle.danger,
        custom_id="RumbleNotifier_unsuscribe",
    )
    async def unsuscribe(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)
        role_id = await self.cog.config.guild(interaction.guild).role()
        role = interaction.guild.get_role(role_id)
        if role not in interaction.user.roles:
            await interaction.followup.send(
                _("You are already unsuscribed from the Rumble notifications."), ephemeral=True
            )
            return
        try:
            await interaction.user.remove_roles(role)
        except discord.HTTPException as e:
            await interaction.followup.send(
                _(
                    "An error occurred while trying to remove the role. Please contact an administrator.\n"
                )
                + box(str(e), lang="py"),
            )
        await interaction.followup.send(
            _("You have been removed from the Rumble notifications."), ephemeral=True
        )

    @discord.ui.button(
        emoji="⚔️",
        label="Suscribe",
        style=discord.ButtonStyle.success,
        custom_id="RumbleNotifier_suscribe",
    )
    async def suscribe(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)
        role_id = await self.cog.config.guild(interaction.guild).role()
        role = interaction.guild.get_role(role_id)
        if role in interaction.user.roles:
            await interaction.followup.send(
                _("You are already suscribed to the Rumble notifications."), ephemeral=True
            )
            return
        try:
            await interaction.user.add_roles(role)
        except discord.HTTPException as e:
            await interaction.followup.send(
                _(
                    "An error occurred while trying to add the role. Please contact an administrator.\n"
                )
                + box(str(e), lang="py"),
            )
        await interaction.followup.send(
            _("You have been added to the Rumble notifications."), ephemeral=True
        )

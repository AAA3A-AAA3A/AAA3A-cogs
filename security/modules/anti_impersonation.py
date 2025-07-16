from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

from fuzzywuzzy import StringMatcher

from ..constants import Emojis, DANGEROUS_PERMISSIONS
from ..views import ToggleModuleButton
from .module import Module

_: Translator = Translator("Security", __file__)


class AntiImpersonationModule(Module):
    name = "Anti Impersonation"
    emoji = Emojis.ANTI_IMPERSONATION.value
    description = "Protect your server from impersonation attacks."
    default_config = {
        "enabled": False,
        "quarantine": False,
        "similarity_ratio": 0.8,
    }

    async def load(self) -> None:
        self.cog.bot.add_listener(self.on_member_join)
        self.cog.bot.add_listener(self.on_member_update)

    async def unload(self) -> None:
        self.cog.bot.remove_listener(self.on_member_join)
        self.cog.bot.remove_listener(self.on_member_update)

    async def get_status(self, guild: discord.Guild, check_enabled: bool = True) -> typing.Tuple[typing.Literal["✅", "⚠️", "❌"], str, str]:
        config = await self.config_value(guild)()
        if not config["enabled"] and check_enabled:
            return "❌", "Disabled", "Anti Impersonation is currently disabled."
        if config["quarantine"] and not guild.me.guild_permissions.manage_roles:
            return (
                "⚠️",
                _("Missing Permission"),
                _("I need the `Manage Roles` permission to quarantine members."),
            )
        return "✅", "Enabled", "Anti Impersonation is enabled and configured correctly."

    async def get_settings(self, guild: discord.Guild, view: discord.ui.View):
        title = f"{self.emoji} {self.name} {(await self.get_status(guild))[0]}"
        description = _("Protect your server from impersonation attacks by checking new members and member updates to ensure their display name, their name and their global name aren't similar to members with dangerous permissions.")
        config = await self.config_value(guild)()
        description += _("\n\n**Similarity Ratio:** {ratio}\nA similarity ratio of {ratio} means that names that are {percent}% similar will be flagged as potential impersonation attempts. You can adjust this ratio.").format(
            ratio=config["similarity_ratio"],
            percent=config["similarity_ratio"] * 100,
        )

        components = [ToggleModuleButton(self, guild, view, config["enabled"])]
        quarantine_button: discord.ui.Button = discord.ui.Button(
            label=_("Quarantine Automatically"),
            style=discord.ButtonStyle.success
            if config["quarantine"]
            else discord.ButtonStyle.danger,
            emoji=Emojis.QUARANTINE.value,
        )
        async def quarantine_callback(interaction: discord.Interaction) -> None:
            await interaction.response.defer()
            config["quarantine"] = not config["quarantine"]
            await self.config_value(guild).quarantine.set(config["quarantine"])
            await interaction.followup.send(
                _("Automatic Quarantine is now {status}.").format(
                    status="enabled" if config["quarantine"] else "disabled"
                ),
                ephemeral=True,
            )
            await view._message.edit(embed=await view.get_embed(), view=view)
        quarantine_button.callback = quarantine_callback
        components.append(quarantine_button)

        configure_similarity_ratio_button: discord.ui.Button = discord.ui.Button(
            label=_("Configure Similarity Ratio"),
            style=discord.ButtonStyle.secondary,
        )
        async def configure_similarity_ratio_button_callback(interaction: discord.Interaction) -> None:
            await interaction.response.send_modal(
                ConfigureSimilarityRatioModal(self, guild, view, config)
            )
        configure_similarity_ratio_button.callback = configure_similarity_ratio_button_callback
        components.append(configure_similarity_ratio_button)

        return title, description, [], components

    async def check_member(self, member: discord.Member, only_check: bool = False) -> bool:
        config = await self.config_value(member.guild)()
        if not only_check:
            if not config["enabled"]:
                return
            if await self.cog.is_whitelisted(member, "anti_impersonation"):
                return
        similarity_ratio = config["similarity_ratio"]
        for other_member in member.guild.members:
            if other_member == member:
                continue
            if not any(getattr(other_member.guild_permissions, permission) for permission in DANGEROUS_PERMISSIONS):
                continue
            if self.is_similar(member.display_name, other_member.display_name, similarity_ratio):
                log = _("{member.mention} (`{member.name}`) has a similar display name to {other_member.mention} (`{other_member.name}`): `{member.display_name}` vs `{other_member.display_name}`.").format(
                    member=member,
                    other_member=other_member
                )
            elif self.is_similar(member.name, other_member.name, similarity_ratio):
                log = _("{member.mention} (`{member.name}`) has a similar name to {other_member.mention} (`{other_member.name}`): `{member.name}` vs `{other_member.name}`.").format(
                    member=member,
                    other_member=other_member
                )
            elif (
                member.global_name is not None
                and other_member.global_name is not None
                and self.is_similar(member.global_name, other_member.global_name, similarity_ratio)
            ):
                log = _("{member.mention} (`{member.name}`) has a similar global name to {other_member.mention} (`{other_member.name}`): `{member.global_name}` vs `{other_member.global_name}`.").format(
                    member=member,
                    other_member=other_member
                )
            else:
                continue
            if only_check:
                return True
            reason = _("**Anti Impersonation** - Potential impersonation detected.")
            if config["quarantine"]:
                await self.cog.quarantine_member(
                    member=member,
                    reason=reason,
                    logs=[log],
                )
            else:
                await self.cog.send_modlog(
                    action="notify",
                    member=member,
                    reason=reason,
                    logs=[log],
                )
        return False

    def is_similar(self, name1: str, name2: str, ratio: float) -> bool:
        return StringMatcher.ratio(name1, name2) >= ratio

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        await self.check_member(member)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member) -> None:
        if (
            before.name != after.name
            or before.nick != after.nick
            or before.global_name != after.global_name
        ):
            if after.guild.me.guild_permissions.view_audit_log:
                async for entry in after.guild.audit_logs(
                    limit=3, action=discord.AuditLogAction.member_update,
                ):
                    if entry.target.id != after.id:
                        continue
                    if await self.cog.is_whitelisted(entry.user, "anti_impersonation"):
                        return
            await self.check_member(after)


class ConfigureSimilarityRatioModal(discord.ui.Modal):
    def __init__(
        self,
        module: AntiImpersonationModule,
        guild: discord.Guild,
        view: discord.ui.View,
        config: dict,
    ) -> None:
        self.module: AntiImpersonationModule = module
        self.guild: discord.Guild = guild
        self.view: discord.ui.View = view
        self.config: dict = config
        super().__init__(title=_("Anti Impersonation"))

        self.similarity_ratio: discord.ui.TextInput = discord.ui.TextInput(
            label=_("Similarity Ratio (0.2 - 1.0):"),
            style=discord.TextStyle.short,
            default=str(config["similarity_ratio"]),
            required=True,
        )
        self.add_item(self.similarity_ratio)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        try:
            similarity_ratio = float(self.similarity_ratio.value)
            if not (0.2 <= similarity_ratio <= 1.0):
                raise ValueError(_("Similarity ratio must be between 0.2 and 1.0."))
        except ValueError as e:
            await interaction.followup.send(
                _("Invalid value: {error}").format(error=str(e)),
                ephemeral=True,
            )
            return
        self.config["similarity_ratio"] = similarity_ratio
        await self.module.config_value(self.guild).similarity_ratio.set(similarity_ratio)
        await self.view._message.edit(embed=await self.view.get_embed(), view=self.view)

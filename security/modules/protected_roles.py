from AAA3A_utils import Menu  # isort:skip
from redbot.core.i18n import Translator  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

from redbot.core.utils.chat_formatting import humanize_list, pagify

from ..constants import Emojis, get_non_animated_asset
from ..views import ToggleModuleButton
from .module import Module

_: Translator = Translator("Security", __file__)


class ProtectedRolesModule(Module):
    name = "Protected Roles"
    emoji = Emojis.PROTECTED_ROLES.value
    description = "Manage protected roles in the server."
    default_config = {
        "enabled": True,
        "protected_roles": {},
    }
    configurable_by_trusted_admins = False

    async def load(self) -> None:
        self.cog.bot.add_listener(self.on_audit_log_entry_create)

    async def unload(self) -> None:
        self.cog.bot.remove_listener(self.on_audit_log_entry_create)

    async def get_status(
        self, guild: discord.Guild, check_enabled: bool = True
    ) -> typing.Tuple[typing.Literal["✅", "⚠️", "❎", "❌"], str, str]:
        config = await self.config_value(guild)()
        if not config["enabled"] and check_enabled:
            return "❌", _("Disabled"), _("Protected roles are currently disabled.")
        if not config["protected_roles"]:
            return "❎", _("No Protected Roles"), _("There are no protected roles configured.")
        if not guild.me.guild_permissions.view_audit_log:
            return (
                "⚠️",
                _("Missing Permissions"),
                _("I need the `View Audit Log` permission to monitor protected roles."),
            )
        if not guild.me.guild_permissions.manage_roles:
            return (
                "⚠️",
                _("Missing Permissions"),
                _("I need the `Manage Roles` permission to manage protected roles."),
            )
        return "✅", _("Enabled"), _("Protected roles are enabled and configured.")

    async def get_settings(
        self, guild: discord.Guild, view: discord.ui.View
    ) -> typing.Tuple[str, str, typing.List[typing.Dict], typing.List[discord.ui.Item]]:
        config = await self.config_value(guild)()
        protected_roles = config["protected_roles"]
        title = _("Security — {emoji} {name} ({count}/25) {status}").format(
            emoji=self.emoji,
            name=self.name,
            status=(await self.get_status(guild))[0],
            count=len(protected_roles),
        )
        description = _(
            "*If someone tries to add one of these roles to an unwhitelisted member, it will be removed automatically and the author will be quarantined."
            " If a trusted admin does this, the member will be whitelisted instead.*\n"
        )
        status = await self.get_status(guild)
        if status[0] == "⚠️":
            description += f"\n{status[0]} **{status[1]}**: {status[2]}\n"
        for role_id, whitelisted_members in protected_roles.items():
            if (role := guild.get_role(int(role_id))) is None:
                continue
            description += _(
                "\n- {role.mention} (`{role.name}`) - {count} whitelisted member{s}"
            ).format(
                role=role,
                count=len(whitelisted_members),
                s="" if len(whitelisted_members) == 1 else "s",
            )

        components = [ToggleModuleButton(self, guild, view, config["enabled"])]
        add_select = discord.ui.RoleSelect(
            placeholder=_("Add Protected Role."),
            disabled=not guild.me.guild_permissions.manage_roles or len(protected_roles) >= 25,
        )

        async def add_select_callback(interaction: discord.Interaction) -> None:
            role = add_select.values[0]
            if str(role.id) in protected_roles:
                await interaction.response.send_message(
                    _("This role is already protected."), ephemeral=True
                )
                return
            if not role.is_assignable():
                await interaction.response.send_message(
                    _("This role can't be protected because it is not assignable or is higher than my top role."),
                    ephemeral=True,
                )
                return
            protected_roles[str(role.id)] = []
            await self.config_value(guild).protected_roles.set(protected_roles)
            await interaction.response.send_message(
                _("Protected role {role.mention} (`{role.name}`) added.").format(role=role),
                ephemeral=True,
            )
            await view._message.edit(embed=await view.get_embed(), view=view)

        add_select.callback = add_select_callback
        components.append(add_select)
        if protected_roles:
            manage_select = discord.ui.Select(
                placeholder=_("Manage Protected Role."),
                options=[
                    discord.SelectOption(label=role.name, value=str(role.id))
                    for role_id in protected_roles
                    if (role := guild.get_role(int(role_id))) is not None
                ],
                custom_id="manage_protected_roles_select",
            )

            async def manage_select_callback(interaction: discord.Interaction) -> None:
                await interaction.response.defer(ephemeral=True, thinking=True)
                role = guild.get_role(int(manage_select.values[0]))
                embeds = await self.get_whitelisted_members_embeds(guild, role)
                fake_context = type(
                    "FakeContext",
                    (),
                    {
                        "interaction": interaction,
                        "bot": interaction.client,
                        "guild": interaction.guild,
                        "channel": interaction.channel,
                        "author": interaction.user,
                        "message": interaction.message,
                        "send": interaction.followup.send,
                    },
                )()
                menu = Menu(pages=embeds, ephemeral=True)
                menu.extra_items.extend(
                    [
                        WhitelistMembersSelect(self, guild, role, view, menu),
                    ] + (
                        [RemoveButton(self, guild, role, view)]
                        if await self.cog.is_extra_owner_or_higher(interaction.user)
                        else []
                    )
                )
                await menu.start(fake_context)

            manage_select.callback = manage_select_callback
            components.append(manage_select)

        return title, description, [], components

    async def get_whitelisted_members_embeds(
        self, guild: discord.Guild, role: discord.Role
    ) -> typing.List[discord.Embed]:
        protected_roles = await self.config_value(guild).protected_roles()
        embed: discord.Embed = discord.Embed(
            title=_("Protected Role `{role.name}` - {count} Whitelisted Members").format(
                role=role, count=len(protected_roles[str(role.id)])
            ),
            color=discord.Color.gold(),
        )
        embed.set_footer(text=guild.name, icon_url=get_non_animated_asset(guild.icon))
        description = "\n".join(
            [
                (
                    f"- {member.mention} (`{member}`)"
                    if (member := guild.get_member(int(member_id))) is not None
                    else _("- {member_id} (unknown)").format(member_id=member_id)
                )
                for member_id in protected_roles[str(role.id)]
            ]
        ) or _("No whitelisted members.")
        embeds = []
        for page in pagify(description, page_length=1024):
            e = embed.copy()
            e.description = page
            embeds.append(e)
        return embeds

    async def on_audit_log_entry_create(self, entry: discord.AuditLogEntry) -> None:
        if entry.action != discord.AuditLogAction.member_role_update:
            return
        config = await self.config_value(entry.guild)()
        if not config["enabled"] or not (protected_roles := config["protected_roles"]):
            return
        if entry.user == entry.guild.me or await self.cog.is_whitelisted(entry.target, "protected_roles"):
            return
        to_remove = []
        for role in entry.after.roles:
            if str(role.id) not in protected_roles:
                continue
            if entry.target.id in protected_roles[str(role.id)]:
                continue
            if await self.cog.is_whitelisted(entry.user, "protected_roles"):
                protected_roles[str(role.id)].append(entry.target.id)
                await self.config_value(entry.guild).protected_roles.set(protected_roles)
                continue
            to_remove.append(role)
        if to_remove:
            try:
                await entry.target.remove_roles(
                    *to_remove,
                    reason=_("Protected role removal by Security due to unauthorized addition."),
                    atomic=True,
                )
            except discord.HTTPException:
                pass
            await self.cog.quarantine_member(
                entry.user,
                reason=_("**Protected Roles** - Added a protected role without permission."),
                logs=[
                    _(
                        "Added the protected role {role.mention} (`{role.name}`) to {entry.target.mention} (`{entry.target}`) without permission."
                    ).format(role=role, entry=entry)
                    for role in to_remove
                ],
            )
            if entry.target != entry.user:
                await self.cog.quarantine_member(
                    entry.target,
                    reason=_(
                        "**Protected Roles** - Was given a protected role without permission."
                    ),
                    logs=[
                        _(
                            "The protected role {role.mention} (`{role.name}`) was added to them by {entry.user.mention} (`{entry.user}`) without permission."
                        ).format(role=role, entry=entry)
                        for role in to_remove
                    ],
                )


class WhitelistMembersSelect(discord.ui.UserSelect):
    def __init__(
        self,
        module: "ProtectedRolesModule",
        guild: discord.Guild,
        role: discord.Role,
        view: discord.ui.View,
        menu: Menu,
    ) -> None:
        super().__init__(placeholder=_("Select members to add/remove from whitelist..."))
        self.module: ProtectedRolesModule = module
        self.guild: discord.Guild = guild
        self.role: discord.Role = role
        self.initial_view: discord.ui.View = view
        self.menu: Menu = menu

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)
        protected_roles = await self.module.config_value(self.guild).protected_roles()
        whitelisted = protected_roles[str(self.role.id)]
        added, removed, trusted_admins = [], [], []
        for member in self.values:
            if await self.module.cog.is_trusted_admin_or_higher(member):
                trusted_admins.append(member)
            elif member.id not in whitelisted:
                whitelisted.append(member.id)
                added.append(member)
            else:
                whitelisted.remove(member.id)
                removed.append(member)
        protected_roles[str(self.role.id)] = whitelisted
        await self.module.config_value(self.guild).protected_roles.set(protected_roles)
        self.menu.pages = await self.module.get_whitelisted_members_embeds(self.guild, self.role)
        self.menu._source.entries = self.menu.pages
        self.menu._current_page = self.menu._source.get_max_pages() - 1
        await self.menu.change_page(interaction)
        await self.initial_view._message.edit(
            embed=await self.initial_view.get_embed(), view=self.initial_view
        )
        await interaction.followup.send(
            "\n".join(
                (
                    [
                        _("✅ Added to protected role's whitelist: {members}").format(
                            members=humanize_list([m.mention for m in added])
                        )
                    ]
                    if added
                    else []
                )
                + (
                    [
                        _("❌ Removed from protected role's whitelist: {members}").format(
                            members=humanize_list([m.mention for m in removed])
                        )
                    ]
                    if removed
                    else []
                )
                + (
                    [
                        _("🛡️ Trusted admins and higher not added: {members}").format(
                            members=humanize_list([m.mention for m in removed])
                        )
                    ]
                    if trusted_admins
                    else []
                )
            ),
            ephemeral=True,
        )


class RemoveButton(discord.ui.Button):
    def __init__(
        self,
        module: ProtectedRolesModule,
        guild: discord.Guild,
        role: discord.Role,
        view: discord.ui.View,
    ) -> None:
        super().__init__(
            label=_("Remove from Protected Roles"),
            style=discord.ButtonStyle.danger,
        )
        self.module: ProtectedRolesModule = module
        self.guild: discord.Guild = guild
        self.role: discord.Role = role
        self.initial_view: discord.ui.View = view

    async def callback(self, interaction: discord.Interaction) -> None:
        await self.module.config_value(self.guild).protected_roles.clear_raw(str(self.role.id))
        await self.view._message.delete()
        await interaction.response.send_message(
            _("Protected role {role.mention} (`{role.name}`) removed.").format(role=self.role),
            ephemeral=True,
        )
        await self.initial_view._message.edit(
            embed=await self.initial_view.get_embed(), view=self.initial_view
        )

from AAA3A_utils import CogsUtils  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import datetime
import functools

from redbot.core.utils.chat_formatting import humanize_list

from .constants import POSSIBLE_ACTIONS, WHITELIST_TYPES, Colors, Emojis, Levels

_: Translator = Translator("Security", __file__)


OBJECT_TYPING = typing.Union[
    discord.Member,
    discord.Role,
    discord.TextChannel,
    discord.VoiceChannel,
    discord.CategoryChannel,
    discord.Webhook,
]


DurationConverter: commands.converter.TimedeltaConverter = commands.converter.TimedeltaConverter(
    minimum=datetime.timedelta(minutes=1),
    maximum=datetime.timedelta(days=365),
    allowed_units=None,
    default_unit="hours",
)


class WhitelistView(discord.ui.View):
    def __init__(self, cog: commands.Cog) -> None:
        super().__init__(timeout=5 * 60)
        self.ctx: commands.Context = None
        self.cog: commands.Cog = cog

        self._object: OBJECT_TYPING = None
        self.whitelist_types = []
        self.whitelist = {}
        self.protected_roles_whitelist = []
        self.config_value = None
        self.saved: bool = False
        self._message: discord.Message = None

        self.select.placeholder = _("Select whitelist types.")
        self.protected_roles_whitelist_select.placeholder = _(
            "Select protected roles to whitelist."
        )
        self.cancel.placeholder = _("Cancel")
        self.save.placeholder = _("Save")

    async def start(self, ctx: commands.Context, _object: OBJECT_TYPING) -> discord.Message:
        self.ctx: commands.Context = ctx
        self._object: OBJECT_TYPING = _object
        embed: discord.Embed = discord.Embed(
            title=_("{emoji} Security Whitelist").format(emoji=Emojis.WHITELIST.value),
            color=Colors.WHITELIST.value,
            timestamp=ctx.message.created_at,
        )
        embed.set_thumbnail(
            url=self._object.display_avatar
            if isinstance(self._object, discord.Member)
            else self._object.guild.icon
            if isinstance(self._object, discord.Role)
            else None
        )
        embed.set_footer(text=ctx.guild.name, icon_url=ctx.guild.icon)
        self.whitelist_types = [
            whitelist_type
            for whitelist_type in WHITELIST_TYPES
            if (
                isinstance(_object, (discord.Member, discord.Role))
                or (isinstance(_object, (discord.TextChannel, discord.VoiceChannel, discord.Webhook)) and whitelist_type["channels"])
                or (isinstance(_object, discord.CategoryChannel) and whitelist_type["categories"])
                or (isinstance(_object, discord.Webhook) and whitelist_type["webhooks"])
            )
        ]
        self.remove_item(self.protected_roles_whitelist_select)
        if isinstance(self._object, discord.Member):
            embed.description = _(
                "👤 **Target:** {member.mention} (`{member}`) {member_emojis}"
            ).format(
                member=_object,
                member_emojis=await self.cog.get_member_emojis(_object),
            )
            self.config_value = self.cog.config.member(self._object).whitelist
            if protected_roles := {
                protected_role: whitelisted_members
                for protected_role_id, whitelisted_members in (
                    await self.cog.config.guild(
                        self._object.guild
                    ).modules.protected_roles.protected_roles()
                ).items()
                if (protected_role := self._object.guild.get_role(int(protected_role_id)))
                is not None
            }:
                self.protected_roles_whitelist = [
                    str(protected_role.id)
                    for protected_role, whitelisted_members in protected_roles.items()
                    if self._object.id in whitelisted_members
                ]
                for protected_role in protected_roles:
                    self.protected_roles_whitelist_select.options.append(
                        discord.SelectOption(
                            label=protected_role.name,
                            value=str(protected_role.id),
                            default=str(protected_role.id) in self.protected_roles_whitelist,
                        )
                    )
                self.protected_roles_whitelist_select.max_values = len(
                    self.protected_roles_whitelist_select.options
                )
                self.add_item(self.protected_roles_whitelist_select)
        elif isinstance(self._object, discord.Role):
            embed.description = _("{emoji} **Target:** {role.mention} (`{role}`)").format(emoji=Emojis.ROLE.value, role=_object)
            self.config_value = self.cog.config.role(self._object).whitelist
        elif isinstance(self._object, discord.Webhook):
            embed.description = _("{emoji} **Target:** {webhook.name} (`{webhook.id}`)").format(
                emoji=Emojis.WEBHOOK.value,
                webhook=_object,
            )
            self.config_value = self.cog.config.custom("webhook", _object.id).whitelist
        else:
            embed.description = _("{emoji} **Target:** {channel.mention} (`{channel}`)").format(
                emoji=Emojis.CHANNEL.value,
                channel=_object,
            )
            self.config_value = self.cog.config.channel(self._object).whitelist
        if isinstance(self._object, discord.Member) and await self.cog.is_moderator_or_higher(self._object):
            embed.add_field(
                name="\u200B",
                value=_(
                    "ℹ️ Your staff members always possess these whitelist types: {staff_whitelist_types}."
                ).format(
                    staff_whitelist_types=humanize_list(
                        [
                            f"`{whitelist_type['name']}`"
                            for whitelist_type in self.whitelist_types
                            if whitelist_type["staff_allowed"]
                        ]
                    )
                ),
            )
        self.whitelist = await self.config_value()
        for whitelist_type in self.whitelist_types:
            self.select.options.append(
                discord.SelectOption(
                    label=whitelist_type["name"],
                    emoji=whitelist_type["emoji"],
                    description=whitelist_type["description"],
                    value=whitelist_type["value"],
                    default=self.whitelist[whitelist_type["value"]],
                )
            )
        self.select.max_values = len(self.select.options)
        self._message: discord.Message = await ctx.send(embed=embed, view=self)
        self.cog.views[self._message] = self
        if not await self.wait():
            await self.on_timeout()
        return self._message

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.ctx.author:
            await interaction.response.send_message(
                _("You are not allowed to use this interaction."), ephemeral=True
            )
            return False
        return True

    async def on_timeout(self) -> None:
        embed = self._message.embeds[0]
        if self.saved:
            embed.description += _(
                "\n{emoji} **Issued by:** {issued_by.mention} (`{issued_by}`) {issued_by_emojis}"
            ).format(
                emoji=Emojis.ISSUED_BY.value,
                issued_by=self.ctx.author,
                issued_by_emojis=await self.cog.get_member_emojis(self.ctx.author),
            )
        embed.description += "\n\n" + "\n".join(
            [
                f"{'✅' if self.whitelist[whitelist_type['value']] else '❌'} {whitelist_type['name']}"
                for whitelist_type in self.whitelist_types
            ]
        )
        if isinstance(self._object, discord.Member) and self.protected_roles_whitelist:
            embed.description += "\n\n" + _(
                "**Protected Roles Whitelist:** {protected_roles}"
            ).format(
                protected_roles=humanize_list(
                    [
                        protected_role.mention
                        for protected_role_id in self.protected_roles_whitelist
                        if (protected_role := self._object.guild.get_role(int(protected_role_id)))
                        is not None
                    ]
                ),
            )
        try:
            await self._message.edit(embed=embed, view=None)
        except discord.HTTPException:
            pass

    @discord.ui.select(placeholder="Select whitelist types.", min_values=0)
    async def select(self, interaction: discord.Interaction, select: discord.ui.Select) -> None:
        await interaction.response.defer()
        selected_values = select.values
        for whitelist_type in self.whitelist_types:
            self.whitelist[whitelist_type["value"]] = whitelist_type["value"] in selected_values

    @discord.ui.select(placeholder="Select protected roles to whitelist.", min_values=0)
    async def protected_roles_whitelist_select(
        self, interaction: discord.Interaction, select: discord.ui.Select
    ) -> None:
        await interaction.response.defer()
        self.protected_roles_whitelist = select.values

    @discord.ui.button(emoji="✖️", label="Cancel", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer()
        self.whitelist = await self.config_value()
        self.stop()

    @discord.ui.button(emoji="✅", label="Save", style=discord.ButtonStyle.success)
    async def save(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer()
        await self.config_value.set(self.whitelist)
        if isinstance(self._object, discord.Member):
            protected_roles = await self.cog.config.guild(
                self._object.guild
            ).modules.protected_roles.protected_roles()
            for protected_role_id, whitelisted_members in protected_roles.items():
                if protected_role_id in self.protected_roles_whitelist:
                    if self._object.id not in whitelisted_members:
                        whitelisted_members.append(self._object.id)
                else:
                    if self._object.id in whitelisted_members:
                        whitelisted_members.remove(self._object.id)
            await self.cog.config.guild(
                self._object.guild
            ).modules.protected_roles.protected_roles.set(protected_roles)
        self.saved = True
        self.stop()


class SettingsView(discord.ui.View):
    def __init__(self, cog: commands.Cog) -> None:
        view_children_items = self.__view_children_items__
        self.__view_children_items__ = []
        super().__init__(timeout=5 * 60)
        self.__view_children_items__ = view_children_items
        self._init_children()
        self.ctx: commands.Context = None
        self.cog: commands.Cog = cog

        self.page: str = "overview"
        self._message: discord.Message = None

        self.reset_recovery_key.label = _("Reset Recovery Key")
        self.create_quarantine_role.label = _("Create Quarantine Role")
        self.create_modlog_channel.label = _("Create Modlog Channel")
        self.quarantine_role_select.placeholder = _("Select Quarantine Role")
        self.modlog_channel_select.placeholder = _("Select Modlog Channel")
        self.modlog_ping_role_select.placeholder = _("Select Modlog Ping Role")
        self.extra_owners_select.placeholder = _("Manage Extra Owners")
        self.trusted_admins_select.placeholder = _("Manage Trusted Admins")

    async def start(self, ctx: commands.Context, page: str = "overview") -> discord.Message:
        self.ctx: commands.Context = ctx
        self.page: str = page
        self.select.options.append(
            discord.SelectOption(
                emoji="🏘️",
                label=_("Overview"),
                value="overview",
            )
        )
        self.select.options.append(
            discord.SelectOption(
                emoji="🛡️",
                label=_("Authority Members"),
                description=_("Manage Extra Owners and Trusted Admins."),
                value="authority_members",
            )
        )
        for module in self.cog.modules.values():
            self.select.options.append(
                discord.SelectOption(
                    emoji=module.emoji,
                    label=module.name,
                    description=module.description,
                    value=module.key_name(),
                )
            )
        self._message: discord.Message = await self.ctx.send(
            embed=await self.get_embed(),
            view=self,
        )
        self.cog.views[self._message] = self
        return self._message

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.ctx.author:
            await interaction.response.send_message(
                _("You are not allowed to use this interaction."), ephemeral=True
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

    async def get_embed(self) -> discord.Embed:
        embed: discord.Embed = discord.Embed(
            timestamp=self.ctx.message.created_at,
        )
        embed.set_author(
            name=_("Invoked by {author.display_name} ({author.id})").format(author=self.ctx.author),
            icon_url=self.ctx.author.display_avatar,
        )
        embed.set_footer(text=self.ctx.guild.name, icon_url=self.ctx.guild.icon)
        self.clear_items()
        self.add_item(self.select)
        for option in self.select.options:
            option.default = option.value == self.page
        if self.page == "overview":
            embed.title = _("Security — Overview")
            config = await self.cog.config.guild(self.ctx.guild).all()
            if await self.cog.is_owner_or_higher(self.ctx.author):
                if config["recovery_key"] is None:
                    await self.cog.send_recovery_key(self.ctx.guild)
                else:
                    self.add_item(self.reset_recovery_key)
            quarantine_role = (
                quarantine_role
                if (quarantine_role_id := config["quarantine_role"]) is not None
                and (quarantine_role := self.ctx.guild.get_role(quarantine_role_id)) is not None
                else None
            )
            modlog_channel = (
                modlog_channel
                if (modlog_channel_id := config["modlog_channel"]) is not None
                and (modlog_channel := self.ctx.guild.get_channel(modlog_channel_id)) is not None
                else None
            )
            modlog_ping_role = (
                modlog_ping_role
                if (modlog_ping_role_id := config["modlog_ping_role"]) is not None
                and (modlog_ping_role := self.ctx.guild.get_role(modlog_ping_role_id)) is not None
                else None
            )
            embed.description = _(
                "**Quarantine Role:** {quarantine_role}\n"
                "**Modlog Channel:** {modlog_channel}\n"
                "**Modlog Ping Role:** {modlog_ping_role}"
            ).format(
                quarantine_role=f"{quarantine_role.mention} (`{quarantine_role}`)"
                if quarantine_role is not None
                else _("Not set (Automatically created when needed)"),
                modlog_channel=f"{modlog_channel.mention} (`{modlog_channel}`)"
                if modlog_channel is not None
                else _("Not set (Automatically created when needed)"),
                modlog_ping_role=f"{modlog_ping_role.mention} (`{modlog_ping_role}`)"
                if modlog_ping_role is not None
                else _("Not set"),
            )
            if (
                higher_roles := [
                    role for role in self.ctx.guild.roles if role >= self.ctx.guild.me.top_role
                ]
            ) and any(
                [
                    not await self.cog.is_trusted_admin_or_higher(member)
                    for higer_role in higher_roles
                    for member in higer_role.members
                ]
            ):
                embed.description += _(
                    "\n⚠️ The bot can't manage {count} role(s) that are higher or equal than its top role: they are considered immune, but can't access features and settings."
                ).format(count=len(higher_roles))
            is_extra_owner_or_higher = await self.cog.is_extra_owner_or_higher(self.ctx.author)
            if quarantine_role is None:
                self.add_item(self.create_quarantine_role)
            else:
                self.quarantine_role_select.default_values = [quarantine_role]
            if is_extra_owner_or_higher:
                self.add_item(self.quarantine_role_select)
            if modlog_channel is None:
                self.add_item(self.create_modlog_channel)
            else:
                self.modlog_channel_select.default_values = [modlog_channel]
            if is_extra_owner_or_higher:
                self.add_item(self.modlog_channel_select)
            if modlog_ping_role is not None:
                self.modlog_ping_role_select.default_values = [modlog_ping_role]
            if is_extra_owner_or_higher:
                self.add_item(self.modlog_ping_role_select)
            for module in self.cog.modules.values():
                status = await module.get_status(self.ctx.guild)
                embed.add_field(
                    name=f"{module.emoji} {module.name}",
                    value=f"{status[0]}{' ' + status[1] if status[0] != '✅' else ''}",
                    inline=True,
                )
        elif self.page == "authority_members":
            embed.title = _("Security — Authority Members")
            embed.description = _(
                "💥 Trusted Admins and Extra Owners are **100% immune** to Security, meaning they will **NEVER** be punished by Security for anything they do.\n"
                "**You should only give these levels to people you really trust!**"
            )
            all_members = await self.cog.config.all_members(self.ctx.guild)
            extra_owners = [
                member
                for member_id, data in all_members.items()
                if data["level"] == Levels.EXTRA_OWNER.name
                and (member := self.ctx.guild.get_member(member_id)) is not None
            ]
            trusted_admins = [
                member
                for member_id, data in all_members.items()
                if data["level"] == Levels.TRUSTED_ADMIN.name
                and (member := self.ctx.guild.get_member(member_id)) is not None
            ]
            embed.add_field(
                name=_("Extra Owners ({count}/5):").format(count=len(extra_owners)),
                value="\n".join(
                    [f"- {member.mention} (`{member}`) {await self.cog.get_member_emojis(member)}" for member in extra_owners]
                )
                + ("\n" if extra_owners else "")
                + _(
                    "⚙️ *They can change **all settings** of Security, and can also manage Trusted Admins.*"
                ),
                inline=False,
            )
            embed.add_field(
                name=_("Trusted Admins ({count}/8):").format(count=len(trusted_admins)),
                value="\n".join(
                    [f"- {member.mention} (`{member}`) {await self.cog.get_member_emojis(member)}" for member in trusted_admins]
                )
                + ("\n" if trusted_admins else "")
                + _("⚙️ *They can change **most settings** of Security.*"),
                inline=False,
            )
            if await self.cog.is_owner_or_higher(self.ctx.author):
                self.add_item(self.extra_owners_select)
            if await self.cog.is_extra_owner_or_higher(self.ctx.author):
                self.add_item(self.trusted_admins_select)
        else:
            module = self.cog.modules[self.page]
            status = await module.get_status(self.ctx.guild)
            embed.color = (
                discord.Color.green()
                if status[0] == "✅"
                else (discord.Color.orange() if status[0] == "⚠️" else discord.Color.red())
            )
            embed.title, embed.description, embed._fields, components = await module.get_settings(
                self.ctx.guild, self
            )
            for component in components:
                if (
                    not module.configurable_by_trusted_admins
                    and not await self.cog.is_extra_owner_or_higher(self.ctx.author)
                ):
                    continue
                self.add_item(component)
        return embed

    @discord.ui.select(min_values=1, max_values=1)
    async def select(self, interaction: discord.Interaction, select: discord.ui.Select) -> None:
        self.page = select.values[0]
        await interaction.response.edit_message(embed=await self.get_embed(), view=self)

    @discord.ui.button(emoji="🔑", label="Reset Recovery Key", style=discord.ButtonStyle.primary)
    async def reset_recovery_key(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)
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
                "send": functools.partial(interaction.followup.send, wait=True),
            },
        )()
        if not await CogsUtils.ConfirmationAsk(
            fake_context,
            _(
                "⚠️ Are you sure you want to reset the recovery key? This will invalidate the current key and generate a new one."
            ),
            timeout_message=None,
            ephemeral=True,
        ):
            return
        try:
            await self.cog.send_recovery_key(self.ctx.guild)
        except RuntimeError as e:
            await interaction.followup.send(
                _("⚠️ Failed to reset recovery key: {error}").format(error=str(e)), ephemeral=True
            )

    @discord.ui.button(label="Create Quarantine Role", style=discord.ButtonStyle.primary)
    async def create_quarantine_role(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await interaction.response.defer(thinking=True, ephemeral=True)
        try:
            await self.cog.create_or_update_quarantine_role(self.ctx.guild)
        except RuntimeError as e:
            await interaction.followup.send(
                _("⚠️ Failed to create quarantine role: {error}").format(error=str(e)), ephemeral=True
            )
            return
        await interaction.followup.send(
            _("✅ Quarantine role has been created successfully."), ephemeral=True
        )
        await self._message.edit(embed=await self.get_embed(), view=self)

    @discord.ui.button(label="Create Modlog Channel", style=discord.ButtonStyle.primary)
    async def create_modlog_channel(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await interaction.response.defer(thinking=True, ephemeral=True)
        try:
            await self.cog.create_modlog_channel(self.ctx.guild)
        except RuntimeError as e:
            await interaction.followup.send(
                _("⚠️ Failed to create modlog channel: {error}").format(error=str(e)), ephemeral=True
            )
            return
        await interaction.followup.send(
            _("✅ Modlog channel has been created successfully."), ephemeral=True
        )
        await self._message.edit(embed=await self.get_embed(), view=self)

    @discord.ui.select(
        cls=discord.ui.RoleSelect, placeholder="Select Quarantine Role", min_values=0, max_values=1
    )
    async def quarantine_role_select(
        self, interaction: discord.Interaction, select: discord.ui.Select
    ) -> None:
        await interaction.response.defer(thinking=True, ephemeral=True)
        if select.values:
            quarantine_role = select.values[0]
            if not quarantine_role.is_assignable():
                await interaction.followup.send(
                    _(
                        "⚠️ The selected role is not assignable by the bot. Please select a role that the bot can assign."
                    ),
                    ephemeral=True,
                )
                return
            await self.cog.config.guild(self.ctx.guild).quarantine_role.set(quarantine_role.id)
            await interaction.followup.send(
                _(
                    "⚠️ Quarantine role will lose all its permissions and overwrites will be added to each channel, when needed."
                ),
                ephemeral=True,
            )
        else:
            await self.cog.config.guild(self.ctx.guild).quarantine_role.clear()
            await interaction.followup.send(
                _("✅ Quarantine role will be created when needed."),
                ephemeral=True,
            )
        await self._message.edit(embed=await self.get_embed(), view=self)

    @discord.ui.select(
        cls=discord.ui.ChannelSelect,
        channel_types=[discord.ChannelType.text],
        placeholder="Select Modlog Channel",
        min_values=0,
        max_values=1,
    )
    async def modlog_channel_select(
        self, interaction: discord.Interaction, select: discord.ui.Select
    ) -> None:
        await interaction.response.defer(thinking=True, ephemeral=True)
        if select.values:
            modlog_channel = select.values[0]
            permissions = interaction.guild.get_channel(modlog_channel.id).permissions_for(self.ctx.guild.me)
            if not (
                permissions.view_channel
                and permissions.send_messages
            ):
                await interaction.followup.send(
                    _(
                        "⚠️ The selected channel is not accessible by the bot. Please select a channel that the bot can access."
                    ),
                    ephemeral=True,
                )
                return
            await self.cog.config.guild(self.ctx.guild).modlog_channel.set(modlog_channel.id)
            await interaction.followup.send(
                _("✅ Modlog channel is now set."),
                ephemeral=True,
            )
        else:
            await self.cog.config.guild(self.ctx.guild).modlog_channel.clear()
            await interaction.followup.send(
                _("⚠️ Modlog channel will be created when needed."),
                ephemeral=True,
            )
        await self._message.edit(embed=await self.get_embed(), view=self)

    @discord.ui.select(
        cls=discord.ui.RoleSelect,
        placeholder="Select Modlog Ping Role",
        min_values=0,
        max_values=1,
    )
    async def modlog_ping_role_select(
        self, interaction: discord.Interaction, select: discord.ui.Select
    ) -> None:
        await interaction.response.defer(ephemeral=True)
        if select.values:
            await self.cog.config.guild(self.ctx.guild).modlog_ping_role.set(select.values[0].id)
            await interaction.followup.send(
                _("✅ Modlog ping role is now set."), ephemeral=True
            )
        else:
            await self.cog.config.guild(self.ctx.guild).modlog_ping_role.clear()
            await interaction.followup.send(
                _("⚠️ Modlog ping role removed.")
            )
        await self._message.edit(embed=await self.get_embed(), view=self)

    @discord.ui.select(
        cls=discord.ui.UserSelect, placeholder="Manage Extra Owners", min_values=0, max_values=1
    )
    async def extra_owners_select(
        self, interaction: discord.Interaction, select: discord.ui.Select
    ) -> None:
        if not select.values:
            await interaction.response.defer()
            return
        await interaction.response.defer(thinking=True, ephemeral=True)
        member = select.values[0]
        if await self.cog.is_owner_or_higher(member):
            await interaction.followup.send(
                _("⚠️ This member is higher than Extra Owners."), ephemeral=True
            )
            return
        level = await self.cog.config.member(member).level()
        if level == Levels.EXTRA_OWNER.name:
            await self.cog.config.member(member).level.clear()
            await interaction.followup.send(
                _("✅ Member {member.mention} **is no longer an Extra Owner**.").format(
                    member=member
                ),
                ephemeral=True,
            )
        elif (
            len(
                [
                    m
                    for m in (await self.cog.config.all_members(self.ctx.guild)).values()
                    if m["level"] == Levels.EXTRA_OWNER.name
                ]
            )
            >= 5
        ):
            await interaction.followup.send(
                _("⚠️ You can't add more than **5 Extra Owners**."), ephemeral=True
            )
        else:
            await self.cog.config.member(member).level.set(Levels.EXTRA_OWNER.name)
            await interaction.followup.send(
                _("✅ Member {member.mention} **is now an Extra Owner**.").format(member=member),
                ephemeral=True,
            )
        await self._message.edit(embed=await self.get_embed(), view=self)

    @discord.ui.select(
        cls=discord.ui.UserSelect, placeholder="Manage Trusted Admins", min_values=0, max_values=1
    )
    async def trusted_admins_select(
        self, interaction: discord.Interaction, select: discord.ui.Select
    ) -> None:
        if not select.values:
            await interaction.response.defer()
            return
        await interaction.response.defer(thinking=True, ephemeral=True)
        member = select.values[0]
        if await self.cog.is_owner_or_higher(member):
            await interaction.followup.send(
                _("⚠️ This member is higher than Extra Owners."), ephemeral=True
            )
            return
        level = await self.cog.config.member(member).level()
        if level == Levels.TRUSTED_ADMIN.name:
            await self.cog.config.member(member).level.clear()
            await interaction.followup.send(
                _("✅ Member {member.mention} **is no longer a Trusted Admin**.").format(
                    member=member
                ),
                ephemeral=True,
            )
        elif (
            len(
                [
                    m
                    for m in (await self.cog.config.all_members(self.ctx.guild)).values()
                    if m["level"] == Levels.TRUSTED_ADMIN.name
                ]
            )
            >= 8
        ):
            await interaction.followup.send(
                _("⚠️ You can't add more than **8 Trusted Admins**."), ephemeral=True
            )
        else:
            await self.cog.config.member(member).level.set(Levels.TRUSTED_ADMIN.name)
            await interaction.followup.send(
                _("✅ Member {member.mention} **is now a Trusted Admin**.").format(member=member),
                ephemeral=True,
            )
        await self._message.edit(embed=await self.get_embed(), view=self)


class ToggleModuleButton(discord.ui.Button):
    def __init__(
        self, module, guild: discord.Guild, view: discord.ui.View, enabled: bool
    ) -> None:
        super().__init__(
            label=_("Disable") if enabled else _("Enable"),
            style=discord.ButtonStyle.danger if enabled else discord.ButtonStyle.success,
        )
        self.module = module
        self.guild: discord.Guild = guild
        self.initial_view: discord.ui.View = view
        self.enabled: bool = enabled

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(thinking=True, ephemeral=True)
        self.enabled = not self.enabled
        await self.module.config_value(self.guild).enabled.set(self.enabled)
        await interaction.followup.send(
            _("✅ Module **{module}** has been **{status}**.").format(
                module=self.module.name,
                status=_("enabled") if self.enabled else _("disabled"),
            ),
            ephemeral=True,
        )
        await self.initial_view._message.edit(
            embed=await self.initial_view.get_embed(), view=self.initial_view
        )


class ActionsView(discord.ui.View):
    def __init__(
        self,
        cog: commands.Cog,
        member: discord.Member,
        staff_allowed: bool = False,
        context_message: typing.Optional[discord.Message] = None,
    ) -> None:
        super().__init__(timeout=24 * 60)
        self.cog: commands.Cog = cog
        self.member: discord.Member = member
        self.staff_allowed: bool = staff_allowed
        self.is_quarantined: bool = False
        self.is_timed_out: bool = False
        self.is_muted: bool = False
        self.context_message: typing.Optional[discord.Message] = context_message
        self._message: discord.Message = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not self.staff_allowed:
            if not await self.cog.is_trusted_admin_or_higher(interaction.user):
                await interaction.response.send_message(
                    _("You are not allowed to use this interaction."), ephemeral=True
                )
                return False
        else:
            if not await self.cog.is_moderator_or_higher(interaction.user):
                await interaction.response.send_message(
                    _("You are not allowed to use this interaction."), ephemeral=True
                )
                return False
        return True

    async def on_timeout(self) -> None:
        await self.populate(include_actions=False)
        try:
            await self._message.edit(view=self)
        except discord.HTTPException:
            pass

    async def populate(self, include_actions: bool = True) -> None:
        self.clear_items()
        if include_actions and self.member.guild.get_member(self.member.id) is not None:
            self.is_quarantined = await self.cog.is_quarantined(self.member)
            self.is_timed_out = self.member.is_timed_out()
            mute_check = (Mutes := self.cog.bot.get_cog("Mutes")) is not None and hasattr(
                Mutes, "mute_user"
            )
            self.is_muted = (
                mute_check
                and hasattr(self.member, "_server_mutes")
                and self.member.id in Mutes._server_mutes[self.member.guild.id]
            )
            for action in POSSIBLE_ACTIONS:
                unquarantine = action["value"] == "quarantine" and self.is_quarantined
                untimeout = action["value"] == "timeout" and self.is_timed_out
                unmute = action["value"] == "mute" and self.is_muted
                button: discord.ui.Button = discord.ui.Button(
                    emoji=action["emoji"] if not unquarantine else Emojis.UNQUARANTINE.value,
                    label=(
                        _("Unquarantine")
                        if unquarantine
                        else (
                            _("Untimeout")
                            if untimeout
                            else (_("Unmute") if unmute else action["name"])
                        )
                    ),
                    style=discord.ButtonStyle.secondary,
                    disabled=(
                        not getattr(self.member.guild.me.guild_permissions, action["permission"])
                        and (
                            action["value"] != "timeout"
                            or not self.member.guild_permissions.administrator
                        )
                        and (action["value"] != "mute" or mute_check)
                    ),
                )
                button.callback = functools.partial(self.action_callback, action=action)
                self.add_item(button)
        if self.context_message is not None:
            self.add_item(
                discord.ui.Button(
                    label=_("View Context Message"),
                    style=discord.ButtonStyle.link,
                    url=self.context_message.jump_url,
                )
            )

    async def action_callback(
        self, interaction: discord.Interaction, action: typing.Dict[str, str]
    ) -> None:
        if not getattr(
            interaction.user.guild_permissions, action["permission"]
        ) and not await self.cog.is_trusted_admin_or_higher(interaction.user):
            await interaction.response.send_message(
                _("You are not allowed to use this action."), ephemeral=True
            )
            return
        await self.populate(include_actions=False)
        if action["value"] == "timeout" and self.is_timed_out:
            action = "untimeout"
        elif action["value"] == "mute" and self.is_muted:
            action = "unmute"
        elif action["value"] == "quarantine" and self.is_quarantined:
            action = "unquarantine"
        else:
            action = action["value"]
        duration = None
        if action not in ("timeout", "mute"):
            await interaction.response.defer(thinking=True, ephemeral=True)
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
                    "send": functools.partial(interaction.followup.send, wait=True),
                },
            )()
            if not await CogsUtils.ConfirmationAsk(
                fake_context,
                _("⚠️ Are you sure you want to {action} {member.mention}?").format(
                    action=action,
                    member=self.member,
                ),
                timeout_message=None,
                ephemeral=True,
            ):
                return
        else:
            modal: discord.ui.Modal = discord.ui.Modal(
                title=_("{action} Duration").format(action=action.title()),
                timeout=120,
            )
            duration_input: discord.ui.TextInput = discord.ui.TextInput(
                label=_("Duration:"),
                placeholder=_("Enter the duration (e.g. 3h)..."),
                required=True,
            )
            modal.add_item(duration_input)

            async def on_submit(modal_interaction: discord.Interaction) -> None:
                await modal_interaction.response.defer()
                nonlocal duration
                try:
                    duration = await DurationConverter.convert(None, duration_input.value)
                except commands.BadArgument as e:
                    await modal_interaction.followup.send(
                        _("Invalid duration: {error}").format(error=str(e)), ephemeral=True
                    )

            modal.on_submit = on_submit
            await interaction.response.send_modal(modal)
            if await modal.wait() or duration is None:
                return
        reason = _("**Security Actions View** - {action}").format(action=action.title())
        if action not in ("quarantine", "unquarantine"):
            await self.cog.send_modlog(
                action=action,
                member=self.member,
                issued_by=interaction.user,
                reason=reason,
                duration=duration,
                context_message=self._message,
            )
        audit_log_reason = f"Security Actions View: issued by {interaction.user.display_name} ({interaction.user.id})"
        if action == "timeout":
            await self.member.timeout(duration, reason=audit_log_reason)
        elif action == "untimeout":
            await self.member.timeout(None, reason=audit_log_reason)
        elif action == "mute":
            Mutes = self.cog.bot.get_cog("Mutes")
            await Mutes.mute_user(
                guild=self.member.guild,
                author=interaction.user,
                user=self.member,
                until=datetime.datetime.now(tz=datetime.timezone.utc) + duration,
                reason=reason,
            )
        elif action == "unmute":
            Mutes = self.cog.bot.get_cog("Mutes")
            await Mutes.unmute_user(
                guild=self.member.guild,
                author=interaction.user,
                user=self.member,
                reason=reason,
            )
        elif action["value"] == "kick":
            await self.member.kick(reason=audit_log_reason)
        elif action["value"] == "ban":
            await self.member.ban(reason=audit_log_reason)
        elif action["value"] == "quarantine":
            await self.cog.quarantine_member(
                member=self.member,
                issued_by=interaction.user,
                reason=reason,
                context_message=self._message,
            )
        elif action["value"] == "unquarantine":
            await self.cog.unquarantine_member(
                member=self.member,
                issued_by=interaction.user,
                reason=reason,
                context_message=self._message,
            )
        await interaction.followup.send(
            _("✅ Action **{action}** has been successfully performed on {member.mention}.").format(
                action=action["name"],
                member=self.member,
            ),
            ephemeral=True,
        )
        await self.on_timeout()
        self.stop()

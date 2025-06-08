from AAA3A_utils import CogsUtils  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import functools
from collections import defaultdict

from redbot.core.utils.chat_formatting import humanize_list

from ..constants import Emojis
from .module import Module

_: Translator = Translator("Security", __file__)


LOCKDOWN_MODES: typing.List[
    typing.Dict[
        typing.Literal["name", "emoji", "description", "value"],
        typing.Union[str, typing.Tuple[str, typing.Any], typing.Callable],
    ]
] = [
    {
        "name": "Server Channels",
        "emoji": "#️⃣",
        "description": _(
            "Prevent members from sending messages in all channels or specific channels."
        ),
        "value": "server_channels",
    },
    {
        "name": "Server Roles",
        "emoji": "👥",
        "description": _("Prevent members from adding or removing roles to/from members."),
        "value": "server_roles",
    },
    {
        "name": "Server Invites",
        "emoji": "🔗",
        "description": _("Prevent members from creating new invites."),
        "value": "server_invites",
    },
    {
        "name": "Kick New Members",
        "emoji": Emojis.KICK.value,
        "description": _("Kick new members who joined while the server is in lockdown."),
        "value": "kick_new_members",
    },
    {
        "name": "Ban New Members",
        "emoji": Emojis.BAN.value,
        "description": _("Ban new members who joined while the server is in lockdown."),
        "value": "ban_new_members",
    },
    {
        "name": "Quarantine all Members with dangerous permissions",
        "emoji": Emojis.QUARANTINE.value,
        "description": _("Quarantine all members with dangerous permissions."),
        "value": "quarantine_dangerous_permissions",
    },
]


class LockdownModule(Module):
    name = "Lockdown"
    emoji = Emojis.LOCKDOWN.value
    description = "Manage lockdown modes in the server."
    default_config = {
        "modes": {option["value"]: False for option in LOCKDOWN_MODES},
        "specific_channels": [],
        "members_with_dangerous_permissions_quarantined": [],
    }
    configurable_by_trusted_admins = False

    def __init__(self, cog: commands.Cog) -> None:
        super().__init__(cog)
        self.action_cache: typing.Dict[discord.Member, typing.List[str]] = defaultdict(list)
        self.warning_cache: typing.Dict[
            typing.Union[discord.abc.GuildChannel, discord.Member], bool
        ] = defaultdict(lambda: False)

    async def load(self) -> None:
        self.cog.bot.add_listener(self.on_message)
        self.cog.bot.add_listener(self.on_audit_log_entry_create)
        self.cog.bot.add_listener(self.on_member_join)

    async def unload(self) -> None:
        self.cog.bot.remove_listener(self.on_message)
        self.cog.bot.remove_listener(self.on_audit_log_entry_create)
        self.cog.bot.remove_listener(self.on_member_join)

    async def get_status(
        self, guild: discord.Guild
    ) -> typing.Tuple[typing.Literal["✅", "⚠️", "❎"], str, str]:
        config = await self.config_value(guild)()
        if all(not enabled for enabled in config["modes"].values()):
            return "❎", _("No Enabled Modes"), _("There are no lockdown modes enabled.")
        missing_permissions = []
        if config["modes"]["server_channels"] and not guild.me.guild_permissions.manage_messages:
            missing_permissions.append("manage_messages")
        if config["modes"]["server_roles"] and not guild.me.guild_permissions.manage_roles:
            missing_permissions.append("manage_roles")
        if config["modes"]["server_invites"] and not guild.me.guild_permissions.manage_guild:
            missing_permissions.append("manage_guild")
        if (config["modes"]["server_roles"] or config["modes"]["server_invites"]) and not guild.me.guild_permissions.view_audit_log:
            missing_permissions.append("view_audit_log")
        if config["modes"]["kick_new_members"] and not guild.me.guild_permissions.kick_members:
            missing_permissions.append("kick_members")
        if config["modes"]["ban_new_members"] and not guild.me.guild_permissions.ban_members:
            missing_permissions.append("ban_members")
        if missing_permissions:
            return (
                "⚠️",
                _("Missing Permissions"),
                _("I need the {permissions} permission{s} to function properly.").format(
                    permissions=humanize_list(
                        [f"`{permission}`" for permission in missing_permissions]
                    ),
                    s="" if len(missing_permissions) == 1 else "s",
                ),
            )
        return "✅", _("Enabled"), _("Lockdown is enabled and configured correctly.")

    async def get_settings(
        self, guild: discord.Guild, view: discord.ui.View
    ) -> typing.Tuple[str, str, typing.List[typing.Dict], typing.List[discord.ui.Item]]:
        title = _("Security — {emoji} {name} {status}").format(
            emoji=self.emoji, name=self.name, status=(await self.get_status(guild))[0]
        )
        description = _(
            "This module allows you to manage lockdown modes to protect your server during raids or emergencies. Members who try to bypass these modes several times after a warning will be quarantined, if the bot has the permission to do so."
        )
        status = await self.get_status(guild)
        if status[0] == "⚠️":
            description += f"\n{status[0]} **{status[1]}**: {status[2]}\n"
        config = await self.config_value(guild)()
        fields = []
        for mode in LOCKDOWN_MODES:
            fields.append(
                dict(
                    name=f"{mode['emoji']} {mode['name']}",
                    value=_("{description}\n**Enabled:** {enabled}").format(
                        description=mode["description"],
                        enabled="✅" if config["modes"][mode["value"]] else "❌",
                    ),
                    inline=True,
                )
            )

        components = []
        modes_select: discord.ui.Select = discord.ui.Select(
            placeholder=_("Lockdown Modes"),
            min_values=0,
            max_values=1,
            options=[
                discord.SelectOption(
                    emoji=mode["emoji"],
                    label=mode["name"],
                    value=mode["value"],
                    description=mode["description"],
                )
                for mode in LOCKDOWN_MODES
            ],
        )

        async def modes_select_callback(interaction: discord.Interaction) -> None:
            if not modes_select.values:
                await interaction.response.defer()
                return
            await interaction.response.defer(ephemeral=True, thinking=True)
            mode = next((m for m in LOCKDOWN_MODES if m["value"] == modes_select.values[0]), None)
            if not config["modes"][mode["value"]]:
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
                    _("⚠️ Are you sure you want to enable **{mode}** mode?").format(
                        mode=mode["name"]
                    ),
                    timeout_message=None,
                    ephemeral=True,
                ):
                    return
            config["modes"][mode["value"]] = not config["modes"][mode["value"]]
            await self.config_value(guild).modes.set_raw(
                mode["value"], value=config["modes"][mode["value"]]
            )
            self.action_cache.clear()
            self.warning_cache.clear()
            if mode["value"] == "quarantine_dangerous_permissions":
                if config["modes"][mode["value"]]:
                    config["members_with_dangerous_permissions_quarantined"] = []
                    for member in guild.members:
                        if any(
                            getattr(member.guild_permissions, perm, False)
                            for perm in (
                                "administrator",
                                "manage_guild",
                                "manage_channels",
                                "manage_roles",
                                "manage_messages",
                                "kick_members",
                                "ban_members",
                            )
                        ) and not await self.cog.is_whitelisted(member, "lockdown"):
                            await self.cog.quarantine_member(
                                member=member,
                                issued_by=interaction.user,
                                reason=_(
                                    "**Lockdown** - Quarantined for having dangerous permissions during lockdown."
                                ),
                                logs=[
                                    _(
                                        "{member.mention} ({member}) has dangerous permissions during lockdown."
                                    ).format(member=member)
                                ],
                            )
                            config["members_with_dangerous_permissions_quarantined"].append(
                                member.id
                            )
                    await self.config_value(
                        guild
                    ).members_with_dangerous_permissions_quarantined.set(
                        config["members_with_dangerous_permissions_quarantined"]
                    )
                else:
                    for member_id in config["members_with_dangerous_permissions_quarantined"]:
                        member = guild.get_member(member_id)
                        if member is not None:
                            await self.cog.unquarantine_member(
                                member=member,
                                issued_by=interaction.user,
                                reason=_(
                                    "**Lockdown** - Unquarantined after disabling dangerous permissions lockdown mode."
                                ),
                            )
                    config["members_with_dangerous_permissions_quarantined"] = []
                    await self.config_value(
                        guild
                    ).members_with_dangerous_permissions_quarantined.set(
                        config["members_with_dangerous_permissions_quarantined"]
                    )
            await interaction.followup.send(
                _("✅ **{mode}** mode has been **{status}**.").format(
                    mode=mode["name"],
                    status=_("enabled") if config["modes"][mode["value"]] else _("disabled"),
                ),
                ephemeral=True,
            )
            await view._message.edit(embed=await view.get_embed(), view=view)

        modes_select.callback = modes_select_callback
        components.append(modes_select)

        specific_channels_select: discord.ui.ChannelSelect = discord.ui.ChannelSelect(
            placeholder=_("Specific Channels..."),
            min_values=0,
            max_values=25,
            default_values=[
                channel
                for channel_id in config["specific_channels"]
                if (channel := guild.get_channel(channel_id)) is not None
            ],
        )

        async def specific_channels_callback(interaction: discord.Interaction) -> None:
            selected_channels = specific_channels_select.values
            config["specific_channels"] = [channel.id for channel in selected_channels]
            await self.config_value(guild).specific_channels.set(config["specific_channels"])
            self.action_cache.clear()
            self.warning_cache.clear()
            await interaction.response.send_message(
                _("✅ Specific channels have been updated."),
                ephemeral=True,
            )
            await view._message.edit(embed=await view.get_embed(), view=view)

        specific_channels_select.callback = specific_channels_callback
        components.append(specific_channels_select)

        return title, description, fields, components

    async def on_message(self, message: discord.Message) -> None:
        if message.guild is None:
            return
        config = await self.config_value(message.guild)()
        if not config["modes"]["server_channels"]:
            return
        if config["specific_channels"] and message.channel.id not in config["specific_channels"]:
            return
        if await self.cog.is_message_whitelisted(message, "lockdown"):
            return
        if not message.channel.permissions_for(message.guild.me).manage_messages:
            return
        await message.delete()
        if not self.warning_cache[message.channel]:
            self.warning_cache[message.channel] = True
            await message.channel.send(
                embed=discord.Embed(
                    title=_("{emoji} Lockdown Warning").format(emoji=Emojis.LOCKDOWN.value),
                    description=_(
                        "A lockdown is currently active in this server. You are not allowed to send messages in any channel. **Please do not attempt to bypass this restriction.**"
                    ),
                    color=discord.Color.red(),
                ).set_footer(text=message.guild.name, icon_url=message.guild.icon),
            )
        self.action_cache[message.author].append(
            _(
                "{author.mention} ({author}) sent a message in {channel.mention} during lockdown."
            ).format(author=message.author, channel=message.channel)
        )
        if (
            len(self.action_cache[message.author]) >= 3
            and message.guild.me.guild_permissions.manage_roles
        ):
            await self.cog.quarantine_member(
                message.author,
                reason=_("**Lockdown** - Several actions during lockdown."),
                logs=self.action_cache[message.author],
            )

    async def on_audit_log_entry_create(self, entry: discord.AuditLogEntry) -> None:
        if entry.user.bot or entry.guild is None:
            return
        if entry.action not in (
            discord.AuditLogAction.member_role_update,
            discord.AuditLogAction.invite_create,
        ):
            return
        if await self.cog.is_whitelisted(entry.user, "lockdown"):
            return
        modes = await self.config_value(entry.guild).modes()
        if entry.action == discord.AuditLogAction.member_role_update and modes["server_roles"]:
            try:
                await entry.target.edit(
                    roles=entry.before.roles,
                    reason=_("Security Lockdown: Role change during lockdown."),
                )
            except discord.HTTPException:
                pass
            if not self.warning_cache[entry.user]:
                self.warning_cache[entry.user] = True
                try:
                    await entry.user.send(
                        embed=discord.Embed(
                            title=_("{emoji} Lockdown Warning").format(
                                emoji=Emojis.LOCKDOWN.value
                            ),
                            description=_(
                                "A lockdown is currently active in this server. You are not allowed to change roles of members. **Please do not attempt to bypass this restriction.**"
                            ),
                            color=discord.Color.red(),
                        ).set_footer(text=entry.guild.name, icon_url=entry.guild.icon),
                    )
                except discord.HTTPException:
                    pass
            self.action_cache[entry.user].append(
                _(
                    "Member {member.mention} [{member}] tried to {action} to/from the member {quarantined_member.mention} [{quarantined_member}] during lockdown."
                ).format(
                    member=entry.user,
                    quarantined_member=entry.target,
                    action=humanize_list(
                        (
                            [
                                _("add the role{s} {roles}").format(
                                    roles=humanize_list(
                                        [
                                            f"{role.mention} (`{role}`)"
                                            for role in entry.after.roles
                                            if role not in entry.before.roles
                                        ]
                                    ),
                                    s=""
                                    if len(
                                        [
                                            role
                                            for role in entry.after.roles
                                            if role not in entry.before.roles
                                        ]
                                    )
                                    == 1
                                    else "s",
                                )
                            ]
                            if any(role not in entry.before.roles for role in entry.after.roles)
                            else []
                        )
                        + (
                            [
                                _("remove the role{s} {roles}").format(
                                    roles=humanize_list(
                                        [
                                            f"{role.mention} (`{role}`)"
                                            for role in entry.before.roles
                                            if role not in entry.after.roles
                                        ]
                                    ),
                                    s=""
                                    if len(
                                        [
                                            role
                                            for role in entry.before.roles
                                            if role not in entry.after.roles
                                        ]
                                    )
                                    == 1
                                    else "s",
                                )
                            ]
                            if any(role not in entry.after.roles for role in entry.before.roles)
                            else []
                        )
                    ),
                ),
            )
        elif entry.action == discord.AuditLogAction.invite_create and modes["server_invites"]:
            try:
                await entry.target.delete(
                    reason=_("Security Lockdown: Invite created during lockdown.")
                )
            except discord.HTTPException as e:
                pass
            if not self.warning_cache[entry.user]:
                self.warning_cache[entry.user] = True
                try:
                    await entry.user.send(
                        embed=discord.Embed(
                            title=_("{emoji} Lockdown Warning").format(
                                emoji=Emojis.LOCKDOWN.value
                            ),
                            description=_(
                                "A lockdown is currently active in this server. You are not allowed to create invites. **Please do not attempt to bypass this restriction.**"
                            ),
                            color=discord.Color.red(),
                        ).set_footer(text=entry.guild.name, icon_url=entry.guild.icon),
                    )
                except discord.HTTPException:
                    pass
            self.action_cache[entry.user].append(
                _("{user.mention} ({user}) created an invite during lockdown.").format(
                    user=entry.user
                )
            )
        if (
            len(self.action_cache[entry.user]) >= 3
            and entry.guild.me.guild_permissions.manage_roles
        ):
            await self.cog.quarantine_member(
                entry.user,
                reason=_("**Lockdown** - Several actions during lockdown."),
                logs=self.action_cache[entry.user],
            )

    async def on_member_join(self, member: discord.Member) -> None:
        if member.bot or member.guild is None:
            return
        modes = await self.config_value(member.guild).modes()
        if modes["kick_new_members"] and member.guild.me.guild_permissions.kick_members:
            await member.kick(reason=_("Security Lockdown: New member joined during lockdown."))
            await self.cog.send_modlog(
                action="kick",
                member=member,
                reason=_("**Lockdown** - Kicked for joining during lockdown."),
                logs=[
                    _("{member.mention} ({member}) joined the server during lockdown.").format(
                        member=member
                    )
                ],
            )
        elif modes["ban_new_members"] and member.guild.me.guild_permissions.ban_members:
            await member.ban(reason=_("Security Lockdown: New member joined during lockdown."))
            await self.cog.send_modlog(
                action="ban",
                member=member,
                reason=_("**Lockdown** - Banned for joining during lockdown."),
                logs=[
                    _("{member.mention} ({member}) joined the server during lockdown.").format(
                        member=member
                    )
                ],
            )

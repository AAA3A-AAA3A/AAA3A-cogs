from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import datetime
from collections import defaultdict

from redbot.core.utils.chat_formatting import box, humanize_list

from ..constants import DANGEROUS_PERMISSIONS, Emojis
from ..views import ToggleModuleButton
from .module import Module

_: Translator = Translator("Security", __file__)


REVERT_AUDIT_LOG_REASON: str = (
    "Reverting action due to suspicious activity detected by Security's Anti Nuke."
)


async def revert_onboarding(entry: discord.AuditLogEntry) -> None:
    """Revert the onboarding changes made by the user."""
    onboarding = await entry._state.http.request(
        discord.http.Route(
            "GET",
            "/guilds/{guild_id}/onboarding",
            guild_id=entry.guild.id,
        )
    )
    role_ids = [
        role_id
        for option in entry.after.options
        for role_id in option["role_ids"]
        if (role := entry.guild.get_role(int(role_id))) is not None
        and all(role_id not in option["role_ids"] for option in entry.before.options)
        and any(
            getattr(role.permissions, dangerous_permission)
            for dangerous_permission in DANGEROUS_PERMISSIONS
        )
    ]
    for prompt in onboarding["prompts"].copy():
        for option in prompt["options"].copy():
            option["role_ids"] = [
                role_id for role_id in option["role_ids"] if role_id not in role_ids
            ]
            if not option["channel_ids"] and not option["role_ids"]:
                prompt["options"].remove(option)
        if not prompt["options"]:
            onboarding["prompts"].remove(prompt)
    await entry._state.http.request(
        discord.http.Route(
            "PUT",
            "/guilds/{guild_id}/onboarding",
            guild_id=entry.guild.id,
        ),
        json=onboarding,
        headers={
            "X-Audit-Log-Reason": REVERT_AUDIT_LOG_REASON,
        },
    )


ANTI_NUKE_OPTIONS: typing.List[
    typing.Dict[
        typing.Literal[
            "name",
            "emoji",
            "description",
            "value",
            "default_enabled",
            "check",
            "log",
            "reason",
            "member_reason",
            "revert",
        ],
        typing.Union[
            str,
            bool,
            typing.Callable[[discord.AuditLogEntry], typing.Union[bool, str]],
            typing.Callable[[], str],
            typing.Optional[
                typing.Callable[[discord.AuditLogEntry], typing.Coroutine[None, None, None]]
            ],
        ],
    ]
] = [
    {
        "name": "Protect Vanity URL",
        "emoji": Emojis.VANITY_URL.value,
        "description": "Prevent changes to the server's vanity URL.",
        "value": "protect_vanity_url",
        "default_enabled": True,
        "check": lambda entry: entry.action == discord.AuditLogAction.guild_update
        and entry.before.vanity_url_code != entry.after.vanity_url_code,
        "log": lambda entry: _(
            "{user.mention} (`{user}`) **changed** the vanity URL from `{before.vanity_url_code}` to `{after.vanity_url_code}` {timestamp}."
        ).format(
            user=entry.user,
            before=entry.before,
            after=entry.after,
            timestamp=f"<t:{int(entry.created_at.timestamp())}:R>",
        ),
        "reason": lambda: _("**Anti Nuke** - Attempted to change the vanity URL."),
        "revert": lambda entry: entry.guild.edit(
            vanity_url_code=entry.before.vanity_url_code,
            reason=REVERT_AUDIT_LOG_REASON,
        ),
    },
    {
        "name": "Detect and react to member prunes",
        "emoji": Emojis.KICK.value,
        "description": "Detect when someone prunes members and react accordingly.",
        "value": "detect_member_prunes",
        "default_enabled": False,
        "check": lambda entry: entry.action == discord.AuditLogAction.member_prune,
        "log": lambda entry: _(
            "{user.mention} (`{user}`) **pruned** {members_removed} members ({delete_member_days} days) {timestamp}."
        ).format(
            user=entry.user,
            members_removed=entry.extra.members_removed,
            delete_member_days=entry.extra.delete_member_days,
            timestamp=f"<t:{int(entry.created_at.timestamp())}:R>",
        ),
        "reason": lambda: _("**Anti Nuke** - Pruned members without proper authorization."),
        "revert": None,
    },
    {
        "name": "Strict Member Role Addition",
        "emoji": Emojis.MEMBER.value,
        "description": "Prevent unauthorized admins given dangerous permissions to members if they don't have them already.",
        "value": "strict_member_role_addition",
        "default_enabled": False,
        "check": lambda entry: (
            entry.action == discord.AuditLogAction.member_role_update
            and any(
                any(getattr(role.permissions, dangerous_permission) for role in entry.after.roles)
                and all(
                    not getattr(role.permissions, dangerous_permission)
                    for role in entry.target.roles + entry.before.roles
                    if role not in entry.after.roles
                )
                for dangerous_permission in DANGEROUS_PERMISSIONS
            )
        ),
        "log": lambda entry: _(
            "{user.mention} (`{user}`) **added** {roles} to {target.mention} (`{target}`) that grant dangerous permissions {timestamp}."
        ).format(
            user=entry.user,
            target=entry.target,
            roles=humanize_list(
                [
                    f"{role.mention} (`{role.name}`)"
                    for role in entry.after.roles
                    if any(
                        getattr(role.permissions, dangerous_permission)
                        and all(
                            not getattr(role.permissions, dangerous_permission)
                            for role in entry.target.roles + entry.before.roles
                            if role not in entry.after.roles
                        )
                        for dangerous_permission in DANGEROUS_PERMISSIONS
                    )
                ]
            ),
            timestamp=f"<t:{int(entry.created_at.timestamp())}:R>",
        )
        + "\n"
        + box(
            "\n".join(
                [
                    f"+ {dangerous_permission.replace('_', ' ').title()}"
                    for dangerous_permission in DANGEROUS_PERMISSIONS
                    if any(
                        getattr(role.permissions, dangerous_permission)
                        and all(
                            not getattr(role.permissions, dangerous_permission)
                            for role in entry.target.roles + entry.before.roles
                            if role not in entry.after.roles
                        )
                        for role in entry.after.roles
                    )
                ]
            ),
            lang="diff",
        ),
        "reason": lambda: _(
            "**Anti Nuke** - Added roles with dangerous permissions to a member without them having those permissions already."
        ),
        "member_reason": lambda: _(
            "**Anti Nuke** - Was given roles that grant dangerous permissions without having them already."
        ),
        "revert": lambda entry: entry.target.remove_roles(
            *[
                role
                for role in entry.after.roles
                if any(
                    getattr(role.permissions, dangerous_permission)
                    and all(
                        not getattr(role.permissions, dangerous_permission)
                        for role in entry.target.roles + entry.before.roles
                        if role not in entry.after.roles
                    )
                    for dangerous_permission in DANGEROUS_PERMISSIONS
                )
            ],
            reason=REVERT_AUDIT_LOG_REASON,
        ),
    },
    {
        "name": "Monitor Public Roles",
        "emoji": Emojis.ROLE.value,
        "description": "Prevent @everyone and main roles from getting dangerous permissions.",
        "value": "protect_everyone_and_main_roles",
        "default_enabled": True,
        "check": lambda entry: (
            entry.action == discord.AuditLogAction.role_update
            and (
                entry.target.is_default()
                or len(entry.target.members) >= len(entry.guild.members) * 0.1
            )
            and entry.before.permissions != entry.after.permissions
            and any(
                getattr(entry.after.permissions, dangerous_permission)
                and not getattr(entry.before.permissions, dangerous_permission)
                for dangerous_permission in DANGEROUS_PERMISSIONS
            )
        ),
        "log": lambda entry: _(
            "{user.mention} (`{user}`) **updated** the permissions of {target.mention} (`{target}`) to include dangerous permissions {timestamp}."
        ).format(
            user=entry.user,
            target=entry.target,
            timestamp=f"<t:{int(entry.created_at.timestamp())}:R>",
        )
        + "\n"
        + box(
            "\n".join(
                [
                    f"+ {dangerous_permission.replace('_', ' ').title()}"
                    for dangerous_permission in DANGEROUS_PERMISSIONS
                    if getattr(entry.after.permissions, dangerous_permission)
                    and not getattr(entry.before.permissions, dangerous_permission)
                ]
            ),
            lang="diff",
        ),
        "reason": lambda: _(
            "**Anti Nuke** - Updated @everyone or main roles to have dangerous permissions."
        ),
        "revert": lambda entry: entry.target.edit(
            permissions=entry.before.permissions,
            reason=REVERT_AUDIT_LOG_REASON,
        ),
    },
    {
        "name": "Monitor Channel Permissions",
        "emoji": Emojis.CHANNEL.value,
        "description": "Prevent @everyone and main roles from getting dangerous permissions in channels.",
        "value": "protect_everyone_and_main_roles_in_channels",
        "default_enabled": False,
        "check": lambda entry: (
            entry.action
            in (discord.AuditLogAction.overwrite_create, discord.AuditLogAction.overwrite_update)
            and isinstance(entry.extra, discord.Role)
            and (
                entry.extra.is_default()
                or len(entry.extra.members) >= len(entry.guild.members) * 0.1
            )
            and any(
                getattr(entry.after.allow, dangerous_permission)
                and not getattr(entry.before.allow, dangerous_permission)
                for dangerous_permission in DANGEROUS_PERMISSIONS
            )
        ),
        "log": lambda entry: _(
            "{user.mention} (`{user}`) **updated** the permissions of {extra.mention} (`{extra}`) in {target.mention} (`{target}`) to include dangerous permissions {timestamp}."
        ).format(
            user=entry.user,
            extra=entry.extra,
            target=entry.target,
            timestamp=f"<t:{int(entry.created_at.timestamp())}:R>",
        )
        + "\n"
        + box(
            "\n".join(
                [
                    f"+ {dangerous_permission.replace('_', ' ').title()}"
                    for dangerous_permission in DANGEROUS_PERMISSIONS
                    if getattr(entry.after.allow, dangerous_permission)
                    and not getattr(entry.before.allow, dangerous_permission)
                ]
            ),
            lang="diff",
        ),
        "reason": lambda: _(
            "**Anti Nuke** - Updated @everyone or main roles to have dangerous permissions in a channel."
        ),
        "revert": lambda entry: entry.target.set_permissions(
            entry.extra,
            overwrite=discord.PermissionOverwrite.from_pair(entry.before.allow, entry.before.deny),
            reason=REVERT_AUDIT_LOG_REASON,
        ),
    },
    {
        "name": "Protect Onboarding",
        "emoji": Emojis.ONBOARDING.value,
        "description": "Prevent adding roles with dangerous permissions to Discord's onboarding.",
        "value": "protect_onboarding",
        "default_enabled": False,
        "check": lambda entry: (
            entry.action.value
            in (163, 164)  # 163: `onboarding_question_create`, 164: `onboarding_question_update`
            and "options" in entry.after.__dict__
            and any(
                getattr(role.permissions, dangerous_permission)
                for dangerous_permission in DANGEROUS_PERMISSIONS
                for option in entry.after.options
                for role_id in option["role_ids"]
                if (role := entry.guild.get_role(int(role_id))) is not None
                and all(role_id not in option["role_ids"] for option in entry.before.options)
            )
        ),
        "log": lambda entry: _(
            "{user.mention} (`{user}`) **added** the role{s} {roles} with dangerous permissions to Discord's onboarding {timestamp}."
        ).format(
            user=entry.user,
            roles=humanize_list(
                (
                    roles := [
                        f"{role.mention} (`{role.name}`)"
                        for option in entry.after.options
                        for role_id in option["role_ids"]
                        if (role := entry.guild.get_role(int(role_id))) is not None
                        and all(
                            role_id not in option["role_ids"] for option in entry.before.options
                        )
                        and any(
                            getattr(role.permissions, dangerous_permission)
                            for dangerous_permission in DANGEROUS_PERMISSIONS
                        )
                    ]
                )
            ),
            s="" if len(roles) == 1 else "s",
            timestamp=f"<t:{int(entry.created_at.timestamp())}:R>",
        )
        + "\n"
        + box(
            "\n".join(
                [
                    f"+ {dangerous_permission.replace('_', ' ').title()}"
                    for dangerous_permission in DANGEROUS_PERMISSIONS
                    if any(
                        getattr(role.permissions, dangerous_permission)
                        for option in entry.after.options
                        for role_id in option["role_ids"]
                        if (role := entry.guild.get_role(int(role_id))) is not None
                        and all(
                            role_id not in option["role_ids"] for option in entry.before.options
                        )
                    )
                ]
            ),
            lang="diff",
        ),
        "reason": lambda: _(
            "**Anti Nuke** - Added roles with dangerous permissions to Discord's onboarding."
        ),
        "revert": revert_onboarding,
    },
    {
        "name": "Strict Mode",
        "emoji": Emojis.ROLE.value,
        "description": "Prevent any role from getting dangerous permissions.",
        "value": "strict_mode",
        "default_enabled": False,
        "check": lambda entry: (
            entry.action == discord.AuditLogAction.role_update
            and any(
                getattr(entry.after.permissions, dangerous_permission)
                and not getattr(entry.before.permissions, dangerous_permission)
                for dangerous_permission in DANGEROUS_PERMISSIONS
            )
        ),
        "log": lambda entry: _(
            "{user.mention} (`{user}`) **updated** the permissions of {target.mention} (`{target}`) to include dangerous permissions {timestamp}."
        ).format(
            user=entry.user,
            target=entry.target,
            timestamp=f"<t:{int(entry.created_at.timestamp())}:R>",
        )
        + "\n"
        + box(
            "\n".join(
                [
                    f"+ {dangerous_permission.replace('_', ' ').title()}"
                    for dangerous_permission in DANGEROUS_PERMISSIONS
                    if getattr(entry.after.permissions, dangerous_permission)
                    and not getattr(entry.before.permissions, dangerous_permission)
                ]
            ),
            lang="diff",
        ),
        "reason": lambda: _("**Anti Nuke** - Updated a role to have dangerous permissions."),
        "revert": lambda entry: entry.target.edit(
            permissions=entry.before.permissions,
            reason=REVERT_AUDIT_LOG_REASON,
        ),
    },
]


ANTI_NUKE_FILTERS: typing.List[
    typing.Dict[
        typing.Literal[
            "name",
            "emoji",
            "description",
            "value",
            "default_enabled",
            "default_minute_limit",
            "default_hour_limit",
            "actions",
            "log",
            "reason",
        ],
        typing.Union[
            str,
            bool,
            int,
            typing.List[discord.AuditLogAction],
            typing.Callable[[discord.AuditLogEntry], str],
            typing.Callable[[], str],
        ],
    ]
] = [
    {
        "name": "Kick & Ban",
        "emoji": Emojis.KICK.value,
        "description": "Limit the number of kicks and bans in a given time frame.",
        "value": "kick_ban",
        "default_enabled": True,
        "default_minute_limit": 5,
        "default_hour_limit": 15,
        "actions": [discord.AuditLogAction.kick, discord.AuditLogAction.ban],
        "log": lambda entry: _(
            "{user.mention} (`{user}`) **{action}** `{target.name}` {timestamp}."
        ).format(
            user=entry.user,
            action=_("kicked") if entry.action == discord.AuditLogAction.kick else _("banned"),
            target=entry.target,
            timestamp=f"<t:{int(entry.created_at.timestamp())}:R>",
        ),
        "reason": lambda: _("**Anti Nuke** - Kicked/Banned too many members in a short time."),
    },
    {
        "name": "Role Creation",
        "emoji": Emojis.ROLE.value,
        "description": "Limit the number of roles created in a given time frame.",
        "value": "role_creation",
        "default_enabled": False,
        "default_minute_limit": 5,
        "default_hour_limit": 15,
        "actions": [discord.AuditLogAction.role_create],
        "log": lambda entry: _(
            "{user.mention} (`{user}`) **created** {target.mention} (`{target.name}`) {timestamp}."
        ).format(
            user=entry.user,
            target=entry.target,
            timestamp=f"<t:{int(entry.created_at.timestamp())}:R>",
        ),
        "reason": lambda: _("**Anti Nuke** - Created too many roles in a short time."),
    },
    {
        "name": "Role Deletion",
        "emoji": Emojis.ROLE.value,
        "description": "Limit the number of roles deleted in a given time frame.",
        "value": "role_deletion",
        "default_enabled": True,
        "default_minute_limit": 3,
        "default_hour_limit": 10,
        "actions": [discord.AuditLogAction.role_delete],
        "log": lambda entry: _(
            "{user.mention} (`{user}`) **deleted** `{target_name}` {timestamp}."
        ).format(
            user=entry.user,
            target_name=entry.before.name,
            timestamp=f"<t:{int(entry.created_at.timestamp())}:R>",
        ),
        "reason": lambda: _("**Anti Nuke** - Deleted too many roles in a short time."),
    },
    {
        "name": "Channel Creation",
        "emoji": Emojis.CHANNEL.value,
        "description": "Limit the number of channels created in a given time frame.",
        "value": "channel_creation",
        "default_enabled": False,
        "default_minute_limit": 4,
        "default_hour_limit": 12,
        "actions": [discord.AuditLogAction.channel_create],
        "log": lambda entry: _(
            "{user.mention} (`{user}`) **created** {target.mention} (`{target.name}`) {timestamp}."
        ).format(
            user=entry.user,
            target=entry.target,
            timestamp=f"<t:{int(entry.created_at.timestamp())}:R>",
        ),
        "reason": lambda: _("**Anti Nuke** - Created too many channels in a short time."),
    },
    {
        "name": "Channel Deletion",
        "emoji": Emojis.CHANNEL.value,
        "description": "Limit the number of channels deleted in a given time frame.",
        "value": "channel_deletion",
        "default_enabled": True,
        "default_minute_limit": 3,
        "default_hour_limit": 8,
        "actions": [discord.AuditLogAction.channel_delete],
        "log": lambda entry: _(
            "{user.mention} (`{user}`) **deleted** `{target_name}` {timestamp}."
        ).format(
            user=entry.user,
            target_name=entry.before.name,
            timestamp=f"<t:{int(entry.created_at.timestamp())}:R>",
        ),
        "reason": lambda: _("**Anti Nuke** - Deleted too many channels in a short time."),
    },
    {
        "name": "Webhook Creation",
        "emoji": Emojis.WEBHOOK.value,
        "description": "Limit the number of webhooks created in a given time frame.",
        "value": "webhook_creation",
        "default_enabled": False,
        "default_minute_limit": 3,
        "default_hour_limit": 10,
        "actions": [discord.AuditLogAction.webhook_create],
        "log": lambda entry: _(
            "{user.mention} (`{user}`) **created** {target.mention} (`{target.name}`) {timestamp}."
        ).format(
            user=entry.user,
            target=entry.target,
            timestamp=f"<t:{int(entry.created_at.timestamp())}:R>",
        ),
        "reason": lambda: _("**Anti Nuke** - Created too many webhooks in a short time."),
    },
    {
        "name": "Webhook Deletion",
        "emoji": Emojis.WEBHOOK.value,
        "description": "Limit the number of webhooks deleted in a given time frame.",
        "value": "webhook_deletion",
        "default_enabled": False,
        "default_minute_limit": 3,
        "default_hour_limit": 8,
        "actions": [discord.AuditLogAction.webhook_delete],
        "log": lambda entry: _(
            "{user.mention} (`{user}`) **deleted** `{target_id}` {timestamp}."
        ).format(
            user=entry.user,
            target_id=entry.target.id,
            timestamp=f"<t:{int(entry.created_at.timestamp())}:R>",
        ),
        "reason": lambda: _("**Anti Nuke** - Deleted too many webhooks in a short time."),
    },
    {
        "name": "Emoji Creation",
        "emoji": Emojis.EMOJI.value,
        "description": "Limit the number of emojis created in a given time frame.",
        "value": "emoji_creation",
        "default_enabled": False,
        "default_minute_limit": 5,
        "default_hour_limit": 15,
        "actions": [discord.AuditLogAction.emoji_create],
        "log": lambda entry: _(
            "{user.mention} (`{user}`) **created** {target} (`{target.name}`) {timestamp}."
        ).format(
            user=entry.user,
            target=entry.target,
            timestamp=f"<t:{int(entry.created_at.timestamp())}:R>",
        ),
        "reason": lambda: _("**Anti Nuke** - Created too many emojis in a short time."),
    },
    {
        "name": "Emoji Deletion",
        "emoji": Emojis.EMOJI.value,
        "description": "Limit the number of emojis deleted in a given time frame.",
        "value": "emoji_deletion",
        "default_enabled": True,
        "default_minute_limit": 3,
        "default_hour_limit": 10,
        "actions": [discord.AuditLogAction.emoji_delete],
        "log": lambda entry: _(
            "{user.mention} (`{user}`) **deleted** `{target_name}` {timestamp}."
        ).format(
            user=entry.user,
            target_name=entry.before.name,
            timestamp=f"<t:{int(entry.created_at.timestamp())}:R>",
        ),
        "reason": lambda: _("**Anti Nuke** - Deleted too many emojis in a short time."),
    },
]


class AntiNukeModule(Module):
    name = "Anti Nuke"
    emoji = Emojis.ANTI_NUKE.value
    description = "Protect your server from malicious actions by members or bots."
    default_config = {
        "enabled": False,
        "quarantine": True,
        "options": {option["value"]: option["default_enabled"] for option in ANTI_NUKE_OPTIONS},
        "revert_option_actions": True,
        "filters": {
            filter["value"]: {
                "enabled": filter["default_enabled"],
                "minute_limit": filter["default_minute_limit"],
                "hour_limit": filter["default_hour_limit"],
            }
            for filter in ANTI_NUKE_FILTERS
        },
        "timeout_mute_duration": "3h",
    }
    configurable_by_trusted_admins = False

    def __init__(self, cog: commands.Cog) -> None:
        super().__init__(cog)
        self.actions_cache: typing.Dict[
            discord.Guild,
            typing.Dict[
                discord.Member, typing.Dict[str, typing.List[typing.Tuple[datetime.datetime, str]]]
            ],
        ] = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))

    async def load(self) -> None:
        self.cog.bot.add_listener(self.on_audit_log_entry_create)

    async def unload(self) -> None:
        self.cog.bot.remove_listener(self.on_audit_log_entry_create)

    async def get_status(
        self, guild: discord.Guild
    ) -> typing.Tuple[typing.Literal["✅", "⚠️", "❎", "❌"], str, str]:
        config = await self.config_value(guild)()
        if not config["enabled"]:
            return "❌", _("Disabled"), _("Anti Nuke is currently disabled.")
        if not any(config["options"].values()) and all(
            not filter["enabled"] for filter in config["filters"].values()
        ):
            return (
                "❎",
                _("No Enabled Options/Filters"),
                _("There are no Anti Nuke option/filter enabled."),
            )
        if not guild.me.guild_permissions.view_audit_log:
            return (
                "⚠️",
                _("Missing Permission"),
                _("I need the `View Audit Log` permission to function properly."),
            )
        if config["quarantine"] and not guild.me.guild_permissions.manage_roles:
            return (
                "⚠️",
                _("Missing Permission"),
                _("I need the `Manage Roles` permission to quarantine members."),
            )
        return "✅", _("Enabled"), _("Anti Nuke is enabled and configured correctly.")

    async def get_settings(
        self, guild: discord.Guild, view: discord.ui.View
    ) -> typing.Tuple[str, str, typing.List[typing.Dict], typing.List[discord.ui.Item]]:
        title = _("Security — {emoji} {name} {status}").format(
            emoji=self.emoji, name=self.name, status=(await self.get_status(guild))[0]
        )
        description = _(
            "This module allows you to protect your server from malicious actions by members or bots.\n"
        )
        status = await self.get_status(guild)
        if status[0] == "⚠️":
            description += f"{status[0]} **{status[1]}**: {status[2]}\n"
        config = await self.config_value(guild)()
        for option in ANTI_NUKE_OPTIONS:
            description += f"\n{'✅' if config['options'][option['value']] else '❌'} {option['emoji']} {option['name']}"
        fields = []
        for filter in ANTI_NUKE_FILTERS:
            filter_config = config["filters"][filter["value"]]
            fields.append(
                dict(
                    name=f"{filter['emoji']} {filter['name']}",
                    value=_(
                        "{description}\n**Enabled:** {enabled}\n**Minute Limit:** {minute_limit}\n**Hour Limit:** {hour_limit}"
                    ).format(
                        description=filter["description"],
                        enabled=("✅" if filter_config["enabled"] else "❌"),
                        minute_limit=filter_config["minute_limit"],
                        hour_limit=filter_config["hour_limit"],
                    ),
                    inline=True,
                )
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
        revert_option_actions_button: discord.ui.Button = discord.ui.Button(
            label=_("Revert Option Actions"),
            style=discord.ButtonStyle.success
            if config["revert_option_actions"]
            else discord.ButtonStyle.danger,
            emoji="🔄",
        )

        async def revert_option_actions_callback(interaction: discord.Interaction) -> None:
            await interaction.response.defer()
            config["revert_option_actions"] = not config["revert_option_actions"]
            await self.config_value(guild).revert_option_actions.set(
                config["revert_option_actions"]
            )
            await interaction.followup.send(
                _("Revert option actions is now {status}.").format(
                    status="enabled" if config["revert_option_actions"] else "disabled"
                ),
                ephemeral=True,
            )
            await view._message.edit(embed=await view.get_embed(), view=view)

        revert_option_actions_button.callback = revert_option_actions_callback
        components.append(revert_option_actions_button)

        options_select: discord.ui.Select = discord.ui.Select(
            placeholder=_("Select Anti Nuke Options"),
            options=[
                discord.SelectOption(
                    emoji=option["emoji"],
                    label=option["name"],
                    value=option["value"],
                    description=option["description"],
                    default=config["options"][option["value"]],
                )
                for option in ANTI_NUKE_OPTIONS
            ],
            min_values=0,
            max_values=len(ANTI_NUKE_OPTIONS),
        )

        async def options_select_callback(interaction: discord.Interaction) -> None:
            await interaction.response.defer()
            for option in ANTI_NUKE_OPTIONS:
                config["options"][option["value"]] = option["value"] in options_select.values
            await self.config_value(guild).options.set(config["options"])
            await view._message.edit(embed=await view.get_embed(), view=view)

        options_select.callback = options_select_callback
        components.append(options_select)

        configure_filter_select: discord.ui.Select = discord.ui.Select(
            placeholder=_("Configure Anti Nuke Filters"),
            options=[
                discord.SelectOption(
                    emoji=filter["emoji"], label=filter["name"], value=filter["value"]
                )
                for filter in ANTI_NUKE_FILTERS
            ],
        )

        async def configure_filter_select_callback(interaction: discord.Interaction) -> None:
            filter = next(
                (
                    filter
                    for filter in ANTI_NUKE_FILTERS
                    if filter["value"] == configure_filter_select.values[0]
                )
            )
            await interaction.response.send_modal(
                ConfigureFilterModal(self, guild, view, filter, config["filters"][filter["value"]])
            )

        configure_filter_select.callback = configure_filter_select_callback
        components.append(configure_filter_select)

        return title, description, fields, components

    async def on_audit_log_entry_create(self, entry: discord.AuditLogEntry) -> None:
        guild = entry.guild
        config = await self.config_value(guild)()
        if not config["enabled"]:
            return
        if await self.cog.is_trusted_admin_or_higher(entry.user):
            return
        for option in ANTI_NUKE_OPTIONS:
            if option["check"](entry):
                option_filter, logs = option, [option["log"](entry)]
                if config["revert_option_actions"]:
                    try:
                        await option["revert"](entry)
                    except discord.Forbidden:
                        logs.append(
                            _(
                                "I **failed** to revert the action due to missing permissions."
                            ).format(user=entry.user)
                        )
                    except discord.HTTPException as e:
                        logs.append(
                            _(
                                "I **failed** to revert the action due to an error: `{error}`."
                            ).format(user=entry.user, error=str(e).replace("\n", " "))
                        )
                    else:
                        logs.append(
                            _("I **successfully** reverted the action.").format(user=entry.user)
                        )
                break
        else:
            for filter in ANTI_NUKE_FILTERS:
                if entry.action in filter["actions"]:
                    filter_config = config["filters"][filter["value"]]
                    if not filter_config["enabled"]:
                        continue
                    if await self.cog.is_whitelisted(
                        entry.user, f"anti_nuke_filter_{filter['value']}"
                    ):
                        continue
                    if filter["value"] == "channel_creation" and await self.cog.is_whitelisted(
                        entry.target.category, "anti_nuke_filter_channel_creation"
                    ):
                        continue
                    elif filter["value"] == "channel_deletion" and await self.cog.is_whitelisted(
                        discord.Object(id=entry.target.id, type=discord.abc.GuildChannel),
                        "anti_nuke_filter_channel_deletion",
                    ):
                        continue
                    elif filter["value"] == "webhook_creation" and await self.cog.is_whitelisted(
                        entry.target.channel, "anti_nuke_filter_webhook_creation"
                    ):
                        continue
                    elif filter["value"] == "webhook_deletion" and await self.cog.is_whitelisted(
                        discord.Object(id=entry.target.id, type=discord.Webhook),
                        "anti_nuke_filter_webhook_deletion",
                    ):
                        continue
                    minute_limit, hour_limit = (
                        filter_config["minute_limit"],
                        filter_config["hour_limit"],
                    )
                    member_actions = self.actions_cache[guild][entry.user]
                    current_time = entry.created_at
                    member_actions[filter["value"]].append((current_time, filter["log"](entry)))
                    member_actions[filter["value"]] = [
                        action
                        for action in member_actions[filter["value"]]
                        if action[0] >= current_time - datetime.timedelta(hours=1)
                    ]
                    if (
                        len(
                            [
                                action
                                for action in member_actions[filter["value"]]
                                if action[0] >= current_time - datetime.timedelta(minutes=1)
                            ]
                        )
                        >= minute_limit
                        or len(member_actions[filter["value"]]) >= hour_limit
                    ):
                        option_filter, logs = filter, [
                            action[1] for action in member_actions[filter["value"]]
                        ]
                        del member_actions[filter["value"]]
                        break
            else:
                return
        reason = option_filter["reason"]()
        if config["quarantine"]:
            await self.cog.quarantine_member(
                member=entry.user,
                reason=reason,
                logs=logs,
            )
        else:
            await self.cog.send_modlog(
                action="notify",
                member=entry.user,
                reason=reason,
                logs=logs,
            )
        if "member_reason" in option_filter and entry.target != entry.user:
            member_reason = option_filter["member_reason"]()
            if config["quarantine"]:
                await self.cog.quarantine_member(
                    member=entry.target,
                    reason=member_reason,
                    logs=logs,
                )
            else:
                await self.cog.send_modlog(
                    action="notify",
                    member=entry.target,
                    reason=member_reason,
                    logs=logs,
                )


class ConfigureFilterModal(discord.ui.Modal):
    def __init__(
        self,
        module: AntiNukeModule,
        guild: discord.Guild,
        view: discord.ui.View,
        filter,
        filter_config,
    ) -> None:
        self.module: AntiNukeModule = module
        self.guild: discord.Guild = guild
        self.view: discord.ui.View = view
        self.filter = filter
        self.filter_config = filter_config
        super().__init__(
            title=_("Anti Nuke - {filter}").format(
                filter=f"{self.filter['emoji']} {self.filter['name']}"
            )
        )
        self.enabled: discord.ui.TextInput = discord.ui.TextInput(
            label=_("Enabled:"),
            style=discord.TextStyle.short,
            default=str(filter_config["enabled"]),
            required=True,
        )
        self.add_item(self.enabled)
        self.minute_limit: discord.ui.TextInput = discord.ui.TextInput(
            label=_("Minute Limit:"),
            style=discord.TextStyle.short,
            default=str(filter_config["minute_limit"]),
            required=True,
        )
        self.add_item(self.minute_limit)
        self.hour_limit: discord.ui.TextInput = discord.ui.TextInput(
            label=_("Hour Limit:"),
            style=discord.TextStyle.short,
            default=str(filter_config["hour_limit"]),
            required=True,
        )
        self.add_item(self.hour_limit)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        enabled = self.enabled.value.lower() in ("true", "yes", "1")
        try:
            minute_limit = int(self.minute_limit.value)
            hour_limit = int(self.hour_limit.value)
        except ValueError as e:
            await interaction.followup.send(
                _("Invalid limit value: {error}").format(error=str(e)),
                ephemeral=True,
            )
            return
        self.filter_config["enabled"] = enabled
        self.filter_config["minute_limit"] = minute_limit
        self.filter_config["hour_limit"] = hour_limit
        await self.module.config_value(self.guild).filters.set_raw(
            self.filter["value"], value=self.filter_config
        )
        await self.view._message.edit(embed=await self.view.get_embed(), view=self.view)

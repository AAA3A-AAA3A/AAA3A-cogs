from AAA3A_utils import CogsUtils  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import datetime
import re

from redbot.core.utils.chat_formatting import humanize_list

from ..constants import POSSIBLE_ACTIONS, Emojis
from ..views import DurationConverter, ToggleModuleButton
from .module import Module

_: Translator = Translator("Security", __file__)


def sum_dicts(*dicts: typing.Dict) -> typing.Dict:
    dict0 = dicts[0]
    for d in dicts[1:]:
        dict0.update(d)
    return dict0


def check_regex_argument(argument: str) -> str:
    argument = re.escape(argument)
    try:
        re.compile(argument)
    except re.error as e:
        return ValueError(_("Invalid regex pattern: {error}").format(error=str(e)))
    return argument


JOIN_GATE_OPTIONS: typing.List[
    typing.Dict[
        typing.Literal["name", "emoji", "description", "action", "param", "value", "check"],
        typing.Union[str, typing.Tuple[str, typing.Any], typing.Callable],
    ]
] = [
    {
        "name": "No Avatar",
        "emoji": "🖼️",
        "description": "Target accounts without an avatar.",
        "action": "kick",
        "value": "no_avatar",
        "check": lambda member: not member.bot and member.avatar is None,
    },
    {
        "name": "Advertising Name",
        "emoji": Emojis.ADVERTISING.value,
        "description": "Target accounts with invite links in their global name/username.",
        "action": "kick",
        "value": "advertising_name",
        "check": lambda member: not member.bot
        and re.search(
            r"(https?://)?(discord\.gg|discordapp\.com/invite)/[a-zA-Z0-9]+",
            member.name,
            re.IGNORECASE,
        )
        is not None,
    },
    {
        "name": "Account Age",
        "emoji": "⏳",
        "description": "Target accounts younger than a certain age.",
        "action": "kick",
        "param": ("minimum_days", int, 7),
        "value": "account_age",
        "check": lambda member, minimum_days: (datetime.datetime.now(tz=datetime.timezone.utc) - member.created_at).days
        < minimum_days,
    },
    {
        "name": "Username",
        "emoji": "🔤",
        "description": "Target accounts with usernames that match a certain pattern.",
        "action": "ban",
        "param": ("pattern", check_regex_argument, None),
        "value": "username",
        "check": lambda member, pattern: pattern is not None
        and (
            re.search(pattern, member.global_name) is not None
            or re.search(pattern, member.name) is not None
        ),
    },
    {
        "name": "Bot Additions",
        "emoji": "🤖",
        "description": "Target bots added by unauthorized members.",
        "action": "kick",
        "value": "bot_additions",
    },
    {
        "name": "Unverified Bot Additions",
        "emoji": "🚫",
        "description": "Target Discord unverified bots added by any.",
        "action": "kick",
        "value": "unverified_bot_additions",
        "check": lambda member: member.bot and not member.public_flags.verified_bot,
    },
]


class JoinGateModule(Module):
    name = "Join Gate"
    emoji = Emojis.JOIN_GATE.value
    description = "Manage join gate roles in the server."
    default_config = {
        "enabled": False,
        "options": {
            option["value"]: sum_dicts(
                {
                    "enabled": False,
                    "action": option["action"],
                },
                ({option["param"][0]: option["param"][2]} if "param" in option else {}),
            )
            for option in JOIN_GATE_OPTIONS
        },
        "timeout_mute_duration": "3h",
    }

    async def load(self) -> None:
        self.cog.bot.add_listener(self.on_member_join)

    async def unload(self) -> None:
        self.cog.bot.remove_listener(self.on_member_join)

    async def get_status(
        self, guild: discord.Guild, check_enabled: bool = True
    ) -> typing.Tuple[typing.Literal["✅", "⚠️", "❎", "❌"], str, str]:
        config = await self.config_value(guild)()
        if not config["enabled"] and check_enabled:
            return "❌", _("Disabled"), _("Join Gate is currently disabled.")
        if all(not option["enabled"] for option in config["options"].values()):
            return "❎", _("No Enabled Options"), _("There are no Join Gate option enabled.")
        missing_permissions = []
        for action, permission in {
            "timeout": "moderate_members",
            "kick": "kick_members",
            "ban": "ban_members",
        }.items():
            if any(
                option["enabled"] and option["action"] == action
                for option in config["options"].values()
            ) and not getattr(guild.me.guild_permissions, permission):
                missing_permissions.append(permission)
        if (
            config["options"]["bot_additions"]["enabled"]
            and not guild.me.guild_permissions.view_audit_log
        ):
            missing_permissions.append("view_audit_log")
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
        return "✅", _("Enabled"), _("Join Gate is enabled and configured correctly.")

    async def get_settings(
        self, guild: discord.Guild, view: discord.ui.View
    ) -> typing.Tuple[str, str, typing.List[typing.Dict], typing.List[discord.ui.Item]]:
        title = _("Security — {emoji} {name} {status}").format(
            emoji=self.emoji, name=self.name, status=(await self.get_status(guild))[0]
        )
        description = _(
            "This module allows you to manage Join Gate options to protect your server from unwanted members/bots."
        )
        status = await self.get_status(guild)
        if status[0] == "⚠️":
            description += f"\n{status[0]} **{status[1]}**: {status[2]}\n"
        config = await self.config_value(guild)()
        fields = []
        for option in JOIN_GATE_OPTIONS:
            if "param" in option:
                value = config["options"][option["value"]].get(
                    option["param"][0], option["param"][2]
                )
                backstick = option["param"][0] == "pattern" and value is not None
            fields.append(
                dict(
                    name=f"{option['emoji']} {option['name']}",
                    value=_("{description}\n**Enabled:** {enabled}\n**Action:** {action}").format(
                        description=option["description"],
                        enabled=("✅" if config["options"][option["value"]]["enabled"] else "❌"),
                        action=config["options"][option["value"]]["action"].title(),
                    )
                    + (
                        f"\n**{option['param'][0].replace('_', ' ').title()}**: {'`' if backstick else ''}{value}{'`' if backstick else ''}"
                        if "param" in option
                        else ""
                    ),
                    inline=True,
                )
            )

        components = [ToggleModuleButton(self, guild, view, config["enabled"])]
        configure_option_select = discord.ui.Select(
            placeholder=_("Configure Option"),
            options=[
                discord.SelectOption(
                    emoji=option["emoji"], label=option["name"], value=option["value"]
                )
                for option in JOIN_GATE_OPTIONS
            ],
        )

        async def configure_option_select_callback(interaction: discord.Interaction) -> None:
            option = next(
                (
                    opt
                    for opt in JOIN_GATE_OPTIONS
                    if opt["value"] == configure_option_select.values[0]
                )
            )
            await interaction.response.send_modal(
                ConfigureOptionModal(self, guild, view, option, config["options"][option["value"]])
            )

        configure_option_select.callback = configure_option_select_callback
        components.append(configure_option_select)

        timeout_mute_duration_button: discord.ui.Button = discord.ui.Button(
            label=_("Set Timeout/Mute Duration"),
            style=discord.ButtonStyle.secondary,
        )

        async def timeout_mute_duration_callback(interaction: discord.Interaction) -> None:
            modal: discord.ui.Modal = discord.ui.Modal(
                title=_("Timeout/Mute Duration"),
                timeout=120,
            )
            duration_input: discord.ui.TextInput = discord.ui.TextInput(
                label=_("Duration:"),
                placeholder=_("Enter the duration (e.g. 3h)..."),
                default=config["timeout_mute_duration"],
                required=True,
            )
            modal.add_item(duration_input)
            duration, argument = None, None

            async def on_submit(modal_interaction: discord.Interaction) -> None:
                await modal_interaction.response.defer()
                nonlocal duration, argument
                try:
                    duration = await DurationConverter.convert(None, duration_input.value)
                    argument = duration_input.value
                except commands.BadArgument as e:
                    await modal_interaction.followup.send(
                        _("Invalid duration: {error}").format(error=str(e)), ephemeral=True
                    )

            modal.on_submit = on_submit
            await interaction.response.send_modal(modal)
            if await modal.wait() or duration is None:
                return
            config["timeout_mute_duration"] = argument
            await self.config_value(guild).timeout_mute_duration.set(
                config["timeout_mute_duration"]
            )
            await interaction.followup.send(
                _("Timeout/Mute duration set to {duration}.").format(
                    duration=CogsUtils.get_interval_string(duration)
                ),
                ephemeral=True,
            )

        timeout_mute_duration_button.callback = timeout_mute_duration_callback
        components.append(timeout_mute_duration_button)

        return title, description, fields, components

    async def on_member_join(self, member: discord.Member) -> None:
        config = await self.config_value(member.guild)()
        if not config["enabled"]:
            return
        triggered = []
        for option in JOIN_GATE_OPTIONS:
            option_config = config["options"][option["value"]]
            if not option_config["enabled"]:
                continue
            if option["value"] != "bot_additions":
                if "param" not in option:
                    if not option["check"](member):
                        continue
                else:
                    if not option["check"](member, option_config[option["param"][0]]):
                        continue
            elif not member.bot or not member.guild.me.guild_permissions.view_audit_log:
                continue
            else:
                responsible = [
                    audit_log
                    for audit_log in await member.guild.audit_logs(
                        limit=1, action=discord.AuditLogAction.bot_add
                    )
                    if audit_log.target.id == member.id
                ][0].user
                if await self.cog.is_trusted_admin_or_higher(responsible):
                    continue
            triggered.append((option, option_config))
        if triggered:
            option, option_config = sorted(
                triggered,
                key=lambda opt: next((i for i, possible_action in enumerate(POSSIBLE_ACTIONS) if possible_action["value"] == opt[1]["action"])),
                reverse=True,
            )[0]
            action = option_config["action"]
            if action in ("timeout", "mute"):
                duration = await DurationConverter.convert(None, config["timeout_mute_duration"])
            else:
                duration = None
            reason = _("**Join Gate** - Triggered by {option}.").format(option=option["name"]) + (
                _("\n- Account Age: {account_age}\n- Minimum Age: {minimum_days} days").format(
                    account_age=CogsUtils.get_interval_string(
                        datetime.timedelta(
                            days=(
                                datetime.datetime.now(tz=datetime.timezone.utc) - member.created_at
                            ).days
                        )
                    ),
                    minimum_days=option_config["minimum_days"],
                )
                if option["value"] == "account_age"
                else ""
            )
            logs = [_("{member.mention} ({member}) joined the server.").format(member=member)]
            if action != "quarantine":
                await self.cog.send_modlog(
                    action=action,
                    member=member,
                    reason=reason,
                    logs=logs,
                    duration=duration,
                )
            audit_log_reason = f"Security's Join Gate: {option['name']}."
            if action == "timeout" and member.guild.me.guild_permissions.moderate_members:
                await member.timeout(duration, reason=audit_log_reason)
            elif (
                action == "mute"
                and member.guild.me.guild_permissions.manage_roles
                and (Mutes := self.cog.bot.get_cog("Mutes")) is not None
                and hasattr(Mutes, "mute_user")
            ):
                await Mutes.mute_user(
                    guild=member.guild,
                    author=member.guild.me,
                    user=member,
                    until=datetime.datetime.now(tz=datetime.timezone.utc) + duration,
                    reason=audit_log_reason,
                )
            elif action == "kick" and member.guild.me.guild_permissions.kick_members:
                await member.kick(reason=audit_log_reason)
            elif action == "ban" and member.guild.me.guild_permissions.ban_members:
                await member.ban(reason=audit_log_reason)
            elif action == "quarantine" and member.guild.me.guild_permissions.manage_roles:
                await self.cog.quarantine_member(
                    member=member,
                    reason=reason,
                    logs=logs,
                )


class ConfigureOptionModal(discord.ui.Modal):
    def __init__(
        self,
        module: JoinGateModule,
        guild: discord.Guild,
        view: discord.ui.View,
        option,
        option_config,
    ) -> None:
        self.module: JoinGateModule = module
        self.guild: discord.Guild = guild
        self.view: discord.ui.View = view
        self.option = option
        self.option_config = option_config
        super().__init__(
            title=_("Join Gate - {option}").format(
                option=f"{self.option['emoji']} {self.option['name']}"
            )
        )
        self.enabled: discord.ui.TextInput = discord.ui.TextInput(
            label=_("Enabled:"),
            style=discord.TextStyle.short,
            default=str(option_config["enabled"]),
            required=True,
        )
        self.add_item(self.enabled)
        self.action: discord.ui.TextInput = discord.ui.TextInput(
            label=_("Action ({actions}):").format(
                actions="/".join([action["value"] for action in POSSIBLE_ACTIONS])
            ),
            style=discord.TextStyle.short,
            default=option_config["action"],
            required=True,
        )
        self.add_item(self.action)
        if "param" in self.option:
            self.param: discord.ui.TextInput = discord.ui.TextInput(
                label=self.option["param"][0].replace("_", " ").title(),
                style=discord.TextStyle.short,
                default=str(default)
                if (default := option_config.get(self.option["param"][0], self.option["param"][2]))
                is not None
                else None,
                required=True,
            )
            self.add_item(self.param)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        enabled = self.enabled.value.lower() in ("true", "yes", "1")
        if (action := self.action.value.lower()) not in [
            action["value"] for action in POSSIBLE_ACTIONS
        ]:
            await interaction.followup.send(
                _("Invalid action: `{action}`. Possible actions are: {actions}").format(
                    action=action,
                    actions="/".join([action["value"] for action in POSSIBLE_ACTIONS]),
                ),
                ephemeral=True,
            )
            return
        if "param" in self.option:
            try:
                param_value = self.option["param"][1](self.param.value)
            except ValueError as e:
                await interaction.followup.send(
                    _("Invalid parameter value: {error}.").format(error=str(e)),
                    ephemeral=True,
                )
                return
        else:
            param_value = None
        self.option_config["enabled"] = enabled
        self.option_config["action"] = action
        if param_value is not None:
            self.option_config[self.option["param"][0]] = param_value
        await self.module.config_value(self.guild).options.set_raw(
            self.option["value"], value=self.option_config
        )
        await self.view._message.edit(embed=await self.view.get_embed(), view=self.view)

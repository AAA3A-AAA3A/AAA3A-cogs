import asyncio
import datetime
import typing
from collections import defaultdict
from dataclasses import dataclass
from io import BytesIO
from itertools import combinations

import discord
import imagehash
from PIL import Image

from AAA3A_utils import CogsUtils
from redbot.core import commands
from redbot.core.i18n import Translator
from redbot.core.utils.chat_formatting import humanize_list
from security.constants import POSSIBLE_ACTIONS, Colors, Emojis
from security.modules.module import Module
from security.utils import get_correct_timeout_duration, similarity_ratio_check
from security.views import DurationConverter, SettingsView, ToggleModuleButton

_: Translator = Translator("Security", __file__)


@dataclass
class Join:
    member: discord.Member
    avatar_hash: imagehash.ImageHash | None
    timestamp: datetime.datetime
    action_taken: bool = False

    def __hash__(self) -> int:
        return hash(self.member.id)


FLAGS: dict[
    str, str | typing.Callable[[Join], bool] | typing.Callable[[Join, Join], bool] | bool
] = {
    "name_similarity": {
        "emoji": "📝",
        "name": _("Name Similarity"),
        "check": lambda left, right: similarity_ratio_check(
            left.member.display_name,
            right.member.display_name,
            0.8,
        ),
        "pairwise": True,
    },
    "no_avatar": {
        "emoji": "🚫",
        "name": _("No Avatar"),
        "check": lambda join: join.member.avatar is None,
        "pairwise": False,
    },
    "avatar_similarity": {
        "emoji": "🖼️",
        "name": _("Avatar Similarity"),
        "check": lambda left, right: (
            left.avatar_hash is not None
            and right.avatar_hash is not None
            and (right.avatar_hash - left.avatar_hash) < 8
        ),
        "pairwise": True,
    },
    "account_age": {
        "emoji": "🕐",
        "name": _("Account Age"),
        "check": lambda join: (
            (
                datetime.datetime.now(tz=datetime.timezone.utc) - join.member.created_at
            ).total_seconds()
            < 60 * 60 * 24 * 7
        ),  # less than 7 days old
        "pairwise": False,
    },
    "account_age_similarity": {
        "emoji": "📅",
        "name": _("Account Age Similarity"),
        "check": lambda left, right: (
            abs((right.member.created_at - left.member.created_at).total_seconds())
            < 60 * 60 * 24 * 7
        ),  # less than 7 days difference
        "pairwise": True,
    },
}


class AntiRaidModule(Module):
    name = "Anti Raid"
    emoji = Emojis.ANTI_RAID.value
    description = "Protect your server from raids by tracking new member activity."
    default_config = {
        "enabled": False,
        "minimum_trigger": 10,
        "join_window": "3h",
        "trigger_duration": "30m",
        "flags": dict.fromkeys(FLAGS.keys(), True),
        "action": "ban",
        "duration": "1h",
    }

    def __init__(self, cog: commands.Cog) -> None:
        super().__init__(cog)
        self.locks: dict[discord.Guild, asyncio.Lock] = defaultdict(asyncio.Lock)
        self.last_joins: dict[discord.Guild, list[Join]] = defaultdict(list)
        self.triggered: dict[discord.Guild, datetime.datetime] = {}

    async def load(self) -> None:
        self.cog.bot.add_listener(self.on_member_join)

    async def unload(self) -> None:
        self.cog.bot.remove_listener(self.on_member_join)

    async def get_status(
        self,
        guild: discord.Guild,
        check_enabled: bool = True,
    ) -> tuple[str, str, str]:
        config = await self.config_value(guild)()
        if not config["enabled"] and check_enabled:
            return "❌", _("Disabled"), _("Anti Raid is currently disabled.")
        missing_permissions = []
        action = next(a for a in POSSIBLE_ACTIONS if a["value"] == config["action"])
        if not getattr(guild.me.guild_permissions, action["permission"]):
            missing_permissions.append(action["permission"])
        if missing_permissions:
            return (
                "⚠️",
                _("Missing Permissions"),
                _("I need the {permissions} permission{s} to function properly.").format(
                    permissions=humanize_list(
                        [f"`{permission}`" for permission in missing_permissions],
                    ),
                    s="" if len(missing_permissions) == 1 else "s",
                ),
            )
        return "✅", _("Enabled"), _("Anti Raid is enabled and configured correctly.")

    async def get_settings(
        self,
        guild: discord.Guild,
        view: SettingsView,
    ) -> tuple[str, str, list[dict], list[discord.ui.Item]]:
        title = _("Security — {emoji} {name} {status}").format(
            emoji=self.emoji,
            name=self.name,
            status=(await self.get_status(guild))[0],
        )
        description = _(
            "A sudden influx of new members can be a sign of a raid. This module tracks new member activity and takes action if it detects a raid.\n"
            "It will trigger if more than a certain number of members who trigger flags within a specified time frame, and will automatically ban them to protect your server, along with alerting you.",
        )
        status = await self.get_status(guild)
        if status[0] == "⚠️":
            description += f"\n{status[0]} **{status[1]}**: {status[2]}"

        config = await self.config_value(guild)()
        action = next(a for a in POSSIBLE_ACTIONS if a["value"] == config["action"])
        fields = [
            {
                "name": _("Minimum Trigger:"),
                "value": f"`{config['minimum_trigger']}`",
                "inline": True,
            },
            {
                "name": _("Join Window:"),
                "value": f"`{config['join_window']}`",
                "inline": True,
            },
            {
                "name": _("Trigger Duration:"),
                "value": f"`{config['trigger_duration']}`",
                "inline": True,
            },
            {
                "name": _("Flags (only accounts that meet these criteria will be affected):"),
                "value": "\n".join(
                    [
                        f"- {flag['emoji']} {flag['name']}: {'✅' if config['flags'][flag_value] else '❌'}"
                        for flag_value, flag in FLAGS.items()
                    ]
                ),
                "inline": False,
            },
            {
                "name": _("Action:"),
                "value": f"{action['emoji']} {action['name']}",
                "inline": True,
            },
            {
                "name": _("Duration:"),
                "value": f"`{config['duration']}`",
                "inline": True,
            },
        ]

        components = [ToggleModuleButton(self, guild, view, config["enabled"])]

        setting_button: discord.ui.Button = discord.ui.Button(
            label=_("Configure Settings"),
            style=discord.ButtonStyle.secondary,
        )

        async def setting_button_callback(interaction: discord.Interaction) -> None:
            await interaction.response.send_modal(
                ConfigureSettingsModal(self, guild, view, config),
            )

        setting_button.callback = setting_button_callback
        components.append(setting_button)

        flag_select: discord.ui.Select = discord.ui.Select(
            placeholder=_("Configure Flags"),
            options=[
                discord.SelectOption(
                    emoji=flag["emoji"],
                    label=flag["name"],
                    value=flag_value,
                    default=config["flags"][flag_value],
                )
                for flag_value, flag in FLAGS.items()
            ],
            min_values=1,
            max_values=len(config["flags"]),
        )

        async def flag_select_callback(interaction: discord.Interaction) -> None:
            await interaction.response.defer()
            selected_flags = flag_select.values
            for flag_name in config["flags"]:
                config["flags"][flag_name] = flag_name in selected_flags
            await self.config_value(guild).flags.set(config["flags"])
            await view.edit_message()

        flag_select.callback = flag_select_callback
        components.append(flag_select)

        action_select: discord.ui.Select = discord.ui.Select(
            placeholder=_("Select action"),
            options=[
                discord.SelectOption(
                    emoji=a["emoji"],
                    label=a["name"],
                    value=a["value"],
                    default=a["value"] == config["action"],
                )
                for a in POSSIBLE_ACTIONS
            ],
        )

        async def action_select_callback(interaction: discord.Interaction) -> None:
            action = next(a for a in POSSIBLE_ACTIONS if a["value"] == action_select.values[0])
            if not getattr(guild.me.guild_permissions, action["permission"]):
                await interaction.response.send_message(
                    _("I do not have the required permission to perform this action."),
                    ephemeral=True,
                )
                return
            await interaction.response.defer()
            config["action"] = action_select.values[0]
            await self.config_value(guild).set(config)
            await view.edit_message()

        action_select.callback = action_select_callback
        components.append(action_select)

        duration_button: discord.ui.Button = discord.ui.Button(
            label=_("Action Duration (for timeout/mute)"),
            style=discord.ButtonStyle.secondary,
            row=4,
        )

        async def duration_button_callback(interaction: discord.Interaction) -> None:
            await interaction.response.send_modal(
                ConfigureDurationModal(self, guild, view, config["duration"]),
            )

        duration_button.callback = duration_button_callback
        components.append(duration_button)

        return title, description, fields, components

    async def on_member_join(self, member: discord.Member) -> None:
        config = await self.config_value(member.guild)()
        if not config["enabled"]:
            return
        if await self.cog.is_trusted_admin_or_higher(member):
            return
        async with self.locks[member.guild]:
            utc_now = datetime.datetime.now(tz=datetime.timezone.utc)
            join_window = await DurationConverter.convert(None, config["join_window"])
            trigger_duration = await DurationConverter.convert(None, config["trigger_duration"])
            min_time = utc_now - join_window
            if (
                member.guild in self.triggered
                and (utc_now - self.triggered[member.guild]) >= trigger_duration
            ):
                min_time = max(min_time, self.triggered[member.guild] + trigger_duration)
                del self.triggered[member.guild]
            self.last_joins[member.guild] = [
                join for join in self.last_joins[member.guild] if join.timestamp >= min_time
            ]
            self.last_joins[member.guild].append(
                Join(
                    member=member,
                    avatar_hash=imagehash.phash(Image.open(BytesIO(await member.avatar.read())))
                    if member.avatar is not None
                    else None,
                    timestamp=utc_now,
                ),
            )

            flagged_joins_set = set()
            simple_flags = [
                flag
                for flag_name, flag in FLAGS.items()
                if config["flags"][flag_name] and not flag["pairwise"]
            ]
            pairwise_flags = [
                flag
                for flag_name, flag in FLAGS.items()
                if config["flags"][flag_name] and flag["pairwise"]
            ]
            for join in self.last_joins[member.guild]:
                for flag in simple_flags:
                    if flag["check"](join):
                        flagged_joins_set.add(join)
                        break
            for join_a, join_b in combinations(self.last_joins[member.guild], 2):
                for flag in pairwise_flags:
                    if flag["check"](join_a, join_b):
                        flagged_joins_set.add(join_a)
                        flagged_joins_set.add(join_b)
                        break
            if len(flagged_joins_set) < config["minimum_trigger"]:
                return
            flagged_joins = sorted(
                flagged_joins_set,
                key=lambda join: join.timestamp,
            )

            action_value = config["action"]
            formatted_join_window = CogsUtils.get_interval_string(join_window)
            reason = _(
                "**Anti Raid** - Detected {count} flagged accounts joining within {formatted_join_window}.",
            ).format(
                count=len(flagged_joins),
                formatted_join_window=formatted_join_window,
            )
            logs = [
                _("{member.mention} (`{member}`) joined the server.").format(member=join.member)
                for join in flagged_joins
            ]
            audit_log_reason = _(
                "Security's Anti Raid: {count} flagged accounts joined within {formatted_join_window}.",
            ).format(
                count=len(flagged_joins),
                formatted_join_window=formatted_join_window,
            )

            async def perform_action(join: Join) -> None:
                join.action_taken = True
                if action_value in ("timeout", "mute"):
                    duration = await DurationConverter.convert(
                        None,
                        config["duration"],
                    )
                    if action_value == "timeout":
                        duration = get_correct_timeout_duration(join.member, duration)
                else:
                    duration = None
                if action_value in ("kick", "ban"):
                    await self.cog.send_modlog(
                        action=action_value,
                        member=join.member,
                        reason=reason,
                        logs=logs,
                    )
                if action_value == "timeout" and member.guild.me.guild_permissions.moderate_members:
                    await join.member.timeout(duration, reason=audit_log_reason)
                elif (
                    action_value == "mute"
                    and member.guild.me.guild_permissions.manage_roles
                    and (Mutes := self.cog.bot.get_cog("Mutes")) is not None
                    and hasattr(Mutes, "mute_user")
                ):
                    await Mutes.mute_user(
                        guild=join.member.guild,
                        author=join.member.guild.me,
                        user=join.member,
                        until=datetime.datetime.now(tz=datetime.timezone.utc) + duration,
                        reason=audit_log_reason,
                    )
                elif action_value == "kick" and member.guild.me.guild_permissions.kick_members:
                    await join.member.kick(reason=audit_log_reason)
                elif action_value == "ban" and member.guild.me.guild_permissions.ban_members:
                    await join.member.ban(reason=audit_log_reason)
                elif (
                    action_value == "quarantine" and member.guild.me.guild_permissions.manage_roles
                ):
                    try:
                        await self.cog.quarantine_member(
                            member=join.member,
                            reason=reason,
                            logs=logs,
                        )
                    except RuntimeError:
                        pass
                if action_value not in ("quarantine", "kick", "ban"):
                    await self.cog.send_modlog(
                        action=action_value,
                        member=join.member,
                        reason=reason,
                        duration=duration,
                        logs=logs,
                    )

            if member.guild not in self.triggered:
                self.triggered[member.guild] = utc_now
                embed: discord.Embed = discord.Embed(
                    title=_("{emoji} Anti Raid Triggered!").format(emoji=self.emoji),
                    description=_(
                        "Detected {count} flagged accounts joining within {formatted_join_window}. Taking action on all flagged accounts.",
                    ).format(
                        count=len(flagged_joins),
                        formatted_join_window=formatted_join_window,
                    ),
                    color=Colors.ANTI_RAID.value,
                    timestamp=utc_now,
                )
                embed.add_field(
                    name=_("Flagged Accounts:"),
                    value="\n".join(
                        [f"- {join.member.mention} ({join.member})" for join in flagged_joins],
                    ),
                    inline=False,
                )
                embed.set_footer(
                    text=member.guild.name,
                    icon_url=member.guild.icon,
                )
                await self.cog.send_in_modlog_channel(
                    guild=member.guild,
                    embed=embed,
                )
            for join in flagged_joins:
                if not join.action_taken:
                    await perform_action(join)


class ConfigureSettingsModal(discord.ui.Modal):
    def __init__(
        self,
        module: AntiRaidModule,
        guild: discord.Guild,
        view: SettingsView,
        config: dict,
    ) -> None:
        self.module: AntiRaidModule = module
        self.guild: discord.Guild = guild
        self.view: SettingsView = view
        self.config: dict = config
        super().__init__(title=_("Configure Settings"))
        self.minimum_trigger_input: discord.ui.TextInput = discord.ui.TextInput(
            label=_("Minimum Trigger:"),
            style=discord.TextStyle.short,
            default=str(config["minimum_trigger"]),
            required=True,
        )
        self.join_window_input: discord.ui.TextInput = discord.ui.TextInput(
            label=_("Join Window:"),
            style=discord.TextStyle.short,
            default=config["join_window"],
            required=True,
        )
        self.trigger_duration_input: discord.ui.TextInput = discord.ui.TextInput(
            label=_("Trigger Duration:"),
            style=discord.TextStyle.short,
            default=config["trigger_duration"],
            required=True,
        )
        self.add_item(self.minimum_trigger_input)
        self.add_item(self.join_window_input)
        self.add_item(self.trigger_duration_input)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        try:
            minimum_trigger = int(self.minimum_trigger_input.value)
            join_window = self.join_window_input.value
            trigger_duration = self.trigger_duration_input.value
            await DurationConverter.convert(None, join_window)
            await DurationConverter.convert(None, trigger_duration)
        except ValueError as e:
            await interaction.followup.send(
                _("Invalid value: {error}").format(error=str(e)),
                ephemeral=True,
            )
            return
        self.config["minimum_trigger"] = minimum_trigger
        self.config["join_window"] = join_window
        self.config["trigger_duration"] = trigger_duration
        await self.module.config_value(self.guild).set(self.config)
        await self.view.edit_message()


class ConfigureDurationModal(discord.ui.Modal):
    def __init__(
        self,
        module: AntiRaidModule,
        guild: discord.Guild,
        view: SettingsView,
        duration: str,
    ) -> None:
        self.module: AntiRaidModule = module
        self.guild: discord.Guild = guild
        self.view: SettingsView = view
        self.duration: str = duration
        super().__init__(title=_("Configure Duration"))
        self.duration_input: discord.ui.TextInput = discord.ui.TextInput(
            label=_("Duration:"),
            style=discord.TextStyle.short,
            default=duration,
            required=True,
        )
        self.add_item(self.duration_input)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        try:
            duration = self.duration_input.value
            await DurationConverter.convert(None, duration)
        except ValueError as e:
            await interaction.followup.send(
                _("Invalid value: {error}").format(error=str(e)),
                ephemeral=True,
            )
            return
        self.duration = duration
        await self.module.config_value(self.guild).duration.set(duration)
        await self.view.edit_message()

from AAA3A_utils import CogsUtils, Loop  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

from redbot.core.utils.chat_formatting import box, humanize_list

import datetime
import functools
from collections import defaultdict

from ..constants import Emojis
from ..views import ToggleModuleButton
from .module import Module

_: Translator = Translator("Security", __file__)


LOGGING_EVENTS: typing.Dict[str, typing.Dict[str, typing.Union[str, typing.List[typing.Dict[str, typing.Union[str, discord.Color, bool]]]]]] = {
    "join_leave": {
        "name": "Joins/Leaves",
        "emoji": "👋",
        "events": [
            {"name": "Member Join", "emoji": "➕", "color": discord.Color.green(), "value": "member_join"},
            {"name": "Member Leave", "emoji": "➖", "color": discord.Color.red(), "value": "member_leave"},
            {"name": "Bot Add", "emoji": "🤖", "color": discord.Color.blurple(), "value": "bot_add"},
        ],
    },
    "member": {
        "name": "Members",
        "emoji": "🧑",
        "events": [
            {"name": "Ban", "emoji": "🔨", "color": discord.Color.red(), "value": "ban"},
            {"name": "Unban", "emoji": "🔓", "color": discord.Color.green(), "value": "unban"},
            {"name": "Kick", "emoji": "👢", "color": discord.Color.red(), "value": "kick"},
            {"name": "Member Role Update", "emoji": "🛡️", "color": discord.Color.gold(), "value": "member_role_update"},
            {"name": "Member Update", "emoji": "👤", "color": discord.Color.gold(), "value": "member_update"},
            {"name": "Member Disconnect", "emoji": "🔌", "color": discord.Color.red(), "value": "member_disconnect"},
            {"name": "Member Move", "emoji": "🚚", "color": discord.Color.gold(), "value": "member_move"},
            {"name": "Member Prune", "emoji": "✂️", "color": discord.Color.red(), "value": "member_prune"},
            {"name": "Automod Timeout Member", "emoji": "⏲️", "color": discord.Color.red(), "value": "automod_timeout_member"},
        ],
    },
    "channel": {
        "name": "Channels",
        "emoji": "📺",
        "events": [
            {"name": "Channel Create", "emoji": "📢", "color": discord.Color.blurple(), "value": "channel_create"},
            {"name": "Channel Delete", "emoji": "🗑️", "color": discord.Color.red(), "value": "channel_delete"},
            {"name": "Channel Update", "emoji": "✏️", "color": discord.Color.gold(), "value": "channel_update"},
            {"name": "Overwrite Create", "emoji": "📝", "color": discord.Color.green(), "value": "overwrite_create"},
            {"name": "Overwrite Delete", "emoji": "📝", "color": discord.Color.red(), "value": "overwrite_delete"},
            {"name": "Overwrite Update", "emoji": "📝", "color": discord.Color.gold(), "value": "overwrite_update"},
            {"name": "Thread Create", "emoji": "🧵", "color": discord.Color.green(), "value": "thread_create"},
            {"name": "Thread Delete", "emoji": "🧵", "color": discord.Color.red(), "value": "thread_delete"},
            {"name": "Thread Update", "emoji": "🧵", "color": discord.Color.gold(), "value": "thread_update"},
            {"name": "Webhook Create", "emoji": "🪝", "color": discord.Color.green(), "value": "webhook_create"},
            {"name": "Webhook Delete", "emoji": "🪝", "color": discord.Color.red(), "value": "webhook_delete"},
            {"name": "Webhook Update", "emoji": "🪝", "color": discord.Color.gold(), "value": "webhook_update"},
            {"name": "Stage Instance Create", "emoji": "🎤", "color": discord.Color.green(), "value": "stage_instance_create"},
            {"name": "Stage Instance Delete", "emoji": "🎤", "color": discord.Color.red(), "value": "stage_instance_delete"},
            {"name": "Stage Instance Update", "emoji": "🎤", "color": discord.Color.gold(), "value": "stage_instance_update"},
        ],
    },
    "message": {
        "name": "Messages",
        "emoji": "💬",
        "events": [
            {"name": "Message Edit", "emoji": "💬", "color": discord.Color.blurple(), "value": "message_edit", "default_ignore_bots": True},
            {"name": "Message Delete", "emoji": "🗑️", "color": discord.Color.red(), "value": "message_delete", "default_ignore_bots": True},
            {"name": "Message Bulk Delete", "emoji": "🧹", "color": discord.Color.red(), "value": "message_bulk_delete"},
            {"name": "Message Pin", "emoji": "📌", "color": discord.Color.gold(), "value": "message_pin"},
            {"name": "Message Unpin", "emoji": "📍", "color": discord.Color.gold(), "value": "message_unpin"},
            {"name": "Automod Block Message", "emoji": "🚫", "color": discord.Color.red(), "value": "automod_block_message"},
            {"name": "Automod Flag Message", "emoji": "🚩", "color": discord.Color.gold(), "value": "automod_flag_message"},
        ],
    },
    "role": {
        "name": "Roles",
        "emoji": "🏷️",
        "events": [
            {"name": "Role Create", "emoji": "➕", "color": discord.Color.green(), "value": "role_create"},
            {"name": "Role Delete", "emoji": "➖", "color": discord.Color.red(), "value": "role_delete"},
            {"name": "Role Update", "emoji": "✏️", "color": discord.Color.gold(), "value": "role_update"},
        ],
    },
    "server": {
        "name": "Server",
        "emoji": "🛡️",
        "events": [
            {"name": "Guild Update", "emoji": "🏰", "color": discord.Color.gold(), "value": "guild_update"},
            {"name": "Scheduled Event Create", "emoji": "📅", "color": discord.Color.green(), "value": "scheduled_event_create"},
            {"name": "Scheduled Event Delete", "emoji": "📅", "color": discord.Color.red(), "value": "scheduled_event_delete"},
            {"name": "Scheduled Event Update", "emoji": "📅", "color": discord.Color.gold(), "value": "scheduled_event_update"},
            {"name": "Invite Create", "emoji": "✉️", "color": discord.Color.green(), "value": "invite_create"},
            {"name": "Invite Delete", "emoji": "❌", "color": discord.Color.red(), "value": "invite_delete"},
            {"name": "Automod Rule Create", "emoji": "🚦", "color": discord.Color.green(), "value": "automod_rule_create"},
            {"name": "Automod Rule Delete", "emoji": "🚦", "color": discord.Color.red(), "value": "automod_rule_delete"},
            {"name": "Automod Rule Update", "emoji": "🚦", "color": discord.Color.gold(), "value": "automod_rule_update"},
            {"name": "Integration Create", "emoji": "🔗", "color": discord.Color.green(), "value": "integration_create"},
            {"name": "Integration Delete", "emoji": "🔗", "color": discord.Color.red(), "value": "integration_delete"},
            {"name": "Integration Update", "emoji": "🔗", "color": discord.Color.gold(), "value": "integration_update"},
            {"name": "Emoji Create", "emoji": "😀", "color": discord.Color.green(), "value": "emoji_create"},
            {"name": "Emoji Delete", "emoji": "😶", "color": discord.Color.red(), "value": "emoji_delete"},
            {"name": "Emoji Update", "emoji": "😃", "color": discord.Color.gold(), "value": "emoji_update"},
            {"name": "Sticker Create", "emoji": "🏷️", "color": discord.Color.green(), "value": "sticker_create"},
            {"name": "Sticker Delete", "emoji": "🏷️", "color": discord.Color.red(), "value": "sticker_delete"},
            {"name": "Sticker Update", "emoji": "🏷️", "color": discord.Color.gold(), "value": "sticker_update"},
            {"name": "App Command Permission Update", "emoji": "⚙️", "color": discord.Color.gold(), "value": "app_command_permission_update"},
            {"name": "Soundboard Sound Create", "emoji": "🔊", "color": discord.Color.green(), "value": "soundboard_sound_create"},
            {"name": "Soundboard Sound Delete", "emoji": "🔇", "color": discord.Color.red(), "value": "soundboard_sound_delete"},
            {"name": "Soundboard Sound Update", "emoji": "🔉", "color": discord.Color.gold(), "value": "soundboard_sound_update"},
            {"name": "Creator Monetization Request Created", "emoji": "💰", "color": discord.Color.green(), "value": "creator_monetization_request_created"},
            {"name": "Creator Monetization Terms Accepted", "emoji": "💰", "color": discord.Color.green(), "value": "creator_monetization_terms_accepted"},
        ],
    },
}


class LoggingModule(Module):
    name = "Logging"
    emoji = Emojis.LOGGING.value
    description = "Configure logging for various events in your server."
    default_config = {
        "enabled": False,
        "events": {
            category: {
                event["value"]: {
                    "enabled": True,
                    "channel": None,
                    "ignore_bots": event.get("default_ignore_bots", False),
                    "emoji": event["emoji"],
                    "color": event["color"].value,
                }
                for event in data["events"]
            }
            for category, data in LOGGING_EVENTS.items()
        }
    }
    

    def __init__(self, cog: commands.Cog) -> None:
        super().__init__(cog)
        self.invites_cache: typing.Dict[discord.Guild, typing.Dict[str, typing.Dict[typing.Literal["uses", "max_uses", "inviter"], typing.Union[typing.Optional[int], discord.Member, discord.User]]]] = defaultdict(dict)
        self.loop: Loop = None

    async def load(self) -> None:
        self.cog.bot.add_listener(self.on_member_join)
        self.cog.bot.add_listener(self.on_member_remove)
        self.cog.bot.add_listener(self.on_message_edit)
        self.cog.bot.add_listener(self.on_message_delete)
        self.cog.bot.add_listener(self.on_audit_log_entry_create)
        self.loop: Loop = Loop(
            cog=self.cog,
            name="Cache Invites",
            function=self.cache_invites,
            minutes=5,
        )
        self.cog.loops.append(self.loop)

    async def unload(self) -> None:
        self.loop.stop_all()
        self.cog.bot.remove_listener(self.on_member_join)
        self.cog.bot.remove_listener(self.on_member_remove)
        self.cog.bot.remove_listener(self.on_message_edit)
        self.cog.bot.remove_listener(self.on_message_delete)
        self.cog.bot.remove_listener(self.on_audit_log_entry_create)

    async def get_status(
        self, guild: discord.Guild
    ) -> typing.Tuple[typing.Literal["✅", "⚠️", "❌"], str, str]:
        config = await self.config_value(guild)()
        if not config["enabled"]:
            return "❌", _("Disabled"), _("Logging is currently disabled.")
        if any(
            event["enabled"] and (
                (channel_id := event["channel"]) is None
                or guild.get_channel(channel_id) is None
                or not guild.get_channel(channel_id).permissions_for(guild.me).send_messages
            )
            for events in config["events"].values()
            for event in events.values()
        ):
            return "⚠️", _("Warning"), _("Some events are enabled but the report channel is not set or inaccessible.")
        if not guild.me.guild_permissions.view_audit_log:
            return "⚠️", _("Warning"), _("The bot lacks the `View Audit Log` permission, which may limit logging capabilities.")
        return "✅", _("Enabled"), _("Logging is enabled and configured.")

    async def get_settings(
        self, guild: discord.Guild, view: discord.ui.View
    ) -> typing.Tuple[str, str, typing.List[typing.Dict], typing.List[discord.ui.Item]]:
        config = await self.config_value(guild)()
        title = _("Security — {emoji} {name} {status}").format(
            emoji=self.emoji, name=self.name, status=(await self.get_status(guild))[0]
        )
        description = _("Configure logging for various events in your server. You can enable or disable specific events, set the logging channel, and more.")
        status = await self.get_status(guild)
        if status[0] == "⚠️":
            description += f"\n{status[0]} **{status[1]}**: {status[2]}"

        fields = []
        for category, data in LOGGING_EVENTS.items():
            category_config = config["events"][category]
            # fields.append(
            #     {
            #         "name": f"{category.replace('_', ' ').title()}:",
            #         "value": "\n".join(
            #             f"{'✅' if category_config[event['value']]['enabled'] else '❌'} {category_config[event['value']]['emoji']} {event['name']}"
            #             for event in data["events"]
            #         ),
            #         "inline": True,
            #     }
            # )
            fields.append(
                {
                    "name": f"{data['emoji']} {data['name']}:",
                    "value": "",
                    "inline": True,
                }
            )
            first_state = list(category_config.values())[0]["enabled"]
            if all(event["enabled"] == first_state for event in category_config.values()):
                fields[-1]["value"] += _("**Enabled:** {state}").format(state="✅" if first_state else "❌")
            else:
                fields[-1]["value"] += _("**Enabled:** 🔀 (Different States)")
            first_channel_id = list(category_config.values())[0]["channel"]
            if all(event["channel"] == first_channel_id for event in category_config.values()):
                if first_channel_id is not None and (channel := guild.get_channel(first_channel_id)) is not None:
                    fields[-1]["value"] += _("\n**Channel:** {channel.mention} (`{channel}`)").format(
                        channel=channel
                    )
                else:
                    fields[-1]["value"] += _("\n**Channel:** None")
            else:
                fields[-1]["value"] += "\n**Channel:** 🔀 (Different Channels)"
            

        components = [ToggleModuleButton(self, guild, view, config["enabled"])]
        toggle_all_button: discord.ui.Button = discord.ui.Button(
            label=_("Toggle All Events"),
            style=discord.ButtonStyle.secondary,
        )
        async def toggle_all_callback(interaction: discord.Interaction) -> None:
            new_state = not list(config["events"].values())[0]["enabled"]
            for events in config["events"].values():
                for event in events.values():
                    event["enabled"] = new_state
            await self.config_value(guild).events.set(config["events"])
            await interaction.response.send_message(
                _("✅ All logging events have been **{state}**.").format(state=_("enabled") if new_state else _("disabled")),
                ephemeral=True,
            )
            await view._message.edit(embed=await view.get_embed(), view=view)
        toggle_all_button.callback = toggle_all_callback
        components.append(toggle_all_button)
        channel_all_select: discord.ui.ChannelSelect = discord.ui.ChannelSelect(
            channel_types=[discord.ChannelType.text],
            placeholder=_("Select a channel for all events..."),
        )
        async def channel_all_callback(interaction: discord.Interaction) -> None:
            channel = channel_all_select.values[0]
            for events in config["events"].values():
                for event in events.values():
                    event["channel"] = channel.id
            await self.config_value(guild).events.set(config["events"])
            await interaction.response.send_message(
                _("✅ All events will now be logged in {channel.mention}.").format(channel=channel),
                ephemeral=True,
            )
            await view._message.edit(embed=await view.get_embed(), view=view)
        channel_all_select.callback = channel_all_callback
        components.append(channel_all_select)

        create_a_logging_category_button: discord.ui.Button = discord.ui.Button(
            label=_("Create a Logging Category"),
            style=discord.ButtonStyle.primary,
            disabled=not guild.me.guild_permissions.manage_channels,
        )
        async def create_logging_category_callback(interaction: discord.Interaction) -> None:
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
                    "⚠️ Are you sure you want to create a new logging category with some channels? That will overwrite the current logging channel for all events."
                ),
                timeout_message=None,
                ephemeral=True,
            ):
                return
            category_channel = await guild.create_category(
                name=_("Logs"),
                overwrites={
                    guild.default_role: discord.PermissionOverwrite(
                        view_channel=False, send_messages=False
                    ),
                    guild.me: discord.PermissionOverwrite(
                        view_channel=True, send_messages=True, embed_links=True
                    ),
                },
                reason=_("Created by Security's Logging Module."),
            )
            config["enabled"] = True
            for category, events in config["events"].items():
                channel = await category_channel.create_text_channel(
                    name=f"{category.replace('_', '-')}-logs",
                    topic=_("This channel is used for logging {category} events.").format(category=LOGGING_EVENTS[category]["name"]),
                    reason=_("Created by Security's Logging Module."),
                )
                for event in events.values():
                    event["channel"] = channel.id
            await self.config_value(guild).set(config)
            await interaction.followup.send(
                _("✅ A new logging category has been created: {category.name}.").format(category=category),
                ephemeral=True,
            )
        create_a_logging_category_button.callback = create_logging_category_callback
        components.append(create_a_logging_category_button)

        create_a_logging_channel_button: discord.ui.Button = discord.ui.Button(
            label=_("Create a Logging Channel"),
            style=discord.ButtonStyle.primary,
            disabled=not guild.me.guild_permissions.manage_channels,
        )
        async def create_logging_channel_callback(interaction: discord.Interaction) -> None:
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
                _("⚠️ Are you sure you want to create a new logging channel? That will overwrite the current logging channel for all events."),
                timeout_message=None,
                ephemeral=True,
            ):
                return
            channel = await guild.create_text_channel(
                name=_("logs"),
                topic=_("This channel is used for logging various events."),
                overwrites={
                    guild.default_role: discord.PermissionOverwrite(
                        view_channel=False, send_messages=False
                    ),
                    guild.me: discord.PermissionOverwrite(
                        view_channel=True, send_messages=True, embed_links=True
                    ),
                },
                reason=_("Created by Security's Logging Module."),
            )
            config["enabled"] = True
            for events in config["events"].values():
                for event in events.values():
                    event["channel"] = channel.id
            await self.config_value(guild).set(config)
            await interaction.followup.send(
                _("✅ A new logging channel has been created: {channel.mention}.").format(channel=channel),
                ephemeral=True,
            )
        create_a_logging_channel_button.callback = create_logging_channel_callback
        components.append(create_a_logging_channel_button)

        configure_event_category_select: discord.ui.Select = discord.ui.Select(
            placeholder=_("Select an event category to configure..."),
            options=[
                discord.SelectOption(
                    emoji=data["emoji"],
                    label=data["name"],
                    value=category,
                )
                for category, data in LOGGING_EVENTS.items()
            ],
        )
        async def configure_event_category_callback(interaction: discord.Interaction) -> None:
            await interaction.response.defer(ephemeral=True, thinking=True)
            await ConfigureEventCategoryView(
                self, guild, view,
                configure_event_category_select.values[0],
            ).start(interaction)
        configure_event_category_select.callback = configure_event_category_callback
        components.append(configure_event_category_select)

        return title, description, fields, components

    async def get_event(self, guild: discord.Guild, event_value: str) -> typing.Dict[str, typing.Any]:
        config = await self.config_value(guild)()
        for category, events in config["events"].items():
            if event_value in events:
                event = events[event_value]
                event["name"] = next(
                    (e["name"] for e in LOGGING_EVENTS[category]["events"] if e["value"] == event_value)
                )
                event["category"] = category
                event["value"] = event_value
                return event

    async def check_config(
        self, guild: discord.Guild, event: typing.Dict[str, typing.Any], responsible: discord.Member
    ) -> discord.TextChannel:
        config = await self.config_value(guild)()
        if not config["enabled"] or not event["enabled"]:
            return False
        if event.get("ignore_bots", False) and responsible.bot:
            return False
        if (
            event["value"] in ("message_edit", "message_delete")
            and await self.cog.is_whitelisted(responsible, "logging_message_log")
        ):
            return False
        if (
            (channel_id := event["channel"]) is None
            or (channel := guild.get_channel(channel_id)) is None
            or channel.id != channel_id
            or not channel.permissions_for(guild.me).view_channel
            or not channel.permissions_for(guild.me).send_messages
        ):
            return False
        return channel

    async def get_embed(
        self,
        guild: discord.Guild,
        event: typing.Dict[str, typing.Any],
        responsible: discord.Member,
        target: typing.Optional[typing.Union[discord.Member, discord.abc.GuildChannel, discord.Thread, discord.Message, discord.Role, discord.Emoji, discord.Sticker, discord.ScheduledEvent]] = None,
        extra: typing.Optional[typing.Any] = None,
        reason: typing.Optional[str] = None,
        before: typing.Optional[typing.Any] = None,
    ) -> discord.Embed:
        embed: discord.Embed = discord.Embed(
            title=f"{event['name']} {event['emoji']}",
            color=discord.Color(event["color"]),
            timestamp=datetime.datetime.now(datetime.timezone.utc),
        )
        embed.set_author(
            name=responsible.display_name,
            icon_url=responsible.display_avatar,
        )
        embed.description = _("{emoji} **Responsible:** {responsible.mention} (`{responsible}`) {responsible_emojis} - `{responsible.id}`").format(
            emoji=Emojis.ISSUED_BY.value,
            responsible=responsible,
            responsible_emojis=await self.cog.get_member_emojis(responsible),
        )
        if target is not None:
            embed.set_thumbnail(
                url=(
                    target.display_avatar
                    if isinstance(target, discord.Member) else
                    (target.icon if isinstance(target, discord.Role) else None)
                ),
            )
            if isinstance(target, discord.Member):
                embed.description += "\n" + _(
                    "{emoji} **Target Member:** {member.mention} (`{member}`) {member_emojis} - `{member.id}`"
                ).format(
                    emoji=Emojis.MEMBER.value,
                    member=target,
                    member_emojis=await self.cog.get_member_emojis(target),
                )
            elif isinstance(target, discord.User):
                embed.description += "\n" + _("{emoji} **Target User:** `{user}` - `{user.id}`").format(
                    emoji=Emojis.MEMBER.value,
                    user=target
                )
            elif isinstance(target, discord.Role):
                embed.description += "\n" + _("{emoji} **Target Role:** {role.mention} (`{role}`) - `{role.id}`").format(emoji=Emojis.ROLE.value, role=target)
            elif isinstance(target, (discord.TextChannel, discord.VoiceChannel, discord.StageChannel, discord.CategoryChannel)):
                embed.description += "\n" + _("{emoji} **Target Channel:** {channel.mention} (`{channel}`) - `{channel.id}`").format(
                    emoji=Emojis.CHANNEL.value,
                    channel=target
                )
            elif isinstance(target, discord.Thread):
                embed.description += "\n" + _("{emoji} **Target Thread:** {thread.mention} (`{thread}`) - `{thread.id}`").format(
                    emoji=Emojis.THREAD.value,
                    thread=target,
                )
            elif isinstance(target, discord.Message):
                embed.description += "\n" + _("{emoji} **Target Message:** [`Jump to Message`]({message.jump_url})").format(
                    emoji=Emojis.MESSAGE.value,
                    message=target
                )
                if target.author != responsible:
                    embed.description += _("\n- **Author:** {target.author.mention} (`{target.author}`) - `{target.author.id}`").format(
                        target=target
                    )
            elif isinstance(target, discord.Emoji):
                embed.description += "\n" + _("{emoji} **Target Emoji:** `{target.name}` - `{target.id}`").format(
                    emoji=Emojis.EMOJI.value,
                    target=target,
                )
            elif isinstance(target, discord.Sticker):
                embed.description += "\n" + _("{emoji} **Target Sticker:** `{sticker.name}` - `{sticker.id}`").format(
                    emoji=Emojis.STICKER.value,
                    sticker=target,
                )
            elif isinstance(target, discord.ScheduledEvent):
                embed.description += "\n" + _("{emoji} **Target Scheduled Event:** `{event.name}` - `{event.id}`").format(
                    emoji=Emojis.SCHEDULED_EVENT.value,
                    event=target
                )
            elif isinstance(target, discord.Object) and before is not None:
                if event["value"] == "channel_delete":
                    embed.description += "\n" + _("{emoji} **Target Channel:** `{target_name}` - `{target.id}`").format(
                        emoji=Emojis.CHANNEL.value, target_name=before.name, target=target
                    )
                elif event["value"] == "thread_delete":
                    embed.description += "\n" + _("{emoji} **Target Thread:** `{target_name}` - `{target.id}`").format(
                        emoji=Emojis.THREAD.value, target_name=before.name, target=target
                    )
                elif event["value"] == "role_delete":
                    embed.description += "\n" + _("{emoji} **Target Role:** `{target_name}` - `{target.id}`").format(
                        emoji=Emojis.ROLE.value, target_name=before.name, target=target
                    )
                else:
                    embed.description += "\n" + _("🗑️ **Target:** `{target}` - `{target.id}`").format(
                        target=target
                    )
        if extra is not None:
            if isinstance(extra, discord.Member):
                embed.description += _("\n{emoji} **Target Member:** {member.mention} (`{member}`) - `{member.id}`").format(
                    emoji=Emojis.MEMBER.value, member=extra
                )
            elif isinstance(extra, discord.Role):
                embed.description += _("\n{emoji} **Target Role:** {role.mention} (`{role}`) - `{role.id}`").format(
                    emoji=Emojis.ROLE.value, role=extra
                )
        if reason is not None:
            embed.description += _("\n{emoji} **Reason:**\n>>> {reason}").format(emoji=Emojis.REASON.value, reason=reason)
        embed.set_footer(text=guild.name, icon_url=guild.icon)
        return embed

    async def cache_invites(self) -> None:
        guilds_data = await self.cog.config.all_guilds()
        for guild_id, guild_data in guilds_data.items():
            if (guild := self.cog.bot.get_guild(guild_id)) is None:
                continue
            if not guild.me.guild_permissions.manage_guild:
                continue
            if not guild_data.get("modules", {}).get("logging", {}).get("enabled", False):
                continue
            invites = await guild.invites()
            self.invites_cache[guild] = {
                invite.code: {
                    "uses": invite.uses,
                    "max_uses": invite.max_uses or None,
                    "inviter": invite.inviter,
                }
                for invite in invites
            }

    async def get_invite(self, member: discord.Member) -> typing.Optional[str]:
        possible_invite = None
        view_audit_logs, manage_guild = member.guild.me.guild_permissions.view_audit_log, member.guild.me.guild_permissions.manage_guild
        if member.bot:
            if view_audit_logs:
                async for entry in member.guild.audit_logs(limit=3, action=discord.AuditLogAction.bot_add):
                    if entry.target.id == member.id:
                        return _("- Added by {user.mention} (`{user}`) - `{user.id}`").format(user=entry.user)
            return possible_invite
        if "VANITY_URL" in member.guild.features and member.guild.vanity_url is not None:
            possible_invite = _("- {vanity_url} (Vanity URL)").format(vanity_url=f"https://discord.gg/{member.guild.vanity_url}")
        if self.invites_cache[member.guild] and manage_guild:
            invites = self.invites_cache[member.guild].copy()
            guild_invites = await member.guild.invites()
            for invite in guild_invites:
                if invite.code in invites:
                    if invite.uses is None or invites[invite.code]["uses"] is None:
                        continue
                    if invite.uses > invites[invite.code]["uses"]:
                        possible_invite = _("- https://discord.gg/{invite.code}\n- Invited by {inviter.mention} (`{inviter}`) - `{inviter.id}`").format(
                            invite=invite, inviter=invite.inviter
                        )
                        break
            if possible_invite is None:
                for code, data in invites.items():
                    try:
                        invite = await member.guild.fetch_invite(code)
                    except discord.NotFound:
                        if data["max_uses"] is not None and (data["max_uses"] - data["uses"]) == 1:
                            possible_invite = _("- https://discord.gg/{code}\n- Invited by {inviter.mention} (`{inviter}`) - `{inviter.id}`").format(
                                code=code, inviter=data["inviter"]
                            )
                            break
            await self.cache_invites()  # Refresh cache.
        if possible_invite is None and view_audit_logs:
            async for entry in member.guild.audit_logs(limit=1, action=discord.AuditLogAction.invite_create):
                if entry.target.id == member.id:
                    possible_invite = _("- https://discord.gg/{entry.target.code}\n- Invited by {entry.user.mention} (`{entry.user}`) - `{entry.user.id}`").format(entry=entry)
                    break
        return possible_invite

    async def on_member_join(self, member: discord.Member) -> None:
        event = await self.get_event(member.guild, "member_join")
        if not (channel := await self.check_config(member.guild, event, member)):
            return
        embed: discord.Embed = await self.get_embed(member.guild, event, member)
        embed.description += _("\n🎂 **Account Created:** {created_at} ({created_ago})").format(
            created_at=discord.utils.format_dt(member.created_at, "F"),
            created_ago=discord.utils.format_dt(member.created_at, "R"),
        )
        if member.roles and not member.top_role.is_default():
            embed.description += _("\n👥 **Roles:** {roles}").format(
                roles=humanize_list(
                    [f"{role.mention} (`{role.name}`)" for role in member.roles if not role.is_default()]
                ) or _("None"),
            )
        embed.description += _("\n🔢 **New Member Count:** {count} incuding {bots} bots").format(
            count=member.guild.member_count,
            bots=len([m for m in member.guild.members if m.bot]),
        )
        if (invite := await self.get_invite(member)) is not None:
            embed.add_field(
                name=_("🔗 Used Invite Link:"),
                value=invite,
                inline=False
            )
        await channel.send(embed=embed)

    async def on_member_remove(self, member: discord.Member) -> None:
        event = await self.get_event(member.guild, "member_leave")
        if not (channel := await self.check_config(member.guild, event, member)):
            return
        embed: discord.Embed = await self.get_embed(member.guild, event, member)
        embed.description += _("\n👥 **Roles:** {roles}").format(
            roles=humanize_list(
                [f"{role.mention} (`{role.name}`)" for role in member.roles if not role.is_default()]
            ) or _("None"),
        )
        embed.description += _("\n🔢 **New Member Count:** {count} incuding {bots} bots").format(
            count=member.guild.member_count,
            bots=len([m for m in member.guild.members if m.bot]),
        )
        await channel.send(embed=embed)

    async def on_message_edit(self, before: discord.Message, after: discord.Message) -> None:
        if after.guild is None:
            return
        if before.content == after.content:
            return
        event = await self.get_event(after.guild, "message_edit")
        if not (channel := await self.check_config(after.guild, event, after.author)):
            return
        embed: discord.Embed = await self.get_embed(
            after.guild, event, after.author, after
        )
        embed.description += f"\n{box('- ' + before.content, 'diff')}"
        if len(embed.description) + len(after.content) <= 4082:
            embed.description += f"\n{box('+ ' + after.content, 'diff')}"
        if after.reference is not None and after.reference.resolved is not None:
            jump_link = (
                after.reference.resolved.jump_url
                if isinstance(after.reference.resolved, discord.Message)
                else f"https://discord.com/channels/{after.guild.id}/{after.channel.id}/{after.reference.message_id}"
            )
            embed.add_field(
                name=_("Replying to:"),
                value=f"[Jump to Message]({jump_link})",
                inline=False,
            )
        await channel.send(embed=embed)

    async def on_message_delete(self, message: discord.Message) -> None:
        if message.guild is None:
            return
        event = await self.get_event(message.guild, "message_delete")
        if not (channel := await self.check_config(message.guild, event, message.author)):
            return
        responsible = message.author
        async for entry in message.guild.audit_logs(limit=3, action=discord.AuditLogAction.message_delete, oldest_first=False):
            if entry.target.id == message.id:
                responsible = entry.user
                break
        embed: discord.Embed = await self.get_embed(
            message.guild, event, responsible, message
        )
        embed.description += f"\n{box('- ' + message.content, 'diff')}" if message.content else ""
        if message.attachments:
            embed.description += "\n" + _("{emoji} **Attachments:**").format(emoji=Emojis.ATTACHMENTS.value)
            for attachment in message.attachments:
                embed.description += f"\n- [{attachment.filename}]({attachment.url})"
        if message.reference is not None and message.reference.resolved is not None:
            jump_link = (
                message.reference.resolved.jump_url
                if isinstance(message.reference.resolved, discord.Message)
                else f"https://discord.com/channels/{message.guild.id}/{message.channel.id}/{message.reference.message_id}"
            )
            embed.add_field(
                name=_("Replying to:"),
                value=f"[Jump to Message]({jump_link})",
                inline=False,
            )
        await channel.send(embed=embed)

    async def on_audit_log_entry_create(self, entry: discord.AuditLogEntry) -> None:
        if (event := await self.get_event(entry.guild, entry.action.name)) is None:
            return
        if not (channel := await self.check_config(entry.guild, event, entry.user)):
            return
        embed: discord.Embed = await self.get_embed(
            entry.guild, event, entry.user, entry.target,
            extra=entry.extra, reason=entry.reason, before=entry.before,
        )
        def get_formatting(value: typing.Any) -> str:
            if isinstance(value, str):
                return f"`{value}`"
            elif isinstance(value, bool):
                return "✅" if value else "❌"
            elif isinstance(value, discord.Color):
                return f"`#{value.value:06X}`"
            elif isinstance(value, discord.Permissions):
                return f"`Permissions({value.value})`"
            elif (
                isinstance(value, typing.List)
                and value
                and isinstance(value[0], typing.Tuple)
                and isinstance(value[0][1], discord.PermissionOverwrite)
            ):
                result = ""
                for target, overwrite in value:
                    if (member := entry.guild.get_member(target.id)) is not None:
                        target_display = f"{member.display_name} (`{member}`) - `{member.id}`"
                    elif (role := entry.guild.get_role(target.id)) is not None:
                        target_display = f"{role.mention} (`{role.name}`) - `{role.id}`"
                    else:
                        target_display = f"{target.type.__name__} `{target.id}`"
                    result += f"\n  - {target_display} - `PermissionOverwrite({len(overwrite._values)} permissions)`"
                return result
            return f"`{value}`"
        added_permissions, removed_permissions = [], []
        if entry.action != discord.AuditLogAction.member_role_update:
            entry_before = any(getattr(entry.before, key) for key in entry.before.__dict__.keys())
            entry_after = any(getattr(entry.after, key) for key in entry.after.__dict__.keys())
            if not entry_before and entry_after:
                embed.add_field(
                    name=_("Settings:"),
                    value="\n".join(
                        f"- **{key.replace('_', ' ').title()}**: {get_formatting(value)}"
                        for key, value in entry.after.__dict__.items()
                        if key == "colour"
                    ),
                )
            elif entry_before and not entry_after:
                embed.add_field(
                    name=_("Previous Settings:"),
                    value="\n".join(
                        f"- **{key.replace('_', ' ').title()}**: {get_formatting(value)}"
                        for key, value in entry.before.__dict__.items()
                        if key == "colour"
                    ),
                )
            elif entry_before and entry_after:
                embed.add_field(
                    name=_("Changes:"),
                    value="\n".join(
                        f"- **{key.replace('_', ' ').title()}**: {get_formatting(before)} ➡️ {get_formatting(after)}"
                        for key, after in entry.after.__dict__.items()
                        if hasattr(entry.before, key) and after != (before := getattr(entry.before, key)) and key == "colour"
                    ),
                )
            if hasattr(entry.after, "permissions"):
                added_permissions.extend(
                    permission.replace('_', ' ').title()
                    for permission, value in entry.after.permissions
                    if value and not getattr(entry.before.permissions, permission, False)
                )
                removed_permissions.extend(
                    permission.replace('_', ' ').title()
                    for permission, value in entry.after.permissions
                    if not value and getattr(entry.before.permissions, permission, False)
                )
            else:
                if hasattr(entry.after, "allow"):
                    added_permissions.extend(
                        permission.replace('_', ' ').title()
                        for permission, value in entry.after.allow
                        if value
                    )
                if hasattr(entry.after, "deny"):
                    removed_permissions.extend(
                        permission.replace('_', ' ').title()
                        for permission, value in entry.after.deny
                        if value
                    )
        else:
            if entry.after.roles:
                embed.add_field(
                    name=_("Added Roles:"),
                    value="\n".join(
                        f"- {role.mention} (`{role.name}`) - `{role.id}`"
                        for role in entry.after.roles if role not in entry.before.roles
                    ),
                )
                for role in entry.after.roles:
                    for permission, value in role.permissions:
                        if value and all(not getattr(r.permissions, permission, False) for r in entry.target.roles if r not in entry.after.roles):
                            added_permissions.append(permission.replace('_', ' ').title())
            if entry.before.roles:
                embed.add_field(
                    name=_("Removed Roles:"),
                    value="\n".join(
                        f"- {role.mention} (`{role.name}`) - `{role.id}`"
                        for role in entry.before.roles if role not in entry.after.roles
                    ),
                )
                for role in entry.before.roles:
                    for permission, value in role.permissions:
                        if value and not getattr(entry.target.guild_permissions, permission, False):
                            removed_permissions.append(permission.replace('_', ' ').title())
        if added_permissions or removed_permissions:
            embed.add_field(
                name=_("Permissions Changes:"),
                value=box(
                    (
                        "\n".join(
                            f"+ {perm}" for perm in added_permissions
                        ) + "\n" + "\n".join(
                            f"- {perm}" for perm in removed_permissions
                        )
                    ).strip(),
                    lang="diff",
                ),
                inline=False,
            )
        await channel.send(embed=embed)


class ConfigureEventCategoryView(discord.ui.View):
    def __init__(self, module: LoggingModule, guild: discord.Guild, parent_view: discord.ui.View, category: str) -> None:
        super().__init__(timeout=None)
        self.module: LoggingModule = module
        self.guild: discord.Guild = guild
        self.category: str = category
        self.parent_view: discord.ui.View = parent_view
        self._message: discord.Message = None

        self.select_logging_channel.placeholder = _("Select a channel to log events...")
        self.configure_event_select.placeholder = _("Select an event to configure...")
        self.configure_event_select.options = [
            discord.SelectOption(
                emoji=event["emoji"],
                label=event["name"],
                value=event["value"],
            )
            for event in LOGGING_EVENTS[self.category]["events"]
        ]

    async def start(self, interaction: discord.Interaction) -> None:
        self._message: discord.Message = await interaction.followup.send(
            embed=await self.get_embed(),
            view=self,
            ephemeral=True,
            wait=True,
        )
        self.module.cog.views[self._message] = self

    async def get_embed(self) -> discord.Embed:
        config = await self.module.config_value(self.guild)()
        category = LOGGING_EVENTS[self.category]
        embed: discord.Embed = discord.Embed(
            title=_("Configure {emoji} {category_name} Events").format(
                emoji=category["emoji"],
                category_name=category["name"],
            ),
            description="\n".join(
                f"{'✅' if config['events'][self.category][event['value']]['enabled'] else '❌'} {event['emoji']} {event['name']}{f' - {channel.mention} (`{channel}`)' if (channel_id := config['events'][self.category][event['value']]['channel']) is not None and (channel := self.guild.get_channel(channel_id)) is not None else ''}"
                for event in LOGGING_EVENTS[self.category]["events"]
            ),
        )
        first_state = list(config["events"][self.category].values())[0]["enabled"]
        if all(event["enabled"] == first_state for event in config["events"][self.category].values()):
            self.toggle_event_category.label = _("Enable All") if not first_state else _("Disable All")
            self.toggle_event_category.style = discord.ButtonStyle.success if not first_state else discord.ButtonStyle.danger
        else:
            self.toggle_event_category.label = _("Toggle All")
            self.toggle_event_category.style = discord.ButtonStyle.secondary
        first_channel_id = next(
            (event["channel"] for event in config["events"][self.category].values()),
        )
        if (
            first_channel_id is not None
            and (channel := self.guild.get_channel(first_channel_id)) is not None
        ):
            self.select_logging_channel.default_values = [channel]
        else:
            self.select_logging_channel.default_values = []
        return embed

    async def on_timeout(self) -> None:
        try:
            await self._message.delete()
        except discord.HTTPException:
            pass

    @discord.ui.button(label="Toggle All")
    async def toggle_event_category(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        config = await self.module.config_value(self.guild)()
        new_state = not list(config["events"][self.category].values())[0]["enabled"]
        for event in config["events"][self.category].values():
            event["enabled"] = new_state
        await self.module.config_value(self.guild).set(config)
        await interaction.response.send_message(
            _("✅ All {category_name} events have been {state}.").format(
                category_name=LOGGING_EVENTS[self.category]["name"],
                state=_("enabled") if new_state else _("disabled"),
            ),
            ephemeral=True,
        )
        await self._message.edit(
            embed=await self.get_embed(),
            view=self,
        )
        await self.parent_view._message.edit(
            embed=await self.parent_view.get_embed(),
            view=self.parent_view,
        )

    @discord.ui.select(
        cls=discord.ui.ChannelSelect,
        channel_types=[discord.ChannelType.text],
        placeholder="Select a channel to log events...",
    )
    async def select_logging_channel(self, interaction: discord.Interaction, select: discord.ui.Select) -> None:
        config = await self.module.config_value(self.guild)()
        channel = select.values[0]
        for event in config["events"][self.category].values():
            event["channel"] = channel.id
        await self.module.config_value(self.guild).set(config)
        await interaction.response.send_message(
            _("✅ All {category_name} events will now be logged in {channel.mention}.").format(
                category_name=LOGGING_EVENTS[self.category]["name"],
                channel=channel,
            ),
            ephemeral=True,
        )
        await self._message.edit(
            embed=await self.get_embed(),
            view=self,
        )
        await self.parent_view._message.edit(
            embed=await self.parent_view.get_embed(),
            view=self.parent_view,
        )

    @discord.ui.select(placeholder="Select an event to configure...")
    async def configure_event_select(self, interaction: discord.Interaction, select: discord.ui.Select) -> None:
        await interaction.response.defer()
        event = next(
            (e for e in LOGGING_EVENTS[self.category]["events"] if e["value"] == select.values[0]),
        )
        await ConfigureEventView(self.module, self.guild, self.parent_view, self, self.category, event).start(interaction)


class ConfigureEventView(discord.ui.View):
    def __init__(
        self,
        module: LoggingModule,
        guild: discord.Guild,
        parent_view: discord.ui.View, category_view: ConfigureEventCategoryView,
        category: str, event: typing.Dict[str, typing.Any],
    ) -> None:
        super().__init__(timeout=None)
        self.module: LoggingModule = module
        self.guild: discord.Guild = guild
        self.category: str = category
        self.event: typing.Dict[str, typing.Any] = event
        self.parent_view: discord.ui.View = parent_view
        self.category_view: ConfigureEventCategoryView = category_view
        self._message: discord.Message = None

        self.toggle_event.label = _("Toggle {event_name}").format(event_name=self.event["name"])
        self.channel_select.placeholder = _("Select a channel to log this event...")

    async def start(self, interaction: discord.Interaction) -> None:
        self._message: discord.Message = await interaction.followup.send(
            embed=await self.get_embed(),
            view=self,
            ephemeral=True,
            wait=True,
        )
        self.module.cog.views[self._message] = self

    async def get_embed(self) -> discord.Embed:
        config = await self.module.config_value(self.guild)()
        state = config["events"][self.category][self.event["value"]]["enabled"]
        channel = (
            channel
            if (channel_id := config["events"][self.category][self.event["value"]]["channel"]) is not None
            and (channel := self.guild.get_channel(channel_id)) is not None
            else None
        )
        embed: discord.Embed = discord.Embed(
            title=_("Configure {emoji} {event_name}").format(
                emoji=self.event["emoji"],
                event_name=self.event["name"],
            ),
            description=_("This event is currently **{state}**.\n**Logging Channel:** {channel}").format(
                state=_("enabled") if state else _("disabled"),
                channel=f"{channel.mention} (`{channel}`)" if channel is not None else _("None"),
            ),
        )
        self.toggle_event.label = _("Enable") if not state else _("Disable")
        self.toggle_event.style = discord.ButtonStyle.success if not state else discord.ButtonStyle.danger
        if channel is not None:
            self.channel_select.default_values = [channel]
        return embed

    async def on_timeout(self) -> None:
        try:
            await self._message.delete()
        except discord.HTTPException:
            pass

    @discord.ui.button(label="Toggle Event")
    async def toggle_event(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        config = await self.module.config_value(self.guild)()
        new_state = not config["events"][self.category][self.event["value"]]["enabled"]
        config["events"][self.category][self.event["value"]]["enabled"] = new_state
        await self.module.config_value(self.guild).set(config)
        await interaction.response.send_message(
            _("✅ {event_name} has been {state}.").format(
                event_name=self.event["name"],
                state=_("enabled") if new_state else _("disabled"),
            ),
            ephemeral=True,
        )
        await self._message.edit(
            embed=await self.get_embed(),
            view=self,
        )
        try:
            await self.category_view._message.edit(
                embed=await self.category_view.get_embed(),
                view=self.category_view,
            )
        except discord.HTTPException:
            pass
        await self.parent_view._message.edit(
            embed=await self.parent_view.get_embed(),
            view=self.parent_view,
        )

    @discord.ui.select(
        cls=discord.ui.ChannelSelect,
        channel_types=[discord.ChannelType.text],
        placeholder="Select a channel to log this event...",
    )
    async def channel_select(self, interaction: discord.Interaction, select: discord.ui.Select) -> None:
        config = await self.module.config_value(self.guild)()
        channel = select.values[0]
        config["events"][self.category][self.event["value"]]["channel"] = channel.id
        await self.module.config_value(self.guild).set(config)
        await interaction.response.send_message(
            _("✅ {event_name} events will now be logged in {channel.mention}.").format(
                event_name=self.event["name"],
                channel=channel,
            ),
            ephemeral=True,
        )
        await self._message.edit(
            embed=await self.get_embed(),
            view=self,
        )
        try:
            await self.category_view._message.edit(
                embed=await self.category_view.get_embed(),
                view=self.category_view,
            )
        except discord.HTTPException:
            pass
        await self.parent_view._message.edit(
            embed=await self.parent_view.get_embed(),
            view=self.parent_view,
        )

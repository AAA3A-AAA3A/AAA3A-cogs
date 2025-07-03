from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

from collections import defaultdict, deque
from io import BytesIO

import chat_exporter

from ..constants import Colors, Emojis, Levels, get_non_animated_asset
from ..views import ToggleModuleButton
from .module import Module

_: Translator = Translator("Security", __file__)


class UnauthorizedTextChannelDeletionsModule(Module):
    name = "Unauthorized Text Channel Deletions"
    emoji = Emojis.UNAUTHORIZED_TEXT_CHANNEL_DELETIONS.value
    description = (
        "Get the last messages from a text channel when it is deleted without authorization."
    )
    default_config = {
        "enabled": False,
        "cache_messages": False,
        "dm_extra_owners_and_higher": False,
        "specific_channels": [],
    }
    configurable_by_trusted_admins = False

    def __init__(self, cog: commands.Cog) -> None:
        super().__init__(cog)
        self.messages_cache: typing.Dict[
            discord.TextChannel, typing.List[discord.Message]
        ] = defaultdict(lambda: deque(maxlen=30))

    async def load(self) -> None:
        self.cog.bot.add_listener(self.on_audit_log_entry_create)
        self.cog.bot.add_listener(self.on_message)

    async def unload(self) -> None:
        self.cog.bot.remove_listener(self.on_audit_log_entry_create)
        self.cog.bot.remove_listener(self.on_message)

    async def get_status(
        self, guild: discord.Guild
    ) -> typing.Tuple[typing.Literal["✅", "⚠️", "❎"], str, str]:
        config = await self.config_value(guild)()
        if not config["enabled"]:
            return "❎", _("Disabled"), _("This module is currently disabled.")
        return (
            "✅",
            _("Enabled"),
            _("This module is enabled and monitoring unauthorized channel deletions."),
        )

    async def get_settings(
        self, guild: discord.Guild, view: discord.ui.View
    ) -> typing.Tuple[str, str, typing.List[typing.Dict], typing.List[discord.ui.Item]]:
        config = await self.config_value(guild)()
        title = _("Security — {emoji} {name} {status}").format(
            emoji=self.emoji, name=self.name, status=(await self.get_status(guild))[0]
        )
        description = _(
            "This module monitors unauthorized text channel deletions and retrieves the last messages from the deleted channel."
        )
        status = await self.get_status(guild)
        if status[0] == "⚠️":
            description += f"\n{status[0]} **{status[1]}**: {status[2]}\n"

        fields = [
            {
                "name": _("Enabled:"),
                "value": "✅" if config["enabled"] else "❌",
                "inline": True,
            },
            {
                "name": _("Cache Last Messages:"),
                "value": "✅" if config["cache_messages"] else "❌",
                "inline": True,
            },
            {
                "name": _("DM Extra Owners+ on Deletion:"),
                "value": "✅" if config["dm_extra_owners_and_higher"] else "❌",
                "inline": True,
            },
        ]

        components = [ToggleModuleButton(self, guild, view, config["enabled"])]

        cache_button: discord.ui.Button = discord.ui.Button(
            label=_("Cache Last Messages"),
            style=discord.ButtonStyle.success
            if config["cache_messages"]
            else discord.ButtonStyle.danger,
            emoji="💾",
        )

        async def cache_callback(interaction: discord.Interaction):
            await interaction.response.defer()
            config["cache_messages"] = not config["cache_messages"]
            await self.config_value(guild).cache_messages.set(config["cache_messages"])
            await view._message.edit(embed=await view.get_embed(), view=view)

        cache_button.callback = cache_callback
        components.append(cache_button)

        dm_button: discord.ui.Button = discord.ui.Button(
            label=_("DM Extra Owners and higher"),
            style=discord.ButtonStyle.success
            if config["dm_extra_owners_and_higher"]
            else discord.ButtonStyle.danger,
            emoji="📬",
        )

        async def dm_callback(interaction: discord.Interaction):
            await interaction.response.defer()
            config["dm_extra_owners_and_higher"] = not config["dm_extra_owners_and_higher"]
            await self.config_value(guild).dm_extra_owners_and_higher.set(
                config["dm_extra_owners_and_higher"]
            )
            await view._message.edit(embed=await view.get_embed(), view=view)

        dm_button.callback = dm_callback
        components.append(dm_button)

        specific_channels_select: discord.ui.ChannelSelect = discord.ui.ChannelSelect(
            placeholder=_("Select Specific Channels..."),
            channel_types=[discord.ChannelType.text],
            min_values=0,
            max_values=25,
            default_values=[
                channel
                for channel_id in config["specific_channels"]
                if (channel := guild.get_channel(channel_id)) is not None
            ],
        )

        async def specific_channels_callback(interaction: discord.Interaction):
            config["specific_channels"] = [
                channel.id for channel in specific_channels_select.values
            ]
            await self.config_value(guild).specific_channels.set(config["specific_channels"])
            await interaction.response.send_message(
                _("✅ Specific channels have been updated."),
                ephemeral=True,
            )
            await view._message.edit(embed=await view.get_embed(), view=view)

        specific_channels_select.callback = specific_channels_callback
        components.append(specific_channels_select)

        return title, description, fields, components

    async def on_audit_log_entry_create(self, entry: discord.AuditLogEntry) -> None:
        if entry.action != discord.AuditLogAction.channel_delete:
            return
        if entry.target is None or entry.before.type != discord.ChannelType.text:
            return
        responsible, channel = entry.user, entry.target
        config = await self.config_value(entry.guild)()
        if not config["enabled"]:
            return
        if config["specific_channels"] and channel.id not in config["specific_channels"]:
            return
        if (
            await self.cog.is_whitelisted(responsible, "unauthorized_text_channel_deletions")
            or await self.cog.is_whitelisted(
                discord.Object(id=channel.id, type=discord.TextChannel),
                "unauthorized_text_channel_deletions",
            )
        ):
            return
        messages = (
            self.messages_cache[channel]
            or sorted(
                [
                    message
                    for message in self.cog.bot.cached_messages
                    if message.channel.id == channel.id
                ],
                key=lambda m: m.created_at,
                reverse=True,
            )[:30]
        )

        embed = discord.Embed(
            title=_("Unauthorized Channel Deletion Detected {emoji}").format(emoji=self.emoji),
            color=Colors.UNAUTHORIZED_TEXT_CHANNEL_DELETIONS.value,
            timestamp=entry.created_at,
        )
        embed.set_author(
            name=responsible.display_name,
            icon_url=get_non_animated_asset(responsible.display_avatar),
        )
        embed.description = _(
            "🛡️ **Responsible:** {responsible.mention} (`{responsible}`) {responsible_emojis} - `{responsible.id}`\n"
            "#️⃣ **Target:** `{channel_name}` - `{channel.id}`"
        ).format(
            responsible=responsible,
            responsible_emojis=await self.cog.get_member_emojis(responsible),
            channel_name=entry.before.name,
            channel=channel,
        )
        embed.set_footer(text=entry.guild.name, icon_url=get_non_animated_asset(entry.guild.icon))
        if messages:
            embed.add_field(
                name="\u200b",
                value=_(
                    "You can find the last {count} message{s} in this channel in the transcript."
                ).format(count=len(messages), s="" if len(messages) == 1 else "s")
            )

            class Transcript(chat_exporter.construct.transcript.TranscriptDAO):
                @classmethod
                async def export(
                    cls,
                    channel: typing.Union[
                        discord.TextChannel, discord.VoiceChannel, discord.Thread
                    ],
                    messages: typing.List[discord.Message],
                    tz_info="UTC",
                    guild: typing.Optional[discord.Guild] = None,
                    bot: typing.Optional[discord.Client] = None,
                    military_time: typing.Optional[bool] = False,
                    fancy_times: typing.Optional[bool] = True,
                    support_dev: typing.Optional[bool] = True,
                    attachment_handler: typing.Optional[typing.Any] = None,
                ):
                    if guild:
                        channel.guild = guild
                    self = cls(
                        channel=channel,
                        limit=None,
                        messages=messages,
                        pytz_timezone=tz_info,
                        military_time=military_time,
                        fancy_times=fancy_times,
                        before=None,
                        after=None,
                        support_dev=support_dev,
                        bot=bot,
                        attachment_handler=attachment_handler,
                    )
                    if not self.after:
                        self.messages.reverse()
                    return (await self.build_transcript()).html

            transcript = await Transcript.export(
                channel=messages[-1].channel,
                messages=messages,
                tz_info="UTC",
                guild=entry.guild,
                bot=self.cog.bot,
            )
            file = discord.File(
                BytesIO(transcript.encode(encoding="utf-8")),
                filename=f"transcript-{channel.id}.html",
            )
        else:
            embed.add_field(
                name="\u200b",
                value=_("No recent messages found in this channel before deletion."),
            )
            file = None

        await self.cog.send_in_modlog_channel(
            entry.guild,
            embed=embed,
            file=file,
        )
        if config["dm_extra_owners_and_higher"]:
            extra_owners_and_higher = [entry.guild.owner] + [
                member
                for member_id, data in (await self.cog.config.all_members(entry.guild)).items()
                if data["level"] == Levels.EXTRA_OWNER.name
                and (member := entry.guild.get_member(member_id)) is not None
            ]
            for owner in extra_owners_and_higher:
                try:
                    await owner.send(embed=embed, file=file)
                except discord.HTTPException:
                    continue

    async def on_message(self, message: discord.Message) -> None:
        if (
            not message.guild
            or not message.channel
            or not isinstance(message.channel, discord.TextChannel)
        ):
            return
        config = await self.config_value(message.guild)()
        if not config["enabled"] or not config["cache_messages"]:
            return
        if config["specific_channels"] and message.channel.id not in config["specific_channels"]:
            return
        # if await self.cog.is_trusted_admin_or_higher(message.author):
        #     return
        self.messages_cache[message.channel].append(message)

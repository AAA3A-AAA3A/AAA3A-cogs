from AAA3A_utils import Cog, Loop, CogsUtils, Menu  # isort:skip
from redbot.core import commands, Config  # isort:skip
from redbot.core.bot import Red  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import asyncio
import datetime
import functools
import io
from collections import Counter
from copy import deepcopy
from pathlib import Path

from fontTools.ttLib import TTFont
from PIL import Image, ImageChops, ImageDraw, ImageFont
import plotly.graph_objects as go

from redbot.core.data_manager import bundled_data_path

from .view import GuildStatsView

# Credits:
# General repo credits.

_ = Translator("GuildStats", __file__)


class ObjectConverter(commands.Converter):
    async def convert(
        self, ctx: commands.Context, argument: str
    ) -> typing.Union[
        discord.Member,
        discord.Role,
        typing.Literal["messages", "voice", "activities"],
        discord.CategoryChannel,
        discord.TextChannel,
        discord.VoiceChannel,
    ]:
        if ctx.command.name == "graphic" and argument.lower() in {
            "messages",
            "voice",
            "activities",
        }:
            return argument.lower()
        try:
            return await commands.MemberConverter().convert(ctx, argument=argument)
        except commands.BadArgument:
            try:
                return await commands.RoleConverter().convert(ctx, argument=argument)
            except commands.BadArgument:
                try:
                    return await commands.CategoryChannelConverter().convert(
                        ctx, argument=argument
                    )
                except commands.BadArgument:
                    try:
                        return await commands.TextChannelConverter().convert(
                            ctx, argument=argument
                        )
                    except commands.BadArgument:
                        try:
                            return await commands.VoiceChannelConverter().convert(
                                ctx, argument=argument
                            )
                        except commands.BadArgument:
                            raise commands.BadArgument(
                                _("No member/category/text channel/voice channel found.")
                            )


@cog_i18n(_)
class GuildStats(Cog):
    """A cog to generate images with messages and voice stats, for members, roles, guilds, categories, text channels, voice channels and activities!"""

    def __init__(self, bot: Red) -> None:
        super().__init__(bot=bot)

        self.config: Config = Config.get_conf(
            self,
            identifier=205192943327321000143939875896557571750,
            force_registration=True,
        )
        self.guildstats_global: typing.Dict[str, typing.Union[int, bool, typing.List[int]]] = {
            "first_loading_time": None,
            "toggle_activities_stats": True,
            "default_state": True,
            "ignored_users": [],
        }
        self.guildstats_guild: typing.Dict[
            str, typing.Union[bool, typing.List[int], typing.List[str]]
        ] = {
            "enabled": None,
            "ignored_categories": [],
            "ignored_channels": [],
            "ignored_activities": [],
        }
        self.guildstats_channel: typing.Dict[
            str,
            typing.Union[
                int,
                typing.Dict[int, int],
                typing.Dict[int, typing.List[int]],
                typing.Dict[int, typing.List[typing.List[int]]],
            ],
        ] = {
            "total_messages": 0,
            "total_humans_messages": 0,
            "total_bots_messages": 0,
            "total_messages_members": {},
            "messages": {},
            "total_voice": 0,
            "total_humans_voice": 0,
            "total_bots_voice": 0,
            "total_voice_members": {},
            "voice": {},
        }
        self.guildstats_member: typing.Dict[
            str,
            typing.Union[
                int,
                typing.Dict[int, int],
                typing.Dict[int, typing.List[int]],
                typing.Dict[int, typing.List[typing.List[int]]],
            ],
        ] = {
            "total_activities": 0,
            "total_activities_times": {},
        }
        self.config.register_global(**self.guildstats_global)
        self.config.register_guild(**self.guildstats_guild)
        self.config.register_channel(**self.guildstats_channel)
        self.config.register_member(**self.guildstats_member)

        self.cache: typing.Dict[
            typing.Dict[
                discord.Guild,
                discord.abc.GuildChannel,
                typing.Dict[datetime.datetime, discord.Member],
            ]
        ] = {}

        self.font_path: Path = bundled_data_path(self) / "arial.ttf"
        self.bold_font_path: Path = bundled_data_path(self) / "arial_bold.ttf"
        self.font: typing.Dict[int, ImageFont.ImageFont] = {
            size: ImageFont.truetype(str(self.font_path), size=size)
            for size in {28, 30, 36, 40, 54}
        }
        self.bold_font: typing.Dict[int, ImageFont.ImageFont] = {
            size: ImageFont.truetype(str(self.bold_font_path), size=size)
            for size in {30, 36, 40, 50, 60}
        }
        self.font_to_remove_unprintable_characters: TTFont = TTFont(self.font_path)
        self.icons: typing.Dict[str, Path] = {
            name: (bundled_data_path(self) / f"{name}.png")
            for name in [
                "trophy",
                "#",
                "sound",
                "history",
                "person",
                "graphic",
                "query_stats",
                "game",
                "home",
                "globe",
            ]
        }

    async def cog_load(self) -> None:
        await super().cog_load()
        if await self.config.first_loading_time() is None:
            await self.config.first_loading_time.set(
                int(datetime.datetime.now(tz=datetime.timezone.utc).timestamp())
            )
        asyncio.create_task(self.load_data())
        self.loops.append(
            Loop(
                cog=self,
                name="Save GuildStats Data",
                function=self.save_to_config,
                minutes=1,
            )
        )

    @commands.Cog.listener(name="on_guild_join")
    async def load_data(self, guild: typing.Optional[discord.Guild] = None) -> None:
        if guild is not None:
            guilds = [guild]
        else:
            await self.bot.wait_until_red_ready()
            guilds = list(self.bot.guilds)
        for guild in guilds:
            for channel in guild.voice_channels:
                for member in channel.members:

                    class FakeVoiceState:
                        def __init__(self, channel: typing.Optional[discord.VoiceChannel]):
                            self.channel: typing.Optional[discord.VoiceChannel] = channel

                    await self.on_voice_state_update(
                        member=member,
                        before=FakeVoiceState(channel=None),
                        after=FakeVoiceState(channel=channel),
                    )
            for member in guild.members:
                if member.activities:
                    await self.on_presence_update(before=None, after=member)

    async def cog_unload(self) -> None:
        cache = self.cache.copy()
        for guild in cache:
            for channel in cache[guild]["channels"].copy():
                for member in cache[guild]["channels"][channel]["voice_cache"].copy():
                    if member not in channel.members:
                        continue

                    class FakeVoiceState:
                        def __init__(self, channel: typing.Optional[discord.VoiceChannel]):
                            self.channel: typing.Optional[discord.VoiceChannel] = channel

                    await self.on_voice_state_update(
                        member=member,
                        before=FakeVoiceState(channel=channel),
                        after=FakeVoiceState(channel=None),
                    )
            for member in cache[guild]["members"].copy():
                # if not member.activities:  # or member.activity.name != list(data["activities"])[-1]
                #     continue
                self.cache[member.guild]["members"][member]["activities_cache"] = {
                    activity_name: start_time
                    for activity_name, start_time in self.cache[member.guild]["members"][member][
                        "activities_cache"
                    ].items()
                    if discord.utils.get(member.activities, name=activity_name) is not None
                }
                if not self.cache[member.guild]["members"][member]["activities_cache"]:
                    continue
                await self.on_presence_update(before=member, after=None)
        asyncio.create_task(self.save_to_config())
        await super().cog_unload()

    async def red_delete_data_for_user(
        self,
        *,
        requester: typing.Literal["discord_deleted_user", "owner", "user", "user_strict"],
        user_id: int,
    ) -> None:
        """Delete all GuildStats data for user, members, roles, channels, categories, guilds; if the user ID matches."""
        if requester not in ["discord_deleted_user", "owner", "user", "user_strict"]:
            return
        await self.save_to_config()  # To clean up the cache too.

        # Channels.
        channel_group = self.config._get_base_group(self.config.CHANNEL)
        async with channel_group.all() as channels_data:
            for channel in channels_data:
                if str(user_id) in channels_data[channel]["total_messages_members"]:
                    del channels_data[channel]["total_messages_members"][str(user_id)]
                if str(user_id) in channels_data[channel]["messages"]:
                    del channels_data[channel]["messages"][str(user_id)]
                if str(user_id) in channels_data[channel]["total_voice_members"]:
                    del channels_data[channel]["total_voice_members"][str(user_id)]
                if str(user_id) in channels_data[channel]["voice"]:
                    del channels_data[channel]["voice"][str(user_id)]

        # Members.
        member_group = self.config._get_base_group(self.config.MEMBER)
        async with member_group.all() as members_data:
            for guild in members_data.copy():
                if str(user_id) in members_data[guild]:
                    del members_data[guild][str(user_id)]
                if not members_data[guild]:
                    del members_data[guild]

        # Global.
        global_data = await self.config.all()
        if user_id in global_data["ignored_users"]:
            global_data["ignored_users"].remove(user_id)
        await self.config.set(global_data)

    async def red_get_data_for_user(self, *, user_id: int) -> typing.Dict[str, io.BytesIO]:
        """Get all data about the user."""
        await self.save_to_config()  # To clean up the cache too.
        data = {
            Config.GLOBAL: {},
            Config.USER: {},
            Config.MEMBER: {},
            Config.ROLE: {},
            Config.CHANNEL: {},
            Config.GUILD: {},
        }

        # Channels.
        channel_group = self.config._get_base_group(self.config.CHANNEL)
        async with channel_group.all() as channels_data:
            for channel in channels_data:
                if str(user_id) in channels_data[channel]["total_messages_members"]:
                    if channel not in data[Config.CHANNEL]:
                        data[Config.CHANNEL][channel] = {}
                    data[Config.CHANNEL][channel]["total_messages_members"] = {
                        str(user_id): channels_data[channel]["total_messages_members"][
                            str(user_id)
                        ]
                    }
                if str(user_id) in channels_data[channel]["messages"]:
                    if channel not in data[Config.CHANNEL]:
                        data[Config.CHANNEL][channel] = {}
                    data[Config.CHANNEL][channel]["messages"] = {
                        str(user_id): channels_data[channel]["messages"][str(user_id)]
                    }
                if str(user_id) in channels_data[channel]["total_voice_members"]:
                    if channel not in data[Config.CHANNEL]:
                        data[Config.CHANNEL][channel] = {}
                    data[Config.CHANNEL][channel]["total_voice_members"] = {
                        str(user_id): channels_data[channel]["total_voice_members"][str(user_id)]
                    }
                if str(user_id) in channels_data[channel]["voice"]:
                    if channel not in data[Config.CHANNEL]:
                        data[Config.CHANNEL][channel] = {}
                    data[Config.CHANNEL][channel]["voice"] = {
                        str(user_id): channels_data[channel]["voice"][str(user_id)]
                    }

        # Members.
        member_group = self.config._get_base_group(self.config.MEMBER)
        async with member_group.all() as members_data:
            for guild in members_data:
                if str(user_id) in members_data[guild]:
                    data[Config.MEMBER][guild] = {str(user_id): members_data[guild][str(user_id)]}

        # Global.
        global_data = await self.config.all()
        if user_id in global_data["ignored_users"]:
            data[Config.GLOBAL]["ignored_users"] = [user_id]

        _data = deepcopy(data)
        for key, value in _data.items():
            if not value:
                del data[key]
        if not data:
            return {}
        file = io.BytesIO(str(data).encode(encoding="utf-8"))
        return {f"{self.qualified_name}.json": file}

    async def save_to_config(self) -> None:
        cache = self.cache.copy()

        # Keep some data in the cache.
        new_cache = {}
        for guild in cache:
            for channel, data in cache[guild]["channels"].items():
                if not data["voice_cache"]:
                    continue
                if guild not in new_cache:
                    new_cache[guild] = {"channels": {}, "members": {}}
                new_cache[guild]["channels"][channel] = {
                    "total_messages": 0,
                    "total_humans_messages": 0,
                    "total_bots_messages": 0,
                    "total_messages_members": {},
                    "messages": {},
                    "total_voice": 0,
                    "total_humans_voice": 0,
                    "total_bots_voice": 0,
                    "total_voice_members": {},
                    "voice": {},
                    "voice_cache": data["voice_cache"],
                }
            for member, data in cache[guild]["members"].items():
                if not data["activities_cache"]:
                    continue
                if guild not in new_cache:
                    new_cache[guild] = {"channels": {}, "members": {}}
                new_cache[guild]["members"][member] = {
                    "total_activities": 0,
                    "total_activities_times": {},
                    "activities_cache": data["activities_cache"],
                }
            self.cache = new_cache

        channel_group = self.config._get_base_group(self.config.CHANNEL)
        async with channel_group.all() as channels_data:
            for guild in cache:
                for channel, data in cache[guild]["channels"].items():
                    if str(channel.id) not in channels_data:
                        channels_data[str(channel.id)] = {
                            "total_messages": 0,
                            "total_humans_messages": 0,
                            "total_bots_messages": 0,
                            "total_messages_members": {},
                            "messages": {},
                            "total_voice": 0,
                            "total_humans_voice": 0,
                            "total_bots_voice": 0,
                            "total_voice_members": {},
                            "voice": {},
                        }
                    # Messages.
                    channels_data[str(channel.id)]["total_messages"] += data["total_messages"]
                    channels_data[str(channel.id)]["total_humans_messages"] += data[
                        "total_humans_messages"
                    ]
                    channels_data[str(channel.id)]["total_bots_messages"] += data[
                        "total_bots_messages"
                    ]
                    for member, count_messages in data["total_messages_members"].items():
                        if (
                            str(member.id)
                            not in channels_data[str(channel.id)]["total_messages_members"]
                        ):
                            channels_data[str(channel.id)]["total_messages_members"][
                                str(member.id)
                            ] = 0
                        channels_data[str(channel.id)]["total_messages_members"][
                            str(member.id)
                        ] += count_messages
                    for member, times in data["messages"].items():
                        if str(member.id) not in channels_data[str(channel.id)]["messages"]:
                            channels_data[str(channel.id)]["messages"][str(member.id)] = []
                        channels_data[str(channel.id)]["messages"][str(member.id)].extend(
                            [int(time.timestamp()) for time in times]
                        )
                    # Voice.
                    channels_data[str(channel.id)]["total_voice"] += data["total_voice"]
                    channels_data[str(channel.id)]["total_humans_voice"] += data[
                        "total_humans_voice"
                    ]
                    channels_data[str(channel.id)]["total_bots_voice"] += data["total_bots_voice"]
                    for member, count_voice in data["total_voice_members"].items():
                        if (
                            str(member.id)
                            not in channels_data[str(channel.id)]["total_voice_members"]
                        ):
                            channels_data[str(channel.id)]["total_voice_members"][
                                str(member.id)
                            ] = 0
                        channels_data[str(channel.id)]["total_voice_members"][
                            str(member.id)
                        ] += count_voice
        member_group = self.config._get_base_group(self.config.MEMBER)
        async with member_group.all() as members_data:
            for guild in cache:
                # Activities.
                for member, data in cache[guild]["members"].items():
                    if not data["total_activities"]:
                        continue
                    if str(guild.id) not in members_data:
                        members_data[str(guild.id)] = {}
                    if str(member.id) not in members_data[str(guild.id)]:
                        members_data[str(guild.id)][str(member.id)] = {
                            "total_activities": 0,
                            "total_activities_times": {},
                        }
                    members_data[str(guild.id)][str(member.id)]["total_activities"] += data[
                        "total_activities"
                    ]
                    for activity_name, count_time in data["total_activities_times"].items():
                        if (
                            activity_name
                            not in members_data[str(guild.id)][str(member.id)][
                                "total_activities_times"
                            ]
                        ):
                            members_data[str(guild.id)][str(member.id)]["total_activities_times"][
                                activity_name
                            ] = 0
                        members_data[str(guild.id)][str(member.id)]["total_activities_times"][
                            activity_name
                        ] += count_time
        await self.cleanup()

    async def cleanup(self, utc_now: datetime.datetime = None) -> None:
        if utc_now is None:
            utc_now = datetime.datetime.now(tz=datetime.timezone.utc)
        channel_group = self.config._get_base_group(self.config.CHANNEL)
        async with channel_group.all() as channels_data:
            for channel in channels_data:
                for member in channels_data[channel]["messages"]:
                    new_index = next(
                        (
                            i + 1
                            for i, time in enumerate(channels_data[channel]["messages"][member])
                            if time < (utc_now - datetime.timedelta(days=30)).timestamp()
                        ),
                        0,
                    )
                    channels_data[channel]["messages"][member] = channels_data[channel][
                        "messages"
                    ][member][new_index:]
                for member in channels_data[channel]["voice"]:
                    new_index = next(
                        (
                            i + 1
                            for i, times in enumerate(channels_data[channel]["voice"][member])
                            if times[1] < (utc_now - datetime.timedelta(days=30)).timestamp()
                        ),
                        0,
                    )
                    channels_data[channel]["voice"][member] = channels_data[channel]["voice"][
                        member
                    ][new_index:]

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.webhook_id is not None:
            return
        if message.guild is None:
            return
        if not isinstance(message.author, discord.Member):
            return
        if isinstance(message.channel, discord.Thread):
            return
        if (
            await self.bot.cog_disabled_in_guild(cog=self, guild=message.guild)
            or not await self.bot.allowed_by_whitelist_blacklist(who=message.author)
            or not (
                enabled_state
                if (enabled_state := await self.config.guild(message.guild).enabled()) is not None
                else await self.config.default_state()
            )
        ):
            return
        ignored_users = await self.config.ignored_users()
        if message.author.id in ignored_users:
            return
        if message.guild not in self.cache:
            self.cache[message.guild] = {"channels": {}, "members": {}}
        if message.channel not in self.cache[message.guild]["channels"]:
            self.cache[message.guild]["channels"][message.channel] = {
                "total_messages": 0,
                "total_humans_messages": 0,
                "total_bots_messages": 0,
                "total_messages_members": {},
                "messages": {},
                "total_voice": 0,
                "total_humans_voice": 0,
                "total_bots_voice": 0,
                "total_voice_members": {},
                "voice": {},
                "voice_cache": {},
            }
        self.cache[message.guild]["channels"][message.channel]["total_messages"] += 1
        if not message.author.bot:
            self.cache[message.guild]["channels"][message.channel]["total_humans_messages"] += 1
        else:
            self.cache[message.guild]["channels"][message.channel]["total_bots_messages"] += 1
        if (
            message.author
            not in self.cache[message.guild]["channels"][message.channel]["total_messages_members"]
        ):
            self.cache[message.guild]["channels"][message.channel]["total_messages_members"][
                message.author
            ] = 0
        self.cache[message.guild]["channels"][message.channel]["total_messages_members"][
            message.author
        ] += 1
        if (
            message.author
            not in self.cache[message.guild]["channels"][message.channel]["messages"]
        ):
            self.cache[message.guild]["channels"][message.channel]["messages"][message.author] = []
        self.cache[message.guild]["channels"][message.channel]["messages"][message.author].append(
            datetime.datetime.now(tz=datetime.timezone.utc)
        )

    @commands.Cog.listener()
    async def on_voice_state_update(
        self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState
    ) -> None:
        if not isinstance(member, discord.Member):
            return
        if (
            await self.bot.cog_disabled_in_guild(cog=self, guild=member.guild)
            or not await self.bot.allowed_by_whitelist_blacklist(who=member)
            or not (
                enabled_state
                if (enabled_state := await self.config.guild(member.guild).enabled()) is not None
                else await self.config.default_state()
            )
        ):
            return
        if after.channel == before.channel:
            return
        if after.channel is not None:
            if isinstance(after.channel, discord.StageChannel):
                return
            ignored_users = await self.config.ignored_users()
            if member.id in ignored_users:
                return
            if after.channel.guild not in self.cache:
                self.cache[after.channel.guild] = {"channels": {}, "members": {}}
            if after.channel not in self.cache[member.guild]["channels"]:
                self.cache[after.channel.guild]["channels"][after.channel] = {
                    "total_messages": 0,
                    "total_humans_messages": 0,
                    "total_bots_messages": 0,
                    "total_messages_members": {},
                    "messages": {},
                    "total_voice": 0,
                    "total_humans_voice": 0,
                    "total_bots_voice": 0,
                    "total_voice_members": {},
                    "voice": {},
                    "voice_cache": {},
                }
            self.cache[after.channel.guild]["channels"][after.channel]["voice_cache"][
                member
            ] = datetime.datetime.now(tz=datetime.timezone.utc)
        if before.channel is not None:
            if isinstance(after.channel, discord.StageChannel):
                return
            try:
                start_time = self.cache[before.channel.guild]["channels"][before.channel][
                    "voice_cache"
                ].pop(member)
            except KeyError:
                return
            ignored_users = await self.config.ignored_users()
            if member.id in ignored_users:
                return
            end_time = datetime.datetime.now(tz=datetime.timezone.utc)
            real_total_time = int((end_time - start_time).total_seconds())
            if round(real_total_time / 3600, 2) == 0:
                return
            self.cache[before.channel.guild]["channels"][before.channel][
                "total_voice"
            ] += real_total_time  # (min(members.values()) - start_time).total_seconds() if (members := {_member: _start_time for _member, _start_time in self.cache[before.channel.guild]["channels"][before.channel]["voice"].items() if _member != member}) and (min(members.values()) - start_time).total_seconds() >= 0 else real_total_time
            if not member.bot:
                self.cache[before.channel.guild]["channels"][before.channel][
                    "total_humans_voice"
                ] += real_total_time  # (min(members.values()) - start_time).total_seconds() if (members := {_member: _start_time for _member, _start_time in self.cache[before.channel.guild]["channels"][before.channel]["voice"].items() if _member != member and not _member.bot}) and (min(members.values()) - start_time).total_seconds() >= 0 else real_total_time
            else:
                self.cache[before.channel.guild]["channels"][before.channel][
                    "total_bots_voice"
                ] += real_total_time  # (min(members.values()) - start_time).total_seconds() if (members := {_member: _start_time for _member, _start_time in self.cache[before.channel.guild]["channels"][before.channel]["voice"].items() if _member != member and member.bot}) and (min(members.values()) - start_time).total_seconds() >= 0 else real_total_time
            if (
                member
                not in self.cache[before.channel.guild]["channels"][before.channel][
                    "total_voice_members"
                ]
            ):
                self.cache[before.channel.guild]["channels"][before.channel][
                    "total_voice_members"
                ][member] = 0
            self.cache[before.channel.guild]["channels"][before.channel]["total_voice_members"][
                member
            ] += real_total_time
            if member not in self.cache[before.channel.guild]["channels"][before.channel]["voice"]:
                self.cache[before.channel.guild]["channels"][before.channel]["voice"][member] = []
            self.cache[before.channel.guild]["channels"][before.channel]["voice"][member].append(
                [int(start_time.timestamp()), int(end_time.timestamp())]
            )

    @commands.Cog.listener()
    async def on_presence_update(
        self, before: typing.Optional[discord.Member], after: typing.Optional[discord.Member]
    ) -> None:
        if not await self.config.toggle_activities_stats():
            return
        if (
            await self.bot.cog_disabled_in_guild(cog=self, guild=(after or before).guild)
            or not await self.bot.allowed_by_whitelist_blacklist(who=(after or before))
            or not (
                enabled_state
                if (enabled_state := await self.config.guild((after or before).guild).enabled())
                is not None
                else await self.config.default_state()
            )
        ):
            return
        if after is not None and before is not None and after.activities == before.activities:
            return
        if after is not None:
            ignored_users = await self.config.ignored_users()
            if after.id in ignored_users:
                return
            for activity in after.activities:
                if activity.type == discord.ActivityType.custom or activity.name is None:
                    continue
                if after.guild not in self.cache:
                    self.cache[after.guild] = {"channels": {}, "members": {}}
                if after not in self.cache[after.guild]["members"]:
                    self.cache[after.guild]["members"][after] = {
                        "total_activities": 0,
                        "total_activities_times": {},
                        "activities_cache": {},
                    }
                self.cache[after.guild]["members"][after]["activities_cache"][
                    activity.name
                ] = datetime.datetime.now(tz=datetime.timezone.utc)
        if before is not None:
            ignored_users = await self.config.ignored_users()
            if before.id in ignored_users:
                return
            for activity in before.activities:
                if activity.type == discord.ActivityType.custom or activity.name is None:
                    continue
                if (
                    after is not None
                    and discord.utils.get(after.activities, name=activity.name) is not None
                ):
                    continue
                try:
                    start_time = self.cache[before.guild]["members"][before][
                        "activities_cache"
                    ].pop(activity.name)
                except KeyError:
                    return
                end_time = datetime.datetime.now(tz=datetime.timezone.utc)
                real_total_time = int((end_time - start_time).total_seconds())
                if real_total_time < 10 * 60:
                    return
                self.cache[before.guild]["members"][before]["total_activities"] += real_total_time
                if (
                    activity.name
                    not in self.cache[before.guild]["members"][before]["total_activities_times"]
                ):
                    self.cache[before.guild]["members"][before]["total_activities_times"][
                        activity.name
                    ] = 0
                self.cache[before.guild]["members"][before]["total_activities_times"][
                    activity.name
                ] += real_total_time

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, old_channel: discord.abc.GuildChannel) -> None:
        await self.config.channel(old_channel).clear()

    def _get_data(
        self,
        _object: typing.Union[
            discord.Member,
            discord.Role,
            discord.Guild,
            typing.Tuple[
                discord.Guild,
                typing.Union[
                    typing.Literal["messages", "voice", "activities"],
                    typing.Tuple[
                        typing.Literal["top"],
                        typing.Literal["messages", "voice"],
                        typing.Literal["members", "channels"],
                    ],
                    typing.Tuple[typing.Literal["activity"], str],
                ],
            ],
            discord.CategoryChannel,
            discord.TextChannel,
            discord.VoiceChannel,
        ],
        members_type: typing.Literal["humans", "bots", "both"],
        utc_now: datetime.datetime,
        all_channels_data: typing.Dict[int, dict],
        all_members_data: typing.Dict[int, dict],
        ignored_categories: typing.List[int],
        ignored_channels: typing.List[int],
        ignored_activities: typing.List[str],
    ) -> typing.Dict[str, typing.Any]:
        if isinstance(_object, typing.Tuple):
            _object, _type = _object
        else:
            _type = None
        if utc_now is None:
            utc_now = datetime.datetime.now(tz=datetime.timezone.utc)
        # Get cache data.
        all_channels_data = {
            channel_id: data
            for channel_id, data in all_channels_data.items()
            if (_object if isinstance(_object, discord.Guild) else _object.guild).get_channel(
                channel_id
            )
            is not None
        }
        for channel, data in self.cache.get(
            _object if isinstance(_object, discord.Guild) else _object.guild, {"channels": {}}
        )["channels"].items():
            if channel.id not in all_channels_data:
                all_channels_data[channel.id] = {
                    "total_messages": 0,
                    "total_humans_messages": 0,
                    "total_bots_messages": 0,
                    "total_messages_members": {},
                    "messages": {},
                    "total_humans_voice": 0,
                    "total_bots_voice": 0,
                    "total_voice": 0,
                    "total_voice_members": {},
                    "voice": {},
                }
            # Messages.
            all_channels_data[channel.id]["total_messages"] += data["total_messages"]
            all_channels_data[channel.id]["total_humans_messages"] += data["total_humans_messages"]
            all_channels_data[channel.id]["total_bots_messages"] += data["total_bots_messages"]
            for member, count_messages in data["total_messages_members"].items():
                if str(member.id) not in all_channels_data[channel.id]["total_messages_members"]:
                    all_channels_data[channel.id]["total_messages_members"][str(member.id)] = 0
                all_channels_data[channel.id]["total_messages_members"][
                    str(member.id)
                ] += count_messages
            for member, times in data["messages"].items():
                if str(member.id) not in all_channels_data[channel.id]["messages"]:
                    all_channels_data[channel.id]["messages"][str(member.id)] = []
                all_channels_data[channel.id]["messages"][str(member.id)].extend(
                    [time.timestamp() for time in times]
                )
            # Voice.
            all_channels_data[channel.id]["total_voice"] += data["total_voice"]
            all_channels_data[channel.id]["total_humans_voice"] += data["total_humans_voice"]
            all_channels_data[channel.id]["total_bots_voice"] += data["total_bots_voice"]
            for member, count_voice in data["total_voice_members"].items():
                if str(member.id) not in all_channels_data[channel.id]["total_voice_members"]:
                    all_channels_data[channel.id]["total_voice_members"][str(member.id)] = 0
                all_channels_data[channel.id]["total_voice_members"][str(member.id)] += count_voice
            # already_seen = []
            for member, start_time in data["voice_cache"].items():
                # already_seen.append(member)
                if member not in channel.members:
                    continue
                end_time = datetime.datetime.now(tz=datetime.timezone.utc)
                real_total_time = int((end_time - start_time).total_seconds())
                if round(real_total_time / 3600, 2) == 0:
                    continue
                all_channels_data[channel.id][
                    "total_voice"
                ] += real_total_time  # (min(members.values()) - start_time).total_seconds() if (members := {_member: _start_time for _member, _start_time in self.cache[channel.guild]["channels"][channel]["voice"].items() if _member not in already_seen}) and (min(members.values()) - start_time).total_seconds() >= 0 else real_total_time
                if not member.bot:
                    all_channels_data[channel.id][
                        "total_humans_voice"
                    ] += real_total_time  # (min(members.values()) - start_time).total_seconds() if (members := {_member: _start_time for _member, _start_time in self.cache[channel.guild]["channels"][channel]["voice"].items() if _member not in already_seen and not member.bot}) and (min(members.values()) - start_time).total_seconds() >= 0 else real_total_time
                else:
                    all_channels_data[channel.id][
                        "total_bots_voice"
                    ] += real_total_time  # (min(members.values()) - start_time).total_seconds() if (members := {_member: _start_time for _member, _start_time in self.cache[channel.guild]["channels"][channel]["voice"].items() if _member not in already_seen and member.bot}) and (min(members.values()) - start_time).total_seconds() >= 0 else real_total_time
                if str(member.id) not in all_channels_data[channel.id]["total_voice_members"]:
                    all_channels_data[channel.id]["total_voice_members"][str(member.id)] = 0
                all_channels_data[channel.id]["total_voice_members"][
                    str(member.id)
                ] += real_total_time
                if str(member.id) not in all_channels_data[channel.id]["voice"]:
                    all_channels_data[channel.id]["voice"][str(member.id)] = []
                all_channels_data[channel.id]["voice"][str(member.id)].append(
                    [int(start_time.timestamp()), int(end_time.timestamp())]
                )
        all_members_data = {
            member_id: data
            for member_id, data in all_members_data.items()
            if (_object if isinstance(_object, discord.Guild) else _object.guild).get_member(
                member_id
            )
            is not None
        }
        for member, data in self.cache.get(
            _object if isinstance(_object, discord.Guild) else _object.guild, {"members": {}}
        )["members"].items():
            if member.id not in all_members_data:
                all_members_data[member.id] = {"total_activities": 0, "total_activities_times": {}}
            for activity_name, start_time in data["activities_cache"].items():
                if discord.utils.get(member.activities, name=activity_name) is None:
                    continue
                end_time = datetime.datetime.now(tz=datetime.timezone.utc)
                real_total_time = int((end_time - start_time).total_seconds())
                if real_total_time < 10 * 60:
                    continue
                all_members_data[member.id]["total_activities"] += real_total_time
                if activity_name not in all_members_data[member.id]["total_activities_times"]:
                    all_members_data[member.id]["total_activities_times"][activity_name] = 0
                all_members_data[member.id]["total_activities_times"][
                    activity_name
                ] += real_total_time
        if not isinstance(_object, discord.CategoryChannel):
            for category_id in ignored_categories:
                if (
                    category := (
                        _object if isinstance(_object, discord.Guild) else _object.guild
                    ).get_channel(category_id)
                ) is not None:
                    for channel in category.channels:
                        if channel.id in all_channels_data:
                            del all_channels_data[channel.id]
        if not isinstance(_object, (discord.TextChannel, discord.VoiceChannel)):
            for channel_id in ignored_channels:
                if channel_id in all_channels_data:
                    del all_channels_data[channel_id]

        # Handle `members_type`.
        def is_valid(member_id: int):
            if members_type == "both":
                return True
            elif (
                member := (
                    _object if isinstance(_object, discord.Guild) else _object.guild
                ).get_member(member_id)
            ) is None:
                return True
            elif members_type == "humans" and not member.bot:
                return True
            elif members_type == "bots" and member.bot:
                return True
            else:
                return False

        members_type_key = "" if members_type == "both" else f"{members_type}_"

        if isinstance(_object, discord.Member):
            members_messages_counter: Counter = Counter(
                [
                    member_id
                    for channel_id in all_channels_data
                    for member_id, count_messages in all_channels_data[channel_id][
                        "total_messages_members"
                    ].items()
                    for __ in range(count_messages)
                    if (member := _object.guild.get_member(int(member_id))) is not None
                    and member.bot == _object.bot
                ]
            )
            members_messages_sorted: typing.List[int] = sorted(
                members_messages_counter,
                key=lambda x: (members_messages_counter[x], 1 if int(x) == _object.id else 0),
                reverse=True,
            )
            members_voice_counter: Counter = Counter(
                [
                    member_id
                    for channel_id in all_channels_data
                    for member_id, count_voice in all_channels_data[channel_id][
                        "total_voice_members"
                    ].items()
                    for __ in range(count_voice)
                    if (member := _object.guild.get_member(int(member_id))) is not None
                    and member.bot == _object.bot
                ]
            )
            members_voice_sorted: typing.List[int] = sorted(
                members_voice_counter,
                key=lambda x: (members_voice_counter[x], 1 if int(x) == _object.id else 0),
                reverse=True,
            )
            top_messages_channels = Counter(
                {
                    channel_id: all_channels_data[channel_id]["total_messages_members"].get(
                        str(_object.id), 0
                    )
                    for channel_id in all_channels_data
                    if _object.guild.get_channel(int(channel_id)) is not None
                }
            )
            top_voice_channels = Counter(
                {
                    channel_id: all_channels_data[channel_id]["total_voice_members"].get(
                        str(_object.id), 0
                    )
                    for channel_id in all_channels_data
                    if _object.guild.get_channel(int(channel_id)) is not None
                }
            )
            top_activities = Counter(
                {
                    activity_name: total_time
                    for activity_name, total_time in all_members_data.get(
                        _object.id, {"total_activities_times": {}}
                    )["total_activities_times"].items()
                    if activity_name not in ignored_activities
                }
            )
            return {
                "server_lookback": {  # type: messages/hours
                    "text": sum(
                        all_channels_data[channel_id]["total_messages_members"].get(
                            str(_object.id), 0
                        )
                        for channel_id in all_channels_data
                    ),
                    "voice": roundest_value
                    if (
                        roundest_value := round(
                            sum(
                                all_channels_data[channel_id]["total_voice_members"].get(
                                    str(_object.id), 0
                                )
                                for channel_id in all_channels_data
                            )
                            / 3600,
                            ndigits=2,
                        )
                    )
                    != 0
                    else 0,
                },
                "messages": {  # days: messages
                    delta: len(
                        [
                            time
                            for channel_id in all_channels_data
                            for time in all_channels_data[channel_id]["messages"].get(
                                str(_object.id), []
                            )
                            if time >= (utc_now - datetime.timedelta(days=delta)).timestamp()
                        ]
                    )
                    for delta in [1, 7, 30]
                },
                "voice_activity": {  # days: hours
                    delta: roundest_value
                    if (
                        roundest_value := round(
                            sum(
                                int(times[1] - times[0])
                                - int(
                                    to_remove
                                    if (
                                        to_remove := (
                                            utc_now - datetime.timedelta(days=delta)
                                        ).timestamp()
                                        - times[0]
                                    )
                                    > 0
                                    else 0
                                )
                                for channel_id in all_channels_data
                                for times in all_channels_data[channel_id]["voice"].get(
                                    str(_object.id), []
                                )
                                if times[1]
                                >= (utc_now - datetime.timedelta(days=delta)).timestamp()
                            )
                            / 3600,
                            ndigits=2,
                        )
                    )
                    != 0
                    else 0
                    for delta in [1, 7, 30]
                },
                "server_ranks": {  # type: rank #
                    "text": (members_messages_sorted.index(str(_object.id)) + 1)
                    if str(_object.id) in members_messages_sorted
                    else None,
                    "voice": (members_voice_sorted.index(str(_object.id)) + 1)
                    if str(_object.id) in members_voice_sorted
                    else None,
                },
                "top_channels_and_activity": {
                    "text": {  # type: {channel, messages}
                        "channel": top_messages_channels.most_common(1)[0][0]
                        if top_messages_channels and top_messages_channels.most_common(1)[0][1] > 0
                        else None,
                        "value": top_messages_channels.most_common(1)[0][1]
                        if top_messages_channels and top_messages_channels.most_common(1)[0][1] > 0
                        else None,
                    },
                    "voice": {  # type: {channel, hours}
                        "channel": top_voice_channels.most_common(1)[0][0]
                        if top_voice_channels and top_voice_channels.most_common(1)[0][1] > 0
                        else None,
                        "value": (
                            roundest_value
                            if (
                                roundest_value := round(
                                    top_voice_channels.most_common(1)[0][1] / 3600, ndigits=2
                                )
                            )
                            != int(roundest_value)
                            else int(roundest_value)
                        )
                        if top_voice_channels and top_voice_channels.most_common(1)[0][1] > 0
                        else None,
                    },
                    "activity": {  # type: {activity, hours}
                        "activity": top_activities.most_common(1)[0][0]
                        if top_activities and top_activities.most_common(1)[0][1] > 0
                        else None,
                        "value": (
                            roundest_value
                            if (
                                roundest_value := round(
                                    top_activities.most_common(1)[0][1] / 3600, ndigits=2
                                )
                            )
                            != int(roundest_value)
                            else int(roundest_value)
                        )
                        if top_activities and top_activities.most_common(1)[0][1] > 0
                        else None,
                    },
                },
                "graphic": {
                    "messages": {  # day: messages
                        day: len(
                            [
                                time
                                for channel_id in all_channels_data
                                for time in all_channels_data[channel_id]["messages"].get(
                                    str(_object.id), []
                                )
                                if (utc_now - datetime.timedelta(days=-day - 1)).timestamp()
                                >= time
                                >= (utc_now - datetime.timedelta(days=-day)).timestamp()
                            ]
                        )
                        for day in range(-30, 0)
                    },
                    "voice": {  # day: hours
                        day: roundest_value
                        if (
                            roundest_value := round(
                                sum(
                                    int(times[1] - times[0])
                                    - int(
                                        to_remove
                                        if (
                                            to_remove := (
                                                utc_now - datetime.timedelta(days=-day)
                                            ).timestamp()
                                            - times[0]
                                        )
                                        - int(
                                            to_remove
                                            if (
                                                to_remove := (
                                                    utc_now - datetime.timedelta(days=-day - 1)
                                                ).timestamp()
                                                - (utc_now.timestamp() - times[1])
                                            )
                                            > 0
                                            else 0
                                        )
                                        > 0
                                        else 0
                                    )
                                    for channel_id in all_channels_data
                                    for times in all_channels_data[channel_id]["voice"].get(
                                        str(_object.id), []
                                    )
                                    if (
                                        (utc_now - datetime.timedelta(days=-day - 1)).timestamp()
                                        >= times[0]
                                        >= (utc_now - datetime.timedelta(days=-day)).timestamp()
                                    )
                                    or ((utc_now - datetime.timedelta(days=-day)).timestamp())
                                    <= times[1]
                                    <= (utc_now - datetime.timedelta(days=-day - 1)).timestamp()
                                )
                                / 3600,
                                ndigits=2,
                            )
                        )
                        != 0
                        else 0
                        for day in range(-30, 0)
                    },
                },
            }

        elif isinstance(_object, discord.Role):
            roles_messages_counter: Counter = Counter(
                [
                    str(role.id)
                    for channel_id in all_channels_data
                    for member_id, count_messages in all_channels_data[channel_id][
                        "total_messages_members"
                    ].items()
                    for __ in range(count_messages)
                    for role in getattr(member, "roles", [])
                    if (member := _object.guild.get_member(int(member_id))) is not None
                    and is_valid(int(member_id))
                ]
            )  # and (role != _object.guild.default_role or role == _object)
            roles_messages_sorted: typing.List[int] = sorted(
                roles_messages_counter,
                key=lambda x: (roles_messages_counter[x], 1 if int(x) == _object.id else 0),
                reverse=True,
            )
            roles_voice_counter: Counter = Counter(
                [
                    str(role.id)
                    for channel_id in all_channels_data
                    for member_id, count_voice in all_channels_data[channel_id][
                        "total_voice_members"
                    ].items()
                    for __ in range(count_voice)
                    for role in getattr(member, "roles", [])
                    if _object.guild.get_member(int(member_id)) is not None
                    and is_valid(int(member_id))
                ]
            )  # and (role != _object.guild.default_role or role == _object)
            roles_voice_sorted: typing.List[int] = sorted(
                roles_voice_counter,
                key=lambda x: (roles_voice_counter[x], 1 if int(x) == _object.id else 0),
                reverse=True,
            )
            top_messages_channels = Counter(
                {
                    channel_id: sum(
                        all_channels_data[channel_id]["total_messages_members"].get(
                            str(member.id), 0
                        )
                        for member in _object.members
                        if is_valid(member.id)
                    )
                    for channel_id in all_channels_data
                    if _object.guild.get_channel(int(channel_id)) is not None
                }
            )
            top_voice_channels = Counter(
                {
                    channel_id: sum(
                        all_channels_data[channel_id]["total_voice_members"].get(str(member.id), 0)
                        for member in _object.members
                        if is_valid(member.id)
                    )
                    for channel_id in all_channels_data
                    if _object.guild.get_channel(int(channel_id)) is not None
                }
            )
            top_activities = Counter(
                [
                    activity_name
                    for member_id in all_members_data
                    for activity_name, count_time in all_members_data[member_id][
                        "total_activities_times"
                    ].items()
                    for __ in range(count_time)
                    if is_valid(member_id)
                ]
            )
            return {
                "server_lookback": {  # type: messages/hours
                    "text": sum(
                        all_channels_data[channel_id]["total_messages_members"].get(
                            str(member.id), 0
                        )
                        for channel_id in all_channels_data
                        for member in _object.members
                        if is_valid(member.id)
                    ),
                    "voice": roundest_value
                    if (
                        roundest_value := round(
                            sum(
                                all_channels_data[channel_id]["total_voice_members"].get(
                                    str(member.id), 0
                                )
                                for channel_id in all_channels_data
                                for member in _object.members
                                if is_valid(member.id)
                            )
                            / 3600,
                            ndigits=2,
                        )
                    )
                    != 0
                    else 0,
                },
                "messages": {  # days: messages
                    delta: len(
                        [
                            time
                            for channel_id in all_channels_data
                            for member in _object.members
                            for time in all_channels_data[channel_id]["messages"].get(
                                str(member.id), []
                            )
                            if is_valid(member.id)
                            and time >= (utc_now - datetime.timedelta(days=delta)).timestamp()
                        ]
                    )
                    for delta in [1, 7, 30]
                },
                "voice_activity": {  # days: hours
                    delta: roundest_value
                    if (
                        roundest_value := round(
                            sum(
                                int(times[1] - times[0])
                                - int(
                                    to_remove
                                    if (
                                        to_remove := (
                                            utc_now - datetime.timedelta(days=delta)
                                        ).timestamp()
                                        - times[0]
                                    )
                                    > 0
                                    else 0
                                )
                                for channel_id in all_channels_data
                                for member in _object.members
                                for times in all_channels_data[channel_id]["voice"].get(
                                    str(member.id), []
                                )
                                if is_valid(member.id)
                                and times[1]
                                >= (utc_now - datetime.timedelta(days=delta)).timestamp()
                            )
                            / 3600,
                            ndigits=2,
                        )
                    )
                    != 0
                    else 0
                    for delta in [1, 7, 30]
                },
                "server_ranks": {  # type: rank #
                    "text": (roles_messages_sorted.index(str(_object.id)) + 1)
                    if str(_object.id) in roles_messages_sorted
                    else None,
                    "voice": (roles_voice_sorted.index(str(_object.id)) + 1)
                    if str(_object.id) in roles_voice_sorted
                    else None,
                },
                "top_channels_and_activity": {
                    "text": {  # type: {channel, messages}
                        "channel": top_messages_channels.most_common(1)[0][0]
                        if top_messages_channels and top_messages_channels.most_common(1)[0][1] > 0
                        else None,
                        "value": top_messages_channels.most_common(1)[0][1]
                        if top_messages_channels and top_messages_channels.most_common(1)[0][1] > 0
                        else None,
                    },
                    "voice": {  # type: {channel, hours}
                        "channel": top_voice_channels.most_common(1)[0][0]
                        if top_voice_channels and top_voice_channels.most_common(1)[0][1] > 0
                        else None,
                        "value": (
                            roundest_value
                            if (
                                roundest_value := round(
                                    top_voice_channels.most_common(1)[0][1] / 3600, ndigits=2
                                )
                            )
                            != int(roundest_value)
                            else int(roundest_value)
                        )
                        if top_voice_channels and top_voice_channels.most_common(1)[0][1] > 0
                        else None,
                    },
                    "activity": {  # type: {activity, hours}
                        "activity": top_activities.most_common(1)[0][0]
                        if top_activities and top_activities.most_common(1)[0][1] > 0
                        else None,
                        "value": (
                            roundest_value
                            if (
                                roundest_value := round(
                                    top_activities.most_common(1)[0][1] / 3600, ndigits=2
                                )
                            )
                            != int(roundest_value)
                            else int(roundest_value)
                        )
                        if top_activities and top_activities.most_common(1)[0][1] > 0
                        else None,
                    },
                },
                "graphic": {
                    "messages": {  # day: messages
                        day: len(
                            [
                                time
                                for channel_id in all_channels_data
                                for member in _object.members
                                for time in all_channels_data[channel_id]["messages"].get(
                                    str(member.id), []
                                )
                                if is_valid(member.id)
                                and (utc_now - datetime.timedelta(days=-day - 1)).timestamp()
                                >= time
                                >= (utc_now - datetime.timedelta(days=-day)).timestamp()
                            ]
                        )
                        for day in range(-30, 0)
                    },
                    "voice": {  # day: hours
                        day: roundest_value
                        if (
                            roundest_value := round(
                                sum(
                                    int(times[1] - times[0])
                                    - int(
                                        to_remove
                                        if (
                                            to_remove := (
                                                utc_now - datetime.timedelta(days=-day)
                                            ).timestamp()
                                            - times[0]
                                        )
                                        - int(
                                            to_remove
                                            if (
                                                to_remove := (
                                                    utc_now - datetime.timedelta(days=-day - 1)
                                                ).timestamp()
                                                - (utc_now.timestamp() - times[1])
                                            )
                                            > 0
                                            else 0
                                        )
                                        > 0
                                        else 0
                                    )
                                    for channel_id in all_channels_data
                                    for member in _object.members
                                    for times in all_channels_data[channel_id]["voice"].get(
                                        str(member.id), []
                                    )
                                    if is_valid(member.id)
                                    and (
                                        (utc_now - datetime.timedelta(days=-day - 1)).timestamp()
                                        >= times[0]
                                        >= (utc_now - datetime.timedelta(days=-day)).timestamp()
                                    )
                                    or ((utc_now - datetime.timedelta(days=-day)).timestamp())
                                    <= times[1]
                                    <= (utc_now - datetime.timedelta(days=-day - 1)).timestamp()
                                )
                                / 3600,
                                ndigits=2,
                            )
                        )
                        != 0
                        else 0
                        for day in range(-30, 0)
                    },
                },
            }

        elif isinstance(_object, discord.Guild):
            members_messages_counter: Counter = Counter(
                [
                    member_id
                    for channel_id in all_channels_data
                    for member_id, count_messages in all_channels_data[channel_id][
                        "total_messages_members"
                    ].items()
                    for __ in range(count_messages)
                    if _object.get_member(int(member_id)) is not None and is_valid(int(member_id))
                ]
            )
            members_voice_counter: Counter = Counter(
                [
                    member_id
                    for channel_id in all_channels_data
                    for member_id, count_voice in all_channels_data[channel_id][
                        "total_voice_members"
                    ].items()
                    for __ in range(count_voice)
                    if _object.get_member(int(member_id)) is not None and is_valid(int(member_id))
                ]
            )
            top_messages_channels = Counter(
                {
                    channel_id: all_channels_data[channel_id][f"total_{members_type_key}messages"]
                    for channel_id in all_channels_data
                    if _object.get_channel(int(channel_id)) is not None
                }
            )
            top_voice_channels = Counter(
                {
                    channel_id: all_channels_data[channel_id][f"total_{members_type_key}voice"]
                    for channel_id in all_channels_data
                    if _object.get_channel(int(channel_id)) is not None
                }
            )
            if _type is None:
                return {
                    "server_lookback": {  # type: messages/hours
                        "text": sum(
                            all_channels_data[channel_id][f"total_{members_type_key}messages"]
                            for channel_id in all_channels_data
                        ),
                        "voice": roundest_value
                        if (
                            roundest_value := round(
                                sum(
                                    all_channels_data[channel_id][f"total_{members_type_key}voice"]
                                    for channel_id in all_channels_data
                                )
                                / 3600,
                                ndigits=2,
                            )
                        )
                        != 0
                        else 0,
                    },
                    "messages": {  # days: messages
                        delta: len(
                            [
                                time
                                for channel_id in all_channels_data
                                for member_id in all_channels_data[channel_id]["messages"]
                                for time in all_channels_data[channel_id]["messages"][member_id]
                                if time >= (utc_now - datetime.timedelta(days=delta)).timestamp()
                                and is_valid(int(member_id))
                            ]
                        )
                        for delta in [1, 7, 30]
                    },
                    "voice_activity": {  # days: hours
                        delta: roundest_value
                        if (
                            roundest_value := round(
                                sum(
                                    int(times[1] - times[0])
                                    - int(
                                        to_remove
                                        if (
                                            to_remove := (
                                                utc_now - datetime.timedelta(days=delta)
                                            ).timestamp()
                                            - times[0]
                                        )
                                        > 0
                                        else 0
                                    )
                                    for channel_id in all_channels_data
                                    for member_id in all_channels_data[channel_id]["voice"]
                                    for times in all_channels_data[channel_id]["voice"][member_id]
                                    if times[1]
                                    >= (utc_now - datetime.timedelta(days=delta)).timestamp()
                                    and is_valid(int(member_id))
                                )
                                / 3600,
                                ndigits=2,
                            )
                        )
                        != 0
                        else 0
                        for delta in [1, 7, 30]
                    },
                    "top_members": {  # type: (member, messages/hours)
                        "text": {
                            "member": int(members_messages_counter.most_common(1)[0][0])
                            if members_messages_counter
                            and members_messages_counter.most_common(1)[0][1] > 0
                            else None,
                            "value": members_messages_counter.most_common(1)[0][1]
                            if members_messages_counter
                            and members_messages_counter.most_common(1)[0][1] > 0
                            else None,
                        },
                        "voice": {
                            "member": int(members_voice_counter.most_common(1)[0][0])
                            if members_voice_counter
                            and members_voice_counter.most_common(1)[0][1] > 0
                            else None,
                            "value": (
                                roundest_value
                                if (
                                    roundest_value := round(
                                        members_voice_counter.most_common(1)[0][1] / 3600,
                                        ndigits=2,
                                    )
                                )
                                != 0
                                else 0
                            )
                            if members_voice_counter
                            and members_voice_counter.most_common(1)[0][1] > 0
                            else None,
                        },
                    },
                    "top_channels": {  # type: (channel, messages/hours)
                        "text": {
                            "channel": int(top_messages_channels.most_common(1)[0][0])
                            if top_messages_channels
                            and top_messages_channels.most_common(1)[0][1] > 0
                            else None,
                            "value": top_messages_channels.most_common(1)[0][1]
                            if top_messages_channels
                            and top_messages_channels.most_common(1)[0][1] > 0
                            else None,
                        },
                        "voice": {
                            "channel": int(top_voice_channels.most_common(1)[0][0])
                            if top_voice_channels and top_voice_channels.most_common(1)[0][1] > 0
                            else None,
                            "value": (
                                roundest_value
                                if (
                                    roundest_value := round(
                                        top_voice_channels.most_common(1)[0][1] / 3600, ndigits=2
                                    )
                                )
                                != 0
                                else 0
                            )
                            if top_voice_channels and top_voice_channels.most_common(1)[0][1] > 0
                            else None,
                        },
                    },
                    "graphic": {
                        "messages": {  # day: messages
                            day: len(
                                [
                                    time
                                    for channel_id in all_channels_data
                                    for member_id in all_channels_data[channel_id]["messages"]
                                    for time in all_channels_data[channel_id]["messages"][
                                        member_id
                                    ]
                                    if (utc_now - datetime.timedelta(days=-day - 1)).timestamp()
                                    >= time
                                    >= (utc_now - datetime.timedelta(days=-day)).timestamp()
                                    and is_valid(int(member_id))
                                ]
                            )
                            for day in range(-30, 0)
                        },
                        "voice": {  # day: hours
                            day: roundest_value
                            if (
                                roundest_value := round(
                                    sum(
                                        int(times[1] - times[0])
                                        - int(
                                            to_remove
                                            if (
                                                to_remove := (
                                                    utc_now - datetime.timedelta(days=-day)
                                                ).timestamp()
                                                - times[0]
                                            )
                                            - int(
                                                to_remove
                                                if (
                                                    to_remove := (
                                                        utc_now - datetime.timedelta(days=-day - 1)
                                                    ).timestamp()
                                                    - (utc_now.timestamp() - times[1])
                                                )
                                                > 0
                                                else 0
                                            )
                                            > 0
                                            else 0
                                        )
                                        for channel_id in all_channels_data
                                        for member_id in all_channels_data[channel_id]["voice"]
                                        for times in all_channels_data[channel_id]["voice"][
                                            member_id
                                        ]
                                        if (
                                            (
                                                utc_now - datetime.timedelta(days=-day - 1)
                                            ).timestamp()
                                            >= times[0]
                                            >= (
                                                utc_now - datetime.timedelta(days=-day)
                                            ).timestamp()
                                        )
                                        or ((utc_now - datetime.timedelta(days=-day)).timestamp())
                                        <= times[1]
                                        <= (
                                            utc_now - datetime.timedelta(days=-day - 1)
                                        ).timestamp()
                                        and is_valid(int(member_id))
                                    )
                                    / 3600,
                                    ndigits=2,
                                )
                            )
                            != 0
                            else 0
                            for day in range(-30, 0)
                        },
                    },
                }
            elif _type == "messages":
                return {
                    "server_lookback": sum(
                        all_channels_data[channel_id][f"total_{members_type_key}messages"]
                        for channel_id in all_channels_data
                    ),  # messages
                    "messages": {  # days: messages
                        delta: len(
                            [
                                time
                                for channel_id in all_channels_data
                                for member_id in all_channels_data[channel_id]["messages"]
                                for time in all_channels_data[channel_id]["messages"][member_id]
                                if time >= (utc_now - datetime.timedelta(days=delta)).timestamp()
                                and is_valid(int(member_id))
                            ]
                        )
                        for delta in [1, 7, 30]
                    },
                    "contributors": {  # days: members
                        delta: len(
                            {
                                member_id
                                for channel_id in all_channels_data
                                for member_id, times in all_channels_data[channel_id][
                                    "messages"
                                ].items()
                                for time in times
                                if time >= (utc_now - datetime.timedelta(days=delta)).timestamp()
                                and is_valid(int(member_id))
                            }
                        )
                        for delta in [1, 7, 30]
                    },
                    "top_messages_members": {  # member: messages
                        int(member_id): count_messages
                        for (member_id, count_messages) in members_messages_counter.most_common(3)
                        if count_messages > 0
                    },
                    "top_messages_channels": {  # channel: messages
                        int(channel_id): count_messages
                        for (channel_id, count_messages) in top_messages_channels.most_common(3)
                        if count_messages > 0
                    },
                    "graphic": {
                        "messages": {  # day: messages
                            day: len(
                                [
                                    time
                                    for channel_id in all_channels_data
                                    for member_id in all_channels_data[channel_id]["messages"]
                                    for time in all_channels_data[channel_id]["messages"][
                                        member_id
                                    ]
                                    if (utc_now - datetime.timedelta(days=-day - 1)).timestamp()
                                    >= time
                                    >= (utc_now - datetime.timedelta(days=-day)).timestamp()
                                    and is_valid(int(member_id))
                                ]
                            )
                            for day in range(-30, 0)
                        },
                        "contributors": {  # day: contributors
                            day: len(
                                set(
                                    member_id
                                    for channel_id in all_channels_data
                                    for member_id, times in all_channels_data[channel_id][
                                        "messages"
                                    ].items()
                                    for time in times
                                    if (utc_now - datetime.timedelta(days=-day - 1)).timestamp()
                                    >= time
                                    >= (utc_now - datetime.timedelta(days=-day)).timestamp()
                                    and is_valid(int(member_id))
                                )
                            )
                            for day in range(-30, 0)
                        },
                    },
                }
            elif _type == "voice":
                return {
                    "server_lookback": roundest_value
                    if (
                        roundest_value := round(
                            sum(
                                all_channels_data[channel_id][f"total_{members_type_key}voice"]
                                for channel_id in all_channels_data
                            )
                            / 3600,
                            ndigits=2,
                        )
                    )
                    != 0
                    else 0,  # hours
                    "voice_activity": {  # days: hours
                        delta: roundest_value
                        if (
                            roundest_value := round(
                                sum(
                                    int(times[1] - times[0])
                                    - int(
                                        to_remove
                                        if (
                                            to_remove := (
                                                utc_now - datetime.timedelta(days=delta)
                                            ).timestamp()
                                            - times[0]
                                        )
                                        > 0
                                        else 0
                                    )
                                    for channel_id in all_channels_data
                                    for member_id in all_channels_data[channel_id]["voice"]
                                    for times in all_channels_data[channel_id]["voice"][member_id]
                                    if times[1]
                                    >= (utc_now - datetime.timedelta(days=delta)).timestamp()
                                    and is_valid(int(member_id))
                                )
                                / 3600,
                                ndigits=2,
                            )
                        )
                        != 0
                        else 0
                        for delta in [1, 7, 30]
                    },
                    "contributors": {  # days: hours
                        delta: len(
                            {
                                member_id
                                for channel_id in all_channels_data
                                for member_id in all_channels_data[channel_id]["voice"]
                                for times in all_channels_data[channel_id]["voice"][member_id]
                                if times[1]
                                >= (utc_now - datetime.timedelta(days=delta)).timestamp()
                                and is_valid(int(member_id))
                            }
                        )
                        for delta in [1, 7, 30]
                    },
                    "top_voice_members": {  # member: messages
                        int(member_id): (
                            roundest_value
                            if (roundest_value := round(count_voice / 3600, ndigits=2)) != 0
                            else 0
                        )
                        for (member_id, count_voice) in members_voice_counter.most_common(3)
                        if count_voice > 0
                    },
                    "top_voice_channels": {  # channel: messages
                        int(channel_id): (
                            roundest_value
                            if (roundest_value := round(count_voice / 3600, ndigits=2)) != 0
                            else 0
                        )
                        for (channel_id, count_voice) in top_voice_channels.most_common(3)
                        if count_voice > 0
                    },
                    "graphic": {
                        "voice": {  # day: hours
                            day: roundest_value
                            if (
                                roundest_value := round(
                                    sum(
                                        int(times[1] - times[0])
                                        - int(
                                            to_remove
                                            if (
                                                to_remove := (
                                                    utc_now - datetime.timedelta(days=-day)
                                                ).timestamp()
                                                - times[0]
                                            )
                                            - int(
                                                to_remove
                                                if (
                                                    to_remove := (
                                                        utc_now - datetime.timedelta(days=-day - 1)
                                                    ).timestamp()
                                                    - (utc_now.timestamp() - times[1])
                                                )
                                                > 0
                                                else 0
                                            )
                                            > 0
                                            else 0
                                        )
                                        for channel_id in all_channels_data
                                        for member_id in all_channels_data[channel_id]["voice"]
                                        for times in all_channels_data[channel_id]["voice"][
                                            member_id
                                        ]
                                        if (
                                            (
                                                utc_now - datetime.timedelta(days=-day - 1)
                                            ).timestamp()
                                            >= times[0]
                                            >= (
                                                utc_now - datetime.timedelta(days=-day)
                                            ).timestamp()
                                        )
                                        or ((utc_now - datetime.timedelta(days=-day)).timestamp())
                                        <= times[1]
                                        <= (
                                            utc_now - datetime.timedelta(days=-day - 1)
                                        ).timestamp()
                                        and is_valid(int(member_id))
                                    )
                                    / 3600,
                                    ndigits=2,
                                )
                            )
                            != 0
                            else 0
                            for day in range(-30, 0)
                        },
                        "contributors": {  # day: contributors
                            day: len(
                                set(
                                    member_id
                                    for channel_id in all_channels_data
                                    for member_id in all_channels_data[channel_id]["voice"]
                                    for times in all_channels_data[channel_id]["voice"][member_id]
                                    if (
                                        (utc_now - datetime.timedelta(days=-day - 1)).timestamp()
                                        >= times[0]
                                        >= (utc_now - datetime.timedelta(days=-day)).timestamp()
                                    )
                                    or ((utc_now - datetime.timedelta(days=-day)).timestamp())
                                    <= times[1]
                                    <= (utc_now - datetime.timedelta(days=-day - 1)).timestamp()
                                    and is_valid(int(member_id))
                                )
                            )
                            for day in range(-30, 0)
                        },
                    },
                }
            elif _type == "activities":
                activities_counter: Counter = Counter(
                    [
                        activity_name
                        for member_id in all_members_data
                        for activity_name, count_time in all_members_data[member_id][
                            "total_activities_times"
                        ].items()
                        for __ in range(count_time)
                        if activity_name not in ignored_activities and is_valid(int(member_id))
                    ]
                )
                return {
                    "top_activities": {  # activity_name: hours
                        activity_name: (
                            roundest_value
                            if (roundest_value := round(count_time / 3600, ndigits=2)) != 0
                            else 0
                        )
                        for (activity_name, count_time) in activities_counter.most_common(10)
                        if count_time > 0
                    },
                    "graphic": {
                        "activities": {  # activity_name: hours
                            activity_name: (
                                roundest_value
                                if (roundest_value := round(count_time / 3600, ndigits=2)) != 0
                                else 0
                            )
                            for (activity_name, count_time) in activities_counter.most_common(10)
                            if count_time > 0
                        },
                    },
                }
            elif isinstance(_type, typing.Tuple):
                if _type[0] == "top":
                    members_messages_counter: Counter = Counter(
                        [
                            member_id
                            for channel_id in all_channels_data
                            for member_id, count_messages in all_channels_data[channel_id][
                                "total_messages_members"
                            ].items()
                            for __ in range(count_messages)
                            if _object.get_member(int(member_id)) is not None
                            and is_valid(int(member_id))
                        ]
                    )
                    members_voice_counter: Counter = Counter(
                        [
                            member_id
                            for channel_id in all_channels_data
                            for member_id, count_voice in all_channels_data[channel_id][
                                "total_voice_members"
                            ].items()
                            for __ in range(count_voice)
                            if _object.get_member(int(member_id)) is not None
                            and is_valid(int(member_id))
                        ]
                    )
                    top_messages_channels = Counter(
                        {
                            channel_id: all_channels_data[channel_id][
                                f"total_{members_type_key}messages"
                            ]
                            for channel_id in all_channels_data
                            if _object.get_channel(int(channel_id)) is not None
                        }
                    )
                    top_voice_channels = Counter(
                        {
                            channel_id: all_channels_data[channel_id][
                                f"total_{members_type_key}voice"
                            ]
                            for channel_id in all_channels_data
                            if _object.get_channel(int(channel_id)) is not None
                        }
                    )
                    if _type[1] == "messages":
                        if _type[2] == "members":
                            counter_to_use = members_messages_counter
                        else:
                            counter_to_use = top_messages_channels
                    else:
                        if _type[2] == "members":
                            counter_to_use = members_voice_counter
                        else:
                            counter_to_use = top_voice_channels
                    return {
                        f"top_{_type[1]}_{_type[2]}": {  # member/channel: messages/hours
                            int(member_or_channel_id): (
                                count_messages_or_voice
                                if _type[1] == "messages"
                                else (
                                    roundest_value
                                    if (
                                        roundest_value := round(
                                            count_messages_or_voice / 3600, ndigits=2
                                        )
                                    )
                                    != 0
                                    else 0
                                )
                            )
                            for (
                                member_or_channel_id,
                                count_messages_or_voice,
                            ) in counter_to_use.most_common(10)
                            if count_messages_or_voice > 0
                        },
                        "graphic": {
                            f"top_{_type[1]}_{_type[2]}": {  # member/channel: messages/hours
                                int(member_or_channel_id): (
                                    count_messages_or_voice
                                    if _type[1] == "messages"
                                    else (
                                        roundest_value
                                        if (
                                            roundest_value := round(
                                                count_messages_or_voice / 3600, ndigits=2
                                            )
                                        )
                                        != 0
                                        else 0
                                    )
                                )
                                for (
                                    member_or_channel_id,
                                    count_messages_or_voice,
                                ) in counter_to_use.most_common(10)
                                if count_messages_or_voice > 0
                            },
                        },
                    }
                elif _type[0] == "activity":
                    activity_members_counter: Counter = Counter(
                        [
                            member_id
                            for member_id in all_members_data
                            for __ in range(
                                all_members_data[member_id]["total_activities_times"].get(
                                    _type[1], 0
                                )
                            )
                            if _object.get_member(int(member_id)) is not None
                            and is_valid(int(member_id))
                        ]
                    )
                    return {
                        "top_members": {  # activity_name: hours
                            member_id: (
                                roundest_value
                                if (roundest_value := round(count_time / 3600, ndigits=2)) != 0
                                else 0
                            )
                            for (member_id, count_time) in activity_members_counter.most_common(10)
                            if count_time > 0
                        },
                        "graphic": {
                            "top_members": {  # activity_name: hours
                                member_id: (
                                    roundest_value
                                    if (roundest_value := round(count_time / 3600, ndigits=2)) != 0
                                    else 0
                                )
                                for (
                                    member_id,
                                    count_time,
                                ) in activity_members_counter.most_common(10)
                                if count_time > 0
                            },
                        },
                    }

        elif isinstance(_object, discord.CategoryChannel):
            members_messages_counter: Counter = Counter(
                [
                    member_id
                    for channel_id in [
                        channel.id
                        for channel in _object.channels
                        if channel.id in all_channels_data
                    ]
                    for member_id, count_messages in all_channels_data[channel_id][
                        "total_messages_members"
                    ].items()
                    for __ in range(count_messages)
                    if _object.guild.get_member(int(member_id)) is not None
                    and is_valid(int(member_id))
                ]
            )
            members_voice_counter: Counter = Counter(
                [
                    member_id
                    for channel_id in [
                        channel.id
                        for channel in _object.channels
                        if channel.id in all_channels_data
                    ]
                    for member_id, count_voice in all_channels_data[channel_id][
                        "total_voice_members"
                    ].items()
                    for __ in range(count_voice)
                    if _object.guild.get_member(int(member_id)) is not None
                    and is_valid(int(member_id))
                ]
            )
            top_messages_channels = Counter(
                {
                    channel_id: all_channels_data[channel_id][f"total_{members_type_key}messages"]
                    for channel_id in [
                        channel.id
                        for channel in _object.channels
                        if channel.id in all_channels_data
                    ]
                    if _object.guild.get_channel(int(channel_id)) is not None
                }
            )
            top_voice_channels = Counter(
                {
                    channel_id: all_channels_data[channel_id][f"total_{members_type_key}voice"]
                    for channel_id in [
                        channel.id
                        for channel in _object.channels
                        if channel.id in all_channels_data
                    ]
                    if _object.guild.get_channel(int(channel_id)) is not None
                }
            )
            return {
                "server_lookback": {  # type: messages/hours
                    "text": sum(
                        all_channels_data[channel_id][f"total_{members_type_key}messages"]
                        for channel_id in [
                            channel.id
                            for channel in _object.channels
                            if channel.id in all_channels_data
                        ]
                    ),
                    "voice": roundest_value
                    if (
                        roundest_value := round(
                            sum(
                                all_channels_data[channel_id][f"total_{members_type_key}voice"]
                                for channel_id in [
                                    channel.id
                                    for channel in _object.channels
                                    if channel.id in all_channels_data
                                ]
                            )
                            / 3600,
                            ndigits=2,
                        )
                    )
                    != 0
                    else 0,
                },
                "messages": {  # days: messages
                    delta: len(
                        [
                            time
                            for channel_id in [
                                channel.id
                                for channel in _object.channels
                                if channel.id in all_channels_data
                            ]
                            for member_id in all_channels_data[channel_id]["messages"]
                            for time in all_channels_data[channel_id]["messages"][member_id]
                            if time >= (utc_now - datetime.timedelta(days=delta)).timestamp()
                            and is_valid(int(member_id))
                        ]
                    )
                    for delta in [1, 7, 30]
                },
                "voice_activity": {  # days: hours
                    delta: roundest_value
                    if (
                        roundest_value := round(
                            sum(
                                int(times[1] - times[0])
                                - int(
                                    to_remove
                                    if (
                                        to_remove := (
                                            utc_now - datetime.timedelta(days=delta)
                                        ).timestamp()
                                        - times[0]
                                    )
                                    > 0
                                    else 0
                                )
                                for channel_id in [
                                    channel.id
                                    for channel in _object.channels
                                    if channel.id in all_channels_data
                                ]
                                for member_id in all_channels_data[channel_id]["voice"]
                                for times in all_channels_data[channel_id]["voice"][member_id]
                                if times[1]
                                >= (utc_now - datetime.timedelta(days=delta)).timestamp()
                                and is_valid(int(member_id))
                            )
                            / 3600,
                            ndigits=2,
                        )
                    )
                    != 0
                    else 0
                    for delta in [1, 7, 30]
                },
                "top_members": {  # type: (member, messages/hours)
                    "text": {
                        "member": int(members_messages_counter.most_common(1)[0][0])
                        if members_messages_counter
                        and members_messages_counter.most_common(1)[0][1] > 0
                        else None,
                        "value": members_messages_counter.most_common(1)[0][1]
                        if members_messages_counter
                        and members_messages_counter.most_common(1)[0][1] > 0
                        else None,
                    },
                    "voice": {
                        "member": int(members_voice_counter.most_common(1)[0][0])
                        if members_voice_counter and members_voice_counter.most_common(1)[0][1] > 0
                        else None,
                        "value": (
                            roundest_value
                            if (
                                roundest_value := round(
                                    members_voice_counter.most_common(1)[0][1] / 3600, ndigits=2
                                )
                            )
                            != 0
                            else 0
                        )
                        if members_voice_counter and members_voice_counter.most_common(1)[0][1] > 0
                        else None,
                    },
                },
                "top_channels": {  # type: (channel, messages/hours)
                    "text": {
                        "channel": int(top_messages_channels.most_common(1)[0][0])
                        if top_messages_channels and top_messages_channels.most_common(1)[0][1] > 0
                        else None,
                        "value": top_messages_channels.most_common(1)[0][1]
                        if top_messages_channels and top_messages_channels.most_common(1)[0][1] > 0
                        else None,
                    },
                    "voice": {
                        "channel": int(top_voice_channels.most_common(1)[0][0])
                        if top_voice_channels and top_voice_channels.most_common(1)[0][1] > 0
                        else None,
                        "value": (
                            roundest_value
                            if (
                                roundest_value := round(
                                    top_voice_channels.most_common(1)[0][1] / 3600, ndigits=2
                                )
                            )
                            != 0
                            else 0
                        )
                        if top_voice_channels and top_voice_channels.most_common(1)[0][1] > 0
                        else None,
                    },
                },
                "graphic": {
                    "messages": {  # day: messages
                        day: len(
                            [
                                time
                                for channel_id in [
                                    channel.id
                                    for channel in _object.channels
                                    if channel.id in all_channels_data
                                ]
                                for member_id in all_channels_data[channel_id]["messages"]
                                for time in all_channels_data[channel_id]["messages"][member_id]
                                if (utc_now - datetime.timedelta(days=-day - 1)).timestamp()
                                >= time
                                >= (utc_now - datetime.timedelta(days=-day)).timestamp()
                                and is_valid(int(member_id))
                            ]
                        )
                        for day in range(-30, 0)
                    },
                    "voice": {  # day: hours
                        day: roundest_value
                        if (
                            roundest_value := round(
                                sum(
                                    int(times[1] - times[0])
                                    - int(
                                        to_remove
                                        if (
                                            to_remove := (
                                                utc_now - datetime.timedelta(days=-day)
                                            ).timestamp()
                                            - times[0]
                                        )
                                        - int(
                                            to_remove
                                            if (
                                                to_remove := (
                                                    utc_now - datetime.timedelta(days=-day - 1)
                                                ).timestamp()
                                                - (utc_now.timestamp() - times[1])
                                            )
                                            > 0
                                            else 0
                                        )
                                        > 0
                                        else 0
                                    )
                                    for channel_id in [
                                        channel.id
                                        for channel in _object.channels
                                        if channel.id in all_channels_data
                                    ]
                                    for member_id in all_channels_data[channel_id]["voice"]
                                    for times in all_channels_data[channel_id]["voice"][member_id]
                                    if (
                                        (utc_now - datetime.timedelta(days=-day - 1)).timestamp()
                                        >= times[0]
                                        >= (utc_now - datetime.timedelta(days=-day)).timestamp()
                                    )
                                    or ((utc_now - datetime.timedelta(days=-day)).timestamp())
                                    <= times[1]
                                    <= (utc_now - datetime.timedelta(days=-day - 1)).timestamp()
                                    and is_valid(int(member_id))
                                )
                                / 3600,
                                ndigits=2,
                            )
                        )
                        != 0
                        else 0
                        for day in range(-30, 0)
                    },
                },
            }

        elif isinstance(_object, discord.TextChannel):
            members_messages_counter: Counter = Counter(
                [
                    member_id
                    for member_id, count_messages in all_channels_data[_object.id][
                        "total_messages_members"
                    ].items()
                    for __ in range(count_messages)
                    if _object.guild.get_member(int(member_id)) is not None
                    and is_valid(int(member_id))
                ]
                if _object.id in all_channels_data
                else []
            )
            top_messages_channels = Counter(
                {
                    channel_id: all_channels_data[channel_id][f"total_{members_type_key}messages"]
                    for channel_id in all_channels_data
                    if _object.guild.get_channel(int(channel_id)) is not None
                }
            )
            top_messages_channels_sorted: typing.List[int] = sorted(
                top_messages_channels,
                key=lambda x: (top_messages_channels[x], 1 if int(x) == _object.id else 0),
                reverse=True,
            )
            return {
                "server_lookback": all_channels_data[_object.id][
                    f"total_{members_type_key}messages"
                ]
                if _object.id in all_channels_data
                else 0,  # messages
                "messages": {  # days: messages
                    delta: (
                        len(
                            [
                                time
                                for member_id in all_channels_data[_object.id]["messages"]
                                for time in all_channels_data[_object.id]["messages"][member_id]
                                if time >= (utc_now - datetime.timedelta(days=delta)).timestamp()
                                and is_valid(int(member_id))
                            ]
                        )
                        if _object.id in all_channels_data
                        else 0
                    )
                    for delta in [1, 7, 30]
                },
                "contributors": {  # days: members
                    delta: (
                        len(
                            {
                                member_id
                                for member_id, times in all_channels_data[_object.id][
                                    "messages"
                                ].items()
                                for time in times
                                if time >= (utc_now - datetime.timedelta(days=delta)).timestamp()
                                and is_valid(int(member_id))
                            }
                        )
                        if _object.id in all_channels_data
                        else 0
                    )
                    for delta in [1, 7, 30]
                },
                "server_rank": (top_messages_channels_sorted.index(_object.id) + 1)
                if _object.id in top_messages_channels_sorted
                and all_channels_data[_object.id][f"total_{members_type_key}messages"] > 0
                else None,  # rank #
                "top_messages_members": {  # member: messages
                    int(member_id): count_messages
                    for (member_id, count_messages) in members_messages_counter.most_common(3)
                },
                "graphic": {
                    "messages": {  # day: messages
                        day: (
                            len(
                                [
                                    time
                                    for member_id in all_channels_data[_object.id]["messages"]
                                    for time in all_channels_data[_object.id]["messages"][
                                        member_id
                                    ]
                                    if (utc_now - datetime.timedelta(days=-day - 1)).timestamp()
                                    >= time
                                    >= (utc_now - datetime.timedelta(days=-day)).timestamp()
                                    and is_valid(int(member_id))
                                ]
                            )
                            if _object.id in all_channels_data
                            else 0
                        )
                        for day in range(-30, 0)
                    },
                    "contributors": {  # day: contributors
                        day: (
                            len(
                                set(
                                    member_id
                                    for member_id, times in all_channels_data[_object.id][
                                        "messages"
                                    ].items()
                                    for time in times
                                    if (utc_now - datetime.timedelta(days=-day - 1)).timestamp()
                                    >= time
                                    >= (utc_now - datetime.timedelta(days=-day)).timestamp()
                                    and is_valid(int(member_id))
                                )
                            )
                            if _object.id in all_channels_data
                            else 0
                        )
                        for day in range(-30, 0)
                    },
                },
            }

        elif isinstance(_object, discord.VoiceChannel):
            members_voice_counter: Counter = Counter(
                [
                    member_id
                    for member_id, count_voice in all_channels_data[_object.id][
                        "total_voice_members"
                    ].items()
                    for __ in range(count_voice)
                    if _object.guild.get_member(int(member_id)) is not None
                    and is_valid(int(member_id))
                ]
                if _object.id in all_channels_data
                else []
            )
            top_voice_channels = Counter(
                {
                    channel_id: all_channels_data[channel_id][f"total_{members_type_key}voice"]
                    for channel_id in all_channels_data
                    if _object.guild.get_channel(int(channel_id)) is not None
                }
            )
            top_voice_channels_sorted: typing.List[int] = sorted(
                top_voice_channels,
                key=lambda x: (top_voice_channels[x], 1 if int(x) == _object.id else 0),
                reverse=True,
            )
            return {
                "server_lookback": (
                    roundest_value
                    if (
                        roundest_value := round(
                            all_channels_data[_object.id][f"total_{members_type_key}voice"] / 3600,
                            ndigits=2,
                        )
                    )
                    != int(roundest_value)
                    else int(roundest_value)
                )
                if _object.id in all_channels_data
                else 0,  # hours
                "voice_activity": {  # days: hours
                    delta: (
                        (
                            roundest_value
                            if (
                                roundest_value := round(
                                    sum(
                                        int(times[1] - times[0])
                                        - int(
                                            to_remove
                                            if (
                                                to_remove := (
                                                    utc_now - datetime.timedelta(days=delta)
                                                ).timestamp()
                                                - times[0]
                                            )
                                            > 0
                                            else 0
                                        )
                                        for member_id in all_channels_data[_object.id]["voice"]
                                        for times in all_channels_data[_object.id]["voice"][
                                            member_id
                                        ]
                                        if times[1]
                                        >= (utc_now - datetime.timedelta(days=delta)).timestamp()
                                        and is_valid(int(member_id))
                                    )
                                    / 3600,
                                    ndigits=2,
                                )
                            )
                            != 0
                            else 0
                        )
                        if _object.id in all_channels_data
                        else 0
                    )
                    for delta in [1, 7, 30]
                },
                "contributors": {  # days: hours
                    delta: (
                        len(
                            {
                                member_id
                                for member_id in all_channels_data[_object.id]["voice"]
                                for times in all_channels_data[_object.id]["voice"][member_id]
                                if times[1]
                                >= (utc_now - datetime.timedelta(days=delta)).timestamp()
                                and is_valid(int(member_id))
                            }
                        )
                        if _object.id in all_channels_data
                        else 0
                    )
                    for delta in [1, 7, 30]
                },
                "server_rank": (top_voice_channels_sorted.index(_object.id) + 1)
                if _object.id in top_voice_channels_sorted
                and all_channels_data[_object.id][f"total_{members_type_key}voice"] > 0
                else None,  # rank #
                "top_voice_members": {  # member: hours
                    int(member_id): (
                        roundest_value
                        if (roundest_value := round(count_voice / 3600, ndigits=2)) != 0
                        else 0
                    )
                    for (member_id, count_voice) in members_voice_counter.most_common(3)
                },
                "graphic": {
                    "voice": {  # day: hours
                        day: (
                            (
                                roundest_value
                                if (
                                    roundest_value := round(
                                        sum(
                                            int(times[1] - times[0])
                                            - int(
                                                to_remove
                                                if (
                                                    to_remove := (
                                                        utc_now - datetime.timedelta(days=-day)
                                                    ).timestamp()
                                                    - times[0]
                                                )
                                                - int(
                                                    to_remove
                                                    if (
                                                        to_remove := (
                                                            utc_now
                                                            - datetime.timedelta(days=-day - 1)
                                                        ).timestamp()
                                                        - (utc_now.timestamp() - times[1])
                                                    )
                                                    > 0
                                                    else 0
                                                )
                                                > 0
                                                else 0
                                            )
                                            for member_id in all_channels_data[_object.id]["voice"]
                                            for times in all_channels_data[_object.id]["voice"][
                                                member_id
                                            ]
                                            if (
                                                (
                                                    utc_now - datetime.timedelta(days=-day - 1)
                                                ).timestamp()
                                                >= times[0]
                                                >= (
                                                    utc_now - datetime.timedelta(days=-day)
                                                ).timestamp()
                                            )
                                            or (
                                                (
                                                    utc_now - datetime.timedelta(days=-day)
                                                ).timestamp()
                                            )
                                            <= times[1]
                                            <= (
                                                utc_now - datetime.timedelta(days=-day - 1)
                                            ).timestamp()
                                            and is_valid(int(member_id))
                                        )
                                        / 3600,
                                        ndigits=2,
                                    )
                                )
                                != 0
                                else 0
                            )
                            if _object.id in all_channels_data
                            else 0
                        )
                        for day in range(-30, 0)
                    },
                    "contributors": {  # day: contributors
                        day: (
                            len(
                                set(
                                    member_id
                                    for member_id in all_channels_data[_object.id]["voice"]
                                    for times in all_channels_data[_object.id]["voice"][member_id]
                                    if (
                                        (utc_now - datetime.timedelta(days=-day - 1)).timestamp()
                                        >= times[0]
                                        >= (utc_now - datetime.timedelta(days=-day)).timestamp()
                                    )
                                    or ((utc_now - datetime.timedelta(days=-day)).timestamp())
                                    <= times[1]
                                    <= (utc_now - datetime.timedelta(days=-day - 1)).timestamp()
                                    and is_valid(int(member_id))
                                )
                            )
                            if _object.id in all_channels_data
                            else 0
                        )
                        for day in range(-30, 0)
                    },
                },
            }

    async def get_data(
        self,
        _object: typing.Union[
            discord.Member,
            discord.Role,
            discord.Guild,
            typing.Tuple[
                discord.Guild,
                typing.Union[
                    typing.Literal["messages", "voice", "activities"],
                    typing.Tuple[
                        typing.Literal["top"],
                        typing.Literal["messages", "voice"],
                        typing.Literal["members", "channels"],
                    ],
                    typing.Tuple[typing.Literal["activity"], str],
                ],
            ],
            discord.CategoryChannel,
            discord.TextChannel,
            discord.VoiceChannel,
        ],
        members_type: typing.Literal["humans", "bots", "both"] = "humans",
        utc_now: datetime.datetime = None,
    ) -> typing.Dict[str, typing.Any]:
        if isinstance(_object, typing.Tuple):
            _object, _type = _object
        else:
            _type = None
        return await asyncio.to_thread(
            self._get_data,
            _object=_object if _type is None else (_object, _type),
            members_type=members_type,
            utc_now=utc_now,
            all_channels_data=await self.config.all_channels(),
            all_members_data=await self.config.all_members(
                guild=(_object if isinstance(_object, discord.Guild) else _object.guild)
            ),
            ignored_categories=await self.config.guild(
                _object if isinstance(_object, discord.Guild) else _object.guild
            ).ignored_categories(),
            ignored_channels=await self.config.guild(
                _object if isinstance(_object, discord.Guild) else _object.guild
            ).ignored_channels(),
            ignored_activities=await self.config.guild(
                _object if isinstance(_object, discord.Guild) else _object.guild
            ).ignored_activities(),
        )

    def align_text_center(
        self,
        draw: ImageDraw.Draw,
        xy: typing.Tuple[int, int, int, int],
        text: str,
        fill: typing.Optional[typing.Tuple[int, int, int, typing.Optional[int]]],
        font: ImageFont.ImageFont,
    ) -> typing.Tuple[int, int]:
        x1, y1, x2, y2 = xy
        text_size = font.getbbox(text)
        x = int((x2 - x1 - text_size[2]) / 2)
        x = max(x, 0)
        y = int((y2 - y1 - text_size[3]) / 2)
        y = max(y, 0)
        if font in self.bold_font.values():
            y -= 5
        draw.text((x1 + x, y1 + y), text=text, fill=fill, font=font)
        return text_size

    def number_to_text_with_suffix(self, number: float) -> str:
        suffixes = ["k", "m", "b", "t", "q", "Q", "s", "S", "o", "n", "d", "U", "D", "T", "Qa", "Qi", "Sx", "Sp", "Oc", "No", "Vi"]  # ["k", "M", "B", "T", "P", "E", "Z", "Y"]
        index = None
        while abs(number) >= 1000 and (index or -1) < len(suffixes) - 1:
            number /= 1000.0
            if index is None:
                index = -1
            index += 1
        # return f"{int(number) if number == int(number) else (f'{number:.1f}' if f'{number:.1f}' != '0.0' else (f'{number:.2f}' if f'{number:.2f}' != '0.0' else '0'))}{suffixes[index]}"
        return f"{int(number) if number == int(number) else ((int(float(f'{number:.1f}')) if float(f'{number:.1f}') == int(float(f'{number:.1f}')) else f'{number:.1f}') if f'{number:.1f}' != '0.0' else ((int(float(f'{number:.2f}')) if float(f'{number:.2f}') == int(float(f'{number:.2f}')) else f'{number:.2f}') if f'{number:.2f}' != '0.0' else '0'))}{suffixes[index] if index is not None else ''}"

    def remove_unprintable_characters(self, text: str) -> str:
        return (
            "".join(
                [
                    char
                    for char in text
                    if ord(char) in self.font_to_remove_unprintable_characters.getBestCmap()
                    and char.isascii()
                ]
            )
            .strip()
            .strip("-|_")
            .strip()
        )

    def get_member_display(self, member: discord.Member) -> str:
        return (
            self.remove_unprintable_characters(member.display_name)
            if (
                sum(
                    1
                    if ord(char) in self.font_to_remove_unprintable_characters.getBestCmap()
                    else 0
                    for char in member.display_name
                )
                / len(member.display_name)
                > 0.8
            )
            and len(self.remove_unprintable_characters(member.display_name)) >= 5
            else (
                self.remove_unprintable_characters(member.global_name)
                if member.global_name is not None
                and (
                    sum(
                        1
                        if ord(char) in self.font_to_remove_unprintable_characters.getBestCmap()
                        else 0
                        for char in member.global_name
                    )
                    / len(member.global_name)
                    > 0.8
                )
                and len(self.remove_unprintable_characters(member.global_name)) >= 5
                else member.name
            )
        )

    def _generate_prefix_image(
        self,
        _object: typing.Union[
            discord.Member,
            discord.Role,
            discord.Guild,
            typing.Tuple[
                discord.Guild,
                typing.Union[
                    typing.Literal["messages", "voice", "activities"],
                    typing.Tuple[
                        typing.Literal["top"],
                        typing.Literal["messages", "voice"],
                        typing.Literal["members", "channels"],
                    ],
                    typing.Tuple[typing.Literal["activity"], str],
                ],
            ],
            discord.CategoryChannel,
            discord.TextChannel,
            discord.VoiceChannel,
        ],
        size: typing.Tuple[int, int],
        to_file: bool,
        _object_display: typing.Optional[bytes],
        guild_icon: typing.Optional[bytes],
    ) -> typing.Union[Image.Image, discord.File]:
        if isinstance(_object, typing.Tuple):
            _object, _type = _object
        else:
            _type = None
        img: Image.Image = Image.new("RGBA", size, (0, 0, 0, 0))
        draw: ImageDraw.ImageDraw = ImageDraw.Draw(img)
        align_text_center = functools.partial(self.align_text_center, draw)
        draw.rounded_rectangle((0, 0, img.width, img.height), radius=50, fill=(32, 34, 37))

        # Member/Channel name & Member avatar.
        if isinstance(_object, discord.Member):
            image = Image.open(io.BytesIO(_object_display))
            image = image.resize((140, 140))
            mask = Image.new("L", image.size, 0)
            d = ImageDraw.Draw(mask)
            d.rounded_rectangle(
                (0, 0, image.width, image.height),
                radius=20,
                fill=255,
            )
            # d.ellipse((0, 0, image.width, image.height), fill=255)
            try:
                img.paste(
                    image, (30, 30, 170, 170), mask=ImageChops.multiply(mask, image.split()[3])
                )
            except IndexError:
                img.paste(image, (30, 30, 170, 170), mask=mask)
            if (
                sum(
                    1
                    if ord(char) in self.font_to_remove_unprintable_characters.getBestCmap()
                    else 0
                    for char in _object.display_name
                )
                / len(_object.display_name)
                > 0.8
            ) and len(self.remove_unprintable_characters(_object.display_name)) >= 5:
                draw.text(
                    (190, 30),
                    text=self.remove_unprintable_characters(_object.display_name),
                    fill=(255, 255, 255),
                    font=self.bold_font[50],
                )
                display_name_size = self.bold_font[50].getbbox(_object.display_name)
                if (
                    display_name_size[2]
                    + 25
                    + self.font[40].getbbox(_object.global_name or _object.name)[2]
                ) <= 1000:
                    draw.text(
                        (190 + display_name_size[2] + 25, 48),
                        text=self.remove_unprintable_characters(_object.global_name)
                        if _object.global_name is not None
                        else _object.name,
                        fill=(163, 163, 163),
                        font=self.font[40],
                    )
            elif (
                _object.global_name is not None
                and (
                    sum(
                        1
                        if ord(char) in self.font_to_remove_unprintable_characters.getBestCmap()
                        else 0
                        for char in _object.global_name
                    )
                    / len(_object.global_name)
                    > 0.8
                )
                and len(self.remove_unprintable_characters(_object.global_name)) >= 5
            ):
                draw.text(
                    (190, 30),
                    text=self.remove_unprintable_characters(_object.global_name),
                    fill=(255, 255, 255),
                    font=self.bold_font[50],
                )
            else:
                draw.text(
                    (190, 30), text=_object.name, fill=(255, 255, 255), font=self.bold_font[50]
                )
        elif isinstance(_object, discord.Role):
            if _object.display_icon is not None:
                image = Image.open(io.BytesIO(_object_display))
                image = image.resize((140, 140))
                mask = Image.new("L", image.size, 0)
                d = ImageDraw.Draw(mask)
                d.rounded_rectangle(
                    (0, 0, image.width, image.height),
                    radius=25,
                    fill=255,
                )
                try:
                    img.paste(
                        image, (30, 30, 170, 170), mask=ImageChops.multiply(mask, image.split()[3])
                    )
                except IndexError:
                    img.paste(image, (30, 30, 170, 170), mask=mask)
            else:
                image = Image.open(self.icons["person"])
                image = image.resize((140, 140))
                img.paste(image, (30, 30, 170, 170), mask=image.split()[3])
            draw.text(
                (190, 30),
                _("Role {_object.name}").format(_object=_object),
                fill=(255, 255, 255),
                font=self.bold_font[50],
            )
        elif isinstance(_object, discord.Guild):
            if _type is None:
                draw.text(
                    (190, 30), text=_("Guild Stats"), fill=(255, 255, 255), font=self.bold_font[50]
                )
                image = Image.open(
                    self.icons[
                        "home"
                        if "DISCOVERABLE"
                        not in (
                            _object if isinstance(_object, discord.Guild) else _object.guild
                        ).features
                        else "globe"
                    ]
                )
            elif _type == "messages":
                draw.text(
                    (190, 30),
                    text=_("Messages Stats"),
                    fill=(255, 255, 255),
                    font=self.bold_font[50],
                )
                image = Image.open(self.icons["#"])
            elif _type == "voice":
                draw.text(
                    (190, 30), text=_("Voice Stats"), fill=(255, 255, 255), font=self.bold_font[50]
                )
                image = Image.open(self.icons["sound"])
            elif _type == "activities":
                draw.text(
                    (190, 30),
                    text=_("Activities Stats"),
                    fill=(255, 255, 255),
                    font=self.bold_font[50],
                )
                image = Image.open(self.icons["game"])
            elif isinstance(_type, typing.Tuple):
                if _type[0] == "top":
                    draw.text(
                        (190, 30),
                        text=_("Top Stats"),
                        fill=(255, 255, 255),
                        font=self.bold_font[50],
                    )
                    image = Image.open(self.icons["#" if _type[1] == "messages" else "sound"])
                elif _type[0] == "activity":
                    draw.text(
                        (190, 30),
                        text=_("Activity - {activity_name}").format(
                            activity_name=self.remove_unprintable_characters(_type[1])
                        ),
                        fill=(255, 255, 255),
                        font=self.bold_font[50],
                    )
                    image = Image.open(self.icons["game"])
            image = image.resize((140, 140))
            img.paste(image, (30, 30, 170, 170), mask=image.split()[3])
        elif isinstance(_object, discord.CategoryChannel):
            draw.text(
                (190, 30),
                _("Category - {_object.name}").format(_object=_object),
                fill=(255, 255, 255),
                font=self.bold_font[50],
            )
            image = Image.open(self.icons["#"])
            image = image.resize((140, 140))
            img.paste(image, (30, 30, 170, 170), mask=image.split()[3])
        elif isinstance(_object, discord.TextChannel):
            draw.text(
                (190, 30),
                self.remove_unprintable_characters(_object.name),
                fill=(255, 255, 255),
                font=self.bold_font[50],
            )
            image = Image.open(self.icons["#"])
            image = image.resize((140, 140))
            img.paste(image, (30, 30, 170, 170), mask=image.split()[3])
        elif isinstance(_object, discord.VoiceChannel):
            draw.text(
                (190, 30),
                self.remove_unprintable_characters(_object.name),
                fill=(255, 255, 255),
                font=self.bold_font[50],
            )
            image = Image.open(self.icons["sound"])
            image = image.resize((140, 140))
            img.paste(image, (30, 30, 170, 170), mask=image.split()[3])

        # Guild name & Guild icon.
        if guild_icon is not None:
            image = Image.open(io.BytesIO(guild_icon))
            image = image.resize((55, 55))
            mask = Image.new("L", image.size, 0)
            d = ImageDraw.Draw(mask)
            d.rounded_rectangle(
                (0, 0, image.width, image.height),
                radius=25,
                fill=255,
            )
            try:
                img.paste(
                    image, (190, 105, 245, 160), mask=ImageChops.multiply(mask, image.split()[3])
                )
            except IndexError:
                img.paste(image, (190, 105, 245, 160), mask=mask)
            draw.text(
                (265, 105),
                text=(_object if isinstance(_object, discord.Guild) else _object.guild).name,
                fill=(163, 163, 163),
                font=self.font[54],
            )
        else:
            image = Image.open(
                self.icons[
                    "home"
                    if "DISCOVERABLE"
                    not in (
                        _object if isinstance(_object, discord.Guild) else _object.guild
                    ).features
                    else "globe"
                ]
            )
            image = image.resize((55, 55))
            img.paste(image, (190, 105, 245, 160), mask=image.split()[3])
            draw.text(
                (255, 105),
                text=self.remove_unprintable_characters(
                    (_object if isinstance(_object, discord.Guild) else _object.guild).name
                ),
                fill=(163, 163, 163),
                font=self.font[54],
            )

        # Optional `joined_on` and `created_on`.
        if isinstance(_object, discord.Member):
            # `created_on`
            draw.rounded_rectangle((1200, 75, 1545, 175), radius=15, fill=(47, 49, 54))
            align_text_center(
                (1200, 75, 1545, 175),
                text=_object.created_at.strftime("%B %d, %Y"),
                fill=(255, 255, 255),
                font=self.font[36],
            )
            draw.rounded_rectangle((1220, 30, 1476, 90), radius=15, fill=(79, 84, 92))
            align_text_center(
                (1220, 30, 1476, 90),
                text=_("Created On"),
                fill=(255, 255, 255),
                font=self.bold_font[30],
            )
            # `joined_on`
            draw.rounded_rectangle((1200 + 365, 75, 1545 + 365, 175), radius=15, fill=(47, 49, 54))
            align_text_center(
                (1200 + 365, 75, 1545 + 365, 175),
                text=_object.joined_at.strftime("%B %d, %Y"),
                fill=(255, 255, 255),
                font=self.font[36],
            )
            draw.rounded_rectangle((1220 + 365, 30, 1476 + 365, 90), radius=15, fill=(79, 84, 92))
            align_text_center(
                (1220 + 365, 30, 1476 + 365, 90),
                text=_("Joined On"),
                fill=(255, 255, 255),
                font=self.bold_font[30],
            )
        elif isinstance(
            _object,
            (discord.Guild, discord.CategoryChannel, discord.TextChannel, discord.VoiceChannel),
        ):
            # `created_on`
            draw.rounded_rectangle((1200 + 365, 75, 1545 + 365, 175), radius=15, fill=(47, 49, 54))
            align_text_center(
                (1200 + 365, 75, 1545 + 365, 175),
                text=_object.created_at.strftime("%B %d, %Y"),
                fill=(255, 255, 255),
                font=self.font[36],
            )
            draw.rounded_rectangle((1220 + 365, 30, 1476 + 365, 90), radius=15, fill=(79, 84, 92))
            align_text_center(
                (1220 + 365, 30, 1476 + 365, 90),
                text=_("Created On"),
                fill=(255, 255, 255),
                font=self.bold_font[30],
            )

        if not to_file:
            return img
        buffer = io.BytesIO()
        img.save(buffer, format="png", optimize=True)
        buffer.seek(0)
        return discord.File(buffer, filename="image.png")

    async def generate_prefix_image(
        self,
        _object: typing.Union[
            discord.Member,
            discord.Role,
            discord.Guild,
            typing.Tuple[
                discord.Guild,
                typing.Union[
                    typing.Literal["messages", "voice", "activities"],
                    typing.Tuple[
                        typing.Literal["top"],
                        typing.Literal["messages", "voice"],
                        typing.Literal["members", "channels"],
                    ],
                    typing.Tuple[typing.Literal["activity"], str],
                ],
            ],
            discord.CategoryChannel,
            discord.TextChannel,
            discord.VoiceChannel,
        ],
        size: typing.Tuple[int, int] = (1942, 1026),
        to_file: bool = True,
    ) -> typing.Union[Image.Image, discord.File]:
        if isinstance(_object, typing.Tuple):
            _object, _type = _object
        else:
            _type = None
        return await asyncio.to_thread(
            self._generate_prefix_image,
            _object=_object if _type is None else (_object, _type),
            size=size,
            to_file=to_file,
            _object_display=(await _object.display_avatar.read())
            if isinstance(_object, discord.Member)
            else (
                (await _object.display_icon.read())
                if isinstance(_object, discord.Role) and _object.display_icon is not None
                else None
            ),
            guild_icon=(
                await (
                    _object if isinstance(_object, discord.Guild) else _object.guild
                ).icon.read()
            )
            if (_object if isinstance(_object, discord.Guild) else _object.guild).icon is not None
            else None,
        )

    def _generate_graphic(
        self,
        _object: typing.Union[
            discord.Member,
            discord.Role,
            discord.Guild,
            typing.Tuple[
                discord.Guild,
                typing.Union[
                    typing.Literal["messages", "voice", "activities"],
                    typing.Tuple[
                        typing.Literal["top"],
                        typing.Literal["messages", "voice"],
                        typing.Literal["members", "channels"],
                    ],
                    typing.Tuple[typing.Literal["activity"], str],
                ],
            ],
            discord.CategoryChannel,
            discord.TextChannel,
            discord.VoiceChannel,
        ],
        members_type: typing.Literal["humans", "bots", "both"],
        size: typing.Optional[typing.Tuple[int, int]],
        data: dict,
        to_file: bool,
        img: Image.Image,
        default_state: bool,
        first_loading_time: datetime.datetime,
    ) -> typing.Union[Image.Image, discord.File]:
        if isinstance(_object, typing.Tuple):
            _object = _object[0]
        draw: ImageDraw.ImageDraw = ImageDraw.Draw(img)
        align_text_center = functools.partial(self.align_text_center, draw)
        if size is None:
            draw.rounded_rectangle((30, 204, 1910, 952), radius=15, fill=(47, 49, 54))
            draw.text((50, 220), text=_("Graphic"), fill=(255, 255, 255), font=self.bold_font[40])
            image = Image.open(self.icons["query_stats"])
            image = image.resize((70, 70))
            img.paste(image, (1830, 214, 1900, 284), mask=image.split()[3])
            draw.rounded_rectangle((50, 301, 1890, 922), radius=15, fill=(32, 34, 37))
        else:
            draw.rounded_rectangle((0, 0, size[0], size[1]), radius=15, fill=(32, 34, 37))

        fig = go.Figure()
        fig.update_layout(
            template="plotly_white",
            paper_bgcolor="rgba(0,0,0,0)",  # Transparent background.
            plot_bgcolor="rgba(0,0,0,0)",  # Transparent background.
            font_color="white",  # White characters font.
            font_size=30,  # Characters font size.
            yaxis2={"overlaying": "y", "side": "right"},
        )
        x = list(range(-30, 1))
        # x_rev = x[::-1]
        if data["graphic"].get("contributors") is not None:
            if size is None:
                draw.ellipse(
                    (img.width - 110, 321, img.width - 70, 361),
                    fill=(105, 105, 105),
                    outline=(0, 0, 0),
                )
                x1 = (
                    img.width
                    - 110
                    - 10
                    - self.bold_font[30].getbbox(
                        f"{self.number_to_text_with_suffix(data['contributors'][30])} Contributors"
                    )[2]
                )
                align_text_center(
                    (x1, 321, x1, 361),
                    text=f"{self.number_to_text_with_suffix(data['contributors'][30])} Contributors",
                    fill=(255, 255, 255),
                    font=self.bold_font[30],
                )
            else:
                draw.ellipse(
                    (img.width - 60, 20, img.width - 20, 60),
                    fill=(105, 105, 105),
                    outline=(0, 0, 0),
                )
                x1 = (
                    img.width
                    - 60
                    - 10
                    - self.bold_font[30].getbbox(
                        f"{self.number_to_text_with_suffix(data['contributors'][30])} Contributors"
                    )[2]
                )
                align_text_center(
                    (x1, 20, x1, 60),
                    text=f"{self.number_to_text_with_suffix(data['contributors'][30])} Contributors",
                    fill=(255, 255, 255),
                    font=self.bold_font[30],
                )
            y3 = list(data["graphic"]["contributors"].values()) + [0]
            fig.add_trace(
                go.Bar(
                    x=x,
                    y=y3,
                    name=_("Contributors"),
                    showlegend=False,
                    marker={"color": "rgb(105,105,105)"},
                )
            )
        if data["graphic"].get("voice") is not None:
            if size is None:
                draw.ellipse(
                    (img.width - 110, 321, img.width - 70, 361),
                    fill=(255, 0, 0),
                    outline=(0, 0, 0),
                )
                x1 = (
                    img.width
                    - 110
                    - 10
                    - self.bold_font[30].getbbox(
                        f"{self.number_to_text_with_suffix(data['voice_activity'][30])} Voice Hours"
                    )[2]
                )
                align_text_center(
                    (x1, 321, x1, 361),
                    text=f"{self.number_to_text_with_suffix(data['voice_activity'][30])} Voice Hour{'' if 0 < data['voice_activity'][30] <= 1 else 's'}",
                    fill=(255, 255, 255),
                    font=self.bold_font[30],
                )
            else:
                draw.ellipse(
                    (img.width - 60, 20, img.width - 20, 60), fill=(255, 0, 0), outline=(0, 0, 0)
                )
                x1 = (
                    img.width
                    - 60
                    - 10
                    - self.bold_font[30].getbbox(
                        f"{self.number_to_text_with_suffix(data['voice_activity'][30])} Voice Hours"
                    )[2]
                )
                align_text_center(
                    (x1, 20, x1, 60),
                    text=f"{self.number_to_text_with_suffix(data['voice_activity'][30])} Voice Hour{'' if 0 < data['voice_activity'][30] <= 1 else 's'}",
                    fill=(255, 255, 255),
                    font=self.bold_font[30],
                )
            y2 = list(data["graphic"]["voice"].values()) + [0]
            # y2_upper = [5.5, 3, 5.5, 8, 6, 3, 8, 5, 6, 5.5]
            # y2_lower = [4.5, 2, 4.4, 7, 4, 2, 7, 4, 5, 4.75]
            # y2_lower = y2_lower[::-1]
            # fig.add_trace(
            #     go.Scatter(
            #         x=x + x_rev,
            #         y=y2_upper + y2_lower,
            #         fill="toself",
            #         fillcolor="rgba(255,0,0,0.2)",
            #         line_color="rgba(255,255,255,0)",
            #         name="Voice",
            #         showlegend=False,
            #     )
            # )
            fig.add_trace(
                go.Scatter(
                    x=x,
                    y=y2,
                    line_color="rgb(255,0,0)",
                    name="Voice",
                    showlegend=False,
                    line={"width": 14},
                    fill="tozeroy",
                    fillcolor="rgba(255,0,0,0.2)",
                    # yaxis="y2"
                )
            )
        if data["graphic"].get("messages") is not None:
            if size is None:
                draw.ellipse((70, 321, 110, 361), fill=(0, 255, 0), outline=(0, 0, 0))
                align_text_center(
                    (120, 321, 120, 361),
                    text=f"{self.number_to_text_with_suffix(data['messages'][30])} Message{'' if 0 < data['messages'][30] <= 1 else 's'}",
                    fill=(255, 255, 255),
                    font=self.bold_font[30],
                )
            else:
                draw.ellipse((20, 20, 60, 60), fill=(0, 255, 0), outline=(0, 0, 0))
                align_text_center(
                    (70, 20, 70, 60),
                    text=f"{self.number_to_text_with_suffix(data['messages'][30])} Message{'' if 0 < data['messages'][30] <= 1 else 's'}",
                    fill=(255, 255, 255),
                    font=self.bold_font[30],
                )
            y1 = list(data["graphic"]["messages"].values()) + [0]
            # y1_upper = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
            # y1_lower = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
            # y1_lower = y1_lower[::-1]
            # fig.add_trace(
            #     go.Scatter(
            #         x=x + x_rev,
            #         y=y1_upper + y1_lower,
            #         fill="toself",
            #         fillcolor="rgba(0,255,0,0.2)",
            #         line_color="rgba(255,255,255,0)",
            #         name="Messages",
            #         showlegend=False,
            #     )
            # )
            # fig.add_trace(
            #     go.Scatter(
            #         x=x,
            #         y=y1,
            #         fill="toself",
            #         fillcolor="rgba(0,255,0,0.2)",
            #         line_color="rgba(255,255,255,0)",
            #         name="Messages",
            #         showlegend=False,
            #         line={"width": 15},
            #     )
            # )
            fig.add_trace(
                go.Scatter(
                    x=x,
                    y=y1,
                    line_color="rgb(0,255,0)",
                    name="Messages",
                    showlegend=False,
                    line={"width": 14},
                    fill="tozeroy",
                    fillcolor="rgba(0,255,0,0.2)",
                )
            )
        for key in [
            "activities",
            "top_messages_members",
            "top_messages_channels",
            "top_voice_members",
            "top_voice_channels",
            "top_members",
        ]:
            if data["graphic"].get(key) is not None:
                fig.add_trace(
                    go.Pie(
                        labels=[
                            (
                                self.remove_unprintable_characters(label)
                                if key.split("_")[0] != "top"
                                else (
                                    self.get_member_display(_object.get_member(label))
                                    if key.split("_")[-1] == "members"
                                    else self.remove_unprintable_characters(
                                        _object.get_channel(label).name
                                    )
                                )
                            )[:20]
                            for label in data["graphic"][key].keys()
                        ],
                        values=list(data["graphic"][key].values()),
                        hole=0.3,
                        textfont_size=20,
                        textposition="inside",
                        textfont={"color": "rgb(255,255,255)"},
                        textinfo="percent+label",
                        marker={"line": {"color": "rgb(0,0,0)", "width": 2}},
                        direction="clockwise",
                    )
                )
        # fig.update_traces(mode="lines")
        fig.update_xaxes(type="category", tickvals=list(range(-30, 1, 5)))  # x
        fig.update_yaxes(showgrid=True)

        graphic_bytes: bytes = fig.to_image(
            format="png",
            width=1840 if size is None else size[0],
            height=621 if size is None else size[1],
            scale=1,
        )
        image = Image.open(io.BytesIO(graphic_bytes))
        if size is None:
            img.paste(image, (50, 301, 1890, 922), mask=image.split()[3])
        else:
            img.paste(image, (0, 0, size[0], size[1]), mask=image.split()[3])

        if size is None:
            if default_state:
                image = Image.open(self.icons["history"])
                image = image.resize((50, 50))
                img.paste(image, (30, 972, 80, 1022), mask=image.split()[3])
                utc_now = datetime.datetime.now(tz=datetime.timezone.utc)
                tracking_data_start_time = max(
                    first_loading_time,
                    (
                        _object if isinstance(_object, discord.Guild) else _object.guild
                    ).me.joined_at,
                )
                tracking_data_start_time = tracking_data_start_time.replace(
                    second=utc_now.second,
                    minute=utc_now.minute
                    if (utc_now - tracking_data_start_time)
                    > datetime.timedelta(seconds=3600 * 24 * 7)
                    else tracking_data_start_time.minute,
                    hour=utc_now.hour
                    if (utc_now - tracking_data_start_time)
                    > datetime.timedelta(seconds=3600 * 24 * 30)
                    else tracking_data_start_time.hour,
                    day=utc_now.day
                    if (utc_now - tracking_data_start_time)
                    > datetime.timedelta(seconds=3600 * 24 * 365)
                    else tracking_data_start_time.day,
                )
                align_text_center(
                    (90, 972, 90, 1022),
                    text=_("Tracking data in this server for {interval_string}.").format(
                        interval_string=CogsUtils.get_interval_string(
                            tracking_data_start_time, utc_now=utc_now
                        )
                    ),
                    fill=(255, 255, 255),
                    font=self.bold_font[30],
                )
            if members_type != "both":
                members_type_text = _("Only {members_type} are taken into account.").format(
                    members_type=members_type
                )
                image = Image.open(self.icons["person"])
                image = image.resize((50, 50))
                img.paste(
                    image,
                    (
                        1942 - 30 - self.bold_font[30].getbbox(members_type_text)[2] - 10 - 50,
                        972,
                        1942 - 30 - self.bold_font[30].getbbox(members_type_text)[2] - 10,
                        1022,
                    ),
                    mask=image.split()[3],
                )
                align_text_center(
                    (
                        1942 - 30 - self.bold_font[30].getbbox(members_type_text)[2],
                        972,
                        1942 - 30 - self.bold_font[30].getbbox(members_type_text)[2],
                        1022,
                    ),
                    text=members_type_text,
                    fill=(255, 255, 255),
                    font=self.bold_font[30],
                )

        if not to_file:
            return img
        buffer = io.BytesIO()
        img.save(buffer, format="png", optimize=True)
        buffer.seek(0)
        return discord.File(buffer, filename="image.png")

    async def generate_graphic(
        self,
        _object: typing.Union[
            discord.Member,
            discord.Role,
            discord.Guild,
            typing.Tuple[
                discord.Guild,
                typing.Union[
                    typing.Literal["messages", "voice", "activities"],
                    typing.Tuple[
                        typing.Literal["top"],
                        typing.Literal["messages", "voice"],
                        typing.Literal["members", "channels"],
                    ],
                    typing.Tuple[typing.Literal["activity"], str],
                ],
            ],
            discord.CategoryChannel,
            discord.TextChannel,
            discord.VoiceChannel,
        ],
        members_type: typing.Literal["humans", "bots", "both"] = "humans",
        size: typing.Optional[typing.Tuple[int, int]] = None,
        data: typing.Optional[dict] = None,
        to_file: bool = True,
    ) -> typing.Union[Image.Image, discord.File]:
        if isinstance(_object, typing.Tuple):
            _object, _type = _object
        else:
            _type = None
        img: Image.Image = await self.generate_prefix_image(
            _object if _type is None else (_object, _type),
            size=(1942, 982 + 70) if size is None else size,
            to_file=False,
        )
        if data is None:
            data = await self.get_data(
                _object if _type is None else (_object, _type), members_type=members_type
            )
        return await asyncio.to_thread(
            self._generate_graphic,
            _object=_object if _type is None else (_object, _type),
            members_type=members_type,
            size=size,
            data=data,
            to_file=to_file,
            img=img,
            default_state=await self.config.default_state(),
            first_loading_time=datetime.datetime.fromtimestamp(
                await self.config.first_loading_time(), tz=datetime.timezone.utc
            ),
        )

    def _generate_image(
        self,
        _object: typing.Union[
            discord.Member,
            discord.Role,
            discord.Guild,
            typing.Tuple[
                discord.Guild,
                typing.Union[
                    typing.Literal["messages", "voice", "activities"],
                    typing.Tuple[
                        typing.Literal["top"],
                        typing.Literal["messages", "voice"],
                        typing.Literal["members", "channels"],
                    ],
                    typing.Tuple[typing.Literal["activity"], str],
                ],
            ],
            discord.CategoryChannel,
            discord.TextChannel,
            discord.VoiceChannel,
        ],
        members_type: typing.Literal["humans", "bots", "both"],
        show_graphic: bool,
        graphic: typing.Optional[Image.Image],
        data: dict,
        to_file: bool,
        img: Image.Image,
        default_state: bool,
        first_loading_time: datetime.datetime,
    ) -> typing.Union[Image.Image, discord.File]:
        if isinstance(_object, typing.Tuple):
            _object, _type = _object
        else:
            _type = None
        draw: ImageDraw.ImageDraw = ImageDraw.Draw(img)
        align_text_center = functools.partial(self.align_text_center, draw)

        # Data.
        if isinstance(_object, (discord.Member, discord.Role)):
            # Server Lookback. box = 606 / empty = 30 | 2 cases / box = 117 / empty = 30
            draw.rounded_rectangle((30, 204, 636, 585), radius=15, fill=(47, 49, 54))
            align_text_center(
                (50, 214, 50, 284),
                text=_("Server Lookback"),
                fill=(255, 255, 255),
                font=self.bold_font[40],
            )
            image = Image.open(self.icons["history"])
            image = image.resize((70, 70))
            img.paste(image, (546, 214, 616, 284), mask=image.split()[3])
            draw.rounded_rectangle((50, 301, 616, 418), radius=15, fill=(32, 34, 37))
            draw.rounded_rectangle((50, 301, 325, 418), radius=15, fill=(24, 26, 27))
            align_text_center(
                (50, 301, 325, 418), text=_("Text"), fill=(255, 255, 255), font=self.bold_font[36]
            )
            align_text_center(
                (325, 301, 616, 418),
                text=f"{self.number_to_text_with_suffix(data['server_lookback']['text'])} message{'' if 0 < data['server_lookback']['text'] <= 1 else 's'}",
                fill=(255, 255, 255),
                font=self.font[36],
            )
            draw.rounded_rectangle((50, 448, 616, 565), radius=15, fill=(32, 34, 37))
            draw.rounded_rectangle((50, 448, 325, 565), radius=15, fill=(24, 26, 27))
            align_text_center(
                (50, 448, 325, 565), text=_("Voice"), fill=(255, 255, 255), font=self.bold_font[36]
            )
            align_text_center(
                (325, 448, 616, 565),
                text=f"{self.number_to_text_with_suffix(data['server_lookback']['voice'])} hour{'' if 0 < data['server_lookback']['voice'] <= 1 else 's'}",
                fill=(255, 255, 255),
                font=self.font[36],
            )

            # Messages. box = 606 / empty = 30 | 3 cases / box = 76 / empty = 16
            draw.rounded_rectangle((668, 204, 1274, 585), radius=15, fill=(47, 49, 54))
            align_text_center(
                (688, 214, 688, 284),
                text=_("Messages"),
                fill=(255, 255, 255),
                font=self.bold_font[40],
            )
            image = Image.open(self.icons["#"])
            image = image.resize((70, 70))
            img.paste(image, (1184, 214, 1254, 284), mask=image.split()[3])
            draw.rounded_rectangle((688, 301, 1254, 377), radius=15, fill=(32, 34, 37))
            draw.rounded_rectangle((688, 301, 910, 377), radius=15, fill=(24, 26, 27))
            align_text_center(
                (688, 301, 910, 377), text=_("1d"), fill=(255, 255, 255), font=self.bold_font[36]
            )
            align_text_center(
                (910, 301, 1254, 377),
                text=f"{self.number_to_text_with_suffix(data['messages'][1])} message{'' if 0 < data['messages'][1] <= 1 else 's'}",
                fill=(255, 255, 255),
                font=self.font[36],
            )
            draw.rounded_rectangle((688, 395, 1254, 471), radius=15, fill=(32, 34, 37))
            draw.rounded_rectangle((688, 395, 910, 471), radius=15, fill=(24, 26, 27))
            align_text_center(
                (688, 395, 910, 471), text=_("7d"), fill=(255, 255, 255), font=self.bold_font[36]
            )
            align_text_center(
                (910, 395, 1254, 471),
                text=f"{self.number_to_text_with_suffix(data['messages'][7])} message{'' if 0 < data['messages'][7] <= 1 else 's'}",
                fill=(255, 255, 255),
                font=self.font[36],
            )
            draw.rounded_rectangle((688, 489, 1254, 565), radius=15, fill=(32, 34, 37))
            draw.rounded_rectangle((688, 489, 910, 565), radius=15, fill=(24, 26, 27))
            align_text_center(
                (688, 489, 910, 565), text=_("30d"), fill=(255, 255, 255), font=self.bold_font[36]
            )
            align_text_center(
                (910, 489, 1254, 565),
                text=f"{self.number_to_text_with_suffix(data['messages'][30])} message{'' if 0 < data['messages'][30] <= 1 else 's'}",
                fill=(255, 255, 255),
                font=self.font[36],
            )

            # Voice Activity. + 52 / box = 606 / empty = 30 | 3 cases / box = 76 / empty = 16
            draw.rounded_rectangle((1306, 204, 1912, 585), radius=15, fill=(47, 49, 54))
            align_text_center(
                (1326, 214, 1326, 284),
                text=_("Voice Activity"),
                fill=(255, 255, 255),
                font=self.bold_font[40],
            )
            image = Image.open(self.icons["sound"])
            image = image.resize((70, 70))
            img.paste(image, (1822, 214, 1892, 284), mask=image.split()[3])
            draw.rounded_rectangle((1326, 301, 1892, 377), radius=15, fill=(32, 34, 37))
            draw.rounded_rectangle((1326, 301, 1548, 377), radius=15, fill=(24, 26, 27))
            align_text_center(
                (1326, 301, 1548, 377), text=_("1d"), fill=(255, 255, 255), font=self.bold_font[36]
            )
            align_text_center(
                (1548, 301, 1892, 377),
                text=f"{self.number_to_text_with_suffix(data['voice_activity'][1])} hour{'' if 0 < data['voice_activity'][1] <= 1 else 's'}",
                fill=(255, 255, 255),
                font=self.font[36],
            )
            draw.rounded_rectangle((1326, 395, 1892, 471), radius=15, fill=(32, 34, 37))
            draw.rounded_rectangle((1326, 395, 1548, 471), radius=15, fill=(24, 26, 27))
            align_text_center(
                (1326, 395, 1548, 471), text=_("7d"), fill=(255, 255, 255), font=self.bold_font[36]
            )
            align_text_center(
                (1548, 395, 1892, 471),
                text=f"{self.number_to_text_with_suffix(data['voice_activity'][7])} hour{'' if 0 < data['voice_activity'][7] <= 1 else 's'}",
                fill=(255, 255, 255),
                font=self.font[36],
            )
            draw.rounded_rectangle((1326, 489, 1892, 565), radius=15, fill=(32, 34, 37))
            draw.rounded_rectangle((1326, 489, 1548, 565), radius=15, fill=(24, 26, 27))
            align_text_center(
                (1326, 489, 1548, 565),
                text=_("30d"),
                fill=(255, 255, 255),
                font=self.bold_font[36],
            )
            align_text_center(
                (1548, 489, 1892, 565),
                text=f"{self.number_to_text_with_suffix(data['voice_activity'][30])} hour{'' if 0 < data['voice_activity'][30] <= 1 else 's'}",
                fill=(255, 255, 255),
                font=self.font[36],
            )

            # # Server Ranks. box = 606 / empty = 30 | 2 cases / box = 117 / empty = 30
            # draw.rounded_rectangle((1942, 204, 2548, 585), radius=15, fill=(47, 49, 54))
            # align_text_center((1962, 214, 1962, 284), text="Server Ranks", fill=(255, 255, 255), font=self.bold_font[40])
            # image = Image.open(self.icons["trophy"])
            # image = image.resize((70, 70))
            # img.paste(image, (2458, 214, 2528, 284), mask=image.split()[3])
            # draw.rounded_rectangle((1962, 301, 2528, 418), radius=15, fill=(32, 34, 37))
            # draw.rounded_rectangle((1962, 301, 2237, 418), radius=15, fill=(24, 26, 27))
            # align_text_center((1962, 301, 2237, 418), text="Text", fill=(255, 255, 255), font=self.bold_font[36])
            # align_text_center((2237, 301, 2528, 418), text=f"#{data['server_ranks']['text']}" if data['server_ranks']['text'] is not None else "No data.", fill=(255, 255, 255), font=self.font[36])
            # draw.rounded_rectangle((1962, 448, 2528, 565), radius=15, fill=(32, 34, 37))
            # draw.rounded_rectangle((1962, 448, 2237, 565), radius=15, fill=(24, 26, 27))
            # align_text_center((1962, 448, 2237, 565), text="Voice", fill=(255, 255, 255), font=self.bold_font[36])
            # align_text_center((2237, 448, 2528, 565), text=f"#{data['server_ranks']['voice']}" if data['server_ranks']['voice'] is not None else "No data.", fill=(255, 255, 255), font=self.font[36])

            # Server Ranks. box = 606 / empty = 30 | 2 cases / box = 117 / empty = 30
            draw.rounded_rectangle((30, 615, 636, 996), radius=15, fill=(47, 49, 54))
            align_text_center(
                (50, 625, 50, 695),
                text=_("Server Ranks"),
                fill=(255, 255, 255),
                font=self.bold_font[40],
            )
            image = Image.open(self.icons["trophy"])
            image = image.resize((70, 70))
            img.paste(image, (546, 625, 616, 695), mask=image.split()[3])
            draw.rounded_rectangle((50, 712, 616, 829), radius=15, fill=(32, 34, 37))
            draw.rounded_rectangle((50, 712, 325, 829), radius=15, fill=(24, 26, 27))
            align_text_center(
                (50, 712, 325, 829), text="Text", fill=(255, 255, 255), font=self.bold_font[36]
            )
            align_text_center(
                (325, 712, 616, 829),
                text=f"#{data['server_ranks']['text']}"
                if data["server_ranks"]["text"] is not None
                else _("No data."),
                fill=(255, 255, 255),
                font=self.font[36],
            )
            draw.rounded_rectangle((50, 859, 616, 976), radius=15, fill=(32, 34, 37))
            draw.rounded_rectangle((50, 859, 325, 976), radius=15, fill=(24, 26, 27))
            align_text_center(
                (50, 859, 325, 976), text=_("Voice"), fill=(255, 255, 255), font=self.bold_font[36]
            )
            align_text_center(
                (325, 859, 616, 976),
                text=f"#{data['server_ranks']['voice']}"
                if data["server_ranks"]["voice"] is not None
                else _("No data."),
                fill=(255, 255, 255),
                font=self.font[36],
            )

            # Top Channels & Activity. box = 925 / empty = 30 | 3 cases / box = 76 / empty = 16
            draw.rounded_rectangle((668, 615, 1593, 996), radius=15, fill=(47, 49, 54))
            align_text_center(
                (688, 625, 688, 695),
                text=_("Top Channels & Activity"),
                fill=(255, 255, 255),
                font=self.bold_font[40],
            )
            image = Image.open(self.icons["query_stats"])
            image = image.resize((70, 70))
            img.paste(image, (1503, 625, 1573, 695), mask=image.split()[3])
            image = Image.open(self.icons["#"])
            image = image.resize((70, 70))
            img.paste(image, (688, 715, 758, 785), mask=image.split()[3])
            draw.rounded_rectangle((768, 712, 1573, 788), radius=15, fill=(32, 34, 37))
            draw.rounded_rectangle((768, 712, 1218, 788), radius=15, fill=(24, 26, 27))
            if (
                data["top_channels_and_activity"]["text"]["channel"] is not None
                and data["top_channels_and_activity"]["text"]["value"] is not None
            ):
                align_text_center(
                    (768, 712, 1218, 788),
                    text=self.remove_unprintable_characters(
                        _object.guild.get_channel(
                            data["top_channels_and_activity"]["text"]["channel"]
                        ).name
                    ),
                    fill=(255, 255, 255),
                    font=self.bold_font[36],
                )
                align_text_center(
                    (1218, 712, 1573, 788),
                    text=f"{self.number_to_text_with_suffix(data['top_channels_and_activity']['text']['value'])} message{'' if 0 < data['top_channels_and_activity']['text']['value'] <= 1 else 's'}",
                    fill=(255, 255, 255),
                    font=self.font[36],
                )
            image = Image.open(self.icons["sound"])
            image = image.resize((70, 70))
            img.paste(image, (688, 807, 758, 877), mask=image.split()[3])
            draw.rounded_rectangle((768, 804, 1573, 880), radius=15, fill=(32, 34, 37))
            draw.rounded_rectangle((768, 804, 1218, 880), radius=15, fill=(24, 26, 27))
            if (
                data["top_channels_and_activity"]["voice"]["channel"] is not None
                and data["top_channels_and_activity"]["voice"]["value"] is not None
            ):
                align_text_center(
                    (768, 804, 1218, 880),
                    text=self.remove_unprintable_characters(
                        _object.guild.get_channel(
                            data["top_channels_and_activity"]["voice"]["channel"]
                        ).name
                    ),
                    fill=(255, 255, 255),
                    font=self.bold_font[36],
                )
                align_text_center(
                    (1218, 804, 1573, 880),
                    text=f"{self.number_to_text_with_suffix(data['top_channels_and_activity']['voice']['value'])} hour{'' if 0 < data['top_channels_and_activity']['voice']['value'] <= 1 else 's'}",
                    fill=(255, 255, 255),
                    font=self.font[36],
                )
            image = Image.open(self.icons["game"])
            image = image.resize((70, 70))
            img.paste(image, (688, 899, 758, 969), mask=image.split()[3])
            draw.rounded_rectangle((768, 896, 1573, 972), radius=15, fill=(32, 34, 37))
            draw.rounded_rectangle((768, 896, 1218, 972), radius=15, fill=(24, 26, 27))
            if (
                data["top_channels_and_activity"]["activity"]["activity"] is not None
                and data["top_channels_and_activity"]["activity"]["value"] is not None
            ):
                align_text_center(
                    (768, 896, 1218, 972),
                    text=data["top_channels_and_activity"]["activity"]["activity"],
                    fill=(255, 255, 255),
                    font=self.bold_font[36],
                )
                align_text_center(
                    (1218, 896, 1573, 972),
                    text=f"{self.number_to_text_with_suffix(data['top_channels_and_activity']['activity']['value'])} hour{'' if 0 < data['top_channels_and_activity']['activity']['value'] <= 1 else 's'}",
                    fill=(255, 255, 255),
                    font=self.font[36],
                )

            if show_graphic:
                # Graphic. box = 940 / empty = 0 | + 411 (381 + 30) / 1 case / box = 264 / empty = 0
                draw.rounded_rectangle((30, 1026, 1910, 1407 + 200), radius=15, fill=(47, 49, 54))
                align_text_center(
                    (50, 1036, 50, 1106),
                    text=_("Graphic"),
                    fill=(255, 255, 255),
                    font=self.bold_font[40],
                )
                image = Image.open(self.icons["query_stats"])
                image = image.resize((70, 70))
                img.paste(image, (1830, 1036, 1900, 1106), mask=image.split()[3])
                draw.rounded_rectangle((50, 1123, 1890, 1387 + 200), radius=15, fill=(32, 34, 37))
                image: Image.Image = graphic
                image = image.resize((1840, 464))
                img.paste(image, (50, 1123, 1890, 1387 + 200))

        elif isinstance(_object, discord.Guild):
            if _type is None:
                # Server Lookback. box = 606 / empty = 30 | 2 cases / box = 117 / empty = 30
                draw.rounded_rectangle((30, 204, 636, 585), radius=15, fill=(47, 49, 54))
                align_text_center(
                    (50, 214, 50, 284),
                    text=_("Server Lookback"),
                    fill=(255, 255, 255),
                    font=self.bold_font[40],
                )
                image = Image.open(self.icons["history"])
                image = image.resize((70, 70))
                img.paste(image, (546, 214, 616, 284), mask=image.split()[3])
                draw.rounded_rectangle((50, 301, 616, 418), radius=15, fill=(32, 34, 37))
                draw.rounded_rectangle((50, 301, 325, 418), radius=15, fill=(24, 26, 27))
                align_text_center(
                    (50, 301, 325, 418),
                    text=_("Text"),
                    fill=(255, 255, 255),
                    font=self.bold_font[36],
                )
                align_text_center(
                    (325, 301, 616, 418),
                    text=f"{self.number_to_text_with_suffix(data['server_lookback']['text'])} message{'' if 0 < data['server_lookback']['text'] <= 1 else 's'}",
                    fill=(255, 255, 255),
                    font=self.font[36],
                )
                draw.rounded_rectangle((50, 448, 616, 565), radius=15, fill=(32, 34, 37))
                draw.rounded_rectangle((50, 448, 325, 565), radius=15, fill=(24, 26, 27))
                align_text_center(
                    (50, 448, 325, 565),
                    text=_("Voice"),
                    fill=(255, 255, 255),
                    font=self.bold_font[36],
                )
                align_text_center(
                    (325, 448, 616, 565),
                    text=f"{self.number_to_text_with_suffix(data['server_lookback']['voice'])} hour{'' if 0 < data['server_lookback']['voice'] <= 1 else 's'}",
                    fill=(255, 255, 255),
                    font=self.font[36],
                )

                # Messages. box = 606 / empty = 30 | 3 cases / box = 76 / empty = 16
                draw.rounded_rectangle((668, 204, 1274, 585), radius=15, fill=(47, 49, 54))
                align_text_center(
                    (688, 214, 688, 284),
                    text=_("Messages"),
                    fill=(255, 255, 255),
                    font=self.bold_font[40],
                )
                image = Image.open(self.icons["#"])
                image = image.resize((70, 70))
                img.paste(image, (1184, 214, 1254, 284), mask=image.split()[3])
                draw.rounded_rectangle((688, 301, 1254, 377), radius=15, fill=(32, 34, 37))
                draw.rounded_rectangle((688, 301, 910, 377), radius=15, fill=(24, 26, 27))
                align_text_center(
                    (688, 301, 910, 377),
                    text=_("1d"),
                    fill=(255, 255, 255),
                    font=self.bold_font[36],
                )
                align_text_center(
                    (910, 301, 1254, 377),
                    text=f"{self.number_to_text_with_suffix(data['messages'][1])} message{'' if 0 < data['messages'][1] <= 1 else 's'}",
                    fill=(255, 255, 255),
                    font=self.font[36],
                )
                draw.rounded_rectangle((688, 395, 1254, 471), radius=15, fill=(32, 34, 37))
                draw.rounded_rectangle((688, 395, 910, 471), radius=15, fill=(24, 26, 27))
                align_text_center(
                    (688, 395, 910, 471),
                    text=_("7d"),
                    fill=(255, 255, 255),
                    font=self.bold_font[36],
                )
                align_text_center(
                    (910, 395, 1254, 471),
                    text=f"{self.number_to_text_with_suffix(data['messages'][7])} message{'' if 0 < data['messages'][7] <= 1 else 's'}",
                    fill=(255, 255, 255),
                    font=self.font[36],
                )
                draw.rounded_rectangle((688, 489, 1254, 565), radius=15, fill=(32, 34, 37))
                draw.rounded_rectangle((688, 489, 910, 565), radius=15, fill=(24, 26, 27))
                align_text_center(
                    (688, 489, 910, 565),
                    text=_("30d"),
                    fill=(255, 255, 255),
                    font=self.bold_font[36],
                )
                align_text_center(
                    (910, 489, 1254, 565),
                    text=f"{self.number_to_text_with_suffix(data['messages'][30])} message{'' if 0 < data['messages'][30] <= 1 else 's'}",
                    fill=(255, 255, 255),
                    font=self.font[36],
                )

                # Voice Activity. box = 606 / empty = 30 | 3 cases / box = 76 / empty = 16
                draw.rounded_rectangle((1306, 204, 1912, 585), radius=15, fill=(47, 49, 54))
                align_text_center(
                    (1326, 214, 1326, 284),
                    text=_("Voice Activity"),
                    fill=(255, 255, 255),
                    font=self.bold_font[40],
                )
                image = Image.open(self.icons["sound"])
                image = image.resize((70, 70))
                img.paste(image, (1822, 214, 1892, 284), mask=image.split()[3])
                draw.rounded_rectangle((1326, 301, 1892, 377), radius=15, fill=(32, 34, 37))
                draw.rounded_rectangle((1326, 301, 1548, 377), radius=15, fill=(24, 26, 27))
                align_text_center(
                    (1326, 301, 1548, 377),
                    text=_("1d"),
                    fill=(255, 255, 255),
                    font=self.bold_font[36],
                )
                align_text_center(
                    (1548, 301, 1892, 377),
                    text=f"{self.number_to_text_with_suffix(data['voice_activity'][1])} hour{'' if 0 < data['voice_activity'][1] <= 1 else 's'}",
                    fill=(255, 255, 255),
                    font=self.font[36],
                )
                draw.rounded_rectangle((1326, 395, 1892, 471), radius=15, fill=(32, 34, 37))
                draw.rounded_rectangle((1326, 395, 1548, 471), radius=15, fill=(24, 26, 27))
                align_text_center(
                    (1326, 395, 1548, 471),
                    text=_("7d"),
                    fill=(255, 255, 255),
                    font=self.bold_font[36],
                )
                align_text_center(
                    (1548, 395, 1892, 471),
                    text=f"{self.number_to_text_with_suffix(data['voice_activity'][7])} hour{'' if 0 < data['voice_activity'][7] <= 1 else 's'}",
                    fill=(255, 255, 255),
                    font=self.font[36],
                )
                draw.rounded_rectangle((1326, 489, 1892, 565), radius=15, fill=(32, 34, 37))
                draw.rounded_rectangle((1326, 489, 1548, 565), radius=15, fill=(24, 26, 27))
                align_text_center(
                    (1326, 489, 1548, 565),
                    text=_("30d"),
                    fill=(255, 255, 255),
                    font=self.bold_font[36],
                )
                align_text_center(
                    (1548, 489, 1892, 565),
                    text=f"{self.number_to_text_with_suffix(data['voice_activity'][30])} hour{'' if 0 < data['voice_activity'][30] <= 1 else 's'}",
                    fill=(255, 255, 255),
                    font=self.font[36],
                )

                # Top Members. box = 925 / empty = 30 | 3 cases / box = 117 / empty = 30
                draw.rounded_rectangle((30, 615, 955, 996), radius=15, fill=(47, 49, 54))
                align_text_center(
                    (50, 625, 50, 695),
                    text=_("Top Members"),
                    fill=(255, 255, 255),
                    font=self.bold_font[40],
                )
                image = Image.open(self.icons["person"])
                image = image.resize((70, 70))
                img.paste(image, (865, 625, 935, 695), mask=image.split()[3])
                image = Image.open(self.icons["#"])
                image = image.resize((70, 70))
                img.paste(image, (50, 735, 120, 805), mask=image.split()[3])
                draw.rounded_rectangle((150, 712, 935, 829), radius=15, fill=(32, 34, 37))
                draw.rounded_rectangle((150, 712, 600, 829), radius=15, fill=(24, 26, 27))
                if (
                    data["top_members"]["text"]["member"] is not None
                    and data["top_members"]["text"]["value"] is not None
                ):
                    align_text_center(
                        (150, 712, 600, 829),
                        text=self.get_member_display(
                            _object.get_member(data["top_members"]["text"]["member"])
                        ),
                        fill=(255, 255, 255),
                        font=self.bold_font[36],
                    )
                    align_text_center(
                        (600, 712, 935, 829),
                        text=f"{self.number_to_text_with_suffix(data['top_members']['text']['value'])} message{'' if 0 < data['top_members']['text']['value'] <= 1 else 's'}",
                        fill=(255, 255, 255),
                        font=self.font[36],
                    )
                image = Image.open(self.icons["sound"])
                image = image.resize((70, 70))
                img.paste(image, (50, 882, 120, 952), mask=image.split()[3])
                draw.rounded_rectangle((150, 859, 935, 976), radius=15, fill=(32, 34, 37))
                draw.rounded_rectangle((150, 859, 600, 976), radius=15, fill=(24, 26, 27))
                if (
                    data["top_members"]["voice"]["member"] is not None
                    and data["top_members"]["voice"]["value"] is not None
                ):
                    align_text_center(
                        (150, 859, 600, 976),
                        text=self.get_member_display(
                            _object.get_member(data["top_members"]["voice"]["member"])
                        ),
                        fill=(255, 255, 255),
                        font=self.bold_font[36],
                    )
                    align_text_center(
                        (600, 859, 935, 976),
                        text=f"{self.number_to_text_with_suffix(data['top_members']['voice']['value'])} hour{'' if 0 < data['top_members']['voice']['value'] <= 1 else 's'}",
                        fill=(255, 255, 255),
                        font=self.font[36],
                    )

                # Top Channels. box = 925 / empty = 30 | 3 cases / box = 76 / empty = 16
                draw.rounded_rectangle((985, 615, 1910, 996), radius=15, fill=(47, 49, 54))
                align_text_center(
                    (1005, 625, 1005, 695),
                    text=_("Top Channels"),
                    fill=(255, 255, 255),
                    font=self.bold_font[40],
                )
                image = Image.open(self.icons["#"])
                image = image.resize((70, 70))
                img.paste(image, (1820, 625, 1890, 695), mask=image.split()[3])
                image = Image.open(self.icons["#"])
                image = image.resize((70, 70))
                img.paste(image, (1005, 735, 1075, 805), mask=image.split()[3])
                draw.rounded_rectangle((1105, 712, 1890, 829), radius=15, fill=(32, 34, 37))
                draw.rounded_rectangle((1105, 712, 1555, 829), radius=15, fill=(24, 26, 27))
                if (
                    data["top_channels"]["text"]["channel"] is not None
                    and data["top_channels"]["text"]["value"] is not None
                ):
                    align_text_center(
                        (1105, 712, 1555, 829),
                        text=_object.get_channel(data["top_channels"]["text"]["channel"]).name,
                        fill=(255, 255, 255),
                        font=self.bold_font[36],
                    )
                    align_text_center(
                        (1555, 712, 1890, 829),
                        text=f"{self.number_to_text_with_suffix(data['top_channels']['text']['value'])} message{'' if 0 < data['top_channels']['text']['value'] <= 1 else 's'}",
                        fill=(255, 255, 255),
                        font=self.font[36],
                    )
                image = Image.open(self.icons["sound"])
                image = image.resize((70, 70))
                img.paste(image, (1005, 882, 1075, 952), mask=image.split()[3])
                draw.rounded_rectangle((1105, 859, 1890, 976), radius=15, fill=(32, 34, 37))
                draw.rounded_rectangle((1105, 859, 1555, 976), radius=15, fill=(24, 26, 27))
                if (
                    data["top_channels"]["voice"]["channel"] is not None
                    and data["top_channels"]["voice"]["value"] is not None
                ):
                    align_text_center(
                        (1105, 859, 1555, 976),
                        text=self.remove_unprintable_characters(
                            _object.get_channel(data["top_channels"]["voice"]["channel"]).name
                        ),
                        fill=(255, 255, 255),
                        font=self.bold_font[36],
                    )
                    align_text_center(
                        (1555, 859, 1890, 976),
                        text=f"{self.number_to_text_with_suffix(data['top_channels']['voice']['value'])} hour{'' if 0 < data['top_channels']['voice']['value'] <= 1 else 's'}",
                        fill=(255, 255, 255),
                        font=self.font[36],
                    )

            elif _type == "messages":
                # Server Lookback. box = 606 / empty = 30 | 1 case / box = 264 / empty = 0
                draw.rounded_rectangle((30, 204, 636, 585), radius=15, fill=(47, 49, 54))
                align_text_center(
                    (50, 214, 50, 284),
                    text=_("Server Lookback"),
                    fill=(255, 255, 255),
                    font=self.bold_font[40],
                )
                image = Image.open(self.icons["history"])
                image = image.resize((70, 70))
                img.paste(image, (546, 214, 616, 284), mask=image.split()[3])
                draw.rounded_rectangle((50, 301, 616, 565), radius=15, fill=(32, 34, 37))
                align_text_center(
                    (50, 351, 616, 433),
                    text=f"{self.number_to_text_with_suffix(data['server_lookback'])}",
                    fill=(255, 255, 255),
                    font=self.bold_font[60],
                )
                align_text_center(
                    (50, 433, 616, 515),
                    text=f"message{'' if 0 < data['server_lookback'] <= 1 else 's'}",
                    fill=(255, 255, 255),
                    font=self.bold_font[60],
                )

                # Messages. box = 606 / empty = 30 | 3 cases / box = 76 / empty = 16
                draw.rounded_rectangle((668, 204, 1274, 585), radius=15, fill=(47, 49, 54))
                align_text_center(
                    (688, 214, 688, 284),
                    text=_("Messages"),
                    fill=(255, 255, 255),
                    font=self.bold_font[40],
                )
                image = Image.open(self.icons["#"])
                image = image.resize((70, 70))
                img.paste(image, (1184, 214, 1254, 284), mask=image.split()[3])
                draw.rounded_rectangle((688, 301, 1254, 377), radius=15, fill=(32, 34, 37))
                draw.rounded_rectangle((688, 301, 910, 377), radius=15, fill=(24, 26, 27))
                align_text_center(
                    (688, 301, 910, 377),
                    text=_("1d"),
                    fill=(255, 255, 255),
                    font=self.bold_font[36],
                )
                align_text_center(
                    (910, 301, 1254, 377),
                    text=f"{self.number_to_text_with_suffix(data['messages'][1])} message{'' if 0 < data['messages'][1] <= 1 else 's'}",
                    fill=(255, 255, 255),
                    font=self.font[36],
                )
                draw.rounded_rectangle((688, 395, 1254, 471), radius=15, fill=(32, 34, 37))
                draw.rounded_rectangle((688, 395, 910, 471), radius=15, fill=(24, 26, 27))
                align_text_center(
                    (688, 395, 910, 471),
                    text=_("7d"),
                    fill=(255, 255, 255),
                    font=self.bold_font[36],
                )
                align_text_center(
                    (910, 395, 1254, 471),
                    text=f"{self.number_to_text_with_suffix(data['messages'][7])} message{'' if 0 < data['messages'][7] <= 1 else 's'}",
                    fill=(255, 255, 255),
                    font=self.font[36],
                )
                draw.rounded_rectangle((688, 489, 1254, 565), radius=15, fill=(32, 34, 37))
                draw.rounded_rectangle((688, 489, 910, 565), radius=15, fill=(24, 26, 27))
                align_text_center(
                    (688, 489, 910, 565),
                    text=_("30d"),
                    fill=(255, 255, 255),
                    font=self.bold_font[36],
                )
                align_text_center(
                    (910, 489, 1254, 565),
                    text=f"{self.number_to_text_with_suffix(data['messages'][30])} message{'' if 0 < data['messages'][30] <= 1 else 's'}",
                    fill=(255, 255, 255),
                    font=self.font[36],
                )

                # Contributors. box = 606 / empty = 30 | 3 cases / box = 76 / empty = 16
                draw.rounded_rectangle((1306, 204, 1912, 585), radius=15, fill=(47, 49, 54))
                align_text_center(
                    (1326, 214, 1326, 284),
                    text=_("Contributors"),
                    fill=(255, 255, 255),
                    font=self.bold_font[40],
                )
                image = Image.open(self.icons["person"])
                image = image.resize((70, 70))
                img.paste(image, (1822, 214, 1892, 284), mask=image.split()[3])
                draw.rounded_rectangle((1326, 301, 1892, 377), radius=15, fill=(32, 34, 37))
                draw.rounded_rectangle((1326, 301, 1548, 377), radius=15, fill=(24, 26, 27))
                align_text_center(
                    (1326, 301, 1548, 377),
                    text=_("1d"),
                    fill=(255, 255, 255),
                    font=self.bold_font[36],
                )
                align_text_center(
                    (1548, 301, 1892, 377),
                    text=f"{self.number_to_text_with_suffix(data['contributors'][1])} member{'' if 0 < data['contributors'][1] <= 1 else 's'}",
                    fill=(255, 255, 255),
                    font=self.font[36],
                )
                draw.rounded_rectangle((1326, 395, 1892, 471), radius=15, fill=(32, 34, 37))
                draw.rounded_rectangle((1326, 395, 1548, 471), radius=15, fill=(24, 26, 27))
                align_text_center(
                    (1326, 395, 1548, 471),
                    text=_("7d"),
                    fill=(255, 255, 255),
                    font=self.bold_font[36],
                )
                align_text_center(
                    (1548, 395, 1892, 471),
                    text=f"{self.number_to_text_with_suffix(data['contributors'][7])} member{'' if 0 < data['contributors'][7] <= 1 else 's'}",
                    fill=(255, 255, 255),
                    font=self.font[36],
                )
                draw.rounded_rectangle((1326, 489, 1892, 565), radius=15, fill=(32, 34, 37))
                draw.rounded_rectangle((1326, 489, 1548, 565), radius=15, fill=(24, 26, 27))
                align_text_center(
                    (1326, 489, 1548, 565),
                    text=_("30d"),
                    fill=(255, 255, 255),
                    font=self.bold_font[36],
                )
                align_text_center(
                    (1548, 489, 1892, 565),
                    text=f"{self.number_to_text_with_suffix(data['contributors'][30])} member{'' if 0 < data['contributors'][30] <= 1 else 's'}",
                    fill=(255, 255, 255),
                    font=self.font[36],
                )

                # Top Messages Members. box = 925 / empty = 30 | 3 cases / box = 76 / empty = 16
                draw.rounded_rectangle((30, 615, 955, 996), radius=15, fill=(47, 49, 54))
                align_text_center(
                    (50, 625, 50, 695),
                    text=_("Top Messages Members"),
                    fill=(255, 255, 255),
                    font=self.bold_font[40],
                )
                image = Image.open(self.icons["#"])
                image = image.resize((70, 70))
                img.paste(image, (865, 625, 935, 695), mask=image.split()[3])
                data["top_messages_members"] = list(data["top_messages_members"].items())
                draw.rounded_rectangle((50, 712, 935, 788), radius=15, fill=(32, 34, 37))
                draw.rounded_rectangle((50, 712, 600, 788), radius=15, fill=(24, 26, 27))
                if len(data["top_messages_members"]) >= 1:
                    align_text_center(
                        (50, 712, 600, 788),
                        text=self.get_member_display(
                            _object.get_member(data["top_messages_members"][0][0])
                        ),
                        fill=(255, 255, 255),
                        font=self.bold_font[36],
                    )
                    align_text_center(
                        (600, 712, 935, 788),
                        text=f"{self.number_to_text_with_suffix(data['top_messages_members'][0][1])} message{'' if 0 < data['top_messages_members'][0][1] <= 1 else 's'}",
                        fill=(255, 255, 255),
                        font=self.font[36],
                    )
                draw.rounded_rectangle((50, 804, 935, 880), radius=15, fill=(32, 34, 37))
                draw.rounded_rectangle((50, 804, 600, 880), radius=15, fill=(24, 26, 27))
                if len(data["top_messages_members"]) >= 2:
                    align_text_center(
                        (50, 804, 600, 880),
                        text=self.get_member_display(
                            _object.get_member(data["top_messages_members"][1][0])
                        ),
                        fill=(255, 255, 255),
                        font=self.bold_font[36],
                    )
                    align_text_center(
                        (600, 804, 935, 880),
                        text=f"{self.number_to_text_with_suffix(data['top_messages_members'][1][1])} message{'' if 0 < data['top_messages_members'][1][1] <= 1 else 's'}",
                        fill=(255, 255, 255),
                        font=self.font[36],
                    )
                draw.rounded_rectangle((50, 896, 935, 972), radius=15, fill=(32, 34, 37))
                draw.rounded_rectangle((50, 896, 600, 972), radius=15, fill=(24, 26, 27))
                if len(data["top_messages_members"]) >= 3:
                    align_text_center(
                        (50, 896, 600, 972),
                        text=self.get_member_display(
                            _object.get_member(data["top_messages_members"][2][0])
                        ),
                        fill=(255, 255, 255),
                        font=self.bold_font[36],
                    )
                    align_text_center(
                        (600, 896, 935, 972),
                        text=f"{self.number_to_text_with_suffix(data['top_messages_members'][2][1])} message{'' if 0 < data['top_messages_members'][2][1] <= 1 else 's'}",
                        fill=(255, 255, 255),
                        font=self.font[36],
                    )

                # Top Messages Channels. box = 925 / empty = 30 | 3 cases / box = 76 / empty = 16
                draw.rounded_rectangle((985, 615, 1910, 996), radius=15, fill=(47, 49, 54))
                align_text_center(
                    (1005, 625, 1005, 695),
                    text=_("Top Messages Channels"),
                    fill=(255, 255, 255),
                    font=self.bold_font[40],
                )
                image = Image.open(self.icons["#"])
                image = image.resize((70, 70))
                img.paste(image, (1820, 625, 1890, 695), mask=image.split()[3])
                data["top_messages_channels"] = list(data["top_messages_channels"].items())
                draw.rounded_rectangle((1005, 712, 1890, 788), radius=15, fill=(32, 34, 37))
                draw.rounded_rectangle((1005, 712, 1555, 788), radius=15, fill=(24, 26, 27))
                if len(data["top_messages_channels"]) >= 1:
                    align_text_center(
                        (1005, 712, 1555, 788),
                        text=self.remove_unprintable_characters(
                            _object.get_channel(data["top_messages_channels"][0][0]).name
                        ),
                        fill=(255, 255, 255),
                        font=self.bold_font[36],
                    )
                    align_text_center(
                        (1555, 712, 1890, 788),
                        text=f"{self.number_to_text_with_suffix(data['top_messages_channels'][0][1])} message{'' if 0 < data['top_messages_channels'][0][1] <= 1 else 's'}",
                        fill=(255, 255, 255),
                        font=self.font[36],
                    )
                draw.rounded_rectangle((1005, 804, 1890, 880), radius=15, fill=(32, 34, 37))
                draw.rounded_rectangle((1005, 804, 1555, 880), radius=15, fill=(24, 26, 27))
                if len(data["top_messages_channels"]) >= 2:
                    align_text_center(
                        (1005, 804, 1555, 880),
                        text=self.remove_unprintable_characters(
                            _object.get_channel(data["top_messages_channels"][1][0]).name
                        ),
                        fill=(255, 255, 255),
                        font=self.bold_font[36],
                    )
                    align_text_center(
                        (1555, 804, 1890, 880),
                        text=f"{self.number_to_text_with_suffix(data['top_messages_channels'][1][1])} message{'' if 0 < data['top_messages_channels'][1][1] <= 1 else 's'}",
                        fill=(255, 255, 255),
                        font=self.font[36],
                    )
                draw.rounded_rectangle((1005, 896, 1890, 972), radius=15, fill=(32, 34, 37))
                draw.rounded_rectangle((1005, 896, 1555, 972), radius=15, fill=(24, 26, 27))
                if len(data["top_messages_channels"]) >= 3:
                    align_text_center(
                        (1005, 896, 1555, 972),
                        text=self.remove_unprintable_characters(
                            _object.get_channel(data["top_messages_channels"][2][0]).name
                        ),
                        fill=(255, 255, 255),
                        font=self.bold_font[36],
                    )
                    align_text_center(
                        (1555, 896, 1890, 972),
                        text=f"{self.number_to_text_with_suffix(data['top_messages_channels'][2][1])} message{'' if 0 < data['top_messages_channels'][2][1] <= 1 else 's'}",
                        fill=(255, 255, 255),
                        font=self.font[36],
                    )

            elif _type == "voice":
                # Server Lookback. box = 606 / empty = 30 | 1 case / box = 264 / empty = 0
                draw.rounded_rectangle((30, 204, 636, 585), radius=15, fill=(47, 49, 54))
                align_text_center(
                    (50, 214, 50, 284),
                    text=_("Server Lookback"),
                    fill=(255, 255, 255),
                    font=self.bold_font[40],
                )
                image = Image.open(self.icons["history"])
                image = image.resize((70, 70))
                img.paste(image, (546, 214, 616, 284), mask=image.split()[3])
                draw.rounded_rectangle((50, 301, 616, 565), radius=15, fill=(32, 34, 37))
                align_text_center(
                    (50, 351, 616, 433),
                    text=f"{self.number_to_text_with_suffix(data['server_lookback'])}",
                    fill=(255, 255, 255),
                    font=self.bold_font[60],
                )
                align_text_center(
                    (50, 433, 616, 515),
                    text=f"hour{'' if 0 < data['server_lookback'] <= 1 else 's'}",
                    fill=(255, 255, 255),
                    font=self.bold_font[60],
                )

                # Voice Activity. box = 606 / empty = 30 | 3 cases / box = 76 / empty = 16
                draw.rounded_rectangle((668, 204, 1274, 585), radius=15, fill=(47, 49, 54))
                align_text_center(
                    (688, 214, 688, 284),
                    text=_("Voice Activity"),
                    fill=(255, 255, 255),
                    font=self.bold_font[40],
                )
                image = Image.open(self.icons["sound"])
                image = image.resize((70, 70))
                img.paste(image, (1184, 214, 1254, 284), mask=image.split()[3])
                draw.rounded_rectangle((688, 301, 1254, 377), radius=15, fill=(32, 34, 37))
                draw.rounded_rectangle((688, 301, 910, 377), radius=15, fill=(24, 26, 27))
                align_text_center(
                    (688, 301, 910, 377),
                    text=_("1d"),
                    fill=(255, 255, 255),
                    font=self.bold_font[36],
                )
                align_text_center(
                    (910, 301, 1254, 377),
                    text=f"{self.number_to_text_with_suffix(data['voice_activity'][1])} hour{'' if 0 < data['voice_activity'][1] <= 1 else 's'}",
                    fill=(255, 255, 255),
                    font=self.font[36],
                )
                draw.rounded_rectangle((688, 395, 1254, 471), radius=15, fill=(32, 34, 37))
                draw.rounded_rectangle((688, 395, 910, 471), radius=15, fill=(24, 26, 27))
                align_text_center(
                    (688, 395, 910, 471),
                    text=_("7d"),
                    fill=(255, 255, 255),
                    font=self.bold_font[36],
                )
                align_text_center(
                    (910, 395, 1254, 471),
                    text=f"{self.number_to_text_with_suffix(data['voice_activity'][7])} hour{'' if 0 < data['voice_activity'][7] <= 1 else 's'}",
                    fill=(255, 255, 255),
                    font=self.font[36],
                )
                draw.rounded_rectangle((688, 489, 1254, 565), radius=15, fill=(32, 34, 37))
                draw.rounded_rectangle((688, 489, 910, 565), radius=15, fill=(24, 26, 27))
                align_text_center(
                    (688, 489, 910, 565),
                    text=_("30d"),
                    fill=(255, 255, 255),
                    font=self.bold_font[36],
                )
                align_text_center(
                    (910, 489, 1254, 565),
                    text=f"{self.number_to_text_with_suffix(data['voice_activity'][30])} hour{'' if 0 < data['voice_activity'][30] <= 1 else 's'}",
                    fill=(255, 255, 255),
                    font=self.font[36],
                )

                # Contributors. box = 606 / empty = 30 | 3 cases / box = 76 / empty = 16
                draw.rounded_rectangle((1306, 204, 1912, 585), radius=15, fill=(47, 49, 54))
                align_text_center(
                    (1326, 214, 1326, 284),
                    text=_("Contributors"),
                    fill=(255, 255, 255),
                    font=self.bold_font[40],
                )
                image = Image.open(self.icons["person"])
                image = image.resize((70, 70))
                img.paste(image, (1822, 214, 1892, 284), mask=image.split()[3])
                draw.rounded_rectangle((1326, 301, 1892, 377), radius=15, fill=(32, 34, 37))
                draw.rounded_rectangle((1326, 301, 1548, 377), radius=15, fill=(24, 26, 27))
                align_text_center(
                    (1326, 301, 1548, 377),
                    text=_("1d"),
                    fill=(255, 255, 255),
                    font=self.bold_font[36],
                )
                align_text_center(
                    (1548, 301, 1892, 377),
                    text=f"{self.number_to_text_with_suffix(data['contributors'][1])} member{'' if 0 < data['contributors'][1] <= 1 else 's'}",
                    fill=(255, 255, 255),
                    font=self.font[36],
                )
                draw.rounded_rectangle((1326, 395, 1892, 471), radius=15, fill=(32, 34, 37))
                draw.rounded_rectangle((1326, 395, 1548, 471), radius=15, fill=(24, 26, 27))
                align_text_center(
                    (1326, 395, 1548, 471),
                    text=_("7d"),
                    fill=(255, 255, 255),
                    font=self.bold_font[36],
                )
                align_text_center(
                    (1548, 395, 1892, 471),
                    text=f"{self.number_to_text_with_suffix(data['contributors'][7])} member{'' if 0 < data['contributors'][7] <= 1 else 's'}",
                    fill=(255, 255, 255),
                    font=self.font[36],
                )
                draw.rounded_rectangle((1326, 489, 1892, 565), radius=15, fill=(32, 34, 37))
                draw.rounded_rectangle((1326, 489, 1548, 565), radius=15, fill=(24, 26, 27))
                align_text_center(
                    (1326, 489, 1548, 565),
                    text=_("30d"),
                    fill=(255, 255, 255),
                    font=self.bold_font[36],
                )
                align_text_center(
                    (1548, 489, 1892, 565),
                    text=f"{self.number_to_text_with_suffix(data['contributors'][30])} member{'' if 0 < data['contributors'][30] <= 1 else 's'}",
                    fill=(255, 255, 255),
                    font=self.font[36],
                )

                # Top Voice Members. box = 925 / empty = 30 | 3 cases / box = 76 / empty = 16
                draw.rounded_rectangle((30, 615, 955, 996), radius=15, fill=(47, 49, 54))
                align_text_center(
                    (50, 625, 50, 695),
                    text=_("Top Voice Members"),
                    fill=(255, 255, 255),
                    font=self.bold_font[40],
                )
                image = Image.open(self.icons["#"])
                image = image.resize((70, 70))
                img.paste(image, (865, 625, 935, 695), mask=image.split()[3])
                data["top_voice_members"] = list(data["top_voice_members"].items())
                draw.rounded_rectangle((50, 712, 935, 788), radius=15, fill=(32, 34, 37))
                draw.rounded_rectangle((50, 712, 600, 788), radius=15, fill=(24, 26, 27))
                if len(data["top_voice_members"]) >= 1:
                    align_text_center(
                        (50, 712, 600, 788),
                        text=self.get_member_display(
                            _object.get_member(data["top_voice_members"][0][0])
                        ),
                        fill=(255, 255, 255),
                        font=self.bold_font[36],
                    )
                    align_text_center(
                        (600, 712, 935, 788),
                        text=f"{self.number_to_text_with_suffix(data['top_voice_members'][0][1])} hour{'' if 0 < data['top_voice_members'][0][1] <= 1 else 's'}",
                        fill=(255, 255, 255),
                        font=self.font[36],
                    )
                draw.rounded_rectangle((50, 804, 935, 880), radius=15, fill=(32, 34, 37))
                draw.rounded_rectangle((50, 804, 600, 880), radius=15, fill=(24, 26, 27))
                if len(data["top_voice_members"]) >= 2:
                    align_text_center(
                        (50, 804, 600, 880),
                        text=self.get_member_display(
                            _object.get_member(data["top_voice_members"][1][0])
                        ),
                        fill=(255, 255, 255),
                        font=self.bold_font[36],
                    )
                    align_text_center(
                        (600, 804, 935, 880),
                        text=f"{self.number_to_text_with_suffix(data['top_voice_members'][1][1])} hour{'' if 0 < data['top_voice_members'][1][1] <= 1 else 's'}",
                        fill=(255, 255, 255),
                        font=self.font[36],
                    )
                draw.rounded_rectangle((50, 896, 935, 972), radius=15, fill=(32, 34, 37))
                draw.rounded_rectangle((50, 896, 600, 972), radius=15, fill=(24, 26, 27))
                if len(data["top_voice_members"]) >= 3:
                    align_text_center(
                        (50, 896, 600, 972),
                        text=self.get_member_display(
                            _object.get_member(data["top_voice_members"][2][0])
                        ),
                        fill=(255, 255, 255),
                        font=self.bold_font[36],
                    )
                    align_text_center(
                        (600, 896, 935, 972),
                        text=f"{self.number_to_text_with_suffix(data['top_voice_members'][2][1])} hour{'' if 0 < data['top_voice_members'][2][1] <= 1 else 's'}",
                        fill=(255, 255, 255),
                        font=self.font[36],
                    )

                # Top Voice Channels. box = 925 / empty = 30 | 3 cases / box = 76 / empty = 16
                draw.rounded_rectangle((985, 615, 1910, 996), radius=15, fill=(47, 49, 54))
                align_text_center(
                    (1005, 625, 1005, 695),
                    text=_("Top Voice Channels"),
                    fill=(255, 255, 255),
                    font=self.bold_font[40],
                )
                image = Image.open(self.icons["#"])
                image = image.resize((70, 70))
                img.paste(image, (1820, 625, 1890, 695), mask=image.split()[3])
                data["top_voice_channels"] = list(data["top_voice_channels"].items())
                draw.rounded_rectangle((1005, 712, 1890, 788), radius=15, fill=(32, 34, 37))
                draw.rounded_rectangle((1005, 712, 1555, 788), radius=15, fill=(24, 26, 27))
                if len(data["top_voice_channels"]) >= 1:
                    align_text_center(
                        (1005, 712, 1555, 788),
                        text=self.remove_unprintable_characters(
                            _object.get_channel(data["top_voice_channels"][0][0]).name
                        ),
                        fill=(255, 255, 255),
                        font=self.bold_font[36],
                    )
                    align_text_center(
                        (1555, 712, 1890, 788),
                        text=f"{self.number_to_text_with_suffix(data['top_voice_channels'][0][1])} hour{'' if 0 < data['top_voice_channels'][0][1] <= 1 else 's'}",
                        fill=(255, 255, 255),
                        font=self.font[36],
                    )
                draw.rounded_rectangle((1005, 804, 1890, 880), radius=15, fill=(32, 34, 37))
                draw.rounded_rectangle((1005, 804, 1555, 880), radius=15, fill=(24, 26, 27))
                if len(data["top_voice_channels"]) >= 2:
                    align_text_center(
                        (1005, 804, 1555, 880),
                        text=self.remove_unprintable_characters(
                            _object.get_channel(data["top_voice_channels"][1][0]).name
                        ),
                        fill=(255, 255, 255),
                        font=self.bold_font[36],
                    )
                    align_text_center(
                        (1555, 804, 1890, 880),
                        text=f"{self.number_to_text_with_suffix(data['top_voice_channels'][1][1])} hour{'' if 0 < data['top_voice_channels'][1][1] <= 1 else 's'}",
                        fill=(255, 255, 255),
                        font=self.font[36],
                    )
                draw.rounded_rectangle((1005, 896, 1890, 972), radius=15, fill=(32, 34, 37))
                draw.rounded_rectangle((1005, 896, 1555, 972), radius=15, fill=(24, 26, 27))
                if len(data["top_voice_channels"]) >= 3:
                    align_text_center(
                        (1005, 896, 1555, 972),
                        text=self.remove_unprintable_characters(
                            _object.get_channel(data["top_voice_channels"][2][0]).name
                        ),
                        fill=(255, 255, 255),
                        font=self.bold_font[36],
                    )
                    align_text_center(
                        (1555, 896, 1890, 972),
                        text=f"{self.number_to_text_with_suffix(data['top_voice_channels'][2][1])} hour{'' if 0 < data['top_voice_channels'][2][1] <= 1 else 's'}",
                        fill=(255, 255, 255),
                        font=self.font[36],
                    )

            elif _type == "activities":
                # Top Activities (Applications). box = 925 / empty = 30 | 30 cases / box = 76 / empty = 16
                draw.rounded_rectangle((30, 204, 955, 996), radius=15, fill=(47, 49, 54))
                align_text_center(
                    (50, 214, 50, 284),
                    text=_("Top Activities (Applications)"),
                    fill=(255, 255, 255),
                    font=self.bold_font[40],
                )
                image = Image.open(self.icons["game"])
                image = image.resize((70, 70))
                img.paste(image, (865, 214, 935, 284), mask=image.split()[3])
                top_activities = list(data["top_activities"])
                current_y = 301
                for i in range(10):
                    draw.rounded_rectangle(
                        (50, current_y, 935, current_y + 58), radius=15, fill=(32, 34, 37)
                    )
                    draw.rounded_rectangle(
                        (50, current_y, 580, current_y + 58), radius=15, fill=(24, 26, 27)
                    )
                    if len(top_activities) >= i + 1:
                        # align_text_center((50, current_y, 100, current_y + 50), text=str(i), fill=(255, 255, 255), font=self.bold_font[36])
                        # align_text_center((100, current_y, 935, current_y + 50), text=top_activities[i - 1], fill=(255, 255, 255), font=self.font[36])
                        align_text_center(
                            (50, current_y, 580, current_y + 58),
                            text=self.remove_unprintable_characters(top_activities[i][:25]),
                            fill=(255, 255, 255),
                            font=self.bold_font[36],
                        )
                        align_text_center(
                            (580, current_y, 935, current_y + 58),
                            text=f"{self.number_to_text_with_suffix(data['top_activities'][top_activities[i]])} hour{'' if 0 < data['top_activities'][top_activities[i]] <= 1 else 's'}",
                            fill=(255, 255, 255),
                            font=self.font[36],
                        )
                    current_y += 58 + 10

                # Graphic. box = 925 / empty = 30 | 1 case / box = 76 / empty = 16
                draw.rounded_rectangle((985, 204, 1910, 996), radius=15, fill=(47, 49, 54))
                align_text_center(
                    (1005, 214, 1005, 284),
                    text=_("Graphic"),
                    fill=(255, 255, 255),
                    font=self.bold_font[40],
                )
                image = Image.open(self.icons["query_stats"])
                image = image.resize((70, 70))
                img.paste(image, (1820, 214, 1890, 284), mask=image.split()[3])
                draw.rounded_rectangle((1005, 301, 1890, 976), radius=15, fill=(32, 34, 37))
                image: Image.Image = graphic
                image = image.resize((885, 675))
                img.paste(image, (1005, 301, 1890, 976))

            elif isinstance(_type, typing.Tuple):
                if _type[0] == "top":
                    # Top Messages/Voice Members/Channels. box = 925 / empty = 30 | 30 cases / box = 76 / empty = 16
                    draw.rounded_rectangle((30, 204, 955, 996), radius=15, fill=(47, 49, 54))
                    align_text_center(
                        (50, 214, 50, 284),
                        text=_("Tope")
                        + f"{_('Messages') if _type[1] == 'messages' else _('Voice')} {_('Members') if _type[2] == 'members' else _('Channels')}",
                        fill=(255, 255, 255),
                        font=self.bold_font[40],
                    )
                    image = Image.open(self.icons["person" if _type[2] == "members" else "#"])
                    image = image.resize((70, 70))
                    img.paste(image, (865, 214, 935, 284), mask=image.split()[3])
                    top = list(data[f"top_{_type[1]}_{_type[2]}"])
                    current_y = 301
                    for i in range(10):
                        draw.rounded_rectangle(
                            (50, current_y, 935, current_y + 58), radius=15, fill=(32, 34, 37)
                        )
                        draw.rounded_rectangle(
                            (50, current_y, 580, current_y + 58), radius=15, fill=(24, 26, 27)
                        )
                        if len(top) >= i + 1:
                            align_text_center(
                                (50, current_y, 580, current_y + 58),
                                text=(
                                    self.get_member_display(_object.get_member(top[i]))
                                    if _type[2] == "members"
                                    else self.remove_unprintable_characters(
                                        _object.get_channel(top[i]).name
                                    )
                                ),
                                fill=(255, 255, 255),
                                font=self.bold_font[36],
                            )
                            align_text_center(
                                (580, current_y, 935, current_y + 58),
                                text=f"{self.number_to_text_with_suffix(data[f'top_{_type[1]}_{_type[2]}'][top[i]])} {'message' if _type[1] == 'messages' else 'hour'}{'' if 0 < data[f'top_{_type[1]}_{_type[2]}'][top[i]] <= 1 else 's'}",
                                fill=(255, 255, 255),
                                font=self.font[36],
                            )
                        current_y += 58 + 10

                    # Graphic. box = 925 / empty = 30 | 1 case / box = 76 / empty = 16
                    draw.rounded_rectangle((985, 204, 1910, 996), radius=15, fill=(47, 49, 54))
                    align_text_center(
                        (1005, 214, 1005, 284),
                        text=_("Graphic"),
                        fill=(255, 255, 255),
                        font=self.bold_font[40],
                    )
                    image = Image.open(self.icons["query_stats"])
                    image = image.resize((70, 70))
                    img.paste(image, (1820, 214, 1890, 284), mask=image.split()[3])
                    draw.rounded_rectangle((1005, 301, 1890, 976), radius=15, fill=(32, 34, 37))
                    image: Image.Image = graphic
                    image = image.resize((885, 675))
                    img.paste(image, (1005, 301, 1890, 976))
                elif _type[0] == "activity":
                    # Top Members. box = 925 / empty = 30 | 30 cases / box = 76 / empty = 16
                    draw.rounded_rectangle((30, 204, 955, 996), radius=15, fill=(47, 49, 54))
                    align_text_center(
                        (50, 214, 50, 284),
                        text=_("Top Members"),
                        fill=(255, 255, 255),
                        font=self.bold_font[40],
                    )
                    image = Image.open(self.icons["person"])
                    image = image.resize((70, 70))
                    img.paste(image, (865, 214, 935, 284), mask=image.split()[3])
                    top = list(data["top_members"])
                    current_y = 301
                    for i in range(10):
                        draw.rounded_rectangle(
                            (50, current_y, 935, current_y + 58), radius=15, fill=(32, 34, 37)
                        )
                        draw.rounded_rectangle(
                            (50, current_y, 580, current_y + 58), radius=15, fill=(24, 26, 27)
                        )
                        if len(top) >= i + 1:
                            align_text_center(
                                (50, current_y, 580, current_y + 58),
                                text=self.get_member_display(_object.get_member(top[i])),
                                fill=(255, 255, 255),
                                font=self.bold_font[36],
                            )
                            align_text_center(
                                (580, current_y, 935, current_y + 58),
                                text=f"{self.number_to_text_with_suffix(data['top_members'][top[i]])} hour{'' if 0 < data['top_members'][top[i]] <= 1 else 's'}",
                                fill=(255, 255, 255),
                                font=self.font[36],
                            )
                        current_y += 58 + 10

                    # Graphic. box = 925 / empty = 30 | 1 case / box = 76 / empty = 16
                    draw.rounded_rectangle((985, 204, 1910, 996), radius=15, fill=(47, 49, 54))
                    align_text_center(
                        (1005, 214, 1005, 284),
                        text=_("Graphic"),
                        fill=(255, 255, 255),
                        font=self.bold_font[40],
                    )
                    image = Image.open(self.icons["query_stats"])
                    image = image.resize((70, 70))
                    img.paste(image, (1820, 214, 1890, 284), mask=image.split()[3])
                    draw.rounded_rectangle((1005, 301, 1890, 976), radius=15, fill=(32, 34, 37))
                    image: Image.Image = graphic
                    image = image.resize((885, 675))
                    img.paste(image, (1005, 301, 1890, 976))

            if show_graphic:
                # Graphic. box = 940 / empty = 0 | + 411 (381 + 30) / 1 case / box = 264 / empty = 0
                draw.rounded_rectangle((30, 1026, 1910, 1407 + 200), radius=15, fill=(47, 49, 54))
                align_text_center(
                    (50, 1036, 50, 1106),
                    text=_("Graphic"),
                    fill=(255, 255, 255),
                    font=self.bold_font[40],
                )
                image = Image.open(self.icons["query_stats"])
                image = image.resize((70, 70))
                img.paste(image, (1830, 1036, 1900, 1106), mask=image.split()[3])
                draw.rounded_rectangle((50, 1123, 1890, 1387 + 200), radius=15, fill=(32, 34, 37))
                image: Image.Image = graphic
                image = image.resize((1840, 464))
                img.paste(image, (50, 1123, 1890, 1387 + 200))

        elif isinstance(_object, discord.CategoryChannel):
            # Server Lookback. box = 606 / empty = 30 | 2 cases / box = 117 / empty = 30
            draw.rounded_rectangle((30, 204, 636, 585), radius=15, fill=(47, 49, 54))
            align_text_center(
                (50, 214, 50, 284),
                text=_("Server Lookback"),
                fill=(255, 255, 255),
                font=self.bold_font[40],
            )
            image = Image.open(self.icons["history"])
            image = image.resize((70, 70))
            img.paste(image, (546, 214, 616, 284), mask=image.split()[3])
            draw.rounded_rectangle((50, 301, 616, 418), radius=15, fill=(32, 34, 37))
            draw.rounded_rectangle((50, 301, 325, 418), radius=15, fill=(24, 26, 27))
            align_text_center(
                (50, 301, 325, 418), text=_("Text"), fill=(255, 255, 255), font=self.bold_font[36]
            )
            align_text_center(
                (325, 301, 616, 418),
                text=f"{self.number_to_text_with_suffix(data['server_lookback']['text'])} message{'' if 0 < data['server_lookback']['text'] <= 1 else 's'}",
                fill=(255, 255, 255),
                font=self.font[36],
            )
            draw.rounded_rectangle((50, 448, 616, 565), radius=15, fill=(32, 34, 37))
            draw.rounded_rectangle((50, 448, 325, 565), radius=15, fill=(24, 26, 27))
            align_text_center(
                (50, 448, 325, 565), text=_("Voice"), fill=(255, 255, 255), font=self.bold_font[36]
            )
            align_text_center(
                (325, 448, 616, 565),
                text=f"{self.number_to_text_with_suffix(data['server_lookback']['voice'])} hour{'' if 0 < data['server_lookback']['voice'] <= 1 else 's'}",
                fill=(255, 255, 255),
                font=self.font[36],
            )

            # Messages. box = 606 / empty = 30 | 3 cases / box = 76 / empty = 16
            draw.rounded_rectangle((668, 204, 1274, 585), radius=15, fill=(47, 49, 54))
            align_text_center(
                (688, 214, 688, 284),
                text=_("Messages"),
                fill=(255, 255, 255),
                font=self.bold_font[40],
            )
            image = Image.open(self.icons["#"])
            image = image.resize((70, 70))
            img.paste(image, (1184, 214, 1254, 284), mask=image.split()[3])
            draw.rounded_rectangle((688, 301, 1254, 377), radius=15, fill=(32, 34, 37))
            draw.rounded_rectangle((688, 301, 910, 377), radius=15, fill=(24, 26, 27))
            align_text_center(
                (688, 301, 910, 377), text=_("1d"), fill=(255, 255, 255), font=self.bold_font[36]
            )
            align_text_center(
                (910, 301, 1254, 377),
                text=f"{self.number_to_text_with_suffix(data['messages'][1])} message{'' if 0 < data['messages'][1] <= 1 else 's'}",
                fill=(255, 255, 255),
                font=self.font[36],
            )
            draw.rounded_rectangle((688, 395, 1254, 471), radius=15, fill=(32, 34, 37))
            draw.rounded_rectangle((688, 395, 910, 471), radius=15, fill=(24, 26, 27))
            align_text_center(
                (688, 395, 910, 471), text=_("7d"), fill=(255, 255, 255), font=self.bold_font[36]
            )
            align_text_center(
                (910, 395, 1254, 471),
                text=f"{self.number_to_text_with_suffix(data['messages'][7])} message{'' if 0 < data['messages'][7] <= 1 else 's'}",
                fill=(255, 255, 255),
                font=self.font[36],
            )
            draw.rounded_rectangle((688, 489, 1254, 565), radius=15, fill=(32, 34, 37))
            draw.rounded_rectangle((688, 489, 910, 565), radius=15, fill=(24, 26, 27))
            align_text_center(
                (688, 489, 910, 565), text=_("30d"), fill=(255, 255, 255), font=self.bold_font[36]
            )
            align_text_center(
                (910, 489, 1254, 565),
                text=f"{self.number_to_text_with_suffix(data['messages'][30])} message{'' if 0 < data['messages'][30] <= 1 else 's'}",
                fill=(255, 255, 255),
                font=self.font[36],
            )

            # Voice Activity. box = 606 / empty = 30 | 3 cases / box = 76 / empty = 16
            draw.rounded_rectangle((1306, 204, 1912, 585), radius=15, fill=(47, 49, 54))
            align_text_center(
                (1326, 214, 1326, 284),
                text=_("Voice Activity"),
                fill=(255, 255, 255),
                font=self.bold_font[40],
            )
            image = Image.open(self.icons["sound"])
            image = image.resize((70, 70))
            img.paste(image, (1822, 214, 1892, 284), mask=image.split()[3])
            draw.rounded_rectangle((1326, 301, 1892, 377), radius=15, fill=(32, 34, 37))
            draw.rounded_rectangle((1326, 301, 1548, 377), radius=15, fill=(24, 26, 27))
            align_text_center(
                (1326, 301, 1548, 377), text=_("1d"), fill=(255, 255, 255), font=self.bold_font[36]
            )
            align_text_center(
                (1548, 301, 1892, 377),
                text=f"{self.number_to_text_with_suffix(data['voice_activity'][1])} hour{'' if 0 < data['voice_activity'][1] <= 1 else 's'}",
                fill=(255, 255, 255),
                font=self.font[36],
            )
            draw.rounded_rectangle((1326, 395, 1892, 471), radius=15, fill=(32, 34, 37))
            draw.rounded_rectangle((1326, 395, 1548, 471), radius=15, fill=(24, 26, 27))
            align_text_center(
                (1326, 395, 1548, 471), text=_("7d"), fill=(255, 255, 255), font=self.bold_font[36]
            )
            align_text_center(
                (1548, 395, 1892, 471),
                text=f"{self.number_to_text_with_suffix(data['voice_activity'][7])} hour{'' if 0 < data['voice_activity'][7] <= 1 else 's'}",
                fill=(255, 255, 255),
                font=self.font[36],
            )
            draw.rounded_rectangle((1326, 489, 1892, 565), radius=15, fill=(32, 34, 37))
            draw.rounded_rectangle((1326, 489, 1548, 565), radius=15, fill=(24, 26, 27))
            align_text_center(
                (1326, 489, 1548, 565),
                text=_("30d"),
                fill=(255, 255, 255),
                font=self.bold_font[36],
            )
            align_text_center(
                (1548, 489, 1892, 565),
                text=f"{self.number_to_text_with_suffix(data['voice_activity'][30])} hour{'' if 0 < data['voice_activity'][30] <= 1 else 's'}",
                fill=(255, 255, 255),
                font=self.font[36],
            )

            # Top Members. box = 925 / empty = 30 | 3 cases / box = 117 / empty = 30
            draw.rounded_rectangle((30, 615, 955, 996), radius=15, fill=(47, 49, 54))
            align_text_center(
                (50, 625, 50, 695),
                text=_("Top Members"),
                fill=(255, 255, 255),
                font=self.bold_font[40],
            )
            image = Image.open(self.icons["person"])
            image = image.resize((70, 70))
            img.paste(image, (865, 625, 935, 695), mask=image.split()[3])
            image = Image.open(self.icons["#"])
            image = image.resize((70, 70))
            img.paste(image, (50, 735, 120, 805), mask=image.split()[3])
            draw.rounded_rectangle((150, 712, 935, 829), radius=15, fill=(32, 34, 37))
            draw.rounded_rectangle((150, 712, 600, 829), radius=15, fill=(24, 26, 27))
            if (
                data["top_members"]["text"]["member"] is not None
                and data["top_members"]["text"]["value"] is not None
            ):
                align_text_center(
                    (150, 712, 600, 829),
                    text=self.get_member_display(
                        _object.guild.get_member(data["top_members"]["text"]["member"])
                    ),
                    fill=(255, 255, 255),
                    font=self.bold_font[36],
                )
                align_text_center(
                    (600, 712, 935, 829),
                    text=f"{self.number_to_text_with_suffix(data['top_members']['text']['value'])} message{'' if 0 < data['top_members']['text']['value'] <= 1 else 's'}",
                    fill=(255, 255, 255),
                    font=self.font[36],
                )
            image = Image.open(self.icons["sound"])
            image = image.resize((70, 70))
            img.paste(image, (50, 882, 120, 952), mask=image.split()[3])
            draw.rounded_rectangle((150, 859, 935, 976), radius=15, fill=(32, 34, 37))
            draw.rounded_rectangle((150, 859, 600, 976), radius=15, fill=(24, 26, 27))
            if (
                data["top_members"]["voice"]["member"] is not None
                and data["top_members"]["voice"]["value"] is not None
            ):
                align_text_center(
                    (150, 859, 600, 976),
                    text=self.get_member_display(
                        _object.guild.get_member(data["top_members"]["voice"]["member"])
                    ),
                    fill=(255, 255, 255),
                    font=self.bold_font[36],
                )
                align_text_center(
                    (600, 859, 935, 976),
                    text=f"{self.number_to_text_with_suffix(data['top_members']['voice']['value'])} hour{'' if 0 < data['top_members']['voice']['value'] <= 1 else 's'}",
                    fill=(255, 255, 255),
                    font=self.font[36],
                )

            # Top Channels. box = 925 / empty = 30 | 3 cases / box = 76 / empty = 16
            draw.rounded_rectangle((985, 615, 1910, 996), radius=15, fill=(47, 49, 54))
            align_text_center(
                (1005, 625, 1005, 695),
                text=_("Top Channels"),
                fill=(255, 255, 255),
                font=self.bold_font[40],
            )
            image = Image.open(self.icons["#"])
            image = image.resize((70, 70))
            img.paste(image, (1820, 625, 1890, 695), mask=image.split()[3])
            image = Image.open(self.icons["#"])
            image = image.resize((70, 70))
            img.paste(image, (1005, 735, 1075, 805), mask=image.split()[3])
            draw.rounded_rectangle((1105, 712, 1890, 829), radius=15, fill=(32, 34, 37))
            draw.rounded_rectangle((1105, 712, 1555, 829), radius=15, fill=(24, 26, 27))
            if (
                data["top_channels"]["text"]["channel"] is not None
                and data["top_channels"]["text"]["value"] is not None
            ):
                align_text_center(
                    (1105, 712, 1555, 829),
                    text=self.remove_unprintable_characters(
                        _object.guild.get_channel(data["top_channels"]["text"]["channel"]).name
                    ),
                    fill=(255, 255, 255),
                    font=self.bold_font[36],
                )
                align_text_center(
                    (1555, 712, 1890, 829),
                    text=f"{self.number_to_text_with_suffix(data['top_channels']['text']['value'])} message{'' if 0 < data['top_channels']['text']['value'] <= 1 else 's'}",
                    fill=(255, 255, 255),
                    font=self.font[36],
                )
            image = Image.open(self.icons["sound"])
            image = image.resize((70, 70))
            img.paste(image, (1005, 882, 1075, 952), mask=image.split()[3])
            draw.rounded_rectangle((1105, 859, 1890, 976), radius=15, fill=(32, 34, 37))
            draw.rounded_rectangle((1105, 859, 1555, 976), radius=15, fill=(24, 26, 27))
            if (
                data["top_channels"]["voice"]["channel"] is not None
                and data["top_channels"]["voice"]["value"] is not None
            ):
                align_text_center(
                    (1105, 859, 1555, 976),
                    text=self.remove_unprintable_characters(
                        _object.guild.get_channel(data["top_channels"]["voice"]["channel"]).name
                    ),
                    fill=(255, 255, 255),
                    font=self.bold_font[36],
                )
                align_text_center(
                    (1555, 859, 1890, 976),
                    text=f"{self.number_to_text_with_suffix(data['top_channels']['voice']['value'])} hour{'' if 0 < data['top_channels']['voice']['value'] <= 1 else 's'}",
                    fill=(255, 255, 255),
                    font=self.font[36],
                )

        elif isinstance(_object, discord.TextChannel):
            # Server Lookback. box = 606 / empty = 30 | 1 case / box = 264 / empty = 0
            draw.rounded_rectangle((30, 204, 636, 585), radius=15, fill=(47, 49, 54))
            align_text_center(
                (50, 214, 50, 284),
                text=_("Server Lookback"),
                fill=(255, 255, 255),
                font=self.bold_font[40],
            )
            image = Image.open(self.icons["history"])
            image = image.resize((70, 70))
            img.paste(image, (546, 214, 616, 284), mask=image.split()[3])
            draw.rounded_rectangle((50, 301, 616, 565), radius=15, fill=(32, 34, 37))
            align_text_center(
                (50, 351, 616, 433),
                text=f"{self.number_to_text_with_suffix(data['server_lookback'])}",
                fill=(255, 255, 255),
                font=self.bold_font[60],
            )
            align_text_center(
                (50, 433, 616, 515),
                text=f"message{'' if 0 < data['server_lookback'] <= 1 else 's'}",
                fill=(255, 255, 255),
                font=self.bold_font[60],
            )

            # Messages. box = 606 / empty = 30 | 3 cases / box = 76 / empty = 16
            draw.rounded_rectangle((668, 204, 1274, 585), radius=15, fill=(47, 49, 54))
            align_text_center(
                (688, 214, 688, 284),
                text=_("Messages"),
                fill=(255, 255, 255),
                font=self.bold_font[40],
            )
            image = Image.open(self.icons["#"])
            image = image.resize((70, 70))
            img.paste(image, (1184, 214, 1254, 284), mask=image.split()[3])
            draw.rounded_rectangle((688, 301, 1254, 377), radius=15, fill=(32, 34, 37))
            draw.rounded_rectangle((688, 301, 910, 377), radius=15, fill=(24, 26, 27))
            align_text_center(
                (688, 301, 910, 377), text=_("1d"), fill=(255, 255, 255), font=self.bold_font[36]
            )
            align_text_center(
                (910, 301, 1254, 377),
                text=f"{self.number_to_text_with_suffix(data['messages'][1])} message{'' if 0 < data['messages'][1] <= 1 else 's'}",
                fill=(255, 255, 255),
                font=self.font[36],
            )
            draw.rounded_rectangle((688, 395, 1254, 471), radius=15, fill=(32, 34, 37))
            draw.rounded_rectangle((688, 395, 910, 471), radius=15, fill=(24, 26, 27))
            align_text_center(
                (688, 395, 910, 471), text=_("7d"), fill=(255, 255, 255), font=self.bold_font[36]
            )
            align_text_center(
                (910, 395, 1254, 471),
                text=f"{self.number_to_text_with_suffix(data['messages'][7])} message{'' if 0 < data['messages'][7] <= 1 else 's'}",
                fill=(255, 255, 255),
                font=self.font[36],
            )
            draw.rounded_rectangle((688, 489, 1254, 565), radius=15, fill=(32, 34, 37))
            draw.rounded_rectangle((688, 489, 910, 565), radius=15, fill=(24, 26, 27))
            align_text_center(
                (688, 489, 910, 565), text=_("30d"), fill=(255, 255, 255), font=self.bold_font[36]
            )
            align_text_center(
                (910, 489, 1254, 565),
                text=f"{self.number_to_text_with_suffix(data['messages'][30])} message{'' if 0 < data['messages'][30] <= 1 else 's'}",
                fill=(255, 255, 255),
                font=self.font[36],
            )

            # Contributors. box = 606 / empty = 30 | 3 cases / box = 76 / empty = 16
            draw.rounded_rectangle((1306, 204, 1912, 585), radius=15, fill=(47, 49, 54))
            align_text_center(
                (1326, 214, 1326, 284),
                text=_("Contributors"),
                fill=(255, 255, 255),
                font=self.bold_font[40],
            )
            image = Image.open(self.icons["person"])
            image = image.resize((70, 70))
            img.paste(image, (1822, 214, 1892, 284), mask=image.split()[3])
            draw.rounded_rectangle((1326, 301, 1892, 377), radius=15, fill=(32, 34, 37))
            draw.rounded_rectangle((1326, 301, 1548, 377), radius=15, fill=(24, 26, 27))
            align_text_center(
                (1326, 301, 1548, 377), text=_("1d"), fill=(255, 255, 255), font=self.bold_font[36]
            )
            align_text_center(
                (1548, 301, 1892, 377),
                text=f"{self.number_to_text_with_suffix(data['contributors'][1])} member{'' if 0 < data['contributors'][1] <= 1 else 's'}",
                fill=(255, 255, 255),
                font=self.font[36],
            )
            draw.rounded_rectangle((1326, 395, 1892, 471), radius=15, fill=(32, 34, 37))
            draw.rounded_rectangle((1326, 395, 1548, 471), radius=15, fill=(24, 26, 27))
            align_text_center(
                (1326, 395, 1548, 471), text=_("7d"), fill=(255, 255, 255), font=self.bold_font[36]
            )
            align_text_center(
                (1548, 395, 1892, 471),
                text=f"{self.number_to_text_with_suffix(data['contributors'][7])} member{'' if 0 < data['contributors'][7] <= 1 else 's'}",
                fill=(255, 255, 255),
                font=self.font[36],
            )
            draw.rounded_rectangle((1326, 489, 1892, 565), radius=15, fill=(32, 34, 37))
            draw.rounded_rectangle((1326, 489, 1548, 565), radius=15, fill=(24, 26, 27))
            align_text_center(
                (1326, 489, 1548, 565),
                text=_("30d"),
                fill=(255, 255, 255),
                font=self.bold_font[36],
            )
            align_text_center(
                (1548, 489, 1892, 565),
                text=f"{self.number_to_text_with_suffix(data['contributors'][30])} member{'' if 0 < data['contributors'][30] <= 1 else 's'}",
                fill=(255, 255, 255),
                font=self.font[36],
            )

            # Server Rank. box = 606 / empty = 30 | 1 case / box = 264 / empty = 0
            draw.rounded_rectangle((30, 615, 636, 996), radius=15, fill=(47, 49, 54))
            align_text_center(
                (50, 625, 50, 695),
                text=_("Server Rank"),
                fill=(255, 255, 255),
                font=self.bold_font[40],
            )
            image = Image.open(self.icons["trophy"])
            image = image.resize((70, 70))
            img.paste(image, (546, 625, 616, 695), mask=image.split()[3])
            draw.rounded_rectangle((50, 712, 616, 976), radius=15, fill=(32, 34, 37))
            align_text_center(
                (50, 712, 616, 976),
                text=f"#{data['server_rank']}" if data["server_rank"] is not None else "No data.",
                fill=(255, 255, 255),
                font=self.bold_font[60],
            )

            # Top Messages Members. box = 925 / empty = 30 | 3 cases / box = 76 / empty = 16
            draw.rounded_rectangle((668, 615, 1593, 996), radius=15, fill=(47, 49, 54))
            align_text_center(
                (688, 625, 688, 695),
                text=_("Top Messages Members"),
                fill=(255, 255, 255),
                font=self.bold_font[40],
            )
            image = Image.open(self.icons["#"])
            image = image.resize((70, 70))
            img.paste(image, (1503, 625, 1573, 695), mask=image.split()[3])
            data["top_messages_members"] = list(data["top_messages_members"].items())
            draw.rounded_rectangle((688, 712, 1573, 788), radius=15, fill=(32, 34, 37))
            draw.rounded_rectangle((688, 712, 1218, 788), radius=15, fill=(24, 26, 27))
            if len(data["top_messages_members"]) >= 1:
                align_text_center(
                    (688, 712, 1218, 788),
                    text=self.get_member_display(
                        _object.guild.get_member(data["top_messages_members"][0][0])
                    ),
                    fill=(255, 255, 255),
                    font=self.bold_font[36],
                )
                align_text_center(
                    (1218, 712, 1573, 788),
                    text=f"{self.number_to_text_with_suffix(data['top_messages_members'][0][1])} message{'' if 0 < data['top_messages_members'][0][1] <= 1 else 's'}",
                    fill=(255, 255, 255),
                    font=self.font[36],
                )
            draw.rounded_rectangle((688, 804, 1573, 880), radius=15, fill=(32, 34, 37))
            draw.rounded_rectangle((688, 804, 1218, 880), radius=15, fill=(24, 26, 27))
            if len(data["top_messages_members"]) >= 2:
                align_text_center(
                    (688, 804, 1218, 880),
                    text=self.get_member_display(
                        _object.guild.get_member(data["top_messages_members"][1][0])
                    ),
                    fill=(255, 255, 255),
                    font=self.bold_font[36],
                )
                align_text_center(
                    (1218, 804, 1573, 880),
                    text=f"{self.number_to_text_with_suffix(data['top_messages_members'][1][1])} message{'' if 0 < data['top_messages_members'][1][1] <= 1 else 's'}",
                    fill=(255, 255, 255),
                    font=self.font[36],
                )
            draw.rounded_rectangle((688, 896, 1573, 972), radius=15, fill=(32, 34, 37))
            draw.rounded_rectangle((688, 896, 1218, 972), radius=15, fill=(24, 26, 27))
            if len(data["top_messages_members"]) >= 3:
                align_text_center(
                    (688, 896, 1218, 972),
                    text=self.get_member_display(
                        _object.guild.get_member(data["top_messages_members"][2][0])
                    ),
                    fill=(255, 255, 255),
                    font=self.bold_font[36],
                )
                align_text_center(
                    (1218, 896, 1573, 972),
                    text=f"{self.number_to_text_with_suffix(data['top_messages_members'][2][1])} message{'' if 0 < data['top_messages_members'][2][1] <= 1 else 's'}",
                    fill=(255, 255, 255),
                    font=self.font[36],
                )

            if show_graphic:
                # Graphic. box = 940 / empty = 0 | + 411 (381 + 30) / 1 case / box = 264 / empty = 0
                draw.rounded_rectangle((30, 1026, 1910, 1407 + 200), radius=15, fill=(47, 49, 54))
                align_text_center(
                    (50, 1036, 50, 1106),
                    text=_("Graphic"),
                    fill=(255, 255, 255),
                    font=self.bold_font[40],
                )
                image = Image.open(self.icons["query_stats"])
                image = image.resize((70, 70))
                img.paste(image, (1830, 1036, 1900, 1106), mask=image.split()[3])
                draw.rounded_rectangle((50, 1123, 1890, 1387 + 200), radius=15, fill=(32, 34, 37))
                image: Image.Image = graphic
                image = image.resize((1840, 464))
                img.paste(image, (50, 1123, 1890, 1387 + 200))

        elif isinstance(_object, discord.VoiceChannel):
            # Server Lookback. box = 606 / empty = 30 | 1 case / box = 264 / empty = 0
            draw.rounded_rectangle((30, 204, 636, 585), radius=15, fill=(47, 49, 54))
            align_text_center(
                (50, 214, 50, 284),
                text=_("Server Lookback"),
                fill=(255, 255, 255),
                font=self.bold_font[40],
            )
            image = Image.open(self.icons["history"])
            image = image.resize((70, 70))
            img.paste(image, (546, 214, 616, 284), mask=image.split()[3])
            draw.rounded_rectangle((50, 301, 616, 565), radius=15, fill=(32, 34, 37))
            align_text_center(
                (50, 351, 616, 433),
                text=f"{self.number_to_text_with_suffix(data['server_lookback'])}",
                fill=(255, 255, 255),
                font=self.bold_font[60],
            )
            align_text_center(
                (50, 433, 616, 515),
                text=f"hour{'' if 0 < data['server_lookback'] <= 1 else 's'}",
                fill=(255, 255, 255),
                font=self.bold_font[60],
            )

            # Voice Activity. box = 606 / empty = 30 | 3 cases / box = 76 / empty = 16
            draw.rounded_rectangle((668, 204, 1274, 585), radius=15, fill=(47, 49, 54))
            align_text_center(
                (688, 214, 688, 284),
                text=_("Voice Activity"),
                fill=(255, 255, 255),
                font=self.bold_font[40],
            )
            image = Image.open(self.icons["sound"])
            image = image.resize((70, 70))
            img.paste(image, (1184, 214, 1254, 284), mask=image.split()[3])
            draw.rounded_rectangle((688, 301, 1254, 377), radius=15, fill=(32, 34, 37))
            draw.rounded_rectangle((688, 301, 910, 377), radius=15, fill=(24, 26, 27))
            align_text_center(
                (688, 301, 910, 377), text=_("1d"), fill=(255, 255, 255), font=self.bold_font[36]
            )
            align_text_center(
                (910, 301, 1254, 377),
                text=f"{self.number_to_text_with_suffix(data['voice_activity'][1])} hour{'' if 0 < data['voice_activity'][1] <= 1 else 's'}",
                fill=(255, 255, 255),
                font=self.font[36],
            )
            draw.rounded_rectangle((688, 395, 1254, 471), radius=15, fill=(32, 34, 37))
            draw.rounded_rectangle((688, 395, 910, 471), radius=15, fill=(24, 26, 27))
            align_text_center(
                (688, 395, 910, 471), text=_("7d"), fill=(255, 255, 255), font=self.bold_font[36]
            )
            align_text_center(
                (910, 395, 1254, 471),
                text=f"{self.number_to_text_with_suffix(data['voice_activity'][7])} hour{'' if 0 < data['voice_activity'][7] <= 1 else 's'}",
                fill=(255, 255, 255),
                font=self.font[36],
            )
            draw.rounded_rectangle((688, 489, 1254, 565), radius=15, fill=(32, 34, 37))
            draw.rounded_rectangle((688, 489, 910, 565), radius=15, fill=(24, 26, 27))
            align_text_center(
                (688, 489, 910, 565), text=_("30d"), fill=(255, 255, 255), font=self.bold_font[36]
            )
            align_text_center(
                (910, 489, 1254, 565),
                text=f"{self.number_to_text_with_suffix(data['voice_activity'][30])} hour{'' if 0 < data['voice_activity'][30] <= 1 else 's'}",
                fill=(255, 255, 255),
                font=self.font[36],
            )

            # Contributors. box = 606 / empty = 30 | 3 cases / box = 76 / empty = 16
            draw.rounded_rectangle((1306, 204, 1912, 585), radius=15, fill=(47, 49, 54))
            align_text_center(
                (1326, 214, 1326, 284),
                text=_("Contributors"),
                fill=(255, 255, 255),
                font=self.bold_font[40],
            )
            image = Image.open(self.icons["person"])
            image = image.resize((70, 70))
            img.paste(image, (1822, 214, 1892, 284), mask=image.split()[3])
            draw.rounded_rectangle((1326, 301, 1892, 377), radius=15, fill=(32, 34, 37))
            draw.rounded_rectangle((1326, 301, 1548, 377), radius=15, fill=(24, 26, 27))
            align_text_center(
                (1326, 301, 1548, 377), text=_("1d"), fill=(255, 255, 255), font=self.bold_font[36]
            )
            align_text_center(
                (1548, 301, 1892, 377),
                text=f"{self.number_to_text_with_suffix(data['contributors'][1])} member{'' if 0 < data['contributors'][1] <= 1 else 's'}",
                fill=(255, 255, 255),
                font=self.font[36],
            )
            draw.rounded_rectangle((1326, 395, 1892, 471), radius=15, fill=(32, 34, 37))
            draw.rounded_rectangle((1326, 395, 1548, 471), radius=15, fill=(24, 26, 27))
            align_text_center(
                (1326, 395, 1548, 471), text=_("7d"), fill=(255, 255, 255), font=self.bold_font[36]
            )
            align_text_center(
                (1548, 395, 1892, 471),
                text=f"{self.number_to_text_with_suffix(data['contributors'][7])} member{'' if 0 < data['contributors'][7] <= 1 else 's'}",
                fill=(255, 255, 255),
                font=self.font[36],
            )
            draw.rounded_rectangle((1326, 489, 1892, 565), radius=15, fill=(32, 34, 37))
            draw.rounded_rectangle((1326, 489, 1548, 565), radius=15, fill=(24, 26, 27))
            align_text_center(
                (1326, 489, 1548, 565),
                text=_("30d"),
                fill=(255, 255, 255),
                font=self.bold_font[36],
            )
            align_text_center(
                (1548, 489, 1892, 565),
                text=f"{self.number_to_text_with_suffix(data['contributors'][30])} member{'' if 0 < data['contributors'][30] <= 1 else 's'}",
                fill=(255, 255, 255),
                font=self.font[36],
            )

            # Server Rank. box = 606 / empty = 30 | 1 case / box = 264 / empty = 0
            draw.rounded_rectangle((30, 615, 636, 996), radius=15, fill=(47, 49, 54))
            align_text_center(
                (50, 625, 50, 695),
                text=_("Server Rank"),
                fill=(255, 255, 255),
                font=self.bold_font[40],
            )
            image = Image.open(self.icons["trophy"])
            image = image.resize((70, 70))
            img.paste(image, (546, 625, 616, 695), mask=image.split()[3])
            draw.rounded_rectangle((50, 712, 616, 976), radius=15, fill=(32, 34, 37))
            align_text_center(
                (50, 712, 616, 976),
                text=f"#{data['server_rank']}" if data["server_rank"] is not None else "No data.",
                fill=(255, 255, 255),
                font=self.bold_font[60],
            )

            # Top Voice Members. box = 925 / empty = 30 | 3 cases / box = 76 / empty = 16
            draw.rounded_rectangle((668, 615, 1593, 996), radius=15, fill=(47, 49, 54))
            align_text_center(
                (688, 625, 688, 695),
                text=_("Top Voice Members"),
                fill=(255, 255, 255),
                font=self.bold_font[40],
            )
            image = Image.open(self.icons["sound"])
            image = image.resize((70, 70))
            img.paste(image, (1503, 625, 1573, 695), mask=image.split()[3])
            data["top_voice_members"] = list(data["top_voice_members"].items())
            draw.rounded_rectangle((688, 712, 1573, 788), radius=15, fill=(32, 34, 37))
            draw.rounded_rectangle((688, 712, 1218, 788), radius=15, fill=(24, 26, 27))
            if len(data["top_voice_members"]) >= 1:
                align_text_center(
                    (688, 712, 1218, 788),
                    text=self.get_member_display(
                        _object.guild.get_member(data["top_voice_members"][0][0])
                    ),
                    fill=(255, 255, 255),
                    font=self.bold_font[36],
                )
                align_text_center(
                    (1218, 712, 1573, 788),
                    text=f"{self.number_to_text_with_suffix(data['top_voice_members'][0][1])} hour{'' if 0 < data['top_voice_members'][0][1] <= 1 else 's'}",
                    fill=(255, 255, 255),
                    font=self.font[36],
                )
            draw.rounded_rectangle((688, 804, 1573, 880), radius=15, fill=(32, 34, 37))
            draw.rounded_rectangle((688, 804, 1218, 880), radius=15, fill=(24, 26, 27))
            if len(data["top_voice_members"]) >= 2:
                align_text_center(
                    (688, 804, 1218, 880),
                    text=self.get_member_display(
                        _object.guild.get_member(data["top_voice_members"][1][0])
                    ),
                    fill=(255, 255, 255),
                    font=self.bold_font[36],
                )
                align_text_center(
                    (1218, 804, 1573, 880),
                    text=f"{self.number_to_text_with_suffix(data['top_voice_members'][1][1])} hour{'' if 0 < data['top_voice_members'][1][1] <= 1 else 's'}",
                    fill=(255, 255, 255),
                    font=self.font[36],
                )
            draw.rounded_rectangle((688, 896, 1573, 972), radius=15, fill=(32, 34, 37))
            draw.rounded_rectangle((688, 896, 1218, 972), radius=15, fill=(24, 26, 27))
            if len(data["top_voice_members"]) >= 3:
                align_text_center(
                    (688, 896, 1218, 972),
                    text=self.get_member_display(
                        _object.guild.get_member(data["top_voice_members"][2][0])
                    ),
                    fill=(255, 255, 255),
                    font=self.bold_font[36],
                )
                align_text_center(
                    (1218, 896, 1573, 972),
                    text=f"{self.number_to_text_with_suffix(data['top_voice_members'][2][1])} hour{'' if 0 < data['top_voice_members'][2][1] <= 1 else 's'}",
                    fill=(255, 255, 255),
                    font=self.font[36],
                )

            if show_graphic:
                # Graphic. box = 940 / empty = 0 | + 411 (381 + 30) / 1 case / box = 264 / empty = 0
                draw.rounded_rectangle((30, 1026, 1910, 1407 + 200), radius=15, fill=(47, 49, 54))
                align_text_center(
                    (50, 1036, 50, 1106),
                    text=_("Graphic"),
                    fill=(255, 255, 255),
                    font=self.bold_font[40],
                )
                image = Image.open(self.icons["query_stats"])
                image = image.resize((70, 70))
                img.paste(image, (1830, 1036, 1900, 1106), mask=image.split()[3])
                draw.rounded_rectangle((50, 1123, 1890, 1387 + 200), radius=15, fill=(32, 34, 37))
                image: Image.Image = graphic
                image = image.resize((1840, 464))
                img.paste(image, (50, 1123, 1890, 1387 + 200))

        utc_now = datetime.datetime.now(tz=datetime.timezone.utc)
        tracking_data_start_time = max(
            first_loading_time,
            (_object if isinstance(_object, discord.Guild) else _object.guild).me.joined_at,
        )
        tracking_data_start_time = tracking_data_start_time.replace(
            second=utc_now.second,
            minute=utc_now.minute
            if (utc_now - tracking_data_start_time)
            > datetime.timedelta(seconds=3600 * 24 * 7)
            else tracking_data_start_time.minute,
            hour=utc_now.hour
            if (utc_now - tracking_data_start_time)
            > datetime.timedelta(seconds=3600 * 24 * 30)
            else tracking_data_start_time.hour,
            day=utc_now.day
            if (utc_now - tracking_data_start_time)
            > datetime.timedelta(seconds=3600 * 24 * 365)
            else tracking_data_start_time.day,
        )
        if show_graphic:
            if default_state:
                image = Image.open(self.icons["history"])
                image = image.resize((50, 50))
                img.paste(image, (30, 1427 + 200, 80, 1477 + 200), mask=image.split()[3])
                align_text_center(
                    (90, 1427 + 200, 90, 1477 + 200),
                    text=_("Tracking data in this server for {interval_string}.").format(
                        interval_string=CogsUtils.get_interval_string(
                            tracking_data_start_time, utc_now=utc_now
                        )
                    ),
                    fill=(255, 255, 255),
                    font=self.bold_font[30],
                )
            if members_type != "both":
                members_type_text = _("Only {members_type} are taken into account.").format(
                    members_type=members_type
                )
                image = Image.open(self.icons["person"])
                image = image.resize((50, 50))
                img.paste(
                    image,
                    (
                        1942 - 30 - self.bold_font[30].getbbox(members_type_text)[2] - 10 - 50,
                        1427 + 200,
                        1942 - 30 - self.bold_font[30].getbbox(members_type_text)[2] - 10,
                        1477 + 200,
                    ),
                    mask=image.split()[3],
                )
                align_text_center(
                    (
                        1942 - 30 - self.bold_font[30].getbbox(members_type_text)[2],
                        1427 + 200,
                        1942 - 30 - self.bold_font[30].getbbox(members_type_text)[2],
                        1477 + 200,
                    ),
                    text=members_type_text,
                    fill=(255, 255, 255),
                    font=self.bold_font[30],
                )
        else:
            if default_state:
                image = Image.open(self.icons["history"])
                image = image.resize((50, 50))
                img.paste(image, (30, 1016, 80, 1066), mask=image.split()[3])
                align_text_center(
                    (90, 1016, 90, 1066),
                    text=_("Tracking data in this server for {interval_string}.").format(
                        interval_string=CogsUtils.get_interval_string(
                            tracking_data_start_time, utc_now=utc_now
                        )
                    ),
                    fill=(255, 255, 255),
                    font=self.bold_font[30],
                )
            if members_type != "both":
                members_type_text = _("Only {members_type} are taken into account.").format(
                    members_type=members_type
                )
                image = Image.open(self.icons["person"])
                image = image.resize((50, 50))
                img.paste(
                    image,
                    (
                        1942 - 30 - self.bold_font[30].getbbox(members_type_text)[2] - 10 - 50,
                        1016,
                        1942 - 30 - self.bold_font[30].getbbox(members_type_text)[2] - 10,
                        1066,
                    ),
                    mask=image.split()[3],
                )
                align_text_center(
                    (
                        1942 - 30 - self.bold_font[30].getbbox(members_type_text)[2],
                        1016,
                        1942 - 30 - self.bold_font[30].getbbox(members_type_text)[2],
                        1066,
                    ),
                    text=members_type_text,
                    fill=(255, 255, 255),
                    font=self.bold_font[30],
                )

        if not to_file:
            return img
        buffer = io.BytesIO()
        img.save(buffer, format="png", optimize=True)
        buffer.seek(0)
        return discord.File(buffer, filename="image.png")

    async def generate_image(
        self,
        _object: typing.Union[
            discord.Member,
            discord.Role,
            discord.Guild,
            typing.Tuple[
                discord.Guild,
                typing.Union[
                    typing.Literal["messages", "voice", "activities"],
                    typing.Tuple[
                        typing.Literal["top"],
                        typing.Literal["messages", "voice"],
                        typing.Literal["members", "channels"],
                    ],
                    typing.Tuple[typing.Literal["activity"], str],
                ],
            ],
            discord.CategoryChannel,
            discord.TextChannel,
            discord.VoiceChannel,
        ],
        members_type: typing.Literal["humans", "bots", "both"] = "humans",
        show_graphic: bool = False,
        data: typing.Optional[dict] = None,
        to_file: bool = True,
    ) -> typing.Union[Image.Image, discord.File]:
        if isinstance(_object, typing.Tuple):
            _object, _type = _object
        else:
            _type = None
        img: Image.Image = await self.generate_prefix_image(
            _object if _type is None else (_object, _type),
            size=(1942, 1437 + 200 + 70 if show_graphic else 1026 + 70),
            to_file=False,
        )  # (1940, 1481) / 1942 + 636
        if data is None:
            data = await self.get_data(
                _object if _type is None else (_object, _type), members_type=members_type
            )
        if show_graphic:
            graphic = await self.generate_graphic(
                _object, size=(1840, 464), data=data, to_file=False
            )
        elif _type == "activities" or (
            isinstance(_type, typing.Tuple) and _type[0] in ["top", "activity"]
        ):
            graphic = await self.generate_graphic(
                _object, size=(885, 675), data=data, to_file=False
            )
        else:
            graphic = None
        return await asyncio.to_thread(
            self._generate_image,
            _object=_object if _type is None else (_object, _type),
            members_type=members_type,
            data=data,
            to_file=to_file,
            img=img,
            show_graphic=show_graphic,
            graphic=graphic,
            default_state=await self.config.default_state(),
            first_loading_time=datetime.datetime.fromtimestamp(
                await self.config.first_loading_time(), tz=datetime.timezone.utc
            ),
        )

    @commands.guild_only()
    @commands.bot_has_permissions(attach_files=True)
    @commands.hybrid_group(invoke_without_command=True)
    async def guildstats(
        self,
        ctx: commands.Context,
        members_type: typing.Optional[typing.Literal["humans", "bots", "both"]] = "humans",
        show_graphic: typing.Optional[bool] = False,
        *,
        _object: ObjectConverter,
    ) -> None:
        """Generate images with messages and voice stats, for members, roles, guilds, categories, text channels, voice channels and activities."""
        # if _object is None:
        #     _object = ctx.guild
        if not (
            enabled_state
            if (enabled_state := await self.config.guild(ctx.guild).enabled()) is not None
            else await self.config.default_state()
        ):
            raise commands.UserFeedbackCheckFailure(
                _(
                    "This cog is disabled in this guild. Administrators can enable it with the command `{prefix}guildstats enable`."
                ).format(prefix=ctx.prefix)
            )
        ignored_users = await self.config.ignored_users()
        if isinstance(_object, discord.Member) and _object.id in ignored_users:
            raise commands.UserFeedbackCheckFailure(
                _(
                    "This user is in the ignored users list (`{prefix}guildstats ignoreme`)."
                ).format(prefix=ctx.prefix)
            )
        # embed: discord.Embed = discord.Embed()
        # embed.set_image(url="attachment://image.png")
        await GuildStatsView(
            cog=self,
            _object=_object,
            members_type=("bots" if _object.bot else "humans")
            if isinstance(_object, discord.Member)
            else members_type,
            show_graphic_in_main=show_graphic if _object != "activities" else False,
            graphic_mode=False,
        ).start(ctx)

    @guildstats.command()
    async def member(
        self,
        ctx: commands.Context,
        show_graphic: typing.Optional[bool] = False,
        *,
        member: discord.Member = None,
    ) -> None:
        """Display stats for a specified member."""
        if member is None:
            member = ctx.author
        if not (
            enabled_state
            if (enabled_state := await self.config.guild(ctx.guild).enabled()) is not None
            else await self.config.default_state()
        ):
            raise commands.UserFeedbackCheckFailure(
                _(
                    "This cog is disabled in this guild. Administrators can enable it with the command `{prefix}guildstats enable`."
                ).format(prefix=ctx.prefix)
            )
        ignored_users = await self.config.ignored_users()
        if member.id in ignored_users:
            raise commands.UserFeedbackCheckFailure(
                _(
                    "This user is in the ignored users list (`{prefix}guildstats ignoreme`)."
                ).format(prefix=ctx.prefix)
            )
        await GuildStatsView(
            cog=self,
            _object=member,
            members_type="bots" if member.bot else "humans",
            show_graphic_in_main=show_graphic,
            graphic_mode=False,
        ).start(ctx)

    @guildstats.command()
    async def role(
        self,
        ctx: commands.Context,
        show_graphic: typing.Optional[bool] = False,
        *,
        role: discord.Role = None,
    ) -> None:
        """Display stats for a specified role."""
        if role is None:
            role = ctx.author.top_role
        if not (
            enabled_state
            if (enabled_state := await self.config.guild(ctx.guild).enabled()) is not None
            else await self.config.default_state()
        ):
            raise commands.UserFeedbackCheckFailure(
                _(
                    "This cog is disabled in this guild. Administrators can enable it with the command `{prefix}guildstats enable`."
                ).format(prefix=ctx.prefix)
            )
        await GuildStatsView(
            cog=self,
            _object=role,
            members_type="both",
            show_graphic_in_main=show_graphic,
            graphic_mode=False,
        ).start(ctx)

    @guildstats.command(aliases=["server"])
    async def guild(
        self,
        ctx: commands.Context,
        members_type: typing.Optional[typing.Literal["humans", "bots", "both"]] = "humans",
        show_graphic: typing.Optional[bool] = False,
    ) -> None:
        """Display stats for this guild."""
        if not (
            enabled_state
            if (enabled_state := await self.config.guild(ctx.guild).enabled()) is not None
            else await self.config.default_state()
        ):
            raise commands.UserFeedbackCheckFailure(
                _(
                    "This cog is disabled in this guild. Administrators can enable it with the command `{prefix}guildstats enable`."
                ).format(prefix=ctx.prefix)
            )
        await GuildStatsView(
            cog=self,
            _object=ctx.guild,
            members_type=members_type,
            show_graphic_in_main=show_graphic,
            graphic_mode=False,
        ).start(ctx)

    @guildstats.command()
    async def messages(
        self,
        ctx: commands.Context,
        members_type: typing.Optional[typing.Literal["humans", "bots", "both"]] = "humans",
        show_graphic: typing.Optional[bool] = False,
    ) -> None:
        """Display stats for the messages in this guild."""
        if not (
            enabled_state
            if (enabled_state := await self.config.guild(ctx.guild).enabled()) is not None
            else await self.config.default_state()
        ):
            raise commands.UserFeedbackCheckFailure(
                _(
                    "This cog is disabled in this guild. Administrators can enable it with the command `{prefix}guildstats enable`."
                ).format(prefix=ctx.prefix)
            )
        await GuildStatsView(
            cog=self,
            _object=(ctx.guild, "messages"),
            members_type=members_type,
            show_graphic_in_main=show_graphic,
            graphic_mode=False,
        ).start(ctx)

    @guildstats.command()
    async def voice(
        self,
        ctx: commands.Context,
        members_type: typing.Optional[typing.Literal["humans", "bots", "both"]] = "humans",
        show_graphic: typing.Optional[bool] = False,
    ) -> None:
        """Display stats for the voice in this guild."""
        if not (
            enabled_state
            if (enabled_state := await self.config.guild(ctx.guild).enabled()) is not None
            else await self.config.default_state()
        ):
            raise commands.UserFeedbackCheckFailure(
                _(
                    "This cog is disabled in this guild. Administrators can enable it with the command `{prefix}guildstats enable`."
                ).format(prefix=ctx.prefix)
            )
        await GuildStatsView(
            cog=self,
            _object=(ctx.guild, "voice"),
            members_type=members_type,
            show_graphic_in_main=show_graphic,
            graphic_mode=False,
        ).start(ctx)

    @guildstats.command()
    async def activities(
        self,
        ctx: commands.Context,
        members_type: typing.Optional[typing.Literal["humans", "bots", "both"]] = "humans",
    ) -> None:
        """Display stats for activities in this guild."""
        if not await self.config.toggle_activities_stats():
            raise commands.UserFeedbackCheckFailure(
                _("Activities stats are disabled on this bot.")
            )
        if not (
            enabled_state
            if (enabled_state := await self.config.guild(ctx.guild).enabled()) is not None
            else await self.config.default_state()
        ):
            raise commands.UserFeedbackCheckFailure(
                _(
                    "This cog is disabled in this guild. Administrators can enable it with the command `{prefix}guildstats enable`."
                ).format(prefix=ctx.prefix)
            )
        await GuildStatsView(
            cog=self,
            _object=(ctx.guild, "activities"),
            members_type=members_type,
            show_graphic_in_main=False,
            graphic_mode=False,
        ).start(ctx)

    @guildstats.command()
    async def category(
        self,
        ctx: commands.Context,
        members_type: typing.Optional[typing.Literal["humans", "bots", "both"]] = "humans",
        show_graphic: typing.Optional[bool] = False,
        *,
        category: discord.CategoryChannel = None,
    ) -> None:
        """Display stats for a specified category."""
        if category is None:
            if ctx.channel.category is not None:
                category = ctx.channel.category
            else:
                raise commands.UserInputError()
        if not (
            enabled_state
            if (enabled_state := await self.config.guild(ctx.guild).enabled()) is not None
            else await self.config.default_state()
        ):
            raise commands.UserFeedbackCheckFailure(
                _(
                    "This cog is disabled in this guild. Administrators can enable it with the command `{prefix}guildstats enable`."
                ).format(prefix=ctx.prefix)
            )
        await GuildStatsView(
            cog=self,
            _object=category,
            members_type=members_type,
            show_graphic_in_main=show_graphic,
            graphic_mode=False,
        ).start(ctx)

    @guildstats.command()
    async def channel(
        self,
        ctx: commands.Context,
        members_type: typing.Optional[typing.Literal["humans", "bots", "both"]] = "humans",
        show_graphic: typing.Optional[bool] = False,
        *,
        channel: typing.Union[discord.TextChannel, discord.VoiceChannel] = None,
    ) -> None:
        """Display stats for a specified channel."""
        if channel is None:
            channel = ctx.channel
        if not (
            enabled_state
            if (enabled_state := await self.config.guild(ctx.guild).enabled()) is not None
            else await self.config.default_state()
        ):
            raise commands.UserFeedbackCheckFailure(
                _(
                    "This cog is disabled in this guild. Administrators can enable it with the command `{prefix}guildstats enable`."
                ).format(prefix=ctx.prefix)
            )
        if isinstance(channel, discord.Thread):
            raise commands.UserFeedbackCheckFailure(_("Threads aren't supported by this cog."))
        await GuildStatsView(
            cog=self,
            _object=channel,
            members_type=members_type,
            show_graphic_in_main=show_graphic,
            graphic_mode=False,
        ).start(ctx)

    @guildstats.command()
    async def top(
        self,
        ctx: commands.Context,
        members_type: typing.Optional[typing.Literal["humans", "bots", "both"]],
        _type_1: typing.Literal["messages", "voice"],
        _type_2: typing.Literal["members", "channels"],
    ) -> None:
        """Display top stats for voice/messages members/channels."""
        if members_type is None:
            members_type = "humans"
        if not (
            enabled_state
            if (enabled_state := await self.config.guild(ctx.guild).enabled()) is not None
            else await self.config.default_state()
        ):
            raise commands.UserFeedbackCheckFailure(
                _(
                    "This cog is disabled in this guild. Administrators can enable it with the command `{prefix}guildstats enable`."
                ).format(prefix=ctx.prefix)
            )
        await GuildStatsView(
            cog=self,
            _object=(ctx.guild, ("top", _type_1, _type_2)),
            members_type=members_type,
            show_graphic_in_main=False,
            graphic_mode=False,
        ).start(ctx)

    @guildstats.command()
    async def activity(
        self,
        ctx: commands.Context,
        members_type: typing.Optional[typing.Literal["humans", "bots", "both"]] = "humans",
        *,
        activity_name: str,
    ) -> None:
        """Display stats for a specific activity in this guild."""
        if not await self.config.toggle_activities_stats():
            raise commands.UserFeedbackCheckFailure(
                _("Activities stats are disabled on this bot.")
            )
        if not (
            enabled_state
            if (enabled_state := await self.config.guild(ctx.guild).enabled()) is not None
            else await self.config.default_state()
        ):
            raise commands.UserFeedbackCheckFailure(
                _(
                    "This cog is disabled in this guild. Administrators can enable it with the command `{prefix}guildstats enable`."
                ).format(prefix=ctx.prefix)
            )
        await GuildStatsView(
            cog=self,
            _object=(ctx.guild, ("activity", activity_name)),
            members_type=members_type,
            show_graphic_in_main=False,
            graphic_mode=False,
        ).start(ctx)

    @guildstats.command(aliases=["graph"])
    async def graphic(
        self,
        ctx: commands.Context,
        members_type: typing.Optional[typing.Literal["humans", "bots", "both"]] = "humans",
        *,
        _object: ObjectConverter = None,
    ) -> None:
        """Display graphic for members, roles guilds, text channels, voice channels and activities."""
        if _object is None:
            _object = ctx.guild
        if _object == "activities" and not await self.config.toggle_activities_stats():
            raise commands.UserFeedbackCheckFailure(
                _("Activities stats are disabled on this bot.")
            )
        if not (
            enabled_state
            if (enabled_state := await self.config.guild(ctx.guild).enabled()) is not None
            else await self.config.default_state()
        ):
            raise commands.UserFeedbackCheckFailure(
                _(
                    "This cog is disabled in this guild. Administrators can enable it with the command `{prefix}guildstats enable`."
                ).format(prefix=ctx.prefix)
            )
        ignored_users = await self.config.ignored_users()
        if isinstance(_object, discord.Member) and _object.id in ignored_users:
            raise commands.UserFeedbackCheckFailure(
                _(
                    "This user is in the ignored users list (`{prefix}guildstats ignoreme`)."
                ).format(prefix=ctx.prefix)
            )
        await GuildStatsView(
            cog=self,
            _object=_object
            if _object not in ["voice", "messages", "activities"]
            else (ctx.guild, _object),
            members_type=members_type,
            show_graphic_in_main=False,
            graphic_mode=True,
        ).start(ctx)

    @guildstats.command()
    async def ignoreme(self, ctx: commands.Context) -> None:
        """Asking GuildStats to ignore your actions."""
        user = ctx.author
        ignored_users: typing.List[int] = await self.config.ignored_users()
        if user.id not in ignored_users:
            ignored_users.append(user.id)
            await self.red_delete_data_for_user(requester="user", user_id=user.id)
            await self.config.ignored_users.set(ignored_users)
            await ctx.send(
                _(
                    "You will no longer be seen by this cog and the data I held on you have been deleted."
                )
            )
        else:
            ignored_users.remove(user.id)
            await self.config.ignored_users.set(ignored_users)
            await ctx.send(_("You'll be seen again by this cog."))

    @commands.is_owner()
    @guildstats.command()
    async def ignoreuser(self, ctx: commands.Context, *, user: discord.User):
        """Ignore or unignore a specific user."""
        ignored_users: typing.List[int] = await self.config.ignored_users()
        if user.id not in ignored_users:
            ignored_users.append(user.id)
            await self.red_delete_data_for_user(requester="user", user_id=user.id)
            await self.config.ignored_users.set(ignored_users)
            await ctx.send(
                _(
                    "{user.mention} ({user.id}) will no longer be seen by this cog, and their data has been deleted."
                ).format(user=user),
                allowed_mentions=discord.AllowedMentions(users=False),
            )
        else:
            ignored_users.remove(user.id)
            await self.config.ignored_users.set(ignored_users)
            await ctx.send(
                _("{user.mention} ({user.id}) will be seen again by this cog.").format(user=user),
                allowed_mentions=discord.AllowedMentions(users=False),
            )

    @commands.admin_or_permissions(administrator=True)
    @guildstats.command()
    async def ignorecategory(self, ctx: commands.Context, *, category: discord.CategoryChannel):
        """Ignore or unignore a specific category."""
        ignored_categories: typing.List[int] = await self.config.guild(
            ctx.guild
        ).ignored_categories()
        if category.id not in ignored_categories:
            ignored_categories.append(category.id)
            await self.config.guild(ctx.guild).ignored_categories.set(ignored_categories)
            await ctx.send(
                _(
                    "`{category.name}` ({category.id}) will now be ignored in stats (except for the specific category one)."
                ).format(category=category),
            )
        else:
            ignored_categories.remove(category.id)
            await self.config.guild(ctx.guild).ignored_categories.set(ignored_categories)
            await ctx.send(
                _("`{category.name}` ({category.id}) will no longer be ignored in stats.").format(
                    category=category
                ),
            )

    @commands.admin_or_permissions(administrator=True)
    @guildstats.command()
    async def ignorechannel(
        self,
        ctx: commands.Context,
        *,
        channel: typing.Union[discord.TextChannel, discord.VoiceChannel],
    ):
        """Ignore or unignore a specific channel."""
        ignored_channels: typing.List[int] = await self.config.guild(ctx.guild).ignored_channels()
        if channel.id not in ignored_channels:
            ignored_channels.append(channel.id)
            await self.config.guild(ctx.guild).ignored_channels.set(ignored_channels)
            await ctx.send(
                _(
                    "{channel.mention} ({channel.id}) will now be ignored in stats (except for the specific channel one)."
                ).format(channel=channel),
            )
        else:
            ignored_channels.remove(channel.id)
            await self.config.guild(ctx.guild).ignored_channels.set(ignored_channels)
            await ctx.send(
                _("{channel.mention} ({channel.id}) will no longer be ignored in stats.").format(
                    channel=channel
                ),
            )

    @commands.admin_or_permissions(administrator=True)
    @guildstats.command()
    async def ignoreactivity(self, ctx: commands.Context, *, activity_name: str):
        """Ignore or unignore a specific activity."""
        ignored_activities: typing.List[str] = await self.config.guild(
            ctx.guild
        ).ignored_activities()
        if activity_name not in ignored_activities:
            ignored_activities.append(activity_name)
            await self.config.guild(ctx.guild).ignored_activities.set(ignored_activities)
            await ctx.send(
                _(
                    "The activity `{activity_name}` will now be ignored in stats (except for the specific activity one)."
                ).format(activity_name=activity_name),
            )
        else:
            ignored_activities.remove(activity_name)
            await self.config.guild(ctx.guild).ignored_activities.set(ignored_activities)
            await ctx.send(
                _("The activity `{activity_name}` will no longer be ignored in stats.").format(
                    activity_name=activity_name
                ),
            )

    @commands.is_owner()
    @guildstats.command()
    async def toggleactivitiesstats(self, ctx: commands.Context, state: bool) -> None:
        """Enable or disable activities stats."""
        await self.config.toggle_activities_stats.set(state)

    @commands.is_owner()
    @guildstats.command()
    async def setdefaultstate(self, ctx: commands.Context, state: bool) -> None:
        """Enable or disable by default the cog in the bot guilds."""
        await self.config.default_state.set(state)

    @commands.admin_or_permissions(administrator=True)
    @guildstats.command()
    async def enable(self, ctx: commands.Context) -> None:
        """Enable the cog in this guild/server."""
        current_state = await self.config.guild(ctx.guild).enabled()
        if current_state is not None and current_state:
            raise commands.UserFeedbackCheckFailure(
                _("GuildStats already enabled in this guild/server.")
            )
        await self.config.guild(ctx.guild).enabled.set(True)
        await ctx.send(_("GuildStats enabled in this guild/server."))

    @commands.admin_or_permissions(administrator=True)
    @guildstats.command()
    async def disable(self, ctx: commands.Context) -> None:
        """Disable the cog in this guild/server."""
        current_state = await self.config.guild(ctx.guild).enabled()
        if current_state is not None and not current_state:
            raise commands.UserFeedbackCheckFailure(
                _("GuildStats already disabled in this guild/server.")
            )
        await self.config.guild(ctx.guild).enabled.set(False)
        await ctx.send(_("GuildStats disabled in this guild/server."))

    @commands.is_owner()
    @commands.bot_has_permissions(embed_links=True)
    @guildstats.command(hidden=True)
    async def getdebugloopsstatus(self, ctx: commands.Context) -> None:
        """Get an embed for check loop status."""
        embeds = [loop.get_debug_embed() for loop in self.loops]
        await Menu(pages=embeds).start(ctx)

    @commands.admin_or_permissions(administrator=True)
    @guildstats.command(hidden=True)
    async def purge(
        self,
        ctx: commands.Context,
        _type: typing.Literal["all", "messages", "voice", "activities"],
    ) -> None:
        """Purge Config for the current guild."""
        await self.save_to_config()
        if _type == "all":
            await self.config.guild(ctx.guild).clear()
            await self.config.clear_all_members(guild=ctx.guild)
            await ctx.send(_("All GuildStats data purged for this guild."))
        elif _type == "activities":
            await self.config.clear_all_members(guild=ctx.guild)
            await ctx.send(_("All GuildStats activities data purged for this guild."))
        else:
            channel_group = self.config._get_base_group(self.config.CHANNEL)
            async with channel_group.all() as channels_data:
                for channel in ctx.guild.channels:
                    if str(channel.id) in channels_data:
                        if _type == "messages":
                            channels_data[str(channel.id)]["total_messages"] = 0
                            channels_data[str(channel.id)]["total_humans_messages"] = 0
                            channels_data[str(channel.id)]["total_bots_messages"] = 0
                            channels_data[str(channel.id)]["total_messages_members"] = {}
                            channels_data[str(channel.id)]["messages"] = {}
                        else:
                            channels_data[str(channel.id)]["total_voice"] = 0
                            channels_data[str(channel.id)]["total_humans_voice"] = 0
                            channels_data[str(channel.id)]["total_bots_voice"] = 0
                            channels_data[str(channel.id)]["total_voice_members"] = {}
                            channels_data[str(channel.id)]["voice"] = {}
            await ctx.send(
                _("All GuildStats {_type} data purged for this guild.").format(_type=_type)
            )

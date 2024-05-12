from AAA3A_utils import Cog, Loop, CogsUtils, Menu  # isort:skip
from redbot.core import commands, Config  # isort:skip
from redbot.core.bot import Red  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import asyncio
import datetime
import io
from copy import deepcopy

from redbot.core.utils.chat_formatting import box, pagify

# Credits:
# General repo credits.
# Thanks to @aikaterna on Discord for the cog idea and a part of the code (https://github.com/aikaterna/aikaterna-cogs/blob/v3/seen/seen.py)!

_ = Translator("Seen", __file__)


@cog_i18n(_)
class Seen(Cog):
    """A cog to check when a member/role/channel/category/user/guild was last active!"""

    __authors__: typing.List[str] = ["AAA3A", "aikaterna"]

    def __init__(self, bot: Red) -> None:
        super().__init__(bot=bot)

        self.config: Config = Config.get_conf(
            self,
            identifier=205192943327321000143939875896557571750,  # 864398642893
            force_registration=True,
        )
        self.config.register_global(
            message={},
            message_edit={},
            reaction_add={},
            reaction_remove={},
            ignored_users=[],
            listeners={
                "message": True,
                "message_edit": True,
                "reaction_add": True,
                "reaction_remove": True,
            },
        )
        self.default_config: typing.Dict[str, typing.Optional[str]] = {
            "message": None,
            "message_edit": None,
            "reaction_add": None,
            "reaction_remove": None,
        }
        self.config.register_user(**self.default_config)
        self.config.register_member(**self.default_config)
        self.config.register_role(**self.default_config)
        self.config.register_channel(**self.default_config)
        self.config.register_guild(**self.default_config)

        self.cache: typing.Dict[
            str,
            typing.Union[
                typing.Dict[
                    str,
                    typing.Union[
                        typing.Dict[str, typing.Dict[str, typing.Union[int, str]]],
                        typing.Dict[
                            typing.Union[discord.Guild, discord.User], typing.Dict[str, str]
                        ],
                        typing.Dict[
                            discord.Guild,
                            typing.Dict[
                                typing.Union[
                                    discord.Member,
                                    discord.Role,
                                    discord.abc.GuildChannel,
                                    discord.Thread,
                                    discord.CategoryChannel,
                                ],
                                typing.Dict[str, str],
                            ],
                        ],
                    ],
                ],
                typing.List[str],
            ],
        ] = {
            "global": {},
            "users": {},
            "members": {},
            "roles": {},
            "channels": {},
            "categories": {},
            "guilds": {},
            "existing_keys": [],
        }

    async def cog_load(self) -> None:
        await super().cog_load()
        self.loops.append(
            Loop(
                cog=self,
                name="Save Seen Data",
                function=self.save_to_config,
                minutes=1,
            )
        )

    async def cog_unload(self) -> None:
        asyncio.create_task(self.save_to_config())
        await super().cog_unload()

    async def red_delete_data_for_user(
        self,
        *,
        requester: typing.Literal["discord_deleted_user", "owner", "user", "user_strict"],
        user_id: int,
    ) -> None:
        """Delete all Seen data for user, members, roles, channels, categories, guilds; if the user ID matches."""
        if requester not in ["discord_deleted_user", "owner", "user", "user_strict"]:
            return
        await self.save_to_config()  # To clean up the cache too.
        global_data = await self.config.all()
        user_group = self.config._get_base_group(self.config.USER)
        member_group = self.config._get_base_group(self.config.MEMBER)
        role_group = self.config._get_base_group(self.config.ROLE)
        channel_group = self.config._get_base_group(self.config.CHANNEL)
        category_group = self.config._get_base_group(self.config.CHANNEL)
        guild_group = self.config._get_base_group(self.config.GUILD)
        custom_ids = []
        # Users.
        async with user_group.all() as users_data:
            if str(user_id) in users_data:
                custom_ids.extend(
                    (_type, custom_id) for _type, custom_id in users_data[str(user_id)].items()
                )
                del users_data[str(user_id)]
        # Members.
        async with member_group.all() as members_data:
            _members_data = deepcopy(members_data)
            for guild in _members_data:
                if str(user_id) in _members_data[guild]:
                    custom_ids.extend(
                        (_type, custom_id)
                        for _type, custom_id in members_data[guild][str(user_id)].items()
                    )
                    del members_data[guild][str(user_id)]
        # Roles.
        async with role_group.all() as roles_data:
            _roles_data = deepcopy(roles_data)
            for role in _roles_data:
                for _type, custom_id in _roles_data[role].items():
                    if (
                        global_data[_type].get(custom_id, {"action": {"member": None}})["action"][
                            "member"
                        ]
                        == user_id
                    ):
                        custom_ids.append((_type, roles_data[role][_type]))
                        roles_data[role][_type] = None
        # Channels.
        async with channel_group.all() as channels_data:
            _channels_data = deepcopy(channels_data)
            for channel in _channels_data:
                for _type, custom_id in _channels_data[channel].items():
                    if (
                        global_data[_type].get(custom_id, {"action": {"member": None}})["action"][
                            "member"
                        ]
                        == user_id
                    ):
                        custom_ids.append((_type, channels_data[channel][_type]))
                        channels_data[channel][_type] = None
        # Categories.
        async with category_group.all() as categories_data:
            _categories_data = deepcopy(categories_data)
            for category in _categories_data:
                for _type, custom_id in _categories_data[category].items():
                    if (
                        global_data[_type].get(custom_id, {"action": {"member": None}})["action"][
                            "member"
                        ]
                        == user_id
                    ):
                        custom_ids.append((_type, categories_data[category][_type]))
                        categories_data[category][_type] = None
        # Guilds.
        async with guild_group.all() as guilds_data:
            _guilds_data = deepcopy(guilds_data)
            for guild in _guilds_data:
                for _type, custom_id in _guilds_data[guild].items():
                    if (
                        global_data[_type].get(custom_id, {"action": {"member": None}})["action"][
                            "member"
                        ]
                        == user_id
                    ):
                        custom_ids.append((_type, guilds_data[guild][_type]))
                        guilds_data[guild][_type] = None
        # Global.
        if user_id in global_data["ignored_users"]:
            global_data["ignored_users"].remove(user_id)
        for _type, custom_id in custom_ids:
            try:
                del global_data[_type][custom_id]
            except KeyError:
                pass
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

        global_data = await self.config.all()
        user_group = self.config._get_base_group(self.config.USER)
        member_group = self.config._get_base_group(self.config.MEMBER)
        role_group = self.config._get_base_group(self.config.ROLE)
        channel_group = self.config._get_base_group(self.config.CHANNEL)
        category_group = self.config._get_base_group(self.config.CHANNEL)
        guild_group = self.config._get_base_group(self.config.GUILD)
        custom_ids = []
        # Users.
        async with user_group.all() as users_data:
            if str(user_id) in users_data:
                data[Config.USER] = {str(user_id): users_data[str(user_id)]}
                custom_ids.extend(
                    (_type, custom_id) for _type, custom_id in users_data[str(user_id)].items()
                )
        # Members.
        async with member_group.all() as members_data:
            for guild in members_data:
                if str(user_id) in members_data[guild]:
                    data[Config.MEMBER][guild] = {str(user_id): members_data[guild][str(user_id)]}
                    custom_ids.extend(
                        (_type, custom_id)
                        for _type, custom_id in members_data[guild][str(user_id)].items()
                    )
        # Roles.
        async with role_group.all() as roles_data:
            for role in roles_data:
                for _type, custom_id in roles_data[role].items():
                    if (
                        global_data[_type].get(custom_id, {"action": {"member": None}})["action"][
                            "member"
                        ]
                        == user_id
                    ):
                        if role not in data[Config.ROLE]:
                            data[Config.ROLE][role] = {}
                        data[Config.ROLE][role][_type] = roles_data[role][_type]
                        custom_ids.append((_type, roles_data[role][_type]))
        # Channels.
        async with channel_group.all() as channels_data:
            for channel in channels_data:
                for _type, custom_id in channels_data[channel].items():
                    if (
                        global_data[_type].get(custom_id, {"action": {"member": None}})["action"][
                            "member"
                        ]
                        == user_id
                    ):
                        if channel not in data[Config.CHANNEL]:
                            data[Config.CHANNEL][channel] = {}
                        data[Config.CHANNEL][channel][_type] = channels_data[channel][_type]
                        custom_ids.append((_type, channels_data[channel][_type]))
        # Categories.
        async with category_group.all() as categories_data:
            for category in categories_data:
                for _type, custom_id in categories_data[category].items():
                    if (
                        global_data[_type].get(custom_id, {"action": {"member": None}})["action"][
                            "member"
                        ]
                        == user_id
                    ):
                        if channel not in data[Config.CHANNEL]:
                            data[Config.CHANNEL][category] = {}
                        data[Config.CHANNEL][category][_type] = categories_data[category][_type]
                        custom_ids.append((_type, categories_data[category][_type]))
        # Guilds.
        async with guild_group.all() as guilds_data:
            for guild in guilds_data:
                for _type, custom_id in guilds_data[guild].items():
                    if (
                        global_data[_type].get(custom_id, {"action": {"member": None}})["action"][
                            "member"
                        ]
                        == user_id
                    ):
                        if channel not in data[Config.GUILD]:
                            data[Config.GUILD][guild] = {}
                        data[Config.GUILD][guild][_type] = guilds_data[guild][_type]
                        custom_ids.append((_type, guilds_data[guild][_type]))
        # Global.
        if user_id in global_data["ignored_users"]:
            data[Config.GLOBAL]["ignored_users"] = [user_id]
        for _type, custom_id in custom_ids:
            d = global_data[_type].get(custom_id, None)
            if d is not None:
                data[Config.GLOBAL][_type] = {custom_id: d}

        _data = deepcopy(data)
        for key, value in _data.items():
            if not value:
                del data[key]
        if not data:
            return {}
        file = io.BytesIO(str(data).encode(encoding="utf-8"))
        return {f"{self.qualified_name}.json": file}

    def upsert_cache(
        self,
        time: typing.Optional[datetime.datetime],
        _type: typing.Literal["message", "message_edit", "reaction_add", "reaction_remove"],
        member: discord.Member,
        guild: discord.Guild,
        channel: discord.TextChannel,
        message: discord.Message,
        reaction: typing.Optional[str] = None,
    ) -> None:
        if time is None:
            time = datetime.datetime.now(tz=datetime.timezone.utc)
        if not isinstance(channel, discord.TextChannel):
            return
        custom_id = CogsUtils.generate_key(
            length=10,
            existing_keys=self.cache["existing_keys"],
            strings_used={
                "ascii_lowercase": True,
                "ascii_uppercase": True,
                "digits": True,
                "punctuation": False,
                "others": [],
            },
        )
        data = {
            "seen": time,
            "action": {
                "message": [message.guild, message.channel, message],
                "member": member,
                "reaction": reaction,
            },
        }
        if data["action"]["reaction"] is None:
            del data["action"]["reaction"]
        # Global.
        if _type not in self.cache["global"]:
            self.cache["global"][_type] = {}
        self.cache["global"][_type][custom_id] = data
        self.cache["existing_keys"].append(custom_id)
        # Users.
        if member._user not in self.cache["users"]:
            self.cache["users"][member._user] = {}
        self.cache["users"][member._user][_type] = custom_id
        # Members.
        if guild not in self.cache["members"]:
            self.cache["members"][guild] = {}
        if member not in self.cache["members"][guild]:
            self.cache["members"][guild][member] = {}
        self.cache["members"][guild][member][_type] = custom_id
        # Roles.
        if guild not in self.cache["roles"]:
            self.cache["roles"][guild] = {}
        for role in member.roles:
            if role not in self.cache["roles"][guild]:
                self.cache["roles"][guild][role] = {}
            self.cache["roles"][guild][role][_type] = custom_id
        # Channels.
        if guild not in self.cache["channels"]:
            self.cache["channels"][guild] = {}
        if channel not in self.cache["channels"][guild]:
            self.cache["channels"][guild][channel] = {}
        self.cache["channels"][guild][channel][_type] = custom_id
        # Categories.
        if channel.category is not None:
            if guild not in self.cache["categories"]:
                self.cache["categories"][guild] = {}
            if channel.category not in self.cache["categories"][guild]:
                self.cache["categories"][guild][channel.category] = {}
            self.cache["categories"][guild][channel.category][_type] = custom_id
        # Guilds.
        if guild not in self.cache["guilds"]:
            self.cache["guilds"][guild] = {}
        self.cache["guilds"][guild][_type] = custom_id

    async def save_to_config(self) -> None:
        cache = self.cache.copy()
        cache["existing_keys"] = []
        if cache == {
            "global": {},
            "users": {},
            "members": {},
            "roles": {},
            "channels": {},
            "categories": {},
            "guilds": {},
            "existing_keys": [],
        }:
            return
        self.cache = {
            "global": {},
            "users": {},
            "members": {},
            "roles": {},
            "channels": {},
            "categories": {},
            "guilds": {},
            "existing_keys": self.cache["existing_keys"].copy(),
        }
        user_group = self.config._get_base_group(self.config.USER)
        member_group = self.config._get_base_group(self.config.MEMBER)
        role_group = self.config._get_base_group(self.config.ROLE)
        channel_group = self.config._get_base_group(self.config.CHANNEL)
        category_group = self.config._get_base_group(self.config.CHANNEL)
        guild_group = self.config._get_base_group(self.config.GUILD)
        # Global.
        async with self.config.all() as global_data:
            for _type in cache["global"]:
                for custom_id, _data in cache["global"][_type].items():
                    data = {
                        "seen": int(_data["seen"].timestamp()),
                        "action": {
                            "message": [
                                _data["action"]["message"][0].id,
                                _data["action"]["message"][1].id,
                                _data["action"]["message"][2].id,
                            ],
                            "member": _data["action"]["member"].id,
                        },
                    }
                    if "reaction" in _data["action"]:
                        data["action"]["reaction"] = _data["action"]["reaction"]
                    global_data[_type][custom_id] = data
        # Users.
        async with user_group.all() as users_data:
            for user in cache["users"]:
                if str(user.id) not in users_data:
                    users_data[str(user.id)] = {}
                for _type, custom_id in cache["users"][user].items():
                    users_data[str(user.id)][_type] = custom_id
        # Members.
        async with member_group.all() as members_data:
            for guild in cache["members"]:
                for member in cache["members"][guild]:
                    if str(guild.id) not in members_data:
                        members_data[str(guild.id)] = {}
                    if str(member.id) not in members_data[str(guild.id)]:
                        members_data[str(guild.id)][str(member.id)] = {}
                    for _type in cache["members"][guild][member]:
                        custom_id = cache["members"][guild][member][_type]
                        members_data[str(guild.id)][str(member.id)][str(_type)] = custom_id
        # Roles.
        async with role_group.all() as roles_data:
            for guild in cache["roles"]:
                for role in cache["roles"][guild]:
                    if str(role.id) not in roles_data:
                        roles_data[str(role.id)] = {}
                    for _type in cache["roles"][guild][role]:
                        custom_id = cache["roles"][guild][role][_type]
                        roles_data[str(role.id)][_type] = custom_id
        # Channels.
        async with channel_group.all() as channels_data:
            for guild in cache["channels"]:
                for channel in cache["channels"][guild]:
                    if str(channel.id) not in channels_data:
                        channels_data[str(channel.id)] = {}
                    for _type in cache["channels"][guild][channel]:
                        custom_id = cache["channels"][guild][channel][_type]
                        channels_data[str(channel.id)][_type] = custom_id
        # Categories.
        async with category_group.all() as categories_data:
            for guild in cache["categories"]:
                for category in cache["categories"][guild]:
                    if str(category.id) not in categories_data:
                        categories_data[str(category.id)] = {}
                    for _type in cache["categories"][guild][category]:
                        custom_id = cache["categories"][guild][category][_type]
                        categories_data[str(category.id)][_type] = custom_id
        # Guilds.
        async with guild_group.all() as guilds_data:
            for guild in cache["guilds"]:
                if str(guild.id) not in guilds_data:
                    guilds_data[str(guild.id)] = {}
                for _type, custom_id in cache["guilds"][guild].items():
                    guilds_data[str(guild.id)][_type] = custom_id
        # Run Cleanup.
        await self.cleanup()

    async def cleanup(self, for_count: typing.Optional[bool] = False) -> None:
        users_data = await self.config.all_users()
        members_data = await self.config.all_members()
        roles_data = await self.config.all_roles()
        channels_data = await self.config.all_channels()
        categories_data = await self.config.all_channels()
        guilds_data = await self.config.all_guilds()
        existing_keys = []
        if for_count:
            global_count = 0
            users_count = 0
            members_count = 0
            roles_count = 0
            channels_count = 0
            categories_count = 0
            guilds_count = 0
        # Users.
        for user in users_data:
            if for_count:
                if any(custom_id is not None for custom_id in users_data[user].values()):
                    users_count += 1
                continue
            existing_keys.extend(
                custom_id for custom_id in users_data[user].values() if custom_id is not None
            )
        # Members.
        for guild in members_data:
            for member in members_data[guild]:
                if for_count:
                    if any(
                        custom_id is not None for custom_id in members_data[guild][member].values()
                    ):
                        members_count += 1
                    continue
                existing_keys.extend(
                    custom_id
                    for custom_id in members_data[guild][member].values()
                    if custom_id is not None
                )
        # Roles.
        for role in roles_data:
            if for_count:
                if any(custom_id is not None for custom_id in roles_data[role].values()):
                    roles_count += 1
                continue
            existing_keys.extend(
                custom_id for custom_id in roles_data[role].values() if custom_id is not None
            )
        # Channels.
        for channel in channels_data:
            if for_count:
                if any(custom_id is not None for custom_id in channels_data[channel].values()):
                    channels_count += 1
                continue
            existing_keys.extend(
                custom_id for custom_id in channels_data[channel].values() if custom_id is not None
            )
        # Categories.
        for category in categories_data:
            if for_count:
                if any(custom_id is not None for custom_id in categories_data[category].values()):
                    categories_count += 1
                continue
            existing_keys.extend(
                custom_id
                for custom_id in categories_data[category].values()
                if custom_id is not None
            )
        # Guilds.
        for guild in guilds_data:
            if for_count:
                if any(custom_id is not None for custom_id in guilds_data[guild].values()):
                    guilds_count += 1
                continue
            existing_keys.extend(
                custom_id for custom_id in guilds_data[guild].values() if custom_id is not None
            )
        if not for_count:
            self.cache["existing_keys"] = list(set(existing_keys))
        # Global.
        async with self.config.all() as global_data:
            _global_data = deepcopy(global_data)
            for _type in _global_data:
                for custom_id in _global_data[_type]:
                    if for_count:
                        global_count += 1
                    elif (
                        custom_id not in self.cache["existing_keys"]
                    ):  # The action is no longer used by any data.
                        try:
                            del global_data[_type][custom_id]
                        except (IndexError, KeyError):
                            pass
        if for_count:
            return (
                global_count,
                users_count,
                members_count,
                roles_count,
                channels_count,
                categories_count,
                guilds_count,
            )

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if await self.bot.cog_disabled_in_guild(
            cog=self, guild=message.guild
        ) or not await self.bot.allowed_by_whitelist_blacklist(who=message.author):
            return
        if message.webhook_id is not None:
            return
        if message.guild is None:
            return
        if not isinstance(message.author, discord.Member):
            return
        # Just don't take in account Seen messages.
        if not message.author.bot:
            ctx: commands.Context = await self.bot.get_context(message)
            if ctx.valid and (ctx.cog is not None and ctx.cog.qualified_name == "Seen"):
                return
        if (
            message.author.id == message.guild.me.id
            and len(message.embeds) == 1
            and (
                "Seen".lower() in message.embeds[0].to_dict().get("description", "").lower()
                or "Seen".lower() in message.embeds[0].to_dict().get("title", "").lower()
            )
        ):
            return
        ignored_users = await self.config.ignored_users()
        if message.author.id in ignored_users:
            return
        if not await self.config.listeners.message():
            return
        self.upsert_cache(
            time=datetime.datetime.now(tz=datetime.timezone.utc),
            _type="message",
            member=message.author,
            guild=message.guild,
            channel=message.channel,
            message=message,
            reaction=None,
        )

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message) -> None:
        if await self.bot.cog_disabled_in_guild(
            cog=self, guild=after.guild
        ) or not await self.bot.allowed_by_whitelist_blacklist(who=after.author):
            return
        if after.webhook_id is not None:
            return
        if after.guild is None:
            return
        if not isinstance(after.author, discord.Member):
            return
        # Just don't take in account Seen messages.
        if not after.author.bot:
            ctx: commands.Context = await self.bot.get_context(after)
            if ctx.valid and (ctx.cog is not None and ctx.cog.qualified_name == "Seen"):
                return
        if (
            after.author.id == after.guild.me.id
            and len(after.embeds) == 1
            and (
                "Seen".lower() in after.embeds[0].to_dict().get("description", "").lower()
                or "Seen".lower() in after.embeds[0].to_dict().get("title", "").lower()
            )
        ):
            return
        ignored_users = await self.config.ignored_users()
        if after.author.id in ignored_users:
            return
        if not await self.config.listeners.message_edit():
            return
        self.upsert_cache(
            time=datetime.datetime.now(tz=datetime.timezone.utc),
            _type="message_edit",
            member=after.author,
            guild=after.guild,
            channel=after.channel,
            message=after,
            reaction=None,
        )

    @commands.Cog.listener()
    async def on_reaction_add(
        self, reaction: discord.Reaction, user: typing.Union[discord.Member, discord.User]
    ) -> None:
        if await self.bot.cog_disabled_in_guild(
            cog=self, guild=reaction.message.guild
        ) or not await self.bot.allowed_by_whitelist_blacklist(who=user):
            return
        if reaction.message.guild is None:
            return
        if not isinstance(user, discord.Member):
            return
        if (
            user.id == reaction.message.guild.me.id
            and reaction.emoji == "✅"
            and not reaction.message.author.bot
        ):
            ctx: commands.Context = await self.bot.get_context(reaction.message)
            if ctx.valid and (ctx.command.cog_name is not None and ctx.command.cog_name == "Seen"):
                return
        ignored_users = await self.config.ignored_users()
        if user.id in ignored_users:
            return
        if not await self.config.listeners.reaction_add():
            return
        self.upsert_cache(
            time=datetime.datetime.now(tz=datetime.timezone.utc),
            _type="reaction_add",
            member=user,
            guild=user.guild,
            channel=reaction.message.channel,
            message=reaction.message,
            reaction=str(reaction.emoji),
        )

    @commands.Cog.listener()
    async def on_reaction_remove(
        self, reaction: discord.Reaction, user: typing.Union[discord.Member, discord.User]
    ) -> None:
        if await self.bot.cog_disabled_in_guild(
            cog=self, guild=reaction.message.guild
        ) or not await self.bot.allowed_by_whitelist_blacklist(who=user):
            return
        if reaction.message.guild is None:
            return
        if not isinstance(user, discord.Member):
            return
        ignored_users = await self.config.ignored_users()
        if user.id in ignored_users:
            return
        if not await self.config.listeners.reaction_remove():
            return
        self.upsert_cache(
            time=datetime.datetime.now(tz=datetime.timezone.utc),
            _type="reaction_remove",
            member=user,
            guild=user.guild,
            channel=reaction.message.channel,
            message=reaction.message,
            reaction=str(reaction.emoji),
        )

    async def get_data_for(
        self,
        _object: typing.Union[
            discord.User,
            discord.Member,
            discord.Role,
            discord.TextChannel,
            discord.CategoryChannel,
            discord.Guild,
        ],
        _type: typing.Optional[
            typing.Literal["message", "message_edit", "reaction_add", "reaction_remove"]
        ],
        all_data_config: typing.Optional[typing.Dict] = None,
        all_data_cache: typing.Optional[typing.Dict] = None,
    ) -> typing.Tuple[float, str, str]:
        global_data = await self.config.all()
        if not all([all_data_config is not None, all_data_cache is not None]):
            if isinstance(_object, discord.User):
                all_data_config = await self.config.user(_object).all()
                all_data_cache = self.cache["users"].get(_object.id, {})
            elif isinstance(_object, discord.Member):
                all_data_config = await self.config.member(_object).all()
                all_data_cache = (
                    self.cache["members"]
                    .get((_object if isinstance(_object, discord.Guild) else _object.guild).id, {})
                    .get(_object.id, {})
                )
            elif isinstance(_object, discord.Role):
                all_data_config = await self.config.role(_object).all()
                all_data_cache = (
                    self.cache["roles"]
                    .get((_object if isinstance(_object, discord.Guild) else _object.guild).id, {})
                    .get(_object.id, {})
                )
            elif isinstance(_object, discord.TextChannel):
                all_data_config = await self.config.channel(_object).all()
                all_data_cache = (
                    self.cache["channels"]
                    .get((_object if isinstance(_object, discord.Guild) else _object.guild).id, {})
                    .get(_object.id, {})
                )
            elif isinstance(_object, discord.CategoryChannel):
                all_data_config = await self.config.channel(_object).all()
                all_data_cache = (
                    self.cache["categories"]
                    .get((_object if isinstance(_object, discord.Guild) else _object.guild).id, {})
                    .get(_object.id, {})
                )
            elif isinstance(_object, discord.Guild):
                all_data_config = await self.config.guild(_object).all()
                all_data_cache = self.cache["guilds"].get(_object.id, {})
            else:
                return None
        if _type is not None:
            custom_ids = [
                custom_id
                for custom_id in [
                    all_data_config.get(_type, None),
                    all_data_cache.get(_type, None),
                ]
                if custom_id is not None
            ]
            if not custom_ids:
                return
            custom_id = sorted(
                custom_ids,
                key=lambda x: global_data[_type].get(x, {}).get("seen")
                or self.cache["global"].get(_type, {}).get(x, {}).get("seen"),
                reverse=True,
            )[0]
            data = global_data[_type].get(custom_id, {}) or self.cache["global"][_type][custom_id]
            if data["seen"] is None or data["action"] is None:
                return None
        else:
            all_data_config = {
                x: all_data_config[x]
                for x in ["message", "message_edit", "reaction_add", "reaction_remove"]
                if all_data_config[x] is not None
            }
            all_data_cache = {
                x: all_data_cache.get(x, None)
                for x in ["message", "message_edit", "reaction_add", "reaction_remove"]
                if all_data_cache.get(x, None) is not None
            }
            all_data_config = [
                {
                    "_type": x,
                    "seen": global_data[x].get(all_data_config[x], {"seen": None, "action": None})[
                        "seen"
                    ],
                    "action": global_data[x].get(
                        all_data_config[x], {"seen": None, "action": None}
                    )["action"],
                }
                for x in all_data_config
                if global_data[x].get(all_data_config[x], {"seen": None, "action": None})["seen"]
                is not None
                and global_data[x].get(all_data_config[x], {"seen": None, "action": None})[
                    "action"
                ]
                is not None
            ]
            all_data_cache = [
                {
                    "_type": x,
                    "seen": global_data[x].get(all_data_cache[x], {"seen": None, "action": None})[
                        "seen"
                    ],
                    "action": global_data[x].get(
                        all_data_cache[x], {"seen": None, "action": None}
                    )["action"],
                }
                for x in all_data_cache
                if global_data[x].get(all_data_cache[x], {"seen": None, "action": None})["seen"]
                is not None
                and global_data[x].get(all_data_cache[x], {"seen": None, "action": None})["action"]
                is not None
            ]
            all_data = all_data_config + all_data_cache
            if len(all_data) == 0:
                return None
            data = sorted(all_data, key=lambda x: x["seen"], reverse=True)[0]
            _type = data["_type"]
            del data["_type"]
        time = data["seen"]
        now = int(datetime.datetime.now(tz=datetime.timezone.utc).timestamp())
        time_elapsed = int(now - time)
        m, s = divmod(time_elapsed, 60)
        h, m = divmod(m, 60)
        d, h = divmod(h, 24)
        output = d, h, m
        if output[2] < 1:
            ts = "just now"
        else:
            ts = ""
            if output[0] == 1:
                ts += f"{output[0]} day, "
            elif output[0] > 1:
                ts += f"{output[0]} days, "
            if output[1] == 1:
                ts += f"{output[1]} hour, "
            elif output[1] > 1:
                ts += f"{output[1]} hours, "
            if output[2] == 1:
                ts += f"{output[2]} minute ago"
            elif output[2] > 1:
                ts += f"{output[2]} minutes ago"
        seen = ts
        action = data["action"]
        message = action["message"]
        guild_id, channel_id, message_id = tuple(message)
        message_link = f"https://discord.com/channels/{guild_id}/{channel_id}/{message_id}"
        if isinstance(_object, discord.User):
            member = getattr(self.bot.get_user(action["member"]), "display_name", None) or (
                "<@" + action["member"] + ">"
            )
        elif isinstance(_object, discord.Member):
            member = (_object if isinstance(_object, discord.Guild) else _object.guild).get_member(
                action["member"]
            ) or (  # getattr((_object if isinstance(_object, discord.Guild) else _object.guild).get_member(action["member"]), "display_name", None)
                "<@" + action["member"] + ">"
            )
        elif isinstance(_object, discord.Role):
            member = (_object if isinstance(_object, discord.Guild) else _object.guild).get_member(
                action["member"]
            ) or ("<@" + action["member"] + ">")
        elif isinstance(_object, discord.TextChannel):
            member = (_object if isinstance(_object, discord.Guild) else _object.guild).get_member(
                action["member"]
            ) or ("<@" + action["member"] + ">")
        elif isinstance(_object, discord.CategoryChannel):
            member = (_object if isinstance(_object, discord.Guild) else _object.guild).get_member(
                action["member"]
            ) or ("<@" + action["member"] + ">")
        elif isinstance(_object, discord.Guild):
            member = (_object if isinstance(_object, discord.Guild) else _object.guild).get_member(
                action["member"]
            ) or ("<@" + action["member"] + ">")
        else:
            member = (_object if isinstance(_object, discord.Guild) else _object.guild).get_member(
                action["member"]
            ) or ("<@" + action["member"] + ">")
        reaction = action["reaction"] if "reaction" in action else None
        if _type == "message":
            action = _("[This message]({message_link}) has been sent by {member_mention}.").format(
                message_link=message_link, member_mention=getattr(member, "mention", member)
            )
        elif _type == "message_edit":
            action = _(
                "[This message]({message_link}) has been edited by {member_mention}."
            ).format(message_link=message_link, member_mention=getattr(member, "mention", member))
        elif _type == "reaction_add":
            action = _(
                "The reaction {reaction} has been added to [this message]({message_link}) by {member_mention}."
            ).format(
                reaction=reaction,
                message_link=message_link,
                member_mention=getattr(member, "mention", member),
            )
        elif _type == "reaction_remove":
            action = _(
                "The reaction {reaction} has been removed to the [this message]({message_link}) by {member_mention}."
            ).format(
                reaction=reaction,
                message_link=message_link,
                member_mention=getattr(member, "mention", member),
            )
        return time, seen, action

    async def send_seen(
        self,
        ctx: commands.Context,
        _object: typing.Union[
            discord.User,
            discord.Member,
            discord.Role,
            discord.TextChannel,
            discord.CategoryChannel,
            discord.Guild,
        ],
        _type: typing.Optional[
            typing.Literal["message", "message_edit", "reaction_add", "reaction_remove"]
        ],
        show_details: typing.Optional[bool],
        all_data_config: typing.Optional[typing.Dict] = None,
        all_data_cache: typing.Optional[typing.Dict] = None,
    ) -> None:
        if isinstance(_object, (discord.User, discord.Member)):
            ignored_users = await self.config.ignored_users()
            if _object.id in ignored_users:
                embed = discord.Embed()
                embed.color = discord.Color.red()
                embed.title = _(
                    "This {object_type} is in the ignored users list (`{prefix}seen ignoreme`)."
                ).format(object_type={_object.__class__.__name__.lower()}, prefix=ctx.prefix)
                await ctx.send(embed=embed)
                return
        data = await self.get_data_for(
            _type=_type,
            _object=_object,
            all_data_config=all_data_config,
            all_data_cache=all_data_cache,
        )
        if data is None:
            embed = discord.Embed()
            embed.color = discord.Color.red()
            embed.title = f"I haven't seen this {_object.__class__.__name__.lower()} yet."
            await ctx.send(embed=embed)
            return
        time, seen, action = data
        embed: discord.Embed = discord.Embed()
        embed.color = getattr(_object, "color", await ctx.embed_color())
        # if isinstance(_object, discord.User):
        #     embed.set_author(
        #         name=_("@{_object.display_name} was seen {seen}.").format(
        #             _object=_object, seen=seen
        #         ),
        #         icon_url=_object.display_avatar,
        #     )
        # elif isinstance(_object, discord.Member):
        #     embed.set_author(
        #         name=_("@{_object.display_name} was seen {seen}.").format(
        #             _object=_object, seen=seen
        #         ),
        #         icon_url=_object.display_avatar,
        #     )
        # elif isinstance(_object, discord.Role):
        #     embed.set_author(
        #         name=_("The role @&{_object.name} was seen {seen}.").format(
        #             _object=_object, seen=seen
        #         ),
        #         icon_url=_object.display_icon,
        #     )
        # elif isinstance(_object, discord.TextChannel):
        #     embed.set_author(
        #         name=_("The text channel #{_object.name} was seen {seen}.").format(
        #             _object=_object, seen=seen
        #         ),
        #         icon_url=None,
        #     )
        # elif isinstance(_object, discord.CategoryChannel):
        #     embed.set_author(
        #         name=_("The category {_object.name} was seen {seen}.").format(
        #             _object=_object, seen=seen
        #         ),
        #         icon_url=None,
        #     )
        # elif isinstance(_object, discord.Guild):
        #     embed.set_author(
        #         name=_("The guild {_object.name} was seen {seen}.").format(
        #             _object=_object, seen=seen
        #         ),
        #         icon_url=_object.icon,
        #     )
        if isinstance(_object, discord.User):
            embed.set_author(
                name=_object.display_name,
                icon_url=_object.display_avatar,
            )
            embed.description = _("**The user {_object.mention} was seen {seen}.**").format(
                _object=_object, seen=seen
            )
        elif isinstance(_object, discord.Member):
            embed.set_author(
                name=_object.display_name,
                icon_url=_object.display_avatar,
            )
            embed.description = _("**The member {_object.mention} was seen {seen}.**").format(
                _object=_object, seen=seen
            )
        elif isinstance(_object, discord.Role):
            embed.set_author(
                name=_object.name,
                icon_url=_object.display_icon,
            )
            embed.description = _("**The role {_object.mention} was seen {seen}.**").format(
                _object=_object, seen=seen
            )
        elif isinstance(_object, discord.TextChannel):
            embed.set_author(
                name=_object.name,
                icon_url=None,
            )
            embed.description = _(
                "**The text channel {_object.mention} was seen {seen}.**"
            ).format(_object=_object, seen=seen)
        elif isinstance(_object, discord.CategoryChannel):
            embed.set_author(
                name=_object.name,
                icon_url=None,
            )
            embed.description = _("**The category {_object.name} was seen {seen}.**").format(
                _object=_object, seen=seen
            )
        elif isinstance(_object, discord.Guild):
            embed.set_author(
                name=_object.name,
                icon_url=_object.icon,
            )
            embed.description = _("**The guild {_object.name} was seen {seen}.**").format(
                _object=_object, seen=seen
            )
        if show_details:
            embed.description += f"\n{action}"
            embed.timestamp = datetime.datetime.fromtimestamp(time)
        await ctx.send(embed=embed)

    async def send_board(
        self,
        ctx: commands.Context,
        _object: typing.Literal["users", "members", "roles", "channels", "categories", "guilds"],
        _type: typing.Optional[
            typing.Literal["message", "message_edit", "reaction_add", "reaction_remove"]
        ],
        reverse: typing.Optional[bool] = False,
        bots: typing.Optional[bool] = None,
        include_role: typing.Optional[discord.Role] = None,
        exclude_role: typing.Optional[discord.Role] = None,
    ) -> None:
        await self.save_to_config()
        if _object == "users":
            # prefix = "@"
            users = await self.config.all_users()
            all_data = {
                user: data
                for user_id, data in users.items()
                if (user := ctx.bot.get_user(user_id)) is not None
                and (bots is None or user.bot == bots)
            }
        elif _object == "members":
            # prefix = "@"
            members = await self.config.all_members(ctx.guild)
            all_data = {
                member: data
                for member_id, data in members.items()
                if (
                    (member := ctx.guild.get_member(member_id)) is not None
                    and (bots is None or member.bot == bots)
                    and (include_role is None or include_role in member.roles)
                    and (exclude_role is None or exclude_role not in member.roles)
                )
            }
        elif _object == "roles":
            # prefix = "@&"
            roles = await self.config.all_roles()
            all_data = {
                role: data
                for role_id, data in roles.items()
                if (role := ctx.guild.get_role(role_id)) is not None
            }
        elif _object == "channels":
            # prefix = "#"
            channels = await self.config.all_channels()
            all_data = {
                channel: data
                for channel_id, data in channels.items()
                if (channel := ctx.guild.get_channel(channel_id)) is not None
                and channel.type == discord.ChannelType.text
            }
        elif _object == "categories":
            # prefix = ""
            categories = await self.config.all_channels()
            all_data = {
                category: data
                for category_id, data in categories.items()
                if (category := ctx.guild.get_channel(category_id)) is not None
                and category.type == discord.ChannelType.category
            }
        elif _object == "guilds":
            # prefix = ""
            guilds = await self.config.all_guilds()
            all_data = {
                guild: data
                for guild_id, data in guilds.items()
                if (guild := ctx.bot.get_guild(guild_id)) is not None
            }
        data = {}
        for x in all_data:
            await asyncio.sleep(0)
            result = await self.get_data_for(
                _type=_type, _object=x, all_data_config=all_data[x], all_data_cache={}
            )
            if result is None:
                continue
            time, seen, action = result
            data[x] = [time, seen]
        if not data:
            embed = discord.Embed()
            embed.color = discord.Color.red()
            embed.title = f"I haven't seen any {_object} yet."
            await ctx.send(embed=embed)
            return
        embed: discord.Embed = discord.Embed()
        embed.title = f"Seen Board {_object.capitalize()}" + (
            f" - ({_type})" if _type is not None else ""
        )
        embed.timestamp = datetime.datetime.now()
        embeds = []
        description = []
        all_count = len(data)
        for count, (x, last_seen) in enumerate(
            sorted(data.items(), key=lambda x: x[1][0], reverse=not reverse), start=1
        ):
            seen = last_seen[1]
            description.append(
                f"• **{all_count + 1 - count if reverse else count}** - **{getattr(x, 'mention', getattr(x, 'name', x))}** (`{x.id}`): {seen.capitalize()}."  # {prefix}{getattr(x, 'display_name', getattr(x, 'name', x))}
            )
        description = "\n".join(description)
        for text in pagify(description, page_length=2000):
            e = embed.copy()
            e.description = text
            embeds.append(e)
        await Menu(pages=embeds).start(ctx)

    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    @commands.hybrid_group(invoke_without_command=True)
    async def seen(
        self,
        ctx: commands.Context,
        _type: typing.Optional[
            typing.Literal["message", "message_edit", "reaction_add", "reaction_remove"]
        ],
        show_details: typing.Optional[bool],
        *,
        _object: typing.Union[
            discord.Member, discord.Role, discord.TextChannel, discord.CategoryChannel
        ],
    ) -> None:
        """Check when a member/role/channel/category was last active!"""
        if show_details is None:
            show_details = True
        await self.send_seen(ctx, _type=_type, _object=_object, show_details=show_details)

    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    @seen.command()
    async def member(
        self,
        ctx: commands.Context,
        _type: typing.Optional[
            typing.Literal["message", "message_edit", "reaction_add", "reaction_remove"]
        ],
        show_details: typing.Optional[bool],
        *,
        member: typing.Optional[discord.Member] = None,
    ) -> None:
        """Check when a member was last active!"""
        if member is None:
            member = ctx.author
        if show_details is None:
            show_details = True
        await self.send_seen(ctx, _type=_type, _object=member, show_details=show_details)

    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    @seen.command()
    async def role(
        self,
        ctx: commands.Context,
        _type: typing.Optional[
            typing.Literal["message", "message_edit", "reaction_add", "reaction_remove"]
        ],
        show_details: typing.Optional[bool],
        *,
        role: typing.Optional[discord.Role] = None,
    ) -> None:
        """Check when a role was last active!"""
        if role is None:
            role = ctx.author.top_role
        if show_details is None:
            show_details = True
        await self.send_seen(ctx, _object=role, _type=_type, show_details=show_details)

    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    @seen.command()
    async def channel(
        self,
        ctx: commands.Context,
        _type: typing.Optional[
            typing.Literal["message", "message_edit", "reaction_add", "reaction_remove"]
        ],
        show_details: typing.Optional[bool],
        channel: typing.Optional[discord.TextChannel] = None,
    ) -> None:
        """Check when a channel was last active!"""
        if channel is None:
            channel = ctx.channel
        if show_details is None:
            show_details = True
        if not channel.permissions_for(ctx.author).view_channel:
            raise commands.UserFeedbackCheckFailure(
                _("You do not have permission to view this channel.")
            )
        await self.send_seen(ctx, _object=channel, _type=_type, show_details=show_details)

    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    @seen.command()
    async def category(
        self,
        ctx: commands.Context,
        _type: typing.Optional[
            typing.Literal["message", "message_edit", "reaction_add", "reaction_remove"]
        ],
        show_details: typing.Optional[bool],
        category: typing.Optional[discord.CategoryChannel] = None,
    ) -> None:
        """Check when a category was last active!"""
        if category is None:
            category = ctx.channel.category
        if category is None:
            raise commands.UserInputError()
        if show_details is None:
            show_details = True
        if all(
            not channel.permissions_for(ctx.author).view_channel
            for channel in category.text_channels
        ):
            raise commands.UserFeedbackCheckFailure(
                _("You do not have permission to view any of the channels in this category.")
            )
        await self.send_seen(ctx, _object=category, _type=_type, show_details=show_details)

    @commands.guild_only()
    @commands.is_owner()
    @commands.bot_has_permissions(embed_links=True)
    @seen.command(hidden=True)
    async def hackmember(
        self,
        ctx: commands.Context,
        _type: typing.Optional[
            typing.Literal["message", "message_edit", "reaction_add", "reaction_remove"]
        ],
        show_details: typing.Optional[bool],
        user: discord.User,
    ) -> None:
        """Check when a old member was last active!"""
        if show_details is None:
            show_details = True
        all_data_config = await self.config.member_from_ids(
            guild_id=ctx.guild.id, member_id=user.id
        ).all()
        all_data_cache = self.cache["members"].get(ctx.guild.id, {}).get(user.id, {})
        await self.send_seen(
            ctx,
            _object=user,
            _type=_type,
            show_details=show_details,
            all_data_config=all_data_config,
            all_data_cache=all_data_cache,
        )

    @commands.bot_has_permissions(embed_links=True)
    @seen.command()
    async def guild(
        self,
        ctx: commands.Context,
        _type: typing.Optional[
            typing.Literal["message", "message_edit", "reaction_add", "reaction_remove"]
        ],
        show_details: typing.Optional[bool],
        *,
        guild: typing.Optional[commands.GuildConverter] = None,
    ) -> None:
        """Check when a guild was last active!"""
        if guild is None or ctx.author.id not in ctx.bot.owner_ids:
            guild = ctx.guild
        if show_details is None:
            show_details = True
        await self.send_seen(ctx, _object=guild, _type=_type, show_details=show_details)

    @commands.is_owner()
    @commands.bot_has_permissions(embed_links=True)
    @seen.command(hidden=True)
    async def user(
        self,
        ctx: commands.Context,
        _type: typing.Optional[
            typing.Literal["message", "message_edit", "reaction_add", "reaction_remove"]
        ],
        show_details: typing.Optional[bool],
        *,
        user: typing.Optional[discord.User] = None,
    ) -> None:
        """Check when a user was last active!"""
        if user is None:
            user = ctx.author
        if show_details is None:
            show_details = True
        await self.send_seen(ctx, _object=user, _type=_type, show_details=show_details)

    @commands.is_owner()
    @commands.bot_has_permissions(embed_links=True)
    @seen.command(hidden=True)
    async def hackuser(
        self,
        ctx: commands.Context,
        _type: typing.Optional[
            typing.Literal["message", "message_edit", "reaction_add", "reaction_remove"]
        ],
        show_details: typing.Optional[bool],
        user_id: int,
    ) -> None:
        """Check when a old user was last active!"""
        if show_details is None:
            show_details = True
        user = await ctx.bot.fetch_user(user_id)
        if user is None:
            raise commands.UserFeedbackCheckFailure(f'User "{user_id}" not found.')
        await self.send_seen(ctx, _object=user, _type=_type, show_details=show_details)

    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    @seen.command(invoke_without_command=True)
    async def board(
        self,
        ctx: commands.Context,
        _type: typing.Optional[
            typing.Literal["message", "message_edit", "reaction_add", "reaction_remove"]
        ],
        _object: typing.Optional[
            typing.Literal["members", "roles", "channels", "categories", "guilds", "users"]
        ] = "members",
        reverse: typing.Optional[bool] = False,
        bots: typing.Optional[bool] = None,
        include_role: typing.Optional[discord.Role] = None,
        exclude_role: typing.Optional[discord.Role] = None,
    ) -> None:
        """View a Seen Board for members/roles/channels/categories/guilds/users!

        `bots` is a parameter for `members` and `users`. `include_role` and `exclude_role` are parameters for only `members`.
        """
        if _object in ["guilds", "users"] and ctx.author.id not in ctx.bot.owner_ids:
            raise commands.UserFeedbackCheckFailure(
                _("You're not allowed to view the Seen board for guilds and users.")
            )
        await self.send_board(
            ctx,
            _object=_object,
            _type=_type,
            reverse=reverse,
            bots=bots,
            include_role=include_role,
            exclude_role=exclude_role,
        )

    @commands.is_owner()
    @seen.command()
    async def configstats(self, ctx: commands.Context) -> None:
        """Get Config data stats."""
        (
            global_count,
            users_count,
            members_count,
            roles_count,
            channels_count,
            categories_count,
            guilds_count,
        ) = await self.cleanup(for_count=True)
        stats = {
            "Global count": global_count,
            "Users count": users_count,
            "Members count": members_count,
            "Roles count": roles_count,
            "Text Channels count (+ categories channels)": channels_count,
            "Categories count (+ text channels)": categories_count,
            "Guilds count": guilds_count,
        }
        stats = [f"{key}: {value}" for key, value in stats.items()]
        message = "---------- Config Stats for Seen ----------\n\n" + "\n".join(stats)
        message = box(message)
        await ctx.send(message)

    @commands.is_owner()
    @seen.command()
    async def listener(
        self,
        ctx: commands.Context,
        state: bool,
        _types: commands.Greedy[
            typing.Literal["message", "message_edit", "reaction_add", "reaction_remove"]
        ],
    ) -> None:
        """Enable or disable a listener."""
        config = await self.config.listeners.all()
        for _type in _types:
            config[_type] = state
        await self.config.listeners.set(config)
        if state:
            await ctx.send(_("Listener enabled for this/these type(s)."))
        else:
            await ctx.send(_("Listener disabled for this/these type(s)."))

    @seen.command()
    async def ignoreme(self, ctx: commands.Context) -> None:
        """Asking Seen to ignore your actions."""
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
    @seen.command()
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

    @commands.is_owner()
    @commands.bot_has_permissions(embed_links=True)
    @seen.command(hidden=True)
    async def getdebugloopsstatus(self, ctx: commands.Context) -> None:
        """Get an embed for check loop status."""
        embeds = [loop.get_debug_embed() for loop in self.loops]
        await Menu(pages=embeds).start(ctx)

    @commands.is_owner()
    @seen.command(hidden=True)
    async def purge(
        self,
        ctx: commands.Context,
        _type: typing.Literal["all", "user", "member", "role", "channel", "guild"],
    ) -> None:
        """Purge Config for a specified _type or all."""
        if _type == "all":
            await self.config.clear_all_users()
            await self.config.clear_all_members()
            await self.config.clear_all_roles()
            await self.config.clear_all_channels()
            await self.config.clear_all_guilds()
            await ctx.send(_("All Seen data purged."))
        else:
            if _type == "user":
                await self.config.clear_all_users()
            elif _type == "member":
                await self.config.clear_all_members()
            if _type == "role":
                await self.config.clear_all_roles()
            if _type == "channel":
                await self.config.clear_all_channels()
            if _type == "guild":
                await self.config.clear_all_guilds()
            await ctx.send(_("Seen data purged for this type."))

    @commands.is_owner()
    @seen.command(aliases=["migratefromaika"])
    async def migratefromseen(self, ctx: commands.Context) -> None:
        """Migrate Seen from Seen by Aikaterna."""
        old_config: Config = Config.get_conf(
            "Seen", identifier=2784481001, force_registration=True, cog_name="Seen"
        )
        old_global_data = await old_config.all()
        if "schema_version" not in old_global_data:
            raise commands.UserFeedbackCheckFailure(
                _("Seen by Aikaterna has no data in this bot.")
            )
        elif old_global_data["schema_version"] != 2:
            raise commands.UserFeedbackCheckFailure(
                _(
                    "Seen by Aikaterna use an old/new data schema version and isn't compatible with this cog actually."
                )
            )
        new_global_data = await self.config.all()
        new_user_group = self.config._get_base_group(self.config.USER)
        new_member_group = self.config._get_base_group(self.config.MEMBER)
        old_members_data = await old_config.all_members()
        async with new_user_group.all() as new_users_data:
            async with new_member_group.all() as new_members_data:
                for guild_id in old_members_data:
                    for member_id, time in old_members_data[guild_id].items():
                        if ctx.bot.get_user(int(member_id)) is None:
                            continue
                        data = {
                            "seen": int(time["seen"]),
                            "action": {
                                "message": [0, 0, 0],
                                "member": int(member_id),
                                "reaction": None,
                            },
                        }
                        # Global
                        custom_id = CogsUtils.generate_key(
                            length=10,
                            existing_keys=self.cache["existing_keys"],
                            strings_used={
                                "ascii_lowercase": True,
                                "ascii_uppercase": True,
                                "digits": True,
                                "punctuation": False,
                                "others": [],
                            },
                        )
                        if "message" not in new_global_data:
                            new_global_data["message"] = {}
                        new_global_data["message"][custom_id] = data
                        self.cache["existing_keys"].append(custom_id)
                        # Users
                        if int(member_id) not in new_users_data:
                            new_users_data[int(member_id)] = {}
                        if (
                            "message" not in new_users_data[int(member_id)]
                            or data["seen"]
                            > new_global_data["message"][
                                new_users_data[int(member_id)]["message"]
                            ]["seen"]
                        ):
                            new_users_data[int(member_id)]["message"] = custom_id
                        # Members
                        if int(guild_id) not in new_members_data:
                            new_members_data[int(guild_id)] = {}
                        if int(member_id) not in new_members_data[int(guild_id)]:
                            new_members_data[int(guild_id)][int(member_id)] = {}
                        if (
                            "message" not in new_members_data[int(guild_id)][int(member_id)]
                            or data["seen"]
                            > new_global_data["message"][
                                new_members_data[int(guild_id)][int(member_id)]["message"]
                            ]["seen"]
                        ):
                            new_members_data[int(guild_id)][int(member_id)]["message"] = custom_id
        await self.config.set(new_global_data)
        await ctx.send(_("Data successfully migrated from Seen by Aikaterna."))

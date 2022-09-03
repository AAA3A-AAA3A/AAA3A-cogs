from .AAA3A_utils import CogsUtils, Menu  # isort:skip
from redbot.core import commands, Config  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
from redbot.core.bot import Red  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import asyncio
import datetime
import time as _time

from copy import deepcopy

from redbot.core.utils.chat_formatting import pagify, box

if CogsUtils().is_dpy2:  # To remove
    setattr(commands, "Literal", typing.Literal)

# Credits:
# Thanks to @epic guy on Discord for the basic syntax (command groups, commands) and also commands (await ctx.send, await ctx.author.send, await ctx.message.delete())!
# Thanks to @aikaterna on Discord for the cog idea and a part of the code! (https://github.com/aikaterna/aikaterna-cogs/blob/v3/seen/seen.py)
# Thanks to the developers of the cogs I added features to as it taught me how to make a cog! (Chessgame by WildStriker, Captcha by Kreusada, Speak by Epic guy and Rommer by Dav)
# Thanks to all the people who helped me with some commands in the #coding channel of the redbot support server!

_ = Translator("Seen", __file__)

if CogsUtils().is_dpy2:
    from functools import partial
    hybrid_command = partial(commands.hybrid_command, with_app_command=False)
    hybrid_group = partial(commands.hybrid_group, with_app_command=False)
else:
    hybrid_command = commands.command
    hybrid_group = commands.group

@cog_i18n(_)
class Seen(commands.Cog):
    """A cog to check when a member/role/channel/category/user/guild was last active!"""

    def __init__(self, bot: Red):
        self.bot: Red = bot

        self.config: Config = Config.get_conf(
            self,
            identifier=864398642893,
            force_registration=True,
        )
        self.global_config = {
            "message": {},
            "message_edit": {},
            "reaction_add": {},
            "reaction_remove": {},
            "ignored_users": [345628097929936898],  # MAX
            "listeners": {
                "message": True,
                "message_edit": True,
                "reaction_add": True,
                "reaction_remove": True
            }
        }
        self.default_config = {
            "message": None,
            "message_edit": None,
            "reaction_add": None,
            "reaction_remove": None
        }
        self.config.register_global(**self.global_config)
        self.config.register_user(**self.default_config)
        self.config.register_member(**self.default_config)
        self.config.register_role(**self.default_config)
        self.config.register_channel(**self.default_config)
        self.config.register_guild(**self.default_config)

        self.cache = {"global": {}, "users": {}, "members": {}, "roles": {}, "channels": {}, "categories": {}, "guilds": {}, "existing_keys": []}

        self.cogsutils = CogsUtils(cog=self)
        self.cogsutils._setup()
        self.purge.very_hidden = True

        self.cogsutils.create_loop(function=self.save_to_config, name="Save Seen Config", minutes=1)

    if CogsUtils().is_dpy2:
        async def cog_unload(self):
            self.cogsutils._end()
            asyncio.create_task(self.save_to_config())
    else:
        def cog_unload(self):
            self.cogsutils._end()
            asyncio.create_task(self.save_to_config())

    async def red_delete_data_for_user(self, *, requester: typing.Literal["discord_deleted_user", "owner", "user", "user_strict"], user_id: int):
        """Delete all Seen data for user, members, roles, channels, categories, guilds; if the user ID matches."""
        if requester not in ["discord_deleted_user", "owner", "user", "user_strict"]:
            return
        global_data = await self.config.all()
        member_group = self.config._get_base_group(self.config.MEMBER)
        role_group = self.config._get_base_group(self.config.ROLE)
        channel_group = self.config._get_base_group(self.config.CHANNEL)
        category_group = self.config._get_base_group(self.config.CHANNEL)
        guild_group = self.config._get_base_group(self.config.GUILD)
        # Users
        await self.config.user_from_id(user_id).clear()
        # Members
        async with member_group.all() as members_data:
            _members_data = deepcopy(members_data)
            for guild in _members_data:
                if str(user_id) in _members_data[guild]:
                    del members_data[guild][str(user_id)]
        # Roles
        async with role_group.all() as roles_data:
            _roles_data = deepcopy(roles_data)
            for role in _roles_data:
                for type, custom_id in _roles_data[role].items():
                    if global_data[type].get(custom_id, {"action": {"member": None}})["action"]["member"] == user_id:
                        roles_data[role][type] = None
        # Channels
        async with channel_group.all() as channels_data:
            _channels_data = deepcopy(channels_data)
            for channel in _channels_data:
                for type, custom_id in _channels_data[channel].items():
                    if global_data[type].get(custom_id, {"action": {"member": None}})["action"]["member"] == user_id:
                        channels_data[channel][type] = None
        # Categories
        async with category_group.all() as categories_data:
            _categories_data = deepcopy(categories_data)
            for category in _categories_data:
                for type, custom_id in _categories_data[category].items():
                    if global_data[type].get(custom_id, {"action": {"member": None}})["action"]["member"] == user_id:
                        categories_data[category][type] = None
        # Guilds
        async with guild_group.all() as guilds_data:
            _guilds_data = deepcopy(guilds_data)
            for guild in guilds_data:
                for type, custom_id in _guilds_data[guild].items():
                    if global_data[type].get(custom_id, {"action": {"member": None}})["action"]["member"] == user_id:
                        guilds_data[guild][type] = None

    def upsert_cache(self, time: _time, type: typing.Literal["message", "message_edit", "reaction_add", "reaction_remove"], member: discord.Member, guild: discord.Guild, channel: discord.TextChannel, message: discord.Message, reaction: typing.Optional[str]=None):
        if not isinstance(channel, discord.TextChannel):
            return
        custom_id = self.cogsutils.generate_key(number=10, existing_keys=self.cache["existing_keys"], strings_used={"ascii_lowercase": True, "ascii_uppercase": True, "digits": True, "punctuation": False, "others": []})
        data = {"seen": int(time), "action": {"message": [message.guild.id, message.channel.id, message.id], "member": member.id, "reaction": reaction}}
        if data["action"]["reaction"] is None:
            del data["action"]["reaction"]
        # Global (data)
        if type not in self.cache["global"]:
            self.cache["global"][type] = {}
        self.cache["global"][type][custom_id] = data
        self.cache["existing_keys"].append(custom_id)
        # Users
        if member._user.id not in self.cache["users"]:
            self.cache["users"][member._user.id] = {}
        self.cache["users"][member._user.id][type] = custom_id
        # Members
        if guild.id not in self.cache["members"]:
            self.cache["members"][guild.id] = {}
        if member.id not in self.cache["members"][guild.id]:
            self.cache["members"][guild.id][member.id] = {}
        self.cache["members"][guild.id][member.id][type] = custom_id
        # Roles
        if guild.id not in self.cache["roles"]:
            self.cache["roles"][guild.id] = {}
        for role in member.roles:
            if role.id not in self.cache["roles"][guild.id]:
                self.cache["roles"][guild.id][role.id] = {}
            self.cache["roles"][guild.id][role.id][type] = custom_id
        # Channels
        if guild.id not in self.cache["channels"]:
            self.cache["channels"][guild.id] = {}
        if channel.id not in self.cache["channels"][guild.id]:
            self.cache["channels"][guild.id][channel.id] = {}
        self.cache["channels"][guild.id][channel.id][type] = custom_id
        # Categories
        if channel.category is not None:
            if guild.id not in self.cache["categories"]:
                self.cache["categories"][guild.id] = {}
            if channel.category.id not in self.cache["categories"][guild.id]:
                self.cache["categories"][guild.id][channel.category.id] = {}
            self.cache["categories"][guild.id][channel.category.id][type] = custom_id
        # Guilds
        if guild.id not in self.cache["guilds"]:
            self.cache["guilds"][guild.id] = {}
        self.cache["guilds"][guild.id][type] = custom_id

    async def save_to_config(self):
        cache = self.cache.copy()
        cache["existing_keys"] = []
        if cache == {"global": {}, "users": {}, "members": {}, "roles": {}, "channels": {}, "categories": {}, "guilds": {}, "existing_keys": []}:
            return
        self.cache = {"global": {}, "users": {}, "members": {}, "roles": {}, "channels": {}, "categories": {}, "guilds": {}, "existing_keys": self.cache["existing_keys"].copy()}
        user_group = self.config._get_base_group(self.config.USER)
        member_group = self.config._get_base_group(self.config.MEMBER)
        role_group = self.config._get_base_group(self.config.ROLE)
        channel_group = self.config._get_base_group(self.config.CHANNEL)
        category_group = self.config._get_base_group(self.config.CHANNEL)
        guild_group = self.config._get_base_group(self.config.GUILD)
        # Global
        async with self.config.all() as global_data:
            for type in cache["global"]:
                for custom_id, data in cache["global"][type].items():
                    global_data[type][custom_id] = data
        # Users
        async with user_group.all() as users_data:
            for user in cache["users"]:
                if str(user) not in users_data:
                    users_data[str(user)] = {}
                for type, custom_id in cache["users"][user].items():
                    users_data[str(user)][type] = custom_id
        # Members
        async with member_group.all() as members_data:
            for guild in cache["members"]:
                for member in cache["members"][guild]:
                    if str(guild) not in members_data:
                        members_data[str(guild)] = {}
                    if str(member) not in members_data[str(guild)]:
                        members_data[str(guild)][str(member)] = {}
                    for type in cache["members"][guild][member]:
                        custom_id = cache["members"][guild][member][type]
                        members_data[str(guild)][str(member)][str(type)] = custom_id
        # Roles
        async with role_group.all() as roles_data:
            for guild in cache["roles"]:
                for role in cache["roles"][guild]:
                    if str(role) not in roles_data:
                        roles_data[str(role)] = {}
                    for type in cache["roles"][guild][role]:
                        custom_id = cache["roles"][guild][role][type]
                        roles_data[str(role)][type] = custom_id
        # Channels
        async with channel_group.all() as channels_data:
            for guild in cache["channels"]:
                for channel in cache["channels"][guild]:
                    if str(channel) not in channels_data:
                        channels_data[str(channel)] = {}
                    for type in cache["channels"][guild][channel]:
                        custom_id = cache["channels"][guild][channel][type]
                        channels_data[str(channel)][type] = custom_id
        # Categories
        async with category_group.all() as categories_data:
            for guild in cache["categories"]:
                for category in cache["categories"][guild]:
                    if str(category) not in categories_data:
                        categories_data[str(category)] = {}
                    for type in cache["categories"][guild][category]:
                        custom_id = cache["categories"][guild][category][type]
                        categories_data[str(category)][type] = custom_id
        # Guilds
        async with guild_group.all() as guilds_data:
            for guild in cache["guilds"]:
                if str(guild) not in guilds_data:
                    guilds_data[str(guild)] = {}
                for type, custom_id in cache["guilds"][guild].items():
                    guilds_data[str(guild)][type] = custom_id
        # Run Cleanup
        await self.cleanup()

    async def cleanup(self, for_count: typing.Optional[bool]=False):
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
        # Users
        for user in users_data:
            for custom_id in users_data[user].values():
                if custom_id is not None:
                    if not for_count:
                        # if custom_id not in self.cache["existing_keys"]:
                        existing_keys.append(custom_id)
                    else:
                        users_count += 1
        # Members
        for guild in members_data:
            for member in members_data[guild]:
                for custom_id in members_data[guild][member].values():
                    if custom_id is not None:
                        if not for_count:
                            # if custom_id not in self.cache["existing_keys"]:
                            existing_keys.append(custom_id)
                        else:
                            members_count += 1
        # Roles
        for role in roles_data:
            for custom_id in roles_data[role].values():
                if custom_id is not None:
                    if not for_count:
                        # if custom_id not in self.cache["existing_keys"]:
                        existing_keys.append(custom_id)
                    else:
                        roles_count += 1
        # Channels
        for channel in channels_data:
            for custom_id in channels_data[channel].values():
                if custom_id is not None:
                    if not for_count:
                        # if custom_id not in self.cache["existing_keys"]:
                        existing_keys.append(custom_id)
                    else:
                        channels_count += 1
        # Categories
        for category in categories_data:
            for custom_id in categories_data[category].values():
                if custom_id is not None:
                    if not for_count:
                        # if custom_id not in self.cache["existing_keys"]:
                        existing_keys.append(custom_id)
                    else:
                        categories_count += 1
        # Guilds
        for guild in guilds_data:
            for custom_id in guilds_data[guild].values():
                if custom_id is not None:
                    if not for_count:
                        # if custom_id not in self.cache["existing_keys"]:
                        existing_keys.append(custom_id)
                    else:
                        guilds_count += 1
        if not for_count:
            self.cache["existing_keys"] = list(set(existing_keys))
        # Global
        async with self.config.all() as global_data:
            _global_data = deepcopy(global_data)
            for type in _global_data:
                for custom_id in _global_data[type]:
                    if not for_count:
                        if custom_id not in self.cache["existing_keys"]:  # The action is no longer used by any data.
                            try:
                                del global_data[type][custom_id]
                            except IndexError:
                                pass
                    else:
                        global_count += 1
        if for_count:
            return global_count, users_count, members_count, roles_count, channels_count, categories_count, guilds_count

    async def get_data_for(self, object: typing.Union[discord.User, discord.Member, discord.Role, discord.TextChannel, discord.CategoryChannel, discord.Guild], type: typing.Optional[typing.Literal["message", "message_edit", "reaction_add", "reaction_remove"]], all_data_config: typing.Optional[typing.Dict]=None, all_data_cache: typing.Optional[typing.Dict]=None):
        global_data = await self.config.all()
        if not all([all_data_config is not None, all_data_cache is not None]):
            if isinstance(object, discord.User):
                all_data_config = await self.config.user(object).all()
                all_data_cache = self.cache["users"].get(object.id, {})
            elif isinstance(object, discord.Member):
                all_data_config = await self.config.member(object).all()
                all_data_cache = self.cache["members"].get(object.guild.id, {}).get(object.id, {})
            elif isinstance(object, discord.Role):
                all_data_config = await self.config.role(object).all()
                all_data_cache = self.cache["roles"].get(object.guild.id, {}).get(object.id, {})
            elif isinstance(object, discord.TextChannel):
                all_data_config = await self.config.channel(object).all()
                all_data_cache = self.cache["channels"].get(object.guild.id, {}).get(object.id, {})
            elif isinstance(object, discord.CategoryChannel):
                all_data_config = await self.config.channel(object).all()
                all_data_cache = self.cache["categories"].get(object.guild.id, {}).get(object.id, {})
            elif isinstance(object, discord.Guild):
                all_data_config = await self.config.guild(object).all()
                all_data_cache = self.cache["guilds"].get(object.id, {})
            else:
                return None
        if type is not None:
            custom_ids = [custom_id for custom_id in [all_data_config.get(type, None), all_data_cache.get(type, None)] if custom_id is not None]
            if len(custom_ids) == 0:
                return
            custom_id = sorted(custom_ids, key=lambda x: global_data[type].get(x, {}).get("seen") or self.cache["global"].get(type, {}).get(x, {}).get("seen"), reverse=True)[0]
            data = global_data[type][custom_id]
            if data["seen"] is None or data["action"] is None:
                return None
        else:
            all_data_config = {x: all_data_config[x] for x in ["message", "message_edit", "reaction_add", "reaction_remove"] if all_data_config[x] is not None}
            all_data_cache = {x: all_data_cache.get(x, None) for x in ["message", "message_edit", "reaction_add", "reaction_remove"] if all_data_cache.get(x, None) is not None}
            all_data_config = [{"type": x, "seen": global_data[x].get(all_data_config[x], {"seen": None, "action": None})["seen"], "action": global_data[x].get(all_data_config[x], {"seen": None, "action": None})["action"]} for x in all_data_config if global_data[x].get(all_data_config[x], {"seen": None, "action": None})["seen"] is not None and global_data[x].get(all_data_config[x], {"seen": None, "action": None})["action"] is not None]
            all_data_cache = [{"type": x, "seen": global_data[x].get(all_data_cache[x], {"seen": None, "action": None})["seen"], "action": global_data[x].get(all_data_cache[x], {"seen": None, "action": None})["action"]} for x in all_data_cache if global_data[x].get(all_data_cache[x], {"seen": None, "action": None})["seen"] is not None and global_data[x].get(all_data_cache[x], {"seen": None, "action": None})["action"] is not None]
            all_data = all_data_config + all_data_cache
            if len(all_data) == 0:
                return None
            data = sorted(all_data, key=lambda x: x["seen"], reverse=True)[0]
            type = data["type"]
            del data["type"]
        time = data["seen"]
        now = int(_time.time())
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
                ts += "{} day, ".format(output[0])
            elif output[0] > 1:
                ts += "{} days, ".format(output[0])
            if output[1] == 1:
                ts += "{} hour, ".format(output[1])
            elif output[1] > 1:
                ts += "{} hours, ".format(output[1])
            if output[2] == 1:
                ts += "{} minute ago".format(output[2])
            elif output[2] > 1:
                ts += "{} minutes ago".format(output[2])
        seen = ts
        action = data["action"]
        message = action["message"]
        guild_id, channel_id, message_id = tuple(message)
        message_link = f"https://discord.com/channels/{guild_id}/{channel_id}/{message_id}"
        if isinstance(object, discord.User):
            member = getattr(self.bot.get_user(action["member"]), "display_name", None) or ("<@" + action["member"] + ">")
        elif isinstance(object, discord.Member):
            member = getattr(object.guild.get_member(action["member"]), "display_name", None) or ("<@" + action["member"] + ">")
        elif isinstance(object, discord.Role):
            member = getattr(object.guild.get_member(action["member"]), "display_name", None) or ("<@" + action["member"] + ">")
        elif isinstance(object, discord.TextChannel):
            member = getattr(object.guild.get_member(action["member"]), "display_name", None) or ("<@" + action["member"] + ">")
        elif isinstance(object, discord.CategoryChannel):
            member = getattr(object.guild.get_member(action["member"]), "display_name", None) or ("<@" + action["member"] + ">")
        elif isinstance(object, discord.Guild):
            member = getattr(object.get_member(action["member"]), "display_name", None) or ("<@" + action["member"] + ">")
        else:
            member = getattr(self.bot.get_user(action["member"]), "display_name", None) or ("<@" + action["member"] + ">")
        reaction = action["reaction"] if "reaction" in action else None
        if type == "message":
            action = f"[This message]({message_link}) has been sent by @{member}."
        elif type == "message_edit":
            action = f"[This message]({message_link}) has been edited by @{member}."
        elif type == "reaction_add":
            action = f"The reaction {reaction} has been added to [this message]({message_link}) by @{member}."
        elif type == "reaction_remove":
            action = f"The reaction {reaction} has been removed to the [this message]({message_link}) by @{member}."
        return time, seen, action

    async def send_seen(self, ctx: commands.Context, object: typing.Union[discord.User, discord.Member, discord.Role, discord.TextChannel, discord.CategoryChannel, discord.Guild], type: typing.Optional[typing.Literal["message", "message_edit", "reaction_add", "reaction_remove"]], show_details: typing.Optional[bool], all_data_config: typing.Optional[typing.Dict]=None, all_data_cache: typing.Optional[typing.Dict]=None):
        async with ctx.typing():
            if isinstance(object, (discord.User, discord.Member)):
                ignored_users = await self.config.ignored_users()
                if object.id in ignored_users:
                    embed = discord.Embed()
                    embed.color = discord.Color.red()
                    embed.title = f"This {object.__class__.__name__.lower()} is in the ignored users list (`{ctx.prefix}seen ignoreme`)."
                    await ctx.send(embed=embed)
                    return
            data = await self.get_data_for(type=type, object=object, all_data_config=all_data_config, all_data_cache=all_data_cache)
            if data is None:
                embed = discord.Embed()
                embed.color = discord.Color.red()
                embed.title = f"I haven't seen this {object.__class__.__name__.lower()} yet."
                await ctx.send(embed=embed)
                return
            time, seen, action = data
            embed: discord.Embed = discord.Embed()
            embed.color = getattr(object, "color", discord.Color.green())
            if isinstance(object, discord.User):
                embed.set_author(name=_("@{object.display_name} was seen {seen}.").format(**locals()), icon_url=object.display_avatar if self.cogsutils.is_dpy2 else object.avatar_url)
            elif isinstance(object, discord.Member):
                embed.set_author(name=_("@{object.display_name} was seen {seen}.").format(**locals()), icon_url=object.display_avatar if self.cogsutils.is_dpy2 else object.avatar_url)
            elif isinstance(object, discord.Role):
                embed.set_author(name=_("The role @&{object.name} was seen {seen}.").format(**locals()), icon_url=None)
            elif isinstance(object, discord.TextChannel):
                embed.set_author(name=_("The text channel #{object.name} was seen {seen}.").format(**locals()), icon_url=None)
            elif isinstance(object, discord.CategoryChannel):
                embed.set_author(name=_("The category {object.name} was seen {seen}.").format(**locals()), icon_url=None)
            elif isinstance(object, discord.Guild):
                embed.set_author(name=_("The guild {object.name} was seen {seen}.").format(**locals()), icon_url=object.icon if self.cogsutils.is_dpy2 else object.icon_url)
            if show_details:
                embed.description = action
                embed.timestamp = datetime.datetime.fromtimestamp(time)
        await ctx.send(embed=embed)

    async def send_board(self, ctx: commands.Context, object: typing.Literal["users", "members", "roles", "channels", "categories", "guilds"], type: typing.Optional[typing.Literal["message", "message_edit", "reaction_add", "reaction_remove"]], reverse: typing.Optional[bool]=False):
        async with ctx.typing():
            await self.save_to_config()
            if object == "users":
                users = await self.config.all_users()
                all_data = {ctx.bot.get_user(user): data for user, data in users.items() if ctx.bot.get_user(user) is not None}
            elif object == "members":
                members = await self.config.all_members(ctx.guild)
                all_data = {ctx.guild.get_member(member): data for member, data in members.items() if ctx.guild.get_member(member) is not None}
            elif object == "roles":
                roles = await self.config.all_roles()
                all_data = {ctx.guild.get_role(role): data for role, data in roles.items() if ctx.guild.get_role(role) is not None}
            elif object == "channels":
                channels = await self.config.all_channels()
                all_data = {ctx.guild.get_channel(channel): data for channel, data in channels.items() if ctx.guild.get_channel(channel) is not None and ctx.guild.get_channel(channel).type == discord.ChannelType.text}
            elif object == "categories":
                categories = await self.config.all_channels()
                all_data = {ctx.guild.get_channel(category): data for category, data in categories.items() if ctx.guild.get_channel(category) is not None and ctx.guild.get_channel(category).type == discord.ChannelType.category}
            elif object == "guilds":
                guilds = await self.config.all_guilds()
                all_data = {ctx.bot.get_guild(guild): data for guild, data in guilds.items() if ctx.bot.get_guild(guild) is not None}
            data = {}
            for x in all_data:
                result = await self.get_data_for(type=type, object=x, all_data_config=all_data[x], all_data_cache={})
                if result is None:
                    continue
                time, seen, action = result
                data[x] = [time, seen]
            if len(data) == 0:
                embed = discord.Embed()
                embed.color = discord.Color.red()
                embed.title = f"I haven't seen any {object} yet."
                await ctx.send(embed=embed)
                return
            embed: discord.Embed = discord.Embed()
            embed.title = f"Seen Board for the {object.capitalize()}"
            embed.timestamp = datetime.datetime.now()
            embeds = []
            description = []
            count = 0
            all_count = len(data)
            for x, y in sorted(data.items(), key=lambda x: x[1][0], reverse=not reverse):
                count += 1
                seen = y[1]
                description.append(f"{(count) if not reverse else ((all_count + 1) - count)} - **{x}**: {seen}.")
            description = "\n".join(description)
            for text in pagify(description):
                e = embed.copy()
                e.description = text
                embeds.append(e)
        await Menu(pages=embeds).start(ctx)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if isinstance(message, discord.WebhookMessage):
            return
        if message.guild is None:
            return
        if not isinstance(message.author, discord.Member):
            return
        if not message.author.bot:
            ctx: commands.Context = await self.bot.get_context(message)
            if ctx.valid:
                if ctx.command.cog_name is not None and ctx.command.cog_name == "Seen":  # The commands of this cog will not be counted in order to measure its own absence for example.
                    return
        if message.author.id == message.guild.me.id and len(message.embeds) == 1 and ("Seen".lower() in message.embeds[0].to_dict().get("author", {}).get("name", "").lower() or "Seen".lower() in message.embeds[0].to_dict().get("title", "").lower()):
            return
        ignored_users = await self.config.ignored_users()
        if message.author.id in ignored_users:
            return
        if not await self.config.listeners.message():
            return
        self.upsert_cache(time=_time.time(), type="message", member=message.author, guild=message.guild, channel=message.channel, message=message, reaction=None)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if isinstance(after, discord.WebhookMessage):
            return
        if after.guild is None:
            return
        if not isinstance(after.author, discord.Member):
            return
        ignored_users = await self.config.ignored_users()
        if after.author.id in ignored_users:
            return
        if not await self.config.listeners.message_edit():
            return
        self.upsert_cache(time=_time.time(), type="message_edit", member=after.author, guild=after.guild, channel=after.channel, message=after, reaction=None)

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction: discord.Reaction, user: typing.Union[discord.Member, discord.User]):
        if reaction.message.guild is None:
            return
        if not isinstance(user, discord.Member):
            return
        if user.id == reaction.message.guild.me.id and reaction.emoji == "✅":
            if not reaction.message.author.bot:
                ctx: commands.Context = await self.bot.get_context(reaction.message)
                if ctx.valid:
                    if ctx.command.cog_name is not None and ctx.command.cog_name == "Seen":  # The commands of this cog will not be counted in order to measure its own absence for example.
                        return
        ignored_users = await self.config.ignored_users()
        if user.id in ignored_users:
            return
        if not await self.config.listeners.reaction_add():
            return
        self.upsert_cache(time=_time.time(), type="reaction_add", member=user, guild=user.guild, channel=reaction.message.channel, message=reaction.message, reaction=str(reaction.emoji))

    @commands.Cog.listener()
    async def on_reaction_remove(self, reaction: discord.Reaction, user: typing.Union[discord.Member, discord.User]):
        if reaction.message.guild is None:
            return
        if not isinstance(user, discord.Member):
            return
        ignored_users = await self.config.ignored_users()
        if user.id in ignored_users:
            return
        if not await self.config.listeners.reaction_remove():
            return
        self.upsert_cache(time=_time.time(), type="reaction_remove", member=user, guild=user.guild, channel=reaction.message.channel, message=reaction.message, reaction=str(reaction.emoji))

    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    @hybrid_group(invoke_without_command=True)
    async def seen(self, ctx: commands.Context, type: typing.Optional[commands.Literal["message", "message_edit", "reaction_add", "reaction_remove"]], show_details: typing.Optional[bool], *, object: typing.Union[discord.Member, discord.Role, discord.TextChannel, discord.CategoryChannel]):
        """Check when a member/role/channel/category was last active!"""
        if show_details is None:
            show_details = True
        await self.send_seen(ctx, type=type, object=object, show_details=show_details)
        await ctx.tick()

    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    @seen.command()
    async def member(self, ctx: commands.Context, type: typing.Optional[commands.Literal["message", "message_edit", "reaction_add", "reaction_remove"]], show_details: typing.Optional[bool], *, member: typing.Optional[discord.Member]=None):
        """Check when a member was last active!"""
        if member is None:
            member = ctx.author
        if show_details is None:
            show_details = True
        await self.send_seen(ctx, type=type, object=member, show_details=show_details)
        await ctx.tick()

    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    @seen.command()
    async def role(self, ctx: commands.Context, type: typing.Optional[commands.Literal["message", "message_edit", "reaction_add", "reaction_remove"]], show_details: typing.Optional[bool], *, role: typing.Optional[discord.Role]=None):
        """Check when a role was last active!"""
        if role is None:
            role = ctx.author.top_role
        if show_details is None:
            show_details = True
        await self.send_seen(ctx, object=role, type=type, show_details=show_details)
        await ctx.tick()

    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    @seen.command()
    async def channel(self, ctx: commands.Context, type: typing.Optional[commands.Literal["message", "message_edit", "reaction_add", "reaction_remove"]], show_details: typing.Optional[bool], channel: typing.Optional[discord.TextChannel]=None):
        """Check when a channel was last active!"""
        if channel is None:
            channel = ctx.channel
        if show_details is None:
            show_details = True
        if not channel.permissions_for(ctx.author).view_channel:
            await ctx.send(_("You do not have permission to view this channel.").format(**locals()))
            return
        await self.send_seen(ctx, object=channel, type=type, show_details=show_details)
        await ctx.tick()

    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    @seen.command()
    async def category(self, ctx: commands.Context, type: typing.Optional[commands.Literal["message", "message_edit", "reaction_add", "reaction_remove"]], show_details: typing.Optional[bool], category: typing.Optional[discord.CategoryChannel]=None):
        """Check when a category was last active!"""
        if category is None:
            category = ctx.channel.category
            if category is None:
                await ctx.send_help()
                return
        if show_details is None:
            show_details = True
        if all([not channel.permissions_for(ctx.author).view_channel for channel in category.text_channels]):
            await ctx.send(_("You do not have permission to view any of the channels in this category.").format(**locals()))
            return
        await self.send_seen(ctx, object=category, type=type, show_details=show_details)
        await ctx.tick()

    @commands.guild_only()
    @commands.is_owner()
    @commands.bot_has_permissions(embed_links=True)
    @seen.command(hidden=True)
    async def hackmember(self, ctx: commands.Context, type: typing.Optional[commands.Literal["message", "message_edit", "reaction_add", "reaction_remove"]], show_details: typing.Optional[bool], user: discord.User):
        """Check when a old member was last active!"""
        if show_details is None:
            show_details = True
        all_data_config = await self.config.member_from_ids(guild_id=ctx.guild.id, member_id=user.id).all()
        all_data_cache = self.cache["members"].get(ctx.guild.id, {}).get(user.id, {})
        await self.send_seen(ctx, object=user, type=type, show_details=show_details, all_data_config=all_data_config, all_data_cache=all_data_cache)
        await ctx.tick()

    @commands.bot_has_permissions(embed_links=True)
    @seen.command()
    async def guild(self, ctx: commands.Context, type: typing.Optional[commands.Literal["message", "message_edit", "reaction_add", "reaction_remove"]], show_details: typing.Optional[bool], *, guild: typing.Optional[discord.ext.commands.converter.GuildConverter]=None):
        """Check when a guild was last active!"""
        if guild is None or ctx.author.id not in ctx.bot.owner_ids:
            guild = ctx.guild
        if show_details is None:
            show_details = True
        await self.send_seen(ctx, object=guild, type=type, show_details=show_details)
        await ctx.tick()

    @commands.is_owner()
    @commands.bot_has_permissions(embed_links=True)
    @seen.command(hidden=True)
    async def user(self, ctx: commands.Context, type: typing.Optional[commands.Literal["message", "message_edit", "reaction_add", "reaction_remove"]], show_details: typing.Optional[bool], *, user: typing.Optional[discord.User]=None):
        """Check when a user was last active!"""
        if user is None:
            user = ctx.author
        if show_details is None:
            show_details = True
        await self.send_seen(ctx, object=user, type=type, show_details=show_details)
        await ctx.tick()

    @commands.is_owner()
    @commands.bot_has_permissions(embed_links=True)
    @seen.command(hidden=True)
    async def hackuser(self, ctx: commands.Context, type: typing.Optional[commands.Literal["message", "message_edit", "reaction_add", "reaction_remove"]], show_details: typing.Optional[bool], user_id: int):
        """Check when a old user was last active!"""
        if show_details is None:
            show_details = True
        user = await ctx.bot.fetch_user(user_id)
        if user is None:
            await ctx.send(f'User "{user_id}" not found.')
            return
        await self.send_seen(ctx, object=user, type=type, show_details=show_details)
        await ctx.tick()

    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    @seen.group(invoke_without_command=True)
    async def board(self, ctx: commands.Context, type: typing.Optional[commands.Literal["message", "message_edit", "reaction_add", "reaction_remove"]], object: typing.Optional[typing.Literal["members", "roles", "channels", "categories"]]="members", reverse: typing.Optional[bool]=False):
        """View a Seen Board for members/roles/channels/categories!"""
        await self.send_board(ctx, object=object, type=type, reverse=reverse)
        await ctx.tick()

    @commands.is_owner()
    @commands.bot_has_permissions(embed_links=True)
    @board.command(name="guilds")
    async def board_guilds(self, ctx: commands.Context, type: typing.Optional[commands.Literal["message", "message_edit", "reaction_add", "reaction_remove"]], reverse: typing.Optional[bool]=False):
        """View a Seen Board for guilds!"""
        object = "guilds"
        await self.send_board(ctx, object=object, type=type, reverse=reverse)
        await ctx.tick()

    @commands.is_owner()
    @commands.bot_has_permissions(embed_links=True)
    @board.command(name="users", hidden=True)
    async def board_users(self, ctx: commands.Context, type: typing.Optional[commands.Literal["message", "message_edit", "reaction_add", "reaction_remove"]], reverse: typing.Optional[bool]=False):
        """View a Seen Board for users!"""
        object = "users"
        await self.send_board(ctx, object=object, type=type, reverse=reverse)
        await ctx.tick()

    @commands.is_owner()
    @seen.command()
    async def configstats(self, ctx: commands.Context):
        """Get Config data stats."""
        async with ctx.typing():
            global_count, users_count, members_count, roles_count, channels_count, categories_count, guilds_count = await self.cleanup(for_count=True)
            stats = {
                "Global count": global_count,
                "Users count": users_count,
                "Members count": members_count,
                "Roles count": roles_count,
                "Channels count (+ categories channels)": channels_count,
                "Categories count (+ text channels)": categories_count,
                "Guilds count": guilds_count
            }
            stats = [f"{key}: {value}" for key, value in stats.items()]
            message = "--- Config Stats for Seen ---\n\n"
            message += "\n".join(stats)
            message = box(message)
        await ctx.send(message)

    @commands.is_owner()
    @seen.command()
    async def listener(self, ctx: commands.Context, state: bool, types: commands.Greedy[typing.Literal["message", "message_edit", "reaction_add", "reaction_remove"]]):
        """Enable or disable a listener."""
        config = await self.config.listeners.all()
        for type in types:
            config[type] = state
        await self.config.listeners.set(config)
        await ctx.tick()

    @seen.command()
    async def ignoreme(self, ctx: commands.Context):
        """Asking Seen to ignore your actions."""
        user = ctx.author
        ignored_users = await self.config.ignored_users()
        if user.id not in ignored_users:
            ignored_users.append(user.id)
            await self.red_delete_data_for_user(requester="user", user_id=user.id)
        else:
            ignored_users.remove(user.id)
        await self.config.ignored_users.set(ignored_users)
        await ctx.tick()

    @commands.is_owner()
    @commands.bot_has_permissions(embed_links=True)
    @seen.command(hidden=True)
    async def getloopstatus(self, ctx: commands.Context):
        """Get an embed for check loop status."""
        for loop in self.cogsutils.loops.values():
            await ctx.send(embed=loop.get_debug_embed())

    @commands.is_owner()
    @seen.command(hidden=True)
    async def purge(self, ctx: commands.Context, type: commands.Literal["all", "user", "member", "role", "channel", "guild"]):
        """Purge Config for a specified type or all."""
        if type == "all":
            await self.config.clear_all_users()
            await self.config.clear_all_members()
            await self.config.clear_all_roles()
            await self.config.clear_all_channels()
            await self.config.clear_all_guilds()
        else:
            if type == "user":
                await self.config.clear_all_users()
            elif type == "member":
                await self.config.clear_all_members()
            if type == "role":
                await self.config.clear_all_roles()
            if type == "channel":
                await self.config.clear_all_channels()
            if type == "guild":
                await self.config.clear_all_guilds()
        await ctx.tick()
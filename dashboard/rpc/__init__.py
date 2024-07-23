from redbot.core import commands, core_commands, i18n  # isort:skip
from redbot.core.bot import Red  # isort:skip
from redbot.core.i18n import Translator  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import asyncio
import base64
import pathlib
import random
import re
import time

from redbot.core.utils import AsyncIter
from redbot.core.utils.chat_formatting import humanize_list

from .default_cogs import DashboardRPC_DefaultCogs
from .pagination import Pagination
from .third_parties import DashboardRPC_ThirdParties
from .utils import rpc_check
from .webhooks import DashboardRPC_Webhooks

# Credits:
# Thank you to NeuroAssassin for the original code.

_: Translator = Translator("Dashboard", __file__)


class DashboardRPC:
    """RPC server handlers for the dashboard to get special things from the bot."""

    def __init__(self, bot: Red, cog: commands.Cog) -> None:
        self.bot: Red = bot
        self.cog: commands.Cog = cog

        # To make sure that both RPC server and client are on the same "version".
        self.version: int = random.randint(1, 10000)

        # Initialize RPC handlers.
        self.bot.register_rpc_handler(self.check_version)
        self.bot.register_rpc_handler(self.get_data)
        self.bot.register_rpc_handler(self.get_variables)
        self.bot.register_rpc_handler(self.get_bot_variables)
        self.bot.register_rpc_handler(self.get_commands)
        self.bot.register_rpc_handler(self.get_user_guilds)
        self.bot.register_rpc_handler(self.get_guild)
        self.bot.register_rpc_handler(self.leave_guild)
        self.bot.register_rpc_handler(self.set_guild_settings)
        self.bot.register_rpc_handler(self.set_bot_profile)
        self.bot.register_rpc_handler(self.get_dashboard_settings)
        self.bot.register_rpc_handler(self.set_dashboard_settings)
        self.bot.register_rpc_handler(self.get_bot_settings)
        self.bot.register_rpc_handler(self.set_bot_settings)
        self.bot.register_rpc_handler(self.set_custom_pages)

        # Initialize handlers.
        self.handlers: typing.Dict[str, typing.Any] = {}
        self.handlers["default_cogs"]: DashboardRPC_DefaultCogs = DashboardRPC_DefaultCogs(
            self.cog
        )
        self.handlers["webhooks"]: DashboardRPC_Webhooks = DashboardRPC_Webhooks(self.cog)
        self.third_parties_handler: DashboardRPC_ThirdParties = DashboardRPC_ThirdParties(self.cog)
        self.handlers["third_parties"]: DashboardRPC_ThirdParties = self.third_parties_handler

        # Caches: you can thank Trusty for the cogs infos.
        self.invite_url: str = None
        self.owner: str = None
        self.cogs_infos_cache: typing.Dict[str, typing.Dict[str, str]] = {}
        self.guilds_cache: typing.Dict[
            int,
            typing.Dict[
                typing.Literal["guilds", "time"], typing.Union[typing.List[typing.Dict], int]
            ],
        ] = {}

    def unload(self) -> None:
        if hasattr(self.bot, "dashboard_url"):
            delattr(self.bot, "dashboard_url")
        self.bot.unregister_rpc_handler(self.check_version)
        self.bot.unregister_rpc_handler(self.get_data)
        self.bot.unregister_rpc_handler(self.get_variables)
        self.bot.unregister_rpc_handler(self.get_bot_variables)
        self.bot.unregister_rpc_handler(self.get_commands)
        self.bot.unregister_rpc_handler(self.get_user_guilds)
        self.bot.unregister_rpc_handler(self.get_guild)
        self.bot.unregister_rpc_handler(self.leave_guild)
        self.bot.unregister_rpc_handler(self.set_guild_settings)
        self.bot.unregister_rpc_handler(self.set_bot_profile)
        self.bot.unregister_rpc_handler(self.get_dashboard_settings)
        self.bot.unregister_rpc_handler(self.set_dashboard_settings)
        self.bot.unregister_rpc_handler(self.get_bot_settings)
        self.bot.unregister_rpc_handler(self.set_bot_settings)
        self.bot.unregister_rpc_handler(self.set_custom_pages)
        for handler in self.handlers.values():
            handler.unload()

    @rpc_check()
    async def check_version(self) -> typing.Dict[str, int]:
        return {"version": self.bot.get_cog("Dashboard").rpc.version}

    @rpc_check()
    async def get_data(self) -> typing.Dict[str, typing.Any]:
        data = await self.cog.config.webserver()
        if data["ui"]["meta"]["title"] is None:
            data["ui"]["meta"]["title"] = _("{name} Dashboard").format(name=self.bot.user.name)
        else:
            data["ui"]["meta"]["title"] = data["ui"]["meta"]["title"].replace(
                "{name}", self.bot.user.name
            )
        if data["ui"]["meta"]["icon"] is None:
            data["ui"]["meta"]["icon"] = self.bot.user.display_avatar.url
        if data["ui"]["meta"]["description"] is None:
            data["ui"]["meta"]["description"] = _(
                "Hello, welcome to the **Red-DiscordBot Dashboard** for {name}! "
                "{name} is based off the popular bot **Red-DiscordBot**, an open "
                "source, multifunctional bot. It has *tons of features* including moderation, "
                "audio, economy, fun and more! Here, you can control and interact with "
                "{name}'s settings. **So what are you waiting for? Invite it now!**"
            ).format(name=self.bot.user.name)
        else:
            data["ui"]["meta"]["description"] = data["ui"]["meta"]["description"].replace(
                "{name}", self.bot.user.name
            )
        if data["ui"]["meta"]["website_description"] is None:
            data["ui"]["meta"]["website_description"] = _(
                "Interactive Dashboard to control and interact with {name}."
            ).format(name=self.bot.user.name)
        # if data["ui"]["meta"]["support_server"] is None:
        #     data["ui"]["meta"]["support_server"] = "https://discord.gg/red"
        return data

    @rpc_check()
    async def get_variables(
        self,
        only_bot_variables: bool = False,
        host_port: typing.Optional[typing.Tuple[str, int]] = None,
    ) -> typing.Dict[str, typing.Any]:
        variables = await self.get_bot_variables()
        variables.update(third_parties=await self.third_parties_handler.get_third_parties())
        variables.update(commands={} if only_bot_variables else await self.get_commands())
        if host_port is not None:
            redirect_uri = await self.cog.config.webserver.core.redirect_uri()
            host, port = host_port
            dashboard_url = (
                redirect_uri[:-9]
                if redirect_uri is not None
                else (
                    f"http://127.0.0.1:{port}"
                    if host in ("0.0.0.0", "127.0.0.1")
                    else f"http://{host}"
                )
            )
            is_private = redirect_uri is None and host in ("0.0.0.0", "127.0.0.1")
            setattr(self.bot, "dashboard_url", (dashboard_url, not is_private))
        return variables

    @rpc_check()
    async def get_bot_variables(self) -> typing.Dict[str, typing.Any]:
        bot_info = await self.bot._config.custom_info()
        prefixes = [
            p for p in await self.bot.get_valid_prefixes() if not re.match(r"<@!?([0-9]+)>", p)
        ]

        guilds_count = len(self.bot.guilds)
        users_count = len(self.bot.users)
        text_channels_count = 0
        voice_channels_count = 0
        categories_count = 0
        for guild in self.bot.guilds:
            text_channels_count += len(guild.text_channels)
            voice_channels_count += len(guild.voice_channels)
            categories_count += len(guild.categories)

        if self.invite_url is None:
            self.invite_url: str = await self.bot.get_invite_url()

        if self.owner is None:
            app_info = await self.bot.application_info()
            self.owner: str = (
                str(app_info.team.name) if app_info.team else app_info.owner.display_name
            )

        return {
            "bot": {
                "name": self.bot.user.name,
                "id": self.bot.user.id,
                "application_id": self.bot.application_id,
                "info": bot_info,
                "profile_description": (await self.bot.application_info()).description,
                "prefixes": prefixes,
                "owner_ids": list(self.bot.owner_ids),
                "owner": self.owner,
                "avatar": str(self.bot.user.display_avatar.url).split("?")[0],
                "default_avatar": str(self.bot.user.default_avatar.url).split("?")[0],
                "is_verified": self.bot.user.public_flags.verified_bot,
                "invite_url": self.invite_url,
                "invite_public": await self.bot._config.invite_public(),
                "blacklisted_users": list(await self.bot.get_blacklist()),
            },
            "stats": {
                "guilds": guilds_count,
                "text": text_channels_count,
                "voice": voice_channels_count,
                "categories": categories_count,
                "users": users_count,
                "uptime": int(self.bot.uptime.timestamp()),
            },
            "constants": {
                "MIN_PREFIX_LENGTH": getattr(
                    core_commands, "MINIMUM_PREFIX_LENGTH", 1
                ),  # Added by #6013 in Red 3.5.6.
                "MAX_PREFIX_LENGTH": core_commands.MAX_PREFIX_LENGTH,
                "MAX_DISCORD_PERMISSIONS_VALUE": discord.Permissions.all().value,
            },
        }

    async def build_cmd_list(
        self,
        commands_list: typing.List[commands.Command],
        details: bool = True,
        is_owner: bool = False,
    ) -> typing.List[typing.Dict[str, typing.Union[str, typing.List]]]:
        final = []
        async for command in AsyncIter(sorted(commands_list, key=lambda c: c.name)):
            if details:
                if command.hidden:
                    continue
                is_owner = (
                    is_owner
                    or command.requires.privilege_level == commands.PrivilegeLevel.BOT_OWNER
                )
                try:
                    details = {
                        "name": command.qualified_name,
                        "signature": command.signature,
                        "short_description": command.short_doc.strip() or "",
                        "description": command.help.strip() or "",
                        "aliases": list(command.aliases),
                        # "is_owner": is_owner,
                        "privilege_level": command.requires.privilege_level.name
                        if command.requires.privilege_level is not None
                        else None,
                        "user_permissions": "\n".join(
                            [
                                permission.replace("_", " ").capitalize()
                                for permission, value in dict(command.requires.user_perms).items()
                                if value
                            ]
                        )
                        if command.requires.user_perms is not None
                        else None,
                        "user_permissions": "\n".join(
                            [
                                permission.replace("_", " ").capitalize()
                                for permission, value in dict(command.requires.user_perms).items()
                                if value
                            ]
                        )
                        if command.requires.user_perms is not None
                        else None,
                        "subs": [],
                    }
                except ValueError:
                    continue
                if isinstance(command, commands.Group):
                    details["subs"] = await self.build_cmd_list(
                        command.commands, is_owner=is_owner
                    )
                final.append(details)
            else:
                if (
                    command.hidden
                    or command.requires.privilege_level == commands.PrivilegeLevel.BOT_OWNER
                ):
                    continue
                final.append(command.qualified_name)
                if isinstance(command, commands.Group):
                    final += await self.build_cmd_list(command.commands, details=False)
        return final

    @rpc_check()
    async def get_commands(
        self,
    ) -> typing.Dict[
        str,
        typing.Dict[
            str, typing.Union[str, typing.List[typing.Dict[str, typing.Union[str, typing.List]]]]
        ],
    ]:
        returning = {}
        downloader_cog = self.bot.get_cog("Downloader")
        installed_cogs = (
            await downloader_cog.installed_cogs() if downloader_cog is not None else []
        )
        for cog in self.bot.cogs.copy().values():
            name = cog.qualified_name
            stripped = [c for c in cog.__cog_commands__ if c.parent is None]
            cmds = await self.build_cmd_list(stripped)
            if not cmds:
                continue

            author = "Unknown"
            repo = "Unknown"
            # Taken from Trusty's downloader fuckery (https://gist.github.com/TrustyJAID/784c8c32dd45b1cc8155ed42c0c56591).
            if name in self.cogs_infos_cache:
                author = self.cogs_infos_cache[name]["author"]
                repo = self.cogs_infos_cache[name]["repo"]
            elif downloader_cog is not None:
                module = cog.__module__.split(".")[0]  # downloader_cog.cog_name_from_instance(cog)
                cog_info = next(
                    (
                        installed_cog
                        for installed_cog in installed_cogs
                        if installed_cog.name == module
                    ),
                    None,
                )
                if cog_info is not None:
                    author = humanize_list(cog_info.author) if cog_info.author else "Unknown"
                    try:
                        repo = cog_info.repo.clean_url or "Unknown"
                    except AttributeError:
                        repo = "Unknown (Removed from Downloader)"
                elif cog.__module__.startswith("redbot."):
                    author = "Cog Creators"
                    repo = "https://github.com/Cog-Creators/Red-DiscordBot"
                elif (
                    pathlib.Path(__import__(cog.__module__).__path__[0]).parent.name
                    == "AAA3A-cogs"
                ):  # Handle my repo's clones... :P
                    author = "AAA3A"
                    repo = "https://github.com/AAA3A-AAA3A/AAA3A-cogs"
            author = getattr(cog, "__authors__", []) or getattr(cog, "__author__", []) or author
            if isinstance(author, (typing.List, typing.Tuple)):
                author = humanize_list(author)
            self.cogs_infos_cache[name] = {"author": author, "repo": repo}
            returning[name] = {
                "name": name,
                "description": (cog.__doc__ or "").strip(),
                "author": author or "",
                "repo": repo,
                "commands": cmds,
            }
        return {name: returning[name] for name in sorted(returning.keys())}

    async def notify_owners_of_blacklist(self, ip: str):
        async with self.cog.config.webserver.core.blacklisted_ips() as blacklisted_ips:
            blacklisted_ips.append(ip)
        await self.bot.send_to_owners(
            f"[Dashboard] Detected suspicious activity from IP `{ip}`. They have been blacklisted."
        )

    @rpc_check()
    async def get_user_guilds(
        self,
        user_id: int,
        per_page: typing.Optional[typing.Union[int, str]] = None,
        page: typing.Optional[typing.Union[int, str]] = None,
        query: typing.Optional[str] = None,
        filter: typing.Optional[typing.Literal["owner", "admin", "mod"]] = None,
    ) -> typing.Dict[str, typing.Any]:
        user = self.bot.get_user(user_id)
        if user is None:
            # Bot doesn't even find user using bot.get_user, might as well spare all the data processing and return.
            return {"guilds": [], "total": 0, "per_page": 10, "pages": 0, "page": 1}
        is_owner = user.id in self.bot.owner_ids
        guilds = []
        if filter is None and user_id in self.guilds_cache:
            cached = self.guilds_cache[user_id]
            if (cached["time"] + 60) > time.time():
                guilds = cached["guilds"]
            else:
                del self.guilds_cache[user_id]

        if not guilds:
            # This could take a while.
            async for guild in AsyncIter(
                sorted(
                    self.bot.guilds,
                    key=lambda guild: (guild.owner.id != user_id, guild.name.lower()),
                ),
                steps=1300,
            ):
                guild_infos = {
                    "id": guild.id,
                    "name": guild.name,
                    "owner": guild.owner.display_name,
                    "owner_id": guild.owner.id,
                    "icon_url": guild.icon.url.split("?")[0]
                    if guild.icon is not None
                    else "https://cdn.discordapp.com/embed/avatars/1.png",
                    "icon_animated": guild.icon.is_animated() if guild.icon is not None else False,
                    "user_role": None,
                }
                if filter is None and is_owner:
                    guilds.append(guild_infos)
                    continue
                member = guild.get_member(user_id)
                if member is None:
                    continue
                if (filter is None or filter == "owner") and member == guild.owner:
                    guild_infos["user_role"] = "OWNER"
                    guilds.append(guild_infos)
                elif (filter is None or filter == "admin") and (
                    await self.bot.is_admin(member) or member.guild_permissions.manage_guild
                ):
                    guild_infos["user_role"] = "ADMIN"
                    guilds.append(guild_infos)
                elif (filter is None or filter == "mod") and await self.bot.is_mod(member):
                    guild_infos["user_role"] = "MOD"
                    guilds.append(guild_infos)
            if filter is None:
                self.guilds_cache[user_id] = {"guilds": guilds, "time": time.time()}

        if query is not None:
            query = query.strip().lower()
            guilds = [
                guild
                for guild in guilds
                if query in guild["name"].lower() or query == str(guild["id"])
            ]
        return Pagination.from_list(guilds, per_page=per_page, page=page).to_dict()

    @rpc_check()
    async def get_guild(self, user_id: int, guild_id: int, for_third_parties: bool = False):
        guild = self.bot.get_guild(guild_id)
        if guild is None:
            return {"status": 1}
        member = guild.get_member(user_id)
        is_owner = user_id in self.bot.owner_ids
        if not is_owner and (
            member is None
            or (
                not await self.bot.is_mod(member)
                and not member.guild_permissions.manage_guild
                and not for_third_parties
            )
        ):
            return {"status": 1}

        # joined_at = member.joined_at if member is not None else None
        if is_owner:
            humanized = "Everything (Bot Owner)"
        elif member == guild.owner:
            humanized = "Everything (Guild Owner)"
        else:
            humanized = "Admin" if await self.bot.is_admin(member) else "Mod"

        status_stats = {"online": 0, "dnd": 0, "idle": 0, "offline": 0}
        for m in guild.members:
            status_stats[m.raw_status if m.raw_status in status_stats else "offline"] += 1

        if guild.verification_level is discord.VerificationLevel.none:
            verification_level = "None"
        elif guild.verification_level is discord.VerificationLevel.low:
            verification_level = "1 - Low"
        elif guild.verification_level is discord.VerificationLevel.medium:
            verification_level = "2 - Medium"
        elif guild.verification_level is discord.VerificationLevel.high:
            verification_level = "3 - High"
        elif guild.verification_level is discord.VerificationLevel.highest:
            verification_level = "4 - Extreme"
        else:
            verification_level = "Unknown"

        all_roles = list(reversed([{"id": role.id, "name": role.name} for role in guild.roles]))
        config_group = self.bot._config.guild(guild)
        admin_roles = [
            {"id": role.id, "name": role.name}
            for role_id in await config_group.admin_role()
            if (role := guild.get_role(role_id)) is not None
        ]
        mod_roles = [
            {"id": role.id, "name": role.name}
            for role_id in await config_group.mod_role()
            if (role := guild.get_role(role_id)) is not None
        ]

        return {
            "status": 0,
            "id": guild.id,
            "name": guild.name,
            "owner": guild.owner.display_name,
            "owner_id": guild.owner.id,
            "icon_url": guild.icon.url
            if guild.icon is not None
            else "https://cdn.discordapp.com/embed/avatars/1.png",
            "icon_animated": guild.icon.is_animated() if guild.icon is not None else False,
            "verification_level": verification_level,
            "created_at": guild.created_at.timestamp(),
            "joined_at": guild.me.joined_at.timestamp(),
            # Guild stats.
            "members_number": len(guild.members),
            "online_number": status_stats["online"],
            "dnd_number": status_stats["dnd"],
            "idle_number": status_stats["idle"],
            "offline_number": status_stats["offline"],
            "bots_number": len([user for user in guild.members if user.bot]),
            "humans_number": len([user for user in guild.members if not user.bot]),
            "channels_number": len(guild.channels),
            "text_channels_number": len(guild.text_channels),
            "voice_channels_number": len(guild.voice_channels),
            "roles_number": len(guild.roles),
            "roles": all_roles,
            # Bot wide settings.
            "prefixes": sorted(await self.bot.get_valid_prefixes(guild)),
            "settings": {
                "edit_permission": user_id in self.bot.owner_ids
                or await self.bot.is_admin(member)
                or member.guild_permissions.manage_guild,
                # Base.
                "bot_nickname": guild.me.nick,
                "prefixes": await config_group.prefix(),
                "admin_roles": admin_roles,
                "mod_roles": mod_roles,
                "whitelist": await config_group.whitelist(),
                "blacklist": await config_group.blacklist(),
                # Commands.
                "ignored": await self.bot._ignored_cache.get_ignored_guild(guild),
                "disabled_commands": await config_group.disabled_commands(),
                # Look.
                "embeds": await config_group.embeds(),
                "use_bot_color": await config_group.use_bot_color(),
                "fuzzy": await config_group.fuzzy(),
                "delete_delay": await config_group.delete_delay(),
                # Locale.
                "locale": await i18n.get_locale_from_guild(self.bot, guild),
                "regional_format": await i18n.get_regional_format_from_guild(self.bot, guild),
            },
            "perms": humanize_list(humanized),
        }

    @rpc_check()
    async def leave_guild(self, user_id: int, guild_id: int):
        guild = self.bot.get_guild(guild_id)
        if guild is None:
            return {"status": 1}
        if user_id not in self.bot.owner_ids:
            return {"status": 1}
        await guild.leave()
        return {"status": 0}

    @rpc_check()
    async def set_guild_settings(
        self, user_id: int, guild_id: int, settings: typing.Dict[str, typing.Any]
    ):
        guild = self.bot.get_guild(guild_id)
        if guild is None:
            return {"status": 1}
        member = guild.get_member(user_id)
        if user_id not in self.bot.owner_ids and (
            member is None
            or not (await self.bot.is_admin(member) or member.guild_permissions.manage_guild)
        ):
            return {"status": 1}
        change_nickname_error = False
        if settings["bot_nickname"] != guild.me.nick:
            try:
                await guild.me.edit(nick=settings["bot_nickname"])
            except discord.HTTPException as e:
                change_nickname_error = str(e)
        await self.bot.set_prefixes(settings["prefixes"], guild=guild)
        config_group = self.bot._config.guild(guild)
        await config_group.admin_role.set([int(role_id) for role_id in settings["admin_roles"]])
        await config_group.mod_role.set([int(role_id) for role_id in settings["mod_roles"]])
        await config_group.ignore.set(settings["ignored"])
        already_disabled_commands = await config_group.disabled_commands()
        for command_name in settings["disabled_commands"].copy():
            if command_name in already_disabled_commands:
                continue
            if (
                (command := self.bot.get_command(command_name)) is None
                or isinstance(command, commands.commands._RuleDropper)
                or (
                    command.requires.privilege_level is not None
                    and command.requires.privilege_level
                    > await commands.PrivilegeLevel.from_ctx(
                        type("Context", (), {"bot": self.bot, "author": member, "guild": guild})
                    )
                )
            ):
                settings["disabled_commands"].remove(command_name)
            else:
                command.disable_in(guild)
        for command_name in already_disabled_commands:
            if command_name not in settings["disabled_commands"]:
                if (command := self.bot.get_command(command_name)) is not None and (
                    command.requires.privilege_level is None
                    or not command.requires.privilege_level
                    > await commands.PrivilegeLevel.from_ctx(
                        type("Context", (), {"bot": self.bot, "author": member, "guild": guild})
                    )
                ):
                    command.enable_in(guild)
        await config_group.disabled_commands.set(settings["disabled_commands"])
        await config_group.embeds.set(settings["embeds"])
        await config_group.use_bot_color.set(settings["use_bot_color"])
        await config_group.fuzzy.set(settings["fuzzy"])
        await config_group.delete_delay.set(settings["delete_delay"])
        if settings["locale"] is None:
            settings["locale"] = await self.bot._config.locale()
        i18n.set_contextual_locale(settings["locale"])
        await self.bot._i18n_cache.set_locale(guild, settings["locale"])
        i18n.set_contextual_regional_format(settings["regional_format"])
        await self.bot._i18n_cache.set_regional_format(guild, settings["regional_format"])
        return {"status": 0, "change_nickname_error": change_nickname_error}

    @rpc_check()
    async def set_bot_profile(self, user_id: int, settings: typing.Dict[str, typing.Any]):
        if user_id not in self.bot.owner_ids:
            return {"status": 1}
        try:
            if settings["avatar"] == "default":
                await self.bot.user.edit(avatar=None)
            elif settings["avatar"] != "keep":
                avatar = base64.b64decode(settings["avatar"])
                await self.bot.user.edit(avatar=avatar)
            if settings["username"] != self.bot.user.name:
                try:
                    await asyncio.wait_for(
                        self.bot.get_cog("Core")._name(name=settings["username"]), timeout=30
                    )
                except TimeoutError:
                    return {
                        "status": 1,
                        "error": "Changing the username timed out. Remember that you can only change it twice per hour.",
                    }
            if settings["description"] is not None:
                from discord.http import Route

                await self.bot.http.request(
                    Route("PATCH", "/applications/@me"),
                    json={"description": settings["description"]},
                )
        except discord.HTTPException as e:
            return {"status": 1, "error": str(e)}

    @rpc_check()
    async def get_dashboard_settings(self, user_id: int):
        if user_id not in self.bot.owner_ids:
            return {"status": 1}
        config_group = self.cog.config.webserver.ui.meta
        return {
            "status": 0,
            "title": await config_group.title(),
            "icon": await config_group.icon(),
            "website_description": await config_group.website_description(),
            "description": await config_group.description(),
            "support_server": await config_group.support_server(),
            "default_color": await config_group.default_color(),
            "default_background_theme": await config_group.default_background_theme(),
            "default_sidenav_theme": await config_group.default_sidenav_theme(),
            "disabled_third_parties": await self.cog.config.webserver.disabled_third_parties(),
        }

    @rpc_check()
    async def set_dashboard_settings(self, user_id: int, settings: typing.Dict[str, typing.Any]):
        if user_id not in self.bot.owner_ids:
            return {"status": 1}
        config_group = self.cog.config.webserver.ui.meta
        await config_group.title.set(settings["title"])
        await config_group.icon.set(settings["icon"])
        await config_group.website_description.set(settings["website_description"])
        await config_group.description.set(settings["description"])
        await config_group.support_server.set(settings["support_server"])
        await config_group.default_color.set(settings["default_color"])
        await config_group.default_background_theme.set(settings["default_background_theme"])
        await config_group.default_sidenav_theme.set(settings["default_sidenav_theme"])
        await self.cog.config.webserver.disabled_third_parties.set(
            settings["disabled_third_parties"]
        )
        return {"status": 0}

    @rpc_check()
    async def get_bot_settings(self, user_id: int):
        if user_id not in self.bot.owner_ids:
            return {"status": 1}
        config_group = self.bot._config
        color = discord.Color(await config_group.color())
        return {
            "status": 0,
            # Base.
            "prefixes": await config_group.prefix(),
            "invoke_error_msg": await config_group.invoke_error_msg(),
            "whitelist": await config_group.whitelist(),
            "blacklist": await config_group.blacklist(),
            # Commands.
            "disabled_commands": await config_group.disabled_commands(),
            "disabled_command_msg": await config_group.disabled_command_msg(),
            # Descriptions.
            "description": await config_group.description(),
            "custom_info": await config_group.custom_info(),
            # Look.
            "embeds": await config_group.embeds(),
            "color": f"#{color.value:06X}",
            "fuzzy": await config_group.fuzzy(),
            "use_buttons": await config_group.use_buttons(),
            # Invite.
            "invite_public": await config_group.invite_public(),
            "invite_commands_scope": await config_group.invite_commands_scope(),
            "invite_perms": await config_group.invite_perm(),
            # Locale.
            "locale": await config_group.locale(),
            "regional_format": await config_group.regional_format(),
        }

    @rpc_check()
    async def set_bot_settings(self, user_id: int, settings: typing.Dict[str, typing.Any]):
        if user_id not in self.bot.owner_ids:
            return {"status": 1}
        config_group = self.bot._config
        await config_group.prefix.set(settings["prefixes"])
        await config_group.invoke_error_msg.set(settings["invoke_error_msg"])
        already_disabled_commands = await config_group.disabled_commands()
        for command_name in settings["disabled_commands"].copy():
            if command_name in already_disabled_commands:
                continue
            if (command := self.bot.get_command(command_name)) is None or isinstance(
                command, commands.commands._RuleDropper
            ):
                settings["disabled_commands"].remove(command_name)
            else:
                command.enabled = False
        for command_name in already_disabled_commands:
            if command_name not in settings["disabled_commands"]:
                if (command := self.bot.get_command(command_name)) is not None:
                    command.enabled = True
        await config_group.disabled_commands.set(settings["disabled_commands"])
        if settings["disabled_command_msg"] is not None:
            await config_group.disabled_command_msg.set(settings["disabled_command_msg"])
        else:
            await config_group.disabled_command_msg.clear()
        if settings["description"] is not None:
            await config_group.description.set(settings["description"])
            self.bot.description = settings["description"]
        else:
            await config_group.description.clear()
            self.bot.description = "Red V3"
        if settings["custom_info"] is not None:
            await config_group.custom_info.set(settings["custom_info"])
        else:
            await config_group.custom_info.clear()
        await config_group.embeds.set(settings["embeds"])
        if settings["color"] is not None:
            hex_color = settings["color"].lstrip("#")
            r = int(hex_color[:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            color = discord.Color.from_rgb(r, g, b)
            await config_group.color.set(color.value)
            self.bot._color = color
        else:
            await config_group.color.clear()
            self.bot._color = discord.Color.red()
        await config_group.fuzzy.set(settings["fuzzy"])
        await config_group.use_buttons.set(settings["use_buttons"])
        await config_group.invite_public.set(settings["invite_public"])
        await config_group.invite_commands_scope.set(settings["invite_commands_scope"])
        await config_group.invite_perm.set(settings["invite_perms"])
        if settings["locale"] is None:
            settings["locale"] = await self.bot._config.locale()
        i18n.set_contextual_locale(settings["locale"])
        await self.bot._i18n_cache.set_locale(None, settings["locale"])
        i18n.set_contextual_regional_format(settings["regional_format"])
        await self.bot._i18n_cache.set_regional_format(None, settings["regional_format"])
        return {"status": 0}

    @rpc_check()
    async def set_custom_pages(
        self, user_id: int, custom_pages: typing.List[typing.Dict[str, str]]
    ):
        if user_id not in self.bot.owner_ids:
            return {"status": 1}
        await self.cog.config.webserver.custom_pages.set(custom_pages)
        return {"status": 0}

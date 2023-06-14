from AAA3A_utils import Cog, CogsUtils, Settings  # isort:skip
from redbot.core import commands, Config  # isort:skip
from redbot.core.bot import Red  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import io
from copy import deepcopy

# Credits:
# General repo credits.
# The idea for this cog came from @OnlyEli on Red cogs support (https://discord.com/channels/240154543684321280/430582201113903114/944075297127538730)!

_ = Translator("MemberPrefix", __file__)


@cog_i18n(_)
class MemberPrefix(Cog):
    """A cog to allow a member to choose custom prefixes, just for them!"""

    def __init__(self, bot: Red) -> None:
        self.bot: Red = bot

        self.config: Config = Config.get_conf(
            self,
            identifier=205192943327321000143939875896557571750,  # 647053803629
            force_registration=True,
        )
        self.memberprefix_global: typing.Dict[str, bool] = {
            "use_normal_prefixes": False,
        }
        self.memberprefix_member: typing.Dict[str, typing.List[str]] = {
            "custom_prefixes": [],
        }
        self.config.register_global(**self.memberprefix_global)
        self.config.register_member(**self.memberprefix_member)

        self.original_prefix_manager = self.bot.command_prefix

        self.cogsutils: CogsUtils = CogsUtils(cog=self)

        _settings: typing.Dict[
            str, typing.Dict[str, typing.Union[typing.List[str], bool, str]]
        ] = {
            "use_normal_prefixes": {
                "path": ["use_normal_prefixes"],
                "converter": bool,
                "description": "Use server/global prefixes in addition to those customized for each member.",
            },
        }
        self.settings: Settings = Settings(
            bot=self.bot,
            cog=self,
            config=self.config,
            group=self.config.GLOBAL,
            settings=_settings,
            global_path=[],
            use_profiles_system=False,
            can_edit=True,
            commands_group=self.configuration,
        )

    async def cog_load(self) -> None:
        await self.settings.add_commands()
        self.bot.command_prefix = self.prefix_manager

    async def cog_unload(self) -> None:
        if self.original_prefix_manager is not None:
            self.bot.command_prefix = self.original_prefix_manager
        await super().cog_unload()

    async def red_delete_data_for_user(
        self,
        *,
        requester: typing.Literal["discord_deleted_user", "owner", "user", "user_strict"],
        user_id: int,
    ) -> None:
        """Delete all user chosen prefixes in all Config guilds."""
        if requester not in ["discord_deleted_user", "owner", "user", "user_strict"]:
            return
        member_group = self.config._get_base_group(self.config.MEMBER)
        async with member_group.all() as members_data:
            _members_data = deepcopy(members_data)
            for guild in _members_data:
                if str(user_id) in _members_data[guild]:
                    del members_data[guild][str(user_id)]
                if members_data[guild] == {}:
                    del members_data[guild]

    async def red_get_data_for_user(self, *, user_id: int) -> typing.Dict[str, io.BytesIO]:
        """Get all data about the user."""
        data = {
            Config.GLOBAL: {},
            Config.USER: {},
            Config.MEMBER: {},
            Config.ROLE: {},
            Config.CHANNEL: {},
            Config.GUILD: {},
        }

        member_group = self.config._get_base_group(self.config.MEMBER)
        async with member_group.all() as members_data:
            for guild in members_data:
                if str(user_id) in members_data[guild]:
                    data[Config.MEMBER][guild] = {str(user_id): members_data[guild][str(user_id)]}

        _data = deepcopy(data)
        for key, value in _data.items():
            if not value:
                del data[key]
        if not data:
            return {}
        file = io.BytesIO(str(data).encode(encoding="utf-8"))
        return {f"{self.qualified_name}.json": file}

    async def prefix_manager(self, bot: Red, message: discord.Message) -> typing.List[str]:
        if message.guild is None or await bot.cog_disabled_in_guild(cog=self, guild=message.guild) or not await bot.allowed_by_whitelist_blacklist(who=message.author):
            prefixes = await bot._prefix_cache.get_prefixes(message.guild)
            if bot._cli_flags.mentionable:
                return discord.ext.commands.when_mentioned_or(*prefixes)(bot, message)
            return prefixes
        custom_prefixes = await self.config.member_from_ids(message.guild.id, message.author.id).custom_prefixes()
        if custom_prefixes == []:
            prefixes = await bot._prefix_cache.get_prefixes(message.guild)
            if bot._cli_flags.mentionable:
                return discord.ext.commands.when_mentioned_or(*prefixes)(bot, message)
        else:
            if await self.config.use_normal_prefixes():
                prefixes = await bot._prefix_cache.get_prefixes(message.guild)
            prefixes.extend(custom_prefixes)
            prefixes = sorted(prefixes, reverse=True)
            return discord.ext.commands.when_mentioned_or(*prefixes)(bot, message)
        return prefixes

    class StrConverter(commands.Converter):
        async def convert(self, ctx: commands.Context, argument: str) -> str:
            return argument

    @commands.guild_only()
    @commands.hybrid_command(aliases=["memberprefixes"], invoke_without_command=True)
    async def memberprefix(
        self, ctx: commands.Context, prefixes: commands.Greedy[StrConverter]
    ) -> None:
        """Sets [botname]'s prefix(es) for you only.
        Warning: This is not additive. It will replace all current prefixes.
        The real prefixes will no longer work for you.

        **Examples:**
            - `[p]memberprefix !`
            - `[p]memberprefix "! "` - Quotes are needed to use spaces in prefixes.
            - `[p]memberprefix ! ? .` - Sets multiple prefixes.
        **Arguments:**
            - `<prefixes...>` - The prefixes the bot will respond for you only.
        """
        if len(prefixes) == 0:
            await self.config.member(ctx.author).custom_prefixes.clear()
            await ctx.send(_("You now use this server or global prefixes."))
            return
        if any(len(x) > 25 for x in prefixes):
            raise commands.UserFeedbackCheckFailure(
                _(
                    "A prefix is above the maximal length (25 characters).\nThis is possible for global or per-server prefixes, but not for per-member prefixes."
                )
            )
        if any(prefix.startswith("/") for prefix in prefixes):
            raise commands.UserFeedbackCheckFailure(
                _("Prefixes cannot start with `/`, as it conflicts with Discord's slash commands.")
            )
        await self.config.member(ctx.author).custom_prefixes.set(prefixes)
        if len(prefixes) == 1:
            await ctx.send(_("Prefix for you only set."))
        else:
            await ctx.send(_("Prefixes for you only set."))

    @commands.is_owner()
    @commands.guild_only()
    @commands.hybrid_group(name="setmemberprefix")
    async def configuration(self, ctx: commands.Context) -> None:
        """Configure MemberPrefix."""

    @configuration.command()
    async def memberprefixpurge(self, ctx: commands.Context, guild: discord.Guild) -> None:
        """Clear all members prefixes for a specified server."""
        await self.config.clear_all_members(guild=guild)

    @configuration.command()
    async def resetmemberprefix(self, ctx: commands.Context, guild: discord.Guild, user: discord.User) -> None:
        """Clear prefixes for a specified member in a specified server."""
        await self.config.member_from_ids(guild.id, user.id).clear()

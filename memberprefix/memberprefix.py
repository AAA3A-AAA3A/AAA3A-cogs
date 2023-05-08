from AAA3A_utils import Cog, CogsUtils  # isort:skip
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

        self.cache_messages: typing.List[discord.Message] = []

        self.cogsutils: CogsUtils = CogsUtils(cog=self)

    async def cog_load(self) -> None:
        self.bot.before_invoke(self.before_invoke)

    async def cog_unload(self) -> None:
        self.bot.remove_before_invoke_hook(self.before_invoke)
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

    async def before_invoke(self, ctx: commands.Context) -> None:
        if ctx.guild is None:
            return
        if ctx.interaction is not None:
            return
        if await self.config.use_normal_prefixes():
            return
        if not isinstance(ctx.author, discord.Member):
            ctx.author = ctx.guild.get_member(ctx.author.id)
        config = await self.config.member(ctx.author).all()
        if config["custom_prefixes"] == []:
            return
        if ctx.message.id in self.cache_messages:
            self.cache_messages.remove(ctx.message.id)
            return
        raise commands.CheckFailure()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.webhook_id is not None or message.author.bot:
            return
        if message.guild is None:
            return
        if not await self.bot.allowed_by_whitelist_blacklist(message.author):
            return
        if not isinstance(message.author, discord.Member):
            message.author = message.guild.get_member(message.author.id)
        config = await self.config.member(message.author).all()
        if config["custom_prefixes"] == []:
            return
        prefixes = config["custom_prefixes"]
        ctx = await self.get_context_with_custom_prefixes(
            origin=message, prefixes=prefixes, cls=commands.context.Context
        )
        if ctx is None:
            ctx = await self.get_context_with_custom_prefixes(
                origin=message,
                prefixes=[f"<@{self.bot.user.id}> ", f"<@!{self.bot.user.id}> "],
                cls=commands.context.Context,
            )
            if ctx is not None and ctx.valid and ctx.command == self.memberprefix:
                self.cache_messages.append(ctx.message.id)
                await self.bot.invoke(ctx)
            return
        if ctx.valid:
            self.cache_messages.append(ctx.message.id)
            await self.bot.invoke(ctx)

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
            raise commands.UserFeedbackCheckFailure(
                _("You now use this server or global prefixes.")
            )
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

    async def get_context_with_custom_prefixes(
        self, origin: discord.Message, prefixes: typing.List, *, cls=commands.context.Context
    ) -> None:
        r"""|coro|

        Returns the invocation context from the message or interaction.

        This is a more low-level counter-part for :meth:`.process_commands`
        to allow users more fine grained control over the processing.

        The returned context is not guaranteed to be a valid invocation
        context, :attr:`.Context.valid` must be checked to make sure it is.
        If the context is not valid then it is not a valid candidate to be
        invoked under :meth:`~.Bot.invoke`.

        .. note::

            In order for the custom context to be used inside an interaction-based
            context (such as :class:`HybridCommand`) then this method must be
            overridden to return that class.

        .. versionchanged:: 2.0

            ``message`` parameter is now positional-only and renamed to ``origin``.
        Parameters
        -----------
        origin: Union[:class:`discord.Message`, :class:`discord.Interaction`]
            The message or interaction to get the invocation context from.
        cls
            The factory class that will be used to create the context.
            By default, this is :class:`.Context`. Should a custom
            class be provided, it must be similar enough to :class:`.Context`\'s
            interface.

        Returns
        --------
        :class:`.Context`
            The invocation context. The type of this can change via the
            ``cls`` parameter.
        """
        if isinstance(origin, discord.Interaction):
            return
        view = discord.ext.commands.view.StringView(origin.content)
        ctx = cls(prefix=None, view=view, bot=self.bot, message=origin)
        if origin.author.id == self.bot.user.id:  # type: ignore
            return ctx
        prefix = prefixes
        invoked_prefix = prefix
        if isinstance(prefix, str):
            if not view.skip_string(prefix):
                return ctx
        elif origin.content.startswith(tuple(prefix)):
            invoked_prefix = discord.utils.find(view.skip_string, prefix)
        else:
            return ctx
        if self.bot.strip_after_prefix:
            view.skip_ws()
        invoker = view.get_word()
        ctx.invoked_with = invoker
        ctx.prefix = invoked_prefix
        ctx.command = self.bot.all_commands.get(invoker)
        return ctx

    @commands.guild_only()
    @commands.guildowner_or_permissions(administrator=True)
    @commands.command(hidden=True)
    async def memberprefixpurge(self, ctx: commands.Context) -> None:
        """Clear all members prefixes for this guild."""
        await self.config.clear_all_members(guild=ctx.guild)

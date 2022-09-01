from .AAA3A_utils import CogsUtils  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
from redbot.core.bot import Red  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

from copy import deepcopy

from redbot.core import Config

# Credits:
# The idea for this cog came from @OnlyEli on Red cogs support! (https://discord.com/channels/240154543684321280/430582201113903114/944075297127538730)
# Thanks to @epic guy on Discord for the basic syntax (command groups, commands) and also commands (await ctx.send, await ctx.author.send, await ctx.message.delete())!
# Thanks to the developers of the cogs I added features to as it taught me how to make a cog! (Chessgame by WildStriker, Captcha by Kreusada, Speak by Epic guy and Rommer by Dav)
# Thanks to all the people who helped me with some commands in the #coding channel of the redbot support server!

_ = Translator("MemberPrefix", __file__)

if CogsUtils().is_dpy2:
    from functools import partial
    hybrid_command = partial(commands.hybrid_command, with_app_command=False)
    hybrid_group = partial(commands.hybrid_group, with_app_command=False)
else:
    hybrid_command = commands.command
    hybrid_group = commands.group

@cog_i18n(_)
class MemberPrefix(commands.Cog):
    """A cog to allow a member to choose custom prefixes, just for them!"""

    def __init__(self, bot: Red):
        self.bot: Red = bot

        self.config: Config = Config.get_conf(
            self,
            identifier=647053803629,
            force_registration=True,
        )
        self.memberprefix_member = {
            "custom_prefixes": [],
        }
        self.memberprefix_global = {
            "use_normal_prefixes": False,
        }
        self.config.register_member(**self.memberprefix_member)
        self.config.register_global(**self.memberprefix_global)

        self.cache_messages = []
        self.bot.before_invoke(self.before_invoke)

        self.cogsutils = CogsUtils(cog=self)
        self.cogsutils._setup()

    if CogsUtils().is_dpy2:
        async def cog_unload(self):
            self.bot.remove_before_invoke_hook(self.before_invoke)
            self.cogsutils._end()
    else:
        def cog_unload(self):
            self.bot.remove_before_invoke_hook(self.before_invoke)
            self.cogsutils._end()

    async def red_delete_data_for_user(self, *, requester: typing.Literal["discord_deleted_user", "owner", "user", "user_strict"], user_id: int):
        """Delete all user chosen prefixes in all Config guilds."""
        if requester not in ["discord_deleted_user", "owner", "user", "user_strict"]:
            return
        if requester == "user":
            return
        member_group = self.config._get_base_group(self.config.MEMBER)
        async with member_group.all() as members_data:
            _members_data = deepcopy(members_data)
            for guild in _members_data:
                if str(user_id) in _members_data[guild]:
                    del members_data[guild][str(user_id)]
                if members_data[guild] == {}:
                    del members_data[guild]

    async def before_invoke(self, ctx: commands.Context) -> None:
        if ctx.guild is None:
            return
        if not isinstance(ctx.author, discord.Member):
            ctx.author = ctx.guild.get_member(ctx.author.id)
        config = await self.config.member(ctx.author).all()
        if config["custom_prefixes"] == []:
            return
        if ctx.message.id in self.cache_messages:
            self.cache_messages.remove(ctx.message.id)
            return
        raise discord.ext.commands.CheckFailure()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.guild is None:
            return
        if not isinstance(message.author, discord.Member):
            message.author = message.guild.get_member(message.author.id)
        config = await self.config.member(message.author).all()
        if not config["custom_prefixes"] == []:
            prefixes = config["custom_prefixes"]
            if await self.config.use_normal_prefixes():
                for p in await self.bot.get_valid_prefixes(message.guild):
                    if p not in prefixes:
                        prefixes.append(p)
        else:
            prefixes = await self.bot.get_valid_prefixes(message.guild)
            return
        ctx = await self.get_context_with_custom_prefixes(origin=message, prefixes=prefixes, cls=commands.context.Context)
        if ctx is None:
            return
        if ctx.valid:
            self.cache_messages.append(ctx.message.id)
            await self.bot.invoke(ctx)

    class StrConverter(commands.Converter):

        async def convert(self, ctx: commands.Context, arg: str):
            return arg

    @commands.guild_only()
    @hybrid_command(aliases=["memberprefixes"], invoke_without_command=True)
    async def memberprefix(self, ctx: commands.Context, prefixes: commands.Greedy[StrConverter]):
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
        prefixes = list(prefixes)
        if len(prefixes) == 0:
            await self.config.member(ctx.author).custom_prefixes.clear()
            await ctx.send(_("You now use this server or global prefixes.").format(**locals()))
            return
        if any(len(x) > 25 for x in prefixes):
            await ctx.send(_("A prefix is above the maximal length (25 characters).\nThis is possible for global or per-server prefixes, but not for per-member prefixes.").format(**locals()))
            return
        if any(prefix.startswith("/") for prefix in prefixes):
            await ctx.send(_("Prefixes cannot start with `/`, as it conflicts with Discord's slash commands.").format(**locals()))
            return
        await self.config.member(ctx.author).custom_prefixes.set(prefixes)
        if len(prefixes) == 1:
            await ctx.send(_("Prefix for you only set.").format(**locals()))
        else:
            await ctx.send(_("Prefixes for you only set.").format(**locals()))

    async def get_context_with_custom_prefixes(self, origin: discord.Message, prefixes: typing.List, *, cls=commands.context.Context):
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
        if self.cogsutils.is_dpy2:
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
        else:
            if origin.content.startswith(tuple(prefix)):
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
    async def memberprefixpurge(self, ctx: commands.Context):
        """Clear all members prefixes for this guild."""
        await self.config.clear_all_members(guild=ctx.guild)
        await ctx.tick()
from .AAA3A_utils.cogsutils import CogsUtils  # isort:skip
from redbot.core import commands  # isort:skip
import discord  # isort:skip
import typing  # isort:skip
from redbot.core import Config

# Credits:
# The idea for this cog came from @OnlyEli on Red cogs support! (https://discord.com/channels/240154543684321280/430582201113903114/944075297127538730)
# Thanks to @epic guy on Discord for the basic syntax (command groups, commands) and also commands (await ctx.send, await ctx.author.send, await ctx.message.delete())!
# Thanks to the developers of the cogs I added features to as it taught me how to make a cog! (Chessgame by WildStriker, Captcha by Kreusada, Speak by Epic guy and Rommer by Dav)
# Thanks to all the people who helped me with some commands in the #coding channel of the redbot support server!

def _(untranslated: str):
    return untranslated

class MemberPrefix(commands.Cog):
    """A cog to allow a member to choose custom prefixes, just for them!"""

    def __init__(self, bot):
        self.bot = bot
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

        self.__func_red__ = ["cog_unload"]
        self.cogsutils = CogsUtils(cog=self)
        self.cogsutils._setup()

    def cog_unload(self):
        self.bot.remove_before_invoke_hook(self.before_invoke)
        self.cogsutils._end()

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
        raise discord.ext.commands.CheckFailure

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
        ctx = await self.get_context_with_custom_prefixes(message=message, prefixes=prefixes, cls=commands.context.Context)
        if ctx is None:
            return
        if ctx.valid:
            self.cache_messages.append(ctx.message.id)
            await self.bot.invoke(ctx)

    @commands.guild_only()
    @commands.command(aliases=["memberprefixes"])
    async def memberprefix(self, ctx: commands.Context, *prefixes: str):
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
        if any(len(x) > 10 for x in prefixes):
            await ctx.send(_("A prefix is above the maximal length (10 characters).\nThis is possible for global or per-server prefixes, but not for per-member prefixes.").format(**locals()))
            return
        await self.config.member(ctx.author).custom_prefixes.set(prefixes)
        if len(prefixes) == 0 or 1:
            await ctx.send(_("Prefix for you only set.").format(**locals()))
        else:
            await ctx.send(_("Prefixes for you only set.").format(**locals()))

    async def get_context_with_custom_prefixes(self, message: discord.Message, prefixes: typing.List, *, cls=commands.context.Context):
        r"""|coro|
        Returns the invocation context from the message.
        This is a more low-level counter-part for :meth:`.process_commands`
        to allow users more fine grained control over the processing.
        The returned context is not guaranteed to be a valid invocation
        context, :attr:`.Context.valid` must be checked to make sure it is.
        If the context is not valid then it is not a valid candidate to be
        invoked under :meth:`~.Bot.invoke`.
        Parameters
        -----------
        message: :class:`discord.Message`
            The message to get the invocation context from.
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
            view = discord.ext.commands.view.StringView(message.content)
            ctx = cls(prefix=None, view=view, bot=self.bot, message=message)
            if message.author.id == self.bot.user.id:
                return ctx
            prefix = prefixes
            invoked_prefix = prefix
            if message.content.startswith(tuple(prefix)):
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
        else:
            view = discord.ext.commands.view.StringView(message.content)
            ctx = cls(prefix=None, view=view, bot=self.bot, message=message)
            if self.bot._skip_check(message.author.id, self.bot.user.id):
                return ctx
            prefix = prefixes
            invoked_prefix = prefix
            if message.content.startswith(tuple(prefix)):
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
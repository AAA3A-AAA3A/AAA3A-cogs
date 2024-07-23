from AAA3A_utils import Cog, CogsUtils, Menu  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.bot import Red  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import traceback

from redbot.core.utils.chat_formatting import box, pagify

from .dashboard_integration import DashboardIntegration

# Credits:
# General repo credits.

_: Translator = Translator("AutoTraceback", __file__)

IGNORED_ERRORS = (
    commands.UserInputError,
    commands.DisabledCommand,
    commands.CommandNotFound,
    commands.CheckFailure,
    commands.NoPrivateMessage,
    commands.CommandOnCooldown,
    commands.MaxConcurrencyReached,
    commands.BadArgument,
    commands.BadBoolArgument,
)


@cog_i18n(_)
class AutoTraceback(DashboardIntegration, Cog):
    """A cog to display the error traceback of a command automatically after the error!"""

    def __init__(self, bot: Red) -> None:
        super().__init__(bot=bot)

        self.tracebacks: typing.List[str] = []

    @commands.is_owner()
    @commands.hybrid_command()
    async def traceback(
        self, ctx: commands.Context, public: typing.Optional[bool] = True, index: int = 0
    ) -> None:
        """Sends to the owner the last command exception that has occurred.

        If public (yes is specified), it will be sent to the chat instead.

        Warning: Sending the traceback publicly can accidentally reveal sensitive information about your computer or configuration.

        **Examples:**
            - `[p]traceback` - Sends the traceback to your DMs.
            - `[p]traceback True` - Sends the last traceback in the current context.

        **Arguments:**
            - `[public]` - Whether to send the traceback to the current context. Default is `True`.
            - `[index]`  - The error index. `0` is the last one.
        """
        if not self.tracebacks and not ctx.bot._last_exception:
            raise commands.UserFeedbackCheckFailure(_("No exception has occurred yet."))
        if index == 0:  # Last bot exception can be set directly by cogs.
            _last_exception = ctx.bot._last_exception
        else:
            try:
                _last_exception = self.tracebacks[-(index + 1)]
            except IndexError:
                _last_exception = ctx.bot._last_exception
        _last_exception = _last_exception.split("\n")
        _last_exception[0] = _last_exception[0] + (
            "" if _last_exception[0].endswith(":") else ":\n"
        )
        _last_exception = "\n".join(_last_exception)
        _last_exception = CogsUtils.replace_var_paths(_last_exception)
        if public:
            try:
                await Menu(pages=_last_exception, timeout=180, lang="py").start(ctx)
            except discord.HTTPException:
                pass
            else:
                return
        for page in pagify(_last_exception, shorten_by=15):
            try:
                await ctx.author.send(box(page, lang="py"))
            except discord.HTTPException:
                raise commands.UserFeedbackCheckFailure(
                    "I couldn't send the traceback message to you in DM. "
                    "Either you blocked me or you disabled DMs in this server."
                )

    @commands.Cog.listener()
    async def on_command_error(
        self, ctx: commands.Context, error: commands.CommandError, unhandled_by_cog: bool = False
    ) -> None:
        if await self.bot.cog_disabled_in_guild(cog=self, guild=ctx.guild):
            return
        if isinstance(error, IGNORED_ERRORS):
            return
        traceback_error = "".join(
            traceback.format_exception(type(error), error, error.__traceback__)
        )
        _traceback_error = traceback_error.split("\n")
        _traceback_error[0] = _traceback_error[0] + (
            "" if _traceback_error[0].endswith(":") else ":\n"
        )
        traceback_error = "\n".join(_traceback_error)
        traceback_error = CogsUtils.replace_var_paths(traceback_error)
        self.tracebacks.append(traceback_error)
        if ctx.author.id not in ctx.bot.owner_ids:
            return
        pages = [box(page, lang="py") for page in pagify(traceback_error, shorten_by=10)]
        try:
            await Menu(pages=pages, timeout=180, delete_after_timeout=False).start(ctx)
        except discord.HTTPException:
            pass

    @commands.Cog.listener()
    async def on_assistant_cog_add(
        self, assistant_cog: typing.Optional[commands.Cog] = None
    ) -> None:  # Vert's Assistant integration/third party.
        if assistant_cog is None:
            return self.get_last_command_error_traceback_for_assistant
        schema = {
            "name": "get_last_command_error_traceback_for_assistant",
            "description": "Get the traceback of the last command error occured on the bot.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        }
        await assistant_cog.register_function(cog_name=self.qualified_name, schema=schema)

    async def get_last_command_error_traceback_for_assistant(
        self, user: typing.Union[discord.Member, discord.User], *args, **kwargs
    ):
        if user.id not in self.bot.owner_ids:
            return "Only bot owners can view errors tracebacks."
        if not self.bot._last_exception:
            return "No last command error recorded."
        last_traceback = self.bot._last_exception
        last_traceback = CogsUtils.replace_var_paths(last_traceback)
        data = {
            "Last command error traceback": f"\n{last_traceback}",
        }
        return [f"{key}: {value}\n" for key, value in data.items() if value is not None]

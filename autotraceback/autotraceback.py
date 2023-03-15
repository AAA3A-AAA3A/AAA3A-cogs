from .AAA3A_utils import CogsUtils, Menu  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
from redbot.core.bot import Red  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import traceback

from redbot.core.utils.chat_formatting import box, pagify

# Credits:
# General repo credits.

_ = Translator("AutoTraceback", __file__)

if CogsUtils().is_dpy2:
    from functools import partial

    hybrid_command = partial(commands.hybrid_command, with_app_command=False)
    hybrid_group = partial(commands.hybrid_group, with_app_command=False)
else:
    hybrid_command = commands.command
    hybrid_group = commands.group

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
class AutoTraceback(commands.Cog):
    """A cog to display the error traceback of a command automatically after the error!"""

    def __init__(self, bot: Red) -> None:
        self.bot: Red = bot

        self.tracebacks: typing.List[str] = []

        self.cogsutils: CogsUtils = CogsUtils(cog=self)

    @commands.is_owner()
    @hybrid_command()
    async def traceback(self, ctx: commands.Context, public: bool = False) -> None:
        """Sends to the owner the last command exception that has occurred.

        If public (yes is specified), it will be sent to the chat instead.

        Warning: Sending the traceback publicly can accidentally reveal sensitive information about your computer or configuration.

        **Examples:**
            - `[p]traceback` - Sends the traceback to your DMs.
            - `[p]traceback True` - Sends the last traceback in the current context.

        **Arguments:**
            - `[public]` - Whether to send the traceback to the current context. Leave blank to send to your DMs.
        """
        if ctx.bot._last_exception:
            _last_exception = ctx.bot._last_exception.split("\n")
            _last_exception[0] = _last_exception[0] + (
                "" if _last_exception[0].endswith(":") else ":\n"
            )
            _last_exception = "\n".join(_last_exception)
            _last_exception = self.cogsutils.replace_var_paths(_last_exception)
            if public:
                pages = [
                    box(page, lang="py")
                    for page in pagify(
                        _last_exception, shorten_by=15, page_length=1985
                    )
                ]
                try:
                    await Menu(pages=pages, timeout=180, delete_after_timeout=False).start(ctx)
                except discord.HTTPException:
                    pass
                else:
                    return
            for page in pagify(_last_exception, shorten_by=15, page_length=1985):
                try:
                    await ctx.author.send(box(page, lang="py"))
                except discord.HTTPException:
                    raise commands.UserFeedbackCheckFailure(
                        "I couldn't send the traceback message to you in DM. "
                        "Either you blocked me or you disabled DMs in this server."
                    )
                return
        else:
            await ctx.send(_("No exception has occurred yet."))

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        if isinstance(error, IGNORED_ERRORS):
            return
        traceback_error = "".join(
            traceback.format_exception(type(error), error, error.__traceback__)
        )
        traceback_error = self.cogsutils.replace_var_paths(traceback_error)
        self.tracebacks.append(traceback_error)
        if ctx.author.id not in ctx.bot.owner_ids:
            return
        pages = [
            box(page, lang="py")
            for page in pagify(traceback_error, shorten_by=15, page_length=1985)
        ]
        try:
            await Menu(pages=pages, timeout=180, delete_after_timeout=False).start(ctx)
        except discord.HTTPException:
            pass

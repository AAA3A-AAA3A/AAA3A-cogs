from .AAA3A_utils.cogsutils import CogsUtils, Menu  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
from redbot.core.bot import Red  # isort:skip
import discord  # isort:skip
import os
import traceback

from redbot.core.utils.chat_formatting import box, pagify

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

# Credits:
# Thanks to @epic guy on Discord for the basic syntax (command groups, commands) and also commands (await ctx.send, await ctx.author.send, await ctx.message.delete())!
# Thanks to @YamiKaitou on Discord for the technique in the init file to load the interaction client only if it is not loaded! Before this fix, when a user clicked on a button, the actions would be launched about 10 times, which caused huge spam and a loop in the channel.
# Thanks to the developers of the cogs I added features to as it taught me how to make a cog! (Chessgame by WildStriker, Captcha by Kreusada, Speak by Epic guy and Rommer by Dav)
# Thanks to all the people who helped me with some commands in the #coding channel of the redbot support server!

_ = Translator("AutoTraceback", __file__)

@cog_i18n(_)
class AutoTraceback(commands.Cog):
    """A cog to display the error traceback of a command aomatically after the error!"""

    def __init__(self, bot):
        self.bot: Red = bot
        super().__init__()

        self.cogsutils = CogsUtils(cog=self)
        self.cogsutils._setup()

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        if ctx.author.id not in ctx.bot.owner_ids:
            return
        if isinstance(error, IGNORED_ERRORS):
            return
        traceback_error = "".join(traceback.format_exception(type(error), error, error.__traceback__))
        traceback_error = self.cogsutils.replace_var_paths(traceback_error)
        pages = []
        for page in pagify(traceback_error, shorten_by=15, page_length=1985):
            pages.append(box(page, lang="py"))
        try:
            await Menu(pages=pages, timeout=30, delete_after_timeout=True).start(ctx)
        except discord.HTTPException:
            return
        return
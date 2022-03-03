from .AAA3A_utils.cogsutils import CogsUtils
import discord
from redbot.core import commands
from redbot.core.utils.chat_formatting import pagify, box
from redbot.core.utils.menus import menu, close_menu
import traceback
import os

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

CONTROLS = {
    "\N{CROSS MARK}": close_menu,
}

# Credits:
# Thanks to @epic guy on Discord for the basic syntax (command groups, commands) and also commands (await ctx.send, await ctx.author.send, await ctx.message.delete())!
# Thanks to @YamiKaitou on Discord for the technique in the init file to load the interaction client only if it is not loaded! Before this fix, when a user clicked on a button, the actions would be launched about 10 times, which caused huge spam and a loop in the channel.
# Thanks to the developers of the cogs I added features to as it taught me how to make a cog! (Chessgame by WildStriker, Captcha by Kreusada, Speak by Epic guy and Rommer by Dav)
# Thanks to all the people who helped me with some commands in the #coding channel of the redbot support server!

class AutoTraceback(commands.Cog):
    """A cog to display the error traceback of a command aomatically after the error!"""

    def __init__(self, bot):
        self.bot = bot
        super().__init__()

        self.cogsutils = CogsUtils(cog=self)
        self.cogsutils._setup()

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        if not ctx.author.id in ctx.bot.owner_ids:
            return
        if isinstance(error, IGNORED_ERRORS):
            return
        traceback_error = "".join(traceback.format_exception(type(error), error, error.__traceback__)).replace(os.environ["USERPROFILE"], "{USERPROFILE}")
        pages = []
        for page in pagify(traceback_error, shorten_by=15, page_length=1985):
            pages.append(box(page, lang="py"))
        try:
            await menu(ctx, pages=pages, controls=CONTROLS, page=0, timeout=30)
        except discord.HTTPException:
            return
        return

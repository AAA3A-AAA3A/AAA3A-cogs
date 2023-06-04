from AAA3A_utils import Cog, CogsUtils  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
from redbot.core.bot import Red  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

from .view import SplitOrStealGameView

# Credits:
# General repo credits.

_ = Translator("SplitOrStealGame", __file__)


@cog_i18n(_)
class SplitOrStealGame(Cog):
    """A cog to play a match of SplitOrSteal game!"""

    def __init__(self, bot: Red) -> None:
        self.bot: Red = bot

        self.games: typing.Dict[discord.Message, SplitOrStealGameView] = {}

        self.cogsutils: CogsUtils = CogsUtils(cog=self)

    @commands.guild_only()
    @commands.hybrid_command(aliases=["splitorsteal", "sosg", "sos"])
    async def splitorstealgame(self, ctx: commands.Context) -> None:
        """
        Play a match of SplitOrSteal game.

        Two player will have to click the button that they choose (`split` or `steal`).
        • If both choose `split` both of them win.
        • If both choose `steal`, both loose.
        • if one chooses `split` and one chooses `steal`, the one who choose `steal` will win.
        """
        await SplitOrStealGameView(cog=self).start(ctx)

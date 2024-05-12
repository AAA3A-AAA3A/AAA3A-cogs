from AAA3A_utils import Cog, CogsUtils  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
from redbot.core.bot import Red  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

from .view import SplitOrStealGameView

# Credits:
# General repo credits.
# Thanks to Lemon for the cog idea!

_ = Translator("SplitOrStealGame", __file__)


@cog_i18n(_)
class SplitOrStealGame(Cog):
    """A cog to play a match of SplitOrSteal game!"""

    @property
    def games(self) -> typing.Dict[discord.Message, SplitOrStealGameView]:
        return self.views

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

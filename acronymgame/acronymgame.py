from AAA3A_utils import Cog, CogsUtils  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
from redbot.core.bot import Red  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

from .view import AcronymGameView


# Credits:
# General repo credits.
# Thanks to Flame for his tests which allowed to discover several errors!
# Thanks to Vertyco for ideas, and leaderboard code (https://github.com/vertyco/vrt-cogs/blob/main/pixl/pixl.py)!

_ = Translator("AcronymGame", __file__)


@cog_i18n(_)
class AcronymGame(Cog):
    """A cog to play a random match of Acrononym game, with Modals!"""

    def __init__(self, bot: Red) -> None:
        self.bot: Red = bot

        self.games: typing.Dict[discord.Message, AcronymGameView] = {}

        self.cogsutils: CogsUtils = CogsUtils(cog=self)

    @commands.guild_only()
    @commands.hybrid_command(aliases=["acro", "acronym"])
    async def acronymgame(self, ctx: commands.Context) -> None:
        """
        Play a random match of Acronym game.
        """
        await AcronymGameView(cog=self).start(ctx)

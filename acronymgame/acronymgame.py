from AAA3A_utils import Cog, CogsUtils  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
from redbot.core.bot import Red  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

from .view import AcronymGameView

# Credits:
# General repo credits.
# Thanks to Lemon for the cog idea!
# Thanks to Flame for his tests which allowed to discover several errors!
# Thanks to Vertyco for ideas, and leaderboard code (https://github.com/vertyco/vrt-cogs/blob/main/pixl/pixl.py)!

_ = Translator("AcronymGame", __file__)


@cog_i18n(_)
class AcronymGame(Cog):
    """A cog to play a random match of Acrononym game, with Modals!"""

    def __init__(self, bot: Red) -> None:
        super().__init__(bot=bot)

    async def red_delete_data_for_user(self, *args, **kwargs) -> None:
        """Nothing to delete."""
        return

    async def red_get_data_for_user(self, *args, **kwargs) -> typing.Dict[str, typing.Any]:
        """Nothing to get."""
        return {}

    @property
    def games(self) -> typing.Dict[discord.Message, AcronymGameView]:
        return self.views

    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    @commands.hybrid_command(aliases=["acro", "acronym"])
    async def acronymgame(self, ctx: commands.Context) -> None:
        """
        Play a random match of Acronym game.
        """
        await AcronymGameView(cog=self).start(ctx)

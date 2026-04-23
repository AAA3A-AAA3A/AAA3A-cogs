import discord

from AAA3A_utils import Cog
from redbot.core import commands
from redbot.core.i18n import Translator, cog_i18n

from .view import AcronymGameView

# Credits:
# General repo credits.
# Thanks to Lemon for the cog idea!
# Thanks to Flame for his tests which allowed to discover several errors!
# Thanks to Vertyco for ideas, and leaderboard code (https://github.com/vertyco/vrt-cogs/blob/main/pixl/pixl.py)!

_: Translator = Translator("AcronymGame", __file__)


@cog_i18n(_)
class AcronymGame(Cog):
    """Play a random match of Acrononym game, with Modals!"""

    @property
    def games(self) -> dict[discord.Message, AcronymGameView]:
        return self.views

    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    @commands.hybrid_command(aliases=["acronym", "acro"])
    async def acronymgame(self, ctx: commands.Context) -> None:
        """Play a random match of Acronym game."""
        await AcronymGameView(cog=self).start(ctx)

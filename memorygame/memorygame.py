from .AAA3A_utils import Cog, CogsUtils  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
from redbot.core.bot import Red  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

from .view import MemoryGameView

# Credits:
# General repo credits.
# Thanks to Flame for his tests which allowed to discover several errors!

_ = Translator("MemoryGame", __file__)

if CogsUtils().is_dpy2:
    hybrid_command = commands.hybrid_command
    hybrid_group = commands.hybrid_group
else:
    hybrid_command = commands.command
    hybrid_group = commands.group


@cog_i18n(_)
class MemoryGame(Cog):
    """A cog to play to Memory game, with buttons!"""

    def __init__(self, bot: Red) -> None:
        self.bot: Red = bot

        self.games: typing.Dict[discord.Message, MemoryGameView] = {}

        self.cogsutils: CogsUtils = CogsUtils(cog=self)

    @hybrid_command()
    async def memorygame(self, ctx: commands.Context) -> None:
        """
        Play to Memory game.
        """
        await MemoryGameView(cog=self).start(ctx)

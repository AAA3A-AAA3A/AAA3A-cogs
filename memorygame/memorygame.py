from .AAA3A_utils import Cog, CogsUtils  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
from redbot.core.bot import Red  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

from .view import MemoryGameView

# Credits:
# General repo credits.

_ = Translator("MemoryGame", __file__)

if CogsUtils().is_dpy2:
    from functools import partial

    hybrid_command = partial(commands.hybrid_command, with_app_command=False)
    hybrid_group = partial(commands.hybrid_group, with_app_command=False)
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

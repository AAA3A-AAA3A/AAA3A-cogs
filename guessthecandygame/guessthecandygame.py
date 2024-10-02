from AAA3A_utils import Cog  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.bot import Red  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

from redbot.core.data_manager import bundled_data_path

from .view import GuessTheCandyGameView

# Credits:
# General repo credits.
# Thanks to Tann for the cog idea and the assets!

_: Translator = Translator("GuessTheCandyGame", __file__)


@cog_i18n(_)
class GuessTheCandyGame(Cog):
    """Recognise the correct candy as fast as you can!"""

    def __init__(self, bot: Red) -> None:
        super().__init__(bot=bot)

        self.candies: typing.Dict[str, discord.File] = {}
        self.shadows: typing.Dict[str, discord.File] = {}

    async def cog_load(self) -> None:
        await super().cog_load()
        cog_path = bundled_data_path(self)
        candies_names = {
            f.name.split(".")[0].replace("_", " ").title(): f.name
            for f in (cog_path / "candies").iterdir() if f.is_file() and f.suffix == ".png"
        }
        self.candies = {
            name: cog_path / "candies" / file_name
            for name, file_name in candies_names.items()
        }
        self.shadows = {
            name: cog_path / "shadows" / file_name
            for name, file_name in candies_names.items()
        }

    @property
    def games(self) -> typing.Dict[discord.Message, GuessTheCandyGameView]:
        return self.views

    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True, attach_files=True)
    @commands.hybrid_command(aliases=["guessthecandygame", "gtc"])
    async def guessthecandy(self, ctx: commands.Context, difficulty: commands.Range[int, 5, 23] = 5) -> None:
        """Recognise the correct candy as fast as you can..."""
        await GuessTheCandyGameView(cog=self, difficulty=difficulty).start(ctx)

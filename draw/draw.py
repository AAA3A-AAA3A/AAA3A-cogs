from AAA3A_utils import Cog, CogsUtils  # isort:skip
from redbot.core import commands, app_commands  # isort:skip
from redbot.core.bot import Red  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import sys
if sys.version_info >= (3, 11):
    from typing import Literal
else:
    from typing_extensions import Literal

import asyncio
import io
from urllib.parse import quote_plus

import aiohttp
from PIL import Image, ImageFilter, UnidentifiedImageError

from .board import Board
from .color import Color
from .constants import (
    DEFAULT_CACHE,
    IMAGE_EXTENSION,
    MAIN_COLORS,
    MAX_HEIGHT_OR_WIDTH,
    MIN_HEIGHT_OR_WIDTH,
    base_colors_options,
)  # NOQA
from .start_view import StartDrawView

# Credits:
# General repo credits.
# Thanks to WitherredAway for the full Draw code (https://github.com/WitherredAway/Yeet/blob/master/cogs/Draw) and his indispensable help!
# Changes: Use Pillow images instead of custom emojis for the board itself, adaptation to Red bot, download images from Discord or Internet, add "Display Cursor" and "Raw Paint" buttons, allow to do a pixels selection with "ABCD" button...
# Thanks to Karlo in Red main server for his ideas and testing the cog!

_ = Translator("Draw", __file__)


@cog_i18n(_)
class Draw(Cog):
    """A cog to make pixel arts on Discord!"""

    def __init__(self, bot: Red) -> None:
        self.bot: Red = bot

        self._session: aiohttp.ClientSession = None
        self.drawings: typing.Dict[discord.Message, StartDrawView] = {}
        self.cache: typing.Dict[
            typing.Union[str, int, typing.Tuple[int, int, int, int]]
        ] = {}  # Unicode emojis, colors RGB and Discord custom emojis ids.

        self.__authors__ = ["WitherredAway", "AAA3A"]
        self.cogsutils: CogsUtils = CogsUtils(cog=self)

    async def cog_load(self) -> None:
        self._session: aiohttp.ClientSession = aiohttp.ClientSession()
        asyncio.create_task(self.generate_cache())

    async def generate_cache(self) -> None:
        for pixel in DEFAULT_CACHE:
            await self.get_pixel(pixel)

    async def cog_unload(self) -> None:
        if self._session is not None:
            await self._session.close()
        await super().cog_unload()

    async def get_pixel(
        self,
        pixel: typing.Union[
            str, discord.Emoji, int, Color, typing.Tuple[int, int, int, typing.Optional[int]]
        ],
        to_file: typing.Optional[bool] = False,
    ) -> typing.Union[Image, discord.File]:
        if isinstance(pixel, typing.Tuple) and len(pixel) in {3, 4}:
            pixel = Color(pixel)
        try:
            pixel = int(pixel)
        except (ValueError, TypeError):
            pass
        if isinstance(pixel, discord.PartialEmoji):
            pixel = pixel.id or pixel.name
        if isinstance(pixel, (discord.Emoji, int)):  # Discord custom emoji
            key = getattr(pixel, "id", pixel)
            url = f"https://cdn.discordapp.com/emojis/{key}.png"
        elif isinstance(pixel, str):
            if pixel.startswith("http"):  # url
                key = pixel
                url = pixel
            else:  # unicode
                key = pixel
                url = f"https://emojicdn.elk.sh/{quote_plus(key)}?style=twitter"
                # chars = [hex(ord(char))[2:] for char in key]
                # if len(chars) == 2 and "fe0f" in chars:
                #     chars.remove("fe0f")
                # if "20e3" in chars:
                #     chars.remove("fe0f")
                # url = f"https://twemoji.maxcdn.com/2/svg/{'-'.join(chars)}.svg"
        elif isinstance(pixel, Color):
            key = pixel.RGBA
            if key not in self.cache:
                url = None
                image = await pixel.to_image()
        else:
            raise TypeError(pixel)
        if key in self.cache:
            image = self.cache[key]
        else:
            if url is not None:
                async with self._session.get(url) as r:
                    image_bytes = await r.read()
                try:
                    image = Image.open(io.BytesIO(image_bytes))
                except (AttributeError, UnidentifiedImageError) as e:
                    self.log.error(
                        f"Error when retrieving the pixel {key} ({url}) image for the cache.",
                        exc_info=e,
                    )
                    return Image.new("RGBA", (100, 100), (0, 0, 0, 0))
            try:
                image = image.filter(ImageFilter.SHARPEN)  # Maybe useless.
            except ValueError:
                pass
            self.cache[key] = image
        if to_file:
            buffer = io.BytesIO()
            image.save(buffer, format=IMAGE_EXTENSION, optimize=True)
            buffer.seek(0)
            return discord.File(buffer, filename=f"pixel.{IMAGE_EXTENSION.lower()}")
        return image

    @commands.hybrid_command(aliases=["paint", "pixelart"])
    @app_commands.choices(
        height=[
            app_commands.Choice(name=str(n), value=str(n))
            for n in range(MIN_HEIGHT_OR_WIDTH, MAX_HEIGHT_OR_WIDTH + 1)
        ],
        width=[
            app_commands.Choice(name=str(n), value=str(n))
            for n in range(MIN_HEIGHT_OR_WIDTH, MAX_HEIGHT_OR_WIDTH + 1)
        ],
        background=[
            app_commands.Choice(name=f"{option.emoji} {option.label}", value=option.value)
            for option in base_colors_options()
        ],
    )
    async def draw(
        self,
        ctx: commands.Context,
        from_message: typing.Optional[commands.MessageConverter] = None,
        height: typing.Optional[commands.Range[int, MIN_HEIGHT_OR_WIDTH, MAX_HEIGHT_OR_WIDTH]] = 9,
        width: typing.Optional[commands.Range[int, MIN_HEIGHT_OR_WIDTH, MAX_HEIGHT_OR_WIDTH]] = 9,
        background: Literal[*MAIN_COLORS] = MAIN_COLORS[-1],
    ) -> None:
        """Make a pixel art on Discord."""
        if from_message is None:
            board = (height, width, background)
        else:
            if from_message not in self.drawings:
                raise commands.UserFeedbackCheckFailure(_("This message isn't in the cache."))
            board = Board(
                cog=self,
                height=self.drawings[from_message].board.height,
                width=self.drawings[from_message].width,
                background=background,
            )
            board.board_history = self.drawings[from_message].board.board_history.copy()
            board.board_index = self.drawings[from_message].board.board_index
        await StartDrawView(cog=self, board=board).start(ctx)

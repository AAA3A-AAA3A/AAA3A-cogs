from redbot.core.bot import Red  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import numpy as np

from .board import Board
from .color import Color
from .constants import MAIN_COLORS_DICT

class Tool(discord.ui.Button):
    """A template class for each of the tools."""

    def __init__(self, view: discord.ui.View, *, primary: typing.Optional[bool] = True) -> None:
        super().__init__(
            emoji=self.emoji,
            style=discord.ButtonStyle.success
            if primary is True
            else discord.ButtonStyle.secondary,
        )
        self._view: discord.ui.View = view
        self.board: Board = self._view.board
        self.bot: Red = self._view.cog.bot

    @property
    def name(self) -> str:
        return None

    @property
    def emoji(self) -> str:
        return None

    @property
    def description(self) -> str:
        return None

    @property
    def auto_use(self) -> bool:
        return False

    async def use(self, *, interaction: discord.Interaction) -> bool:
        """The method that is called when the tool is used."""
        pass

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        if await self.use(interaction=interaction):
            await self.view._update()


class BrushTool(Tool):
    @property
    def name(self) -> str:
        return "Brush"

    @property
    def emoji(self) -> str:
        return "<:brush:1056853866563506176>"  # "🖌️"

    @property
    def description(self) -> str:
        return "Draw where the cursor is."

    async def use(self, *, interaction: discord.Interaction) -> bool:
        """The method that is called when the tool is used."""
        return self.board.draw(self.board.cursor)


class EraseTool(Tool):
    @property
    def name(self) -> str:
        return "Eraser"

    @property
    def emoji(self) -> str:
        return "<:eraser:1056853917973094420>"  # "✏️"

    @property
    def description(self) -> str:
        return "Erase where the cursor is."

    async def use(self, *, interaction: discord.Interaction) -> bool:
        """The method that is called when the tool is used."""
        return self.board.draw(self.board.background)


class EyedropperTool(Tool):
    @property
    def name(self) -> str:
        return "Eyedropper"

    @property
    def emoji(self) -> str:
        return "<:eyedropper:1056854084004630568>"  # "💉"

    @property
    def description(self) -> str:
        return "Pick and add color to Palette."

    @property
    def auto_use(self) -> bool:
        return True

    async def use(self, *, interaction: discord.Interaction) -> bool:
        """The method that is called when the tool is used."""
        cursor_pixel = self.board.cursor_pixel
        pixel = cursor_pixel

        # Check if the option already exists.
        option = self.view.color_menu.value_to_option(pixel)
        if option is None:
            # Try to find the emoji so that we can use its real name as label.
            try:
                pixel = int(pixel)
            except (ValueError, TypeError):
                pass
            if isinstance(pixel, int) and (fetched_emoji := self.bot.get_emoji(pixel)) is not None:
                label = fetched_emoji.name
                emoji = fetched_emoji
                value = str(fetched_emoji.id)
            elif isinstance(pixel, Color):
                label = (await pixel.get_name()) + f" ({pixel.hex})"
                emoji = None
                value = f"#{pixel.hex}"
            else:
                label = pixel
                emoji = discord.PartialEmoji.from_str(pixel)
                value = pixel
            option = discord.SelectOption(
                label=f"Eyedropped option: {label}",
                emoji=emoji,
                value=value,
            )
            self.view.color_menu.append_option(option)

        if self.board.cursor == option.value:
            return False
        self.board.cursor = option.value
        self.view.color_menu.set_default(option)
        return True


class FillTool(Tool):
    @property
    def name(self) -> str:
        return "Fill"

    @property
    def emoji(self) -> str:
        return "<:fill:1056853974394867792>"  # "🎨"

    @property
    def description(self) -> str:
        return "Fill closed area."

    @property
    def auto_use(self) -> bool:
        return True

    async def use(
        self,
        *,
        interaction: discord.Interaction,
        initial_coords: typing.Optional[typing.Tuple[int, int]] = None,
    ) -> bool:
        """The method that is called when the tool is used."""
        color = self.board.cursor
        if self.board.cursor_pixel == color:
            return

        # Use Breadth-First Search algorithm to fill an area.
        initial_coords = initial_coords or (
            self.board.cursor_row,
            self.board.cursor_col,
        )
        initial_pixel = self.board.get_pixel(*initial_coords)

        coords = []
        queue = [initial_coords]
        i = 0

        while i < len(queue):
            row, col = queue[i]
            i += 1
            # Skip to next cell in the queue if
            # the row is less than 0 or greater than the max row possible,
            # the col is less than 0 or greater than the max col possible or
            # the current pixel (or its cursor version) is not the same as the pixel to replace (or its cursor version)
            if (
                any((row < 0, row > self.board.cursor_row_max))
                or any((col < 0, col > self.board.cursor_col_max))
                or self.board.get_pixel(row, col) != initial_pixel
                or (row, col) in coords
            ):
                continue

            coords.append((row, col))

            queue.extend(((row + 1, col), (row - 1, col), (row, col + 1), (row, col - 1)))
        return self.board.draw(coords=coords)  # Draw all the cells.


class ReplaceTool(Tool):
    @property
    def name(self) -> str:
        return "Replace"

    @property
    def emoji(self) -> str:
        return "<:replace:1056854037066154034>"  # "🎨"

    @property
    def description(self) -> str:
        return "Replace all pixels."

    @property
    def auto_use(self) -> bool:
        return True

    async def use(self, *, interaction: discord.Interaction) -> bool:
        """The method that is called when the tool is used."""
        color = self.board.cursor
        to_replace = self.board.cursor_pixel
        return self.board.draw(
            color, coords=np.array(np.where(self.board.board == to_replace)).T
        )


CHANGE_AMOUNT = 17  # Change amount for Lighten & Darken tools to allow exactly 15 changes from 0 or 255, respectively.

class DarkenTool(Tool):
    @property
    def name(self) -> str:
        return "Darken"

    @property
    def emoji(self) -> str:
        return "🔅"

    @property
    def description(self) -> str:
        return "Darken pixel(s) by 17 RGB values."

    @staticmethod
    def edit(value: int) -> int:
        return max(
            value - CHANGE_AMOUNT, 0
        )  # The max func makes sure it doesn't go below 0 when decreasing, for example, black.

    async def use(self, *, interaction: discord.Interaction) -> bool:
        """The method that is called when the tool is used."""
        coords = self.board.cursor_coords
        for coord in coords:
            pixel = self.board.board[coord]
            color = MAIN_COLORS_DICT.get(pixel, pixel)
            if isinstance(color, Color):
                RGB_A = (
                    self.edit(color.R),
                    self.edit(color.G),
                    self.edit(color.B),
                    color.A,
                )
                modified_color = Color(RGB_A)
                self.board.draw(modified_color, coords=[coord])
        return True


class LightenTool(DarkenTool):
    @property
    def name(self) -> str:
        return "Lighten"

    @property
    def emoji(self) -> str:
        return "🔆"

    @property
    def description(self) -> str:
        return "Lighten pixel(s) by 17 RGB values."

    @staticmethod
    def edit(value: int) -> int:
        return min(
            value + CHANGE_AMOUNT, 255
        )  # The min func makes sure it doesn't go above 255 when increasing, for example, white.

class InverseTool(DarkenTool):
    @property
    def name(self) -> str:
        return "Invert Colors"

    @property
    def emoji(self) -> str:
        return "🔦"

    @property
    def description(self) -> str:
        return "Invert colors in pixel(s)."

    @staticmethod
    def edit(value: int) -> int:
        return 255 - value

from redbot.core import commands  # isort:skip
import discord  # isort:skip
import typing  # isort:skip
import typing_extensions  # isort:skip

import io
from dataclasses import dataclass

import numpy as np
from PIL import Image, ImageDraw

from .color import Color
from .constants import (
    COLUMN_ICONS,
    COLUMN_ICONS_DICT,
    IMAGE_EXTENSION,
    LB,
    MAIN_COLORS,
    MAIN_COLORS_DICT,
    PADDING,
    ROW_ICONS,
    ROW_ICONS_DICT,
    u200b,
)  # NOQA


@dataclass
class Coords:
    x: int
    y: int

    def __post_init__(self) -> None:
        self.ix: int = self.x * -1
        self.iy: int = self.y * -1


class Board:
    def __init__(
        self,
        cog: commands.Cog,
        *,
        height: typing.Optional[int] = 9,
        width: typing.Optional[int] = 9,
        background: typing.Optional[typing.Literal["🟥", "🟧", "🟨", "🟩", "🟦", "🟪", "🟫", "⬛", "⬜", "transparent"]] = MAIN_COLORS[-1],  # Literal[*MAIN_COLORS]
    ) -> None:
        self.cog: commands.Cog = cog

        self.height: int = height
        self.width: int = width
        self.background: str = background

        self.cursor_display: bool = True

        self.initial_board: np.ndarray = np.full(
            (self.height, self.width), self.background, dtype="object"
        )
        self.board_history: typing.List[np.ndarray] = [self.initial_board.copy()]
        self.board_index: int = 0
        self.set_attributes()

        # This is for the select tool.
        self.initial_coords: typing.Tuple[int, int]
        self.initial_row: int = 0
        self.initial_col: int = 0
        self.final_coords: typing.Tuple[int, int]
        self.final_row: int = 0
        self.final_col: int = 0

        self.clear_cursors()

    def set_attributes(self) -> None:
        self.row_labels: typing.Tuple[str] = ROW_ICONS[: self.height]
        self.col_labels: typing.Tuple[str] = COLUMN_ICONS[: self.width]
        self.centre: typing.Tuple[int, int] = (
            len(self.row_labels) // 2,
            len(self.col_labels) // 2,
        )
        self.centre_row, self.centre_col = self.centre

        self.cursor: str = self.background
        self.cursor_row, self.cursor_col = self.centre
        self.cursor_row_max = len(self.row_labels) - 1
        self.cursor_col_max = len(self.col_labels) - 1
        self.cursor_coords: typing.List[typing.Tuple[int, int]] = [
            (self.cursor_row, self.cursor_col)
        ]

    def __str__(self) -> str:
        """Method that gives a formatted version of the board with row/col labels."""
        cursor_rows = tuple(row for row, __ in self.cursor_coords)
        cursor_cols = tuple(col for __, col in self.cursor_coords)
        row_labels = [
            (str(row) if idx not in cursor_rows else str(ROW_ICONS_DICT[row]))
            for idx, row in enumerate(self.row_labels)
        ]
        col_labels = [
            (str(col) if idx not in cursor_cols else str(COLUMN_ICONS_DICT[col]))
            for idx, col in enumerate(self.col_labels)
        ]
        return (
            f"{self.cursor}{PADDING}{u200b.join(col_labels)}\n"
            f"\n{LB.join([f'{row_labels[idx]}{PADDING}{u200b.join(row)}' for idx, row in enumerate(self.board)])}"
        )

    async def to_image(self) -> Image:
        height, width = len(self.board), len(self.board[0])
        cursor_rows = tuple(row for row, __ in self.cursor_coords)
        cursor_cols = tuple(col for __, col in self.cursor_coords)
        row_labels = [
            (row if idx not in cursor_rows else ROW_ICONS_DICT[row])
            for idx, row in enumerate(self.row_labels)
        ]
        col_labels = [
            (col if idx not in cursor_cols else COLUMN_ICONS_DICT[col])
            for idx, col in enumerate(self.col_labels)
        ]

        size = 25
        sp = 1 if self.cursor_display else 0
        _width = size * (width + 1) + sp * width + round(size / 4)
        _height = size * (height + 1) + sp * height + round(size / 4)
        img: Image.Image = Image.new("RGBA", (_width, _height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        y = 0
        for _y in range(0 if self.cursor_display else 2, height + 2):
            if _y == 1:
                y += round(size / 4)
                continue
            x = 0
            for _x in range(0 if self.cursor_display else 2, width + 2):
                if _x == 1:
                    x += round(size / 4)
                    continue
                # draw.rounded_rectangle((x, y, x + size, y + size), radius=3, fill=(255, 255, 255), outline=(255, 0, 0) if (_y - 2, _x - 2) in self.cursor_coords else (0, 0, 0))
                if _x == 0 and _y == 0:
                    cursor = self.cursor
                    if cursor == "transparent":
                        x += size + sp
                        continue
                    image: Image.Image = await self.cog.get_pixel(MAIN_COLORS_DICT.get(cursor, cursor))
                elif _x == 0 and _y > 1:
                    emoji = row_labels[_y - 2]
                    image: Image.Image = await self.cog.get_pixel(emoji)
                elif _y == 0 and _x > 1:
                    emoji = col_labels[_x - 2]
                    image: Image.Image = await self.cog.get_pixel(emoji)
                else:
                    pixel = self.board[_y - 2, _x - 2]
                    if pixel == "transparent":
                        if self.cursor_display:
                            if (_y - 2, _x - 2) in self.cursor_coords:
                                draw.rounded_rectangle(
                                    (x, y, x + size, y + size),
                                    radius=3,
                                    fill=None,
                                    outline=(18, 18, 20, 255)
                                    if getattr(
                                        MAIN_COLORS_DICT.get(self.cursor, self.cursor),
                                        "RGBA",
                                        (0, 0, 0, 0),
                                    )
                                    == (0, 0, 0, 255)
                                    else (
                                        MAIN_COLORS_DICT.get(self.cursor, self.cursor).RGBA
                                        if isinstance(
                                            MAIN_COLORS_DICT.get(self.cursor, self.cursor), Color
                                        )
                                        and self.cursor != "transparent"
                                        else (255, 0, 0, 255)
                                    ),
                                    width=2,
                                )
                            else:
                                draw.rounded_rectangle(
                                    (x, y, x + size, y + size), radius=3, outline=(0, 0, 0, 255)
                                )
                        x += size + sp
                        continue
                    image: Image.Image = await self.cog.get_pixel(MAIN_COLORS_DICT.get(pixel, pixel))
                image = image.resize((size, size))
                mask = Image.new("L", image.size, 0)
                d = ImageDraw.Draw(mask)
                # if self.cursor_display and (_y - 2, _x - 2) in self.cursor_coords:
                #     d.ellipse((0, 0, image.width, image.height), fill=255)
                # else:
                d.rounded_rectangle(
                    (0, 0, image.width, image.height),
                    radius=3 if self.cursor_display else 0,
                    fill=255,
                )
                image.putalpha(mask)
                img.paste(image, (x, y, x + size, y + size))
                if self.cursor_display and (_y - 2, _x - 2) in self.cursor_coords:
                    draw.rounded_rectangle(
                        (x, y, x + size, y + size),
                        radius=3,
                        fill=None,
                        outline=(18, 18, 20, 255)
                        if getattr(
                            MAIN_COLORS_DICT.get(self.cursor, self.cursor), "RGBA", (0, 0, 0, 0)
                        )
                        == (0, 0, 0, 255)
                        else (
                            MAIN_COLORS_DICT.get(self.cursor, self.cursor).RGBA
                            if isinstance(MAIN_COLORS_DICT.get(self.cursor, self.cursor), Color)
                            and self.cursor != "transparent"
                            else (255, 0, 0, 255)
                        ),
                        width=2,
                    )
                x += size + sp
            y += size + sp
        return img

    async def to_file(self) -> discord.File:
        img: Image.Image = await self.to_image()
        buffer = io.BytesIO()
        img.save(buffer, format=IMAGE_EXTENSION, optimize=True)
        buffer.seek(0)
        return discord.File(buffer, filename=f"image.{IMAGE_EXTENSION.lower()}")

    @property
    def board(self) -> np.ndarray:
        return self.board_history[self.board_index]

    @board.setter
    def board(self, board: np.ndarray):
        self.board_history.append(board)
        self.board_index += 1

    @property
    def backup_board(self) -> np.ndarray:
        return self.board_history[self.board_index - 1]

    def modify(
        self,
        *,
        height: typing.Optional[int] = None,
        width: typing.Optional[int] = None,
        background: typing.Optional[typing.Literal["🟥", "🟧", "🟨", "🟩", "🟦", "🟪", "🟫", "⬛", "⬜", "transparent"]] = None,  # typing.Literal[*MAIN_COLORS]
    ) -> None:
        height = height or self.height
        width = width or self.width
        background = background or self.background
        if all(
            (self.height == height, self.width == width, self.background == background)
        ):  # the attributes haven't been changed
            return
        if np.array_equal(
            self.initial_board, self.board
        ):  # Board has only background, so replace all pixels.
            self.__init__(cog=self.cog, height=height, width=width, background=background)
            return
        overlay = self.board
        base = np.full((height, width), background, dtype="object")
        # Coordinates of the centre of the overlay board
        overlay_centre = Coords(overlay.shape[1] // 2, overlay.shape[0] // 2)
        # Coordinates of the centre of the base board
        base_centre = Coords(base.shape[1] // 2, base.shape[0] // 2)
        # Difference between the centres
        centre_diff = Coords(base_centre.x - overlay_centre.x, base_centre.y - overlay_centre.y)
        # Coordinates where the overlay board should crop from
        # x = overlay's centre's width MINUS base's centre's width, if greater than 0, else 0
        # y = overlay's centre's height MINUS base's centre's height, if greater than 0, else 0
        # Meaning that if base is larger than overlay, it will include from the start of overlay
        overlay_from = Coords(max(centre_diff.ix, 0), max(centre_diff.iy, 0))
        # Coordinates where the overlay board should crop to
        # x = base's total width MINUS its centre's x-coord PLUS overlay's centre's x-coord
        # y = base's total height MINUS its centre's y-coord PLUS overlay's centre's y-coord
        # This formula gives an optimal value to crop the overlay board *to*, for both
        # smaller and larger overlay boards
        overlay_to = Coords(
            (base.shape[1] - base_centre.x) + overlay_centre.x,
            (base.shape[0] - base_centre.y) + overlay_centre.y,
        )
        # Coordinates where the base board should paste from
        # x = base's centre's width MINUS overlay's centre's width, if bigger than 0, else 0
        # y = base's centre's height MINUS overlay's centre's height, if bigger than 0, else 0
        # Meaning that if overlay is larger than base, it will start pasting from the start of base
        base_overlay_from = Coords(max(centre_diff.x, 0), max(centre_diff.y, 0))
        # Coordinates where the base board should paste to
        # x = whichever is less b/w base board's width and overlay board's width PLUS x-coord of beginning (for respective offset)
        # y = whichever is less b/w base board's height and overlay board's height PLUS y-coord of beginning (for respective offset)
        base_overlay_to = Coords(
            min(overlay.shape[1], base.shape[1]) + base_overlay_from.x,
            min(overlay.shape[0], base.shape[0]) + base_overlay_from.y,
        )
        # Crops overlay board if necessary (i.e. if base < overlay)
        overlay = overlay[overlay_from.y : overlay_to.y, overlay_from.x : overlay_to.x]
        # Pastes cropped overlay board on top of the selected portion of base board
        base[
            base_overlay_from.y : base_overlay_to.y,
            base_overlay_from.x : base_overlay_to.x,
        ] = overlay
        # return Board.from_board(base, background=background)
        self.__init__(cog=self.cog, height=len(base), width=len(base[0]), background=background)
        self.board_history = [base]

    @property
    def cursor_pixel(self) -> typing.Any:
        return self.board[self.cursor_row, self.cursor_col]

    @cursor_pixel.setter
    def cursor_pixel(self, value: str) -> None:
        if not isinstance(value, str):
            raise TypeError("Value must be a string.")
        self.board[self.cursor_row, self.cursor_col] = value

    def get_pixel(
        self,
        row: typing.Optional[int] = None,
        col: typing.Optional[int] = None,
    ) -> typing.Any:
        row = row if row is not None else self.cursor_row
        col = col if col is not None else self.cursor_col
        return self.board[row, col]

    @classmethod
    def from_board(
        cls,
        cog: commands.Cog,
        board: np.ndarray,
        *,
        background: typing.Optional[str] = MAIN_COLORS[-1],
    ) -> typing_extensions.Self:
        height = len(board)
        width = len(board[0])
        board_obj = cls(cog=cog, height=height, width=width, background=background)
        board_obj.board_history = [board]
        return board_obj

    @classmethod
    def from_str(
        cls, string: str, *, background: typing.Optional[str] = None
    ) -> typing_extensions.Self:
        lines = string.split("\n")[2:]
        board = [line.split(PADDING)[-1].split("\u200b") for line in lines]
        board = cls.from_board(np.array(board, dtype="object"), background=background)
        board.clear_cursors()
        return board

    def clear(self) -> None:
        self.draw(self.background, coords=np.array(np.where(self.board != self.background)).T)
        self.clear_cursors()

    def draw(
        self,
        color: typing.Optional[typing.Union[str, discord.Emoji, int, Color]] = None,
        *,
        coords: typing.Optional[typing.List[typing.Tuple[int, int]]] = None,
    ) -> bool:
        color = color or self.cursor
        color_pixel = getattr(color, "id", color)
        coords = coords if coords is not None else self.cursor_coords

        cursor_matches = []
        for row, col in coords:
            if self.board[row, col] == color_pixel:
                cursor_matches.append(True)
            else:
                cursor_matches.append(False)
        if all(cursor_matches):
            return False

        self.board_history = self.board_history[: self.board_index + 1]
        self.board = self.board.copy()
        for row, col in coords:
            self.board[row, col] = color_pixel
        return True

    def clear_cursors(self, *, empty: typing.Optional[bool] = False) -> None:
        self.cursor_coords = [(self.cursor_row, self.cursor_col)] if empty is False else []

    def move_cursor(
        self,
        row_move: typing.Optional[int] = 0,
        col_move: typing.Optional[int] = 0,
        select: typing.Optional[bool] = False,
    ) -> None:
        self.clear_cursors()
        self.cursor_row = (self.cursor_row + row_move) % (self.cursor_row_max + 1)
        self.cursor_col = (self.cursor_col + col_move) % (self.cursor_col_max + 1)
        if select is True:
            self.initial_col, self.initial_row = self.initial_coords
            self.final_coords = (self.cursor_row, self.cursor_col)
            self.final_row, self.final_col = self.final_coords
            self.cursor_coords = [
                (row, col)
                for col in range(
                    min(self.initial_col, self.final_col),
                    max(self.initial_col, self.final_col) + 1,
                )
                for row in range(
                    min(self.initial_row, self.final_row),
                    max(self.initial_row, self.final_row) + 1,
                )
            ]
        else:
            self.cursor_coords = [(self.cursor_row, self.cursor_col)]

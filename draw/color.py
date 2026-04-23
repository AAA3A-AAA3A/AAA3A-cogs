import asyncio
import io
import re
from functools import cached_property

import aiohttp
import discord
import typing_extensions
from PIL import Image

from redbot.core import commands

IMAGE_EXTENSION = "PNG"

CHANNEL = "[a-fA-F0-9]{2}"
HEX_REGEX = re.compile(
    rf"\b(?P<red>{CHANNEL})(?P<green>{CHANNEL})(?P<blue>{CHANNEL})(?P<alpha>{CHANNEL})?\b",
)


class Color:
    # RGB_A accepts RGB values and an optional Alpha value.
    def __init__(self, RGB_A: tuple[int, int, int, int | None]) -> None:
        self.RGBA: tuple[int, int, int, int] = RGB_A if len(RGB_A) == 4 else (*RGB_A, 255)
        self.RGB: tuple[int, int, int] = self.RGBA[:3]
        self.R, self.G, self.B, self.A = self.RGBA

        self.loop = asyncio.get_running_loop()

    @cached_property
    def hex(self) -> str:
        return "{:02x}{:02x}{:02x}{:02x}".format(*self.RGBA)

    def __str__(self) -> str:
        return f"#{self.hex}"

    async def get_name(self) -> str:
        async with (
            aiohttp.ClientSession() as session,
            session.get(
                "https://www.thecolorapi.com/id",
                params={"hex": self.hex[:-2]},
            ) as r,
        ):
            color_response = await r.json()
        return color_response.get("name", {}).get("value", "?")

    async def to_bytes(self) -> bytes:
        return await self.loop.run_in_executor(None, self._to_bytes)

    def _to_bytes(self) -> bytes:
        image = self._to_image()
        buffer = io.BytesIO()
        image.save(buffer, IMAGE_EXTENSION)
        buffer.seek(0)
        return buffer.getvalue()

    async def to_file(self) -> discord.File:
        return await self.loop.run_in_executor(None, self._to_file)

    def _to_file(self) -> discord.File:
        image_bytes = io.BytesIO(self._to_bytes())
        return discord.File(image_bytes, filename=f"{self.hex}.{IMAGE_EXTENSION.lower()}")

    async def to_image(self) -> Image.Image:
        return await self.loop.run_in_executor(None, self._to_image)

    def _to_image(self) -> Image.Image:
        # # If you pass in an emoji, it uses that as base
        # # Else it uses the base_emoji property which uses 🟪
        # base_emoji = self.base_emoji
        # data = np.array(base_emoji)
        # r, g, b, a = data.T
        # data[..., :-1][a != 0] = self.RGB
        # # Set the alpha relatively, to respect individual alpha values
        # alpha_percent = self.A / 255
        # data[..., -1] = alpha_percent * data[..., -1]
        # return Image.fromarray(data)
        return Image.new("RGBA", (100, 100), self.RGBA)

    async def to_emoji(self, guild: discord.Guild) -> discord.Emoji:
        return await guild.create_custom_emoji(name=self.hex, image=await self.to_bytes())

    @classmethod
    async def from_emoji(
        cls,
        cog: commands.Cog,
        emoji: str | discord.Emoji | discord.PartialEmoji,
    ) -> typing_extensions.Self:
        image = await cog.get_pixel(emoji)
        colors = [
            color
            for color in sorted(
                image.getcolors(image.size[0] * image.size[1]),
                key=lambda c: c[0],
                reverse=True,
            )
            if color[-1][-1] != 0
        ]
        return cls(colors[0][1])

    @classmethod
    async def from_attachment(
        cls,
        attachment: discord.Attachment,
        *,
        n_colors: int | None = 5,
    ) -> list[typing_extensions.Self]:
        image = Image.open(io.BytesIO(await attachment.read()))
        colors: tuple[int, tuple[int, int, int]] = [
            color
            for color in sorted(
                image.getcolors(image.size[0] * image.size[1]),
                key=lambda c: c[0],
                reverse=True,
            )
            if color[-1][-1] != 0
        ]
        return [cls(colors[min(len(colors), i)][-1]) for i in range(n_colors)]

    @classmethod
    def from_hex(cls, hex: str) -> typing_extensions.Self:
        if (match := HEX_REGEX.match(hex)) is None:
            raise ValueError("Invalid hex code provided.")
        RGBA = (
            int(match.group("red"), 16),
            int(match.group("green"), 16),
            int(match.group("blue"), 16),
            int(match.group("alpha") or "ff", 16),
        )
        return cls(RGBA)

    @classmethod
    def mix_colors(
        cls,
        colors: list[typing_extensions.Self | tuple[int, int, int, int]],
    ) -> typing_extensions.Self:
        colors = [color.RGBA if isinstance(color, Color) else color for color in colors]
        total_weight = len(colors)
        return cls(
            tuple(round(sum(color) / total_weight) for color in zip(*colors)),
        )

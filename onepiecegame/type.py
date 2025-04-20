from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import io
from dataclasses import dataclass

from cache import AsyncTTL
from PIL import Image, ImageFilter

_: Translator = Translator("OnePieceGame", __file__)


ARCS: typing.Dict[str, typing.Tuple[int, int]] = {
    "Romance Dawn": (1, 7),
    "Orange Town": (8, 21),
    "Syrup Village": (22, 41),
    "Baratie": (42, 68),
    "Arlong Park": (69, 95),
    "Loguetown": (96, 100),
    "Reverse Mountain": (101, 105),
    "Whisky Peak": (106, 114),
    "Little Garden": (115, 129),
    "Drum Island": (130, 154),
    "Arabasta": (155, 217),
    "Jaya": (218, 236),
    "Skypiea": (237, 302),
    "Long Ring Long Land": (303, 321),
    "Water 7": (322, 374),
    "Enies Lobby": (375, 430),
    "Post-Enies Lobby": (431, 441),
    "Thriller Bark": (442, 489),
    "Sabaody Archipelago": (490, 513),
    "Amazon Lily": (514, 524),
    "Impel Down": (525, 549),
    "Marineford": (550, 580),
    "Post-War": (581, 597),
    "Return to Sabaody": (598, 602),
    "Fish-Man Island": (603, 653),
    "Punk Hazard": (654, 699),
    "Dressrosa": (700, 801),
    "Zou": (802, 824),
    "Whole Cake Island": (825, 902),
    "Levely": (903, 908),
    "Wano Country": (909, 1057),
    # "Egghead": (1058, None),
}


@dataclass
class Character:
    cog: commands.Cog

    name: str
    aliases: typing.List[str]
    epithets: typing.List[str]

    gender: str
    affiliation: str
    origin: str

    bounty: typing.Optional[int]
    devil_fruit: typing.Optional[typing.Dict[typing.Literal["name", "translated_name", "type"], str]]
    haki: typing.List[str]

    status: str
    height: int
    blood_type: str

    first_apparition: typing.Dict[typing.Literal["manga", "anime"], int]

    def __hash__(self) -> int:
        return hash(self.name)

    @property
    def bounty_display(self) -> str:
        value = self.bounty
        unities = ["", "K", "M", "B"]
        index = 0
        while value > 1000 and index < len(unities) - 1:
            value /= 1000
            index += 1
        return f"{int(value)}{unities[index]} berries"

    @property
    def first_arc(self) -> str:
        return next(
            arc
            for arc, (start, end) in ARCS.items()
            if start <= self.first_apparition["manga"]
            and (end is None or self.first_apparition["manga"] <= end)
        )

    @AsyncTTL(time_to_live=60 * 30, maxsize=1024)
    async def get_image(self) -> bytes:
        with open(self.cog.image_path / f"{self.name.replace(' ', '_')}.png", "rb") as f:
            return f.read()

    async def get_image_file(self) -> discord.File:
        return discord.File(
            io.BytesIO(await self.get_image()),
            filename=f"character.png",
        )

    @AsyncTTL(time_to_live=60 * 30, maxsize=1024)
    async def get_wanted_poster(
        self, blurry_level: int = 0, show_colors: bool = False
    ) -> discord.File:
        if self.name != "Brook":
            img = Image.open(io.BytesIO(self.cog.wanted_poster_template))
            img = img.convert("RGBA")
            image = Image.open(io.BytesIO(await self.get_image()))
            image = image.convert("RGBA")
            if blurry_level > 0:
                image = image.filter(ImageFilter.GaussianBlur(radius=blurry_level))
            if not show_colors:
                image = image.convert("L")
            image = image.resize((585, 440))
            img.paste(image, (60, 215, 645, 655))
        else:
            img = Image.open(io.BytesIO(self.cog.brook_wanted_poster))
            img = img.convert("RGBA")
            if blurry_level > 0:
                img = img.filter(ImageFilter.GaussianBlur(radius=blurry_level*2))
            if not show_colors:
                img = img.convert("L")
        img = img.resize((img.width * 3, img.height * 3))
        buffer = io.BytesIO()
        img.save(buffer, "png")
        buffer.seek(0)
        return buffer.read()

    async def get_wanted_poster_file(
        self, blurry_level: int = 0, show_colors: bool = False
    ) -> discord.File:
        return discord.File(
            io.BytesIO(await self.get_wanted_poster(blurry_level, show_colors)),
            filename="wanted_poster.png",
        )

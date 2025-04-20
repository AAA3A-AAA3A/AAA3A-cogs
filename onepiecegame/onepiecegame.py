from AAA3A_utils import Cog, Menu  # isort:skip
from redbot.core import commands, Config, app_commands  # isort:skip
from redbot.core.bot import Red  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import io
import json

from fuzzywuzzy import process
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from redbot.core.data_manager import bundled_data_path
from redbot.core.utils.chat_formatting import box

from .type import ARCS, Character
from .view import OnePieceGameView

# Credits:
# General repo credits.
# Thanks to OnePieceDle for some of the characters' data!

_: Translator = Translator("OnePieceGame", __file__)


CLASSIC_MODE_KEYS: typing.List[str] = [
    "gender",
    "affiliation",
    "devil_fruit",
    "haki",
    "bounty",
    "height",
    "origin",
    "first_arc",
]


@cog_i18n(_)
class OnePieceGame(Cog):
    """Guess One Piece characters from their characteristics, their devil fruit, or their blury wanted poster!"""

    def __init__(self, bot: Red) -> None:
        super().__init__(bot=bot)

        self.config: Config = Config.get_conf(
            self,
            identifier=205192943327321000143939875896557571750,
            force_registration=True,
        )
        self.config.register_member(
            wins=0,
            games=0,
        )

        self.characters: typing.List[Character] = []
        self.character_autocomplete_data: typing.List[str] = []
        self.image_path: Path = None
        self.font: ImageFont.FreeTypeFont = None
        self.wanted_poster_template: bytes = None
        self.brook_wanted_poster: bytes = None

    async def cog_load(self) -> None:
        await super().cog_load()
        data_path = bundled_data_path(self)
        with open(data_path / "characters.json", mode="rt", encoding="utf-8") as f:
            for character_data in json.loads(f.read()):
                self.characters.append(Character(self, **character_data))
                self.character_autocomplete_data.append(character_data["name"])
        self.image_path = data_path / "images"
        self.font = ImageFont.truetype(str(data_path / "ClearSans-Bold.ttf"), 65)
        with open(data_path / "wanted_poster_template.png", mode="rb") as f:
            self.wanted_poster_template = f.read()
        with open(data_path / "brook_wanted_poster.png", mode="rb") as f:
            self.brook_wanted_poster = f.read()

    @property
    def games(self) -> typing.Dict[discord.Message, OnePieceGameView]:
        return self.views

    async def get_character_by_name(self, name: str) -> typing.Optional[Character]:
        if (
            character_name := process.extractOne(
                name,
                [character.name for character in self.characters]
                + [
                    character.name.split(" ")[-1]
                    for character in self.characters
                    if " " in character.name
                ]
                + [alias for character in self.characters for alias in character.aliases]
                + [epithet for character in self.characters for epithet in character.epithets],
                scorer=process.fuzz.ratio,
                score_cutoff=80,
            )
        ) is None:
            return None
        character_name = character_name[0]
        return next(
            (
                character
                for character in self.characters
                if character_name == character.name
                or character_name == character.name.split(" ")[-1]
                or character_name in character.aliases
                or character_name in character.epithets
            ),
            None,
        )

    async def generate_image(
        self,
        mode: typing.Literal["classic", "devil_fruit", "wanted_poster"],
        character: Character,
        attempts: typing.List[Character] = [],
    ) -> discord.File:
        length, width, height, between, between_characters, border, header = (
            len(attempts),
            400,
            450,
            10,
            20,
            5,
            150,
        )
        mask = Image.new("L", (width, height), 0)
        d = ImageDraw.Draw(mask)
        d.rounded_rectangle(
            (0, 0, width, height),
            radius=20,
            fill=255,
        )

        if mode == "classic":
            image = Image.new(
                "RGBA",
                (
                    2 * border + 9 * width + 8 * between,
                    2 * border + header + length * height + (length - 1) * between_characters,
                ),
                (0, 0, 0, 0),
            )
            draw = ImageDraw.Draw(image)
            for j, key in enumerate(CLASSIC_MODE_KEYS):
                key_title = key.replace("_", " ").title()
                text_width, text_height = self.font.getbbox(key_title)[2:]
                draw.text(
                    (
                        (j + 1) * (width + between) + border + width // 2 - text_width // 2,
                        header // 2 - text_height // 2,
                    ),
                    key_title,
                    font=self.font,
                    fill=(255, 255, 255, 255),
                )
            for i, attempt in enumerate(attempts):
                img = Image.open(io.BytesIO(await attempt.get_image()))
                img = img.resize((width, height))
                image.paste(
                    img,
                    (
                        border,
                        header + i * (height + between_characters) + border,
                        border + width,
                        header + i * (height + between_characters) + border + height,
                    ),
                    mask=mask,
                )

                for j, key in enumerate(CLASSIC_MODE_KEYS):
                    if key == "devil_fruit":
                        success = (
                            attempt.devil_fruit is None and character.devil_fruit is None
                        ) or (
                            attempt.devil_fruit is not None
                            and character.devil_fruit is not None
                            and attempt.devil_fruit["type"] == character.devil_fruit["type"]
                        )
                        value = attempt.devil_fruit["type"] if attempt.devil_fruit else None
                    elif key == "haki":
                        success = set(attempt.haki) == set(character.haki)
                        value = "\n".join(attempt.haki) if attempt.haki else None
                    else:
                        success = getattr(attempt, key) == getattr(character, key)
                        value = attr if (attr := getattr(attempt, key)) is not None else None

                    draw.rounded_rectangle(
                        (
                            (j + 1) * (width + between) + border,
                            header + i * (height + between_characters) + border,
                            (j + 1) * (width + between) + border + width,
                            header + i * (height + between_characters) + border + height,
                        ),
                        fill=((60, 170, 95, 255) if success else (190, 50, 45, 255)),
                        outline=((40, 140, 75, 255) if success else (230, 50, 50, 255)),
                        radius=20,
                        width=5,
                    )

                    if isinstance(value, int) or key == "first_arc":
                        if not success:
                            if (
                                (getattr(character, key) or 0) > getattr(attempt, key)
                                if key != "first_arc"
                                else list(ARCS).index(character.first_arc)
                                > list(ARCS).index(attempt.first_arc)
                            ):
                                draw.polygon(
                                    [
                                        (
                                            (j + 1) * (width + between) + border + width // 2,
                                            header
                                            + i * (height + between_characters)
                                            + border
                                            + height // 2
                                            - 200,
                                        ),
                                        (
                                            (j + 1) * (width + between)
                                            + border
                                            + width // 2
                                            - 100,
                                            header
                                            + i * (height + between_characters)
                                            + border
                                            + height // 2
                                            + 200,
                                        ),
                                        (
                                            (j + 1) * (width + between)
                                            + border
                                            + width // 2
                                            + 100,
                                            header
                                            + i * (height + between_characters)
                                            + border
                                            + height // 2
                                            + 200,
                                        ),
                                    ],
                                    fill=(130, 30, 30, 255),
                                )
                            else:
                                draw.polygon(
                                    [
                                        (
                                            (j + 1) * (width + between) + border + width // 2,
                                            header
                                            + i * (height + between_characters)
                                            + border
                                            + height // 2
                                            + 200,
                                        ),
                                        (
                                            (j + 1) * (width + between)
                                            + border
                                            + width // 2
                                            - 100,
                                            header
                                            + i * (height + between_characters)
                                            + border
                                            + height // 2
                                            - 200,
                                        ),
                                        (
                                            (j + 1) * (width + between)
                                            + border
                                            + width // 2
                                            + 100,
                                            header
                                            + i * (height + between_characters)
                                            + border
                                            + height // 2
                                            - 200,
                                        ),
                                    ],
                                    fill=(130, 30, 30, 255),
                                )
                        if key == "bounty":
                            value = attempt.bounty_display
                        elif key == "height":
                            if value > 100:
                                value = f"{int(value / 100)}m{value % 100}"
                            else:
                                value = f"{value}cm"

                    if value is not None:
                        max_width = width - 20
                        words = value.split()
                        lines = []
                        current_line = words[0]
                        for word in words[1:]:
                            test_line = f"{current_line} {word}"
                            text_width = self.font.getbbox(test_line)[2]
                            if text_width <= max_width:
                                current_line = test_line
                            else:
                                lines.append(current_line)
                                current_line = word
                        lines.append(current_line)
                        total_text_height = len(lines) * self.font.size
                        y_offset = (
                            header
                            + i * (height + between_characters)
                            + border
                            + height // 2
                            - total_text_height // 2
                            - 10
                        )
                        for line in lines:
                            text_width, text_height = self.font.getbbox(line)[2:]
                            draw.text(
                                (
                                    (j + 1) * (width + between)
                                    + border
                                    + width // 2
                                    - text_width // 2,
                                    y_offset,
                                ),
                                line,
                                font=self.font,
                                fill=(255, 255, 255, 255),
                            )
                            y_offset += text_height
                    else:
                        draw.line(
                            (
                                (j + 1) * (width + between) + border + 50,
                                header + i * (height + between_characters) + border + 50,
                                (j + 1) * (width + between) + border + width - 50,
                                header + i * (height + between_characters) + border + height - 50,
                            ),
                            fill=(255, 255, 255, 255),
                            width=15,
                        )
                        draw.line(
                            (
                                (j + 1) * (width + between) + border + 50,
                                header + i * (height + between_characters) + border + height - 50,
                                (j + 1) * (width + between) + border + width - 50,
                                header + i * (height + between_characters) + border + 50,
                            ),
                            fill=(255, 255, 255, 255),
                            width=15,
                        )

        else:
            boxes_per_line = 5
            lines = (length + boxes_per_line - 1) // boxes_per_line
            image = Image.new(
                "RGBA",
                (
                    2 * border + boxes_per_line * width + (boxes_per_line - 1) * between,
                    2 * border + lines * height + (lines - 1) * between,
                ),
                (0, 0, 0, 0),
            )
            draw = ImageDraw.Draw(image)
            for i, attempt in enumerate(attempts):
                img = Image.open(io.BytesIO(await attempt.get_image()))
                img = img.resize((width, height))
                line = i // boxes_per_line
                col = i % boxes_per_line
                image.paste(
                    img,
                    (
                        col * (width + between) + border,
                        line * (height + between) + border,
                        col * (width + between) + border + width,
                        line * (height + between) + border + height,
                    ),
                    mask=mask,
                )

        buffer = io.BytesIO()
        image.save(buffer, "png")
        buffer.seek(0)
        return discord.File(buffer, filename="tries.png")

    async def get_kwargs(
        self,
        ctx: commands.Context,
        mode: typing.Literal["classic", "devil_fruit", "wanted_poster"],
        character: Character,
        attempts: typing.List[Character] = [],
        each_attempt_decreases_blurry_level: bool = True,
        show_colors: bool = False,
    ) -> typing.Dict[
        typing.Literal["embeds", "files", "allowed_mentions"],
        typing.Union[discord.Embed, discord.File, discord.AllowedMentions],
    ]:
        embeds: typing.List[discord.Embed] = [
            discord.Embed(
                title=_("One Piece Game - {mode}").format(
                    mode={
                        "classic": _("Classic mode"),
                        "devil_fruit": _("Devil Fruit mode"),
                        "wanted_poster": _("Wanted Poster mode"),
                    }[mode],
                ),
                description={
                    "classic": _(
                        "Guess the character from its characteristics! Make a guess to reveal more of the character."
                    ),
                    "devil_fruit": _("Guess the character from its devil fruit name!"),
                    "wanted_poster": _(
                        "Use the blurry wanted poster to guess the character! Each guess will reveal more of the poster."
                    ),
                }[mode],
                color=await ctx.embed_color(),
            ).set_author(
                name=ctx.author.display_name,
                icon_url=ctx.author.display_avatar,
            ),
        ]
        files = []
        if mode == "devil_fruit":
            embeds[-1].add_field(
                name="\u200b",
                value=box(f"« {character.devil_fruit['name']} »"),
            )
        elif mode == "wanted_poster":
            embeds[-1].set_image(
                url="attachment://wanted_poster.png",
            )
            files.append(
                await character.get_wanted_poster_file(
                    blurry_level=max(
                        8 - (len(attempts) if each_attempt_decreases_blurry_level else 0), 0
                    ),
                    show_colors=show_colors,
                )
            )
        if attempts:
            embeds.append(
                discord.Embed(
                    color=await ctx.embed_color(),
                ).set_image(url="attachment://tries.png")
            )
            files.append(
                await self.generate_image(mode, character, attempts),
            )
        if character in attempts:
            embeds.append(
                discord.Embed(
                    title=_("You guessed it!"),
                    description=_("The character was: **{character.name}**.").format(
                        character=character
                    ),
                    color=await ctx.embed_color(),
                ).set_image(url="attachment://character.png")
            )
            files.append(
                await character.get_image_file(),
            )
        embeds[-1].set_footer(
            text=ctx.guild.name,
            icon_url=ctx.guild.icon,
        )
        embeds[-1].timestamp = ctx.message.created_at
        return {
            "embeds": embeds,
            "files": files,
            "allowed_mentions": discord.AllowedMentions(replied_user=False),
        }

    def get_hints(
        self,
        mode: typing.Literal["classic", "devil_fruit", "wanted_poster"],
        character: Character,
    ) -> typing.Dict[str, typing.Dict[typing.Literal["tries", "value"], typing.Union[int, str]]]:
        if mode == "classic":
            return {
                _("First Apparition hint"): {
                    "tries": 5,
                    "value": _("Chapter {manga} / Episode {anime}").format(
                        manga=character.first_apparition["manga"],
                        anime=character.first_apparition["anime"],
                    ),
                },
                _("Devil Fruit hint"): {
                    "tries": 8,
                    "value": character.devil_fruit["name"]
                    if character.devil_fruit is not None
                    else _("Unknown"),
                },
            }
        elif mode == "devil_fruit":
            return {
                _("Type hint"): {
                    "tries": 5,
                    "value": character.devil_fruit["type"],
                },
                _("Translation hint"): {
                    "tries": 8,
                    "value": f">>> {character.devil_fruit['translated_name']}",
                },
            }
        elif mode == "wanted_poster":
            return {
                _("Bounty hint"): {
                    "tries": 10,
                    "value": character.bounty_display if character.bounty is not None else "❌",
                },
            }

    @commands.max_concurrency(1, commands.BucketType.member)
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True, attach_files=True)
    @commands.hybrid_group(aliases=["onepiecegame", "opg"])
    async def onepiece(self, ctx: commands.Context) -> None:
        """Guess One Piece characters from their characteristics, their devil fruit, or their blury wanted poster."""
        pass

    @onepiece.command()
    async def classic(self, ctx: commands.Context) -> None:
        """Play the **Classic mode** of the game: guess the character from its characteristics."""
        await OnePieceGameView(self, mode="classic").start(ctx)

    @onepiece.command(aliases=["devil", "fruit"])
    async def devilfruit(self, ctx: commands.Context) -> None:
        """Play the **Devil Fruit mode** of the game: guess the character from its devil fruit."""
        await OnePieceGameView(self, mode="devil_fruit").start(ctx)

    @onepiece.command(aliases=["wanted", "poster"])
    async def wantedposter(self, ctx: commands.Context) -> None:
        """Play the **Wanted Poster** mode of the game: guess the character from its blurry wanted poster."""
        await OnePieceGameView(self, mode="wanted_poster").start(ctx)

    async def character_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> typing.List[app_commands.Choice[str]]:
        """Autocomplete a character name."""
        if not current:
            return [
                app_commands.Choice(name=character_name, value=character_name)
                for character_name in self.character_autocomplete_data[:25]
            ]
        lowered_current = current.lower()
        return [
            app_commands.Choice(name=character_name, value=character_name)
            for character_name in self.character_autocomplete_data
            if any(
                part.startswith(lowered_current)
                for part in character_name.lower().split(" ")
            )
        ][:25]

    @onepiece.command()
    @app_commands.describe(name="The name of the character to guess.")
    @app_commands.autocomplete(name=character_autocomplete)
    async def autocomplete(self, ctx: commands.Context, *, name: str) -> None:
        """Autocomplete a character name."""
        if (character := await self.get_character_by_name(name)) is None:
            raise commands.UserFeedbackCheckFailure(
                _("This character does not exist or is not supported by the game."),
            )
        await ctx.send(character.name)
        ctx.message.content = character.name
        ctx.bot.dispatch("message_without_command", ctx.message)

    @onepiece.command(aliases=["chronology"])
    async def arcs(self, ctx: commands.Context) -> None:
        """Display the list of arcs in the game."""
        embed: discord.Embed = discord.Embed(
            title=_("Arcs"),
            description=_("The following arcs are available in the game:"),
            color=await ctx.embed_color(),
        )
        embeds = [embed]
        for i, (arc, (start, end)) in enumerate(ARCS.items(), start=1):
            if len(embed.fields) == 24:
                embed: discord.Embed = discord.Embed(color=embed.color)
                embeds.append(embed)
            embed.add_field(
                name=f"{i}. {arc}",
                value=_(
                    "Chapters **{start}** to **{end}**"
                ).format(start=start, end=end if end is not None else _("ongoing")),
                inline=True
            )
        await Menu(pages=[{"embeds": embeds}]).start(ctx)

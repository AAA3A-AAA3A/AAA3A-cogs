from AAA3A_utils import Cog  # isort:skip
from redbot.core import commands, Config  # isort:skip
from redbot.core.bot import Red  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

from redbot.core.data_manager import bundled_data_path

import io
from collections import defaultdict
from PIL import Image, ImageDraw, ImageFont

from .view import Lang, WordleGameView

# Credits:
# General repo credits.

_: Translator = Translator("WordleGame", __file__)


@cog_i18n(_)
class WordleGame(Cog):
    """Play a match of Wordle game, in multiple languages and lengths!"""

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
            guess_distribution=[0] * 10,
        )

        self.words: typing.Dict[str, typing.Dict[int, typing.List[str]]] = defaultdict(lambda: defaultdict(list))
        self.dictionaries: typing.Dict[str, typing.Dict[int, typing.List[str]]] = defaultdict(lambda: defaultdict(list))
        self.font: ImageFont.FreeTypeFont = None
        self.games_in_progress: typing.List[discord.Member] = []

    async def cog_load(self) -> None:
        await super().cog_load()
        data_path = bundled_data_path(self)
        for lang in Lang:
            for dirname in ("words", "dictionaries"):
                with (data_path / dirname / f"{lang.value}.txt").open("r", encoding="utf-8") as file:
                    for word in file.read().split("\n"):
                        getattr(self, dirname)[lang.value][len(word)].append(word)
        self.font = ImageFont.truetype(str(data_path / "ClearSans-Bold.ttf"), 80)

    @property
    def games(self) -> typing.Dict[discord.Message, WordleGameView]:
        return self.views

    async def generate_image(
        self,
        word: str,
        attempts: typing.List[str] = [],
        max_attempts: int = 6,
    ) -> discord.File:
        length, size, between, border = len(word), 70, 10, 5
        image = Image.new(
            "RGB",
            (
                length * size + (length + 1) * between + 2 * border,
                max_attempts * size + (max_attempts + 1) * between + 2 * border
            ),
            (255, 255, 255),
        )
        draw = ImageDraw.Draw(image)
        for i, attempt in enumerate(attempts):
            for j in range(length):
                letter = attempt[j]
                if letter == word[j]:
                    color = (106, 170, 100)  # Green
                elif any(letter == word[k] and attempt[k] != word[k] for k in range(length)):
                    color = (202, 180, 86)  # Yellow
                else:
                    color = (120, 124, 126)  # Grey
                draw.rectangle(
                    [
                        (border + (j + 1) * between + j * size, border + (i + 1) * between + i * size),
                        (border + (j + 1) * between + (j + 1) * size, border + (i + 1) * between + (i + 1) * size),
                    ],
                    fill=color,
                )
                s = self.font.getlength(letter.upper())
                draw.text(
                    (
                        border + (j + 1) * between + j * size + size // 2 - s // 2,
                        border + (i + 1) * between + i * size - size * 0.36,
                    ),
                    letter.upper(),
                    font=self.font,
                    fill=(255, 255, 255),
                )
        for i in range(max_attempts - len(attempts)):
            for j in range(length):
                draw.rectangle(
                    [
                        (border + (j + 1) * between + j * size, border + (len(attempts) + i + 1) * between + (len(attempts) + i) * size),
                        (border + (j + 1) * between + (j + 1) * size, border + (len(attempts) + i + 1) * between + (len(attempts) + i + 1) * size),
                    ],
                    outline=(211, 214, 218),
                    width=3,
                )
        buffer = io.BytesIO()
        image.save(buffer, "png")
        buffer.seek(0)
        return discord.File(buffer, filename="wordle.png")

    async def get_kwargs(
        self,
        ctx: commands.Context,
        lang: Lang, word: str,
        attempts: typing.List[str] = [],
        max_attempts: int = 6,
    ) -> typing.Dict[typing.Literal["embed", "file", "allowed_mentions"], typing.Union[discord.Embed, discord.File, discord.AllowedMentions]]:
        embed: discord.Embed = discord.Embed(
            title=_("{flag} Wordle Game - {attempts}/{max_attempts} attempts").format(
                flag=f":flag_{'gb' if lang is Lang.ENGLISH else lang.value}:",
                attempts=len(attempts),
                max_attempts=max_attempts,
            ),
            color=await ctx.embed_color(),
            timestamp=ctx.message.created_at,
        )
        embed.set_author(
            name=ctx.author.display_name,
            icon_url=ctx.author.display_avatar,
        )
        has_won, has_lost = word in attempts, len(attempts) == 6
        if has_won or has_lost:
            embed.add_field(
                name=_("You won!") if has_won else _("You lost!"),
                value=_("The word was: **{word}**.").format(word=word),
            )
        embed.set_footer(
            text=ctx.guild.name,
            icon_url=ctx.guild.icon,
        )
        file = await self.generate_image(word, attempts, max_attempts=max_attempts)
        embed.set_image(url="attachment://wordle.png")
        return {
            "embed": embed,
            "file": file,
            "allowed_mentions": discord.AllowedMentions(replied_user=False),
        }

    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True, attach_files=True)
    @commands.hybrid_command(aliases=["wordlegame"])
    async def wordle(
        self,
        ctx: commands.Context,
        lang: typing.Optional[Lang] = Lang.ENGLISH,
        length: typing.Optional[commands.Range[int, 4, 11]] = 5,
        max_attempts: typing.Optional[commands.Range[int, 5, 10]] = 6,
    ) -> None:
        """Play a match of Wordle game.

        You can find the rules of the game by clicking on the button after starting the game.
        Available languages: `en`, `fr`, `de`, `es`, `it`, `pt`, `nl`, `cs`, `el`, `id`, `ie`, `ph`, `pl`, `ua`, `ru`, `sv` and `tr`.
        """
        if ctx.author in self.games_in_progress:
            raise commands.UserFeedbackCheckFailure(_("You are already playing a match of Wordle game."))
        self.games_in_progress.append(ctx.author)
        has_won, attempts = await WordleGameView(
            self,
            lang=lang,
            length=length,
            max_attempts=max_attempts,
        ).start(ctx)
        data = await self.config.member(ctx.author).all()
        data["games"] += 1
        if has_won:
            data["wins"] += 1
            data["guess_distribution"][len(attempts) - 1] += 1
        await self.config.member(ctx.author).set(data)
        self.games_in_progress.remove(ctx.author)

    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    @commands.command()
    async def wordlestats(self, ctx: commands.Context) -> None:
        """Show the stats for the Wordle game."""
        data = await self.config.member(ctx.author).all()
        embed = discord.Embed(
            title=_("Wordle Game Stats"),
            description=_(">>> **Games played**: {games}\n**Wins**: {wins}\n**Win rate:** {win_rate:.2%}").format(
                games=data["games"],
                wins=data["wins"],
                win_rate=data["wins"] / data["games"] if data["games"] else 0,
            ),
            color=await ctx.embed_color(),
            timestamp=ctx.message.created_at,
        )
        embed.set_author(
            name=ctx.author.display_name,
            icon_url=ctx.author.display_avatar,
        )
        embed.set_thumbnail(url=ctx.author.display_avatar)
        if data["games"]:
            embed.add_field(
                name=_("Guess distribution:"),
                value="\n".join(
                    [
                        _("**•** **{count}** guess{es} with {i} attempts").format(count=count, i=i+1, es="es" if count > 1 else "")
                        for i, count in enumerate(data["guess_distribution"], start=1)
                        if count > 0
                    ]
                ),
            )
        embed.set_footer(
            text=ctx.guild.name,
            icon_url=ctx.guild.icon,
        )
        await ctx.send(embed=embed)

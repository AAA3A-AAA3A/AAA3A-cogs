from AAA3A_utils import Cog, Menu  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.bot import Red  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

from redbot.core.data_manager import bundled_data_path

import aiohttp
import io
import json
import random

# Credits:
# General repo credits.

_: Translator = Translator("EmojiMixup", __file__)


class UnicodeEmojiConverter(commands.Converter):
    async def convert(
        self, ctx: commands.Context, argument: str
    ) -> typing.Union[str, discord.Emoji]:
        cog = ctx.bot.get_cog("EmojiMixup")
        if argument == "random":
            return random.choice(cog.emojis)
        if argument not in cog.emojis:
            raise commands.BadArgument(_("That's not a valid Unicode emoji or it isn't supported!"))
        return argument


@cog_i18n(_)
class EmojiMixup(Cog):
    """Mix and match emojis to create new ones, from Google's Emoji Kitchen!"""

    def __init__(self, bot: Red) -> None:
        super().__init__(bot)
        self._session: aiohttp.ClientSession = None
        self.emojis: typing.List[str] = []
        self.mixup_emojis: typing.Dict[typing.Tuple[str, str], str] = {}

    async def cog_load(self) -> None:
        await super().cog_load()
        self._session: aiohttp.ClientSession = aiohttp.ClientSession()
        with open(bundled_data_path(self) / "emojis.txt", encoding="utf-8") as f:
            self.emojis = list(f.read().strip().splitlines())
        with open(bundled_data_path(self) / "mixup_emojis.json", encoding="utf-8") as f:
            self.mixup_emojis = json.load(f)

    async def cog_unload(self) -> None:
        if self._session is not None:
            await self._session.close()
        await super().cog_unload()

    def get_emoji_codepoints(self, emoji: str) -> typing.List[str]:
        return [hex(ord(char))[2:].lower() for char in emoji]

    def get_emoji_url(self, emoji: str) -> str:
        return f"https://fonts.gstatic.com/s/e/notoemoji/14.0/{'_'.join(self.get_emoji_codepoints(emoji))}/512.png"

    def get_mixup_emoji_url(self, emoji1: str, emoji2: str) -> str:
        # date = "..."
        # code_point_1, code_point_2 = "_".join(self.get_emoji_codepoints(emoji1)), "_".join(self.get_emoji_codepoints(emoji2))
        # return f"https://www.gstatic.com/android/keyboard/emojikitchen/{date}/u{code_point_1}/u{code_point_1}_u{code_point_2}.png"
        key = "_".join(sorted([emoji1, emoji2]))
        if key not in self.mixup_emojis:
            raise commands.UserFeedbackCheckFailure(_("Sorry, this mixup isn't supported!"))
        return f"https://www.gstatic.com/android/keyboard/emojikitchen/{self.mixup_emojis[key]}"

    async def get_image(self, url: str) -> discord.File:
        async with self._session.get(url) as r:
            return discord.File(
                io.BytesIO(await r.read()),
                filename="emoji.png",
            )

    @commands.bot_has_permissions(embed_links=True, attach_files=True)
    @commands.hybrid_command(aliases=["emixup"])
    async def emojimixup(
        self,
        ctx: commands.Context,
        emoji1: UnicodeEmojiConverter,
        emoji2: UnicodeEmojiConverter = None,
    ) -> None:
        """Mix two emojis together to create a new one! Use `random` for a random emoji."""
        if emoji2 is None:
            embed: discord.Embed = discord.Embed(
                title=emoji1,
                color=await ctx.embed_color(),
            )
            embed.set_image(url="attachment://emoji.png")
            embed.set_footer(text=_("Provided by Google."))
            file: discord.File = await self.get_image(self.get_emoji_url(emoji1))
            await Menu(pages=[{"embed": embed, "file": file}]).start(ctx)
            return
        embed: discord.Embed = discord.Embed(
            title=f"{emoji1} + {emoji2} =",
            color=await ctx.embed_color(),
        )
        embed.set_image(url=f"attachment://emoji.png")
        embed.set_footer(text=_("Provided by Emoji Kitchen from Google."))
        file: discord.File = await self.get_image(self.get_mixup_emoji_url(emoji1, emoji2))
        await Menu(pages=[{"embed": embed, "file": file}]).start(ctx)

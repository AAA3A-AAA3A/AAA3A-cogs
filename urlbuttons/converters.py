import re

import discord
import validators

from redbot.core import commands
from redbot.core.i18n import Translator

try:
    from emoji import EMOJI_DATA  # emoji>=2.0.0
except ImportError:
    from emoji import UNICODE_EMOJI_ENGLISH as EMOJI_DATA  # emoji<2.0.0

_: Translator = Translator("UrlButtons", __file__)


class UrlConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> str:
        if argument.startswith("<") and argument.endswith(">"):
            argument = argument[1:-1]
        try:
            validators.url(argument, public=True)
        except validators.ValidationFailure:
            raise commands.BadArgument(_("It's not a valid public URL."))
        return argument


class Emoji(commands.EmojiConverter):
    async def convert(
        self,
        ctx: commands.Context,
        argument: str,
    ) -> str | discord.Emoji:
        # argument = argument.strip("\N{VARIATION SELECTOR-16}")
        if argument in EMOJI_DATA:
            return argument
        if argument in {
            "🇦",
            "🇧",
            "🇨",
            "🇩",
            "🇪",
            "🇫",
            "🇬",
            "🇭",
            "🇮",
            "🇯",
            "🇰",
            "🇱",
            "🇲",
            "🇳",
            "🇴",
            "🇵",
            "🇶",
            "🇷",
            "🇸",
            "🇹",
            "🇺",
            "🇻",
            "🇼",
            "🇽",
            "🇾",
            "🇿",
        }:
            return argument
        return await super().convert(ctx, argument=argument)


class EmojiUrlConverter(commands.Converter):
    async def convert(
        self,
        ctx: commands.Context,
        argument: str,
    ) -> tuple[str, discord.PartialEmoji | str]:
        arg_split = re.split(r"[;,|\-]", argument)
        try:
            emoji, url = arg_split
        except ValueError:
            raise commands.BadArgument(
                _(
                    "Emoji Url must be an emoji followed by a url separated by either `;`, `,`, `|`, or `-`.",
                ),
            )
        emoji = await Emoji().convert(ctx, emoji.strip())
        url = await UrlConverter().convert(ctx, argument=url)
        return emoji, url

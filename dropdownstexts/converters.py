import re

import discord

from redbot.core import commands
from redbot.core.i18n import Translator

try:
    from emoji import EMOJI_DATA  # emoji>=2.0.0
except ImportError:
    from emoji import UNICODE_EMOJI_ENGLISH as EMOJI_DATA  # emoji<2.0.0

_: Translator = Translator("RolesButtons", __file__)


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


class EmojiLabelTextConverter(commands.Converter):
    async def convert(
        self,
        ctx: commands.Context,
        argument: str,
    ) -> tuple[discord.Role, discord.PartialEmoji | str]:
        arg_split = re.split(r"[;,|\-]", argument)
        try:
            emoji, label, text_or_message = arg_split
        except ValueError:
            raise commands.BadArgument(
                _(
                    "Dropdown Text must be an `emoji`, followed by a `label` and a `text_or_message`, separated by either `;`, `,`, `|`, or `-`.",
                ),
            )
        emoji = await Emoji().convert(ctx, emoji.strip())
        return emoji, label, text_or_message

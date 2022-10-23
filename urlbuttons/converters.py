from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import re

try:
    from emoji import UNICODE_EMOJI_ENGLISH as EMOJI_DATA  # emoji<2.0.0
except ImportError:
    from emoji import EMOJI_DATA  # emoji>=2.0.0

_ = Translator("UrlButtons", __file__)


class Emoji(commands.EmojiConverter):
    async def convert(self, ctx: commands.Context, argument: str):
        if argument in EMOJI_DATA:
            return argument
        return await super().convert(ctx, argument)


class EmojiUrlConverter(discord.ext.commands.Converter):
    async def convert(
        self, ctx: commands.Context, argument: str
    ) -> typing.Tuple[str, typing.Union[discord.PartialEmoji, str]]:
        arg_split = re.split(r";|,|\||-", argument)
        try:
            emoji, url = arg_split
        except Exception:
            raise discord.ext.commands.BadArgument(
                _(
                    "Emoji Url must be an emoji followed by a url separated by either `;`, `,`, `|`, or `-`."
                ).format(**locals())
            )
        emoji = await Emoji().convert(ctx, emoji.strip())
        url = str(url)
        if url.startswith("<") and url.endswith(">"):
            url = url[1:-1]
        if not url.startswith("http"):
            raise discord.ext.commands.BadArgument(
                _("Url must start with `https` or `http`.").format(**locals())
            )
        return emoji, url

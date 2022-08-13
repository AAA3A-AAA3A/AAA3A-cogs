from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import re

_ = Translator("UrlButtons", __file__)

class EmojiUrlConverter(discord.ext.commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> typing.Tuple[str, typing.Union[discord.PartialEmoji, str]]:
        arg_split = re.split(r";|,|\||-", argument)
        try:
            emoji, url = arg_split
        except Exception:
            raise discord.ext.commands.BadArgument(_("Emoji Url must be an emoji followed by a url separated by either `;`, `,`, `|`, or `-`.").format(**locals()))
        try:
            emoji = await commands.PartialEmojiConverter().convert(ctx, emoji.strip())
        except commands.BadArgument:
            emoji = str(emoji)
        url = str(url)
        if not url.startswith("http"):
            raise discord.ext.commands.BadArgument(_("Url must start with `https` or `http`.").format(**locals()))
        return url, emoji
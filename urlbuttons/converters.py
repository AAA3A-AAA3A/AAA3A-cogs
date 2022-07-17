from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import re

_ = Translator("UrlButtons", __file__)

class UrlEmojiConverter(discord.ext.commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> typing.Tuple[str, typing.Union[discord.PartialEmoji, str]]:
        arg_split = re.split(r";|,|\||-", argument)
        try:
            url, emoji = arg_split
        except Exception:
            raise discord.ext.commands.BadArgument(_("Url Emoji must be a url followed by an emoji separated by either `;`, `,`, `|`, or `-`.").format(**locals()))
        url = str(url)
        if not url.startswith("http"):
            raise discord.ext.commands.BadArgument(_("Url must start with `https` or `http`.").format(**locals()))
        custom_emoji = None
        try:
            custom_emoji = await commands.PartialEmojiConverter().convert(ctx, emoji.strip())
        except commands.BadArgument:
            pass
        if not custom_emoji:
            custom_emoji = str(emoji)
        return url, custom_emoji
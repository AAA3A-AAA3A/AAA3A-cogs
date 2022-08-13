from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import re

_ = Translator("RolesButtons", __file__)

class EmojiLabelTextConverter(discord.ext.commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> typing.Tuple[discord.Role, typing.Union[discord.PartialEmoji, str]]:
        arg_split = re.split(r";|,|\||-", argument)
        try:
            emoji, label, text = arg_split
        except Exception:
            raise discord.ext.commands.BadArgument(_("Dropdown Text must be an emoji, followed by a label and a text, separated by either `;`, `,`, `|`, or `-`.").format(**locals()))
        return emoji, label, text
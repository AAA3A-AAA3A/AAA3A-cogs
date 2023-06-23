from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import re

try:
    from emoji import UNICODE_EMOJI_ENGLISH as EMOJI_DATA  # emoji<2.0.0
except ImportError:
    from emoji import EMOJI_DATA  # emoji>=2.0.0

_ = Translator("RolesButtons", __file__)


class Emoji(commands.EmojiConverter):
    async def convert(
        self, ctx: commands.Context, argument: str
    ) -> typing.Union[discord.PartialEmoji, str]:
        argument = argument.strip("\N{VARIATION SELECTOR-16}")
        if argument in EMOJI_DATA:
            return argument
        return await super().convert(ctx, argument=argument)


class EmojiLabelTextConverter(discord.ext.commands.Converter):
    async def convert(
        self, ctx: commands.Context, argument: str
    ) -> typing.Tuple[discord.Role, typing.Union[discord.PartialEmoji, str]]:
        arg_split = re.split(r";|\||-", argument)
        try:
            emoji, label, text = arg_split
        except Exception:
            # emoji = None
            # try:
            #     label, text = arg_split
            # except Exception:
            raise discord.ext.commands.BadArgument(
                _(
                    "Dropdown Text must be an emoji, followed by a label and a text, separated by either `;`, `,`, `|`, or `-`."
                )
            )
        # if emoji is not None:
        emoji = await Emoji().convert(ctx, emoji.strip())
        return emoji, label, text

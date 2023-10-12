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
    ) -> typing.Union[str, discord.Emoji]:
        # argument = argument.strip("\N{VARIATION SELECTOR-16}")
        if argument in EMOJI_DATA:
            return argument
        if argument in {
            "0",
            "1",
            "2",
            "3",
            "4",
            "5",
            "6",
            "7",
            "8",
            "9",
            "#",
            "*",
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


class RoleHierarchyConverter(commands.RoleConverter):
    """Similar to d.py's RoleConverter but only returns if we have already
    passed our hierarchy checks.
    """

    async def convert(self, ctx: commands.Context, argument: str) -> discord.Role:
        if not ctx.me.guild_permissions.manage_roles:
            raise commands.BadArgument("I require manage roles permission to use this command.")
        try:
            role = await commands.RoleConverter().convert(ctx, argument=argument)
        except commands.BadArgument:
            raise
        else:
            if getattr(role, "is_bot_managed", None) and role.is_bot_managed():
                raise commands.BadArgument(
                    _(
                        "The {role.mention} role is a bot integration role and cannot be assigned or removed."
                    ).format(role=role)
                )
            if getattr(role, "is_integration", None) and role.is_integration():
                raise commands.BadArgument(
                    _(
                        "The {role.mention} role is an integration role and cannot be assigned or removed."
                    ).format(role=role)
                )
            if getattr(role, "is_premium_subscriber", None) and role.is_premium_subscriber():
                raise commands.BadArgument(
                    _(
                        "The {role.mention} role is a premium subscriber role and can only be assigned or removed by Nitro boosting the server."
                    ).format(role=role)
                )
            if role >= ctx.me.top_role:
                raise commands.BadArgument(
                    _(
                        "The {role.mention} role is higher than my highest role in the discord hierarchy."
                    ).format(role=role)
                )
            if role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
                raise commands.BadArgument(
                    _(
                        "The {role.mention} role is higher than your highest role in the discord hierarchy."
                    ).format(role=role)
                )
        return role


class EmojiRoleConverter(commands.Converter):
    async def convert(
        self, ctx: commands.Context, argument: str
    ) -> typing.Tuple[discord.Role, typing.Union[discord.PartialEmoji, str]]:
        arg_split = re.split(r";|\||-", argument)
        try:
            emoji, role = arg_split
        except Exception:
            # emoji = None
            # role = arg_split[0]
            raise commands.BadArgument(
                _(
                    "Emoji Role must be an emoji followed by a role separated by either `;`, `,`, `|`, or `-`."
                )
            )
        # if emoji is not None:
        emoji = await Emoji().convert(ctx, emoji.strip())
        role = await RoleHierarchyConverter().convert(ctx, role.strip())
        return emoji, role

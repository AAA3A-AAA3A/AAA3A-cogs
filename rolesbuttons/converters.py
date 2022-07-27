from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import re

_ = Translator("RolesButtons", __file__)

class RoleHierarchyConverter(discord.ext.commands.RoleConverter):
    """Similar to d.py's RoleConverter but only returns if we have already
    passed our hierarchy checks.
    """

    async def convert(self, ctx: commands.Context, argument: str) -> discord.Role:
        if not ctx.me.guild_permissions.manage_roles:
            raise discord.ext.commands.BadArgument("I require manage roles permission to use this command.")
        try:
            role = await commands.RoleConverter().convert(ctx, argument)
        except commands.BadArgument:
            raise
        else:
            if getattr(role, "is_bot_managed", None) and role.is_bot_managed():
                raise discord.ext.commands.BadArgument(_("The {role.mention} role is a bot integration role and cannot be assigned or removed.").format(**locals()))
            if getattr(role, "is_integration", None) and role.is_integration():
                raise discord.ext.commands.BadArgument(_("The {role.mention} role is an integration role and cannot be assigned or removed.").format(**locals()))
            if getattr(role, "is_premium_subscriber", None) and role.is_premium_subscriber():
                raise discord.ext.commands.BadArgument(_("The {role.mention} role is a premium subscriber role and can only be assigned or removed by Nitro boosting the server.").format(**locals()))
            if role >= ctx.me.top_role:
                raise discord.ext.commands.BadArgument(_("The {role.mention} role is higher than my highest role in the discord hierarchy.").format(**locals()))
            if role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
                raise discord.ext.commands.BadArgument(_("The {role.mention} role is higher than your highest role in the discord hierarchy.").format(**locals()))
        return role

class EmojiRoleConverter(discord.ext.commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> typing.Tuple[discord.Role, typing.Union[discord.PartialEmoji, str]]:
        arg_split = re.split(r";|,|\||-", argument)
        try:
            emoji, role = arg_split
        except Exception:
            raise discord.ext.commands.BadArgument(_("Emoji Role must be an emoji followed by a role separated by either `;`, `,`, `|`, or `-`.").format(**locals()))
        try:
            emoji = await commands.PartialEmojiConverter().convert(ctx, emoji.strip())
        except commands.BadArgument:
            emoji = str(emoji)
            role = await RoleHierarchyConverter().convert(ctx, role.strip())
        return emoji, role
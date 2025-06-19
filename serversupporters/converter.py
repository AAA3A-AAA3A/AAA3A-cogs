from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

_: Translator = Translator("ServerSupporters", __file__)


DANGEROUS_PERMISSIONS: typing.List[str] = [
    "administrator",
    "manage_guild",
    "manage_roles",
    "manage_channels",
    "manage_webhooks",
    "manage_emojis_and_stickers",
    "manage_messages",
    "manage_threads",
    "moderate_members",
]


class RoleHierarchyConverter(commands.RoleConverter):
    """Similar to d.py's RoleConverter but only returns if we have already passed our hierarchy checks."""

    async def convert(self, ctx: commands.Context, argument: str) -> discord.Role:
        try:
            role = await super().convert(ctx, argument=argument)
        except commands.BadArgument:
            raise
        if not role.is_assignable():
            raise commands.BadArgument(_("This role isn't assignable."))
        if role >= ctx.me.top_role:
            raise commands.BadArgument(
                _("This role is higher than my highest role in the discord hierarchy.")
            )
        if role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
            raise commands.BadArgument(
                _("This role is higher than your highest role in the discord hierarchy.")
            )
        if any(getattr(role.permissions, permission, False) for permission in DANGEROUS_PERMISSIONS):
            raise commands.BadArgument(
                _("This role has dangerous permissions and should not be used in this context. Please choose a different role.")
            )
        return role

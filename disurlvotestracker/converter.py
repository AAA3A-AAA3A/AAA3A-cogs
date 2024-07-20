from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator  # isort:skip
import discord  # isort:skip

_ = Translator("DisurlVotesTracker", __file__)


class RoleHierarchyConverter(commands.RoleConverter):
    """Similar to d.py's RoleConverter but only returns if we have already passed our hierarchy checks."""

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

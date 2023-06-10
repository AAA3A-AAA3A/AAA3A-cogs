from AAA3A_utils import Cog, CogsUtils, Menu  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
from redbot.core.bot import Red  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

from redbot.core.utils.chat_formatting import box, pagify

def _(untranslated: str) -> str:  # `redgettext` will found these strings.
    return untranslated
ERROR_MESSAGE = _("I attempted to do something that Discord denied me permissions for. Your command failed to successfully complete.\n{error}")

_ = Translator("DiscordEdit", __file__)


class PositionConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> int:
        try:
            position = int(argument)
        except ValueError:
            raise commands.BadArgument(_("The position must be an integer."))
        max_guild_roles_position = len(ctx.guild.roles)
        if position <= 0 or position >= max_guild_roles_position + 1:
            raise commands.BadArgument(
                _(
                    "The indicated position must be between 1 and {max_guild_roles_position}."
                ).format(max_guild_roles_position=max_guild_roles_position)
            )
        _list = list(range(max_guild_roles_position - 1))
        _list.reverse()
        position = _list[position - 1]
        return position + 1


class PermissionsConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> discord.Permissions:
        try:
            permissions = int(argument)
        except ValueError:
            raise commands.BadArgument(_("The permissions must be an integer."))
        permissions_none = discord.Permissions.none().value
        permissions_all = discord.Permissions.all().value
        if permissions <= permissions_none or permissions >= permissions_all:
            raise commands.BadArgument(
                _(
                    "The indicated permissions value must be between {permissions_none} and {permissions_all}."
                ).format(permissions_none=permissions_none, permissions_all=permissions_all)
            )
        return discord.Permissions(permissions=permissions)


@cog_i18n(_)
class EditRole(Cog):
    """A cog to edit roles!"""

    def __init__(self, bot: Red) -> None:  # Never performed except manually.
        self.bot: Red = bot

        self.cogsutils: CogsUtils = CogsUtils(cog=self)

    async def check_role(self, ctx: commands.Context, role: discord.Role) -> bool:
        if (
            not ctx.author.top_role > role
            and ctx.author.id != ctx.guild.owner.id
            and ctx.author.id not in ctx.bot.owner_ids
        ):
            raise commands.UserFeedbackCheckFailure(
                _(
                    "I can not let you edit {role.mention} ({role.id}) because that role is higher than or equal to your highest role in the Discord hierarchy."
                ).format(role=role),
                allowed_mentions=None,
            )
        if not ctx.guild.me.top_role > role:
            raise commands.UserFeedbackCheckFailure(
                _(
                    "I can not edit {role.mention} ({role.id}) because that role is higher than or equal to my highest role in the Discord hierarchy."
                ).format(role=role),
                allowed_mentions=None,
            )
        return True

    @commands.guild_only()
    @commands.admin_or_permissions(manage_roles=True)
    @commands.bot_has_guild_permissions(manage_roles=True)
    @commands.hybrid_group()
    async def editrole(self, ctx: commands.Context) -> None:
        """Commands for edit a role."""
        pass

    @editrole.command(name="create")
    async def editrole_create(
        self,
        ctx: commands.Context,
        color: typing.Optional[commands.ColorConverter] = None,
        *,
        name: str,
    ) -> None:
        """Create a role."""
        try:
            await ctx.guild.create_role(
                name=name,
                color=color,
                reason=f"{ctx.author} ({ctx.author.id}) has created the role {name}.",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @editrole.command(name="list")
    async def editrole_list(
        self,
        ctx: commands.Context,
    ) -> None:
        """List all roles in the current guild."""
        description = "".join(
            f"\n**•** **{len(ctx.guild.roles) - role.position}** - {role.mention} ({role.id}) - {len(role.members)} members"
            for role in sorted(ctx.guild.roles, key=lambda x: x.position, reverse=True)
        )
        embed: discord.Embed = discord.Embed(color=await ctx.embed_color())
        embed.title = _("List of roles in {guild.name} ({guild.id})").format(guild=ctx.guild)
        embeds = []
        pages = pagify(description, page_length=4096)
        for page in pages:
            e = embed.copy()
            e.description = page
            embeds.append(e)
        await Menu(pages=embeds).start(ctx)

    @editrole.command(name="name")
    async def editrole_name(self, ctx: commands.Context, role: discord.Role, *, name: str) -> None:
        """Edit role name."""
        await self.check_role(ctx, role)
        try:
            await role.edit(
                name=name,
                reason=f"{ctx.author} ({ctx.author.id}) has modified the role {role.name} ({role.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @editrole.command(name="color", aliases=["colour"])
    async def editrole_color(
        self, ctx: commands.Context, role: discord.Role, color: discord.Color
    ) -> None:
        """Edit role color."""
        await self.check_role(ctx, role)
        try:
            await role.edit(
                color=color,
                reason=f"{ctx.author} ({ctx.author.id}) has modified the role {role.name} ({role.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @editrole.command(name="mentionable")
    async def editrole_mentionable(
        self, ctx: commands.Context, role: discord.Role, mentionable: bool
    ) -> None:
        """Edit role mentionable."""
        await self.check_role(ctx, role)
        try:
            await role.edit(
                mentionable=mentionable,
                reason=f"{ctx.author} ({ctx.author.id}) has modified the role {role.name} ({role.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @editrole.command(name="position")
    async def editrole_position(
        self, ctx: commands.Context, role: discord.Role, position: PositionConverter
    ) -> None:
        """Edit role position.

        Warning: The role with a position 1 is the highest role in the Discord hierarchy.
        """
        await self.check_role(ctx, role)
        try:
            await role.edit(
                position=position,
                reason=f"{ctx.author} ({ctx.author.id}) has modified the role {role.name} ({role.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @editrole.command(name="permissions")
    async def editrole_permissions(
        self, ctx: commands.Context, role: discord.Role, permissions: PermissionsConverter
    ) -> None:
        """Edit role permissions.

        Warning: You must use the permissions value in numbers (admnistrator=8).
        You can use: https://discordapi.com/permissions.html
        """
        await self.check_role(ctx, role)
        try:
            await role.edit(
                permissions=permissions,
                reason=f"{ctx.author} ({ctx.author.id}) has modified the role {role.name} ({role.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @editrole.command(name="delete")
    async def editrole_delete(
        self,
        ctx: commands.Context,
        role: discord.Role,
        confirmation: bool = False,
    ) -> None:
        """Delete a role."""
        await self.check_role(ctx, role)
        if not confirmation and not ctx.assume_yes:
            embed: discord.Embed = discord.Embed()
            embed.title = _("⚠️ - Delete role")
            embed.description = _(
                "Do you really want to delete the role {role.mention} ({role.id})?"
            ).format(role=role)
            embed.color = 0xF00020
            if not await self.cogsutils.ConfirmationAsk(
                ctx, content=f"{ctx.author.mention}", embed=embed
            ):
                await self.cogsutils.delete_message(ctx.message)
                return
        try:
            await role.delete(
                reason=f"{ctx.author} ({ctx.author.id}) has deleted the role {role.name} ({role.id})."
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

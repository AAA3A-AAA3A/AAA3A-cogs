from .AAA3A_utils import CogsUtils  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
from redbot.core.bot import Red  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

# Credits:
# Thanks to @epic guy on Discord for the basic syntax (command groups, commands) and also commands (await ctx.send, await ctx.author.send, await ctx.message.delete())!
# Thanks to the developers of the cogs I added features to as it taught me how to make a cog! (Chessgame by WildStriker, Captcha by Kreusada, Speak by Epic guy and Rommer by Dav)
# Thanks to all the people who helped me with some commands in the #coding channel of the redbot support server!

_ = Translator("EditRole", __file__)

@cog_i18n(_)
class EditRole(commands.Cog):
    """A cog to edit roles!"""

    def __init__(self, bot: Red):
        self.bot: Red = bot

        self.cogsutils = CogsUtils(cog=self)
        self.cogsutils._setup()

    async def check_role(self, ctx: commands.Context, role: discord.Role):
        if not ctx.guild.me.top_role > role:
            await ctx.send(_("I can not let you edit {role.mention} ({role.id}) because that role is higher than or equal to your highest role in the Discord hierarchy.").format(**locals()), allowed_mentions=None)
            return False
        if not ctx.author.top_role > role and not ctx.author.id == ctx.guild.owner.id:
            await ctx.send(_("I can not edit {role.mention} ({role.id}) because that role is higher than or equal to my highest role in the Discord hierarchy.").format(**locals()), allowed_mentions=None)
            return False
        return True

    @commands.guild_only()
    @commands.admin_or_permissions(manage_roles=True)
    @commands.bot_has_guild_permissions(manage_roles=True)
    @commands.group()
    async def editrole(self, ctx: commands.Context):
        """Commands for edit a role."""
        pass

    @editrole.command()
    async def name(self, ctx: commands.Context, role: discord.Role, name: str):
        """Edit role name.
        """
        if not await self.check_role(ctx, role):
            return
        try:
            await role.edit(name=name, reason=f"{ctx.author} ({ctx.author.id}) has modified the role {role.name} ({role.id}).")
        except discord.HTTPException:
            await ctx.send(_("I attempted to do something that Discord denied me permissions for. Your command failed to successfully complete.").format(**locals()))
        else:
            await ctx.tick()

    @editrole.command(aliases=["color"])
    async def colour(self, ctx: commands.Context, role: discord.Role, colour: discord.Colour):
        """Edit role colour.
        """
        if not await self.check_role(ctx, role):
            return
        try:
            await role.edit(color=colour, reason=f"{ctx.author} ({ctx.author.id}) has modified the role {role.name} ({role.id}).")
        except discord.HTTPException:
            await ctx.send(_("I attempted to do something that Discord denied me permissions for. Your command failed to successfully complete.").format(**locals()))
        else:
            await ctx.tick()

    @editrole.command()
    async def mentionable(self, ctx: commands.Context, role: discord.Role, mentionable: bool):
        """Edit role mentionable.
        """
        if not await self.check_role(ctx, role):
            return
        try:
            await role.edit(mentionable=mentionable, reason=f"{ctx.author} ({ctx.author.id}) has modified the role {role.name} ({role.id}).")
        except discord.HTTPException:
            await ctx.send(_("I attempted to do something that Discord denied me permissions for. Your command failed to successfully complete.").format(**locals()))
        else:
            await ctx.tick()

    @editrole.command()
    async def position(self, ctx: commands.Context, role: discord.Role, position: int):
        """Edit role position.
        
        Warning: The role with a position 1 is the highest role in the Discord hierarchy.
        """
        if not await self.check_role(ctx, role):
            return
        max_guild_roles_position = len(ctx.guild.roles)
        if not position > 0 or not position < max_guild_roles_position + 1:
            await ctx.send(_("The indicated position must be between 1 and {max_guild_roles_position}.").format(**locals()))
            return
        l = [x for x in range(0, max_guild_roles_position - 1)]
        l.reverse()
        position = l[position - 1]
        position = position + 1
        try:
            await role.edit(position=position, reason=f"{ctx.author} ({ctx.author.id}) has modified the role {role.name} ({role.id}).")
        except discord.HTTPException:
            await ctx.send(_("I attempted to do something that Discord denied me permissions for. Your command failed to successfully complete.").format(**locals()))
        else:
            await ctx.tick()

    @editrole.command()
    async def permissions(self, ctx: commands.Context, role: discord.Role, permissions: int):
        """Edit role permissions.
        
        Warning: You must use the permissions value in numbers (admnistrator=8).
        You can use: https://discordapi.com/permissions.html
        """
        if not await self.check_role(ctx, role):
            return
        permissions_none = discord.Permissions.none().value
        permissions_all = discord.Permissions.all().value
        if not permissions > permissions_none or not permissions < permissions_all:
            await ctx.send(_("The indicated permissions value must be between {permissions_none} and {permissions_all}.").format(**locals()))
            return
        permissions = discord.Permissions(permissions=permissions)
        try:
            await role.edit(permissions=permissions, reason=f"{ctx.author} ({ctx.author.id}) has modified the role {role.name} ({role.id}).")
        except discord.HTTPException:
            await ctx.send(_("I attempted to do something that Discord denied me permissions for. Your command failed to successfully complete.").format(**locals()))
        else:
            await ctx.tick()

    @editrole.command()
    async def delete(self, ctx: commands.Context, role: discord.Role, confirmation: typing.Optional[bool]=False):
        """Delete role.
        """
        if not await self.check_role(ctx, role):
            return
        if not confirmation:
            embed: discord.Embed = discord.Embed()
            embed.title = _(":warning: - Delete role").format(**locals())
            embed.description = _("Do you really want to delete the role {role.mention} ({role.id})?").format(**locals())
            embed.color = 0xf00020
            if not await self.cogsutils.ConfirmationAsk(ctx, text=f"{ctx.author.mention}", embed=embed):
                await self.cogsutils.delete_message(ctx.message)
                return
        try:
            await role.delete(reason=f"{ctx.author} ({ctx.author.id}) has deleted the role {role.name} ({role.id}).")
        except discord.HTTPException:
            await ctx.send(_("I attempted to do something that Discord denied me permissions for. Your command failed to successfully complete.").format(**locals()))
        else:
            await ctx.tick()
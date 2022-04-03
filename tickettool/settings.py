from .AAA3A_utils.cogsutils import CogsUtils  # isort:skip
if CogsUtils().is_dpy2:
    from .AAA3A_utils.cogsutils import Buttons  # isort:skip
else:
    from dislash import ActionRow, Button, ButtonStyle  # isort:skip

from redbot.core import commands  # isort:skip
import discord  # isort:skip
import typing  # isort:skip


def _(untranslated: str):
    return untranslated

class settings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.guild_only()
    @commands.admin_or_permissions(administrator=True)
    @commands.group(name="setticket", aliases=["ticketset"])
    async def configuration(self, ctx: commands.Context):
        """Configure TicketTool for your server."""
        pass

    @configuration.command(name="enable", usage="<true_or_false>")
    async def enable(self, ctx: commands.Context, state: bool):
        """Enable or disable Ticket System

        Use `True` (Or `yes`) to enable or `False` (or `no`) to disable.
        """
        config = await self.config.guild(ctx.guild).settings.all()

        if config["category_open"] is None or config["category_close"] is None or config["admin_role"] is None:
            await ctx.send(_("You cannot enable the ticket system on this server if you have not configured the following options:"
                            f"- The category of open tickets : `{ctx.prefix}setticket categoryopen <category>`"
                            f"- The category of close tickets : `{ctx.prefix}setticket categoryclose <category>`"
                            f"- The admin role has full access to the tickets : `{ctx.prefix}setticket adminrole <role>`"
                            "All other parameters are optional or have default values that will be used.").format(**locals()))
            return

        actual_enable = config["enable"]
        if actual_enable is state:
            await ctx.send(_("Ticket System is already set on {state}.").format(**locals()))
            return

        await self.config.guild(ctx.guild).settings.enable.set(state)
        await ctx.send(_("Ticket System state registered: {state}.").format(**locals()))

    @configuration.command(aliases=["lchann", "lchannel", "logschan", "logchannel", "logsc"], usage="<text_channel_or_'none'>")
    async def logschannel(self, ctx: commands.Context, *, channel: typing.Optional[discord.TextChannel]=None):
        """Set a channel where events are registered.

        ``channel``: Text channel.
        You can also use "None" if you wish to remove the logging channel.
        """
        if channel is None:
            await self.config.guild(ctx.guild).settings.logschannel.clear()
            await ctx.send(_("Logging channel removed.").format(**locals()))
            return

        needperm = await self.check_permissions_in_channel(["embed_links", "read_messages", "read_message_history", "send_messages", "attach_files"], channel)
        if needperm:
            await ctx.send(_("The bot does not have at least one of the following permissions in this channel: `embed_links`, `read_messages`, `read_message_history`, `send_messages`, `attach_files`.").format(**locals()))
            return

        await self.config.guild(ctx.guild).settings.logschannel.set(channel.id)
        await ctx.send(_("Logging channel registered: {channel.mention}.").format(**locals()))

    @configuration.command(usage="<category_or_'none'>")
    async def categoryopen(self, ctx: commands.Context, *, category: typing.Optional[discord.CategoryChannel]=None):
        """Set a category where open tickets are created.

        ``category``: Category.
        You can also use "None" if you wish to remove the open category.
        """
        if category is None:
            await self.config.guild(ctx.guild).settings.category_open.clear()
            await ctx.send(_("Category Open removed.").format(**locals()))
            return

        await self.config.guild(ctx.guild).settings.category_open.set(category.id)
        await ctx.send(_("Category Open registered: {category.name}.").format(**locals()))

    @configuration.command(usage="<category_or_'none'>")
    async def categoryclose(self, ctx: commands.Context, *, category: typing.Optional[discord.CategoryChannel]=None):
        """Set a category where close tickets are created.

        ``category``: Category.
        You can also use "None" if you wish to remove the close category.
        """
        if category is None:
            await self.config.guild(ctx.guild).settings.category_close.clear()
            await ctx.send(_("Category Close removed.").format(**locals()))
            return

        await self.config.guild(ctx.guild).settings.category_close.set(category.id)
        await ctx.send(_("Category Close registered: {category.name}.").format(**locals()))

    @configuration.command(usage="<role_or_'none'>")
    async def adminrole(self, ctx: commands.Context, *, role: typing.Optional[discord.Role]=None):
        """Set a role for administrators of the ticket system.

        ``role``: Role.
        You can also use "None" if you wish to remove the admin role.
        """
        if role is None:
            await self.config.guild(ctx.guild).settings.admin_role.clear()
            await ctx.send(_("Admin Role removed.").format(**locals()))
            return

        await self.config.guild(ctx.guild).settings.admin_role.set(role.id)
        await ctx.send(_("Admin Role registered: {role.name}.").format(**locals()))

    @configuration.command(usage="<role_or_'none'>")
    async def supportrole(self, ctx: commands.Context, *, role: typing.Optional[discord.Role]=None):
        """Set a role for helpers of the ticket system.

        ``role``: Role.
        You can also use "None" if you wish to remove the support role.
        """
        if role is None:
            await self.config.guild(ctx.guild).settings.support_role.clear()
            await ctx.send(_("Support Role removed.").format(**locals()))
            return

        await self.config.guild(ctx.guild).settings.support_role.set(role.id)
        await ctx.send(_("Support Role registered: {role.name}.").format(**locals()))

    @configuration.command(usage="<role_or_'none'>")
    async def ticketrole(self, ctx: commands.Context, *, role: typing.Optional[discord.Role]=None):
        """Set a role for creaters of a ticket.

        ``role``: Role.
        You can also use "None" if you wish to remove the ticket role.
        """
        if role is None:
            await self.config.guild(ctx.guild).settings.ticket_role.clear()
            await ctx.send(_("Ticket Role removed.").format(**locals()))
            return

        await self.config.guild(ctx.guild).settings.ticket_role.set(role.id)
        await ctx.send(_("Ticket Role registered: {role.name}.").format(**locals()))

    @configuration.command(usage="<role_or_'none'>")
    async def viewrole(self, ctx: commands.Context, *, role: typing.Optional[discord.Role]=None):
        """Set a role for viewers of tickets.

        ``role``: Role.
        You can also use "None" if you wish to remove the view role.
        """
        if role is None:
            await self.config.guild(ctx.guild).settings.view_role.clear()
            await ctx.send(_("View Role removed.").format(**locals()))
            return

        await self.config.guild(ctx.guild).settings.view_role.set(role.id)
        await ctx.send(_("View Role registered: {role.name}.").format(**locals()))

    @configuration.command(usage="<role_or_'none'>")
    async def pingrole(self, ctx: commands.Context, *, role: typing.Optional[discord.Role]=None):
        """Set a role for pings on ticket creation.

        ``role``: Role.
        You can also use "None" if you wish to remove the ping role.
        """
        if role is None:
            await self.config.guild(ctx.guild).settings.ping_role.clear()
            await ctx.send(_("Ping Role removed.").format(**locals()))
            return

        await self.config.guild(ctx.guild).settings.ping_role.set(role.id)
        await ctx.send(_("Ping Role registered: {role.name}.").format(**locals()))

    @configuration.command(usage="<int>")
    async def nbmax(self, ctx: commands.Context, int: int):
        """Max Number of tickets for a member.
        """
        if int == 0:
            await ctx.send(_("Disable the system instead.").format(**locals()))
            return

        await self.config.guild(ctx.guild).nb_max.set(int)
        await ctx.send(_("Max Number registered: {int}.").format(**locals()))

    @configuration.command(usage="<true_or_false>")
    async def modlog(self, ctx: commands.Context, state: bool):
        """Enable or disable Modlog.

        Use `True` (Or `yes`) to enable or `False` (or `no`) to disable.
        """
        config = await self.config.guild(ctx.guild).settings.all()

        actual_create_modlog = config["create_modlog"]
        if actual_create_modlog is state:
            await ctx.send(_("Modlog is already set on {state}.").format(**locals()))
            return

        await self.config.guild(ctx.guild).settings.create_modlog.set(state)
        await ctx.send(_("Modlog state registered: {state}.").format(**locals()))

    @configuration.command(usage="<true_or_false>")
    async def closeonleave(self, ctx: commands.Context, state: bool):
        """Enable or disable Close on Leave.

        Use `True` (Or `yes`) to enable or `False` (or `no`) to disable.
        """
        config = await self.config.guild(ctx.guild).settings.all()

        actual_close_on_leave = config["close_on_leave"]
        if actual_close_on_leave is state:
            await ctx.send(_("Close on Leave is already set on {state}.").format(**locals()))
            return

        await self.config.guild(ctx.guild).settings.close_on_leave.set(state)
        await ctx.send(_("Close on Leave state registered: {state}.").format(**locals()))

    @configuration.command(usage="<true_or_false>")
    async def createonreact(self, ctx: commands.Context, state: bool):
        """Enable or disable Create on React ``.

        Use `True` (Or `yes`) to enable or `False` (or `no`) to disable.
        """
        config = await self.config.guild(ctx.guild).settings.all()

        actual_create_on_react = config["create_on_react"]
        if actual_create_on_react is state:
            await ctx.send(_("Create on React is already set on {state}.").format(**locals()))
            return

        await self.config.guild(ctx.guild).settings.create_on_react.set(state)
        await ctx.send(_("Create on React state registered: {state}.").format(**locals()))

    @configuration.command(aliases=["colour", "col", "embedcolor", "embedcolour"], usage="<color_or_'none'>")
    async def color(self, ctx: commands.Context, *, color: typing.Optional[discord.Color]=None):
        """Set a colour fort the embed.

        ``color``: Color.
        You can also use "None" if you wish to reset the color.
        """

        if color is None:
            await self.config.guild(ctx.guild).settings.color.clear()
            config = await self.config.guild(ctx.guild).settings.all()
            actual_color = config["color"]
            actual_thumbnail = config["thumbnail"]
            embed: discord.Embed = discord.Embed()
            embed.color = actual_color
            embed.set_thumbnail(url=actual_thumbnail)
            embed.title = _("Configure the embed").format(**locals())
            embed.description = _("Reset color:").format(**locals())
            embed.add_field(
                name=_("Color:").format(**locals()),
                value=f"{actual_color}")
            message = await ctx.send(embed=embed)
            return

        await self.config.guild(ctx.guild).settings.color.set(color.value)
        config = await self.config.guild(ctx.guild).settings.all()
        actual_color = config["color"]
        actual_thumbnail = config["thumbnail"]
        embed: discord.Embed = discord.Embed()
        embed.title = _("Configure the embed").format(**locals())
        embed.description = _("Set color:").format(**locals())
        embed.color = actual_color
        embed.set_thumbnail(url=actual_thumbnail)
        embed.add_field(
            name=_("Color:").format(**locals()),
            value=f"{actual_color}")
        message = await ctx.send(embed=embed)

    @configuration.command(aliases=["picture", "thumb", "link"], usage="<link_or_'none'>")
    async def thumbnail(self, ctx: commands.Context, *, link = None):
        """Set a thumbnail fort the embed.

        ``link``: Thumbnail link.
        You can also use "None" if you wish to reset the thumbnail.
        """

        if link is None:
            await self.config.guild(ctx.guild).settings.thumbnail.clear()
            config = await self.config.guild(ctx.guild).settings.all()
            actual_thumbnail = config["thumbnail"]
            actual_color = config["color"]
            embed: discord.Embed = discord.Embed()
            embed.title = _("Configure the embed").format(**locals())
            embed.description = _("Reset thumbnail:").format(**locals())
            embed.set_thumbnail(url=actual_thumbnail)
            embed.color = actual_color
            embed.add_field(
                name=_("Thumbnail:").format(**locals()),
                value=f"{actual_thumbnail}")
            message = await ctx.send(embed=embed)
            return

        await self.config.guild(ctx.guild).settings.thumbnail.set(link)
        config = await self.config.guild(ctx.guild).settings.all()
        actual_thumbnail = config["thumbnail"]
        actual_color = config["color"]
        embed: discord.Embed = discord.Embed()
        embed.title = _("Configure the embed").format(**locals())
        embed.description = _("Set thumbnail:").format(**locals())
        embed.set_thumbnail(url=actual_thumbnail)
        embed.color = actual_color
        embed.add_field(
            name=_("Thumbnail:").format(**locals()),
            value=f"{actual_thumbnail}")
        message = await ctx.send(embed=embed)

    @configuration.command(name="auditlogs", aliases=["logsaudit"], usage="<true_or_false>")
    async def showauthor(self, ctx: commands.Context, state: bool):
        """Make the author of each action concerning a ticket appear in the server logs.

        Use `True` (Or `yes`) to enable or `False` (or `no`) to disable.
        """
        config = await self.config.guild(ctx.guild).settings.all()

        actual_audit_logs = config["audit_logs"]
        if actual_audit_logs is state:
            await ctx.send(_("Audit Logs is already set on {state}.").format(**locals()))
            return

        await self.config.guild(ctx.guild).settings.audit_logs.set(state)
        await ctx.send(_("Audit Logs state registered: {state}.").format(**locals()))

    @configuration.command(name="closeconfirmation", aliases=["confirm"], usage="<true_or_false>")
    async def confirmation(self, ctx: commands.Context, state: bool):
        """Enable or disable Close Confirmation.

        Use `True` (Or `yes`) to enable or `False` (or `no`) to disable.
        """
        config = await self.config.guild(ctx.guild).settings.all()

        actual_close_confirmation = config["close_confirmation"]
        if actual_close_confirmation is state:
            await ctx.send(_("Close Confirmation is already set on {state}.").format(**locals()))
            return

        await self.config.guild(ctx.guild).settings.close_confirmation.set(state)
        await ctx.send(_("Close Confirmation state registered: {state}.").format(**locals()))

    @configuration.command(name="message")
    async def message(self, ctx: commands.Context, channel: typing.Optional[discord.TextChannel]=None):
        if channel is None:
            channel = ctx.channel
        config = await self.config.guild(ctx.guild).settings.all()
        actual_color = config["color"]
        actual_thumbnail = config["thumbnail"]
        embed: discord.Embed = discord.Embed()
        embed.title = str(config["embed_button"]["title"])
        embed.description = str(config["embed_button"]["description"]).replace('{prefix}', f'{ctx.prefix}')
        embed.set_thumbnail(url=actual_thumbnail)
        embed.color = actual_color
        embed.set_footer(text=ctx.guild.name, icon_url=ctx.guild.icon or "" if self.cogsutils.is_dpy2 else ctx.guild.icon_url or "")
        if self.cogsutils.is_dpy2:
            view = Buttons(timeout=None, buttons=[{"style": 2, "label": _("Create ticket").format(**locals()), "emoji": "🎟️", "custom_id": "create_ticket_button", "disabled": False}])
            await channel.send(embed=embed, view=view)
        else:
            button = ActionRow(
                Button(
                    style=ButtonStyle.grey,
                    label=_("Create ticket"),
                    emoji="🎟️",
                    custom_id="create_ticket_button",
                    disabled=False
                )
            )
            await channel.send(embed=embed, components=[button])

    async def check_permissions_in_channel(self, permissions: typing.List[str], channel: discord.TextChannel):
        """Function to checks if the permissions are available in a guild.
        This will return a list of the missing permissions.
        """
        return [
            permission
            for permission in permissions
            if not getattr(channel.permissions_for(channel.guild.me), permission)
        ]

    @commands.is_owner()
    @configuration.command(name="purge", hidden=True)
    async def command_purge(self, ctx: commands.Context, confirmation: typing.Optional[bool]=False):
        """Purge all existing tickets in the config. Does not delete any channels. All commands associated with the tickets will no longer work.
        """
        config = await self.bot.get_cog("TicketTool").get_config(ctx.guild)
        if not confirmation:
            embed: discord.Embed = discord.Embed()
            embed.title = _("Do you really want to purge all the tickets in the config?").format(**locals())
            embed.description = _("Does not delete any channels. All commands associated with the tickets will no longer work.").format(**locals())
            embed.color = config["color"]
            embed.set_author(name=ctx.author.name, url=ctx.author.display_avatar if self.cogsutils.is_dpy2 else ctx.author.avatar_url, icon_url=ctx.author.display_avatar if self.cogsutils.is_dpy2 else ctx.author.avatar_url)
            response = await CogsUtils().ConfirmationAsk(ctx, embed=embed)
            if not response:
                return
        count = 0
        to_remove = []
        data = await ctx.bot.get_cog("TicketTool").config.guild(ctx.guild).tickets.all()
        for channel in data:
            count += 1
            to_remove.append(channel)
        for channel in to_remove:
            del data[str(channel)]
        await ctx.bot.get_cog("TicketTool").config.guild(ctx.guild).tickets.set(data)
        await ctx.send(_("{count} tickets have been removed from the config.").format(**locals()))
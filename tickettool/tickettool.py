from .AAA3A_utils.cogsutils import CogsUtils  # isort:skip
from redbot.core import commands  # isort:skip
import discord  # isort:skip
import typing  # isort:skip
if CogsUtils().is_dpy2:
    from .AAA3A_utils.cogsutils import Buttons  # isort:skip
else:
    from dislash import ActionRow, Button, ButtonStyle  # isort:skip

import asyncio
import datetime
import io
from copy import copy

import chat_exporter
from redbot.core import Config, modlog
from redbot.core.bot import Red

from .settings import settings
from .utils import utils

# Credits:
# Thanks to @epic guy on Discord for the basic syntax (command groups, commands) and also commands (await ctx.send, await ctx.author.send, await ctx.message.delete())!
# Thanks to @YamiKaitou on Discord for the technique in the init file to load the interaction client only if it is not loaded! Before this fix, when a user clicked on a button, the actions would be launched about 10 times, which caused huge spam and a loop in the channel!
# Thanks to the developers of the cogs I added features to as it taught me how to make a cog! (Chessgame by WildStriker, Captcha by Kreusada, Speak by Epic guy and Rommer by Dav)
# Thanks to all the people who helped me with some commands in the #coding channel of the redbot support server!

def _(untranslated: str):
    return untranslated

class TicketTool(settings, commands.Cog):
    """A cog to manage a ticket system!"""

    def __init__(self, bot):
        self.bot = bot

        self.config: Config = Config.get_conf(
            self,
            identifier=937480369417,
            force_registration=True,
        )
        self.ticket_guild = {
            "settings": {
                "enable": False,
                "logschannel": None,
                "category_open": None,
                "category_close": None,
                "admin_role": None,
                "support_role": None,
                "ticket_role": None,
                "view_role": None,
                "ping_role": None,
                "nb_max": 5,
                "create_modlog": False,
                "close_on_leave": False,
                "create_on_react": False,
                "color": 0x01d758,
                "thumbnail": "http://www.quidd.it/wp-content/uploads/2017/10/Ticket-add-icon.png",
                "audit_logs": False,
                "close_confirmation": False,
                "emoji_open": "❓",
                "emoji_close": "🔒",
                "last_nb": 0000,
                "embed_button": {
                    "title": "Create a ticket",
                    "description": _("To get help on this server or to place a command for example, you can create a ticket.\n"
                                     "Just use the command `{prefix}ticket create` or click on the button below.\n"
                                     "You can then use the `{prefix}ticket` subcommand to manage your ticket."),
                },
            },
            "tickets": {},
        }
        self.config.register_guild(**self.ticket_guild)

        self.cogsutils = CogsUtils(cog=self)
        self.cogsutils._setup()

        asyncio.create_task(self.load_buttons())

    async def load_buttons(self):
        try:
            self.bot.add_view(Buttons(timeout=None, buttons=[{"style": 2, "label": _("Create ticket").format(**locals()), "emoji": "🎟️", "custom_id": "create_ticket_button", "disabled": False}], function=self.on_button_interaction, infinity=True))
            self.bot.add_view(Buttons(timeout=None, buttons=[{"style": 2, "label": _("Close").format(**locals()), "emoji": "🔒", "custom_id": "close_ticket_button", "disabled": False}, {"style": 2, "label": _("Claim").format(**locals()), "emoji": "🙋‍♂️", "custom_id": "claim_ticket_button", "disabled": False}], function=self.on_button_interaction, infinity=True))
        except Exception as e:
            self.log.error(f"The Buttons View could not be added correctly.", exc_info=e)

    async def get_config(self, guild: discord.Guild):
        config = await self.bot.get_cog("TicketTool").config.guild(guild).settings.all()
        if config["logschannel"] is not None:
            config["logschannel"] = guild.get_channel(config["logschannel"])
        if config["category_open"] is not None:
            config["category_open"] = guild.get_channel(config["category_open"])
        if config["category_close"] is not None:
            config["category_close"] = guild.get_channel(config["category_close"])
        if config["admin_role"] is not None:
            config["admin_role"] = guild.get_role(config["admin_role"])
        if config["support_role"] is not None:
            config["support_role"] = guild.get_role(config["support_role"])
        if config["ticket_role"] is not None:
            config["ticket_role"] = guild.get_role(config["ticket_role"])
        if config["view_role"] is not None:
            config["view_role"] = guild.get_role(config["view_role"])
        if config["ping_role"] is not None:
            config["ping_role"] = guild.get_role(config["ping_role"])
        return config

    async def get_ticket(self, channel: discord.TextChannel):
        config = await self.bot.get_cog("TicketTool").config.guild(channel.guild).tickets.all()
        if str(channel.id) in config:
            json = config[str(channel.id)]
        else:
            return None
        ticket = Ticket.from_json(json, self.bot)
        ticket.bot = self.bot
        ticket.guild = ticket.bot.get_guild(ticket.guild)
        ticket.owner = ticket.guild.get_member(ticket.owner)
        ticket.channel = ticket.guild.get_channel(ticket.channel)
        ticket.claim = ticket.guild.get_member(ticket.claim)
        ticket.created_by = ticket.guild.get_member(ticket.created_by)
        ticket.opened_by = ticket.guild.get_member(ticket.opened_by)
        ticket.closed_by = ticket.guild.get_member(ticket.closed_by)
        ticket.deleted_by = ticket.guild.get_member(ticket.deleted_by)
        ticket.renamed_by = ticket.guild.get_member(ticket.renamed_by)
        members = ticket.members
        ticket.members = []
        for m in members:
            ticket.members.append(channel.guild.get_member(m))
        if ticket.created_at is not None:
            ticket.created_at = datetime.datetime.fromtimestamp(ticket.created_at)
        if ticket.opened_at is not None:
            ticket.opened_at = datetime.datetime.fromtimestamp(ticket.opened_at)
        if ticket.closed_at is not None:
            ticket.closed_at = datetime.datetime.fromtimestamp(ticket.closed_at)
        if ticket.deleted_at is not None:
            ticket.deleted_at = datetime.datetime.fromtimestamp(ticket.deleted_at)
        if ticket.renamed_at is not None:
            ticket.renamed_at = datetime.datetime.fromtimestamp(ticket.renamed_at)
        if ticket.first_message is not None:
            ticket.first_message = ticket.channel.get_partial_message(ticket.first_message)
        return ticket

    async def get_audit_reason(self, guild: discord.Guild, author: typing.Optional[discord.Member]=None, reason: typing.Optional[str]=None):
        if reason is None:
            reason = _("Action taken for the ticket system.").format(**locals())
        config = await self.bot.get_cog("TicketTool").get_config(guild)
        if author is None or not config["audit_logs"]:
            return f"{reason}"
        else:
            return f"{author.name} ({author.id}) - {reason}"

    async def get_embed_important(self, ticket, more: bool, author: discord.Member, title: str, description: str):
        config = await self.bot.get_cog("TicketTool").get_config(ticket.guild)
        actual_color = config["color"]
        actual_thumbnail = config["thumbnail"]
        embed: discord.Embed = discord.Embed()
        embed.title = f"{title}"
        embed.description = f"{description}"
        embed.set_thumbnail(url=actual_thumbnail)
        embed.color = actual_color
        embed.timestamp = datetime.datetime.now(tz=datetime.timezone.utc)
        embed.set_author(name=author, url=author.display_avatar if self.cogsutils.is_dpy2 else author.avatar_url, icon_url=author.display_avatar if self.cogsutils.is_dpy2 else author.avatar_url)
        embed.set_footer(text=ticket.guild.name, icon_url=ticket.guild.icon or "" if self.cogsutils.is_dpy2 else ticket.guild.icon_url or "")
        embed.add_field(
            inline=True,
            name=_("Ticket ID:").format(**locals()),
            value=f"{ticket.id}")
        embed.add_field(
            inline=True,
            name=_("Owned by:").format(**locals()),
            value=f"{ticket.owner.mention} ({ticket.owner.id})")
        embed.add_field(
            inline=True,
            name=_("Channel:").format(**locals()),
            value=f"{ticket.channel.mention} - {ticket.channel.name} ({ticket.channel.id})")
        if more:
            if ticket.closed_by is not None:
                embed.add_field(
                    inline=False,
                    name=_("Closed by:").format(**locals()),
                    value=f"{ticket.owner.mention} ({ticket.owner.id})")
            if ticket.deleted_by is not None:
                embed.add_field(
                    inline=True,
                    name=_("Deleted by:").format(**locals()),
                    value=f"{ticket.deleted_by.mention} ({ticket.deleted_by.id})")
            if ticket.closed_at:
                embed.add_field(
                    inline=False,
                    name=_("Closed at:").format(**locals()),
                    value=f"{ticket.closed_at}")
        embed.add_field(
            inline=False,
            name=_("Reason:").format(**locals()),
            value=f"{ticket.reason}")
        return embed

    async def get_embed_action(self, ticket, author: discord.Member, action: str):
        config = await self.bot.get_cog("TicketTool").get_config(ticket.guild)
        actual_color = config["color"]
        embed: discord.Embed = discord.Embed()
        embed.title = _("Ticket {ticket.id} - Action taken").format(**locals())
        embed.description = f"{action}"
        embed.color = actual_color
        embed.timestamp = datetime.datetime.now(tz=datetime.timezone.utc)
        embed.set_author(name=author, url=author.display_avatar if self.cogsutils.is_dpy2 else author.avatar_url, icon_url=author.display_avatar if self.cogsutils.is_dpy2 else author.avatar_url)
        embed.set_footer(text=ticket.guild.name, icon_url=ticket.guild.icon or "" if self.cogsutils.is_dpy2 else ticket.guildicon_url or "")
        embed.add_field(
            inline=False,
            name=_("Reason:").format(**locals()),
            value=f"{ticket.reason}")
        return embed

    async def check_limit(self, member: discord.Member):
        config = await self.bot.get_cog("TicketTool").get_config(member.guild)
        data = await self.bot.get_cog("TicketTool").config.guild(member.guild).tickets.all()
        to_remove = []
        count = 1
        for id in data:
            channel = member.guild.get_channel(int(id))
            if channel is not None:
                ticket = await self.bot.get_cog("TicketTool").get_ticket(channel)
                if ticket.created_by == member and ticket.status == "open":
                    count += 1
            if channel is None:
                to_remove.append(id)
        if not to_remove == []:
            data = await self.bot.get_cog("TicketTool").config.guild(member.guild).tickets.all()
            for id in to_remove:
                del data[str(id)]
            await self.bot.get_cog("TicketTool").config.guild(member.guild).tickets.set(data)
        if count > config["nb_max"]:
            return False
        else:
            return True

    async def create_modlog(self, ticket, action: str, reason: str):
        config = await self.bot.get_cog("TicketTool").get_config(ticket.guild)
        if config["create_modlog"]:
            case = await modlog.create_case(
                        ticket.bot,
                        ticket.guild,
                        ticket.created_at,
                        action_type=action,
                        user=ticket.created_by,
                        moderator=ticket.created_by,
                        reason=reason,
                    )
            return case
        return

    def decorator(enable_check: typing.Optional[bool]=False, ticket_check: typing.Optional[bool]=False, status: typing.Optional[str]=None, ticket_owner: typing.Optional[bool]=False, admin_role: typing.Optional[bool]=False, support_role: typing.Optional[bool]=False, ticket_role: typing.Optional[bool]=False, view_role: typing.Optional[bool]=False, guild_owner: typing.Optional[bool]=False, claim: typing.Optional[bool]=None, claim_staff: typing.Optional[bool]=False, members: typing.Optional[bool]=False):
        async def pred(ctx):
            config = await ctx.bot.get_cog("TicketTool").get_config(ctx.guild)
            if enable_check:
                if not config["enable"]:
                    return
            if ticket_check:
                ticket = await ctx.bot.get_cog("TicketTool").get_ticket(ctx.channel)
                if ticket is None:
                    return
                if status is not None:
                    if not ticket.status == status:
                        return False
                if claim is not None:
                    if ticket.claim is not None:
                        check = True
                    elif ticket.claim is None:
                        check = False
                    if not check == claim:
                        return False
                if ctx.author.id in ctx.bot.owner_ids:
                    return True
                if ticket_owner:
                    if ctx.author == ticket.owner:
                        return True
                if admin_role and config["admin_role"] is not None:
                    if ctx.author in config["admin_role"].members:
                        return True
                if support_role and config["support_role"] is not None:
                    if ctx.author in config["support_role"].members:
                        return True
                if ticket_role and config["ticket_role"] is not None:
                    if ctx.author in config["ticket_role"].members:
                        return True
                if view_role and config["view_role"] is not None:
                    if ctx.author in config["view_role"].members:
                        return True
                if guild_owner:
                    if ctx.author == ctx.guild.owner:
                        return True
                if claim_staff:
                    if ctx.author == ticket.claim:
                        return True
                if members:
                    if ctx.author in ticket.members:
                        return True
                return False
            return True
        return commands.check(pred)

    @commands.guild_only()
    @commands.group(name="ticket")
    async def ticket(self, ctx: commands.Context):
        """Commands for using the ticket system."""

    @ticket.command(name="create")
    async def command_create(self, ctx: commands.Context, *, reason: typing.Optional[str]="No reason provided."):
        """Create a ticket.
        """
        config = await self.bot.get_cog("TicketTool").get_config(ctx.guild)
        limit = config["nb_max"]
        category_open = config["category_open"]
        category_close = config["category_close"]
        if not config["enable"]:
            await ctx.send(_("The ticket system is not activated on this server. Please ask an administrator of this server to use the `{ctx.prefix}ticketset` subcommands to configure it.").format(**locals()))
            return
        if not await self.bot.get_cog("TicketTool").check_limit(ctx.author):
            await ctx.send(f"Sorry. You have already reached the limit of {limit} open tickets.")
            return
        if not category_open.permissions_for(ctx.guild.me).manage_channels or not category_close.permissions_for(ctx.guild.me).manage_channels:
            await ctx.send(_("The bot does not have `manage_channels` permission on the 'open' and 'close' categories to allow the ticket system to function properly. Please notify an administrator of this server.").format(**locals()))
            return
        ticket = Ticket.instance(ctx, reason)
        await ticket.create()
        await ctx.tick()

    @decorator(enable_check=False, ticket_check=True, status=None, ticket_owner=True, admin_role=True, support_role=False, ticket_role=False, view_role=False, guild_owner=True, claim=None, claim_staff=True, members=False)
    @ticket.command(name="export")
    async def command_export(self, ctx: commands.Context):
        """Export all the messages of an existing ticket in html format.
        Please note: all attachments and user avatars are saved with the Discord link in this file.
        """
        ticket = await self.bot.get_cog("TicketTool").get_ticket(ctx.channel)
        transcript = await chat_exporter.export(channel=ticket.channel, limit=None, tz_info="UTC", guild=ticket.guild, bot=ticket.bot)
        if transcript is not None:
            file = discord.File(io.BytesIO(transcript.encode()),
                                filename=f"transcript-ticket-{ticket.id}.html")
        await ctx.send(_("Here is the html file of the transcript of all the messages in this ticket.\nPlease note: all attachments and user avatars are saved with the Discord link in this file.").format(**locals()), file=file)
        await ctx.tick()

    @decorator(enable_check=True, ticket_check=True, status="close", ticket_owner=True, admin_role=True, support_role=False, ticket_role=False, view_role=False, guild_owner=True, claim=None, claim_staff=True, members=False)
    @ticket.command(name="open")
    async def command_open(self, ctx: commands.Context, *, reason: typing.Optional[str]="No reason provided."):
        """Open an existing ticket.
        """
        ticket = await self.bot.get_cog("TicketTool").get_ticket(ctx.channel)
        ticket.reason = reason
        await ticket.open(ctx.author)
        await ctx.tick()

    @decorator(enable_check=False, ticket_check=True, status="open", ticket_owner=True, admin_role=True, support_role=True, ticket_role=False, view_role=False, guild_owner=True, claim=None, claim_staff=True, members=False)
    @ticket.command(name="close")
    async def command_close(self, ctx: commands.Context, confirmation: typing.Optional[bool]=None, *, reason: typing.Optional[str]="No reason provided."):
        """Close an existing ticket.
        """
        ticket = await self.bot.get_cog("TicketTool").get_ticket(ctx.channel)
        config = await self.bot.get_cog("TicketTool").get_config(ticket.guild)
        if confirmation is None:
            config = await self.bot.get_cog("TicketTool").get_config(ticket.guild)
            confirmation = not config["close_confirmation"]
        if not confirmation:
            embed: discord.Embed = discord.Embed()
            embed.title = _("Do you really want to close the ticket {ticket.id}?").format(**locals())
            embed.color = config["color"]
            embed.set_author(name=ctx.author.name, url=ctx.author.display_avatar if self.cogsutils.is_dpy2 else ctx.author.avatar_url, icon_url=ctx.author.display_avatar if self.cogsutils.is_dpy2 else ctx.author.avatar_url)
            response = await self.cogsutils.ConfirmationAsk(ctx, embed=embed)
            if not response:
                return
        ticket.reason = reason
        await ticket.close(ctx.author)
        await ctx.tick()

    @decorator(enable_check=False, ticket_check=True, status=None, ticket_owner=True, admin_role=True, support_role=True, ticket_role=False, view_role=False, guild_owner=True, claim=None, claim_staff=True, members=False)
    @ticket.command(name="rename")
    async def command_rename(self, ctx: commands.Context, new_name: str, *, reason: typing.Optional[str]="No reason provided."):
        """Rename an existing ticket.
        """
        ticket = await self.bot.get_cog("TicketTool").get_ticket(ctx.channel)
        ticket.reason = reason
        await ticket.rename(new_name, ctx.author)
        await ctx.tick()

    @decorator(enable_check=False, ticket_check=True, status=None, ticket_owner=True, admin_role=True, support_role=False, ticket_role=False, view_role=False, guild_owner=True, claim=None, claim_staff=True, members=False)
    @ticket.command(name="delete")
    async def command_delete(self, ctx: commands.Context, confirmation: typing.Optional[bool]=False, *, reason: typing.Optional[str]="No reason provided."):
        """Delete an existing ticket.
        If a log channel is defined, an html file containing all the messages of this ticket will be generated.
        (Attachments are not supported, as they are saved with their Discord link)
        """
        ticket = await self.bot.get_cog("TicketTool").get_ticket(ctx.channel)
        config = await self.bot.get_cog("TicketTool").get_config(ticket.guild)
        if not confirmation:
            embed: discord.Embed = discord.Embed()
            embed.title = _("Do you really want to delete all the messages of the ticket {ticket.id}?").format(**locals())
            embed.description = _("If a log channel is defined, an html file containing all the messages of this ticket will be generated. (Attachments are not supported, as they are saved with their Discord link)").format(**locals())
            embed.color = config["color"]
            embed.set_author(name=ctx.author.name, url=ctx.author.display_avatar if self.cogsutils.is_dpy2 else ctx.author.avatar_url, icon_url=ctx.author.display_avatar if self.cogsutils.is_dpy2 else ctx.author.avatar_url)
            response = await self.cogsutils.ConfirmationAsk(ctx, embed=embed)
            if not response:
                return
        ticket.reason = reason
        await ticket.delete(ctx.author)

    @decorator(enable_check=False, ticket_check=True, status="open", ticket_owner=False, admin_role=True, support_role=True, ticket_role=False, view_role=False, guild_owner=True, claim=False, claim_staff=False, members=False)
    @ticket.command(name="claim")
    async def command_claim(self, ctx: commands.Context, member: typing.Optional[discord.Member]=None, *, reason: typing.Optional[str]="No reason provided."):
        """Claim an existing ticket.
        """
        ticket = await self.bot.get_cog("TicketTool").get_ticket(ctx.channel)
        ticket.reason = reason
        if member is None:
            member = ctx.author
        await ticket.claim_ticket(member, ctx.author)
        await ctx.tick()

    @decorator(enable_check=False, ticket_check=True, status=None, ticket_owner=False, admin_role=True, support_role=False, ticket_role=False, view_role=False, guild_owner=True, claim=True, claim_staff=True, members=False)
    @ticket.command(name="unclaim")
    async def command_unclaim(self, ctx: commands.Context, *, reason: typing.Optional[str]="No reason provided."):
        """Unclaim an existing ticket.
        """
        ticket = await self.bot.get_cog("TicketTool").get_ticket(ctx.channel)
        ticket.reason = reason
        await ticket.unclaim_ticket(ticket.claim, ctx.author)
        await ctx.tick()

    @decorator(enable_check=False, ticket_check=True, status="open", ticket_owner=True, admin_role=True, support_role=False, ticket_role=False, view_role=False, guild_owner=True, claim=None, claim_staff=False, members=False)
    @ticket.command(name="owner")
    async def command_owner(self, ctx: commands.Context, new_owner: discord.Member, *, reason: typing.Optional[str]="No reason provided."):
        """Change the owner of an existing ticket.
        """
        ticket = await self.bot.get_cog("TicketTool").get_ticket(ctx.channel)
        ticket.reason = reason
        if new_owner is None:
            new_owner = ctx.author
        await ticket.change_owner(new_owner, ctx.author)
        await ctx.tick()

    @decorator(enable_check=False, ticket_check=True, status="open", ticket_owner=True, admin_role=True, support_role=False, ticket_role=False, view_role=False, guild_owner=True, claim=None, claim_staff=True, members=False)
    @ticket.command(name="add")
    async def command_add(self, ctx: commands.Context, member: discord.Member, *, reason: typing.Optional[str]="No reason provided."):
        """Add a member to an existing ticket.
        """
        ticket = await self.bot.get_cog("TicketTool").get_ticket(ctx.channel)
        ticket.reason = reason
        await ticket.add_member(member, ctx.author)
        await ctx.tick()

    @decorator(enable_check=False, ticket_check=True, status=None, ticket_owner=True, admin_role=True, support_role=False, ticket_role=False, view_role=False, guild_owner=True, claim=None, claim_staff=True, members=False)
    @ticket.command(name="remove")
    async def command_remove(self, ctx: commands.Context, member: discord.Member, *, reason: typing.Optional[str]="No reason provided."):
        """Remove a member to an existing ticket.
        """
        ticket = await self.bot.get_cog("TicketTool").get_ticket(ctx.channel)
        ticket.reason = reason
        await ticket.remove_member(member, ctx.author)
        await ctx.tick()

    if CogsUtils().is_dpy2:
        async def on_button_interaction(self, view: Buttons, interaction: discord.Interaction):
            # if "component_type" in interaction.data:
            #     if not interaction.data["component_type"] == 2:
            #         return
            if interaction.data["custom_id"] == "close_ticket_button":
                permissions = interaction.channel.permissions_for(interaction.user)
                if not permissions.read_messages and not permissions.send_messages:
                    return
                permissions = interaction.channel.permissions_for(interaction.guild.me)
                if not permissions.read_messages and not permissions.read_message_history:
                    return
                ticket = await self.bot.get_cog("TicketTool").get_ticket(interaction.channel)
                if ticket is not None:
                    if ticket.status == "open":
                        async for message in interaction.channel.history(limit=1):
                            p = await self.bot.get_valid_prefixes()
                            p = p[0]
                            msg = copy(message)
                            msg.author = interaction.user
                            msg.content = f"{p}ticket close"
                            context = await interaction.client.get_context(msg)
                            await interaction.client.invoke(context)
                            await interaction.response.send_message(_("You have chosen to close this ticket. If this ticket is not closed, you do not have the necessary permissions.").format(**locals()), ephemeral=True)
            if interaction.data["custom_id"] == "claim_ticket_button":
                permissions = interaction.channel.permissions_for(interaction.user)
                if not permissions.read_messages and not permissions.send_messages:
                    return
                permissions = interaction.channel.permissions_for(interaction.guild.me)
                if not permissions.read_messages and not permissions.read_message_history:
                    return
                ticket = await self.bot.get_cog("TicketTool").get_ticket(interaction.channel)
                if ticket is not None:
                    if ticket.claim is None:
                        async for message in interaction.channel.history(limit=1):
                            p = await self.bot.get_valid_prefixes()
                            p = p[0]
                            msg = copy(message)
                            msg.author = interaction.user
                            msg.content = f"{p}ticket claim"
                            context = await interaction.client.get_context(msg)
                            await interaction.client.invoke(context)
                            await interaction.response.send_message(_("You have chosen to claim this ticket. If this ticket is not claimed, you do not have the necessary permissions.").format(**locals()), ephemeral=True)
            if interaction.data["custom_id"] == "create_ticket_button":
                permissions = interaction.channel.permissions_for(interaction.user)
                if not permissions.read_messages and not permissions.send_messages:
                    return
                permissions = interaction.channel.permissions_for(interaction.guild.me)
                if not permissions.read_messages and not permissions.read_message_history:
                    return
                async for message in interaction.channel.history(limit=1):
                    p = await self.bot.get_valid_prefixes()
                    p = p[0]
                    msg = copy(message)
                    msg.author = interaction.user
                    msg.content = f"{p}ticket create"
                    context = await interaction.client.get_context(msg)
                    await interaction.client.invoke(context)
                    await interaction.response.send_message(_("You have chosen to create a ticket.").format(**locals()), ephemeral=True)
            return
    else:
        @commands.Cog.listener()
        async def on_button_click(self, inter):
            if inter.clicked_button.custom_id == "close_ticket_button":
                permissions = inter.channel.permissions_for(inter.author)
                if not permissions.read_messages and not permissions.send_messages:
                    return
                permissions = inter.channel.permissions_for(inter.guild.me)
                if not permissions.read_messages and not permissions.read_message_history:
                    return
                ticket = await self.bot.get_cog("TicketTool").get_ticket(inter.channel)
                if ticket is not None:
                    if ticket.status == "open":
                        async for message in inter.channel.history(limit=1):
                            p = await self.bot.get_valid_prefixes()
                            p = p[0]
                            msg = copy(message)
                            msg.author = inter.author
                            msg.content = f"{p}ticket close"
                            inter.bot.dispatch("message", msg)
                        await inter.send(_("You have chosen to close this ticket. If this ticket is not closed, you do not have the necessary permissions.").format(**locals()), ephemeral=True)
            if inter.clicked_button.custom_id == "claim_ticket_button":
                permissions = inter.channel.permissions_for(inter.author)
                if not permissions.read_messages and not permissions.send_messages:
                    return
                permissions = inter.channel.permissions_for(inter.guild.me)
                if not permissions.read_messages and not permissions.read_message_history:
                    return
                ticket = await self.bot.get_cog("TicketTool").get_ticket(inter.channel)
                if ticket is not None:
                    if ticket.claim is None:
                        async for message in inter.channel.history(limit=1):
                            p = await self.bot.get_valid_prefixes()
                            p = p[0]
                            msg = copy(message)
                            msg.author = inter.author
                            msg.content = f"{p}ticket claim"
                            inter.bot.dispatch("message", msg)
                        await inter.send(_("You have chosen to claim this ticket. If this ticket is not claimed, you do not have the necessary permissions.").format(**locals()), ephemeral=True)
            if inter.clicked_button.custom_id == "create_ticket_button":
                permissions = inter.channel.permissions_for(inter.author)
                if not permissions.read_messages and not permissions.send_messages:
                    return
                permissions = inter.channel.permissions_for(inter.guild.me)
                if not permissions.read_messages and not permissions.read_message_history:
                    return
                async for message in inter.channel.history(limit=1):
                    p = await self.bot.get_valid_prefixes()
                    p = p[0]
                    msg = copy(message)
                    msg.author = inter.author
                    msg.content = f"{p}ticket create"
                    inter.bot.dispatch("message", msg)
                await inter.send(_("You have chosen to create a ticket.").format(**locals()), ephemeral=True)
            return

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, old_channel: discord.abc.GuildChannel):
        data = await self.bot.get_cog("TicketTool").config.guild(old_channel.guild).tickets.all()
        if str(old_channel.id) not in data:
            return
        del data[str(old_channel.id)]
        await self.bot.get_cog("TicketTool").config.guild(old_channel.guild).tickets.set(data)
        return

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        config = await self.bot.get_cog("TicketTool").get_config(member.guild)
        data = await self.bot.get_cog("TicketTool").config.guild(member.guild).tickets.all()
        if config["close_on_leave"]:
            for channel in data:
                channel = member.guild.get_channel(int(channel))
                ticket = await self.bot.get_cog("TicketTool").get_ticket(channel)
                if ticket.owner == member and ticket.status == "open":
                    await ticket.close(ticket.guild.me)
        return

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if not payload.guild_id:
            return
        guild = payload.member.guild
        channel = guild.get_channel(payload.channel_id)
        member = guild.get_member(payload.user_id)
        if member == guild.me or member.bot:
            return
        config = await self.bot.get_cog("TicketTool").get_config(guild)
        if config["enable"]:
            if config["create_on_react"]:
                if str(payload.emoji) == str("🎟️"):
                    permissions = channel.permissions_for(member)
                    if not permissions.read_messages and not permissions.send_messages:
                        return
                    permissions = channel.permissions_for(guild.me)
                    if not permissions.read_messages and not permissions.read_message_history:
                        return
                    async for message in channel.history(limit=1):
                        p = await self.bot.get_valid_prefixes()
                        p = p[0]
                        msg = copy(message)
                        msg.author = member
                        msg.content = f"{p}ticket create"
                        self.bot.dispatch("message", msg)
        return

class Ticket:
    """Representation of a ticket"""

    def __init__(self,
                bot,
                id,
                owner,
                guild,
                channel,
                claim,
                created_by,
                opened_by,
                closed_by,
                deleted_by,
                renamed_by,
                members,
                created_at,
                opened_at,
                closed_at,
                deleted_at,
                renamed_at,
                status,
                reason,
                logs_messages,
                save_data,
                first_message):
        self.bot: Red = bot
        self.id: int = id
        self.owner: discord.Member = owner
        self.guild: discord.Guild = guild
        self.channel: discord.TextChannel = channel
        self.claim: discord.Member = claim
        self.created_by: discord.Member = created_by
        self.opened_by: discord.Member = opened_by
        self.closed_by: discord.Member = closed_by
        self.deleted_by: discord.Member = deleted_by
        self.renamed_by: discord.Member = renamed_by
        self.members: typing.List[discord.Member] = members
        self.created_at: datetime.datetime = created_at
        self.opened_at: datetime.datetime = opened_at
        self.closed_at: datetime.datetime = closed_at
        self.deleted_at: datetime.datetime = deleted_at
        self.renamed_at: datetime.datetime = renamed_at
        self.status: str = status
        self.reason: str = reason
        self.logs_messages: bool = logs_messages
        self.save_data: bool = save_data
        self.first_message: discord.Message = first_message

    @staticmethod
    def instance(ctx, reason: typing.Optional[str]=_("No reason provided.").format(**locals())):
        ticket = Ticket(
            bot=ctx.bot,
            id=None,
            owner=ctx.author,
            guild=ctx.guild,
            channel=None,
            claim=None,
            created_by=ctx.author,
            opened_by=ctx.author,
            closed_by=None,
            deleted_by=None,
            renamed_by=None,
            members=[],
            created_at=datetime.datetime.now(),
            opened_at=None,
            closed_at=None,
            deleted_at=None,
            renamed_at=None,
            status="open",
            reason=reason,
            logs_messages=True,
            save_data=True,
            first_message=None,
        )
        return ticket

    @staticmethod
    def from_json(json: dict, bot: Red):
        ticket = Ticket(
            bot=bot,
            id=json["id"],
            owner=json["owner"],
            guild=json["guild"],
            channel=json["channel"],
            claim=json["claim"],
            created_by=json["created_by"],
            opened_by=json["opened_by"],
            closed_by=json["closed_by"],
            deleted_by=json["deleted_by"],
            renamed_by=json["renamed_by"],
            members=json["members"],
            created_at=json["created_at"],
            opened_at=json["opened_at"],
            closed_at=json["closed_at"],
            deleted_at=json["deleted_at"],
            renamed_at=json["renamed_at"],
            status=json["status"],
            reason=json["reason"],
            logs_messages=json["logs_messages"],
            save_data=json["save_data"],
            first_message=json["first_message"],
        )
        return ticket

    async def save(ticket):
        if not ticket.save_data:
            return
        bot = ticket.bot
        guild = ticket.guild
        channel = ticket.channel
        ticket.bot = None
        if ticket.owner is not None:
            ticket.owner = int(ticket.owner.id)
        if ticket.guild is not None:
            ticket.guild = int(ticket.guild.id)
        if ticket.channel is not None:
            ticket.channel = int(ticket.channel.id)
        if ticket.claim is not None:
            ticket.claim = ticket.claim.id
        if ticket.created_by is not None:
            ticket.created_by = int(ticket.created_by.id)
        if ticket.opened_by is not None:
            ticket.opened_by = int(ticket.opened_by.id)
        if ticket.closed_by is not None:
            ticket.closed_by = int(ticket.closed_by.id)
        if ticket.deleted_by is not None:
            ticket.deleted_by = int(ticket.deleted_by.id)
        if ticket.renamed_by is not None:
            ticket.renamed_by = int(ticket.renamed_by.id)
        members = ticket.members
        ticket.members = []
        for m in members:
            ticket.members.append(int(m.id))
        if ticket.created_at is not None:
            ticket.created_at = float(datetime.datetime.timestamp(ticket.created_at))
        if ticket.opened_at is not None:
            ticket.opened_at = float(datetime.datetime.timestamp(ticket.opened_at))
        if ticket.closed_at is not None:
            ticket.closed_at = float(datetime.datetime.timestamp(ticket.closed_at))
        if ticket.deleted_at is not None:
            ticket.deleted_at = float(datetime.datetime.timestamp(ticket.deleted_at))
        if ticket.renamed_at is not None:
            ticket.renamed_at = float(datetime.datetime.timestamp(ticket.renamed_at))
        if ticket.first_message is not None:
            ticket.first_message = int(ticket.first_message.id)
        json = ticket.__dict__
        data = await bot.get_cog("TicketTool").config.guild(guild).tickets.all()
        data[str(channel.id)] = json
        await bot.get_cog("TicketTool").config.guild(guild).tickets.set(data)
        return data

    async def create(ticket, name: typing.Optional[str]="ticket"):
        config = await ticket.bot.get_cog("TicketTool").get_config(ticket.guild)
        logschannel = config["logschannel"]
        overwrites = await utils(ticket.bot).get_overwrites(ticket)
        emoji_open = config["emoji_open"]
        ping_role = config["ping_role"]
        ticket.id = config["last_nb"] + 1
        name = f"{emoji_open}-{name}-{ticket.id}"
        reason = await ticket.bot.get_cog("TicketTool").get_audit_reason(guild=ticket.guild, author=ticket.created_by, reason=_("Creating the ticket {ticket.id}.").format(**locals()))
        ticket.channel = await ticket.guild.create_text_channel(
                            name,
                            overwrites=overwrites,
                            category=config["category_open"],
                            topic=ticket.reason,
                            reason=reason,
                         )
        if config["create_modlog"]:
            await ticket.bot.get_cog("TicketTool").create_modlog(ticket, "ticket_created", reason)
        if ticket.logs_messages:
            if CogsUtils().is_dpy2:
                view = Buttons(timeout=None, buttons=[{"style": 2, "label": _("Close").format(**locals()), "emoji": "🔒", "custom_id": "close_ticket_button", "disabled": False}, {"style": 2, "label": _("Claim").format(**locals()), "emoji": "🙋‍♂️", "custom_id": "claim_ticket_button", "disabled": False}], function=ticket.bot.get_cog("TicketTool").on_button_interaction, infinity=True)
            else:
                buttons = ActionRow(
                    Button(
                        style=ButtonStyle.grey,
                        label=_("Close").format(**locals()),
                        emoji="🔒",
                        custom_id="close_ticket_button",
                        disabled=False
                    ),
                    Button(
                        style=ButtonStyle.grey,
                        label=_("Claim").format(**locals()),
                        emoji="🙋‍♂️",
                        custom_id="claim_ticket_button",
                        disabled=False
                    )
                )
            if ping_role is not None:
                optionnal_ping = f" ||{ping_role.mention}||"
            else:
                optionnal_ping = ""
            embed = await ticket.bot.get_cog("TicketTool").get_embed_important(ticket, False, author=ticket.created_by, title=_("Ticket Created").format(**locals()), description=_("Thank you for creating a ticket on this server!").format(**locals()))
            if CogsUtils().is_dpy2:
                ticket.first_message = await ticket.channel.send(f"{ticket.created_by.mention}{optionnal_ping}", embed=embed, view=view)
            else:
                ticket.first_message = await ticket.channel.send(f"{ticket.created_by.mention}{optionnal_ping}", embed=embed, components=[buttons])
            if logschannel is not None:
                embed = await ticket.bot.get_cog("TicketTool").get_embed_important(ticket, True, author=ticket.created_by, title=_("Ticket Created").format(**locals()), description=_("The ticket was created by {ticket.created_by}.").format(**locals()))
                await logschannel.send(_("Report on the creation of the ticket {ticket.id}.").format(**locals()), embed=embed)
        await ticket.bot.get_cog("TicketTool").config.guild(ticket.guild).settings.last_nb.set(ticket.id)
        if config["ticket_role"] is not None:
            if ticket.owner:
                try:
                    ticket.owner.add_roles(config["ticket_role"], reason=reason)
                except discord.HTTPException:
                    pass
        await ticket.save()
        return ticket

    async def export(ticket):
        if ticket.channel:
            transcript = await chat_exporter.export(channel=ticket.channel, limit=None, tz_info="UTC", guild=ticket.guild, bot=ticket.bot)
            if transcript is not None:
                transcript_file = discord.File(io.BytesIO(transcript.encode()),
                                  filename=f"transcript-ticket-{ticket.id}.html")
                return transcript_file
        return None

    async def open(ticket, author: typing.Optional[discord.Member]=None):
        config = await ticket.bot.get_cog("TicketTool").get_config(ticket.guild)
        reason = await ticket.bot.get_cog("TicketTool").get_audit_reason(guild=ticket.guild, author=author, reason=_("Opening the ticket {ticket.id}.").format(**locals()))
        logschannel = config["logschannel"]
        emoji_open = config["emoji_open"]
        emoji_close = config["emoji_close"]
        ticket.status = "open"
        ticket.opened_by = author
        ticket.opened_at = datetime.datetime.now()
        ticket.closed_by = None
        ticket.closed_at = None
        new_name = f"{ticket.channel.name}"
        new_name = new_name.replace(f"{emoji_close}-", "", 1)
        new_name = f"{emoji_open}-{new_name}"
        await ticket.channel.edit(name=new_name, category=config["category_open"], reason=reason)
        if ticket.logs_messages:
            embed = await ticket.bot.get_cog("TicketTool").get_embed_action(ticket, author=ticket.opened_by, action=_("Ticket Opened").format(**locals()))
            await ticket.channel.send(embed=embed)
            if logschannel is not None:
                embed = await ticket.bot.get_cog("TicketTool").get_embed_important(ticket, True, author=ticket.opened_by, title=_("Ticket Opened").format(**locals()), description=_("The ticket was opened by {ticket.opened_by}.").format(**locals()))
                await logschannel.send(_("Report on the close of the ticket {ticket.id}.").format(**locals()), embed=embed)
        if ticket.first_message is not None:
            try:
                if CogsUtils().is_dpy2:
                    view = Buttons(timeout=None, buttons=[{"style": 2, "label": _("Close").format(**locals()), "emoji": "🔒", "custom_id": "close_ticket_button", "disabled": False}, {"style": 2, "label": _("Claim").format(**locals()), "emoji": "🙋‍♂️", "custom_id": "claim_ticket_button", "disabled": False}], function=ticket.bot.get_cog("TicketTool").on_button_interaction, infinity=True)
                    ticket.first_message = await ticket.channel.fetch_message(int(ticket.first_message.id))
                    await ticket.first_message.edit(view=view)
                else:
                    buttons = ActionRow(
                        Button(
                            style=ButtonStyle.grey,
                            label=_("Close").format(**locals()),
                            emoji="🔒",
                            custom_id="close_ticket_button",
                            disabled=False
                        ),
                        Button(
                            style=ButtonStyle.grey,
                            label=_("Claim").format(**locals()),
                            emoji="🙋‍♂️",
                            custom_id="claim_ticket_button",
                            disabled=False
                        )
                    )
                    ticket.first_message = await ticket.channel.fetch_message(int(ticket.first_message.id))
                    await ticket.first_message.edit(components=[buttons])
            except discord.HTTPException:
                pass
        await ticket.save()
        return ticket

    async def close(ticket, author: typing.Optional[discord.Member]=None):
        config = await ticket.bot.get_cog("TicketTool").get_config(ticket.guild)
        reason = await ticket.bot.get_cog("TicketTool").get_audit_reason(guild=ticket.guild, author=author, reason=f"Closing the ticket {ticket.id}.")
        logschannel = config["logschannel"]
        emoji_open = config["emoji_open"]
        emoji_close = config["emoji_close"]
        ticket.status = "close"
        ticket.closed_by = author
        ticket.closed_at = datetime.datetime.now()
        new_name = f"{ticket.channel.name}"
        new_name = new_name.replace(f"{emoji_open}-", "", 1)
        new_name = f"{emoji_close}-{new_name}"
        await ticket.channel.edit(name=new_name, category=config["category_close"], reason=reason)
        if ticket.logs_messages:
            embed = await ticket.bot.get_cog("TicketTool").get_embed_action(ticket, author=ticket.closed_by, action="Ticket Closed")
            await ticket.channel.send(embed=embed)
            if logschannel is not None:
                embed = await ticket.bot.get_cog("TicketTool").get_embed_important(ticket, True, author=ticket.closed_by, title="Ticket Closed", description=f"The ticket was closed by {ticket.closed_by}.")
                await logschannel.send(_("Report on the close of the ticket {ticket.id}.").format(**locals()), embed=embed)
        if ticket.first_message is not None:
            try:
                if CogsUtils().is_dpy2:
                    view = Buttons(timeout=None, buttons=[{"style": 2, "label": _("Close").format(**locals()), "emoji": "🔒", "custom_id": "close_ticket_button", "disabled": True}, {"style": 2, "label": _("Claim").format(**locals()), "emoji": "🙋‍♂️", "custom_id": "claim_ticket_button", "disabled": True}], function=ticket.bot.get_cog("TicketTool").on_button_interaction, infinity=True)
                    ticket.first_message = await ticket.channel.fetch_message(int(ticket.first_message.id))
                    await ticket.first_message.edit(view=view)
                else:
                    buttons = ActionRow(
                        Button(
                            style=ButtonStyle.grey,
                            label=_("Close").format(**locals()),
                            emoji="🔒",
                            custom_id="close_ticket_button",
                            disabled=True
                        ),
                        Button(
                            style=ButtonStyle.grey,
                            label=_("Claim").format(**locals()),
                            emoji="🙋‍♂️",
                            custom_id="claim_ticket_button",
                            disabled=True
                        )
                    )
                    ticket.first_message = await ticket.channel.fetch_message(int(ticket.first_message.id))
                    await ticket.first_message.edit(components=[buttons])
            except discord.HTTPException:
                pass
        await ticket.save()
        return ticket

    async def rename(ticket, new_name: str, author: typing.Optional[discord.Member]=None):
        config = await ticket.bot.get_cog("TicketTool").get_config(ticket.guild)
        reason = await ticket.bot.get_cog("TicketTool").get_audit_reason(guild=ticket.guild, author=author, reason=_("Renaming the ticket {ticket.id}. (`{ticket.channel.name}` to `{new_name}`)").format(**locals()))
        emoji_open = config["emoji_open"]
        emoji_close = config["emoji_close"]
        ticket.renamed_by = author
        ticket.renamed_at = datetime.datetime.now()
        if ticket.status == "open":
            new_name = f"{emoji_open}-{new_name}"
        elif ticket.status == "close":
            new_name = f"{emoji_close}-{new_name}"
        else:
            new_name = f"{new_name}"
        await ticket.channel.edit(name=new_name, reason=reason)
        if ticket.logs_messages:
            embed = await ticket.bot.get_cog("TicketTool").get_embed_action(ticket, author=ticket.renamed_by, action=_("Ticket Renamed.").format(**locals()))
            await ticket.channel.send(embed=embed)
        await ticket.save()
        return ticket

    async def delete(ticket, author: typing.Optional[discord.Member]=None):
        config = await ticket.bot.get_cog("TicketTool").get_config(ticket.guild)
        logschannel = config["logschannel"]
        reason = await ticket.bot.get_cog("TicketTool").get_audit_reason(guild=ticket.guild, author=author, reason=_("Deleting the ticket {ticket.id}.").format(**locals()))
        ticket.deleted_by = author
        ticket.deleted_at = datetime.datetime.now()
        if ticket.logs_messages:
            if logschannel is not None:
                embed = await ticket.bot.get_cog("TicketTool").get_embed_important(ticket, True, author=ticket.deleted_by, title=_("Ticket Deleted").format(**locals()), description=_("The ticket was deleted by {ticket.deleted_by}.").format(**locals()))
                transcript = await chat_exporter.export(channel=ticket.channel, limit=None, tz_info="UTC", guild=ticket.guild, bot=ticket.bot)
                if transcript is not None:
                    file = discord.File(io.BytesIO(transcript.encode()),
                                        filename=f"transcript-ticket-{ticket.id}.html")
                else:
                    file = None
                await logschannel.send(_("Report on the deletion of the ticket {ticket.id}.").format(**locals()), embed=embed, file=file)
        await ticket.channel.delete(reason=reason)
        data = await ticket.bot.get_cog("TicketTool").config.guild(ticket.guild).tickets.all()
        try:
            del data[str(ticket.channel.id)]
        except ValueError:
            pass
        await ticket.bot.get_cog("TicketTool").config.guild(ticket.guild).tickets.set(data)
        return ticket

    async def claim_ticket(ticket, member: discord.Member, author: typing.Optional[discord.Member]=None):
        config = await ticket.bot.get_cog("TicketTool").get_config(ticket.guild)
        reason = await ticket.bot.get_cog("TicketTool").get_audit_reason(guild=ticket.guild, author=author, reason=_("Claiming the ticket {ticket.id}.").format(**locals()))
        if member.bot:
            await ticket.channel.send(_("A bot cannot claim a ticket.").format(**locals()))
            return
        ticket.claim = member
        overwrites = ticket.channel.overwrites
        overwrites[member] = (
            discord.PermissionOverwrite(
                attach_files=True,
                read_messages=True,
                read_message_history=True,
                send_messages=True,
            )
        )
        if config["support_role"] is not None:
            overwrites[config["support_role"]] = (
                discord.PermissionOverwrite(
                    view_channel=True,
                    read_messages=True,
                    read_message_history=True,
                    send_messages=False,
                    attach_files=True,
                )
            )
        await ticket.channel.edit(overwrites=overwrites, reason=reason)
        if ticket.first_message is not None:
            try:
                if CogsUtils().is_dpy2:
                    view = Buttons(timeout=None, buttons=[{"style": 2, "label": _("Close").format(**locals()), "emoji": "🔒", "custom_id": "close_ticket_button", "disabled": False if ticket.status == "open" else True}, {"style": 2, "label": _("Claim").format(**locals()), "emoji": "🙋‍♂️", "custom_id": "claim_ticket_button", "disabled": True}], function=ticket.bot.get_cog("TicketTool").on_button_interaction, infinity=True)
                    ticket.first_message = await ticket.channel.fetch_message(int(ticket.first_message.id))
                    await ticket.first_message.edit(view=view)
                else:
                    buttons = ActionRow(
                        Button(
                            style=ButtonStyle.grey,
                            label=_("Close").format(**locals()),
                            emoji="🔒",
                            custom_id="close_ticket_button",
                            disabled=False if ticket.status == "open" else True
                        ),
                        Button(
                            style=ButtonStyle.grey,
                            label=_("Claim").format(**locals()),
                            emoji="🙋‍♂️",
                            custom_id="claim_ticket_button",
                            disabled=True
                        )
                    )
                    ticket.first_message = await ticket.channel.fetch_message(int(ticket.first_message.id))
                    await ticket.first_message.edit(components=[buttons])
            except discord.HTTPException:
                pass
        await ticket.save()
        return ticket

    async def unclaim_ticket(ticket, member: discord.Member, author: typing.Optional[discord.Member]=None):
        config = await ticket.bot.get_cog("TicketTool").get_config(ticket.guild)
        reason = await ticket.bot.get_cog("TicketTool").get_audit_reason(guild=ticket.guild, author=author, reason=_("Claiming the ticket {ticket.id}.").format(**locals()))
        ticket.claim = None
        if config["support_role"] is not None:
            overwrites = ticket.channel.overwrites
            overwrites[config["support_role"]] = (
                discord.PermissionOverwrite(
                    view_channel=True,
                    read_messages=True,
                    read_message_history=True,
                    send_messages=True,
                    attach_files=True,
                )
            )
            await ticket.channel.edit(overwrites=overwrites, reason=reason)
        await ticket.channel.set_permissions(member, overwrite=None, reason=reason)
        if ticket.first_message is not None:
            try:
                if CogsUtils().is_dpy2:
                    view = Buttons(timeout=None, buttons=[{"style": 2, "label": _("Close").format(**locals()), "emoji": "🔒", "custom_id": "close_ticket_button", "disabled": False if ticket.status == "open" else True}, {"style": 2, "label": _("Claim").format(**locals()), "emoji": "🙋‍♂️", "custom_id": "claim_ticket_button", "disabled": True}], function=ticket.bot.get_cog("TicketTool").on_button_interaction, infinity=True)
                    ticket.first_message = await ticket.channel.fetch_message(int(ticket.first_message.id))
                    await ticket.first_message.edit(view=view)
                else:
                    buttons = ActionRow(
                        Button(
                            style=ButtonStyle.grey,
                            label=_("Close").format(**locals()),
                            emoji="🔒",
                            custom_id="close_ticket_button",
                            disabled=False if ticket.status == "open" else True
                        ),
                        Button(
                            style=ButtonStyle.grey,
                            label=_("Claim").format(**locals()),
                            emoji="🙋‍♂️",
                            custom_id="claim_ticket_button",
                            disabled=False
                        )
                    )
                    ticket.first_message = await ticket.channel.fetch_message(int(ticket.first_message.id))
                    await ticket.first_message.edit(components=[buttons])
            except discord.HTTPException:
                pass
        await ticket.save()
        return ticket

    async def change_owner(ticket, member: discord.Member, author: typing.Optional[discord.Member]=None):
        config = await ticket.bot.get_cog("TicketTool").get_config(ticket.guild)
        reason = await ticket.bot.get_cog("TicketTool").get_audit_reason(guild=ticket.guild, author=author, reason=_("Changing owner of the ticket {ticket.id}.").format(**locals()))
        if member.bot:
            await ticket.channel.send(_("You cannot transfer ownership of a ticket to a bot.").format(**locals()))
            return
        if config["ticket_role"] is not None:
            if ticket.owner:
                try:
                    ticket.owner.remove_roles(config["ticket_role"], reason=reason)
                except discord.HTTPException:
                    pass
        ticket.members.append(ticket.owner)
        ticket.owner = member
        ticket.remove(ticket.owner)
        overwrites = ticket.channel.overwrites
        overwrites[member] = (
            discord.PermissionOverwrite(
                attach_files=True,
                read_messages=True,
                read_message_history=True,
                send_messages=True,
            )
        )
        await ticket.channel.edit(overwrites=overwrites, reason=reason)
        if config["ticket_role"] is not None:
            if ticket.owner:
                try:
                    ticket.owner.add_roles(config["ticket_role"], reason=reason)
                except discord.HTTPException:
                    pass
        if ticket.logs_messages:
            embed = await ticket.bot.get_cog("TicketTool").get_embed_action(ticket, author=author, action=_("Owner Modified.").format(**locals()))
            await ticket.channel.send(embed=embed)
        await ticket.save()
        return ticket

    async def add_member(ticket, member: discord.Member, author: typing.Optional[discord.Member]=None):
        reason = await ticket.bot.get_cog("TicketTool").get_audit_reason(guild=ticket.guild, author=author, reason=_("Adding a member to the ticket {ticket.id}.").format(**locals()))
        if member.bot:
            await ticket.channel.send(_("You cannot add a bot to a ticket.").format(**locals()))
            return
        if member in ticket.members:
            await ticket.channel.send(_("This member already has access to this ticket.").format(**locals()))
            return
        if member == ticket.owner:
            await ticket.channel.send(_("This member is already the owner of this ticket.").format(**locals()))
            return
        ticket.members.append(member)
        overwrites = ticket.channel.overwrites
        overwrites[member] = (
            discord.PermissionOverwrite(
                attach_files=True,
                read_messages=True,
                read_message_history=True,
                send_messages=True,
            )
        )
        await ticket.channel.edit(overwrites=overwrites, reason=reason)
        if ticket.logs_messages:
            embed = await ticket.bot.get_cog("TicketTool").get_embed_action(ticket, author=author, action=_("Member {member.mention} ({member.id}) Added.").format(**locals()))
            await ticket.channel.send(embed=embed)
        await ticket.save()
        return ticket

    async def remove_member(ticket, member: discord.Member, author: typing.Optional[discord.Member]=None):
        reason = await ticket.bot.get_cog("TicketTool").get_audit_reason(guild=ticket.guild, author=author, reason=_("Removing a member to the ticket {ticket.id}.").format(**locals()))
        if member.bot:
            await ticket.channel.send("You cannot remove a bot to a ticket.")
            return
        if member not in ticket.members:
            await ticket.channel.send("This member is not in the list of those authorised to access the ticket.")
            return
        ticket.members.remove(member)
        await ticket.channel.set_permissions(member, overwrite=None, reason=reason)
        if ticket.logs_messages:
            embed = await ticket.bot.get_cog("TicketTool").get_embed_action(ticket, author=author, action=_("Member {member.mention} ({member.id}) Removed.").format(**locals()))
            await ticket.channel.send(embed=embed)
        await ticket.save()
        return ticket
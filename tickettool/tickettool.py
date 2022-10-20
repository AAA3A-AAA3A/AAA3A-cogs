from .AAA3A_utils import CogsUtils  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
from redbot.core.bot import Red  # isort:skip
import discord  # isort:skip
import typing  # isort:skip
if CogsUtils().is_dpy2:
    from .AAA3A_utils import Buttons, Dropdown  # isort:skip
else:
    from dislash import ActionRow, Button, ButtonStyle, MessageInteraction  # isort:skip

import asyncio
import datetime
import io

import chat_exporter

from .settings import settings
from .utils import utils

from redbot.core import Config, modlog

# Credits:
# Thanks to @epic guy on Discord for the basic syntax (command groups, commands) and also commands (await ctx.send, await ctx.author.send, await ctx.message.delete())!
# Thanks to @YamiKaitou on Discord for the technique in the init file to load the interaction client only if it is not loaded! Before this fix, when a user clicked on a button, the actions would be launched about 10 times, which caused huge spam and a loop in the channel!
# Thanks to the developers of the cogs I added features to as it taught me how to make a cog! (Chessgame by WildStriker, Captcha by Kreusada, Speak by Epic guy and Rommer by Dav)
# Thanks to all the people who helped me with some commands in the #coding channel of the redbot support server!

_ = Translator("TicketTool", __file__)

if CogsUtils().is_dpy2:
    from functools import partial
    hybrid_command = partial(commands.hybrid_command, with_app_command=False)
    hybrid_group = partial(commands.hybrid_group, with_app_command=False)
else:
    hybrid_command = commands.command
    hybrid_group = commands.group

@cog_i18n(_)
class TicketTool(settings, commands.Cog):
    """A cog to manage a ticket system!"""

    def __init__(self, bot: Red):
        self.bot: Red = bot

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
                "user_can_close": True,
                "color": 0x01d758,
                "thumbnail": "http://www.quidd.it/wp-content/uploads/2017/10/Ticket-add-icon.png",
                "audit_logs": False,
                "close_confirmation": False,
                "emoji_open": "❓",
                "emoji_close": "🔒",
                "dynamic_channel_name": "❓-ticket-{ticket.id}",
                "last_nb": 0000,
                "custom_message": None,
                "embed_button": {
                    "title": "Create a ticket",
                    "description": _("To get help on this server or to make an order for example, you can create a ticket.\n"
                                     "Just use the command `{prefix}ticket create` or click on the button below.\n"
                                     "You can then use the `{prefix}ticket` subcommand to manage your ticket."),
                    "image": None,
                    "placeholder_dropdown": "Choose the reason for open a ticket.",
                    "rename_channel_dropdown": False,
                },
            },
            "tickets": {},
            "dropdowns": {}
        }
        self.config.register_guild(**self.ticket_guild)

        self.cogsutils = CogsUtils(cog=self)
        self.cogsutils._setup()

        if self.cogsutils.is_dpy2:
            asyncio.create_task(self.load_buttons())

    async def load_buttons(self):
        try:
            self.bot.add_view(Buttons(timeout=None, buttons=[{"style": 2, "label": _("Create ticket").format(**locals()), "emoji": "🎟️", "custom_id": "create_ticket_button", "disabled": False}], function=self.on_button_interaction, infinity=True))
            self.bot.add_view(Buttons(timeout=None, buttons=[{"style": 2, "label": _("Close").format(**locals()), "emoji": "🔒", "custom_id": "close_ticket_button", "disabled": False}, {"style": 2, "label": _("Claim").format(**locals()), "emoji": "🙋‍♂️", "custom_id": "claim_ticket_button", "disabled": False}], function=self.on_button_interaction, infinity=True))
        except Exception as e:
            self.log.error("The Buttons View could not be added correctly.", exc_info=e)
        all_guilds = await self.config.all_guilds()
        for guild in all_guilds:
            for dropdown in all_guilds[guild]["dropdowns"]:
                try:
                    self.bot.add_view(Dropdown(timeout=None, placeholder="Choose the reason for open a ticket.", options=[{"label": reason_option["label"], "value": reason_option.get("value", reason_option["label"]), "description": reason_option.get("description", None), "emoji": reason_option["emoji"], "default": False} for reason_option in all_guilds[guild]["dropdowns"][dropdown]], function=self.on_dropdown_interaction, infinity=True, custom_id="create_ticket_dropdown"), message_id=int((str(dropdown).split("-"))[1]))
                except Exception as e:
                    self.log.error(f"The Dropdown View could not be added correctly for the {guild}-{dropdown} message.", exc_info=e)

    async def get_config(self, guild: discord.Guild):
        config = await self.config.guild(guild).settings.all()
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
        config = await self.config.guild(channel.guild).tickets.all()
        if str(channel.id) in config:
            json = config[str(channel.id)]
        else:
            return None
        ticket: Ticket = Ticket.from_json(json, self.bot)
        ticket.bot = self.bot
        ticket.guild = ticket.bot.get_guild(ticket.guild)
        ticket.owner = ticket.guild.get_member(ticket.owner) or ticket.owner
        ticket.channel = ticket.guild.get_channel(ticket.channel)
        ticket.claim = ticket.guild.get_member(ticket.claim)
        ticket.created_by = ticket.guild.get_member(ticket.created_by) or ticket.created_by
        ticket.opened_by = ticket.guild.get_member(ticket.opened_by) or ticket.opened_by
        ticket.closed_by = ticket.guild.get_member(ticket.closed_by) or ticket.closed_by
        ticket.deleted_by = ticket.guild.get_member(ticket.deleted_by) or ticket.deleted_by
        ticket.renamed_by = ticket.guild.get_member(ticket.renamed_by) or ticket.renamed_by
        members = ticket.members
        ticket.members = [channel.guild.get_member(m) for m in members]
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
        config = await self.get_config(guild)
        if author is None or not config["audit_logs"]:
            return f"{reason}"
        else:
            return f"{author.name} ({author.id}) - {reason}"

    async def get_embed_important(self, ticket, more: bool, author: discord.Member, title: str, description: str):
        config = await self.get_config(ticket.guild)
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
            value=f"<@{ticket.owner}> ({ticket.owner})"
            if isinstance(ticket.owner, int)
            else f"{ticket.owner.mention} ({ticket.owner.id})",
        )

        embed.add_field(
            inline=True,
            name=_("Channel:").format(**locals()),
            value=f"{ticket.channel.mention} - {ticket.channel.name} ({ticket.channel.id})")
        if more:
            if ticket.closed_by is not None:
                embed.add_field(
                    inline=False,
                    name=_("Closed by:").format(**locals()),
                    value=f"<@{ticket.closed_by}> ({ticket.closed_by})"
                    if isinstance(ticket.closed_by, int)
                    else f"{ticket.closed_by.mention} ({ticket.closed_by.id})",
                )

            if ticket.deleted_by is not None:
                embed.add_field(
                    inline=True,
                    name=_("Deleted by:").format(**locals()),
                    value=f"<@{ticket.deleted_by}> ({ticket.deleted_by})"
                    if isinstance(ticket.deleted_by, int)
                    else f"{ticket.deleted_by.mention} ({ticket.deleted_by.id})",
                )

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
        config = await self.get_config(ticket.guild)
        actual_color = config["color"]
        embed: discord.Embed = discord.Embed()
        embed.title = _("Ticket {ticket.id} - Action taken").format(**locals())
        embed.description = f"{action}"
        embed.color = actual_color
        embed.timestamp = datetime.datetime.now(tz=datetime.timezone.utc)
        embed.set_author(name=author, url=author.display_avatar if self.cogsutils.is_dpy2 else author.avatar_url, icon_url=author.display_avatar if self.cogsutils.is_dpy2 else author.avatar_url)
        embed.set_footer(text=ticket.guild.name, icon_url=ticket.guild.icon or "" if self.cogsutils.is_dpy2 else ticket.guild.icon_url or "")
        embed.add_field(
            inline=False,
            name=_("Reason:").format(**locals()),
            value=f"{ticket.reason}")
        return embed

    async def check_limit(self, member: discord.Member):
        config = await self.get_config(member.guild)
        data = await self.config.guild(member.guild).tickets.all()
        to_remove = []
        count = 1
        for id in data:
            channel = member.guild.get_channel(int(id))
            if channel is not None:
                ticket: Ticket = await self.get_ticket(channel)
                if ticket.created_by == member and ticket.status == "open":
                    count += 1
            else:
                to_remove.append(id)
        if to_remove:
            data = await self.config.guild(member.guild).tickets.all()
            for id in to_remove:
                del data[str(id)]
            await self.config.guild(member.guild).tickets.set(data)
        return count <= config["nb_max"]

    async def create_modlog(self, ticket, action: str, reason: str):
        config = await self.get_config(ticket.guild)
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
            if enable_check and not config["enable"]:
                return False
            if ticket_check:
                ticket: Ticket = await ctx.bot.get_cog("TicketTool").get_ticket(ctx.channel)
                if ticket is None:
                    return False
                if status is not None and ticket.status != status:
                    return False
                if claim is not None:
                    if ticket.claim is not None:
                        check = True
                    elif ticket.claim is None:
                        check = False
                    if check != claim:
                        return False
                if ctx.author.id in ctx.bot.owner_ids:
                    return True
                if (
                    ticket_owner
                    and not isinstance(ticket.owner, int)
                    and ctx.author == ticket.owner
                    and (ctx.command.name != "close" or config["user_can_close"])
                ):
                    return True
                if (
                    admin_role
                    and config["admin_role"] is not None
                    and ctx.author in config["admin_role"].members
                ):
                    return True
                if (
                    support_role
                    and config["support_role"] is not None
                    and ctx.author in config["support_role"].members
                ):
                    return True
                if (
                    ticket_role
                    and config["ticket_role"] is not None
                    and ctx.author in config["ticket_role"].members
                ):
                    return True
                if (
                    view_role
                    and config["view_role"] is not None
                    and ctx.author in config["view_role"].members
                ):
                    return True
                if guild_owner and ctx.author == ctx.guild.owner:
                    return True
                if claim_staff and ctx.author == ticket.claim:
                    return True
                return bool(members and ctx.author in ticket.members)
            return True

        return commands.check(pred)

    @commands.guild_only()
    @hybrid_group(name="ticket")
    async def ticket(self, ctx: commands.Context):
        """Commands for using the ticket system."""

    @ticket.command(name="create")
    async def command_create(self, ctx: commands.Context, *, reason: typing.Optional[str]="No reason provided."):
        """Create a ticket.
        """
        config = await self.get_config(ctx.guild)
        limit = config["nb_max"]
        category_open = config["category_open"]
        category_close = config["category_close"]
        if not config["enable"]:
            await ctx.send(_("The ticket system is not activated on this server. Please ask an administrator of this server to use the `{ctx.prefix}ticketset` subcommands to configure it.").format(**locals()))
            return
        if category_open is None or category_close is None:
            await ctx.send(_("The category `open` or the category `close` have not been configured. Please ask an administrator of this server to use the `{ctx.prefix}ticketset` subcommands to configure it.").format(**locals()))
            return
        if not await self.check_limit(ctx.author):
            await ctx.send(_("Sorry. You have already reached the limit of {limit} open tickets.").format(**locals()))
            return
        if not category_open.permissions_for(ctx.guild.me).manage_channels or not category_close.permissions_for(ctx.guild.me).manage_channels:
            await ctx.send(_("The bot does not have `manage_channels` permission on the 'open' and 'close' categories to allow the ticket system to function properly. Please notify an administrator of this server.").format(**locals()))
            return
        ticket: Ticket = Ticket.instance(ctx, reason)
        await ticket.create()
        ctx.ticket = ticket
        await ctx.tick(message="Done.")

    @decorator(enable_check=False, ticket_check=True, status=None, ticket_owner=True, admin_role=True, support_role=False, ticket_role=False, view_role=False, guild_owner=True, claim=None, claim_staff=True, members=False)
    @ticket.command(name="export")
    async def command_export(self, ctx: commands.Context):
        """Export all the messages of an existing ticket in html format.
        Please note: all attachments and user avatars are saved with the Discord link in this file.
        """
        ticket: Ticket = await self.get_ticket(ctx.channel)
        if ticket.bot.get_cog("TicketTool").cogsutils.is_dpy2:
            transcript = await chat_exporter.export(channel=ticket.channel, limit=None, tz_info="UTC", guild=ticket.guild, bot=ticket.bot)
        else:
            transcript = await chat_exporter.export(channel=ticket.channel, guild=ticket.guild, limit=None)
        if transcript is not None:
            file = discord.File(io.BytesIO(transcript.encode()),
                                filename=f"transcript-ticket-{ticket.id}.html")
        await ctx.send(_("Here is the html file of the transcript of all the messages in this ticket.\nPlease note: all attachments and user avatars are saved with the Discord link in this file.").format(**locals()), file=file)
        await ctx.tick(message="Done.")

    @decorator(enable_check=True, ticket_check=True, status="close", ticket_owner=True, admin_role=True, support_role=False, ticket_role=False, view_role=False, guild_owner=True, claim=None, claim_staff=True, members=False)
    @ticket.command(name="open")
    async def command_open(self, ctx: commands.Context, *, reason: typing.Optional[str]="No reason provided."):
        """Open an existing ticket.
        """
        ticket: Ticket = await self.get_ticket(ctx.channel)
        ticket.reason = reason
        await ticket.open(ctx.author)
        await ctx.tick(message="Done.")

    @decorator(enable_check=False, ticket_check=True, status="open", ticket_owner=True, admin_role=True, support_role=True, ticket_role=False, view_role=False, guild_owner=True, claim=None, claim_staff=True, members=False)
    @ticket.command(name="close")
    async def command_close(self, ctx: commands.Context, confirmation: typing.Optional[bool]=None, *, reason: typing.Optional[str]="No reason provided."):
        """Close an existing ticket.
        """
        ticket: Ticket = await self.get_ticket(ctx.channel)
        config = await self.get_config(ticket.guild)
        if confirmation is None:
            config = await self.get_config(ticket.guild)
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
        await ctx.tick(message="Done.")

    @decorator(enable_check=False, ticket_check=True, status=None, ticket_owner=True, admin_role=True, support_role=True, ticket_role=False, view_role=False, guild_owner=True, claim=None, claim_staff=True, members=False)
    @ticket.command(name="rename")
    async def command_rename(self, ctx: commands.Context, new_name: str, *, reason: typing.Optional[str]="No reason provided."):
        """Rename an existing ticket.
        """
        ticket: Ticket = await self.get_ticket(ctx.channel)
        ticket.reason = reason
        await ticket.rename(new_name, ctx.author)
        await ctx.tick(message="Done.")

    @decorator(enable_check=False, ticket_check=True, status=None, ticket_owner=False, admin_role=True, support_role=False, ticket_role=False, view_role=False, guild_owner=True, claim=None, claim_staff=True, members=False)
    @ticket.command(name="delete")
    async def command_delete(self, ctx: commands.Context, confirmation: typing.Optional[bool]=False, *, reason: typing.Optional[str]="No reason provided."):
        """Delete an existing ticket.
        If a log channel is defined, an html file containing all the messages of this ticket will be generated.
        (Attachments are not supported, as they are saved with their Discord link)
        """
        ticket: Ticket = await self.get_ticket(ctx.channel)
        config = await self.get_config(ticket.guild)
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
        ticket: Ticket = await self.get_ticket(ctx.channel)
        ticket.reason = reason
        if member is None:
            member = ctx.author
        await ticket.claim_ticket(member, ctx.author)
        await ctx.tick(message="Done.")

    @decorator(enable_check=False, ticket_check=True, status=None, ticket_owner=False, admin_role=True, support_role=False, ticket_role=False, view_role=False, guild_owner=True, claim=True, claim_staff=True, members=False)
    @ticket.command(name="unclaim")
    async def command_unclaim(self, ctx: commands.Context, *, reason: typing.Optional[str]="No reason provided."):
        """Unclaim an existing ticket.
        """
        ticket: Ticket = await self.get_ticket(ctx.channel)
        ticket.reason = reason
        await ticket.unclaim_ticket(ticket.claim, ctx.author)
        await ctx.tick(message="Done.")

    @decorator(enable_check=False, ticket_check=True, status="open", ticket_owner=True, admin_role=True, support_role=False, ticket_role=False, view_role=False, guild_owner=True, claim=None, claim_staff=False, members=False)
    @ticket.command(name="owner")
    async def command_owner(self, ctx: commands.Context, new_owner: discord.Member, *, reason: typing.Optional[str]="No reason provided."):
        """Change the owner of an existing ticket.
        """
        ticket: Ticket = await self.get_ticket(ctx.channel)
        ticket.reason = reason
        if new_owner is None:
            new_owner = ctx.author
        await ticket.change_owner(new_owner, ctx.author)
        await ctx.tick(message="Done.")

    @decorator(enable_check=False, ticket_check=True, status="open", ticket_owner=True, admin_role=True, support_role=False, ticket_role=False, view_role=False, guild_owner=True, claim=None, claim_staff=True, members=False)
    @ticket.command(name="add")
    async def command_add(self, ctx: commands.Context, members: commands.Greedy[discord.Member], reason: typing.Optional[str]="No reason provided."):
        """Add a member to an existing ticket.
        """
        ticket: Ticket = await self.get_ticket(ctx.channel)
        ticket.reason = reason
        members = list(members)
        await ticket.add_member(members, ctx.author)
        await ctx.tick(message="Done.")

    @decorator(enable_check=False, ticket_check=True, status=None, ticket_owner=True, admin_role=True, support_role=False, ticket_role=False, view_role=False, guild_owner=True, claim=None, claim_staff=True, members=False)
    @ticket.command(name="remove")
    async def command_remove(self, ctx: commands.Context, members: commands.Greedy[discord.Member], reason: typing.Optional[str]="No reason provided."):
        """Remove a member to an existing ticket.
        """
        ticket: Ticket = await self.get_ticket(ctx.channel)
        ticket.reason = reason
        members = list(members)
        await ticket.remove_member(members, ctx.author)
        await ctx.tick(message="Done.")

    if CogsUtils().is_dpy2:
        async def on_button_interaction(self, view: Buttons, interaction: discord.Interaction):
            if interaction.data["custom_id"] == "create_ticket_button":
                permissions = interaction.channel.permissions_for(interaction.user)
                if not permissions.read_messages and not permissions.send_messages:
                    return
                permissions = interaction.channel.permissions_for(interaction.guild.me)
                if not permissions.read_messages and not permissions.read_message_history:
                    return
                ctx = await self.cogsutils.invoke_command(author=interaction.user, channel=interaction.channel, command="ticket create")
                if not await discord.utils.async_all(check(ctx) for check in ctx.command.checks):
                    await interaction.response.send_message(_("You are not allowed to execute this command."), ephemeral=True)
                else:
                    await interaction.response.send_message(_("You have chosen to create a ticket.").format(**locals()), ephemeral=True)
            if interaction.data["custom_id"] == "close_ticket_button":
                permissions = interaction.channel.permissions_for(interaction.user)
                if not permissions.read_messages and not permissions.send_messages:
                    return
                permissions = interaction.channel.permissions_for(interaction.guild.me)
                if not permissions.read_messages and not permissions.read_message_history:
                    return
                ctx = await self.cogsutils.invoke_command(author=interaction.user, channel=interaction.channel, command="ticket close")
                if not await discord.utils.async_all(check(ctx) for check in ctx.command.checks):
                    await interaction.response.send_message(_("You are not allowed to execute this command."), ephemeral=True)
                else:
                    await interaction.response.send_message(_("You have chosen to close this ticket.").format(**locals()), ephemeral=True)
            if interaction.data["custom_id"] == "claim_ticket_button":
                permissions = interaction.channel.permissions_for(interaction.user)
                if not permissions.read_messages and not permissions.send_messages:
                    return
                permissions = interaction.channel.permissions_for(interaction.guild.me)
                if not permissions.read_messages and not permissions.read_message_history:
                    return
                ctx = await self.cogsutils.invoke_command(author=interaction.user, channel=interaction.channel, command="ticket claim")
                if not await discord.utils.async_all(check(ctx) for check in ctx.command.checks):
                    await interaction.response.send_message(_("You are not allowed to execute this command."), ephemeral=True)
                else:
                    await interaction.response.send_message(_("You have chosen to claim this ticket.").format(**locals()), ephemeral=True)
            return

        async def on_dropdown_interaction(self, view: Dropdown, interaction: discord.Interaction, options: typing.List):
            if len(options) == 0:
                await interaction.response.defer()
                return
            permissions = interaction.channel.permissions_for(interaction.user)
            if not permissions.read_messages and not permissions.send_messages:
                return
            permissions = interaction.channel.permissions_for(interaction.guild.me)
            if not permissions.read_messages and not permissions.read_message_history:
                return
            option = [option for option in view.dropdown._options if option.value == options[0]][0]
            reason = f"{option.emoji} - {option.label}"
            ctx = await self.cogsutils.invoke_command(author=interaction.user, channel=interaction.channel, command=f"ticket create {reason}")
            if not await discord.utils.async_all(check(ctx) for check in ctx.command.checks) or not hasattr(ctx, "ticket"):
                await interaction.response.send_message(_("You are not allowed to execute this command."), ephemeral=True)
            else:
                config = await self.get_config(interaction.guild)
                if config["embed_button"]["rename_channel_dropdown"]:
                    try:
                        ticket: Ticket = await self.get_ticket(ctx.guild.get_channel(ctx.ticket.channel))
                        if ticket is not None:
                            await ticket.rename(new_name=f"{option.emoji}-{option.value}_{interaction.user.id}".replace(" ", "-"), author=None)
                    except discord.HTTPException:
                        pass
                await interaction.response.send_message(_("You have chosen to create a ticket with the reason `{reason}`.").format(**locals()), ephemeral=True)
    else:
        @commands.Cog.listener()
        async def on_button_click(self, inter: MessageInteraction):
            if inter.clicked_button.custom_id == "create_ticket_button":
                permissions = inter.channel.permissions_for(inter.author)
                if not permissions.read_messages and not permissions.send_messages:
                    return
                permissions = inter.channel.permissions_for(inter.guild.me)
                if not permissions.read_messages and not permissions.read_message_history:
                    return
                ctx = await self.cogsutils.invoke_command(author=inter.author, channel=inter.channel, command="ticket create")
                if not await discord.utils.async_all(check(ctx) for check in ctx.command.checks):
                    await inter.create_response(_("You are not allowed to execute this command."), ephemeral=True)
                else:
                    await inter.create_response(_("You have chosen to create a ticket.").format(**locals()), ephemeral=True)
            if inter.clicked_button.custom_id == "close_ticket_button":
                permissions = inter.channel.permissions_for(inter.author)
                if not permissions.read_messages and not permissions.send_messages:
                    return
                permissions = inter.channel.permissions_for(inter.guild.me)
                if not permissions.read_messages and not permissions.read_message_history:
                    return
                ctx = await self.cogsutils.invoke_command(author=inter.author, channel=inter.channel, command="ticket close")
                if not await discord.utils.async_all(check(ctx) for check in ctx.command.checks):
                    await inter.create_response(_("You are not allowed to execute this command."), ephemeral=True)
                else:
                    await inter.create_response(_("You have chosen to close this ticket.").format(**locals()), ephemeral=True)
            if inter.clicked_button.custom_id == "claim_ticket_button":
                permissions = inter.channel.permissions_for(inter.author)
                if not permissions.read_messages and not permissions.send_messages:
                    return
                permissions = inter.channel.permissions_for(inter.guild.me)
                if not permissions.read_messages and not permissions.read_message_history:
                    return
                ctx = await self.cogsutils.invoke_command(author=inter.author, channel=inter.channel, command="ticket claim")
                commands.Command
                if not await discord.utils.async_all(check(ctx) for check in ctx.command.checks):
                    await inter.create_response(_("You are not allowed to execute this command."), ephemeral=True)
                else:
                    await inter.create_response(_("You have chosen to claim this ticket.").format(**locals()), ephemeral=True)
            return

        @commands.Cog.listener()
        async def on_dropdown(self, inter: MessageInteraction):
            if inter.select_menu.custom_id != "create_ticket_dropdown":
                return
            if len(inter.select_menu.selected_options) == 0:
                return
            permissions = inter.channel.permissions_for(inter.author)
            if not permissions.read_messages and not permissions.send_messages:
                return
            permissions = inter.channel.permissions_for(inter.guild.me)
            if not permissions.read_messages and not permissions.read_message_history:
                return
            option = inter.select_menu.selected_options[0]
            reason = f"{option.emoji} - {option.label}"
            ctx = await self.cogsutils.invoke_command(author=inter.author, channel=inter.channel, command=f"ticket create {reason}")
            if not await discord.utils.async_all(check(ctx) for check in ctx.command.checks) or not hasattr(ctx, "ticket"):
                await inter.create_response(_("You are not allowed to execute this command."), ephemeral=True)
            else:
                config = await self.get_config(inter.guild)
                if config["embed_button"]["rename_channel_dropdown"]:
                    try:
                        ticket: Ticket = await self.get_ticket(ctx.guild.get_channel(ctx.ticket.channel))
                        if ticket is not None:
                            await ticket.rename(new_name=(f"{option.emoji}-{option.value}_{inter.author.id}".replace(" ", "-"))[:99], author=None)
                    except discord.HTTPException:
                        pass
                await inter.create_response(_("You have chosen to create a ticket with the reason `{reason}`.").format(**locals()), ephemeral=True)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if not payload.guild_id:
            return
        guild = payload.member.guild
        channel = guild.get_channel(payload.channel_id)
        member = guild.get_member(payload.user_id)
        if member == guild.me or member.bot:
            return
        config = await self.get_config(guild)
        if (
            config["enable"]
            and config["create_on_react"]
            and str(payload.emoji) == "🎟️"
        ):
            permissions = channel.permissions_for(member)
            if not permissions.read_messages and not permissions.send_messages:
                return
            permissions = channel.permissions_for(guild.me)
            if not permissions.read_messages and not permissions.read_message_history:
                return
            await self.cogsutils.invoke_command(author=member, channel=channel, command="ticket create")
        return

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if not message.guild:
            return
        config = await self.config.guild(message.guild).dropdowns.all()
        if f"{message.channel.id}-{message.id}" not in config:
            return
        del config[f"{message.channel.id}-{message.id}"]
        await self.config.guild(message.guild).dropdowns.set(config)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, old_channel: discord.abc.GuildChannel):
        data = await self.config.guild(old_channel.guild).tickets.all()
        if str(old_channel.id) not in data:
            return
        try:
            del data[str(old_channel.id)]
        except KeyError:
            pass
        await self.config.guild(old_channel.guild).tickets.set(data)
        return

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        config = await self.get_config(member.guild)
        data = await self.config.guild(member.guild).tickets.all()
        if config["close_on_leave"]:
            for channel in data:
                channel = member.guild.get_channel(int(channel))
                ticket: Ticket = await self.get_ticket(channel)
                if isinstance(ticket.owner, int):
                    continue
                if ticket.owner == member and ticket.status == "open":
                    await ticket.close(ticket.guild.me)
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
    def instance(ctx: commands.Context, reason: typing.Optional[str]=_("No reason provided.").format(**locals())):
        return Ticket(
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

    @staticmethod
    def from_json(json: dict, bot: Red):
        return Ticket(
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

    async def save(self):
        if not self.save_data:
            return
        bot = self.bot
        guild = self.guild
        channel = self.channel
        self.bot = None
        if self.owner is not None:
            self.owner = (
                int(self.owner)
                if isinstance(self.owner, int)
                else int(self.owner.id)
            )

        if self.guild is not None:
            self.guild = int(self.guild.id)
        if self.channel is not None:
            self.channel = int(self.channel.id)
        if self.claim is not None:
            self.claim = self.claim.id
        if self.created_by is not None:
            self.created_by = (
                int(self.created_by)
                if isinstance(self.created_by, int)
                else int(self.created_by.id)
            )

        if self.opened_by is not None:
            self.opened_by = (
                int(self.opened_by)
                if isinstance(self.opened_by, int)
                else int(self.opened_by.id)
            )

        if self.closed_by is not None:
            self.closed_by = (
                int(self.closed_by)
                if isinstance(self.closed_by, int)
                else int(self.closed_by.id)
            )

        if self.deleted_by is not None:
            self.deleted_by = (
                int(self.deleted_by)
                if isinstance(self.deleted_by, int)
                else int(self.deleted_by.id)
            )

        if self.renamed_by is not None:
            self.renamed_by = (
                int(self.renamed_by)
                if isinstance(self.renamed_by, int)
                else int(self.renamed_by.id)
            )

        members = self.members
        self.members = [int(m.id) for m in members]
        if self.created_at is not None:
            self.created_at = float(datetime.datetime.timestamp(self.created_at))
        if self.opened_at is not None:
            self.opened_at = float(datetime.datetime.timestamp(self.opened_at))
        if self.closed_at is not None:
            self.closed_at = float(datetime.datetime.timestamp(self.closed_at))
        if self.deleted_at is not None:
            self.deleted_at = float(datetime.datetime.timestamp(self.deleted_at))
        if self.renamed_at is not None:
            self.renamed_at = float(datetime.datetime.timestamp(self.renamed_at))
        if self.first_message is not None:
            self.first_message = int(self.first_message.id)
        json = self.__dict__
        data = await bot.get_cog("TicketTool").config.guild(guild).tickets.all()
        data[str(channel.id)] = json
        await bot.get_cog("TicketTool").config.guild(guild).tickets.set(data)
        return data

    async def create(self):
        config = await self.bot.get_cog("TicketTool").get_config(self.guild)
        logschannel = config["logschannel"]
        overwrites = await utils().get_overwrites(self)
        emoji_open = config["emoji_open"]
        ping_role = config["ping_role"]
        self.id = config["last_nb"] + 1
        reason = await self.bot.get_cog("TicketTool").get_audit_reason(
            guild=self.guild,
            author=self.created_by,
            reason=_("Creating the ticket {ticket.id}.").format(**locals()),
        )

        try:
            name = config["dynamic_channel_name"].format(self=self).replace(" ", "-")
            self.channel = await self.guild.create_text_channel(
                name,
                overwrites=overwrites,
                category=config["category_open"],
                topic=self.reason,
                reason=reason,
            )

        except (KeyError, AttributeError, discord.HTTPException):
            name = f"{emoji_open}-ticket-{self.id}"
            self.channel = await self.guild.create_text_channel(
                name,
                overwrites=overwrites,
                category=config["category_open"],
                topic=self.reason,
                reason=reason,
            )

        topic = _("🎟️ Ticket ID: {ticket.id}\n"
                  "🔥 Channel ID: {ticket.channel.id}\n"
                  "🕵️ Ticket created by: @{ticket.created_by.display_name} ({ticket.created_by.id})\n"
                  "☢️ Ticket reason: {ticket.reason}\n"
                  "👥 Ticket claimed by: Nobody.").format(**locals())
        await self.channel.edit(topic=topic)
        if config["create_modlog"]:
            await self.bot.get_cog("TicketTool").create_modlog(
                self, "ticket_created", reason
            )

        if self.logs_messages:
            if CogsUtils().is_dpy2:
                view = Buttons(
                    timeout=None,
                    buttons=[
                        {
                            "style": 2,
                            "label": _("Close").format(**locals()),
                            "emoji": "🔒",
                            "custom_id": "close_ticket_button",
                            "disabled": False,
                        },
                        {
                            "style": 2,
                            "label": _("Claim").format(**locals()),
                            "emoji": "🙋‍♂️",
                            "custom_id": "claim_ticket_button",
                            "disabled": False,
                        },
                    ],
                    function=self.bot.get_cog("TicketTool").on_button_interaction,
                    infinity=True,
                )

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
            optionnal_ping = f" ||{ping_role.mention}||" if ping_role is not None else ""
            embed = await self.bot.get_cog("TicketTool").get_embed_important(
                self,
                False,
                author=self.created_by,
                title=_("Ticket Created").format(**locals()),
                description=_(
                    "Thank you for creating a ticket on this server!"
                ).format(**locals()),
            )

            if CogsUtils().is_dpy2:
                self.first_message = await self.channel.send(
                    f"{self.created_by.mention}{optionnal_ping}",
                    embed=embed,
                    view=view,
                    allowed_mentions=discord.AllowedMentions(
                        users=True, roles=True
                    ),
                )

            else:
                self.first_message = await self.channel.send(
                    f"{self.created_by.mention}{optionnal_ping}",
                    embed=embed,
                    components=[buttons],
                    allowed_mentions=discord.AllowedMentions(
                        users=True, roles=True
                    ),
                )

            if config["custom_message"] is not None:
                try:
                    embed: discord.Embed = discord.Embed()
                    embed.title = "Custom Message"
                    embed.description = config["custom_message"].format(self=self)
                    await self.channel.send(embed=embed)
                except (KeyError, AttributeError, discord.HTTPException):
                    pass
            if logschannel is not None:
                embed = await self.bot.get_cog("TicketTool").get_embed_important(
                    self,
                    True,
                    author=self.created_by,
                    title=_("Ticket Created").format(**locals()),
                    description=_(
                        "The ticket was created by {ticket.created_by}."
                    ).format(**locals()),
                )

                await logschannel.send(_("Report on the creation of the ticket {ticket.id}.").format(**locals()), embed=embed)
        await self.bot.get_cog("TicketTool").config.guild(
            self.guild
        ).settings.last_nb.set(self.id)

        if config["ticket_role"] is not None and self.owner:
            try:
                await self.owner.add_roles(config["ticket_role"], reason=reason)
            except discord.HTTPException:
                pass
        await self.save()
        return self

    async def export(self):
        if self.channel:
            if self.bot.get_cog("TicketTool").cogsutils.is_dpy2:
                transcript = await chat_exporter.export(
                    channel=self.channel,
                    limit=None,
                    tz_info="UTC",
                    guild=self.guild,
                    bot=self.bot,
                )

            else:
                transcript = await chat_exporter.export(
                    channel=self.channel, guild=self.guild, limit=None
                )

            if transcript is not None:
                return discord.File(
                    io.BytesIO(transcript.encode()),
                    filename=f"transcript-ticket-{self.id}.html",
                )

        return None

    async def open(self, author: typing.Optional[discord.Member]=None):
        config = await self.bot.get_cog("TicketTool").get_config(self.guild)
        reason = await self.bot.get_cog("TicketTool").get_audit_reason(
            guild=self.guild,
            author=author,
            reason=_("Opening the ticket {ticket.id}.").format(**locals()),
        )

        logschannel = config["logschannel"]
        emoji_open = config["emoji_open"]
        emoji_close = config["emoji_close"]
        self.status = "open"
        self.opened_by = author
        self.opened_at = datetime.datetime.now()
        self.closed_by = None
        self.closed_at = None
        new_name = f"{self.channel.name}"
        new_name = new_name.replace(f"{emoji_close}-", "", 1)
        new_name = f"{emoji_open}-{new_name}"
        await self.channel.edit(
            name=new_name, category=config["category_open"], reason=reason
        )

        if self.logs_messages:
            embed = await self.bot.get_cog("TicketTool").get_embed_action(
                self,
                author=self.opened_by,
                action=_("Ticket Opened").format(**locals()),
            )

            await self.channel.send(embed=embed)
            if logschannel is not None:
                embed = await self.bot.get_cog("TicketTool").get_embed_important(
                    self,
                    True,
                    author=self.opened_by,
                    title=_("Ticket Opened").format(**locals()),
                    description=_(
                        "The ticket was opened by {ticket.opened_by}."
                    ).format(**locals()),
                )

                await logschannel.send(_("Report on the close of the ticket {ticket.id}.").format(**locals()), embed=embed)
        if self.first_message is not None:
            try:
                if CogsUtils().is_dpy2:
                    view = Buttons(
                        timeout=None,
                        buttons=[
                            {
                                "style": 2,
                                "label": _("Close").format(**locals()),
                                "emoji": "🔒",
                                "custom_id": "close_ticket_button",
                                "disabled": False,
                            },
                            {
                                "style": 2,
                                "label": _("Claim").format(**locals()),
                                "emoji": "🙋‍♂️",
                                "custom_id": "claim_ticket_button",
                                "disabled": False,
                            },
                        ],
                        function=self.bot.get_cog(
                            "TicketTool"
                        ).on_button_interaction,
                        infinity=True,
                    )

                    self.first_message = await self.channel.fetch_message(
                        int(self.first_message.id)
                    )

                    await self.first_message.edit(view=view)
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
                    self.first_message = await self.channel.fetch_message(
                        int(self.first_message.id)
                    )

                    await self.first_message.edit(components=[buttons])
            except discord.HTTPException:
                pass
        await self.save()
        return self

    async def close(self, author: typing.Optional[discord.Member]=None):
        config = await self.bot.get_cog("TicketTool").get_config(self.guild)
        reason = await self.bot.get_cog("TicketTool").get_audit_reason(
            guild=self.guild,
            author=author,
            reason=f"Closing the ticket {self.id}.",
        )

        logschannel = config["logschannel"]
        emoji_open = config["emoji_open"]
        emoji_close = config["emoji_close"]
        self.status = "close"
        self.closed_by = author
        self.closed_at = datetime.datetime.now()
        new_name = f"{self.channel.name}"
        new_name = new_name.replace(f"{emoji_open}-", "", 1)
        new_name = f"{emoji_close}-{new_name}"
        await self.channel.edit(
            name=new_name, category=config["category_close"], reason=reason
        )

        if self.logs_messages:
            embed = await self.bot.get_cog("TicketTool").get_embed_action(
                self, author=self.closed_by, action="Ticket Closed"
            )

            await self.channel.send(embed=embed)
            if logschannel is not None:
                embed = await self.bot.get_cog("TicketTool").get_embed_important(
                    self,
                    True,
                    author=self.closed_by,
                    title="Ticket Closed",
                    description=f"The ticket was closed by {self.closed_by}.",
                )

                await logschannel.send(_("Report on the close of the ticket {ticket.id}.").format(**locals()), embed=embed)
        if self.first_message is not None:
            try:
                if CogsUtils().is_dpy2:
                    view = Buttons(
                        timeout=None,
                        buttons=[
                            {
                                "style": 2,
                                "label": _("Close").format(**locals()),
                                "emoji": "🔒",
                                "custom_id": "close_ticket_button",
                                "disabled": True,
                            },
                            {
                                "style": 2,
                                "label": _("Claim").format(**locals()),
                                "emoji": "🙋‍♂️",
                                "custom_id": "claim_ticket_button",
                                "disabled": True,
                            },
                        ],
                        function=self.bot.get_cog(
                            "TicketTool"
                        ).on_button_interaction,
                        infinity=True,
                    )

                    self.first_message = await self.channel.fetch_message(
                        int(self.first_message.id)
                    )

                    await self.first_message.edit(view=view)
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
                    self.first_message = await self.channel.fetch_message(
                        int(self.first_message.id)
                    )

                    await self.first_message.edit(components=[buttons])
            except discord.HTTPException:
                pass
        await self.save()
        return self

    async def rename(self, new_name: str, author: typing.Optional[discord.Member]=None):
        reason = await self.bot.get_cog("TicketTool").get_audit_reason(
            guild=self.guild,
            author=author,
            reason=_(
                "Renaming the ticket {ticket.id}. (`{ticket.channel.name}` to `{new_name}`)"
            ).format(**locals()),
        )

        await self.channel.edit(name=new_name, reason=reason)
        if author is not None:
            self.renamed_by = author
            self.renamed_at = datetime.datetime.now()
            if self.logs_messages:
                embed = await self.bot.get_cog("TicketTool").get_embed_action(
                    self,
                    author=self.renamed_by,
                    action=_("Ticket Renamed.").format(**locals()),
                )

                await self.channel.send(embed=embed)
            await self.save()
        return self

    async def delete(self, author: typing.Optional[discord.Member]=None):
        config = await self.bot.get_cog("TicketTool").get_config(self.guild)
        logschannel = config["logschannel"]
        reason = await self.bot.get_cog("TicketTool").get_audit_reason(
            guild=self.guild,
            author=author,
            reason=_("Deleting the ticket {ticket.id}.").format(**locals()),
        )

        self.deleted_by = author
        self.deleted_at = datetime.datetime.now()
        if self.logs_messages and logschannel is not None:
            embed = await self.bot.get_cog("TicketTool").get_embed_important(
                self,
                True,
                author=self.deleted_by,
                title=_("Ticket Deleted").format(**locals()),
                description=_(
                    "The ticket was deleted by {ticket.deleted_by}."
                ).format(**locals()),
            )

            try:
                if self.bot.get_cog("TicketTool").cogsutils.is_dpy2:
                    transcript = await chat_exporter.export(
                        channel=self.channel,
                        limit=None,
                        tz_info="UTC",
                        guild=self.guild,
                        bot=self.bot,
                    )

                else:
                    transcript = await chat_exporter.export(
                        channel=self.channel, guild=self.guild, limit=None
                    )

            except AttributeError:
                transcript = None
            if transcript is not None:
                file = discord.File(
                    io.BytesIO(transcript.encode()),
                    filename=f"transcript-ticket-{self.id}.html",
                )

            else:
                file = None
            await logschannel.send(_("Report on the deletion of the ticket {ticket.id}.").format(**locals()), embed=embed, file=file)
        await self.channel.delete(reason=reason)
        data = (
            await self.bot.get_cog("TicketTool")
            .config.guild(self.guild)
            .tickets.all()
        )

        try:
            del data[str(self.channel.id)]
        except KeyError:
            pass
        await self.bot.get_cog("TicketTool").config.guild(self.guild).tickets.set(data)
        return self

    async def claim_ticket(self, member: discord.Member, author: typing.Optional[discord.Member]=None):
        config = await self.bot.get_cog("TicketTool").get_config(self.guild)
        reason = await self.bot.get_cog("TicketTool").get_audit_reason(
            guild=self.guild,
            author=author,
            reason=_("Claiming the ticket {ticket.id}.").format(**locals()),
        )

        if member.bot:
            await self.channel.send(_("A bot cannot claim a ticket.").format(**locals()))
            return
        self.claim = member
        topic = _("🎟️ Ticket ID: {ticket.id}\n"
                  "🔥 Channel ID: {ticket.channel.id}\n"
                  "🕵️ Ticket created by: @{ticket.created_by.display_name} ({ticket.created_by.id})\n"
                  "☢️ Ticket reason: {ticket.reason}\n"
                  "👥 Ticket claimed by: @{ticket.claim.display_name}.").format(**locals())
        overwrites = self.channel.overwrites
        overwrites[member] = (
            discord.PermissionOverwrite(
                    attach_files=True,
                    read_message_history=True,
                    read_messages=True,
                    send_messages=True,
                    view_channel=True,
            )
        )
        if config["support_role"] is not None:
            overwrites[config["support_role"]] = (
                discord.PermissionOverwrite(
                    attach_files=False,
                    read_message_history=True,
                    read_messages=True,
                    send_messages=False,
                    view_channel=True,
                )
            )
        await self.channel.edit(topic=topic, overwrites=overwrites, reason=reason)
        if self.first_message is not None:
            try:
                if CogsUtils().is_dpy2:
                    view = Buttons(
                        timeout=None,
                        buttons=[
                            {
                                "style": 2,
                                "label": _("Close").format(**locals()),
                                "emoji": "🔒",
                                "custom_id": "close_ticket_button",
                                "disabled": self.status != "open",
                            },
                            {
                                "style": 2,
                                "label": _("Claim").format(**locals()),
                                "emoji": "🙋‍♂️",
                                "custom_id": "claim_ticket_button",
                                "disabled": True,
                            },
                        ],
                        function=self.bot.get_cog(
                            "TicketTool"
                        ).on_button_interaction,
                        infinity=True,
                    )

                    self.first_message = await self.channel.fetch_message(
                        int(self.first_message.id)
                    )

                    await self.first_message.edit(view=view)
                else:
                    buttons = ActionRow(
                        Button(
                            style=ButtonStyle.grey,
                            label=_("Close").format(**locals()),
                            emoji="🔒",
                            custom_id="close_ticket_button",
                            disabled=self.status != "open",
                        ),
                        Button(
                            style=ButtonStyle.grey,
                            label=_("Claim").format(**locals()),
                            emoji="🙋‍♂️",
                            custom_id="claim_ticket_button",
                            disabled=True,
                        ),
                    )

                    self.first_message = await self.channel.fetch_message(
                        int(self.first_message.id)
                    )

                    await self.first_message.edit(components=[buttons])
            except discord.HTTPException:
                pass
        await self.save()
        return self

    async def unclaim_ticket(self, member: discord.Member, author: typing.Optional[discord.Member]=None):
        config = await self.bot.get_cog("TicketTool").get_config(self.guild)
        reason = await self.bot.get_cog("TicketTool").get_audit_reason(
            guild=self.guild,
            author=author,
            reason=_("Claiming the ticket {ticket.id}.").format(**locals()),
        )

        self.claim = None
        topic = _("🎟️ Ticket ID: {ticket.id}\n"
                  "🔥 Channel ID: {ticket.channel.id}\n"
                  "🕵️ Ticket created by: @{ticket.created_by.display_name} ({ticket.created_by.id})\n"
                  "☢️ Ticket reason: {ticket.reason}\n"
                  "👥 Ticket claimed by: Nobody.").format(**locals())
        await self.channel.edit(topic=topic)
        if config["support_role"] is not None:
            overwrites = self.channel.overwrites
            overwrites[config["support_role"]] = (
                discord.PermissionOverwrite(
                    attach_files=True,
                    read_message_history=True,
                    read_messages=True,
                    send_messages=True,
                    view_channel=True,
                )
            )
            await self.channel.edit(overwrites=overwrites, reason=reason)
        await self.channel.set_permissions(member, overwrite=None, reason=reason)
        if self.first_message is not None:
            try:
                if CogsUtils().is_dpy2:
                    view = Buttons(
                        timeout=None,
                        buttons=[
                            {
                                "style": 2,
                                "label": _("Close").format(**locals()),
                                "emoji": "🔒",
                                "custom_id": "close_ticket_button",
                                "disabled": self.status != "open",
                            },
                            {
                                "style": 2,
                                "label": _("Claim").format(**locals()),
                                "emoji": "🙋‍♂️",
                                "custom_id": "claim_ticket_button",
                                "disabled": True,
                            },
                        ],
                        function=self.bot.get_cog(
                            "TicketTool"
                        ).on_button_interaction,
                        infinity=True,
                    )

                    self.first_message = await self.channel.fetch_message(
                        int(self.first_message.id)
                    )

                    await self.first_message.edit(view=view)
                else:
                    buttons = ActionRow(
                        Button(
                            style=ButtonStyle.grey,
                            label=_("Close").format(**locals()),
                            emoji="🔒",
                            custom_id="close_ticket_button",
                            disabled=self.status != "open",
                        ),
                        Button(
                            style=ButtonStyle.grey,
                            label=_("Claim").format(**locals()),
                            emoji="🙋‍♂️",
                            custom_id="claim_ticket_button",
                            disabled=False,
                        ),
                    )

                    self.first_message = await self.channel.fetch_message(
                        int(self.first_message.id)
                    )

                    await self.first_message.edit(components=[buttons])
            except discord.HTTPException:
                pass
        await self.save()
        return self

    async def change_owner(self, member: discord.Member, author: typing.Optional[discord.Member]=None):
        config = await self.bot.get_cog("TicketTool").get_config(self.guild)
        reason = await self.bot.get_cog("TicketTool").get_audit_reason(
            guild=self.guild,
            author=author,
            reason=_("Changing owner of the ticket {ticket.id}.").format(
                **locals()
            ),
        )

        if member.bot:
            await self.channel.send(
                _("You cannot transfer ownership of a ticket to a bot.").format(
                    **locals()
                )
            )

            return
        if not isinstance(self.owner, int):
            if config["ticket_role"] is not None:
                try:
                    self.owner.remove_roles(config["ticket_role"], reason=reason)
                except discord.HTTPException:
                    pass
            self.remove_member(self.owner, author=None)
            self.add_member(self.owner, author=None)
        self.owner = member
        self.remove_member(self.owner, author=None)
        overwrites = self.channel.overwrites
        overwrites[member] = (
            discord.PermissionOverwrite(
                    attach_files=True,
                    read_message_history=True,
                    read_messages=True,
                    send_messages=True,
                    view_channel=True,
            )
        )
        await self.channel.edit(overwrites=overwrites, reason=reason)
        if config["ticket_role"] is not None:
            try:
                self.owner.add_roles(config["ticket_role"], reason=reason)
            except discord.HTTPException:
                pass
        if self.logs_messages:
            embed = await self.bot.get_cog("TicketTool").get_embed_action(
                self, author=author, action=_("Owner Modified.").format(**locals())
            )

            await self.channel.send(embed=embed)
        await self.save()
        return self

    async def add_member(self, members: typing.List[discord.Member], author: typing.Optional[discord.Member]=None):
        config = await self.bot.get_cog("TicketTool").get_config(self.guild)
        reason = await self.bot.get_cog("TicketTool").get_audit_reason(
            guild=self.guild,
            author=author,
            reason=_("Adding a member to the ticket {ticket.id}.").format(
                **locals()
            ),
        )

        if config["admin_role"] is not None:
            admin_role_members = config["admin_role"].members
        else:
            admin_role_members = []
        overwrites = self.channel.overwrites
        for member in members:
            if author is not None:
                if member.bot:
                    await self.channel.send(
                        _("You cannot add a bot to a ticket. ({member})").format(
                            **locals()
                        )
                    )

                    continue
                if not isinstance(self.owner, int) and member == self.owner:
                    await self.channel.send(
                        _(
                            "This member is already the owner of this ticket. ({member})"
                        ).format(**locals())
                    )

                    continue
                if member in admin_role_members:
                    await self.channel.send(
                        _(
                            "This member is an administrator for the ticket system. They will always have access to the ticket anyway. ({member})"
                        ).format(**locals())
                    )

                    continue
                if member in self.members:
                    await self.channel.send(
                        _(
                            "This member already has access to this ticket. ({member})"
                        ).format(**locals())
                    )

                    continue
            if member not in self.members:
                self.members.append(member)
            overwrites[member] = (
                discord.PermissionOverwrite(
                    attach_files=True,
                    read_message_history=True,
                    read_messages=True,
                    send_messages=True,
                    view_channel=True,
                )
            )
        await self.channel.edit(overwrites=overwrites, reason=reason)
        await self.save()
        return self

    async def remove_member(self, members: typing.List[discord.Member], author: typing.Optional[discord.Member]=None):
        config = await self.bot.get_cog("TicketTool").get_config(self.guild)
        reason = await self.bot.get_cog("TicketTool").get_audit_reason(
            guild=self.guild,
            author=author,
            reason=_("Removing a member to the ticket {ticket.id}.").format(
                **locals()
            ),
        )

        if config["admin_role"] is not None:
            admin_role_members = config["admin_role"].members
        else:
            admin_role_members = []
        if config["support_role"] is not None:
            support_role_members = config["support_role"].members
        else:
            support_role_members = []
        for member in members:
            if author is not None:
                if member.bot:
                    await self.channel.send(
                        _(
                            "You cannot remove a bot to a ticket ({member})."
                        ).format(locals())
                    )

                    continue
                if not isinstance(self.owner, int) and member == self.owner:
                    await self.channel.send(
                        _(
                            "You cannot remove the owner of this ticket. ({member})"
                        ).format(**locals())
                    )

                    continue
                if member in admin_role_members:
                    await self.channel.send(
                        _(
                            "This member is an administrator for the ticket system. They will always have access to the ticket. ({member})"
                        ).format(**locals())
                    )

                    continue
                if (
                    member not in self.members
                    and member not in support_role_members
                ):
                    await self.channel.send(
                        _(
                            "This member is not in the list of those authorised to access the ticket. ({member})"
                        ).format(locals())
                    )

                    continue
            if member in self.members:
                self.members.remove(member)
            if member in support_role_members:
                overwrites = self.channel.overwrites
                overwrites[member] = (
                    discord.PermissionOverwrite(
                        attach_files=False,
                        read_message_history=False,
                        read_messages=False,
                        send_messages=False,
                        view_channel=False,
                    )
                )
                await self.channel.edit(overwrites=overwrites, reason=reason)
            else:
                await self.channel.set_permissions(member, overwrite=None, reason=reason)
        await self.save()
        return self
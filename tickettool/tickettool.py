wfrom .AAA3A_utils import CogsUtils, Settings  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
from redbot.core.bot import Red  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

if CogsUtils().is_dpy2:
    from .AAA3A_utils import Buttons, Dropdown, Modal  # isort:skip
else:
    from dislash import (
        ActionRow,
        Button,
        ButtonStyle,
        MessageInteraction,
        ResponseType,
    )  # isort:skip

import datetime
import io
from copy import deepcopy

import chat_exporter
from redbot.core import Config, modlog

from .settings import settings
from .utils import utils

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
            identifier=205192943327321000143939875896557571750,  # 937480369417
            force_registration=True,
        )
        self.CONFIG_SCHEMA = 2
        self.tickettool_global = {
            "CONFIG_SCHEMA": None,
        }
        self.tickettool_guild = {
            "panels": {},
            "default_profile_settings": {
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
                "delete_on_close": False,
                "color": 0x01D758,
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
                    "description": _(
                        "To get help on this server or to make an order for example, you can create a ticket.\n"
                        "Just use the command `{prefix}ticket create` or click on the button below.\n"
                        "You can then use the `{prefix}ticket` subcommands to manage your ticket."
                    ),
                    "image": None,
                    "placeholder_dropdown": "Choose the reason to open a ticket.",
                    "rename_channel_dropdown": False,
                },
            },
            "tickets": {},
            "buttons": {},
            "dropdowns": {},
        }
        self.config.register_global(**self.tickettool_global)
        self.config.register_guild(**self.tickettool_guild)

        self.cogsutils = CogsUtils(cog=self)

        _settings = {
            "enable": {"path": ["enable"], "converter": bool, "description": "Enable the system."},
            "logschannel": {
                "path": ["logschannel"],
                "converter": discord.TextChannel,
                "description": "Set the channel where the logs will be saved.",
            },
            "category_open": {
                "path": ["category_open"],
                "converter": discord.CategoryChannel,
                "description": "Set the category where the opened tickets will be.",
            },
            "category_close": {
                "path": ["category_close"],
                "converter": discord.CategoryChannel,
                "description": "Set the category where the closed tickets will be.",
            },
            "admin_role": {
                "path": ["admin_role"],
                "converter": discord.Role,
                "description": "Users with this role will have full permissions for tickets, but will not be able to set up the cog.",
            },
            "support_role": {
                "path": ["support_role"],
                "converter": discord.Role,
                "description": "Users with this role will be able to participate and claim the ticket.",
            },
            "view_role": {
                "path": ["support_role"],
                "converter": discord.Role,
                "description": "Users with this role will only be able to read messages from the ticket, but not send them.",
            },
            "ping_role": {
                "path": ["ping_role"],
                "converter": discord.Role,
                "description": "This role will be pinged automatically when the ticket is created, but does not give any additional permissions.",
            },
            "dynamic_channel_name": {
                "path": ["dynamic_channel_name"],
                "converter": str,
                "description": "Set the template that will be used to name the channel when creating a ticket.\n\n`{ticket_id}` - Ticket number\n`{owner_display_name}` - user's nick or name\n`{owner_name}` - user's name\n`{owner_id}` - user's id\n`{guild_name}` - guild's name\n`{guild_id}` - guild's id\n`{bot_display_name}` - bot's nick or name\n`{bot_name}` - bot's name\n`{bot_id}` - bot's id\n`{shortdate}` - mm-dd\n`{longdate}` - mm-dd-yyyy\n`{time}` - hh-mm AM/PM according to bot host system time\n\nIf, when creating the ticket, an error occurs with this name, another name will be used automatically.",
            },
            "nb_max": {
                "path": ["nb_max"],
                "converter": int,
                "description": "Sets the maximum number of open tickets a user can have on the system at any one time (for the profile only).",
            },
            "custom_message": {
                "path": ["custom_message"],
                "converter": str,
                "description": "This message will be sent in the ticket channel when the ticket is opened.\n\n`{ticket_id}` - Ticket number\n`{owner_display_name}` - user's nick or name\n`{owner_name}` - user's name\n`{owner_id}` - user's id\n`{guild_name}` - guild's name\n`{guild_id}` - guild's id\n`{bot_display_name}` - bot's nick or name\n`{bot_name}` - bot's name\n`{bot_id}` - bot's id\n`{shortdate}` - mm-dd\n`{longdate}` - mm-dd-yyyy\n`{time}` - hh-mm AM/PM according to bot host system time",
                "style": 2,
            },
            "user_can_close": {
                "path": ["user_can_close"],
                "converter": bool,
                "description": "Can the author of the ticket, if he/she does not have a role set up for the system, close the ticket himself?",
            },
            "close_confirmation": {
                "path": ["close_confirmation"],
                "converter": bool,
                "description": "Should the bot ask for confirmation before closing the ticket (deletion will necessarily have a confirmation)?",
            },
            "close_on_leave": {
                "path": ["close_on_leave"],
                "converter": bool,
                "description": "If a user leaves the server, will all their open tickets be closed?\n\nIf the user then returns to the server, even if their ticket is still open, the bot will not automatically add them to the ticket.",
            },
            "delete_on_close": {
                "path": ["delete_on_close"],
                "converter": bool,
                "description": "Does closing the ticket directly delete it (with confirmation)?",
            },
            "modlog": {
                "path": ["create_modlog"],
                "converter": bool,
                "description": "Does the bot create an action in the bot modlog when a ticket is created?",
            },
            "audit_logs": {
                "path": ["audit_logs"],
                "converter": bool,
                "description": "On all requests to the Discord api regarding the ticket (channel modification), does the bot send the name and id of the user who requested the action as the reason?",
                "no_slash": True,
            },
            "create_on_react": {
                "path": ["create_on_react"],
                "converter": bool,
                "description": "Create a ticket when the reaction 🎟️ is set on any message on the server.",
            },
        }
        self.settings = Settings(
            bot=self.bot,
            cog=self,
            config=self.config,
            group=self.config.GUILD,
            settings=_settings,
            global_path=["panels"],
            use_profiles_system=True,
            can_edit=True,
            commands_group=self.configuration,
        )

    async def cog_load(self):
        await self.edit_config_schema()
        await self.settings.add_commands()
        if self.cogsutils.is_dpy2:
            await self.load_buttons()

    async def edit_config_schema(self):
        CONFIG_SCHEMA = await self.config.CONFIG_SCHEMA()
        if CONFIG_SCHEMA is None:
            CONFIG_SCHEMA = 1
            await self.config.CONFIG_SCHEMA(CONFIG_SCHEMA)
        if CONFIG_SCHEMA == self.CONFIG_SCHEMA:
            return
        if CONFIG_SCHEMA == 1:
            guild_group = self.config._get_base_group(self.config.GUILD)
            async with guild_group.all() as guilds_data:
                _guilds_data = deepcopy(guilds_data)
                for guild in _guilds_data:
                    if "settings" not in _guilds_data[guild]:
                        continue
                    if "main" in _guilds_data[guild].get("panels", []):
                        continue
                    if "panels" not in guilds_data[guild]:
                        guilds_data[guild]["panels"] = {}
                    guilds_data[guild]["panels"]["main"] = self.config._defaults[
                        self.config.GUILD
                    ]["default_profile_settings"]
                    for key, value in _guilds_data[guild]["settings"].items():
                        guilds_data[guild]["panels"]["main"][key] = value
                    del guilds_data[guild]["settings"]
            CONFIG_SCHEMA = 2
            await self.config.CONFIG_SCHEMA.set(CONFIG_SCHEMA)
        if CONFIG_SCHEMA < self.CONFIG_SCHEMA:
            CONFIG_SCHEMA = self.CONFIG_SCHEMA
            await self.config.CONFIG_SCHEMA.set(CONFIG_SCHEMA)
        self.log.info(
            f"The Config schema has been successfully modified to {self.CONFIG_SCHEMA} for the {self.qualified_name} cog."
        )

    async def load_buttons(self):
        try:
            view = Buttons(
                timeout=None,
                buttons=[
                    {
                        "style": 2,
                        "label": _("Create ticket"),
                        "emoji": "🎟️",
                        "custom_id": "create_ticket_button",
                        "disabled": False,
                    }
                ],
                function=self.on_button_interaction,
                infinity=True,
            )
            self.bot.add_view(view)
            self.cogsutils.views.append(view)
            view = Buttons(
                timeout=None,
                buttons=[
                    {
                        "style": 2,
                        "label": _("Close"),
                        "emoji": "🔒",
                        "custom_id": "close_ticket_button",
                        "disabled": False,
                    },
                    {
                        "style": 2,
                        "label": _("Claim"),
                        "emoji": "🙋‍♂️",
                        "custom_id": "claim_ticket_button",
                        "disabled": False,
                    },
                ],
                function=self.on_button_interaction,
                infinity=True,
            )
            self.bot.add_view(view)
            self.cogsutils.views.append(view)
        except Exception as e:
            self.log.error(f"The Buttons View could not be added correctly.", exc_info=e)
        all_guilds = await self.config.all_guilds()
        for guild in all_guilds:
            for dropdown in all_guilds[guild]["dropdowns"]:
                try:
                    view = Dropdown(
                        timeout=None,
                        placeholder=_("Choose the reason for open a ticket."),
                        options=[
                            {
                                "label": reason_option["label"],
                                "value": reason_option.get("value", reason_option["label"]),
                                "description": reason_option.get("description", None),
                                "emoji": reason_option["emoji"],
                                "default": False,
                            }
                            for reason_option in all_guilds[guild]["dropdowns"][dropdown]
                        ],
                        function=self.on_dropdown_interaction,
                        infinity=True,
                        custom_id="create_ticket_dropdown",
                    )
                    self.bot.add_view(view, message_id=int((str(dropdown).split("-"))[1]))
                    self.cogsutils.views.append(view)
                except Exception as e:
                    self.log.error(
                        f"The Dropdown View could not be added correctly for the {guild}-{dropdown} message.",
                        exc_info=e,
                    )

    async def get_config(self, guild: discord.Guild, panel: str):
        config = await self.config.guild(guild).panels.get_raw(panel)
        for key, value in self.config._defaults[Config.GUILD]["default_profile_settings"].items():
            if key not in config:
                config[key] = value
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
        for key, value in self.config._defaults[self.config.GUILD][
            "default_profile_settings"
        ].items():
            if key not in config:
                config[key] = value
        if len(config["embed_button"]) == 0:
            config["embed_button"] = self.config._defaults[self.config.GUILD][
                "default_profile_settings"
            ]["embed_button"]
        else:
            for key, value in self.config._defaults[self.config.GUILD]["default_profile_settings"][
                "embed_button"
            ].items():
                if key not in config:
                    config[key] = value
        return config

    async def get_ticket(self, channel: discord.TextChannel):
        config = await self.config.guild(channel.guild).tickets.all()
        if str(channel.id) in config:
            json = config[str(channel.id)]
        else:
            return None
        if "panel" not in json:
            json["panel"] = "main"
        ticket: Ticket = Ticket.from_json(json, self.bot, self)
        ticket.bot = self.bot
        ticket.cog = self
        ticket.guild = ticket.bot.get_guild(ticket.guild) or ticket.guild
        ticket.owner = ticket.guild.get_member(ticket.owner) or ticket.owner
        ticket.channel = ticket.guild.get_channel(ticket.channel) or ticket.channel
        ticket.claim = ticket.guild.get_member(ticket.claim) or ticket.claim
        ticket.created_by = ticket.guild.get_member(ticket.created_by) or ticket.created_by
        ticket.opened_by = ticket.guild.get_member(ticket.opened_by) or ticket.opened_by
        ticket.closed_by = ticket.guild.get_member(ticket.closed_by) or ticket.closed_by
        ticket.deleted_by = ticket.guild.get_member(ticket.deleted_by) or ticket.deleted_by
        ticket.renamed_by = ticket.guild.get_member(ticket.renamed_by) or ticket.renamed_by
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

    async def get_audit_reason(
        self,
        guild: discord.Guild,
        panel: str,
        author: typing.Optional[discord.Member] = None,
        reason: typing.Optional[str] = None,
    ):
        if reason is None:
            reason = _("Action taken for the ticket system.")
        config = await self.get_config(guild, panel)
        if author is None or not config["audit_logs"]:
            return f"{reason}"
        else:
            return f"{author.name} ({author.id}) - {reason}"

    async def get_embed_important(
        self, ticket, more: bool, author: discord.Member, title: str, description: str
    ):
        config = await self.get_config(ticket.guild, ticket.panel)
        actual_color = config["color"]
        actual_thumbnail = config["thumbnail"]
        embed: discord.Embed = discord.Embed()
        embed.title = f"{title}"
        embed.description = f"{description}"
        embed.set_thumbnail(url=actual_thumbnail)
        embed.color = actual_color
        embed.timestamp = datetime.datetime.now(tz=datetime.timezone.utc)
        embed.set_author(
            name=author,
            url=author.display_avatar if self.cogsutils.is_dpy2 else author.avatar_url,
            icon_url=author.display_avatar if self.cogsutils.is_dpy2 else author.avatar_url,
        )
        embed.set_footer(
            text=ticket.guild.name,
            icon_url=ticket.guild.icon or ""
            if self.cogsutils.is_dpy2
            else ticket.guild.icon_url or "",
        )
        embed.add_field(inline=True, name=_("Ticket ID:"), value=f"[{ticket.panel}] {ticket.id}")
        embed.add_field(
            inline=True,
            name=_("Owned by:"),
            value=f"{ticket.owner.mention} ({ticket.owner.id})"
            if not isinstance(ticket.owner, int)
            else f"<@{ticket.owner}> ({ticket.owner})",
        )
        embed.add_field(
            inline=True,
            name=_("Channel:"),
            value=f"{ticket.channel.mention} - {ticket.channel.name} ({ticket.channel.id})",
        )
        if more:
            if ticket.closed_by is not None:
                embed.add_field(
                    inline=False,
                    name=_("Closed by:"),
                    value=f"{ticket.closed_by.mention} ({ticket.closed_by.id})"
                    if not isinstance(ticket.closed_by, int)
                    else f"<@{ticket.closed_by}> ({ticket.closed_by})",
                )
            if ticket.deleted_by is not None:
                embed.add_field(
                    inline=True,
                    name=_("Deleted by:"),
                    value=f"{ticket.deleted_by.mention} ({ticket.deleted_by.id})"
                    if not isinstance(ticket.deleted_by, int)
                    else f"<@{ticket.deleted_by}> ({ticket.deleted_by})",
                )
            if ticket.closed_at:
                embed.add_field(
                    inline=False,
                    name=_("Closed at:"),
                    value=f"{ticket.closed_at}",
                )
        embed.add_field(inline=False, name=_("Reason:"), value=f"{ticket.reason}")
        return embed

    async def get_embed_action(self, ticket, author: discord.Member, action: str):
        config = await self.get_config(ticket.guild, ticket.panel)
        actual_color = config["color"]
        embed: discord.Embed = discord.Embed()
        embed.title = _("Ticket [{ticket.panel}] {ticket.id} - Action taken").format(**locals())
        embed.description = f"{action}"
        embed.color = actual_color
        embed.timestamp = datetime.datetime.now(tz=datetime.timezone.utc)
        embed.set_author(
            name=author,
            url=author.display_avatar if self.cogsutils.is_dpy2 else author.avatar_url,
            icon_url=author.display_avatar if self.cogsutils.is_dpy2 else author.avatar_url,
        )
        embed.set_footer(
            text=ticket.guild.name,
            icon_url=ticket.guild.icon or ""
            if self.cogsutils.is_dpy2
            else ticket.guild.icon_url or "",
        )
        embed.add_field(inline=False, name=_("Reason:"), value=f"{ticket.reason}")
        return embed

    async def check_limit(self, member: discord.Member, panel: str):
        config = await self.get_config(member.guild, panel)
        data = await self.config.guild(member.guild).tickets.all()
        to_remove = []
        count = 1
        for id in data:
            channel = member.guild.get_channel(int(id))
            if channel is not None:
                ticket: Ticket = await self.get_ticket(channel)
                if not ticket.panel == panel:
                    continue
                if ticket.created_by == member and ticket.status == "open":
                    count += 1
            else:
                to_remove.append(id)
        if not to_remove == []:
            data = await self.config.guild(member.guild).tickets.all()
            for id in to_remove:
                del data[str(id)]
            await self.config.guild(member.guild).tickets.set(data)
        if count > config["nb_max"]:
            return False
        else:
            return True

    async def create_modlog(self, ticket, action: str, reason: str):
        config = await self.get_config(ticket.guild, ticket.panel)
        if config["create_modlog"]:
            case = await modlog.create_case(
                ticket.bot,
                ticket.guild,
                ticket.created_at,
                action_type=action,
                user=ticket.created_by,
                moderator=None,
                reason=reason,
            )
            return case
        return

    def decorator(
        ticket_check: typing.Optional[bool] = False,
        status: typing.Optional[str] = None,
        ticket_owner: typing.Optional[bool] = False,
        admin_role: typing.Optional[bool] = False,
        support_role: typing.Optional[bool] = False,
        ticket_role: typing.Optional[bool] = False,
        view_role: typing.Optional[bool] = False,
        guild_owner: typing.Optional[bool] = False,
        claim: typing.Optional[bool] = None,
        claim_staff: typing.Optional[bool] = False,
        members: typing.Optional[bool] = False,
    ):
        async def pred(ctx):
            if ticket_check:
                ticket: Ticket = await ctx.bot.get_cog("TicketTool").get_ticket(ctx.channel)
                if ticket is None:
                    return False
                config = await ctx.bot.get_cog("TicketTool").get_config(ticket.guild, ticket.panel)
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
                    if not isinstance(ticket.owner, int):
                        if ctx.author == ticket.owner:
                            if not ctx.command.name == "close" or config["user_can_close"]:
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

    class PanelConverter(commands.Converter):
        async def convert(self, ctx: commands.Context, argument: str):
            if len(argument) > 10:
                raise commands.BadArgument(_("This panel does not exist."))
            panels = await ctx.bot.get_cog("TicketTool").config.guild(ctx.guild).panels()
            if argument.lower() not in panels:
                raise commands.BadArgument(_("This panel does not exist."))
            return argument.lower()

    @commands.guild_only()
    @hybrid_group(name="ticket")
    async def ticket(self, ctx: commands.Context):
        """Commands for using the ticket system."""

    @ticket.command(name="create")
    async def command_create(
        self,
        ctx: commands.Context,
        panel: typing.Optional[PanelConverter] = "main",
        *,
        reason: typing.Optional[str] = "No reason provided.",
    ):
        """Create a ticket."""
        panels = await self.config.guild(ctx.guild).panels()
        if panel not in panels:
            raise commands.UserFeedbackCheckFailure(_("This panel does not exist."))
        config = await self.get_config(ctx.guild, panel)
        category_open = config["category_open"]
        category_close = config["category_close"]
        if not config["enable"]:
            raise commands.UserFeedbackCheckFailure(
                _(
                    "The ticket system is not enabled on this server. Please ask an administrator of this server to use the `{ctx.prefix}ticketset` subcommands to configure it."
                ).format(**locals())
            )
        if category_open is None or category_close is None:
            raise commands.UserFeedbackCheckFailure(
                _(
                    "The category `open` or the category `close` have not been configured. Please ask an administrator of this server to use the `{ctx.prefix}ticketset` subcommands to configure it."
                ).format(**locals())
            )
        if not await self.check_limit(ctx.author, panel):
            raise commands.UserFeedbackCheckFailure(
                _("Sorry. You have already reached the limit of {limit} open tickets.").format(
                    **locals()
                )
            )
        if (
            not category_open.permissions_for(ctx.guild.me).manage_channels
            or not category_close.permissions_for(ctx.guild.me).manage_channels
        ):
            raise commands.UserFeedbackCheckFailure(
                _(
                    "The bot does not have `manage_channels` permission on the 'open' and 'close' categories to allow the ticket system to function properly. Please notify an administrator of this server."
                )
            )
        ticket: Ticket = Ticket.instance(ctx, panel, reason)
        await ticket.create()
        ctx.ticket = ticket

    @decorator(
        ticket_check=True,
        status=None,
        ticket_owner=True,
        admin_role=True,
        support_role=False,
        ticket_role=False,
        view_role=False,
        guild_owner=True,
        claim=None,
        claim_staff=True,
        members=False,
    )
    @ticket.command(name="export")
    async def command_export(self, ctx: commands.Context):
        """Export all the messages of an existing ticket in html format.
        Please note: all attachments and user avatars are saved with the Discord link in this file.
        """
        ticket: Ticket = await self.get_ticket(ctx.channel)
        if ticket.cog.cogsutils.is_dpy2:
            transcript = await chat_exporter.export(
                channel=ticket.channel,
                limit=None,
                tz_info="UTC",
                guild=ticket.guild,
                bot=ticket.bot,
            )
        else:
            transcript = await chat_exporter.export(
                channel=ticket.channel, guild=ticket.guild, limit=None
            )
        if transcript is not None:
            file = discord.File(
                io.BytesIO(transcript.encode()),
                filename=f"transcript-ticket-{ticket.panel}-{ticket.id}.html",
            )
        message = await ctx.send(
            _(
                "Here is the html file of the transcript of all the messages in this ticket.\nPlease note: all attachments and user avatars are saved with the Discord link in this file."
            ),
            file=file,
        )
        embed = discord.Embed(
            title="Transcript Link",
            description=(
                f"[Click here to view the transcript.](https://mahto.id/chat-exporter?url={message.attachments[0].url})"
            ),
            colour=discord.Colour.green(),
        )
        await message.edit(embed=embed)

    @decorator(
        ticket_check=True,
        status="close",
        ticket_owner=True,
        admin_role=True,
        support_role=False,
        ticket_role=False,
        view_role=False,
        guild_owner=True,
        claim=None,
        claim_staff=True,
        members=False,
    )
    @ticket.command(name="open")
    async def command_open(
        self, ctx: commands.Context, *, reason: typing.Optional[str] = "No reason provided."
    ):
        """Open an existing ticket."""
        ticket: Ticket = await self.get_ticket(ctx.channel)
        config = await ctx.bot.get_cog("TicketTool").get_config(ticket.guild, ticket.panel)
        if not config["enable"]:
            raise commands.UserFeedbackCheckFailure(
                _("The ticket system is not enabled on this server.")
            )
        ticket.reason = reason
        await ticket.open(ctx.author)

    @decorator(
        ticket_check=True,
        status="open",
        ticket_owner=True,
        admin_role=True,
        support_role=True,
        ticket_role=False,
        view_role=False,
        guild_owner=True,
        claim=None,
        claim_staff=True,
        members=False,
    )
    @ticket.command(name="close")
    async def command_close(
        self,
        ctx: commands.Context,
        confirmation: typing.Optional[bool] = None,
        *,
        reason: typing.Optional[str] = _("No reason provided."),
    ):
        """Close an existing ticket."""
        ticket: Ticket = await self.get_ticket(ctx.channel)
        config = await self.get_config(ticket.guild, ticket.panel)
        if config["delete_on_close"]:
            await self.command_delete(ctx, confirmation=confirmation, reason=reason)
            return
        if confirmation is None:
            config = await self.get_config(ticket.guild, ticket.panel)
            confirmation = not config["close_confirmation"]
        if not confirmation:
            embed: discord.Embed = discord.Embed()
            embed.title = _("Do you really want to close the ticket {ticket.id}?").format(
                **locals()
            )
            embed.color = config["color"]
            embed.set_author(
                name=ctx.author.name,
                url=ctx.author.display_avatar if self.cogsutils.is_dpy2 else ctx.author.avatar_url,
                icon_url=ctx.author.display_avatar
                if self.cogsutils.is_dpy2
                else ctx.author.avatar_url,
            )
            response = await self.cogsutils.ConfirmationAsk(ctx, embed=embed)
            if not response:
                return
        ticket.reason = reason
        await ticket.close(ctx.author)

    @decorator(
        ticket_check=True,
        status=None,
        ticket_owner=True,
        admin_role=True,
        support_role=True,
        ticket_role=False,
        view_role=False,
        guild_owner=True,
        claim=None,
        claim_staff=True,
        members=False,
    )
    @ticket.command(name="rename")
    async def command_rename(
        self,
        ctx: commands.Context,
        new_name: str,
        *,
        reason: typing.Optional[str] = _("No reason provided."),
    ):
        """Rename an existing ticket."""
        ticket: Ticket = await self.get_ticket(ctx.channel)
        ticket.reason = reason
        await ticket.rename(new_name, ctx.author)

    @decorator(
        ticket_check=True,
        status=None,
        ticket_owner=False,
        admin_role=True,
        support_role=False,
        ticket_role=False,
        view_role=False,
        guild_owner=True,
        claim=None,
        claim_staff=True,
        members=False,
    )
    @ticket.command(name="delete")
    async def command_delete(
        self,
        ctx: commands.Context,
        confirmation: typing.Optional[bool] = False,
        *,
        reason: typing.Optional[str] = _("No reason provided."),
    ):
        """Delete an existing ticket.
        If a log channel is defined, an html file containing all the messages of this ticket will be generated.
        (Attachments are not supported, as they are saved with their Discord link)
        """
        ticket: Ticket = await self.get_ticket(ctx.channel)
        config = await self.get_config(ticket.guild, ticket.panel)
        if not confirmation:
            embed: discord.Embed = discord.Embed()
            embed.title = _(
                "Do you really want to delete all the messages of the ticket {ticket.id}?"
            ).format(**locals())
            embed.description = _(
                "If a log channel is defined, an html file containing all the messages of this ticket will be generated. (Attachments are not supported, as they are saved with their Discord link)"
            )
            embed.color = config["color"]
            embed.set_author(
                name=ctx.author.name,
                url=ctx.author.display_avatar if self.cogsutils.is_dpy2 else ctx.author.avatar_url,
                icon_url=ctx.author.display_avatar
                if self.cogsutils.is_dpy2
                else ctx.author.avatar_url,
            )
            response = await self.cogsutils.ConfirmationAsk(ctx, embed=embed)
            if not response:
                return
        ticket.reason = reason
        await ticket.delete(ctx.author)

    @decorator(
        ticket_check=True,
        status="open",
        ticket_owner=False,
        admin_role=True,
        support_role=True,
        ticket_role=False,
        view_role=False,
        guild_owner=True,
        claim=False,
        claim_staff=False,
        members=False,
    )
    @ticket.command(name="claim")
    async def command_claim(
        self,
        ctx: commands.Context,
        member: typing.Optional[discord.Member] = None,
        *,
        reason: typing.Optional[str] = _("No reason provided."),
    ):
        """Claim an existing ticket."""
        ticket: Ticket = await self.get_ticket(ctx.channel)
        ticket.reason = reason
        if member is None:
            member = ctx.author
        await ticket.claim_ticket(member, ctx.author)

    @decorator(
        ticket_check=True,
        status=None,
        ticket_owner=False,
        admin_role=True,
        support_role=False,
        ticket_role=False,
        view_role=False,
        guild_owner=True,
        claim=True,
        claim_staff=True,
        members=False,
    )
    @ticket.command(name="unclaim")
    async def command_unclaim(
        self, ctx: commands.Context, *, reason: typing.Optional[str] = _("No reason provided.")
    ):
        """Unclaim an existing ticket."""
        ticket: Ticket = await self.get_ticket(ctx.channel)
        ticket.reason = reason
        await ticket.unclaim_ticket(ticket.claim, ctx.author)

    @decorator(
        ticket_check=True,
        status="open",
        ticket_owner=True,
        admin_role=True,
        support_role=False,
        ticket_role=False,
        view_role=False,
        guild_owner=True,
        claim=None,
        claim_staff=False,
        members=False,
    )
    @ticket.command(name="owner")
    async def command_owner(
        self,
        ctx: commands.Context,
        new_owner: discord.Member,
        *,
        reason: typing.Optional[str] = _("No reason provided."),
    ):
        """Change the owner of an existing ticket."""
        ticket: Ticket = await self.get_ticket(ctx.channel)
        ticket.reason = reason
        if new_owner is None:
            new_owner = ctx.author
        await ticket.change_owner(new_owner, ctx.author)

    @decorator(
        ticket_check=True,
        status="open",
        ticket_owner=True,
        admin_role=True,
        support_role=False,
        ticket_role=False,
        view_role=False,
        guild_owner=True,
        claim=None,
        claim_staff=True,
        members=False,
    )
    @ticket.command(name="add")
    async def command_add(
        self,
        ctx: commands.Context,
        members: commands.Greedy[discord.Member],
        reason: typing.Optional[str] = _("No reason provided."),
    ):
        """Add a member to an existing ticket."""
        ticket: Ticket = await self.get_ticket(ctx.channel)
        ticket.reason = reason
        members = [member for member in members]
        await ticket.add_member(members, ctx.author)

    @decorator(
        ticket_check=True,
        status=None,
        ticket_owner=True,
        admin_role=True,
        support_role=False,
        ticket_role=False,
        view_role=False,
        guild_owner=True,
        claim=None,
        claim_staff=True,
        members=False,
    )
    @ticket.command(name="remove")
    async def command_remove(
        self,
        ctx: commands.Context,
        members: commands.Greedy[discord.Member],
        reason: typing.Optional[str] = _("No reason provided."),
    ):
        """Remove a member to an existing ticket."""
        ticket: Ticket = await self.get_ticket(ctx.channel)
        ticket.reason = reason
        members = [member for member in members]
        await ticket.remove_member(members, ctx.author)

    if CogsUtils().is_dpy2:

        async def on_button_interaction(self, view: Buttons, interaction: discord.Interaction):
            permissions = interaction.channel.permissions_for(interaction.user)
            if not permissions.read_messages and not permissions.send_messages:
                return
            permissions = interaction.channel.permissions_for(interaction.guild.me)
            if not permissions.read_messages and not permissions.read_message_history:
                return
            if (
                not interaction.response.is_done()
                and not interaction.data["custom_id"] == "create_ticket_button"
            ):
                await interaction.response.defer(ephemeral=True)
            if interaction.data["custom_id"] == "create_ticket_button":
                buttons = await self.config.guild(interaction.guild).buttons.all()
                if f"{interaction.message.channel.id}-{interaction.message.id}" in buttons:
                    panel = buttons[f"{interaction.message.channel.id}-{interaction.message.id}"][
                        "panel"
                    ]
                else:
                    panel = "main"
                modal = Modal(
                    title="Create a Ticket",
                    inputs=[
                        {
                            "label": "Panel",
                            "style": discord.TextStyle.short,
                            "default": "main",
                            "max_length": 10,
                            "required": True,
                        },
                        {
                            "label": "Why are you creating this ticket?",
                            "style": discord.TextStyle.long,
                            "max_length": 1000,
                            "required": False,
                            "placeholder": "No reason provided.",
                        },
                    ],
                )
                await interaction.response.send_modal(modal)
                try:
                    interaction, inputs, function_result = await modal.wait_result()
                except TimeoutError:
                    return
                else:
                    if not interaction.response.is_done():
                        await interaction.response.defer(ephemeral=True)
                panel = inputs[0].value
                reason = inputs[1].value or ""
                panels = await self.config.guild(interaction.guild).panels()
                if panel not in panels:
                    await interaction.followup.send(
                        _("The panel for which this button was configured no longer exists."),
                        ephemeral=True,
                    )
                    return
                ctx = await self.cogsutils.invoke_command(
                    author=interaction.user,
                    channel=interaction.channel,
                    command=f"ticket create {panel}" + (f" {reason}" if not reason == "" else ""),
                )
                if not await ctx.command.can_run(
                    ctx, change_permission_state=True
                ):  # await discord.utils.async_all(check(ctx) for check in ctx.command.checks)
                    await interaction.followup.send(
                        _("You are not allowed to execute this command."), ephemeral=True
                    )
                else:
                    await interaction.followup.send(
                        _("You have chosen to create a ticket."), ephemeral=True
                    )
            if interaction.data["custom_id"] == "close_ticket_button":
                ctx = await self.cogsutils.invoke_command(
                    author=interaction.user, channel=interaction.channel, command="ticket close"
                )
                await interaction.followup.send(
                    _(
                        "You have chosen to close this ticket. If this is not done, you do not have the necessary permissions to execute this command."
                    ),
                    ephemeral=True,
                )
            if interaction.data["custom_id"] == "claim_ticket_button":
                ctx = await self.cogsutils.invoke_command(
                    author=interaction.user, channel=interaction.channel, command="ticket claim"
                )
                await interaction.followup.send(
                    _(
                        "You have chosen to claim this ticket. If this is not done, you do not have the necessary permissions to execute this command."
                    ),
                    ephemeral=True,
                )
            return

        async def on_dropdown_interaction(
            self, view: Dropdown, interaction: discord.Interaction, options: typing.List
        ):
            if len(options) == 0:
                if not interaction.response.is_done():
                    await interaction.response.defer()
                return
            permissions = interaction.channel.permissions_for(interaction.user)
            if not permissions.read_messages and not permissions.send_messages:
                return
            permissions = interaction.channel.permissions_for(interaction.guild.me)
            if not permissions.read_messages and not permissions.read_message_history:
                return
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=True)
            dropdowns = await self.config.guild(interaction.guild).dropdowns()
            if f"{interaction.message.channel.id}-{interaction.message.id}" not in dropdowns:
                await interaction.followup.send(
                    _("This message is not in TicketTool config."), ephemeral=True
                )
                return
            panel = dropdowns[f"{interaction.message.channel.id}-{interaction.message.id}"][0].get(
                "panel", "main"
            )
            panels = await self.config.guild(interaction.guild).panels()
            if panel not in panels:
                await interaction.followup.send(
                    _("The panel for which this dropdown was configured no longer exists."),
                    ephemeral=True,
                )
                return
            option = [option for option in view.options if option.value == options[0]][0]
            reason = f"{option.emoji} - {option.label}"
            ctx = await self.cogsutils.invoke_command(
                author=interaction.user,
                channel=interaction.channel,
                command=f"ticket create {panel} {reason}",
            )
            if not await discord.utils.async_all(
                check(ctx) for check in ctx.command.checks
            ) or not hasattr(ctx, "ticket"):
                await interaction.followup.send(
                    _("You are not allowed to execute this command."), ephemeral=True
                )
                return
            config = await self.get_config(interaction.guild, panel)
            if config["embed_button"]["rename_channel_dropdown"]:
                try:
                    ticket: Ticket = await self.get_ticket(
                        ctx.guild.get_channel(ctx.ticket.channel)
                    )
                    if ticket is not None:
                        await ticket.rename(
                            new_name=f"{option.emoji}-{option.value}_{interaction.user.id}".replace(
                                " ", "-"
                            ),
                            author=None,
                        )
                except discord.HTTPException:
                    pass
            await interaction.followup.send(
                _("You have chosen to create a ticket with the reason `{reason}`.").format(
                    **locals()
                ),
                ephemeral=True,
            )

    else:

        @commands.Cog.listener()
        async def on_button_click(self, inter: MessageInteraction):
            permissions = inter.channel.permissions_for(inter.author)
            if not permissions.read_messages and not permissions.send_messages:
                return
            permissions = inter.channel.permissions_for(inter.guild.me)
            if not permissions.read_messages and not permissions.read_message_history:
                return
            if not getattr(inter, "_sent", False) and not inter.expired:
                try:
                    await inter.respond(type=ResponseType.DeferredUpdateMessage, ephemeral=True)
                except discord.HTTPException:
                    pass
            if inter.clicked_button.custom_id == "create_ticket_button":
                buttons = await self.config.guild(inter.guild).buttons.all()
                if f"{inter.message.channel.id}-{inter.message.id}" in buttons:
                    panel = buttons[f"{inter.message.channel.id}-{inter.message.id}"]["panel"]
                else:
                    panel = "main"
                panels = await self.config.guild(inter.guild).panels()
                if panel not in panels:
                    await inter.followup(
                        _("The panel for which this button was configured no longer exists."),
                        ephemeral=True,
                    )
                    return
                ctx = await self.cogsutils.invoke_command(
                    author=inter.author, channel=inter.channel, command=f"ticket create {panel}"
                )
                if not await ctx.command.can_run(
                    ctx, change_permission_state=True
                ):  # await discord.utils.async_all(check(ctx) for check in ctx.command.checks)
                    await inter.followup(
                        _("You are not allowed to execute this command."), ephemeral=True
                    )
                else:
                    await inter.followup(
                        _("You have chosen to create a ticket.").format(**locals()), ephemeral=True
                    )
            elif inter.clicked_button.custom_id == "close_ticket_button":
                ctx = await self.cogsutils.invoke_command(
                    author=inter.author, channel=inter.channel, command="ticket close"
                )
                await inter.followup(
                    _(
                        "You have chosen to close this ticket. If this is not done, you do not have the necessary permissions to execute this command."
                    ),
                    ephemeral=True,
                )
            elif inter.clicked_button.custom_id == "claim_ticket_button":
                ctx = await self.cogsutils.invoke_command(
                    author=inter.author, channel=inter.channel, command="ticket claim"
                )
                await inter.followup(
                    _(
                        "You have chosen to claim this ticket. If this is not done, you do not have the necessary permissions to execute this command."
                    ),
                    ephemeral=True,
                )
            return

        @commands.Cog.listener()
        async def on_dropdown(self, inter: MessageInteraction):
            if not inter.select_menu.custom_id == "create_ticket_dropdown":
                return
            if len(inter.select_menu.selected_options) == 0:
                return
            permissions = inter.channel.permissions_for(inter.author)
            if not permissions.read_messages and not permissions.send_messages:
                return
            permissions = inter.channel.permissions_for(inter.guild.me)
            if not permissions.read_messages and not permissions.read_message_history:
                return
            if not getattr(inter, "_sent", False) and not inter.expired:
                try:
                    await inter.respond(type=ResponseType.DeferredUpdateMessage, ephemeral=True)
                except discord.HTTPException:
                    pass
            dropdowns = await self.config.guild(inter.guild).dropdowns()
            if f"{inter.message.channel.id}-{inter.message.id}" not in dropdowns:
                await inter.followup(
                    _("This message is not in TicketTool Config."), ephemeral=True
                )
                return
            panel = dropdowns[f"{inter.message.channel.id}-{inter.message.id}"][0].get(
                "panel", "main"
            )
            panels = await self.config.guild(inter.guild).panels()
            if panel not in panels:
                await inter.followup(
                    _("The panel for which this button was configured no longer exists."),
                    ephemeral=True,
                )
                return
            option = inter.select_menu.selected_options[0]
            reason = f"{option.emoji} - {option.label}"
            ctx = await self.cogsutils.invoke_command(
                author=inter.author,
                channel=inter.channel,
                command=f"ticket create {panel} {reason}",
            )
            if not await discord.utils.async_all(
                check(ctx) for check in ctx.command.checks
            ) or not hasattr(ctx, "ticket"):
                await inter.followup(
                    _("You are not allowed to execute this command."), ephemeral=True
                )
                return
            config = await self.get_config(inter.guild, panel)
            if config["embed_button"]["rename_channel_dropdown"]:
                try:
                    ticket: Ticket = await self.get_ticket(
                        ctx.guild.get_channel(ctx.ticket.channel)
                    )
                    if ticket is not None:
                        await ticket.rename(
                            new_name=(
                                f"{option.emoji}-{option.value}_{inter.author.id}".replace(
                                    " ", "-"
                                )
                            )[:99],
                            author=None,
                        )
                except discord.HTTPException:
                    pass
            await inter.followup(
                _("You have chosen to create a ticket with the reason `{reason}`.").format(
                    **locals()
                ),
                ephemeral=True,
            )

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if not payload.guild_id:
            return
        guild = self.bot.get_guild(payload.guild_id)
        channel = guild.get_channel(payload.channel_id)
        member = guild.get_member(payload.user_id)
        if member == guild.me or member.bot:
            return
        panel = "main"
        panels = await self.config.guild(guild).panels()
        if panel not in panels:
            return
        config = await self.get_config(guild, panel)
        if config["enable"]:
            if config["create_on_react"]:
                if str(payload.emoji) == str("🎟️"):
                    permissions = channel.permissions_for(member)
                    if not permissions.read_messages and not permissions.send_messages:
                        return
                    permissions = channel.permissions_for(guild.me)
                    if not permissions.read_messages and not permissions.read_message_history:
                        return
                    await self.cogsutils.invoke_command(
                        author=member, channel=channel, command="ticket create"
                    )
        return

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.guild is None:
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
        data = await self.config.guild(member.guild).tickets.all()
        for channel in data:
            channel = member.guild.get_channel(int(channel))
            if channel is None:
                continue
            ticket: Ticket = await self.get_ticket(channel)
            config = await self.get_config(ticket.guild, ticket.panel)
            if config["close_on_leave"]:
                if (
                    getattr(ticket.owner, "id", ticket.owner) == member.id
                    and ticket.status == "open"
                ):
                    await ticket.close(ticket.guild.me)
        return


class Ticket:
    """Representation of a ticket"""

    def __init__(
        self,
        bot,
        cog,
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
        first_message,
        panel,
    ):
        self.bot: Red = bot
        self.cog: commands.Cog = cog
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
        self.panel: str = panel

    @staticmethod
    def instance(
        ctx: commands.Context,
        panel: str,
        reason: typing.Optional[str] = _("No reason provided."),
    ):
        ticket: Ticket = Ticket(
            bot=ctx.bot,
            cog=ctx.cog,
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
            panel=panel,
        )
        return ticket

    @staticmethod
    def from_json(json: dict, bot: Red, cog: commands.Cog):
        ticket: Ticket = Ticket(
            bot=bot,
            cog=cog,
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
            panel=json["panel"],
        )
        return ticket

    async def save(ticket):
        if not ticket.save_data:
            return
        bot = ticket.bot
        cog = ticket.cog
        guild = ticket.guild
        channel = ticket.channel
        ticket.bot = None
        ticket.cog = None
        if ticket.owner is not None:
            ticket.owner = int(getattr(ticket.owner, "id", ticket.owner))
        if ticket.guild is not None:
            ticket.guild = int(ticket.guild.id)
        if ticket.channel is not None:
            ticket.channel = int(ticket.channel.id)
        if ticket.claim is not None:
            ticket.claim = ticket.claim.id
        if ticket.created_by is not None:
            ticket.created_by = (
                int(ticket.created_by.id)
                if not isinstance(ticket.created_by, int)
                else int(ticket.created_by)
            )
        if ticket.opened_by is not None:
            ticket.opened_by = (
                int(ticket.opened_by.id)
                if not isinstance(ticket.opened_by, int)
                else int(ticket.opened_by)
            )
        if ticket.closed_by is not None:
            ticket.closed_by = (
                int(ticket.closed_by.id)
                if not isinstance(ticket.closed_by, int)
                else int(ticket.closed_by)
            )
        if ticket.deleted_by is not None:
            ticket.deleted_by = (
                int(ticket.deleted_by.id)
                if not isinstance(ticket.deleted_by, int)
                else int(ticket.deleted_by)
            )
        if ticket.renamed_by is not None:
            ticket.renamed_by = (
                int(ticket.renamed_by.id)
                if not isinstance(ticket.renamed_by, int)
                else int(ticket.renamed_by)
            )
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
        data = await cog.config.guild(guild).tickets.all()
        data[str(channel.id)] = json
        await cog.config.guild(guild).tickets.set(data)
        return data

    async def create(ticket):
        config = await ticket.cog.get_config(ticket.guild, ticket.panel)
        logschannel = config["logschannel"]
        overwrites = await utils().get_overwrites(ticket)
        emoji_open = config["emoji_open"]
        ping_role = config["ping_role"]
        ticket.id = config["last_nb"] + 1
        reason = await ticket.cog.get_audit_reason(
            guild=ticket.guild,
            panel=ticket.panel,
            author=ticket.created_by,
            reason=_("Creating the ticket {ticket.id}.").format(**locals()),
        )
        try:
            to_replace = {
                "ticket_id": str(ticket.id),
                "owner_display_name": ticket.owner.display_name,
                "owner_name": ticket.owner.name,
                "owner_id": str(ticket.owner.id),
                "guild_name": ticket.guild.name,
                "guild_id": ticket.guild.id,
                "bot_display_name": ticket.guild.me.display_name,
                "bot_name": ticket.bot.user.name,
                "bot_id": str(ticket.bot.user.id),
                "shortdate": ticket.created_at.strftime("%m-%d"),
                "longdate": ticket.created_at.strftime("%m-%d-%Y"),
                "time": ticket.created_at.strftime("%I-%M-%p"),
            }
            name = config["dynamic_channel_name"].format(**to_replace).replace(" ", "-")
            ticket.channel = await ticket.guild.create_text_channel(
                name,
                overwrites=overwrites,
                category=config["category_open"],
                topic=ticket.reason,
                reason=reason,
            )
        except (KeyError, AttributeError, discord.HTTPException):
            name = f"{emoji_open}-ticket-{ticket.id}"
            ticket.channel = await ticket.guild.create_text_channel(
                name,
                overwrites=overwrites,
                category=config["category_open"],
                topic=ticket.reason,
                reason=reason,
            )
        topic = _(
            "🎟️ Ticket ID: {ticket.id}\n"
            "🔥 Channel ID: {ticket.channel.id}\n"
            "🕵️ Ticket created by: @{ticket.created_by.display_name} ({ticket.created_by.id})\n"
            "☢️ Ticket reason: {ticket.reason}\n"
            "👥 Ticket claimed by: Nobody."
        ).format(**locals())
        await ticket.channel.edit(topic=topic)
        if config["create_modlog"]:
            await ticket.cog.create_modlog(ticket, "ticket_created", reason)
        if CogsUtils().is_dpy2:
            view = Buttons(
                timeout=None,
                buttons=[
                    {
                        "style": 2,
                        "label": _("Close"),
                        "emoji": "🔒",
                        "custom_id": "close_ticket_button",
                        "disabled": False,
                    },
                    {
                        "style": 2,
                        "label": _("Claim"),
                        "emoji": "🙋‍♂️",
                        "custom_id": "claim_ticket_button",
                        "disabled": False,
                    },
                ],
                function=ticket.cog.on_button_interaction,
                infinity=True,
            )
        else:
            buttons = ActionRow(
                Button(
                    style=ButtonStyle.grey,
                    label=_("Close"),
                    emoji="🔒",
                    custom_id="close_ticket_button",
                    disabled=False,
                ),
                Button(
                    style=ButtonStyle.grey,
                    label=_("Claim"),
                    emoji="🙋‍♂️",
                    custom_id="claim_ticket_button",
                    disabled=False,
                ),
            )
        if ping_role is not None:
            optionnal_ping = f" ||{ping_role.mention}||"
        else:
            optionnal_ping = ""
        embed = await ticket.cog.get_embed_important(
            ticket,
            False,
            author=ticket.created_by,
            title=_("Ticket Created"),
            description=_("Thank you for creating a ticket on this server!"),
        )
        if CogsUtils().is_dpy2:
            ticket.first_message = await ticket.channel.send(
                f"{ticket.created_by.mention}{optionnal_ping}",
                embed=embed,
                view=view,
                allowed_mentions=discord.AllowedMentions(users=True, roles=True),
            )
        else:
            ticket.first_message = await ticket.channel.send(
                f"{ticket.created_by.mention}{optionnal_ping}",
                embed=embed,
                components=[buttons],
                allowed_mentions=discord.AllowedMentions(users=True, roles=True),
            )
        self.cogsutils.views.append(view)
        if config["custom_message"] is not None:
            try:
                embed: discord.Embed = discord.Embed()
                embed.title = "Custom Message"
                to_replace = {
                    "ticket_id": str(ticket.id),
                    "owner_display_name": ticket.owner.display_name,
                    "owner_name": ticket.owner.name,
                    "owner_id": str(ticket.owner.id),
                    "guild_name": ticket.guild.name,
                    "guild_id": ticket.guild.id,
                    "bot_display_name": ticket.guild.me.display_name,
                    "bot_name": ticket.bot.user.name,
                    "bot_id": str(ticket.bot.user.id),
                    "shortdate": ticket.created_at.strftime("%m-%d"),
                    "longdate": ticket.created_at.strftime("%m-%d-%Y"),
                    "time": ticket.created_at.strftime("%I-%M-%p"),
                }
                embed.description = config["custom_message"].format(**to_replace)
                await ticket.channel.send(embed=embed)
            except (KeyError, AttributeError, discord.HTTPException):
                pass
        if logschannel is not None:
            embed = await ticket.cog.get_embed_important(
                ticket,
                True,
                author=ticket.created_by,
                title=_("Ticket Created"),
                description=_("The ticket was created by {ticket.created_by}.").format(**locals()),
            )
            await logschannel.send(
                _("Report on the creation of the ticket {ticket.id}.").format(**locals()),
                embed=embed,
            )
        if config["ticket_role"] is not None:
            if ticket.owner:
                try:
                    await ticket.owner.add_roles(config["ticket_role"], reason=reason)
                except discord.HTTPException:
                    pass
        await ticket.cog.config.guild(ticket.guild).panels.set_raw(
            ticket.panel, "last_nb", value=ticket.id
        )
        await ticket.save()
        return ticket

    async def export(ticket):
        if ticket.channel:
            if ticket.cog.cogsutils.is_dpy2:
                transcript = await chat_exporter.export(
                    channel=ticket.channel,
                    limit=None,
                    tz_info="UTC",
                    guild=ticket.guild,
                    bot=ticket.bot,
                )
            else:
                transcript = await chat_exporter.export(
                    channel=ticket.channel, guild=ticket.guild, limit=None
                )
            if transcript is not None:
                transcript_file = discord.File(
                    io.BytesIO(transcript.encode()),
                    filename=f"transcript-ticket-{ticket.panel}-{ticket.id}.html",
                )
                return transcript_file
        return None

    async def open(ticket, author: typing.Optional[discord.Member] = None):
        config = await ticket.cog.get_config(ticket.guild, ticket.panel)
        reason = await ticket.cog.get_audit_reason(
            guild=ticket.guild,
            panel=ticket.panel,
            author=author,
            reason=_("Opening the ticket {ticket.id}.").format(**locals()),
        )
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
            embed = await ticket.cog.get_embed_action(
                ticket, author=ticket.opened_by, action=_("Ticket Opened")
            )
            await ticket.channel.send(embed=embed)
            if logschannel is not None:
                embed = await ticket.cog.get_embed_important(
                    ticket,
                    True,
                    author=ticket.opened_by,
                    title=_("Ticket Opened"),
                    description=_("The ticket was opened by {ticket.opened_by}.").format(
                        **locals()
                    ),
                )
                await logschannel.send(
                    _("Report on the close of the ticket {ticket.id}.").format(**locals()),
                    embed=embed,
                )
        if ticket.first_message is not None:
            try:
                if CogsUtils().is_dpy2:
                    view = Buttons(
                        timeout=None,
                        buttons=[
                            {
                                "style": 2,
                                "label": _("Close"),
                                "emoji": "🔒",
                                "custom_id": "close_ticket_button",
                                "disabled": False,
                            },
                            {
                                "style": 2,
                                "label": _("Claim"),
                                "emoji": "🙋‍♂️",
                                "custom_id": "claim_ticket_button",
                                "disabled": False,
                            },
                        ],
                        function=ticket.cog.on_button_interaction,
                        infinity=True,
                    )
                    ticket.first_message = await ticket.channel.fetch_message(
                        int(ticket.first_message.id)
                    )
                    await ticket.first_message.edit(view=view)
                else:
                    buttons = ActionRow(
                        Button(
                            style=ButtonStyle.grey,
                            label=_("Close"),
                            emoji="🔒",
                            custom_id="close_ticket_button",
                            disabled=False,
                        ),
                        Button(
                            style=ButtonStyle.grey,
                            label=_("Claim"),
                            emoji="🙋‍♂️",
                            custom_id="claim_ticket_button",
                            disabled=False,
                        ),
                    )
                    ticket.first_message = await ticket.channel.fetch_message(
                        int(ticket.first_message.id)
                    )
                    await ticket.first_message.edit(components=[buttons])
            except discord.HTTPException:
                pass
        await ticket.save()
        return ticket

    async def close(ticket, author: typing.Optional[discord.Member] = None):
        config = await ticket.cog.get_config(ticket.guild, ticket.panel)
        reason = await ticket.cog.get_audit_reason(
            guild=ticket.guild,
            panel=ticket.panel,
            author=author,
            reason=f"Closing the ticket {ticket.id}.",
        )
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
            embed = await ticket.cog.get_embed_action(
                ticket, author=ticket.closed_by, action="Ticket Closed"
            )
            await ticket.channel.send(embed=embed)
            if logschannel is not None:
                embed = await ticket.cog.get_embed_important(
                    ticket,
                    True,
                    author=ticket.closed_by,
                    title="Ticket Closed",
                    description=f"The ticket was closed by {ticket.closed_by}.",
                )
                await logschannel.send(
                    _("Report on the close of the ticket {ticket.id}."),
                    embed=embed,
                )
        if ticket.first_message is not None:
            try:
                if CogsUtils().is_dpy2:
                    view = Buttons(
                        timeout=None,
                        buttons=[
                            {
                                "style": 2,
                                "label": _("Close"),
                                "emoji": "🔒",
                                "custom_id": "close_ticket_button",
                                "disabled": True,
                            },
                            {
                                "style": 2,
                                "label": _("Claim"),
                                "emoji": "🙋‍♂️",
                                "custom_id": "claim_ticket_button",
                                "disabled": True,
                            },
                        ],
                        function=ticket.cog.on_button_interaction,
                        infinity=True,
                    )
                    ticket.first_message = await ticket.channel.fetch_message(
                        int(ticket.first_message.id)
                    )
                    await ticket.first_message.edit(view=view)
                else:
                    buttons = ActionRow(
                        Button(
                            style=ButtonStyle.grey,
                            label=_("Close"),
                            emoji="🔒",
                            custom_id="close_ticket_button",
                            disabled=True,
                        ),
                        Button(
                            style=ButtonStyle.grey,
                            label=_("Claim"),
                            emoji="🙋‍♂️",
                            custom_id="claim_ticket_button",
                            disabled=True,
                        ),
                    )
                    ticket.first_message = await ticket.channel.fetch_message(
                        int(ticket.first_message.id)
                    )
                    await ticket.first_message.edit(components=[buttons])
            except discord.HTTPException:
                pass
        await ticket.save()
        return ticket

    async def rename(ticket, new_name: str, author: typing.Optional[discord.Member] = None):
        reason = await ticket.cog.get_audit_reason(
            guild=ticket.guild,
            panel=ticket.panel,
            author=author,
            reason=_(
                "Renaming the ticket {ticket.id}. (`{ticket.channel.name}` to `{new_name}`)"
            ).format(**locals()),
        )
        await ticket.channel.edit(name=new_name, reason=reason)
        if author is not None:
            ticket.renamed_by = author
            ticket.renamed_at = datetime.datetime.now()
            if ticket.logs_messages:
                embed = await ticket.cog.get_embed_action(
                    ticket,
                    author=ticket.renamed_by,
                    action=_("Ticket Renamed."),
                )
                await ticket.channel.send(embed=embed)
            await ticket.save()
        return ticket

    async def delete(ticket, author: typing.Optional[discord.Member] = None):
        config = await ticket.cog.get_config(ticket.guild, ticket.panel)
        logschannel = config["logschannel"]
        reason = await ticket.cog.get_audit_reason(
            guild=ticket.guild,
            panel=ticket.panel,
            author=author,
            reason=_("Deleting the ticket {ticket.id}.").format(**locals()),
        )
        ticket.deleted_by = author
        ticket.deleted_at = datetime.datetime.now()
        if ticket.logs_messages:
            if logschannel is not None:
                embed = await ticket.cog.get_embed_important(
                    ticket,
                    True,
                    author=ticket.deleted_by,
                    title=_("Ticket Deleted"),
                    description=_("The ticket was deleted by {ticket.deleted_by}.").format(
                        **locals()
                    ),
                )
                try:
                    if ticket.cog.cogsutils.is_dpy2:
                        transcript = await chat_exporter.export(
                            channel=ticket.channel,
                            limit=None,
                            tz_info="UTC",
                            guild=ticket.guild,
                            bot=ticket.bot,
                        )
                    else:
                        transcript = await chat_exporter.export(
                            channel=ticket.channel, guild=ticket.guild, limit=None
                        )
                except AttributeError:
                    transcript = None
                if transcript is not None:
                    file = discord.File(
                        io.BytesIO(transcript.encode()),
                        filename=f"transcript-ticket-{ticket.id}.html",
                    )
                else:
                    file = None
                message = await logschannel.send(
                    _("Report on the deletion of the ticket {ticket.id}.").format(**locals()),
                    embed=embed,
                    file=file,
                )
                embed = discord.Embed(
                    title="Transcript Link",
                    description=(
                        f"[Click here to view the transcript.](https://mahto.id/chat-exporter?url={message.attachments[0].url})"
                    ),
                    colour=discord.Colour.green(),
                )
                await logschannel.send(embed=embed)
        await ticket.channel.delete(reason=reason)
        data = await ticket.cog.config.guild(ticket.guild).tickets.all()
        try:
            del data[str(ticket.channel.id)]
        except KeyError:
            pass
        await ticket.cog.config.guild(ticket.guild).tickets.set(data)
        return ticket

    async def claim_ticket(
        ticket, member: discord.Member, author: typing.Optional[discord.Member] = None
    ):
        config = await ticket.cog.get_config(ticket.guild, ticket.panel)
        reason = await ticket.cog.get_audit_reason(
            guild=ticket.guild,
            panel=ticket.panel,
            author=author,
            reason=_("Claiming the ticket {ticket.id}.").format(**locals()),
        )
        if member.bot:
            raise commands.UserFeedbackCheckFailure(_("A bot cannot claim a ticket."))
        ticket.claim = member
        topic = _(
            "🎟️ Ticket ID: {ticket.id}\n"
            "🔥 Channel ID: {ticket.channel.id}\n"
            "🕵️ Ticket created by: @{ticket.created_by.display_name} ({ticket.created_by.id})\n"
            "☢️ Ticket reason: {ticket.reason}\n"
            "👥 Ticket claimed by: @{ticket.claim.display_name} (@{ticket.claim.id})."
        ).format(**locals())
        overwrites = ticket.channel.overwrites
        overwrites[member] = discord.PermissionOverwrite(
            attach_files=True,
            read_message_history=True,
            read_messages=True,
            send_messages=True,
            view_channel=True,
        )
        if config["support_role"] is not None:
            overwrites[config["support_role"]] = discord.PermissionOverwrite(
                attach_files=False,
                read_message_history=True,
                read_messages=True,
                send_messages=False,
                view_channel=True,
            )
        await ticket.channel.edit(topic=topic, overwrites=overwrites, reason=reason)
        if ticket.first_message is not None:
            try:
                if CogsUtils().is_dpy2:
                    view = Buttons(
                        timeout=None,
                        buttons=[
                            {
                                "style": 2,
                                "label": _("Close"),
                                "emoji": "🔒",
                                "custom_id": "close_ticket_button",
                                "disabled": False if ticket.status == "open" else True,
                            },
                            {
                                "style": 2,
                                "label": _("Claim"),
                                "emoji": "🙋‍♂️",
                                "custom_id": "claim_ticket_button",
                                "disabled": True,
                            },
                        ],
                        function=ticket.cog.on_button_interaction,
                        infinity=True,
                    )
                    ticket.first_message = await ticket.channel.fetch_message(
                        int(ticket.first_message.id)
                    )
                    await ticket.first_message.edit(view=view)
                else:
                    buttons = ActionRow(
                        Button(
                            style=ButtonStyle.grey,
                            label=_("Close"),
                            emoji="🔒",
                            custom_id="close_ticket_button",
                            disabled=False if ticket.status == "open" else True,
                        ),
                        Button(
                            style=ButtonStyle.grey,
                            label=_("Claim"),
                            emoji="🙋‍♂️",
                            custom_id="claim_ticket_button",
                            disabled=True,
                        ),
                    )
                    ticket.first_message = await ticket.channel.fetch_message(
                        int(ticket.first_message.id)
                    )
                    await ticket.first_message.edit(components=[buttons])
            except discord.HTTPException:
                pass
        await ticket.save()
        return ticket

    async def unclaim_ticket(
        ticket, member: discord.Member, author: typing.Optional[discord.Member] = None
    ):
        config = await ticket.cog.get_config(ticket.guild, ticket.panel)
        reason = await ticket.cog.get_audit_reason(
            guild=ticket.guild,
            panel=ticket.panel,
            author=author,
            reason=_("Claiming the ticket {ticket.id}.").format(**locals()),
        )
        ticket.claim = None
        topic = _(
            "🎟️ Ticket ID: {ticket.id}\n"
            "🔥 Channel ID: {ticket.channel.id}\n"
            "🕵️ Ticket created by: @{ticket.created_by.display_name} ({ticket.created_by.id})\n"
            "☢️ Ticket reason: {ticket.reason}\n"
            "👥 Ticket claimed by: Nobody."
        ).format(**locals())
        await ticket.channel.edit(topic=topic)
        if config["support_role"] is not None:
            overwrites = ticket.channel.overwrites
            overwrites[config["support_role"]] = discord.PermissionOverwrite(
                attach_files=True,
                read_message_history=True,
                read_messages=True,
                send_messages=True,
                view_channel=True,
            )
            await ticket.channel.edit(overwrites=overwrites, reason=reason)
        await ticket.channel.set_permissions(member, overwrite=None, reason=reason)
        if ticket.first_message is not None:
            try:
                if CogsUtils().is_dpy2:
                    view = Buttons(
                        timeout=None,
                        buttons=[
                            {
                                "style": 2,
                                "label": _("Close"),
                                "emoji": "🔒",
                                "custom_id": "close_ticket_button",
                                "disabled": False if ticket.status == "open" else True,
                            },
                            {
                                "style": 2,
                                "label": _("Claim"),
                                "emoji": "🙋‍♂️",
                                "custom_id": "claim_ticket_button",
                                "disabled": True,
                            },
                        ],
                        function=ticket.cog.on_button_interaction,
                        infinity=True,
                    )
                    ticket.first_message = await ticket.channel.fetch_message(
                        int(ticket.first_message.id)
                    )
                    await ticket.first_message.edit(view=view)
                else:
                    buttons = ActionRow(
                        Button(
                            style=ButtonStyle.grey,
                            label=_("Close"),
                            emoji="🔒",
                            custom_id="close_ticket_button",
                            disabled=False if ticket.status == "open" else True,
                        ),
                        Button(
                            style=ButtonStyle.grey,
                            label=_("Claim"),
                            emoji="🙋‍♂️",
                            custom_id="claim_ticket_button",
                            disabled=False,
                        ),
                    )
                    ticket.first_message = await ticket.channel.fetch_message(
                        int(ticket.first_message.id)
                    )
                    await ticket.first_message.edit(components=[buttons])
            except discord.HTTPException:
                pass
        await ticket.save()
        return ticket

    async def change_owner(
        ticket, member: discord.Member, author: typing.Optional[discord.Member] = None
    ):
        config = await ticket.cog.get_config(ticket.guild, ticket.panel)
        reason = await ticket.cog.get_audit_reason(
            guild=ticket.guild,
            panel=ticket.panel,
            author=author,
            reason=_("Changing owner of the ticket {ticket.id}.").format(**locals()),
        )
        if member.bot:
            raise commands.UserFeedbackCheckFailure(
                _("You cannot transfer ownership of a ticket to a bot.")
            )
        if not isinstance(ticket.owner, int):
            if config["ticket_role"] is not None:
                try:
                    ticket.owner.remove_roles(config["ticket_role"], reason=reason)
                except discord.HTTPException:
                    pass
            ticket.remove_member(ticket.owner, author=None)
            ticket.add_member(ticket.owner, author=None)
        ticket.owner = member
        ticket.remove_member(ticket.owner, author=None)
        overwrites = ticket.channel.overwrites
        overwrites[member] = discord.PermissionOverwrite(
            attach_files=True,
            read_message_history=True,
            read_messages=True,
            send_messages=True,
            view_channel=True,
        )
        await ticket.channel.edit(overwrites=overwrites, reason=reason)
        if config["ticket_role"] is not None:
            try:
                ticket.owner.add_roles(config["ticket_role"], reason=reason)
            except discord.HTTPException:
                pass
        if ticket.logs_messages:
            embed = await ticket.cog.get_embed_action(
                ticket, author=author, action=_("Owner Modified.")
            )
            await ticket.channel.send(embed=embed)
        await ticket.save()
        return ticket

    async def add_member(
        ticket,
        members: typing.List[discord.Member],
        author: typing.Optional[discord.Member] = None,
    ):
        config = await ticket.cog.get_config(ticket.guild, ticket.panel)
        reason = await ticket.cog.get_audit_reason(
            guild=ticket.guild,
            panel=ticket.panel,
            author=author,
            reason=_("Adding a member to the ticket {ticket.id}.").format(**locals()),
        )
        if config["admin_role"] is not None:
            admin_role_members = config["admin_role"].members
        else:
            admin_role_members = []
        overwrites = ticket.channel.overwrites
        for member in members:
            if author is not None:
                if member.bot:
                    raise commands.UserFeedbackCheckFailure(
                        _("You cannot add a bot to a ticket. ({member})").format(**locals())
                    )
                if not isinstance(ticket.owner, int):
                    if member == ticket.owner:
                        raise commands.UserFeedbackCheckFailure(
                            _(
                                "This member is already the owner of this ticket. ({member})"
                            ).format(**locals())
                        )
                if member in admin_role_members:
                    raise commands.UserFeedbackCheckFailure(
                        _(
                            "This member is an administrator for the ticket system. They will always have access to the ticket anyway. ({member})"
                        ).format(**locals())
                    )
                if member in ticket.members:
                    raise commands.UserFeedbackCheckFailure(
                        _("This member already has access to this ticket. ({member})").format(
                            **locals()
                        )
                    )
            if member not in ticket.members:
                ticket.members.append(member)
            overwrites[member] = discord.PermissionOverwrite(
                attach_files=True,
                read_message_history=True,
                read_messages=True,
                send_messages=True,
                view_channel=True,
            )
        await ticket.channel.edit(overwrites=overwrites, reason=reason)
        await ticket.save()
        return ticket

    async def remove_member(
        ticket,
        members: typing.List[discord.Member],
        author: typing.Optional[discord.Member] = None,
    ):
        config = await ticket.cog.get_config(ticket.guild, ticket.panel)
        reason = await ticket.cog.get_audit_reason(
            guild=ticket.guild,
            panel=ticket.panel,
            author=author,
            reason=_("Removing a member to the ticket {ticket.id}.").format(**locals()),
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
                    raise commands.UserFeedbackCheckFailure(
                        _("You cannot remove a bot to a ticket ({member}).").format(locals())
                    )
                if not isinstance(ticket.owner, int):
                    if member == ticket.owner:
                        raise commands.UserFeedbackCheckFailure(
                            _("You cannot remove the owner of this ticket. ({member})").format(
                                **locals()
                            )
                        )
                if member in admin_role_members:
                    raise commands.UserFeedbackCheckFailure(
                        _(
                            "This member is an administrator for the ticket system. They will always have access to the ticket. ({member})"
                        ).format(**locals())
                    )
                if member not in ticket.members and member not in support_role_members:
                    raise commands.UserFeedbackCheckFailure(
                        _(
                            "This member is not in the list of those authorised to access the ticket. ({member})"
                        ).format(locals())
                    )
            if member in ticket.members:
                ticket.members.remove(member)
            if member in support_role_members:
                overwrites = ticket.channel.overwrites
                overwrites[member] = discord.PermissionOverwrite(
                    attach_files=False,
                    read_message_history=False,
                    read_messages=False,
                    send_messages=False,
                    view_channel=False,
                )
                await ticket.channel.edit(overwrites=overwrites, reason=reason)
            else:
                await ticket.channel.set_permissions(member, overwrite=None, reason=reason)
        await ticket.save()
        return ticket

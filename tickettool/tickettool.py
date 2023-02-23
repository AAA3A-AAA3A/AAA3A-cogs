from .AAA3A_utils import CogsUtils, Settings  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
from redbot.core.bot import Red  # isort:skip
import discord  # isort:skip
import typing  # isort:skip*

if CogsUtils().is_dpy2:
    from .AAA3A_utils import Buttons, Dropdown, Modal  # isort:skip
else:
    from dislash import (
        MessageInteraction,
        ResponseType,
    )  # isort:skip

import datetime
import io
from copy import deepcopy

import chat_exporter
from redbot.core import Config, modlog

from .settings import settings
from .ticket import Ticket

# Credits:
# General repo credits.
# Thanks to Yami for the technique in the init file of some cogs to load the interaction client only if it is not already loaded! Before this fix, when a user clicked a button, the actions would be run about 10 times, causing a huge spam and loop in the channel.

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

    def __init__(self, bot: Red) -> None:
        self.bot: Red = bot

        self.config: Config = Config.get_conf(
            self,
            identifier=205192943327321000143939875896557571750,  # 937480369417
            force_registration=True,
        )
        self.CONFIG_SCHEMA: int = 2
        self.tickettool_global: typing.Dict[str, typing.Optional[int]] = {
            "CONFIG_SCHEMA": None,
        }
        self.tickettool_guild: typing.Dict[
            str,
            typing.Union[
                typing.Dict[
                    str,
                    typing.Dict[
                        str, typing.Union[bool, str, typing.Optional[str], typing.Optional[int]]
                    ],
                ],
                typing.Dict[
                    str, typing.Union[bool, str, typing.Optional[str], typing.Optional[int]]
                ],
            ],
        ] = {
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

        self.cogsutils: CogsUtils = CogsUtils(cog=self)

        _settings: typing.Dict[
            str, typing.Dict[str, typing.Union[typing.List[str], typing.Any, str]]
        ] = {
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
                "no_slash": True,
            },
        }
        self.settings: Settings = Settings(
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

    async def load_buttons(self) -> None:
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

    async def get_config(self, guild: discord.Guild, panel: str) -> typing.Dict[str, typing.Any]:
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

    async def get_ticket(self, channel: discord.TextChannel) -> Ticket:
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
    ) -> str:
        if reason is None:
            reason = _("Action taken for the ticket system.")
        config = await self.get_config(guild, panel)
        if author is None or not config["audit_logs"]:
            return f"{reason}"
        else:
            return f"{author.name} ({author.id}) - {reason}"

    async def get_embed_important(
        self, ticket, more: bool, author: discord.Member, title: str, description: str
    ) -> discord.Embed:
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

    async def get_embed_action(self, ticket, author: discord.Member, action: str) -> discord.Embed:
        config = await self.get_config(ticket.guild, ticket.panel)
        actual_color = config["color"]
        embed: discord.Embed = discord.Embed()
        embed.title = _("Ticket [{ticket.panel}] {ticket.id} - Action taken").format(ticket=ticket)
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

    async def check_limit(self, member: discord.Member, panel: str) -> bool:
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

    async def create_modlog(
        self, ticket, action: str, reason: str
    ) -> typing.Optional[modlog.Case]:
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
    ) -> None:
        async def pred(ctx) -> bool:
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
        async def convert(self, ctx: commands.Context, argument: str) -> str:
            if len(argument) > 10:
                raise commands.BadArgument(_("This panel does not exist."))
            panels = await ctx.bot.get_cog("TicketTool").config.guild(ctx.guild).panels()
            if argument.lower() not in panels:
                raise commands.BadArgument(_("This panel does not exist."))
            return argument.lower()

    @commands.guild_only()
    @hybrid_group(name="ticket")
    async def ticket(self, ctx: commands.Context) -> None:
        """Commands for using the ticket system."""

    @ticket.command(name="create")
    async def command_create(
        self,
        ctx: commands.Context,
        panel: typing.Optional[PanelConverter] = "main",
        *,
        reason: typing.Optional[str] = "No reason provided.",
    ) -> None:
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
                ).format(ctx=ctx)
            )
        if category_open is None or category_close is None:
            raise commands.UserFeedbackCheckFailure(
                _(
                    "The category `open` or the category `close` have not been configured. Please ask an administrator of this server to use the `{ctx.prefix}ticketset` subcommands to configure it."
                ).format(ctx=ctx)
            )
        if not await self.check_limit(ctx.author, panel):
            limit = config["nb_max"]
            raise commands.UserFeedbackCheckFailure(
                _("Sorry. You have already reached the limit of {limit} open tickets.").format(
                    limit=limit
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
    async def command_export(self, ctx: commands.Context) -> None:
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
    ) -> None:
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
    ) -> None:
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
                ticket=ticket
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
    ) -> None:
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
    ) -> None:
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
            ).format(ticket=ticket)
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
    ) -> None:
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
    ) -> None:
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
    ) -> None:
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
    ) -> None:
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
    ) -> None:
        """Remove a member to an existing ticket."""
        ticket: Ticket = await self.get_ticket(ctx.channel)
        ticket.reason = reason
        members = [member for member in members]
        await ticket.remove_member(members, ctx.author)

    if CogsUtils().is_dpy2:

        async def on_button_interaction(
            self, view: Buttons, interaction: discord.Interaction
        ) -> None:
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
        ) -> None:
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
                    reason=reason
                ),
                ephemeral=True,
            )

    else:

        @commands.Cog.listener()
        async def on_button_click(self, inter: MessageInteraction) -> None:
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
                    await inter.followup(_("You have chosen to create a ticket."), ephemeral=True)
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
        async def on_dropdown(self, inter: MessageInteraction) -> None:
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
                    reason=reason
                ),
                ephemeral=True,
            )

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
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
    async def on_message_delete(self, message: discord.Message) -> None:
        if message.guild is None:
            return
        config = await self.config.guild(message.guild).dropdowns.all()
        if f"{message.channel.id}-{message.id}" not in config:
            return
        del config[f"{message.channel.id}-{message.id}"]
        await self.config.guild(message.guild).dropdowns.set(config)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, old_channel: discord.abc.GuildChannel) -> None:
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
    async def on_member_remove(self, member: discord.Member) -> None:
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

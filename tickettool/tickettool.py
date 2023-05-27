from AAA3A_utils import Cog, CogsUtils, Menu, Settings, Modal  # isort:skip
from redbot.core import commands, Config  # isort:skip
from redbot.core.bot import Red  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import datetime
import chat_exporter
import io
from copy import deepcopy
from functools import partial

from redbot.core import modlog
from redbot.core.utils.chat_formatting import pagify

from .dashboard_integration import DashboardIntegration
from .settings import settings
from .ticket import Ticket

# Credits:
# General repo credits.
# Thanks to Yami for the technique in the init file of some cogs to load the interaction client only if it is not already loaded! Before this fix, when a user clicked a button, the actions would be run about 10 times, causing a huge spam and loop in the channel.

_ = Translator("TicketTool", __file__)


@cog_i18n(_)
class TicketTool(settings, DashboardIntegration, Cog):
    """A cog to manage a ticket system!"""

    def __init__(self, bot: Red) -> None:
        self.bot: Red = bot

        self.config: Config = Config.get_conf(
            self,
            identifier=205192943327321000143939875896557571750,  # 937480369417
            force_registration=True,
        )
        self.CONFIG_SCHEMA: int = 3
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
            "profiles": {},
            "default_profile_settings": {
                "enable": False,
                "logschannel": None,
                "forum_channel": None,
                "category_open": None,
                "category_close": None,
                "admin_role": None,
                "support_role": None,
                "view_role": None,
                "ping_role": None,
                "ticket_role": None,
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
                    "placeholder_dropdown": "Choose a reason to open a ticket.",
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
            "forum_channel": {
                "path": ["forum_channel"],
                "converter": typing.Union[discord.ForumChannel, discord.TextChannel],
                "description": "Set the forum channel where the opened tickets will be, or a text channel to use private threads. If it's set, `category_open` and `category_close` will be ignored (except for existing tickets).",
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
                "path": ["view_role"],
                "converter": discord.Role,
                "description": "Users with this role will only be able to read messages from the ticket, but not send them.",
            },
            "ping_role": {
                "path": ["ping_role"],
                "converter": discord.Role,
                "description": "This role will be pinged automatically when the ticket is created, but does not give any additional permissions.",
            },
            "ticket_role": {
                "path": ["ticket_role"],
                "converter": discord.Role,
                "description": "This role will be added automatically to open tickets owners.",
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
                "style": discord.ButtonStyle(2),
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
                "no_slash": True,
            },
            "modlog": {
                "path": ["create_modlog"],
                "converter": bool,
                "description": "Does the bot create an action in the bot modlog when a ticket is created?",
                "no_slash": True,
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
            "rename_channel_dropdown": {
                "path": ["embed_button", "rename_channel_dropdown"],
                "converter": bool,
                "description": "With Dropdowns feature, rename the ticket channel with chosen reason.",
                "no_slash": True,
            },
        }
        self.settings: Settings = Settings(
            bot=self.bot,
            cog=self,
            config=self.config,
            group=self.config.GUILD,
            settings=_settings,
            global_path=["profiles"],
            use_profiles_system=True,
            can_edit=True,
            commands_group=self.configuration,
        )

    async def cog_load(self):
        await self.edit_config_schema()
        await self.settings.add_commands()
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
        if CONFIG_SCHEMA == 2:
            guild_group = self.config._get_base_group(self.config.GUILD)
            async with guild_group.all() as guilds_data:
                _guilds_data = deepcopy(guilds_data)
                for guild in _guilds_data:
                    if "profiles" in guilds_data[guild]:
                        continue
                    if "panels" in guilds_data[guild]:
                        guilds_data[guild]["profiles"] = guilds_data[guild]["panels"]
                        del guilds_data[guild]["panels"]
                    if "tickets" in guilds_data[guild]:
                        for channel_id in guilds_data[guild]["tickets"]:
                            if "panel" not in guilds_data[guild]["tickets"][channel_id]:
                                continue
                            guilds_data[guild]["tickets"][channel_id]["profile"] = guilds_data[guild]["tickets"][channel_id]["panel"]
                            del guilds_data[guild]["tickets"][channel_id]["panel"]
                    if "buttons" in guilds_data[guild]:
                        for message_id in guilds_data[guild]["buttons"]:
                            if "panel" not in guilds_data[guild]["buttons"][message_id]:
                                continue
                            guilds_data[guild]["buttons"][message_id]["profile"] = guilds_data[guild]["buttons"][message_id]["panel"]
                            del guilds_data[guild]["buttons"][message_id]["panel"]
                    if "dropdowns" in guilds_data[guild]:
                        for message_id in guilds_data[guild]["dropdowns"]:
                            if "panel" not in guilds_data[guild]["dropdowns"][message_id]:
                                continue
                            guilds_data[guild]["dropdowns"][message_id]["profile"] = guilds_data[guild]["dropdowns"][message_id]["panel"]
                            del guilds_data[guild]["dropdowns"][message_id]["panel"]
            CONFIG_SCHEMA = 3
            await self.config.CONFIG_SCHEMA.set(CONFIG_SCHEMA)
        if CONFIG_SCHEMA < self.CONFIG_SCHEMA:
            CONFIG_SCHEMA = self.CONFIG_SCHEMA
            await self.config.CONFIG_SCHEMA.set(CONFIG_SCHEMA)
        self.log.info(
            f"The Config schema has been successfully modified to {self.CONFIG_SCHEMA} for the {self.qualified_name} cog."
        )

    async def load_buttons(self) -> None:
        try:
            view = self.get_buttons(
                buttons=[
                    {
                        "style": discord.ButtonStyle(2),
                        "label": _("Create ticket"),
                        "emoji": "🎟️",
                        "custom_id": "create_ticket_button",
                        "disabled": False,
                    }
                ],
            )
            self.bot.add_view(view)
            self.cogsutils.views.append(view)
            view = self.get_buttons(
                buttons=[
                    {
                        "style": discord.ButtonStyle(2),
                        "label": _("Close"),
                        "emoji": "🔒",
                        "custom_id": "close_ticket_button",
                        "disabled": False,
                    },
                    {
                        "style": discord.ButtonStyle(2),
                        "label": _("Re-open"),
                        "emoji": "🔓",
                        "custom_id": "open_ticket_button",
                        "disabled": False,
                    },
                    {
                        "style": discord.ButtonStyle(2),
                        "label": _("Claim"),
                        "emoji": "🙋‍♂️",
                        "custom_id": "claim_ticket_button",
                        "disabled": False,
                    },
                    {
                        "style": discord.ButtonStyle(2),
                        "label": _("Delete"),
                        "emoji": "⛔",
                        "custom_id": "delete_ticket_button",
                        "disabled": False,
                    },
                ],
            )
            self.bot.add_view(view)
            self.cogsutils.views.append(view)
        except Exception as e:
            self.log.error("The Buttons View could not be added correctly.", exc_info=e)
        all_guilds = await self.config.all_guilds()
        for guild in all_guilds:
            for dropdown in all_guilds[guild]["dropdowns"]:
                try:
                    view = self.get_dropdown(
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
                    )
                    self.bot.add_view(view, message_id=int((str(dropdown).split("-"))[1]))
                    self.cogsutils.views.append(view)
                except Exception as e:
                    self.log.error(
                        f"The Dropdown View could not be added correctly for the {guild}-{dropdown} message.",
                        exc_info=e,
                    )

    async def get_config(self, guild: discord.Guild, profile: str) -> typing.Dict[str, typing.Any]:
        config = await self.config.guild(guild).profiles.get_raw(profile)
        for key, value in self.config._defaults[Config.GUILD]["default_profile_settings"].items():
            if key not in config:
                config[key] = value
        if config["logschannel"] is not None:
            config["logschannel"] = guild.get_channel(config["logschannel"])
        if config["forum_channel"] is not None:
            config["forum_channel"] = guild.get_channel(config["forum_channel"])
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
        tickets = await self.config.guild(channel.guild).tickets.all()
        if str(channel.id) in tickets:
            json = tickets[str(channel.id)]
        else:
            return None
        if "profile" not in json:
            json["profile"] = "main"
        ticket: Ticket = Ticket.from_json(json, self.bot, self)
        ticket.bot = self.bot
        ticket.cog = self
        ticket.guild = ticket.bot.get_guild(ticket.guild) or ticket.guild
        ticket.owner = ticket.guild.get_member(ticket.owner) or ticket.owner
        ticket.channel = channel
        ticket.claim = ticket.guild.get_member(ticket.claim) or ticket.claim
        ticket.created_by = ticket.guild.get_member(ticket.created_by) or ticket.created_by
        ticket.opened_by = ticket.guild.get_member(ticket.opened_by) or ticket.opened_by
        ticket.closed_by = ticket.guild.get_member(ticket.closed_by) or ticket.closed_by
        ticket.deleted_by = ticket.guild.get_member(ticket.deleted_by) or ticket.deleted_by
        ticket.renamed_by = ticket.guild.get_member(ticket.renamed_by) or ticket.renamed_by
        ticket.locked_by = ticket.guild.get_member(ticket.locked_by) or ticket.locked_by
        ticket.unlocked_by = ticket.guild.get_member(ticket.unlocked_by) or ticket.unlocked_by
        members = ticket.members
        ticket.members = []
        ticket.members.extend(channel.guild.get_member(m) for m in members)
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
        if ticket.locked_at is not None:
            ticket.locked_at = datetime.datetime.fromtimestamp(ticket.locked_at)
        if ticket.unlocked_at is not None:
            ticket.unlocked_at = datetime.datetime.fromtimestamp(ticket.unlocked_at)
        if ticket.first_message is not None:
            ticket.first_message = ticket.channel.get_partial_message(ticket.first_message)
        return ticket

    async def get_audit_reason(
        self,
        guild: discord.Guild,
        profile: str,
        author: typing.Optional[discord.Member] = None,
        reason: typing.Optional[str] = None,
    ) -> str:
        if reason is None:
            reason = _("Action taken for the ticket system.")
        config = await self.get_config(guild, profile)
        if author is None or not config["audit_logs"]:
            return f"{reason}"
        else:
            return f"{author.name} ({author.id}) - {reason}"

    async def get_embed_important(
        self, ticket, more: bool, author: discord.Member, title: str, description: str, reason: typing.Optional[str] = None
    ) -> discord.Embed:
        config = await self.get_config(ticket.guild, ticket.profile)
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
            url=author.display_avatar,
            icon_url=author.display_avatar,
        )
        embed.set_footer(
            text=ticket.guild.name,
            icon_url=ticket.guild.icon,
        )
        embed.add_field(inline=True, name=_("Ticket ID:"), value=f"[{ticket.profile}] {ticket.id}")
        embed.add_field(
            inline=True,
            name=_("Owned by:"),
            value=f"<@{ticket.owner}> ({ticket.owner})"
            if isinstance(ticket.owner, int)
            else f"{ticket.owner.mention} ({ticket.owner.id})",
        )
        if ticket.channel is not None:
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
                    value=f"<@{ticket.closed_by}> ({ticket.closed_by})"
                    if isinstance(ticket.closed_by, int)
                    else f"{ticket.closed_by.mention} ({ticket.closed_by.id})",
                )
            if ticket.deleted_by is not None:
                embed.add_field(
                    inline=True,
                    name=_("Deleted by:"),
                    value=f"<@{ticket.deleted_by}> ({ticket.deleted_by})"
                    if isinstance(ticket.deleted_by, int)
                    else f"{ticket.deleted_by.mention} ({ticket.deleted_by.id})",
                )
            if ticket.closed_at is not None:
                embed.add_field(
                    inline=False,
                    name=_("Closed at:"),
                    value=f"{ticket.closed_at}",
                )
        embed.add_field(inline=False, name=_("Reason:"), value=f"{reason}")
        return embed

    async def get_embed_action(self, ticket, author: discord.Member, action: str, reason: typing.Optional[str] = None) -> discord.Embed:
        config = await self.get_config(ticket.guild, ticket.profile)
        actual_color = config["color"]
        embed: discord.Embed = discord.Embed()
        embed.title = _("Ticket [{ticket.profile}] {ticket.id} - Action taken").format(ticket=ticket)
        embed.description = f"{action}"
        embed.color = actual_color
        embed.timestamp = datetime.datetime.now(tz=datetime.timezone.utc)
        embed.set_author(
            name=author,
            url=author.display_avatar,
            icon_url=author.display_avatar,
        )
        embed.set_footer(
            text=ticket.guild.name,
            icon_url=ticket.guild.icon,
        )
        embed.add_field(inline=False, name=_("Reason:"), value=f"{reason}")
        return embed

    async def check_limit(self, member: discord.Member, profile: str) -> bool:
        config = await self.get_config(member.guild, profile)
        tickets = await self.config.guild(member.guild).tickets.all()
        to_remove = []
        count = 1
        for id in tickets:
            if config["forum_channel"] is not None:
                channel = config["forum_channel"].get_thread(int(id))
            else:
                channel = member.guild.get_channel(int(id))
            if channel is not None:
                ticket: Ticket = await self.get_ticket(channel)
                if ticket.profile != profile:
                    continue
                if ticket.created_by == member and ticket.status == "open":
                    count += 1
            else:
                to_remove.append(id)
        if to_remove:
            tickets = await self.config.guild(member.guild).tickets.all()
            for id in to_remove:
                del tickets[str(id)]
            await self.config.guild(member.guild).tickets.set(tickets)
        return count <= config["nb_max"]

    async def create_modlog(
        self, ticket, action: str, reason: str
    ) -> typing.Optional[modlog.Case]:
        config = await self.get_config(ticket.guild, ticket.profile)
        if config["create_modlog"]:
            return await modlog.create_case(
                ticket.bot,
                ticket.guild,
                ticket.created_at,
                action_type=action,
                user=ticket.created_by,
                moderator=None,
                reason=reason,
            )
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
        locked: typing.Optional[bool] = None,
    ) -> None:
        async def pred(ctx) -> bool:
            if not ticket_check:
                return True

            ticket: Ticket = await ctx.bot.get_cog("TicketTool").get_ticket(ctx.channel)
            if ticket is None:
                return False
            config = await ctx.bot.get_cog("TicketTool").get_config(ticket.guild, ticket.profile)
            if status is not None and ticket.status != status:
                return False
            if claim is not None:
                if ticket.claim is not None:
                    check = True
                elif ticket.claim is None:
                    check = False
                if check != claim:
                    return False
            if (
                locked is not None
                and not isinstance(ticket.channel, discord.TextChannel)
                and ticket.channel.locked != locked
            ):
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

        return commands.check(pred)

    class ProfileConverter(commands.Converter):
        async def convert(self, ctx: commands.Context, argument: str) -> str:
            if len(argument) > 10:
                raise commands.BadArgument(_("This profile does not exist."))
            profiles = await ctx.bot.get_cog("TicketTool").config.guild(ctx.guild).profiles()
            if argument.lower() not in profiles:
                raise commands.BadArgument(_("This profile does not exist."))
            return argument.lower()

    @commands.guild_only()
    @commands.hybrid_group(name="ticket")
    async def ticket(self, ctx: commands.Context) -> None:
        """Commands for using the ticket system."""

    @ticket.command(name="create", aliases=["+"])
    async def command_create(
        self,
        ctx: commands.Context,
        profile: typing.Optional[ProfileConverter] = "main",
        *,
        reason: typing.Optional[str] = "No reason provided.",
    ) -> None:
        """Create a ticket."""
        profiles = await self.config.guild(ctx.guild).profiles()
        if profile not in profiles:
            raise commands.UserFeedbackCheckFailure(_("This profile does not exist."))
        config = await self.get_config(ctx.guild, profile)
        forum_channel: typing.Union[discord.ForumChannel, discord.Thread] = config["forum_channel"]
        category_open: discord.CategoryChannel = config["category_open"]
        category_close: discord.CategoryChannel = config["category_close"]
        if not config["enable"]:
            raise commands.UserFeedbackCheckFailure(
                _(
                    "The ticket system is not enabled on this server. Please ask an administrator of this server to use the `{ctx.prefix}ticketset` subcommands to configure it."
                ).format(ctx=ctx)
            )
        if forum_channel is None and (category_open is None or category_close is None):
            raise commands.UserFeedbackCheckFailure(
                _(
                    "The category `open` or the category `close` have not been configured. Please ask an administrator of this server to use the `{ctx.prefix}ticketset` subcommands to configure it."
                ).format(ctx=ctx)
            )
        if not await self.check_limit(ctx.author, profile):
            limit = config["nb_max"]
            raise commands.UserFeedbackCheckFailure(
                _("Sorry. You have already reached the limit of {limit} open tickets.").format(
                    limit=limit
                )
            )
        if forum_channel is None:
            if (
                not category_open.permissions_for(ctx.guild.me).manage_channels
                or not category_close.permissions_for(ctx.guild.me).manage_channels
            ):
                raise commands.UserFeedbackCheckFailure(
                    _(
                        "The bot does not have `manage_channels` permission on the `open` and `close` categories to allow the ticket system to function properly. Please notify an administrator of this server."
                    )
                )
        elif (
            not forum_channel.permissions_for(ctx.guild.me).create_private_threads
            or not forum_channel.permissions_for(ctx.guild.me).create_public_threads
        ):
            raise commands.UserFeedbackCheckFailure(
                _(
                    "The bot does not have `manage_channel` permission in the forum channel to allow the ticket system to function properly. Please notify an administrator of this server."
                )
            )
        ticket: Ticket = Ticket.instance(ctx, profile=profile, reason=reason)
        await ticket.create()
        ctx.ticket: Ticket = ticket

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
        locked=None,
    )
    @ticket.command(name="export")
    async def command_export(self, ctx: commands.Context) -> None:
        """Export all the messages of an existing ticket in html format.
        Please note: all attachments and user avatars are saved with the Discord link in this file.
        """
        ticket: Ticket = await self.get_ticket(ctx.channel)
        transcript = await chat_exporter.export(
            channel=ticket.channel,
            limit=None,
            tz_info="UTC",
            guild=ticket.guild,
            bot=ticket.bot,
        )
        if transcript is not None:
            file = discord.File(
                io.BytesIO(transcript.encode()),
                filename=f"transcript-ticket-{ticket.profile}-{ticket.id}.html",
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
            color=await ctx.embed_color(),
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
        locked=None,
    )
    @ticket.command(name="open", aliases=["reopen"])
    async def command_open(
        self, ctx: commands.Context, *, reason: typing.Optional[str] = "No reason provided."
    ) -> None:
        """Open an existing ticket."""
        ticket: Ticket = await self.get_ticket(ctx.channel)
        config = await ctx.bot.get_cog("TicketTool").get_config(ticket.guild, ticket.profile)
        if not config["enable"]:
            raise commands.UserFeedbackCheckFailure(
                _("The ticket system is not enabled on this server.")
            )
        await ticket.open(ctx.author, reason=reason)

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
        locked=None,
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
        config = await self.get_config(ticket.guild, ticket.profile)
        if config["delete_on_close"]:
            await self.command_delete(ctx, confirmation=confirmation, reason=reason)
            return
        if confirmation is None:
            config = await self.get_config(ticket.guild, ticket.profile)
            confirmation = not config["close_confirmation"]
        if not confirmation:
            embed: discord.Embed = discord.Embed()
            embed.title = _("Do you really want to close the ticket {ticket.id}?").format(
                ticket=ticket
            )
            embed.color = config["color"]
            embed.set_author(
                name=ctx.author.name,
                url=ctx.author.display_avatar,
                icon_url=ctx.author.display_avatar,
            )
            response = await self.cogsutils.ConfirmationAsk(ctx, embed=embed)
            if not response:
                return
        await ticket.close(ctx.author, reason=reason)

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
        locked=False,
    )
    @ticket.command(name="lock")
    async def command_lock(
        self,
        ctx: commands.Context,
        confirmation: typing.Optional[bool] = None,
        *,
        reason: typing.Optional[str] = _("No reason provided."),
    ) -> None:
        """Lock an existing ticket."""
        ticket: Ticket = await self.get_ticket(ctx.channel)
        if isinstance(ticket.channel, discord.TextChannel):
            raise commands.UserFeedbackCheckFailure(_("Cannot execute action on a text channel."))
        config = await self.get_config(ticket.guild, ticket.profile)
        if not confirmation:
            embed: discord.Embed = discord.Embed()
            embed.title = _("Do you really want to lock the ticket {ticket.id}?").format(
                ticket=ticket
            )
            embed.color = config["color"]
            embed.set_author(
                name=ctx.author.name,
                url=ctx.author.display_avatar,
                icon_url=ctx.author.display_avatar,
            )
            response = await self.cogsutils.ConfirmationAsk(ctx, embed=embed)
            if not response:
                return
        await ticket.lock(ctx.author, reason=reason)

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
        locked=True,
    )
    @ticket.command(name="unlock")
    async def command_unlock(
        self,
        ctx: commands.Context,
        *,
        reason: typing.Optional[str] = _("No reason provided."),
    ) -> None:
        """Unlock an existing locked ticket."""
        ticket: Ticket = await self.get_ticket(ctx.channel)
        if isinstance(ticket.channel, discord.TextChannel):
            raise commands.UserFeedbackCheckFailure(_("Cannot execute action on a text channel."))
        await ticket.unlock(ctx.author, reason=reason)

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
        locked=None,
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
        await ticket.rename(new_name, ctx.author, reason=reason)

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
        locked=None,
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
        config = await self.get_config(ticket.guild, ticket.profile)
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
                url=ctx.author.display_avatar,
                icon_url=ctx.author.display_avatar,
            )
            response = await self.cogsutils.ConfirmationAsk(ctx, embed=embed)
            if not response:
                return
        await ticket.delete(ctx.author, reason=reason)

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
        locked=None,
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
        if member is None:
            member = ctx.author
        await ticket.claim_ticket(member, ctx.author, reason=reason)

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
        locked=None,
    )
    @ticket.command(name="unclaim")
    async def command_unclaim(
        self, ctx: commands.Context, *, reason: typing.Optional[str] = _("No reason provided.")
    ) -> None:
        """Unclaim an existing ticket."""
        ticket: Ticket = await self.get_ticket(ctx.channel)
        await ticket.unclaim_ticket(ticket.claim, ctx.author, reason=reason)

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
        locked=None,
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
        if new_owner is None:
            new_owner = ctx.author
        await ticket.change_owner(new_owner, ctx.author, reason=reason)

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
        locked=None,
    )
    @ticket.command(name="addmember", aliases=["add"])
    async def command_addmember(
        self,
        ctx: commands.Context,
        members: commands.Greedy[discord.Member],
    ) -> None:
        """Add a member to an existing ticket."""
        ticket: Ticket = await self.get_ticket(ctx.channel)
        members = list(members)
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
        locked=None,
    )
    @ticket.command(name="removemember", aliases=["remove"])
    async def command_removemember(
        self,
        ctx: commands.Context,
        members: commands.Greedy[discord.Member],
    ) -> None:
        """Remove a member to an existing ticket."""
        ticket: Ticket = await self.get_ticket(ctx.channel)
        members = list(members)
        await ticket.remove_member(members, ctx.author)

    @commands.admin_or_permissions(administrator=True)
    @ticket.command(name="list")
    async def command_list(
        self,
        ctx: commands.Context,
        profile: ProfileConverter,
        status: typing.Optional[typing.Literal["open", "close", "all"]],
        member: typing.Optional[discord.Member],
    ) -> None:
        if status is None:
            status = "open"
        tickets = await self.config.guild(ctx.guild).tickets.all()
        tickets_to_show = []
        for channel_id in tickets:
            config = await self.get_config(ctx.guild, profile=profile)
            if config["forum_channel"] is not None:
                channel = config["forum_channel"].get_thread(int(channel_id))
            else:
                channel = ctx.guild.get_channel(int(channel_id))
            if channel is None:
                continue
            ticket: Ticket = await self.get_ticket(channel)
            if (
                ticket.profile == profile
                and (member is None or ticket.owner == member)
                and (status == "all" or ticket.status == status)
            ):
                tickets_to_show.append(ticket)
        if not tickets_to_show:
            raise commands.UserFeedbackCheckFailure(_("No tickets to show."))
        description = "\n".join(
            [
                f"• **{ticket.id}** - {ticket.status} - {ticket.channel.mention}"
                for ticket in sorted(tickets_to_show, key=lambda x: x.id)
            ]
        )
        pages = list(pagify(description, page_length=6000))
        embeds = []
        for page in pages:
            embed: discord.Embed = discord.Embed(title=f"Tickets in this guild - Profile {profile}")
            embed.description = page
            embeds.append(embed)
        await Menu(pages=embeds).start(ctx)

    async def on_button_interaction(self, interaction: discord.Interaction) -> None:
        permissions = interaction.channel.permissions_for(interaction.user)
        if not permissions.read_messages and not permissions.send_messages:
            return
        permissions = interaction.channel.permissions_for(interaction.guild.me)
        if not permissions.read_messages and not permissions.read_message_history:
            return
        if not interaction.response.is_done() and interaction.data["custom_id"] not in [
            "create_ticket_button",
            "close_ticket_button",
        ]:
            await interaction.response.defer(ephemeral=True)
        if interaction.data["custom_id"] == "create_ticket_button":
            buttons = await self.config.guild(interaction.guild).buttons.all()
            if f"{interaction.message.channel.id}-{interaction.message.id}" in buttons:
                profile = buttons[f"{interaction.message.channel.id}-{interaction.message.id}"][
                    "profile"
                ]
            else:
                profile = "main"
            modal = discord.ui.Modal(title="Create a Ticket", timeout=180, custom_id="create_ticket_modal")
            modal.on_submit = lambda interaction: interaction.response.defer(ephemeral=True)
            profile_input = discord.ui.TextInput(label="Profile", style=discord.TextStyle.short, default=profile, max_length=10, required=True)
            reason_input = discord.ui.TextInput(label="Why are you creating this ticket?", style=discord.TextStyle.long, max_length=1000, required=False, placeholder="No reason provided.")
            modal.add_item(profile_input)
            modal.add_item(reason_input)
            await interaction.response.send_modal(modal)
            timeout = await modal.wait()
            if timeout:
                return
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=True)
            profile = profile_input.value
            reason = reason_input.value or ""
            profiles = await self.config.guild(interaction.guild).profiles()
            if profile not in profiles:
                await interaction.followup.send(
                    _("The profile for which this button was configured no longer exists."),
                    ephemeral=True,
                )
                return
            ctx = await self.cogsutils.invoke_command(
                author=interaction.user,
                channel=interaction.channel,
                command=f"ticket create {profile}" + (f" {reason}" if reason != "" else ""),
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
        elif interaction.data["custom_id"] == "close_ticket_button":
            modal = discord.ui.Modal(title="Close the Ticket", timeout=180, custom_id="close_ticket_modal")
            modal.on_submit = lambda interaction: interaction.response.defer(ephemeral=True)
            reason_input = discord.ui.TextInput(label="Why are you closing this ticket?", style=discord.TextStyle.long, max_length=1000, required=False, placeholder="No reason provided.")
            modal.add_item(reason_input)
            await interaction.response.send_modal(modal)
            timeout = await modal.wait()
            if timeout:
                return
            reason = reason_input.value or ""
            ctx = await self.cogsutils.invoke_command(
                author=interaction.user,
                channel=interaction.channel,
                command=("ticket close" + (f" {reason}" if reason != "" else "")),
            )
            try:
                await interaction.followup.send(
                    _(
                        "You have chosen to close this ticket. If this is not done, you do not have the necessary permissions to execute this command."
                    ),
                    ephemeral=True,
                )
            except discord.HTTPException:
                pass
        elif interaction.data["custom_id"] == "open_ticket_button":
            ctx = await self.cogsutils.invoke_command(
                author=interaction.user, channel=interaction.channel, command="ticket open"
            )
            try:
                await interaction.followup.send(
                    _(
                        "You have chosen to re-open this ticket. If this is not done, you do not have the necessary permissions to execute this command."
                    ),
                    ephemeral=True,
                )
            except discord.HTTPException:
                pass
        elif interaction.data["custom_id"] == "claim_ticket_button":
            ctx = await self.cogsutils.invoke_command(
                author=interaction.user, channel=interaction.channel, command="ticket claim"
            )
            await interaction.followup.send(
                _(
                    "You have chosen to claim this ticket. If this is not done, you do not have the necessary permissions to execute this command."
                ),
                ephemeral=True,
            )
        elif interaction.data["custom_id"] == "delete_ticket_button":
            ctx = await self.cogsutils.invoke_command(
                author=interaction.user, channel=interaction.channel, command="ticket delete"
            )

    async def on_dropdown_interaction(self, interaction: discord.Interaction, select_menu: discord.ui.Select) -> None:
        options = select_menu.values
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
        profile = dropdowns[f"{interaction.message.channel.id}-{interaction.message.id}"][0].get(
            "profile", "main"
        )
        profiles = await self.config.guild(interaction.guild).profiles()
        if profile not in profiles:
            await interaction.followup.send(
                _("The profile for which this dropdown was configured no longer exists."),
                ephemeral=True,
            )
            return
        option = [option for option in select_menu.options if option.value == options[0]][0]
        reason = f"{option.emoji} - {option.label}"
        ctx = await self.cogsutils.invoke_command(
            author=interaction.user,
            channel=interaction.channel,
            command=f"ticket create {profile} {reason}",
        )
        if not await discord.utils.async_all(
            check(ctx) for check in ctx.command.checks
        ) or not hasattr(ctx, "ticket"):
            await interaction.followup.send(
                _("You are not allowed to execute this command."), ephemeral=True
            )
            return
        config = await self.get_config(interaction.guild, profile)
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

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
        if not payload.guild_id:
            return
        guild = self.bot.get_guild(payload.guild_id)
        channel = guild.get_channel(payload.channel_id)
        member = guild.get_member(payload.user_id)
        if member == guild.me or member.bot:
            return
        profile = "main"
        profiles = await self.config.guild(guild).profiles()
        if profile not in profiles:
            return
        config = await self.get_config(guild, profile)
        if config["enable"] and config["create_on_react"] and str(payload.emoji) == "🎟️":
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
        tickets = await self.config.guild(old_channel.guild).tickets.all()
        if str(old_channel.id) not in tickets:
            return
        try:
            del tickets[str(old_channel.id)]
        except KeyError:
            pass
        await self.config.guild(old_channel.guild).tickets.set(tickets)
        return

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member) -> None:
        tickets = await self.config.guild(member.guild).tickets.all()
        for channel_id in tickets:
            config = await self.get_config(member.guild, profile=tickets[channel_id]["profile"])
            if config["forum_channel"] is not None:
                channel = config["forum_channel"].get_thread(int(channel_id))
            else:
                channel = member.guild.get_channel(int(channel_id))
            if channel is None:
                continue
            ticket: Ticket = await self.get_ticket(channel)
            if config["close_on_leave"] and (
                getattr(ticket.owner, "id", ticket.owner) == member.id and ticket.status == "open"
            ):
                await ticket.close(ticket.guild.me)
        return

    def get_buttons(self, buttons: typing.List[dict]) -> discord.ui.View:
        view = discord.ui.View(timeout=None)
        for button in buttons:
            if "emoji" in button:
                try:
                    int(button["emoji"])
                except ValueError:
                    pass
                else:
                    button["emoji"] = str(self.bot.get_emoji(int(button["emoji"])))
            button = discord.ui.Button(**button)
            button.callback = self.on_button_interaction
            view.add_item(button)
        return view

    def get_dropdown(self, placeholder: str, options: typing.List[dict]) -> discord.ui.View:
        view = discord.ui.View(timeout=None)
        select_menu = discord.ui.Select(placeholder=placeholder, custom_id="create_ticket_dropdown")
        for option in options:
            if "emoji" in option:
                try:
                    int(option["emoji"])
                except ValueError:
                    pass
                else:
                    option["emoji"] = str(self.bot.get_emoji(int(option["emoji"])))
            option = discord.SelectOption(**option)
            select_menu.append_option(option)
        select_menu.callback = partial(self.on_dropdown_interaction, select_menu=select_menu)
        view.add_item(select_menu)
        return view

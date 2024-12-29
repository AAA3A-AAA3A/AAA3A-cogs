from AAA3A_utils import Cog, Loop, Menu, Settings, CogsUtils  # isort:skip
from redbot.core import commands, Config, modlog  # isort:skip
from redbot.core.bot import Red  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import asyncio
import datetime

from redbot.core.utils.chat_formatting import humanize_list, pagify

from .converters import (
    Emoji,
    ForumTagConverter,
    ModalConverter,
    MyMessageConverter,
    ProfileConverter,
)  # NOQA
from .dashboard_integration import DashboardIntegration
from .types import Ticket
from .views import ClosedTicketControls, CreateTicketView, OwnerCloseConfirmation, TicketView

# Credits:
# General repo credits.

_: Translator = Translator("Tickets", __file__)


class TicketConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> Ticket:
        cog = ctx.bot.get_cog("Tickets")
        try:
            arg = int(argument)
        except ValueError:
            ticket = None
        else:
            ticket = discord.utils.get(
                cog.tickets.get(ctx.guild.id, {}).values(), channel_id=arg
            ) or discord.utils.get(cog.tickets.get(ctx.guild.id, {}).values(), message_id=arg)
        if ticket is None:
            try:
                ticket = cog.tickets[ctx.guild.id][int(argument.removeprefix("#"))]
            except (ValueError, KeyError):
                raise commands.BadArgument(_("Event not found."))
        if (
            not ticket.channel.permissions_for(ctx.author).view_channel
            and ctx.author.id not in ctx.bot.owner_ids
        ):
            raise commands.UserFeedbackCheckFailure(
                _("You don't have permission to view the channel of this ticket.")
            )
        return ticket


@cog_i18n(_)
class Tickets(DashboardIntegration, Cog):
    """Configure and manage a tickets system for your server!"""

    def __init__(self, bot: Red) -> None:
        super().__init__(bot=bot)

        self.config: Config = Config.get_conf(
            self,
            identifier=205192943327321000143939875896557571750,
            force_registration=True,
        )
        guild_settings = dict(
            tickets={},
            last_id=0,
            profiles={},
            default_profile_settings={
                "enabled": False,
                "max_open_tickets_by_member": 5,
                "creating_modal": None,
                "channel_name": None,
                "welcome_message": "Welcome {owner_mention}! 👋",
                "custom_message": "Don't ping staff members, they will answer you as soon as possible.",
                "close_reopen_reason_modal": True,
                "create_modlog_case": False,
                "transcripts": True,
                "always_include_item_label": False,
                # Roles.
                "support_roles": [],
                "ping_roles": [],
                "view_roles": [],
                "whitelist_roles": [],
                "blacklist_roles": [],
                # Channels.
                "forum_channel": None,
                "forum_tags": [],
                "category_open": None,
                "category_closed": None,
                "logs_channel": None,
                # Checks.
                "owner_close_confirmation": True,
                "owner_can_close": True,
                "owner_can_reopen": True,
                "owner_can_add_members": False,
                "owner_can_remove_members": False,
                "close_on_leave": True,
                "auto_delete_on_close": None,
                # Emojis.
                "emojis": {
                    "close": "✖️",
                    "reopen": "👐",
                    "claim": "👥",
                    "unclaim": "👤",
                    "lock": "🔒",
                    "unlock": "🔓",
                    "transcript": "📜",
                    "delete": "🗑️",
                },
            },
            buttons_dropdowns={},
        )
        guild_settings["profiles"]["main"] = guild_settings["default_profile_settings"]
        self.config.register_guild(**guild_settings)
        self.config.register_member(
            tickets_number=0,
            closed_tickets_number=0,
        )

        self.tickets: typing.Dict[int, typing.Dict[int, Tickets]] = {}

        _settings: typing.Dict[str, typing.Dict[str, typing.Any]] = {
            "enabled": {
                "converter": bool,
                "description": "Whether the profile is enabled or not.",
            },
            "creating_modal": {
                "converter": ModalConverter,
                "description": "Whether a modal will be sent to the ticket owner when they create a ticket.\n\n**Example:**\n```\n[p]settickets creatingmodal <profile>\n- label: What is the problem?\n  style: 2 #  short = 1, paragraph = 2\n  required: True\n  default: None\n  placeholder: None\n  min_length: None\n  max_length: None\n```",
                "no_slash": True,
            },
            "max_open_tickets_by_member": {
                "converter": commands.Range[int, 1, 50],
                "description": "Maximum number of open tickets a member can have.",
            },
            "channel_name": {
                "converter": commands.Range[str, 1, 500],
                "description": "Name of the channel where the tickets will be created, reduced to 100 characters. You can use the following placeholders: `{emoji}`, `{owner_display_name}`, `{owner_name}`, `{owner_mention}`, `{owner_id}`, `{guild_name}` and `{guild_id}`.",
                "no_slash": True,
            },
            "welcome_message": {
                "converter": commands.Range[str, 1, 1000],
                "description": "Welcome message that will be sent when a ticket is created. You can use the following placeholders: `{owner_display_name}`, `{owner_name}`, `{owner_mention}`, `{owner_id}`, `{guild_name}` and `{guild_id}`.",
                "no_slash": True,
            },
            "custom_message": {
                "converter": commands.Range[str, 1, 3000],
                "description": "Custom message that will be sent when a ticket is created. You can use the following placeholders: `{owner_display_name}`, `{owner_name}`, `{owner_mention}`, `{owner_id}`, `{guild_name}` and `{guild_id}`.",
            },
            "close_reopen_reason_modal": {
                "converter": bool,
                "description": "Whether a modal will be sent to the ticket owner when they close or reopen a ticket for asking a reason.",
                "no_slash": True,
            },
            "create_modlog_case": {
                "converter": bool,
                "description": "Whether a modlog's case will be created when a ticket is created.",
                "no_slash": True,
            },
            "transcripts": {
                "converter": bool,
                "description": "Whether a transcript will be created when a ticket is deleted.",
                "no_slash": True,
            },
            "always_include_item_label": {
                "converter": bool,
                "description": "Whether the item label will always be included in the embeds.",
                "no_slash": True,
            },
            # Roles.
            "support_roles": {
                "converter": commands.Greedy[discord.Role],
                "description": "Roles that can support tickets.",
            },
            "ping_roles": {
                "converter": commands.Greedy[discord.Role],
                "description": "Roles that will be pinged when a ticket is created.",
            },
            "view_roles": {
                "converter": commands.Greedy[discord.Role],
                "description": "Roles that can view tickets.",
            },
            "whitelist_roles": {
                "converter": commands.Greedy[discord.Role],
                "description": "Roles that can create tickets.",
            },
            "blacklist_roles": {
                "converter": commands.Greedy[discord.Role],
                "description": "Roles that can't create tickets.",
            },
            "ticket_role": {
                "converter": discord.Role,
                "description": "Role that will be added to the ticket owner for the duration of the ticket.",
                "no_slash": True,
            },
            # Channels.
            "forum_channel": {
                "converter": typing.Union[discord.ForumChannel, discord.TextChannel],
                "description": "Forum/text channel where the tickets will be created as threads.",
            },
            "forum_tags": {
                "converter": commands.Greedy[ForumTagConverter],
                "description": "Tags that will be added to the threads in the forum channel.",
                "no_slash": True,
            },
            "category_open": {
                "converter": discord.CategoryChannel,
                "description": "Category where the open tickets will be created.",
            },
            "category_closed": {
                "converter": discord.CategoryChannel,
                "description": "Category where the closed tickets will be created.",
            },
            "logs_channel": {
                "converter": typing.Union[
                    discord.TextChannel, discord.VoiceChannel, discord.Thread
                ],
                "description": "Channel where the logs will be sent.",
            },
            # Checks.
            "owner_close_confirmation": {
                "converter": bool,
                "description": "Whether the ticket owner get a message to confirm the closing of the ticket.",
                "no_slash": True,
            },
            "owner_can_close": {
                "converter": bool,
                "description": "Whether the ticket owner can close the ticket.",
                "no_slash": True,
            },
            "owner_can_reopen": {
                "converter": bool,
                "description": "Whether the ticket owner can reopen the ticket.",
                "no_slash": True,
            },
            "owner_can_add_members": {
                "converter": bool,
                "description": "Whether the ticket owner can add members to the ticket.",
                "no_slash": True,
            },
            "owner_can_remove_members": {
                "converter": bool,
                "description": "Whether the ticket owner can remove members from the ticket.",
                "no_slash": True,
            },
            "close_on_leave": {
                "converter": bool,
                "description": "Whether the ticket will be closed when the owner leaves the server.",
                "no_slash": True,
            },
            "auto_delete_on_close": {
                "converter": commands.Range[int, 0, 30 * 24],
                "description": "Time in hours before the ticket is deleted after being closed. Set to 0 for an immediate deletion.",
                "no_slash": True,
            },
            # Emojis.
            "emoji_close": {
                "path": ["emojis", "close"],
                "converter": Emoji,
                "description": "Emoji of the `Close` buttons.",
                "no_slash": True,
            },
            "emoji_reopen": {
                "path": ["emojis", "reopen"],
                "converter": Emoji,
                "description": "Emoji of the `Reopen` buttons.",
                "no_slash": True,
            },
            "emoji_claim": {
                "path": ["emojis", "claim"],
                "converter": Emoji,
                "description": "Emoji of the `Claim` button.",
                "no_slash": True,
            },
            "emoji_unclaim": {
                "path": ["emojis", "unclaim"],
                "converter": Emoji,
                "description": "Emoji of the `Unclaim` button.",
                "no_slash": True,
            },
            "emoji_lock": {
                "path": ["emojis", "lock"],
                "converter": Emoji,
                "description": "Emoji of the `Lock` button.",
                "no_slash": True,
            },
            "emoji_unlock": {
                "path": ["emojis", "unlock"],
                "converter": Emoji,
                "description": "Emoji of the `Unlock` button.",
                "no_slash": True,
            },
            "emoji_transcript": {
                "path": ["emojis", "transcript"],
                "converter": Emoji,
                "description": "Emoji of the `Transcript` button.",
                "no_slash": True,
            },
            "emoji_delete": {
                "path": ["emojis", "delete"],
                "converter": Emoji,
                "description": "Emoji of the `Delete` button.",
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
            commands_group=self.settickets,
        )

    async def cog_load(self) -> None:
        await super().cog_load()
        await modlog.register_casetypes(
            [
                {
                    "name": "ticket_created",
                    "default_setting": True,
                    "image": "❓",
                    "case_str": "Ticket Created",
                },
                {
                    "name": "ticket_claimed",
                    "default_setting": True,
                    "image": "👥",
                    "case_str": "Ticket Claimed",
                },
                {
                    "name": "ticket_unclaimed",
                    "default_setting": True,
                    "image": "👤",
                    "case_str": "Ticket Unclaimed",
                },
                {
                    "name": "ticket_closed",
                    "default_setting": True,
                    "image": "❌",
                    "case_str": "Ticket Closed",
                },
                {
                    "name": "ticket_reopened",
                    "default_setting": True,
                    "image": "👐",
                    "case_str": "Ticket Reopened",
                },
                {
                    "name": "ticket_locked",
                    "default_setting": True,
                    "image": "🔒",
                    "case_str": "Ticket Locked",
                },
                {
                    "name": "ticket_unlocked",
                    "default_setting": True,
                    "image": "🔓",
                    "case_str": "Ticket Unlocked",
                },
                {
                    "name": "ticket_member_added",
                    "default_setting": True,
                    "image": "➕",
                    "case_str": "Member Added to Ticket",
                },
                {
                    "name": "ticket_member_removed",
                    "default_setting": True,
                    "image": "➖",
                    "case_str": "Member Removed from Ticket",
                },
            ]
        )
        await self.settings.add_commands()
        asyncio.create_task(self.load_tickets())

    async def cog_unload(self) -> None:
        await super().cog_unload()

    async def load_tickets(self) -> None:
        await self.bot.wait_until_red_ready()
        for guild_id, guild_data in (await self.config.all_guilds()).items():
            for ticket_id, ticket_data in guild_data["tickets"].items():
                ticket = Ticket(bot=self.bot, cog=self, **ticket_data)
                self.tickets.setdefault(guild_id, {})[int(ticket_id)] = ticket
                view: TicketView = TicketView(cog=self, ticket=ticket)
                view._message = ticket.message
                await view._update()
                self.bot.add_view(view, message_id=f"{ticket.channel_id}-{ticket.message_id}")
                self.views[ticket.message] = view
            for message, components in guild_data["buttons_dropdowns"].items():
                channel = self.bot.get_channel(int((str(message).split("-"))[0]))
                if channel is None:
                    continue
                message_id = int((str(message).split("-"))[1])
                view: CreateTicketView = CreateTicketView(cog=self, components=components)
                self.bot.add_view(view, message_id=message_id)
                self.views[discord.PartialMessage(channel=channel, id=message_id)] = view
        view: OwnerCloseConfirmation = OwnerCloseConfirmation(cog=self)
        self.bot.add_view(view)
        self.views["OwnerCloseConfirmation"] = view
        view: ClosedTicketControls = ClosedTicketControls(cog=self)
        self.bot.add_view(view)
        self.views["ClosedTicketControls"] = view
        self.loops.append(
            Loop(
                cog=self,
                name="Check Tickets",
                function=self.check_tickets,
                minutes=1,
            )
        )

    async def check_tickets(self) -> None:
        for guild_id, tickets in self.tickets.copy().items():
            profiles = await self.config.guild_from_id(guild_id).profiles()
            for ticket_id, ticket in tickets.copy().items():
                if ticket.guild is None:
                    try:
                        await self.bot.fetch_guild(guild_id)
                    except discord.NotFound:
                        await ticket.delete()
                    continue
                if ticket.channel is None:
                    try:
                        await ticket.guild.fetch_channel(ticket.channel_id)
                    except discord.NotFound:
                        await ticket.delete()
                    continue
                if ticket.profile not in profiles:
                    await ticket.delete()
                    continue
                config = profiles[ticket.profile]
                if ticket.owner is None:
                    try:
                        await ticket.guild.fetch_member(ticket.host_id)
                    except discord.NotFound:
                        if config["close_on_leave"]:
                            await ticket.close()
                    continue
                if (
                    ticket.is_closed
                    and config["auto_delete_on_close"] is not None
                    and datetime.datetime.now(tz=datetime.timezone.utc) - ticket.closed_at
                    > datetime.timedelta(hours=config["auto_delete_on_close"])
                ):
                    await ticket.delete_action()

    def is_support(ignore_owner=False):
        async def predicate(ctx: typing.Union[commands.Context, discord.Interaction]) -> bool:
            bot = ctx.client if isinstance(ctx, discord.Interaction) else ctx.bot
            author = ctx.user if isinstance(ctx, discord.Interaction) else ctx.author
            if (
                not ctx.channel.permissions_for(author).view_channel
                or not ctx.channel.permissions_for(ctx.guild.me).send_messages
            ) and author.id not in bot.owner_ids:
                return False
            cog = bot.get_cog("Tickets")
            if (
                ticket := (ctx.data if isinstance(ctx, discord.Interaction) else ctx.kwargs).get(
                    "ticket"
                )
            ) is not None:
                profile = ticket.profile
            elif (
                ticket := discord.utils.get(
                    cog.tickets.get(ctx.guild.id, {}).values(), channel=ctx.channel
                )
            ) is not None:
                profile = ticket.profile
            else:
                profile = "main"
            return (
                (ticket is not None and ticket.owner == author and not ignore_owner)
                or await bot.is_admin(author)
                or author.guild_permissions.manage_guild
                or any(
                    author.get_role(role_id) is not None
                    for role_id in await cog.config.guild(ctx.guild).profiles.get_raw(
                        profile, "support_roles", default=[]
                    )
                )
            )

        return commands.check(predicate)

    def is_support_any_profile():
        async def predicate(ctx: typing.Union[commands.Context, discord.Interaction]) -> bool:
            bot = ctx.client if isinstance(ctx, discord.Interaction) else ctx.bot
            author = ctx.user if isinstance(ctx, discord.Interaction) else ctx.author
            cog = bot.get_cog("Tickets")
            return await cog.is_support.__func__().predicate(ctx) or any(
                author.get_role(role_id) is not None
                for data in (await cog.config.guild(ctx.guild).profiles()).values()
                for role_id in data["support_roles"]
            )

        return commands.check(predicate)

    async def send_ticket_log(self, ticket: Ticket) -> None:
        if (
            (guild := ticket.guild) is not None
            and (
                logs_channel_id := await self.config.guild(guild).profiles.get_raw(
                    ticket.profile, "logs_channel", default=None
                )
            )
            is not None
            and (logs_channel := guild.get_channel_or_thread(logs_channel_id)) is not None
        ):
            try:
                view: discord.ui.View = discord.ui.View()
                view.add_item(
                    discord.ui.Button(
                        label=_("Jump to Ticket"),
                        style=discord.ButtonStyle.link,
                        url=ticket.message.jump_url,
                    )
                )
                await logs_channel.send(
                    embed=await ticket.get_embed(for_logging=True),
                    view=view,
                )
            except discord.HTTPException as e:
                self.logger.error(
                    f"Error when sending event creation log for the event #{ticket.id} in the guild `{ticket.channel.name}` ({ticket.channel.id}) in the channel `{ticket.guild.name}` ({ticket.guild.id}).",
                    exc_info=e,
                )

    async def create_ticket(
        self,
        ctx_interaction: typing.Union[commands.Context, discord.Interaction],
        profile: str,
        owner: discord.Member,
        reason: typing.Optional[str] = None,
        **kwargs,
    ) -> None:
        guild = ctx_interaction.guild

        creating_modal = await self.config.guild(guild).profiles.get_raw(profile, "creating_modal")
        if (
            creating_modal is None
            and reason is None
            and isinstance(ctx_interaction, discord.Interaction)
        ):
            final_modal = [
                {
                    "label": "Reason:",
                    "style": discord.TextStyle.paragraph.value,
                    "required": True,
                    "default": None,
                    "placeholder": "Enter the reason for creating the ticket...",
                    "min_length": 1,
                    "max_length": 1000,
                },
            ]
        else:
            final_modal = creating_modal
        owner_answers = {}
        if final_modal is not None:
            modal: discord.ui.Modal = discord.ui.Modal(
                title=_("Create a Ticket"),
            )
            modal.on_submit = lambda interaction: interaction.response.defer()
            text_inputs = []
            for text_input_kwargs in final_modal:
                if not text_input_kwargs["label"].endswith((":", "?")):
                    text_input_kwargs["label"] += ":"
                text_input_kwargs["style"] = discord.TextStyle(text_input_kwargs["style"])
                text_input: discord.ui.TextInput = discord.ui.TextInput(**text_input_kwargs)
                modal.add_item(text_input)
                text_inputs.append(text_input)
            if isinstance(ctx_interaction, discord.Interaction):
                await ctx_interaction.response.send_modal(modal)
            else:
                view: discord.ui.View = discord.ui.View(timeout=180)

                async def interaction_check(interaction: discord.Interaction):
                    if interaction.user != owner and interaction.user != (
                        ctx_interaction.user
                        if isinstance(ctx_interaction, discord.Interaction)
                        else ctx_interaction.author
                    ):
                        await interaction.response.send_message(
                            _("Only the ticket owner can fill the answers."),
                            ephemeral=True,
                        )
                        return False
                    return True

                view.interaction_check = interaction_check

                async def on_timeout():
                    try:
                        await view._message.delete()
                    except discord.HTTPException:
                        pass

                view.on_timeout = on_timeout
                button: discord.ui.Button = discord.ui.Button(
                    emoji="❓",
                    label=_("Fill Answers"),
                )

                async def callback(interaction: discord.Interaction):
                    await view.on_timeout()
                    view.stop()
                    await interaction.response.send_modal(modal)

                button.callback = callback
                view.add_item(button)
                view._message = await ctx_interaction.reply(view=view)
                timeout = await view.wait()
                if timeout:
                    return
            timeout = await modal.wait()
            if timeout:
                return
            if creating_modal is None:
                reason = text_inputs[0].value.strip() or None
            else:
                owner_answers = {
                    text_input.label: text_input.value.strip()
                    for text_input in text_inputs
                    if text_input.value.strip()
                }
        elif isinstance(ctx_interaction, discord.Interaction):
            await ctx_interaction.response.defer(ephermal=True, thinking=True)

        id = await self.config.guild(guild).last_id() + 1
        ticket: Ticket = Ticket(
            bot=self.bot,
            cog=self,
            guild_id=guild.id,
            id=id,
            owner_id=owner.id,
            profile=profile,
            **kwargs,
            reason=reason,
            owner_answers=owner_answers,
        )
        try:
            await ticket.create()
        except RuntimeError as e:
            raise commands.UserFeedbackCheckFailure(str(e))
        await self.config.guild(guild).last_id.set(id)

        if isinstance(ctx_interaction, discord.Interaction):
            await ctx_interaction.followup.send(
                _(
                    "❓ Your ticket has been created! Please wait for a staff member to assist you in {channel.mention}."
                ).format(channel=ticket.channel),
                ephemeral=True,
            )

    @commands.guild_only()
    @commands.hybrid_group(aliases=["tickets"])
    async def ticket(self, ctx: commands.Context) -> None:
        """Create, manage and list tickets."""
        pass

    @ticket.command(aliases=["+"])
    async def create(
        self,
        ctx: commands.Context,
        profile: typing.Optional[ProfileConverter] = "main",
        *,
        reason: commands.Range[str, 1, 1000] = None,
    ) -> None:
        """Create a ticket."""
        await self.create_ticket(ctx, profile, ctx.author, reason=reason)

    @commands.admin_or_permissions(manage_guild=True)
    @ticket.command()
    async def createfor(
        self,
        ctx: commands.Context,
        owner: discord.Member,
        profile: typing.Optional[ProfileConverter] = "main",
        *,
        reason: commands.Range[str, 1, 1000] = None,
    ) -> None:
        """Create a ticket for a member."""
        await self.create_ticket(ctx, profile, owner, reason=reason)

    @commands.bot_has_permissions(embed_links=True)
    @is_support(ignore_owner=True)
    @ticket.command()
    async def settings(self, ctx: commands.Context, profile: str = None) -> None:
        """Show Tickets settings."""
        profiles = await self.config.guild(ctx.guild).profiles()
        if profile is None:
            embed: discord.Embed = discord.Embed(
                title=_("Tickets — Settings — Profiles"),
                description="\n".join([f"**•** `{profile}`" for profile in profiles]),
                color=await ctx.embed_color(),
            )
            await ctx.send(embed=embed)
            return
        if profile not in profiles:
            raise commands.UserFeedbackCheckFailure(_("This profile doesn't exist."))
        config = profiles[profile]
        embeds = [
            discord.Embed(
                title=_("Tickets — Settings — Profile `{profile}`").format(profile=profile),
                color=await ctx.embed_color(),
            ),
        ]
        forum_channel = (
            ctx.guild.get_channel_or_thread(config.get("forum_channel"))
            if config.get("forum_channel")
            else None
        )
        embeds.append(
            discord.Embed(
                title=_("Settings:"),
                description=_(
                    "**•** Enabled: {enabled}\n"
                    "**•** Max Open Tickets By Member: {max_open_tickets_by_member}\n"
                    "**•** Creating Modal: {creating_modal}\n"
                    "**•** Channel Name: {channel_name}\n"
                    "**•** Welcome Message: {welcome_message}\n"
                    "**•** Custom Message: {custom_message}\n"
                    "**•** Close/Reopen Reason Modal: {close_reopen_reason_modal}\n"
                    "**•** Create Modlog Case: {create_modlog_case}\n"
                    "**•** Transcripts: {transcripts}\n"
                    "**•** Always Include Item Label: {always_include_item_label}\n\n"
                    "**•** Support Roles: {support_roles}\n"
                    "**•** Ping Roles: {ping_roles}\n"
                    "**•** View Roles: {view_roles}\n"
                    "**•** Whitelist Roles: {whitelist_roles}\n"
                    "**•** Blacklist Roles: {blacklist_roles}\n\n"
                    "**•** Forum Channel: {forum_channel}\n"
                    "**•** Forum Tags: {forum_tags}\n"
                    "**•** Category Open: {category_open}\n"
                    "**•** Category Closed: {category_closed}\n"
                    "**•** Logs Channel: {logs_channel}\n\n"
                    "**•** Owner Close Confirmation: {owner_close_confirmation}\n"
                    "**•** Owner Can Close: {owner_can_close}\n"
                    "**•** Owner Can Reopen: {owner_can_reopen}\n"
                    "**•** Owner Can Add Members: {owner_can_add_members}\n"
                    "**•** Owner Can Remove Members: {owner_can_remove_members}\n"
                    "**•** Close On Leave: {close_on_leave}\n"
                    "**•** Auto Delete On Close: {auto_delete_on_close}\n\n"
                    "**•** Emoji Claim: {emoji_claim}\n"
                    "**•** Emoji Unclaim: {emoji_unclaim}\n"
                    "**•** Emoji Close: {emoji_close}\n"
                    "**•** Emoji Reopen: {emoji_reopen}\n"
                    "**•** Emoji Lock: {emoji_lock}\n"
                    "**•** Emoji Unlock: {emoji_unlock}\n"
                    "**•** Emoji Transcript: {emoji_transcript}\n"
                    "**•** Emoji Delete: {emoji_delete}"
                ).format(
                    enabled=config["enabled"],
                    max_open_tickets_by_member=config["max_open_tickets_by_member"],
                    creating_modal=_("Set.") if config["creating_modal"] is not None else "...",
                    channel_name=config["channel_name"] or "...",
                    welcome_message=config.get("welcome_message") or "...",
                    custom_message=config["custom_message"] or "...",
                    close_reopen_reason_modal=config["close_reopen_reason_modal"],
                    create_modlog_case=config["create_modlog_case"],
                    transcripts=config["transcripts"],
                    always_include_item_label=config["always_include_item_label"],
                    support_roles=humanize_list(
                        [
                            role.mention
                            for role_id in config["support_roles"]
                            if (role := ctx.guild.get_role(role_id)) is not None
                        ]
                    )
                    or "...",
                    ping_roles=humanize_list(
                        [
                            role.mention
                            for role_id in config["ping_roles"]
                            if (role := ctx.guild.get_role(role_id)) is not None
                        ]
                    )
                    or "...",
                    view_roles=humanize_list(
                        [
                            role.mention
                            for role_id in config["view_roles"]
                            if (role := ctx.guild.get_role(role_id)) is not None
                        ]
                    )
                    or "...",
                    whitelist_roles=humanize_list(
                        [
                            role.mention
                            for role_id in config["whitelist_roles"]
                            if (role := ctx.guild.get_role(role_id)) is not None
                        ]
                    )
                    or "...",
                    blacklist_roles=humanize_list(
                        [
                            role.mention
                            for role_id in config["blacklist_roles"]
                            if (role := ctx.guild.get_role(role_id)) is not None
                        ]
                    )
                    or "...",
                    forum_channel=forum_channel.mention if forum_channel is not None else "...",
                    forum_tags=(
                        (
                            humanize_list(
                                [
                                    f"`{f'{tag.emoji} ' if tag.emoji is not None else ''}{tag.name}`"
                                    for tag_id in config["forum_tags"]
                                    if (tag := forum_channel.get_tag(tag_id)) is not None
                                ]
                            )
                            or "..."
                        )
                        if forum_channel is not None
                        else "..."
                    ),
                    category_open=(
                        category.mention
                        if (category := ctx.guild.get_channel(config["category_open"])) is not None
                        else "..."
                    ),
                    category_closed=(
                        category.mention
                        if (category := ctx.guild.get_channel(config["category_closed"]))
                        is not None
                        else "..."
                    ),
                    logs_channel=(
                        channel.mention
                        if (channel := ctx.guild.get_channel_or_thread(config["logs_channel"]))
                        is not None
                        else "..."
                    ),
                    owner_close_confirmation=config["owner_close_confirmation"],
                    owner_can_close=config["owner_can_close"],
                    owner_can_reopen=config["owner_can_reopen"],
                    owner_can_add_members=config["owner_can_add_members"],
                    owner_can_remove_members=config["owner_can_remove_members"],
                    close_on_leave=config["close_on_leave"],
                    auto_delete_on_close=config["auto_delete_on_close"],
                    emoji_claim=config["emojis"]["claim"],
                    emoji_unclaim=config["emojis"]["unclaim"],
                    emoji_close=config["emojis"]["close"],
                    emoji_reopen=config["emojis"]["reopen"],
                    emoji_lock=config["emojis"]["lock"],
                    emoji_unlock=config["emojis"]["unlock"],
                    emoji_transcript=config["emojis"]["transcript"],
                    emoji_delete=config["emojis"]["delete"],
                ),
                color=await ctx.embed_color(),
            ),
        )
        await Menu(pages=[{"embeds": embeds}]).start(ctx)

    @is_support_any_profile()
    @ticket.command(aliases=["infos"])
    async def show(
        self, ctx: commands.Context, ticket: typing.Optional[TicketConverter] = None
    ) -> None:
        """Show a ticket."""
        if (
            ticket is None
            and (
                ticket := discord.utils.get(
                    self.tickets.get(ctx.guild.id, {}).values(), channel=ctx.channel
                )
            )
            is None
        ):
            raise commands.UserFeedbackCheckFailure(_("No ticket found."))
        await ctx.send(embed=await ticket.get_embed(for_logging=True))

    @is_support_any_profile()
    @ticket.command()
    async def list(
        self,
        ctx: commands.Context,
        short: bool = False,
        claimed: bool = False,
        status: typing.Literal["all", "open", "claimed", "unclaimed", "closed"] = "open",
        *,
        owner: typing.Optional[discord.Member] = None,
    ) -> None:
        """List tickets."""
        if not (tickets := self.tickets.get(ctx.guild.id)):
            raise commands.UserFeedbackCheckFailure(_("No ticket found."))
        tickets_to_display = []
        for ticket in tickets.values():
            if (
                not ticket.channel.permissions_for(ctx.author).view_channel
                and ctx.author.id not in ctx.bot.owner_ids
            ):
                continue
            if owner is not None and ticket.owner != owner:
                continue
            if claimed and (
                ticket.is_closed or not ticket.is_claimed or ctx.author != ticket.claimed_by
            ):
                continue
            if status == "open" and ticket.is_closed:
                continue
            elif status == "claimed" and (ticket.is_closed or not ticket.is_claimed):
                continue
            elif status == "unclaimed" and (ticket.is_closed or ticket.is_claimed):
                continue
            elif status == "closed" and not ticket.is_closed:
                continue
            tickets_to_display.append(ticket)
        if not short:
            embeds = [await ticket.get_embed(for_logging=True) for ticket in tickets_to_display]
        else:
            embed: discord.Embed = discord.Embed(
                title=_("{len_tickets} Ticket{s}").format(
                    len_tickets=len(tickets_to_display),
                    s="s" if len(tickets_to_display) > 1 else "",
                ),
                color=await ctx.embed_color(),
                timestamp=ctx.message.created_at,
            )
            embed.set_footer(text=ctx.guild.name, icon_url=ctx.guild.icon)
            BREAK_LINE = "\n"
            description = "\n".join(
                [
                    f"• **#{ticket.id}** **{'CLOSED' if ticket.is_closed else ('CLAIMED' if ticket.is_claimed else 'OPEN')}** - {ticket.owner.mention if ticket.owner is not None else '[Unknown]'} - {ticket.channel.mention} - {ticket.reason.split(BREAK_LINE)[0][:30]}"
                    for ticket in tickets_to_display
                ]
            )
            pages = list(pagify(description, page_length=6000))
            embeds = []
            for page in pages:
                e = embed.copy()
                e.description = page
                embeds.append(e)
        await Menu(pages=embeds, page_start=-1).start(ctx)

    @is_support()
    @ticket.command()
    async def close(
        self, ctx: commands.Context, ticket: typing.Optional[TicketConverter] = None
    ) -> None:
        """Close a ticket."""
        if (
            ticket is None
            and (
                ticket := discord.utils.get(
                    self.tickets.get(ctx.guild.id, {}).values(), channel=ctx.channel
                )
            )
            is None
        ):
            raise commands.UserFeedbackCheckFailure(_("No ticket found."))
        try:
            await ticket.close(ctx.author)
        except RuntimeError as e:
            raise commands.UserFeedbackCheckFailure(str(e))

    @is_support()
    @ticket.command(aliases=["open"])
    async def reopen(
        self, ctx: commands.Context, ticket: typing.Optional[TicketConverter] = None
    ) -> None:
        """Reopen a ticket."""
        if (
            ticket is None
            and (
                ticket := discord.utils.get(
                    self.tickets.get(ctx.guild.id, {}).values(), channel=ctx.channel
                )
            )
            is None
        ):
            raise commands.UserFeedbackCheckFailure(_("No ticket found."))
        try:
            await ticket.reopen(ctx.author)
        except RuntimeError as e:
            raise commands.UserFeedbackCheckFailure(str(e))

    @is_support(ignore_owner=True)
    @ticket.command()
    async def claim(
        self, ctx: commands.Context, ticket: typing.Optional[TicketConverter] = None
    ) -> None:
        """Claim a ticket."""
        if (
            ticket is None
            and (
                ticket := discord.utils.get(
                    self.tickets.get(ctx.guild.id, {}).values(), channel=ctx.channel
                )
            )
            is None
        ):
            raise commands.UserFeedbackCheckFailure(_("No ticket found."))
        try:
            await ticket.claim(ctx.author)
        except RuntimeError as e:
            raise commands.UserFeedbackCheckFailure(str(e))

    @is_support(ignore_owner=True)
    @ticket.command()
    async def unclaim(
        self, ctx: commands.Context, ticket: typing.Optional[TicketConverter] = None
    ) -> None:
        """Unclaim a ticket."""
        if (
            ticket is None
            and (
                ticket := discord.utils.get(
                    self.tickets.get(ctx.guild.id, {}).values(), channel=ctx.channel
                )
            )
            is None
        ):
            raise commands.UserFeedbackCheckFailure(_("No ticket found."))
        try:
            await ticket.unclaim()
        except RuntimeError as e:
            raise commands.UserFeedbackCheckFailure(str(e))

    @is_support(ignore_owner=True)
    async def lock(
        self, ctx: commands.Context, ticket: typing.Optional[TicketConverter] = None
    ) -> None:
        """Lock a ticket."""
        if (
            ticket is None
            and (
                ticket := discord.utils.get(
                    self.tickets.get(ctx.guild.id, {}).values(), channel=ctx.channel
                )
            )
            is None
        ):
            raise commands.UserFeedbackCheckFailure(_("No ticket found."))
        try:
            await ticket.lock(ctx.author)
        except RuntimeError as e:
            raise commands.UserFeedbackCheckFailure(str(e))

    @is_support(ignore_owner=True)
    @ticket.command()
    async def unlock(
        self, ctx: commands.Context, ticket: typing.Optional[TicketConverter] = None
    ) -> None:
        """Unlock a ticket."""
        if (
            ticket is None
            and (
                ticket := discord.utils.get(
                    self.tickets.get(ctx.guild.id, {}).values(), channel=ctx.channel
                )
            )
            is None
        ):
            raise commands.UserFeedbackCheckFailure(_("No ticket found."))
        try:
            await ticket.unlock(ctx.author)
        except RuntimeError as e:
            raise commands.UserFeedbackCheckFailure(str(e))

    @is_support()
    @ticket.command(aliases=["add"])
    async def addmember(
        self,
        ctx: commands.Context,
        ticket: typing.Optional[TicketConverter] = None,
        *,
        member: discord.Member,
    ) -> None:
        """Add a member to a ticket."""
        if (
            ticket is None
            and (
                ticket := discord.utils.get(
                    self.tickets.get(ctx.guild.id, {}).values(), channel=ctx.channel
                )
            )
            is None
        ):
            raise commands.UserFeedbackCheckFailure(_("No ticket found."))
        try:
            await ticket.add_member(member, ctx.author)
        except RuntimeError as e:
            raise commands.UserFeedbackCheckFailure(str(e))

    @is_support()
    @ticket.command(aliases=["remove"])
    async def removemember(
        self,
        ctx: commands.Context,
        ticket: typing.Optional[TicketConverter] = None,
        *,
        member: discord.Member,
    ) -> None:
        """Remove a member from a ticket."""
        if (
            ticket is None
            and (
                ticket := discord.utils.get(
                    self.tickets.get(ctx.guild.id, {}).values(), channel=ctx.channel
                )
            )
            is None
        ):
            raise commands.UserFeedbackCheckFailure(_("No ticket found."))
        try:
            await ticket.remove_member(member, ctx.author)
        except RuntimeError as e:
            raise commands.UserFeedbackCheckFailure(str(e))

    @is_support(ignore_owner=True)
    @ticket.command()
    async def export(
        self, ctx: commands.Context, ticket: typing.Optional[TicketConverter] = None
    ) -> None:
        """Export a ticket."""
        if (
            ticket is None
            and (
                ticket := discord.utils.get(
                    self.tickets.get(ctx.guild.id, {}).values(), channel=ctx.channel
                )
            )
            is None
        ):
            raise commands.UserFeedbackCheckFailure(_("No ticket found."))
        transcript = await ticket.export()
        message = await ctx.send(
            _("📜 Here is the transcript of this ticket!"),
            file=transcript,
        )
        view: discord.ui.View = discord.ui.View()
        view.add_item(
            discord.ui.Button(
                label=_("View Transcript"),
                style=discord.ButtonStyle.link,
                url=f"https://mahto.id/chat-exporter?url={message.attachments[0].url}",
            )
        )
        await message.edit(view=view)

    @is_support(ignore_owner=True)
    async def delete(
        self, ctx: commands.Context, ticket: typing.Optional[TicketConverter] = None
    ) -> None:
        """Delete a ticket."""
        if (
            ticket is None
            and (
                ticket := discord.utils.get(
                    self.tickets.get(ctx.guild.id, {}).values(), channel=ctx.channel
                )
            )
            is None
        ):
            raise commands.UserFeedbackCheckFailure(_("No ticket found."))
        await ticket.delete_channel(ctx.author)

    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    @commands.hybrid_group()
    async def settickets(self, ctx: commands.Context) -> None:
        """Commands to configure Tickets."""
        pass

    @commands.bot_has_permissions(embed_links=True)
    @settickets.command()
    async def setup(self, ctx: commands.Context) -> None:
        """Help to setup Tickets."""
        embeds = []
        embeds.append(
            discord.Embed(
                title=_("Getting Started (Required Steps):"),
                description=_(
                    "**1.** Enable the profile system with `{ctx.prefix}settickets enabled <profile> True`.\n"
                    "**2.** Set the support roles with `{ctx.prefix}settickets supportroles <profile> <roles...>`.\n"
                    "**3.** Set the forum channel/text channel with `{ctx.prefix}settickets forumchannel <profile> <channel>`.\n"
                    "   **Or** set the open and closed (optional) categories with `{ctx.prefix}settickets categoryopen <profile> <category>` and `{ctx.prefix}settickets categoryclosed <profile> <category>`.\n"
                    "**4.** Eventually, set the ping roles with `{ctx.prefix}settickets pingroles <profile> <roles...>`.\n"
                    "**5.** Eventually, set the logs channel with `{ctx.prefix}settickets logschannel <profile> <channel>`.\n"
                    "**6.** Eventually, set the whitelist or blacklist roles with `{ctx.prefix}settickets whitelistroles <profile> <roles...>` and `{ctx.prefix}settickets blacklistroles <profile> <roles...>`.\n"
                    "**7.** Eventually, set the forum tags with `{ctx.prefix}settickets forumtags <profile> <tags...>`.\n"
                    "**8.** Eventually, set the custom message with `{ctx.prefix}settickets custommessage <profile> <message>`.\n"
                    "**9.** Eventually, set a creating modal with `{ctx.prefix}settickets creatingmodal <profile> <modal>`."
                ).format(ctx=ctx),
                color=await ctx.embed_color(),
            )
        )
        embeds.append(
            discord.Embed(
                title=_(
                    "Look at all the different settings with `{ctx.prefix}tickets settings`."
                ).format(ctx=ctx),
                color=await ctx.embed_color(),
            )
        )
        embeds.append(
            discord.Embed(
                title=_("Buttons & Dropdowns:"),
                description=_(
                    "You can add buttons and dropdowns to messages to create tickets.\n"
                    "- Use `{ctx.clean_prefix}tickets addbutton <message> [profile=main] [emoji] [style=secondary] <label>` to add a button to a message.\n"
                    "- Use `{ctx.clean_prefix}tickets adddropdownoption <message> [profile=main] [emoji] <label> [description]` to add an option to a dropdown.\n"
                    "- Use `{ctx.clean_prefix}tickets clearmessage <message>` to remove them."
                ).format(ctx=ctx),
                color=await ctx.embed_color(),
            )
        )
        await Menu(pages=[{"embeds": embeds}]).start(ctx)

    @settickets.command()
    async def addbutton(
        self,
        ctx: commands.Context,
        message: MyMessageConverter,
        profile: typing.Optional[ProfileConverter],
        emoji: typing.Optional[Emoji],
        style: typing.Optional[typing.Literal["1", "2", "3", "4"]] = "2",
        *,
        label: typing.Optional[commands.Range[str, 1, 100]] = None,
    ) -> None:
        """Add a button to a message.

        (Use the number for the color.)
        • `primary`: 1
        • `secondary`: 2
        • `success`: 3
        • `danger`: 4
        # Aliases
        • `blurple`: 1
        • `grey`: 2
        • `gray`: 2
        • `green`: 3
        • `red`: 4
        """
        profile = profile or "main"
        if emoji is None and label is None:
            raise commands.UserFeedbackCheckFailure(
                _("You have to specify at least an emoji or a label.")
            )
        buttons_dropdowns = await self.config.guild(ctx.guild).buttons_dropdowns()
        if f"{message.channel.id}-{message.id}" not in buttons_dropdowns:
            if message.components:
                raise commands.UserFeedbackCheckFailure(_("This message already has components."))
            components = buttons_dropdowns[f"{message.channel.id}-{message.id}"] = {
                "buttons": {},
                "dropdown_options": {},
            }
        else:
            components = buttons_dropdowns[f"{message.channel.id}-{message.id}"]
        if len(components["buttons"]) >= 20:
            raise commands.UserFeedbackCheckFailure(
                _("You can't add more than 20 buttons for one message.")
            )
        config_identifier = CogsUtils.generate_key(length=5, existing_keys=components["buttons"])
        components["buttons"][config_identifier] = {
            "emoji": f"{getattr(emoji, 'id', emoji)}" if emoji is not None else None,
            "label": label,
            "style": int(style),
            "profile": profile,
        }
        if message in self.views:
            self.views.pop(message).stop()
        view: CreateTicketView = CreateTicketView(
            cog=self,
            components=components,
        )
        message = await message.edit(view=view)
        self.views[message] = view
        await self.config.guild(ctx.guild).buttons_dropdowns.set(buttons_dropdowns)

    @settickets.command()
    async def adddropdownoption(
        self,
        ctx: commands.Context,
        message: MyMessageConverter,
        profile: typing.Optional[ProfileConverter],
        emoji: typing.Optional[Emoji],
        label: commands.Range[str, 1, 100],
        description: commands.Range[str, 1, 100] = None,
    ) -> None:
        """Add an option to the dropdown of a message."""
        profile = profile or "main"
        buttons_dropdowns = await self.config.guild(ctx.guild).buttons_dropdowns()
        if f"{message.channel.id}-{message.id}" not in buttons_dropdowns:
            if message.components:
                raise commands.UserFeedbackCheckFailure(_("This message already has components."))
            components = buttons_dropdowns[f"{message.channel.id}-{message.id}"] = {
                "buttons": {},
                "dropdown_options": {},
            }
        else:
            components = buttons_dropdowns[f"{message.channel.id}-{message.id}"]
        if len(components["dropdown_options"]) >= 25:
            raise commands.UserFeedbackCheckFailure(
                _("I can't add more than 25 options for one dropdown.")
            )
        config_identifier = CogsUtils.generate_key(
            length=5, existing_keys=components["dropdown_options"]
        )
        components["dropdown_options"][config_identifier] = {
            "emoji": f"{getattr(emoji, 'id', emoji)}" if emoji is not None else None,
            "label": label,
            "description": description,
            "profile": profile,
        }
        if message in self.views:
            self.views.pop(message).stop()
        view: CreateTicketView = CreateTicketView(
            cog=self,
            components=components,
        )
        message = await message.edit(view=view)
        self.views[message] = view
        await self.config.guild(ctx.guild).buttons_dropdowns.set(buttons_dropdowns)

    @settickets.command()
    async def clearmessage(self, ctx: commands.Context, message: MyMessageConverter) -> None:
        """Clear the components of a message."""
        buttons_dropdowns = await self.config.guild(ctx.guild).buttons_dropdowns()
        if f"{message.channel.id}-{message.id}" not in buttons_dropdowns:
            raise commands.UserFeedbackCheckFailure(
                _("This message doesn't have components added with Tickets.")
            )
        buttons_dropdowns.pop(f"{message.channel.id}-{message.id}")
        if message in self.views:
            self.views.pop(message).stop()
        await message.edit(view=None)
        await self.config.guild(ctx.guild).buttons_dropdowns.set(buttons_dropdowns)

    @commands.is_owner()
    @commands.bot_has_permissions(embed_links=True)
    @settickets.command(hidden=True)
    async def getdebugloopsstatus(self, ctx: commands.Context) -> None:
        """Get an embed for check loop status."""
        embeds = [loop.get_debug_embed() for loop in self.loops]
        await Menu(pages=embeds).start(ctx)

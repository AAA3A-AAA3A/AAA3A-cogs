from .AAA3A_utils import CogsUtils  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator  # isort:skip
from redbot.core.bot import Red  # isort:skip
import discord  # isort:skip
import typing  # isort:skip
# import typing_extensions  # isort:skip

if CogsUtils().is_dpy2:
    from .AAA3A_utils import Buttons  # isort:skip
else:
    from dislash import (
        ActionRow,
        Button,
        ButtonStyle,
    )  # isort:skip

import datetime
import chat_exporter
import io

from .utils import utils

_ = Translator("TicketTool", __file__)


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
    ) -> typing.Any:  # typing_extensions.Self
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
    def from_json(json: dict, bot: Red, cog: commands.Cog) -> typing.Any:  # typing_extensions.Self
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

    async def save(ticket) -> typing.Dict[str, typing.Any]:
        if not ticket.save_data:
            return
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

    async def create(ticket) -> typing.Any:  # typing_extensions.Self
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
            reason=_("Creating the ticket {ticket.id}.").format(ticket=ticket),
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
        ).format(ticket=ticket)
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
            ticket.cog.cogsutils.views.append(view)
        else:
            ticket.first_message = await ticket.channel.send(
                f"{ticket.created_by.mention}{optionnal_ping}",
                embed=embed,
                components=[buttons],
                allowed_mentions=discord.AllowedMentions(users=True, roles=True),
            )
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
                description=_("The ticket was created by {ticket.created_by}.").format(ticket=ticket),
            )
            await logschannel.send(
                _("Report on the creation of the ticket {ticket.id}.").format(ticket=ticket),
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

    async def export(ticket) -> typing.Optional[discord.File]:
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

    async def open(ticket, author: typing.Optional[discord.Member] = None) -> typing.Any:  # typing_extensions.Self
        config = await ticket.cog.get_config(ticket.guild, ticket.panel)
        reason = await ticket.cog.get_audit_reason(
            guild=ticket.guild,
            panel=ticket.panel,
            author=author,
            reason=_("Opening the ticket {ticket.id}.").format(ticket=ticket),
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
                        ticket=ticket
                    ),
                )
                await logschannel.send(
                    _("Report on the close of the ticket {ticket.id}.").format(ticket=ticket),
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

    async def close(ticket, author: typing.Optional[discord.Member] = None) -> typing.Any:  # typing_extensions.Self
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

    async def rename(ticket, new_name: str, author: typing.Optional[discord.Member] = None) -> typing.Any:  # typing_extensions.Self
        reason = await ticket.cog.get_audit_reason(
            guild=ticket.guild,
            panel=ticket.panel,
            author=author,
            reason=_(
                "Renaming the ticket {ticket.id}. (`{ticket.channel.name}` to `{new_name}`)"
            ).format(ticket=ticket, new_name=new_name),
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

    async def delete(ticket, author: typing.Optional[discord.Member] = None) -> typing.Any:  # typing_extensions.Self
        config = await ticket.cog.get_config(ticket.guild, ticket.panel)
        logschannel = config["logschannel"]
        reason = await ticket.cog.get_audit_reason(
            guild=ticket.guild,
            panel=ticket.panel,
            author=author,
            reason=_("Deleting the ticket {ticket.id}.").format(ticket=ticket),
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
                        ticket=ticket
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
                    _("Report on the deletion of the ticket {ticket.id}.").format(ticket=ticket),
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
    ) -> typing.Any:  # typing_extensions.Self
        config = await ticket.cog.get_config(ticket.guild, ticket.panel)
        reason = await ticket.cog.get_audit_reason(
            guild=ticket.guild,
            panel=ticket.panel,
            author=author,
            reason=_("Claiming the ticket {ticket.id}.").format(ticket=ticket),
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
        ).format(ticket=ticket)
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
    ) -> typing.Any:  # typing_extensions.Self
        config = await ticket.cog.get_config(ticket.guild, ticket.panel)
        reason = await ticket.cog.get_audit_reason(
            guild=ticket.guild,
            panel=ticket.panel,
            author=author,
            reason=_("Claiming the ticket {ticket.id}.").format(ticket=ticket),
        )
        ticket.claim = None
        topic = _(
            "🎟️ Ticket ID: {ticket.id}\n"
            "🔥 Channel ID: {ticket.channel.id}\n"
            "🕵️ Ticket created by: @{ticket.created_by.display_name} ({ticket.created_by.id})\n"
            "☢️ Ticket reason: {ticket.reason}\n"
            "👥 Ticket claimed by: Nobody."
        ).format(ticket=ticket)
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
    ) -> typing.Any:  # typing_extensions.Self
        config = await ticket.cog.get_config(ticket.guild, ticket.panel)
        reason = await ticket.cog.get_audit_reason(
            guild=ticket.guild,
            panel=ticket.panel,
            author=author,
            reason=_("Changing owner of the ticket {ticket.id}.").format(ticket=ticket),
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
    ) -> typing.Any:  # typing_extensions.Self
        config = await ticket.cog.get_config(ticket.guild, ticket.panel)
        reason = await ticket.cog.get_audit_reason(
            guild=ticket.guild,
            panel=ticket.panel,
            author=author,
            reason=_("Adding a member to the ticket {ticket.id}.").format(ticket=ticket)
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
                        _("You cannot add a bot to a ticket. ({member})").format(member=member)
                    )
                if not isinstance(ticket.owner, int):
                    if member == ticket.owner:
                        raise commands.UserFeedbackCheckFailure(
                            _(
                                "This member is already the owner of this ticket. ({member})"
                            ).format(member=member)
                        )
                if member in admin_role_members:
                    raise commands.UserFeedbackCheckFailure(
                        _(
                            "This member is an administrator for the ticket system. They will always have access to the ticket anyway. ({member})"
                        ).format(member=member)
                    )
                if member in ticket.members:
                    raise commands.UserFeedbackCheckFailure(
                        _("This member already has access to this ticket. ({member})").format(member=member)
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
    ) -> typing.Any:  # typing_extensions.Self
        config = await ticket.cog.get_config(ticket.guild, ticket.panel)
        reason = await ticket.cog.get_audit_reason(
            guild=ticket.guild,
            panel=ticket.panel,
            author=author,
            reason=_("Removing a member to the ticket {ticket.id}.").format(ticket=ticket),
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
                        _("You cannot remove a bot to a ticket ({member}).").format(member=member)
                    )
                if not isinstance(ticket.owner, int):
                    if member == ticket.owner:
                        raise commands.UserFeedbackCheckFailure(
                            _("You cannot remove the owner of this ticket. ({member})").format(member=member)
                        )
                if member in admin_role_members:
                    raise commands.UserFeedbackCheckFailure(
                        _(
                            "This member is an administrator for the ticket system. They will always have access to the ticket. ({member})"
                        ).format(member=member)
                    )
                if member not in ticket.members and member not in support_role_members:
                    raise commands.UserFeedbackCheckFailure(
                        _(
                            "This member is not in the list of those authorised to access the ticket. ({member})"
                        ).format(member=member)
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

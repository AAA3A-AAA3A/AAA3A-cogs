from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator  # isort:skip
from redbot.core.bot import Red  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import datetime
import io

import chat_exporter

from .utils import utils

_ = Translator("TicketTool", __file__)


class Ticket:
    """Representation of a ticket"""

    def __init__(
        self,
        bot,
        cog,
        profile,
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
        locked_by,
        unlocked_by,
        members,
        created_at,
        opened_at,
        closed_at,
        deleted_at,
        renamed_at,
        locked_at,
        unlocked_at,
        status,
        reason,
        logs_messages,
        save_data,
        first_message,
    ):
        self.bot: Red = bot
        self.cog: commands.Cog = cog
        self.profile: str = profile
        self.id: int = id
        self.owner: discord.Member = owner
        self.guild: discord.Guild = guild
        self.channel: typing.Union[discord.TextChannel, discord.Thread] = channel
        self.claim: discord.Member = claim
        self.created_by: discord.Member = created_by
        self.opened_by: discord.Member = opened_by
        self.closed_by: discord.Member = closed_by
        self.deleted_by: discord.Member = deleted_by
        self.renamed_by: discord.Member = renamed_by
        self.locked_by: discord.Member = locked_by
        self.unlocked_by: discord.Member = unlocked_by
        self.members: typing.List[discord.Member] = members
        self.created_at: datetime.datetime = created_at
        self.opened_at: datetime.datetime = opened_at
        self.closed_at: datetime.datetime = closed_at
        self.deleted_at: datetime.datetime = deleted_at
        self.renamed_at: datetime.datetime = renamed_at
        self.locked_at: datetime.datetime = locked_at
        self.unlocked_at: datetime.datetime = unlocked_at
        self.status: str = status
        self.reason: str = reason
        self.logs_messages: bool = logs_messages
        self.save_data: bool = save_data
        self.first_message: discord.Message = first_message

    @staticmethod
    def instance(
        ctx: commands.Context,
        profile: str,
        reason: typing.Optional[str] = _("No reason provided."),
    ) -> typing.Any:
        ticket: Ticket = Ticket(
            bot=ctx.bot,
            cog=ctx.cog,
            profile=profile,
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
            locked_by=None,
            unlocked_by=None,
            members=[],
            created_at=datetime.datetime.now(),
            opened_at=None,
            closed_at=None,
            deleted_at=None,
            renamed_at=None,
            locked_at=None,
            unlocked_at=None,
            status="open",
            reason=reason,
            logs_messages=True,
            save_data=True,
            first_message=None,
        )
        return ticket

    @staticmethod
    def from_json(json: dict, bot: Red, cog: commands.Cog) -> typing.Any:
        ticket: Ticket = Ticket(
            bot=bot,
            cog=cog,
            profile=json["profile"],
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
            locked_by=json.get("renamed_by"),
            unlocked_by=json.get("unlocked_by"),
            members=json["members"],
            created_at=json["created_at"],
            opened_at=json["opened_at"],
            closed_at=json["closed_at"],
            deleted_at=json["deleted_at"],
            renamed_at=json["renamed_at"],
            locked_at=json.get("locked_at"),
            unlocked_at=json.get("unlocked_at"),
            status=json["status"],
            reason=json["reason"],
            logs_messages=json["logs_messages"],
            save_data=json["save_data"],
            first_message=json["first_message"],
        )
        return ticket

    async def save(self) -> typing.Dict[str, typing.Any]:
        if not self.save_data:
            return
        cog = self.cog
        guild = self.guild
        channel = self.channel
        self.bot = None
        self.cog = None
        if self.owner is not None:
            self.owner = int(getattr(self.owner, "id", self.owner))
        if self.guild is not None:
            self.guild = int(self.guild.id)
        if self.channel is not None:
            self.channel = int(self.channel.id)
        if self.claim is not None:
            self.claim = self.claim.id
        if self.created_by is not None:
            self.created_by = int(getattr(self.created_by, "id", self.created_by))
        if self.opened_by is not None:
            self.opened_by = int(getattr(self.opened_by, "id", self.opened_by))
        if self.closed_by is not None:
            self.closed_by = int(getattr(self.closed_by, "id", self.closed_by))
        if self.deleted_by is not None:
            self.deleted_by = int(getattr(self.deleted_by, "id", self.deleted_by))
        if self.renamed_by is not None:
            self.renamed_by = int(getattr(self.renamed_by, "id", self.renamed_by))
        if self.locked_by is not None:
            self.locked_by = int(getattr(self.locked_by, "id", self.locked_by))
        if self.unlocked_by is not None:
            self.unlocked_by = int(getattr(self.unlocked_by, "id", self.unlocked_by))
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
        if self.locked_at is not None:
            self.locked_at = float(datetime.datetime.timestamp(self.locked_at))
        if self.unlocked_at is not None:
            self.unlocked_at = float(datetime.datetime.timestamp(self.unlocked_at))
        if self.first_message is not None:
            self.first_message = int(self.first_message.id)
        json = self.__dict__
        data = await cog.config.guild(guild).tickets.all()
        data[str(channel.id)] = json
        await cog.config.guild(guild).tickets.set(data)
        return data

    async def create(self) -> typing.Any:
        config = await self.cog.get_config(self.guild, self.profile)
        logschannel = config["logschannel"]
        emoji_open = config["emoji_open"]
        ping_role = config["ping_role"]
        self.id = config["last_nb"] + 1
        _reason = await self.cog.get_audit_reason(
            guild=self.guild,
            profile=self.profile,
            author=self.created_by,
            reason=_("Creating the ticket {ticket.id}.").format(ticket=self),
        )
        try:
            to_replace = {
                "ticket_id": str(self.id),
                "owner_display_name": self.owner.display_name,
                "owner_name": self.owner.name,
                "owner_id": str(self.owner.id),
                "guild_name": self.guild.name,
                "guild_id": self.guild.id,
                "bot_display_name": self.guild.me.display_name,
                "bot_name": self.bot.user.name,
                "bot_id": str(self.bot.user.id),
                "shortdate": self.created_at.strftime("%m-%d"),
                "longdate": self.created_at.strftime("%m-%d-%Y"),
                "time": self.created_at.strftime("%I-%M-%p"),
            }
            name = config["dynamic_channel_name"].format(**to_replace).replace(" ", "-")
        except (KeyError, AttributeError):
            name = f"{emoji_open}-ticket-{self.id}"

        view = self.cog.get_buttons(
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
        optionnal_ping = f" ||{ping_role.mention}||" if ping_role is not None else ""
        embed = await self.cog.get_embed_important(
            self,
            False,
            author=self.created_by,
            title=_("Ticket Created"),
            description=_("Thank you for creating a ticket on this server!"),
            reason=self.reason,
        )
        if config["forum_channel"] is None:
            overwrites = await utils().get_overwrites(self)
            self.channel: discord.TextChannel = await self.guild.create_text_channel(
                name,
                overwrites=overwrites,
                category=config["category_open"],
                topic=self.reason,
                reason=_reason,
            )
            topic = _(
                "🎟️ Ticket ID: {ticket.id}\n"
                "🔥 Channel ID: {ticket.channel.id}\n"
                "🕵️ Ticket created by: @{ticket.created_by.display_name} ({ticket.created_by.id})\n"
                "☢️ Ticket reason: {ticket.reason}\n"
                "👥 Ticket claimed by: Nobody."
            ).format(ticket=self)
            await self.channel.edit(topic=topic)
            self.first_message = await self.channel.send(
                f"{self.created_by.mention}{optionnal_ping}",
                embed=embed,
                view=view,
                allowed_mentions=discord.AllowedMentions(users=True, roles=True),
            )
            self.cog.cogsutils.views.append(view)
        else:
            if isinstance(config["forum_channel"], discord.ForumChannel):
                forum_channel: discord.ForumChannel = config["forum_channel"]
                result: discord.channel.ThreadWithMessage = await forum_channel.create_thread(
                    name=name,
                    content=f"{self.created_by.mention}{optionnal_ping}",
                    embed=embed,
                    view=view,
                    allowed_mentions=discord.AllowedMentions(users=True, roles=True),
                    auto_archive_duration=10080,
                    reason=_reason,
                )
                self.channel: discord.Thread = result.thread
                self.first_message: discord.Message = result.message
            else:  # isinstance(config["forum_channel"], discord.TextChannel)
                forum_channel: discord.TextChannel = config["forum_channel"]
                self.channel: discord.Thread = await forum_channel.create_thread(
                    name=name,
                    message=None,  # Private thread.
                    type=discord.ChannelType.private_thread,
                    invitable=False,
                    auto_archive_duration=10080,
                    reason=_reason,
                )
                self.first_message = await self.channel.send(
                    f"{self.created_by.mention}{optionnal_ping}",
                    embed=embed,
                    view=view,
                    allowed_mentions=discord.AllowedMentions(users=True, roles=True),
                )
                self.cog.cogsutils.views.append(view)
            self.cog.cogsutils.views.append(view)
            members = [self.owner]
            if self.claim is not None:
                members.append(self.claim)
            if config["admin_role"] is not None:
                members.extend(config["admin_role"].members)
            if config["support_role"] is not None:
                members.extend(config["support_role"].members)
            if config["view_role"] is not None:
                members.extend(config["view_role"].members)
            for member in members:
                self.channel.add_user(member)
        if config["create_modlog"]:
            await self.cog.create_modlog(self, "ticket_created", _reason)
        if config["custom_message"] is not None:
            try:
                embed: discord.Embed = discord.Embed()
                embed.title = "Custom Message"
                to_replace = {
                    "ticket_id": str(self.id),
                    "owner_display_name": self.owner.display_name,
                    "owner_name": self.owner.name,
                    "owner_id": str(self.owner.id),
                    "guild_name": self.guild.name,
                    "guild_id": self.guild.id,
                    "bot_display_name": self.guild.me.display_name,
                    "bot_name": self.bot.user.name,
                    "bot_id": str(self.bot.user.id),
                    "shortdate": self.created_at.strftime("%m-%d"),
                    "longdate": self.created_at.strftime("%m-%d-%Y"),
                    "time": self.created_at.strftime("%I-%M-%p"),
                }
                embed.description = config["custom_message"].format(**to_replace)
                await self.channel.send(embed=embed)
            except (KeyError, AttributeError, discord.HTTPException):
                pass
        if logschannel is not None:
            embed = await self.cog.get_embed_important(
                self,
                True,
                author=self.created_by,
                title=_("Ticket Created"),
                description=_("The ticket was created by {ticket.created_by}.").format(
                    ticket=self
                ),
                reason=self.reason,
            )
            await logschannel.send(
                _("Report on the creation of the ticket {ticket.id}.").format(ticket=self),
                embed=embed,
            )
        if config["ticket_role"] is not None and self.owner:
            try:
                await self.owner.add_roles(config["ticket_role"], reason=_reason)
            except discord.HTTPException:
                pass
        await self.cog.config.guild(self.guild).profiles.set_raw(
            self.profile, "last_nb", value=self.id
        )
        await self.save()
        return self

    async def export(self) -> typing.Optional[discord.File]:
        if self.channel:
            transcript = await chat_exporter.export(
                channel=self.channel,
                limit=None,
                tz_info="UTC",
                guild=self.guild,
                bot=self.bot,
            )
            if transcript is not None:
                return discord.File(
                    io.BytesIO(transcript.encode()),
                    filename=f"transcript-ticket-{self.profile}-{self.id}.html",
                )
        return None

    async def open(
        self, author: typing.Optional[discord.Member] = None, reason: typing.Optional[str] = None
    ) -> typing.Any:
        config = await self.cog.get_config(self.guild, self.profile)
        _reason = await self.cog.get_audit_reason(
            guild=self.guild,
            profile=self.profile,
            author=author,
            reason=_("Opening the ticket {ticket.id}.").format(ticket=self),
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
        if isinstance(self.channel, discord.TextChannel):
            await self.channel.edit(
                name=new_name, category=config["category_open"], reason=_reason
            )
        else:
            await self.channel.edit(name=new_name, archived=False, reason=_reason)
        if self.logs_messages:
            embed = await self.cog.get_embed_action(
                self, author=self.opened_by, action=_("Ticket Opened"), reason=reason
            )
            await self.channel.send(embed=embed)
            if logschannel is not None:
                embed = await self.cog.get_embed_important(
                    self,
                    True,
                    author=self.opened_by,
                    title=_("Ticket Opened"),
                    description=_("The ticket was opened by {ticket.opened_by}.").format(
                        ticket=self
                    ),
                    reason=reason,
                )
                await logschannel.send(
                    _("Report on the close of the ticket {ticket.id}.").format(ticket=self),
                    embed=embed,
                )
        if self.first_message is not None:
            view = self.cog.get_buttons(
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
            try:
                self.first_message = await self.channel.fetch_message(int(self.first_message.id))
                await self.first_message.edit(view=view)
            except discord.HTTPException:
                pass
        if config["ticket_role"] is not None and self.owner:
            try:
                await self.owner.add_roles(config["ticket_role"], reason=_reason)
            except discord.HTTPException:
                pass
        await self.save()
        return self

    async def close(
        self, author: typing.Optional[discord.Member] = None, reason: typing.Optional[str] = None
    ) -> typing.Any:
        config = await self.cog.get_config(self.guild, self.profile)
        _reason = await self.cog.get_audit_reason(
            guild=self.guild,
            profile=self.profile,
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
        if isinstance(self.channel, discord.TextChannel):
            await self.channel.edit(
                name=new_name, category=config["category_close"], reason=_reason
            )
        else:
            await self.channel.edit(name=new_name, archived=True, reason=_reason)
        if self.logs_messages:
            embed = await self.cog.get_embed_action(
                self, author=self.closed_by, action="Ticket Closed", reason=reason
            )
            await self.channel.send(embed=embed)
            if logschannel is not None:
                embed = await self.cog.get_embed_important(
                    self,
                    True,
                    author=self.closed_by,
                    title="Ticket Closed",
                    description=f"The ticket was closed by {self.closed_by}.",
                    reason=reason,
                )
                await logschannel.send(
                    _("Report on the close of the ticket {ticket.id}."),
                    embed=embed,
                )
        if self.first_message is not None:
            view = self.cog.get_buttons(
                buttons=[
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
                        "disabled": True,
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
            try:
                self.first_message = await self.channel.fetch_message(int(self.first_message.id))
                await self.first_message.edit(view=view)
            except discord.HTTPException:
                pass
        if config["ticket_role"] is not None and self.owner:
            try:
                await self.owner.remove_roles(config["ticket_role"], reason=_reason)
            except discord.HTTPException:
                pass
        await self.save()
        return self

    async def lock(
        self, author: typing.Optional[discord.Member] = None, reason: typing.Optional[str] = None
    ) -> typing.Any:
        if isinstance(self.channel, discord.TextChannel):
            raise commands.UserFeedbackCheckFailure(_("Cannot execute action on a text channel."))
        config = await self.cog.get_config(self.guild, self.profile)
        _reason = await self.cog.get_audit_reason(
            guild=self.guild,
            profile=self.profile,
            author=author,
            reason=f"Locking the ticket {self.id}.",
        )
        logschannel = config["logschannel"]
        self.locked_by = author
        self.locked_at = datetime.datetime.now()
        await self.channel.edit(locked=True, reason=_reason)
        if self.logs_messages:
            embed = await self.cog.get_embed_action(
                self, author=self.locked_by, action="Ticket Locked", reason=reason
            )
            await self.channel.send(embed=embed)
            if logschannel is not None:
                embed = await self.cog.get_embed_important(
                    self,
                    True,
                    author=self.locked_by,
                    title="Ticket Locked",
                    description=f"The ticket was locked by {self.closed_by}.",
                    reason=reason,
                )
                await logschannel.send(
                    _("Report on the lock of the ticket {ticket.id}."),
                    embed=embed,
                )
        await self.save()
        return self

    async def unlock(
        self, author: typing.Optional[discord.Member] = None, reason: typing.Optional[str] = None
    ) -> typing.Any:
        if isinstance(self.channel, discord.TextChannel):
            raise commands.UserFeedbackCheckFailure(_("Cannot execute action on a text channel."))
        config = await self.cog.get_config(self.guild, self.profile)
        _reason = await self.cog.get_audit_reason(
            guild=self.guild,
            profile=self.profile,
            author=author,
            reason=f"Unlocking the ticket {self.id}.",
        )
        logschannel = config["logschannel"]
        self.unlocked_by = author
        self.unlocked_at = datetime.datetime.now()
        await self.channel.edit(locked=False, reason=_reason)
        if self.logs_messages:
            embed = await self.cog.get_embed_action(
                self, author=self.unlocked_by, action="Ticket Unlocked"
            )
            await self.channel.send(embed=embed)
            if logschannel is not None:
                embed = await self.cog.get_embed_important(
                    self,
                    True,
                    author=self.unlocked_by,
                    title="Ticket Unlocked",
                    description=f"The ticket was unlocked by {self.closed_by}.",
                    reason=reason,
                )
                await logschannel.send(
                    _("Report on the unlock of the ticket {ticket.id}."),
                    embed=embed,
                )
        await self.save()
        return self

    async def rename(
        self,
        new_name: str,
        author: typing.Optional[discord.Member] = None,
        reason: typing.Optional[str] = None,
    ) -> typing.Any:
        _reason = await self.cog.get_audit_reason(
            guild=self.guild,
            profile=self.profile,
            author=author,
            reason=_(
                "Renaming the ticket {ticket.id}. (`{ticket.channel.name}` to `{new_name}`)"
            ).format(ticket=self, new_name=new_name),
        )
        await self.channel.edit(name=new_name, reason=_reason)
        if author is not None:
            self.renamed_by = author
            self.renamed_at = datetime.datetime.now()
            if self.logs_messages:
                embed = await self.cog.get_embed_action(
                    self, author=self.renamed_by, action=_("Ticket Renamed."), reason=reason
                )
                await self.channel.send(embed=embed)
            await self.save()
        return self

    async def delete(
        self, author: typing.Optional[discord.Member] = None, reason: typing.Optional[str] = None
    ) -> typing.Any:
        config = await self.cog.get_config(self.guild, self.profile)
        logschannel = config["logschannel"]
        self.deleted_by = author
        self.deleted_at = datetime.datetime.now()
        if self.logs_messages and logschannel is not None:
            embed = await self.cog.get_embed_important(
                self,
                True,
                author=self.deleted_by,
                title=_("Ticket Deleted"),
                description=_("The ticket was deleted by {ticket.deleted_by}.").format(
                    ticket=self
                ),
                reason=reason,
            )
            try:
                transcript = await chat_exporter.export(
                    channel=self.channel,
                    limit=None,
                    tz_info="UTC",
                    guild=self.guild,
                    bot=self.bot,
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
            message = await logschannel.send(
                _("Report on the deletion of the ticket {ticket.id}.").format(ticket=self),
                embed=embed,
                file=file,
            )
            embed = discord.Embed(
                title="Transcript Link",
                description=(
                    f"[Click here to view the transcript.](https://mahto.id/chat-exporter?url={message.attachments[0].url})"
                ),
                color=discord.Color.red(),
            )
            await logschannel.send(embed=embed)
        if isinstance(self.channel, discord.TextChannel):
            _reason = await self.cog.get_audit_reason(
                guild=self.guild,
                profile=self.profile,
                author=author,
                reason=_("Deleting the ticket {ticket.id}.").format(ticket=self),
            )
            await self.channel.delete(reason=_reason)
        else:
            await self.channel.delete()
        data = await self.cog.config.guild(self.guild).tickets.all()
        try:
            del data[str(self.channel.id)]
        except KeyError:
            pass
        await self.cog.config.guild(self.guild).tickets.set(data)
        return self

    async def claim_ticket(
        self,
        member: discord.Member,
        author: typing.Optional[discord.Member] = None,
        reason: typing.Optional[str] = None,
    ) -> typing.Any:
        if self.status != "open":
            raise commands.UserFeedbackCheckFailure(
                _("A ticket cannot be claimed if it is closed.")
            )
        config = await self.cog.get_config(self.guild, self.profile)
        if member.bot:
            raise commands.UserFeedbackCheckFailure(_("A bot cannot claim a ticket."))
        self.claim = member
        topic = _(
            "🎟️ Ticket ID: {ticket.id}\n"
            "🔥 Channel ID: {ticket.channel.id}\n"
            "🕵️ Ticket created by: @{ticket.created_by.display_name} ({ticket.created_by.id})\n"
            "☢️ Ticket reason: {ticket.reason}\n"
            "👥 Ticket claimed by: @{ticket.claim.display_name} (@{ticket.claim.id})."
        ).format(ticket=self)
        if isinstance(self.channel, discord.TextChannel):
            _reason = await self.cog.get_audit_reason(
                guild=self.guild,
                profile=self.profile,
                author=author,
                reason=_("Claiming the ticket {ticket.id}.").format(ticket=self),
            )
            overwrites = self.channel.overwrites
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
            await self.channel.edit(topic=topic, overwrites=overwrites, reason=_reason)
        if self.first_message is not None:
            view = self.cog.get_buttons(
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
                        "label": _("Claim"),
                        "emoji": "🙋‍♂️",
                        "custom_id": "claim_ticket_button",
                        "disabled": True,
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
            try:
                self.first_message = await self.channel.fetch_message(int(self.first_message.id))
                await self.first_message.edit(view=view)
            except discord.HTTPException:
                pass
        if self.logs_messages:
            embed = await self.cog.get_embed_action(
                self, author=author, action=_("Ticket claimed."), reason=reason
            )
            await self.channel.send(embed=embed)
        await self.save()
        return self

    async def unclaim_ticket(
        self,
        member: discord.Member,
        author: typing.Optional[discord.Member] = None,
        reason: typing.Optional[str] = None,
    ) -> typing.Any:
        if self.status != "open":
            raise commands.UserFeedbackCheckFailure(
                _("A ticket cannot be unclaimed if it is closed.")
            )
        config = await self.cog.get_config(self.guild, self.profile)
        self.claim = None
        topic = _(
            "🎟️ Ticket ID: {ticket.id}\n"
            "🔥 Channel ID: {ticket.channel.id}\n"
            "🕵️ Ticket created by: @{ticket.created_by.display_name} ({ticket.created_by.id})\n"
            "☢️ Ticket reason: {ticket.reason}\n"
            "👥 Ticket claimed by: Nobody."
        ).format(ticket=self)
        await self.channel.edit(topic=topic)
        if isinstance(self.channel, discord.TextChannel):
            _reason = await self.cog.get_audit_reason(
                guild=self.guild,
                profile=self.profile,
                author=author,
                reason=_("Unclaiming the ticket {ticket.id}.").format(ticket=self),
            )
            if config["support_role"] is not None:
                overwrites = self.channel.overwrites
                overwrites[config["support_role"]] = discord.PermissionOverwrite(
                    attach_files=True,
                    read_message_history=True,
                    read_messages=True,
                    send_messages=True,
                    view_channel=True,
                )
                await self.channel.edit(overwrites=overwrites, reason=_reason)
            await self.channel.set_permissions(member, overwrite=None, reason=_reason)
        if self.first_message is not None:
            view = self.cog.get_buttons(
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
                        "label": _("Claim"),
                        "emoji": "🙋‍♂️",
                        "custom_id": "claim_ticket_button",
                        "disabled": True,
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
            try:
                self.first_message = await self.channel.fetch_message(int(self.first_message.id))
                await self.first_message.edit(view=view)
            except discord.HTTPException:
                pass
        if self.logs_messages:
            embed = await self.cog.get_embed_action(
                self, author=author, action=_("Ticket unclaimed."), reason=reason
            )
            await self.channel.send(embed=embed)
        await self.save()
        return self

    async def change_owner(
        self,
        member: discord.Member,
        author: typing.Optional[discord.Member] = None,
        reason: typing.Optional[str] = None,
    ) -> typing.Any:
        if not isinstance(self.channel, discord.TextChannel):
            raise commands.UserFeedbackCheckFailure(
                _("Cannot execute action on a thread channel.")
            )
        config = await self.cog.get_config(self.guild, self.profile)
        _reason = await self.cog.get_audit_reason(
            guild=self.guild,
            profile=self.profile,
            author=author,
            reason=_("Changing owner of the ticket {ticket.id}.").format(ticket=self),
        )
        if member.bot:
            raise commands.UserFeedbackCheckFailure(
                _("You cannot transfer ownership of a ticket to a bot.")
            )
        if not isinstance(self.owner, int):
            if config["ticket_role"] is not None:
                try:
                    self.owner.remove_roles(config["ticket_role"], reason=_reason)
                except discord.HTTPException:
                    pass
            self.remove_member(self.owner, author=None)
            self.add_member(self.owner, author=None)
        self.owner = member
        self.remove_member(self.owner, author=None)
        overwrites = self.channel.overwrites
        overwrites[member] = discord.PermissionOverwrite(
            attach_files=True,
            read_message_history=True,
            read_messages=True,
            send_messages=True,
            view_channel=True,
        )
        await self.channel.edit(overwrites=overwrites, reason=_reason)
        if config["ticket_role"] is not None:
            try:
                self.owner.add_roles(config["ticket_role"], reason=_reason)
            except discord.HTTPException:
                pass
        if self.logs_messages:
            embed = await self.cog.get_embed_action(
                self, author=author, action=_("Owner Modified."), reason=reason
            )
            await self.channel.send(embed=embed)
        await self.save()
        return self

    async def add_member(
        self, members: typing.List[discord.Member], author: typing.Optional[discord.Member] = None
    ) -> typing.Any:
        config = await self.cog.get_config(self.guild, self.profile)
        if config["admin_role"] is not None:
            admin_role_members = config["admin_role"].members
        else:
            admin_role_members = []
        if isinstance(self.channel, discord.TextChannel):
            _reason = await self.cog.get_audit_reason(
                guild=self.guild,
                profile=self.profile,
                author=author,
                reason=_("Adding a member to the ticket {ticket.id}.").format(ticket=self),
            )
            overwrites = self.channel.overwrites
            for member in members:
                if author is not None:
                    if member.bot:
                        raise commands.UserFeedbackCheckFailure(
                            _("You cannot add a bot to a ticket. ({member})").format(member=member)
                        )
                    if not isinstance(self.owner, int) and member == self.owner:
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
                    if member in self.members:
                        raise commands.UserFeedbackCheckFailure(
                            _("This member already has access to this ticket. ({member})").format(
                                member=member
                            )
                        )
                if member not in self.members:
                    self.members.append(member)
                overwrites[member] = discord.PermissionOverwrite(
                    attach_files=True,
                    read_message_history=True,
                    read_messages=True,
                    send_messages=True,
                    view_channel=True,
                )
            await self.channel.edit(overwrites=overwrites, reason=_reason)
        else:
            for member in members:
                if author is not None:
                    if member.bot:
                        raise commands.UserFeedbackCheckFailure(
                            _("You cannot add a bot to a ticket. ({member})").format(member=member)
                        )
                    if not isinstance(self.owner, int) and member == self.owner:
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
                    if member in self.members:
                        raise commands.UserFeedbackCheckFailure(
                            _("This member already has access to this ticket. ({member})").format(
                                member=member
                            )
                        )
                    await self.channel.add_user(member)
                if member not in self.members:
                    self.members.append(member)
        await self.save()
        return self

    async def remove_member(
        self, members: typing.List[discord.Member], author: typing.Optional[discord.Member] = None
    ) -> typing.Any:
        config = await self.cog.get_config(self.guild, self.profile)
        if config["admin_role"] is not None:
            admin_role_members = config["admin_role"].members
        else:
            admin_role_members = []
        if config["support_role"] is not None:
            support_role_members = config["support_role"].members
        else:
            support_role_members = []
        if isinstance(self.channel, discord.TextChannel):
            _reason = await self.cog.get_audit_reason(
                guild=self.guild,
                profile=self.profile,
                author=author,
                reason=_("Removing a member to the ticket {ticket.id}.").format(ticket=self),
            )
            for member in members:
                if author is not None:
                    if member.bot:
                        raise commands.UserFeedbackCheckFailure(
                            _("You cannot remove a bot to a ticket ({member}).").format(
                                member=member
                            )
                        )
                    if not isinstance(self.owner, int) and member == self.owner:
                        raise commands.UserFeedbackCheckFailure(
                            _("You cannot remove the owner of this ticket. ({member})").format(
                                member=member
                            )
                        )
                    if member in admin_role_members:
                        raise commands.UserFeedbackCheckFailure(
                            _(
                                "This member is an administrator for the ticket system. They will always have access to the ticket. ({member})"
                            ).format(member=member)
                        )
                    if member not in self.members and member not in support_role_members:
                        raise commands.UserFeedbackCheckFailure(
                            _(
                                "This member is not in the list of those authorised to access the ticket. ({member})"
                            ).format(member=member)
                        )
                    await self.channel.set_permissions(member, overwrite=None, reason=_reason)
                if member in self.members:
                    self.members.remove(member)
        else:
            for member in members:
                if author is not None:
                    if member.bot:
                        raise commands.UserFeedbackCheckFailure(
                            _("You cannot remove a bot to a ticket ({member}).").format(
                                member=member
                            )
                        )
                    if not isinstance(self.owner, int) and member == self.owner:
                        raise commands.UserFeedbackCheckFailure(
                            _("You cannot remove the owner of this ticket. ({member})").format(
                                member=member
                            )
                        )
                    if member in admin_role_members:
                        raise commands.UserFeedbackCheckFailure(
                            _(
                                "This member is an administrator for the ticket system. They will always have access to the ticket. ({member})"
                            ).format(member=member)
                        )
                    if member not in self.members and member not in support_role_members:
                        raise commands.UserFeedbackCheckFailure(
                            _(
                                "This member is not in the list of those authorised to access the ticket. ({member})"
                            ).format(member=member)
                        )
                    await self.channel.remove_user(member)
                if member in self.members:
                    self.members.remove(member)
        await self.save()
        return self

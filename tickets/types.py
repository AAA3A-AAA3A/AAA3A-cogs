from redbot.core import commands, modlog  # isort:skip
from redbot.core.bot import Red  # isort:skip
from redbot.core.i18n import Translator  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import asyncio
import copy
import datetime
import io
from dataclasses import _is_dataclass_instance, dataclass, field, fields

import chat_exporter
from redbot.core.utils.chat_formatting import bold, humanize_list

from .views import ClosedTicketControls, TicketView

_: Translator = Translator("Tickets", __file__)


def _asdict_inner(obj, dict_factory=dict):
    if _is_dataclass_instance(obj):
        result = []
        for f in fields(obj):
            if isinstance(getattr(obj, f.name), (Red, commands.Cog)):
                continue
            value = _asdict_inner(getattr(obj, f.name), dict_factory)
            result.append((f.name, value))
        return dict_factory(result)
    elif isinstance(obj, tuple) and hasattr(obj, "_fields"):
        return type(obj)(*[_asdict_inner(v, dict_factory) for v in obj])
    elif isinstance(obj, (list, tuple)):
        return type(obj)(_asdict_inner(v, dict_factory) for v in obj)
    elif isinstance(obj, dict):
        return type(obj)(
            (_asdict_inner(k, dict_factory), _asdict_inner(v, dict_factory))
            for k, v in obj.items()
        )
    else:
        return copy.deepcopy(obj)


@dataclass
class Ticket:
    bot: Red
    cog: commands.Cog

    guild_id: int
    id: int

    owner_id: int
    channel_id: int = None
    message_id: int = None

    profile: typing.Optional[str] = "main"
    reason: typing.Optional[str] = None
    category_label: typing.Optional[str] = None
    owner_answers: typing.Dict[str, str] = field(default_factory=dict)

    opened_at_timestamp: int = field(
        default_factory=lambda: int(
            datetime.datetime.now(tz=datetime.timezone.utc)
            .replace(second=0, microsecond=0)
            .timestamp()
        )
    )
    is_claimed: bool = False
    claimed_by_id: typing.Optional[int] = None
    claimed_at_timestamp: int = None
    is_closed: bool = False
    closed_by_id: typing.Optional[int] = None
    closed_at_timestamp: int = None
    reopened_by_id: typing.Optional[int] = None
    reopened_at_timestamp: int = None
    is_locked: bool = False
    locked_by_id: typing.Optional[int] = None
    locked_at_timestamp: int = None
    unlocked_by_id: typing.Optional[int] = None
    unlocked_at_timestamp: int = None

    members_ids: typing.List[int] = field(default_factory=list)

    def to_dict(self) -> typing.Dict[str, typing.Any]:
        return _asdict_inner(self)

    async def save(self) -> None:
        await self.cog.config.guild(self.guild).tickets.set_raw(str(self.id), value=self.to_dict())
        self.cog.tickets.setdefault(self.guild_id, {})[self.id] = self

    async def delete(self) -> None:
        try:
            del self.cog.tickets[self.guild_id][self.id]
        except KeyError:
            pass
        else:
            if not self.cog.tickets[self.guild_id]:
                del self.cog.tickets[self.guild_id]
        await self.cog.config.guild(self.guild).tickets.clear_raw(str(self.id))
        if self.message in self.cog.views:
            self.cog.views.pop(self.message).stop()

    @property
    def guild(self) -> discord.Guild:
        return self.bot.get_guild(self.guild_id)

    @guild.setter
    def guild(self, guild: discord.Guild) -> None:
        self.guild_id = guild.id

    @property
    def owner(self) -> typing.Optional[discord.Member]:
        if (guild := self.guild) is None:
            return None
        return guild.get_member(self.owner_id)

    @owner.setter
    def owner(self, owner: discord.Member) -> None:
        self.owner_id = owner.id

    @property
    def channel(
        self,
    ) -> typing.Optional[typing.Union[discord.TextChannel, discord.VoiceChannel, discord.Thread]]:
        if (guild := self.guild) is None:
            return None
        return guild.get_channel_or_thread(self.channel_id)

    @channel.setter
    def channel(
        self, channel: typing.Union[discord.TextChannel, discord.VoiceChannel, discord.Thread]
    ) -> None:
        self.guild_id = channel.guild.id
        self.channel_id = channel.id

    @property
    def message(self) -> typing.Optional[discord.Message]:
        if (channel := self.channel) is None:
            return None
        if self.message_id is None:
            return None
        return channel.get_partial_message(self.message_id)

    @message.setter
    def message(self, message: discord.Message) -> None:
        self.guild_id = message.guild.id
        self.channel_id = message.channel.id
        self.message_id = message.id

    @property
    def opened_at(self) -> datetime.datetime:
        return datetime.datetime.fromtimestamp(self.opened_at_timestamp, tz=datetime.timezone.utc)

    @opened_at.setter
    def opened_at(self, opened_at: datetime.datetime) -> None:
        self.opened_at_timestamp = int(opened_at.timestamp())

    @property
    def claimed_by(self) -> typing.Optional[discord.Member]:
        if (guild := self.guild) is None:
            return None
        return guild.get_member(self.claimed_by_id)

    @claimed_by.setter
    def claimed_by(self, claimed_by: typing.Optional[discord.Member]) -> None:
        if claimed_by is None:
            self.claimed_by_id = None
        else:
            self.claimed_by_id = claimed_by.id

    @property
    def claimed_at(self) -> typing.Optional[datetime.datetime]:
        if self.claimed_at_timestamp is None:
            return None
        return datetime.datetime.fromtimestamp(self.claimed_at_timestamp, tz=datetime.timezone.utc)

    @claimed_at.setter
    def claimed_at(self, claimed_at: typing.Optional[datetime.datetime]) -> None:
        self.claimed_at_timestamp = None if claimed_at is None else int(claimed_at.timestamp())

    @property
    def closed_by(self) -> typing.Optional[discord.Member]:
        if (guild := self.guild) is None:
            return None
        return guild.get_member(self.closed_by_id)

    @closed_by.setter
    def closed_by(self, closed_by: typing.Optional[discord.Member]) -> None:
        if closed_by is None:
            self.closed_by_id = None
        else:
            self.closed_by_id = closed_by.id

    @property
    def closed_at(self) -> typing.Optional[datetime.datetime]:
        if self.closed_at_timestamp is None:
            return None
        return datetime.datetime.fromtimestamp(self.closed_at_timestamp, tz=datetime.timezone.utc)

    @closed_at.setter
    def closed_at(self, closed_at: typing.Optional[datetime.datetime]) -> None:
        self.closed_at_timestamp = None if closed_at is None else int(closed_at.timestamp())

    @property
    def reopened_by(self) -> typing.Optional[discord.Member]:
        if (guild := self.guild) is None:
            return None
        return guild.get_member(self.reopened_by_id)

    @reopened_by.setter
    def reopened_by(self, reopened_by: typing.Optional[discord.Member]) -> None:
        if reopened_by is None:
            self.reopened_by_id = None
        else:
            self.reopened_by_id = reopened_by.id

    @property
    def locked_by(self) -> typing.Optional[discord.Member]:
        if (guild := self.guild) is None:
            return None
        return guild.get_member(self.locked_by_id)

    @locked_by.setter
    def locked_by(self, locked_by: typing.Optional[discord.Member]) -> None:
        if locked_by is None:
            self.locked_by_id = None
        else:
            self.locked_by_id = locked_by.id

    @property
    def locked_at(self) -> typing.Optional[datetime.datetime]:
        if self.locked_at_timestamp is None:
            return None
        return datetime.datetime.fromtimestamp(self.locked_at_timestamp, tz=datetime.timezone.utc)

    @locked_at.setter
    def locked_at(self, locked_at: typing.Optional[datetime.datetime]) -> None:
        self.locked_at_timestamp = None if locked_at is None else int(locked_at.timestamp())

    @property
    def unlocked_by(self) -> typing.Optional[discord.Member]:
        if (guild := self.guild) is None:
            return None
        return guild.get_member(self.unlocked_by_id)

    @unlocked_by.setter
    def unlocked_by(self, unlocked_by: typing.Optional[discord.Member]) -> None:
        if unlocked_by is None:
            self.unlocked_by_id = None
        else:
            self.unlocked_by_id = unlocked_by.id

    @property
    def unlocked_at(self) -> typing.Optional[datetime.datetime]:
        if self.unlocked_at_timestamp is None:
            return None
        return datetime.datetime.fromtimestamp(
            self.unlocked_at_timestamp, tz=datetime.timezone.utc
        )

    @unlocked_at.setter
    def unlocked_at(self, unlocked_at: typing.Optional[datetime.datetime]) -> None:
        self.unlocked_at_timestamp = None if unlocked_at is None else int(unlocked_at.timestamp())

    @property
    def members(self) -> typing.List[discord.Member]:
        if (guild := self.guild) is None:
            return []
        return [
            member
            for member_id in self.members_ids
            if (member := guild.get_member(member_id)) is not None
        ]

    @members.setter
    def members(self, members: typing.List[discord.Member]) -> None:
        self.members_ids = [member.id for member in members]

    @property
    def emoji(self) -> str:
        return "🔒" if self.is_closed else ("👥" if self.is_claimed else "❓")

    async def channel_name(self, forum_channel: typing.Optional[bool] = None) -> str:
        channel_name = await self.cog.config.guild(self.guild).profiles.get_raw(
            self.profile, "channel_name"
        )
        if channel_name is None:
            if forum_channel or (
                self.channel is not None and isinstance(self.channel, discord.Thread)
            ):
                channel_name = (
                    "{emoji} Ticket{profile} — {owner_display_name} ({owner_id})".replace(
                        "{profile}",
                        (
                            ""
                            if self.profile == "main"
                            else f" ({self.profile.replace('_', ' ').title()})"
                        ),
                    )
                )
            else:
                channel_name = "{emoji}-{profile}-{owner_name}".replace(
                    "{profile}", "ticket" if self.profile == "main" else self.profile
                )

        return channel_name.format(
            emoji=self.emoji,
            owner_display_name=self.owner.display_name,
            owner_name=self.owner.name,
            owner_mention=self.owner.mention,
            owner_id=self.owner.id,
            guild_name=self.guild.name,
            guild_id=self.guild.id,
        )[:100]

    async def get_embed(self, for_logging: bool = False) -> discord.Embed:
        embed: discord.Embed = discord.Embed(
            title=bold(_("Ticket #{self.id} [{self.profile}]")).format(self=self),
            color=(
                discord.Color.red()
                if self.is_closed
                else (discord.Color.green() if not self.is_claimed else discord.Color.blue())
            ),
            url=self.message.jump_url if for_logging and self.message is not None else None,
        )
        if self.owner is not None:
            embed.set_author(
                name=f"{self.owner.display_name} ({self.owner.id})",
                icon_url=self.owner.display_avatar,
            )
        else:
            if self.message_id is not None:
                try:
                    message = await self.message.channel.fetch_message(self.message.id)
                except discord.HTTPException:
                    pass
                else:
                    embed._author = message.embeds[0]._author
            if embed.author.name is None:
                embed.set_author(
                    name=f"[Unknown] ({self.owner_id})",
                )
        embed.set_thumbnail(url=self.guild.icon)
        embed.description = (
            _(
                "Claimed by: {claimed_by.mention}"
                "\nClaimed at: <t:{claimed_at}:F> (<t:{claimed_at}:R>)"
            ).format(
                claimed_by=(
                    self.claimed_by
                    if self.claimed_by is not None
                    else type("", (), {"mention": _("[Unknown]"), "id": self.claimed_by_id})
                ),
                claimed_at=int(self.claimed_at.timestamp()),
            )
            if self.is_claimed
            else _("Not claimed.")
        ) + (
            _(
                "\nClosed by: {closed_by.mention}"
                "\nClosed at: <t:{closed_at}:F> (<t:{closed_at}:R>)"
            ).format(
                closed_by=(
                    self.closed_by
                    if self.closed_by is not None
                    else type("", (), {"mention": _("[Unknown]"), "id": self.closed_by_id})
                ),
                closed_at=int(self.closed_at.timestamp()),
            )
            if self.is_closed
            else ""
        )
        if self.reason is not None:
            embed.add_field(
                name=_("Reason:"),
                value=f">>> {self.reason}",
                inline=False,
            )
        embed.set_footer(
            text=f"{self.guild.name} | " + _("Opened at:"),
            icon_url=self.guild.icon,
        )
        embed.timestamp = self.opened_at
        return embed

    async def get_embeds(self) -> typing.List[discord.Embed]:
        embeds = [await self.get_embed()]
        config = await self.cog.config.guild(self.guild).profiles.get_raw(self.profile)
        if (
            self.category_label is not None and config["always_include_item_label"]
        ) or self.owner_answers:
            embed: discord.Embed = discord.Embed(
                title=self.category_label,
                color=await self.bot.get_embed_color(self.guild.channels[0]),
            )
            for question, answer in self.owner_answers.items():
                embed.add_field(
                    name=question,
                    value=f">>> {answer}",
                    inline=False,
                )
            embeds.append(embed)
        if config["custom_message"] is not None:
            embeds.append(
                discord.Embed(
                    description=config["custom_message"].format(
                        owner_display_name=self.owner.display_name,
                        owner_name=self.owner.name,
                        owner_mention=self.owner.mention,
                        owner_id=self.owner.id,
                        guild_name=self.guild.name,
                        guild_id=self.guild.id,
                    ),
                    color=await self.bot.get_embed_color(self.guild.channels[0]),
                )
            )
        return embeds

    async def get_kwargs(
        self,
    ) -> typing.Dict[
        typing.Literal["content", "embeds", "view", "allowed_mentions"],
        typing.Union[str, discord.Embed, discord.ui.View],
    ]:
        config = await self.cog.config.guild(self.guild).profiles.get_raw(self.profile)
        content = (
            f"[ {humanize_list([ping_role.mention for ping_role in ping_roles])} ]\n\n"
            if any(
                ping_roles := [
                    ping_role
                    for ping_role_id in config["ping_roles"]
                    if (ping_role := self.guild.get_role(ping_role_id)) is not None
                ]
            )
            else ""
        )
        if self.owner is not None:
            content += config.get("welcome_message", "Welcome {owner_mention}! 👋").format(
                owner_display_name=self.owner.display_name,
                owner_name=self.owner.name,
                owner_mention=self.owner.mention,
                owner_id=self.owner.id,
                guild_name=self.guild.name,
                guild_id=self.guild.id,
            )

        embeds = await self.get_embeds()
        view: TicketView = TicketView(cog=self.cog, ticket=self)

        return {
            "content": content.strip(),
            "embeds": embeds,
            "view": view,
            "allowed_mentions": discord.AllowedMentions(roles=True),
        }

    async def create(self) -> typing.Union[discord.TextChannel, discord.Thread]:
        config: typing.Dict[str, typing.Any] = await self.cog.config.guild(
            self.guild
        ).profiles.get_raw(self.profile)
        if not config["enabled"]:
            raise RuntimeError(_("The creation of tickets is disabled for this profile."))
        forum_channel = (
            self.guild.get_channel(forum_channel_id)
            if (forum_channel_id := config.get("forum_channel")) is not None
            else None
        )
        category_open = (
            self.guild.get_channel(category_open_id)
            if (category_open_id := config.get("category_open")) is not None
            else None
        )
        if forum_channel is None and category_open is None:
            raise RuntimeError(_("No forum channel or category open configured for this profile."))
        if not await self.bot.is_admin(self.owner) and self.owner.id not in self.bot.owner_ids:
            if (
                config["whitelist_roles"]
                and not any(
                    self.owner.get_role(whitelist_role_id) is not None
                    for whitelist_role_id in config["whitelist_roles"]
                )
                or config["blacklist_roles"]
                and any(
                    self.owner.get_role(blacklist_role_id) is not None
                    for blacklist_role_id in config["blacklist_roles"]
                )
            ):
                raise RuntimeError(_("You are not allowed to create a ticket with this profile."))
            if (
                len(
                    [
                        ticket
                        for ticket in self.cog.tickets.get(self.guild_id, {}).values()
                        if ticket.owner_id == self.owner_id and not ticket.is_closed
                    ]
                )
                >= config["max_open_tickets_by_member"]
            ):
                raise RuntimeError(
                    _("You have reached the maximum number of open tickets for this profile.")
                )

        audit_reason = _(
            "Ticket creation for {ticket.owner.display_name} ({ticket.owner.id}) (profile `{ticket.profile}`)"
        ).format(ticket=self)
        if (
            (ticket_role_id := config.get("ticket_role")) is not None
            and (ticket_role := self.guild.get_role(ticket_role_id)) is not None
            and ticket_role not in self.owner.roles
        ):
            try:
                await self.owner.add_roles(
                    ticket_role,
                    reason=audit_reason,
                )
            except discord.HTTPException:
                pass

        kwargs = await self.get_kwargs()
        view = kwargs["view"]
        await view._update()
        if forum_channel is not None:
            if not forum_channel.permissions_for(forum_channel.guild.me).create_private_threads:
                raise RuntimeError(
                    _(
                        "I don't have the required permissions to create private threads in the forum/text channel configured."
                    )
                )
            if isinstance(forum_channel, discord.ForumChannel):
                thread_message = await forum_channel.create_thread(
                    name=await self.channel_name(forum_channel=True),
                    auto_archive_duration=10080,
                    reason=audit_reason,
                    **kwargs,
                )
                self.channel, view._message = thread_message.thread, thread_message.message
            else:
                self.channel = await forum_channel.create_thread(
                    name=await self.channel_name(forum_channel=True),
                    auto_archive_duration=10080,
                    invitable=False,
                    reason=audit_reason,
                )
                view._message = await self.channel.send(**kwargs)
        else:
            if not category_open.permissions_for(self.guild.me).manage_channels:
                raise RuntimeError(
                    _(
                        "I don't have the required permissions to create text channels in the category configured."
                    )
                )
            self.channel = await self.guild.create_text_channel(
                name=await self.channel_name(forum_channel=False),
                category=category_open,
                overwrites=await self.get_channel_overwrites(),
                reason=audit_reason,
            )
            view._message = await self.channel.send(**kwargs)
        self.cog.views[view._message] = view
        self.message = view._message
        tickets_number = await self.cog.config.member(self.owner).tickets_number()
        await self.cog.config.member(self.owner).tickets_number.set(tickets_number + 1)
        await self.save()

        self.bot.dispatch("ticket_created", self)
        if config["create_modlog_case"]:
            await modlog.create_case(
                bot=self.bot,
                guild=self.guild,
                created_at=self.opened_at,
                action_type="ticket_created",
                user=self.owner,
                moderator=self.guild.me,
                channel=self.channel,
            )
        await self.cog.send_ticket_log(self)

        return view._message

    async def get_channel_overwrites(
        self,
    ) -> typing.Dict[typing.Union[discord.Member, discord.Role], discord.PermissionOverwrite]:
        config: typing.Dict[str, typing.Any] = await self.cog.config.guild(
            self.guild
        ).profiles.get_raw(self.profile)
        overwrites = {
            self.guild.default_role: discord.PermissionOverwrite(
                read_messages=False,
                read_message_history=False,
                send_messages=False,
                add_reactions=False,
                embed_links=False,
                attach_files=False,
            ),
            self.guild.me: discord.PermissionOverwrite(
                read_messages=True,
                read_message_history=True,
                send_messages=True,
                add_reactions=True,
                manage_channels=True,
                manage_permissions=True,
                manage_messages=True,
                embed_links=True,
                attach_files=True,
            ),
            self.owner: discord.PermissionOverwrite(
                read_messages=True,
                read_message_history=True,
                send_messages=True,
                add_reactions=True,
                embed_links=True,
                attach_files=True,
            ),
        }
        for support_role_id in config["support_roles"]:
            if (support_role := self.guild.get_role(support_role_id)) is not None:
                overwrites[support_role] = discord.PermissionOverwrite(
                    read_messages=True,
                    read_message_history=True,
                    send_messages=True,
                    add_reactions=True,
                    embed_links=True,
                    attach_files=True,
                )
        for view_role_id in config["view_roles"]:
            if (view_role := self.guild.get_role(view_role_id)) is not None:
                overwrites[view_role] = discord.PermissionOverwrite(
                    read_messages=True,
                    read_message_history=True,
                    send_messages=False,
                    add_reactions=True,
                    embed_links=False,
                    attach_files=False,
                )
        return overwrites

    async def close(
        self,
        closer: typing.Optional[discord.Member] = None,
        reason: typing.Optional[str] = None,
    ) -> None:
        if self.is_closed:
            raise RuntimeError(_("This ticket is already closed."))
        config = await self.cog.config.guild(self.guild).profiles.get_raw(self.profile)
        if closer is not None and not config["owner_can_close"]:
            fake_context = type(
                "FakeContext",
                (),
                {
                    "bot": self.bot,
                    "guild": self.guild,
                    "channel": self.channel,
                    "author": closer,
                    "kwargs": {"profile": self.profile},
                },
            )()
            if not await self.cog.is_support.__func__(ignore_owner=True).predicate(fake_context):
                raise RuntimeError(_("You aren't allowed to close this ticket!"))
        config = await self.cog.config.guild(self.guild).profiles.get_raw(self.profile)
        self.is_closed = True
        # self.reopened_by = None
        # self.reopened_at = None
        self.closed_by = closer
        self.closed_at = datetime.datetime.now(tz=datetime.timezone.utc)
        await self.save()

        if closer is None:
            audit_reason = _("Ticket closed (profile `{self.profile}`)").format(self=self)
        else:
            audit_reason = _(
                "Ticket closed by {closer.display_name} ({closer.id}) (profile `{self.profile}`)"
            ).format(closer=closer, self=self)
        if isinstance(self.channel, discord.Thread):
            await self.channel.edit(
                name=await self.channel_name(),
                archived=True,
                locked=True,
                reason=audit_reason,
            )
        else:
            await self.channel.edit(
                name=await self.channel_name(),
                category=(
                    category_closed
                    if (
                        (category_closed_id := config.get("category_closed")) is not None
                        and (category_closed := self.guild.get_channel(category_closed_id))
                        is not None
                    )
                    else self.channel.category
                ),
                reason=audit_reason,
            )
        view = self.cog.views[self.message]
        await view._update()
        await self.message.edit(
            embeds=await self.get_embeds(),
            view=view,
        )

        self.bot.dispatch("ticket_closed", self)
        await self.log_action(
            action=_("❌ Ticket Closed"),
            author=closer,
            reason=reason,
        )
        view: ClosedTicketControls = ClosedTicketControls(cog=self.cog)
        await view.start(self)
        if config["create_modlog_case"]:
            await modlog.create_case(
                bot=self.bot,
                guild=self.guild,
                created_at=self.closed_at,
                action_type="ticket_closed",
                user=self.owner,
                moderator=closer,
                reason=reason,
                channel=self.channel,
            )
        await self.cog.send_ticket_log(self)

        if config["auto_delete_on_close"] == 0:
            await self.channel.send(
                embed=discord.Embed(
                    title=_("🗑️ This ticket will be deleted in a few seconds..."),
                    color=discord.Color.red(),
                ),
            )
            await asyncio.sleep(5)
            await self.delete_channel(None)  # That's a setting, so no deleter.

    async def reopen(
        self,
        reopener: typing.Optional[discord.Member] = None,
        reason: typing.Optional[str] = None,
    ) -> None:
        if not self.is_closed:
            raise RuntimeError(_("This ticket is not closed."))
        config = await self.cog.config.guild(self.guild).profiles.get_raw(self.profile)
        if reopener is not None and not config["owner_can_reopen"]:
            fake_context = type(
                "FakeContext",
                (),
                {
                    "bot": self.bot,
                    "guild": self.guild,
                    "channel": self.channel,
                    "author": reopener,
                    "kwargs": {"profile": self.profile},
                },
            )()
            if not await self.cog.is_support.__func__(ignore_owner=True).predicate(fake_context):
                raise RuntimeError(_("You aren't allowed to reopen this ticket!"))
        self.is_closed = False
        # self.closed_by = None
        # self.closed_at = None
        self.reopened_by = reopener
        self.reopened_at = datetime.datetime.now(tz=datetime.timezone.utc)
        await self.save()

        if reopener is None:
            audit_reason = _("Ticket reopened (profile `{self.profile}`)").format(self=self)
        else:
            audit_reason = _(
                "Ticket reopened by {reopener.display_name} ({reopener.id}) (profile `{self.profile}`)"
            ).format(reopener=reopener, self=self)
        if isinstance(self.channel, discord.Thread):
            await self.channel.edit(
                name=await self.channel_name(),
                archived=False,
                locked=False,
                reason=audit_reason,
            )
        else:
            await self.channel.edit(
                name=await self.channel_name(),
                category=(
                    category_open
                    if (
                        (category_open_id := config.get("category_open")) is not None
                        and (category_open := self.guild.get_channel(category_open_id)) is not None
                    )
                    else self.channel.category
                ),
                reason=audit_reason,
            )
        view = self.cog.views[self.message]
        await view._update()
        await self.message.edit(
            embeds=await self.get_embeds(),
            view=view,
        )

        self.bot.dispatch("ticket_reopened", self)
        await self.log_action(
            action=_("👐 Ticket Reopened"),
            author=reopener,
            reason=reason,
        )
        if config["create_modlog_case"]:
            await modlog.create_case(
                bot=self.bot,
                guild=self.guild,
                created_at=self.reopened_at,
                action_type="ticket_reopened",
                user=self.owner,
                moderator=reopener,
                reason=reason,
                channel=self.channel,
            )
        await self.cog.send_ticket_log(self)

    async def claim(self, claimer: discord.Member) -> None:
        if self.is_claimed:
            raise RuntimeError(_("This ticket is already claimed."))
        self.is_claimed = True
        self.claimed_by = claimer
        self.claimed_at = datetime.datetime.now(tz=datetime.timezone.utc)
        await self.save()

        audit_reason = _(
            "Ticket claimed by {claimer.display_name} ({claimer.id}) (profile `{self.profile}`)"
        ).format(claimer=claimer, self=self)
        await self.channel.edit(
            name=await self.channel_name(),
            reason=audit_reason,
        )
        view = self.cog.views[self.message]
        await view._update()
        await self.message.edit(
            embeds=await self.get_embeds(),
            view=view,
        )

        self.bot.dispatch("ticket_claimed", self)
        config = await self.cog.config.guild(self.guild).profiles.get_raw(self.profile)
        await self.log_action(
            action=_("👥 Ticket Claimed"),
            author=claimer,
        )
        if config["create_modlog_case"]:
            await modlog.create_case(
                bot=self.bot,
                guild=self.guild,
                created_at=self.claimed_at,
                action_type="ticket_claimed",
                user=self.owner,
                moderator=claimer,
                channel=self.channel,
            )
        await self.cog.send_ticket_log(self)

    async def unclaim(self) -> None:
        if not self.is_claimed:
            raise RuntimeError(_("This ticket is not claimed."))
        self.is_claimed = False
        # self.claimed_by = None
        # self.claimed_at = None
        await self.save()

        audit_reason = _("Ticket unclaimed (profile `{self.profile}`)").format(self=self)
        await self.channel.edit(
            name=await self.channel_name(),
            reason=audit_reason,
        )
        view = self.cog.views[self.message]
        await view._update()
        await self.message.edit(
            embeds=await self.get_embeds(),
            view=view,
        )

        self.bot.dispatch("ticket_unclaimed", self)
        config = await self.cog.config.guild(self.guild).profiles.get_raw(self.profile)
        await self.log_action(
            action=_("👤 Ticket Unclaimed"),
        )
        if config["create_modlog_case"]:
            await modlog.create_case(
                bot=self.bot,
                guild=self.guild,
                created_at=datetime.datetime.now(tz=datetime.timezone.utc),
                action_type="ticket_unclaimed",
                user=self.owner,
                moderator=self.guild.me,
                channel=self.channel,
            )
        await self.cog.send_ticket_log(self)

    async def lock(self, locker: typing.Optional[discord.Member] = None) -> None:
        if self.is_locked:
            raise RuntimeError(_("This ticket is already locked."))
        config = await self.cog.config.guild(self.guild).profiles.get_raw(self.profile)
        if locker is not None:
            fake_context = type(
                "FakeContext",
                (),
                {
                    "bot": self.bot,
                    "guild": self.guild,
                    "channel": self.channel,
                    "author": locker,
                    "kwargs": {"profile": self.profile},
                },
            )()
            if not await self.cog.is_support.__func__(ignore_owner=True).predicate(fake_context):
                raise RuntimeError(_("You aren't allowed to lock this ticket!"))
        self.is_locked = True
        self.locked_by = locker
        self.locked_at = datetime.datetime.now(tz=datetime.timezone.utc)
        await self.save()

        if locker is None:
            audit_reason = _("Ticket locked (profile `{self.profile}`)").format(self=self)
        else:
            audit_reason = _(
                "Ticket locked by {locker.display_name} ({locker.id}) (profile `{self.profile}`)"
            ).format(locker=locker, self=self)
        if isinstance(self.channel, discord.Thread):
            await self.channel.edit(
                locked=True,
                reason=audit_reason,
            )
        else:
            await self.channel.set_permissions(
                self.owner,
                send_messages=False,
                reason=audit_reason,
            )
            for member in self.members:
                await self.channel.set_permissions(
                    member,
                    send_messages=False,
                    reason=audit_reason,
                )
        view = self.cog.views[self.message]
        await view._update()
        await self.message.edit(
            embeds=await self.get_embeds(),
            view=view,
        )

        self.bot.dispatch("ticket_locked", self)
        await self.log_action(
            action=_("🔒 Ticket Locked"),
            author=locker,
        )
        if config["create_modlog_case"]:
            await modlog.create_case(
                bot=self.bot,
                guild=self.guild,
                created_at=self.locked_at,
                action_type="ticket_locked",
                user=self.owner,
                moderator=locker,
                channel=self.channel,
            )

    async def unlock(self, unlocker: typing.Optional[discord.Member] = None) -> None:
        if not self.is_locked:
            raise RuntimeError(_("This ticket is not locked."))
        config = await self.cog.config.guild(self.guild).profiles.get_raw(self.profile)
        if unlocker is not None:
            fake_context = type(
                "FakeContext",
                (),
                {
                    "bot": self.bot,
                    "guild": self.guild,
                    "channel": self.channel,
                    "author": unlocker,
                    "kwargs": {"profile": self.profile},
                },
            )()
            if not await self.cog.is_support.__func__(ignore_owner=True).predicate(fake_context):
                raise RuntimeError(_("You aren't allowed to unlock this ticket!"))
        self.is_locked = False
        # self.locked_by = None
        # self.locked_at = None
        self.unlocked_by = unlocker
        self.unlocked_at = datetime.datetime.now(tz=datetime.timezone.utc)
        await self.save()

        if unlocker is not None:
            audit_reason = _("Ticket unlocked (profile `{self.profile}`)").format(self=self)
        else:
            audit_reason = _(
                "Ticket unlocked by {unlocker.display_name} ({unlocker.id}) (profile `{self.profile}`)"
            ).format(unlocker=unlocker, self=self)
        if isinstance(self.channel, discord.Thread):
            await self.channel.edit(
                locked=False,
                reason=audit_reason,
            )
        else:
            await self.channel.set_permissions(
                self.owner,
                send_messages=True,
                reason=audit_reason,
            )
            for member in self.members:
                await self.channel.set_permissions(
                    member,
                    send_messages=True,
                    reason=audit_reason,
                )
        view = self.cog.views[self.message]
        await view._update()
        await self.message.edit(
            embeds=await self.get_embeds(),
            view=view,
        )

        self.bot.dispatch("ticket_unlocked", self)
        await self.log_action(
            action=_("🔓 Ticket Unlocked"),
            author=unlocker,
        )
        if config["create_modlog_case"]:
            await modlog.create_case(
                bot=self.bot,
                guild=self.guild,
                created_at=self.unlocked_at,
                action_type="ticket_unlocked",
                user=self.owner,
                moderator=unlocker,
                channel=self.channel,
            )

    async def add_member(
        self, member: discord.Member, author: typing.Optional[discord.Member] = None
    ) -> None:
        config = await self.cog.config.guild(self.guild).profiles.get_raw(self.profile)
        if author is not None and not config["owner_can_add_members"]:
            fake_context = type(
                "FakeContext",
                (),
                {
                    "bot": self.bot,
                    "guild": self.guild,
                    "channel": self.channel,
                    "author": author,
                    "kwargs": {"profile": self.profile},
                },
            )()
            if not await self.cog.is_support.__func__(ignore_owner=True).predicate(fake_context):
                raise RuntimeError(_("You aren't allowed to add members to this ticket!"))
        if member.id in self.members_ids:
            raise RuntimeError(_("This member is already in the ticket."))
        config = await self.cog.config.guild(self.guild).profiles.get_raw(self.profile)
        if (
            member == self.owner
            or any(
                member.get_role(support_role_id) is not None
                for support_role_id in config["support_roles"]
            )
            or member.guild_permissions.administrator
        ):
            raise RuntimeError(
                _(
                    "This member has a role that allows them to access the ticket without being added manually."
                )
            )
        self.members_ids.append(member.id)
        await self.save()

        if author is None:
            audit_reason = _(
                "Member added to the ticket: {member.display_name} ({member.id})"
            ).format(member=member)
        else:
            audit_reason = _(
                "Member added to the ticket by {author.display_name} ({author.id}): {member.display_name} ({member.id})"
            ).format(author=author, member=member)
        if isinstance(self.channel, discord.Thread):
            await self.channel.add_user(member)
        else:
            await self.channel.set_permissions(
                member,
                read_messages=True,
                read_message_history=True,
                send_messages=True,
                add_reactions=True,
                embed_links=True,
                attach_files=True,
                reason=audit_reason,
            )

        self.bot.dispatch("ticket_member_added", self)
        await self.log_action(
            action=_("➕ Member Added"),
            author=author,
            target=member,
        )
        if config["create_modlog_case"]:
            await modlog.create_case(
                bot=self.bot,
                guild=self.guild,
                created_at=datetime.datetime.now(tz=datetime.timezone.utc),
                action_type="ticket_member_added",
                user=member,
                moderator=author,
                channel=self.channel,
            )

    async def remove_member(
        self, member: discord.Member, author: typing.Optional[discord.Member] = None
    ) -> None:
        config = await self.cog.config.guild(self.guild).profiles.get_raw(self.profile)
        if author is not None and not config["owner_can_remove_members"]:
            fake_context = type(
                "FakeContext",
                (),
                {
                    "bot": self.bot,
                    "guild": self.guild,
                    "channel": self.channel,
                    "author": author,
                    "kwargs": {"profile": self.profile},
                },
            )()
            if not await self.cog.is_support.__func__(ignore_owner=True).predicate(fake_context):
                raise RuntimeError(_("You aren't allowed to remove members from this ticket!"))
        if member.id not in self.members_ids:
            raise RuntimeError(_("This member is not in the ticket."))
        self.members_ids.remove(member.id)
        await self.save()

        if author is None:
            audit_reason = _(
                "Member removed from the ticket: {member.display_name} ({member.id})"
            ).format(member=member)
        else:
            audit_reason = _(
                "Member removed from the ticket by {author.display_name} ({author.id}): {member.display_name} ({member.id})"
            ).format(author=author, member=member)
        if isinstance(self.channel, discord.Thread):
            await self.channel.remove_user(member)
        else:
            await self.channel.set_permissions(
                member,
                overwrite=None,
                reason=audit_reason,
            )

        self.bot.dispatch("ticket_member_removed", self)
        await self.log_action(
            action=_("➖ Member Removed"),
            author=author,
            target=member,
        )
        if config["create_modlog_case"]:
            await modlog.create_case(
                bot=self.bot,
                guild=self.guild,
                created_at=datetime.datetime.now(tz=datetime.timezone.utc),
                action_type="ticket_member_removed",
                user=member,
                moderator=author,
                channel=self.channel,
            )

    async def log_action(
        self,
        action: str,
        author: typing.Optional[discord.Member] = None,
        target: typing.Optional[discord.Member] = None,
        reason: typing.Optional[str] = None,
    ) -> None:
        embed = discord.Embed(
            description=bold(
                _("{action} by {author.mention}").format(action=action, author=author)
            ),
            color=await self.bot.get_embed_color(self.channel),
            timestamp=datetime.datetime.now(tz=datetime.timezone.utc),
        )
        if target is not None:
            embed.add_field(
                name=_("Target:"),
                value=f"{target.mention} ({target.id})",
                inline=False,
            )
        if reason is not None:
            embed.add_field(
                name=_("Reason:"),
                value=f">>> {reason}",
                inline=False,
            )
        await self.channel.send(embed=embed)

    async def export(self) -> discord.File:
        class Transcript(chat_exporter.construct.transcript.TranscriptDAO):
            @classmethod
            async def export(
                cls,
                channel: typing.Union[discord.TextChannel, discord.VoiceChannel, discord.Thread],
                messages: typing.List[discord.Message],
                tz_info="UTC",
                guild: typing.Optional[discord.Guild] = None,
                bot: typing.Optional[discord.Client] = None,
                military_time: typing.Optional[bool] = False,
                fancy_times: typing.Optional[bool] = True,
                support_dev: typing.Optional[bool] = True,
                attachment_handler: typing.Optional[typing.Any] = None,
            ):
                if guild:
                    channel.guild = guild
                self = cls(
                    channel=channel,
                    limit=None,
                    messages=messages,
                    pytz_timezone=tz_info,
                    military_time=military_time,
                    fancy_times=fancy_times,
                    before=None,
                    after=None,
                    support_dev=support_dev,
                    bot=bot,
                    attachment_handler=attachment_handler,
                )
                if not self.after:
                    self.messages.reverse()
                return (await self.build_transcript()).html

        class AttachmentHandler(chat_exporter.AttachmentHandler):
            async def process_asset(self, attachment: discord.Attachment) -> discord.Attachment:
                # encoded = base64.b64encode(await attachment.read()).decode()
                # attachment.url = f"data:{attachment.content_type};base64,{encoded}"
                # attachment.proxy_url = attachment.url
                return attachment

        transcript = await Transcript.export(
            channel=self.channel,
            messages=[message async for message in self.channel.history(limit=None)],
            tz_info="UTC",
            guild=self.guild,
            bot=self.bot,
            attachment_handler=AttachmentHandler(),
        )
        return discord.File(
            filename=f"ticket-{self.id}-{self.owner.name}.html",
            fp=io.BytesIO(transcript.encode()),
        )

    async def delete_channel(self, deleter: typing.Optional[discord.Member] = None) -> None:
        if deleter is None:
            audit_reason = _("Ticket deleted (profile `{self.profile}`)").format(self=self)
        else:
            audit_reason = _(
                "Ticket deleted by {deleter.display_name} ({deleter.id}) (profile `{self.profile}`)"
            ).format(deleter=deleter, self=self)
        if isinstance(self.channel, discord.Thread):
            await self.channel.delete(reason=audit_reason)
        else:
            await self.channel.delete(reason=audit_reason)

        config = await self.cog.config.guild(self.guild).profiles.get_raw(self.profile)
        if (
            logs_channel_id := await self.cog.config.guild(self.guild).profiles.get_raw(
                self.profile, "logs_channel"
            )
        ) and (logs_channel := self.guild.get_channel(logs_channel_id)) is not None:
            await logs_channel.send(
                embeds=[
                    discord.Embed(
                        title=_("🗑 Ticket Deleted"),
                        description=_("{self.owner.mention}'s ticket has been deleted.").format(
                            self=self
                        ),
                        color=discord.Color.red(),
                        timestamp=datetime.datetime.now(tz=datetime.timezone.utc),
                    ),
                    await self.get_embed(for_logging=True),
                ],
                file=await self.export() if config["transcripts"] else None,
            )

        self.bot.dispatch("ticket_deleted", self)
        if config["create_modlog_case"]:
            await modlog.create_case(
                bot=self.bot,
                guild=self.guild,
                created_at=datetime.datetime.now(tz=datetime.timezone.utc),
                action_type="ticket_deleted",
                user=self.owner,
                moderator=deleter,
                channel=self.channel,
            )
        await self.delete()

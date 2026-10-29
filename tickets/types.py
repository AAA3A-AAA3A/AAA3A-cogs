import asyncio
import copy
import datetime
import functools
import io
import typing
from dataclasses import _is_dataclass_instance, dataclass, field, fields

import chat_exporter
import discord

from redbot.core import commands, modlog
from redbot.core.bot import Red
from redbot.core.i18n import Translator
from redbot.core.utils.chat_formatting import bold, box, humanize_list

from .views import ClosedTicketControls, TicketView

_: Translator = Translator("Tickets", __file__)


def get_non_animated_asset(
    asset: discord.Asset | None = None,
) -> discord.Asset | None:
    if asset is None:
        return None
    if not asset.is_animated():
        return asset
    return discord.Asset(
        asset._state,
        url=asset.url.replace("/a_", "/").replace(".gif", ".png"),
        key=asset.key.removeprefix("a_"),
        animated=False,
    )


def _asdict_inner(obj, dict_factory=dict):
    if _is_dataclass_instance(obj):
        result = []
        for f in fields(obj):
            if isinstance(getattr(obj, f.name), (Red, commands.Cog)):
                continue
            value = _asdict_inner(getattr(obj, f.name), dict_factory)
            result.append((f.name, value))
        return dict_factory(result)
    if isinstance(obj, tuple) and hasattr(obj, "_fields"):
        return type(obj)(*[_asdict_inner(v, dict_factory) for v in obj])
    if isinstance(obj, (list, tuple)):
        return type(obj)(_asdict_inner(v, dict_factory) for v in obj)
    if isinstance(obj, dict):
        return type(obj)(
            (_asdict_inner(k, dict_factory), _asdict_inner(v, dict_factory)) for k, v in obj.items()
        )
    return copy.deepcopy(obj)


def merge_dicts(
    defaults: dict[str, typing.Any],
    data: dict[str, typing.Any],
) -> dict[str, typing.Any]:
    result = copy.deepcopy(defaults)
    for key, value in data.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = merge_dicts(result[key], value)
        else:
            result[key] = value
    return result


def with_ticket_lock(func: typing.Callable) -> typing.Callable:
    @functools.wraps(func)
    async def wrapper(self, *args, **kwargs) -> typing.Any:
        if self._lock_task is asyncio.current_task():  # `close` calls `delete_channel`.
            return await func(self, *args, **kwargs)
        async with self._lock:
            self._lock_task = asyncio.current_task()
            try:
                return await func(self, *args, **kwargs)
            finally:
                self._lock_task = None

    return wrapper


@dataclass
class Ticket:
    bot: Red
    cog: commands.Cog

    guild_id: int
    id: int

    owner_id: int
    channel_id: int = None
    message_id: int = None

    profile: str | None = "main"
    reason: str | None = None
    category_label: str | None = None
    owner_answers: dict[str, str] = field(default_factory=dict)

    opened_at_timestamp: int = field(
        default_factory=lambda: int(
            datetime.datetime.now(tz=datetime.timezone.utc)
            .replace(second=0, microsecond=0)
            .timestamp(),
        ),
    )
    is_claimed: bool = False
    claimed_by_id: int | None = None
    claimed_at_timestamp: int = None
    is_closed: bool = False
    closed_by_id: int | None = None
    closed_at_timestamp: int = None
    reopened_by_id: int | None = None
    reopened_at_timestamp: int = None
    is_locked: bool = False
    locked_by_id: int | None = None
    locked_at_timestamp: int = None
    unlocked_by_id: int | None = None
    unlocked_at_timestamp: int = None
    appeal_approved: bool = False
    appeal_approved_by_id: int | None = None
    appeal_approved_at_timestamp: int = None
    deleted_by_id: int | None = None
    deleted_at_timestamp: int = None

    members_ids: list[int] = field(default_factory=list)

    def __post_init__(self) -> None:
        self._channel: discord.TextChannel | discord.VoiceChannel | discord.Thread | None = None
        self._lock: asyncio.Lock = asyncio.Lock()
        self._lock_task: asyncio.Task | None = None

    def to_dict(self) -> dict[str, typing.Any]:
        return _asdict_inner(self)

    def restore(self, data: dict[str, typing.Any]) -> None:
        for key, value in data.items():
            setattr(self, key, value)

    async def save(self) -> None:
        await self.cog.config.guild_from_id(self.guild_id).tickets.set_raw(
            str(self.id),
            value=self.to_dict(),
        )
        self.cog.tickets.setdefault(self.guild_id, {})[self.id] = self

    async def get_config(self) -> dict[str, typing.Any]:
        profiles = self.cog.config.guild_from_id(self.guild_id).profiles
        try:
            config = await profiles.get_raw(self.profile)
        except KeyError:
            if (self.guild_id, self.id) not in self.cog.missing_profile_warnings:
                self.cog.missing_profile_warnings.add((self.guild_id, self.id))
                self.cog.logger.warning(
                    f"The profile `{self.profile}` of the ticket #{self.id} in the guild {self.guild_id} doesn't exist anymore. The `main` profile settings will be used instead.",
                )
            config = await profiles.get_raw("main")
        return merge_dicts(self.cog.default_profile_settings, config)

    async def resolve_channel(
        self,
    ) -> discord.TextChannel | discord.VoiceChannel | discord.Thread | None:
        if (channel := self.channel) is not None:
            return channel
        if (guild := self.guild) is None or self.channel_id is None:
            return None
        try:
            self._channel = await guild.fetch_channel(self.channel_id)
        except discord.NotFound:
            self._channel = None
            raise
        return self._channel

    async def fetch_channel(self) -> discord.TextChannel | discord.VoiceChannel | discord.Thread:
        try:
            channel = await self.resolve_channel()
        except discord.HTTPException:
            channel = None
        if channel is None:
            raise RuntimeError(_("I can't find the channel of this ticket."))
        return channel

    def get_view(self) -> TicketView:
        if (view := self.cog.views.get(self.message)) is None or view.is_finished():
            view = TicketView(cog=self.cog, ticket=self)
            view._message = self.message
            self.cog.views[self.message] = view
        view.ticket = self
        return view

    async def edit_channel(self, old_state: dict[str, typing.Any], **kwargs) -> None:
        try:
            channel = await self.channel.edit(**kwargs)
        except discord.HTTPException as e:
            self.restore(old_state)
            raise RuntimeError(
                _("I couldn't edit the channel of this ticket.\n{error}").format(
                    error=box(str(e), lang="py"),
                ),
            )
        if isinstance(channel, discord.Thread):
            self._channel = channel

    async def set_send_messages(
        self,
        old_state: dict[str, typing.Any],
        send_messages: bool,
        reason: str,
    ) -> None:
        try:
            for member in [self.owner, *self.members]:
                if member is None:
                    continue
                # Keep the other permissions of the overwrite (`read_messages`...).
                overwrite = self.channel.overwrites_for(member)
                overwrite.send_messages = send_messages
                await self.channel.set_permissions(member, overwrite=overwrite, reason=reason)
        except discord.HTTPException as e:
            self.restore(old_state)
            raise RuntimeError(
                _("I couldn't edit the permissions of this ticket.\n{error}").format(
                    error=box(str(e), lang="py"),
                ),
            )

    async def delete(self) -> None:
        try:
            del self.cog.tickets[self.guild_id][self.id]
        except KeyError:
            pass
        else:
            if not self.cog.tickets[self.guild_id]:
                del self.cog.tickets[self.guild_id]
        await self.cog.config.guild_from_id(self.guild_id).tickets.clear_raw(str(self.id))
        if self.message in self.cog.views:
            self.cog.views.pop(self.message).stop()

    @property
    def guild(self) -> discord.Guild:
        return self.bot.get_guild(self.guild_id)

    @guild.setter
    def guild(self, guild: discord.Guild) -> None:
        self.guild_id = guild.id

    @property
    def owner(self) -> discord.Member | None:
        if (guild := self.guild) is None:
            return None
        return guild.get_member(self.owner_id)

    @owner.setter
    def owner(self, owner: discord.Member) -> None:
        self.owner_id = owner.id

    @property
    def channel(
        self,
    ) -> discord.TextChannel | discord.VoiceChannel | discord.Thread | None:
        if (guild := self.guild) is None:
            return None
        if (channel := guild.get_channel_or_thread(self.channel_id)) is not None:
            return channel
        if self._channel is not None and self._channel.id == self.channel_id:
            return self._channel
        return None

    @channel.setter
    def channel(
        self,
        channel: discord.TextChannel | discord.VoiceChannel | discord.Thread,
    ) -> None:
        self.guild_id = channel.guild.id
        self.channel_id = channel.id
        self._channel = channel

    @property
    def message(self) -> discord.PartialMessage | None:
        if self.channel_id is None or self.message_id is None:
            return None
        if (channel := self.channel) is not None:
            return channel.get_partial_message(self.message_id)
        return self.bot.get_partial_messageable(
            self.channel_id,
            guild_id=self.guild_id,
        ).get_partial_message(self.message_id)

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
    def claimed_by(self) -> discord.Member | None:
        if (guild := self.guild) is None:
            return None
        return guild.get_member(self.claimed_by_id)

    @claimed_by.setter
    def claimed_by(self, claimed_by: discord.Member | None) -> None:
        if claimed_by is None:
            self.claimed_by_id = None
        else:
            self.claimed_by_id = claimed_by.id

    @property
    def claimed_at(self) -> datetime.datetime | None:
        if self.claimed_at_timestamp is None:
            return None
        return datetime.datetime.fromtimestamp(self.claimed_at_timestamp, tz=datetime.timezone.utc)

    @claimed_at.setter
    def claimed_at(self, claimed_at: datetime.datetime | None) -> None:
        self.claimed_at_timestamp = None if claimed_at is None else int(claimed_at.timestamp())

    @property
    def closed_by(self) -> discord.Member | None:
        if (guild := self.guild) is None:
            return None
        return guild.get_member(self.closed_by_id)

    @closed_by.setter
    def closed_by(self, closed_by: discord.Member | None) -> None:
        if closed_by is None:
            self.closed_by_id = None
        else:
            self.closed_by_id = closed_by.id

    @property
    def closed_at(self) -> datetime.datetime | None:
        if self.closed_at_timestamp is None:
            return None
        return datetime.datetime.fromtimestamp(self.closed_at_timestamp, tz=datetime.timezone.utc)

    @closed_at.setter
    def closed_at(self, closed_at: datetime.datetime | None) -> None:
        self.closed_at_timestamp = None if closed_at is None else int(closed_at.timestamp())

    @property
    def reopened_by(self) -> discord.Member | None:
        if (guild := self.guild) is None:
            return None
        return guild.get_member(self.reopened_by_id)

    @reopened_by.setter
    def reopened_by(self, reopened_by: discord.Member | None) -> None:
        if reopened_by is None:
            self.reopened_by_id = None
        else:
            self.reopened_by_id = reopened_by.id

    @property
    def locked_by(self) -> discord.Member | None:
        if (guild := self.guild) is None:
            return None
        return guild.get_member(self.locked_by_id)

    @locked_by.setter
    def locked_by(self, locked_by: discord.Member | None) -> None:
        if locked_by is None:
            self.locked_by_id = None
        else:
            self.locked_by_id = locked_by.id

    @property
    def locked_at(self) -> datetime.datetime | None:
        if self.locked_at_timestamp is None:
            return None
        return datetime.datetime.fromtimestamp(self.locked_at_timestamp, tz=datetime.timezone.utc)

    @locked_at.setter
    def locked_at(self, locked_at: datetime.datetime | None) -> None:
        self.locked_at_timestamp = None if locked_at is None else int(locked_at.timestamp())

    @property
    def unlocked_by(self) -> discord.Member | None:
        if (guild := self.guild) is None:
            return None
        return guild.get_member(self.unlocked_by_id)

    @unlocked_by.setter
    def unlocked_by(self, unlocked_by: discord.Member | None) -> None:
        if unlocked_by is None:
            self.unlocked_by_id = None
        else:
            self.unlocked_by_id = unlocked_by.id

    @property
    def unlocked_at(self) -> datetime.datetime | None:
        if self.unlocked_at_timestamp is None:
            return None
        return datetime.datetime.fromtimestamp(self.unlocked_at_timestamp, tz=datetime.timezone.utc)

    @unlocked_at.setter
    def unlocked_at(self, unlocked_at: datetime.datetime | None) -> None:
        self.unlocked_at_timestamp = None if unlocked_at is None else int(unlocked_at.timestamp())

    @property
    def appeal_approved_by(self) -> discord.Member | None:
        if (guild := self.guild) is None:
            return None
        return guild.get_member(self.appeal_approved_by_id)

    @appeal_approved_by.setter
    def appeal_approved_by(self, appeal_approved_by: discord.Member | None) -> None:
        if appeal_approved_by is None:
            self.appeal_approved_by_id = None
        else:
            self.appeal_approved_by_id = appeal_approved_by.id

    @property
    def appeal_approved_at(self) -> datetime.datetime | None:
        if self.appeal_approved_at_timestamp is None:
            return None
        return datetime.datetime.fromtimestamp(
            self.appeal_approved_at_timestamp,
            tz=datetime.timezone.utc,
        )

    @appeal_approved_at.setter
    def appeal_approved_at(self, appeal_approved_at: datetime.datetime | None) -> None:
        self.appeal_approved_at_timestamp = (
            None if appeal_approved_at is None else int(appeal_approved_at.timestamp())
        )

    @property
    def deleted_by(self) -> discord.Member | None:
        if (guild := self.guild) is None:
            return None
        return guild.get_member(self.deleted_by_id)

    @deleted_by.setter
    def deleted_by(self, deleted_by: discord.Member | None) -> None:
        if deleted_by is None:
            self.deleted_by_id = None
        else:
            self.deleted_by_id = deleted_by.id

    @property
    def deleted_at(self) -> datetime.datetime | None:
        if self.deleted_at_timestamp is None:
            return None
        return datetime.datetime.fromtimestamp(self.deleted_at_timestamp, tz=datetime.timezone.utc)

    @deleted_at.setter
    def deleted_at(self, deleted_at: datetime.datetime | None) -> None:
        self.deleted_at_timestamp = None if deleted_at is None else int(deleted_at.timestamp())

    @property
    def members(self) -> list[discord.Member]:
        if (guild := self.guild) is None:
            return []
        return [
            member
            for member_id in self.members_ids
            if (member := guild.get_member(member_id)) is not None
        ]

    @members.setter
    def members(self, members: list[discord.Member]) -> None:
        self.members_ids = [member.id for member in members]

    @property
    def emoji(self) -> str:
        if self.appeal_approved:
            return "🛡️"
        return "🔒" if self.is_closed else ("👥" if self.is_claimed else "❓")

    async def channel_name(self, forum_channel: bool | None = None) -> str:
        channel_name = (await self.get_config())["channel_name"]
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
                    "{profile}",
                    "ticket" if self.profile == "main" else self.profile,
                )

        owner = self.owner if self.owner is not None else await self.bot.fetch_user(self.owner_id)
        return channel_name.format(
            id=self.id,
            emoji=self.emoji,
            owner_display_name=owner.display_name,
            owner_name=owner.name,
            owner_mention=owner.mention,
            owner_id=owner.id,
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
            embed.set_thumbnail(url=get_non_animated_asset(self.owner.display_avatar))
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
        embed.description = (
            (
                _(
                    "Claimed by: {claimed_by.mention}\nClaimed at: {claimed_at}",
                ).format(
                    claimed_by=(
                        self.claimed_by
                        if self.claimed_by is not None
                        else type(
                            "",
                            (),
                            {
                                "mention": f"<@{self.appeal_approved_by_id}>"
                                if self.appeal_approved_by_id
                                else _("Automatic"),
                            },
                        )
                    ),
                    claimed_at=f"{discord.utils.format_dt(self.claimed_at, style='F')} ({discord.utils.format_dt(self.claimed_at, style='R')})",
                )
                if self.is_claimed
                else _("Not claimed.")
            )
            + (
                _(
                    "\nClosed by: {closed_by.mention}\nClosed at: {closed_at}",
                ).format(
                    closed_by=(
                        self.closed_by
                        if self.closed_by is not None
                        else type(
                            "",
                            (),
                            {
                                "mention": f"<@{self.appeal_approved_by_id}>"
                                if self.appeal_approved_by_id
                                else _("Automatic"),
                            },
                        )
                    ),
                    closed_at=f"{discord.utils.format_dt(self.closed_at, style='F')} ({discord.utils.format_dt(self.closed_at, style='R')})",
                )
                if self.is_closed
                else ""
            )
            + (
                _(
                    "\nAppeal approved by: {appeal_approved_by.mention}"
                    "\nAppeal approved at: {appeal_approved_at}",
                ).format(
                    appeal_approved_by=(
                        self.appeal_approved_by
                        if self.appeal_approved_by is not None
                        else type(
                            "",
                            (),
                            {
                                "mention": f"<@{self.appeal_approved_by_id}>"
                                if self.appeal_approved_by_id
                                else _("Automatic"),
                            },
                        )
                    ),
                    appeal_approved_at=f"{discord.utils.format_dt(self.appeal_approved_at, style='F')} ({discord.utils.format_dt(self.appeal_approved_at, style='R')})",
                )
                if self.appeal_approved
                else ""
            )
            + (
                _(
                    "\nDeleted by: {deleted_by.mention}\nDeleted at: {deleted_at}",
                ).format(
                    deleted_by=(
                        self.deleted_by
                        if self.deleted_by is not None
                        else type(
                            "",
                            (),
                            {
                                "mention": f"<@{self.deleted_by_id}>"
                                if self.deleted_by_id
                                else _("Automatic"),
                            },
                        )
                    ),
                    deleted_at=f"{discord.utils.format_dt(self.deleted_at, style='F')} ({discord.utils.format_dt(self.deleted_at, style='R')})",
                )
                if self.deleted_at is not None
                else ""
            )
        )
        if self.reason is not None:
            embed.add_field(
                name=_("Reason:"),
                value=f">>> {self.reason}",
                inline=False,
            )
        embed.set_footer(
            text=f"{self.guild.name} | " + _("Opened at:"),
            icon_url=get_non_animated_asset(self.guild.icon),
        )
        embed.timestamp = self.opened_at
        return embed

    async def get_embeds(self) -> list[discord.Embed]:
        embeds = [await self.get_embed()]
        config = await self.get_config()
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
            owner = (
                self.owner if self.owner is not None else await self.bot.fetch_user(self.owner_id)
            )
            embeds.append(
                discord.Embed(
                    description=config["custom_message"].format(
                        id=self.id,
                        emoji=self.emoji,
                        owner_display_name=owner.display_name,
                        owner_name=owner.name,
                        owner_mention=owner.mention,
                        owner_id=owner.id,
                        guild_name=self.guild.name,
                        guild_id=self.guild.id,
                    ),
                    color=await self.bot.get_embed_color(self.guild.channels[0]),
                ),
            )
        return embeds

    async def get_kwargs(
        self,
    ) -> dict[
        typing.Literal["content", "embeds", "view", "allowed_mentions"],
        str | discord.Embed | discord.ui.View,
    ]:
        config = await self.get_config()
        content = (
            f"[ {humanize_list([ping_role.mention for ping_role in ping_roles])} ]\n\n"
            if any(
                ping_roles := [
                    ping_role
                    for ping_role_id in config["ping_roles"]
                    if (ping_role := self.guild.get_role(ping_role_id)) is not None
                ],
            )
            else ""
        )
        if self.owner is not None:
            content += config.get("welcome_message", "Welcome {owner_mention}! 👋").format(
                id=self.id,
                emoji=self.emoji,
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

    async def create(self) -> discord.TextChannel | discord.Thread:
        config: dict[str, typing.Any] = await self.get_config()
        if not config["enabled"]:
            raise RuntimeError(_("The creation of tickets is disabled for this profile."))
        forum_channel = (
            self.guild.get_channel(forum_channel_id)
            if (forum_channel_id := config["forum_channel"]) is not None
            else None
        )
        category_open = (
            self.guild.get_channel(category_open_id)
            if (category_open_id := config["category_open"]) is not None
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
                    ],
                )
                >= config["max_open_tickets_by_member"]
            ):
                raise RuntimeError(
                    _("You have reached the maximum number of open tickets for this profile."),
                )
            if (
                config.get("appeals", {"enabled": False})["enabled"]
                and (appeals_for_guild := self.bot.get_guild(config["appeals"]["guild_id"]))
                is not None
            ):
                try:
                    await appeals_for_guild.fetch_ban(self.owner)
                except discord.NotFound:
                    raise RuntimeError(
                        _("You are not banned from the server, so you can't create a ticket."),
                    )
                except discord.HTTPException:
                    pass

        if not self.id:
            self.id = await self.cog.get_ticket_id(self.guild)
        audit_reason = _(
            "Ticket creation for {ticket.owner.display_name} ({ticket.owner.id}) (profile `{ticket.profile}`).",
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
                        "I don't have the required permissions to create private threads in the forum/text channel configured.",
                    ),
                )
            if isinstance(forum_channel, discord.ForumChannel):
                applied_tags = [
                    tag
                    for tag_id in config["forum_tags"]
                    if (tag := forum_channel.get_tag(tag_id)) is not None
                ]
                thread_message = await forum_channel.create_thread(
                    name=await self.channel_name(forum_channel=True),
                    auto_archive_duration=10080,
                    applied_tags=applied_tags,
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
                try:
                    await self.channel.add_user(self.owner)
                except discord.HTTPException:
                    pass
                view._message = await self.channel.send(**kwargs)
        else:
            if not category_open.permissions_for(self.guild.me).manage_channels:
                raise RuntimeError(
                    _(
                        "I don't have the required permissions to create text channels in the category configured.",
                    ),
                )
            self.channel = await self.guild.create_text_channel(
                name=await self.channel_name(forum_channel=False),
                category=category_open,
                overwrites=await self.get_channel_overwrites(),
                reason=audit_reason,
            )
            view._message = await self.channel.send(**kwargs)
        self.cog.views[view._message] = view
        try:
            await view._message.pin()
        except discord.HTTPException:
            pass
        self.message = view._message
        tickets_number = await self.cog.config.member(self.owner).tickets_number()
        await self.cog.config.member(self.owner).tickets_number.set(tickets_number + 1)
        await self.save()

        self.bot.dispatch("ticket_create", self)
        if config["create_modlog_case"]:
            await modlog.create_case(
                bot=self.bot,
                guild=self.guild,
                created_at=self.opened_at,
                action_type="ticket_created",
                user=self.owner or self.owner_id,
                moderator=self.guild.me,
                channel=self.channel,
            )
        await self.cog.send_ticket_log(self)

        return view._message

    async def get_channel_overwrites(
        self,
    ) -> dict[discord.Member | discord.Role, discord.PermissionOverwrite]:
        config: dict[str, typing.Any] = await self.get_config()
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
        }
        if self.owner is not None:
            overwrites[self.owner] = discord.PermissionOverwrite(
                read_messages=True,
                read_message_history=True,
                send_messages=not self.is_closed,
                add_reactions=not self.is_closed,
                embed_links=not self.is_closed,
                attach_files=not self.is_closed,
            )
        for support_role_id in config["support_roles"]:
            if (support_role := self.guild.get_role(support_role_id)) is not None:
                overwrites[support_role] = discord.PermissionOverwrite(
                    read_messages=True,
                    read_message_history=True,
                    send_messages=not self.is_closed,
                    add_reactions=not self.is_closed,
                    embed_links=not self.is_closed,
                    attach_files=not self.is_closed,
                )
        for speak_role_id in config.get("speak_roles", []):
            if (speak_role := self.guild.get_role(speak_role_id)) is not None:
                overwrites[speak_role] = discord.PermissionOverwrite(
                    read_messages=True,
                    read_message_history=True,
                    send_messages=not self.is_closed,
                    add_reactions=not self.is_closed,
                    embed_links=not self.is_closed,
                    attach_files=not self.is_closed,
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
        for member_id in self.members_ids:
            if (member := self.guild.get_member(member_id)) is not None:
                overwrites[member] = discord.PermissionOverwrite(
                    read_messages=True,
                    read_message_history=True,
                    send_messages=not self.is_closed,
                    add_reactions=not self.is_closed,
                    embed_links=not self.is_closed,
                    attach_files=not self.is_closed,
                )
        return overwrites

    @with_ticket_lock
    async def close(
        self,
        closer: discord.Member | None = None,
        reason: str | None = None,
    ) -> None:
        if self.is_closed:
            raise RuntimeError(_("This ticket is already closed."))
        await self.fetch_channel()
        config = await self.get_config()
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
        old_state = self.to_dict()
        self.is_closed = True
        # self.reopened_by = None
        # self.reopened_at = None
        self.closed_by = closer
        self.closed_at = datetime.datetime.now(tz=datetime.timezone.utc)

        if closer is None:
            audit_reason = _("Ticket closed (profile `{self.profile}`).").format(self=self)
        else:
            audit_reason = _(
                "Ticket closed by {closer.display_name} ({closer.id}) (profile `{self.profile}`).",
            ).format(closer=closer, self=self)
        if isinstance(self.channel, discord.Thread):
            if (name := await self.channel_name()) != self.channel.name:
                await self.edit_channel(old_state, name=name, reason=audit_reason)
        else:
            await self.edit_channel(
                old_state,
                name=await self.channel_name(),
                category=(
                    category_closed
                    if (
                        (category_closed_id := config["category_closed"]) is not None
                        and (category_closed := self.guild.get_channel(category_closed_id))
                        is not None
                    )
                    else self.channel.category
                ),
                overwrites=await self.get_channel_overwrites(),
                reason=audit_reason,
            )
        await self.save()

        await self.log_action(
            action=_("❌ Ticket Closed"),
            author=closer,
            reason=reason,
        )
        view = self.get_view()
        await view._update()
        await self.message.edit(
            embeds=await self.get_embeds(),
            view=view,
        )
        view: ClosedTicketControls = ClosedTicketControls(cog=self.cog)
        await view.start(self)
        if isinstance(self.channel, discord.Thread):
            try:
                self._channel = await self.channel.edit(
                    archived=True,
                    locked=True,
                    reason=audit_reason,
                )
            except discord.HTTPException as e:
                self.cog.logger.error(
                    f"Error when archiving the thread of the ticket #{self.id} in the guild {self.guild_id}.",
                    exc_info=e,
                )

        self.bot.dispatch("ticket_close", self)
        if config["create_modlog_case"]:
            await modlog.create_case(
                bot=self.bot,
                guild=self.guild,
                created_at=self.closed_at,
                action_type="ticket_closed",
                user=self.owner or self.owner_id,
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

    @with_ticket_lock
    async def reopen(
        self,
        reopener: discord.Member | None = None,
        reason: str | None = None,
    ) -> None:
        if not self.is_closed:
            raise RuntimeError(_("This ticket is not closed."))
        await self.fetch_channel()
        config = await self.get_config()
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
        old_state = self.to_dict()
        self.is_closed = False
        # self.closed_by = None
        # self.closed_at = None
        self.reopened_by = reopener
        self.reopened_at = datetime.datetime.now(tz=datetime.timezone.utc)

        if reopener is None:
            audit_reason = _("Ticket reopened (profile `{self.profile}.`)").format(self=self)
        else:
            audit_reason = _(
                "Ticket reopened by {reopener.display_name} ({reopener.id}) (profile `{self.profile}`).",
            ).format(reopener=reopener, self=self)
        if isinstance(self.channel, discord.Thread):
            await self.edit_channel(
                old_state,
                name=await self.channel_name(),
                archived=False,
                locked=False,
                reason=audit_reason,
            )
        else:
            await self.edit_channel(
                old_state,
                name=await self.channel_name(),
                category=(
                    category_open
                    if (
                        (category_open_id := config["category_open"]) is not None
                        and (category_open := self.guild.get_channel(category_open_id)) is not None
                    )
                    else self.channel.category
                ),
                overwrites=await self.get_channel_overwrites(),
                reason=audit_reason,
            )
        await self.save()

        view = self.get_view()
        await view._update()
        await self.message.edit(
            embeds=await self.get_embeds(),
            view=view,
        )

        self.bot.dispatch("ticket_reopen", self)
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
                user=self.owner or self.owner_id,
                moderator=reopener,
                reason=reason,
                channel=self.channel,
            )
        await self.cog.send_ticket_log(self)

    @with_ticket_lock
    async def claim(self, claimer: discord.Member) -> None:
        if self.is_claimed:
            raise RuntimeError(_("This ticket is already claimed."))
        await self.fetch_channel()
        old_state = self.to_dict()
        self.is_claimed = True
        self.claimed_by = claimer
        self.claimed_at = datetime.datetime.now(tz=datetime.timezone.utc)

        audit_reason = _(
            "Ticket claimed by {claimer.display_name} ({claimer.id}) (profile `{self.profile}`).",
        ).format(claimer=claimer, self=self)
        await self.edit_channel(
            old_state,
            name=await self.channel_name(),
            reason=audit_reason,
        )
        await self.save()

        view = self.get_view()
        await view._update()
        await self.message.edit(
            embeds=await self.get_embeds(),
            view=view,
        )

        self.bot.dispatch("ticket_claimed", self)
        config = await self.get_config()
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
                user=self.owner or self.owner_id,
                moderator=claimer,
                channel=self.channel,
            )
        await self.cog.send_ticket_log(self)

    @with_ticket_lock
    async def unclaim(self, unclaimer: discord.Member | None = None) -> None:
        if not self.is_claimed:
            raise RuntimeError(_("This ticket is not claimed."))
        await self.fetch_channel()
        old_state = self.to_dict()
        self.is_claimed = False
        # self.claimed_by = None
        # self.claimed_at = None

        if unclaimer is None:
            audit_reason = _("Ticket unclaimed (profile `{self.profile}`).").format(self=self)
        else:
            audit_reason = _(
                "Ticket unclaimed by {unclaimer.display_name} ({unclaimer.id}) (profile `{self.profile}`).",
            ).format(unclaimer=unclaimer, self=self)
        await self.edit_channel(
            old_state,
            name=await self.channel_name(),
            reason=audit_reason,
        )
        await self.save()

        view = self.get_view()
        await view._update()
        await self.message.edit(
            embeds=await self.get_embeds(),
            view=view,
        )

        self.bot.dispatch("ticket_unclaim", self)
        config = await self.get_config()
        await self.log_action(
            action=_("👤 Ticket Unclaimed"),
            author=unclaimer,
        )
        if config["create_modlog_case"]:
            await modlog.create_case(
                bot=self.bot,
                guild=self.guild,
                created_at=datetime.datetime.now(tz=datetime.timezone.utc),
                action_type="ticket_unclaimed",
                user=self.owner or self.owner_id,
                moderator=unclaimer or self.guild.me,
                channel=self.channel,
            )
        await self.cog.send_ticket_log(self)

    @with_ticket_lock
    async def lock(self, locker: discord.Member | None = None) -> None:
        if self.is_locked:
            raise RuntimeError(_("This ticket is already locked."))
        await self.fetch_channel()
        config = await self.get_config()
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
        old_state = self.to_dict()
        self.is_locked = True
        self.locked_by = locker
        self.locked_at = datetime.datetime.now(tz=datetime.timezone.utc)

        if locker is None:
            audit_reason = _("Ticket locked (profile `{self.profile}`).").format(self=self)
        else:
            audit_reason = _(
                "Ticket locked by {locker.display_name} ({locker.id}) (profile `{self.profile}`).",
            ).format(locker=locker, self=self)
        if isinstance(self.channel, discord.Thread):
            await self.edit_channel(old_state, locked=True, reason=audit_reason)
        else:
            await self.set_send_messages(old_state, False, reason=audit_reason)
        await self.save()

        view = self.get_view()
        await view._update()
        await self.message.edit(
            embeds=await self.get_embeds(),
            view=view,
        )

        self.bot.dispatch("ticket_lock", self)
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
                user=self.owner or self.owner_id,
                moderator=locker,
                channel=self.channel,
            )

    @with_ticket_lock
    async def unlock(self, unlocker: discord.Member | None = None) -> None:
        if not self.is_locked:
            raise RuntimeError(_("This ticket is not locked."))
        await self.fetch_channel()
        config = await self.get_config()
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
        old_state = self.to_dict()
        self.is_locked = False
        # self.locked_by = None
        # self.locked_at = None
        self.unlocked_by = unlocker
        self.unlocked_at = datetime.datetime.now(tz=datetime.timezone.utc)

        if unlocker is None:
            audit_reason = _("Ticket unlocked (profile `{self.profile}`).").format(self=self)
        else:
            audit_reason = _(
                "Ticket unlocked by {unlocker.display_name} ({unlocker.id}) (profile `{self.profile}`).",
            ).format(unlocker=unlocker, self=self)
        if isinstance(self.channel, discord.Thread):
            await self.edit_channel(old_state, locked=False, reason=audit_reason)
        else:
            await self.set_send_messages(old_state, not self.is_closed, reason=audit_reason)
        await self.save()

        view = self.get_view()
        await view._update()
        await self.message.edit(
            embeds=await self.get_embeds(),
            view=view,
        )

        self.bot.dispatch("ticket_unlock", self)
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
                user=self.owner or self.owner_id,
                moderator=unlocker,
                channel=self.channel,
            )

    @with_ticket_lock
    async def approve_appeal(self, approver: discord.Member | None = None) -> None:
        if self.appeal_approved:
            raise RuntimeError(_("This ticket appeal is already approved."))
        await self.fetch_channel()
        config = await self.get_config()
        if not config["appeals"]["enabled"]:
            raise RuntimeError(_("Appeals are not enabled for this profile."))
        if (guild := self.bot.get_guild(config["appeals"]["guild_id"])) is None:
            raise RuntimeError(_("The server is not available."))
        if not guild.me.guild_permissions.ban_members:
            raise RuntimeError(
                _("I don't have the required permissions to unban users in the server."),
            )
        old_state = self.to_dict()
        self.appeal_approved = True
        self.appeal_approved_by = approver
        self.appeal_approved_at = datetime.datetime.now(tz=datetime.timezone.utc)

        if approver is None:
            audit_reason = _("Ticket appeal approved.").format(self=self)
        else:
            audit_reason = _(
                "Ticket appeal approved by {approver.display_name} ({approver.id}).",
            ).format(approver=approver, self=self)

        try:
            await guild.unban(
                discord.Object(self.owner_id),
                reason=audit_reason,
            )
        except discord.NotFound:
            await self.channel.send(
                embed=discord.Embed(
                    title=_("❌ The user has already been unbanned."),
                    color=discord.Color.red(),
                ),
            )
        except discord.HTTPException as e:
            self.restore(old_state)
            raise RuntimeError(
                _("I couldn't unban the user.\n{error}").format(error=box(str(e), lang="py")),
            )
        await self.save()

        await self.log_action(
            action=_("🛡️ Ticket Appeal Approved"),
            author=approver,
        )
        await self.channel.send(
            _(
                "## 🛡️ **Congratulations!** Your appeal request got approved by our staff!\n\n"
                "You can use the invite url below to join the server again:\n"
                "https://discord.gg/{invite_code}\n"
                "*If you still encounter any issues to join the server, try restarting your Discord client.*\n\n"
                "Then, please close this ticket. Thank you!",
            ).format(
                invite_code=config["appeals"]["invite_code"],
            ),
        )

        try:
            await self.channel.edit(
                name=await self.channel_name(),
                reason=audit_reason,
            )
        except discord.HTTPException:
            pass
        view = self.get_view()
        await view._update()
        await self.message.edit(
            embeds=await self.get_embeds(),
            view=view,
        )

        self.bot.dispatch("ticket_appeal_approve", self)
        if config["create_modlog_case"]:
            await modlog.create_case(
                bot=self.bot,
                guild=self.guild,
                created_at=datetime.datetime.now(tz=datetime.timezone.utc),
                action_type="ticket_appeal_approved",
                user=self.owner or self.owner_id,
                moderator=self.guild.me,
                channel=self.channel,
            )

    @with_ticket_lock
    async def add_member(
        self,
        member: discord.Member,
        author: discord.Member | None = None,
    ) -> None:
        config = await self.get_config()
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
        await self.fetch_channel()
        config = await self.get_config()
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
                    "This member has a role that allows them to access the ticket without being added manually.",
                ),
            )
        old_state = self.to_dict()
        self.members_ids.append(member.id)

        if author is None:
            audit_reason = _(
                "Member added to the ticket: {member.display_name} ({member.id}).",
            ).format(member=member)
        else:
            audit_reason = _(
                "Member added to the ticket by {author.display_name} ({author.id}): {member.display_name} ({member.id}).",
            ).format(author=author, member=member)
        if isinstance(self.channel, discord.Thread):
            try:
                await self.channel.add_user(member)
            except discord.HTTPException as e:
                self.restore(old_state)
                raise RuntimeError(
                    _("I couldn't add the member to the thread.\n{error}").format(
                        error=box(str(e), lang="py"),
                    ),
                )
        else:
            await self.edit_channel(
                old_state,
                overwrites=await self.get_channel_overwrites(),
                reason=audit_reason,
            )
        await self.save()

        self.bot.dispatch("ticket_member_add", self)
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

    @with_ticket_lock
    async def remove_member(
        self,
        member: discord.Member,
        author: discord.Member | None = None,
    ) -> None:
        config = await self.get_config()
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
        await self.fetch_channel()
        old_state = self.to_dict()
        self.members_ids.remove(member.id)

        if author is None:
            audit_reason = _(
                "Member removed from the ticket: {member.display_name} ({member.id}).",
            ).format(member=member)
        else:
            audit_reason = _(
                "Member removed from the ticket by {author.display_name} ({author.id}): {member.display_name} ({member.id}).",
            ).format(author=author, member=member)
        if isinstance(self.channel, discord.Thread):
            try:
                await self.channel.remove_user(member)
            except discord.HTTPException as e:
                self.restore(old_state)
                raise RuntimeError(
                    _("I couldn't remove the member from the thread.\n{error}").format(
                        error=box(str(e), lang="py"),
                    ),
                )
        else:
            overwrites = await self.get_channel_overwrites()
            overwrites.pop(member, None)
            await self.edit_channel(old_state, overwrites=overwrites, reason=audit_reason)
        await self.save()

        self.bot.dispatch("ticket_member_remove", self)
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
        author: discord.Member | None = None,
        target: discord.Member | None = None,
        reason: str | None = None,
    ) -> None:
        embed = discord.Embed(
            description=bold(
                action
                + (_(" by {author.mention}").format(author=author) if author is not None else ""),
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
                channel: discord.TextChannel | discord.VoiceChannel | discord.Thread,
                messages: list[discord.Message],
                tz_info="UTC",
                guild: discord.Guild | None = None,
                bot: discord.Client | None = None,
                military_time: bool | None = False,
                fancy_times: bool | None = True,
                support_dev: bool | None = True,
                attachment_handler: typing.Any | None = None,
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

        channel = await self.fetch_channel()
        transcript = await Transcript.export(
            channel=channel,
            messages=[message async for message in channel.history(limit=None)],
            tz_info="UTC",
            guild=self.guild,
            bot=self.bot,
            attachment_handler=AttachmentHandler(),
        )
        owner = self.owner if self.owner is not None else await self.bot.fetch_user(self.owner_id)
        return discord.File(
            filename=f"ticket-{self.id}-{owner.name}.html",
            fp=io.BytesIO(transcript.encode()),
        )

    @with_ticket_lock
    async def delete_channel(self, deleter: discord.Member | None = None) -> None:
        channel = await self.fetch_channel()
        old_state = self.to_dict()
        self.deleted_by = deleter
        self.deleted_at = datetime.datetime.now(tz=datetime.timezone.utc)
        if deleter is None:
            audit_reason = _("Ticket deleted (profile `{self.profile}`).").format(self=self)
        else:
            audit_reason = _(
                "Ticket deleted by {deleter.display_name} ({deleter.id}) (profile `{self.profile}`).",
            ).format(deleter=deleter, self=self)

        config = await self.get_config()
        if (
            logs_channel_id := config["logs_channel"]
        ) and (logs_channel := self.guild.get_channel_or_thread(logs_channel_id)) is not None:
            transcript = None
            if config["transcripts"]:
                try:
                    transcript = await self.export()
                except Exception as e:
                    self.cog.logger.error(
                        f"Error when exporting the transcript of the ticket #{self.id} in the guild {self.guild_id}.",
                        exc_info=e,
                    )
            try:
                await logs_channel.send(
                    embeds=[
                        discord.Embed(
                            title=_("🗑 Ticket Deleted"),
                            description=_("<@{self.owner_id}>'s ticket has been deleted.").format(
                                self=self,
                            ),
                            color=discord.Color.red(),
                            timestamp=datetime.datetime.now(tz=datetime.timezone.utc),
                        ),
                        await self.get_embed(for_logging=True),
                    ],
                    file=transcript,
                )
            except discord.HTTPException as e:
                self.cog.logger.error(
                    f"Error when sending the deletion log of the ticket #{self.id} in the channel `{logs_channel.name}` ({logs_channel.id}) in the guild `{self.guild.name}` ({self.guild.id}).",
                    exc_info=e,
                )

        try:
            await channel.delete(reason=audit_reason)
        except discord.NotFound:
            pass
        except discord.HTTPException as e:
            self.restore(old_state)
            raise RuntimeError(
                _("I couldn't delete the channel of this ticket.\n{error}").format(
                    error=box(str(e), lang="py"),
                ),
            )
        await self.delete()

        self.bot.dispatch("ticket_delete", self)
        if config["create_modlog_case"]:
            await modlog.create_case(
                bot=self.bot,
                guild=self.guild,
                created_at=datetime.datetime.now(tz=datetime.timezone.utc),
                action_type="ticket_deleted",
                user=self.owner or self.owner_id,
                moderator=deleter,
                channel=channel,
            )

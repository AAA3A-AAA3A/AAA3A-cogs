from redbot.core import commands  # isort:skip
from redbot.core.bot import Red  # isort:skip
from redbot.core.i18n import Translator  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import copy
import datetime
from dataclasses import _is_dataclass_instance, dataclass, field, fields
from urllib.parse import quote_plus

from redbot.core.utils.chat_formatting import humanize_list

_: Translator = Translator("Events", __file__)


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
class Point:
    amount: int
    member_id: typing.Optional[int] = None
    managed_by_id: typing.Optional[int] = None
    managed_at_timestamp: int = field(
        default_factory=lambda: int(
            datetime.datetime.now(tz=datetime.timezone.utc)
            .replace(second=0, microsecond=0)
            .timestamp()
        )
    )

    def to_dict(self) -> typing.Dict[str, typing.Any]:
        return _asdict_inner(self)

    def get_member(self, guild: discord.Guild) -> typing.Optional[discord.Member]:
        if self.member_id is None:
            return None
        return guild.get_member(self.member_id)

    def get_managed_by(self, guild: discord.Guild) -> typing.Optional[discord.Member]:
        if self.managed_by_id is None:
            return None
        return guild.get_member(self.managed_by_id)

    @property
    def managed_at(self) -> datetime.datetime:
        return datetime.datetime.fromtimestamp(self.managed_at_timestamp, tz=datetime.timezone.utc)


@dataclass
class Team:
    bot: Red
    cog: commands.Cog

    guild_id: int
    name: str

    captain_id: int
    vice_captain_ids: typing.List[int] = field(default_factory=list)
    member_ids: typing.List[int] = field(default_factory=list)
    points: typing.List[Point] = field(default_factory=list)

    emoji: typing.Optional[typing.Union[str, int]] = None
    logo_url: typing.Optional[str] = None
    color_value: typing.Optional[int] = None
    description: typing.Optional[str] = None
    slogan: typing.Optional[str] = None
    created_at_timestamp: int = field(
        default_factory=lambda: int(
            datetime.datetime.now(tz=datetime.timezone.utc)
            .replace(second=0, microsecond=0)
            .timestamp()
        )
    )

    captain_role_id: typing.Optional[int] = None
    vice_captain_role_id: typing.Optional[int] = None
    member_role_id: typing.Optional[int] = None

    @property
    def id(self) -> str:
        get_id = lambda name: "".join(word[0].upper() for word in name.split() if word)
        id = get_id(self.name)
        teams = sorted(
            [
                team
                for team in self.cog.teams.get(self.guild_id, {}).values()
                if team is not self
                and team.created_at < self.created_at
                and get_id(team.name) == id
            ],
            key=lambda team: team.created_at,
        )
        return id if not teams else f"{id}{len(teams)}"

    def __hash__(self) -> int:
        return hash(self.id)

    def to_dict(self) -> typing.Dict[str, typing.Any]:
        return _asdict_inner(self)

    async def save(self) -> None:
        await self.cog.config.guild(self.guild).teams.set_raw(self.id, value=self.to_dict())
        self.cog.teams.setdefault(self.guild_id, {})[self.id] = self

    async def delete(self) -> None:
        for role in (self.captain_role, self.vice_captain_role, self.member_role):
            if role is not None:
                try:
                    await role.delete()
                except discord.HTTPException:
                    pass
        try:
            del self.cog.teams[self.guild_id][self.id]
        except KeyError:
            pass
        else:
            if not self.cog.teams[self.guild_id]:
                del self.cog.teams[self.guild_id]
        await self.cog.config.guild(self.guild).teams.clear_raw(self.id)

    @property
    def guild(self) -> discord.Guild:
        return self.bot.get_guild(self.guild_id)

    @guild.setter
    def guild(self, guild: discord.Guild) -> None:
        self.guild_id = guild.id

    @property
    def display_name(self) -> str:
        return "{emoji}{name} [{id}]".format(
            emoji=f"{self.display_emoji} " if self.emoji is not None else "",
            name=self.name,
            id=self.id,
        )

    @property
    def captain(self) -> typing.Optional[discord.Member]:
        if (guild := self.guild) is None:
            return None
        return guild.get_member(self.captain_id)

    @captain.setter
    def captain(self, captain: discord.Member) -> None:
        self.captain_id = captain.id

    @property
    def vice_captains(self) -> typing.List[discord.Member]:
        if (guild := self.guild) is None:
            return []
        return [
            vice_captain
            for vice_captain_id in self.vice_captain_ids
            if (vice_captain := guild.get_member(vice_captain_id)) is not None
        ]

    @property
    def members(self) -> typing.List[discord.Member]:
        if (guild := self.guild) is None:
            return []
        return [
            member
            for member_id in self.member_ids
            if (member := guild.get_member(member_id)) is not None
        ]

    @members.setter
    def members(self, members: typing.List[discord.Member]) -> None:
        self.member_ids = [member.id for member in members]

    @property
    def created_at(self) -> datetime.datetime:
        return datetime.datetime.fromtimestamp(self.created_at_timestamp, tz=datetime.timezone.utc)

    @created_at.setter
    def created_at(self, created_at: datetime.datetime) -> None:
        self.created_at_timestamp = int(created_at.timestamp())

    @property
    def display_emoji(self) -> typing.Optional[str]:
        if self.emoji is None:
            return None
        return self.emoji if isinstance(self.emoji, str) else str(self.bot.get_emoji(self.emoji))

    @display_emoji.setter
    def display_emoji(self, emoji: typing.Optional[typing.Union[discord.Emoji, str]]) -> None:
        self.emoji = getattr(emoji, "id", emoji)

    @property
    def color(self) -> discord.Color:
        if self.color_value is None:
            return None
        return discord.Color(self.color_value)

    @color.setter
    def color(self, color: typing.Optional[discord.Color]) -> None:
        self.color_value = color.value if color is not None else None

    @property
    def display_logo_url(self) -> typing.Optional[str]:
        if self.logo_url is not None:
            return self.logo_url
        elif self.emoji is not None:
            emoji = self.emoji if isinstance(self.emoji, str) else self.bot.get_emoji(self.emoji)
            if isinstance(emoji, str):
                try:
                    return f"https://cdnjs.cloudflare.com/ajax/libs/twemoji/14.0.2/72x72/{hex(ord(emoji))[2:]}.png"
                except TypeError:
                    return f"https://emojicdn.elk.sh/{quote_plus(emoji)}?style=twitter"
            return emoji.url
        return None

    @property
    def captain_role(self) -> typing.Optional[discord.Role]:
        if (guild := self.guild) is None:
            return None
        return guild.get_role(self.captain_role_id)

    @captain_role.setter
    def captain_role(self, role: typing.Optional[discord.Role]) -> None:
        self.captain_role_id = role.id if role is not None else None

    @property
    def vice_captain_role(self) -> typing.Optional[discord.Role]:
        if (guild := self.guild) is None:
            return None
        return guild.get_role(self.vice_captain_role_id)

    @vice_captain_role.setter
    def vice_captain_role(self, role: typing.Optional[discord.Role]) -> None:
        self.vice_captain_role_id = role.id if role is not None else None

    @property
    def member_role(self) -> typing.Optional[discord.Role]:
        if (guild := self.guild) is None:
            return None
        return guild.get_role(self.member_role_id)

    @member_role.setter
    def member_role(self, role: typing.Optional[discord.Role]) -> None:
        self.member_role_id = role.id if role is not None else None

    async def get_embed(self, sample: bool = False) -> discord.Embed:
        embed: discord.Embed = discord.Embed(
            title=self.display_name,
            color=self.color or await self.bot.get_embed_color(self.guild.text_channels[0]),
            timestamp=datetime.datetime.now(tz=datetime.timezone.utc),
        )
        embed.set_thumbnail(url=self.display_logo_url)
        if not sample:
            # embed.description = (
            #     (
            #         f"{self.description}\n"
            #         if self.description is not None
            #         else ""
            #     )
            #     + _("- **Captain:** {captain}").format(captain=f"<@{self.captain.id}>")
            #     + (
            #         _("\n- **Vice-Captain{s}:** {vice_captains}").format(
            #             vice_captains=humanize_list([vice_captain.mention for vice_captain in self.vice_captains]),
            #             s="" if len(self.vice_captains) == 1 else "s"
            #         ) if self.vice_captains else ""
            #     )
            #     + (
            #         _("\n- **{member_count} Member{s}**").format(
            #             member_count=len(self.members),
            #             s="" if len(self.members) == 1 else "s"
            #         )
            #     )
            # )
            embed.add_field(
                name=_("👥 Membership:"),
                value=_(
                    "- **Total Members:** {member_count}\n" "- **Captain:** {captain.mention}"
                ).format(
                    member_count=len(self.members),
                    captain=self.captain,
                )
                + (
                    _("\n- **Vice-Captain{s}:** {vice_captains}").format(
                        vice_captains=humanize_list(
                            [vice_captain.mention for vice_captain in self.vice_captains]
                        ),
                        s="" if len(self.vice_captains) == 1 else "s",
                    )
                    if self.vice_captains
                    else ""
                ),
            )
            embed.add_field(
                name=_("🏆 Points:"),
                value=_(
                    "- **Total Points:** {total_points}\n"
                    "- **Contributions:** {contributions}\n"
                    "- **Contributors:** {contributors}"
                ).format(
                    total_points=sum(point.amount for point in self.points),
                    contributions=len(self.points),
                    contributors=len(
                        {
                            member
                            for point in self.points
                            if (member := point.get_member(self.guild)) is not None
                        }
                    ),
                ),
            )
            if any((self.captain_role, self.vice_captain_role, self.member_role)):
                embed.add_field(
                    name=_("🎭 Discord Roles:"),
                    value=_(
                        "- **Captain Role:** {captain_role}\n"
                        "- **Vice-Captain Role:** {vice_captain_role}\n"
                        "- **Member Role:** {member_role}"
                    ).format(
                        captain_role=self.captain_role.mention
                        if self.captain_role is not None
                        else _("None"),
                        vice_captain_role=self.vice_captain_role.mention
                        if self.vice_captain_role is not None
                        else _("None"),
                        member_role=self.member_role.mention
                        if self.member_role is not None
                        else _("None"),
                    ),
                    inline=False,
                )
            if self.slogan is not None:
                embed.add_field(
                    name=_("📣 Slogan:"),
                    value=f"> *{self.slogan}*",
                    inline=True,
                )
            embed.add_field(
                name=_("📅 Created At:"),
                value=discord.utils.format_dt(self.created_at, style="F"),
                inline=True,
            )
        embed.set_footer(
            text=self.guild.name,
            icon_url=self.guild.icon,
        )
        embed.timestamp = self.created_at
        return embed

    async def add_member(self, member: discord.Member) -> None:
        if member in self.member_ids:
            raise RuntimeError(_("Member is already in the team."))
        if any(
            member.id in team.member_ids for team in self.cog.teams.get(self.guild.id, {}).values()
        ):
            raise RuntimeError(_("Member is already in another team."))
        self.member_ids.append(member.id)
        await self.save()
        if (
            (member_role := self.member_role) is not None
            and member.guild.me.guild_permissions.manage_roles
            and member_role not in member.roles
        ):
            try:
                await member.add_roles(member_role, reason="Adding member role to team member.")
            except discord.HTTPException:
                pass

    async def remove_member(self, member: discord.Member) -> None:
        if member.id not in self.member_ids:
            raise RuntimeError(_("Member is not in the team."))
        self.member_ids.remove(member.id)
        await self.save()
        if (
            (member_role := self.member_role) is not None
            and member.guild.me.guild_permissions.manage_roles
            and member_role in member.roles
        ):
            try:
                await member.remove_roles(
                    member_role, reason="Removing member role from team member."
                )
            except discord.HTTPException:
                pass

    async def promote_member(self, member: discord.Member) -> None:
        if member.id not in self.member_ids:
            raise RuntimeError(_("Member is not in the team."))
        if member.id == self.captain_id:
            raise RuntimeError(_("Member is already the captain."))
        elif member.id in self.vice_captain_ids:
            raise RuntimeError(_("Member is already a vice captain."))
        self.vice_captain_ids.append(member.id)
        await self.save()
        if (
            (vice_captain_role := self.vice_captain_role) is not None
            and member.guild.me.guild_permissions.manage_roles
            and vice_captain_role not in member.roles
        ):
            try:
                await member.add_roles(
                    vice_captain_role, reason="Adding vice captain role to team member."
                )
            except discord.HTTPException:
                pass

    async def demote_member(self, member: discord.Member) -> None:
        if member.id not in self.member_ids:
            raise RuntimeError(_("Member is not in the team."))
        if member.id == self.captain_id:
            raise RuntimeError(_("Member is the captain and cannot be demoted."))
        elif member.id not in self.vice_captain_ids:
            raise RuntimeError(_("Member is not a vice captain."))
        self.vice_captain_ids.remove(member.id)
        await self.save()
        if (
            (vice_captain_role := self.vice_captain_role) is not None
            and member.guild.me.guild_permissions.manage_roles
            and vice_captain_role in member.roles
        ):
            try:
                await member.remove_roles(vice_captain_role)
            except discord.HTTPException:
                pass

    async def transfer_captaincy(self, new_captain: discord.Member) -> None:
        if new_captain.id not in self.member_ids:
            raise RuntimeError(_("New captain is not a member of the team."))
        if new_captain.id == self.captain_id:
            raise RuntimeError(_("New captain is already the captain."))
        old_captain = self.captain
        self.captain_id = new_captain.id
        await self.save()
        if (
            captain_role := self.captain_role
        ) is not None and new_captain.guild.me.guild_permissions.manage_roles:
            if captain_role not in new_captain.roles:
                try:
                    await new_captain.add_roles(
                        captain_role, reason="Adding captain role to new team captain."
                    )
                except discord.HTTPException:
                    pass
            if old_captain is not None and captain_role in old_captain.roles:
                try:
                    await old_captain.remove_roles(
                        captain_role, reason="Removing captain role from old team captain."
                    )
                except discord.HTTPException:
                    pass

    async def add_points(
        self,
        amount: int,
        member: typing.Optional[discord.Member] = None,
        managed_by: typing.Optional[discord.Member] = None,
    ) -> None:
        self.points.append(
            Point(
                amount=amount,
                member_id=member.id if member is not None else None,
                managed_by_id=managed_by.id if managed_by is not None else None,
            )
        )
        await self.save()

    async def remove_points(
        self,
        amount: int,
        member: typing.Optional[discord.Member] = None,
        managed_by: typing.Optional[discord.Member] = None,
    ) -> None:
        self.points.append(
            Point(
                amount=-amount,
                member_id=member.id if member is not None else None,
                managed_by_id=managed_by.id if managed_by is not None else None,
            )
        )
        await self.save()

    async def reset_points(self) -> None:
        self.points.clear()
        await self.save()

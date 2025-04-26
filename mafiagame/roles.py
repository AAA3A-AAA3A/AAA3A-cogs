from AAA3A_utils import CogsUtils  # isort:skip
from redbot.core.i18n import Translator  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import functools
import inspect
import os
import random
from dataclasses import dataclass, field

from redbot.core.utils.chat_formatting import humanize_list

from .constants import (
    MAFIA_COLOR,
    NEUTRAL_COLOR,
    VILLAGERS_COLOR,
)  # NOQA
from .utils import get_death_reason, get_image
from .views import (
    GamblerView,
    GuessTargetsRolesView,
    IsekaiView,
    JudgeView,
    SelectRolesView,
    SelectTargetsView,
)  # NOQA

TARGET_TYPE_HINT = typing.Optional[
    typing.Union[
        "Player",
        typing.Tuple["Player", typing.Optional["Player"]],
        typing.Type["Role"],
        typing.Tuple["Player", typing.Type["Role"]],
        typing.List[typing.Tuple["Player", typing.Type["Role"]]],
    ]
]


def _(untranslated: str) -> str:  # `redgettext` will find these strings.
    return untranslated


@dataclass
class Player:
    game: typing.Any
    member: discord.Member
    role: typing.Type["Role"]
    previous_role: typing.Optional[typing.Type["Role"]] = None

    is_dead: bool = False
    death_cause: typing.Union[
        typing.Literal["Mafia", "voting", "suicide", "afk", "scorching_sun"], "Player"
    ] = None
    death_day_night_number: typing.Optional[int] = None
    dying_message: typing.Optional[str] = None
    last_interaction: typing.Optional[discord.Interaction] = None
    game_targets: typing.List[TARGET_TYPE_HINT] = field(default_factory=list)

    is_town_traitor: bool = False
    is_town_vip: bool = False

    revealed: bool = False
    extra_votes: int = 0
    global_target: typing.Optional["Player"] = None
    uses_amount: int = 0
    bomb_planted: bool = False
    infected: bool = False
    immune: bool = False
    voodoo_doll_vanished: bool = False
    submissor_attacker: typing.Optional["Player"] = None
    guardian_successfully_protected_players: typing.List["Player"] = field(default_factory=list)
    cupid_lovers: typing.Tuple["Player"] = field(default_factory=tuple)

    def __hash__(self) -> int:
        return hash(self.member)

    def __repr__(self) -> str:
        return f"<Player role=<{self.role.__name__} side={self.role.side!r}> member={self.member!r} is_dead={self.is_dead}>"

    async def send(
        self, *args, **kwargs
    ) -> typing.Optional[typing.Union[discord.WebhookMessage, discord.Message]]:
        if self.last_interaction is not None:
            try:
                return await self.last_interaction.followup.send(
                    *args, **kwargs, ephemeral=True, wait=True
                )
            except discord.HTTPException:
                pass
        try:
            return await self.member.send(*args, **kwargs)
        except discord.HTTPException:
            pass

    async def kill(
        self,
        cause: typing.Union[
            typing.Literal["Mafia", "voting", "suicide", "afk", "scorching_sun"], "Player"
        ] = "Mafia",
        reason: str = None,
    ) -> None:
        _: Translator = Translator("MafiaGame", __file__)

        try:
            await self.role.on_death(self)
        except NotImplementedError:
            pass
        except ValueError:
            return

        self.is_dead = True
        self.death_cause = cause
        self.death_day_night_number = (
            self.game.days_nights[-1].number if self.game.days_nights else 0
        )
        self.game.afk_players.pop(self, None)
        if not isinstance(self.game.channel, discord.Thread):
            try:
                overwrites = self.game.channel.overwrites.copy()
                overwrites.setdefault(
                    self.member,
                    discord.PermissionOverwrite(
                        view_channel=True, read_messages=True, attach_files=False
                    ),
                )
                overwrites[self.member].send_messages = False
                overwrites[self.member].add_reactions = False
                await self.game.channel.edit(overwrites=overwrites)
            except discord.HTTPException:
                pass

        if self.game.days_nights and self.game.days_nights[-1].__class__.__name__ == "Night":
            silencer = next(
                (
                    t
                    for p, t in self.game.days_nights[-1].targets.items()
                    if p.role is Silencer and self == t
                ),
                None,
            )
        else:
            silencer = None
        if self.game.current_anomaly is None or self.game.current_anomaly.name != "Foggy Mist":
            embeds = []
            embed: discord.Embed = discord.Embed(
                title=(
                    _("{member.display_name} has been attacked by **the Mafia**!").format(
                        member=self.member
                    )
                    if cause == "Mafia"
                    else (
                        _("{member.display_name} has been **lynched**!").format(member=self.member)
                        if cause == "voting"
                        else (
                            _("{member.display_name} has killed **themselves**!").format(
                                member=self.member
                            )
                            if cause == "suicide"
                            else (
                                _("{member.display_name} has been considered as **AFK**!").format(
                                    member=self.member
                                )
                                if cause == "afk"
                                else (
                                    _(
                                        "{member.display_name} has been killed by the **Anomaly Scorching Sun**!"
                                    ).format(member=self.member)
                                    if cause == "scorching_sun"
                                    else _(
                                        "{member.display_name} has been killed by {the_or_a} **{cause}**!"
                                    ).format(
                                        member=self.member,
                                        cause=cause.role.name,
                                        the_or_a=cause.role.the_or_a(self.game),
                                    )
                                )
                            )
                        )
                    )
                ),
                description=get_death_reason(self.member) if cause == "Mafia" else reason,
                color=MAFIA_COLOR,
            )
            embed.set_thumbnail(url=self.member.display_avatar)
            embed.set_image(url="attachment://you_died.png")
            embeds.append(embed)
            if self.game.config["show_dead_role"]:
                embed: discord.Embed = discord.Embed(
                    title=(
                        _("They were {the_or_a} **{player.role.name}**!").format(
                            player=self, the_or_a=self.role.the_or_a(self.game)
                        )
                        if silencer is None
                        else _("They were **???**!")
                    ),
                    color=self.role.color(),
                )
                embed.set_image(url=self.role.image_url())
                embeds.append(embed)
            if self.is_town_traitor:
                embed: discord.Embed = discord.Embed(
                    title=_("They were {the_or_a} **Town Traitor**!").format(
                        the_or_a=(
                            _("the")
                            if len([p for p in self.game.players if p.is_town_traitor]) == 1
                            else _("a")
                        )
                    ),
                    description=_("They were working with the Mafia to kill the villagers."),
                    color=MAFIA_COLOR,
                )
                embed.set_image(url="attachment://town_traitor.png")
                embeds.append(embed)
            # if self.is_town_vip:
            #     embed: discord.Embed = discord.Embed(
            #         title=_("They were {the_or_a} **Town VIP**!").format(the_or_a=_("the") if len([p for p in self.game.players if p.is_town_vip]) == 1 else _("a")),
            #         description=_("They were the most important person in the town."),
            #         color=VILLAGERS_COLOR,
            #     )
            #     embed.set_image(url="attachment://town_vip.png")
            #     embeds.append(embed)
            if self.dying_message is not None:
                embeds.append(
                    discord.Embed(
                        title=_("Last Words (Dying Message):"),
                        description=f">>> {self.dying_message}" if silencer is None else _("???"),
                        color=discord.Color.red(),
                    )
                )
            await self.game.send(
                content=self.member.mention,
                embeds=embeds,
                files=(
                    [get_image("you_died")]
                    + (
                        [self.role.get_image()]
                        if self.game.config["show_dead_role"] and silencer is None
                        else []
                    )
                    + ([get_image("town_traitor")] if self.is_town_traitor else [])
                    # + ([get_image("town_vip")] if self.is_town_vip else [])
                ),
            )

        if silencer is not None:
            embeds = []
            if self.game.config["show_dead_role"]:
                embed: discord.Embed = discord.Embed(
                    title=_(
                        "{player.member.display_name} were {the_or_a} **{player.role.name}**!"
                    ).format(player=self, the_or_a=self.role.the_or_a(self.game)),
                    color=self.role.color(),
                )
                image = self.role.name.lower().replace(" ", "_")
                embed.set_image(url=f"attachment://{image}.png")
                embeds.append(embed)
            if self.dying_message is not None:
                embeds.append(
                    discord.Embed(
                        title=_("Last Words (Dying Message):"),
                        description=f">>> {self.dying_message}",
                        color=discord.Color.red(),
                    )
                )
            if embeds:
                await silencer.send(
                    embeds=embeds,
                    files=[self.role.get_image()] if self.game.config["show_dead_role"] else [],
                )

        for player in self.game.alive_players:
            try:
                await player.role.on_other_player_death(player, self)
            except NotImplementedError:
                pass

    async def change_role(
        self,
        role: typing.Type["Role"],
        reason: typing.Optional[str] = None,
    ) -> None:
        self.previous_role = self.role
        self.role = role
        await self.send(
            reason,
            **role.get_kwargs(self, change=True),
        )
        self.uses_amount = 0
        try:
            await role.on_game_start(self.game, self)  # For a new Executioner/Santa for example.
        except NotImplementedError:
            pass
        if len(self.game.days_nights) > 1 or (
            len(self.game.days_nights) == 1 and self in self.game.days_nights[0].targets
        ):
            try:
                await role.no_action(
                    self.game.days_nights[0], self
                )  # For a new Cupid for example.
            except NotImplementedError:
                pass

    @property
    def has_won(self) -> bool:
        return self.role.has_won(self)

    async def check_achievements(
        self, save: bool = True
    ) -> typing.Dict[typing.Optional[typing.Type["Role"]], typing.List[str]]:
        data = await self.game.cog.config.user(self.member).all()
        data["games"].setdefault(self.role.name, 0)
        data["games"][self.role.name] += 1
        if self.has_won:
            data["wins"].setdefault(self.role.name, 0)
            data["wins"][self.role.name] += 1
        new_achievements = {}
        to_check = {None: ACHIEVEMENTS}
        if self.previous_role is not None:
            to_check[self.previous_role.name] = self.previous_role.achievements
        to_check[self.role.name] = self.role.achievements
        for location, achievements in to_check.items():
            for achievement, value in achievements.items():
                if achievement in data["achievements"].get(str(location), []):
                    continue
                check, value = value["check"], value.get("value")
                if check in ("wins", "games"):
                    if (
                        sum(data[check].values())
                        if location is None
                        else data[check].get(location, 0)
                    ) >= value:
                        new_achievements.setdefault(location, []).append(achievement)
                elif check == "win_without_dying":
                    if self.has_won and not self.is_dead:
                        new_achievements.setdefault(location, []).append(achievement)
                elif check == "targets":
                    if len(self.game_targets) >= value:
                        new_achievements.setdefault(location, []).append(achievement)
                elif check(
                    self
                    if list(inspect.signature(check).parameters.values())[0].name == "player"
                    else data["wins"]
                ):
                    new_achievements.setdefault(location, []).append(achievement)
        for location, achievements in new_achievements.items():
            data["achievements"].setdefault(str(location), []).extend(achievements)
        if save:
            await self.game.cog.config.user(self.member).set(data)
        return new_achievements


class Role:
    name: str
    side: typing.Literal["Mafia", "Villagers", "Neutral", "Horsemen of the Apocalypse"]
    description: str
    ability: str = _("No special ability.")
    max_uses: typing.Optional[int] = None
    visit_type: str = "N/A"
    objective: str
    objective_secondary: bool = False
    starting: bool = True

    achievements: typing.Dict[
        str,
        typing.Dict[
            typing.Literal["check", "value", "description"],
            typing.Union[
                typing.Literal["wins", "games", "win_without_dying"],
                typing.Optional[
                    typing.Union[int, typing.Type["Role"], typing.List[typing.Type["Role"]]]
                ],
            ],
        ],
    ] = {}

    @classmethod
    def image_name(cls) -> str:
        return cls.name.lower().replace(" ", "_")

    @classmethod
    def image_url(cls) -> str:
        return f"attachment://{cls.image_name()}.png"

    @classmethod
    def get_image(cls) -> discord.File:
        return get_image(os.path.join("roles", cls.image_name()))

    @classmethod
    def color(cls) -> discord.Color:
        if cls is Alchemist:
            return discord.Color.dark_theme()
        if cls.side == "Mafia":
            return MAFIA_COLOR
        elif cls.side == "Villagers":
            return VILLAGERS_COLOR
        elif cls.side == "Neutral":
            return NEUTRAL_COLOR

    @classmethod
    def get_kwargs(
        cls, player: Player = None, change: bool = False
    ) -> typing.Dict[str, typing.Union[discord.Embed, discord.File]]:
        _: Translator = Translator("MafiaGame", __file__)
        embed: discord.Embed = discord.Embed(
            title=_("You are {now}{the_or_a} **{name}**!").format(
                name=cls.name,
                the_or_a=cls.the_or_a(player.game if player is not None else None),
                now="now " if change else "",
            ),
            description=_(cls.description)
            + (
                ""
                if cls.starting
                else _(
                    "\n\n*Outside the `Custom` mode, it is not possible to be assigned this role at the start of the game.*"
                )
            ),
            color=cls.color(),
        )
        image = cls.name.lower().replace(" ", "_")
        embed.set_image(url=cls.image_url())
        embed.add_field(name=_("Ability: 🔪"), value=_(cls.ability), inline=False)
        embed.add_field(name=_("Side: 👀"), value=cls.side)
        embed.add_field(name=_("Visit Type: 🏃‍♂️"), value=cls.visit_type)
        embed.add_field(
            name=_("Objective: 🥅"),
            value=_(cls.objective) + (_(" *(secondary)*") if cls.objective_secondary else ""),
            inline=False,
        )
        if player is not None:
            embed.set_thumbnail(url=player.member.display_avatar)
            embed.set_footer(
                text=player.game.channel.guild.name, icon_url=player.game.channel.guild.icon
            )
        return {
            "embed": embed,
            "file": cls.get_image(),
        }

    @classmethod
    def the_or_a(cls, game=None) -> str:
        if game is None:
            return _("the")
        game = getattr(cls, "game", game)
        return _("the") if len([p for p in game.players if p.role is cls]) <= 1 else _("a")

    @classmethod
    def has_won(cls, player: Player) -> bool:
        mafia_check = (
            len(
                [p for p in player.game.alive_players if p.role.side == "Mafia" or p.is_town_traitor]
            ) >= len(
                [
                    p
                    for p in player.game.alive_players
                    if p.role.side != "Mafia" and not p.is_town_traitor
                ]
            ) or (
                all(p.is_dead for p in player.game.players if p.role.side == "Mafia")
                and any(p for p in player.game.alive_players if p.is_town_traitor)
                and player.game.current_number
                - max(
                    p.death_day_night_number
                    for p in player.game.dead_players
                    if p.role.side == "Mafia"
                )
                >= 3
            ) and not any(
                p.has_won for p in player.game.alive_players if p.role is Jester
            )
        )
        if player.role.side == "Mafia" or player.is_town_traitor:
            # all(p.is_dead for p in player.game.players if p.role.side != "Mafia" and not p.is_town_traitor)
            return mafia_check and not any(p for p in player.game.alive_players if p.is_town_vip)
        elif player.role.side == "Villagers":
            return (
                all(
                    p.is_dead
                    for p in player.game.players
                    if p.role.side == "Mafia" or p.role is Bomber or p.is_town_traitor
                )
            ) or (mafia_check and any(p for p in player.game.alive_players if p.is_town_vip))
        return False

    @classmethod
    async def on_game_start(cls, game, player: Player) -> None:
        raise NotImplementedError()

    @classmethod
    async def perform_action(cls, night, player: Player, interaction: discord.Interaction) -> None:
        raise NotImplementedError()

    @classmethod
    async def check_pt(cls, night, player: Player, p: Player, t: Player) -> Player:
        raise NotImplementedError()

    @classmethod
    async def action(cls, night, player: Player, target: TARGET_TYPE_HINT) -> None:
        raise NotImplementedError()

    @classmethod
    async def no_action(cls, night, player: Player) -> None:
        raise NotImplementedError()

    @classmethod
    async def perform_day_action(
        cls, day, player: Player, interaction: discord.Interaction
    ) -> None:
        raise NotImplementedError()

    @classmethod
    async def day_action(cls, day, player: Player, target: TARGET_TYPE_HINT) -> None:
        raise NotImplementedError()

    @classmethod
    async def next_end_day_action(cls, day, player: Player, target: TARGET_TYPE_HINT) -> None:
        raise NotImplementedError()

    @classmethod
    async def on_death(cls, player: Player) -> None:
        raise NotImplementedError()

    @classmethod
    async def on_other_player_death(cls, player: Player, other: Player) -> None:
        raise NotImplementedError()


def perform_action_select_targets(
    targets_number: int = 1,
    self_allowed: bool = True,
    mafia_allowed: bool = True,
    last_target_allowed: bool = True,
    condition: typing.Callable[[Player, Player], bool] = None,
    two_selects: bool = False,
    second_select_optional: bool = False,
) -> None:
    async def func(
        night,
        player: Player,
        interaction: discord.Interaction,
        content: typing.Optional[str] = None,
        **kwargs,
    ) -> None:
        view: SelectTargetsView = SelectTargetsView(night, player, **kwargs)
        await interaction.followup.send(
            _(content),
            view=view,
            ephemeral=True,
        )
        view._message = await interaction.original_response()

    return functools.partial(
        func,
        targets_number=targets_number,
        self_allowed=self_allowed,
        mafia_allowed=mafia_allowed,
        last_target_allowed=last_target_allowed,
        condition=condition,
        two_selects=two_selects,
        second_select_optional=second_select_optional,
    )


def perform_action_select_roles(
    self_allowed: bool = True,
    mafia_allowed: bool = True,
    last_target_allowed: bool = True,
    condition: typing.Callable[[Player, Role], bool] = None,
) -> None:
    async def func(
        night,
        player: Player,
        interaction: discord.Interaction,
        content: typing.Optional[str] = None,
        **kwargs,
    ) -> None:
        view: SelectRolesView = SelectRolesView(night, player, ROLES, **kwargs)
        await interaction.followup.send(
            _(content),
            view=view,
            ephemeral=True,
        )
        view._message = await interaction.original_response()

    return functools.partial(
        func,
        self_allowed=self_allowed,
        mafia_allowed=mafia_allowed,
        last_target_allowed=last_target_allowed,
        condition=condition,
    )


def perform_action_guess_targets_roles(
    targets_number: int = 1,
    self_allowed: bool = True,
    mafia_allowed: bool = True,
    last_target_allowed: bool = True,
    condition: typing.Callable[[Player, Player], bool] = None,
) -> None:
    async def func(
        night,
        player: Player,
        interaction: discord.Interaction,
        content: typing.Optional[str] = None,
        **kwargs,
    ) -> None:
        view: GuessTargetsRolesView = GuessTargetsRolesView(night, player, ROLES, **kwargs)
        await interaction.followup.send(
            _(content),
            view=view,
            ephemeral=True,
        )
        view._message = await interaction.original_response()

    return functools.partial(
        func,
        targets_number=targets_number,
        self_allowed=self_allowed,
        mafia_allowed=mafia_allowed,
        last_target_allowed=last_target_allowed,
        condition=condition,
    )


# CLASSIC ROLES


class GodFather(Role):
    name: str = "God Father"
    side: str = "Mafia"
    description: str = _(
        "God Father is the big bad boss of the town. Every mafia is under his thumb, ready to execute the God Father's will."
    )
    ability: str = _(
        "Each night, the God Father can select a player to kill. If they have a Mafia, their Mafia will attack the target instead, and they will not be seen visiting."
    )
    visit_type: str = "**Passive** if you order a mafia to kill otherwise **Active**."
    objective: str = _("Kill all villagers.")
    achievements = {
        "Leader of the Mafia": {
            "check": "wins",
            "value": 1,
        },
        "Cosa Nostra": {
            "check": "wins",
            "value": 5,
        },
        "Organized Crime": {
            "check": "wins",
            "value": 10,
        },
        "Evil Syndicate": {
            "check": "wins",
            "value": 25,
        },
        "Mastermind": {
            "check": "win_without_dying",
        },
    }

    perform_action = perform_action_select_targets(self_allowed=False, mafia_allowed=False)

    @classmethod
    async def action(cls, night, player: Player, target: Player) -> None:
        await Mafia.action(night, player, target)

    @classmethod
    async def on_death(cls, player: Player) -> None:
        _: Translator = Translator("MafiaGame", __file__)
        if any(p for p in player.game.alive_players if p.role is GodFather and p != player):
            return
        if not (
            mafia_players := sorted(
                [
                    p
                    for p in player.game.alive_players
                    if p.role.side == "Mafia" and p.role is not GodFather
                ],
                key=lambda p: (MAFIA_HIERARCHY.index(p.role), player.game.players.index(p)),
            )
        ):
            return
        new_god_father = mafia_players[0]
        await new_god_father.change_role(
            GodFather,
            reason=_(
                "Your God Father is about to die and appointed you to replace them at the head of the Mafia! *You will now be able to choose who to kill every night...*"
            ),
        )


class Mafia(Role):
    name: str = "Mafia"
    side: str = "Mafia"
    description: str = _(
        "The God Father's right hand. The mafia lives to serve the God Father, doing the biddings the God Father commands. That is always how it is... for now..."
    )
    ability: str = _(
        "Each night, the Mafia carries out the God Father's kill orders. If the God Father dies, they become the God Father."
    )
    visit_type: str = "Active"
    objective: str = _("Help the God Father to kill all villagers.")
    achievements = {
        "Mobster": {
            "check": "wins",
            "value": 1,
        },
        "Gangster": {
            "check": "wins",
            "value": 5,
        },
        "Hoodlum": {
            "check": "wins",
            "value": 10,
        },
        "Thug": {
            "check": "wins",
            "value": 25,
        },
        "Loyal Servant": {
            "check": "win_without_dying",
            "description": _("Win the game without dying or becoming the God Father."),
        },
        "Michael Corleone": {
            "check": lambda player: player.role is GodFather,
            "description": _("Be promoted to the God Father."),
        },
    }

    @classmethod
    async def action(cls, night, player: Player, target: Player) -> None:
        if target in [t for p, t in night.targets.items() if p.role is Doctor]:
            if (
                night.game.current_anomaly is None
                or night.game.current_anomaly.name != "Foggy Mist"
            ):
                await night.game.send(
                    embed=discord.Embed(
                        title=_(
                            "{target.member.display_name} was attacked by the Mafia but the Doctor saved them!"
                        ).format(target=target),
                        color=Doctor.color(),
                    ),
                )
            return
        await target.kill()


class Doctor(Role):
    name: str = "Doctor"
    side: str = "Villagers"
    description: str = _(
        "As the villagers' only medical professional, the Doctor possesses all the knowledge to save mafia victims. However, the online degree does not cover non mafia victims."
    )
    ability: str = _(
        "Each night, the Doctor can select a player to save. If the player is attacked, they will survive. The Doctor can't save the same person two nights in row."
    )
    visit_type: str = "Active"
    objective: str = _("Save the Mafia's victims.")
    achievements = {
        "Practitioner": {
            "check": "wins",
            "value": 1,
        },
        "Healer": {
            "check": "wins",
            "value": 5,
        },
        "Medic": {
            "check": "wins",
            "value": 10,
        },
        "Surgeon": {
            "check": "wins",
            "value": 15,
        },
        "Need Medical Attention?": {
            "check": "targets",
            "value": 1,
            "description": _("Heal someone who was attacked."),
        },
        "Where Does it Hurt?": {
            "check": "targets",
            "value": 3,
            "description": _("Save 3 people in the same game."),
        },
        "Stitch Yourself": {
            "check": lambda player: player in player.game_targets,
            "description": _("Heal yourself after being attacked."),
        },
    }

    perform_action = perform_action_select_targets(last_target_allowed=False)


class Detective(Role):
    name: str = "Detective"
    side: str = "Villagers"
    description: str = _(
        "It is late at night. Another case was reported. It's time to start cracking the case and expose the Mafia in this town..."
    )
    ability: str = _(
        "Each night, the Detective can select a player to investigate. They will know if they are on the Mafia's side or not."
    )
    visit_type: str = "Active"
    objective: str = _("Sniff out the Mafia.")
    achievements = {
        "Enfore the Law": {
            "check": "wins",
            "value": 1,
        },
        "Marshall": {
            "check": "wins",
            "value": 5,
        },
        "Constable": {
            "check": "wins",
            "value": 10,
        },
        "Deputy": {
            "check": "wins",
            "value": 25,
        },
        "Not Suspicious": {
            "check": lambda player: any(t for t in player.game_targets if t.role.side != "Mafia"),
            "description": _("Investigate someone who is not on the Mafia's side."),
        },
        "Busted": {
            "check": lambda player: any(t for t in player.game_targets if t.role.side == "Mafia"),
            "description": _("Investigate someone who is on the Mafia's side."),
        },
    }

    perform_action = perform_action_select_targets(self_allowed=False)

    @classmethod
    async def action(cls, night, player: Player, target: Player) -> None:
        to_check = target if target.role is not Mimic else night.targets.get(target, target)
        is_mafia_side = to_check.role.side == "Mafia" or to_check in [
            t for p, t in night.targets.items() if p.role is Framer
        ]
        await player.send(
            embed=discord.Embed(
                title=(
                    _("{target.member.display_name} is on the Mafia's side!").format(target=target)
                    if is_mafia_side
                    else _("{target.member.display_name} is not on the Mafia's side!").format(
                        target=target
                    )
                ),
                color=MAFIA_COLOR if target.role.side == "Mafia" else VILLAGERS_COLOR,
            ),
        )


class Villager(Role):
    name: str = "Villager"
    side: str = "Villagers"
    description: str = _(
        "It's another normal day for good villager. Just finished a day of hard work, and it's good to be back home. Hope nothing bad happens!"
    )
    objective: str = _("Survive the nights.")
    achievements = {
        "Forkman": {
            "check": "wins",
            "value": 1,
        },
        "Slow and Steady": {
            "check": "wins",
            "value": 5,
        },
        "Savant of Town": {
            "check": "wins",
            "value": 10,
        },
        "True Villager": {
            "check": "wins",
            "value": 25,
        },
        "Boredom at it's Finest": {
            "check": lambda player: not player.is_dead,
            "description": _("Stay alive until the end of the game."),
        },
    }


CLASSIC_ROLES: typing.List[typing.Type["Role"]] = [GodFather, Mafia, Doctor, Detective, Villager]


# CRAZY ROLES


class Vigilante(Role):
    name: str = "Vigilante"
    side: str = "Villagers"
    description: str = _(
        "The Vigilante is a villager who has taken the law into their own hands. They will do whatever it takes to protect the town."
    )
    ability: str = _(
        "Each night, the Vigilante can select a player to kill. However, if they kill a villager, they kill their target, but also themselves."
    )
    visit_type: str = "Active"
    objective: str = _("Kill all the Mafia's members.")
    achievements = {
        "Mercenary": {
            "check": "wins",
            "value": 1,
        },
        "Justice": {
            "check": "wins",
            "value": 5,
        },
        "Smoking Gun": {
            "check": "wins",
            "value": 10,
        },
        "Judicatory": {
            "check": "wins",
            "value": 25,
        },
        "Perfect Shot": {
            "check": lambda player: len(
                [t for t in player.game_targets if t.role.side != "Villagers"]
            )
            >= 3,
            "description": _("Shoot 3 Non-Villagers in the same game."),
        },
        "Ouch!": {
            "check": lambda player: player.is_dead and player.death_cause == "suicide",
            "description": _("Shoot yourself at night."),
        },
    }

    @classmethod
    async def perform_action(cls, night, player: Player, interaction: discord.Interaction) -> None:
        if night.number == 1 and not night.game.config["vigilante_shoot_night_1"]:
            raise RuntimeError(_("The Vigilante can't shoot on Night 1."))
        await perform_action_select_targets(self_allowed=False)(night, player, interaction)

    @classmethod
    async def action(cls, night, player: Player, target: Player) -> None:
        await target.kill(cause=player)
        if target.role.side == "Villagers":
            await player.kill(
                cause="suicide", reason=_("They killed someone on the villagers' side.")
            )


class Mayor(Role):
    name: str = "Mayor"
    side: str = "Villagers"
    description: str = _(
        "The Mayor is the leader of the town. They can reveal themselves to the town and permanently gain an extra vote."
    )
    ability: str = _("A night, the Mayor can choose to reveal themselves to the town.")
    objective: str = _("Help the town lynch the Mafia's members.")
    achievements = {
        "Supervisor": {
            "check": "wins",
            "value": 1,
        },
        "Ambassador": {
            "check": "wins",
            "value": 5,
        },
        "Executive": {
            "check": "wins",
            "value": 10,
        },
        "Commander and Chief": {
            "check": "wins",
            "value": 25,
        },
        "Incognito": {
            "check": lambda player: player.has_won and not player.revealed,
            "description": _("Win without revealing yourself as the Mayor."),
        },
        "Fearless": {
            "check": lambda player: player in player.game.days_nights[0].targets,
            "description": _("Reveal yourself as Mayor on day 1."),
        },
    }

    @classmethod
    async def perform_action(cls, night, player: Player, interaction: discord.Interaction) -> None:
        if player.revealed:
            raise RuntimeError(_("You've already revealed yourself!"))
        embed: discord.Embed = discord.Embed(
            title=_("Hey Mayor! Would you like to reveal yourself to the town the next morning?"),
            color=cls.color(),
        )
        embed.set_image(url="attachment://mayor.png")
        fake_context = type(
            "FakeContext",
            (),
            {
                "interaction": interaction,
                "bot": interaction.client,
                "guild": interaction.guild,
                "channel": interaction.channel,
                "author": interaction.user,
                "message": interaction.message,
                "send": functools.partial(interaction.followup.send, wait=True),
            },
        )()
        if await CogsUtils.ConfirmationAsk(
            fake_context,
            embed=embed,
            file=get_image(os.path.join("roles", "mayor")),
            ephemeral=True,
            timeout_message=None,
        ):
            night.targets[player] = None
            await interaction.followup.send(
                content=_("You have decided to reveal yourself to the town the next morning!"),
                ephemeral=True,
            )
        else:
            night.targets.pop(player, None)
            await interaction.followup.send(
                content=_("You have decided to not reveal yourself to the town the next morning!"),
                ephemeral=True,
            )

    @classmethod
    async def action(cls, night, player: Player, target=None) -> None:
        player.revealed = True
        player.extra_votes += 1


class Framer(Role):
    name: str = "Framer"
    side: str = "Mafia"
    description: str = _(
        "A master of deception and cunning, the Framer knows every trick to deceive the town's investigative force. Planting fake evidence and alibis are what makes the Framer feared in the investigative world."
    )
    ability: str = _(
        "Each night, the Framer can select a player to frame. They will appear as a member of the Mafia, to all role-checkers for the night."
    )
    visit_type: str = "Active"
    objective: str = _("Mislead the village.")
    achievements = {
        "Slander": {
            "check": "wins",
            "value": 1,
        },
        "Incriminate": {
            "check": "wins",
            "value": 5,
        },
        "Plant the Evidence": {
            "check": "wins",
            "value": 10,
        },
        "Shift the Blame": {
            "check": "wins",
            "value": 25,
        },
        "That was Pointless": {
            "check": lambda player: any(t for t in player.game_targets if t.role.side == "Mafia"),
            "description": _("Frame a member of the Mafia."),
        },
    }

    perform_action = perform_action_select_targets(mafia_allowed=False)


class Executioner(Role):
    name: str = "Executioner"
    side: str = "Neutral"
    description: str = _(
        "A being of unknown intentions, the Executioner harbors unforgivable hatred towards a specific villager. Did the villager insult him? Stole something? Took the last curly fry? Who knows. All the executioner wants is the demise of this villager..."
    )
    ability: str = _(
        "Each day, the Executioner tries to convince the town to lynch a given target."
    )
    objective: str = _("Convince the town to lynch their target during a vote.")
    achievements = {
        "Firing Squad": {
            "check": "wins",
            "value": 1,
        },
        "Guillotine": {
            "check": "wins",
            "value": 5,
        },
        "Lynch 'Em": {
            "check": "wins",
            "value": 10,
        },
        "Gas Chamber": {
            "check": "wins",
            "value": 25,
        },
        "Quick Execution": {
            "check": lambda player: player.global_target.is_dead
            and player.global_target.death_cause == "voting"
            and player.global_target.death_day_night_number == 1,
            "description": _("Get your target lynched on day 1."),
        },
        "Patience, Jackass, Patience": {
            "check": lambda player: player.global_target.is_dead
            and player.global_target.death_cause == "voting"
            and player.global_target.death_day_night_number >= 10,
            "description": _("Get your target lynched on day 10 or later."),
        },
    }

    @classmethod
    def has_won(cls, player: Player) -> bool:
        return player.global_target.is_dead and player.global_target.death_cause == "voting"

    @classmethod
    async def on_game_start(cls, game, player: Player) -> None:
        player.global_target = random.choice(
            [
                p
                for p in game.alive_players
                if p != player and p.role.side not in ("Mafia", "Neutral")
            ]
        )
        try:
            await player.member.send(
                embed=discord.Embed(
                    title=_(
                        "🔫 Your target is {player.global_target.member.display_name}! 🔫"
                    ).format(player=player),
                    description=_("You must get them lynched by the town."),
                    color=cls.color(),
                ),
            )
        except discord.HTTPException:
            pass

    @classmethod
    async def on_other_player_death(cls, player: Player, other: Player) -> None:
        if other != player.global_target:
            return
        if other.death_cause != "voting":
            await player.change_role(
                Jester,
                reason=_(
                    "Your target, {other.member.display_name}, has died, you have failed to make the town lynch them!"
                ).format(other=other),
            )


class Jester(Role):
    name: str = "Jester"
    side: str = "Neutral"
    description: str = _(
        "The Jester sits in the corner of the room, waiting in anticipation. The rioters are shouting outside, waiting to lynch the Jester. Does the Jester fear death? No. Death fears the Jester..."
    )
    objective: str = _("Get themselves lynched by the town, and win the game.")
    starting: bool = False
    achievements = {
        "Joker": {
            "check": "wins",
            "value": 1,
        },
        "Trickster": {
            "check": "wins",
            "value": 5,
        },
        "Suicidal": {
            "check": "wins",
            "value": 10,
        },
        "Lunatic": {
            "check": "wins",
            "value": 25,
        },
        "It's Too Easy": {
            "check": lambda player: player.is_dead
            and player.death_cause == "voting"
            and player.death_day_night_number == 1,
            "description": _("Get lynched on day 1."),
        },
        "I Can Still Win": {
            "check": lambda player: player.is_dead
            and player.death_cause == "voting"
            and player.death_day_night_number >= 10,
            "description": _("Get lynched on day 10 or later."),
        },
    }

    @classmethod
    def has_won(cls, player: Player) -> bool:
        return player.is_dead and player.death_cause == "voting"


CRAZY_ROLES: typing.List[typing.Type["Role"]] = [Vigilante, Mayor, Framer, Executioner, Jester]


# CHAOS ROLES


class PrivateInvestigator(Role):
    name: str = "Private Investigator"
    side: str = "Villagers"
    description: str = _(
        "As a freelance investigator, the Private Investigator works alone. With only a camera and incredible stealth, the Private Investigator can gather information faster than the local law."
    )
    ability: str = _(
        "Each night, the Private Investigator can check two people to see if they share the same side."
    )
    visit_type: str = "Active"
    objective: str = _("Gather informations for the village.")
    achievements = {
        "Detective": {
            "check": "wins",
            "value": 1,
        },
        "Gumshoe": {
            "check": "wins",
            "value": 5,
        },
        "Private Eye": {
            "check": "wins",
            "value": 10,
        },
        "Sherlock Holmes": {
            "check": "wins",
            "value": 25,
        },
        "That's Different": {
            "check": lambda player: any(
                (target := night.targets.get(player)) is not None
                and target[0].role.side != target[1].role.side
                for night in player.game.days_nights
                if night.__class__.__name__ == "Night"
                if player in night.targets
            ),
            "description": _("Check 2 players from different sides."),
        },
        "Who Am I?": {
            "check": lambda player: any(player in target for target in player.game_targets),
            "description": _("Investigate yourself."),
        },
    }

    perform_action = perform_action_select_targets(targets_number=2)

    @classmethod
    async def action(cls, night, player: Player, target: typing.Tuple[Player, Player]) -> None:
        to_checks = [tg if tg.role is not Mimic else night.targets.get(tg, tg) for tg in target]
        tg1_side = (
            to_checks[0].role.side
            if to_checks[0] not in [t for p, t in night.targets.items() if p.role is Framer]
            else "Mafia"
        )
        tg2_side = (
            to_checks[1].role.side
            if to_checks[1] not in [t for p, t in night.targets.items() if p.role is Framer]
            else "Mafia"
        )
        is_same_side = tg1_side == tg2_side
        await player.send(
            embed=discord.Embed(
                title=(
                    _(
                        "{tg1.member.display_name} and {tg2.member.display_name} are on the same side!"
                    ).format(tg1=to_checks[0], tg2=to_checks[1])
                    if is_same_side
                    else _(
                        "{tg1.member.display_name} and {tg2.member.display_name} are not on the same side!"
                    ).format(tg1=to_checks[0], tg2=to_checks[1])
                ),
                color=discord.Color.green() if is_same_side else discord.Color.red(),
            ),
        )


class Spy(Role):
    name: str = "Spy"
    side: str = "Villagers"
    description: str = _(
        "Highly trained in espionage, the Spy sneaks around the town to track down mafia activities. However, the Spy stays a safe distance from his targets, knowing he is no match for them yet..."
    )
    ability: str = _(
        "Each night, the Spy can choose a target to spy on each night. They can see who the target visits on the night."
    )
    visit_type: str = "Active"
    objective: str = _("Gather informations for the village.")
    achievements = {
        "Low Jack": {
            "check": "wins",
            "value": 1,
        },
        "Pathfinder": {
            "check": "wins",
            "value": 5,
        },
        "Trail Chaser": {
            "check": "wins",
            "value": 10,
        },
        "Bloodhound": {
            "check": "wins",
            "value": 25,
        },
        "Around the Block": {
            "check": lambda player: any(
                (target := night.targets.get(player)) is not None
                and target.role.visit_type != "Passive"
                and night.targets.get(target) == player
                for night in player.game.days_nights
                if night.__class__.__name__ == "Night"
            ),
            "description": _("See your target visit you."),
        },
        "Stalker": {
            "check": lambda player: any(
                target.role.visit_type != "Passive"
                and len(
                    [
                        night.targets.get(player) == target and target in night.targets
                        for night in player.game.days_nights
                        if night.__class__.__name__ == "Night"
                    ]
                )
                >= 3
                for target in player.game_targets
            ),
            "description": _("Spy on the same player 3 times and see them visiting."),
        },
    }

    perform_action = perform_action_select_targets()

    @classmethod
    async def action(cls, night, player: Player, target: Player) -> None:
        t = night.targets.get(target)
        if t is not None and isinstance(t, typing.Tuple):
            t = t[0]
        await player.send(
            embed=discord.Embed(
                title=_("Your target, {target.member.display_name}, ").format(target=target)
                + (
                    _(" has visited {t.member.display_name} this night.").format(t=t)
                    if t is not None
                    and target.role.visit_type != "Passive"
                    else _("apparently didn't visit anyone this night.")
                )
            ),
        )


class Distractor(Role):
    name: str = "Distractor"
    side: str = "Villagers"
    description: str = _(
        "A master of distractions, the Distractor can divert the attention of people however they please. With only a fear of poultry, the Distractor are a fearsome foe to the Mafia."
    )
    ability: str = _(
        "Each night, the Distractor can choose one player to prevent them from using their role. They can distract anyone with a visiting role."
    )
    visit_type: str = "Active"
    objective: str = _("Distract the bad guys.")
    achievements = {
        "Attendant": {
            "check": "wins",
            "value": 1,
        },
        "Tailgater": {
            "check": "wins",
            "value": 5,
        },
        "Great Company": {
            "check": "wins",
            "value": 10,
        },
        "Master of Distraction": {
            "check": "wins",
            "value": 25,
        },
        "Hey There!": {
            "check": lambda player: any(
                (target := night.targets.get(player)) is not None
                and target.role.visit_type != "Passive"
                and target in night.targets
                for night in player.game.days_nights
                if night.__class__.__name__ == "Night"
            ),
            "description": _("Successfully distract someone."),
        },
    }

    perform_action = perform_action_select_targets()

    @classmethod
    async def check_pt(cls, night, player: Player, p: Player, t: Player) -> Player:
        if p == night.targets.get(player) and p.role.visit_type != "Passive":
            await p.send(
                embed=discord.Embed(
                    title=_("Sorry, you got distracted tonight!"),
                    description=_("You were unable to perform your action."),
                ),
            )
            raise ValueError()
        return t


class Baiter(Role):
    name: str = "Baiter"
    side: str = "Neutral"
    description: str = _(
        "The Baiter is a serial killer, but really a lazy one. Instead of hunting for prey, Baiter prefer to stay at home and kill whoever shows up."
    )
    ability: str = _(
        "Baiter doesn't have any special night abilities, but they have a powerful passive ability: they kill anyone that visits them with an active visit type. They can kill an unlimited number of players in any night."
    )
    objective: str = _("Kill at least 3 people.")
    objective_secondary: bool = True
    achievements = {
        "Battle-Hardened": {
            "check": "wins",
            "value": 1,
        },
        "Lurer": {
            "check": "wins",
            "value": 5,
        },
        "Warrior": {
            "check": "wins",
            "value": 10,
        },
        "Expert in Luring": {
            "check": "wins",
            "value": 25,
        },
        "Massacre": {
            "check": lambda player: any(
                len(
                    [
                        p
                        for p in player.game.dead_players
                        if p.death_cause == player and p.death_day_night_number == night.number
                    ]
                )
                >= 3
                for night in player.game.days_nights
                if night.__class__.__name__ == "Night"
            ),
            "description": _("Kill 3 or more people in one night."),
        },
        "Lucky Paranoia": {
            "check": lambda player: player.has_won
            and not any(
                p
                for p in player.game.dead_players
                if p.death_cause == player and p.role.side == "Villagers"
            ),
            "description": _("Win the game without killing any Villagers' player."),
        },
        "Bad Luck": {
            "check": lambda player: not any(
                p for p in player.game.dead_players if p.death_cause == player
            ),
            "description": _("Have no one get killed by you the whole game."),
        },
    }

    @classmethod
    def has_won(cls, player: Player) -> bool:
        return (
            not player.is_dead
            and len([p for p in player.game.dead_players if p.death_cause == player]) >= 3
        )

    @classmethod
    async def check_pt(cls, night, player: Player, p: Player, t: Player) -> Player:
        if p.role.visit_type != "Passive" and player == t:
            await player.kill(cause=player, reason=_("They have visited them."))
            raise ValueError()
        return t


class Bomber(Role):
    name: str = "Bomber"
    side: str = "Neutral"
    description: str = _(
        "The Bomber loves big booms. Bomber worked at a mine before, but those explosions got old quick. Bomber missed the excitement, the rush! That's why the Bomber came to this town, look for more things to go big boom..."
    )
    ability: str = _(
        "Each night, the Bomber can plant a bomb on someone or blow up all planted bombs. They have a 20 percent chance of strapping a bomb to themselves each night, in which they need to spend the night defusing the bomb. If they die, one of their planted bombs will explode randomly. Considered a threat to the village, the town isn't safe until the Bomber is dead."
    )
    visit_type: str = "Active"
    objective: str = _("KILL EVERYONE!")
    achievements = {
        "Explosion": {
            "check": "wins",
            "value": 1,
        },
        "Nuclear Power": {
            "check": "wins",
            "value": 5,
        },
        "Wiring Expert": {
            "check": "wins",
            "value": 10,
        },
        "Explosion in Need": {
            "check": "wins",
            "value": 25,
        },
        "Disco Ball": {
            "check": lambda player: any(
                len(
                    [
                        p
                        for p in player.game.dead_players
                        if getattr(p.death_cause, "role", None) is Bomber
                        and p.death_day_night_number == night.number
                    ]
                )
                >= 5
                for night in player.game.days_nights
                if night.__class__.__name__ == "Night"
            ),
            "description": _("Explode 5 or more players at once."),
        },
        "There Can Only be One": {
            "check": lambda player: any(
                p
                for p in player.game.dead_players
                if getattr(p.death_cause, "role", None) is Bomber and p.role is GodFather
            ),
            "description": _("Explode a God Father."),
        },
    }

    @classmethod
    def has_won(cls, player: Player) -> bool:
        return all(p.is_dead for p in player.game.players if p.role is not Bomber)

    perform_action = perform_action_select_targets(self_allowed=False)

    @classmethod
    async def action(cls, night, player: Player, target: typing.Optional[Player] = None) -> None:
        if target is not None:
            if random.random() <= 0.20:
                await player.send(
                    embed=discord.Embed(
                        title=_(
                            "You've attached a bomb to yourself by mistake, and spent all night defusing it! Your target is not dead."
                        ),
                    ),
                )
                return
            target.bomb_planted = True
        else:
            for t in [p for p in night.game.alive_players if p.bomb_planted]:
                await t.kill(cause=player, reason=_("One of the Bomber's bombs has exploded!"))

    @classmethod
    async def on_death(cls, player: Player) -> None:
        bomb_planted_players = [p for p in player.game.alive_players if p.bomb_planted]
        if bomb_planted_players:
            choiced = random.choice(bomb_planted_players)
            choiced.kill(
                cause=player, reason=_("The Bomber has died, and one of their bombs has exploded!")
            )
            bomb_planted_players.remove(choiced)
            for p in bomb_planted_players:
                p.bomb_planted = False


CHAOS_ROLES: typing.List[typing.Type["Role"]] = [
    PrivateInvestigator,
    Spy,
    Distractor,
    Baiter,
    Bomber,
]


class Watcher(Role):
    name: str = "Watcher"
    side: str = "Villagers"
    description: str = _(
        "A protective guardian, the Watcher has eyes of a hawk. Unlike the Vigilante, the Watcher does not believe in violence. Justice should be handled the right way."
    )
    ability: str = _(
        "Each night, the Watcher can choose a player to watch for the night. The Watcher will be told which players have visited their chosen target."
    )
    visit_type: str = "Active"
    objective: str = _("Gather info for the village.")
    achievements = {
        "Sentry": {
            "check": "wins",
            "value": 1,
        },
        "Eagle Eye": {
            "check": "wins",
            "value": 5,
        },
        "Hawk": {
            "check": "wins",
            "value": 10,
        },
        "Sentinel": {
            "check": "wins",
            "value": 25,
        },
        "I See You": {
            "check": lambda player: any(
                any(
                    p
                    for p, t in night.targets.items()
                    if t == player and p.role.visit_type != "Passive"
                )
                for night in player.game.days_nights
                if night.__class__.__name__ == "Night"
            ),
            "description": _("Successfully watch your target get visited by someone."),
        },
        "It's A Party": {
            "check": lambda player: any(
                len(
                    [
                        p
                        for p, t in night.targets.items()
                        if t == player and p.role.visit_type != "Passive"
                    ]
                )
                >= 4
                for night in player.game.days_nights
                if night.__class__.__name__ == "Night"
            ),
            "description": _("Have 4 or more people visit your target in one night."),
        },
    }

    perform_action = perform_action_select_targets()

    @classmethod
    async def action(cls, night, player: Player, target: Player) -> None:
        players = [
            p for p, t in night.targets.items() if (t == target if not isinstance(t, typing.Tuple) else target in t) and p.role.visit_type != "Passive"
        ]
        await player.send(
            embed=discord.Embed(
                title=_("Your target, {target.member.display_name}, ").format(target=target)
                + (
                    _(" has been visited by {players} this night.").format(
                        players=humanize_list([p.member.display_name for p in players])
                    )
                    if players
                    else _("hasn't been visited by anyone this night.")
                )
            ),
        )


class PlagueDoctor(Role):
    name: str = "Plague Doctor"
    side: str = "Neutral"
    description: str = _(
        "The town seems to have lost its usual liveliness. The streets are empty, the shops are closed, and a fog covers the entire village. Not a single soul dares to step out into the night. Out of the fog steps out a black, hooded figure with a bird mask. It's time..."
    )
    ability: str = _(
        "Each night, the Plague Doctor can visit someone to infect them with the plague. The infected players will spread the plague to all those whom they visit and those who visit them.\n🦠 Once the Plague Doctor has everyone infected, a warning is given to the party that the Plague Doctor has infected everyone with the Plague. The party then has to lynch the Plague Doctor on the day of the warning or else the Plague Doctor will win the game."
    )
    visit_type: str = "Passive"
    objective: str = _("Infect everyone.")
    achievements = {
        "Diseased": {
            "check": "wins",
            "value": 1,
        },
        "Infectious": {
            "check": "wins",
            "value": 5,
        },
        "Virulent": {
            "check": "wins",
            "value": 10,
        },
        "Pestilent": {
            "check": "wins",
            "value": 25,
        },
        "A Plague": {
            "check": lambda player: all(
                p.infected for p in player.game.alive_players if p.role is not PlagueDoctor
            ),
            "description": _("Infect all the living players."),
        },
        "A Virulent Plague": {
            "check": lambda player: any(
                night.plague_doctor_warning
                for night in player.game.days_nights
                if night.__class__.__name__ == "Night" and night.number <= 5
            ),
            "description": _("Have all the living players be infected on day 5 or earlier."),
        },
    }

    @classmethod
    async def has_won(cls, player: Player) -> bool:
        if (
            not player.is_dead
            and player.game.days_nights
            and player.game.days_nights[-1].__class__.__name__ == "Day"
            and all(p.infected for p in player.game.alive_players if p.role is not PlagueDoctor)
            and (
                (
                    len(player.game.days_nights) >= 2
                    and player.game.days_nights[-2].plague_doctor_warning
                )
                or (
                    any(
                        p
                        for p in player.game.dead_players
                        if p.role is not PlagueDoctor
                        and not p.infected
                        and p.death_cause == "voting"
                        and p.death_day_night_number == player.game.days_nights[-1].number
                    )
                )
            )
        ):
            for p in player.game.alive_players:
                if p.infected:
                    p.is_dead = True
            return True
        return False

    perform_action = perform_action_select_targets(
        self_allowed=False,
        condition=lambda player, target: not target.infected and target.role is not PlagueDoctor,
    )

    @classmethod
    async def action(cls, night, player: Player, target: Player) -> None:
        target.infected = True
        if all(p.infected for p in night.game.alive_players if p.role is not PlagueDoctor):
            night.plague_doctor_warning = True
            embed: discord.Embed = discord.Embed(
                title=_("The **Plague Doctor** has infected everyone!"),
                description=_("The town has one day to lynch them, or else everyone will die!"),
                color=cls.color(),
            )
            embed.set_image(url="attachment://plague_doctor.png")
            await night.game.send(
                embed=embed,
                file=get_image("plague_doctor"),
            )

    @classmethod
    async def on_death(cls, player: Player) -> None:
        for p in player.game.players:
            p.infected = False


class Hoarder(Role):
    name: str = "Hoarder"
    side: str = "Neutral"
    description: str = _(
        "A madman driven by panic and fear, the Hoarder will stop at nothing to make sure they have enough toilet paper, even if it means raiding other people's homes and stealing their toilet paper. The Hoarder is also banned from Walmart."
    )
    ability: str = _(
        "Each night, the Hoarder can choose a player to duel for their toilet paper. If the Hoarder is victorious, the Hoarder kills the target and acquires one stash of toilet paper. If the Hoarder fails, nothing happens."
    )
    visit_type: str = "Active"
    objective: str = _("Collect 3 stashes of toilet paper.")
    objective_secondary: bool = True
    achievements = {
        "Greedy": {
            "check": "wins",
            "value": 1,
        },
        "Defender": {
            "check": "wins",
            "value": 5,
        },
        "Swift": {
            "check": "wins",
            "value": 10,
        },
        "Hoarding Expert": {
            "check": "wins",
            "value": 25,
        },
        "No More Threats!": {
            "check": lambda player: len(
                {
                    p.role
                    for p in player.game.dead_players
                    if p.death_cause == player and p.role in (GodFather, Bomber)
                }
            )
            == 2,
            "description": _(
                "Successfully hoard and kill the Godfather and Bomber in the same game."
            ),
        },
        "Rampage": {
            "check": lambda player: len(
                [p for p in player.game.dead_players if p.death_cause == player]
            )
            >= 5,
            "description": _("Hoard and kill at least 5 players."),
        },
    }

    @classmethod
    def has_won(cls, player: Player) -> bool:
        return len([p for p in player.game.dead_players if p.death_cause == player]) >= 3

    perform_action = perform_action_select_targets(
        self_allowed=False,
        condition=lambda player, target: player.game.config["hoarder_hoard_same_player_if_failed"]
        or target not in player.game_targets,
    )

    @classmethod
    async def action(cls, night, player: Player, target: Player) -> None:
        if random.random() >= 0.70:
            await target.kill(
                cause=player,
                reason=_("They have killed them and acquired one stash of 🧻 toilet paper 🧻."),
            )


class Hacker(Role):
    name: str = "Hacker"
    side: str = "Mafia"
    description: str = _(
        "The Hacker is a deity in the cyber world. They can find anything about their target in a snap of a finger by tracing their internet histories, banking statements, and social medias. Nothing is safe from the Hacker if it's online."
    )
    ability: str = _(
        "Each night, the Hacker can select a player and get a list of their possible roles."
    )
    visit_type: str = "Passive"
    objective: str = _("Gather intel for the Mafia.")
    achievements = {
        "Private Detective": {
            "check": "wins",
            "value": 1,
        },
        "Interrogate": {
            "check": "wins",
            "value": 5,
        },
        "Cross-Examine": {
            "check": "wins",
            "value": 10,
        },
        "Snooper": {
            "check": "wins",
            "value": 25,
        },
        "Kill Them, Quick!": {
            "check": lambda player: any(
                target.role in (Spy, Vigilante, Doctor) for target in player.game_targets
            ),
            "description": _("Find a Spy, Vigilante or Doctor."),
        },
        "Swift Hacking!": {
            "check": lambda player: len(
                {
                    target.role
                    for target in player.game_targets
                    if target.role in (Detective, Vigilante, Doctor)
                }
            )
            == 3,
            "description": _("Find a Detective, Vigilante and Doctor in the same game."),
        },
        "Uh Oh": {
            "check": lambda player: any(target.role is Baiter for target in player.game_targets),
            "description": _("Find a Baiter."),
        },
    }

    perform_action = perform_action_select_targets(self_allowed=False, mafia_allowed=False)

    @classmethod
    async def action(cls, night, player: Player, target: Player) -> None:
        POSSIBLE_ROLES = [
            (Vigilante, Doctor, Spy, Bomber),
            (PrivateInvestigator, Jester, Mayor),
            (PlagueDoctor, Detective, Hoarder),
            (Baiter, Executioner, Distractor),
            (Link, Villager, Santa),
            (Watcher, Alchemist, Gambler, Isekai),
            (Guardian, Mortician, Baker, Cupid),
            (Killer, Oracle, Ritualist, Judge),
            (Lawyer, Politician, Magician, Starspawn),
            (Thief, Manager, Shaman),
            (Necromancer, GraveRobber, Death, Farmer),
            (Famine, Doomsayer, War),
        ]
        to_check = target if target.role is not Mimic else night.targets.get(target, target)
        possible_roles = next((roles for roles in POSSIBLE_ROLES if to_check.role in roles))
        await player.send(
            embed=discord.Embed(
                title=_("Possible roles for {target.member.display_name}:").format(target=target),
                description=humanize_list([role.name for role in possible_roles]),
            ),
        )


class Goose(Role):
    name: str = "Goose"
    side: str = "Mafia"
    description: str = _(
        "Goose is the embodiment of chaos. The Goose's sole purpose in life is to torture the living. There are no emotions in the Goose, only the desire to Goose."
    )
    ability: str = _(
        "Each night, the Goose can select a player and change their target(s) at random."
    )
    visit_type: str = "Active"
    objective: str = _("Fulfill your destiny and bring chaos to the village.")
    achievements = {
        "Occulist": {
            "check": "wins",
            "value": 1,
        },
        "Enchantress": {
            "check": "wins",
            "value": 5,
        },
        "Voodoo": {
            "check": "wins",
            "value": 10,
        },
        "Warlock": {
            "check": "wins",
            "value": 25,
        },
        "Two Birds, One Stone": {
            "check": lambda player: any(
                (target := night.targets.get(player)) is not None
                and target.role is Vigilante
                and (t := night.targets.get(target)) is not None
                and t.role.side == "Villagers"
                for night in player.game.days_nights
                if night.__class__.__name__ == "Night"
            ),
            "description": _("Make a Vigilante shoot another villager."),
        },
        "Double-Edged Sword": {
            "check": lambda player: len(
                [
                    target
                    for night in player.game.days_nights
                    if night.__class__.__name__ == "Night"
                    and (target := night.targets.get(player)) is not None
                    and target.role.side == "Villagers"
                    and getattr(target.death_cause, "role", None) is Baiter
                    and target.death_day_night_number == night.number
                ]
            )
            >= 2,
            "description": _("Force 2 villagers to die to a Baiter in the same game."),
        },
    }

    perform_action = perform_action_select_targets(
        self_allowed=False,
        mafia_allowed=False,
        condition=lambda player, target: target.role is not Goose,
    )

    @classmethod
    async def check_pt(cls, night, player: Player, p: Player, t: Player) -> Player:
        if t == player:
            return random.choice([p for p in night.game.alive_players if p != player and p != t])
        return t

    @classmethod
    async def action(cls, night, player: Player, target: Player) -> None:
        if target.role is Gambler:
            await player.send(
                embed=discord.Embed(
                    title=_(
                        "{target.member.display_name} seems to be duelling with fate, better not interfere..."
                    ).format(target=target),
                ),
            )
            night.targets.pop(target, None)
        elif target not in night.targets:
            await player.send(
                embed=discord.Embed(
                    title=_(
                        "{target.member.display_name} didn't visit anyone last night. Weird..."
                    ).format(target=target),
                ),
            )


CORONA_ROLES: typing.List[typing.Type["Role"]] = [Watcher, PlagueDoctor, Hoarder, Hacker, Goose]


class Link(Role):
    name: str = "Link"
    side: str = "Villagers"
    description: str = _(
        "Possessing one of the rarest talents in the world, the Link serves as the medium between two minds. Years of training allows the Link to dig into the hidden minds of others and expose all secrets."
    )
    ability: str = _(
        "Each night, the Link can create psychic links between two people, allowing them to see each other's side. The Link can't see the sides themselves."
    )
    visit_type: str = "Passive"
    objective: str = _("Provide the Village with information.")
    achievements = {
        "Courier": {
            "check": "wins",
            "value": 1,
        },
        "Envoy": {
            "check": "wins",
            "value": 5,
        },
        "Electrician": {
            "check": "wins",
            "value": 10,
        },
        "Precious Touch": {
            "check": "wins",
            "value": 25,
        },
        "Self Dose": {
            "check": lambda player: any(player in target for target in player.game_targets),
            "description": _("Link yourself."),
        },
    }

    perform_action = perform_action_select_targets(targets_number=2, self_allowed=False)

    @classmethod
    async def action(cls, night, player: Player, target: typing.Tuple[Player, Player]) -> None:
        for tg in target:
            other_tg = target[1] if tg == target[0] else target[0]
            await tg.send(
                embed=discord.Embed(
                    title=_(
                        "You have been linked to {other_tg.member.display_name}! Their side is **{other_tg.role.side}**."
                    ).format(other_tg=other_tg),
                    color=other_tg.role.color(),
                ).set_image(url="attachment://link.png"),
                file=get_image(os.path.join("roles", "link")),
            )
        await player.send(
            embed=discord.Embed(
                title=_(
                    "You have linked {tg1.member.display_name} and {tg2.member.display_name}!"
                ).format(tg1=target[0], tg2=target[1]),
            ),
        )


class Mimic(Role):
    name: str = "Mimic"
    side: str = "Mafia"
    description: str = _(
        "Thirsty for blood, the Mimic hunts every night for prey to consume. As the Mimic drains the blood of the victims, Mimic's silhouette slowly morphes into their victim's shape..."
    )
    ability: str = _(
        "Each night, the Mimic can drain a player and assume their identity for the night to investigators. They have a 50% chance of distracting the target."
    )
    visit_type: str = "Passive"
    objective: str = _("Confuse the village's intel and cause obstructions.")
    achievements = {
        "Camouflage": {
            "check": "wins",
            "value": 1,
        },
        "Masquerade": {
            "check": "wins",
            "value": 5,
        },
        "Smoke Screen": {
            "check": "wins",
            "value": 10,
        },
        "Master of Disguise": {
            "check": "wins",
            "value": 25,
        },
        "Slippery Chameleon": {
            "check": lambda player: any(
                len([p for p in player.game_targets if p == t]) >= 3 for t in player.game_targets
            ),
            "description": _("Mimic the same player 3 times in one game."),
        },
    }

    perform_action = perform_action_select_targets(self_allowed=False, mafia_allowed=False)

    @classmethod
    async def check_pt(cls, night, player: Player, p: Player, t: Player) -> Player:
        if p == night.targets.get(player) and random.random() <= 0.50:
            await p.send(
                embed=discord.Embed(
                    title=_("Sorry, you got distracted tonight!"),
                    description=_("You were unable to perform your action."),
                ),
            )
            raise ValueError()
        return t


class Alchemist(Role):
    name: str = "Alchemist"
    side: str = "Mafia **or** Villagers (randomly)"
    description: str = _(
        "With a mastery in the art of potion brewing, the Alchemist utilizes their knowledge to help their side win through deception, control, and death."
    )
    ability: str = _(
        "Each night, the Alchemist randomly brews one of 4 potions:\n- The **Lethal Potion** kills a player.\n- The **Invisibility Potion** grants a player immunity for the night.\n- The **Truth Potion** forces a player to reveal their side to the Alchemist.\n- The **Mundane Potion** does nothing.\nThe Alchemist can use the brewed potion on a chosen target."
    )
    visit_type: str = "Active"
    objective: str = _("Help your side win.")
    achievements = {
        "Potion Master": {
            "check": "wins",
            "value": 1,
        },
        "Eye of Newt": {
            "check": "wins",
            "value": 5,
        },
        "Vial Juggler": {
            "check": "wins",
            "value": 10,
        },
        "Elixir of Victory": {
            "check": "wins",
            "value": 25,
        },
        "The Trifecta": {
            "check": lambda player: len(
                {
                    night.alchemists_potions.get(player)
                    for night in player.game.days_nights
                    if night.__class__.__name__ == "Night"
                    and player in night.alchemists_potions
                    and player in night.targets
                }
            )
            == 3,
            "description": _("Use the Invisibility, Lethal and Truth potion in a single game."),
        },
        "Natural Remedies": {
            "check": lambda player: len(
                [t for t in player.game_targets if t.role.side == player.role.side]
            )
            >= 5,
            "description": _("Make your team members invisible 5 times."),
        },
    }

    @classmethod
    async def perform_action(cls, night, player: Player, interaction: discord.Interaction) -> None:
        POTIONS = {
            "lethal": _("Lethal Potion"),
            "invisibility": _("Invisibility Potion"),
            "truth": _("Truth Potion"),
            "mundane": _("Mundane Potion"),
        }
        if player not in night.alchemists_potions:
            night.alchemists_potions[player] = random.choice(list(POTIONS.keys()))
        potion = night.alchemists_potions[player]
        await perform_action_select_targets(self_allowed=False)(
            night,
            player,
            interaction,
            content=_("You have brewed a **{potion}**!").format(potion=POTIONS[potion]),
        )

    @classmethod
    async def action(cls, night, player: Player, target: Player) -> None:
        potion = night.alchemists_potions.pop(player)
        if potion == "lethal":
            await target.kill(cause=player)
        elif potion == "invisibility":
            night.immune_players.append(target)
        elif potion == "truth":
            await player.send(
                embed=discord.Embed(
                    title=_(
                        "The side of {target.member.display_name} is **{target.role.side}**."
                    ).format(target=target),
                ),
            )


class MafiaAlchemist(Alchemist):
    side: str = "Mafia"


class VillagerAlchemist(Alchemist):
    side: str = "Villagers"


CRIMSON_ROLES: typing.List[typing.Type["Role"]] = [Link, Mimic, Alchemist]


class Isekai(Role):
    name: str = "Isekai"
    side: str = "Neutral"
    description: str = _(
        "After living a mundane, uneventful life, the Isekai finds themselve facing a Goddess. The Goddess laids out three cards to choose from, each depicitng a different life. The Isekai is given a second chance to redeem his life in another world..."
    )
    ability: str = _(
        "The Isekai has no ability at the start of the game. However, once they die, the next night they are given three role choices to reincarnate as."
    )
    objective: str = _("Die, so you can be useful. :P")

    @classmethod
    async def on_death(cls, player: Player) -> None:
        roles = random.sample(
            [
                role
                for role in ROLES
                if role is not Isekai
                and not any(p for p in player.game.alive_players if p.role is role)
            ],
            3,
        )
        view: IsekaiView = IsekaiView(player, roles=roles)
        view._message = await player.member.send(
            embed=discord.Embed(
                title=_("You have died!"),
                description=_("You can choose to reincarnate as one of the following roles."),
            ),
            view=view,
        )


class Santa(Role):
    name: str = "Santa"
    side: str = "Neutral"
    description: str = _(
        "It's the time of the jolly. Looking at the Good list, however, the Santa raises his glasses to take a second look. Looks like there's only one good child this year. Time to make sure the spirit of Christmas lives on..."
    )
    ability: str = _(
        "The Santa doesn't have any special night abilities. However, they have a different goal: Keep a given target alive. If the good boi dies, they will lose faith in humanity and become a Jester."
    )
    objective: str = _("Keep the good child alive.")
    objective_secondary: bool = True
    achievements = {
        "Guardian": {
            "check": "wins",
            "value": 1,
        },
        "Holy Protection": {
            "check": "wins",
            "value": 5,
        },
        "Defender of the Weak": {
            "check": "wins",
            "value": 10,
        },
        "Castiel": {
            "check": "wins",
            "value": 25,
        },
        "From Beyond the Grave": {
            "check": lambda player: player.is_dead and player.has_won,
            "description": _("Win even after you're dead."),
        },
    }

    @classmethod
    def has_won(cls, player: Player) -> bool:
        return not player.global_target.is_dead

    @classmethod
    async def on_game_start(cls, game, player: Player) -> None:
        player.global_target = random.choice([p for p in game.players if p != player])
        try:
            await player.member.send(
                embed=discord.Embed(
                    title=_(
                        "🎅 Your target is {player.global_target.member.display_name}! 🎅"
                    ).format(player=player),
                    description=_("You must keep them alive."),
                    color=cls.color(),
                ),
            )
        except discord.HTTPException:
            pass

    @classmethod
    async def on_other_player_death(cls, player: Player, other: Player) -> None:
        if other != player.global_target:
            return
        await player.change_role(
            Jester,
            reason=_(
                "You have lost faith in humanity after failing to protect your target, {other.member.display_name}!"
            ),
        )


class Silencer(Role):
    name: str = "Silencer"
    side: str = "Mafia"
    description: str = _(
        "A figure scurries back into the house. As the person spreads the intel onto the table in relief, the door locked behind them. Looking back in fear, the person pounds on the door. Outside the window, a shadow disappears into the night..."
    )
    ability: str = _(
        "Each night, the Silencer can choose a player to silence. If their target dies that night, their role and their last words will not be revealed, but only shown to the Silencer."
    )
    visit_type: str = "Active"
    objective: str = _("Prevent the village from gathering intel.")
    achievements = {
        "Custodian": {
            "check": "wins",
            "value": 1,
        },
        "Clean as a Whistle": {
            "check": "wins",
            "value": 5,
        },
        "Neat as a Button": {
            "check": "wins",
            "value": 10,
        },
        "Sanitary Duty": {
            "check": "wins",
            "value": 25,
        },
        "Oh Strike": {
            "check": lambda player: player.has_won and not player.game_targets,
            "description": _("Win the game without silencing anyone."),
        },
    }

    perform_action = perform_action_select_targets(self_allowed=False, mafia_allowed=False)


class Shaman(Role):
    name: str = "Shaman"
    side: str = "Neutral"
    description: str = _(
        "The Mafia outside continues to bang on the door. The Shaman inside pulls out a blank voodoo doll. If they're coming with intent of harm, the Shaman won't be going down without a fight..."
    )
    ability: str = _(
        "Each night that they have a voodoo doll, the Shaman can link it to another player, causing any effects on them to instead transfer to that player.\nIf no one actively attacks Shaman on the night which they use their voodoo doll, it will vanish for the rest of the game."
    )
    visit_type: str = "Passive"
    objective: str = _("Stay alive until the end of the game.")
    objective_secondary: bool = True
    achievements = {
        "I'm Not Gon' Give Up!": {
            "check": "wins",
            "value": 1,
        },
        "Refuse to Die": {
            "check": "wins",
            "value": 5,
        },
        "Persevere": {
            "check": "wins",
            "value": 10,
        },
        "Still Standing": {
            "check": "wins",
            "value": 25,
        },
        "Not Afraid": {
            "check": lambda player: player.has_won and not player.game_targets,
            "description": _("Win the game without using your voodoo doll."),
        },
        "Kevlar": {
            "check": lambda player: player.game_targets
            and (len(player.game_targets) >= 2 or not player.voodoo_doll_vanished),
            "description": _("Have your doll redirect an attack."),
        },
    }

    @classmethod
    def has_won(cls, player: Player) -> bool:
        return not player.is_dead

    @classmethod
    async def perform_action(
        cls, night, player: Player, interaction: discord.Interaction[discord.Client]
    ) -> None:
        if player.voodoo_doll_vanished:
            raise RuntimeError(_("Your voodoo doll has vanished for the rest of the game."))
        await perform_action_select_targets(self_allowed=False)(night, player, interaction)

    @classmethod
    async def check_pt(cls, night, player: Player, p: Player, t: Player) -> Player:
        if (
            p.role.visit_type != "Passive"
            and t == player
            and not player.voodoo_doll_vanished
            and player in night.targets
            and p.role is not PrivateInvestigator
        ):
            await p.send(
                embed=discord.Embed(
                    title=_(
                        "You tried to perform your action on {t.member.display_name}, but some mysterious force transferred all the effects of your action to another player!"
                    ).format(t=t),
                ),
            )
            return night.targets[player]
        return t

    @classmethod
    async def action(cls, night, player: Player, target: Player) -> None:
        if not any(
            p
            for p, t in night.targets.items()
            if t == player and p.role.visit_type == "Active" and p.role is not PrivateInvestigator
        ):
            player.voodoo_doll_vanished = True


class Gambler(Role):
    name: str = "Gambler"
    side: str = "Villagers"
    description: str = _(
        "An addict to the evil abyss of gambling, the Gambler is willing to bet anything to feel the rush of gambling. Armed with sets of magical dice, the Gambler is well aware of the risks and rewards the dice could reap."
    )
    ability: str = _(
        "Each night, the Gambler has up to 3 dice options to throw one of them.\n- **White Dice**, *70% chance* of success. If successful, you gain a 50% chance of surviving a Mafia's attack. Otherwise, a random villager is distracted.\n- **Yellow Dice**, *50% chance* of success. If successful, a random villager is given an extra vote for the day. Otherwise, you lose one vote for the day.\n- **Red Dice**, *20% chance* of success. If successful, a random dead villager is revived. Otherwise, you die. This option only appears when at least one village side role is dead."
    )
    objective: str = _("Make good gambling decisions that won't doom the town.")
    achievements = {
        "The First Bet": {
            "check": "wins",
            "value": 1,
        },
        "Casino Owner": {
            "check": "wins",
            "value": 5,
        },
        "Card Dealer": {
            "check": "wins",
            "value": 10,
        },
        "A Perfect Bet": {
            "check": "wins",
            "value": 25,
        },
        "Hand-made Shield": {
            "check": lambda player: any(
                p for p, t in player.game_targets if t == player and p.role is not Gambler
            ),
            "description": _("Heal yourself by rolling the White Dice."),
        },
        "Helping Hand": {
            "check": lambda player: any(
                p
                for p, t in player.game_targets
                if t == player and p.role is not Gambler and p.role.side == "Mafia"
            ),
            "description": _("Give a villager an extra vote from the Yellow Dice."),
        },
        "Chance Manipulator": {
            "check": lambda player: any(
                p
                for p, t in player.game_targets
                if t == player and p.role is not Gambler and p.role.side == "Neutral"
            ),
            "description": _("Successfully revive someone from the Red Dice."),
        },
    }

    @classmethod
    async def perform_action(cls, night, player: Player, interaction: discord.Interaction) -> None:
        embed: discord.Embed = discord.Embed(
            title=_("Hey Gambler! What dice do you want to throw tonight?"),
            color=cls.color(),
        )
        embed.set_image(url="attachment://gambler.png")
        view: GamblerView = GamblerView(night, player)
        view._message = await interaction.followup.send(
            embed=embed,
            file=get_image(os.path.join("roles", "gambler")),
            view=view,
            ephemeral=True,
            wait=True,
        )

    @classmethod
    def get_dice_result(
        cls, night, player: Player
    ) -> typing.Tuple[bool, typing.Optional[Player]]:
        dice = night.gamblers_dices[player]
        if player not in night.gamblers_results:
            if dice == "white":
                if random.random() >= 0.70:
                    night.gamblers_results[player] = (True, None)
                else:
                    distracted = random.choice(
                        [p for p in night.game.alive_players if p.role.side == "Villagers"]
                    )
                    night.gamblers_results[player] = (False, distracted)
            elif dice == "yellow":
                if random.random() >= 0.50:
                    p = random.choice(
                        [p for p in night.game.alive_players if p.role.side == "Villagers"]
                    )
                    night.gamblers_results[player] = (True, p)
                else:
                    night.gamblers_results[player] = (False, None)
            elif dice == "red":
                if random.random() >= 0.20:
                    revived = random.choice(
                        [p for p in night.game.dead_players if p.role.side == "Villagers"]
                    )
                    night.gamblers_results[player] = (True, revived)
                else:
                    night.gamblers_results[player] = (False, None)
        return night.gamblers_results[player]

    @classmethod
    async def check_pt(cls, night, player: Player, p: Player, t: Player) -> Player:
        if (dice := night.gamblers_dices.get(player)) is None:
            return t
        dice_result = cls.get_dice_result(night, player)
        if dice == "white":
            if (
                dice_result[0]
                and t == player
                and p.role in (GodFather, Mafia)
                and random.random() >= 0.50
            ):
                await player.send(
                    embed=discord.Embed(
                        title=_("You have survived a Mafia's attack!"),
                    ),
                )
                raise ValueError()
            elif not dice_result[0] and p == dice_result[1] and p.role.visit_type != "Passive":
                await p.send(
                    embed=discord.Embed(
                        title=_("Sorry, you got distracted by the Gambler's dice tonight!"),
                        description=_("You were unable to perform your action."),
                    ),
                )
                raise ValueError()

    @classmethod
    async def action(cls, night, player: Player, target: Player) -> None:
        if (dice := night.gamblers_dices.get(player)) is None:
            return
        dice_result = cls.get_dice_result(night, player)
        if dice == "red":
            if dice_result[0]:
                dice_result[1].is_dead = False
                await dice_result[1].send(
                    embed=discord.Embed(
                        title=_("You have been revived by the Gambler's dice!"),
                        description=_("You are now alive and well."),
                        color=cls.color(),
                    ),
                )
            else:
                await player.kill(
                    cause=player, reason=_("They have rolled the Red Dice and lost.")
                )


PREMIUM_ROLES: typing.List[typing.Type["Role"]] = [Isekai, Santa, Silencer, Shaman, Gambler]


class Judge(Role):
    name: str = "Judge"
    side: str = "Villagers"
    description: str = _(
        "The Judge is the ultimate authority in the village. They have the power to decide the fate of the accused."
    )
    ability: str = _(
        "Each day, the Judge can choose a player to be lynched immediately. However, if they prosecute a villager, they kill their target, but also themselves. They can use their ability twice."
    )
    max_uses: int = 2
    objective: str = _("Help the village find the guilty players.")
    achievements = {
        "Attorney": {
            "check": "wins",
            "value": 1,
        },
        "Litigator": {
            "check": "wins",
            "value": 5,
        },
        "Indictor": {
            "check": "wins",
            "value": 10,
        },
        "Blow the Whistle": {
            "check": "wins",
            "value": 25,
        },
        "Indict": {
            "check": "targets",
            "value": 1,
            "description": _("Prosecute someone."),
        },
        "Triumphant Prosecution": {
            "check": lambda player: any(
                t for t in player.game_targets if t.role.side != "Villagers" or t.is_town_traitor
            ),
            "description": _("Prosecute a non-town member."),
        },
        "My bad": {
            "check": lambda player: any(t for t in player.game_targets if t.role is Jester),
            "description": _("Prosecute a Jester."),
        },
    }

    @classmethod
    async def perform_day_action(
        cls, day, player: Player, interaction: discord.Interaction
    ) -> None:
        if day.number == 1 and not day.game.config["judge_prosecute_day_1"]:
            raise RuntimeError(_("The Judge can't prosecute on Day 1."))
        embed: discord.Embed = discord.Embed(
            title=_("Hey Judge! Who do you want to prosecute today?"),
            color=cls.color(),
        )
        embed.set_image(url=cls.image_url())
        view: JudgeView = JudgeView(day, player)
        view._message = await interaction.followup.send(
            embed=embed,
            file=cls.get_image(),
            view=view,
            ephemeral=True,
            wait=True,
        )

    @classmethod
    async def day_action(cls, day, player: Player, target: Player) -> None:
        player.game_targets.append(target)
        await target.kill(cause=player, reason=_("They have been judged guilty."))
        player.uses_amount += 1
        if target.role.side == "Villagers" and not target.is_town_traitor:
            await player.kill(
                cause="suicide", reason=_("They have prosecuted an innocent Villager.")
            )


class Lawyer(Role):
    name: str = "Lawyer"
    side: str = "Villagers"
    description: str = _(
        "The Lawyer is a master of manipulation and deceit. They can defend someone each day, making them appear innocent to the town."
    )
    ability: str = _(
        "Each day, the Lawyer can choose to acquit a player on the stand. If the player has been voted guilty, they'll use 1 charge and save them from being lynched. However, if you save someone that does not belong to the Villagers team, both they and the player they saved's role will be revealed to everyone, and they'll lose their remaining usages. They can only acquit twice a game."
    )
    max_uses: int = 2
    objective: str = _("Help the village protect their allies.")
    achievements = {
        "First Defendant": {
            "check": "wins",
            "value": 1,
        },
        "Law School": {
            "check": "wins",
            "value": 5,
        },
        "Judge's Pet": {
            "check": "wins",
            "value": 10,
        },
        "Courtroom": {
            "check": "wins",
            "value": 25,
        },
        "Master of Acquital": {
            "check": "targets",
            "value": 2,
            "description": _("Acquit 2 players in the same game."),
        },
        "Self Representer": {
            "check": lambda player: player in player.game_targets,
            "description": _("Acquit yourself."),
        },
        "Not On My Watch!": {
            "check": lambda player: any(t for t in player.game_targets if t.role is Jester),
            "description": _("Acquit a Jester."),
        },
    }

    @classmethod
    async def perform_day_action(
        cls, day, player: Player, interaction: discord.Interaction, target: Player
    ) -> None:
        embed: discord.Embed = discord.Embed(
            title=_(
                "Hey Lawyer! Do you want to defend {target.member.display_name} today?"
            ).format(target=target),
            color=cls.color(),
        )
        embed.set_image(url=cls.image_url())
        fake_context = type(
            "FakeContext",
            (),
            {
                "interaction": interaction,
                "bot": interaction.client,
                "guild": interaction.guild,
                "channel": interaction.channel,
                "author": interaction.user,
                "message": interaction.message,
                "send": functools.partial(interaction.followup.send, wait=True),
            },
        )()
        if await CogsUtils.ConfirmationAsk(
            fake_context, embed=embed, file=cls.get_image(), ephemeral=True, timeout_message=None
        ):
            day.targets[player] = None
            await interaction.followup.send(
                _("You have chosen to defend {target.member.display_name}.").format(target=target),
                ephemeral=True,
            )
        else:
            day.targets.pop(player, None)
            await interaction.followup.send(
                _("You have chosen not to defend {target.member.display_name}.").format(
                    target=target
                ),
                ephemeral=True,
            )


class Blackmailer(Role):
    name: str = "Blackmailer"
    side: str = "Mafia"
    description: str = _("The Blackmailer is a master of threatening and silencing.")
    ability: str = _(
        "Every night, the Blackmailer can select a player to blackmail. Blackmailed players won't be able to speak nor vote for that day. You cannot blackmail the same player twice a row."
    )
    visit_type: str = "Active"
    objective: str = _("Help the Mafia win.")
    achievements = {
        "Extortion": {
            "check": "wins",
            "value": 1,
        },
        "Hush Money": {
            "check": "wins",
            "value": 5,
        },
        "Deceitful": {
            "check": "wins",
            "value": 10,
        },
        "Treachery": {
            "check": "wins",
            "value": 25,
        },
        "Oops": {
            "check": lambda player: any(t for t in player.game_targets if t.role.side == "Mafia"),
            "description": _("Blackmail a member of the Mafia."),
        },
        "Self Concious": {
            "check": lambda player: player in player.game_targets,
            "description": _("Blackmail yourself."),
        },
        "Gag Order": {
            "check": lambda player: any(
                len([p for p in player.game_targets if p == t]) >= 3 for t in player.game_targets
            ),
            "description": _("Blackmail the same person 3 times in the same game."),
        },
    }

    perform_action = perform_action_select_targets(self_allowed=False, mafia_allowed=False)

    @classmethod
    async def action(cls, night, player: Player, target: Player) -> None:
        await target.send(
            embed=discord.Embed(
                title=_(
                    "You have been **blackmailed**! You won't be able to speak or vote today."
                ),
                color=cls.color(),
            ),
        )


class Harbinger(Role):
    name: str = "Harbinger"
    side: str = "Mafia"
    description: str = _(
        "The Harbinger is a mysterious figure that protect their target at all costs."
    )
    ability: str = _(
        "Each night, the Harbinger can select a player to hide with. They will kill a random player that visits their target, but also reveal their own role to everyone that visits their target."
    )
    visit_type: str = "Active"
    objective: str = _("Help the Mafia win.")
    achievements = {
        "Ambushed!": {
            "check": "wins",
            "value": 1,
        },
        "From the Shadows": {
            "check": "wins",
            "value": 5,
        },
        "Never saw it coming": {
            "check": "wins",
            "value": 10,
        },
        "Lying In Wait": {
            "check": "wins",
            "value": 25,
        },
        "Surgical Precision": {
            "check": lambda player: any(
                p for p in player.game.dead_players if p.death_cause == player and p.role is Doctor
            ),
            "description": _("Assasinate a Doctor."),
        },
        "Why are you here?": {
            "check": lambda player: any(
                p
                for p in player.game.dead_players
                if p.death_cause == player and p.role is Vigilante
            ),
            "description": _("Assasinate a Vigilante."),
        },
        "One Killer": {
            "check": lambda player: any(
                p for p in player.game.dead_players if p.death_cause == player and p.role is Bomber
            ),
            "description": _("Assasinate a Bomber."),
        },
    }

    perform_action = perform_action_select_targets(self_allowed=False, mafia_allowed=False)

    @classmethod
    async def check_pt(cls, night, player: Player, p: Player, t: Player) -> Player:
        if t == night.targets.get(player) and p.role.visit_type == "Active" and p != player:
            await p.send(
                embed=discord.Embed(
                    title=_("{player.member.display_name} is {the_or_a} **{role_name}**!").format(
                        player=player, the_or_a=cls.the_or_a(night.game), role_name=cls.name
                    ),
                    description=_("They were hiding with {player.member.display_name}.").format(
                        player=player
                    ),
                    color=cls.color(),
                ).set_image(url=cls.get_image()),
                file=cls.get_image(),
            )
            possible_p = [
                p2
                for p2, t2 in night.targets.items()
                if t2 == player
                and p2.role.visit_type == "Active"
                and ROLES_PRIORITY.index(cls) > ROLES_PRIORITY.index(p2.role)
            ]
            if (len(possible_p) == 1 or random.random() < 0.3) and not any(
                p3.death_day_night_number == night.number and p3.death_cause == player
                for p3 in night.game.dead_players
            ):
                p.kill(cause=cls)
                night.targets.pop(p, None)
                raise ValueError()
        return t


class Submissor(Role):
    name: str = "Submissor"
    side: str = "Neutral"
    description: str = _("The Submissor is a coward that will do anything to save their own skin.")
    ability: str = _(
        "The first time you are attacked, you will beg mercy from the attacker and will join their side. Once the player who attacked you dies, you take on their role. If attacked the second time, you will die as you have given your life to the first attacker."
    )
    objective: str = _("Help your side win.")
    achievements = {
        "Teamer": {
            "check": "wins",
            "value": 1,
        },
        "I Can Help You": {
            "check": "wins",
            "value": 5,
        },
        "Second Chance": {
            "check": "wins",
            "value": 10,
        },
        "You Can't Kill Me": {
            "check": "wins",
            "value": 25,
        },
        "I'll Do Anything": {
            "check": lambda player: player.submissor_attacker is not None
            and player.submissor_attacker.role.side == "Mafia",
            "description": _("Submit yourself to the Mafia."),
        },
        "Don't Shoot Me!": {
            "check": lambda player: player.submissor_attacker is not None
            and player.submissor_attacker.role is Vigilante,
            "description": _("Submit yourself to a Vigilante."),
        },
        "I Need No Team": {
            "check": lambda player: player.submissor_attacker is not None
            and player.submissor_attacker.role.side == "Neutral",
            "description": _("Submit yourself to a Neutral player."),
        },
    }

    @classmethod
    def has_won(cls, player: Player) -> bool:
        return player.submissor_attacker is not None and player.submissor_attacker.has_won

    @classmethod
    async def check_pt(cls, night, player: Player, p: Player, t: Player) -> Player:
        if t != player:
            return t
        if player.submissor_attacker is not None:
            return t
        player.submissor_attacker = p
        await player.member.send(
            content=p.member.mention,
            embed=discord.Embed(
                title=_(
                    "You have been attacked by {p.member.display_name}! You have begged mercy and joined their side: **{p.role.side}**."
                ).format(p=p),
                color=p.role.color(),
            ).set_image(url=cls.image_url()),
            file=cls.get_image(),
        )
        await p.member.send(
            content=player.member.mention,
            embed=discord.Embed(
                title=_(
                    "You have been joined by {player.member.display_name}, {the_or_a} **{role_name}**!"
                ).format(player=player, the_or_a=cls.the_or_a(night.game), role_name=cls.name),
                color=cls.color(),
            ).set_image(url=cls.image_url()),
            file=cls.get_image(),
        )
        raise ValueError()

    @classmethod
    async def on_other_player_death(cls, player: Player, other: Player) -> None:
        if other != player.submissor_attacker:
            return
        await player.change_role(
            other.role,
            reason=_(
                "You have taken on the role of {other.member.display_name}, because they died."
            ).format(other=other),
        )


class Manipulator(Role):
    name: str = "Manipulator"
    side: str = "Mafia"
    description: str = _("The Manipulator is a master of deception and manipulation.")
    ability: str = _(
        "Once a game, during the day, the Manipulator can manipulate the Mafia's votes, giving them an extra vote each for that day, while hiding everyone's vote."
    )
    objective: str = _("Help the Mafia win.")
    achievements = {
        "Figurine": {
            "check": "wins",
            "value": 1,
        },
        "From the Valleys": {
            "check": "wins",
            "value": 5,
        },
        "A Shadow": {
            "check": "wins",
            "value": 10,
        },
        "Corrupt Polictian": {
            "check": "wins",
            "value": 25,
        },
        "How the turn tables": {
            "check": lambda player: player.uses_amount,
            "description": _("Manipulate the votes."),
        },
        "I have the power!": {
            "check": lambda player: any(
                p
                for p in player.game.dead_players
                if p.role is Mayor
                and p.revealed
                and p.death_cause == "voting"
                and player
                in next(
                    (
                        day_night
                        for day_night in player.game.days_nights
                        if day_night.__class__.__name__ == "Day"
                        and day_night.number == p.death_day_night_number
                    )
                ).targets
            ),
            "description": _("Lynch a revealed Mayor with your manipulated votes."),
        },
        "Too slow for me": {
            "check": lambda player: any(
                p
                for p in player.game.dead_players
                if p.role is Judge
                and p.death_cause == "voting"
                and player
                in next(
                    (
                        day_night
                        for day_night in player.game.days_nights
                        if day_night.__class__.__name__ == "Day"
                        and day_night.number == p.death_day_night_number
                    )
                ).targets
            ),
            "description": _("Lynch a Judge with your manipulated votes."),
        },
    }

    @classmethod
    async def perform_day_action(
        cls, day, player: Player, interaction: discord.Interaction
    ) -> None:
        if player.uses_amount:
            raise RuntimeError(_("You have already used your manipulation for this game."))
        embed: discord.Embed = discord.Embed(
            title=_("Hey Manipulator! Do you want to manipulate the Mafia's votes today?"),
            color=cls.color(),
        )
        embed.set_image(url=cls.image_url())
        fake_context = type(
            "FakeContext",
            (),
            {
                "interaction": interaction,
                "bot": interaction.client,
                "guild": interaction.guild,
                "channel": interaction.channel,
                "author": interaction.user,
                "message": interaction.message,
                "send": functools.partial(interaction.followup.send, wait=True),
            },
        )()
        if await CogsUtils.ConfirmationAsk(
            fake_context, embed=embed, file=cls.get_image(), ephemeral=True, timeout_message=None
        ):
            day.targets[player] = None
            await interaction.followup.send(
                _("You have chosen to manipulate the Mafia's votes."),
                ephemeral=True,
            )
        else:
            day.targets.pop(player, None)
            await interaction.followup.send(
                _("You have chosen not to manipulate the Mafia's votes."),
                ephemeral=True,
            )


class Politician(Role):
    name: str = "Politician"
    side: str = "Villagers"
    description: str = _("The Politician is a master of public speaking and manipulation.")
    ability: str = _(
        "Twice a game, during the day, you may interrupt the nomination phase by choosing a player to reveal their role to everyone, and blocking everyone from voting."
    )
    max_uses: int = 2
    objective: str = _("Help the village find the guilty players.")
    achievements = {
        "Democracy Hater": {
            "check": "wins",
            "value": 1,
        },
        "Peace Disrupter": {
            "check": "wins",
            "value": 5,
        },
        "Corrupt Leader": {
            "check": "wins",
            "value": 10,
        },
        "Protesting Maniac": {
            "check": "wins",
            "value": 25,
        },
        "Perfect Luck": {
            "check": lambda player: any(t for t in player.game_targets if t.role is Submissor),
            "description": _("Protest and reveal an unturned Submissor."),
        },
        "Quick Thinking": {
            "check": lambda player: any(t for t in player.game_targets if t.role is Mayor),
            "description": _("Protest and reveal a Mayor."),
        },
        "My Goals are Beyond Your Understanding": {
            "check": lambda player: any(t for t in player.game_targets if t.role.side == "Mafia"),
            "description": _("Protest and reveal a member of the Mafia."),
        },
    }

    perform_day_action = perform_action_select_targets(self_allowed=False)

    @classmethod
    async def day_action(cls, day, player: Player, target: Player) -> None:
        player.uses_amount += 1
        player.game_targets.append(target)
        image = target.role.name.lower().replace(" ", "_")
        await day.game.send(
            embeds=[
                discord.Embed(
                    title=_("{the_or_a} Politician has interrupted the voting phase!").format(
                        the_or_a=cls.the_or_a(day.game).capitalize()
                    ),
                    description=_(
                        "They have chosen to reveal {target.member.display_name}'s role to everyone."
                    ).format(target=target),
                    color=cls.color(),
                ).set_image(url=cls.image_url()),
                discord.Embed(
                    title=_(
                        "**{target.member.display_name}** is {the_or_a} **{role_name}**!"
                    ).format(
                        target=target, the_or_a=cls.the_or_a(day.game), role_name=target.role.name
                    ),
                    color=target.role.color(),
                ).set_image(url=target.role.image_url()),
            ],
            files=[cls.get_image(), target.role.get_image()],
        )


class Magician(Role):
    name: str = "Magician"
    side: str = "Neutral"
    description: str = _("The Magician is a master of illusions and trickery.")
    ability: str = _(
        "Each night, the Magician can select 2 players. If those 2 players live until the following night, their roles will be swapped. They can use this ability twice."
    )
    max_uses: int = 2
    visit_type: str = "Passive"
    objective: str = _("Witness the village lose.")
    achievements = {
        "Bunny in the Hat": {
            "check": "wins",
            "value": 1,
        },
        "Circus Party": {
            "check": "wins",
            "value": 5,
        },
        "Confusionist": {
            "check": "wins",
            "value": 10,
        },
        "Deceiving Trickster": {
            "check": "wins",
            "value": 25,
        },
        "No Harm Done": {
            "check": lambda player: any(
                target[0].role.side == target[1].role.side
                for night in player.game.days_nights
                if night.__class__.__name__ == "Night"
                if (target := night.targets.get(player))
            ),
            "description": _("Swap two players with the same side."),
        },
        "Shining Opportunity": {
            "check": lambda player: any(
                (target[0].role.side == "Mafia" and target[1].role is Submissor)
                or (target[0].role is Submissor and target[1].role.side == "Mafia")
                for night in player.game.days_nights
                if night.__class__.__name__ == "Night"
                if (target := night.targets.get(player))
            ),
            "description": _("Swap a member of the Mafia with an unturned Submissor."),
        },
        "Huge Mistake": {
            "check": lambda player: any(
                (target[0].role is Vigilante and target[1].role.side == "Neutral")
                or (target[0].role.side == "Neutral" and target[1].role is Vigilante)
                for night in player.game.days_nights
                if night.__class__.__name__ == "Night"
                if (target := night.targets.get(player))
            ),
            "description": _("Swap a Vigilante with a Neutral player."),
        },
    }

    perform_action = perform_action_select_targets(self_allowed=False)

    @classmethod
    async def next_end_day_action(
        cls, day, player: Player, target: typing.Tuple[Player, Player]
    ) -> None:
        player.uses_amount += 1
        role0, role1 = target[0].role, target[1].role
        reason = _("Your role has been swapped with someone else by the Magician!")
        await target[0].change_role(role1, reason=reason)
        await target[1].change_role(role0, reason=reason)


class Starspawn(Role):
    name: str = "Starspawn"
    side: str = "Neutral"
    description: str = _(
        "The Starspawn is a powerful being that can manipulate the stars to their will."
    )
    ability: str = _(
        "Each night, the Starspawn can visit a player and make them invisible. They cannot choose the same player on consecutive nights. Once a game, they can use their daybreak ability and block all day-actions from happening."
    )
    visit_type: str = "Active"
    objective: str = _("Witness the village lose.")
    achievements = {
        "Night World": {
            "check": "wins",
            "value": 1,
        },
        "Fire-y Battle": {
            "check": "wins",
            "value": 5,
        },
        "Astronomer": {
            "check": "wins",
            "value": 10,
        },
        "The Bright Star": {
            "check": "wins",
            "value": 25,
        },
        "Maximum Effect": {
            "check": lambda player: any(
                target is None
                for night in player.game.days_nights
                if night.__class__.__name__ == "Night"
                if (target := night.targets.get(player))
            )
            and len(
                {
                    p.role
                    for p in player.game.players
                    if p.role in (Judge, Lawyer, Manipulator, Politician)
                }
            )
            == 4,
            "description": _(
                "Use your daybreak ability in a game with Judge, Lawyer, Manipulator and Politician!"
            ),
        },
        "Wasted Effort": {
            "check": lambda player: any(
                target is None
                for night in player.game.days_nights
                if night.__class__.__name__ == "Night"
                if (target := night.targets.get(player))
            )
            and not {
                p.role
                for p in player.game.players
                if p.role in (Judge, Lawyer, Manipulator, Politician)
            },
            "description": _("Have your daybreak ability affect no one."),
        },
        "Guardian Angel": {
            "check": lambda player: any(
                len([p for p in player.game_targets if p == t]) >= 5 for t in player.game_targets
            ),
            "description": _("Make the same player invisible 5 times in the same game."),
        },
    }

    perform_action = perform_action_select_targets(last_target_allowed=False)

    @classmethod
    async def action(cls, night, player: Player, target: typing.Optional[Player]) -> None:
        if target is None:
            player.uses_amount += 1
        else:
            night.immune_players.append(target)


class Thief(Role):
    name: str = "Thief"
    side: str = "Neutral"
    description: str = _("The Thief is a master of stealing and deceit.")
    ability: str = _(
        "Each night, the Thief can select a player to steal from. If they have an ability with limited usages, they will be left with 0 remaining usages. Otherwise, you learn the role of that player."
    )
    visit_type: str = "Active"
    objective: str = _("Witness the village lose.")
    achievements = {
        "Swiper, No Swiping!": {
            "check": "wins",
            "value": 1,
        },
        "Apprentice in Robbery": {
            "check": "wins",
            "value": 5,
        },
        "Trinket": {
            "check": "wins",
            "value": 10,
        },
        "Pyramid Scheme": {
            "check": "wins",
            "value": 25,
        },
        "No Prosecution": {
            "check": lambda player: any(t for t in player.game_targets if t.role is Judge),
            "description": _("Steal the Judge's ability."),
        },
        "No Defense": {
            "check": lambda player: any(t for t in player.game_targets if t.role is Lawyer),
            "description": _("Steal the Lawyer's ability."),
        },
    }

    perform_action = perform_action_select_targets()

    @classmethod
    async def action(cls, night, player: Player, target: Player) -> None:
        if target.role.max_uses is not None:
            target.uses_amount = target.role.max_uses
            await player.send(
                embed=discord.Embed(
                    title=_(
                        "You have stolen from {target.member.display_name}! They have 0 usages left."
                    ).format(target=target),
                    color=cls.color(),
                ).set_image(url=cls.image_url()),
                file=cls.get_image(),
            )
        else:
            await player.send(
                embeds=[
                    discord.Embed(
                        title=_("You have stolen from {target.member.display_name}!").format(
                            target=target
                        ),
                        color=cls.color(),
                    ).set_image(url=cls.image_url()),
                    discord.Embed(
                        title=_(
                            "**{target.member.display_name}** is {the_or_a} **{role_name}**!"
                        ).format(
                            target=target,
                            the_or_a=cls.the_or_a(night.game),
                            role_name=target.role.name,
                        ),
                        color=target.role.color(),
                    ).set_image(url=target.role.image_url()),
                ],
                files=[cls.get_image(), target.role.get_image()],
            )


class Manager(Role):
    name: str = "Manager"
    side: str = "Neutral"
    description: str = _("The Manager is a master of organization and efficiency.")
    ability: str = _(
        "Each night, the Manager can visit a player to manage them. If their action is limited to a certain number of usages, they will gain an additional usage. Otherwise, they will permanently gain an extra vote. They don't learn the outcome of their action. They can't manage a player they have managed before. They can use their ability thrice."
    )
    max_uses: int = 3
    visit_type: str = "Active"
    objective: str = _("Witness the village lose.")
    achievements = {
        "Team Leader": {
            "check": "wins",
            "value": 1,
        },
        "Efficiency": {
            "check": "wins",
            "value": 5,
        },
        "Organization": {
            "check": "wins",
            "value": 10,
        },
        "Management": {
            "check": "wins",
            "value": 25,
        },
        "Extra Work": {
            "check": lambda player: any(t for t in player.game_targets if t.uses_amount),
            "description": _("Manage a player with limited usages."),
        },
        "Extra Vote": {
            "check": lambda player: any(t for t in player.game_targets if t.role is not Manager),
            "description": _("Manage a player without limited usages."),
        },
    }

    perform_action = perform_action_select_targets(
        self_allowed=False,
        condition=lambda player, target: target not in player.game_targets,
    )

    @classmethod
    async def action(cls, night, player: Player, target: Player) -> None:
        player.uses_amount += 1
        if target.uses_amount:
            target.uses_amount -= 1
            await player.send(
                embed=discord.Embed(
                    title=_(
                        "You have managed {target.member.display_name}! They have gained an additional usage."
                    ).format(target=target),
                    color=cls.color(),
                ).set_image(url=cls.image_url()),
                file=cls.get_image(),
            )
        else:
            target.extra_votes += 1
            await player.send(
                embed=discord.Embed(
                    title=_(
                        "You have managed {target.member.display_name}! They have gained an extra vote."
                    ).format(target=target),
                    color=cls.color(),
                ).set_image(url=cls.image_url()),
                file=cls.get_image(),
            )


class Guardian(Role):
    name: str = "Guardian"
    side: str = "Villagers"
    description: str = _("The Guardian is a protector of the innocent and a defender of the weak.")
    ability: str = _(
        "Each night, the Guardian can select a player to protect. If that player is attacked, the Guardian will block the attack and kill the attacker instead, dying alongside with them. If the Guardian protects themselves, they will not die, but will not kill the attacker either. They cannot protect the same player twice a row."
    )
    visit_type: str = "Active"
    objective: str = _("Help the village protect their allies.")
    achievements = {
        "Bodyguard": {
            "check": "wins",
            "value": 1,
        },
        "Tough Guy": {
            "check": "wins",
            "value": 5,
        },
        "Chaperon": {
            "check": "wins",
            "value": 10,
        },
        "Warden": {
            "check": "wins",
            "value": 25,
        },
        "I'll save you!": {
            "check": lambda player: any(
                t != player for t in player.guardian_successfully_protected_players
            ),
            "description": _("Successfully protect someone from being attacked."),
        },
        "You can't hurt me.": {
            "check": lambda player: player in player.guardian_successfully_protected_players,
            "description": _("Successfully protect yourself from being attacked."),
        },
        "It takes two to tango": {
            "check": lambda player: any(
                p
                for p in player.game.dead_players
                if p.death_cause == player and p.role is GodFather
            ),
            "description": _("Take down the Godfather as you die."),
        },
    }

    perform_action = perform_action_select_targets(last_target_allowed=False)

    @classmethod
    async def check_pt(cls, night, player: Player, p: Player, t: Player) -> Player:
        if t == night.targets.get(player) and p.role in (
            GodFather,
            Mafia,
            Vigilante,
            Bomber,
            PlagueDoctor,
            Hoarder,
            Alchemist,
        ):
            player.guardian_successfully_protected_players.append(t)
            if t != player:
                await p.kill(
                    cause=player,
                    reason=_("They have attacked a player protected by the Guardian."),
                )
                player.kill(
                    cause="suicide", reason=_("They have protected a player from an attack.")
                )
            raise ValueError()
        return t


class Mortician(Role):
    name: str = "Mortician"
    side: str = "Villagers"
    description: str = _("The Mortician is a master of post-mortem investigations.")
    ability: str = _(
        "Every other night, the Mortician can select a dead player to identify their attacker. They will obtain three suspects that might have killed their target."
    )
    visit_type: str = "Passive"
    objective: str = _("Help the village win.")
    achievements = {
        "Post-Mortem Investigator": {
            "check": "wins",
            "value": 1,
        },
        "Forensic Expert": {
            "check": "wins",
            "value": 5,
        },
        "Crime Scene Analyst": {
            "check": "wins",
            "value": 10,
        },
        "Master of the Morgue": {
            "check": "wins",
            "value": 25,
        },
        "Postmoterm": {
            "check": "targets",
            "value": 1,
            "description": _("Autopsy a body."),
        },
        "Master of Dissection": {
            "check": lambda player: len({t.death_cause for t in player.game_targets}) >= 3,
            "description": _(
                "Autopsy 3 bodies that were killed by different killers in the same game."
            ),
        },
        "Exploded Corpse": {
            "check": lambda player: any(
                t for t in player.game_targets if getattr(t.death_cause, "role", None) is Bomber
            ),
            "description": _("Autopsy a body that was killed by the Bomber."),
        },
    }

    perform_action = perform_action_select_targets(
        self_allowed=False,
        condition=lambda player, target: not getattr(target.death_cause, "is_dead", False),
    )

    @classmethod
    async def action(cls, night, player: Player, target: Player) -> None:
        suspects = [target.death_cause] + random.sample(
            [p for p in player.game.alive_players if p != target.death_cause], 2
        )
        await player.send(
            embed=discord.Embed(
                title=_("Investigation Results"),
                description=_(
                    "The suspects for the death of {target.member.display_name} are: {suspects}."
                ).format(
                    target=target,
                    suspects=humanize_list(
                        [
                            f"{player.member.display_name} ({player.member.name})"
                            for player in suspects
                        ]
                    ),
                ),
                color=cls.color(),
            )
        )


class Baker(Role):
    name: str = "Baker"
    side: str = "Neutral"
    description: str = _("The Baker is a master of baking and cooking.")
    ability: str = _(
        "Each night, the Baker can select a player to give bread to. The player receiving the bread might gain an additional vote for that day, healed from Mafia attacks, distracted or lose the ability to vote for that day. The Baker will win once the required number of alive players have bread, and their only win condition is to survive. They may continue giving bread after they have won."
    )
    visit_type: str = "Active"
    objective: str = _("Give the required amount of alive players bread.")
    objective_secondary: bool = True
    achievements = {
        "Bread": {
            "check": "wins",
            "value": 1,
        },
        "Baguette Man": {
            "check": "wins",
            "value": 5,
        },
        "Certified Bakery": {
            "check": "wins",
            "value": 10,
        },
        "Wholemeal": {
            "check": "wins",
            "value": 25,
        },
        "Quick bake": {
            "check": lambda player: len(player.game_targets) >= 3,
            "description": _("Give bread to 3 players in the same game."),
        },
        "Moldy Bread": {
            "check": lambda player: all(
                night.bakers_effects.get(player) in ("distracted", "lose_vote")
                for night in player.game.days_nights
                if night.__class__.__name__ == "Night"
                if night.targets.get(player)
            ),
            "description": _("Have all of your breads give negative effects to players."),
        },
        "Perfect Baker": {
            "check": lambda player: all(
                night.bakers_effects.get(player) in ("extra_vote", "healed_from_mafia_attacks")
                for night in player.game.days_nights
                if night.__class__.__name__ == "Night"
                if night.targets.get(player)
            ),
            "description": _("Have all of your breads give positive effects to players."),
        },
    }

    @classmethod
    def has_won(cls, player: Player) -> bool:
        return (
            not player.is_dead
            and len({t for t in player.game_targets if not t.is_dead})
            >= len(player.game.players) // 3
        )

    @classmethod
    async def perform_action(cls, night, player: Player, interaction: discord.Interaction) -> None:
        EFFECTS = ["extra_vote", "healed_from_mafia_attacks", "distracted", "vote_lost"]
        if player not in night.bakers_effects:
            night.bakers_effects[player] = random.choice(list(EFFECTS))
        await perform_action_select_targets(self_allowed=False)(night, player, interaction)

    @classmethod
    async def check_pt(cls, night, player: Player, p: Player, t: Player) -> Player:
        if (target := night.targets.get(player)) is None:
            return t
        effect = night.bakers_effects[player]
        if effect == "healed_from_mafia_attacks" and t == target and p.role in (GodFather, Mafia):
            raise ValueError()
        elif effect == "distracted" and p == target and p.role.visit_type != "Passive":
            await p.send(
                embed=discord.Embed(
                    title=_("Sorry, you got distracted by the bread you received!"),
                    description=_("You were unable to perform your action."),
                    color=cls.color(),
                ).set_image(url=cls.get_image()),
                file=cls.get_image(),
            )
            raise ValueError()
        return t


class Cupid(Role):
    name: str = "Cupid"
    side: str = "Neutral"
    description: str = _(
        "Cupid is a mischievous matchmaker who loves to play with people's hearts."
    )
    ability: str = _(
        "On the first night, the Cupid can choose two players to become lovers. If they don't, two players will be selected randomly. If one lover dies, the other will commit suicide and the Cupid will become a Killer and gain the ability to kill each night. If the Cupid dies, the lovers become Killers."
    )
    objective: str = _("Ensure the lovers survive until the end of the game.")
    objective_secondary: bool = True
    achievements = {
        "Love Maker": {
            "check": "wins",
            "value": 1,
        },
        "Valentine's Gift": {
            "check": "wins",
            "value": 5,
        },
        "Angel from Heaven": {
            "check": "wins",
            "value": 10,
        },
        "Master of Couple": {
            "check": "wins",
            "value": 25,
        },
        "Easy Passion": {
            "check": lambda player: player.lovers[0].role == player.lovers[1].role,
            "description": _("Have a couple be formed by two players from the same side."),
        },
        "Pandora's Box": {
            "check": lambda player: {player.lovers[0].role, player.lovers[1].role}
            == {"Mafia", "Villagers"},
            "description": _(
                "Have a couple be formed by a member of the Mafia and a Villagers' player."
            ),
        },
        "The A-team": {
            "check": lambda player: player.has_won and not player.is_dead,
            "description": _("Win a game where you and your couple are both alive."),
        },
    }

    @classmethod
    def has_won(cls, player: Player) -> bool:
        return all(not lover.is_dead for lover in player.cupid_lovers)

    perform_action = perform_action_select_targets(targets_number=2)

    @classmethod
    async def action(
        cls, night, player: Player, target: typing.Optional[typing.Tuple[Player, Player]]
    ) -> None:
        if night.number != 1:
            raise RuntimeError(_("You can only use your ability on the first night."))
        lovers = target or tuple(random.sample([p for p in night.game.players if p != player], 2))
        player.cupid_lovers = lovers
        for lover in lovers:
            await lover.member.send(
                embed=discord.Embed(
                    title=_("You have been struck by Cupid's arrow!"),
                    description=_(
                        "You are now in love with {other_lover.member.display_name} ({other_lover.member.name}). If they die, you will die too. If your Cupid die, you will become a Killer."
                    ).format(other_lover=lovers[1] if lover == lovers[0] else lovers[0]),
                    color=cls.color(),
                ).set_image(url=cls.image_url()),
                file=cls.get_image(),
            )
        await player.member.send(
            embed=discord.Embed(
                title=_(
                    "You have struck **{lover1.member.display_name} ({lover1.member.name})** and **{lover2.member.display_name} ({lover2.member.name})** with your arrow!"
                ).format(lover1=lovers[0], lover2=lovers[1]),
                description=_(
                    "They are now in love with each other. If your lovers die, you will become a Killer."
                ),
                color=cls.color(),
            ).set_image(url=cls.image_url()),
            file=cls.get_image(),
        )

    @classmethod
    async def no_action(cls, night, player: Player) -> None:
        if night.number == 1:
            await cls.action(night, player, None)

    @classmethod
    async def on_death(cls, player: Player) -> None:
        for lover in player.cupid_lovers:
            await lover.change_role(
                Killer,
                reason=_(
                    "Your Cupid has died! You are now a Killer and can vote to kill someone each night."
                ),
            )
            lover.game_targets.clear()

    @classmethod
    async def on_other_player_death(cls, player: Player, other: Player) -> None:
        if other in player.cupid_lovers:
            for lover in player.cupid_lovers:
                if lover != other:
                    if lover.is_dead:
                        return
                    await lover.kill(
                        cause="suicide",
                        reason=_("They saw their lover die and couldn't bear the pain."),
                    )
            await player.change_role(
                Killer,
                reason=_(
                    "Your lovers have died! You are now a Killer and can kill someone each night."
                ),
            )
            player.game_targets.clear()


class Killer(Role):
    name: str = "Killer"
    side: str = "Neutral"
    description: str = _(
        "The Killer is a ruthless murderer who will stop at nothing to achieve their goal."
    )
    ability: str = _(
        "Each night, the Killer can select a player to kill. If there is several Killers in the game, who target different players, nothing happens. They can't kill other Killers."
    )
    objective: str = _("Kill all players.")
    starting: bool = False
    achievements = {
        "First Blood": {
            "check": "wins",
            "value": 1,
        },
        "Serial Killer": {
            "check": "wins",
            "value": 5,
        },
        "Mass Murderer": {
            "check": "wins",
            "value": 10,
        },
        "Ultimate Killer": {
            "check": "wins",
            "value": 25,
        },
        "Perfect Kill": {
            "check": "targets",
            "value": 3,
            "description": _("Kill at least 3 players in the same game."),
        },
    }

    @classmethod
    def has_won(cls, player: Player) -> bool:
        return not player.is_dead and all(p.role is Killer for p in player.game.alive_players)

    perform_action = perform_action_select_targets(
        self_allowed=False,
        last_target_allowed=False,
        condition=lambda player, target: target.role is not Killer,
    )

    @classmethod
    async def action(cls, night, player: Player, target: Player) -> None:
        killers = [p for p in night.game.alive_players if p.role is Killer]
        targets = [t for killer in killers if (t := night.targets.get(killer)) is not None]
        if len(set(targets)) == 1:
            await targets[0].kill(cause=random.choice(killers))
        else:
            for killer in killers:
                await killer.send(
                    embed=discord.Embed(
                        title=_("The Killers couldn't agree on a target!"),
                        description=_("No one was killed."),
                        color=cls.color(),
                    ),
                )


class Oracle(Role):
    name: str = "Oracle"
    side: str = "Villagers"
    description: str = _("The Oracle is a protector of the town.")
    ability: str = _(
        "Each night, the Oracle can select a Villagers' role to make all players with that role invisible."
    )
    objective: str = _("Help the village win.")
    achievements = {
        "Hidden Talent": {
            "check": "wins",
            "value": 1,
        },
        "From Above": {
            "check": "wins",
            "value": 5,
        },
        "Roleblocker": {
            "check": "wins",
            "value": 10,
        },
        "Master of Invisibility": {
            "check": "wins",
            "value": 25,
        },
        "True Vision": {
            "check": lambda player: any(
                any(
                    all(
                        t not in n.targets
                        for n in player.game.days_nights
                        if n.__class__.__name__ == "Night" and n.number < night.number
                    )
                    for t in player.game.players
                    if t.role is Mayor
                    and (
                        t.death_day_night_number is None or t.death_day_night_number > night.number
                    )
                )
                for night in player.game.days_nights
                if night.__class__.__name__ == "Night"
                if night.targets.get(player) is Mayor
            ),
            "description": _("Make an unrevealed Mayor invisible."),
        },
        "Everyone's Invisible": {
            "check": lambda player: len(
                {
                    t
                    for night in player.game.days_nights
                    if night.__class__.__name__ == "Night"
                    if (target := night.targets.get(player)) is not None
                    for t in [
                        t
                        for t in player.game.players
                        if t.role is Mayor
                        and (
                            t.death_day_night_number is None
                            or t.death_day_night_number > night.number
                        )
                    ]
                }
            )
            >= 5,
            "description": _("Successfully make 5 different players invisible in the same game."),
        },
    }

    perform_action = perform_action_select_roles(
        mafia_allowed=False,
        condition=lambda player, role: role.side == "Villagers",
    )

    @classmethod
    async def action(cls, night, player: Player, target: typing.Type[Role]) -> None:
        if target not in player.game_targets:
            for p in night.game.alive_players:
                if p.role is target:
                    night.immune_players.append(p)
        else:
            number = len([p for p in night.game.alive_players if p.role is target])
            await player.send(
                embed=discord.Embed(
                    title=_("There are {number} {target.name}{s} alive in the game.").format(
                        number=number, target=target, s="" if number == 1 else "s"
                    ),
                    color=cls.color(),
                ),
            )


class Ritualist(Role):
    name: str = "Ritualist"
    side: str = "Mafia"
    description: str = _(
        "The Ritualist is a master of dark arts, using rituals to eliminate their enemies."
    )
    ability: str = _(
        "Each night, the Ritualist can select a player and guess their role. If they guess correctly, the player will be killed. Otherwise, the Ritualist's role will be revealed to everyone. This action can be used three times."
    )
    max_uses: int = 3
    objective: str = _("Help the Mafia win.")
    achievements = {
        "Traditional": {
            "check": "wins",
            "value": 1,
        },
        "Activist": {
            "check": "wins",
            "value": 5,
        },
        "Blood Circle": {
            "check": "wins",
            "value": 10,
        },
        "Sorcerer's Apprentice": {
            "check": "wins",
            "value": 25,
        },
        "Successful Sacrifice": {
            "check": lambda player: any(
                p for p in player.game.dead_players if p.death_cause == player
            ),
            "description": _("Successfully perform a ritual."),
        },
        "Too Easy": {
            "check": lambda player: any(
                p.side == "Villagers" for p in player.game.dead_players if p.death_cause == player
            ),
            "description": _("Perform all 3 rituals on Villagers' players."),
        },
    }

    perform_action = perform_action_guess_targets_roles(self_allowed=False, mafia_allowed=False)

    @classmethod
    async def action(
        cls, night, player: Player, target: typing.Tuple[Player, typing.Type[Role]]
    ) -> None:
        player.uses_amount += 1
        if target[0].role is target[1]:
            await target[0].kill(
                cause=player,
                reason=_("The Ritualist has guessed their role correctly."),
            )
        else:
            await night.game.send(
                embeds=[
                    discord.Embed(
                        title=_(
                            "The Ritualist has guessed wrong! Their role is now revealed to everyone."
                        ),
                    ),
                    discord.Embed(
                        title=_("{player.member.display_name} is the **Ritualist**!").format(
                            player=player
                        ),
                        color=cls.color(),
                    ).set_image(url=cls.image_url()),
                ],
                file=cls.get_image(),
            )


class Necromancer(Role):
    name: str = "Necromancer"
    side: str = "Mafia"
    description: str = _(
        "The Necromancer is a master of the dark arts, able to reanimate the dead."
    )
    ability: str = _(
        "Every night, the Necromancer can select a dead player to reanimate, and a living player to target. Any feedback that the dead player would receive will instead be redirected to the Necromancer. If the dead player requires multiple inputs, they will not respond. The Necromancer can't reanimate corpses that they have used before. Additionally, once a game, they may revive a dead player that they have not used as a corpse. That player will only be revived at the end of the day if the Necromancer is alive."
    )
    visit_type: str = "Active"
    objective: str = _("Help the Mafia win.")
    achievements = {
        "Necromancy": {
            "check": "wins",
            "value": 1,
        },
        "The Undead": {
            "check": "wins",
            "value": 5,
        },
        "Rising Corpses": {
            "check": "wins",
            "value": 10,
        },
        "Zombie Apocalypse": {
            "check": "wins",
            "value": 25,
        },
        "Final Retribution": {
            "check": lambda player: any(
                t[0].role is Vigilante and getattr(t[1].death_cause, "role", None) is Vigilante
                for t in player.game_targets
            ),
            "description": _("Reanimate a Vigilante and shoot someone."),
        },
        "New God Father": {
            "check": lambda player: any(
                t[0].role is GodFather and getattr(t[1].death_cause, "role", None) is GodFather
                for t in player.game_targets
            ),
            "description": _("Reanimate a GodFather and kill someone."),
        },
    }

    @classmethod
    async def perform_action(cls, night, player: Player, interaction: discord.Interaction) -> None:
        await perform_action_select_targets(
            targets_number=2,
            self_allowed=False,
            condition=lambda player, target: not any(t[0] is target for t in player.game_targets),
            two_selects=True,
            second_select_optional=not player.use_amount,
        )(night, player, interaction)

    @classmethod
    async def action(
        cls, night, player: Player, target: typing.Tuple[Player, typing.Optional[Player]]
    ) -> None:
        if target[1] is not None:
            _target = target[1]
            try:
                await target[0].role.action(
                    night,
                    player,
                    _target,
                )
            except NotImplementedError:
                pass

    @classmethod
    async def next_end_day_action(
        cls, day, player: Player, target: typing.Tuple[Player, typing.Optional[Player]]
    ) -> None:
        if target[1] is None:
            player.uses_amount += 1
            target[0].is_dead = False
            await player.game.send(
                embed=discord.Embed(
                    title=_(
                        "The Necromancer has revived **{target.member.display_name}**!"
                    ).format(target=target[0]),
                    color=cls.color(),
                ).set_thumbnail(url=cls.image_url()),
                file=cls.get_image(),
            )


MORE_ROLES: typing.List[typing.Type["Role"]] = [
    Judge,
    Lawyer,
    Blackmailer,
    Harbinger,
    Submissor,
    Manipulator,
    Politician,
    Magician,
    Starspawn,
    Thief,
    Manager,
    Guardian,
    Mortician,
    Baker,
    Cupid,
    Killer,
    Oracle,
    Ritualist,
    Necromancer,
]


ROLES: typing.List[typing.Type["Role"]] = (
    CLASSIC_ROLES
    + CRAZY_ROLES
    + CHAOS_ROLES
    + CORONA_ROLES
    + CRIMSON_ROLES
    + PREMIUM_ROLES
    + MORE_ROLES
)

ROLES_PRIORITY: typing.List[typing.Type["Role"]] = [
    Submissor,
    Gambler,
    Oracle,
    Shaman,
    Goose,
    Mimic,
    Harbinger,
    Distractor,
    Necromancer,
    Starspawn,
    Santa,
    Silencer,
    Framer,
    Baiter,
    Guardian,
    Jester,
    Executioner,
    Alchemist,
    MafiaAlchemist,
    VillagerAlchemist,
    Doctor,
    Baker,
    Bomber,
    GodFather,
    Mafia,
    Killer,
    Hoarder,
    Vigilante,
    Ritualist,
    Cupid,
    Mayor,
    Blackmailer,
    Mortician,
    Detective,
    PrivateInvestigator,
    Hacker,
    Spy,
    Watcher,
    Link,
    Manager,
    Magician,
    Thief,
    PlagueDoctor,
    Isekai,
] + [Judge, Lawyer, Manipulator, Politician, Villager]
MAFIA_HIERARCHY: typing.List[typing.Type["Role"]] = [
    GodFather,
    Mafia,
    Manipulator,
    Politician,
    Ritualist,
    Framer,
    Hacker,
    Necromancer,
    Goose,
    Mimic,
    Blackmailer,
    Silencer,
    Harbinger,
    MafiaAlchemist,
]


ACHIEVEMENTS: typing.Dict[
    str,
    typing.Dict[
        typing.Literal["check", "value", "description"],
        typing.Union[
            typing.Literal["wins", "games", "win_without_dying"],
            typing.Optional[
                typing.Union[int, typing.Type["Role"], typing.List[typing.Type["Role"]]]
            ],
        ],
    ],
] = {
    "Welcome": {
        "check": "games",
        "value": 1,
    },
    "Initiation": {
        "check": "wins",
        "value": 1,
    },
    "Novice": {
        "check": "wins",
        "value": 5,
    },
    "Apprentice": {
        "check": "wins",
        "value": 10,
    },
    "Dedicated": {
        "check": "wins",
        "value": 25,
    },
    "Patriarch": {
        "check": "wins",
        "value": 50,
    },
    "Zealous": {
        "check": "wins",
        "value": 100,
    },
    "Iconic": {
        "check": "wins",
        "value": 250,
    },
    "The Perfect Town": {
        "check": lambda player: player.has_won
        and all(not p.is_dead for p in player.game.players if p.role.side == "Villagers"),
        "description": _("Win with all Villagers' players still alive."),
    },
    "Marathon": {
        "check": lambda player: player.game.current_number >= 10,
        "description": _("Have a game that last 10 days."),
    },
    "Half Way There": {
        "check": lambda wins: sum(
            wins.get(role, 0) > 0 for role in ROLES if role.side == "Villagers"
        )
        >= len([role for role in ROLES if role.side == "Villagers"]) // 2,
        "description": _("Win with half of the Villagers' roles."),
    },
    "The Sicilian Mafia": {
        "check": lambda player: player.has_won
        and all(not p.is_dead for p in player.game.players if p.role.side == "Mafia"),
        "description": _("Win with all Mafia members still alive."),
    },
    "Discipline for Crime": {
        "check": lambda wins: sum(wins.get(role, 0) > 0 for role in ROLES if role.side == "Mafia")
        >= len([role for role in ROLES if role.side == "Mafia"]) // 2,
        "description": _("Win with half of the Mafia roles."),
    },
    "Pacifist in Training": {
        "check": lambda wins: sum(
            wins.get(role, 0) > 0 for role in ROLES if role.side == "Neutral"
        )
        >= len([role for role in ROLES if role.side == "Neutral"]) // 2,
        "description": _("Win with half of the Neutral roles."),
    },
    "Fifty-fifty": {
        "check": lambda wins: sum(wins.get(role, 0) > 0 for role in ROLES) >= len(ROLES) // 2,
        "description": _("Win with half of the roles."),
    },
    "Adept of the Village": {
        "check": lambda wins: sum(
            wins.get(role, 0) > 0 for role in ROLES if role.side == "Villagers"
        )
        >= len([role for role in ROLES if role.side == "Villagers"]),
        "description": _("Win with all Villagers' roles."),
    },
    "Adept of the Mafia": {
        "check": lambda wins: sum(wins.get(role, 0) > 0 for role in ROLES if role.side == "Mafia")
        >= len([role for role in ROLES if role.side == "Mafia"]),
        "description": _("Win with all Mafia roles."),
    },
    "Indifferent": {
        "check": lambda wins: sum(
            wins.get(role, 0) > 0 for role in ROLES if role.side == "Neutral"
        )
        >= len([role for role in ROLES if role.side == "Neutral"]),
        "description": _("Win with all Neutral roles."),
    },
    "Expert in Mafia": {
        "check": lambda wins: sum(wins.get(role, 0) > 0 for role in ROLES) >= len(ROLES),
        "description": _("Win with all roles."),
    },
}

for i, achievements in enumerate([ACHIEVEMENTS] + [role.achievements for role in ROLES]):
    role = ROLES[i - 1] if i != 0 else None
    for achievement, data in achievements.items():
        if "description" not in data:
            if data["check"] == "wins":
                if data["value"] == 1:
                    data["description"] = _("Win your first game{as_role}.").format(
                        as_role=_(" as {role.name}").format(role=role) if role is not None else ""
                    )
                else:
                    data["description"] = _("Win {value} games{as_role}.").format(
                        value=data["value"],
                        as_role=_(" as {role.name}").format(role=role) if role is not None else "",
                    )
            elif data["check"] == "games":
                if data["value"] == 1:
                    data["description"] = _("Play your first game{as_role}.").format(
                        as_role=_(" as {role.name}").format(role=role) if role is not None else ""
                    )
                else:
                    data["description"] = _("Play {value} games{as_role}.").format(
                        value=data["value"],
                        as_role=_(" as {role.name}").format(role=role) if role is not None else "",
                    )
            elif data["check"] == "win_without_dying":
                data["description"] = _("Win the game{as_role} without dying.").format(
                    as_role=_(" as {role.name}").format(role=role) if role is not None else ""
                )

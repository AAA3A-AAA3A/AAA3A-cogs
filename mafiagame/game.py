from AAA3A_utils import CogsUtils  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import asyncio
import datetime
import io
import os
import random
from dataclasses import dataclass, field

import chat_exporter
from redbot.core import bank
from redbot.core.errors import BalanceTooHigh
from redbot.core.utils.chat_formatting import humanize_list

from .anomalies import (
    ANOMALIES,
    Anomaly,
    BlindingLights,
    CatsTongue,
    DejaVu,
    FoggyMist,
    LightningRound,
)  # NOQA
from .constants import (
    ACHIEVEMENTS_COLOR,
    DAY_COLOR,
    MAFIA_COLOR,
    NIGHT_COLOR,
    VILLAGERS_COLOR,
    VOTING_AND_JUDGEMENT_COLOR,
)  # NOQA
from .modes import Classic, Mode
from .roles import (
    ACHIEVEMENTS,
    MAFIA_HIERARCHY,
    ROLES,
    ROLES_PRIORITY,
    TARGET_TYPE_HINT,
    Alchemist,
    Blackmailer,
    Doctor,
    Gambler,
    GodFather,
    Lawyer,
    Mafia,
    MafiaAlchemist,
    Manipulator,
    Mayor,
    Player,
    Politician,
    VillagerAlchemist,
)  # NOQA
from .utils import get_image
from .views import JudgementView, PerformActionView, SpectateView, StartMessageView, VoteView

_: Translator = Translator("MafiaGame", __file__)


@dataclass
class DayNight:
    game: "Game"
    number: int
    targets: typing.Dict[Player, TARGET_TYPE_HINT] = field(default_factory=dict)

    async def start(self) -> None:
        embed: discord.Embed = discord.Embed(
            title=_(
                _("🌙 Night {number} 🌙") if isinstance(self, Night) else _("🌞 Day {number} 🌞")
            ).format(number=self.number),
            color=NIGHT_COLOR if isinstance(self, Night) else DAY_COLOR,
        )
        embed.add_field(
            name=_("Currently alive:"),
            value="\n".join(
                [
                    f"😃 {player.member.mention}"
                    + (f" (Mayor)" if player.role is Mayor and player.revealed else "")
                    for player in self.game.alive_players
                ]
            ),
        )
        embed.add_field(
            name=_("Currently dead:"),
            value="\n".join(
                [
                    f"☠️ {player.member.mention}"
                    + (
                        f" ({player.role.name}{_(' - Town Traitor') if player.is_town_traitor else ''})"
                        if self.game.config["show_dead_role"]
                        else ""
                    )
                    for player in self.game.dead_players
                ]
            )
            or _("No one is dead yet..."),
        )
        embed.set_image(
            url=f"attachment://{'night.png' if isinstance(self, Night) else 'day.png'}"
        )
        await self.game.send(
            embed=embed,
            file=get_image("night" if isinstance(self, Night) else "day"),
        )


@dataclass
class Night(DayNight):
    immune_players: typing.List[Player] = field(default_factory=list)
    plague_doctor_warning: bool = False
    alchemists_potions: typing.Dict[
        Player, typing.Literal["lethal", "invisibility", "truth", "mundane"]
    ] = field(default_factory=dict)
    gamblers_dices: typing.Dict[Player, typing.Literal["white", "yellow", "red"]] = field(
        default_factory=dict
    )
    gamblers_results: typing.Dict[Player, typing.Tuple[bool, typing.Optional[Player]]] = field(
        default_factory=dict
    )
    bakers_effects: typing.Dict[
        Player,
        typing.Literal["extra_vote", "healed_from_mafia_attacks", "distracted", "vote_lost"],
    ] = field(default_factory=dict)

    async def start(self) -> None:
        await super().start()
        await asyncio.sleep(2)
        embed: discord.Embed = discord.Embed(
            title=_("Night falls... 🌙"),
            description=_(
                "Alright everyone, close your eyes and let the night begin. It's 🔪 story time 🔪!"
            ),
            color=NIGHT_COLOR,
        )
        embed.set_image(url="attachment://sleep.png")
        embed.set_footer(text=_("Don't panic, I've muted all of you."))
        view: PerformActionView = PerformActionView(self)
        view._message = await self.game.send(
            embed=embed,
            view=view,
            file=get_image("sleep"),
        )
        self.game.cog.views[view._message] = view
        await asyncio.sleep(self.game.config["perform_action_timeout"])
        await view.on_timeout()
        view.stop()

        self.targets = {
            player: target
            for player, target in sorted(
                self.targets.items(),
                key=lambda item: (
                    ROLES_PRIORITY.index(item[0].role),
                    self.game.players.index(item[0]),
                ),
            )
        }
        for player in self.game.alive_players:
            if player in self.targets:
                self.game.afk_players.pop(player, None)
                continue
            self.game.afk_players.setdefault(player, 0)
            self.game.afk_players[player] += 1
        if not any(player.role is GodFather for player in self.targets):
            if self.game.current_anomaly is not FoggyMist:
                await self.game.send(
                    embed=discord.Embed(
                        title=_("The Mafia was too lazy to kill anyone tonight..."),
                        color=MAFIA_COLOR,
                    ),
                )
        for player, target in self.targets.copy().items():
            if player.is_dead:
                self.targets.pop(player, None)
                continue
            if (
                self.game.current_anomaly is BlindingLights
                and player in self.game.current_anomaly_players
            ):
                self.targets.pop(player, None)
                continue
            if (
                player.role is GodFather
                and (
                    mafia_player := next(
                        (player for player in self.game.alive_players if player.role is Mafia),
                        None,
                    )
                )
                is not None
            ):
                player = mafia_player
            if target is not None:
                try:
                    for tg in [target] if not isinstance(target, typing.Tuple) else target:
                        if not isinstance(tg, Player):
                            continue
                        for p in sorted(
                            [
                                p
                                for p in self.game.alive_players
                                if ROLES_PRIORITY.index(p.role) < ROLES_PRIORITY.index(player.role)
                            ],
                            key=lambda p: ROLES_PRIORITY.index(p.role),
                        ):
                            try:
                                tg = await p.role.check_pt(self, p, player, tg)
                            except NotImplementedError:
                                pass
                            if not isinstance(target, typing.Tuple):
                                self.targets[player] = tg
                            else:
                                t = list(self.targets[player])
                                t[t.index(target)] = tg
                                self.targets[player] = tuple(t)
                        if tg.is_dead:
                            if player.role in (GodFather, Mafia):
                                if self.game.current_anomaly is not FoggyMist:
                                    await self.game.send(
                                        embed=discord.Embed(
                                            title=_(
                                                "The Mafia visited {tg.member.display_name} tonight, but they were already dead!"
                                            ).format(tg=tg),
                                            color=MAFIA_COLOR,
                                        ),
                                    )
                            del self.targets[player]
                            raise ValueError()
                        if tg.immune or tg in self.immune_players:
                            await player.send(
                                embed=discord.Embed(
                                    title=_("{tg.member.display_name} hasn't been found!").format(
                                        tg=tg
                                    ),
                                    description=_("You were unable to perform your action."),
                                ),
                            )
                            del self.targets[player]
                            raise ValueError()
                        if player.role.visit_type != "Passive" and player.infected:
                            tg.infected = False
                except ValueError:
                    self.targets.pop(player, None)
                    continue
            if player.role is not Doctor or target in [
                t for p, t in self.targets.items() if p.role is GodFather
            ]:
                player.game_targets.append(target)
            try:
                await player.role.action(self, player, target)
            except NotImplementedError:
                pass
        if (afk_days_before_kick := self.game.config["afk_days_before_kick"]) is not None:
            for player, days in self.game.afk_players.copy().items():
                if days >= afk_days_before_kick:
                    await player.kill(cause="afk", reason=_("They were AFK for too long."))
                    if (
                        afk_temp_ban_duration := self.game.config["afk_temp_ban_duration"]
                    ) is not None:
                        await self.game.cog.config.member(player.member).temp_ban_until.set(
                            int(
                                (
                                    datetime.datetime.now(tz=datetime.timezone.utc)
                                    + datetime.timedelta(hours=afk_temp_ban_duration)
                                )
                                .replace(second=0, microsecond=0)
                                .timestamp()
                            )
                        )
        for player in self.game.alive_players:
            if player not in self.targets:
                try:
                    await player.role.no_action(self, player)
                except NotImplementedError:
                    pass


@dataclass
class Day(DayNight):
    async def start(self) -> None:
        await super().start()
        await self.game.send(
            embed=discord.Embed(
                title=_("Day dawns... 🌞"),
                description=_(
                    "Good morning everyone! It's time to discuss who you think is a Mafia."
                ),
                color=DAY_COLOR,
            ),
        )
        await asyncio.sleep(2)
        for mayor_player in [
            player
            for player in self.game.alive_players
            if player.role is Mayor and player.revealed
        ]:
            embed: discord.Embed = discord.Embed(
                title=_(
                    "{mayor_player.member.display_name} has revealed themselves as **Mayor**!"
                ).format(mayor_player=mayor_player),
                description=_(
                    "The {mayor_player.member.mention}'s vote will now count as two."
                ).format(mayor_player=mayor_player),
                color=mayor_player.role.color(),
            )
            embed.set_image(url="attachment://mayor.png")
            await self.game.send(
                embed=embed,
                file=get_image(os.path.join("roles", "mayor")),
            )
        await asyncio.sleep(1)
        embed: discord.Embed = discord.Embed(
            title=_("Now, I will give you {talk_timeout} seconds to talk! 🔊").format(
                talk_timeout=self.game.config["talk_timeout"]
            ),
            description=_(
                "Want to accuse someone? Want to defend yourself, or confess? Now is the time!"
            ),
            color=DAY_COLOR,
        )
        embed.set_image(url="attachment://talk.png")
        await self.game.send(
            embed=embed,
            file=get_image("talk"),
        )
        try:
            overwrites = self.game.channel.overwrites.copy()
            for player in self.game.alive_players:
                overwrites.setdefault(
                    player.member,
                    discord.PermissionOverwrite(
                        view_channel=True, read_messages=True, attach_files=False
                    ),
                )
                send_messages = (
                    self.game.current_anomaly is not CatsTongue
                    or player not in self.game.current_anomaly_players
                ) and player not in [
                    t
                    for p, t in self.game.days_nights[-2].targets.items()
                    if p.role is Blackmailer
                ]
                overwrites[player.member].send_messages = send_messages
                overwrites[player.member].add_reactions = (
                    send_messages and self.game.config["add_reactions"]
                )
            await self.game.channel.edit(overwrites=overwrites)
        except discord.HTTPException:
            pass
        await asyncio.sleep(
            self.game.config["talk_timeout"]
            if self.game.current_anomaly is not LightningRound
            else 10
        )

        manipulator = None
        for i in range(1 if self.game.current_anomaly is not DejaVu else 2):
            if i == 1:
                if any(
                    player.has_won and not player.role.objective_secondary
                    for player in self.players
                ):
                    break
                if (
                    len([p for p in self.game.alive_players if p.side == "Mafia"]) == 1
                    or len([p for p in self.game.alive_players if p.side == "Villagers"]) == 1
                ):
                    break
                await self.game.send(**self.game.current_anomaly.get_kwargs(self.game))
            remaining_players: typing.List[Player] = self.game.alive_players
            minimum_votes_required = (
                len(remaining_players) // 2 + 1
                if len(remaining_players) % 2
                else len(remaining_players) // 2
            )
            embed: discord.Embed = discord.Embed(
                title=_(
                    "🗳️ Voting time! 🗳️\nMinimum votes required: {minimum_votes_required}"
                ).format(minimum_votes_required=minimum_votes_required),
                description="\n".join(
                    [f"🔴 {player.member.mention}" for player in self.game.alive_players]
                ),
                color=VOTING_AND_JUDGEMENT_COLOR,
            )
            embed.set_image(url="attachment://voting.png")
            embed.set_footer(
                text=_("You have {voting_timeout} seconds to vote.").format(
                    voting_timeout=self.game.config["voting_timeout"]
                )
            )
            view: VoteView = VoteView(self, remaining_players=remaining_players)
            view._message = await self.game.send(
                embed=embed,
                view=view,
                file=get_image("voting"),
            )
            self.game.cog.views[view._message] = view
            await asyncio.sleep(
                self.game.config["voting_timeout"]
                if self.game.current_anomaly is not LightningRound
                else 10
            )
            await view.on_timeout()
            if politicians := {
                player: target
                for player, target in sorted(
                    self.targets.items(), key=lambda x: self.game.players.index(x[0])
                )
                if player.role is Politician
            }:
                for politician, target in politicians.items():
                    await politician.role.day_action(self, politician, target)
                continue
            votes = {
                player: v
                for player in remaining_players
                if (v := [voter for voter, p in view.votes.items() if p == player])
            }
            manipulator = next(
                (
                    player
                    for player in sorted(self.targets.keys(), key=self.game.players.index)
                    if player.role is Manipulator
                ),
                None,
            )
            if manipulator is not None:
                manipulator.uses_amount += 1

            def get_extra_votes(voter: Player, for_displaying: bool = False) -> int:
                extra_votes = voter.extra_votes
                last_night = self.game.days_nights[-2]
                for p in [p for p in self.game.alive_players if p.role is Gambler]:
                    if (
                        p in last_night.targets
                        and last_night.gamblers_dices[p] == "yellow"
                        and last_night.gamblers_results[p][0]
                        and voter == last_night.gamblers_results[p][1]
                    ):
                        extra_votes += 1
                if not for_displaying:
                    if manipulator is not None and (
                        voter.role.side == "Mafia" or voter.is_town_traitor
                    ):
                        extra_votes += 1
                if (
                    targeter := next(
                        (
                            p
                            for p, t in last_night.targets.items()
                            if p.role.name == "Baker" and t == voter
                        ),
                        None,
                    )
                ) is not None and last_night.bakers_effects[targeter] == "extra_vote":
                    extra_votes += 1
                return extra_votes

            len_votes = {
                player: len(votes[player]) + sum(get_extra_votes(voter) for voter in votes[player])
                for player in votes
            }
            result = sorted(votes, key=len_votes.get, reverse=True)
            if votes:
                await self.game.send(
                    embed=discord.Embed(
                        title=_("Voting Results:"),
                        description="\n\n".join(
                            [
                                f"🔴 {player.member.mention} ({len_votes[player]} vote{'s' if len_votes[player] != 1 else ''})"
                                + (
                                    ":\n"
                                    + "\n".join(
                                        [
                                            f"**•** {voter.member.mention}{f' **+{extra_votes}**' if (extra_votes := get_extra_votes(voter, for_displaying=True)) else ''}"
                                            for voter in votes[player]
                                        ]
                                    )
                                    if not self.game.config["anonymous_voting"]
                                    and manipulator is None
                                    else ""
                                )
                                for player in result
                            ]
                        ),
                        color=VOTING_AND_JUDGEMENT_COLOR,
                    ),
                )

            if (
                votes
                and len_votes[result[0]] >= minimum_votes_required
                and (len(votes) == 1 or len_votes[result[1]] != len_votes[result[0]])
            ):
                target: Player = result[0]
                if (
                    self.game.config["defend_judgement"]
                    and len(remaining_players) != 2
                    or any(p.extra_votes for p in remaining_players)
                ):
                    embed: discord.Embed = discord.Embed(
                        title=_(
                            "{target.member.display_name} has been called to the stand!"
                        ).format(target=target),
                        description=_(
                            "You have {defend_timeout} seconds to defend yourself, before the town casts your judgement."
                        ).format(defend_timeout=self.game.config["defend_timeout"]),
                        color=VOTING_AND_JUDGEMENT_COLOR,
                    )
                    embed.set_image(url="attachment://defend.png")
                    await self.game.send(
                        content=target.member.mention,
                        embed=embed,
                        file=get_image("defend"),
                    )
                    await asyncio.sleep(self.game.config["defend_timeout"])
                    embed: discord.Embed = discord.Embed(
                        title=_(
                            "It's judgement time! The town has now {judgement_timeout} seconds to vote."
                        ).format(judgement_timeout=self.game.config["judgement_timeout"]),
                        color=VOTING_AND_JUDGEMENT_COLOR,
                    )
                    embed.set_image(url="attachment://judgement.png")
                    view: JudgementView = JudgementView(self, target=target)
                    view._message = await self.game.send(
                        embed=embed,
                        view=view,
                        file=get_image("judgement"),
                    )
                    self.game.cog.views[view._message] = view
                    for __ in range(self.game.config["judgement_timeout"]):
                        if len(view.results) == len(remaining_players) - 1:
                            break
                        await asyncio.sleep(1)
                    await view.on_timeout()

                    guilty_voters = [voter for voter in view.results if view.results[voter]]
                    innocent_voters = [
                        voter for voter in view.results if view.results[voter] is False
                    ]
                    embed: discord.Embed = discord.Embed(
                        title=_("Judgement Results:"),
                        color=VOTING_AND_JUDGEMENT_COLOR,
                    )
                    if guilty_voters or innocent_voters:
                        embed.add_field(
                            name=_("👿 GUIlTY ({len_guilty})").format(
                                len_guilty=len(guilty_voters)
                            )
                            + (":" if guilty_voters else ""),
                            value=(
                                "\n".join(
                                    [
                                        f"🔴 {voter.member.mention}{f' **+{extra_votes}**' if (extra_votes := get_extra_votes(voter, for_displaying=True)) else ''}"
                                        for voter in guilty_voters
                                    ]
                                )
                                if not self.game.config["anonymous_judgement"]
                                and manipulator is None
                                else "\u200b"
                            ),
                        )
                        embed.add_field(
                            name=_("😇 INNOCENT ({len_innocent})").format(
                                len_innocent=len(innocent_voters)
                            )
                            + (":" if innocent_voters else ""),
                            value=(
                                "\n".join(
                                    [
                                        f"🔵 {voter.member.mention}{f' **+{extra_votes}**' if (extra_votes := get_extra_votes(voter, for_displaying=True)) else ''}"
                                        for voter in innocent_voters
                                    ]
                                )
                                if not self.game.config["anonymous_judgement"]
                                and manipulator is None
                                else "\u200b"
                            ),
                        )
                    else:
                        embed.description = _("No one has voted.")
                    await self.game.send(embed=embed)
                if (
                    not self.game.config["defend_judgement"]
                    or len(remaining_players) == 2
                    or (
                        len(guilty_voters) + sum(get_extra_votes(voter) for voter in guilty_voters)
                    )
                    > (
                        len(innocent_voters)
                        + sum(get_extra_votes(voter) for voter in innocent_voters)
                    )
                ):
                    if (
                        lawyer := next(
                            (
                                player
                                for player in sorted(
                                    self.targets.keys(), key=self.game.players.index
                                )
                                if player.role is Lawyer
                            ),
                            None,
                        )
                    ) is None:
                        await target.kill(
                            cause="voting", reason=_("They have been voted out by the town.")
                        )
                    else:
                        lawyer.uses_amount += 1
                        lawyer.game_targets.append(target)
                        embed: discord.Embed = discord.Embed(
                            title=_(
                                "The Lawyer has obtained an acquittal for {target.member.display_name}!"
                            ).format(target=target),
                            color=lawyer.role.color(),
                        )
                        embed.set_image(url=lawyer.role.image_url())
                        await self.game.send(
                            embed=embed,
                            file=lawyer.role.get_image(),
                        )
                        if target.role.side != "Villagers":
                            embeds = [
                                discord.Embed(
                                    title=_("The Lawyer has defended a non-Villager!"),
                                ),
                                discord.Embed(
                                    title=_(
                                        "{lawyer.member.display_name} is the **Lawyer**!"
                                    ).format(lawyer=lawyer),
                                    color=lawyer.role.color(),
                                ).set_image(url=lawyer.role.image_url()),
                                discord.Embed(
                                    title=_(
                                        "{target.member.display_name} is the **{target.role.name}**!"
                                    ).format(target=target),
                                    color=target.role.color(),
                                ).set_image(url=target.role.image_url()),
                            ]
                            await self.game.send(
                                embed=embeds,
                                files=[lawyer.role.get_image(), target.role.get_image()],
                            )
            else:
                await self.game.send(
                    embed=discord.Embed(
                        title=_("The town was unable to reach a consensus."),
                        description=_("Better work together on that next time!"),
                        color=VOTING_AND_JUDGEMENT_COLOR,
                    ),
                )

        try:
            overwrites = self.game.channel.overwrites.copy()
            for player in self.game.alive_players:
                overwrites.setdefault(
                    player.member,
                    discord.PermissionOverwrite(
                        view_channel=True, read_messages=True, attach_files=False
                    ),
                )
                overwrites[player.member].send_messages = False
                overwrites[player.member].add_reactions = False
            await self.game.channel.edit(overwrites=overwrites)
        except discord.HTTPException:
            pass

        if len(self.game.days_nights) > 1:  # Should be always `True`.
            for player, target in self.game.days_nights[-2].targets.items():
                try:
                    await player.role.next_end_day_action(self, player, target)
                except NotImplementedError:
                    pass


class Game:
    def __init__(
        self,
        cog: commands.Cog,
        mode: typing.Type[Mode] = Classic,
        config: typing.Dict[str, typing.Any] = None,
    ) -> None:
        self.cog: commands.Cog = cog
        self.ctx: commands.Context = None
        self.mode: typing.Type[Mode] = mode
        self.config: typing.Dict[str, typing.Any] = config

        self.channel: typing.Union[discord.TextChannel] = None
        self.players: typing.List[Player] = []
        self.days_nights: typing.List[DayNight] = []
        self.current_number: int = 0

        self.immunity_night_1: typing.List[Player] = []
        self.afk_players: typing.Dict[Player, int] = {}
        self._start_message_view: StartMessageView = None
        self._spectate_view: typing.Optional[SpectateView] = None

        self.current_anomaly: typing.Optional[typing.Type[Anomaly]] = None
        self.current_anomaly_players: typing.Dict[Player, typing.Any] = {}

    @property
    def send(self) -> typing.Type[discord.abc.Messageable.send]:
        return self.channel.send

    @property
    def alive_players(self) -> typing.List[Player]:
        return [player for player in self.players if not player.is_dead]

    @property
    def dead_players(self) -> typing.List[Player]:
        return [player for player in self.players if player.is_dead]

    def get_player(self, member: discord.Member) -> typing.Optional[Player]:
        return next((player for player in self.players if player.member == member), None)

    def get_player_by_id(self, member_id: int) -> typing.Optional[Player]:
        return next((player for player in self.players if player.member.id == member_id), None)

    async def start(self, ctx: commands.Context, players: typing.List[discord.Member]) -> None:
        self.ctx: commands.Context = ctx
        self.cog.games[self.ctx.guild] = self
        self.players: typing.List[Player] = [
            Player(
                game=self,
                member=player,
                role=None,
                dying_message=await self.cog.config.user(player).default_dying_message(),
            )
            for player in players
        ]
        self.config: typing.Dict[str, typing.Any] = (
            self.config or await self.cog.config.guild(ctx.guild).all()
        )
        if self.config["red_economy"]:
            for player in self.players:
                try:
                    await bank.withdraw_credits(player.member, self.config["cost_to_play"])
                except ValueError:
                    await bank.set_balance(player.member, 0)
        if self.config["town_traitor"] and len(self.players) < 8:
            self.config["town_traitor"] = False
            await self.ctx.send(
                embed=discord.Embed(
                    title=_("There is no **Town Traitor** in this game!"),
                    description=_("It would be too much chaos for a small game like this."),
                    color=MAFIA_COLOR,
                ),
            )

        category = (
            category
            if (
                (category_id := self.config["category"]) is not None
                and (category := self.ctx.guild.get_channel(category_id)) is not None
            )
            else self.ctx.channel.category
        )
        overwrites = {
            self.ctx.guild.default_role: discord.PermissionOverwrite(
                view_channel=False,
                read_messages=False,
                send_messages=False,
                add_reactions=False,
                attach_files=False,
            ),
            self.ctx.guild.me: discord.PermissionOverwrite(
                view_channel=True,
                read_messages=True,
                send_messages=True,
                add_reactions=True,
                manage_messages=True,
                manage_channels=True,
                manage_permissions=True,
            ),
        }
        for player in self.players:
            overwrites[player.member] = discord.PermissionOverwrite(
                view_channel=True,
                read_messages=True,
                send_messages=False,
                add_reactions=False,
                attach_files=False,
            )
        self.channel: typing.Union[discord.TextChannel] = await self.ctx.guild.create_text_channel(
            name="mafia",
            topic=_("A game of Mafia is currently in progress."),
            overwrites=overwrites,
            category=category,
            reason="Creating a Mafia channel.",
        )
        # self.channel: typing.Union[discord.TextChannel, discord.VoiceChannel, discord.Thread] = self.ctx.channel
        # if not isinstance(self.channel, discord.Thread):
        #     original_overwrites = self.ctx.channel.overwrites
        #     overwrites = original_overwrites.copy()
        #     for player in self.players:
        #         overwrites[player.member] = discord.PermissionOverwrite(
        #             view_channel=True, read_messages=True, send_messages=False, add_reactions=False, attach_files=False,
        #         )
        #     try:
        #         await self.ctx.channel.edit(overwrites=overwrites)
        #     except discord.HTTPException:
        #         pass

        embed: discord.Embed = discord.Embed(
            title=_("👋 Welcome to Mafia! 👋"),
            description=_("If you haven't read the rules yet, please do it now."),
            color=discord.Color.green(),
        )
        embed.add_field(
            name=_("Some important rules:"),
            value=_(
                "💬 Please not send any messages, unless instructed to do so.\n"
                "💢 Admins, please don't use your godly powers to talk when others can't.\n"
                "🔇 Please don't talk about the game outside of this channel, unless instructed to do so.\n"
                "💯 Please don't leave the game unless you have a valid reason to do so.\n"
                "🚫 Screenshots are not permitted and would only ruin the game."
            ),
        )
        embed.set_footer(text=self.ctx.guild.name, icon_url=self.ctx.guild.icon)
        self._start_message_view: StartMessageView = StartMessageView(self.cog, self)
        self._start_message_view._message = await self.send(
            content=humanize_list([player.member.mention for player in self.players]),
            embed=embed,
            view=self._start_message_view,
        )

        self._spectate_view: SpectateView = SpectateView(self)
        self._spectate_view._message = await self.ctx.send(
            embed=discord.Embed(
                title=_("👀 Mafia is starting...! 👀"),
                color=discord.Color.purple(),
            ),
            view=self._spectate_view,
        )
        self.cog.views[self._spectate_view._message] = self._spectate_view

        roles = self.mode.get_roles(len(self.players), config=self.config)
        if self.config["display_roles_when_starting"]:
            await self.send(
                embed=discord.Embed(
                    title=_("Roles in this game:"),
                    description="\n".join(
                        [
                            f"- **{f'{count} ' if (count := roles.count(role)) > 1 else ''}{role.name}{'s' if count > 1 else ''}** (**{role.side}**): {_(role.ability)}"
                            for role in sorted(
                                set(roles),
                                key=lambda role: (
                                    role.side != "Mafia",
                                    role.side != "Villagers",
                                    role.side != "Neutral",
                                    role not in (GodFather, Mayor),
                                    role.name,
                                ),
                            )
                        ]
                    ),
                    color=discord.Color.purple(),
                ),
            )
        for player in self.players:
            role = random.choice(roles)
            roles.remove(role)
            if role is Alchemist:
                role = random.choice([MafiaAlchemist, VillagerAlchemist])
            player.role = role
        if self.config["town_traitor"]:
            random.choice(
                [player for player in self.players if player.role.side == "Villagers"]
            ).is_town_traitor = True
        if self.config["town_vip"]:
            random.choice(
                [
                    player
                    for player in self.players
                    if player.role.side == "Villagers" and not player.is_town_traitor
                ]
            ).is_town_vip = True

        failed_to_send = []
        for player in self.players:
            kwargs = player.role.get_kwargs(player=player)
            kwargs["embeds"] = [kwargs.pop("embed")]
            kwargs["files"] = [kwargs.pop("file")]
            if player.is_town_traitor:
                embed: discord.Embed = discord.Embed(
                    title=_("🔪 You are {the_or_a} **Town Traitor**! 🔪").format(
                        the_or_a=(
                            _("the")
                            if len([p for p in self.players if p.is_town_traitor]) == 1
                            else _("a")
                        )
                    ),
                    description=_(
                        "You are a Villager, but you are secretly working for the Mafia."
                    ),
                    color=MAFIA_COLOR,
                )
                embed.set_image(url="attachment://town_traitor.png")
                kwargs["embeds"].append(embed)
                kwargs["files"].append(get_image("town_traitor"))
            if player.is_town_vip:
                embed: discord.Embed = discord.Embed(
                    title=_("🔪 You are {the_or_a} **Town VIP**! 🔪").format(
                        the_or_a=(
                            _("the")
                            if len([p for p in self.players if p.is_town_vip]) == 1
                            else _("a")
                        )
                    ),
                    description=_("Mafia have to kill you before winning the game."),
                    color=VILLAGERS_COLOR,
                )
                embed.set_image(url="attachment://town_vip.png")
                kwargs["embeds"].append(embed)
                kwargs["files"].append(get_image("town_vip"))
            if (
                player.role.side == "Mafia" and player.role != MafiaAlchemist
            ) or player.is_town_traitor:
                kwargs["embeds"].append(self.get_mafia_team_embed(player=player))
            try:
                await player.member.send(**kwargs)
            except discord.HTTPException:
                failed_to_send.append(player)
            try:
                await player.role.on_game_start(self, player)
            except NotImplementedError:
                pass

        # if failed_to_send:
        #     self._show_my_role_view: ShowMyRoleView = ShowMyRoleView(self, players=players)
        #     self._show_my_role_view._message: discord.Message = await self.send(
        #         content=humanize_list([player.member.mention for player in failed_to_send]),
        #         embed=discord.Embed(
        #             title=_("🔔 Some players couldn't receive their roles! 🔔"),
        #             description=_("Please make sure to enable your DMs next time."),
        #             color=discord.Color.red(),
        #         ),
        #         view=self._show_my_role_view,
        #     )

        await asyncio.sleep(20)
        await self.send(
            embed=discord.Embed(
                title=_("🔪 Let the game begin! 🔪"),
                color=discord.Color.purple(),
            ),
        )

        while True:
            self.current_number += 1
            if self.config["anomalies"] and random.random() < 0.40:
                self.current_anomaly: Anomaly = random.choice(
                    [
                        anomaly
                        for anomaly in ANOMALIES
                        if anomaly.name not in self.config["disabled_anomalies"]
                        and anomaly is not self.current_anomaly
                    ]
                )
            else:
                self.current_anomaly = None
            night: Night = Night(game=self, number=self.current_number)
            self.days_nights.append(night)
            await night.start()
            if any(
                player.has_won and not player.role.objective_secondary for player in self.players
            ):
                break
            await asyncio.sleep(3)
            if self.current_anomaly is not None:
                try:
                    await self.current_anomaly.start(self)
                except NotImplementedError:
                    pass
            day: Day = Day(game=self, number=self.current_number)
            self.days_nights.append(day)
            await day.start()
            if any(
                player.has_won and not player.role.objective_secondary for player in self.players
            ):
                break
            if self.current_anomaly is not None:
                try:
                    await self.current_anomaly.end(self)
                except NotImplementedError:
                    pass
            await asyncio.sleep(5)

        main_winners = sorted(
            [
                player
                for player in self.players
                if player.has_won and not player.role.objective_secondary
            ],
            key=lambda player: (player.is_dead, ROLES_PRIORITY.index(player.role)),
        )
        secondary_winners = sorted(
            [
                player
                for player in self.players
                if player.has_won and player.role.objective_secondary
            ],
            key=lambda player: (player.is_dead, ROLES_PRIORITY.index(player.role)),
        )
        losers = sorted(
            [player for player in self.players if not player.has_won],
            key=lambda player: (player.is_dead, ROLES_PRIORITY.index(player.role)),
        )
        embeds = []
        embed: discord.Embed = discord.Embed(
            title=_("Game Over — {side} won the game!").format(
                side=(
                    "Mafia"
                    if main_winners[0].role.side == "Mafia"
                    else (
                        "Villagers"
                        if main_winners[0].role.side == "Villagers"
                        else main_winners[0].role.name
                    )
                )
            ),
            color=main_winners[0].role.color(),
        )
        if main_winners:
            embed.add_field(
                name=_("🏆 Main Winners ({len_main_winners}):").format(
                    len_main_winners=len(main_winners)
                ),
                value="\n".join(
                    [
                        f"{'👼' if not player.is_dead else '☠️'} {player.member.mention} ({player.role.name}{_(' - Town Traitor') if player.is_town_traitor else ''}{_(' - Town VIP') if player.is_town_vip else ''})"
                        for player in main_winners
                    ]
                ),
            )
        if secondary_winners:
            embed.add_field(
                name=_("🏅 Secondary Winners ({len_secondary_winners}):").format(
                    len_secondary_winners=len(secondary_winners)
                ),
                value="\n".join(
                    [
                        f"{'👼' if not player.is_dead else '☠️'} {player.member.mention} ({player.role.name}{_(' - Town Traitor') if player.is_town_traitor else ''}{_(' - Town VIP') if player.is_town_vip else ''})"
                        for player in secondary_winners
                    ]
                ),
            )
        if losers:
            embed.add_field(
                name=_("🗡️ Losers ({len_losers}):").format(len_losers=len(losers)),
                value="\n".join(
                    [
                        f"{'👼' if not player.is_dead else '☠️'} {player.member.mention} ({player.role.name}{_(' - Town Traitor') if player.is_town_traitor else ''}{_(' - Town VIP') if player.is_town_vip else ''})"
                        for player in losers
                    ]
                ),
            )
        embed.set_footer(
            text=_("Thanks for playing! Enjoyed the game? Please consider supporting the Dev!")
        )
        embeds.append(embed)
        if main_winners[0].role.side == "Villagers" and any(
            (town_vip_players := [player for player in self.alive_players if player.is_town_vip])
        ):
            embeds.append(
                discord.Embed(
                    title=(
                        _(
                            "{town_vip_player.member.display_name} was the **Town VIP** and was still alive!"
                        ).format(town_vip_player=town_vip_players[0])
                        if len(town_vip_players) == 1
                        else _(
                            "{town_vip_players} were the **Town VIPs** and were still alive!"
                        ).format(
                            town_vip_players=humanize_list(
                                [player.member.display_name for player in town_vip_players]
                            )
                        )
                    )
                )
            )
        view: discord.ui.View = discord.ui.View()
        view.add_item(
            discord.ui.Button(
                emoji="💖",
                label=_("Support the Dev!"),
                style=discord.ButtonStyle.link,
                url="https://buymeacoffee.com/aaa3a",
            ),
        )
        await self.send(
            content=humanize_list([player.member.mention for player in self.players]),
            embeds=embeds,
            view=view,
        )
        embeds[-1].set_footer(
            text=f"{self.ctx.guild.name}\n{embeds[-1].footer.text}",
            icon_url=self.ctx.guild.icon,
        )

        for player in self.players:
            new_achievements = await player.check_achievements()
            if player in main_winners and self.config["red_economy"]:
                try:
                    await bank.deposit_credits(player.member, self.config["credits_to_win"])
                except BalanceTooHigh as e:
                    await bank.set_balance(player.member, e.max_balance)
            if player not in failed_to_send:
                try:
                    await player.member.send(
                        embeds=embeds,
                        view=view,
                    )
                except discord.HTTPException:
                    pass
                if new_achievements:
                    achievements_embed: discord.Embed = discord.Embed(
                        title=_("🏆 New Achievements Unlocked! 🏆"),
                        color=ACHIEVEMENTS_COLOR,
                    )
                    for role, achievements in new_achievements.items():
                        for achievement in achievements:
                            data = (
                                ACHIEVEMENTS
                                if role is None
                                else discord.utils.get(ROLES, name=role).achievements
                            )[achievement]
                            achievements_embed.add_field(
                                name=achievement,
                                value=data["description"],
                            )
                    try:
                        await player.member.send(embed=achievements_embed)
                    except discord.HTTPException:
                        pass
                if player in main_winners and self.config["red_economy"]:
                    try:
                        await player.member.send(
                            embed=discord.Embed(
                                title=_("💰 You have received **{credits}** {currency_name}! 💰").format(
                                    credits=self.config["credits_to_win"],
                                    currency_name=await bank.get_currency_name(self.ctx.guild)
                                ),
                                color=ACHIEVEMENTS_COLOR,
                            ),
                        )
                    except discord.HTTPException:
                        pass

        await self._start_message_view.on_timeout()
        self._start_message_view.stop()
        await self._spectate_view.on_timeout()
        self._spectate_view.stop()

        if self.config["game_logs"]:

            class Transcript(chat_exporter.construct.transcript.TranscriptDAO):
                @classmethod
                async def export(
                    cls,
                    channel: typing.Union[
                        discord.TextChannel, discord.VoiceChannel, discord.Thread
                    ],
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

                    class AttachmentHandler(
                        chat_exporter.construct.attachment_handlers.AttachmentHandler
                    ):
                        async def process_asset(
                            self, attachment: discord.Attachment
                        ) -> discord.Attachment:
                            attachment.url = None
                            attachment.proxy_url = None
                            return attachment

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
                        attachment_handler=attachment_handler or AttachmentHandler(),
                    )
                    if not self.after:
                        self.messages.reverse()
                    return (await self.build_transcript()).html

            transcript = await Transcript.export(
                channel=self.channel,
                messages=[
                    message
                    async for message in self.channel.history(limit=None)
                    if message.author == self.ctx.guild.me
                ],
                tz_info="UTC",
                guild=self.ctx.guild,
                bot=ctx.bot,
            )
        else:
            transcript = None
        await self.ctx.send(
            embeds=embeds,
            file=(
                discord.File(io.BytesIO(transcript.encode("utf-8")), filename="transcript.html")
                if transcript
                else None
            ),
            view=view,
        )
        self.cog.games.pop(self.ctx.guild, None)
        self.cog.last_games[self.ctx.guild] = self
        if self.channel.permissions_for(self.ctx.guild.me).manage_channels:
            await asyncio.sleep(10)
            if not self.config["channel_auto_delete"] and not await CogsUtils.ConfirmationAsk(
                self.ctx,
                _("{host.mention} Do you want to delete the Mafia channel?").format(
                    host=self.ctx.author
                ),
                timeout=600,
                timeout_message=None,
            ):
                return
            try:
                await self.channel.delete()
            except discord.HTTPException:
                pass

    def get_mafia_team_embed(self, player: typing.Optional[Player] = None) -> discord.Embed:
        mafia_players = sorted(
            [
                p
                for p in self.players
                if (p.role.side == "Mafia" and p.role not in (MafiaAlchemist, VillagerAlchemist))
                or p.is_town_traitor
            ],
            key=lambda p: (
                MAFIA_HIERARCHY.index(p.role)
                if p.role in MAFIA_HIERARCHY
                else len(MAFIA_HIERARCHY) + 1
            ),
        )
        embed: discord.Embed = discord.Embed(
            title=_("🔪 Here's your Mafia team! 🔪"),
            description="\n".join(
                [
                    f"🔫 {p.member.mention} ({p.role.name}{_(' - Town Traitor') if p.is_town_traitor else ''})"
                    for p in mafia_players
                ]
            ),
            color=MAFIA_COLOR,
        )
        if len(mafia_players) > 1:
            embed.set_footer(text=_("You can DM the bot to communicate with your team!"))
        return embed

    def get_readable_spoil(self) -> typing.Dict[str, str]:
        return {player.member.display_name: player.role.name for player in self.players}

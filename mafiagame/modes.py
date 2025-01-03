from redbot.core.i18n import Translator  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import random

from redbot.core.utils.chat_formatting import humanize_list

from .constants import MODES_COLOR
from .roles import (
    MORE_ROLES,
    ROLES,
    Alchemist,
    Baiter,
    Bomber,
    Detective,
    Distractor,
    Doctor,
    Executioner,
    Framer,
    GodFather,
    Goose,
    Hacker,
    Hoarder,
    Link,
    Mafia,
    Mayor,
    Mimic,
    PlagueDoctor,
    PrivateInvestigator,
    Role,
    Spy,
    Vigilante,
    Villager,
    Watcher,
)  # NOQA


def _(untranslated: str) -> str:  # `redgettext` will find these strings.
    return untranslated


class Mode:
    name: str
    emoji: str
    description: str

    roles: typing.Dict[
        typing.Union[int, typing.Tuple[typing.Optional[int], typing.Optional[int]]],
        typing.Dict[
            typing.Literal["must", "may", "choices"],
            typing.Union[
                typing.List[typing.Type[Role]],
                typing.Tuple[
                    typing.Optional[int], typing.Optional[int], typing.List[typing.Type[Role]]
                ],
            ],
        ],
    ]
    amounts: typing.Dict[int, typing.Dict[typing.Literal["villagers", "mafia", "neutral"], int]]

    @classmethod
    def get_kwargs(cls) -> typing.Dict[str, typing.Union[discord.Embed, discord.File]]:
        _: Translator = Translator("MafiaGame", __file__)
        embed: discord.Embed = discord.Embed(
            title=_("Mode — **{emoji} {name}**").format(emoji=cls.emoji, name=cls.name),
            description=_(cls.description),
            color=MODES_COLOR,
        )

        if hasattr(cls, "roles"):
            for players_range, roles in cls.roles.items():
                value = _("**•** **Must:** {must}").format(
                    must=humanize_list([role.name for role in roles["must"]]),
                )
                if "may" in roles:
                    value += _("\n**•** **May (1):** {may}").format(
                        may=humanize_list([role.name for role in roles["may"]]),
                    )
                if "choices" in roles:
                    value += _("\n**•** **Choices:**")
                    for amount, choices in roles["choices"]:
                        value += _("\n  **{amount}** from {choices}").format(
                            amount=(
                                (
                                    str(amount)
                                    if isinstance(amount, int)
                                    else f"{amount[0]}-{amount[1]}"
                                )
                                if amount is not None
                                else _("Any")
                            ),
                            choices=humanize_list([role.name for role in choices]),
                        )
                embed.add_field(
                    name=_("{players_range} Players").format(
                        players_range=(
                            str(players_range)
                            if isinstance(players_range, int)
                            else (
                                f"{players_range[0]}-{players_range[1]}"
                                if players_range[1] is not None
                                else f"{players_range[0]}+"
                            )
                        ),
                    ),
                    value=value,
                    inline=True,
                )
        elif hasattr(cls, "amounts"):
            for players_number, amounts in cls.amounts.items():
                embed.add_field(
                    name=_("{players_number} Players").format(players_number=players_number),
                    value=_(
                        "**•** Villagers: {villagers}\n"
                        "**•** Mafia: {mafia}\n"
                        "**•** Neutral: {neutral}"
                    ).format(
                        villagers=amounts["villagers"],
                        mafia=amounts["mafia"],
                        neutral=amounts["neutral"],
                    ),
                    inline=True,
                )

        return {
            "embed": embed,
        }

    @classmethod
    def get_roles(
        cls,
        players_number: int,
        config: typing.Dict[str, typing.Any] = {
            "disabled_roles": [],
            "more_roles": False,
            "custom_roles": [],
        },
    ) -> typing.List[typing.Type[Role]]:
        specificities = next(
            (
                roles
                for players_range, roles in cls.roles.items()
                if (
                    players_range == players_number
                    if isinstance(players_range, int)
                    else (players_range[0] or 5) <= players_number <= (players_range[1] or 25)
                )
            ),
        )
        roles = [role for role in specificities["must"] if role not in config["disabled_roles"]]
        if len(roles) < players_number and "may" in specificities and random.random() < 0.5:
            may = [role for role in specificities["may"] if role not in config["disabled_roles"]]
            roles.append(random.choice(may))
        if "choices" in specificities:
            for amount, choices in specificities["choices"]:
                choices = [role for role in choices if role not in config["disabled_roles"]]
                if amount is not None:
                    if not isinstance(amount, typing.Tuple):
                        roles.extend(random.sample(choices, k=amount))
                    else:
                        roles.extend(random.sample(choices, k=random.randint(*amount)))
                elif len(roles) < players_number:
                    roles.extend(
                        random.sample(choices, min(len(choices), players_number - len(roles)))
                    )
        if len(roles) < players_number:
            roles.extend([Villager] * (players_number - len(roles)))
        return roles


ALWAYS_MUST = [GodFather, Detective, Doctor]


class Classic(Mode):
    name: str = "Classic"
    emoji: str = "🏛️"
    description: str = _("A mode with 3 classic roles and some villagers.")
    roles = {
        (5, None): {
            "must": ALWAYS_MUST,
        },
    }


class Crazy(Mode):
    name: str = "Crazy"
    emoji: str = "🤪"
    description: str = _("A mode which includes some crazy roles.")
    roles = {
        5: {
            "must": ALWAYS_MUST,
            "choose": [(2, [Vigilante, Mayor, Executioner])],
        },
        (6, None): {
            "must": ALWAYS_MUST + [Vigilante, Mayor, Executioner],
        },
    }


class Chaos(Mode):
    name: str = "Chaos"
    emoji: str = "🌀"
    description: str = _("A mode where chaos reigns.")
    roles = {
        (5, 7): {
            "must": ALWAYS_MUST,
            "may": [Executioner],
            "choices": [(None, [Vigilante, Mayor, Spy, PrivateInvestigator, Distractor])],
        },
        (8, 9): {
            "must": ALWAYS_MUST + [Executioner],
            "may": [Executioner, Baiter, Bomber],
            "choices": [
                (1, [Mafia, Framer]),
                (None, [Vigilante, Mayor, Spy, PrivateInvestigator, Distractor]),
            ],
        },
        10: {
            "must": ALWAYS_MUST,
            "may": [Executioner, Baiter, Bomber],
            "choices": [
                (1, [Mafia, Framer]),
                (None, [Vigilante, Mayor, Spy, PrivateInvestigator, Distractor]),
            ],
        },
        11: {
            "must": ALWAYS_MUST + [Vigilante, Mayor, Spy, PrivateInvestigator, Distractor],
            "choices": [
                ((1, 2), [Mafia, Framer]),
                (1, [Executioner, Baiter, Bomber]),
            ],
        },
        (12, None): {
            "must": ALWAYS_MUST
            + [Vigilante, Mayor, Spy, PrivateInvestigator, Distractor, Mafia, Framer],
            "choices": [
                (2, [Executioner, Baiter, Bomber]),
            ],
        },
    }


class Corona(Mode):
    name: str = "Corona"
    emoji: str = "🦠"
    description: str = _("A mode where survival is key.")
    roles = {
        (5, 7): {
            "must": ALWAYS_MUST,
            "may": [Executioner],
            "choices": [(None, [Vigilante, Mayor, Spy, PrivateInvestigator, Distractor, Watcher])],
        },
        (8, 10): {
            "must": ALWAYS_MUST,
            "may": [Executioner, Baiter, Bomber, PlagueDoctor, Hoarder],
            "choices": [
                (1, [Mafia, Framer, Hacker, Goose]),
                (None, [Vigilante, Mayor, Spy, PrivateInvestigator, Distractor, Watcher]),
            ],
        },
        11: {
            "must": ALWAYS_MUST,
            "choices": [
                ((1, 2), [Mafia, Framer, Hacker, Goose]),
                (1, [Executioner, Baiter, Bomber, PlagueDoctor, Hoarder]),
                (None, [Vigilante, Mayor, Spy, PrivateInvestigator, Distractor, Watcher]),
            ],
        },
        (12, None): {
            "must": ALWAYS_MUST,
            "choices": [
                (2, [Mafia, Framer, Hacker, Goose]),
                (2, [Executioner, Bomber, PlagueDoctor, Hoarder]),
                (None, [Vigilante, Mayor, Spy, PrivateInvestigator, Distractor, Watcher]),
            ],
        },
    }


class Crimson(Mode):
    name: str = "Crimson"
    emoji: str = "🩸"
    description: str = _("A mode where blood is spilled.")
    roles = {
        (5, 7): {
            "must": ALWAYS_MUST,
            "may": [Executioner],
            "choices": [
                (
                    None,
                    [
                        Vigilante,
                        Mayor,
                        Spy,
                        PrivateInvestigator,
                        Distractor,
                        Watcher,
                        Link,
                        Alchemist,
                    ],
                )
            ],
        },
        (8, 10): {
            "must": ALWAYS_MUST,
            "may": [Executioner, Baiter, Bomber, PlagueDoctor, Hoarder],
            "choices": [
                (1, [Mafia, Framer, Hacker, Goose, Mimic]),
                (
                    None,
                    [
                        Vigilante,
                        Mayor,
                        Spy,
                        PrivateInvestigator,
                        Distractor,
                        Watcher,
                        Link,
                        Alchemist,
                    ],
                ),
            ],
        },
        11: {
            "must": ALWAYS_MUST,
            "may": [Executioner, Baiter, Bomber, PlagueDoctor, Hoarder],
            "choices": [
                ((1, 2), [Mafia, Framer, Hacker, Goose, Mimic]),
                (
                    None,
                    [
                        Vigilante,
                        Mayor,
                        Spy,
                        PrivateInvestigator,
                        Distractor,
                        Watcher,
                        Link,
                        Alchemist,
                    ],
                ),
            ],
        },
        (12, 13): {
            "must": ALWAYS_MUST,
            "choices": [
                (2, [Mafia, Framer, Hacker, Goose, Mimic]),
                (2, [Executioner, Baiter, Bomber, PlagueDoctor, Hoarder]),
                (
                    None,
                    [
                        Vigilante,
                        Mayor,
                        Spy,
                        PrivateInvestigator,
                        Distractor,
                        Watcher,
                        Link,
                        Alchemist,
                    ],
                ),
            ],
        },
        (14, 15): {
            "must": ALWAYS_MUST,
            "choices": [
                ((2, 3), [Mafia, Framer, Hacker, Goose, Mimic]),
                ((2, 3), [Executioner, Baiter, Bomber, PlagueDoctor, Hoarder]),
                (
                    None,
                    [
                        Vigilante,
                        Mayor,
                        Spy,
                        PrivateInvestigator,
                        Distractor,
                        Watcher,
                        Link,
                        Alchemist,
                    ],
                ),
            ],
        },
        16: {
            "must": ALWAYS_MUST,
            "choices": [
                (3, [Mafia, Framer, Hacker, Goose, Mimic]),
                (3, [Executioner, Baiter, Bomber, PlagueDoctor, Hoarder]),
                (
                    None,
                    [
                        Vigilante,
                        Mayor,
                        Spy,
                        PrivateInvestigator,
                        Distractor,
                        Watcher,
                        Link,
                        Alchemist,
                    ],
                ),
            ],
        },
        17: {
            "must": ALWAYS_MUST
            + [Vigilante, Mayor, Spy, PrivateInvestigator, Distractor, Watcher, Link, Alchemist],
            "choices": [
                (3, [Mafia, Framer, Hacker, Goose, Mimic]),
                (3, [Executioner, Baiter, Bomber, PlagueDoctor, Hoarder]),
            ],
        },
        18: {
            "must": ALWAYS_MUST
            + [
                Vigilante,
                Mayor,
                Spy,
                PrivateInvestigator,
                Distractor,
                Watcher,
                Link,
                Alchemist,
                Villager,
            ],
            "choices": [
                (3, [Mafia, Framer, Hacker, Goose, Mimic]),
                (3, [Executioner, Baiter, Bomber, PlagueDoctor, Hoarder]),
            ],
        },
        (19, None): {
            "must": ALWAYS_MUST
            + [Vigilante, Mayor, Spy, PrivateInvestigator, Distractor, Watcher, Link, Alchemist],
            "choices": [
                (4, [Mafia, Framer, Hacker, Goose, Mimic]),
                (4, [Executioner, Baiter, Bomber, PlagueDoctor, Hoarder]),
            ],
        },
    }


class Random(Mode):
    name: str = "Random"
    emoji: str = "🎲"
    description: str = _("A mode where roles are randomly assigned.")
    amounts = {
        5: {"villagers": 4, "mafia": 1, "neutral": 0},
        6: {"villagers": 5, "mafia": 1, "neutral": 0},
        7: {"villagers": 5, "mafia": 1, "neutral": 1},
        8: {"villagers": 6, "mafia": 2, "neutral": 0},
        9: {"villagers": 6, "mafia": 2, "neutral": 1},
        10: {"villagers": 7, "mafia": 2, "neutral": 1},
        11: {"villagers": 7, "mafia": 2, "neutral": 2},
        12: {"villagers": 8, "mafia": 3, "neutral": 1},
        13: {"villagers": 8, "mafia": 3, "neutral": 2},
        14: {"villagers": 9, "mafia": 3, "neutral": 2},
        15: {"villagers": 9, "mafia": 3, "neutral": 3},
        16: {"villagers": 10, "mafia": 4, "neutral": 2},
        17: {"villagers": 10, "mafia": 4, "neutral": 3},
        18: {"villagers": 11, "mafia": 4, "neutral": 3},
        19: {"villagers": 11, "mafia": 4, "neutral": 4},
        20: {"villagers": 12, "mafia": 5, "neutral": 3},
        21: {"villagers": 12, "mafia": 5, "neutral": 4},
        22: {"villagers": 13, "mafia": 5, "neutral": 4},
        23: {"villagers": 13, "mafia": 5, "neutral": 5},
        24: {"villagers": 14, "mafia": 6, "neutral": 4},
        25: {"villagers": 14, "mafia": 6, "neutral": 5},
    }

    @classmethod
    def get_roles(
        cls,
        players_number: int,
        config: typing.Dict[str, typing.Any] = {
            "disabled_roles": [],
            "more_roles": False,
            "custom_roles": [],
        },
    ) -> typing.List[typing.Type[Role]]:
        roles = [GodFather]
        possible_roles = [
            role
            for role in ROLES
            if (
                role not in config["disabled_roles"]
                and (
                    config["more_roles"]
                    or role not in MORE_ROLES
                )
                and role != GodFather
                and role.starting
            )
        ]
        mafia_roles = [role for role in possible_roles if role.side == "Mafia"]
        villagers_roles = [role for role in possible_roles if role.side == "Villagers"]
        neutral_roles = [role for role in possible_roles if role.side == "Neutral"]
        amounts = cls.amounts[players_number]
        mafia_amount, villagers_amount, neutral_amount = (
            amounts["mafia"],
            amounts["villagers"],
            amounts["neutral"],
        )
        roles.extend(random.sample(mafia_roles, k=mafia_amount - 1))
        roles.extend(random.sample(villagers_roles, k=villagers_amount))
        roles.extend(random.sample(neutral_roles, k=neutral_amount))
        if len(roles) < players_number:
            roles.extend([Villager] * (players_number - len(roles)))
        return roles


class Custom(Mode):
    name: str = "Custom"
    emoji: str = "🔧"
    description: str = _(
        "A mode where you can choose all the roles. Use `[p]setmafia customroles` to configure this mode."
    )

    @classmethod
    def get_roles(
        cls,
        players_number: int,
        config: typing.Dict[str, typing.Any] = {
            "disabled_roles": [],
            "more_roles": False,
            "custom_roles": [],
        },
    ) -> typing.List[typing.Type[Role]]:
        roles = [discord.utils.get(ROLES, name=role) for role in config["custom_roles"]]
        if GodFather not in roles:
            roles.insert(0, GodFather)
            if len(roles) > players_number:
                del roles[-1]
        roles = roles[:players_number]  # Ensure the roles are not more than the players.
        if len(roles) < players_number:
            roles.extend([Villager] * (players_number - len(roles)))
        return roles


MODES: typing.List[typing.Type[Mode]] = [Classic, Crazy, Chaos, Corona, Crimson, Random, Custom]

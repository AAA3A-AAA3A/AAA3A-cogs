import typing
from dataclasses import dataclass, field

import discord


@dataclass
class PlayerEvent:
    round_number: int
    type: typing.Literal["kill", "death", "revive", "apparition"]
    cause: str
    message: discord.Message
    other: discord.Member | None = None


@dataclass
class RumbleRoyale:
    first_message: discord.Message
    host: discord.User
    players: dict[
        discord.Member,
        list[PlayerEvent],
    ] = field(default_factory=dict)
    views: list[discord.ui.View] = field(default_factory=list)

    @property
    def is_started(self) -> bool:
        return bool(self.players)

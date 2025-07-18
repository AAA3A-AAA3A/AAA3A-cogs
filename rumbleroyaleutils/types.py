import discord  # isort:skip
import typing  # isort:skip

from dataclasses import dataclass, field


@dataclass
class PlayerApparition:
    round_number: int
    type: typing.Literal["kill", "death", "revive", "apparition"]
    cause: str
    message: discord.Message
    other: typing.Optional[discord.Member] = None


@dataclass
class RumbleRoyale:
    first_message: discord.Message
    host: discord.User
    players: typing.Dict[
        discord.Member,
        typing.List[PlayerApparition],
    ] = field(default_factory=dict)
    views: typing.List[discord.ui.View] = field(default_factory=list)

    @property
    def is_started(self) -> bool:
        return bool(self.players)

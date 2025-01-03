from redbot.core.i18n import Translator  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import os
import random

from .constants import ANOMALIES_COLOR
from .roles import Jester, PlagueDoctor
from .utils import get_image


def _(untranslated: str) -> str:  # `redgettext` will find these strings.
    return untranslated


class Anomaly:
    name: str
    emoji: str
    description: str
    message: typing.Optional[str] = None

    @classmethod
    def image_name(cls) -> str:
        return cls.name.lower().replace(" ", "_").replace("'", "")

    @classmethod
    def image_url(cls) -> str:
        return f"attachment://{cls.image_name()}.png"

    @classmethod
    def get_image(cls) -> discord.File:
        return get_image(os.path.join("anomalies", cls.image_name()))

    @classmethod
    def get_kwargs(cls) -> typing.Dict[str, typing.Union[discord.Embed, discord.File]]:
        _: Translator = Translator("MafiaGame", __file__)
        embed: discord.Embed = discord.Embed(
            title=_("Anomaly — **{emoji} {name}**!").format(name=cls.name, emoji=cls.emoji),
            description=f"*{_(cls.description)}*",
            color=ANOMALIES_COLOR,
        )
        image = cls.name.lower().replace(" ", "_").replace("'", "")
        embed.set_image(url=cls.image_url())
        if cls.message is not None:
            embed.add_field(name="\u200b", value=_(cls.message))
        return {
            "embed": embed,
            "file": cls.get_image(),
        }

    @classmethod
    async def start(cls, game) -> None:
        if cls.message is not None:
            for player in game.current_anomaly_players or game.alive_players:
                await player.send(**cls.get_kwargs())

    @classmethod
    async def end(cls, game) -> None:
        raise NotImplementedError()


class ClownFestival(Anomaly):
    name: str = "Clown Fest"
    emoji: str = "🤡"
    description: str = _(
        "Everyone except Mafia side's players and Plague Doctor turn into the Jester for one day, then return to their normal selves."
    )
    message: str = _(
        "Some weird gas filled up the sky, and you were suddenly turned into a **Jester**! You will return to your normal self the following night."
    )

    @classmethod
    async def start(cls, game) -> None:
        game.current_anomaly_players = {
            player: player.role
            for player in game.alive_players
            if player.role.side != "Mafia" and player.role is not PlagueDoctor
        }
        for player in game.current_anomaly_players:
            player.role = Jester
        await super().start(game)

    @classmethod
    async def end(cls, game) -> None:
        for player, role in game.current_anomaly_players.items():
            player.role = role
        game.current_anomaly_players = {}


class BlindingLights(Anomaly):
    name: str = "Blinding Lights"
    emoji: str = "💡"
    description: str = _(
        "Random amount of people will be blinded and unable to perform their roles."
    )
    message: str = _(
        "A blinding light filled the sky! You were blinded and unable to perform your task tonight... if you were going to anyways..."
    )

    @classmethod
    async def start(cls, game) -> None:
        game.current_anomaly_players = random.sample(
            game.alive_players, k=random.randint(1, len(game.alive_players))
        )
        await super().start(game)

    @classmethod
    async def end(cls, game) -> None:
        game.current_anomaly_players = {}


class DejaVu(Anomaly):
    name: str = "Deja Vu"
    emoji: str = "🔄"
    description: str = _(
        "Town gets another chance to lynch someone! The second chance to vote immediately appears after someone is lynched or no one was hanged."
    )


class TalkingDead(Anomaly):
    name: str = "Talking Dead"
    emoji: str = "🗣️"
    description: str = _(
        "Some dead can talk! But not vote because, you know, dead people can't vote."
    )
    message: str = _("You suddenly feel a surge of energy, and you can talk to the living!")

    @classmethod
    async def start(cls, game) -> None:
        game.current_anomaly_players = random.sample(
            game.dead_players, k=random.randint(1, len(game.dead_players))
        )
        if not isinstance(game.channel, discord.Thread):
            try:
                overwrites = game.channel.overwrites.copy()
                for player in game.current_anomaly_players:
                    overwrites.setdefault(
                        player.member,
                        discord.PermissionOverwrite(
                            view_channel=True, read_messages=True, attach_files=False
                        ),
                    )
                    overwrites[player.member].send_messages = True
                    overwrites[player.member].add_reactions = game.config["add_reactions"]
                await game.channel.edit(overwrites=overwrites)
            except discord.HTTPException:
                pass
        await super().start(game)

    @classmethod
    async def end(cls, game) -> None:
        if not isinstance(game.channel, discord.Thread):
            try:
                overwrites = game.channel.overwrites.copy()
                for player in game.current_anomaly_players:
                    overwrites.setdefault(
                        player.member,
                        discord.PermissionOverwrite(
                            view_channel=True, read_messages=True, attach_files=False
                        ),
                    )
                    overwrites[player.member].send_messages = False
                    overwrites[player.member].add_reactions = False
                await game.channel.edit(overwrites=overwrites)
            except discord.HTTPException:
                pass
        game.current_anomaly_players = {}


class LightningRound(Anomaly):
    name: str = "Lightning Round"
    emoji: str = "⚡"
    description: str = _("The town has only 10 seconds to talk and 10 seconds to vote!")


class FoggyMist(Anomaly):
    name: str = "Foggy Mist"
    emoji: str = "🌫️"
    description: str = _(
        "Messages from last night disappeared! Who killed who? Who saved who? Who knows? Only thing you know is who's dead..."
    )


# Remastered's Anomalies.


class AcidRain(Anomaly):
    name: str = "Acid Rain"
    emoji: str = "🌧️"
    description: str = _("The role of a random player gets revealed to everyone!")

    @classmethod
    async def start(cls, game) -> None:
        game.current_anomaly_players = [random.choice(game.alive_players)]
        player = game.current_anomaly_players[0]
        kwargs = cls.get_kwargs()
        embed: discord.Embed = discord.Embed(
            title=_("{player.member.display_name} is {the_or_a} **{player.role.name}**!").format(
                player=player, the_or_a=player.role.the_or_a(player.game)
            ),
            color=player.role.color(),
        )
        image = player.role.name.lower().replace(" ", "_")
        embed.set_image(url=f"attachment://{image}.png")
        kwargs["embeds"] = [kwargs.pop("embed"), embed]
        kwargs["files"] = [kwargs.pop("file"), get_image(os.path.join("roles", image))]
        await game.send(**kwargs)

    @classmethod
    async def end(cls, game) -> None:
        game.current_anomaly_players = {}


class LivingDead(Anomaly):
    name: str = "Living Dead"
    emoji: str = "💀"
    description: str = _("A random dead player gets revived!")

    @classmethod
    async def start(cls, game) -> None:
        game.current_anomaly_players = [random.choice(game.dead_players)]
        player = game.current_anomaly_players[0]
        player.is_dead = False
        kwargs = cls.get_kwargs()
        embed: discord.Embed = discord.Embed(
            title=_("{player.member.display_name} has been revived!").format(player=player),
        )
        kwargs["embeds"] = [kwargs.pop("embed"), embed]
        await game.send(**kwargs)

    @classmethod
    async def end(cls, game) -> None:
        game.current_anomaly_players = {}


class ScorchingSun(Anomaly):
    name: str = "Scorching Sun"
    emoji: str = "☀️"
    description: str = _("The Sun is causing a heat stroke! A random player will die.")

    @classmethod
    async def start(cls, game) -> None:
        game.current_anomaly_players = [random.choice(game.alive_players)]
        player = game.current_anomaly_players[0]
        await game.send(**cls.get_kwargs())
        await player.kill(reason="scorching_sun")

    @classmethod
    async def end(cls, game) -> None:
        game.current_anomaly_players = {}


class CatsTongue(Anomaly):
    name: str = "Cat's Tongue"
    emoji: str = "😼"
    description: str = _(
        "The cat has gotten your tongue! Random amount of peope can't speak, but they can vote."
    )

    @classmethod
    async def start(cls, game) -> None:
        game.current_anomaly_players = random.sample(
            game.alive_players, k=random.randint(1, len(game.alive_players))
        )
        await super().start(game)

    @classmethod
    async def end(cls, game) -> None:
        game.current_anomaly_players = {}


# class NecronomiconsCurse(Anomaly):
#     name: str = "Necronomicon's Curse"
#     emoji: str = "📕"
#     description: str = _("Some roles will have their necronomicon status toggled! If it was on before, it'll be off and vice versa.")


ANOMALIES: typing.List[typing.Type[Anomaly]] = [
    ClownFestival,
    BlindingLights,
    DejaVu,
    TalkingDead,
    LightningRound,
    FoggyMist,
    AcidRain,
    LivingDead,
    ScorchingSun,
    CatsTongue,
]

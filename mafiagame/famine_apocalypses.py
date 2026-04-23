import random

import discord

from redbot.core.i18n import Translator

# These will be imported from `mafiagame.roles` to avoid circular imports.
ROLES = []
perform_action_select_targets = []


def _(untranslated: str) -> str:  # `redgettext` will find these strings.
    return untranslated


class FamineApocalypse:
    name: str
    emoji: str
    description: str

    @classmethod
    async def perform_action(cls, night, player, interaction: discord.Interaction) -> None:
        if player not in night.targets:
            night.targets[player] = None
        player.famine_used_apocalypses.append(cls)
        await interaction.followup.send(
            _("You have chosen to bring forth the **{emoji} {name}** apocalypse!").format(
                emoji=cls.emoji,
                name=_(cls.name),
            ),
            ephemeral=True,
        )

    @classmethod
    async def action(cls, night, player, target) -> None:
        raise NotImplementedError()

    @classmethod
    async def next_end_day_action(cls, day, player, target) -> None:
        raise NotImplementedError()


class LifeDeathSwap(FamineApocalypse):
    name: str = _("Life/Death Swap")
    emoji: str = "🔄"
    description: str = _(
        "Swap all living players with dead players. You'll appear as a dead player for 1 day.",
    )

    @classmethod
    async def action(cls, night, player, __) -> None:
        player.famine_alive_players_before_life_death_swap = night.game.alive_players.copy()
        for p in night.game.players:
            p.is_dead = not p.is_dead
        embed: discord.Embed = discord.Embed(
            title=_(
                "The **{emoji} {name}** famine apocalypse has occurred! All living players are now dead, and all dead players are now alive! This effect will last for 1 day.",
            ).format(
                emoji=cls.emoji,
                name=_(cls.name),
            ),
            color=cls.color(),
        )
        embed.set_image(url=player.role.image_url())
        await night.game.send(
            embed=embed,
            file=player.role.get_image(night.game),
        )

    @classmethod
    async def next_end_day_action(cls, day, player, __) -> None:
        for p in day.game.players:
            p.is_dead = p not in player.famine_alive_players_before_life_death_swap
        player.famine_alive_players_before_life_death_swap = []
        embed: discord.Embed = discord.Embed(
            title=_(
                "The **{emoji} {name}** famine apocalypse has ended! Everyone has returned to their original state.",
            ).format(
                emoji=cls.emoji,
                name=_(cls.name),
            ),
            color=cls.color(),
        )
        embed.set_image(url=player.role.image_url())
        await day.game.send(
            embed=embed,
            file=player.role.get_image(day.game),
        )


class MassExecution(FamineApocalypse):
    name: str = _("Mass Execution")
    emoji: str = "💀"
    description: str = _("Kill 2 random players.")

    @classmethod
    async def action(cls, night, player, __) -> None:
        targets = random.sample(
            [p for p in night.game.alive_players if p != player],
            k=min(2, len(night.game.alive_players) - 1),
        )
        for t in targets:
            await t.kill(
                player,
                reason=_("Killed by the Mass Execution famine apocalypse."),
            )


class SilencedForever(FamineApocalypse):
    name: str = _("Silenced Forever")
    emoji: str = "🔇"
    description: str = _("Permanently remove the vote of a player.")

    @classmethod
    async def perform_action(cls, night, player, interaction: discord.Interaction) -> None:
        view = await perform_action_select_targets[0](
            targets_number=1,
            self_allowed=False,
        )(
            night,
            player,
            interaction,
            content=_("Select a player to permanently remove their vote."),
        )
        await view.wait()
        if player in night.targets:
            await super().perform_action(night, player, interaction)

    @classmethod
    async def action(cls, night, player, target) -> None:
        target.extra_votes -= 1
        embed: discord.Embed = discord.Embed(
            title=_(
                "You have been silenced forever by the **{emoji} {name}** Famine's apocalypse! You can no longer vote.",
            ).format(
                emoji=cls.emoji,
                name=_(cls.name),
            ),
            color=cls.color(),
        )
        embed.set_image(url=player.role.image_url())
        await target.send(
            embed=embed,
            file=player.role.get_image(night.game),
        )


class Resurrection(FamineApocalypse):
    name: str = _("Resurrection")
    emoji: str = "✨"
    description: str = _("Revive a player of your choice.")

    @classmethod
    async def perform_action(cls, night, player, interaction: discord.Interaction) -> None:
        view = await perform_action_select_targets[0](
            targets_number=1,
            self_allowed=False,
            dead_targets=True,
            condition=lambda player, target: target.death_cause != "afk",
        )(night, player, interaction, content=_("Select a player to resurrect."))
        await view.wait()
        if player in night.targets:
            await super().perform_action(night, player, interaction)

    @classmethod
    async def action(cls, night, player, target) -> None:
        target.is_dead = False
        embed: discord.Embed = discord.Embed(
            title=_(
                "You have been resurrected by the **{emoji} {name}** Famine's apocalypse!",
            ).format(
                emoji=cls.emoji,
                name=_(cls.name),
            ),
            color=cls.color(),
        )
        embed.set_image(url=player.role.image_url())
        await target.send(
            embed=embed,
            file=player.role.get_image(night.game),
        )


class NeutralChaos(FamineApocalypse):
    name: str = _("Neutral Chaos")
    emoji: str = "🎭"
    description: str = _("Change a random player's role into any other neutral role available.")

    @classmethod
    async def action(cls, night, player, __) -> None:
        target = random.choice([p for p in night.game.alive_players if p != player])
        new_role = random.choice(
            [role for role in ROLES if role.side == "Neutral" and role != target.role],
        )
        await target.change_role(
            new_role,
            reason=_("Your role was changed by the **{emoji} {name}** Famine's apocalypse.").format(
                emoji=cls.emoji,
                name=_(cls.name),
            ),
        )


class EternalDistraction(FamineApocalypse):
    name: str = _("Eternal Distraction")
    emoji: str = "🙈"
    description: str = _("Permanently distract a player of your choice.")

    @classmethod
    async def perform_action(cls, night, player, interaction: discord.Interaction) -> None:
        view = await perform_action_select_targets[0](
            targets_number=1,
            self_allowed=False,
        )(night, player, interaction, content=_("Select a player to permanently distract."))
        await view.wait()
        if player in night.targets:
            await super().perform_action(night, player, interaction)

    @classmethod
    async def action(cls, night, player, target) -> None:
        target.is_distracted = True
        embed: discord.Embed = discord.Embed(
            title=_(
                "You have been eternally distracted by the **{emoji} {name}** Famine's apocalypse! You can no longer perform night actions.",
            ).format(
                emoji=cls.emoji,
                name=_(cls.name),
            ),
            color=cls.color(),
        )
        embed.set_image(url=player.role.image_url())
        await target.send(
            embed=embed,
            file=player.role.get_image(night.game),
        )


class VoteCollapse(FamineApocalypse):
    name: str = _("Vote Collapse")
    emoji: str = "⚠️"
    description: str = _("Change the votes required to be 0 for one day.")

    @classmethod
    async def action(cls, night, player, __) -> None:
        embed: discord.Embed = discord.Embed(
            title=_(
                "The vote requirement has been changed to 0 for today by the **{emoji} {name}** Famine's apocalypse!",
            ).format(
                emoji=cls.emoji,
                name=_(cls.name),
            ),
            color=cls.color(),
        )
        embed.set_image(url=player.role.image_url())
        await night.game.send(
            embed=embed,
            file=player.role.get_image(night.game),
        )


FAMINE_APOCALYPSES: list[type[FamineApocalypse]] = [
    # LifeDeathSwap,  #  No purpose...
    MassExecution,
    SilencedForever,
    Resurrection,
    NeutralChaos,
    EternalDistraction,
    VoteCollapse,
]


_: Translator = Translator("MafiaGame", __file__)

from AAA3A_utils import CogsUtils  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import datetime
import functools
import os
import random

from redbot.core import bank
from redbot.core.utils.chat_formatting import humanize_timedelta

from .constants import (
    ACHIEVEMENTS_COLOR,
    ANOMALIES_COLOR,
    DAY_COLOR,
    MAFIA_COLOR,
    MODES_COLOR,
    NEUTRAL_COLOR,
    NIGHT_COLOR,
    VILLAGERS_COLOR,
    VOTING_AND_JUDGEMENT_COLOR,
)  # NOQA
from .utils import get_image

_: Translator = Translator("MafiaGame", __file__)


class JoinGameView(discord.ui.View):
    def __init__(
        self,
        cog: commands.Cog,
        MODES: typing.List[typing.Any],
        mode: typing.Any,
        config: typing.Dict[str, typing.Any],
    ) -> None:
        super().__init__(timeout=None)
        self.ctx: commands.Context = None
        self.cog: commands.Cog = cog
        self.MODES: typing.List[typing.Any] = MODES
        self.mode: typing.Any = mode
        self.config: typing.Dict[str, typing.Any] = config

        self._message: discord.Message = None
        self.host: discord.Member = None
        self.players: typing.List[discord.Member] = []

        self.cancelled: bool = True

        self.join.label = _("Join Game")
        self.leave.label = _("Leave")
        self.view_players.label = _("View Players (1)")
        self.start_button.label = _("Start Game!")
        self.mode_select.options = [
            discord.SelectOption(
                label=mode.name,
                value=mode.name,
                emoji=mode.emoji,
                description=mode.description,
                default=mode == self.mode,
            )
            for mode in self.MODES
        ]
        for setting in (
            "show_dead_role",
            "dying_message",
            "town_traitor",
            "town_vip",
            "anomalies",
        ):
            button: discord.ui.Button = discord.ui.Button(
                label=setting.replace("_", " ").title(),
                style=(
                    discord.ButtonStyle.success
                    if self.config[setting]
                    else discord.ButtonStyle.danger
                ),
                custom_id=setting,
            )
            button.callback = self.setting_callback
            self.add_item(button)

    async def start(self, ctx: commands.Context) -> discord.Message:
        self.ctx: commands.Context = ctx
        self.host: discord.Member = ctx.author
        self.players.append(ctx.author)
        embed: discord.Embed = discord.Embed(
            title=_("Mafia Game"),
            description=_(
                "Click the button below to join the party! Please note that the maximum amount of players is 25."
            ),
            color=await self.ctx.embed_color(),
            timestamp=self.ctx.message.created_at,
        )
        if self.config["red_economy"]:
            currency_name = await bank.get_currency_name(self.ctx.guild)
            embed.add_field(
                name=_("Cost to play:"),
                value=f"**{self.config['cost_to_play']}** {currency_name}",
            )
            embed.add_field(
                name=_("Reward for winning:"),
                value=(
                    f"**{self.config['reward_for_winning']}** {currency_name}"
                    if not self.config["reward_for_winning_based_on_costs"]
                    else _("Based on the costs of the game.")
                ),
            )
        embed.set_author(
            name=_("Hosted by {host.display_name}").format(host=self.host),
            icon_url=self.host.display_avatar,
        )
        embed.set_footer(
            text=self.ctx.guild.name,
            icon_url=self.ctx.guild.icon,
        )
        self._message: discord.Message = await self.ctx.send(embed=embed, view=self)
        self.cog.views[self._message] = self
        return self._message

    async def on_timeout(self) -> None:
        for child in self.children:
            child: discord.ui.Item
            if hasattr(child, "disabled") and not (
                isinstance(child, discord.ui.Button) and child.style == discord.ButtonStyle.url
            ):
                child.disabled = True
        try:
            await self._message.edit(view=self)
        except discord.HTTPException:
            pass

    @discord.ui.button(label="Join Game", emoji="🎮", style=discord.ButtonStyle.success)
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if interaction.user in self.players:
            await interaction.response.send_message(
                _("You have already joined the game!"), ephemeral=True
            )
            return
        if len(self.players) >= 25:
            await interaction.response.send_message(
                _("The game is full, you can't join!"), ephemeral=True
            )
            return
        if (
            temp_banned_until := await self.cog.config.member(interaction.user).temp_banned_until()
        ) is not None:
            await interaction.response.send_message(
                _(
                    "You are **temporarily banned for {duration}** from joining Mafia games!"
                ).format(
                    duration=humanize_timedelta(
                        timedelta=temp_banned_until
                        - datetime.datetime.now(tz=datetime.timezone.utc)
                    )
                ),
                ephemeral=True,
            )
            return
        if any(
            game
            for game in self.cog.games.values()
            if game.get_player(interaction.user) is not None
        ):
            await interaction.response.send_message(
                _("You are already in a game of Mafia in another server!"), ephemeral=True
            )
            return
        self.players.append(interaction.user)
        self.view_players.label = _("View Players ({len_players})").format(
            len_players=len(self.players)
        )
        try:
            await self._message.edit(view=self)
        except discord.HTTPException:
            pass
        await interaction.response.send_message(_("You have joined the game!"), ephemeral=True)

    @discord.ui.button(label="Leave", style=discord.ButtonStyle.danger)
    async def leave(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if interaction.user not in self.players:
            await interaction.response.send_message(
                _("You have not joined the game!"), ephemeral=True
            )
            return
        self.players.remove(interaction.user)
        self.view_players.label = _("View Players ({len_players})").format(
            len_players=len(self.players)
        )
        try:
            await self._message.edit(view=self)
        except discord.HTTPException:
            pass
        await interaction.response.send_message(_("You have left the game!"), ephemeral=True)

    @discord.ui.button(label="View Players (1)", style=discord.ButtonStyle.secondary)
    async def view_players(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        if not self.players:
            await interaction.response.send_message(
                _("No one has joined the game yet!"), ephemeral=True
            )
            return
        embed = discord.Embed(
            title=_("Mafia Game - Players"),
            color=await self.ctx.embed_color(),
        )
        embed.set_author(
            name=_("Hosted by {host.display_name}").format(host=self.host),
            icon_url=self.host.display_avatar,
        )
        embed.set_footer(text=interaction.guild.name, icon_url=interaction.guild.icon)
        embed.description = "\n".join(
            f"**•** {player.mention} ({player.id})" for player in self.players
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Start Game!", style=discord.ButtonStyle.primary)
    async def start_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        if not (
            interaction.user == self.host
            or await self.ctx.bot.is_admin(interaction.user)
            or interaction.user.guild_permissions.manage_guild
            or interaction.user.id in interaction.client.owner_ids
        ):
            await interaction.response.send_message(_("You can't start the game!"), ephemeral=True)
            return
        if len(self.players) < 5:
            await interaction.response.send_message(
                _("You need at least 5 players to start the game!"), ephemeral=True
            )
            return
        self.cancelled: bool = False
        self.stop()
        await interaction.response.defer()
        await self.on_timeout()

    @discord.ui.button(emoji="✖️", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if interaction.user != self.host:
            await interaction.response.send_message(
                _("Only the host can cancel the game!"), ephemeral=True
            )
            return
        try:
            await self._message.delete()
        except discord.HTTPException:
            pass

    @discord.ui.select(placeholder="Select a mode...", options=[], row=1)
    async def mode_select(
        self, interaction: discord.Interaction, select: discord.ui.Select
    ) -> None:
        if not (
            interaction.user == self.host
            or await self.ctx.bot.is_admin(interaction.user)
            or interaction.user.guild_permissions.manage_guild
            or interaction.user.id in interaction.client.owner_ids
        ):
            await interaction.response.send_message(
                _("You can't change the mode of the game!"), ephemeral=True
            )
            return
        self.mode = discord.utils.get(self.MODES, name=select.values[0])
        await interaction.response.send_message(
            _("You have selected the **{mode}** mode!").format(mode=self.mode.name), ephemeral=True
        )
        for option in select.options:
            option.default = option.value == self.mode.name
        try:
            await self._message.edit(view=self)
        except discord.HTTPException:
            pass

    async def setting_callback(self, interaction: discord.Interaction) -> None:
        if not (
            interaction.user == self.host
            or await self.ctx.bot.is_admin(interaction.user)
            or interaction.user.guild_permissions.manage_guild
            or interaction.user.id in interaction.client.owner_ids
        ):
            await interaction.response.send_message(
                _("You can't change the settings of the game!"), ephemeral=True
            )
            return
        custom_id: str = interaction.data["custom_id"]
        self.config[custom_id] = not self.config[custom_id]
        discord.utils.get(self.children, custom_id=custom_id).style = (
            discord.ButtonStyle.success if self.config[custom_id] else discord.ButtonStyle.danger
        )
        await interaction.response.edit_message(view=self)


class StartMessageView(discord.ui.View):
    def __init__(self, cog, game) -> None:
        super().__init__(timeout=None)
        self.cog: commands.Cog = cog
        self.game = game
        self._message: discord.Message = None

        self.show_my_role.label = _("Show my Role")

    async def on_timeout(self) -> None:
        for child in self.children:
            child: discord.ui.Item
            if hasattr(child, "disabled") and not (
                isinstance(child, discord.ui.Button) and child.style == discord.ButtonStyle.url
            ):
                child.disabled = True
        try:
            await self._message.edit(view=self)
        except discord.HTTPException:
            pass

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if (player := self.game.get_player(interaction.user)) is None:
            await interaction.response.send_message(
                _("You are not a player in this game!"), ephemeral=True
            )
            return False
        if not all(p for p in self.game.players if p.role is not None):
            await interaction.response.send_message(
                _("Not all players have been assigned a role yet!"), ephemeral=True
            )
            return False
        if player.is_dead:
            await interaction.response.send_message(_("You are already dead!"), ephemeral=True)
            return False
        return True

    @discord.ui.button(emoji="🔍", label="Show my Role", style=discord.ButtonStyle.secondary)
    async def show_my_role(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        player = self.game.get_player(interaction.user)
        kwargs = player.role.get_kwargs()
        kwargs["embeds"] = [kwargs.pop("embed")]
        if player.is_town_traitor:
            kwargs["embeds"].append(
                discord.Embed(
                    title=_("🔪 You are {the_or_a} **Town Traitor**! 🔪").format(
                        the_or_a=(
                            _("the")
                            if len([p for p in self.game.players if p.is_town_traitor]) == 1
                            else _("a")
                        )
                    ),
                    description=_(
                        "You are a Villager, but you are secretly working for the Mafia."
                    ),
                    color=MAFIA_COLOR,
                )
            )
        if player.is_town_vip:
            kwargs["embeds"].append(
                discord.Embed(
                    title=_("🔪 You are {the_or_a} **Town VIP**! 🔪").format(
                        the_or_a=(
                            _("the")
                            if len([p for p in self.game.players if p.is_town_vip]) == 1
                            else _("a")
                        )
                    ),
                    description=_("Mafia have to kill you before winning the game."),
                    color=VILLAGERS_COLOR,
                )
            )
        if (
            player.role.side == "Mafia" and player.role.name != "Alchemist"
        ) or player.is_town_traitor:
            kwargs["embeds"].append(self.game.get_mafia_team_embed(player))
        if player.role.name == "Executioner":
            kwargs["embeds"].append(
                discord.Embed(
                    title=_(
                        "🔫 Your target is {player.global_target.member.display_name}! 🔫"
                    ).format(player=player),
                    description=_("You must get them lynched by the town."),
                    color=player.role.color(),
                )
            )
        await interaction.response.send_message(**kwargs, ephemeral=True)

    @discord.ui.button(label="Immunity Night 1", style=discord.ButtonStyle.secondary)
    async def immunity_night_1(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        if not (
            interaction.user == self.game.ctx.author
            or await interaction.client.is_admin(interaction.user)
            or interaction.user.guild_permissions.manage_guild
            or interaction.user.id in interaction.client.owner_ids
        ):
            await interaction.response.send_message(
                _("You are not allowed to use this interaction."), ephemeral=True
            )
            return
        view: ImmunityNight1View = ImmunityNight1View(self.cog, self.game)
        await view._update()
        await interaction.response.send_message(view=view, ephemeral=True)
        view._message = await interaction.original_response()
        self.cog.views[view._message] = view


class ImmunityNight1View(discord.ui.View):
    def __init__(self, cog: commands.Cog, game) -> None:
        super().__init__(timeout=180)
        self.cog: commands.Cog = cog
        self.game = game
        self._message: discord.Message = None

        self.select.placeholder = _("Make a selection...")

    async def _update(self) -> None:
        self.select.options = [
            discord.SelectOption(
                label=player.member.display_name,
                description=player.member.name,
                value=str(player.member.id),
            )
            for player in self.game.players
            if not player.is_dead
        ]
        self.select.max_values = len(self.select.options)

    async def on_timeout(self) -> None:
        if self._message is not None:
            try:
                await self._message.delete()
            except discord.HTTPException:
                pass

    @discord.ui.select(min_values=0, placeholder="Make a selection...")
    async def select(
        self, interaction: discord.Interaction, select: discord.ui.UserSelect
    ) -> None:
        self.game.immunity_night_1 = [
            self.game.get_player_by_id(int(value)) for value in select.values
        ]
        await interaction.response.send_message(
            _("You have selected {len_players} player{s} to be immune during the Night 1!").format(
                len_players=len(self.game.immunity_night_1),
                s="" if len(self.game.immunity_night_1) == 1 else "s",
            ),
            ephemeral=True,
        )


class SpectateView(discord.ui.View):
    def __init__(self, game) -> None:
        super().__init__(timeout=None)
        self.game = game
        self.spectaters: typing.List[discord.Member] = []
        self._message: discord.Message = None

        self.clear_items()
        self.add_item(
            discord.ui.Button(
                label=_("Jump to Mafia!"),
                style=discord.ButtonStyle.url,
                url=self.game.channel.jump_url,
            ),
        )
        if self.game.config["allow_spectators"]:
            self.add_item(self.spectate)
            self.spectate.label = _("Spectate")

    async def on_timeout(self) -> None:
        for child in self.children:
            child: discord.ui.Item
            if hasattr(child, "disabled") and not (
                isinstance(child, discord.ui.Button) and child.style == discord.ButtonStyle.url
            ):
                child.disabled = True
        try:
            await self._message.edit(view=self)
        except discord.HTTPException:
            pass

    @discord.ui.button(emoji="👀", label="Spectate", style=discord.ButtonStyle.secondary)
    async def spectate(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if interaction.user in self.spectaters:
            await interaction.response.send_message(
                _("You are already spectating the game!"), ephemeral=True
            )
            return
        if self.game.get_player(interaction.user) is not None:
            await interaction.response.send_message(
                _("You are a player in this game!"), ephemeral=True
            )
            return
        await self.game.channel.set_permissions(
            interaction.user, view_channel=True, read_messages=True, send_messages=False
        )
        await interaction.response.send_message(
            _("You are now spectating the game! 👀 Jump to {channel.mention}!").format(
                channel=self.game.channel
            ),
            ephemeral=True,
        )


class PerformActionView(discord.ui.View):
    def __init__(self, night) -> None:
        super().__init__(timeout=None)
        self.night = night
        self._message: discord.Message = None

        self.perform_action.label = _("Perform Action")
        if self.night.game.config["dying_message"]:
            self.dying_message.label = _("Dying Message")
        else:
            self.remove_item(self.dying_message)

    async def on_timeout(self) -> None:
        for child in self.children:
            child: discord.ui.Item
            if hasattr(child, "disabled") and not (
                isinstance(child, discord.ui.Button) and child.style == discord.ButtonStyle.url
            ):
                child.disabled = True
        try:
            await self._message.edit(view=self)
        except discord.HTTPException:
            pass

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if (player := self.night.game.get_player(interaction.user)) is None:
            await interaction.response.send_message(
                _("You are not a player in this game!"), ephemeral=True
            )
            return False
        if player.is_dead:
            await interaction.response.send_message(
                _("You are dead, you can't perform any action!"), ephemeral=True
            )
            return False
        return True

    @discord.ui.button(emoji="🔪", label="Perform Action", style=discord.ButtonStyle.success)
    async def perform_action(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)
        player = self.night.game.get_player(interaction.user)
        player.last_interaction = interaction
        if player.role.max_uses is not None and player.uses_amount >= player.role.max_uses:
            await interaction.followup.send(
                _("You have already used your action the maximum amount of times!"), ephemeral=True
            )
            return
        try:
            await player.role.perform_action(self.night, player, interaction)
        except NotImplementedError:
            await interaction.followup.send(
                _("You can't perform any night action!"), ephemeral=True
            )
        except RuntimeError as error:
            await interaction.followup.send(str(error), ephemeral=True)

    @discord.ui.button(emoji="💀", label="Dying Message", style=discord.ButtonStyle.danger)
    async def dying_message(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        player = self.night.game.get_player(interaction.user)
        await interaction.response.send_modal(DeathMessageModal(player))
        player.last_interaction = interaction


class SelectTargetsView(discord.ui.View):
    def __init__(
        self,
        day_night,
        player,
        targets_number: int = 1,
        self_allowed: bool = True,
        mafia_allowed: bool = True,
        last_target_allowed: bool = True,
        condition: typing.Callable[[typing.Any, typing.Any], bool] = None,
        two_selects: bool = False,
        second_select_optional: bool = False,
    ) -> None:
        if not isinstance(self, GuessTargetsRolesView):
            super().__init__(timeout=180)
        self.day_night = day_night
        self.player = player
        self.targets_number: int = targets_number
        self.self_allowed: bool = self_allowed
        self.mafia_allowed: bool = mafia_allowed
        self.last_target_allowed: bool = last_target_allowed
        self.condition: typing.Callable[[typing.Any, typing.Any], bool] = condition
        self.two_selects: bool = two_selects
        self.second_select_optional: bool = second_select_optional

        self.first_target: typing.Any = None

        self.possible_targets: typing.List[typing.Any] = []
        last_day_night_target = (
            self.day_night.game.days_nights[-3].targets.get(self.player)
            if len(self.day_night.game.days_nights) >= 3
            else None
        )
        day_night_target = self.day_night.targets.get(self.player)
        for select in [self.select] + ([self.second_select] if self.two_selects else []):
            for target in (
                self.day_night.game.alive_players
                if select is not self.select or self.player.role.name not in ("Mortician", "Necromancer")
                else self.day_night.game.dead_players
            ):
                if (
                    day_night.number == 1 and target in day_night.game.immunity_night_1
                ):  # and self.player.role.name in KILLING_ROLES:
                    continue
                if not self.self_allowed and target == self.player:
                    continue
                if (
                    not self.mafia_allowed
                    and target.role.side == "Mafia"
                    and target.role.name != "Alchemist"
                ):
                    continue
                if not self.last_target_allowed and target == last_day_night_target:
                    continue
                if self.condition is not None and not self.condition(self.player, target):
                    continue
                self.possible_targets.append(target)
                select.add_option(
                    label=target.member.display_name,
                    description=target.member.name,
                    value=str(target.member.id),
                    emoji="🫠" if target == self.player else None,
                    default=(
                        target == day_night_target
                        if not isinstance(day_night_target, typing.Tuple)
                        else target in day_night_target
                    ),
                )
        if len(self.select.options) < self.targets_number:
            raise RuntimeError(_("There are no valid target to select!"))
        self._message: discord.Message = None

        self.select.max_values = self.targets_number
        if self.player.role.name == "God Father":
            self.select.placeholder = _("Select a target to kill ") + (
                "with your mafia."
                if any(player.role.name == "Mafia" for player in self.day_night.game.players)
                else "yourself."
            )
        else:
            self.select.placeholder = (
                _("Select a target.")
                if self.targets_number == 1
                else _("Select {targets_number} targets.").format(
                    targets_number=self.targets_number
                )
            )

        if self.player.role.name == "Bomber":
            self.boom.label = _("BOOM!")
        else:
            self.remove_item(self.boom)
        if self.player.role.name == "Starspawn":
            self.daybreak.label = _("Daybreak")
        else:
            self.remove_item(self.daybreak)
        if not self.two_selects:
            self.remove_item(self.second_select)

    async def on_timeout(self) -> None:
        try:
            await self._message.delete()
        except discord.HTTPException:
            pass

    @discord.ui.select(min_values=0, max_values=1, placeholder="Select a target.")
    async def select(self, interaction: discord.Interaction, select: discord.ui.Select) -> None:
        if self.two_selects or isinstance(self, GuessTargetsRolesView):
            await interaction.response.defer()
            self.first_target = self.day_night.game.get_player_by_id(int(select.values[0]))
            if self.second_select_optional:
                return
        if select.values:
            if self.targets_number == 1:
                target = self.day_night.game.get_player_by_id(int(select.values[0]))
                if not self.two_selects and not isinstance(self, GuessTargetsRolesView):
                    self.day_night.targets[self.player] = target
                    await interaction.response.send_message(
                        _("You have selected {target.member.mention}!").format(target=target),
                        ephemeral=True,
                    )
                else:
                    self.day_night.targets[self.player] = (target, None)
                    await interaction.response.send_message(
                        _(
                            "You have selected {target.member.mention}! If you don't select your second target, you will perform your special action."
                        ),
                        ephemeral=True,
                    )
            elif len(select.values) < self.targets_number:
                self.day_night.targets.pop(self.player, None)
                await interaction.response.send_message(
                    _("You need to select {targets_number} targets!").format(
                        targets_number=self.targets_number
                    ),
                    ephemeral=True,
                )
            else:
                targets = tuple(
                    [self.day_night.game.get_player_by_id(int(value)) for value in select.values]
                )
                self.day_night.targets[self.player] = targets
                await interaction.response.send_message(
                    _("You have selected {len_targets} targets!").format(len_targets=len(targets)),
                    ephemeral=True,
                )
        else:
            self.day_night.targets.pop(self.player, None)
            await interaction.response.send_message(_("You have unselected!"), ephemeral=True)
        self.player.last_interaction = interaction

    @discord.ui.button(emoji="💣", label="BOOM!", style=discord.ButtonStyle.danger)
    async def boom(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.day_night.targets[self.player] = None
        await interaction.response.send_message(
            _("You have chosen to make explode all the bombs you already planted!"), ephemeral=True
        )
        self.player.last_interaction = interaction

    @discord.ui.button(emoji="🌥️", label="Daybreak", style=discord.ButtonStyle.secondary)
    async def daybreak(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.day_night.targets[self.player] = None
        await interaction.response.send_message(
            _("You have chosen to block all days-actions from happening tomorrow!"), ephemeral=True
        )
        self.player.last_interaction = interaction

    @discord.ui.select(min_values=0, max_values=1, placeholder="Select a target.")
    async def second_select(
        self, interaction: discord.Interaction, select: discord.ui.Select
    ) -> None:
        if self.first_target is None:
            await interaction.response.send_message(
                _("You need to select a target first!"), ephemeral=True
            )
            return
        if select.values:
            target = self.day_night.game.get_player_by_id(int(select.values[0]))
            self.day_night.targets[self.player] = (self.first_target, target)
            await interaction.response.send_message(
                _(
                    "You have selected {first_target.member.mention} and {target.member.mention}!"
                ).format(first_target=self.first_target, target=target),
                ephemeral=True,
            )
        else:
            self.day_night.targets.pop(self.player, None)
            await interaction.response.send_message(_("You have unselected!"), ephemeral=True)
        self.player.last_interaction = interaction


class SelectRolesView(discord.ui.View):
    def __init__(
        self,
        day_night,
        player,
        ROLES: typing.List[typing.Any],
        self_allowed: bool = True,
        mafia_allowed: bool = True,
        last_target_allowed: bool = True,
        condition: typing.Callable[[typing.Any, typing.Any], bool] = None,
    ) -> None:
        if not isinstance(self, GuessTargetsRolesView):
            super().__init__(timeout=180)
        self.day_night = day_night
        self.player = player
        self.ROLES: typing.List[typing.Any] = ROLES
        self.self_allowed: bool = self_allowed
        self.mafia_allowed: bool = mafia_allowed
        self.last_target_allowed: bool = last_target_allowed
        self.condition: typing.Callable[[typing.Any, typing.Any], bool] = condition
        self._message: discord.Message = None

        last_day_night_target = (
            self.day_night.game.days_nights[-3].targets.get(self.player)
            if len(self.day_night.game.days_nights) >= 3
            else None
        )
        self.possible_roles: typing.List[typing.Type[typing.Any]] = sorted(
            [
                role
                for role in self.ROLES
                if (
                    (self.self_allowed or role != self.player.role)
                    and (self.mafia_allowed or role.side != "Mafia")
                    and (self.last_target_allowed or role != last_day_night_target)
                    and (self.condition is None or self.condition(self.player, role))
                )
            ],
            key=lambda role: role.name,
        )
        day_night_target = self.day_night.targets.get(self.player)
        for i, _roles in enumerate(discord.utils.as_chunks(self.possible_roles, 25)):
            select = discord.ui.Select(
                min_values=0,
                max_values=1,
                placeholder=_("Select a role."),
            )
            select.callback = functools.partial(self.role_select, select=select)
            for role in _roles:
                select.add_option(
                    label=role.name,
                    description=role.side,
                    value=role.name,
                    default=(
                        role == day_night_target
                        if not isinstance(day_night_target, typing.Tuple)
                        else role in day_night_target
                    ),
                )
            self.add_item(select)

    async def on_timeout(self) -> None:
        try:
            await self._message.delete()
        except discord.HTTPException:
            pass

    async def role_select(
        self, interaction: discord.Interaction, select: discord.ui.Select
    ) -> None:
        if isinstance(self, GuessTargetsRolesView) and self.first_target is None:
            await interaction.response.send_message(
                _("You need to select a target first!"), ephemeral=True
            )
            return
        if select.values:
            role = discord.utils.get(self.ROLES, name=select.values[0])
            if not isinstance(self, GuessTargetsRolesView):
                self.day_night.targets[self.player] = role
            elif self.pages == 1:
                self.day_night.targets[self.player] = (self.first_target, role)
            else:
                self.targets[self.page] = (self.first_target, role)
                if all(None not in target for target in self.targets):
                    self.day_night.targets[self.player] = self.targets.copy()
            await interaction.response.send_message(
                _("You have selected the **{role.name}** role{for_player}!").format(
                    role=role,
                    for_player=(
                        ""
                        if not isinstance(self, GuessTargetsRolesView)
                        else _(" for {player.member.mention}").format(player=self.first_target)
                    ),
                ),
                ephemeral=True,
            )
        else:
            self.day_night.targets.pop(self.player, None)
            await interaction.response.send_message(_("You have unselected!"), ephemeral=True)
        self.player.last_interaction = interaction


class GuessTargetsRolesView(SelectTargetsView, SelectRolesView):
    def __init__(
        self,
        night,
        player,
        ROLES: typing.List[typing.Any],
        targets_number: int = 1,
        self_allowed: bool = True,
        mafia_allowed: bool = True,
        last_target_allowed: bool = True,
        condition: typing.Callable[[typing.Any, typing.Any], bool] = None,
    ) -> None:
        self.pages: int = targets_number
        self.page: int = 0
        discord.ui.View.__init__(self, timeout=180)
        SelectTargetsView.__init__(
            self,
            night,
            player,
            targets_number=1,
            self_allowed=self_allowed,
            mafia_allowed=mafia_allowed,
            last_target_allowed=last_target_allowed,
            condition=condition,
        )
        SelectRolesView.__init__(
            self,
            night,
            player,
            ROLES,
            self_allowed=self_allowed,
            mafia_allowed=mafia_allowed,
            last_target_allowed=last_target_allowed,
            condition=condition,
        )
        self._message: discord.Message = None
        self.targets: typing.List[typing.Tuple[typing.Any, typing.Any]] = [
            (None, None) for _ in range(self.pages)
        ]


class DeathMessageModal(discord.ui.Modal):
    def __init__(self, player) -> None:
        super().__init__(title=_("Dying Message"))
        self.player = player
        self.dying_message: discord.ui.TextInput = discord.ui.TextInput(
            label=_("Dying Message:"),
            placeholder=_("Enter your death message..."),
            style=discord.TextStyle.long,
            min_length=1,
            max_length=200,
            required=False,
            default=self.player.dying_message,
        )
        self.add_item(self.dying_message)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        self.player.dying_message = self.dying_message.value.strip() or None
        await interaction.response.send_message(
            _("Your death message has been set!"), ephemeral=True
        )


class VoteView(discord.ui.View):
    def __init__(self, day, remaining_players: typing.List) -> None:
        super().__init__(timeout=None)
        self.day = day
        self.remaining_players: typing.List = remaining_players
        for player in self.remaining_players:
            self.select.add_option(
                label=player.member.display_name,
                description=player.member.name,
                value=str(player.member.id),
            )
        self.votes: typing.Dict = {}
        self._message: discord.Message = None

        self.select.placeholder = _("Select a player to vote against.")
        self.perform_action.label = _("Perform Action")

    async def on_timeout(self) -> None:
        for child in self.children:
            child: discord.ui.Item
            if hasattr(child, "disabled") and not (
                isinstance(child, discord.ui.Button) and child.style == discord.ButtonStyle.url
            ):
                child.disabled = True
        try:
            await self._message.edit(view=self)
        except discord.HTTPException:
            pass

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if (player := self.day.game.get_player(interaction.user)) is None:
            await interaction.response.send_message(
                _("You are not a player in this game!"), ephemeral=True
            )
            return False
        if player.is_dead:
            await interaction.response.send_message(
                _("You are dead, you can't vote!"), ephemeral=True
            )
            return False
        self.day.game.afk_players.pop(player, None)
        last_night = self.day.game.days_nights[-2]
        if (
            player.role.name == "Gambler"
            and player in last_night.targets
            and last_night.gamblers_dices[player] == "yellow"
            and not last_night.gamblers_results[player][0]
        ):
            await interaction.response.send_message(
                _("You have **rolled a yellow dice** and lost, you can't vote today!"),
                ephemeral=True,
            )
            return False
        if player in [t for p, t in last_night.targets.items() if p.role.name == "Blackmailer"]:
            await interaction.response.send_message(
                _("You are **blackmailed**, you can't vote today!"), ephemeral=True
            )
            return False
        if (
            targeter := next(
                (
                    p
                    for p, t in last_night.targets.items()
                    if p.role.name == "Baker" and t == player
                ),
                None,
            )
        ) is not None and last_night.bakers_effects[targeter] == "vote_lost":
            await interaction.response.send_message(
                _("You are **breaded**, you can't vote today!").format(targeter=targeter),
                ephemeral=True,
            )
            return False
        return True

    @discord.ui.select(placeholder="Select a player to vote against.", min_values=0, max_values=1)
    async def select(self, interaction: discord.Interaction, select: discord.ui.Select) -> None:
        voter = self.day.game.get_player(interaction.user)
        if select.values:
            player = next(
                (
                    player
                    for player in self.remaining_players
                    if int(select.values[0]) == player.member.id
                )
            )
            self.votes[voter] = player
            await interaction.response.send_message(
                _("You have voted against {player.member.mention}!").format(player=player),
                ephemeral=True,
            )
        else:
            self.votes.pop(voter, None)
            await interaction.response.send_message(_("You have unvoted!"), ephemeral=True)
        voter.last_interaction = interaction

    @discord.ui.button(emoji="⚖️", label="Perform Action", style=discord.ButtonStyle.success)
    async def perform_action(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        if (
            starspawn := next(
                (t is None for p, t in self.day.targets.items() if p.role.name == "Starspawn"),
                None,
            )
        ) is not None:
            await interaction.response.send_message(
                _("All day-actions have been blocked for today by {the_or_a} Starspawn!").format(
                    the_or_a=starspawn.role.the_or_a(self.day.game)
                ),
                ephemeral=True,
            )
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        player = self.day.game.get_player(interaction.user)
        player.last_interaction = interaction
        if player.role.max_uses is not None and player.uses_amount >= player.role.max_uses:
            await interaction.followup.send(
                _("You have already used your action the maximum amount of times!"), ephemeral=True
            )
            return
        try:
            await player.role.perform_day_action(self.day, player, interaction)
        except NotImplementedError:
            await interaction.followup.send(_("You can't perform any day action!"), ephemeral=True)
        except RuntimeError as error:
            await interaction.followup.send(str(error), ephemeral=True)


class JudgementView(discord.ui.View):
    def __init__(self, day, target) -> None:
        super().__init__(timeout=None)
        self.day = day
        self.target = target
        self._message: discord.Message = None

        self.results: typing.Dict[discord.Member, typing.Optional[bool]] = {}

        self.guilty.label = _("GUILTY")
        self.innocent.label = _("INNOCENT")
        self.abstain.label = _("Abstain")

    async def on_timeout(self) -> None:
        for child in self.children:
            child: discord.ui.Item
            if hasattr(child, "disabled") and not (
                isinstance(child, discord.ui.Button) and child.style == discord.ButtonStyle.url
            ):
                child.disabled = True
        try:
            await self._message.edit(view=self)
        except discord.HTTPException:
            pass

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if (player := self.day.game.get_player(interaction.user)) is None:
            await interaction.response.send_message(
                _("You are not a player in this game!"), ephemeral=True
            )
            return False
        if player.is_dead:
            await interaction.response.send_message(
                _("You are dead, you can't vote!"), ephemeral=True
            )
            return False
        self.day.game.afk_players.pop(player, None)
        if player == self.target:
            await interaction.response.send_message(
                _("You can't vote on your own judgement!"), ephemeral=True
            )
            return False
        last_night = self.day.game.days_nights[-2]
        if (
            player.role.name == "Gambler"
            and player in last_night.targets
            and last_night.gamblers_dices[player] == "yellow"
            and not last_night.gamblers_results[player][0]
        ):
            await interaction.response.send_message(
                _("You have **rolled a yellow dice** and lost, you can't vote today!"),
                ephemeral=True,
            )
            return False
        if player in [t for p, t in last_night.targets.items() if p.role.name == "Blackmailer"]:
            await interaction.response.send_message(
                _("You are **blackmailed**, you can't vote today!"), ephemeral=True
            )
            return False
        if (
            targeter := next(
                (
                    p
                    for p, t in last_night.targets.items()
                    if p.role.name == "Baker" and t == player
                ),
                None,
            )
        ) is not None and last_night.bakers_effects[targeter] == "vote_lost":
            await interaction.response.send_message(
                _("You are **breaded**, you can't vote today!").format(targeter=targeter),
                ephemeral=True,
            )
            return False
        return True

    async def _update(self) -> None:
        embed: discord.Embed = self._message.embeds[0]
        embed.clear_fields()
        guilty_voters = [voter for voter in self.results if self.results[voter]]
        innocent_voters = [voter for voter in self.results if self.results[voter] is False]
        manipulator = next(
            (
                player
                for player in sorted(self.day.targets.keys(), key=self.day.game.players.index)
                if player.role.name == "Manipulator"
            ),
            None,
        )
        embed.add_field(
            name=_("👿 GUIlTY ({len_guilty})").format(len_guilty=len(guilty_voters))
            + (":" if guilty_voters else ""),
            value=(
                "\n".join([f"🔴 {voter.member.mention}" for voter in guilty_voters])
                if not self.day.game.config["anonymous_judgement"] and manipulator is None
                else "\u200b"
            ),
        )
        embed.add_field(
            name=_("😇 INNOCENT ({len_innocent})").format(len_innocent=len(innocent_voters))
            + (":" if innocent_voters else ""),
            value=(
                "\n".join([f"🔵 {voter.member.mention}" for voter in innocent_voters])
                if not self.day.game.config["anonymous_judgement"] and manipulator is None
                else "\u200b"
            ),
        )
        try:
            await self._message.edit(embed=embed, attachments=[])
        except discord.HTTPException:
            pass

    @discord.ui.button(emoji="👿", label="GUILTY", style=discord.ButtonStyle.danger)
    async def guilty(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        player = self.day.game.get_player(interaction.user)
        self.results[player] = True
        await interaction.response.send_message(_("You have voted **GUILTY**!"), ephemeral=True)
        player.last_interaction = interaction
        await self._update()

    @discord.ui.button(emoji="😇", label="INNOCENT", style=discord.ButtonStyle.success)
    async def innocent(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        player = self.day.game.get_player(interaction.user)
        self.results[player] = False
        await interaction.response.send_message(_("You have voted **INNOCENT**!"), ephemeral=True)
        player.last_interaction = interaction
        await self._update()
        if player.role.name == "Lawyer":
            await player.role.perform_day_action(self.day, player, interaction, target=self.target)

    @discord.ui.button(label="Abstain", style=discord.ButtonStyle.secondary)
    async def abstain(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        player = self.day.game.get_player(interaction.user)
        self.results[player] = None
        await interaction.response.send_message(_("You have abstained!"), ephemeral=True)
        player.last_interaction = interaction
        await self._update()


class IsekaiView(discord.ui.View):
    def __init__(self, player, roles: typing.List[typing.Any]) -> None:
        super().__init__(timeout=180)
        self.player = player
        self.roles: typing.List[typing.Any] = roles
        self.selected_role: typing.Optional[typing.Any] = None
        self._message: discord.Message = None

        self.select.placeholder = _("Select the role you want to reincarnate as.")
        for role in self.roles:
            self.select.add_option(
                label=role.name,
                value=role.name,
            )

    async def on_timeout(self) -> None:
        for child in self.children:
            child: discord.ui.Item
            if hasattr(child, "disabled") and not (
                isinstance(child, discord.ui.Button) and child.style == discord.ButtonStyle.url
            ):
                child.disabled = True
        try:
            await self._message.edit(view=self)
        except discord.HTTPException:
            pass
        role = self.selected_role or random.choice(self.roles)
        self.player.role = role
        self.player.is_dead = False
        await self.player.member.send(
            content=_("You have reincarnated as **{role.name}**!").format(role=role),
            **role.get_kwargs(self.player, change=True),
            reference=self._message.to_reference(fail_if_not_exists=False),
        )

    @discord.ui.select(placeholder="Select the role you want to reincarnate as.")
    async def select(self, interaction: discord.Interaction, select: discord.ui.Select) -> None:
        await interaction.response.defer()
        self.player.last_interaction = interaction
        self.selected_role = discord.utils.get(self.roles, name=select.values[0])
        await self.on_timeout()


class GamblerView(discord.ui.View):
    def __init__(self, night, player) -> None:
        super().__init__(timeout=180)
        self.night = night
        self.player = player
        self._message: discord.Message = None

        self.select.placeholder = _("Select a dice to throw.")
        self.select.add_option(
            emoji="⬜",
            label=_("White Dice"),
            value="white",
            description=_("70% chance of success"),
        )
        self.select.add_option(
            emoji="🟨",
            label=_("Yellow Dice"),
            value="yellow",
            description=_("50% chance of success"),
        )
        self.select.add_option(
            emoji="🟥",
            label=_("Red Dice"),
            value="red",
            description=_("20% chance of success"),
        )

    async def on_timeout(self) -> None:
        try:
            await self._message.delete()
        except discord.HTTPException:
            pass

    @discord.ui.select(min_values=0, max_values=1, placeholder="Select a dice to throw.")
    async def select(self, interaction: discord.Interaction, select: discord.ui.Select) -> None:
        if select.values:
            dice = select.values[0]
            self.night.targets[self.player] = None
            self.night.gamblers_dices[self.player] = dice
            await interaction.response.send_message(
                _("You have thrown the **{dice}** dice!").format(dice=dice.title()),
                ephemeral=True,
            )
        else:
            self.night.targets.pop(self.player, None)
            self.night.gamblers_dices.pop(self.player, None)
            await interaction.response.send_message(_("You have unselected!"), ephemeral=True)
        self.player.last_interaction = interaction


class JudgeView(discord.ui.View):
    def __init__(self, day, player) -> None:
        super().__init__(timeout=None)
        self.day = day
        self.player = player
        self._message: discord.Message = None

        for target in self.day.game.alive_players:
            if target == self.player:
                continue
            self.select.add_option(
                label=f"{target.member.display_name} ({target.member.name})",
                value=str(target.member.id),
            )
        self.select.placeholder = _("Select a player to prosecute.")

    async def on_timeout(self) -> None:
        try:
            await self._message.delete()
        except discord.HTTPException:
            pass

    @discord.ui.select(placeholder="Select a player to prosecute.")
    async def select(self, interaction: discord.Interaction, select: discord.ui.Select) -> None:
        await interaction.response.defer()
        target = self.day.game.get_player_by_id(int(select.values[0]))
        await self.on_timeout()
        await self.player.role.day_action(self.day, self.player, target)


class ExplainView(discord.ui.View):
    def __init__(
        self,
        ROLES: typing.List[typing.Any],
        MODES: typing.List[typing.Any],
        ANOMALIES: typing.List[typing.Any],
        page: str = "main",
    ) -> None:
        super().__init__(timeout=180)
        self.ctx: commands.Context = None
        self._message: discord.Message = None

        self.ROLES: typing.List[typing.Any] = ROLES
        self.MODES: typing.List[typing.Any] = MODES
        self.ANOMALIES: typing.List[typing.Any] = ANOMALIES

        self.page: str = page
        GodFather = discord.utils.get(self.ROLES, name="God Father")
        Mayor = discord.utils.get(self.ROLES, name="Mayor")
        self.pages: typing.Dict[
            str,
            typing.Dict[
                typing.Literal["label", "emoji", "embeds", "files", "command"],
                typing.Union[str, typing.List[typing.Union[discord.Embed, str]]],
            ],
        ] = {
            "main": {
                "emoji": "🏠",
                "label": _("Main Page"),
                "embeds": [
                    discord.Embed(
                        title=_("How to play the Mafia game?"),
                        description=_(
                            "Mafia is a party game where players are secretly assigned roles that determine their objectives."
                        ),
                    ).set_thumbnail(url=GodFather.image_url()),
                ],
                "files": [os.path.join("roles", GodFather.image_name())],
            },
            "phases": {
                "emoji": "🌅",
                "label": _("Phases"),
                "embeds": [
                    discord.Embed(
                        title=_("**Phases:**"),
                        description=_("The game is divided into several phases."),
                    ),
                    discord.Embed(
                        title=_("🌙 Night Phase"),
                        description=_(
                            "At night, players with night actions can use their abilities, possibly choose their target(s). The Mafia can kill a player, the Doctor can save a player, the Detective can investigate a player, etc."
                        ),
                        color=NIGHT_COLOR,
                    ),
                    discord.Embed(
                        title=_("🌞 Day Phase"),
                        description=_(
                            "At the end of the night, the various events of the night and the victims of the Mafia are described. Players then have a time to talk and identify who to vote against."
                        ),
                        color=DAY_COLOR,
                    ),
                    discord.Embed(
                        title=_("⚖️ Voting & Judgement Phases"),
                        description=_(
                            "- Once the speaking time is up, players who are still alive can vote against those they wish to eliminate. A minimum number of votes must be reached, worth around half the remaining players. Some players may have multiple votes for the whole game (like the Mayor), or just one day.\n- If a player is nominated by enough players, they have a time to defend themselves before a new vote, for which the answer can be “Guilty”, “Innocent” or “Abstain”. This time, if more players vote “Guilty”, the player is lynched. Depending on the configuration, his role or death message will be displayed for all to see."
                        ),
                        color=VOTING_AND_JUDGEMENT_COLOR,
                    ),
                    discord.Embed(
                        title=_("🔁 Repeat"),
                        description=_("The game continues until one side or a Neutral role wins."),
                    ),
                ],
            },
            "roles": {
                "emoji": "🎭",
                "label": _("Roles"),
                "embeds": [
                    discord.Embed(
                        title=_("**Roles ({len_roles}):**").format(len_roles=len(self.ROLES)),
                        description=_(
                            "There are many different roles in the game. Each role has its own abilities and objectives. They are randomly assigned to players at the beginning of the game."
                        ),
                    ),
                    discord.Embed(
                        title=_("Mafia Roles ({len_mafia_roles})").format(
                            len_mafia_roles=len(
                                [role for role in self.ROLES if "Mafia" in role.side]
                            )  # Including Alchemist.
                        ),
                        description=_(
                            "The Mafia is a group of players who know each other and must eliminate the Villagers. The God Father is the leader of the Mafia and choose the victim each night.\n🏆 The Mafia wins when their number is equal to or greater than the half of the alive players."
                        ),
                        color=MAFIA_COLOR,
                    ).set_thumbnail(url=GodFather.image_url()),
                    discord.Embed(
                        title=_("Villagers' Roles ({len_villagers_roles})").format(
                            len_villagers_roles=len(
                                [role for role in self.ROLES if "Villagers" in role.side]
                            )  # Including Alchemist.
                        ),
                        description=_(
                            "The Villagers are the majority of the players. They don't know each other and must eliminate the Mafia. The Mayor is the leader of the Town and can choose to revelate their role to everyone.\n🏆 The Villagers win when all the Mafia members and the Bomber are dead."
                        ),
                        color=VILLAGERS_COLOR,
                    ).set_thumbnail(url=Mayor.image_url()),
                    discord.Embed(
                        title=_("Neutral Roles ({len_neutral_roles})").format(
                            len_neutral_roles=len(
                                [role for role in self.ROLES if role.side == "Neutral"]
                            )
                        ),
                        description=_(
                            "The Neutral roles have their own objectives and can win alone or with another side."
                        ),
                        color=NEUTRAL_COLOR,
                    ),
                    discord.Embed(
                        description=_(
                            "ℹ️ See `{prefix}mafia roles` or `{prefix}mafia role <role>` for more information."
                        ).format(prefix="[p]"),
                    ),
                    discord.Embed(
                        title=_("Roles Priority"),
                        description=_(
                            " Each role waits for an action to finish before proceeding to the next role. This is the reason why sometimes you die before you could do your action. The roles are resolved in a specific order. If two players have the same role, the player who joined the game first will have their role resolved first."
                        ),
                    ),
                ],
                "files": [
                    os.path.join("roles", GodFather.image_name()),
                    os.path.join("roles", Mayor.image_name()),
                ],
                "command": "mafia roles",
            },
            "modes": {
                "emoji": "🎮",
                "label": _("Modes"),
                "embeds": [
                    discord.Embed(
                        title=_("**Modes:**"),
                        description=_(
                            "There are several possible modes.\n- {predefined_modes_number} have predefined options and make specific choices depending on the number of players.\n- A `Random` mode works from the number of players and selects roles randomly according to the number of players on Mafia's side, Villagers' side or Neutral's side required.\n- A `Custom` mode depends on your own preferences with `{prefix}setmafia customroles <roles...>`.\nℹ️ See `{prefix}mafia modes` or `{prefix}mafia mode <mode>` for more information."
                        ).format(prefix="[p]", predefined_modes_number=len(self.MODES) - 2),
                        color=MODES_COLOR,
                    ),
                ],
                "command": "mafia modes",
            },
            "town_traitor_town_vip": {
                "emoji": "🔪",
                "label": _("Town Traitor & Town VIP"),
                "embeds": [
                    discord.Embed(
                        title=_("**Town Traitor:**"),
                        description=_(
                            "The Town Traitor is a member of the Town who is secretly working with the Mafia. The Town Traitor wins with the Mafia.\n⚠️ Warning: the Mayor could be the Town Traitor!"
                        ),
                        color=MAFIA_COLOR,
                    ).set_thumbnail(url="attachment://town_traitor.png"),
                    discord.Embed(
                        title=_("**Town VIP:**"),
                        description=_(
                            "The Town VIP is a member of the Town that the Mafia must kill to win. The Villagers win if the Town VIP is alive at the end of the game."
                        ),
                        color=VILLAGERS_COLOR,
                    ).set_thumbnail(url="attachment://town_vip.png"),
                ],
                "files": ["town_traitor", "town_vip"],
            },
            "anomalies": {
                "emoji": "🔍",
                "label": _("Anomalies"),
                "embeds": [
                    discord.Embed(
                        title=_("**Anomalies:**"),
                        description=_(
                            "Anomalies are special events that can occur during the game. They can be beneficial or harmful. Each turn, they have 40% chance to occur and a random anomaly among the {anomalies_number} existing will be selected.\nℹ️ See `{prefix}mafia anomalies` or `{prefix}mafia anomaly <anomaly>` for more information."
                        ).format(prefix="[p]", anomalies_number=len(self.ANOMALIES)),
                        color=ANOMALIES_COLOR,
                    ),
                ],
                "command": "mafia anomalies",
            },
            "achievements": {
                "emoji": "🏆",
                "label": _("Achievements"),
                "embeds": [
                    discord.Embed(
                        title=_("**Achievements:**"),
                        description=_(
                            "Achievements are special goals that players can achieve during the game. They can be general or specific to a role. They are global for all the servers. If you get an achievement, you will receive a DM when a game ends.\nℹ️ You can check them with `{prefix}mafia achievements`."
                        ).format(prefix="[p]"),
                        color=ACHIEVEMENTS_COLOR,
                    ),
                ],
                "command": "mafia achievements",
            },
        }

        self.execute_command.label = _("More Information")

    def get_kwargs(
        self,
        page: typing.Optional[str] = None,
        files_key: str = "files",
    ) -> typing.Dict[
        str, typing.Union[typing.List[discord.Embed], typing.List[discord.File], "ExplainView"]
    ]:
        page = page or self.page
        return {
            "embeds": self.pages[page]["embeds"],
            files_key: [get_image(file) for file in self.pages[page].get("files", [])],
            "view": self,
        }

    async def start(self, ctx: commands.Context) -> None:
        self.ctx: commands.Context = ctx
        await self._update(edit_message=False)
        kwargs = self.get_kwargs()
        self._message = await self.ctx.send(**kwargs)

    async def _update(self, edit_message: bool = True) -> None:
        self.clear_items()
        self.select_page.options.clear()
        for page, data in self.pages.items():
            self.select_page.add_option(
                emoji=data["emoji"],
                label=data["label"],
                value=page,
                default=page == self.page,
            )
        self.add_item(self.select_page)
        if "command" in self.pages[self.page]:
            self.add_item(self.execute_command)
        self.add_item(self.close)
        try:
            if await self.ctx.bot.get_command("mafia start").can_run(self.ctx):
                self.add_item(self.send_all)
        except commands.CommandError:
            pass
        self.add_item(
            discord.ui.Button(
                emoji="💖",
                label=_("Support the Dev!"),
                style=discord.ButtonStyle.link,
                url="https://buymeacoffee.com/aaa3a",
            ),
        )
        if edit_message:
            try:
                await self._message.edit(
                    **self.get_kwargs(files_key="attachments"),
                )
            except discord.HTTPException:
                pass

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id not in [self.ctx.author.id] + list(self.ctx.bot.owner_ids):
            await interaction.response.send_message(
                _("You are not allowed to use this interaction."), ephemeral=True
            )
            return False
        return True

    async def on_timeout(self) -> None:
        try:
            await self._message.delete()
        except discord.HTTPException:
            pass

    @discord.ui.select(min_values=1, max_values=1, placeholder="Select a page.")
    async def select_page(
        self, interaction: discord.Interaction, select: discord.ui.Select
    ) -> None:
        await interaction.response.defer()
        self.page = select.values[0]
        await self._update()

    @discord.ui.button(emoji="ℹ️", label="More Information", style=discord.ButtonStyle.secondary)
    async def execute_command(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await interaction.response.defer()
        command = self.pages[self.page]["command"]
        await CogsUtils.invoke_command(
            bot=interaction.client,
            author=interaction.user,
            channel=interaction.channel,
            command=command,
        )

    @discord.ui.button(emoji="✖️", style=discord.ButtonStyle.danger)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer()
        try:
            await self._message.delete()
        except discord.HTTPException:
            pass

    @discord.ui.button(emoji="📜", style=discord.ButtonStyle.secondary)
    async def send_all(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer()
        for i, page in enumerate(self.pages):
            kwargs = self.get_kwargs(page)
            if i != len(self.pages) - 1:
                kwargs["embeds"].append(discord.Embed(title="\u200b"))
            del kwargs["view"]
            await interaction.channel.send(**kwargs)

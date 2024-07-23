from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import asyncio
import datetime
import random

_: Translator = Translator("SplitOrSteal", __file__)


class SplitOrStealGameView(discord.ui.View):
    def __init__(
        self,
        cog: commands.Cog,
    ) -> None:
        super().__init__(timeout=120 + 60 + 10)
        self.ctx: commands.Context = None
        self.cog: commands.Cog = cog

        self.initial_players: typing.List[discord.Member] = []
        self.players: typing.Dict[discord.Member, typing.Literal["split", "steal"]] = {}

        self._message: discord.Message = None
        self._mode: typing.Literal["join", "play"] = None

    async def start(self, ctx: commands.Context) -> None:
        self.ctx: commands.Context = ctx
        embed: discord.Embed = discord.Embed(
            title="SplitOrSteal Game", color=await self.ctx.embed_color()
        )
        embed.description = _(
            "Join the game by clicking on the button below. 2 players will be selected randomly."
        )
        end_time = int((datetime.datetime.now() + datetime.timedelta(seconds=60)).timestamp())
        embed.add_field(name="End time for joining", value=f"<t:{end_time}:T> (<t:{end_time}:R>)")
        self.clear_items()
        self.add_item(self.join_button)
        self._mode = "join"
        self._message: discord.Message = await self.ctx.send(embed=embed, view=self)
        self.cog.views[self._message] = self
        await asyncio.sleep(60)
        self._mode = "play"
        initial_players = self.initial_players.copy()
        if len(initial_players) < 2:
            await self.on_timeout()
            self.stop()
            raise commands.UserFeedbackCheckFailure(_("At least two players are needed to play."))
        player_A = random.choice(initial_players)
        initial_players.remove(player_A)
        player_B = random.choice(initial_players)
        initial_players.remove(player_B)
        self.players = {player_A: None, player_B: None}
        embed: discord.Embed = discord.Embed(
            title="SplitOrSteal Game", color=await self.ctx.embed_color()
        )
        embed.description = _(
            "The two players are {player_A.mention} and {player_B.mention}.\n"
            "You have to click the button that you choose (`split` or `steal`).\n"
            "• If you both choose `split` both of them win.\n"
            "• If you both choose `steal`, both of you loose.\n"
            "• if one of you chooses `split` and one of you chooses `steal`, the one who choose `steal` will win."
        ).format(player_A=player_A, player_B=player_B)
        end_time = int((datetime.datetime.now() + datetime.timedelta(seconds=60)).timestamp())
        embed.add_field(name="End time for play", value=f"<t:{end_time}:T> (<t:{end_time}:R>)")
        self.clear_items()
        self.add_item(self.join_button)
        self.join_button.disabled = True
        self.add_item(self.split_button)
        self.add_item(self.steal_button)
        self._message: discord.Message = await self._message.edit(embed=embed, view=self)

        async def check_conditions():
            while self.players[player_A] is None or self.players[player_B] is None:
                await asyncio.sleep(1)
            return True

        try:
            await asyncio.wait_for(check_conditions(), timeout=60)
        except asyncio.TimeoutError:
            await self.on_timeout()
            self.stop()
            raise commands.UserFeedbackCheckFailure(_("At least one player has stopped playing."))
        if self.players[player_A] == "split" and self.players[player_B] == "split":
            await self._message.reply(
                _(
                    "{player_A.display_name} and {player_B.display_name}, you both chose `split` and therefore both win."
                ).format(player_A=player_A, player_B=player_B)
            )
        elif self.players[player_A] == "steal" and self.players[player_B] == "steal":
            await self._message.reply(
                _(
                    "{player_A.display_name} and {player_B.display_name}, you both chose `steal` and therefore both loose."
                ).format(player_A=player_A, player_B=player_B)
            )
        elif self.players[player_A] == "steal" and self.players[player_B] == "split":
            await self._message.reply(
                _(
                    "{player_A.display_name} chose `steal` and {player_B.display_name} chose `split`, and therefore {player_A.display_name} win."
                ).format(player_A=player_A, player_B=player_B)
            )
        elif self.players[player_A] == "split" and self.players[player_B] == "steal":
            await self._message.reply(
                _(
                    "{player_B.display_name} chose `steal` and {player_A.display_name} chose `split`, and therefore {player_B.display_name} win."
                ).format(player_A=player_A, player_B=player_B)
            )
        return self._message

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if self._mode == "play" and interaction.user not in self.players:
            await interaction.response.send_message(
                _("You are not allowed to use this interaction."), ephemeral=True
            )
            return False
        return True

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
    async def join_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        if interaction.user in self.initial_players:
            await interaction.response.send_message(
                _("You have already joined this game."), ephemeral=True
            )
            return
        self.initial_players.append(interaction.user)
        await interaction.response.send_message(_("You have joined this game."), ephemeral=True)

    @discord.ui.button(label="Split", style=discord.ButtonStyle.secondary)
    async def split_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        if self.players[interaction.user] is not None:
            await interaction.response.send_message(
                _("You have already chose `{original_response}`.").format(
                    original_response=self.players[interaction.user]
                ),
                ephemeral=True,
            )
            return
        self.players[interaction.user] = "split"
        await interaction.response.send_message(_("You have chose `split`."), ephemeral=True)

    @discord.ui.button(label="Steal", style=discord.ButtonStyle.secondary)
    async def steal_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        if self.players[interaction.user] is not None:
            await interaction.response.send_message(
                _("You have already chose `{original_response}`.").format(
                    original_response=self.players[interaction.user]
                ),
                ephemeral=True,
            )
            return
        self.players[interaction.user] = "steal"
        await interaction.response.send_message(_("You have chose `steal`."), ephemeral=True)

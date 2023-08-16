from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import asyncio
import datetime
import random
import string
from collections import Counter

from prettytable import PrettyTable
from redbot.core.utils.chat_formatting import box, humanize_list

_ = Translator("AcronymGame", __file__)


class JoinGameModal(discord.ui.Modal):
    def __init__(self, parent: discord.ui.View) -> None:
        super().__init__(title="Join Acronym Game")
        self._parent: discord.ui.View = parent
        self.answer: discord.ui.TextInput = discord.ui.TextInput(
            label=f"Answer for {self._parent.acronym} acronym",
            placeholder=f"Your full name for {self._parent.acronym} acronym",
            default=None,
            style=discord.TextStyle.short,
            custom_id="description",
            required=True,
            min_length=(len(self._parent.acronym) * 2)
            + (len(self._parent.acronym) - 1),  # n words with at least 2 characters + spaces
            max_length=(len(self._parent.acronym) * 13)
            + (len(self._parent.acronym) - 1),  # n words with 13 characters + spaces
        )
        self.add_item(self.answer)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if interaction.user in self._parent.players:
            await interaction.response.send_message(
                _("You have already joined this game, with `{answer}` answer.").format(
                    answer=self._parent.players[interaction.user]
                ),
                ephemeral=True,
            )
            return
        if len(self._parent.players) >= 20:
            await interaction.response.send_message(
                _("Sorry, maximum 20 players."), ephemeral=True
            )
            return
        if self._parent._mode != "join":
            await interaction.response.send_message(
                _("Sorry, the vote has already started."), ephemeral=True
            )
            return
        answer = self.answer.value.strip()
        if len(answer.split(" ")) != len(self._parent.acronym):
            await interaction.response.send_message(
                _("Sorry, the number of words in your answer must be {len_words}.").format(
                    len_words=len(self._parent.acronym)
                ),
                ephemeral=True,
            )
            return
        for i, letter in enumerate(self._parent.acronym):
            if answer.split(" ")[i][0].upper() != letter.upper():
                await interaction.response.send_message(
                    _(
                        "Sorry, the initial of each word in your answer must be each letter of the acronym ({acronym})."
                    ).format(acronym=self._parent.acronym),
                    ephemeral=True,
                )
                return
        self._parent.players[interaction.user] = answer
        embed: discord.Embed = self._parent._message.embeds[0]
        table = PrettyTable()
        table.field_names = ["#", "Answer"]
        for num, (__, answer) in enumerate(self._parent.players.items()):
            table.add_row([num + 1, answer])
        embed.description = _(
            "Join the game by clicking on the button below and entering your acronym. Maximum 20 players.\n"
        ) + box(str(table), lang="py")
        self._parent._message: discord.Message = await self._parent._message.edit(embed=embed)
        await interaction.response.send_message(
            _("Game joined with `{answer}` answer.").format(answer=answer), ephemeral=True
        )


class AnswerSelect(discord.ui.Select):
    def __init__(self, parent: discord.ui.View, players: typing.Dict[discord.Member, int]) -> None:
        self._parent: discord.ui.View = parent
        self._options = [
            discord.SelectOption(
                label=f"{answer[:97]}..." if len(answer) > 100 else answer, value=str(num + 1)
            )
            for num, (_, answer) in enumerate(players.items())
        ]
        super().__init__(
            placeholder="Select the best answer.",
            options=self._options,
            row=1,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        option = discord.utils.get(self._options, value=self.values[0])
        await self._parent._callback(interaction, option)


class AcronymGameView(discord.ui.View):
    def __init__(
        self,
        cog: commands.Cog,
    ) -> None:
        super().__init__(timeout=120 + 60 + 10)
        self.ctx: commands.Context = None
        self.cog: commands.Cog = cog

        self.acronym: str = None
        self.players: typing.Dict[discord.Member, str] = {}
        self.votes: Counter[int, int] = Counter()

        self._message: discord.Message = None
        self._voters: typing.Dict[discord.Member, int] = {}
        self._mode: typing.Literal["join", "vote"] = None

    async def start(self, ctx: commands.Context) -> None:
        self.ctx: commands.Context = ctx
        self.acronym: str = self.get_acronym()
        embed: discord.Embed = discord.Embed(
            title="Acronym Game", color=await self.ctx.embed_color()
        )
        embed.description = _(
            "Join the game by clicking on the button below and entering your acronym. Maximum 20 players."
        )
        embed.add_field(name="Random Acronym", value=self.acronym)
        end_time = int((datetime.datetime.now() + datetime.timedelta(seconds=120)).timestamp())
        embed.add_field(name="End time for joining", value=f"<t:{end_time}:T> (<t:{end_time}:R>)")
        self._mode = "join"
        self._message: discord.Message = await self.ctx.send(embed=embed, view=self)
        self.cog.views[self._message] = self
        await asyncio.sleep(120)
        self._mode = "vote"
        if len(self.players) < 3:
            await self.on_timeout()
            self.stop()
            raise commands.UserFeedbackCheckFailure(
                _("At least three players are needed to play.")
            )
        table = PrettyTable()
        table.field_names = ["#", "Answer"]
        for num, (__, answer) in enumerate(self.players.items()):
            table.add_row([num + 1, answer])
        embed: discord.Embed = discord.Embed(
            title="Acronym Game", color=await self.ctx.embed_color()
        )
        embed.description = _(
            "Use the dropdown below to vote for the best answer for the random acronym. All guild members can vote.\n"
        ) + box(str(table), lang="py")
        embed.add_field(name="Random Acronym", value=self.acronym)
        end_time = int((datetime.datetime.now() + datetime.timedelta(seconds=60)).timestamp())
        embed.add_field(name="End time for voting", value=f"<t:{end_time}:T> (<t:{end_time}:R>)")
        self.join_button.disabled = True
        self.add_item(AnswerSelect(self, players=self.players))
        self._message: discord.Message = await self._message.edit(embed=embed, view=self)
        await asyncio.sleep(60)
        if not self._voters:
            await self.on_timeout()
            self.stop()
            raise commands.UserFeedbackCheckFailure(_("No vote given."))
        table = PrettyTable()
        players = sorted(
            self.players.items(),
            key=lambda x: self.votes[list(self.players).index(x[0]) + 1],
            reverse=True,
        )
        winners = [players[0][0].display_name]
        winners.extend(
            player.display_name
            for player, __ in players[1:]
            if self.votes[list(self.players).index(player) + 1] == players[0][1]
        )
        table.field_names = ["#", "Name", "Answer", "Votes"]
        for num, (player, answer) in enumerate(players):
            table.add_row(
                [
                    num + 1,
                    (
                        f"{player.display_name[:15]}..."
                        if len(player.display_name) > 15
                        else player.display_name
                    ),
                    answer,
                    self.votes[list(self.players).index(player) + 1],
                ]
            )
        embed: discord.Embed = discord.Embed(
            title="Acronym Game", color=await self.ctx.embed_color()
        )
        embed.description = _("Here is the leaderboard for this game:") + box(
            str(table), lang="py"
        )
        embed.add_field(name="Random Acronym", value=self.acronym)
        self._message: discord.Message = await self._message.edit(embed=embed, view=self)
        await self._message.reply(
            _("Winner{s}: {winners}!").format(
                winners=humanize_list(winners), s="s" if len(winners) > 1 else ""
            )
        )
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

    def get_acronym(self) -> str:
        return "".join(
            [
                random.choice(string.ascii_uppercase) for __ in range(4)
            ]  # range(random.choice(range(4, 5)))
        )

    @discord.ui.button(label="Join Game", emoji="🎮", style=discord.ButtonStyle.success)
    async def join_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        modal = JoinGameModal(self)
        await interaction.response.send_modal(modal)

    async def _callback(
        self, interaction: discord.Interaction, option: discord.SelectOption
    ) -> None:
        if interaction.user in self._voters:
            await interaction.response.send_message(
                _("You have already voted in this game."), ephemeral=True
            )
            return
        value = int(option.value)
        if interaction.user == list(self.players)[value - 1]:
            await interaction.response.send_message(
                _("You can't vote for yourself."), ephemeral=True
            )
            return
        self._voters[interaction.user] = value
        self.votes[value] += 1
        await interaction.response.send_message(
            _("Vote given for answer {num}.").format(num=value), ephemeral=True
        )

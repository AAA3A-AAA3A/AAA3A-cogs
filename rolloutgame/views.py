from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

from redbot.core.utils.chat_formatting import humanize_list

import datetime
from random import choice

_: Translator = Translator("RolloutGame", __file__)


class JoinGameView(discord.ui.View):
    def __init__(self, cog: commands.Cog):
        super().__init__(timeout=None)
        self.ctx: commands.Context = None
        self.cog: commands.Cog = cog

        self._message: discord.Message = None
        self.hoster: discord.Member = None
        self.players: typing.List[discord.Member] = []

    async def start(self, ctx: commands.Context) -> None:
        self.ctx: commands.Context = ctx
        self.hoster = ctx.author
        self.players.append(ctx.author)
        embed: discord.Embed = discord.Embed(
            title=_("Rollout Game"),
            color=await self.ctx.embed_color(),
            timestamp=ctx.message.created_at,
        )
        embed.add_field(
            name=_("Instructions:"),
            value=_(
                "**•** Click the **Join Game** button to join the game. Limited to 25 players.\n"
                "**•** Wait for the host to start the game.\n"
                "**•** At each round, select a number between 1 and 25 within 30 seconds.\n"
                "**•** If the bot rolls the number you selected, you lose.\n"
                "**•** The last player standing wins the game!"
            )
        )
        embed.set_author(name=_("Hosted by {hoster.display_name}").format(hoster=self.hoster), icon_url=self.hoster.display_avatar)
        embed.set_footer(text=ctx.guild.name, icon_url=ctx.guild.icon)
        self._message: discord.Message = await ctx.send(embed=embed, view=self)
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
    async def join_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        if interaction.user in self.players:
            await interaction.response.send_message(
                "You have already joined the game!", ephemeral=True
            )
            return
        if len(self.players) >= 25:
            await interaction.response.send_message(
                "The game is full, you can't join!", ephemeral=True
            )
            return
        self.players.append(interaction.user)
        self.view_players.label = f"View Players ({len(self.players)})"
        try:
            await self._message.edit(view=self)
        except discord.HTTPException:
            pass
        await interaction.response.send_message("You have joined the game!", ephemeral=True)

    @discord.ui.button(label="Leave", style=discord.ButtonStyle.danger)
    async def leave_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        if interaction.user not in self.players:
            await interaction.response.send_message(
                "You have not joined the game!", ephemeral=True
            )
            return
        self.players.remove(interaction.user)
        self.view_players.label = f"View Players ({len(self.players)})"
        try:
            await self._message.edit(view=self)
        except discord.HTTPException:
            pass
        await interaction.response.send_message("You have left the game!", ephemeral=True)

    @discord.ui.button(label="View Players (1)", style=discord.ButtonStyle.secondary)
    async def view_players(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        if not self.players:
            await interaction.response.send_message("No one has joined the game yet!", ephemeral=True)
            return
        embed = discord.Embed(
            title="Rollout Game - Game Players",
            color=await self.ctx.embed_color(),
        )
        embed.set_author(name=_("Hosted by {hoster.display_name}").format(hoster=self.hoster), icon_url=self.hoster.display_avatar)
        embed.set_footer(text=interaction.guild.name, icon_url=interaction.guild.icon)
        embed.description = "\n".join(f"**•** **{player.display_name}** ({player.id})" for player in self.players)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Start Game!", style=discord.ButtonStyle.primary)
    async def start_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        if interaction.user != self.hoster:
            await interaction.response.send_message(
                "Only the host can start the game!", ephemeral=True
            )
            return
        if len(self.players) < 2:
            await interaction.response.send_message(
                "You need at least 2 players to start the game!", ephemeral=True
            )
            return
        await self.on_timeout()
        await interaction.response.defer()
        self.stop()


class RolloutGameView(discord.ui.View):
    def __init__(self, cog: commands.Cog):
        super().__init__(timeout=30)
        self.ctx: commands.Context = None
        self.cog: commands.Cog = cog

        self._message: discord.Message = None
        self.hoster: discord.Member = None
        self.players: typing.List[discord.Member] = []
        self.round: int = 1
        self.disabled_numbers: typing.List[int] = []
        self._choices: typing.Dict[discord.Member, int] = {}
        self._number: int = None

    async def start(
        self,
        ctx: commands.Context,
        players: typing.List[discord.Member],
        round: int = 1,
        disabled_numbers: typing.List[int] = [],
    ) -> None:
        self.ctx: commands.Context = ctx
        self.hoster: discord.Member = ctx.author
        self.players: typing.List[discord.Member] = players
        self.round: int = round
        self.disabled_numbers: typing.List[int] = disabled_numbers
        embed: discord.Embed = discord.Embed(
            title=_("Rollout Game - Round {round}").format(round=round),
            description=_(
                "Select a number between 1 and 25. Choose is limited to 30 seconds."
            ),
            color=await self.ctx.embed_color(),
            timestamp=ctx.message.created_at,
        )
        embed.set_footer(text=ctx.guild.name, icon_url=ctx.guild.icon)
        for i in range(1, 25+1):
            button: discord.ui.Button = discord.ui.Button(
                label=str(i),
                custom_id=str(i),
                disabled=i in self.disabled_numbers,
                style=discord.ButtonStyle.primary if i not in self.disabled_numbers else discord.ButtonStyle.secondary,
            )
            button.callback = self.callback
            self.add_item(button)
        self._number = choice([i for i in range(1, 25+1) if i not in self.disabled_numbers])
        embed.add_field(
            name="Time Left:",
            value=f"<t:{int((datetime.datetime.now(tz=datetime.timezone.utc) + datetime.timedelta(seconds=30)).timestamp())}:R>",
        )
        self._message: discord.Message = await ctx.send(
            content=humanize_list([player.mention for player in self.players]),
            embed=embed,
            view=self,
        )
        self.cog.views[self._message] = self
        return self._message

    async def on_timeout(self) -> None:
        embed = self._message.embeds[0]
        embed.clear_fields()
        for child in self.children:
            child: discord.ui.Item
            if hasattr(child, "disabled") and not (
                isinstance(child, discord.ui.Button) and child.style == discord.ButtonStyle.url
            ):
                child.disabled = True
        try:
            await self._message.edit(embed=embed, view=self)
        except discord.HTTPException:
            pass

    async def callback(self, interaction: discord.Interaction) -> None:
        if interaction.user not in self.players:
            await interaction.response.send_message(
                "You are not in the game!", ephemeral=True
            )
            return
        number = int(interaction.data["custom_id"])
        self._choices[interaction.user] = number
        try:
            await self._message.edit(content=humanize_list([player.mention for player in self.players if player not in self._choices]))
        except discord.HTTPException:
            pass
        await interaction.response.send_message(f"You have selected the number {number}!", ephemeral=True)

    async def choose_number(self) -> int:
        number = self._number
        self.disabled_numbers.append(number)
        discord.utils.get(self.children, label=str(number)).style = discord.ButtonStyle.danger
        try:
            await self._message.edit(view=self)
        except discord.HTTPException:
            pass

        embed: discord.Embed = discord.Embed(
            title=_("Round {round} - Results").format(round=self.round),
            color=await self.ctx.embed_color(),
            timestamp=self.ctx.message.created_at,
        )

        eliminated_players_timeout = [
            player
            for player in self.players
            if player not in self._choices
        ]
        eleminated_players_wrong_number = [
            player
            for player in self.players
            if player in self._choices and self._choices[player] == number
        ]
        eleminated_players = eliminated_players_timeout + eleminated_players_wrong_number
        self.players = [player for player in self.players if player not in eleminated_players]
        if not self.players:
            if not eleminated_players_wrong_number:
                embed.description = _("No one has answered in time. The game ends...")
                await self.ctx.send(
                    embed=embed,
                    reference=self._message.to_reference(fail_if_not_exists=False),
                )
                raise TimeoutError()
            embed.description = _("The bot has rolled the number {number}! However, since all remaining  players have been eliminated, the round will be restarted.").format(number=number)
            await self.ctx.send(
                embed=embed,
                reference=self._message.to_reference(fail_if_not_exists=False),
            )
            raise RuntimeError("No players left in the game.")

        embed.description = _("The bot has rolled the number {number}!").format(number=number)
        if not eleminated_players:
            embed.description += _("\n\n**No one has been eliminated this round.**")
        else:
            embed.description += _("\n\n**{number} players have been eliminated this round:**").format(number=len(eleminated_players))
            for eleminated in eleminated_players_wrong_number:
                embed.description += _(
                    _("\n**•** **{eleminated.display_name}** - Selected the number {number}.").format(eleminated=eleminated, number=number)
                ).format(eleminated=eleminated)
            for eleminated in eliminated_players_timeout:
                embed.description += _(
                    _("\n**•** **{eleminated.display_name}** - Did not select a number in time.").format(eleminated=eleminated)
                ).format(eleminated=eleminated)
        await self.ctx.send(
            content=humanize_list([eliminated.mention for eliminated in eleminated_players]),
            embed=embed,
            reference=self._message.to_reference(fail_if_not_exists=False),
        )
        return number, self.players, eleminated_players

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

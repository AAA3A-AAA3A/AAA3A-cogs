from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import datetime
from random import choice

from redbot.core.utils.chat_formatting import humanize_list

_: Translator = Translator("RolloutGame", __file__)


class JoinGameView(discord.ui.View):
    def __init__(self, cog: commands.Cog) -> None:
        super().__init__(timeout=None)
        self.ctx: commands.Context = None
        self.cog: commands.Cog = cog

        self._message: discord.Message = None
        self.host: discord.Member = None
        self.players: typing.List[discord.Member] = []

        self.cancelled: bool = True

        self.join.label = _("Join Game")
        self.leave.label = _("Leave")
        self.view_players.label = _("View Players (1)")
        self.start_button.label = _("Start Game!")

    async def start(self, ctx: commands.Context) -> None:
        self.ctx: commands.Context = ctx
        self.host: discord.Member = ctx.author
        self.players.append(ctx.author)
        embed: discord.Embed = discord.Embed(
            title=_("Rollout Game"),
            description=_(
                "Click the button below to join the party! Please note that the maximum amount of players is 50."
            ),
            color=await self.ctx.embed_color(),
            timestamp=ctx.message.created_at,
        )
        embed.add_field(
            name=_("Instructions:"),
            value=_(
                "**•** At each round, select a number between 1 and 25 within 30 seconds.\n"
                "**•** If the bot rolls the number you selected, you lose.\n"
                "**•** The last player standing wins the game!"
            ),
        )
        embed.set_author(
            name=_("Hosted by {host.display_name}").format(host=self.host),
            icon_url=self.host.display_avatar,
        )
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
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if interaction.user in self.players:
            await interaction.response.send_message(
                _("You have already joined the game!"), ephemeral=True
            )
            return
        if len(self.players) >= 50:
            await interaction.response.send_message(
                _("The game is full, you can't join!"), ephemeral=True
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
            title=_("Rollout Game — Players"),
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
        if len(self.players) < 2:
            await interaction.response.send_message(
                _("You need at least 2 players to start the game!"), ephemeral=True
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


class RolloutGameView(discord.ui.View):
    def __init__(self, cog: commands.Cog):
        super().__init__(timeout=30)
        self.ctx: commands.Context = None
        self.cog: commands.Cog = cog

        self._message: discord.Message = None
        self.host: discord.Member = None
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
        self.host: discord.Member = ctx.author
        self.players: typing.List[discord.Member] = players
        self.round: int = round
        self.disabled_numbers: typing.List[int] = disabled_numbers
        embed: discord.Embed = discord.Embed(
            title=_("Rollout Game — Round {round}").format(round=round),
            description=_("Select a number between 1 and 25. Choose is limited to 30 seconds."),
            color=await self.ctx.embed_color(),
            timestamp=ctx.message.created_at,
        )
        embed.set_footer(text=ctx.guild.name, icon_url=ctx.guild.icon)
        for i in range(1, 25 + 1):
            button: discord.ui.Button = discord.ui.Button(
                label=str(i),
                custom_id=str(i),
                disabled=i in self.disabled_numbers,
                style=discord.ButtonStyle.secondary,
            )
            button.callback = self.callback
            self.add_item(button)
        self._number = choice([i for i in range(1, 25 + 1) if i not in self.disabled_numbers])
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
            await interaction.response.send_message(_("You are not in this game!"), ephemeral=True)
            return
        if interaction.user in self._choices:
            await interaction.response.send_message(
                _("You have already selected a number!"), ephemeral=True
            )
            return
        await interaction.response.defer(ephemeral=True)
        number = int(interaction.data["custom_id"])
        self._choices[interaction.user] = number
        for button in self.children:
            players = [
                player
                for player in self._choices
                if self._choices[player] == int(button.custom_id)
            ]
            if players:
                button.style = discord.ButtonStyle.primary
                button.label = (
                    f"{button.custom_id} ({len(players)})"
                    if len(players) > 1
                    else button.custom_id
                )
            else:
                button.style = discord.ButtonStyle.secondary
                button.label = button.custom_id
        try:
            await self._message.edit(
                content=humanize_list(
                    [player.mention for player in self.players if player not in self._choices]
                ),
                view=self,
            )
        except discord.HTTPException:
            pass
        await interaction.followup.send(
            _("You have selected the number {number}!").format(number=number), ephemeral=True
        )

    async def choose_number(self) -> int:
        number = self._number
        discord.utils.get(self.children, custom_id=str(number)).style = discord.ButtonStyle.danger
        try:
            await self._message.edit(view=self)
        except discord.HTTPException:
            pass

        embed: discord.Embed = discord.Embed(
            title=_("Round {round} — Results").format(round=self.round),
            color=await self.ctx.embed_color(),
            timestamp=self.ctx.message.created_at,
        )

        eliminated_players_timeout = [
            player for player in self.players if player not in self._choices
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
            embed.description = _(
                "The bot has rolled the number {number}! However, since all remaining players have been eliminated, the round will be restarted."
            ).format(number=number)
            await self.ctx.send(
                embed=embed,
                reference=self._message.to_reference(fail_if_not_exists=False),
            )
            raise RuntimeError(_("No player left in the game."))
        self.disabled_numbers.append(number)

        embed.description = _("The bot has rolled the number {number}!").format(number=number)
        if not eleminated_players:
            embed.description += _("\n\n**No one has been eliminated this round.**")
        else:
            embed.description += (
                _("\n\n**{number} players have been eliminated this round:**").format(
                    number=len(eleminated_players)
                )
                if len(eleminated_players) > 1
                else _("\n\n**1 player has been eliminated this round:**")
            )
            for eleminated in eleminated_players_wrong_number:
                embed.description += _(
                    _(
                        "\n**•** **{eleminated.display_name}** - Selected the number {number}."
                    ).format(eleminated=eleminated, number=number)
                ).format(eleminated=eleminated)
            for eleminated in eliminated_players_timeout:
                embed.description += _(
                    _(
                        "\n**•** **{eleminated.display_name}** - Did not select a number in time."
                    ).format(eleminated=eleminated)
                ).format(eleminated=eleminated)
        await self.ctx.send(
            content=("💀 " if eleminated_players else "")
            + humanize_list([eliminated.mention for eliminated in eleminated_players]),
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

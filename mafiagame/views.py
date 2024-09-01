from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator  # isort:skip
import discord  # isort:skip
import typing  # isort:skip


_: Translator = Translator("MafiaGame", __file__)


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
        self.start.label = _("Start Game!")

    async def start(self, ctx: commands.Context) -> None:
        self.ctx: commands.Context = ctx
        self.host: discord.Member = ctx.author
        self.players.append(ctx.author)
        embed: discord.Embed = discord.Embed(
            title=_("Mafia Game"),
            description=_("Click the button below to join the party! Please note that the maximum amount of players is 25."),
            color=await self.ctx.embed_color(),
            timestamp=ctx.message.created_at,
        )
        embed.set_author(name=_("Hosted by {host.display_name}").format(host=self.host), icon_url=self.host.display_avatar)
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
    async def join(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
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
        self.players.append(interaction.user)
        self.view_players.label = _("View Players ({len_players})").format(len_players=len(self.players))
        try:
            await self._message.edit(view=self)
        except discord.HTTPException:
            pass
        await interaction.response.send_message(_("You have joined the game!"), ephemeral=True)

    @discord.ui.button(label="Leave", style=discord.ButtonStyle.danger)
    async def leave(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        if interaction.user not in self.players:
            await interaction.response.send_message(
                _("You have not joined the game!"), ephemeral=True
            )
            return
        self.players.remove(interaction.user)
        self.view_players.label = _("View Players ({len_players})").format(len_players=len(self.players))
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
            await interaction.response.send_message(_("No one has joined the game yet!"), ephemeral=True)
            return
        embed = discord.Embed(
            title=_("Mafia Game - Players"),
            color=await self.ctx.embed_color(),
        )
        embed.set_author(name=_("Hosted by {host.display_name}").format(host=self.host), icon_url=self.host.display_avatar)
        embed.set_footer(text=interaction.guild.name, icon_url=interaction.guild.icon)
        embed.description = "\n".join(f"**•** **{player.member.display_name}** ({player.id})" for player in self.players)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Start Game!", style=discord.ButtonStyle.primary)
    async def start(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        if interaction.user != self.host:
            await interaction.response.send_message(
                _("Only the host can start the game!"), ephemeral=True
            )
            return
        if len(self.players) < 2:
            await interaction.response.send_message(
                _("You need at least 2 players to start the game!"), ephemeral=True
            )
            return
        self.cancelled: bool = False
        await self.on_timeout()
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(emoji="✖️", style=discord.ButtonStyle.danger)
    async def cancel(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        if interaction.user != self.host:
            await interaction.response.send_message(
                _("Only the host can cancel the game!"), ephemeral=True
            )
            return
        try:
            await self._message.delete()
        except discord.HTTPException:
            pass


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
    async def spectate(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        if interaction.user in self.spectaters:
            await interaction.response.send_message(_("You are already spectating the game!"), ephemeral=True)
            return
        if self.game.get_player(interaction.user) is not None:
            await interaction.response.send_message(_("You are a player in this game!"), ephemeral=True)
            return
        await self.game.channel.set_permissions(interaction.user, view_channel=True, read_messages=True, send_messages=False)
        await interaction.response.send_message(
            _("You are now spectating the game! 👀 Jump to {channel.mention}!").format(channel=self.game.channel),
            ephemeral=True,
        )


class PerformActionView(discord.ui.View):
    def __init__(self, game) -> None:
        super().__init__(timeout=None)
        self.game = game
        self._message: discord.Message = None

        self.action.label = _("Perform Action")

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

    @discord.ui.button(emoji="🔪", label="Perform Action", style=discord.ButtonStyle.success)
    async def action(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        if (player := self.game.get_player(interaction.user)) is None:
            await interaction.response.send_message(_("You are not a player in this game!"), ephemeral=True)
            return
        if player.dead:
            await interaction.response.send_message(_("You are dead, you can't perform any actions!"), ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            await player.role.perform_action(player, interaction)
        except NotImplementedError:
            await interaction.response.send_message(_("You can't perform any actions!"), ephemeral=True)
        except RuntimeError as error:
            await interaction.response.send_message(str(error), ephemeral=True)


class VoteView(discord.ui.View):
    def __init__(self, game, remaining_players: typing.List) -> None:
        super().__init__(timeout=None)
        self.game = game
        self.remaining_players: typing.List = remaining_players
        for player in self.remaining_players:
            self.select.add_option(
                label=player.member.display_name,
                value=str(player.member.id),
            )
        self.votes: typing.Dict = {}
        self._message: discord.Message = None

        self.select.placeholder = _("Select a player to vote against.")

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
            await interaction.response.send_message(_("You are not a player in this game!"), ephemeral=True)
            return False
        if player.dead:
            await interaction.response.send_message(_("You are dead, you can't vote!"), ephemeral=True)
            return False
        return True

    @discord.ui.select(placeholder="Select a player to vote against.", min_values=0, max_values=1)
    async def select(self, interaction: discord.Interaction, select: discord.ui.Select) -> None:
        if select.values:
            player = next((player for player in self.remaining_players if int(select.values[0]) == player.member.id))
            self.votes[self.game.get_player(interaction.user)] = player
            await interaction.response.send_message(
                _("You have voted against **{player.member.display_name}**!").format(player=player), ephemeral=True
            )
        else:
            self.votes.pop(self.game.get_player(interaction.user), None)
            await interaction.response.send_message(_("You have unvoted!"), ephemeral=True)


class JudgementView(discord.ui.View):
    def __init__(self, game, player) -> None:
        super().__init__(timeout=None)
        self.game = game
        self.player = player
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
        if (player := self.game.get_player(interaction.user)) is None:
            await interaction.response.send_message(_("You are not a player in this game!"), ephemeral=True)
            return False
        if player.dead:
            await interaction.response.send_message(_("You are dead, you can't vote!"), ephemeral=True)
            return False
        if player == self.player:
            await interaction.response.send_message(_("You can't vote on your own judgement!"), ephemeral=True)
            return False
        return True

    @discord.ui.button(emoji="👿", label="GUILTY", style=discord.ButtonStyle.danger)
    async def guilty(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.results[interaction.user] = True
        await interaction.response.send_message(_("You have voted **GUILTY**!"), ephemeral=True)

    @discord.ui.button(emoji="😇", label="INNOCENT", style=discord.ButtonStyle.success)
    async def innocent(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.results[interaction.user] = False
        await interaction.response.send_message(_("You have voted **INNOCENT**!"), ephemeral=True)

    @discord.ui.button(label="Abstain", style=discord.ButtonStyle.secondary)
    async def abstain(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.results[interaction.user] = None
        await interaction.response.send_message(_("You have abstained!"), ephemeral=True)
    
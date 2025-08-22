from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

_: Translator = Translator("BlackTeaGame", __file__)


class Lang(discord.Enum):
    ENGLISH: str = "en"
    FRANCAIS: str = "fr"
    DEUTSCH: str = "de"
    ESPANOL: str = "es"
    ITALIANO: str = "it"
    PORTUGUES: str = "pt"
    NEDERLANDS: str = "nl"
    CESTINA: str = "cs"
    ELLENIKA: str = "el"
    INDONESIAN: str = "id"
    GAEILGE: str = "ie"
    FILIPINO: str = "ph"
    POLSKI: str = "pl"
    UKRAIHCBKA: str = "ua"
    RUSSIAN: str = "ru"
    SVENSKA: str = "sv"
    TURKCE: str = "tr"


class JoinGameView(discord.ui.View):
    def __init__(self, cog: commands.Cog, lang: Lang = Lang.ENGLISH) -> None:
        super().__init__(timeout=None)
        self.ctx: commands.Context = None
        self.cog: commands.Cog = cog
        self.lang: Lang = lang

        self.host: discord.Member = None
        self.players: typing.List[discord.Member] = []
        self._message: discord.Message = None

        self.cancelled: bool = True

        self.join.label = _("Join Game")
        self.leave.label = _("Leave")
        self.view_players.label = _("View Players (1)")
        self.start_button.label = _("Start Game!")

    async def start(self, ctx: commands.Context) -> discord.Message:
        self.ctx: commands.Context = ctx
        self.host: discord.Member = ctx.author
        self.players.append(ctx.author)
        embed: discord.Embed = discord.Embed(
            title=_("{flag} Black Tea Game ☕").format(
                flag=f":flag_{'gb' if self.lang is Lang.ENGLISH else self.lang.value}:",
            ),
            description=_(
                "Click the button below to **join the party**! Please note that the maximum amount of players is **50**."
            ),
            color=await self.ctx.embed_color(),
            timestamp=ctx.message.created_at,
        )
        embed.add_field(
            name=_("Rules:"),
            value=_(
                "- Each time the bot asks you, you have a few seconds to respond with a word containing the 3 provided letters. Already used words are not allowed.\n"
                "- If you fail to respond in time, you lose 1 HP. If you lose all your HP, you are out of the game.\n"
                "- The last player remaining wins the game!\n"
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

    @discord.ui.button(emoji="🎮", label="Join Game", style=discord.ButtonStyle.success)
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
            title=_("Black Tea Game — Players"),
            color=await self.ctx.embed_color(),
        )
        embed.set_author(
            name=_("Hosted by {host.display_name}").format(host=self.host),
            icon_url=self.host.display_avatar,
        )
        embed.set_footer(text=interaction.guild.name, icon_url=interaction.guild.icon)
        embed.description = "\n".join(
            f"- {player.mention} ({player.id})" for player in self.players
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
        if not (
            interaction.user == self.host
            or await self.ctx.bot.is_admin(interaction.user)
            or interaction.user.guild_permissions.manage_guild
            or interaction.user.id in interaction.client.owner_ids
        ):
            await interaction.response.send_message(
                _("You can't cancel the game!"), ephemeral=True
            )
            return
        try:
            await self._message.delete()
        except discord.HTTPException:
            pass
        self.stop()

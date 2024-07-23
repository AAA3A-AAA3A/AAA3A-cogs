from AAA3A_utils import CogsUtils  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import asyncio

from .board import Board
from .constants import (
    IMAGE_EXTENSION,
    MAIN_COLORS,
    base_colors_options,
    base_height_or_width_select_options,
)  # NOQA
from .view import DrawView

_: Translator = Translator("Draw", __file__)


class StartDrawView(discord.ui.View):
    def __init__(
        self,
        cog: commands.Cog,
        board: typing.Union[typing.Tuple[int, int, str], Board] = (0, 0, MAIN_COLORS[-1]),
        tool_options: typing.Optional[typing.List[discord.SelectOption]] = None,
        color_options: typing.Optional[typing.List[discord.SelectOption]] = None,
    ) -> None:
        super().__init__(timeout=60)
        self.cog: commands.Cog = cog
        self.ctx: commands.Context = None

        if isinstance(board, typing.Tuple):
            board = Board(cog=self.cog, height=board[0], width=board[1], background=board[2])
        self._board: Board = board
        self.height: int = self._board.height
        self.width: int = self._board.width
        self.background: str = self._board.background
        self.draw_view: typing.Optional[DrawView] = None

        self.tool_options: typing.Optional[typing.List[discord.SelectOption]] = tool_options
        self.color_options: typing.Optional[typing.List[discord.SelectOption]] = color_options

        self._message: discord.Message = None
        self._embed: discord.Embed = None

        self._ready: asyncio.Event = asyncio.Event()

    async def start(self, ctx: commands.Context) -> None:
        self.ctx: commands.Context = ctx
        await self._update()
        await self._ready.wait()
        if self.draw_view is not None:
            await self.draw_view._ready.wait()
        return self._message

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id not in [self.ctx.author.id] + list(self.ctx.bot.owner_ids):
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
        self._ready.set()

    @property
    def board(self) -> Board:
        self._board.modify(height=self.height, width=self.width, background=self.background)
        return self._board

    async def _update(self) -> None:
        self._embed: discord.Embed = await self.get_embed(self.ctx)
        file = await self.board.to_file()
        self.select_background.options = base_colors_options()
        discord.utils.get(self.select_background.options, value=self.background).default = True
        self.select_height.options = base_height_or_width_select_options("height")
        discord.utils.get(self.select_height.options, value=int(self.height)).default = True
        self.select_width.options = base_height_or_width_select_options("width")
        discord.utils.get(self.select_width.options, value=int(self.width)).default = True
        if self._message is None:
            self._message: discord.Message = await self.ctx.send(
                _(
                    "Create a new Draw Board with `height = {height}`, `width = {width}` and `background = {background}`."
                ).format(height=self.height, width=self.width, background=self.background),
                embed=self._embed,
                file=file,
                view=self,
            )
        else:
            self._message: discord.Message = await self._message.edit(
                content=_(
                    "Create a new Draw Board with `height = {height}`, `width = {width}` and `background = {background}`."
                ).format(height=self.height, width=self.width, background=self.background),
                embed=self._embed,
                attachments=[file],
                view=self,
            )

    async def get_embed(self, ctx: commands.Context) -> discord.Embed:
        embed: discord.Embed = discord.Embed(title="Draw Board", color=await ctx.embed_color())
        # embed.description = str(self.board)
        embed.set_image(url=f"attachment://image.{IMAGE_EXTENSION.lower()}")
        return embed

    @discord.ui.button(style=discord.ButtonStyle.danger, emoji="✖️", custom_id="close_page")
    async def close_page(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        try:
            await interaction.response.defer()
        except discord.errors.NotFound:
            pass
        self.stop()
        await CogsUtils.delete_message(self._message)
        self._ready.set()

    @discord.ui.button(label="Create Draw", style=discord.ButtonStyle.success)
    async def create_draw(self, interaction: discord.Interaction, button: discord.Button) -> None:
        await interaction.response.defer()
        self.stop()
        self.draw_view: DrawView = DrawView(
            cog=self.cog,
            board=self.board,
            tool_options=self.tool_options,
            color_options=self.color_options,
        )
        await self.draw_view.start(self.ctx, message=self._message)
        self._ready.set()

    @discord.ui.select(options=base_colors_options(), placeholder="Select Board Background.")
    async def select_background(
        self, interaction: discord.Interaction, select: discord.ui.Select
    ) -> None:
        await interaction.response.defer()
        if self.background == select.values[0]:
            return
        self.background: str = select.values[0]
        await self._update()

    @discord.ui.select(
        options=base_height_or_width_select_options("height"), placeholder="Select Board Height."
    )
    async def select_height(
        self, interaction: discord.Interaction, select: discord.ui.Select
    ) -> None:
        await interaction.response.defer()
        if self.height == int(select.values[0]):
            return
        self.height: str = int(select.values[0])
        await self._update()

    @discord.ui.select(
        options=base_height_or_width_select_options("width"), placeholder="Select Board Width."
    )
    async def select_width(
        self, interaction: discord.Interaction, select: discord.ui.Select
    ) -> None:
        await interaction.response.defer()
        if self.width == int(select.values[0]):
            return
        self.width: str = int(select.values[0])
        await self._update()

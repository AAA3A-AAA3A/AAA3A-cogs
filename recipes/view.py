from AAA3A_utils import Menu, CogsUtils  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator  # isort:skip
import discord  # isort:skip

import asyncio

from .types import Recipe

_: Translator = Translator("Recipes", __file__)


class InstructionsSectionsSelect(discord.ui.Select):
    def __init__(self, parent: discord.ui.View, recipe: Recipe) -> None:
        self._parent: discord.ui.View = parent
        self._options = [
            discord.SelectOption(label=instructions_section, value=instructions_section)
            for instructions_section in recipe.instructions
        ]
        super().__init__(
            placeholder="Select an instructions section.",
            options=self._options,
            row=1,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        option = discord.utils.get(self._options, value=self.values[0])
        await self._parent._callback(interaction, option)


class RecipesView(discord.ui.View):
    def __init__(self, cog: commands.Cog, recipe: Recipe) -> None:
        super().__init__(timeout=180)
        self.cog: commands.Cog = cog
        self.ctx: commands.Context = None

        self.recipe: Recipe = recipe

        self._message: discord.Message = None
        self._ready: asyncio.Event = asyncio.Event()

    async def start(self, ctx: commands.Context) -> discord.Message:
        self.ctx: commands.Context = ctx
        embeds = self.recipe.to_embeds(embed_color=await ctx.embed_color())
        self.add_item(
            discord.ui.Button(
                label=_("View recipe on Food52"),
                url=self.recipe.url,
                style=discord.ButtonStyle.url,
            )
        )
        if self.recipe.instructions:
            self.add_item(InstructionsSectionsSelect(parent=self, recipe=self.recipe))
        self._message: discord.Message = await self.ctx.send(embeds=embeds, view=self)
        self.cog.views[self._message] = self
        await self._ready.wait()
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

    async def _callback(self, interaction: discord.Interaction, option: discord.SelectOption):
        await interaction.response.defer()
        embed: discord.Embed = discord.Embed(
            title="Instructions" + (f" {option.value}" if option.value != "Instructions" else ""),
            color=await self.ctx.embed_color(),
        )
        embed.description = "\n\n".join(
            [
                f"**{n}.** {instruction}"
                for n, instruction in enumerate(self.recipe.instructions[option.value], start=1)
            ]
        )
        await Menu(pages=[embed]).start(self.ctx)

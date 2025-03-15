import dis
from AAA3A_utils import Menu  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import json

from mimesis.datasets.int import GENDER_SYMBOLS
from mimesis.enums import Gender
from mimesis.locales import Locale

from .types import LOCALES, FakeIdentity, get_pages

_: Translator = Translator("FakeIdentities", __file__)


class FakeIdentityView(discord.ui.View):
    def __init__(
        self,
        cog: commands.Cog,
        gender: typing.Optional[Gender] = None,
        nationality: typing.Optional[Locale] = None,
        location: typing.Optional[Locale] = None,
        seed: typing.Optional[int] = None,
    ) -> None:
        super().__init__(timeout=180)
        self.cog: commands.Cog = cog
        self.ctx: commands.Context = None
        self.current_fake_identity: FakeIdentity = None
        self.page: str = "main"

        self.gender: typing.Optional[Gender] = gender
        self.nationality: typing.Optional[Locale] = nationality
        self.location: typing.Optional[Locale] = location
        self.seed: typing.Optional[int] = seed

        self.gender_select.placeholder = _("Select a gender.")
        self.nationality_select.placeholder = _("Select a nationality.")
        self.location_select.placeholder = _("Select a location.")
        self.select_page.placeholder = _("Select the page.")

    def generate_fake_identity(self) -> FakeIdentity:
        self.current_fake_identity: FakeIdentity = self.cog.generate_fake_identity(
            gender=self.gender,
            nationality=self.nationality,
            location=self.location,
            seed=self.seed,
        )
        return self.current_fake_identity

    async def start(self, ctx: commands.Context) -> discord.Message:
        self.ctx: commands.Context = ctx
        self.generate_fake_identity()
        await self._update(edit_message=False)
        self._message: discord.Message = await ctx.send(
            embed=self.current_fake_identity.to_embed(),
            view=self,
        )
        self.cog.views[self._message] = self
        return self._message

    async def _update(self, edit_message: bool = True) -> None:
        self.gender_select.options.clear()
        for i, gender in enumerate(Gender):
            self.gender_select.add_option(
                emoji=GENDER_SYMBOLS[i],
                label=gender.name.capitalize(),
                value=gender.value,
                default=gender == self.gender,
            )
        self.nationality_select.options.clear()
        self.location_select.options.clear()
        for locale, country in LOCALES.items():
            self.nationality_select.add_option(
                emoji=country.flag,
                label=country.name,
                description=locale.value,
                value=locale.value,
                default=locale == self.nationality,
            )
            self.location_select.add_option(
                emoji=country.flag,
                label=country.name,
                description=locale.value,
                value=locale.value,
                default=locale == self.location,
            )
        self.select_page.options.clear()
        for page, data in get_pages().items():
            self.select_page.add_option(
                emoji=data["emoji"],
                label=data["title"],
                value=page,
                default=page == self.page,
            )
        if edit_message:
            try:
                await self._message.edit(
                    embed=self.current_fake_identity.to_embed(page=self.page),
                    view=self,
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

    @discord.ui.button(emoji="🔄", style=discord.ButtonStyle.secondary)
    async def refresh(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer()
        self.generate_fake_identity()
        self.page: str = "main"
        await self._update()

    @discord.ui.button(emoji="✖️", style=discord.ButtonStyle.danger)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer()
        try:
            await self._message.delete()
        except discord.HTTPException:
            pass

    @discord.ui.button(emoji="📥", style=discord.ButtonStyle.secondary)
    async def download(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer()
        await Menu(
            json.dumps(
                self.current_fake_identity.to_dict(),
                indent=4,
            ),
            lang="json",
        ).start(self.ctx)

    @discord.ui.select(min_values=0, max_values=1, placeholder="Select a gender.")
    async def gender_select(
        self, interaction: discord.Interaction, select: discord.ui.Select
    ) -> None:
        await interaction.response.defer()
        if select.values:
            self.gender: Gender = Gender(select.values[0])
        else:
            self.gender = None
        self.generate_fake_identity()
        self.page: str = "main"
        await self._update()

    @discord.ui.select(min_values=0, max_values=1, placeholder="Select a nationality.")
    async def nationality_select(
        self, interaction: discord.Interaction, select: discord.ui.Select
    ) -> None:
        await interaction.response.defer()
        if select.values:
            self.nationality: Locale = Locale(select.values[0])
            self.location: Locale = self.nationality
        else:
            self.nationality = None
            self.location = None
        self.generate_fake_identity()
        self.page: str = "main"
        await self._update()

    @discord.ui.select(min_values=0, max_values=1, placeholder="Select a location.")
    async def location_select(
        self, interaction: discord.Interaction, select: discord.ui.Select
    ) -> None:
        await interaction.response.defer()
        if select.values:
            self.location: Locale = Locale(select.values[0])
        else:
            self.location = None
        self.generate_fake_identity()
        self.page: str = "main"
        await self._update()

    @discord.ui.select(min_values=1, max_values=1, placeholder="Select the page.")
    async def select_page(
        self, interaction: discord.Interaction, select: discord.ui.Select
    ) -> None:
        await interaction.response.defer()
        self.page: str = select.values[0]
        await self._update()

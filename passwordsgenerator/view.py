from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

from redbot.core.utils.chat_formatting import box

import hashlib

_: Translator = Translator("PasswordsGenerator", __file__)

DEFAULT_LENGTHS: typing.Dict[str, int] = {
    "length": 16, "min_upper": 1, "min_lower": 1, "min_digits": 1, "min_special": 1,
    "min_word_length": 3, "max_word_length": 8, "max_int_value": 1000, "number_of_elements": 4,
}
DEFAULT_INCLUDE_CHARACTERS: typing.List[str] = ["upper", "lower", "digits", "special"]


class PasswordsGeneratorView(discord.ui.View):
    def __init__(
        self,
        cog: commands.Cog,
        easy_to_remember: bool = False,
        lengths: typing.Dict[str, int] = None,
        include_characters: typing.List[typing.Literal["upper", "lower", "digits", "special"]] = DEFAULT_INCLUDE_CHARACTERS,
    ) -> None:
        super().__init__(timeout=180)
        self.cog: commands.Cog = cog
        self.ctx: commands.Context = None
        self.current_password: str = None

        self.easy_to_remember: bool = easy_to_remember
        self.lengths: typing.Dict[str, int] = lengths or {}
        self.include_characters: typing.List[typing.Literal["upper", "lower", "digits", "special"]] = include_characters

        self.ephemeral.label = _("Ephemeral")
        self.lengths_button.label = _("Lengths")
        self.include_characters_select.placeholder = _("Include Characters")
        self.hashes.label = _("Hashes")

    def get_embed(self, store_password: bool = True) -> discord.Embed:
        password, strength = self.cog.generate_password(
            easy_to_remember=self.easy_to_remember,
            lengths=self.lengths,
            include_characters=self.include_characters,
        )
        if store_password:
            self.current_password = password
        return self.cog.get_embed(
            password=password,
            strength=strength,
        )

    async def start(self, ctx: commands.Context) -> None:
        self.ctx: commands.Context = ctx
        await self._update(edit_message=False)
        self._message: discord.Message = await ctx.send(
            embed=self.get_embed(),
            view=self,
        )
        self.cog.views[self._message] = self
        return self._message

    async def _update(self, edit_message: bool = True) -> None:
        self.remove_item(self.include_characters_select)
        if not self.easy_to_remember:
            self.change_mode.emoji = "🤔"
            self.change_mode.label = _("Easy to Remember")
            INCLUDE_CHARACTERS_OPTIONS = {
                "upper": {
                    "label": _("Upper Characters"),
                    "emoji": "🔠",
                    "description": "ABC",
                },
                "lower": {
                    "label": _("Lower Characters"),
                    "emoji": "🔡",
                    "description": "abc",
                },
                "digits": {
                    "label": _("Digits"),
                    "emoji": "🔢",
                    "description": "123",
                },
                "special": {
                    "label": _("Special Characters"),
                    "emoji": "🔣",
                    "description": "!@#",
                },
            }
            self.include_characters_select.options.clear()
            for key, value in INCLUDE_CHARACTERS_OPTIONS.items():
                self.include_characters_select.add_option(
                    emoji=value["emoji"],
                    label=value["label"],
                    description=value["description"],
                    value=key,
                    default=key in self.include_characters,
                )
            self.add_item(self.include_characters_select)
        else:
            self.change_mode.emoji = "🤖"
            self.change_mode.label = _("Random")
        if edit_message:
            try:
                await self._message.edit(
                    embed=self.get_embed(),
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
        await self._update()

    @discord.ui.button(emoji="🔒", label="Ephemeral", style=discord.ButtonStyle.success)
    async def ephemeral(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.send_message(
            embed=self.get_embed(store_password=False),
            ephemeral=True,
        )

    @discord.ui.button(emoji="✖️", style=discord.ButtonStyle.danger)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer()
        try:
            await self._message.delete()
        except discord.HTTPException:
            pass

    @discord.ui.button(style=discord.ButtonStyle.secondary)
    async def change_mode(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer()
        self.easy_to_remember = not self.easy_to_remember
        await self._update()

    @discord.ui.button(emoji="📋", label="Lengths", style=discord.ButtonStyle.secondary)
    async def lengths_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.send_modal(LengthsModal(self))

    @discord.ui.select(placeholder="Include Characters", min_values=1, max_values=4)
    async def include_characters_select(self, interaction: discord.Interaction, select: discord.ui.Select) -> None:
        await interaction.response.defer()
        self.include_characters = [option for option in select.values]
        await self._update()

    @discord.ui.button(emoji="#️⃣", label="Hashes", style=discord.ButtonStyle.secondary)
    async def hashes(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        embed: discord.Embed = discord.Embed(
            title=_("Password Hashes:"),
        )
        for hash_name in ("md5", "sha1", "sha224", "sha256", "sha384", "sha512"):
            embed.add_field(
                name=f"{hash_name.upper()}:",
                value=box(hashlib.new(hash_name, self.current_password.encode()).hexdigest()),
                inline=False,
            )
        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
        )


class LengthsModal(discord.ui.Modal):
    def __init__(self, view: PasswordsGeneratorView) -> None:
        super().__init__(title=_("Lengths"))
        self.view: PasswordsGeneratorView = view
        if not self.view.easy_to_remember:
            self.inputs = [
                "length", "min_upper", "min_lower", "min_digits", "min_special",
            ]
        else:
            self.inputs = [
                "min_word_length", "max_word_length", "max_int_value", "number_of_elements",
            ]
        for key in self.inputs:
            text_input = discord.ui.TextInput(
                label=f"{key.replace('_', ' ').title()}:",
                default=str(self.view.lengths[key]) if key in self.view.lengths else None,
                placeholder=str(DEFAULT_LENGTHS[key]),
                max_length=3,
                required=False,
            )
            setattr(self, key, text_input)
            self.add_item(text_input)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        for key in self.inputs:
            value = getattr(self, key).value
            if not value:
                self.view.lengths.pop(key, None)
                continue
            try:
                value = int(value)
            except (ValueError, OverflowError):
                await interaction.response.send_message(
                    _("You must enter a valid number."), ephemeral=True
                )
                return
            if value <= 0:
                await interaction.response.send_message(
                    _("The value must be positive."), ephemeral=True
                )
                return
            if key != "max_int_value" and value > 500:
                await interaction.response.send_message(
                    _("The value must be less than 100."), ephemeral=True
                )
                return
            self.view.lengths[key] = value
        await interaction.response.defer()
        await self.view._update()

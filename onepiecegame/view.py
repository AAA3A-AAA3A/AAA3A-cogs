from AAA3A_utils import CogsUtils  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import asyncio
import functools
import random

from redbot.core.utils.menus import start_adding_reactions
from redbot.core.utils.predicates import MessagePredicate

from .type import Character

_: Translator = Translator("OnePieceGame", __file__)


class OnePieceGameView(discord.ui.View):
    def __init__(
        self,
        cog: commands.Cog,
        mode: typing.Literal["classic", "devil_fruit", "wanted_poster"],
    ) -> None:
        super().__init__(timeout=60 * 10)
        self.ctx: commands.Context = None
        self.cog: commands.Cog = cog
        self.mode: typing.Literal["classic", "devil_fruit", "wanted_poster"] = mode

        self.character: Character = None
        self.hints: typing.Dict[
            str, typing.Dict[typing.Literal["tries", "value"], typing.Union[int, str]]
        ] = {}
        self.has_won: bool = False
        self.attempts: typing.List[Character] = []
        self._message: discord.Message = None

        self.each_attempt_decreases_blurry_level: bool = True
        self.show_colors: bool = False

    async def start(self, ctx: commands.Context) -> typing.Tuple[bool, typing.List[str]]:
        self.ctx: commands.Context = ctx

        self.remove_item(self.select_wanted_poster_options)
        if self.mode == "classic":
            self.character: Character = random.choice(self.cog.characters)
        elif self.mode == "devil_fruit":
            self.character: Character = random.choice(
                [
                    character
                    for character in self.cog.characters
                    if character.devil_fruit is not None
                ]
            )
        elif self.mode == "wanted_poster":
            self.character: Character = random.choice(
                [character for character in self.cog.characters if character.bounty is not None]
            )
            self.select_wanted_poster_options.options = [
                discord.SelectOption(
                    emoji="🔍",
                    label=_("Each attempt decreases blurry level"),
                    value="each_attempt_decreases_blurry_level",
                    default=self.each_attempt_decreases_blurry_level,
                ),
                discord.SelectOption(
                    emoji="🌈",
                    label=_("Show colors"),
                    value="show_colors",
                    default=self.show_colors,
                ),
            ]
            self.add_item(self.select_wanted_poster_options)

        self.hints = self.cog.get_hints(self.mode, self.character)
        for name in self.hints:
            button: discord.ui.Button = discord.ui.Button(
                emoji="💡",
                label=f"{name} (0/{self.hints[name]['tries']})",
                style=discord.ButtonStyle.blurple,
                row=2,
                disabled=True,
            )
            button.callback = functools.partial(
                self.hint_callback,
                button=button,
            )
            self.add_item(button)

        self._message: discord.Message = await ctx.send(
            **await self.cog.get_kwargs(
                self.ctx,
                self.mode,
                self.character,
                each_attempt_decreases_blurry_level=self.each_attempt_decreases_blurry_level,
                show_colors=self.show_colors,
            ),
            view=self,
            reference=self.ctx.message.to_reference(fail_if_not_exists=False),
        )
        self.cog.views[self._message] = self

        try:
            while not self.has_won:
                guess = await self.ctx.bot.wait_for(
                    "message_without_command",
                    check=lambda message: (MessagePredicate.same_context(ctx)(message)),
                    timeout=60 * 5,
                )
                if guess.content.lower() == "cancel":
                    await self.ctx.send(
                        _(
                            "You have cancelled the game. The character was: **{character.name}**."
                        ).format(character=self.character),
                        reference=self._message.to_reference(fail_if_not_exists=False),
                        allowed_mentions=discord.AllowedMentions(replied_user=False),
                    )
                    break

                if (attempt := await self.cog.get_character_by_name(guess.content)) is None:
                    if ctx.bot_permissions.add_reactions:
                        start_adding_reactions(guess, "❌")
                    await self.ctx.send(
                        _("This character does not exist or is not supported by the game."),
                        delete_after=3,
                        reference=guess.to_reference(fail_if_not_exists=False),
                        allowed_mentions=discord.AllowedMentions(replied_user=False),
                    )
                    continue
                self.attempts.append(attempt)
                for button in self.children:
                    if isinstance(
                        button, discord.ui.Button
                    ) and button.emoji == discord.PartialEmoji.from_str("💡"):
                        hint_label = button.label.split(" (")[0]
                        button.disabled = len(self.attempts) < self.hints[hint_label]["tries"]
                        if not button.disabled:
                            button.label = hint_label
                        else:
                            button.label = f"{hint_label} ({len(self.attempts)}/{self.hints[hint_label]['tries']})"

                try:
                    await self._message.delete()
                except discord.HTTPException:
                    pass
                self._message: discord.Message = await ctx.send(
                    **await self.cog.get_kwargs(
                        self.ctx,
                        self.mode,
                        self.character,
                        attempts=self.attempts,
                        each_attempt_decreases_blurry_level=self.each_attempt_decreases_blurry_level,
                        show_colors=self.show_colors,
                    ),
                    view=self,
                    reference=self.ctx.message.to_reference(fail_if_not_exists=False),
                )
                self.cog.views[self._message] = self
                if attempt == self.character:
                    self.has_won = True
        except asyncio.TimeoutError:
            await self.ctx.send(
                _(
                    "You took too long to guess the character. The character was: **{character.name}**."
                ).format(
                    character=self.character,
                ),
                reference=self._message.to_reference(fail_if_not_exists=False),
                allowed_mentions=discord.AllowedMentions(replied_user=False),
            )

        await self.on_timeout()
        try:
            await self._message.edit(view=self)
        except discord.HTTPException:
            pass
        return self.has_won, self.attempts

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
        # try:
        #     await self._message.edit(view=self)
        # except discord.HTTPException:
        #     pass
        await self.cancel.callback(None)

    @discord.ui.button(emoji="✖️", label=_("Cancel"), style=discord.ButtonStyle.danger)
    async def cancel(
        self,
        interaction: typing.Optional[discord.Interaction],
        button: discord.ui.Button,
    ) -> None:
        if interaction is not None:
            await interaction.response.defer()
        await CogsUtils.invoke_command(
            bot=self.ctx.bot,
            author=self.ctx.author,
            channel=self.ctx.channel,
            command="cancel",
            prefix="",
            dispatch_message=True,
        )

    async def hint_callback(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        await interaction.response.send_message(
            embed=discord.Embed(
                title=button.label,
                description=self.hints[button.label.split(" (")[0]]["value"],
                color=await self.ctx.embed_color(),
            ),
            ephemeral=True,
        )
        button.style = discord.ButtonStyle.danger
        try:
            await self._message.edit(view=self)
        except discord.HTTPException:
            pass

    @discord.ui.select(min_values=0, max_values=2, row=1)
    async def select_wanted_poster_options(
        self,
        interaction: discord.Interaction,
        select: discord.ui.Select,
    ) -> None:
        self.each_attempt_decreases_blurry_level = (
            "each_attempt_decreases_blurry_level" in select.values
        )
        discord.utils.get(
            select.options,
            value="each_attempt_decreases_blurry_level",
        ).default = self.each_attempt_decreases_blurry_level
        self.show_colors = "show_colors" in select.values
        discord.utils.get(
            select.options,
            value="show_colors",
        ).default = self.show_colors
        kwargs = await self.cog.get_kwargs(
            self.ctx,
            self.mode,
            self.character,
            attempts=self.attempts,
            each_attempt_decreases_blurry_level=self.each_attempt_decreases_blurry_level,
            show_colors=self.show_colors,
        )
        kwargs["attachments"] = kwargs.pop("files")
        await interaction.response.edit_message(
            **kwargs,
            view=self,
        )

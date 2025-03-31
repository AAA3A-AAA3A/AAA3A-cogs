from AAA3A_utils import CogsUtils  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import asyncio
import random

from redbot.core.utils.menus import start_adding_reactions
from redbot.core.utils.predicates import MessagePredicate

_: Translator = Translator("WordleGame", __file__)


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


DIACRITIC_SYMBOLS: typing.Dict[str, str] = {
    "a": "àáâãäå",
    "c": "ç",
    "e": "èéêë",
    "i": "ìíîï",
    "n": "ñ",
    "o": "òóôõö",
    "u": "ùúûü",
    "y": "ýÿ",
}


class WordleGameView(discord.ui.View):
    def __init__(
        self,
        cog: commands.Cog,
        lang: Lang = Lang.ENGLISH,
        length: int = 5,
        max_attempts: int = 6,
    ) -> None:
        super().__init__(timeout=60 * 10)
        self.ctx: commands.Context = None
        self.cog: commands.Cog = cog
        self.lang: Lang = lang
        self.length: int = length
        self.max_attempts: int = max_attempts

        self.word: str = None
        self._message: discord.Message = None

    async def start(self, ctx: commands.Context) -> typing.Tuple[bool, typing.List[str]]:
        self.ctx: commands.Context = ctx

        if not (words := self.cog.words[self.lang.value][self.length]):
            raise commands.UserFeedbackCheckFailure(
                _("There are no words in this language with {length} letters.").format(
                    length=self.length
                )
            )
        self.word: str = random.choice(words)
        self._message: discord.Message = await ctx.send(
            **await self.cog.get_kwargs(
                self.ctx,
                self.lang,
                self.word,
                max_attempts=self.max_attempts,
            ),
            view=self,
            reference=self.ctx.message.to_reference(fail_if_not_exists=False),
        )
        self.cog.views[self._message] = self

        has_won, attempts = False, []
        try:
            while not has_won and len(attempts) < self.max_attempts:
                guess = await self.ctx.bot.wait_for(
                    "message",
                    check=lambda message: (
                        MessagePredicate.same_context(ctx)(message)
                        and (
                            (len(message.content) == self.length and message.content.isalpha())
                            or message.content.lower() == "cancel"
                        )
                    ),
                    timeout=60 * 5,
                )
                if guess.content.lower() == "cancel":
                    await self.ctx.send(
                        _("You have cancelled the game. The word was: **{word}**.").format(
                            word=self.word
                        ),
                        reference=self._message.to_reference(fail_if_not_exists=False),
                        allowed_mentions=discord.AllowedMentions(replied_user=False),
                    )
                    break

                attempt = guess.content.lower().translate(
                    str.maketrans(
                        {v: key for key, value in DIACRITIC_SYMBOLS.items() for v in value}
                    )
                )
                if attempt not in self.cog.dictionaries[self.lang.value][self.length]:
                    if ctx.bot_permissions.add_reactions:
                        start_adding_reactions(guess, "❌")
                    await self.ctx.send(
                        _("This word is not a valid word in the dictionary."),
                        delete_after=3,
                        reference=guess.to_reference(fail_if_not_exists=False),
                        allowed_mentions=discord.AllowedMentions(replied_user=False),
                    )
                    continue
                attempts.append(attempt)

                try:
                    await self._message.delete()
                except discord.HTTPException:
                    pass
                self._message: discord.Message = await ctx.send(
                    **await self.cog.get_kwargs(
                        self.ctx,
                        self.lang,
                        self.word,
                        attempts=attempts,
                        max_attempts=self.max_attempts,
                    ),
                    view=self,
                    reference=self.ctx.message.to_reference(fail_if_not_exists=False),
                )
                self.cog.views[self._message] = self
                if attempt == self.word:
                    has_won = True
        except asyncio.TimeoutError:
            await self.ctx.send(
                _("You took too long to guess the word. The word was: **{word}**.").format(
                    word=self.word,
                ),
                reference=self._message.to_reference(fail_if_not_exists=False),
                allowed_mentions=discord.AllowedMentions(replied_user=False),
            )

        self.cancel.disabled = True
        try:
            await self._message.edit(view=self)
        except discord.HTTPException:
            pass
        return has_won, attempts

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.data["custom_id"] == "WordleGameView_explanation":
            return True
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

    @discord.ui.button(
        label=_("Explanation"),
        style=discord.ButtonStyle.secondary,
        custom_id="WordleGameView_explanation",
    )
    async def explanation(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await interaction.response.send_message(
            embed=discord.Embed(
                title=_("Wordle Game - Explanation"),
                description=_(
                    "The game is simple, you have to guess a word in some attempts. A word is chosen randomly from a dictionary of words in a language and with a specific length. The game ends when you guess the word or when you reach the maximum number of attempts.\n"
                    "• If the letter is **🟩 Green**, it is in the correct position.\n"
                    "• If the letter is **🟨 Yellow**, it is in the word but not in the correct position.\n"
                    "• If the letter is **⬛ Grey**, it is not in the word.\n"
                    "You can cancel the game at any time by clicking on the button or typing `cancel`.\n\n"
                    "**Launch a new game by executing `{prefix}wordle`!**\n"
                    "Available languages: `en`, `fr`, `de`, `es`, `it`, `pt`, `nl`, `cs`, `el`, `id`, `ie`, `ph`, `pl`, `ua`, `ru`, `sv` and `tr`."
                ).format(prefix=self.ctx.prefix),
                color=await self.ctx.embed_color(),
            ),
            ephemeral=True,
        )

    @discord.ui.button(emoji="✖️", label=_("Cancel"), style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer()
        await CogsUtils.invoke_command(
            bot=self.ctx.bot,
            author=self.ctx.author,
            channel=self.ctx.channel,
            command="cancel",
            prefix="",
            dispatch_message=True,
        )

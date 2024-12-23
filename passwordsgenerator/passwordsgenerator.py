from AAA3A_utils import Cog  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

from redbot.core.utils.chat_formatting import box

import string
from password_generator import PasswordGenerator
from passwordgenerator import pwgenerator as pw
from password_strength import PasswordStats

from .view import DEFAULT_LENGTHS, DEFAULT_INCLUDE_CHARACTERS, PasswordsGeneratorView

# Credits:
# General repo credits.

_: Translator = Translator("PasswordsGenerator", __file__)


@cog_i18n(_)
class PasswordsGenerator(Cog):
    """Generate random and possibly easier to remember passwords with specific requirements!"""

    def generate_password(
        self,
        easy_to_remember: bool = False,
        lengths: typing.Dict[str, int] = {},
        include_characters: typing.List[typing.Literal["upper", "lower", "digits", "special"]] = DEFAULT_INCLUDE_CHARACTERS,
    ) -> typing.Tuple[str, float]:
        _lengths = DEFAULT_LENGTHS.copy()
        _lengths.update(lengths)
        lengths = _lengths
        if not easy_to_remember:
            pwo: PasswordGenerator = PasswordGenerator()
            pwo.minlen = pwo.maxlen = lengths["length"]
            if "upper" not in include_characters:
                pwo.minuchars = 0
                pwo.excludeuchars = pwo.upper_chars
            else:
                pwo.minuchars = lengths["min_upper"]
            if "lower" not in include_characters:
                pwo.minlchars = 0
                pwo.excludelchars = pwo.lower_chars
            else:
                pwo.minlchars = lengths["min_lower"]
            if "digits" not in include_characters:
                pwo.minnumbers = 0
                pwo.excludenumbers = pwo.numbers_list
            else:
                pwo.minnumbers = lengths["min_digits"]
            if "special" not in include_characters:
                pwo.minschars = 0
                pwo.excludeschars = pwo._schars
            else:
                pwo.minschars = lengths["min_special"]
            password = pwo.generate()
        else:
            password = pw.pw(
                min_word_length=lengths["min_word_length"],
                max_word_length=lengths["max_word_length"],
                max_int_value=lengths["max_int_value"],
                number_of_elements=lengths["number_of_elements"],
            )
        return password, PasswordStats(password).strength()

    def get_embed(self, password: str, strength: float) -> discord.Embed:
        embed: discord.Embed = discord.Embed(
            title=_("Generated Password"),
            description=box(password),
            color=(
                discord.Color.green()
                if strength >= 0.66 else (
                    discord.Color.orange()
                    if strength >= 0.50 else
                    discord.Color.red()
                )
            ),
        )
        embed.add_field(
            name=_("Length:"),
            value=str(len(password)),
        )
        embed.add_field(
            name=_("Strength:"),
            value=f"{strength:.2f} / 1.00",
            inline=True,
        )
        return embed

    @commands.bot_has_permissions(embed_links=True)
    @commands.hybrid_command(aliases=["genpass"])
    async def generatepassword(
        self,
        ctx: commands.Context,
        easy_to_remember: typing.Optional[bool] = False,
        length: typing.Optional[commands.Range[int, 6, 1000]] = None,
        include_special: typing.Optional[bool] = True,
    ) -> None:
        """Generate a random password."""
        lengths = {"length": length} if length is not None else {}
        include_characters = DEFAULT_INCLUDE_CHARACTERS.copy()
        if not include_special:
            include_characters.remove("special")
        view: PasswordsGeneratorView = PasswordsGeneratorView(
            self,
            easy_to_remember=easy_to_remember,
            lengths=lengths,
            include_characters=include_characters,
        )
        await view.start(ctx)

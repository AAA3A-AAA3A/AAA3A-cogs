from AAA3A_utils import Cog, CogsUtils  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
from redbot.core.bot import Red  # isort:skip
import typing  # isort:skip

import io
import re

import aiohttp

from redbot.core.utils.chat_formatting import box

from .converters import Flake8FlagsConverter, PyLintFlagsConverter, MyPyFlagsConverter, BanditFlagsConverter, PyRightFlagsConverter, RuffFlagsConverter
from .linter import Linter

# Credits:
# General repo credits.
# Thanks to rtk-rnjn for a part of the code (https://github.com/rtk-rnjn/Parrot/tree/main/cogs/rtfm)!

_ = Translator("LintCodes", __file__)


@cog_i18n(_)
class LintCodes(Cog):
    """A cog to lint a code from Discord, with Flake8, PyLint, MyPy, Bandit, Black, Isort, Yapf, AutoFlake8, PyRight and Ruff!"""

    def __init__(self, bot: Red) -> None:
        super().__init__(bot=bot)
        self.__authors__: typing.List[str] = ["rtk-rnjn", "AAA3A"]

        self._session: aiohttp.ClientSession = None

    async def cog_load(self) -> None:
        await super().cog_load()
        self._session: aiohttp.ClientSession = aiohttp.ClientSession()

    async def cog_unload(self) -> None:
        if self._session is not None:
            await self._session.close()
        await super().cog_unload()

    async def red_delete_data_for_user(self, *args, **kwargs) -> None:
        """Nothing to delete."""
        return

    async def red_get_data_for_user(self, *args, **kwargs) -> typing.Dict[str, typing.Any]:
        """Nothing to get."""
        return {}

    async def get_code_from_context(
        self,
        ctx: commands.Context,
        code: typing.Optional[str],
    ) -> str:
        if ctx.message.attachments:
            file = ctx.message.attachments[0]
            if file.size > 20000:
                raise commands.UserFeedbackCheckFailure(_("File must be smaller than 20 kio."))
            buffer = io.BytesIO()
            await ctx.message.attachments[0].save(buffer)
            code = buffer.read().decode("utf-8")
            if ctx.message.attachments[0].filename.split(".")[-1] not in ["txt", "py", "pyc", "pyo", "pyd", "pyw", "rpy"]:
                raise commands.UserFeedbackCheckFailure(_("Incorrect Python file extension."))
        elif code is not None:
            if code.strip().startswith("url="):
                url = code[4:].strip()
                regex_gist = r"^https:\/\/gist\.github\.com\/([a-zA-Z0-9_-]+)\/([a-zA-Z0-9]+)$"
                regex_pastebin = r"^https:\/\/(www\.)?pastebin\.com\/(raw\/)?([a-zA-Z0-9]+)$"
                if (match := re.match(regex_gist, url)) is not None:
                    __, gist_id = match.groups()
                    api_url = f"https://api.github.com/gists/{gist_id}"
                    async with self._session.get(api_url) as r:
                        response = await r.json()
                    code = response["files"][f"{gist_id}.txt"]["content"]
                elif (match := re.match(regex_pastebin, url)) is not None:
                    paste_id = match[3]
                    api_url = f"https://pastebin.com/raw/{paste_id}"
                    async with self._session.get(api_url) as r:
                        code = await r.text()
                else:
                    api_url = url
                    async with self._session.get(api_url) as r:
                        code = await r.text()
        else:
            raise commands.UserFeedbackCheckFailure(_("Please provide the code!"))

        if ctx.interaction is not None:
            return code

        begin = code.find("```")
        language_identifier = code[
            begin + 3: code[begin + 3:].find("\n") + begin + 3
        ].lower()
        no_code = False
        try:
            end = code[begin + 3 + len(language_identifier):].rfind("```")
        except IndexError:
            no_code = True
        if begin == -1 or end == -1:
            no_code = True
        if no_code:
            raise commands.UserFeedbackCheckFailure(
                _("Incorrect syntax, please use Markdown's syntax for your code.")
            )
        if language_identifier not in ["python", "py"]:
            raise commands.UserFeedbackCheckFailure(
                _(
                    "Incorrect language identifier for your code, use `python` for the code syntax."
                ).format(ctx=ctx)
            )
        before = code[:begin]
        after = code[end + begin + 6 + len(language_identifier):]
        lines = ((before[:-1] if before else "") + (after[1:] if after else "")).split("\n")
        if len(lines) == 1 and lines[0] == "":
            lines = []
        return code[
            (begin + 4 + len(language_identifier)): (
                end + begin + 2 + len(language_identifier)
            )
        ]

    @commands.is_owner()
    @commands.hybrid_group(aliases=["linter", "lint"])
    async def lintcode(self, ctx: commands.Context):
        pass

    @lintcode.command(name="flake8", aliases=["f8", "flake"])
    async def flake8_shortcut(self, ctx: commands.Context, *, code: str = None):
        """Format code with Flake8, without flags, just the code."""
        code = await self.get_code_from_context(ctx, code=code)
        await Linter(linter="flake8", flags=None).lint(ctx, code=code)

    @commands.is_owner()
    @lintcode.command(name="aflake8", aliases=["af8", "aflake"])
    async def flake8_advanced(self, ctx: commands.Context, *, flags: Flake8FlagsConverter):
        """Format code with Flake8, with flags.

        **Supported flags:**

        - `--code <code>`
        - `--count <yes>`
        - `--verbose <yes>`
        - `--statistics <yes>`
        - `--doctests <yes>`

        - `--color <auto/always/never>`

        - `--ignore <ignore_list>`
        - `--select <select_list>`

        - `--max_line_length <integer>`
        - `--max_doc_length <integer>`
        - `--max_complexity <integer>`
        """
        code = await self.get_code_from_context(ctx, code=box(flags.code, lang="py"))
        await Linter(linter="flake8", flags=flags).lint(ctx, code=code)

    @lintcode.command(name="pylint", aliases=["pyl"])
    async def pylint_shortcut(self, ctx: commands.Context, *, code: str = None):
        """Format code with PyLint, without flags, just the code."""
        code = await self.get_code_from_context(ctx, code=code)
        await Linter(linter="pylint", flags=None).lint(ctx, code=code)

    @commands.is_owner()
    @lintcode.command(name="apylint", aliases=["apyl"])
    async def pylint_advanced(self, ctx: commands.Context, *, flags: PyLintFlagsConverter):
        """Format code with PyLint, with flags.

        **Supported flags:**
        - `--code <code>`

        - `--confidence <high/control_flow/inference_failure/undefined/inference>` = `HIGH CONTROL_FLOW INFERENCE_FAILURE UNDEFINED INFERENCE`

        - `--disable <disable_list>`
        - `--enable <enable_list>`
        """
        code = await self.get_code_from_context(ctx, code=box(flags.code, lang="py"))
        await Linter(linter="pylint", flags=flags).lint(ctx, code=code)

    @lintcode.command(name="mypy", aliases=["mp"])
    async def mypy_shortcut(self, ctx: commands.Context, *, code: str = None):
        """Format code with MyPy, without flags, just the code."""
        code = await self.get_code_from_context(ctx, code=code)
        await Linter(linter="mypy", flags=None).lint(ctx, code=code)

    @commands.is_owner()
    @lintcode.command(name="amypy", aliases=["amp"])
    async def mypy_advanced(self, ctx: commands.Context, *, flags: MyPyFlagsConverter):
        """Format code with MyPy, with flags.

        **Supported flags:**
        - `--code <code>`

        - Import Discovery:
          - `--no_namespace_packages <yes>`
          - `--ignore_missing_imports <yes>`
          - `--follow_imports <skip/silent/error/normal>`
          - `--no_site_packages <yes>`
          - `--no_silence_site_packages <yes>`.

        - Disallow dynamic typing:
          - `--disallow_any_unimported <yes>`
          - `--disallow_any_expr <yes>`
          - `--disallow_any_decorated <yes>`
          - `--disallow_any_explicit <yes>`
          - `--disallow_any_generics <yes>`
          - `--allow_any_generics <yes>`
          - `--disallow_subclassing_any <yes>`
          - `--allow_subclassing_any <yes>`

        - Untyped definitions and calls:
          - `--disallow_untyped_calls <yes>`
          - `--allow_untyped_calls <yes>`
          - `--disallow_untyped_defs <yes>`
          - `--allow_untyped_defs <yes>`
          - `--disallow_incomplete_defs <yes>`
          - `--allow_incomplete_defs <yes>`
          - `--check_untyped_defs <yes>`
          - `--no_check_untyped_defs <yes>`
          - `--disallow_untyped_decorators <yes>`
          - `--allow_untyped_decorators <yes>`

        - None and Optional handling:
          - `--implicit_optional <yes>`
          - `--no_implicit_optional <yes>`
          - `--no_strict_optional <yes>`
          - `--strict_optional <yes>`

        - Configuring warnings:
          - `--warn_redunant_casts <yes>`
          - `--no_warn_redunant_casts <yes>`
          - `--warn_unused_ignores <yes>`
          - `--no_warn_unused_ignores <yes>`
          - `--warn_no_return <yes>`
          - `--no_warn_no_return <yes>`
          - `--warn_return_any <yes>`
          - `--no_warn_return_any <yes>`
          - `--warn_unreachable <yes>`
          - `--no_warn_unreachable <yes>`

        - Miscellaneous strictness flags:
          - `--allow_untyped_globals <yes>`
          - `--disallow_untyped_globals <yes>`
          - `--allow_redifinition <yes>`
          - `--disallow_redifinition <yes>`
          - `--implicit_reexport <yes>`
          - `--no_implicit_reexport <yes>`
          - `--strict_equality <yes>`
          - `--no_strict_equality <yes>`
          - `--strict_concatenate <yes>`
          - `--no_strict_concatenate <yes>`
          - `--strict <yes>`

        - Configuring error messages:
          - `--show_error_context <yes>`
          - `--hide_error_context <yes>`
          - `--show_column_numbers <yes>`
          - `--hide_column_numbers <yes>`
          - `--show_error_end <yes>`
          - `--hide_error_end <yes>`
          - `--show_error_codes <yes>`
          - `--hide_error_codes <yes>`
          - `--pretty <yes>`
        """
        code = await self.get_code_from_context(ctx, code=box(flags.code, lang="py"))
        await Linter(linter="mypy", flags=flags).lint(ctx, code=code)

    @lintcode.command(name="bandit", aliases=["bd"])
    async def bandit_shortcut(self, ctx: commands.Context, *, code: str = None):
        """Format code with Bandit, without flags, just the code."""
        code = await self.get_code_from_context(ctx, code=code)
        await Linter(linter="bandit", flags=None).lint(ctx, code=code)

    @commands.is_owner()
    @lintcode.command(name="abandit", aliases=["abd"])
    async def bandit_advanced(self, ctx: commands.Context, *, flags: BanditFlagsConverter):
        """Format code with Bandit, with flags.

        **Supported flags:**
        - `--code <code>`

        - `--read <yes>`
        - `--verbose <yes>`

        - `--skip <ignore_list>`

        - `--level <low/medium/high>`
        - `--confidence <low/medium/high>`
        """
        code = await self.get_code_from_context(ctx, code=box(flags.code, lang="py"))
        await Linter(linter="bandit", flags=flags).lint(ctx, code=code)

    @lintcode.command(name="black", aliases=["fmt"])
    async def black_shortcut(self, ctx: commands.Context, *, code: str = None):
        """Format code with Black, without flags, just the code."""
        code = await self.get_code_from_context(ctx, code=code)
        await Linter(linter="black", flags=None).lint(ctx, code=code)

    @lintcode.command(name="isort", aliases=["is"])
    async def isort_shortcut(self, ctx: commands.Context, *, code: str = None):
        """Format code with Isort, without flags, just the code."""
        code = await self.get_code_from_context(ctx, code=code)
        await Linter(linter="isort", flags=None).lint(ctx, code=code)

    @lintcode.command(name="yapf", aliases=["yf"])
    async def yapf_shortcut(self, ctx: commands.Context, *, code: str = None):
        """Format code with Yapf, without flags, just the code."""
        code = await self.get_code_from_context(ctx, code=code)
        await Linter(linter="yapf", flags=None).lint(ctx, code=code)

    @lintcode.command(name="autopep8", aliases=["ap8"])
    async def autopep8_shortcut(self, ctx: commands.Context, *, code: str = None):
        """Format code with AutoPep8, without flags, just the code."""
        code = await self.get_code_from_context(ctx, code=code)
        await Linter(linter="autopep8", flags=None).lint(ctx, code=code)

    @lintcode.command(name="pyright", aliases=["pyr"])
    async def pyright_shortcut(self, ctx: commands.Context, *, code: str = None):
        """Format code with PyRight, without flags, just the code.

        **Supported flags:**
        - `--code <code>`
        """
        code = await self.get_code_from_context(ctx, code=code)
        await Linter(linter="pyright", flags=None).lint(ctx, code=code)

    @commands.is_owner()
    @lintcode.command(name="apyright", aliases=["apyr"])
    async def pyright_advanced(self, ctx: commands.Context, *, flags: PyRightFlagsConverter):
        """Format code with PyRight, with flags."""
        code = await self.get_code_from_context(ctx, code=box(flags.code, lang="py"))
        await Linter(linter="pyright", flags=flags).lint(ctx, code=code)

    @lintcode.command(name="ruff", aliases=["rf"])
    async def ruff_shortcut(self, ctx: commands.Context, *, code: str = None):
        """Format code with Ruff, without flags, just the code."""
        code = await self.get_code_from_context(ctx, code=code)
        await Linter(linter="ruff", flags=None).lint(ctx, code=code)

    @commands.is_owner()
    @lintcode.command(name="aruff", aliases=["arf"])
    async def ruff_advanced(self, ctx: commands.Context, *, flags: RuffFlagsConverter):
        """Format code with Ruff, with flags.

        **Supported flags:**
        - `--code <code>`

        - `--ignore <ignore_list>`
        - `--select <select_list>`

        - `--line_length <integer>`
        - `--max_doc_length <integer>`
        - `--max_complexity <integer>`
        """
        code = await self.get_code_from_context(ctx, code=box(flags.code, lang="py"))
        await Linter(linter="ruff", flags=flags).lint(ctx, code=code)

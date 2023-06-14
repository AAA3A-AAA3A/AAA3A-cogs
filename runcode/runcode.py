from AAA3A_utils import Cog, CogsUtils, Menu  # isort:skip
from redbot.core import commands, app_commands  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
from redbot.core.bot import Red  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import asyncio
import io
import re
import textwrap

import aiohttp
from fuzzywuzzy import fuzz
from redbot.core.utils.chat_formatting import box, humanize_list, pagify

from .data import LANGUAGES_FILES_EXTENSIONS, LANGUAGES_IDENTIFIERS, LANGUAGES_IMAGES
from .types import (
    TioLanguage,
    TioRequest,
    TioResponse,
    WandboxEngine,
    WandboxRequest,
    WandboxResponse,
)  # NOQA

# Credits:
# General repo credits.

_ = Translator("RunCode", __file__)


class WandboxLanguageConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> str:
        ctx.cog: RunCode
        if argument in ctx.cog.wandbox_languages:
            return argument
        for _language in LANGUAGES_IDENTIFIERS:
            if (
                argument.lower() == _language.lower()
                or argument.lower() in LANGUAGES_IDENTIFIERS[_language]
            ):
                if _language not in ctx.cog.wandbox_languages:
                    raise commands.BadArgument(_("The cog is not fully charged."))
                return _language
        raise commands.BadArgument(
            _(
                "Incorrect language identifier for your code.\nTo list all the supported languages identifiers, please use `{ctx.prefix}setruncode listidentifiers`."
            ).format(ctx=ctx)
        )


class TioLanguageConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> TioLanguage:
        ctx.cog: RunCode
        if argument not in ctx.cog.wandbox_languages:  # Improve language converter
            for _language in LANGUAGES_IDENTIFIERS:
                if (
                    argument.lower() == _language.lower()
                    or argument.lower() in LANGUAGES_IDENTIFIERS[_language]
                ):
                    argument = _language
        if argument == "Python":
            argument = "Python 3"
        matches = sorted(
            ctx.cog.tio_languages,
            key=lambda x: fuzz.ratio(argument, x),
            reverse=True,
        )
        return ctx.cog.tio_languages[matches[0]]


class ListConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> typing.List[str]:
        return list(re.split(r";|,|\|", argument))


class WandboxFlagsConverter(commands.FlagConverter):  # , prefix="--", delimiter=" "
    engine: str = commands.Flag(name="engine", annotation=str, default=None)
    input: str = commands.Flag(name="input", annotation=str, default=None)
    compiler_options: str = commands.Flag(
        name="compiler_options", annotation=ListConverter, default=None
    )
    runtime_options: str = commands.Flag(
        name="runtime_options", annotation=ListConverter, default=None
    )

    async def convert(self, ctx: commands.Context, argument: str) -> typing.Any:
        if ":" not in argument:
            raise commands.BadArgument(_("No flags in argument."))
        return super().conver(ctx, argument)


class TioFlagsConverter(commands.FlagConverter):
    inputs: typing.List[str] = commands.Flag(name="inputs", annotation=ListConverter, default=None)
    compiler_flags: typing.List[str] = commands.Flag(
        name="compiler_flags", annotation=ListConverter, default=None
    )
    command_line_options: typing.List[str] = commands.Flag(
        name="command_line_options", annotation=ListConverter, default=None
    )
    args: typing.List[str] = commands.Flag(name="args", annotation=ListConverter, default=None)

    async def convert(self, ctx: commands.Context, argument: str) -> typing.Any:
        if ":" not in argument:
            raise commands.BadArgument(_("No flags in argument."))
        return super().conver(ctx, argument)


@cog_i18n(_)
class RunCode(Cog):
    """A cog to compile and run codes in some languages! Use `[p]setruncode listlanguages` to get a list of all the available languages."""

    def __init__(self, bot: Red) -> None:
        self.bot: Red = bot

        self.wandbox_languages: typing.Dict[
            str, typing.Dict[str, typing.Dict[str, WandboxEngine]]
        ] = {}
        self.tio_languages: typing.Dict[str, TioLanguage] = {}

        self._session: aiohttp.ClientSession = None
        self.history: typing.Dict[
            typing.Union[discord.Member, discord.User], typing.List[WandboxResponse, TioResponse]
        ] = {}

        self.cogsutils: CogsUtils = CogsUtils(cog=self)

    async def cog_load(self) -> None:
        self._session: aiohttp.ClientSession = aiohttp.ClientSession()
        asyncio.create_task(self.load_wandbox_languages())
        asyncio.create_task(self.load_tio_languages())

    async def cog_unload(self) -> None:
        if self._session is not None:
            await self._session.close()
        await super().cog_unload()

    async def load_wandbox_languages(
        self, force: typing.Optional[bool] = False
    ) -> typing.Dict[str, typing.Dict[str, typing.Dict[str, typing.Dict[str, str]]]]:
        if self.wandbox_languages and not force:
            return self.wandbox_languages
        self.wandbox_languages = {}
        async with self._session.get("https://wandbox.org/api/list.json") as r:
            result = await r.json()
        for info in result:
            language = info["language"]
            if language not in ["CPP", "OpenSSL"]:
                if language.endswith(" script"):  # Bash and Vim
                    language = language[:-7]
                if language not in self.wandbox_languages:
                    self.wandbox_languages[language] = {}
                # info["template"] is a list but it only contains one element at the moment.
                template = info["templates"][0]
                if template not in self.wandbox_languages[language]:
                    self.wandbox_languages[language][template] = {}
                name = info["name"]
                self.wandbox_languages[language][template][name] = WandboxEngine(
                    name=name,
                    version=info["version"],
                    template=template,
                    language=language,
                    compiler_option_raw=info["compiler-option-raw"],
                    runtime_option_raw=info["runtime-option-raw"],
                    display_compile_command=info["display-compile-command"],
                )
        return self.wandbox_languages

    async def load_tio_languages(
        self, force: typing.Optional[bool] = False
    ) -> typing.Dict[str, typing.Dict[str, typing.Dict[str, typing.Dict[str, str]]]]:
        if self.tio_languages and not force:
            return self.tio_languages
        self.tio_languages = {}
        async with self._session.get("https://tio.run/languages.json") as r:
            result = await r.json()
        for language in result:
            name = result[language]["name"]
            self.tio_languages[name] = TioLanguage(
                name=name,
                link=result[language].get("link", None),
                prettify=result[language].get("prettify", None),
                value=language,
            )

    def get_wandbox_request_from_eval(
        self, language: typing.Union[str, WandboxEngine], code: str
    ) -> WandboxRequest:
        if isinstance(language, WandboxEngine):
            engine = language
        else:
            if language not in self.wandbox_languages:
                for _language in self.wandbox_languages:
                    if (
                        language.lower() == _language.lower()
                        or language.lower() in LANGUAGES_IDENTIFIERS[_language]
                    ):
                        language = _language
                        break
                else:
                    raise RuntimeError("Language not found.")
            engine: WandboxEngine = list(
                list(self.wandbox_languages[language].values())[0].values()
            )[0]
        return WandboxRequest(
            cog=self,
            engine=engine,
            code=code,
            save=True,
            stdin="",
            compiler_options="",
            runtime_options="",
        )  # compiler=DEFAULT_ENGINES[engine.language][1]

    def get_tio_request_from_eval(
        self, language: typing.Union[str, TioLanguage], code: str
    ) -> WandboxRequest:
        if not isinstance(language, TioLanguage):
            matches = sorted(
                self.tio_languages,
                key=lambda x: fuzz.ratio(language, x),
                reverse=True,
            )
            language = self.tio_languages[matches[0]]
        return TioRequest(
            cog=self,
            language=language,
            code=code,
            inputs=[],
            compiler_flags=[],
            command_line_options=[],
            args=[],
        )

    async def get_code_from_context(
        self,
        ctx: commands.Context,
        code: typing.Optional[str],
        provided_language: typing.Optional[str],
    ):
        _language = provided_language
        _code = None

        if ctx.message.attachments:
            file = ctx.message.attachments[0]
            if file.size > 20000:
                raise commands.UserFeedbackCheckFailure(_("File must be smaller than 20 kio."))
            buffer = io.BytesIO()
            await ctx.message.attachments[0].save(buffer)
            code = buffer.read().decode("utf-8")
            if _language is None:
                if (
                    language_extension := ctx.message.attachments[0].filename.split(".")[-1]
                ) != "txt":
                    for language in LANGUAGES_FILES_EXTENSIONS:
                        if language_extension in LANGUAGES_FILES_EXTENSIONS[language]:
                            _language = language
                            break
                    _language = ctx.message.attachments[0].filename.split(".")[-1]
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

        if ctx.interaction is None:
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
            if _language is None:
                for language in LANGUAGES_IDENTIFIERS:
                    if language_identifier in LANGUAGES_IDENTIFIERS[language]:
                        _language = language
                        break
                else:
                    raise commands.UserFeedbackCheckFailure(
                        _(
                            "Incorrect language identifier for your code.\nTo list all the supported languages identifiers, please use `{ctx.prefix}setruncode listidentifiers`."
                        ).format(ctx=ctx)
                    )
            before = code[:begin]
            after = code[end + begin + 6 + len(language_identifier) :]
            lines = ((before[:-1] if before else "") + (after[1:] if after else "")).split("\n")
            if len(lines) == 1 and lines[0] == "":
                lines = []
            _code = code[
                (begin + 4 + len(language_identifier)): (
                    end + begin + 2 + len(language_identifier)
                )
            ]
        else:
            _code = code

        wrapping = {
            "python": "async def func():\ncode",
            "c": "#include <stdio.h>\nint main() {code}",
            "cpp": "#include <iostream>\nint main() {code}",
            "cs": "using System;class Main {static void Main(string[] args) {code}}" if ctx.command == self.runtio else "using System;class Program {static void Main(string[] args) {code}}",
            "java": "public class prog {public static void main(String[] args) {code}}",  # Main.java
            "rust": "fn main() {code}",
            "d": "import std.stdio; void main(){code}",
            "kotlin": "fun main(args: Array<String>) {code}",
        }
        if (
            getattr(_language, "name", _language).split(" ")[0].lower() in wrapping
            and getattr(_language, "name", None) != "Python 1"
        ):
            _code = wrapping[getattr(_language, "name", _language).split(" ")[0].lower()].replace(
                "code", textwrap.indent(_code, "    ")
            )
            if getattr(_language, "name", _language).split(" ")[0].lower() == "python":
                _code = (
                    "import asyncio\nasync def _func():\n"
                    + textwrap.indent(_code, "    ")
                    + "\n\n    result = await func()\n    if result is not None:\n        print(result)\nasyncio.run(_func())"
                )

        return _language, _code

    @commands.hybrid_command(aliases=["executecode"])
    async def runcode(
        self,
        ctx: commands.Context,
        verbose: typing.Optional[bool] = False,
        language: typing.Optional[WandboxLanguageConverter] = None,
        parameters: typing.Optional[WandboxFlagsConverter] = None,
        *,
        code: typing.Optional[str] = None,
    ) -> None:
        """
        Run a code in a langage, with Wandbox API.

        Arguments:
        - `verbose`: Without this mode, only the programme output will be sent, without any additional information. In case of an error, it will be used automatically.
        - `language`: If not specified, the command will try to "guess" with the file extension or Discord Markdown syntax.
        - `parameters`: Optional option to send with the request. `engine:1/cpython-3.10.2`, `input:<input>`, `compiler_options:option1|option2|option3` and `runtime_options:option1|option2|option3`.
        - `code`: May be normal code, but also an attached file, or a link from [pastebin](https://pastebin.com), [Github gist](https://gist.github.com) or another "raw" website.
                  If you use a link, your command must end with this syntax: `link=<link>` (no space around `=`). You may also not provide it and upload an attachment instead.
        """
        if parameters is None:
            _parameters = {}
        else:
            _parameters = {
                key: getattr(parameters, key)
                for key in parameters.get_flags().keys()
                if getattr(parameters, key)
            }

        raw_request = {}

        _parameters["code_language"], raw_request["code"] = await self.get_code_from_context(
            ctx, code=code, provided_language=language
        )
        if _parameters["code_language"] is None:
            raise commands.UserFeedbackCheckFailure(
                _(
                    "The language of your code could not be found. Specify it with the `language` parameter."
                )
            )

        code_language = _parameters["code_language"]
        if "engine" in _parameters:
            engine: str = _parameters["engine"].lower()
            try:
                engine_index = int(engine)
                if engine_index >= 1:
                    i = 0
                    for engine_template in self.wandbox_languages[code_language]:
                        nb_engines = len(self.wandbox_languages[code_language][engine_template])
                        if engine_index > nb_engines + i:
                            i += nb_engines
                        else:
                            raw_request["engine"]: WandboxEngine = list(
                                self.wandbox_languages[code_language][engine_template].values()
                            )[engine_index - i - 1]
                            break
            except ValueError:
                for engine_template in self.wandbox_languages[code_language]:
                    for _engine in self.wandbox_languages[code_language][engine_template].values():
                        if engine == _engine.name:
                            raw_request["engine"]: WandboxEngine = _engine
                            break
            if "engine" not in raw_request:
                raise commands.UserFeedbackCheckFailure(
                    _(
                        "`{engine}` is not a correct engine for {code_language}\nTo list all the available engine for it, please use `{ctx.prefix}setruncode listengines {code_language}`."
                    ).format(engine=engine, code_language=code_language, ctx=ctx)
                )
        else:
            raw_request["engine"]: WandboxEngine = list(
                list(self.wandbox_languages[code_language].values())[0].values()
            )[0]
        raw_request["stdin"] = " ".join(_parameters.get("input", [""]))
        if "compiler_options" in _parameters:
            if not raw_request["engine"].compiler_option_raw:
                engine = raw_request["engine"]
                await ctx.send(
                    _(
                        "There is no options available for compilation using `{engine}`.\nIgnoring this option."
                    ).format(engine=engine)
                )
                raw_request["compiler_options"] = ""
            else:
                raw_request["compiler_options"] = " ".join(_parameters["compiler_options"])
        else:
            raw_request["compiler_options"] = ""
        if "runtime_options" in _parameters:
            if not raw_request["engine"].runtime_option_raw:
                engine = raw_request["engine"]
                await ctx.send(
                    _(
                        "There is no options available for runtime execution `{engine}`.\nIgnoring this option."
                    ).format(engine=engine)
                )
                raw_request["runtime_options"] = ""
            else:
                raw_request["runtime_options"] = " ".join(_parameters["runtime_options"])
        else:
            raw_request["runtime_options"] = ""

        request = WandboxRequest(cog=self, save=True, **raw_request)
        try:
            response = await request.fetch_response()
        except RuntimeError as e:
            raise commands.UserFeedbackCheckFailure(
                "The external server returned an error:\n" + box(str(e), lang="py")
            )
        if ctx.author not in self.history:
            self.history[ctx.author] = []
        self.history[ctx.author].append(response)
        await response.send(ctx, verbose=verbose)

    @commands.hybrid_command(aliases=["tiorun"])
    async def runtio(
        self,
        ctx: commands.Context,
        verbose: typing.Optional[bool],
        language: TioLanguageConverter,
        parameters: typing.Optional[WandboxFlagsConverter] = None,
        *,
        code: typing.Optional[str] = None,
    ) -> None:
        """
        Run a code in a langage, with Tio API.

        Arguments:
        - `verbose`: Without this mode, only the programme output will be sent, without any additional information. In case of an error, it will be used automatically.
        - `language`: If not specified, the command will try to "guess" with the file extension or Discord Markdown syntax.
        - `parameters`: Optional option to send with the request. `inputs:input1|input2|input3`, `compiler_flags:flag1|flag2|flag3`, `command_line_options:option1|option2|option3` and `args:arg1|arg2|arg3`.
        - `code`: May be normal code, but also an attached file, or a link from [pastebin](https://pastebin.com), [Github gist](https://gist.github.com) or another "raw" website.
                  If you use a link, your command must end with this syntax: `link=<link>` (no space around `=`). You may also not provide it and upload an attachment instead.
        """
        if parameters is None:
            _parameters = {}
        else:
            _parameters = {
                key: getattr(parameters, key)
                for key in parameters.get_flags().keys()
                if getattr(parameters, key)
            }

        raw_request = {}

        raw_request["language"], raw_request["code"] = await self.get_code_from_context(
            ctx, code=code, provided_language=language
        )

        raw_request["inputs"] = _parameters.get("inputs", [])
        raw_request["compiler_flags"] = _parameters.get("compiler_flags", [])
        raw_request["command_line_options"] = _parameters.get("command_line_options", [])
        raw_request["args"] = _parameters.get("args", [])
        request = TioRequest(cog=self, **raw_request)
        try:
            response = await request.fetch_response()
        except RuntimeError as e:
            raise commands.UserFeedbackCheckFailure(
                "The external server returned an error:\n" + box(str(e), lang="py")
            )
        if ctx.author not in self.history:
            self.history[ctx.author] = []
        self.history[ctx.author].append(response)
        await response.send(ctx, verbose=verbose)

    # async def _cogsutils_add_hybrid_commands(
    #     self, command: typing.Union[commands.HybridCommand, commands.HybridGroup]
    # ) -> None:
    #     if command.app_command is None:
    #         return
    #     if not isinstance(command, commands.HybridCommand):
    #         return
    #     if "language" in command.app_command._params and command.qualified_name == "runcode":
    #         command.app_command._params["language"].required = True
    #         command.app_command._params["language"].default = "Python"
    #     if "code" in command.app_command._params:
    #         command.app_command._params["code"].required = True
    #     _params1 = command.app_command._params.copy()
    #     _params2 = list(command.app_command._params.keys())
    #     _params2 = sorted(_params2, key=lambda x: _params1[x].required, reverse=True)
    #     _params3 = {key: _params1[key] for key in _params2}
    #     command.app_command._params = _params3

    @runcode.autocomplete("language")
    async def runcode_language_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> typing.List[app_commands.Choice[str]]:
        return (
            [
                app_commands.Choice(name=language, value=language)
                for language in list(self.wandbox_languages.keys())
                if language.lower().startswith(current.lower())
            ][:25]
            if current
            else [
                app_commands.Choice(name=language, value=language)
                for language in list(self.wandbox_languages.keys())[:25]
            ]
        )

    @runtio.autocomplete("language")
    async def runtio_language_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> typing.List[app_commands.Choice[str]]:
        return (
            [
                app_commands.Choice(name=language, value=language)
                for language in list(self.tio_languages.keys())
                if language.lower().startswith(current.lower())
            ][:25]
            if current
            else [
                app_commands.Choice(name=language, value=language)
                for language in list(self.tio_languages.keys())[:25]
            ]
        )

    @commands.hybrid_group(name="setruncode")
    async def configuration(self, ctx: commands.Context) -> None:
        """
        View RunCode options.
        """
        pass

    @configuration.command(name="listlanguages")
    async def _languages_list(
        self, ctx: commands.Context, api: typing.Literal["wandbox", "tio"]
    ) -> None:
        """
        Shows a list of all the available languages, or Wandbox or Tio API.
        """
        if api == "wandbox":
            keys: str = humanize_list([f"`{key}`" for key in self.wandbox_languages.keys()])
        elif api == "tio":
            keys: str = humanize_list(
                [f"[{key}]({value.link})" for key, value in self.tio_languages.items()]
            )
        pages = list(pagify(keys, delims=[", ["], page_length=4000))
        embeds = []
        for page in pages:
            embed = discord.Embed(
                title=f"RunCode {api.capitalize()} API Languages", color=await ctx.embed_color()
            )
            embed.description = page
            embeds.append(embed)
        await Menu(pages=embeds).start(ctx)

    @configuration.command(name="listengines")
    async def _engines_list(self, ctx: commands.Context, language: str) -> None:
        """
        Shows a list of all the available engines for a specified language, only for Wandbox API.

        Arguments:
        - `language`: The language name.
        """
        if language not in self.wandbox_languages:
            for _language in self.wandbox_languages:
                if (
                    language.lower() == _language.lower()
                    or language.lower() in LANGUAGES_IDENTIFIERS[_language]
                ):
                    language = _language
                    break
            else:
                raise RuntimeError("Language not found.")
        keys: str = humanize_list(
            [f"`{key}`" for key in list(self.wandbox_languages[language].values())[0].keys()]
        )
        embed = discord.Embed(title="RunCode Wandbox API Engines", color=await ctx.embed_color())
        embed.set_author(
            name=f"{language.capitalize()} language", icon_url=LANGUAGES_IMAGES[language]
        )
        embed.description = keys
        await ctx.send(embed=embed)

    @configuration.command(name="listidentifiers")
    async def _identifiers_list(self, ctx: commands.Context) -> None:
        """
        Lists all the languages identifiers recognized by the bot, only for Wandbox API.
        """
        result: str = "\n".join(
            [
                f'**{language.capitalize()}**: {humanize_list([f"`{identifier}`" for identifier in identifiers])}'
                for language, identifiers in LANGUAGES_IDENTIFIERS.items()
            ]
        )
        embed = discord.Embed(
            title="RunCode Wandbox API Identifiers", color=await ctx.embed_color()
        )
        embed.description = result
        await ctx.send(embed=embed)

    @configuration.command(name="listextensions")
    async def _extensions_list(self, ctx: commands.Context) -> None:
        """
        Lists all the languages extensions.
        """
        result: str = "\n".join(
            [
                f'**{language.capitalize()}**: {humanize_list([f"`.{extension}`" for extension in extensions])}'
                for language, extensions in LANGUAGES_FILES_EXTENSIONS.items()
            ]
        )
        embed = discord.Embed(title="Languages extensions", color=await ctx.embed_color())
        embed.description = result
        await ctx.send(embed=embed)

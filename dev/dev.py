from AAA3A_utils import Cog, Menu, Settings, CogsUtils  # isort:skip
from redbot.core import commands, Config  # isort:skip
from redbot.core.bot import Red  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import ast
import asyncio
import collections
import contextlib
import io
import random
import re
import subprocess
import sys
import textwrap

import aiohttp
import rich
from pygments.styles import get_style_by_name
from redbot.core import dev_commands
from redbot.core.utils.chat_formatting import box
from redbot.core.utils.predicates import MessagePredicate

from .dashboard_integration import DashboardIntegration
from .env import DevEnv, DevSpace, Exit, ctxconsole
from .view import ExecuteView, cleanup_code

# Credits:
# General repo credits.
# Thanks to Cogs-Creators for the original Dev cog!
# Thanks to Zeph for many ideas and a big part of the code (code removed from public)!

_: Translator = Translator("Dev", __file__)

TimeConverter: commands.converter.TimedeltaConverter = commands.converter.TimedeltaConverter(
    minimum=None,
    maximum=None,
    allowed_units=None,
    default_unit="minutes",
)


class SolarizedCustom(get_style_by_name("solarized-dark")):
    background_color = None
    line_number_background_color = None


@contextlib.contextmanager
def redirect(**kwargs):
    if "file" not in kwargs:
        kwargs["file"] = file = io.StringIO()
    else:
        file = None
    console = rich.console.Console(**kwargs)
    token = ctxconsole.set(console)
    try:
        yield console
    finally:
        ctxconsole.reset(token)
        if file:
            file.close()


class DevOutput(dev_commands.DevOutput):
    def __init__(self, *args, **kwargs) -> None:
        self._locals: typing.Dict[str, typing.Any] = kwargs.pop("_locals", {})
        self.prints: str = ""
        self.rich_tracebacks: bool = kwargs.pop("rich_tracebacks", False)
        self.exc: typing.Optional[Exception] = None
        super().__init__(*args, **kwargs)

    def __str__(self, output_mode: typing.Literal["repr", "repr_or_str", "str"] = "repr") -> str:
        _console_custom_kwargs: typing.Dict[str, typing.Any] = self.env.get(
            "_console_custom",
            {
                "width": 80,
                "no_color": True,
                "color_system": None,
                "tab_size": 2,
                "soft_wrap": False,
            },
        )
        with redirect(**_console_custom_kwargs) as console:
            with console.capture() as captured:
                if formatted_imports := self.env.get_formatted_imports():
                    console.print(
                        rich.syntax.Syntax(formatted_imports, "pycon", theme=SolarizedCustom)
                    )
                if self.prints:
                    console.print(self.prints)
                if printed := self._stream.getvalue():
                    console.print(printed.strip())
                if self.formatted_exc:
                    console.print(self.formatted_exc.strip())
                elif (
                    self.result is not None
                    or self.always_include_result
                    # and not self.prints
                    # and not formatted_imports
                    # and not printed
                ):
                    if output_mode == "str":
                        result = str(self.result)
                    elif (
                        isinstance(self.result, collections.abc.Iterable)
                        and not (output_mode == "repr" and isinstance(self.result, str))
                        or hasattr(self.result, "__dataclass_fields__")
                    ):
                        result = self.result
                    else:
                        result = repr(self.result)
                    try:
                        console.print(result)
                    except Exception as exc:
                        console.print(self.format_exception(exc).strip())
            output = captured.get().strip()
        return CogsUtils.replace_var_paths(dev_commands.sanitize_output(self.ctx, output)).replace(
            "```", "\u02CB\u02CB\u02CB"
        )

    async def send(
        self,
        *,
        tick: bool = True,
        output_mode: typing.Literal["repr", "repr_or_str", "str"] = "repr",
        ansi_formatting: bool = False,
        send_interactive: bool = False,
        send_dpy_objects: bool = True,
        wait: bool = True,
    ) -> None:
        if send_dpy_objects and self.result is not None:
            kwargs = {}
            channel_permissions = self.ctx.channel.permissions_for(self.ctx.me)
            if isinstance(self.result, discord.Embed) and channel_permissions.embed_links:
                kwargs["embed"] = self.result
            elif isinstance(self.result, discord.File) and channel_permissions.attach_files:
                kwargs["file"] = self.result
            elif isinstance(self.result, discord.abc.Iterable):
                kwargs = {"embeds": [], "files": []}
                for element in self.result:
                    if isinstance(element, discord.Embed) and channel_permissions.embed_links:
                        if (
                            len(kwargs["embeds"]) < 10
                            and (sum(len(embed) for embed in kwargs["embeds"]) + len(element))
                            <= 6000
                        ):
                            kwargs["embeds"].append(element)
                    elif isinstance(element, discord.File) and channel_permissions.attach_files:
                        if (sum(len(file) for file in kwargs["files"]) + len(element)) <= 6000:
                            kwargs["files"].append(element)
                for key in ("embeds", "files"):
                    if not kwargs[key]:
                        del kwargs[key]
            if kwargs:
                try:
                    await Menu(pages=[kwargs]).start(self.ctx, wait=False)
                except discord.HTTPException:
                    pass
        if tick and self.exc is not None:
            await self.ctx.react_quietly(
                reaction="❗"
                if isinstance(self.exc, SyntaxError)
                else (
                    "⏰"
                    if isinstance(
                        self.exc,
                        (
                            TimeoutError,
                            asyncio.TimeoutError,
                            aiohttp.ClientTimeout,
                            aiohttp.ServerTimeoutError,
                            subprocess.TimeoutExpired,
                        ),
                    )
                    else "❌"
                )
            )
        box_lang = (
            "ini" if self.ctx.command.name == "eshell" else ("ansi" if ansi_formatting else "py")
        )
        if send_interactive:
            task = self.ctx.send_interactive(
                [
                    box(page, lang=box_lang)
                    for page in dev_commands.get_pages(
                        (
                            f"{self.env['prefix_dev_output']}\n\n"
                            if "prefix_dev_output" in self.env
                            else None
                        )
                        + self.__str__(output_mode=output_mode)
                    )
                ],
            )
            if wait:
                await task
            else:
                await asyncio.create_task(task)
        elif pages := self.__str__(output_mode=output_mode):
            await Menu(
                pages=pages,
                prefix=self.env.get("prefix_dev_output"),
                lang=box_lang,
            ).start(
                self.ctx,
                wait=wait,
            )
        if tick and self.exc is None:
            await self.ctx.react_quietly(
                # sourcery skip: swap-if-expression
                reaction=commands.context.TICK
                if not hasattr(commands.context, "MORE_TICKS")
                else random.choice(list(commands.context.MORE_TICKS))
            )

    @classmethod
    async def from_debug(
        cls,
        ctx: commands.Context,
        *,
        source: str,
        source_cache: dev_commands.SourceCache,
        env: typing.Dict[str, typing.Any],
        **kwargs,
    ) -> "DevOutput":
        output = cls(
            ctx,
            source=source,
            source_cache=source_cache,
            filename=f"<debug command - snippet #{source_cache.take_next_index()}>",
            env=env,
            **kwargs,
        )
        await output.run_debug()
        return output

    @classmethod
    async def from_eval(
        cls,
        ctx: commands.Context,
        *,
        source: str,
        source_cache: dev_commands.SourceCache,
        env: typing.Dict[str, typing.Any],
        **kwargs,
    ) -> "DevOutput":
        output = cls(
            ctx,
            source=source,
            source_cache=source_cache,
            filename=f"<eval command - snippet #{source_cache.take_next_index()}>",
            env=env,
            **kwargs,
        )
        await output.run_eval()
        return output

    @classmethod
    async def from_repl(
        cls,
        ctx: commands.Context,
        *,
        source: str,
        source_cache: dev_commands.SourceCache,
        env: typing.Dict[str, typing.Any],
        **kwargs,
    ) -> "DevOutput":
        output = cls(
            ctx,
            source=source,
            source_cache=source_cache,
            filename=f"<repl session - snippet #{source_cache.take_next_index()}>",
            env=env,
            **kwargs,
        )
        await output.run_repl()
        return output

    async def run_debug(self) -> None:
        async def add_triangle_reaction_after_1_seconds():
            await asyncio.sleep(2)
            try:
                await self.ctx.message.add_reaction("▶")
            except discord.HTTPException:
                pass

        task = asyncio.create_task(add_triangle_reaction_after_1_seconds())

        self.env.update({"dev_output": self})
        self.env.update(**self._locals)
        _console_custom_kwargs: typing.Dict[str, typing.Any] = self.env.get(
            "_console_custom",
            {
                "width": 80,
                "no_color": True,
                "color_system": None,
                "tab_size": 2,
                "soft_wrap": False,
            },
        ).copy()
        _console_custom_kwargs["color_system"] = None
        with redirect(**_console_custom_kwargs) as console:
            with console.capture() as captured:
                try:
                    await super().run_debug()
                except Exit:  # Not a real exception...
                    pass
                except (SystemExit, KeyboardInterrupt):
                    raise
                except BaseException as exc:
                    self.set_exception(exc)
            self.always_include_result: bool = False
            self.prints: str = captured.get().strip()

        task.cancel()

    async def run_eval(self) -> None:
        async def add_triangle_reaction_after_1_seconds():
            await asyncio.sleep(2)
            try:
                await self.ctx.message.add_reaction("▶")
            except discord.HTTPException:
                pass

        task = asyncio.create_task(add_triangle_reaction_after_1_seconds())

        self.env.update({"dev_output": self})
        try:
            parse = ast.parse("async def func():\n%s" % textwrap.indent(self.raw_source, "  "))
            try:
                return_found = [d for d in parse.body[0].body if isinstance(d, ast.Return)][0]
            except IndexError:
                line = len(self.raw_source.split("\n"))
            else:
                line = return_found.lineno - 2
            _raw_source = self.raw_source.split("\n")
            _raw_source.insert(line, textwrap.indent("dev_output._locals.update(**locals())", ""))
            # `yield` like in Jishaku.
            for line, line_text in enumerate(_raw_source.copy()):
                _line_text = textwrap.dedent(line_text)
                if _line_text.startswith("yield "):
                    _raw_source[line] = textwrap.indent(
                        f"print(repr(({_line_text[6:]})))",
                        (len(line_text) - len(_line_text)) * " ",
                    )
            self.raw_source = "\n".join(_raw_source)
        except SyntaxError:
            pass
        self.env.update(**self._locals)
        _console_custom_kwargs: typing.Dict[str, typing.Any] = self.env.get(
            "_console_custom",
            {
                "width": 80,
                "no_color": True,
                "color_system": None,
                "tab_size": 2,
                "soft_wrap": False,
            },
        ).copy()
        _console_custom_kwargs["color_system"] = None
        with redirect(**_console_custom_kwargs) as console:
            with console.capture() as captured:
                try:
                    await super().run_eval()
                except Exit:  # Not a real exception...
                    pass
                except (SystemExit, KeyboardInterrupt):
                    raise
                except BaseException as exc:
                    self.set_exception(exc)
            self.prints: str = captured.get().strip()

        task.cancel()

    async def run_repl(self) -> None:
        async def add_triangle_reaction_after_1_seconds():
            await asyncio.sleep(2)
            try:
                await self.ctx.message.add_reaction("▶")
            except discord.HTTPException:
                pass

        task = asyncio.create_task(add_triangle_reaction_after_1_seconds())

        self.env.update({"dev_output": self})
        self.env.update(**self._locals)
        _console_custom_kwargs: typing.Dict[str, typing.Any] = self.env.get(
            "_console_custom",
            {
                "width": 80,
                "no_color": True,
                "color_system": None,
                "tab_size": 2,
                "soft_wrap": False,
            },
        ).copy()
        _console_custom_kwargs["color_system"] = None
        with redirect(**_console_custom_kwargs) as console:
            with console.capture() as captured:
                try:
                    await super().run_repl()
                except (Exit, SystemExit, KeyboardInterrupt):  # `Exit` isn't a real exception...
                    raise
                except BaseException as exc:
                    self.set_exception(exc)
            self.prints: str = captured.get().strip()

        task.cancel()

    def set_exception(self, exc: Exception, *, skip_frames: int = 1) -> None:
        self.exc: Exception = exc
        self.formatted_exc: str = self.format_exception(exc, skip_frames=skip_frames)

    def format_exception(self, exc: Exception, *, skip_frames: int = 1) -> str:
        if not self.rich_tracebacks:
            return super().format_exception(exc=exc, skip_frames=skip_frames)
        _console_custom_kwargs: typing.Dict[str, typing.Any] = self.env.get(
            "_console_custom",
            {
                "width": 80,
                "no_color": True,
                "color_system": None,
                "tab_size": 2,
                "soft_wrap": False,
            },
        ).copy()
        _console_custom_kwargs["color_system"] = None
        with redirect(**_console_custom_kwargs) as console:
            with console.capture() as captured:
                tb = exc.__traceback__
                for _ in range(skip_frames):
                    if tb is None:
                        break
                    tb = tb.tb_next
                # sometimes SyntaxError.text is None, sometimes it isn't
                if issubclass(type(exc), SyntaxError) and exc.lineno is not None:
                    try:
                        source_lines, line_offset = self.source_cache[exc.filename]
                    except KeyError:
                        pass
                    else:
                        if exc.text is None:
                            try:
                                # line numbers are 1-based, the list indexes are 0-based
                                exc.text = source_lines[exc.lineno - 1]
                            except IndexError:
                                # the frame might be pointing at a different source code, ignore...
                                pass
                            else:
                                exc.lineno -= line_offset
                                if sys.version_info >= (3, 10) and exc.end_lineno is not None:
                                    exc.end_lineno -= line_offset
                        else:
                            exc.lineno -= line_offset
                            if sys.version_info >= (3, 10) and exc.end_lineno is not None:
                                exc.end_lineno -= line_offset
                rich_tb = rich.traceback.Traceback.from_exception(
                    type(exc), exc, tb, extra_lines=0, theme=SolarizedCustom
                )
                console.print(rich_tb)
            return captured.get().strip()


@cog_i18n(_)
class Dev(DashboardIntegration, Cog, dev_commands.Dev):
    """Various development focused utilities!"""

    __authors__: typing.List[str] = ["Cog-Creators", "Zephyrkul (Zephyrkul#1089)", "AAA3A"]

    def __init__(self, bot: Red) -> None:
        super().__init__(bot=bot)

        self.env_extensions: typing.Dict[str, typing.Any] = {}
        self.source_cache: dev_commands.SourceCache = dev_commands.SourceCache()
        self._session: aiohttp.ClientSession = None
        self.dev_space: DevSpace = DevSpace()

        self._last_result: typing.Optional[typing.Any] = None
        self._last_locals: typing.Dict[
            typing.Union[discord.Member, discord.User], typing.Dict[str, typing.Any]
        ] = {}
        self.dev_outputs: typing.Dict[discord.Message, DevOutput] = {}
        self.sessions: typing.Dict[int, bool] = {}
        self._repl_tasks: typing.List[asyncio.Task] = []
        self._bypass_cooldowns_task: typing.Optional[asyncio.Task] = None

        self.config: Config = Config.get_conf(
            self,
            identifier=205192943327321000143939875896557571750,
            force_registration=True,
        )
        self.dev_global: typing.Dict[
            str, typing.Union[typing.Literal["repr", "repr_or_str", "str"], bool]
        ] = {
            "auto_imports": True,
            "output_mode": "repr",
            "rich_tracebacks": False,
            "ansi_formatting": False,
            "send_interactive": False,
            "send_dpy_objects": True,
            "use_last_locals": True,
            "downloader_already_agreed": False,
            "use_extended_environment": True,
        }
        self.config.register_global(
            auto_imports=True,
            output_mode="repr",
            rich_tracebacks=False,
            ansi_formatting=False,
            send_interactive=False,
            send_dpy_objects=True,
            use_last_locals=True,
            downloader_already_agreed=False,
            use_extended_environment=True,
        )

        _settings: typing.Dict[
            str, typing.Dict[str, typing.Union[typing.List[str], bool, str]]
        ] = {
            "auto_imports": {
                "converter": bool,
                "description": "Enable or disable auto imports.",
            },
            "output_mode": {
                "converter": typing.Literal["repr", "repr_or_str", "str"],
                "description": "Set the output mode. `repr` is to display the repr of the result. `repr_or_str` is to display in the same way, but a string as a string. `str` is to display the string of the result.",
            },
            "rich_tracebacks": {
                "converter": bool,
                "description": "Use `rich` to display tracebacks.",
            },
            "ansi_formatting": {
                "converter": bool,
                "description": "Use the `ansi` formatting for results.",
            },
            "send_interactive": {
                "converter": bool,
                "description": "Send results with `commands.Context.send_interactive`, not a Menu.",
            },
            "send_dpy_objects": {
                "converter": bool,
                "description": "If the result is an embed/file/attachment object or an iterable of these, send.",
            },
            "use_last_locals": {
                "converter": bool,
                "description": "Use the last locals for each evals. Locals are only registered for `[p]eval`, but can be used in other commands.",
            },
            "downloader_already_agreed": {
                "converter": bool,
                "description": "If enabled, Downloader will no longer prompt you to type `I agree` when adding a repo, even after a bot restart.",
            },
            "use_extended_environment": {
                "converter": bool,
                "description": "Use my own Dev env with useful values.",
            },
        }
        self.settings: Settings = Settings(
            bot=self.bot,
            cog=self,
            config=self.config,
            group=self.config.GLOBAL,
            settings=_settings,
            global_path=[],
            use_profiles_system=False,
            can_edit=True,
            commands_group=self.configuration,
        )

    async def cog_load(self) -> None:
        await super().cog_load()
        await self.settings.add_commands()
        if (
            await self.config.downloader_already_agreed()
            and (downloader_cog := self.bot.get_cog("Downloader")) is not None
        ):
            downloader_cog.already_agreed = True
        self._session: aiohttp.ClientSession = aiohttp.ClientSession()

    async def cog_unload(self) -> None:
        if self._session is not None:
            await self._session.close()
        core_dev: dev_commands.Dev = dev_commands.Dev()
        core_dev.env_extensions: typing.Dict[str, typing.Any] = self.env_extensions
        core_dev.source_cache: dev_commands.SourceCache = self.source_cache
        core_dev.dev_space: DevSpace = self.dev_space
        core_dev._last_result: typing.Optional[typing.Any] = self._last_result
        # core_dev.sessions: typing.Dict[int, bool] = self.sessions
        for task in self._repl_tasks:
            task.cancel()
        await self.bot.add_cog(core_dev)
        await super().cog_unload()

    def get_environment(
        self, ctx: commands.Context, use_extended_environment: bool = True
    ) -> DevEnv:
        return DevEnv.get_environment(ctx, use_extended_environment=use_extended_environment)

    async def my_exec(
        self,
        ctx: commands.Context,
        type: typing.Literal["debug", "eval", "repl"],
        source: str,
        env: typing.Optional[typing.Dict[str, typing.Any]] = None,
        send_result: bool = False,
        wait: bool = True,
    ) -> bool:
        tasks: typing.List[asyncio.Task] = [
            asyncio.create_task(
                ctx.bot.wait_for("message", check=MessagePredicate.cancelled(ctx))
            ),
            asyncio.create_task(
                self._my_exec(
                    ctx, type=type, source=source, env=env, send_result=send_result, wait=wait
                )
            ),
        ]
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in pending:
            task.cancel()
        result = done.pop().result()
        return result if result is not None else None

    async def _my_exec(
        self,
        ctx: commands.Context,
        type: typing.Literal["debug", "eval", "repl"],
        source: str,
        env: typing.Optional[typing.Dict[str, typing.Any]] = None,
        send_result: bool = False,
        wait: bool = True,
    ) -> DevOutput:
        source = cleanup_code(source)
        if env is None:
            env = self.get_environment(
                ctx, use_extended_environment=await self.config.use_extended_environment()
            )
        env["auto_imports"] = await self.config.auto_imports()
        if (
            isinstance(ctx.author, (discord.Member, discord.User))
            and ctx.author in self._last_locals
            and await self.config.use_last_locals()
        ):
            _locals = self._last_locals[ctx.author]
        else:
            _locals = {}
        types = {
            "debug": DevOutput.from_debug,
            "eval": DevOutput.from_eval,
            "repl": DevOutput.from_repl,
        }
        mobile = ctx.author.is_on_mobile() if isinstance(ctx.author, discord.Member) else False
        if await self.config.ansi_formatting():
            _console_custom_kwargs: typing.Dict[str, typing.Any] = {
                "width": 37 if mobile else 80,
                "no_color": mobile,
                "color_system": None if mobile else "standard",
                "tab_size": 2,
                "soft_wrap": False,
            }
        else:
            _console_custom_kwargs: typing.Dict[str, typing.Any] = {
                "width": 80,
                "no_color": True,
                "color_system": None,
                "tab_size": 2,
                "soft_wrap": False,
            }
        if _console_custom := env.get("_console_custom"):
            _console_custom_kwargs.update(_console_custom)
        env["_console_custom"] = _console_custom_kwargs
        output: DevOutput = await types[type](
            ctx,
            source=source,
            source_cache=self.source_cache,
            env=env,
            rich_tracebacks=await self.config.rich_tracebacks(),
            _locals=_locals,
        )
        self._last_result = output.result
        self.dev_outputs[ctx.message] = output
        if (
            type == "eval"
            and isinstance(ctx.author, (discord.Member, discord.User))
            and output._locals
        ):
            if ctx.author not in self._last_locals:
                self._last_locals[ctx.author] = {}
            self._last_locals[ctx.author].update(**output._locals)
        if send_result:
            send_interactive = await self.config.send_interactive()
            send_coroutine = output.send(
                tick=type != "repl",
                output_mode=await self.config.output_mode(),
                ansi_formatting=await self.config.ansi_formatting(),
                send_interactive=send_interactive,
                send_dpy_objects=await self.config.send_dpy_objects(),
                wait=wait,
            )
            if wait and not send_coroutine:
                await send_coroutine
            else:
                asyncio.create_task(send_coroutine)
        return output

    @commands.is_owner()
    @commands.hybrid_command()
    # @discord.utils.copy_doc(dev_commands.Dev.debug.callback)
    async def debug(self, ctx: commands.Context, *, code: str = None) -> None:
        """Evaluate a statement of python code.

        The bot will always respond with the return value of the code.
        If the return value of the code is a coroutine, it will be awaited,
        and the result of that will be the bot's response.

        Note: Only one statement may be evaluated. Using certain restricted
        keywords, e.g. yield, will result in a syntax error. For multiple
        lines or asynchronous code, see [p]repl or [p]eval.

        The code can be within a codeblock, inline code or neither, as long as they are not mixed and they are formatted correctly.
        You can upload a file with the code to be executed, or reply to a message containing the command, from any bot.

        Environment Variables:
            `ctx`      - the command invocation context
            `bot`      - the bot object
            `channel`  - the current channel object
            `author`   - the command author's member object
            `guild`    - the current guild object
            `message`  - the command's message object
            `_`        - the result of the last dev command
            `aiohttp`  - the aiohttp library
            `asyncio`  - the asyncio library
            `discord`  - the discord.py library
            `commands` - the redbot.core.commands module
            `cf`       - the redbot.core.utils.chat_formatting module
        (See `[p]setdev getenvironment` for more.)
        """
        if code is None:
            if ctx.message.attachments:
                try:
                    code = (await ctx.message.attachments[0].read()).decode(encoding="utf-8")
                except UnicodeDecodeError:
                    raise commands.UserFeedbackCheckFailure(
                        _("Unreadable attachment with `utf-8`.")
                    )
            elif ctx.message.reference is not None and isinstance(
                (reference := ctx.message.reference.resolved), discord.Message
            ):
                if (
                    match := re.compile(
                        r"(debug|(jsk|jishaku) (py|python|eval|ev))(\n)?( )?(?P<code>(.|\n)*)"
                    ).search(reference.content)
                ) is not None and match.groupdict()["code"].strip():
                    code = match.groupdict()["code"]
                elif (
                    re.compile(r"```py\n(.|\n)*\n```").match(reference.content)
                    and reference.content.count("```") == 2
                ):
                    code = reference.content
                else:
                    raise commands.UserFeedbackCheckFailure(_("This message isn't reachable."))
            else:
                return asyncio.create_task(ExecuteView(cog=self).start(ctx))
        source = cleanup_code(code)
        await self.my_exec(
            getattr(ctx, "original_context", ctx),
            type="debug",
            source=source,
            send_result=True,
        )

    @commands.is_owner()
    @commands.hybrid_command(name="eval")
    # @discord.utils.copy_doc(dev_commands.Dev._eval.callback)
    async def _eval(self, ctx: commands.Context, *, body: str = None) -> None:
        """Execute asynchronous code.

        This command wraps code into the body of an async function and then
        calls and awaits it. The bot will respond with anything printed to
        stdout, as well as the return value of the function.

        The code can be within a codeblock, inline code or neither, as long as they are not mixed and they are formatted correctly.
        You can upload a file with the code to be executed, or reply to a message containing the command, from any bot.

        Environment Variables:
            `ctx`      - the command invocation context
            `bot`      - the bot object
            `channel`  - the current channel object
            `author`   - the command author's member object
            `guild`    - the current guild object
            `message`  - the command's message object
            `_`        - the result of the last dev command
            `aiohttp`  - the aiohttp library
            `asyncio`  - the asyncio library
            `discord`  - the discord.py library
            `commands` - the redbot.core.commands module
            `cf`       - the redbot.core.utils.chat_formatting module
        (See `[p]setdev getenvironment` for more.)
        """
        if body is None:
            if ctx.message.attachments:
                try:
                    body = (await ctx.message.attachments[0].read()).decode(encoding="utf-8")
                except UnicodeDecodeError:
                    raise commands.UserFeedbackCheckFailure(
                        _("Unreadable attachment with `utf-8`.")
                    )
            elif ctx.message.reference is not None and isinstance(
                (reference := ctx.message.reference.resolved), discord.Message
            ):
                if (
                    match := re.compile(
                        r"(eval|ev|e|(jsk|jishaku) (py|python|eval|ev)|(runcode|executecode) (py|python))(\n)?( )?(?P<body>(.|\n)*)"
                    ).search(reference.content)
                ) is not None and match.groupdict()["body"].strip():
                    body = match.groupdict()["body"]
                elif (
                    re.compile(r"```py\n(.|\n)*\n```").match(reference.content)
                    and reference.content.count("```") == 2
                ):
                    body = reference.content
                else:
                    raise commands.UserInputError()
            else:
                return asyncio.create_task(ExecuteView(cog=self).start(ctx))
        source = cleanup_code(body)
        await self.my_exec(
            getattr(ctx, "original_context", ctx),
            type="eval",
            source=source,
            send_result=True,
        )

    @commands.is_owner()
    @commands.hybrid_command()
    # @discord.utils.copy_doc(dev_commands.Dev.repl.callback)
    async def repl(self, ctx: commands.Context) -> None:
        """Open an interactive REPL.

        The REPL will only recognise code as messages which start with a
        backtick. This includes codeblocks, and as such multiple lines can be
        evaluated.

        Use `exit()` or `quit` to exit the REPL session, prefixed with
        a backtick so they may be interpreted.

        You can upload a file with the code to be executed, or reply to a message containing the same command, for any bot.

        Environment Variables:
            `ctx`      - the command invocation context
            `bot`      - the bot object
            `channel`  - the current channel object
            `author`   - the command author's member object
            `guild`    - the current guild object
            `message`  - the command's message object
            `_`        - the result of the last dev command
            `aiohttp`  - the aiohttp library
            `asyncio`  - the asyncio library
            `discord`  - the discord.py library
            `commands` - the redbot.core.commands module
            `cf`       - the redbot.core.utils.chat_formatting module
        (See `[p]setdev getenvironment` for more.)
        """
        if ctx.channel.id in self.sessions:
            if self.sessions[ctx.channel.id]:
                await ctx.send(
                    _("Already running a REPL session in this channel. Exit it with `quit`.")
                )
            else:
                await ctx.send(
                    _(
                        "Already running a REPL session in this channel. Resume the REPL with `{prefix}replresume`."
                    ).format(prefix=ctx.prefix)
                )
            return

        env = self.get_environment(
            ctx, use_extended_environment=await self.config.use_extended_environment()
        )
        env["_"] = None
        self.sessions[ctx.channel.id] = True
        await ctx.send(
            _(
                "Enter code to execute or evaluate. `exit()` or `quit` to exit. `{prefix}replpause` to pause."
            ).format(prefix=ctx.prefix)
        )

        while True:
            task = asyncio.create_task(
                ctx.bot.wait_for("message", check=MessagePredicate.regex(r"^`", ctx))
            )
            self._repl_tasks.append(task)
            try:
                response = await task
            except asyncio.CancelledError:
                return
            finally:
                self._repl_tasks.remove(task)
            if not self.sessions[ctx.channel.id]:
                continue
            env["message"] = response
            source = cleanup_code(response.content)
            try:
                # if source in ("quit", "exit", "exit()"):
                #     raise Exit()
                output = await self._my_exec(
                    getattr(ctx, "original_context", ctx),
                    type="repl",
                    source=source,
                    env=env,
                    wait=False,
                    send_result=True,
                )
            except Exit:
                break
            try:
                if output.formatted_exc:
                    await response.add_reaction("❌")
                elif not str(output):
                    await response.add_reaction(
                        commands.context.TICK
                        if not hasattr(commands.context, "MORE_TICKS")
                        else random.choice(list(commands.context.MORE_TICKS))
                    )
            except discord.HTTPException:
                pass

        await ctx.send(_("Exiting."))
        del self.sessions[ctx.channel.id]

    @commands.is_owner()
    @commands.hybrid_command(name="replpause", aliases=["replresume"])
    async def pause(self, ctx: commands.Context, toggle: bool = None) -> None:
        """Pauses/resumes the REPL running in the current channel."""
        if ctx.channel.id not in self.sessions:
            await ctx.send(_("There is no currently running REPL session in this channel."))
            return
        if toggle is None:
            toggle = not self.sessions[ctx.channel.id]
        self.sessions[ctx.channel.id] = toggle
        if toggle:
            await ctx.send(_("The REPL session in this channel has been resumed."))
        else:
            await ctx.send(_("The REPL session in this channel is now paused."))

    @commands.is_owner()
    @commands.hybrid_command()
    async def bypasscooldowns(
        self,
        ctx: commands.Context,
        toggle: typing.Optional[bool] = None,
        *,
        time: TimeConverter = None,
    ) -> None:
        """Give bot owners the ability to bypass cooldowns.

        Does not persist through restarts.
        """
        if toggle is None:
            toggle = not ctx.bot._bypass_cooldowns
        if self._bypass_cooldowns_task is not None:
            self._bypass_cooldowns_task.cancel()
        ctx.bot._bypass_cooldowns = toggle
        if toggle:
            await ctx.send(
                _(
                    "Bot owners will now bypass all commands with cooldowns{optional_duration}."
                ).format(
                    optional_duration=""
                    if time is None
                    else f" for {CogsUtils.get_interval_string(time)}"
                )
            )
        else:
            await ctx.send(
                _(
                    "Bot owners will no longer bypass all commands with cooldowns{optional_duration}."
                ).format(
                    optional_duration=""
                    if time is None
                    else f" for {CogsUtils.get_interval_string(time)}"
                )
            )
        if time is not None:
            task = asyncio.create_task(asyncio.sleep(time.total_seconds()))
            self._bypass_cooldowns_task: asyncio.Task = task
            try:
                await task
            except asyncio.CancelledError:
                return
            finally:
                self._bypass_cooldowns_task = None
            ctx.bot._bypass_cooldowns = not toggle

    @commands.is_owner()
    @commands.hybrid_command(name="eshell")
    async def _eshell(
        self, ctx: commands.Context, silent: typing.Optional[bool] = False, *, command: str = None
    ) -> None:
        """Execute Shell commands.

        This command wraps the shell command into a Python code to invoke them.

        The code can be within a codeblock, inline code or neither, as long as they are not mixed and they are formatted correctly.
        You can upload a file with the code to be executed, or reply to a message containing the command, from any bot.
        """
        if command is None:
            if ctx.message.attachments:
                try:
                    command = (await ctx.message.attachments[0].read()).decode(encoding="utf-8")
                except UnicodeDecodeError:
                    raise commands.UserFeedbackCheckFailure(
                        _("Unreadable attachment with `utf-8`.")
                    )
            elif ctx.message.reference is not None and isinstance(
                (reference := ctx.message.reference.resolved), discord.Message
            ):
                if (
                    match := re.compile(
                        r"(eshell|shell|qshell)(\n)?( )?(?P<command>(.|\n)*)"
                    ).search(reference.content)
                ) is not None and match.groupdict()["command"].strip():
                    command = match.groupdict()["command"]
                elif (
                    re.compile(r"```py\n(.|\n)*\n```").match(reference.content)
                    and reference.content.count("```") == 2
                ):
                    command = reference.content
                else:
                    raise commands.UserInputError()
            else:
                raise commands.UserInputError()
        command = cleanup_code(command)

        # Thanks Jack for a part of this code!
        source = (
            cleanup_code(
                """
                import asyncio
                import asyncio.subprocess as asp
                import os
                import sys
                import typing

                command = '''
                COMMAND
                '''.strip()

                def get_env() -> typing.Dict[str, str]:
                    env = os.environ.copy()
                    if hasattr(sys, "real_prefix") or sys.base_prefix != sys.prefix:
                        if sys.platform == "win32":
                            binfolder = f"{sys.prefix}{os.path.sep}Scripts"
                            env["PATH"] = f"{binfolder}{os.pathsep}{env['PATH']}"
                        else:
                            binfolder = f"{sys.prefix}{os.path.sep}bin"
                            env["PATH"] = f"{binfolder}{os.pathsep}{env['PATH']}"
                    return env

                process = await asp.create_subprocess_shell(
                    command,
                    stdout=asp.PIPE,
                    stderr=asp.STDOUT,
                    env=get_env(),
                    executable=None,
                )
                try:
                    await process.wait()
                except asyncio.CancelledError:
                    prefix = f"Command was terminated early and this is a partial output:\\n\\n"
                    # raise
                else:
                    prefix = ""
                finally:
                    lines = [line async for line in process.stdout]
                    print(prefix + b"".join(lines).decode("utf-8", "replace").strip().replace("\\r", ""))
                """
            )
            .strip()
            .replace("COMMAND", command)
        )
        if silent:
            source = "\n".join(source.split("\n")[:-3])

        await self.my_exec(
            getattr(ctx, "original_context", ctx),
            type="eval",
            source=source,
            send_result=True,
        )

    @commands.is_owner()
    @commands.hybrid_group(name="setdev")
    async def configuration(self, ctx: commands.Context) -> None:
        """
        Commands to configure Dev.
        """
        pass

    @configuration.command(aliases=["getenv", "getformattedenvironment", "getformattedenv"])
    async def getenvironment(self, ctx: commands.Context, show_values: bool = True) -> None:
        """Display all Dev environment values."""
        env = self.get_environment(
            ctx, use_extended_environment=await self.config.use_extended_environment()
        )
        formatted_env = env.get_formatted_env(show_values=show_values)
        await Menu(pages=formatted_env, lang="py").start(ctx)

    @configuration.command(aliases=["rlocals"])
    async def resetlocals(self, ctx: commands.Context) -> None:
        """Reset its own locals in evals."""
        try:
            del self._last_locals[ctx.author]
        except ValueError:
            pass

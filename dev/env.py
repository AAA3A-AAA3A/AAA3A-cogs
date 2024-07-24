import asyncio
import builtins
import collections
import datetime
import functools
import importlib
import inspect
import logging
import os
import re
import sys
import textwrap
import time
import traceback
import types
from contextvars import ContextVar
from functools import partial
from io import BytesIO, StringIO

import aiohttp
import discord.ext
import redbot
import rich
from AAA3A_utils.cog import Cog
from AAA3A_utils.cogsutils import CogsUtils
from AAA3A_utils.context import Context, is_dev
from AAA3A_utils.loop import Loop
from AAA3A_utils.menus import Menu, Reactions
from AAA3A_utils.sentry import SentryHelper
from AAA3A_utils.settings import Settings
from AAA3A_utils.shared_cog import SharedCog
from AAA3A_utils.views import (
    Buttons,
    ChannelSelect,
    ConfirmationAskView,
    Dropdown,
    MentionableSelect,
    Modal,
    RoleSelect,
    Select,
    UserSelect,
)  # NOQA
from redbot.core import Config, dev_commands
from redbot.core import utils as redutils
from redbot.core.utils import chat_formatting as cf
from redbot.core.utils.chat_formatting import box
from rich.console import Console
from rich.table import Table

from redbot.core import commands  # isort:skip
from redbot.core.bot import Red  # isort:skip
import discord  # isort:skip
import typing  # isort:skip


ctxconsole = ContextVar[rich.console.Console]("ctxconsole")


class Exit(BaseException):
    pass


def no_colour_rich_markup(
    *objects: typing.Any, lang: str = "", no_box: typing.Optional[bool] = False
) -> str:
    """
    Slimmed down version of rich_markup which ensure no colours (/ANSI) can exist
    https://github.com/Cog-Creators/Red-DiscordBot/pull/5538/files (Kowlin)
    """
    temp_console = Console(  # Prevent messing with STDOUT's console
        color_system=None,
        file=StringIO(),
        force_terminal=True,
        width=80,
    )
    temp_console.print(*objects)
    if no_box:
        return temp_console.file.getvalue()
    return box(temp_console.file.getvalue(), lang=lang)  # type: ignore


class DevSpace:
    def __init__(self, **kwargs) -> None:
        self.__dict__.update(**kwargs)

    def __repr__(self) -> str:
        items = [f"{k}={v!r}" for k, v in self.__dict__.items()]
        return (
            f"<{self.__class__.__name__} {' '.join(items)}>"
            if items
            else f"<{self.__class__.__name__} [Nothing]>"
        )

    def __eq__(self, other: object) -> bool:
        if isinstance(self, self.__class__) and isinstance(other, self.__class__):
            return self.__dict__ == other.__dict__
        return NotImplemented

    def __len__(self) -> int:
        return len(self.__dict__)

    def __contains__(self, key: str) -> typing.Any:
        return key in self.__dict__

    def __iter__(self) -> typing.Iterator[typing.Tuple[str, typing.Any]]:
        yield from self.__dict__.items()

    def __reversed__(self) -> typing.Dict:
        return self.__dict__.__reversed__()

    def __getattr__(self, attr: str) -> typing.Any:
        raise AttributeError(attr)

    def __setattr__(self, attr: str, value: typing.Any) -> None:
        self.__dict__[attr] = value

    def __delattr__(self, attr: str) -> None:
        del self.__dict__[attr]

    def __getitem__(self, key: str) -> typing.Any:
        return self.__dict__[key]

    def __setitem__(self, key: str, value: typing.Any) -> None:
        self.__dict__[key] = value

    def __delitem__(self, key: str) -> None:
        del self.__dict__[key]

    def clear(self) -> None:
        self.__dict__.clear()

    def update(self, **kwargs) -> None:
        self.__dict__.update(**kwargs)

    def copy(self) -> typing.Any:  # typing_extensions.Self
        return self.__class__(**self.__dict__)

    def items(self):
        return self.__dict__.items()

    def keys(self):
        return self.__dict__.keys()

    def values(self):
        return self.__dict__.values()

    def get(self, key: str, _default: typing.Optional[typing.Any] = None) -> typing.Any:
        return self.__dict__.get(key, _default)

    def pop(self, key: str, _default: typing.Optional[typing.Any] = None) -> typing.Any:
        return self.__dict__.pop(key, _default)

    def popitem(self) -> typing.Any:
        return self.__dict__.popitem()

    def _update_with_defaults(
        self, defaults: typing.Iterable[typing.Tuple[str, typing.Any]]
    ) -> None:
        for key, value in defaults:
            self.__dict__.setdefault(key, value)


class DevEnv(typing.Dict[str, typing.Any]):
    is_dev = is_dev

    def __init__(self, *args, **kwargs) -> None:
        # self.__dict__ = {}
        super().__init__(*args, **kwargs)
        self.imported: typing.List[typing.Union[str, typing.Tuple[str, str]]] = []

    @classmethod
    def get_environment(
        cls, ctx: commands.Context, use_extended_environment: bool = True
    ) -> typing.Dict[str, typing.Any]:
        env = cls(  # In Dev cog by Zeph.
            **{
                "me": ctx.me,
                # Redirect builtin console functions to rich.
                "print": rich.print,
                "help": functools.partial(rich.inspect, help=True),
                # Eval and exec automatically put this in, but types.FunctionType does not.
                "__builtins__": builtins,
                # Fill in various other environment keys that some code might expect.
                "__builtin__": builtins,
                "__doc__": ctx.command.help,
                "__package__": None,
                "__loader__": None,
                "__spec__": None,
            }
        )
        env["interaction"] = ctx.interaction
        if getattr(ctx.channel, "category", None) is not None:
            env["category"] = ctx.channel.category
        Dev = ctx.bot.get_cog("Dev")
        if use_extended_environment:
            env.update(cls.get_env(ctx.bot, ctx))  # My nice env!
        base_env = dev_commands.Dev.get_environment(Dev, ctx)  # In Dev in Core.
        # del base_env["_"]
        env.update(base_env)
        env.update({"dev_env": env, "devenv": env})
        return env

    def get_formatted_env(
        self,
        ctx: typing.Optional[commands.Context] = None,
        show_values: typing.Optional[bool] = True,
    ) -> str:
        if show_values:
            raw_table = Table(
                "Key",
                "Value",
                title="------------------------------ DevEnv ------------------------------",
            )
        else:
            raw_table = Table(
                "Key", title="------------------------------ DevEnv ------------------------------"
            )
        for name, value in self.items():
            if name in self.imported:
                continue
            if show_values:
                raw_table.add_row(str(name), repr(value))
            else:
                raw_table.add_row(str(name))
        raw_table_str = no_colour_rich_markup(raw_table, no_box=True)
        raw_table_str = self.sanitize_output(self.get("ctx", ctx), raw_table_str)
        if ctx is not None:
            asyncio.create_task(Menu(pages=raw_table_str, lang="py").start(ctx))
        return raw_table_str

    def get_formatted_imports(self) -> str:
        if not (imported := self.imported):
            return ""
        imported.sort(key=lambda x: x if isinstance(x, str) else f"z{x[0]}")
        message = "".join(
            (
                f">>> import {_import}\n"
                if isinstance(_import, str)
                else f">>> from {_import[0]} import {_import[1]}\n"
            )
            for _import in imported
        )
        imported.clear()
        return message

    def __missing__(self, key: str) -> typing.Any:
        try:
            if (value := self["devspace"].get(key)) is not None:
                return value
        except (KeyError, AttributeError):
            pass
        if not self.get("auto_imports", True):
            raise KeyError(key)
        if key in {"exit", "quit"}:
            raise Exit()
        try:
            # this is called implicitly after KeyError, but
            # some modules would overwrite builtins (e.g. bin)
            return getattr(builtins, key)
        except AttributeError:
            pass
        try:
            module = importlib.import_module(key)
        except ImportError:
            pass
        else:
            self.imported.append(key)
            self[key] = module
            return module
        try:
            if (cog := self["bot"].get_cog(key)) is not None:
                self[key] = cog
                return cog
        except (KeyError, AttributeError):
            pass
        if key.lower().startswith("id"):
            _id = key[2:] if key[2] != "_" else key[3:]
            try:
                _id = int(_id)
            except ValueError:
                pass
            else:
                try:
                    if (member := self["guild"].get_member(_id)) is not None:
                        self[key] = member
                        return member
                except (KeyError, AttributeError):
                    pass
                try:
                    if (user := self["bot"].get_user(_id)) is not None:
                        self[key] = user
                        return user
                except (KeyError, AttributeError):
                    pass
                try:
                    if (guild := self["bot"].get_guild(_id)) is not None:
                        self[key] = guild
                        return guild
                except (KeyError, AttributeError):
                    pass
                try:
                    if (channel := self["guild"].get_channel(_id)) is not None:
                        self[key] = channel
                        return channel
                except (KeyError, AttributeError):
                    pass
                try:
                    if (role := self["guild"].get_role(_id)) is not None:
                        self[key] = role
                        return role
                except (KeyError, AttributeError):
                    pass
                try:
                    if (message := self["channel"].get_partial_message(_id)) is not None:
                        self[key] = message
                        return message
                except (KeyError, AttributeError):
                    pass
        if (attr := getattr(discord, key, None)) is not None:
            self.imported.append(("discord", key))
            self[key] = attr
            return attr
        if (attr := getattr(typing, key, None)) is not None:
            self.imported.append(("typing", key))
            self[key] = attr
            return attr
        if (attr := getattr(cf, key, None)) is not None:
            self.imported.append(("redbot.core.utils.chat_formatting", key))
            self[key] = attr
            return attr
        try:
            if is_dev(bot=self["bot"]) and (attr := getattr(CogsUtils, key, None)) is not None:
                self.imported.append(("AAA3A_utils.CogsUtils", key))
                self[key] = attr
                return attr
        except (KeyError, AttributeError):
            pass
        raise KeyError(key)

    @staticmethod
    def sanitize_output(ctx: commands.Context, input_: str) -> str:
        """Hides the bot's token from a string."""
        token = ctx.bot.http.token
        input_ = CogsUtils.replace_var_paths(input_)
        return re.sub(re.escape(token), "[EXPUNGED]", input_, re.I)

    @classmethod
    def get_env(
        cls, bot: Red, ctx: typing.Optional[commands.Context] = None
    ) -> typing.Dict[str, typing.Any]:
        logger = CogsUtils.get_logger(name="Test")

        def where(name_or_module: typing.Union[str, types.MethodType]) -> str:
            name = (
                name_or_module if isinstance(name_or_module, str) else (getattr(name_or_module, "__module__", None) or name_or_module.__name__)
            ).replace("-", "_")
            spec = importlib.util.find_spec(name)
            if spec is None:
                raise RuntimeError("Module `{name}` not found.".format(name=name))
            return spec.origin

        async def _rtfs(ctx: commands.Context, object):
            code = inspect.getsource(object)
            await Menu(pages=code, lang="py").start(ctx)

        def reference(ctx: commands.Context) -> typing.Optional[discord.Message]:
            if ctx.message.reference is not None and isinstance(
                ctx.message.reference.resolved, discord.Message
            ):
                return ctx.message.reference.resolved

        # def _console_custom(ctx: commands.Context):
        #     return {"width": 80, "color_system": None}

        def search_attribute(
            a, b: typing.Optional[str] = "", startswith: typing.Optional[str] = ""
        ) -> typing.List[str]:
            return [
                x
                for x in dir(a)
                if b.lower() in x.lower() and x.lower().startswith(startswith.lower())
            ]

        async def run_converter(
            converter: typing.Any, argument: str, label: typing.Optional[str] = "test"
        ) -> typing.Any:
            param = discord.ext.commands.parameters.Parameter(
                name=label, kind=inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=converter
            )
            return await discord.ext.commands.converter.run_converters(
                ctx, converter=param.converter, argument=argument, param=param
            )

        async def run_converters(
            command_or_function: typing.Union[str, commands.Command, typing.Callable],
            arguments: str,
        ) -> typing.Dict[str, typing.Any]:
            if isinstance(command_or_function, str):
                if (command := ctx.bot.get_command(command_or_function)) is None:
                    raise RuntimeError()
            elif isinstance(command_or_function, commands.Command):
                command = command_or_function
            else:
                command = commands.Command(command_or_function)
            view = discord.ext.commands.view.StringView(arguments)
            fake_context = type(
                "FakeContext",
                (),
                {
                    "bot": ctx.bot,
                    "command": command,
                    "message": ctx.message,
                    "prefix": None,
                    "view": view,
                },
            )
            await command._parse_arguments(fake_context)
            kwargs = {}
            for i, arg in enumerate(fake_context.args[1:]):
                kwargs[list(command.params.keys())[i]] = arg
            kwargs.update(fake_context.kwargs)
            return kwargs

        def get_internal(ctx: commands.Context):
            def _get_internal(
                name: typing.Literal["events", "listeners", "loggers", "parsers", "converters"],
                b: typing.Optional[str] = "",
                startswith: typing.Optional[str] = "",
            ):
                if name == "events":
                    if b == "":
                        result = ctx.bot.extra_events.copy()
                    else:
                        return ctx.bot.extra_events[b]
                elif name == "listeners":
                    if b == "":
                        result = ctx.bot._listeners.copy()
                    else:
                        return ctx.bot._listeners[b]
                elif name == "loggers":
                    result = logging.Logger.manager.loggerDict.copy()
                elif name == "parsers":
                    result = ctx.bot._get_websocket(0)._discord_parsers.copy()
                elif name == "converters":
                    result = discord.ext.commands.converter.CONVERTER_MAPPING.copy()
                else:
                    raise ValueError(name)
                result = {
                    name: value
                    for name, value in result.items()
                    if b.lower() in name.lower() and name.lower().startswith(startswith.lower())
                }
                return result

            return _get_internal

        def set_loggers_level(
            level: typing.Optional[str] = logging.DEBUG,
            loggers: typing.Optional[typing.List] = None,
            exclusions: typing.Optional[typing.List] = None,
            b: typing.Optional[str] = "",
            startswith: typing.Optional[str] = "",
        ) -> int:
            __loggers = logging.Logger.manager.loggerDict
            if loggers is not None:
                _loggers = [
                    logger
                    for name, logger in __loggers.items()
                    if name in loggers and isinstance(logger, logging.Logger)
                ]
            else:
                _loggers = [
                    logger for logger in __loggers.values() if isinstance(logger, logging.Logger)
                ]
            _loggers = [
                logger
                for logger in _loggers
                if b.lower() in logger.name and logger.name.lower().startswith(startswith.lower())
            ]
            if exclusions is not None:
                _loggers = [logger for logger in _loggers if logger.name not in exclusions]
            for logger in _loggers:
                logger.setLevel(level)
            return len(_loggers)

        def params(_object: typing.Any) -> None:
            return {param.name: param for param in inspect.signature(_object).parameters.values()}

        def find_all(predicate, iterable: collections.abc.Iterable) -> typing.List[typing.Any]:
            if hasattr(iterable, "__aiter__"):

                async def _a_find_all():
                    return [element async for element in iterable if predicate(element)]

                return _a_find_all()
            else:
                return [element for element in iterable if predicate(element)]

        def get_all(iterable: collections.abc.Iterable, **attrs) -> typing.List[typing.Any]:
            attrget = discord.utils.attrgetter
            converted = [
                (attrget(attr.replace("__", ".")), value) for attr, value in attrs.items()
            ]
            if hasattr(iterable, "__aiter__"):

                async def _a_get_all():
                    return [
                        element
                        async for element in iterable
                        if all(pred(element) == value for pred, value in converted)
                    ]

                return _a_get_all()
            else:
                return [
                    element
                    for element in iterable
                    if all(pred(element) == value for pred, value in converted)
                ]

        dev_space: DevSpace = getattr(ctx.bot.get_cog("Dev"), "dev_space", AttributeError())

        def get_url(ctx: commands.Context):
            async def _get_url(url: str, **kwargs):
                async with ctx.bot.get_cog("Dev")._session.get(url=url, **kwargs) as r:
                    return r

            return _get_url

        if is_dev(bot=bot):
            env = {
                # CogsUtils
                "CogsUtils": lambda ctx: CogsUtils,
                "Loop": lambda ctx: Loop,
                "Reactions": lambda ctx: Reactions,
                "Menu": lambda ctx: Menu,
                "SharedCog": lambda ctx: SharedCog,
                "Cog": lambda ctx: Cog,
                "Context": lambda ctx: Context,
                "Settings": lambda ctx: Settings,
                "SentryHelper": lambda ctx: SentryHelper,
                "logger": lambda ctx: logger,
                "_rtfs": lambda ctx: partial(_rtfs, ctx),
                "DevEnv": lambda ctx: cls,
                "DevSpace": lambda ctx: DevSpace,
                "Cogs": lambda ctx: CogsCommands.Cogs(
                    bot=ctx.bot, Cog=CogsCommands.Cog, Command=CogsCommands.Command
                ),
                "Commands": lambda ctx: CogsCommands.Commands(
                    bot=ctx.bot, Cog=CogsCommands.Cog, Command=CogsCommands.Command
                ),
            }
            # Dpy2 things
            env.update(
                {
                    "ConfirmationAskView": lambda ctx: ConfirmationAskView,
                    "Buttons": lambda ctx: Buttons,
                    "Dropdown": lambda ctx: Dropdown,
                    "Select": lambda ctx: Select,
                    "ChannelSelect": lambda ctx: ChannelSelect,
                    "MentionableSelect": lambda ctx: MentionableSelect,
                    "RoleSelect": lambda ctx: RoleSelect,
                    "UserSelect": lambda ctx: UserSelect,
                    "Modal": lambda ctx: Modal,
                }
            )
        else:
            env = {}
        env.update(
            {
                # Dpy & Red
                "discord": lambda ctx: discord,
                "redbot": lambda ctx: redbot,
                "Red": lambda ctx: Red,
                "redutils": lambda ctx: redutils,
                "cf": lambda ctx: cf,
                "Config": lambda ctx: Config,
                "run_converter": lambda ctx: run_converter,
                "run_converters": lambda ctx: run_converters,
                "Route": lambda ctx: discord.http.Route,
                "websocket": lambda ctx: ctx.bot._get_websocket(ctx.guild.id),
                "get_internal": get_internal,
                "set_loggers_level": lambda ctx: set_loggers_level,
                "find": lambda ctx: discord.utils.find,
                "get": lambda ctx: discord.utils.get,
                "MISSING": lambda ctx: discord.utils.MISSING,
                "escape_markdown": lambda ctx: discord.utils.escape_markdown,
                "as_chunks": lambda ctx: discord.utils.as_chunks,
                "format_dt": lambda ctx: discord.utils.format_dt,
                # Ty Lemon.
                "params": lambda ctx: params,
                "find_all": lambda ctx: find_all,
                "get_all": lambda ctx: get_all,
                # Dev Space
                "dev_space": lambda ctx: dev_space,
                "devspace": lambda ctx: dev_space,
                # Typing
                "typing": lambda ctx: typing,
                # Inspect
                "inspect": lambda ctx: inspect,
                "source": lambda ctx: lambda _object: rich.print(
                    textwrap.dedent(inspect.getsource(_object)).strip()
                ),
                "gs": lambda ctx: lambda _object: rich.print(
                    textwrap.dedent(inspect.getsource(_object)).strip()
                ),
                # "gs": lambda ctx: inspect.getsource,
                # logging
                "logging": lambda ctx: logging,
                # Date & Time
                "datetime": lambda ctx: datetime,
                "time": lambda ctx: time,
                "utc_now": lambda ctx: datetime.datetime.now(tz=datetime.timezone.utc),
                "local_now": lambda ctx: datetime.datetime.now(),
                "get_utc_now": lambda ctx: functools.partial(
                    datetime.datetime.now, tz=datetime.timezone.utc
                ),
                "get_local_now": lambda ctx: datetime.datetime.now,
                # Os & Sys
                "os": lambda ctx: os,
                "sys": lambda ctx: sys,
                # Aiohttp
                "aiohttp": lambda ctx: aiohttp,
                "session": lambda ctx: ctx.bot.get_cog("Dev")._session,
                "get_url": get_url,
                "BytesIO": lambda ctx: BytesIO,
                # TextWrap
                "textwrap": lambda ctx: textwrap,
                # Search attributes
                "search_attrs": lambda ctx: search_attribute,
                # search python library
                "where": lambda ctx: where,
                # `reference`
                "reference": reference,
                # No color (Dev cog from fluffy-cogs in mobile).
                # "_console_custom": _console_custom,
                # Dpy get
                "get_cog": lambda ctx: ctx.bot.get_cog,
                "get_command": lambda ctx: ctx.bot.get_command,
                "get_guild": lambda ctx: ctx.bot.get_guild,
                "get_channel": lambda ctx: ctx.guild.get_channel,
                "fetch_message": lambda ctx: ctx.channel.fetch_message,
                # Fake
                "token": lambda ctx: "[EXPUNGED]",
            }
        )
        if ctx is not None:
            _env = {}
            for name, value in env.items():
                try:
                    _env[name] = value(ctx)
                except Exception as exc:
                    traceback.clear_frames(exc.__traceback__)
                    _env[name] = exc
        else:
            _env = env
        return _env


class CogsCommands:
    class Cog(commands.Cog):
        def __init__(self, *args, **kwargs) -> None:
            super().__init__(*args, **kwargs)

        @classmethod
        def _setup(cls, bot: Red, Cog, Command, cog) -> typing.Any:  # typing_extensions.Self
            c = cls()
            c.__dict__ = cog.__dict__
            c.__cog_name__ = cog.__cog_name__
            c.bot = bot
            c.Cog = Cog
            c.Command = Command
            c.original_object = cog
            return c

        def __repr__(self) -> str:
            if getattr(self, "original_object", None) is not None:
                return repr(self.original_object)
            return super().__repr__()

        def __len__(self) -> int:
            cog = self
            source = {
                command.name: command
                for command in self.bot.all_commands.values()
                if getattr(command.cog, "qualified_name", None)
                == getattr(cog, "qualified_name", None)
            }
            return len(source)

        def __contains__(self, key: str) -> bool:
            cog = self
            source = {
                command.name: command
                for command in self.bot.all_commands.values()
                if getattr(command.cog, "qualified_name", None)
                == getattr(cog, "qualified_name", None)
            }
            return key in source

        def __iter__(self) -> typing.Iterator[typing.Tuple[str, typing.Any]]:
            cog = self
            source = {
                command.name: command
                for command in self.bot.all_commands.values()
                if getattr(command.cog, "qualified_name", None)
                == getattr(cog, "qualified_name", None)
            }
            _items = source
            items = {
                key: self.Command._setup(
                    bot=self.bot, Cog=self.Cog, Command=self.Command, command=value
                )
                for key, value in _items.items()
            }
            yield from items.items()

        def __getitem__(self, key: str) -> typing.Any:
            cog = self
            source = {
                command.name: command
                for command in self.bot.all_commands.values()
                if getattr(command.cog, "qualified_name", None)
                == getattr(cog, "qualified_name", None)
            }
            _item = source[key]
            return self.Command._setup(
                bot=self.bot, Cog=self.Cog, Command=self.Command, command=_item
            )

        def items(self):
            cog = self
            source = {
                command.name: command
                for command in self.bot.all_commands.values()
                if getattr(command.cog, "qualified_name", None)
                == getattr(cog, "qualified_name", None)
            }
            _items = source
            return {
                key: self.Command._setup(
                    bot=self.bot, Cog=self.Cog, Command=self.Command, command=value
                )
                for key, value in _items.items()
            }

        def keys(self):
            cog = self
            source = {
                command.name: command
                for command in self.bot.all_commands.values()
                if getattr(command.cog, "qualified_name", None)
                == getattr(cog, "qualified_name", None)
            }
            return source.keys()

        def values(self):
            cog = self
            source = {
                command.name: command
                for command in self.bot.all_commands.values()
                if getattr(command.cog, "qualified_name", None)
                == getattr(cog, "qualified_name", None)
            }
            _items = source
            items = {
                key: self.Command._setup(
                    bot=self.bot, Cog=self.Cog, Command=self.Command, command=value
                )
                for key, value in _items.items()
            }
            return items.values()

    class Command(commands.Command):
        def __init__(func, *args, **kwargs):
            super().__init__(func=func, *args, **kwargs)

        @classmethod
        def _setup(cls, bot: Red, Cog, Command, command) -> typing.Any:  # typing_extensions.Self
            c = cls(command.callback)
            c.__dict__ = command.__dict__
            c.bot = bot
            c.Cog = Cog
            c.Command = Command
            c.original_object = command
            return c

        def __repr__(self) -> str:
            if getattr(self, "original_object", None) is not None:
                return repr(self.original_object)
            return super().__repr__()

        def __eq__(self, other) -> bool:
            return (
                isinstance(other, commands.Command)
                and other.qualified_name == self.qualified_name
                and other.callback == self.callback
            )

        def __len__(self) -> int:
            command = self
            source = {
                c.name: c
                for c in self.bot.walk_commands()
                if getattr(c.parent, "qualified_name", None) == command.qualified_name
            }
            return len(source)

        def __contains__(self, key: str) -> bool:
            command = self
            source = {
                c.name: c
                for c in self.bot.walk_commands()
                if getattr(c.parent, "qualified_name", None) == command.qualified_name
            }
            return key in source

        def __iter__(self) -> typing.Iterator[typing.Tuple[str, typing.Any]]:
            command = self
            source = {
                c.name: c
                for c in self.bot.walk_commands()
                if getattr(c.parent, "qualified_name", None) == command.qualified_name
            }
            _items = source
            items = {
                key: self.Command._setup(
                    bot=self.bot, Cog=self.Cog, Command=self.Command, command=value
                )
                for key, value in _items.items()
            }
            yield from items.items()

        def __getitem__(self, key: str) -> typing.Any:
            command = self
            source = {
                c.name: c
                for c in self.bot.walk_commands()
                if getattr(c.parent, "qualified_name", None) == command.qualified_name
            }
            _item = source[key]
            return self.Command._setup(
                bot=self.bot, Cog=self.Cog, Command=self.Command, command=_item
            )

        def items(self):
            command = self
            source = {
                c.name: c
                for c in self.bot.walk_commands()
                if getattr(c.parent, "qualified_name", None) == command.qualified_name
            }
            _items = source
            return {
                key: self.Command._setup(
                    bot=self.bot, Cog=self.Cog, Command=self.Command, command=value
                )
                for key, value in _items.items()
            }

        def keys(self):
            command = self
            source = {
                c.name: c
                for c in self.bot.walk_commands()
                if getattr(c.parent, "qualified_name", None) == command.qualified_name
            }
            return source.keys()

        def values(self):
            command = self
            source = {
                c.name: c
                for c in self.bot.walk_commands()
                if getattr(c.parent, "qualified_name", None) == command.qualified_name
            }
            _items = source
            items = {
                key: self.Command._setup(
                    bot=self.bot, Cog=self.Cog, Command=self.Command, command=value
                )
                for key, value in _items.items()
            }
            return items.values()

    class Cogs:
        def __init__(self, bot: Red, Cog, Command) -> None:
            self.bot: Red = bot
            self.Cog = Cog
            self.Command = Command

        def __eq__(self, other: object) -> bool:
            return isinstance(self, self.__class__) and isinstance(other, self.__class__)

        def __len__(self) -> int:
            source = {cog.qualified_name: cog for cog in self.bot.cogs.values()}
            return len(source)

        def __contains__(self, key: str) -> bool:
            source = {cog.qualified_name: cog for cog in self.bot.cogs.values()}
            return key in source

        def __iter__(self) -> typing.Iterator[typing.Tuple[str, typing.Any]]:
            source = {cog.qualified_name: cog for cog in self.bot.cogs.values()}
            _items = source.items()
            yield from {
                key: self.Cog._setup(bot=self.bot, Cog=self.Cog, Command=self.Command, cog=value)
                for key, value in _items
            }

        def __getitem__(self, key: str) -> typing.Any:
            source = {cog.qualified_name: cog for cog in self.bot.cogs.values()}
            _item = source[key]
            return self.Cog._setup(bot=self.bot, Cog=self.Cog, Command=self.Command, cog=_item)

        def items(self):
            source = {cog.qualified_name: cog for cog in self.bot.cogs.values()}
            _items = source.items()
            return {
                key: self.Cog._setup(bot=self.bot, Cog=self.Cog, Command=self.Command, cog=value)
                for key, value in _items
            }

        def keys(self):
            source = {cog.qualified_name: cog for cog in self.bot.cogs.values()}
            return source.keys()

        def values(self):
            source = {cog.qualified_name: cog for cog in self.bot.cogs.values()}
            _items = source.items()
            items = {
                key: self.Cog._setup(bot=self.bot, Cog=self.Cog, Command=self.Command, cog=value)
                for key, value in _items
            }
            return items.values()

    class Commands:
        def __init__(self, bot: Red, Cog, Command) -> None:
            self.bot: Red = bot
            self.Cog = Cog
            self.Command = Command

        def __eq__(self, other: object) -> bool:
            return isinstance(self, self.__class__) and isinstance(other, self.__class__)

        def __len__(self) -> int:
            source = {command.name: command for command in self.bot.all_commands.values()}
            return len(source)

        def __contains__(self, key: str) -> bool:
            source = {command.name: command for command in self.bot.all_commands.values()}
            return key in source

        def __iter__(self) -> typing.Iterator[typing.Tuple[str, typing.Any]]:
            source = {command.name: command for command in self.bot.all_commands.values()}
            _items = source.items()
            yield from {
                key: self.Command._setup(
                    bot=self.bot, Cog=self.Cog, Command=self.Command, command=value
                )
                for key, value in _items.items()
            }

        def __getitem__(self, key: str) -> typing.Any:
            source = {command.name: command for command in self.bot.all_commands.values()}
            _item = source[key]
            return self.Command._setup(
                bot=self.bot, Cog=self.Cog, Command=self.Command, command=_item
            )

        def items(self):
            source = {command.name: command for command in self.bot.all_commands.values()}
            _items = source.items()
            return {
                key: self.Command._setup(
                    bot=self.bot, Cog=self.Cog, Command=self.Command, command=value
                )
                for key, value in _items.items()
            }

        def keys(self):
            source = {command.name: command for command in self.bot.all_commands.values()}
            return source.keys()

        def values(self):
            source = {command.name: command for command in self.bot.all_commands.values()}
            _items = source.items()
            items = {
                key: self.Command._setup(
                    bot=self.bot, Cog=self.Cog, Command=self.Command, command=value
                )
                for key, value in _items.items()
            }
            return items.values()

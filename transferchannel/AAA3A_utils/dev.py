from redbot.core import commands  # isort:skip
from redbot.core.bot import Red  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

# import typing_extensions  # isort:skip

import asyncio
import builtins
import datetime
import functools
import importlib
import inspect
import logging
import os
import re
import sys
import time
import traceback
from functools import partial
from io import StringIO

import aiohttp
import redbot
import rich
from redbot.core import Config
from redbot.core import utils as redutils
from redbot.core.utils import chat_formatting as cf
from redbot.core.utils.chat_formatting import box, pagify
from rich.console import Console
from rich.table import Table

from .cog import Cog
from .context import Context, is_dev
from .loop import Loop
from .menus import Menu, Reactions

try:
    from .sentry import SentryHelper
except ImportError:
    SentryHelper = None
from .settings import Settings
from .shared_cog import SharedCog

if discord.version_info.major >= 2:
    from .views import Buttons, ChannelSelect, Dropdown, MentionableSelect, Modal, RoleSelect, Select, UserSelect  # NOQA

CogsUtils: typing.Any = None

__all__ = ["DevSpace", "DevEnv"]


def _(untranslated: str) -> str:
    return untranslated


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
        if len(items) == 0:
            return f"<{self.__class__.__name__} [Nothing]>"
        return f"<{self.__class__.__name__} {' '.join(items)}>"

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
        self.imported: typing.List[str] = []

    @staticmethod
    def sanitize_output(ctx: commands.Context, input_: str) -> str:
        """Hides the bot's token from a string."""
        token = ctx.bot.http.token
        input_ = CogsUtils().replace_var_paths(input_)
        return re.sub(re.escape(token), "[EXPUNGED]", input_, re.I)

    @classmethod
    def get_env(
        cls, bot: Red, ctx: typing.Optional[commands.Context] = None
    ) -> typing.Dict[str, typing.Any]:
        log = CogsUtils().init_logger(name="Test")

        async def _rtfs(ctx: commands.Context, object):
            code = inspect.getsource(object)
            await Menu(pages=code, box_language_py=True).start(ctx)

        async def get_url(url: str, **kwargs):
            async with aiohttp.ClientSession() as session:
                async with session.get(url=url, **kwargs) as r:
                    return r

        def reference(ctx: commands.Context):
            if hasattr(ctx.message, "reference") and ctx.message.reference is not None:
                msg = ctx.message.reference.resolved
                if isinstance(msg, discord.Message):
                    return msg

        def _console_custom(ctx: commands.Context):
            return {"width": 80, "color_system": None}

        def get(a, b: typing.Optional[str] = "", startswith: typing.Optional[str] = ""):
            return [
                x
                for x in dir(a)
                if b.lower() in x.lower() and x.lower().startswith(startswith.lower())
            ]

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
        ):
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

        async def run_converter(
            converter: typing.Any, value: str, label: typing.Optional[str] = "test"
        ):
            if CogsUtils().is_dpy2:
                param = discord.ext.commands.parameters.Parameter(
                    name=label, kind=inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=converter
                )
                try:
                    return await discord.ext.commands.converter.run_converters(
                        ctx, converter=param.converter, argument=str(value), param=param
                    )
                except commands.CommandError as e:
                    return e
            else:
                param = inspect.Parameter(
                    name=label, kind=inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=converter
                )
                try:
                    return await ctx.command.do_conversion(
                        ctx, converter=converter, argument=str(value), param=param
                    )
                except commands.CommandError as e:
                    return e

        def get_devspace(bot: Red):
            Dev = bot.get_cog("Dev")
            if (
                "devspace" in getattr(Dev, "env_extensions", {})
                and hasattr(Dev.env_extensions["devspace"](bot), "__class__")
                and Dev.env_extensions["devspace"](bot).__class__.__name__ == "DevSpace"
            ):
                devspace = DevSpace(**Dev.env_extensions["devspace"](bot).__dict__)
                Dev.env_extensions["devspace"] = lambda ctx: devspace
                return lambda ctx: devspace
            devspace = DevSpace()
            if hasattr(Dev, "env_extensions"):
                Dev.env_extensions["devspace"] = lambda ctx: devspace
            return lambda ctx: devspace

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
            "log": lambda ctx: log,
            "_rtfs": lambda ctx: partial(_rtfs, ctx),
            "DevEnv": lambda ctx: cls,
            "DevSpace": lambda ctx: DevSpace,
            "devspace": get_devspace(bot),
            "Cogs": lambda ctx: CogsCommands.Cogs(
                bot=ctx.bot, Cog=CogsCommands.Cog, Command=CogsCommands.Command
            ),
            "Commands": lambda ctx: CogsCommands.Commands(
                bot=ctx.bot, Cog=CogsCommands.Cog, Command=CogsCommands.Command
            ),
        }
        if discord.version_info.major >= 2:
            env.update(
                {
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
                "Route": lambda ctx: discord.http.Route,
                "websocket": lambda ctx: ctx.bot._get_websocket(0),
                "get_internal": get_internal,
                "set_loggers_level": lambda ctx: set_loggers_level,
                # Typing
                "typing": lambda ctx: typing,
                # Inspect
                "inspect": lambda ctx: inspect,
                "gs": lambda ctx: inspect.getsource,
                # logging
                "logging": lambda ctx: logging,
                # Date & Time
                "datetime": lambda ctx: datetime,
                "time": lambda ctx: time,
                # Os & Sys
                "os": lambda ctx: os,
                "sys": lambda ctx: sys,
                # Aiohttp
                "session": lambda ctx: aiohttp.ClientSession(),
                "get_url": lambda ctx: get_url,
                # Search attr
                "get": lambda ctx: get,
                # `reference`
                "reference": reference,
                # No color (Dev cog from fluffy-cogs in mobile).
                "_console_custom": _console_custom,
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

    @classmethod
    def get_environment(cls, ctx: commands.Context) -> typing.Dict[str, typing.Any]:
        env = cls(  # In Dev cog from Zeph.
            **{
                "me": ctx.me,
                # redirect builtin console functions to rich
                "print": rich.print,
                "help": functools.partial(rich.inspect, help=True),
                # eval and exec automatically put this in, but types.FunctionType does not
                "__builtins__": builtins,
                # fill in various other environment keys that some code might expect
                "__builtin__": builtins,
                "__doc__": ctx.command.help,
                "__package__": None,
                "__loader__": None,
                "__spec__": None,
            }
        )
        Dev = ctx.bot.get_cog("Dev")
        base_env = redbot.core.dev_commands.Dev.get_environment(Dev, ctx)  # In Dev in Core.
        if not Dev.__class__ == redbot.core.dev_commands.Dev:
            del base_env["_"]
        env.update(base_env)
        env.update(cls.get_env(ctx.bot, ctx))  # In CogsUtils.
        env.update({"devenv": env})
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
                raw_table.add_row(str(name), str(value))
            else:
                raw_table.add_row(str(name))
        raw_table_str = no_colour_rich_markup(raw_table, lang="py")
        raw_table_str = self.sanitize_output(self.get("ctx", ctx), raw_table_str)
        pages = []
        for page in pagify(raw_table_str, page_length=2000 - 10):
            page = "\n".join(page.split("\n")[1:-1])
            pages.append(box(page, "py"))
        if ctx is not None:
            asyncio.create_task(Menu(pages=pages).start(ctx))
        return pages

    def get_formatted_imports(self) -> str:
        if not (imported := self.imported):
            return ""
        imported.sort()
        message = "".join(f">>> import {import_}\n" for import_ in imported)
        imported.clear()
        return message

    @classmethod
    def add_dev_env_values(
        cls, bot: Red, cog: commands.Cog, force: typing.Optional[bool] = False
    ) -> typing.Dict[str, typing.Any]:
        """
        If the bot owner is X, then add several values to the development environment, if they don't already exist.
        Even checks the id of the bot owner in the variable of my Sudo cog, if it's installed and loaded.
        """
        global CogsUtils
        CogsUtils = cog.cogsutils.__class__
        if cog.qualified_name == "AAA3A_utils":
            return
        if not (is_dev(bot) or force):
            return None
        _env = cls.get_env(bot)
        _env.update({cog.qualified_name: lambda ctx: cog})
        for name, value in _env.items():
            try:
                try:
                    bot.remove_dev_env_value(name)
                except KeyError:
                    pass
                bot.add_dev_env_value(name, value)
            except RuntimeError:
                pass
            except Exception as e:
                cog.log.error(
                    f"Error when adding the value `{name}` to the development environment.",
                    exc_info=e,
                )
        Dev = bot.get_cog("Dev")
        if Dev is not None:
            asyncio.create_task(cls().on_cog_add(Dev))
        RTFS = bot.get_cog("RTFS")
        if RTFS is not None:
            asyncio.create_task(cls().on_cog_add(RTFS))
        funcs = [
            i
            for i, func in enumerate(bot.extra_events.get("on_cog_add", []))
            if func.__class__.__name__ == "DevEnv"
        ]
        for func in funcs:
            del bot.extra_events.get("on_cog_add", [])[func]
        bot.add_listener(cls().on_cog_add)
        return _env

    @classmethod
    def remove_dev_env_values(
        cls, bot: Red, cog: commands.Cog, force: typing.Optional[bool] = False
    ) -> typing.Optional[typing.Dict[str, typing.Any]]:
        """
        If the bot owner is X, then remove several values to the development environment, if they don't already exist.
        Even checks the id of the bot owner in the variable of my Sudo cog, if it's installed and loaded.
        """
        if cog.qualified_name == "AAA3A_utils":
            return
        if not (is_dev(bot) or force):
            return None
        try:
            bot.remove_dev_env_value(cog.qualified_name)
        except Exception:
            pass
        if not cog.cogsutils.at_least_one_cog_loaded():
            _env = cls.get_env(bot)
            for name in _env:
                try:
                    bot.remove_dev_env_value(name)
                except Exception:
                    pass
            return _env

    @commands.Cog.listener()
    async def on_cog_add(self, cog: commands.Cog) -> None:
        if cog.qualified_name == "Dev":
            if hasattr(cog, "get_environment"):
                setattr(cog, "get_environment", self.get_environment)
            if hasattr(cog, "sanitize_output"):
                setattr(cog, "sanitize_output", self.sanitize_output)
            elif hasattr(redbot.core.dev_commands, "sanitize_output"):
                setattr(redbot.core.dev_commands, "sanitize_output", self.sanitize_output)
            c = Cog(None)
            c.cog = cog
            setattr(cog, "cog_before_invoke", c.cog_before_invoke)
            setattr(cog, "cog_after_invoke", c.cog_after_invoke)
        if cog.qualified_name == "RTFS":
            try:
                from rtfs import rtfs

                class SourceSource(rtfs.SourceSource):
                    def format_page(self, menu, page):
                        try:
                            if page is None:
                                if self.header.startswith("<"):
                                    return CogsUtils().replace_var_paths(self.header)
                                return {}
                            return CogsUtils().replace_var_paths(
                                f"{self.header}\n{box(page, lang='py')}\nPage {menu.current_page + 1} / {self.get_max_pages()}"
                            )
                        except Exception as e:
                            # since d.py menus likes to suppress all errors
                            rtfs.LOG.debug("Exception in SourceSource", exc_info=e)
                            raise

                setattr(rtfs, "SourceSource", SourceSource)
            except ImportError:
                pass

    def __missing__(self, key: str) -> typing.Any:
        if key in ("exit", "quit"):
            try:
                from dev.dev import Exit
            except ImportError:

                class Exit(BaseException):
                    pass

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
            if "bot" not in self:
                raise KeyError("bot")
            if cog := self["bot"].get_cog(key):
                return cog
        except (KeyError, AttributeError):
            pass
        if key.lower().startswith("id"):
            id = key[2:] if not key[2] == "_" else key[3:]
            try:
                id = int(id)
            except ValueError:
                pass
            else:
                try:
                    if "guild" not in self:
                        raise KeyError("guild")
                    if member := self["guild"].get_member(id):
                        return member
                except (KeyError, AttributeError):
                    pass
                try:
                    if "bot" not in self:
                        raise KeyError("bot")
                    if user := self["bot"].get_user(id):
                        return user
                except (KeyError, AttributeError):
                    pass
                try:
                    if "bot" not in self:
                        raise KeyError("bot")
                    if guild := self["bot"].get_guild(id):
                        return guild
                except (KeyError, AttributeError):
                    pass
                try:
                    if "guild" not in self:
                        raise KeyError("guild")
                    if channel := self["guild"].get_channel(id):
                        return channel
                except (KeyError, AttributeError):
                    pass
                try:
                    if "guild" not in self:
                        raise KeyError("guild")
                    if role := self["guild"].get_role(id):
                        return role
                except (KeyError, AttributeError):
                    pass
                try:
                    if "channel" not in self:
                        raise KeyError("channel")
                    if message := self["channel"].get_partial_message(id):
                        return message
                except (KeyError, AttributeError):
                    pass
        try:
            if "devspace" not in self:
                raise KeyError("devspace")
            if value := self["devspace"].get(key):
                return value
        except (KeyError, AttributeError):
            pass
        if attr := getattr(discord, key, None):
            self.imported.append(f"discord.{key}")
            return attr
        if attr := getattr(typing, key, None):
            self.imported.append(f"typing.{key}")
            return attr
        try:
            if "bot" not in self:
                raise KeyError("bot")
            if attr := getattr(self["bot"].get_cog("AAA3A_utils").cogsutils, key, None):
                self.imported.append(f"AAA3A_utils.cogsutils.CogsUtils.{key}")
                return attr
        except (KeyError, AttributeError):
            pass
        raise KeyError(key)


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
            items = {}
            for key, value in _items.items():
                items[key] = self.Command._setup(
                    bot=self.bot, Cog=self.Cog, Command=self.Command, command=value
                )
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
            item = self.Command._setup(
                bot=self.bot, Cog=self.Cog, Command=self.Command, command=_item
            )
            return item

        def items(self):
            cog = self
            source = {
                command.name: command
                for command in self.bot.all_commands.values()
                if getattr(command.cog, "qualified_name", None)
                == getattr(cog, "qualified_name", None)
            }
            _items = source
            items = {}
            for key, value in _items.items():
                items[key] = self.Command._setup(
                    bot=self.bot, Cog=self.Cog, Command=self.Command, command=value
                )
            return items

        def keys(self):
            cog = self
            source = {
                command.name: command
                for command in self.bot.all_commands.values()
                if getattr(command.cog, "qualified_name", None)
                == getattr(cog, "qualified_name", None)
            }
            keys = source.keys()
            return keys

        def values(self):
            cog = self
            source = {
                command.name: command
                for command in self.bot.all_commands.values()
                if getattr(command.cog, "qualified_name", None)
                == getattr(cog, "qualified_name", None)
            }
            _items = source
            items = {}
            for key, value in _items.items():
                items[key] = self.Command._setup(
                    bot=self.bot, Cog=self.Cog, Command=self.Command, command=value
                )
            values = items.values()
            return values

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
            items = {}
            for key, value in _items.items():
                items[key] = self.Command._setup(
                    bot=self.bot, Cog=self.Cog, Command=self.Command, command=value
                )
            yield from items.items()

        def __getitem__(self, key: str) -> typing.Any:
            command = self
            source = {
                c.name: c
                for c in self.bot.walk_commands()
                if getattr(c.parent, "qualified_name", None) == command.qualified_name
            }
            _item = source[key]
            item = self.Command._setup(
                bot=self.bot, Cog=self.Cog, Command=self.Command, command=_item
            )
            return item

        def items(self):
            command = self
            source = {
                c.name: c
                for c in self.bot.walk_commands()
                if getattr(c.parent, "qualified_name", None) == command.qualified_name
            }
            _items = source
            items = {}
            for key, value in _items.items():
                items[key] = self.Command._setup(
                    bot=self.bot, Cog=self.Cog, Command=self.Command, command=value
                )
            return items

        def keys(self):
            command = self
            source = {
                c.name: c
                for c in self.bot.walk_commands()
                if getattr(c.parent, "qualified_name", None) == command.qualified_name
            }
            keys = source.keys()
            return keys

        def values(self):
            command = self
            source = {
                c.name: c
                for c in self.bot.walk_commands()
                if getattr(c.parent, "qualified_name", None) == command.qualified_name
            }
            _items = source
            items = {}
            for key, value in _items.items():
                items[key] = self.Command._setup(
                    bot=self.bot, Cog=self.Cog, Command=self.Command, command=value
                )
            values = items.values()
            return values

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
            items = {}
            for key, value in _items:
                items[key] = self.Cog._setup(
                    bot=self.bot, Cog=self.Cog, Command=self.Command, cog=value
                )
            yield from items

        def __getitem__(self, key: str) -> typing.Any:
            source = {cog.qualified_name: cog for cog in self.bot.cogs.values()}
            _item = source[key]
            item = self.Cog._setup(bot=self.bot, Cog=self.Cog, Command=self.Command, cog=_item)
            return item

        def items(self):
            source = {cog.qualified_name: cog for cog in self.bot.cogs.values()}
            _items = source.items()
            items = {}
            for key, value in _items:
                items[key] = self.Cog._setup(
                    bot=self.bot, Cog=self.Cog, Command=self.Command, cog=value
                )
            return items

        def keys(self):
            source = {cog.qualified_name: cog for cog in self.bot.cogs.values()}
            keys = source.keys()
            return keys

        def values(self):
            source = {cog.qualified_name: cog for cog in self.bot.cogs.values()}
            _items = source.items()
            items = {}
            for key, value in _items:
                items[key] = self.Cog._setup(
                    bot=self.bot, Cog=self.Cog, Command=self.Command, cog=value
                )
            values = items.values()
            return values

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
            items = {}
            for key, value in _items.items():
                items[key] = self.Command._setup(
                    bot=self.bot, Cog=self.Cog, Command=self.Command, command=value
                )
            yield from items

        def __getitem__(self, key: str) -> typing.Any:
            source = {command.name: command for command in self.bot.all_commands.values()}
            _item = source[key]
            item = self.Command._setup(
                bot=self.bot, Cog=self.Cog, Command=self.Command, command=_item
            )
            return item

        def items(self):
            source = {command.name: command for command in self.bot.all_commands.values()}
            _items = source.items()
            items = {}
            for key, value in _items.items():
                items[key] = self.Command._setup(
                    bot=self.bot, Cog=self.Cog, Command=self.Command, command=value
                )
            return items

        def keys(self):
            source = {command.name: command for command in self.bot.all_commands.values()}
            keys = source.keys()
            return keys

        def values(self):
            source = {command.name: command for command in self.bot.all_commands.values()}
            _items = source.items()
            items = {}
            for key, value in _items.items():
                items[key] = self.Command._setup(
                    bot=self.bot, Cog=self.Cog, Command=self.Command, command=value
                )
            values = items.values()
            return values

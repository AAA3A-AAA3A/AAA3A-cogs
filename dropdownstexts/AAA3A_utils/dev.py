from redbot.core import commands  # isort:skip
from redbot.core.bot import Red  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import asyncio
import builtins
import datetime
import functools
import importlib
import inspect
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
from redbot.core import utils as redutils
from redbot.core.utils import chat_formatting as cf
from redbot.core.utils.chat_formatting import box, pagify
from rich.console import Console
from rich.table import Table

from .captcha import Captcha
from .cog import Cog
from .context import Context
from .loop import Loop
from .menus import Menu, Reactions
from .shared_cog import SharedCog

if discord.version_info.major >= 2:
    from .views import Buttons, Dropdown, Modal, Select

CogsUtils: typing.Any = None

__all__ = ["DevSpace", "DevEnv"]


def _(untranslated: str):
    return untranslated


def no_colour_rich_markup(*objects: typing.Any, lang: str = "") -> str:
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
    return box(temp_console.file.getvalue(), lang=lang)  # type: ignore


class DevSpace:
    def __init__(self, **kwargs):
        self.__dict__.update(**kwargs)

    def __repr__(self) -> str:
        items = [f"{k}={v!r}" for k, v in self.__dict__.items()]
        if items == []:
            return f"<{self.__class__.__name__} [Nothing]>"
        return f"<{self.__class__.__name__} {' '.join(items)}>"

    def __eq__(self, other: object) -> bool:
        if isinstance(self, DevSpace) and isinstance(other, DevSpace):
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

    def copy(self):
        return self.__class__(**self.__dict__)

    def items(self):
        return self.__dict__.items()

    def keys(self):
        return self.__dict__.keys()

    def values(self):
        return self.__dict__.values()

    def get(self, key: str, _default: typing.Optional[typing.Any] = None):
        return self.__dict__.get(key, _default)

    def pop(self, key: str, _default: typing.Optional[typing.Any] = None):
        return self.__dict__.pop(key, _default)

    def popitem(self):
        return self.__dict__.popitem()

    def _update_with_defaults(
        self, defaults: typing.Iterable[typing.Tuple[str, typing.Any]]
    ) -> None:
        for key, value in defaults:
            self.__dict__.setdefault(key, value)


class DevEnv(typing.Dict[str, typing.Any]):
    def __init__(self, *args, **kwargs):
        # self.__dict__ = {}
        super().__init__(*args, **kwargs)
        self.imported: typing.List[str] = []

    @classmethod
    def get_env(cls, bot: Red, ctx: typing.Optional[commands.Context] = None):
        log = CogsUtils().init_logger(name="Test")

        async def _rtfs(ctx: commands.Context, object):
            code = inspect.getsource(object)
            await Menu(
                pages=[box(page, "py") for page in pagify(code, page_length=2000 - 10)]
            ).start(ctx)

        def get_url(ctx: commands.Context):
            async def get_url_with_aiohttp(url: str, **kwargs):
                async with aiohttp.ClientSession() as session:
                    async with session.get(url=url, **kwargs) as r:
                        return r

            return get_url_with_aiohttp

        def get(ctx: commands.Context):
            def inner(a, b):
                return [x for x in dir(a) if b.lower() in x.lower()]

            return inner

        def reference(ctx: commands.Context):
            if hasattr(ctx.message, "reference") and ctx.message.reference is not None:
                msg = ctx.message.reference.resolved
                if isinstance(msg, discord.Message):
                    return msg

        def _console_custom(ctx: commands.Context):
            return {"width": 80, "color_system": None}

        async def run_converter(
            converter: typing.Any, value: str, label: typing.Optional[str] = "test"
        ):
            param = discord.ext.commands.parameters.Parameter(
                name=label, kind=inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=converter
            )
            try:
                return await discord.ext.commands.converter.run_converters(
                    ctx, converter=param.converter, argument=str(value), param=param
                )
            except discord.ext.commands.errors.CommandError as e:
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
            "Captcha": lambda ctx: Captcha,
            "Reactions": lambda ctx: Reactions,
            "Menu": lambda ctx: Menu,
            "SharedCog": lambda ctx: SharedCog,
            "Cog": lambda ctx: Cog,
            "Context": lambda ctx: Context,
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
                "run_converter": lambda ctx: run_converter,
                # Typing
                "typing": lambda ctx: typing,
                # Inspect
                "inspect": lambda ctx: inspect,
                "gs": lambda ctx: inspect.getsource,
                # Date & Time
                "datetime": lambda ctx: datetime,
                "time": lambda ctx: time,
                # Os & Sys
                "os": lambda ctx: os,
                "sys": lambda ctx: sys,
                # Aiohttp
                "session": lambda ctx: aiohttp.ClientSession(),
                "get_url": get_url,
                # Search attr
                "get": get,
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
                except Exception as e:
                    traceback.clear_frames(e.__traceback__)
                    _env[name] = e
        else:
            _env = env
        return _env

    @classmethod
    def get_environment(cls, ctx: commands.Context):
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
        # class HTTP():
        #     def __init__(self):
        #         self.token = "OTQ5OTg4NTk3NDYzOTE2NTU0.YiSX0w.gsylrfoyk51gxXhnCvdGVm8Jc6k"
        # class Red():
        #     def __init__(self):
        #         self.http = HTTP()
        # env.update({"bot": Red()})
        return env

    def get_formatted_env(
        self, ctx: typing.Optional[commands.Context] = None, value: typing.Optional[bool] = True
    ) -> str:
        if value:
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
            if value:
                raw_table.add_row(str(name), str(value))
            else:
                raw_table.add_row(str(name))
        raw_table_str = no_colour_rich_markup(raw_table, lang="py")
        raw_table_str = self.sanitize_output(ctx, raw_table_str)
        pages = []
        for page in pagify(raw_table_str, page_length=2000 - 10):
            page = "\n".join(page.split("\n")[1:-1])
            pages.append(box(page, "py"))
        if ctx is not None:
            asyncio.create_task(Menu(pages=pages).start(ctx))
        return pages

    @classmethod
    def add_dev_env_values(cls, bot: Red, cog: commands.Cog, force: typing.Optional[bool] = False):
        """
        If the bot owner is X, then add several values to the development environment, if they don't already exist.
        Even checks the id of the bot owner in the variable of my Sudo cog, if it's installed and loaded.
        """
        global CogsUtils
        CogsUtils = cog.cogsutils.__class__
        if cog.qualified_name == "AAA3A_utils":
            return
        Sudo = bot.get_cog("Sudo")
        if Sudo is None:
            owner_ids = bot.owner_ids
        else:
            if hasattr(Sudo, "all_owner_ids"):
                if len(Sudo.all_owner_ids) == 0:
                    owner_ids = bot.owner_ids
                else:
                    owner_ids = bot.owner_ids | Sudo.all_owner_ids
            else:
                owner_ids = bot.owner_ids
        if 829612600059887649 in owner_ids or force:
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
                setattr(Dev, "get_environment", cls.get_environment)
                setattr(Dev, "sanitize_output", cls.sanitize_output)
            RTFS = bot.get_cog("RTFS")
            if RTFS is not None:
                try:
                    from rtfs import rtfs

                    class SourceSource(rtfs.SourceSource):
                        def format_page(self, menu, page):
                            try:
                                if page is None:
                                    if self.header.startswith("<"):
                                        return cog.cogsutils.replace_var_paths(self.header)
                                    return {}
                                return cog.cogsutils.replace_var_paths(
                                    f"{self.header}\n{box(page, lang='py')}\nPage {menu.current_page + 1} / {self.get_max_pages()}"
                                )
                            except Exception as e:
                                # since d.py menus likes to suppress all errors
                                rtfs.LOG.debug("Exception in SourceSource", exc_info=e)
                                raise

                    setattr(rtfs, "SourceSource", SourceSource)
                except ImportError:
                    pass
            funcs = [
                func
                for func in bot.extra_events["on_cog_add"]
                if func.__class__.__name__ == "DevEnv"
            ]
            for func in funcs:
                del bot.extra_events["on_cog_add"][func]
            bot.add_listener(cls().on_cog_add)
            return _env

    @classmethod
    def remove_dev_env_values(
        cls, bot: Red, cog: commands.Cog, force: typing.Optional[bool] = False
    ):
        """
        If the bot owner is X, then remove several values to the development environment, if they don't already exist.
        Even checks the id of the bot owner in the variable of my Sudo cog, if it's installed and loaded.
        """
        if cog.qualified_name == "AAA3A_utils":
            return
        Sudo = bot.get_cog("Sudo")
        if Sudo is None:
            owner_ids = bot.owner_ids
        else:
            if hasattr(Sudo, "all_owner_ids"):
                if len(Sudo.all_owner_ids) == 0:
                    owner_ids = bot.owner_ids
                else:
                    owner_ids = bot.owner_ids | Sudo.all_owner_ids
            else:
                owner_ids = bot.owner_ids
        if 829612600059887649 in owner_ids or force:
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

    @staticmethod
    def sanitize_output(ctx: commands.Context, input_: str) -> str:
        """Hides the bot's token from a string."""
        token = ctx.bot.http.token
        input_ = CogsUtils().replace_var_paths(input_)
        return re.sub(re.escape(token), "[EXPUNGED]", input_, re.I)

    @commands.Cog.listener()
    async def on_cog_add(self, cog: commands.Cog):
        if cog.qualified_name == "Dev":
            if hasattr(cog, "get_environment"):
                setattr(cog, "get_environment", self.get_environment)
            if hasattr(cog, "sanitize_output"):
                setattr(cog, "sanitize_output", self.sanitize_output)
            return
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

    def __missing__(self, key: str):
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
            if cog := self["bot"].get_cog(key):
                return cog
        except (AttributeError, KeyError):
            pass
        if key.lower().startswith("id"):
            id = key[2:] if not key[2] == "_" else key[3:]
            try:
                id = int(id)
            except ValueError:
                pass
            else:
                try:
                    if member := self["guild"].get_member(id):
                        return member
                except (AttributeError, KeyError):
                    pass
                try:
                    if user := self["bot"].get_user(id):
                        return user
                except (AttributeError, KeyError):
                    pass
                try:
                    if guild := self["bot"].get_guild(id):
                        return guild
                except (AttributeError, KeyError):
                    pass
                try:
                    if channel := self["guild"].get_channel(id):
                        return channel
                except (AttributeError, KeyError):
                    pass
                try:
                    if role := self["guild"].get_role(id):
                        return role
                except (AttributeError, KeyError):
                    pass
                try:
                    if message := self["channel"].get_partial_message(id):
                        return message
                except (AttributeError, KeyError):
                    pass
        raise KeyError(key)

    def get_formatted_imports(self) -> str:
        if not (imported := self.imported):
            return ""
        imported.sort()
        message = "\n".join(f">>> import {import_}" for import_ in imported)
        imported.clear()
        return message


class CogsCommands:
    class Cog:
        def __init__(self, bot: Red, Cog, Command, cog: commands.Cog):
            self.bot = bot
            self.Cog = Cog
            self.Command = Command
            self.cog: commands.Cog = cog

        def _setup(self):
            for attr in [
                "__len__",
                "__contains__",
                "__iter__",
                "__getitem__",
                "items",
                "keys",
                "values",
            ]:
                if not hasattr(self, attr):
                    continue
                setattr(self.cog, attr, getattr(self, attr))

        def __len__(self) -> int:
            cog = self.cog
            source = {
                command.name: command.copy()
                for command in self.bot.all_commands.values()
                if getattr(command.cog, "qualified_name", None)
                == getattr(cog, "qualified_name", None)
            }
            return len(source)

        def __contains__(self, key: str) -> typing.Any:
            cog = self.cog
            source = {
                command.name: command.copy()
                for command in self.bot.all_commands.values()
                if getattr(command.cog, "qualified_name", None)
                == getattr(cog, "qualified_name", None)
            }
            return key in source

        def __iter__(self) -> typing.Iterator[typing.Tuple[str, typing.Any]]:
            cog = self.cog
            source = {
                command.name: command.copy()
                for command in self.bot.all_commands.values()
                if getattr(command.cog, "qualified_name", None)
                == getattr(cog, "qualified_name", None)
            }
            items = source
            for value in items.values():
                self.Command(
                    bot=self.bot, Cog=self.Cog, Command=self.Command, command=value
                )._setup()
            yield from items.items()

        def __getitem__(self, key: str) -> typing.Any:
            cog = self.cog
            source = {
                command.name: command.copy()
                for command in self.bot.all_commands.values()
                if getattr(command.cog, "qualified_name", None)
                == getattr(cog, "qualified_name", None)
            }
            item = source[key]
            self.Command(bot=self.bot, Cog=self.Cog, Command=self.Command, command=item)._setup()
            return item

        def items(self):
            cog = self.cog
            source = {
                command.name: command.copy()
                for command in self.bot.all_commands.values()
                if getattr(command.cog, "qualified_name", None)
                == getattr(cog, "qualified_name", None)
            }
            items = source
            for value in items.values():
                self.Command(
                    bot=self.bot, Cog=self.Cog, Command=self.Command, command=value
                )._setup()
            return items

        def keys(self):
            cog = self.cog
            source = {
                command.name: command.copy()
                for command in self.bot.all_commands.values()
                if getattr(command.cog, "qualified_name", None)
                == getattr(cog, "qualified_name", None)
            }
            keys = source.keys()
            return keys

        def values(self):
            cog = self.cog
            source = {
                command.name: command.copy()
                for command in self.bot.all_commands.values()
                if getattr(command.cog, "qualified_name", None)
                == getattr(cog, "qualified_name", None)
            }
            values = source.values()
            for value in values:
                self.Command(
                    bot=self.bot, Cog=self.Cog, Command=self.Command, command=value
                )._setup()
            return values

    class Command:
        def __init__(
            self, bot: Red, Cog, Command, command: typing.Union[commands.Command, commands.Group]
        ):
            self.bot = bot
            self.Cog = Cog
            self.Command = Command
            self.command: typing.Union[commands.Command, commands.Group] = command

        def _setup(self):
            for attr in [
                "__len__",
                "__contains__",
                "__iter__",
                "__getitem__",
                "items",
                "keys",
                "values",
            ]:
                if not hasattr(self, attr):
                    continue
                setattr(self.command, attr, getattr(self, attr))

        def __len__(self) -> int:
            command = self.command
            source = {
                c.name: c.copy()
                for c in self.bot.walk_commands()
                if getattr(c.parent, "qualified_name", None) == command.qualified_name
            }
            return len(source)

        def __contains__(self, key: str) -> typing.Any:
            command = self.command
            source = {
                c.name: c.copy()
                for c in self.bot.walk_commands()
                if getattr(c.parent, "qualified_name", None) == command.qualified_name
            }
            return key in source

        def __iter__(self) -> typing.Iterator[typing.Tuple[str, typing.Any]]:
            command = self.command
            source = {
                c.name: c.copy()
                for c in self.bot.walk_commands()
                if getattr(c.parent, "qualified_name", None) == command.qualified_name
            }
            items = source
            for value in items.values():
                self.Command(
                    bot=self.bot, Cog=self.Cog, Command=self.Command, command=value
                )._setup()
            yield from items.items()

        def __getitem__(self, key: str) -> typing.Any:
            command = self.command
            source = {
                c.name: c.copy()
                for c in self.bot.walk_commands()
                if getattr(c.parent, "qualified_name", None) == command.qualified_name
            }
            item = source[key]
            self.Command(bot=self.bot, Cog=self.Cog, Command=self.Command, command=item)._setup()
            return item

        def items(self):
            command = self.command
            source = {
                c.name: c.copy()
                for c in self.bot.walk_commands()
                if getattr(c.parent, "qualified_name", None) == command.qualified_name
            }
            items = source
            for value in items.values():
                self.Command(
                    bot=self.bot, Cog=self.Cog, Command=self.Command, command=value
                )._setup()
            return items

        def keys(self):
            command = self.command
            source = {
                c.name: c.copy()
                for c in self.bot.walk_commands()
                if getattr(c.parent, "qualified_name", None) == command.qualified_name
            }
            keys = source.keys()
            return keys

        def values(self):
            command = self.command
            source = {
                c.name: c.copy()
                for c in self.bot.walk_commands()
                if getattr(c.parent, "qualified_name", None) == command.qualified_name
            }
            values = source.values()
            for value in values:
                self.Command(
                    bot=self.bot, Cog=self.Cog, Command=self.Command, command=value
                )._setup()
            return values

    class Cogs:
        def __init__(self, bot: Red, Cog, Command):
            self.bot: Red = bot
            self.Cog = Cog
            self.Command = Command

        def __eq__(self, other: object) -> bool:
            return isinstance(self, self.__class__) and isinstance(other, self.__class__)

        def __len__(self) -> int:
            source = {cog.qualified_name: cog for cog in self.bot.cogs.values()}
            return len(source)

        def __contains__(self, key: str) -> typing.Any:
            source = {cog.qualified_name: cog for cog in self.bot.cogs.values()}
            return key in source

        def __iter__(self) -> typing.Iterator[typing.Tuple[str, typing.Any]]:
            source = {cog.qualified_name: cog for cog in self.bot.cogs.values()}
            items = source.items()
            for name, value in items:
                self.Cog(bot=self.bot, Cog=self.Cog, Command=self.Command, cog=value)._setup()
            yield from items

        def __getitem__(self, key: str) -> typing.Any:
            source = {cog.qualified_name: cog for cog in self.bot.cogs.values()}
            item = source[key]
            self.Cog(bot=self.bot, Cog=self.Cog, Command=self.Command, cog=item)._setup()
            return item

        def items(self):
            source = {cog.qualified_name: cog for cog in self.bot.cogs.values()}
            items = source.items()
            for name, value in items:
                self.Cog(bot=self.bot, Cog=self.Cog, Command=self.Command, cog=value)._setup()
            return items

        def keys(self):
            source = {cog.qualified_name: cog for cog in self.bot.cogs.values()}
            keys = source.keys()
            return keys

        def values(self):
            source = {cog.qualified_name: cog for cog in self.bot.cogs.values()}
            values = source.values()
            for value in values:
                self.Cog(bot=self.bot, Cog=self.Cog, Command=self.Command, cog=value)._setup()
            return values

    class Commands:
        def __init__(self, bot: Red, Cog, Command):
            self.bot: Red = bot
            self.Cog = Cog
            self.Command = Command

        def __eq__(self, other: object) -> bool:
            return isinstance(self, self.__class__) and isinstance(other, self.__class__)

        def __len__(self) -> int:
            source = {command.name: command.copy() for command in self.bot.all_commands.values()}
            return len(source)

        def __contains__(self, key: str) -> typing.Any:
            source = {command.name: command.copy() for command in self.bot.all_commands.values()}
            return key in source

        def __iter__(self) -> typing.Iterator[typing.Tuple[str, typing.Any]]:
            source = {command.name: command.copy() for command in self.bot.all_commands.values()}
            items = source.items()
            for name, value in items:
                self.Command(
                    bot=self.bot, Cog=self.Cog, Command=self.Command, command=value
                )._setup()
            yield from items

        def __getitem__(self, key: str) -> typing.Any:
            source = {command.name: command.copy() for command in self.bot.all_commands.values()}
            item = source[key]
            self.Command(bot=self.bot, Cog=self.Cog, Command=self.Command, command=item)._setup()
            return item

        def items(self):
            source = {command.name: command.copy() for command in self.bot.all_commands.values()}
            items = source.items()
            for name, value in items:
                self.Command(
                    bot=self.bot, Cog=self.Cog, Command=self.Command, command=value
                )._setup()
            return items

        def keys(self):
            source = {command.name: command.copy() for command in self.bot.all_commands.values()}
            keys = source.keys()
            return keys

        def values(self):
            source = {command.name: command.copy() for command in self.bot.all_commands.values()}
            values = source.values()
            for value in values:
                self.Command(
                    bot=self.bot, Cog=self.Cog, Command=self.Command, command=value
                )._setup()
            return values

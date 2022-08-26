from redbot.core import commands  # isort:skip
from redbot.core.bot import Red  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import asyncio
import contextlib
import datetime
import inspect
import logging
import os
import re
import string
import sys
import time
import traceback
from copy import copy
from io import StringIO
from pathlib import Path
from random import choice

import aiohttp
from functools import partial
from rich.console import Console

import redbot
from redbot.core.data_manager import cog_data_path
from redbot.core.utils.chat_formatting import box, humanize_list, inline, pagify
from redbot.core.utils.menus import start_adding_reactions
from redbot.logging import RotatingFileHandler
from redbot.core import utils as redutils
from redbot.core.utils import chat_formatting as cf

from .captcha import Captcha
from .loop import Loop
from .menus import Reactions, Menu
from .shared_cog import SharedCog
if discord.version_info.major >= 2:
    from .views import Buttons, Dropdown, Select, Modal

__all__ = ["CogsUtils", "Reactions", "Menu"]

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

class CogsUtils(commands.Cog):
    """Tools for AAA3A-cogs!"""

    def __init__(self, cog: typing.Optional[commands.Cog]=None, bot: typing.Optional[Red]=None):
        if cog is not None:
            if isinstance(cog, str):
                cog = bot.get_cog(cog)
            self.cog: commands.Cog = cog
            self.bot: Red = self.cog.bot if hasattr(self.cog, "bot") else bot
            self.DataPath: Path = cog_data_path(cog_instance=self.cog)
        elif bot is not None:
            self.cog: commands.Cog = None
            self.bot: Red = bot
        else:
            self.cog: commands.Cog = None
            self.bot: Red = None
        self.__authors__ = ["AAA3A"]
        self.__version__ = 1.0
        self.interactions = {"slash": [], "buttons": [], "dropdowns": [], "added": False, "removed": False}
        if self.cog is not None:
            if hasattr(self.cog, "__authors__"):
                if isinstance(self.cog.__authors__, typing.List):
                    self.__authors__ = self.cog.__authors__
                else:
                    self.__authors__ = [self.cog.__authors__]
                del self.cog.__authors__
            elif hasattr(self.cog, "__author__"):
                if isinstance(self.cog.__author__, typing.List):
                    self.__authors__ = self.cog.__author__
                else:
                    self.__authors__ = [self.cog.__author__]
                del self.cog.__author__
            self.cog.__authors__ = self.__authors__
            if hasattr(self.cog, "__version__"):
                if isinstance(self.cog.__version__, typing.List):
                    self.__version__ = self.cog.__version__
                del self.cog.__version__
            self.cog.__version__ = self.__version__
            self.interactions = {}
            if hasattr(self.cog, "interactions"):
                if isinstance(self.cog.interactions, typing.Dict):
                    self.interactions = self.cog.interactions
        self.loops: typing.Dict[str, Loop] = {}
        self.repo_name: str = "AAA3A-cogs"
        self.all_cogs: typing.List = [
                                        "AntiNuke",
                                        "AutoTraceback",
                                        "Calculator",
                                        "ClearChannel",
                                        "CmdChannel",
                                        "CtxVar",
                                        "DiscordModals",
                                        "DiscordSearch",
                                        "DropdownsTexts",
                                        "EditFile",
                                        "EditRole",
                                        "EditTextChannel",
                                        "EditVoiceChannel",
                                        "ExportChannel",
                                        "GetLoc",
                                        "Ip",
                                        "Medicat",  # Private cog, but public code.
                                        "MemberPrefix",
                                        "UrlButtons",
                                        "ReactToCommand",
                                        "RolesButtons",
                                        "Seen",
                                        "SimpleSanction",
                                        "Sudo",
                                        "TicketTool",
                                        "TransferChannel"
                                    ]
        self.all_cogs_dpy2: typing.List = [
                                        "AntiNuke",
                                        "AutoTraceback",
                                        "Calculator",
                                        "ClearChannel",
                                        "CmdChannel",
                                        "CtxVar",
                                        "DiscordModals",
                                        "DiscordSearch",
                                        "DropdownsTexts",
                                        "EditFile",
                                        "EditRole",
                                        "EditTextChannel",
                                        "EditVoiceChannel",
                                        "ExportChannel",
                                        "GetLoc",
                                        "Ip",
                                        "Medicat",  # Private cog, but public code.
                                        "MemberPrefix",
                                        "UrlButtons",
                                        "ReactToCommand",
                                        "RolesButtons",
                                        "Seen",
                                        "SimpleSanction",
                                        "Sudo",
                                        "TicketTool",
                                        "TransferChannel"
                                    ]
        if self.cog is not None:
            if self.cog.__class__.__name__ in self.all_cogs and self.cog.__class__.__name__ not in self.all_cogs_dpy2:
                if self.is_dpy2 or redbot.version_info >= redbot.VersionInfo.from_str("3.5.0"):
                    raise RuntimeError(f"{self.cog.__class__.__name__} needs to be updated to run on dpy2/Red 3.5.0. It's best to use `[p]cog update` with no arguments to update all your cogs, which may be using new dpy2-specific methods.")

    @property
    def is_dpy2(self) -> bool:
        """
        Returns True if the current redbot instance is running under dpy2.
        """
        return discord.version_info.major >= 2

    def format_help_for_context(self, ctx: commands.Context):
        """Thanks Simbad!"""
        context = super(type(self.cog), self.cog).format_help_for_context(ctx)
        s = "s" if len(self.__authors__) > 1 else ""
        return f"{context}\n\n**Author{s}**: {humanize_list(self.__authors__)}\n**Cog version**: {self.__version__}\n**Cog documentation**: https://aaa3a-cogs.readthedocs.io/en/latest/cog_{self.cog.__class__.__name__.lower()}.html\n**Translate my cogs**: https://crowdin.com/project/aaa3a-cogs"

    def format_text_for_context(self, ctx: commands.Context, text: str, shortdoc: typing.Optional[bool]=False):
        text = text.replace("        ", "")
        context = super(type(ctx.command), ctx.command).format_text_for_context(ctx, text)
        if shortdoc:
            return context
        s = "s" if len(self.__authors__) > 1 else ""
        return f"{context}\n\n**Author{s}**: {humanize_list(self.__authors__)}\n**Cog version**: {self.__version__}\n**Cog documentation**: https://aaa3a-cogs.readthedocs.io/en/latest/cog_{self.cog.__class__.__name__.lower()}.html\n**Translate my cogs**: https://crowdin.com/project/aaa3a-cogs"

    def format_shortdoc_for_context(self, ctx: commands.Context):
        sh = super(type(ctx.command), ctx.command).short_doc
        try:
            return super(type(ctx.command), ctx.command).format_text_for_context(ctx, sh, shortdoc=True) if sh else sh
        except Exception:
            return super(type(ctx.command), ctx.command).format_text_for_context(ctx, sh) if sh else sh

    async def red_delete_data_for_user(self, **kwargs):
        """Nothing to delete."""
        return

    async def red_get_data_for_user(self, *args, **kwargs) -> typing.Dict[typing.Any, typing.Any]:
        """Nothing to get."""
        return {}

    async def cog_unload_dpy2(self):
        self._end()

    def cog_unload_dpy1(self):
        self._end()

    async def cog_command_error(self, ctx: commands.Context, error: Exception):
        if self.cog is None:
            return
        if isinstance(error, commands.CommandInvokeError):
            asyncio.create_task(ctx.bot._delete_delay(ctx))
            self.cog.log.exception(f"Exception in command '{ctx.command.qualified_name}'.", exc_info=error.original)
            message = f"Error in command '{ctx.command.qualified_name}'. Check your console or logs for details.\nIf necessary, please inform the creator of the cog in which this command is located. Thank you."
            exception_log = f"Exception in command '{ctx.command.qualified_name}'.\n"
            exception_log += "".join(traceback.format_exception(type(error), error, error.__traceback__))
            exception_log = self.replace_var_paths(exception_log)
            ctx.bot._last_exception = exception_log
            await ctx.send(inline(message))
        else:
            await ctx.bot.on_command_error(ctx=ctx, error=error, unhandled_by_cog=True)

    def replace_var_paths(self, text: str, reverse: typing.Optional[bool]=False):
        if not reverse:
            if "USERPROFILE" in os.environ:
                text = text.replace(os.environ["USERPROFILE"], "{USERPROFILE}")
                text = text.replace(os.environ["USERPROFILE"].lower(), "{USERPROFILE}")
                text = text.replace(os.environ["USERPROFILE"].replace("\\", "\\\\"), "{USERPROFILE}")
                text = text.replace(os.environ["USERPROFILE"].replace("\\", "\\\\").lower(), "{USERPROFILE}")
            if "HOME" in os.environ:
                text = text.replace(os.environ["HOME"], "{HOME}")
                text = text.replace(os.environ["HOME"].lower(), "{HOME}")
                text = text.replace(os.environ["HOME"].replace("\\", "\\\\"), "{HOME}")
                text = text.replace(os.environ["HOME"].replace("\\", "\\\\").lower(), "{HOME}")
            if "USERNAME" in os.environ:
                text = text.replace(os.environ["USERNAME"], "{USERNAME}")
                text = text.replace(os.environ["USERNAME"].lower(), "{USERNAME}")
        else:
            if "USERPROFILE" in os.environ:
                text = text.replace("{USERPROFILE}", os.environ["USERPROFILE"])
                text = text.replace("{USERPROFILE}".lower(), os.environ["USERPROFILE"])
            if "HOME" in os.environ:
                text = text.replace("{HOME}", os.environ["HOME"])
                text = text.replace("{HOME}".lower(), os.environ["HOME"])
            if "USERNAME" in os.environ:
                text = text.replace("{USERNAME}", os.environ["USERNAME"])
                text = text.replace("{USERNAME}".lower(), os.environ["USERNAME"])
        return text

    @staticmethod
    def sanitize_output(ctx: commands.Context, input_: str) -> str:
        """Hides the bot's token from a string."""
        token = ctx.bot.http.token
        input_ = CogsUtils().replace_var_paths(input_)
        return re.sub(re.escape(token), "[EXPUNGED]", input_, re.I)

    async def add_cog(self, bot: Red, cog: commands.Cog):
        """
        Load a cog by checking whether the required function is awaitable or not.
        """
        value = bot.add_cog(cog)
        if inspect.isawaitable(value):
            cog = await value
        else:
            cog = value
        if hasattr(cog, "initialize"):
            await cog.initialize()
        return cog

    def _setup(self):
        """
        Adding additional functionality to the cog.
        """
        if self.cog is None:
            return
        self.cog.cogsutils = self
        self.init_logger()
        if self.cog.format_help_for_context.__func__ == commands.Cog.format_help_for_context:
            setattr(self.cog, 'format_help_for_context', self.format_help_for_context)
        # for command in self.cog.walk_commands():
        #     setattr(command, 'format_text_for_context', self.format_text_for_context)
        #     setattr(command, 'format_shortdoc_for_context', self.format_shortdoc_for_context)
        if self.cog.red_delete_data_for_user.__func__ == commands.Cog.red_delete_data_for_user:
            setattr(self.cog, 'red_delete_data_for_user', self.red_delete_data_for_user)
        if self.cog.red_get_data_for_user.__func__ == commands.Cog.red_get_data_for_user:
            setattr(self.cog, 'red_get_data_for_user', self.red_get_data_for_user)
        if self.cog.cog_unload.__func__ == commands.Cog.cog_unload:
            setattr(self.cog, 'cog_unload', self.cog_unload_dpy2 if self.is_dpy2 else self.cog_unload_dpy1)
        if self.cog.cog_command_error.__func__ == commands.Cog.cog_command_error:
            setattr(self.cog, 'cog_command_error', self.cog_command_error)
        asyncio.create_task(self._await_setup())

    async def _await_setup(self):
        """
        Adds dev environment values, slash commands add Views.
        """
        await self.bot.wait_until_red_ready()
        try:
            to_update, local_commit, online_commit = await self.to_update()
            if to_update:
                self.cog.log.warning(f"Your {self.cog.__class__.__name__} cog, from {self.repo_name}, is out of date. You can update your cogs with the 'cog update' command in Discord.")
            else:
                self.cog.log.debug(f"{self.cog.__class__.__name__} cog is up to date.")
        except (self.DownloaderNotLoaded, asyncio.TimeoutError, ValueError):
            pass
        except Exception as e:  # really doesn't matter if this fails so fine with debug level
            self.cog.log.debug(f"Something went wrong checking if {self.cog.__class__.__name__} cog is up to date.", exc_info=e)
        self.add_dev_env_values()
        # if self.is_dpy2:
        #     if not hasattr(self.bot, "tree"):
        #         self.bot.tree = discord.app_commands.CommandTree(self.bot)
        #     if not self.interactions == {}:
        #         if "added" in self.interactions:
        #             if not self.interactions["added"]:
        #                 if "slash" in self.interactions:
        #                     for slash in self.interactions["slash"]:
        #                         try:
        #                             self.bot.tree.add_command(slash, guild=None)
        #                         except Exception as e:
        #                             if hasattr(self.cog, "log"):
        #                                 self.cog.log.error(f"The slash command `{slash.name}` could not be added correctly.", exc_info=e)
        #                 if "button" in self.interactions:
        #                     for button in self.interactions["button"]:
        #                         try:
        #                             self.bot.add_view(button, guild=None)
        #                         except Exception:
        #                             pass
        #                 self.interactions["removed"] = False
        #                 self.interactions["added"] = True
        #             await self.bot.tree.sync(guild=None)
        if self.is_dpy2:
            await self.bot.remove_cog("AAA3A_utils")
        else:
            self.bot.remove_cog("AAA3A_utils")
        cog = SharedCog(self.bot, CogsUtils)
        await self.add_cog(bot=self.bot, cog=cog)

    def _end(self):
        """
        Removes dev environment values, slash commands add Views.
        """
        self.close_logger()
        self.remove_dev_env_values()
        for loop in self.loops:
            self.loops[loop].stop_all()
        asyncio.create_task(self._await_end())

    async def _await_end(self):
        # if self.is_dpy2:
        #     if not self.interactions == {}:
        #         if "removed" in self.interactions:
        #             if not self.interactions["removed"]:
        #                 if "slash" in self.interactions:
        #                     for slash in self.interactions["slash"]:
        #                         try:
        #                             self.bot.tree.remove_command(slash, guild=None)
        #                         except Exception as e:
        #                             if hasattr(self.cog, "log"):
        #                                 self.cog.log.error(f"The slash command `{slash.name}` could not be removed correctly.", exc_info=e)
        #                 if "button" in self.interactions:
        #                     for button in self.interactions["button"]:
        #                         try:
        #                             self.bot.remove_view(button, guild=None)
        #                         except Exception:
        #                             pass
        #                 self.interactions["added"] = False
        #                 self.interactions["removed"] = True
        #                 await asyncio.sleep(2)
        #                 await self.bot.tree.sync(guild=None)
        if not self.at_least_one_cog_loaded:
            if self.is_dpy2:
                await self.bot.remove_cog("AAA3A_utils")
            else:
                self.bot.remove_cog("AAA3A_utils")

    def init_logger(self, name: typing.Optional[str]=None):
        """
        Prepare the logger for the cog.
        Thanks to @laggron42 on GitHub! (https://github.com/laggron42/Laggron-utils/blob/master/laggron_utils/logging.py)
        """
        if name is None:
            self.cog.log = logging.getLogger(f"red.{self.repo_name}.{self.cog.__class__.__name__}")
            formatter = logging.Formatter(
                "[{asctime}] {levelname} [{name}] {message}", datefmt="%Y-%m-%d %H:%M:%S", style="{"
            )
            # logging to a log file
            # file is automatically created by the module, if the parent foler exists
            cog_path = cog_data_path(cog_instance=self.cog)
            if cog_path.exists():
                file_handler = RotatingFileHandler(
                    stem=self.cog.__class__.__name__,
                    directory=cog_path,
                    maxBytes=1_000_0,
                    backupCount=0,
                    encoding="utf-8",
                )
                # file_handler.doRollover()
                file_handler.setLevel(logging.DEBUG)
                file_handler.setFormatter(formatter)
                self.cog.log.addHandler(file_handler)
        else:
            return logging.getLogger(f"red.{self.repo_name}.{name}")

    def close_logger(self):
        """
        Closes the files for the logger of a cog.
        """
        for handler in self.cog.log.handlers:
            handler.close()
        self.cog.log.handlers = []

    async def to_update(self, cog_name: typing.Optional[str]=None):
        if cog_name is None:
            cog_name = self.cog.__class__.__name__
        cog_name = cog_name.lower()

        downloader = self.bot.get_cog("Downloader")
        if downloader is None:
            raise self.DownloaderNotLoaded(_("The cog downloader is not loaded.").format(**locals()))

        if await self.bot._cog_mgr.find_cog(cog_name) is None:
            raise ValueError(_("This cog was not found in any cog path."))

        local = discord.utils.get(await downloader.installed_cogs(), name=cog_name)
        if local is None:
            raise ValueError(_("This cog is not installed on this bot.").format(**locals()))
        local_commit = local.commit
        repo = local.repo
        if repo is None:
            raise ValueError(_("This cog has not been installed from the cog Downloader.").format(**locals()))

        repo_owner, repo_name, repo_branch = (re.compile(r"(?:https?:\/\/)?git(?:hub|lab).com\/(?P<repo_owner>[A-z0-9-_.]*)\/(?P<repo>[A-z0-9-_.]*)(?:\/tree\/(?P<repo_branch>[A-z0-9-_.]*))?", re.I).findall(repo.url))[0]
        repo_branch = repo.branch
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.github.com/repos/{repo_owner}/{repo_name}/git/refs/heads/{repo_branch}", timeout=3) as r:
                online = await r.json()
        if online is None or "object" not in online or "sha" not in online["object"]:
            raise asyncio.IncompleteReadError(_("No results could be retrieved from the git api.").format(**locals()), None)
        online_commit = online["object"]["sha"]

        return online_commit != local_commit, local_commit, online_commit

    def add_dev_env_values(self):
        """
        If the bot owner is X, then add several values to the development environment, if they don't already exist.
        Even checks the id of the bot owner in the variable of my Sudo cog, if it's installed and loaded.
        """
        Sudo = self.bot.get_cog("Sudo")
        if Sudo is None:
            owner_ids = self.bot.owner_ids
        else:
            if hasattr(Sudo, "all_owner_ids"):
                if len(Sudo.all_owner_ids) == 0:
                    owner_ids = self.bot.owner_ids
                else:
                    owner_ids = set(list(self.bot.owner_ids) + list(Sudo.all_owner_ids))
            else:
                owner_ids = self.bot.owner_ids
        if 829612600059887649 in owner_ids:
            async def _rtfs(ctx: commands.Context, object):
                code = inspect.getsource(object)
                await Menu(pages=[box(page, "py") for page in pagify(code, page_length=2000 - 10)]).start(ctx)
            def get_url(ctx: commands.Context):
                async def get_url_with_aiohttp(url: str, **kwargs):
                    async with aiohttp.ClientSession() as session:
                        async with session.get(url=url, **kwargs) as r:
                            return r
                return get_url_with_aiohttp
            def get(ctx: commands.Context):
                def inner(a, b):
                    return [x for x in dir(b) if a.lower() in x]
                return inner
            def reference(ctx: commands.Context):
                if hasattr(ctx.message, "reference") and ctx.message.reference is not None:
                    msg = ctx.message.reference.resolved
                    if isinstance(msg, discord.Message):
                        return msg
            def _console_custom(ctx: commands.Context):
                return {"width": 80, "color_system": None}
            if self.is_dpy2:
                to_add = {
                    # Cog
                    self.cog.__class__.__name__: lambda x: self.cog,
                    # CogsUtils
                    "CogsUtils": lambda ctx: CogsUtils,
                    "Loop": lambda ctx: Loop,
                    "Captcha": lambda ctx: Captcha,
                    "Buttons": lambda ctx: Buttons,
                    "Dropdown": lambda ctx: Dropdown,
                    "Select": lambda ctx: Select,
                    "Modal": lambda ctx: Modal,
                    "Reactions": lambda ctx: Reactions,
                    "Menu": lambda ctx: Menu,
                    "_rtfs": lambda ctx: partial(_rtfs, ctx),
                    # Dpy & Red
                    "discord": lambda ctx: discord,
                    "redbot": lambda ctx: redbot,
                    "Red": lambda ctx: Red,
                    "redutils": lambda ctx: redutils,
                    "cf": lambda ctx: cf,
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
                    "fetch_message": lambda ctx: ctx.channel.fetch_message
                }
            else:
                to_add = {
                    # Cog
                    self.cog.__class__.__name__: lambda x: self.cog,
                    # CogsUtils
                    "CogsUtils": lambda ctx: CogsUtils,
                    "Loop": lambda ctx: Loop,
                    "Captcha": lambda ctx: Captcha,
                    "Menu": lambda ctx: Menu,
                    "_rtfs": lambda ctx: partial(_rtfs, ctx),
                    # Dpy & Red
                    "discord": lambda ctx: discord,
                    "redbot": lambda ctx: redbot,
                    "Red": lambda ctx: Red,
                    "redutils": lambda ctx: redutils,
                    "cf": lambda ctx: cf,
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
                    "fetch_message": lambda ctx: ctx.channel.fetch_message
                }
            for name, value in to_add.items():
                try:
                    try:
                        self.bot.remove_dev_env_value(name)
                    except KeyError:
                        pass
                    self.bot.add_dev_env_value(name, value)
                except RuntimeError:
                    pass
                except Exception as e:
                    self.cog.log.error(f"Error when adding the value `{name}` to the development environment.", exc_info=e)
            Dev = self.bot.get_cog("Dev")
            if Dev is not None:
                setattr(Dev, 'sanitize_output', self.sanitize_output)
            RTFS = self.bot.get_cog("RTFS")
            if RTFS is not None:
                try:
                    from rtfs import rtfs
                    class SourceSource(rtfs.SourceSource):
                        def format_page(self, menu, page):
                            try:
                                if page is None:
                                    if self.header.startswith("<"):
                                        return CogsUtils().replace_var_paths(self.header)
                                    return {}
                                return CogsUtils().replace_var_paths(f"{self.header}\n{box(page, lang='py')}\nPage {menu.current_page + 1} / {self.get_max_pages()}")
                            except Exception as e:
                                # since d.py menus likes to suppress all errors
                                rtfs.LOG.debug("Exception in SourceSource", exc_info=e)
                                raise
                    setattr(rtfs, "SourceSource", SourceSource)
                except ImportError:
                    pass
            self.bot.remove_listener(self.on_cog_add)
            self.bot.add_listener(self.on_cog_add)
            return to_add

    def remove_dev_env_values(self):
        """
        If the bot owner is X, then remove several values to the development environment, if they don't already exist.
        Even checks the id of the bot owner in the variable of my Sudo cog, if it's installed and loaded.
        """
        Sudo = self.bot.get_cog("Sudo")
        if Sudo is None:
            owner_ids = self.bot.owner_ids
        else:
            if hasattr(Sudo, "all_owner_ids"):
                if len(Sudo.all_owner_ids) == 0:
                    owner_ids = self.bot.owner_ids
                else:
                    owner_ids = set(list(self.bot.owner_ids) + list(Sudo.all_owner_ids))
            else:
                owner_ids = self.bot.owner_ids
        if 829612600059887649 in owner_ids:
            async def _rtfs(ctx: commands.Context, object):
                code = inspect.getsource(object)
                await Menu(pages=[box(page, "py") for page in pagify(code, page_length=2000 - 10)]).start(ctx)
            try:
                self.bot.remove_dev_env_value(self.cog.__class__.__name__)
            except Exception:
                pass
            if not self.at_least_one_cog_loaded():
                def get_url(ctx: commands.Context):
                    async def get_url_with_aiohttp(url: str, **kwargs):
                        async with aiohttp.ClientSession() as session:
                            async with session.get(url=url, **kwargs) as r:
                                return r
                    return get_url_with_aiohttp
                def get(ctx: commands.Context):
                    def inner(a, b):
                        return [x for x in dir(b) if a.lower() in x]
                def reference(ctx: commands.Context):
                    if hasattr(ctx.message, "reference") and ctx.message.reference is not None:
                        msg = ctx.message.reference.resolved
                        if isinstance(msg, discord.Message):
                            return msg
                def _console_custom(ctx: commands.Context):
                    return {"width": 80, "color_system": None}
                if self.is_dpy2:
                    to_remove = {
                        # CogsUtils
                        "CogsUtils": lambda ctx: CogsUtils,
                        "Loop": lambda ctx: Loop,
                        "Captcha": lambda ctx: Captcha,
                        "Buttons": lambda ctx: Buttons,
                        "Dropdown": lambda ctx: Dropdown,
                        "Select": lambda ctx: Select,
                        "Modal": lambda ctx: Modal,
                        "Reactions": lambda ctx: Reactions,
                        "Menu": lambda ctx: Menu,
                        "_rtfs": lambda ctx: partial(_rtfs, ctx),
                        # Dpy & Red
                        "discord": lambda ctx: discord,
                        "redbot": lambda ctx: redbot,
                        "Red": lambda ctx: Red,
                        "redutils": lambda ctx: redutils,
                        "cf": lambda ctx: cf,
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
                        "fetch_message": lambda ctx: ctx.channel.fetch_message
                    }
                else:
                    to_remove = {
                        # CogsUtils
                        "CogsUtils": lambda ctx: CogsUtils,
                        "Loop": lambda ctx: Loop,
                        "Captcha": lambda ctx: Captcha,
                        "Menu": lambda ctx: Menu,
                        "_rtfs": lambda ctx: partial(_rtfs, ctx),
                        # Dpy & Red
                        "discord": lambda ctx: discord,
                        "redbot": lambda ctx: redbot,
                        "Red": lambda ctx: Red,
                        "redutils": lambda ctx: redutils,
                        "cf": lambda ctx: cf,
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
                        "fetch_message": lambda ctx: ctx.channel.fetch_message
                    }
                for name in to_remove:
                    try:
                        self.bot.remove_dev_env_value(name)
                    except Exception:
                        pass

    @commands.Cog.listener()
    async def on_cog_add(self, cog: commands.Cog):
        if cog.qualified_name == "Dev":
            if not hasattr(cog, "sanitize_output"):
                return
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
                            return CogsUtils().replace_var_paths(f"{self.header}\n{box(page, lang='py')}\nPage {menu.current_page + 1} / {self.get_max_pages()}")
                        except Exception as e:
                            # since d.py menus likes to suppress all errors
                            rtfs.LOG.debug("Exception in SourceSource", exc_info=e)
                            raise
                setattr(rtfs, "SourceSource", SourceSource)
            except ImportError:
                pass

    async def ConfirmationAsk(
            self,
            ctx: commands.Context,
            text: typing.Optional[str]=None,
            embed: typing.Optional[discord.Embed]=None,
            file: typing.Optional[discord.File]=None,
            timeout: typing.Optional[int]=60,
            timeout_message: typing.Optional[str]=_("Timed out, please try again").format(**locals()),
            way: typing.Optional[typing.Literal["buttons", "dropdown", "reactions", "message"]] = "buttons",
            message: typing.Optional[discord.Message]=None,
            put_reactions: typing.Optional[bool]=True,
            delete_message: typing.Optional[bool]=True,
            reactions: typing.Optional[typing.Iterable[typing.Union[str, discord.Emoji]]]=["✅", "❌"],
            check_owner: typing.Optional[bool]=True,
            members_authored: typing.Optional[typing.Iterable[discord.Member]]=[]):
        """
        Allow confirmation to be requested from the user, in the form of buttons/dropdown/reactions/message, with many additional options.
        """
        if (way == "buttons" or way == "dropdown") and not self.is_dpy2:
            way = "reactions"
        if message is None:
            if not text and not embed and not file:
                if way == "buttons":
                    text = _("To confirm the current action, please use the buttons below this message.").format(**locals())
                if way == "dropdown":
                    text = _("To confirm the current action, please use the dropdown below this message.").format(**locals())
                if way == "reactions":
                    text = _("To confirm the current action, please use the reactions below this message.").format(**locals())
                if way == "message":
                    text = _("To confirm the current action, please send yes/no in this channel.").format(**locals())
            if not way == "buttons" and not way == "dropdown":
                message = await ctx.send(content=text, embed=embed, file=file)
        if way == "reactions":
            if put_reactions:
                try:
                    start_adding_reactions(message, reactions)
                except discord.HTTPException:
                    way = "message"
        if way == "buttons":
            view = Buttons(timeout=timeout, buttons=[{"style": 3, "label": "Yes", "emoji": reactions[0], "custom_id": "ConfirmationAsk_Yes"}, {"style": 4, "label": "No", "emoji": reactions[1], "custom_id": "ConfirmationAsk_No"}], members=[ctx.author.id] + list(ctx.bot.owner_ids) if check_owner else [] + [x.id for x in members_authored])
            message = await ctx.send(content=text, embed=embed, file=file, view=view)
            try:
                interaction, function_result = await view.wait_result()
                if str(interaction.data["custom_id"]) == "ConfirmationAsk_Yes":
                    if delete_message:
                        await self.delete_message(message)
                    else:
                        view = Buttons(timeout=timeout, buttons=[{"style": 3, "label": "Yes", "emoji": reactions[0], "custom_id": "ConfirmationAsk_Yes", "disabled": True}, {"style": 4, "label": "No", "emoji": reactions[1], "custom_id": "ConfirmationAsk_No", "disabled": True}], members=[[ctx.author.id] + list(ctx.bot.owner_ids) if check_owner else [] + [x.id for x in members_authored]])
                        await interaction.response.edit_message(view=view)
                    return True
                elif str(interaction.data["custom_id"]) == "ConfirmationAsk_No":
                    if delete_message:
                        await self.delete_message(message)
                    else:
                        view = Buttons(timeout=timeout, buttons=[{"style": 3, "label": "Yes", "emoji": reactions[0], "custom_id": "ConfirmationAsk_Yes", "disabled": True}, {"style": 4, "label": "No", "emoji": reactions[1], "custom_id": "ConfirmationAsk_No", "disabled": True}], members=[[ctx.author.id] + list(ctx.bot.owner_ids) if check_owner else [] + [x.id for x in members_authored]])
                        await interaction.response.edit_message(view=view)
                    return False
            except TimeoutError:
                if delete_message:
                    await self.delete_message(message)
                else:
                    view = Buttons(timeout=timeout, buttons=[{"style": 3, "label": "Yes", "emoji": reactions[0], "custom_id": "ConfirmationAsk_Yes", "disabled": True}, {"style": 4, "label": "No", "emoji": reactions[1], "custom_id": "ConfirmationAsk_No", "disabled": True}], members=[[ctx.author.id] + list(ctx.bot.owner_ids) if check_owner else [] + [x.id for x in members_authored]])
                    await interaction.response.edit_message(view=view)
                if timeout_message is not None:
                    await ctx.send(timeout_message)
                return None
        if way == "dropdown":
            view = Dropdown(timeout=timeout, options=[{"label": "Yes", "emoji": reactions[0], "value": "ConfirmationAsk_Yes", "disabled": False}, {"label": "No", "emoji": reactions[1], "value": "ConfirmationAsk_No", "disabled": False}], disabled=False, members=[ctx.author.id] + list(ctx.bot.owner_ids) if check_owner else [] + [x.id for x in members_authored])
            message = await ctx.send(content=text, embed=embed, file=file, view=view)
            try:
                interaction, values, function_result = await view.wait_result()
                if str(values[0]) == "ConfirmationAsk_Yes":
                    if delete_message:
                        await self.delete_message(message)
                    else:
                        view = Dropdown(timeout=timeout, options=[{"label": "Yes", "emoji": reactions[0], "value": "ConfirmationAsk_Yes", "disabled": True}, {"label": "No", "emoji": reactions[1], "value": "ConfirmationAsk_No", "disabled": False}], disabled=True, members=[ctx.author.id] + list(ctx.bot.owner_ids) if check_owner else [] + [x.id for x in members_authored])
                        await interaction.response.edit_message(view=view)
                    return True
                elif str(values[0]) == "ConfirmationAsk_No":
                    if delete_message:
                        await self.delete_message(message)
                    else:
                        view = Dropdown(timeout=timeout, options=[{"label": "Yes", "emoji": reactions[0], "value": "ConfirmationAsk_Yes", "disabled": True}, {"label": "No", "emoji": reactions[1], "value": "ConfirmationAsk_No", "disabled": False}], disabled=True, members=[ctx.author.id] + list(ctx.bot.owner_ids) if check_owner else [] + [x.id for x in members_authored])
                        await interaction.response.edit_message(view=view)
                    return False
            except TimeoutError:
                if delete_message:
                    await self.delete_message(message)
                else:
                    view = Dropdown(timeout=timeout, options=[{"label": "Yes", "emoji": reactions[0], "value": "ConfirmationAsk_Yes", "disabled": True}, {"label": "No", "emoji": reactions[1], "value": "ConfirmationAsk_No", "disabled": False}], disabled=True, members=[ctx.author.id] + list(ctx.bot.owner_ids) if check_owner else [] + [x.id for x in members_authored])
                    await interaction.response.edit_message(view=view)
                if timeout_message is not None:
                    await ctx.send(timeout_message)
                return None
        if way == "reactions":
            view = Reactions(bot=ctx.bot, message=message, remove_reaction=False, timeout=timeout, reactions=reactions, members=[ctx.author.id] + list(ctx.bot.owner_ids) if check_owner else [] + [x.id for x in members_authored])
            try:
                reaction, user, function_result = await view.wait_result()
                if str(reaction.emoji) == reactions[0]:
                    end_reaction = True
                    if delete_message:
                        await self.delete_message(message)
                    return True
                elif str(reaction.emoji) == reactions[1]:
                    end_reaction = True
                    if delete_message:
                        await self.delete_message(message)
                    return False
            except TimeoutError:
                if delete_message:
                    await self.delete_message(message)
                if timeout_message is not None:
                    await ctx.send(timeout_message)
                return None
        if way == "message":
            def check(msg):
                if check_owner:
                    return msg.author.id == ctx.author.id or msg.author.id in ctx.bot.owner_ids or msg.author.id in [x.id for x in members_authored] and msg.channel == ctx.channel and msg.content in ("yes", "y", "no", "n")
                else:
                    return msg.author.id == ctx.author.id or msg.author.id in [x.id for x in members_authored] and msg.channel == ctx.channel and msg.content in ("yes", "y", "no", "n")
                # This makes sure nobody except the command sender can interact with the "menu"
            try:
                end_reaction = False
                msg = await ctx.bot.wait_for("message", timeout=timeout, check=check)
                # waiting for a a message to be sended - times out after x seconds
                if msg.content in ("yes", "y"):
                    end_reaction = True
                    if delete_message:
                        await self.delete_message(message)
                    await self.delete_message(msg)
                    return True
                elif msg.content in ("no", "n"):
                    end_reaction = True
                    if delete_message:
                        await self.delete_message(message)
                    await self.delete_message(msg)
                    return False
            except asyncio.TimeoutError:
                if not end_reaction:
                    if delete_message:
                        await self.delete_message(message)
                    if timeout_message is not None:
                        await ctx.send(timeout_message)
                    return None

    async def delete_message(self, message: discord.Message):
        """
        Delete a message, ignoring any exceptions.
        Easier than putting these 3 lines at each message deletion for each cog.
        """
        try:
            await message.delete()
        except discord.HTTPException:
            return False
        else:
            return True

    async def invoke_command(self, author: discord.User, channel: discord.TextChannel, command: str, prefix: typing.Optional[str]=None, message: typing.Optional[discord.Message]=None, dispatch_message: typing.Optional[bool]=False, message_id: typing.Optional[str]="".join(choice(string.digits) for i in range(18)), timestamp: typing.Optional[datetime.datetime]=datetime.datetime.now()) -> typing.Union[commands.Context, discord.Message]:
        """
        Invoke the specified command with the specified user in the specified channel.
        """
        bot = self.bot
        if prefix is None:
            prefixes = await bot.get_valid_prefixes(guild=channel.guild)
            prefix = prefixes[0] if len(prefixes) < 3 else prefixes[2]
        old_content = f"{command}"
        content = f"{prefix}{old_content}"

        if message is None:
            message_content = content
            author_dict = {"id": f"{author.id}", "username": author.display_name, "avatar": author.avatar, 'avatar_decoration': None, 'discriminator': f"{author.discriminator}", "public_flags": author.public_flags, "bot": author.bot}
            channel_id = channel.id
            timestamp = str(timestamp).replace(" ", "T") + "+00:00"
            data = {"id": message_id, "type": 0, "content": message_content, "channel_id": f"{channel_id}", "author": author_dict, "attachments": [], "embeds": [], "mentions": [], "mention_roles": [], "pinned": False, "mention_everyone": False, "tts": False, "timestamp": timestamp, "edited_timestamp": None, "flags": 0, "components": [], "referenced_message": None}
            message = discord.Message(channel=channel, state=bot._connection, data=data)
        else:
            message = copy(message)
            message.author = author

        message.content = content
        context = await bot.get_context(message)
        if context.valid:
            context.author = author
            context.guild = channel.guild
            context.channel = channel
            MemberPrefix = self.bot.get_cog("MemberPrefix")
            if MemberPrefix is not None:
                if hasattr(MemberPrefix, "cache_messages"):
                    MemberPrefix.cache_messages.append(message.id)
            await bot.invoke(context)
        else:
            if dispatch_message:
                message.content = old_content
                message.author = author
                message.channel = channel
                bot.dispatch("message", message)
        return context if context.valid else message

    async def get_hook(self, channel: discord.TextChannel):
        """
        Create a discord.Webhook object. It tries to retrieve an existing webhook created by the bot or to create it itself.
        """
        hook = None
        for webhook in await channel.webhooks():
            if webhook.user.id == self.bot.user.id:
                hook = webhook
                break
        if hook is None:
            hook = await channel.create_webhook(name="red_bot_hook_" + str(channel.id))
        return hook

    def get_embed(self, embed_dict: typing.Dict) -> typing.Dict[discord.Embed, str]:
        data = embed_dict
        if data.get("embed"):
            data = data["embed"]
        elif data.get("embeds"):
            data = data.get("embeds")[0]
        if timestamp := data.get("timestamp"):
            data["timestamp"] = timestamp.strip("Z")
        if data.get("content"):
            content = data["content"]
            del data["content"]
        else:
            content = ""
        for x in data:
            if data[x] is None:
                del data[x]
            elif isinstance(data[x], typing.Dict):
                for y in data[x]:
                    if data[x][y] is None:
                        del data[x][y]
        try:
            embed = discord.Embed.from_dict(data)
            length = len(embed)
            if length > 6000:
                raise commands.BadArgument(
                    f"Embed size exceeds Discord limit of 6000 characters ({length})."
                )
        except Exception as e:
            raise commands.BadArgument(
                f"An error has occurred.\n{e})."
            )
        back = {"embed": embed, "content": content}
        return back

    def datetime_to_timestamp(self, dt: datetime.datetime, format: typing.Literal["f", "F", "d", "D", "t", "T", "R"]="f") -> str:
        """
        Generate a Discord timestamp from a datetime object.
        <t:TIMESTAMP:FORMAT>
        Parameters
        ----------
        dt : datetime.datetime
            The datetime object to use
        format : TimestampFormat, by default `f`
            The format to pass to Discord.
            - `f` short date time | `18 June 2021 02:50`
            - `F` long date time  | `Friday, 18 June 2021 02:50`
            - `d` short date      | `18/06/2021`
            - `D` long date       | `18 June 2021`
            - `t` short time      | `02:50`
            - `T` long time       | `02:50:15`
            - `R` relative time   | `8 days ago`
        Returns
        -------
        str
            Formatted timestamp
        Thanks to vexutils from Vexed01 in GitHub! (https://github.com/Vexed01/Vex-Cogs/blob/master/timechannel/vexutils/chat.py)
        """
        t = str(int(dt.timestamp()))
        return f"<t:{t}:{format}>"

    def check_permissions_for(self, channel: typing.Union[discord.TextChannel, discord.VoiceChannel, discord.DMChannel], user: discord.User, check: typing.Union[typing.List, typing.Dict]):
        """
        Check all permissions specified as an argument.
        """
        if getattr(channel, "guild", None) is None:
            return True
        permissions = channel.permissions_for(user)
        if isinstance(check, typing.List):
            new_check = {}
            for p in check:
                new_check[p] = True
            check = new_check
        for p in check:
            if getattr(permissions, f"{p}", None):
                if check[p]:
                    if not getattr(permissions, f"{p}"):
                        return False
                else:
                    if getattr(permissions, f"{p}"):
                        return False
        return True

    def create_loop(self, function, name: typing.Optional[str]=None, days: typing.Optional[int]=0, hours: typing.Optional[int]=0, minutes: typing.Optional[int]=0, seconds: typing.Optional[int]=0, function_args: typing.Optional[typing.Dict]={}, wait_raw: typing.Optional[bool]=False, limit_count: typing.Optional[int]=None, limit_date: typing.Optional[datetime.datetime]=None, limit_exception: typing.Optional[int]=None):
        """
        Create a loop like Loop, but with default values and loop object recording functionality.
        """
        if name is None:
            name = f"{self.cog.__class__.__name__}"
        if datetime.timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds).total_seconds() == 0:
            seconds = 900  # 15 minutes
        loop = Loop(cogsutils=self, name=name, function=function, days=days, hours=hours, minutes=minutes, seconds=seconds, function_args=function_args, wait_raw=wait_raw, limit_count=limit_count, limit_date=limit_date, limit_exception=limit_exception)
        if f"{loop.name}" in self.loops:
            self.loops[f"{loop.name}"].stop_all()
        self.loops[f"{loop.name}"] = loop
        return loop

    async def captcha(self, member: discord.Member, channel: discord.TextChannel, limit: typing.Optional[int]=3, timeout: typing.Optional[int]=60, why: typing.Optional[str]=""):
        """
        Create a Captcha challenge like Captcha, but with default values.
        """
        return await Captcha(cogsutils=self, member=member, channel=channel, limit=limit, timeout=timeout, why=why).realize_challenge()

    def get_all_repo_cogs_objects(self):
        """
        Get a dictionary containing the objects or None of all my cogs.
        """
        cogs = {}
        for cog in self.all_cogs:
            object = self.bot.get_cog(f"{cog}")
            if object is not None:
                cogs[f"{cog}"] = object if hasattr(object, "cogsutils") else None
            else:
                cogs[f"{cog}"] = None
        for cog in self.bot.cogs.values():
            if hasattr(cog, "cogsutils"):
                if getattr(cog.cogsutils, "repo_name", None) == "AAA3A-cogs":
                    if f"{cog.__class__.__name__}" not in cogs or cogs[f"{cog.__class__.__name__}"] is None:
                        cogs[f"{cog.__class__.__name__}"] = cog
        return cogs

    def at_least_one_cog_loaded(self):
        """
        Return True if at least one cog of all my cogs is loaded.
        """
        at_least_one_cog_loaded = False
        for object in self.get_all_repo_cogs_objects().values():
            if object is not None:
                at_least_one_cog_loaded = True
                break
        return at_least_one_cog_loaded

    def add_all_dev_env_values(self):
        """
        Add values to the development environment for all my loaded cogs. Not really useful anymore, now that my cogs use AAA3A_utils.
        """
        cogs = self.get_all_repo_cogs_objects()
        for cog in cogs:
            if cogs[cog] is not None:
                try:
                    CogsUtils(cog=cogs[cog]).add_dev_env_value()
                except Exception:
                    pass

    def class_instance_to_dict(self, instance):
        """
        Convert a class instance into a dictionary, while using ids for all sub-attributes.
        """
        original_dict = instance.__dict__
        new_dict = self.to_id(original_dict)
        return new_dict

    def to_id(self, original_dict: typing.Dict):
        """
        Return a dict with ids for all sub-attributes
        """
        new_dict = {}
        for e in original_dict:
            if isinstance(original_dict[e], typing.Dict):
                new_dict[e] = self.to_id(original_dict[e])
            elif hasattr(original_dict[e], "id"):
                new_dict[e] = int(original_dict[e].id)
            elif isinstance(original_dict[e], datetime.datetime):
                new_dict[e] = float(datetime.datetime.timestamp(original_dict[e]))
            else:
                new_dict[e] = original_dict[e]
        return new_dict

    def generate_key(self, number: typing.Optional[int]=10, existing_keys: typing.Optional[typing.Union[typing.List, typing.Set]]=[], strings_used: typing.Optional[typing.List]={"ascii_lowercase": True, "ascii_uppercase": False, "digits": True, "punctuation": False, "others": []}):
        """
        Generate a secret key, with the choice of characters, the number of characters and a list of existing keys.
        """
        strings = []
        if "ascii_lowercase" in strings_used:
            if strings_used["ascii_lowercase"]:
                strings += string.ascii_lowercase
        if "ascii_uppercase" in strings_used:
            if strings_used["ascii_uppercase"]:
                strings += string.ascii_uppercase
        if "digits" in strings_used:
            if strings_used["digits"]:
                strings += string.digits
        if "punctuation" in strings_used:
            if strings_used["punctuation"]:
                strings += string.punctuation
        if "others" in strings_used:
            if isinstance(strings_used["others"], typing.List):
                strings += strings_used["others"]
        while True:
            # This probably won't turn into an endless loop.
            key = "".join(choice(strings) for x in range(number))
            if key not in existing_keys:
                return key

    def await_function(self, function, function_args: typing.Optional[typing.Dict]={}):
        """
        Allow to use an asynchronous function, from a non-asynchronous function.
        """
        task = asyncio.create_task(self.do_await_function(function=function, function_args=function_args))
        return task

    async def do_await_function(self, function, function_args: typing.Optional[typing.Dict]={}):
        try:
            await function(**function_args)
        except Exception as e:
            if hasattr(self.cogsutils.cog, "log"):
                self.cog.log.error(f"An error occurred with the {function.__name__} function.", exc_info=e)

    async def check_in_listener(self, output, allowed_by_whitelist_blacklist: typing.Optional[bool]=True):
        """
        Check all parameters for the output of any listener.
        Thanks to Jack! (https://discord.com/channels/133049272517001216/160386989819035648/825373605000511518)
        """
        if isinstance(output, discord.Message):
            # check whether the message was sent in a guild
            if output.guild is None:
                raise discord.ext.commands.BadArgument()
            # check whether the message author isn't a bot
            if output.author is None:
                raise discord.ext.commands.BadArgument()
            if output.author.bot:
                raise discord.ext.commands.BadArgument()
            # check whether the bot can send message in the given channel
            if output.channel is None:
                raise discord.ext.commands.BadArgument()
            if not self.check_permissions_for(channel=output.channel, user=output.guild.me, check=["send_messages"]):
                raise discord.ext.commands.BadArgument()
            # check whether the cog isn't disabled
            if self.cog is not None:
                if await self.bot.cog_disabled_in_guild(self.cog, output.guild):
                    raise discord.ext.commands.BadArgument()
            # check whether the channel isn't on the ignore list
            if not await self.bot.ignored_channel_or_guild(output):
                raise discord.ext.commands.BadArgument()
            # check whether the message author isn't on allowlist/blocklist
            if allowed_by_whitelist_blacklist:
                if not await self.bot.allowed_by_whitelist_blacklist(output.author):
                    raise discord.ext.commands.BadArgument()
        if isinstance(output, discord.RawReactionActionEvent):
            # check whether the message was sent in a guild
            output.guild = self.bot.get_guild(output.guild_id)
            if output.guild is None:
                raise discord.ext.commands.BadArgument()
            # check whether the message author isn't a bot
            output.author = output.guild.get_member(output.user_id)
            if output.author is None:
                raise discord.ext.commands.BadArgument()
            if output.author.bot:
                raise discord.ext.commands.BadArgument()
            # check whether the bot can send message in the given channel
            output.channel = output.guild.get_channel(output.channel_id)
            if output.channel is None:
                raise discord.ext.commands.BadArgument()
            if not self.check_permissions_for(channel=output.channel, user=output.guild.me, check=["send_messages"]):
                raise discord.ext.commands.BadArgument()
            # check whether the cog isn't disabled
            if self.cog is not None:
                if await self.bot.cog_disabled_in_guild(self.cog, output.guild):
                    raise discord.ext.commands.BadArgument()
            # check whether the channel isn't on the ignore list
            if not await self.bot.ignored_channel_or_guild(output):
                raise discord.ext.commands.BadArgument()
            # check whether the message author isn't on allowlist/blocklist
            if allowed_by_whitelist_blacklist:
                if not await self.bot.allowed_by_whitelist_blacklist(output.author):
                    raise discord.ext.commands.BadArgument()
        if self.is_dpy2:
            if isinstance(output, discord.Interaction):
                # check whether the message was sent in a guild
                if output.guild is None:
                    raise discord.ext.commands.BadArgument()
                # check whether the message author isn't a bot
                if output.author is None:
                    raise discord.ext.commands.BadArgument()
                if output.author.bot:
                    raise discord.ext.commands.BadArgument()
                # check whether the bot can send message in the given channel
                if output.channel is None:
                    raise discord.ext.commands.BadArgument()
                if not self.check_permissions_for(channel=output.channel, user=output.guild.me, check=["send_messages"]):
                    raise discord.ext.commands.BadArgument()
                # check whether the cog isn't disabled
                if self.cog is not None:
                    if await self.bot.cog_disabled_in_guild(self.cog, output.guild):
                        raise discord.ext.commands.BadArgument()
                # check whether the message author isn't on allowlist/blocklist
                if allowed_by_whitelist_blacklist:
                    if not await self.bot.allowed_by_whitelist_blacklist(output.author):
                        raise discord.ext.commands.BadArgument()
        return

    async def get_new_Config_with_modal(self, ctx: commands.Context, config: typing.Dict, all_config: typing.Optional[typing.Dict]={}, bypass_confirm: typing.Optional[bool]=False):
        # {"x": {"default": "", "value": "", "style": 1, "converter": None}, "all_config": {}}
        for input in config:
            config[input]["param"] = discord.ext.commands.parameters.Parameter(name=input, kind=inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=config[input]["converter"])
        new_config = {}
        view_button = Buttons(timeout=180, buttons=[{"label": "Configure", "emoji": "⚙️", "disabled": False}], members=[ctx.author.id])
        message = await ctx.send(_("Click on the buttons below to fully set up the cog {self.cog.__class__.__name__}.").format(**locals()), view=view_button)
        try:
            interaction, function_result = await view_button.wait_result()
        except TimeoutError:
            await message.edit(view=Buttons(timeout=None, buttons=[{"label": "Configure", "emoji": "⚙️", "disabled": True}]))
            return None
        view_modal = Modal(title=f"{self.cog.__class__.__name__} Config", inputs=[{"label": (input.replace("_", " ").capitalize() + " (" + (('|'.join(f'"{v}"' if isinstance(v, str) else str(v) for v in config[input]["param"].converter.__args__)) if config[input]["param"].converter is typing.Literal else getattr(config[input]["param"].converter, "__name__", "")) + ")")[:44], "style": config[input]["style"], "placeholder": str(config[input]["default"]), "default": (str(config[input]["value"]) if not str(config[input]["value"]) == str(config[input]["default"]) else None), "required": False, "custom_id": f"CogsUtils_ModalConfig_{input}"} for input in config], custom_id=f"CogsUtils_ModalConfig_{self.cog.__class__.__name__}")
        await interaction.response.send_modal(view_modal)
        try:
            interaction, inputs, function_result = await view_modal.wait_result()
        except TimeoutError:
            return None
        async with ctx.typing():
            for input in inputs:
                custom_id = input.custom_id.replace("CogsUtils_ModalConfig_", "")
                if input.value == "":
                    new_config[input.custom_id.replace("CogsUtils_ModalConfig_", "")] = config[custom_id]["default"]
                    continue
                try:
                    value = await discord.ext.commands.converter.run_converters(ctx, converter=config[custom_id]["param"].converter, argument=str(input.value), param=config[custom_id]["param"])
                except discord.ext.commands.errors.CommandError as e:
                    await ctx.send(f"An error occurred when using the `{input.label}` converter:\n{box(e)}")
                    return
                new_config[custom_id] = value
            for key, value in all_config.items():
                if key not in new_config:
                    new_config[key] = value
        await message.delete()
        if not bypass_confirm:
            embed: discord.Embed = discord.Embed()
            embed.title = _("⚙️ Do you want to replace the entire Config of {self.cog.__class__.__name__} with what you specified?").format(**locals())
            if not await self.ConfirmationAsk(ctx, embed=embed):
                return None
        return new_config

    async def autodestruction(self):
        """
        Cog self-destruct.
        Will of course never be used, just a test.
        """
        downloader = self.bot.get_cog("Downloader")
        if downloader is not None:
            poss_installed_path = (await downloader.cog_install_path()) / self.cog.__class__.__name__.lower()
            if poss_installed_path.exists():
                with contextlib.suppress(commands.ExtensionNotLoaded):
                    self.bot.unload_extension(self.cog.__class__.__name__.lower())
                    await self.bot.remove_loaded_package(self.cog.__class__.__name__.lower())
                await downloader._delete_cog(poss_installed_path)
            await downloader._remove_from_installed([discord.utils.get(await downloader.installed_cogs(), name=self.cog.__class__.__name__.lower())])
        else:
            raise self.DownloaderNotLoaded(_("The cog downloader is not loaded.").format(**locals()))

    class DownloaderNotLoaded(Exception):
        pass
from redbot.core import commands  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import asyncio
import contextlib
import datetime
import inspect
import logging
import math
import os
import platform
import re
import string
import sys
import traceback
from copy import copy
from io import StringIO
from pathlib import Path
from random import choice
from time import monotonic

import aiohttp
import pip
from rich.console import Console
from rich.table import Table

import redbot
from redbot import version_info as red_version_info
from redbot.cogs.downloader.converters import InstalledCog
from redbot.cogs.downloader.repo_manager import Repo
from redbot.core._diagnoser import IssueDiagnoser
from redbot.core.bot import Red
from redbot.core.data_manager import basic_config, cog_data_path, config_file, instance_name, storage_type
from redbot.core.utils.chat_formatting import bold, box, error, humanize_list, humanize_timedelta, inline, pagify, text_to_file, warning
from redbot.core.utils.menus import start_adding_reactions, menu
from redbot.core.utils.predicates import MessagePredicate, ReactionPredicate
from redbot.logging import RotatingFileHandler
from redbot.vendored.discord.ext import menus

__all__ = ["CogsUtils", "Loop", "Captcha", "Buttons", "Dropdown", "Modal", "Reactions"]

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
            if hasattr(self.cog, "__func_red__"):
                if not isinstance(self.cog.__func_red__, typing.List):
                    self.cog.__func_red__ = []
            else:
                self.cog.__func_red__ = []
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
        return f"{context}\n\n**Author{s}**: {humanize_list(self.__authors__)}\n**Version**: {self.__version__}"

    def format_text_for_context(self, ctx: commands.Context, text: str, shortdoc: typing.Optional[bool]=False):
        text = text.replace("        ", "")
        context = super(type(ctx.command), ctx.command).format_text_for_context(ctx, text)
        if shortdoc:
            return context
        s = "s" if len(self.__authors__) > 1 else ""
        return f"{context}\n\n**Author{s}**: {humanize_list(self.__authors__)}\n**Version**: {self.__version__}"

    def format_shortdoc_for_context(self, ctx: commands.Context):
        sh = super(type(ctx.command), ctx.command).short_doc
        try:
            return super(type(ctx.command), ctx.command).format_text_for_context(ctx, sh, shortdoc=True) if sh else sh
        except Exception:
            return super(type(ctx.command), ctx.command).format_text_for_context(ctx, sh) if sh else sh

    async def red_delete_data_for_user(self, **kwargs):
        """Nothing to delete"""
        return

    async def red_get_data_for_user(self, *args, **kwargs) -> typing.Dict[typing.Any, typing.Any]:
        return {}

    def cog_unload(self):
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
            if "HOME" in os.environ:
                text = text.replace(os.environ["HOME"], "{HOME}")
                text = text.replace(os.environ["HOME"].lower(), "{HOME}")
        else:
            if "USERPROFILE" in os.environ:
                text = text.replace("{USERPROFILE}", os.environ["USERPROFILE"])
                text = text.replace("{USERPROFILE}".lower(), os.environ["USERPROFILE"])
            if "HOME" in os.environ:
                text = text.replace("{HOME}", os.environ["HOME"])
                text = text.replace("{HOME}".lower(), os.environ["HOME"])
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
        if self.cog is not None:
            self.cog.cogsutils = self
            self.init_logger()
            if "format_help_for_context" not in self.cog.__func_red__:
                setattr(self.cog, 'format_help_for_context', self.format_help_for_context)
            # for command in self.cog.walk_commands():
            #     setattr(command, 'format_text_for_context', self.format_text_for_context)
            #     setattr(command, 'format_shortdoc_for_context', self.format_shortdoc_for_context)
            if "red_delete_data_for_user" not in self.cog.__func_red__:
                setattr(self.cog, 'red_delete_data_for_user', self.red_delete_data_for_user)
            if "red_get_data_for_user" not in self.cog.__func_red__:
                setattr(self.cog, 'red_get_data_for_user', self.red_get_data_for_user)
            if "cog_unload" not in self.cog.__func_red__:
                setattr(self.cog, 'cog_unload', self.cog_unload)
            if "cog_command_error" not in self.cog.__func_red__:
                setattr(self.cog, 'cog_command_error', self.cog_command_error)
        asyncio.create_task(self._await_setup())
        self.bot.remove_listener(self.on_command_error)
        self.bot.add_listener(self.on_command_error)
        self.bot.remove_command("getallfor")
        self.bot.add_command(getallfor)

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
        except self.DownloaderNotLoaded:
            pass
        except asyncio.TimeoutError:
            pass
        except ValueError:
            pass
        except Exception as e:  # really doesn't matter if this fails so fine with debug level
            self.cog.log.debug(f"Something went wrong checking if {self.cog.__class__.__name__} cog is up to date.", exc_info=e)
        self.add_dev_env_value()
        if self.is_dpy2:
            if not hasattr(self.bot, "tree"):
                self.bot.tree = discord.app_commands.CommandTree(self.bot)
            if not self.interactions == {}:
                if "added" in self.interactions:
                    if not self.interactions["added"]:
                        if "slash" in self.interactions:
                            for slash in self.interactions["slash"]:
                                try:
                                    self.bot.tree.add_command(slash, guild=None)
                                except Exception as e:
                                    if hasattr(self.cog, "log"):
                                        self.cog.log.error(f"The slash command `{slash.name}` could not be added correctly.", exc_info=e)
                        if "button" in self.interactions:
                            for button in self.interactions["button"]:
                                try:
                                    self.bot.add_view(button, guild=None)
                                except Exception:
                                    pass
                        self.interactions["removed"] = False
                        self.interactions["added"] = True
                    await self.bot.tree.sync(guild=None)

    def _end(self):
        """
        Removes dev environment values, slash commands add Views.
        """
        self.close_logger()
        self.remove_dev_env_value()
        for loop in self.loops:
            self.loops[loop].stop_all()
        if not self.at_least_one_cog_loaded:
            self.bot.remove_listener(self.on_command_error)
            self.bot.remove_command("getallfor")
        asyncio.create_task(self._await_end())

    async def _await_end(self):
        if self.is_dpy2:
            if not self.interactions == {}:
                if "removed" in self.interactions:
                    if not self.interactions["removed"]:
                        if "slash" in self.interactions:
                            for slash in self.interactions["slash"]:
                                try:
                                    self.bot.tree.remove_command(slash, guild=None)
                                except Exception as e:
                                    if hasattr(self.cog, "log"):
                                        self.cog.log.error(f"The slash command `{slash.name}` could not be removed correctly.", exc_info=e)
                        if "button" in self.interactions:
                            for button in self.interactions["button"]:
                                try:
                                    self.bot.remove_view(button, guild=None)
                                except Exception:
                                    pass
                        self.interactions["added"] = False
                        self.interactions["removed"] = True
                        await asyncio.sleep(2)
                        await self.bot.tree.sync(guild=None)

    def init_logger(self):
        """
        Prepare the logger for the cog.
        Thanks to @laggron42 on GitHub! (https://github.com/laggron42/Laggron-utils/blob/master/laggron_utils/logging.py) 
        """
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

    def add_dev_env_value(self):
        """
        If the bot owner is X, then add several values to the development environment, if they don't already exist.
        Even checks the id of the bot owner in the variable of my Sudo cog, if it is installed and loaded.
        """
        sudo_cog = self.bot.get_cog("Sudo")
        if sudo_cog is None:
            owner_ids = self.bot.owner_ids
        else:
            if hasattr(sudo_cog, "all_owner_ids"):
                if len(sudo_cog.all_owner_ids) == 0:
                    owner_ids = self.bot.owner_ids
                else:
                    owner_ids = set(list(self.bot.owner_ids) + list(sudo_cog.all_owner_ids))
            else:
                owner_ids = self.bot.owner_ids
        if 829612600059887649 in owner_ids:
            if self.is_dpy2:
                to_add = {
                    self.cog.__class__.__name__: lambda x: self.cog,
                    "CogsUtils": lambda ctx: CogsUtils,
                    "Loop": lambda ctx: Loop,
                    "Captcha": lambda ctx: Captcha,
                    "Buttons": lambda ctx: Buttons,
                    "Dropdown": lambda ctx: Dropdown,
                    "Modal": lambda ctx: Modal,
                    "Reactions": lambda ctx: Reactions,
                    "Menu": lambda ctx: Menu,
                    "discord": lambda ctx: discord,
                    "redbot": lambda ctx: redbot,
                    "Red": lambda ctx: Red,
                    "typing": lambda ctx: typing,
                    "inspect": lambda ctx: inspect
                }
            else:
                to_add = {
                    self.cog.__class__.__name__: lambda x: self.cog,
                    "CogsUtils": lambda ctx: CogsUtils,
                    "Loop": lambda ctx: Loop,
                    "Captcha": lambda ctx: Captcha,
                    "Menu": lambda ctx: Menu,
                    "discord": lambda ctx: discord,
                    "redbot": lambda ctx: redbot,
                    "Red": lambda ctx: Red,
                    "typing": lambda ctx: typing,
                    "inspect": lambda ctx: inspect
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

    def remove_dev_env_value(self):
        """
        If the bot owner is X, then remove several values to the development environment, if they don't already exist.
        Even checks the id of the bot owner in the variable of my Sudo cog, if it is installed and loaded.
        """
        sudo_cog = self.bot.get_cog("Sudo")
        if sudo_cog is None:
            owner_ids = self.bot.owner_ids
        else:
            if hasattr(sudo_cog, "all_owner_ids"):
                if len(sudo_cog.all_owner_ids) == 0:
                    owner_ids = self.bot.owner_ids
                else:
                    owner_ids = set(list(self.bot.owner_ids) + list(sudo_cog.all_owner_ids))
            else:
                owner_ids = self.bot.owner_ids
        if 829612600059887649 in owner_ids:
            try:
                self.bot.remove_dev_env_value(self.cog.__class__.__name__)
            except Exception:
                pass
            if not self.at_least_one_cog_loaded():
                if self.is_dpy2:
                    to_remove = {
                        "CogsUtils": lambda ctx: CogsUtils,
                        "Loop": lambda ctx: Loop,
                        "Captcha": lambda ctx: Captcha,
                        "Buttons": lambda ctx: Buttons,
                        "Dropdown": lambda ctx: Dropdown,
                        "Modal": lambda ctx: Modal,
                        "Reactions": lambda ctx: Reactions,
                        "Menu": lambda ctx: Menu,
                        "discord": lambda ctx: discord,
                        "redbot": lambda ctx: redbot,
                        "Red": lambda ctx: Red,
                        "typing": lambda ctx: typing,
                        "inspect": lambda ctx: inspect
                    }
                else:
                    to_remove = {
                        "CogsUtils": lambda ctx: CogsUtils,
                        "Loop": lambda ctx: Loop,
                        "Captcha": lambda ctx: Captcha,
                        "Menu": lambda ctx: Menu,
                        "discord": lambda ctx: discord,
                        "redbot": lambda ctx: redbot,
                        "Red": lambda ctx: Red,
                        "typing": lambda ctx: typing,
                        "inspect": lambda ctx: inspect
                    }
                for name, value in to_remove.items():
                    try:
                        self.bot.remove_dev_env_value(name)
                    except Exception:
                        pass

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        """
        Record all exceptions generated by commands by cog and by command in `bot.last_exceptions_cogs`.
        All my cogs will add this listener if it doesn't exist, so I need to record this in a common variable. Also, this may be useful to others.
        """
        try:
            IGNORED_ERRORS = (
                commands.UserInputError,
                commands.DisabledCommand,
                commands.CommandNotFound,
                commands.CheckFailure,
                commands.NoPrivateMessage,
                commands.CommandOnCooldown,
                commands.MaxConcurrencyReached,
                commands.BadArgument,
                commands.BadBoolArgument,
            )
            if ctx.cog is not None:
                cog = ctx.cog.__class__.__name__
            else:
                cog = "None"
            if ctx.command is None:
                return
            if isinstance(error, IGNORED_ERRORS):
                return
            if not hasattr(self.bot, "last_exceptions_cogs"):
                self.bot.last_exceptions_cogs = {}
            if "global" not in self.bot.last_exceptions_cogs:
                self.bot.last_exceptions_cogs["global"] = []
            if error in self.bot.last_exceptions_cogs["global"]:
                return
            self.bot.last_exceptions_cogs["global"].append(error)
            if isinstance(error, commands.CommandError):
                traceback_error = "".join(traceback.format_exception(type(error), error, error.__traceback__))
            else:
                traceback_error = f"Traceback (most recent call last): {error}"
            traceback_error = self.replace_var_paths(traceback_error)
            if cog not in self.bot.last_exceptions_cogs:
                self.bot.last_exceptions_cogs[cog] = {}
            if ctx.command.qualified_name not in self.bot.last_exceptions_cogs[cog]:
                self.bot.last_exceptions_cogs[cog][ctx.command.qualified_name] = []
            self.bot.last_exceptions_cogs[cog][ctx.command.qualified_name].append(traceback_error)
        except Exception:
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
                    return True
                elif str(interaction.data["custom_id"]) == "ConfirmationAsk_No":
                    if delete_message:
                        await self.delete_message(message)
                    return False
            except TimeoutError:
                if delete_message:
                    await self.delete_message(message)
                if timeout_message is not None:
                    await ctx.send(timeout_message)
                return None
        if way == "dropdown":
            view = Dropdown(timeout=timeout, options=[{"label": "Yes", "emoji": reactions[0], "value": "ConfirmationAsk_Yes"}, {"label": "No", "emoji": reactions[1], "value": "ConfirmationAsk_No"}], members=[ctx.author.id] + list(ctx.bot.owner_ids) if check_owner else [] + [x.id for x in members_authored])
            message = await ctx.send(content=text, embed=embed, file=file, view=view)
            try:
                interaction, values, function_result = await view.wait_result()
                if str(values[0]) == "ConfirmationAsk_Yes":
                    if delete_message:
                        await self.delete_message(message)
                    return True
                elif str(values[0]) == "ConfirmationAsk_No":
                    if delete_message:
                        await self.delete_message(message)
                    return False
            except TimeoutError:
                if delete_message:
                    await self.delete_message(message)
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

    async def invoke_command(self, author: discord.User, channel: discord.TextChannel, command: str, prefix: typing.Optional[str]=None, message: typing.Optional[discord.Message]=None, message_id: typing.Optional[str]="".join(choice(string.digits) for i in range(18)), timestamp: typing.Optional[datetime.datetime]=datetime.datetime.now()) -> typing.Union[commands.Context, discord.Message]:
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
            await bot.invoke(context)
        else:
            message.content = old_content
            message.author = author
            message.channel = channel
            bot.dispatch("message", message)
        return context if context.valid else message

    async def get_hook(self, channel: discord.TextChannel):
        """
        Create a discord.Webhook object. It tries to retrieve an existing webhook created by the bot or to create it itself.
        """
        try:
            for webhook in await channel.webhooks():
                if webhook.user.id == self.bot.user.id:
                    hook = webhook
                    break
            else:
                hook = await channel.create_webhook(
                    name="red_bot_hook_" + str(channel.id)
                )
        except discord.errors.NotFound:  # Probably user deleted the hook
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
        for object in self.get_all_repo_cogs_objects().values:
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

    def generate_key(self, number: typing.Optional[int]=10, existing_keys: typing.Optional[typing.List]=[], strings_used: typing.Optional[typing.List]={"ascii_lowercase": True, "ascii_uppercase": False, "digits": True, "punctuation": False, "others": []}):
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
            # This probably won't turn into an endless loop
            key = "".join(choice(strings) for i in range(number))
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

    # async def get_new_Config_with_modal(self, ctx: commands.Context, config: typing.Dict):
    #     new_config = {}
    #     view_button = Buttons(timeout=180, buttons=[{"label": "Configure", "emoji": "⚙️", "disabled": False}], members=[ctx.author.id])
    #     message = await ctx.send(view=view_button)
    #     try:
    #         interaction, function_result = await view_button.wait_result()
    #     except TimeoutError:
    #         await message.edit(view=Buttons(timeout=None, buttons=[{"label": "Configure", "emoji": "⚙️", "disabled": True}]))
    #         return None
    #     view_modal = None ###########################
    #     view_modal = Modal(title=f"{self.cog.__class__.__name__} Config", inputs=[{"label": config[input]["label"], "default"} for input in config], function=self.send_embed_with_responses)
    #     await interaction.response.send_modal(view_modal)
    #     try:
    #         interaction, values, function_result = await view_modal.wait_result()
    #     except TimeoutError:
    #         return None
    #     ###########################
    #     await message.delete()
    #     embed: discord.Embed = discord.Embed()
    #     embed.title = _("⚙️ Do you want to replace the entire Config of {self.cog.__class__.__name__} with what you specified?").format(**locals())
    #     if not await self.ConfirmationAsk(ctx, embed=embed):
    #         return None
    #     return new_config

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

class Loop():
    """
    Create a loop, with many features.
    Thanks to Vexed01 on GitHub! (https://github.com/Vexed01/Vex-Cogs/blob/master/timechannel/loop.py and https://github.com/Vexed01/vex-cog-utils/vexutils/loop.py)
    """
    def __init__(self, cogsutils: CogsUtils, name: str, function, days: typing.Optional[int]=0, hours: typing.Optional[int]=0, minutes: typing.Optional[int]=0, seconds: typing.Optional[int]=0, function_args: typing.Optional[typing.Dict]={}, wait_raw: typing.Optional[bool]=False, limit_count: typing.Optional[int]=None, limit_date: typing.Optional[datetime.datetime]=None, limit_exception: typing.Optional[int]=None) -> None:
        self.cogsutils: CogsUtils = cogsutils

        self.name: str = name
        self.function = function
        self.function_args = function_args
        self.interval: float = datetime.timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds).total_seconds()
        self.wait_raw = wait_raw
        self.limit_count: int = limit_count
        self.limit_date: datetime.datetime = limit_date
        self.limit_exception: int = limit_exception
        self.stop_manually: bool = False

        self.start_datetime: datetime.datetime = datetime.datetime.utcnow()
        self.expected_interval = datetime.timedelta(seconds=self.interval)
        self.last_iteration: typing.Optional[datetime.datetime] = None
        self.next_iteration: typing.Optional[datetime.datetime] = None
        self.currently_running: bool = False  # whether the function is running 
        self.iteration_count: int = 0
        self.last_result = None
        self.iteration_exception: int = 0
        self.last_exc: str = "No exception has occurred yet."
        self.last_exc_raw: typing.Optional[BaseException] = None
        self.stop: bool = False

        self.loop = self.cogsutils.bot.loop.create_task(self.loop())

    async def start(self):
        if self.cogsutils.is_dpy2:
            async with self.cogsutils.bot:
                self.cogsutils.bot.loop.create_task(self.loop())
        else:
            self.cogsutils.bot.loop.create_task(self.loop())

    async def wait_until_iteration(self) -> None:
        """Sleep during the raw interval."""
        now = datetime.datetime.utcnow()
        time = now.timestamp()
        time = math.ceil(time / self.interval) * self.interval
        next_iteration = datetime.datetime.fromtimestamp(time) - now
        seconds_to_sleep = (next_iteration).total_seconds()
        if not self.interval <= 60:
            if hasattr(self.cogsutils.cog, "log"):
                self.cogsutils.cog.log.debug(f"Sleeping for {seconds_to_sleep} seconds until {self.name} loop next iteration ({self.iteration_count + 1})...")
        await asyncio.sleep(seconds_to_sleep)

    async def loop(self) -> None:
        await self.cogsutils.bot.wait_until_red_ready()
        await asyncio.sleep(1)
        if hasattr(self.cogsutils.cog, "log"):
            self.cogsutils.cog.log.debug(f"{self.name} loop has started.")
        while True:
            try:
                start = monotonic()
                self.iteration_start()
                self.last_result = await self.function(**self.function_args)
                self.iteration_finish()
                end = monotonic()
                total = round(end - start, 1)
                if hasattr(self.cogsutils.cog, "log"):
                    if self.iteration_count == 1:
                        self.cogsutils.cog.log.debug(f"{self.name} initial iteration finished in {total}s ({self.iteration_count}).")
                    else:
                        if not self.interval <= 60:
                            self.cogsutils.cog.log.debug(f"{self.name} iteration finished in {total}s ({self.iteration_count}).")
            except Exception as e:
                if hasattr(self.cogsutils.cog, "log"):
                    if self.iteration_count == 1:
                        self.cogsutils.cog.log.exception(f"Something went wrong in the {self.name} loop ({self.iteration_count}).", exc_info=e)
                    else:
                        self.cogsutils.cog.log.exception(f"Something went wrong in the {self.name} loop iteration ({self.iteration_count}).", exc_info=e)
                self.iteration_error(e)
            if self.maybe_stop():
                return
            if not self.wait_raw:
                # both iteration_finish and iteration_error set next_iteration as not None
                assert self.next_iteration is not None
                if float(self.interval) % float(3600) == 0:
                    self.next_iteration = self.next_iteration.replace(
                        minute=0,
                        second=0,
                        microsecond=0
                    )  # ensure further iterations are on the hour
                elif float(self.interval) % float(60) == 0:
                    self.next_iteration = self.next_iteration.replace(
                        second=0,
                        microsecond=0
                    )  # ensure further iterations are on the minute
                else:
                    self.next_iteration = self.next_iteration.replace(
                        microsecond=0
                    )  # ensure further iterations are on the second
                if not self.interval == 0:
                    await self.wait_until_iteration()
            else:
                await self.sleep_until_next()

    def maybe_stop(self):
        if self.stop_manually:
            self.stop_all()
        if self.limit_count is not None:
            if self.iteration_count >= self.limit_count:
                self.stop_all()
        if self.limit_date is not None:
            if datetime.datetime.timestamp(datetime.datetime.now()) >= datetime.datetime.timestamp(self.limit_date):
                self.stop_all()
        if self.limit_exception:
            if self.iteration_exception >= self.limit_exception:
                self.stop_all()
        if self.stop:
            return True
        return False

    def stop_all(self):
        self.stop = True
        self.next_iteration = None
        self.loop.cancel()
        if f"{self.name}" in self.cogsutils.loops:
            if self.cogsutils.loops[f"{self.name}"] == self:
                del self.cogsutils.loops[f"{self.name}"]
        if hasattr(self.cogsutils.cog, "log"):
            self.cogsutils.cog.log.debug(f"{self.name} loop has been stopped after {self.iteration_count} iterations.")
        return self

    def __repr__(self) -> str:
        return (
            f"<friendly_name={self.name} iteration_count={self.iteration_count} "
            f"currently_running={self.currently_running} last_iteration={self.last_iteration} "
            f"next_iteration={self.next_iteration} integrity={self.integrity}>"
        )

    @property
    def integrity(self) -> bool:
        """
        If the loop is running on time (whether or not next expected iteration is in the future)
        """
        if self.next_iteration is None:  # not started yet
            return False
        return self.next_iteration > datetime.datetime.utcnow()

    @property
    def until_next(self) -> float:
        """
        Positive float with the seconds until the next iteration, based off the last
        iteration and the interval.
        If the expected time of the next iteration is in the past, this will return `0.0`
        """
        if self.next_iteration is None:  # not started yet
            return 0.0

        raw_until_next = (self.next_iteration - datetime.datetime.utcnow()).total_seconds()
        if raw_until_next > self.expected_interval.total_seconds():  # should never happen
            return self.expected_interval.total_seconds()
        elif raw_until_next > 0.0:
            return raw_until_next
        else:
            return 0.0

    async def sleep_until_next(self) -> None:
        """Sleep until the next iteration. Basically an "all-in-one" version of `until_next`."""
        await asyncio.sleep(self.until_next)

    def iteration_start(self) -> None:
        """Register an iteration as starting."""
        self.iteration_count += 1
        self.currently_running = True
        self.last_iteration = datetime.datetime.utcnow()
        self.next_iteration = datetime.datetime.utcnow() + self.expected_interval
        # this isn't accurate, it will be "corrected" when finishing is called

    def iteration_finish(self) -> None:
        """Register an iteration as finished successfully."""
        self.currently_running = False
        # now this is accurate. imo its better to have something than nothing

    def iteration_error(self, error: BaseException) -> None:
        """Register an iteration's error."""
        self.currently_running = False
        self.last_exc_raw = error
        self.last_exc = "".join(
            traceback.format_exception(type(error), error, error.__traceback__)
        )

    def get_debug_embed(self) -> discord.Embed:
        """Get an embed with infomation on this loop."""
        now: datetime.datetime = datetime.datetime.utcnow()

        raw_table = Table("Key", "Value")
        raw_table.add_row("expected_interval", str(self.expected_interval))
        raw_table.add_row("iteration_count", str(self.iteration_count))
        raw_table.add_row("currently_running", str(self.currently_running))
        raw_table.add_row("next_iteration", str(self.last_iteration))
        raw_table.add_row("next_iteration", str(self.next_iteration))
        raw_table_str = no_colour_rich_markup(raw_table)

        if self.next_iteration and self.last_iteration:
            processed_table = Table("Key", "Value")
            processed_table.add_row("Seconds until next", str((self.next_iteration - now).total_seconds()))
            processed_table.add_row("Seconds since last", str((now - self.last_iteration).total_seconds()))
            processed_table.add_row("Raw interval", str((self.next_iteration - now).total_seconds() + (now - self.last_iteration).total_seconds()))
            processed_table_str = no_colour_rich_markup(processed_table)
        else:
            processed_table_str = "Loop hasn't started yet."

        datetime_table = Table("Key", "Value")
        datetime_table.add_row("Start date-time", str(self.start_datetime))
        datetime_table.add_row("Now date-time", str(now))
        datetime_table.add_row("Runtime", (str(now - self.start_datetime) + "\n" + str((now - self.start_datetime).total_seconds()) + "s"))
        datetime_table_str = no_colour_rich_markup(datetime_table)

        emoji = "✅" if self.integrity else "❌"
        embed: discord.Embed = discord.Embed(title=f"{self.name} Loop: `{emoji}`")
        embed.color = 0x00D26A if self.integrity else 0xF92F60
        embed.timestamp = now
        embed.add_field(
            name="Raw data",
            value=raw_table_str,
            inline=False
        )
        embed.add_field(
            name="Processed data",
            value=processed_table_str,
            inline=False,
        )
        embed.add_field(
            name="DateTime data",
            value=datetime_table_str,
            inline=False,
        )
        exc = self.last_exc
        exc = self.cogsutils.replace_var_paths(exc)
        if len(exc) > 1024:
            exc = list(pagify(exc, page_length=1024))[0] + "\n..."
        embed.add_field(name="Exception", value=box(exc), inline=False)

        return embed

class Captcha():
    """
    Captcha for an member in a text channel.
    Thanks to Kreusada for this code! (https://github.com/Kreusada/Kreusada-Cogs/blob/master/captcha/)
    """

    def __init__(self, cogsutils: CogsUtils, member: discord.Member, channel: discord.TextChannel, limit: typing.Optional[int]=3, timeout: typing.Optional[int]=60, why: typing.Optional[str]=""):
        self.cogsutils: CogsUtils = cogsutils

        self.member: discord.Member = member
        self.guild: discord.Guild = member.guild
        self.channel: discord.TextChannel = channel
        self.why: str = why

        self.limit: int = limit
        self.timeout: int = timeout

        self.message: discord.Message = None
        self.code: str = None
        self.running: bool = False
        self.tasks: list = []
        self.trynum: int = 0
        self.escape_char = "\u200B"

    async def realize_challenge(self) -> None:
        is_ok = None
        timeout = False
        try:
            while is_ok is not True:
                if self.trynum > self.limit:
                    break
                try:
                    self.code = self.generate_code()
                    await self.send_message()
                    this = await self.try_challenging()
                except TimeoutError:
                    timeout = True
                    break
                except self.AskedForReload:
                    self.trynum += 1
                    continue
                except TypeError:
                    continue
                except self.LeftGuildError:
                    leave_guild = True
                    break
                if this is False:
                    self.trynum += 1
                    is_ok = False
                else:
                    is_ok = True
            if self.message is not None:
                try:
                    await self.message.delete()
                except discord.HTTPException:
                    pass
            failed = self.trynum > self.limit
        except self.MissingPermissions as e:
            raise self.MissingPermissions(e)
        except Exception as e:
            if hasattr(self.cogsutils.cog, "log"):
                self.cogsutils.cog.log.error("An unsupported error occurred during the captcha.", exc_info=e)
            raise self.OtherException(e)
        finally:
            if timeout:
                raise TimeoutError()
            if failed:
                return False
            if leave_guild:
                raise self.LeftGuildError("User has left guild.")
            return True

    async def try_challenging(self) -> bool:
        """Do challenging in one function!
        """
        self.running = True
        try:
            received = await self.wait_for_action()
            if received is None:
                raise self.LeftGuildError("User has left guild.")
            if hasattr(received, "content"):
                # It's a message!
                try:
                    await received.delete()
                except discord.HTTPException:
                    pass
                error_message = ""
                try:
                    state = await self.verify(received.content)
                except self.SameCodeError:
                    error_message += error(bold(_("Code invalid. Do not copy and paste.").format(**locals())))
                    state = False
                else:
                    if not state:
                        error_message += warning("Code invalid.")
                if error_message:
                    await self.channel.send(error_message, delete_after=3)
                return state
            else:
                raise self.AskedForReload("User want to reload Captcha.")
        except TimeoutError:
            raise TimeoutError()
        finally:
            self.running = False

    def generate_code(self, put_fake_espace: typing.Optional[bool] = True):
        code = self.cogsutils.generate_key(number=8, existing_keys=[], strings_used={"ascii_lowercase": False, "ascii_uppercase": True, "digits": True, "punctuation": False})
        if put_fake_espace:
            code = self.escape_char.join(list(code))
        return code

    def get_embed(self) -> discord.Embed:
        """
        Get the embed containing the captcha code.
        """
        embed_dict = {
                        "embeds": [
                            {
                                "title": _("Captcha").format(**locals()) + _(" for {self.why}").format(**locals()) if not self.why == "" else "",
                                "description": _("Please return me the following code:\n{box(str(self.code))}\nDo not copy and paste.").format(**locals()),
                                "author": {
                                    "name": f"{self.member.display_name}",
                                    "icon_url": self.member.display_avatar if self.is_dpy2 else self.member.avatar_url
                                },
                                "footer": {
                                    "text": _("Tries: {self.trynum} / Limit: {self.limit}").format(**locals())
                                }
                            }
                        ]
                    }
        embed = self.cogsutils.get_embed(embed_dict)["embed"]
        return embed

    async def send_message(self) -> None:
        """
        Send a message with new code.
        """
        if self.message is not None:
            try:
                await self.message.delete()
            except discord.HTTPException:
                pass
        embed = self.get_embed()
        try:
            self.message = await self.channel.send(
                            embed=embed,
                            delete_after=900,  # Delete after 15 minutes.
                        )
        except discord.HTTPException:
            raise self.MissingPermissions("Cannot send message in verification channel.")
        try:
            await self.message.add_reaction("🔁")
        except discord.HTTPException:
            raise self.MissingPermissions("Cannot react in verification channel.")

    async def verify(self, code_input: str) -> bool:
        """Verify a code."""
        if self.escape_char in code_input:
            raise self.SameCodeError
        if code_input.lower() == self.code.replace(self.escape_char, "").lower():
            return True
        else:
            return False

    async def wait_for_action(self) -> typing.Union[discord.Reaction, discord.Message, None]:
        """Wait for an action from the user.
        It will return an object of discord.Message or discord.Reaction depending what the user
        did.
        """
        self.cancel_tasks()  # Just in case...
        self.tasks = self._give_me_tasks()
        done, pending = await asyncio.wait(
            self.tasks,
            timeout=self.timeout,
            return_when=asyncio.FIRST_COMPLETED,
        )
        self.cancel_tasks()
        if len(done) == 0:
            raise TimeoutError()("User didn't answer.")
        try:  # An error is raised if we return the result and when the task got cancelled.
            return done.pop().result()
        except asyncio.CancelledError:
            return None

    def cancel_tasks(self) -> None:
        """Cancel the ongoing tasks."""
        for task in self.tasks:
            task: asyncio.Task
            if not task.done():
                task.cancel()

    def _give_me_tasks(self) -> typing.List:
        def leave_check(u):
            return u.id == self.member.id
        return [
            asyncio.create_task(
                self.cogsutils.bot.wait_for(
                    "reaction_add",
                    check=ReactionPredicate.with_emojis(
                        "🔁", message=self.message, user=self.member
                    )
                )
            ),
            asyncio.create_task(
                self.cogsutils.bot.wait_for(
                    "message",
                    check=MessagePredicate.same_context(
                        channel=self.channel,
                        user=self.member,
                    )
                )
            ),
            asyncio.create_task(self.cogsutils.bot.wait_for("user_remove", check=leave_check))
        ]

    class MissingPermissions(Exception):
        pass

    class AskedForReload(Exception):
        pass

    class SameCodeError(Exception):
        pass

    class LeftGuildError(Exception):
        pass

    class OtherException(Exception):
        pass

if CogsUtils().is_dpy2:

    class Buttons(discord.ui.View):
        """Create Buttons easily."""

        def __init__(self, timeout: typing.Optional[float]=180, buttons: typing.Optional[typing.List]=[{}], members: typing.Optional[typing.List]=None, check: typing.Optional[typing.Any]=None, function: typing.Optional[typing.Any]=None, function_args: typing.Optional[typing.Dict]={}, infinity: typing.Optional[bool]=False):
            """style: ButtonStyle, label: Optional[str], disabled: bool, custom_id: Optional[str], url: Optional[str], emoji: Optional[Union[str, Emoji, PartialEmoji]], row: Optional[int]"""
            for button_dict in buttons:
                if "url" in button_dict and button_dict["url"] is not None:
                    button_dict["style"] = 5
                    continue
                if "custom_id" not in button_dict:
                    button_dict["custom_id"] = "CogsUtils" + "_" + CogsUtils().generate_key(number=10)
            self.buttons_dict_instance = {"timeout": timeout, "buttons": [b.copy() for b in buttons], "members": members, "check": check, "function": function, "function_args": function_args, "infinity": infinity}
            super().__init__(timeout=timeout)
            self.infinity = infinity
            self.interaction_result = None
            self.function_result = None
            self.members = members
            self.check = check
            self.function = function
            self.function_args = function_args
            self.clear_items()
            self.buttons = []
            self.buttons_dict = []
            self.done = asyncio.Event()
            for button_dict in buttons:
                if "style" not in button_dict:
                    button_dict["style"] = int(discord.ButtonStyle(2))
                if "disabled" not in button_dict:
                    button_dict["disabled"] = False
                if "label" not in button_dict and "emoji" not in button_dict:
                    button_dict["label"] = "Test"
                button = discord.ui.Button(**button_dict)
                self.add_item(button)
                self.buttons.append(button)
                self.buttons_dict.append(button_dict)

        def to_dict_cogsutils(self, for_Config: typing.Optional[bool]=False):
            buttons_dict_instance = self.buttons_dict_instance
            if for_Config:
                buttons_dict_instance["check"] = None
                buttons_dict_instance["function"] = None
            return buttons_dict_instance

        @classmethod
        def from_dict_cogsutils(cls, buttons_dict_instance: typing.Dict):
            return cls(**buttons_dict_instance)

        async def interaction_check(self, interaction: discord.Interaction):
            if self.check is not None:
                if not self.check(interaction):
                    await interaction.response.send_message("You are not allowed to use this interaction.", ephemeral=True)
                    return True
            if self.members is not None:
                if interaction.user.id not in self.members:
                    await interaction.response.send_message("You are not allowed to use this interaction.", ephemeral=True)
                    return True
            self.interaction_result = interaction
            if self.function is not None:
                self.function_result = await self.function(self, interaction, **self.function_args)
            self.done.set()
            if not self.infinity:
                self.stop()
            return True

        async def on_timeout(self):
            self.done.set()
            self.stop()

        async def wait_result(self):
            self.done = asyncio.Event()
            await self.done.wait()
            interaction, function_result = self.get_result()
            if interaction is None:
                raise TimeoutError()
            return interaction, function_result

        def get_result(self):
            return self.interaction_result, self.function_result

    class Dropdown(discord.ui.View):
        """Create Dropdown easily."""

        def __init__(self, timeout: typing.Optional[float]=180, placeholder: typing.Optional[str]="Choose a option.", min_values: typing.Optional[int]=1, max_values: typing.Optional[int]=1, *, options: typing.Optional[typing.List]=[{}], members: typing.Optional[typing.List]=None, check: typing.Optional[typing.Any]=None, function: typing.Optional[typing.Any]=None, function_args: typing.Optional[typing.Dict]={}, infinity: typing.Optional[bool]=False, custom_id: typing.Optional[str]=f"CogsUtils_{CogsUtils().generate_key(number=10)}"):
            """label: str, value: str, description: Optional[str], emoji: Optional[Union[str, Emoji, PartialEmoji]], default: bool"""
            self.dropdown_dict_instance = {"timeout": timeout, "placeholder": placeholder, "min_values": min_values, "max_values": max_values, "options": [o.copy() for o in options], "members": members, "check": check, "function": function, "function_args": function_args, "infinity": infinity}
            super().__init__(timeout=timeout)
            self.infinity = infinity
            self.dropdown = self.Dropdown(placeholder=placeholder, min_values=min_values, max_values=max_values, options=options, members=members, check=check, function=function, function_args=function_args, infinity=self.infinity, custom_id=custom_id)
            self.add_item(self.dropdown)

        def to_dict_cogsutils(self, for_Config: typing.Optional[bool]=False):
            dropdown_dict_instance = self.dropdown_dict_instance
            if for_Config:
                dropdown_dict_instance["check"] = None
                dropdown_dict_instance["function"] = None
            return dropdown_dict_instance

        @classmethod
        def from_dict_cogsutils(cls, dropdown_dict_instance: typing.Dict):
            return cls(**dropdown_dict_instance)

        async def on_timeout(self):
            self.dropdown.done.set()
            self.stop()

        async def wait_result(self):
            self.dropdown.done = asyncio.Event()
            await self.dropdown.done.wait()
            interaction, values, function_result = self.get_result()
            if interaction is None:
                raise TimeoutError()
            return interaction, values, function_result

        def get_result(self):
            return self.dropdown.interaction_result, self.dropdown.values_result, self.dropdown.function_result

        class Dropdown(discord.ui.Select):

            def __init__(self, placeholder: typing.Optional[str]="Choose a option.", min_values: typing.Optional[int]=1, max_values: typing.Optional[int]=1, *, options: typing.Optional[typing.List]=[], members: typing.Optional[typing.List]=None, check: typing.Optional[typing.Any]=None, function: typing.Optional[typing.Any]=None, function_args: typing.Optional[typing.Dict]={}, infinity: typing.Optional[bool]=False, custom_id: typing.Optional[str]=f"CogsUtils_{CogsUtils().generate_key(number=10)}"):
                self.infinity = infinity
                self.interaction_result = None
                self.values_result = None
                self.function_result = None
                self.members = members
                self.check = check
                self.function = function
                self.function_args = function_args
                self._options = []
                self.options_dict = []
                self.done = asyncio.Event()
                for option_dict in options:
                    if "label" not in option_dict and "emoji" not in option_dict:
                        option_dict["label"] = "Test"
                    option = discord.SelectOption(**option_dict)
                    self._options.append(option)
                    self.options_dict.append(option_dict)
                super().__init__(custom_id=custom_id, placeholder=placeholder, min_values=min_values, max_values=max_values, options=self._options)

            async def callback(self, interaction: discord.Interaction):
                if self.check is not None:
                    if not self.check(interaction):
                        await interaction.response.send_message("You are not allowed to use this interaction.", ephemeral=True)
                        return True
                if self.members is not None:
                    if interaction.user.id not in self.members:
                        await interaction.response.send_message("You are not allowed to use this interaction.", ephemeral=True)
                        return True
                self.interaction_result = interaction
                self.values_result = self.values
                if self.function is not None:
                    self.function_result = await self.function(self.view, interaction, self.values, **self.function_args)
                self.done.set()
                if not self.infinity:
                    self.view.stop()

    class Modal(discord.ui.Modal):
        """Create Modal easily."""

        def __init__(self, title: typing.Optional[str]="Form", timeout: typing.Optional[float]=None, inputs: typing.Optional[typing.List]=[{}], members: typing.Optional[typing.List]=None, check: typing.Optional[typing.Any]=None, function: typing.Optional[typing.Any]=None, function_args: typing.Optional[typing.Dict]={}):
            """name: str, label: str, style: TextStyle, custom_id: str, placeholder: Optional[str], default: Optional[str], required: bool, min_length: Optional[int], max_length: Optional[int], row: Optional[int]"""
            for input_dict in inputs:
                if "custom_id" not in input_dict:
                    input_dict["custom_id"] = "CogsUtils" + "_" + CogsUtils().generate_key(number=10)
            self.modal_dict_instance = {"title": title, "timeout": timeout, "inputs": [i.copy() for i in inputs], "function": function, "function_args": function_args}
            super().__init__(title=title, timeout=timeout)
            self.title = title
            self.interaction_result = None
            self.values_result = None
            self.function_result = None
            self.members = members
            self.check = check
            self.function = function
            self.function_args = function_args
            self.inputs = []
            self.inputs_dict = []
            self.done = asyncio.Event()
            for input_dict in inputs:
                if "label" not in input_dict:
                    input_dict["label"] = "Test"
                if "style" in input_dict:
                    if isinstance(input_dict["style"], int):
                        input_dict["style"] = discord.ui.text_input.TextStyle(input_dict["style"])
                input = discord.ui.text_input.TextInput(**input_dict)
                self.add_item(input)
                self.inputs.append(input)
                self.inputs_dict.append(input_dict)

        def to_dict_cogsutils(self, for_Config: typing.Optional[bool]=False):
            modal_dict_instance = self.modal_dict_instance
            if for_Config:
                modal_dict_instance["function"] = None
            return modal_dict_instance

        @classmethod
        def from_dict_cogsutils(cls, modal_dict_instance: typing.Dict):
            return cls(**modal_dict_instance)

        async def on_submit(self, interaction: discord.Interaction):
            if self.check is not None:
                if not self.check(interaction):
                    await interaction.response.send_message("You are not allowed to use this interaction.", ephemeral=True)
                    return True
            if self.members is not None:
                if interaction.user.id not in self.members:
                    await interaction.response.send_message("You are not allowed to use this interaction.", ephemeral=True)
                    return True
            self.interaction_result = interaction
            self.values_result = self.inputs
            if self.function is not None:
                self.function_result = await self.function(self, self.interaction_result, self.values_result, **self.function_args)
            self.done.set()
            self.stop()

        async def on_timeout(self):
            self.done.set()
            self.stop()

        async def wait_result(self):
            self.done = asyncio.Event()
            await self.done.wait()
            interaction, values, function_result = self.get_result()
            if interaction is None:
                raise TimeoutError()
            return interaction, values, function_result

        def get_result(self):
            return self.interaction_result, self.values_result, self.function_result

class Reactions():
    """Create Reactions easily."""

    def __init__(self, bot: Red, message: discord.Message, remove_reaction: typing.Optional[bool]=True, timeout: typing.Optional[float]=180, reactions: typing.Optional[typing.List]=["✅", "❌"], members: typing.Optional[typing.List]=None, check: typing.Optional[typing.Any]=None, function: typing.Optional[typing.Any]=None, function_args: typing.Optional[typing.Dict]={}, infinity: typing.Optional[bool]=False):
        self.reactions_dict_instance = {"message": message, "timeout": timeout, "reactions": reactions, "members": members, "check": check, "function": function, "function_args": function_args, "infinity": infinity}
        self.bot = bot
        self.message = message
        self.remove_reaction = remove_reaction
        self.timeout = timeout
        self.infinity = infinity
        self.reaction_result = None
        self.user_result = None
        self.function_result = None
        self.members = members
        self.check = check
        self.function = function
        self.function_args = function_args
        self.reactions = reactions
        self.done = asyncio.Event()
        self.r = False
        asyncio.create_task(self.wait())

    def to_dict_cogsutils(self, for_Config: typing.Optional[bool]=False):
        reactions_dict_instance = self.reactions_dict_instance
        if for_Config:
            reactions_dict_instance["bot"] = None
            reactions_dict_instance["message"] = None
            reactions_dict_instance["check"] = None
            reactions_dict_instance["function"] = None
        return reactions_dict_instance

    @classmethod
    def from_dict_cogsutils(cls, reactions_dict_instance: typing.Dict):
        return cls(**reactions_dict_instance)

    async def wait(self):
        if not self.r:
            await start_adding_reactions(self.message, self.reactions)
            self.r = True
        predicates = ReactionPredicate.same_context(message=self.message)
        running = True
        try:
            while True:
                if not running:
                    break
                tasks = [asyncio.create_task(self.bot.wait_for("reaction_add", check=predicates))]
                done, pending = await asyncio.wait(
                    tasks, timeout=self.timeout, return_when=asyncio.FIRST_COMPLETED
                )
                for task in pending:
                    task.cancel()
                if len(done) == 0:
                    raise TimeoutError()
                reaction, user = done.pop().result()
                running = await self.reaction_check(reaction, user)
        except TimeoutError:
            await self.on_timeout()

    async def reaction_check(self, reaction: discord.Reaction, user: discord.User):
        async def remove_reaction(remove_reaction, message: discord.Message, reaction: discord.Reaction, user: discord.User):
            if remove_reaction:
                try:
                    await message.remove_reaction(emoji=reaction, member=user)
                except discord.HTTPException:
                    pass
        if not str(reaction.emoji) in self.reactions:
            await remove_reaction(self.remove_reaction, self.message, reaction, user)
            return False
        if self.check is not None:
            if not self.check(reaction, user):
                await remove_reaction(self.remove_reaction, self.message, reaction, user)
                return False
        if self.members is not None:
            if user.id not in self.members:
                await remove_reaction(self.remove_reaction, self.message, reaction, user)
                return False
        await remove_reaction(self.remove_reaction, self.message, reaction, user)
        self.reaction_result = reaction
        self.user_result = user
        if self.function is not None:
            self.function_result = await self.function(self, reaction, user, **self.function_args)
        self.done.set()
        if self.infinity:
            return True
        else:
            return False

    async def on_timeout(self):
        self.done.set()

    async def wait_result(self):
        self.done = asyncio.Event()
        await self.done.wait()
        reaction, user, function_result = self.get_result()
        if reaction is None:
            raise TimeoutError()
        return reaction, user, function_result

    def get_result(self):
        return self.reaction_result, self.user_result, self.function_result

class Menu():
    """Create Menus easily."""

    def __init__(self, pages: typing.List[typing.Union[typing.Dict[str, typing.Union[str, typing.Any]], discord.Embed, str]], timeout: typing.Optional[int]=180, delete_after_timeout: typing.Optional[bool]=False, way: typing.Optional[typing.Literal["buttons", "reactions", "dropdown"]]="buttons", controls: typing.Optional[typing.Dict]={"⏮️": "left_page", "◀️": "prev_page", "❌": "close_page", "▶️": "next_page", "⏭️": "right_page"}, page_start: typing.Optional[int]=0, check_owner: typing.Optional[bool]=True, members_authored: typing.Optional[typing.Iterable[discord.Member]]=[]):
        self.ctx: commands.Context = None
        self.pages: typing.List = pages
        self.timeout: int = timeout
        self.delete_after_timeout: bool = delete_after_timeout
        self.way: typing.Literal["buttons", "reactions", "dropdown"] = way
        self.controls: typing.Dict = controls.copy()
        self.check_owner: bool = check_owner
        self.members_authored: typing.List = members_authored
        if not CogsUtils().is_dpy2 and self.way == "buttons" or not CogsUtils().is_dpy2 and self.way == "dropdown":
            self.way = "reactions"
        if not isinstance(self.pages[0], (typing.Dict, discord.Embed, str)):
            raise RuntimeError("Pages must be of type discord.Embed or str.")

        self.source = self._SimplePageSource(items=pages)
        if not self.source.is_paginating():
            for emoji, name in controls.items():
                if name in ["left_page", "prev_page", "next_page", "right_page"]:
                    del self.controls[emoji]
        self.message: discord.Message = None
        self.view: typing.Union[Buttons, Dropdown] = None
        self.current_page: int = page_start

    async def start(self, ctx: commands.Context):
        """
        Used to start the menu displaying the first page requested.
        Parameters
        ----------
            ctx: `commands.Context`
                The context to start the menu in.
        """
        self.ctx = ctx
        if self.way == "buttons":
            self.view = Buttons(timeout=self.timeout, buttons=[{"emoji": str(e), "custom_id": str(n)} for e, n in self.controls.items()], members=[self.ctx.author.id] + list(self.ctx.bot.owner_ids) if self.check_owner else [] + [x.id for x in self.members_authored], infinity=True)
            await self.send_initial_message(ctx, ctx.channel)
        elif self.way == "reactions":
            await self.send_initial_message(ctx, ctx.channel)
            self.view = Reactions(bot=self.ctx.bot, message=self.message, remove_reaction=True, timeout=self.timeout, reactions=[str(e) for e in self.controls.keys()], members=[self.ctx.author.id] + list(self.ctx.bot.owner_ids) if self.check_owner else [] + [x.id for x in self.members_authored], infinity=True)
        elif self.way == "dropdown":
            self.view = Dropdown(timeout=self.timeout, options=[{"emoji": str(e), "label": str(n).replace("_", " ").capitalize()} for e, n in self.controls.items()], members=[self.ctx.author.id] + list(self.ctx.bot.owner_ids) if self.check_owner else [] + [x.id for x in self.members_authored], infinity=True)
            await self.send_initial_message(ctx, ctx.channel)
        try:
            while True:
                if self.way == "buttons":
                    interaction, function_result = await self.view.wait_result()
                    response = interaction.data["custom_id"]
                elif self.way == "reactions":
                    reaction, user, function_result = await self.view.wait_result()
                    response = self.controls[str(reaction.emoji)]
                elif self.way == "dropdown":
                    interaction, values, function_result = await self.view.wait_result()
                    response = str(values[0]).lower().replace(" ", "_")
                if response == "left_page":
                    self.current_page = 0
                elif response == "prev_page":
                    self.current_page += -1
                elif response == "close_page":
                    if self.way == "buttons" or self.way == "dropdown":
                        self.view.stop()
                    await self.message.delete()
                    break
                elif response == "next_page":
                    self.current_page += 1
                elif response == "right_page":
                    self.current_page = self.source.get_max_pages() - 1
                kwargs = await self.get_page(self.current_page)
                if self.way == "buttons" or self.way == "dropdown":
                    try:
                        await interaction.response.edit_message(**kwargs)
                    except discord.errors.InteractionResponded:
                        await self.message.edit(**kwargs)
                else:
                    await self.message.edit(**kwargs)
        except TimeoutError:
            await self.on_timeout()

    async def send_initial_message(self, ctx: commands.Context, channel: discord.abc.Messageable):
        self.author = ctx.author
        self.ctx = ctx
        kwargs = await self.get_page(self.current_page)
        self.message = await channel.send(**kwargs, view=self.view if self.way in ["buttons", "dropdown"] else None)
        for page in self.pages:
            if isinstance(page, typing.Dict):
                if "file" in page:
                    del page["file"]
        return self.message

    async def get_page(self, page_num: int):
        try:
            page = await self.source.get_page(page_num)
        except IndexError:
            self.current_page = 0
            page = await self.source.get_page(self.current_page)
        value = await self.source.format_page(self, page)
        if isinstance(value, typing.Dict):
            return value
        elif isinstance(value, str):
            return {"content": value, "embed": None}
        elif isinstance(value, discord.Embed):
            return {"embed": value, "content": None}

    async def on_timeout(self):
        if self.delete_after_timeout:
            await self.message.delete()
        else:
            if self.way == "buttons":
                self.view.stop()
                await self.message.edit(view=None)
            elif self.way == "reactions":
                try:
                    await self.message.clear_reactions()
                except discord.HTTPException:
                    try:
                        await self.message.remove_reaction(*self.controls.keys(), self.ctx.bot.user)
                    except discord.HTTPException:
                        pass
            elif self.way == "dropdown":
                self.view.stop()
                await self.message.edit(view=None)

    class _SimplePageSource(menus.ListPageSource):

        def __init__(self, items: typing.List[typing.Union[typing.Dict[str, typing.Union[str, discord.Embed]], discord.Embed, str]]):
            super().__init__(items, per_page=1)

        async def format_page(
            self, view, page: typing.Union[typing.Dict[str, typing.Union[str, discord.Embed]], discord.Embed, str]
        ) -> typing.Union[str, discord.Embed]:
            return page

@commands.is_owner()
@commands.command(hidden=True)
async def getallfor(ctx: commands.Context, all: typing.Optional[typing.Literal["all", "ALL"]]=None, page: typing.Optional[int]=None, repo: typing.Optional[typing.Union[Repo, typing.Literal["AAA3A", "aaa3a"]]]=None, check_updates: typing.Optional[bool]=False, cog: typing.Optional[InstalledCog]=None, command: typing.Optional[str]=None):
    """Get all the necessary information to get support on a bot/repo/cog/command.
    With a html file.
    """
    if all is not None:
        repo = None
        cog = None
        command = None
        check_updates = False
    if repo is not None:
        _repos = [repo]
    else:
        _repos = [None]
    if cog is not None:
        _cogs = [cog]
    else:
        _cogs = [None]
    if command is not None:
        _commands = [command]
    else:
        _commands = [None]
    if command is not None:
        object_command = ctx.bot.get_command(_commands[0])
        if object_command is None:
            await ctx.send(_("The command `{command}` does not exist.").format(**locals()))
            return
        _commands = [object_command]
    downloader = ctx.bot.get_cog("Downloader")
    if downloader is None:
        if CogsUtils(bot=ctx.bot).ConfirmationAsk(ctx, _("The cog downloader is not loaded. I can't continue. Do you want me to do it?").format(**locals())):
            await ctx.invoke(ctx.bot.get_command("load"), "downloader")
            downloader = ctx.bot.get_cog("Downloader")
        else:
            return
    installed_cogs = await downloader.config.installed_cogs()
    loaded_cogs = [c.lower() for c in ctx.bot.cogs]
    if repo is not None:
        rp = _repos[0]
        if not isinstance(rp, Repo) and not "AAA3A".lower() in rp.lower():
            await ctx.send(_("Repo by the name `{rp}` does not exist.").format(**locals()))
            return
        if not isinstance(repo, Repo):
            found = False
            for r in await downloader.config.installed_cogs():
                if "AAA3A".lower() in str(r).lower():
                    _repos = [downloader._repo_manager.get_repo(str(r))]
                    found = True
                    break
            if not found:
                await ctx.send(_("Repo by the name `{rp}` does not exist.").format(**locals()))
                return
        if check_updates:
            cogs_to_check, failed = await downloader._get_cogs_to_check(repos={_repos[0]})
            cogs_to_update, libs_to_update = await downloader._available_updates(cogs_to_check)
            cogs_to_update, filter_message = downloader._filter_incorrect_cogs(cogs_to_update)
            to_update_cogs = [c.name.lower() for c in cogs_to_update]

    if all is not None:
        _repos = []
        for r in installed_cogs:
            _repos.append(downloader._repo_manager.get_repo(str(r)))
        _cogs = []
        for r in installed_cogs:
            for c in installed_cogs[r]:
                _cogs.append(await InstalledCog.convert(ctx, str(c)))
        _commands = []
        for c in ctx.bot.all_commands:
            cmd = ctx.bot.get_command(str(c))
            if cmd.cog is not None:
                _commands.append(cmd)
        repo = True
        cog = True
        command = True

    IS_WINDOWS = os.name == "nt"
    IS_MAC = sys.platform == "darwin"
    IS_LINUX = sys.platform == "linux"
    if IS_LINUX:
        import distro  # pylint: disable=import-error
    python_executable = sys.executable
    python_version = ".".join(map(str, sys.version_info[:3]))
    pyver = f"{python_version} ({platform.architecture()[0]})"
    pipver = pip.__version__
    redver = red_version_info
    dpy_version = discord.__version__
    if IS_WINDOWS:
        os_info = platform.uname()
        osver = f"{os_info.system} {os_info.release} (version {os_info.version})"
    elif IS_MAC:
        os_info = platform.mac_ver()
        osver = f"Mac OSX {os_info[0]} {os_info[2]}"
    elif IS_LINUX:
        osver = f"{distro.name()} {distro.version()}".strip()
    else:
        osver = "Could not parse OS, report this on Github."
    driver = storage_type()
    data_path_original = Path(basic_config["DATA_PATH"])
    data_path = Path(CogsUtils().replace_var_paths(str(data_path_original)))
    _config_file = Path(CogsUtils().replace_var_paths(str(config_file)))
    python_executable = Path(CogsUtils().replace_var_paths(str(python_executable)))
    disabled_intents = (
        ", ".join(
            intent_name.replace("_", " ").title()
            for intent_name, enabled in ctx.bot.intents
            if not enabled
        )
        or "None"
    )
    uptime = humanize_timedelta(timedelta=datetime.datetime.utcnow() - ctx.bot.uptime)
    async def can_run(command):
        try:
            await command.can_run(ctx, check_all_parents=True, change_permission_state=False)
        except Exception:
            return False
        else:
            return True
    def get_aliases(command, original):
        if alias := list(command.aliases):
            if original in alias:
                alias.remove(original)
                alias.append(command.name)
            return alias
    def get_perms(command):
        final_perms = ""
        def neat_format(x):
            return " ".join(i.capitalize() for i in x.replace("_", " ").split())
        user_perms = []
        if perms := getattr(command.requires, "user_perms"):
            user_perms.extend(neat_format(i) for i, j in perms if j)
        if perms := command.requires.privilege_level:
            if perms.name != "NONE":
                user_perms.append(neat_format(perms.name))
        if user_perms:
            final_perms += "User Permission(s): " + ", ".join(user_perms) + "\n"
        if perms := getattr(command.requires, "bot_perms"):
            if perms_list := ", ".join(neat_format(i) for i, j in perms if j):
                final_perms += "Bot Permission(s): " + perms_list
        return final_perms
    def get_cooldowns(command):
        cooldowns = []
        if s := command._buckets._cooldown:
            txt = f"{s.rate} time{'s' if s.rate>1 else ''} in {humanize_timedelta(seconds=s.per)}"
            try:
                txt += f" per {s.type.name.capitalize()}"
            # This is to avoid custom bucketype erroring out stuff (eg:licenseinfo)
            except AttributeError:
                pass
            cooldowns.append(txt)
        if s := command._max_concurrency:
            cooldowns.append(f"Max concurrent uses: {s.number} per {s.per.name.capitalize()}")
        return cooldowns
    async def get_diagnose(ctx, command):
        issue_diagnoser = IssueDiagnoser(ctx.bot, ctx, ctx.channel, ctx.author, command)
        await issue_diagnoser._prepare()
        diagnose_result = []
        result = await issue_diagnoser._check_until_fail(
            "",
            (
                issue_diagnoser._check_global_call_once_checks_issues,
                issue_diagnoser._check_disabled_command_issues,
                issue_diagnoser._check_can_run_issues,
            ),
        )
        if result.success:
            diagnose_result.append(_("All checks passed and no issues were detected."))
        else:
            diagnose_result.append(_("The bot has been able to identify the issue."))
        details = issue_diagnoser._get_details_from_check_result(result)
        if details:
            diagnose_result.append(bold(_("Detected issue: ")) + details)
        if result.resolution:
            diagnose_result.append(bold(_("Solution: ")) + result.resolution)
        diagnose_result.extend(issue_diagnoser._get_message_from_check_result(result))
        return diagnose_result
    async def get_all_config(cog: commands.Cog):
        config = {}
        if not hasattr(cog, 'config'):
            return config
        try:
            config["global"] = await cog.config.all()
            config["users"] = await cog.config.all_users()
            config["guilds"] = await cog.config.all_guilds()
            config["members"] = await cog.config.all_members()
            config["roles"] = await cog.config.all_roles()
            config["channels"] = await cog.config.all_channels()
        except Exception:
            return config
        return config
    use_emojis = False
    check_emoji = "✅" if use_emojis else True
    cross_emoji = "❌" if use_emojis else False

    ##################################################
    os_table = Table("Key", "Value", title="Host machine informations")
    os_table.add_row("OS version", str(osver))
    os_table.add_row("Python executable", str(python_executable))
    os_table.add_row("Python version", str(pyver))
    os_table.add_row("Pip version", str(pipver))
    raw_os_table_str = no_colour_rich_markup(os_table)
    ##################################################
    red_table = Table("Key", "Value", title="Red instance informations")
    red_table.add_row("Red version", str(redver))
    red_table.add_row("Discord.py version", str(dpy_version))
    red_table.add_row("Instance name", str(instance_name))
    red_table.add_row("Storage type", str(driver))
    red_table.add_row("Disabled intents", str(disabled_intents))
    red_table.add_row("Data path", str(data_path))
    red_table.add_row("Metadata file", str(_config_file))
    red_table.add_row("Uptime", str(uptime))
    red_table.add_row("Global prefixe(s)", str(await ctx.bot.get_valid_prefixes()).replace(f"{ctx.bot.user.id}", "{bot_id}"))
    if ctx.guild is not None:
        if not await ctx.bot.get_valid_prefixes() == await ctx.bot.get_valid_prefixes(ctx.guild):
            red_table.add_row("Guild prefixe(s)", str(await ctx.bot.get_valid_prefixes(ctx.guild)).replace(f"{ctx.bot.user.id}", "{bot_id}"))
    raw_red_table_str = no_colour_rich_markup(red_table)
    ##################################################
    context_table = Table("Key", "Value", title="Context")
    context_table.add_row("Channel type", str(f"discord.{ctx.channel.__class__.__name__}"))
    context_table.add_row("Bot permissions value (guild)", str(ctx.guild.me.guild_permissions.value if ctx.guild is not None else "Not in a guild."))
    context_table.add_row("Bot permissions value (channel)", str(ctx.channel.permissions_for(ctx.guild.me).value if ctx.guild is not None else ctx.channel.permissions_for(ctx.bot.user).value))
    context_table.add_row("User permissions value (guild)", str(ctx.author.guild_permissions.value if ctx.guild is not None else "Not in a guild."))
    context_table.add_row("User permissions value (channel)", str(ctx.channel.permissions_for(ctx.author).value))
    raw_context_table_str = no_colour_rich_markup(context_table)
    ##################################################
    if repo is not None:
        raw_repo_table_str = []
        for repo in _repos:
            if not check_updates:
                cogs_table = Table("Name", "Commit", "Loaded", "Pinned", title=f"Cogs installed for {repo.name}")
            else:
                cogs_table = Table("Name", "Commit", "Loaded", "Pinned", "To update", title=f"Cogs installed for {repo.name}")
            for _cog in installed_cogs[repo.name]:
                _cog = await InstalledCog.convert(ctx, _cog)
                if not check_updates:
                    cogs_table.add_row(str(_cog.name), str(_cog.commit), str(check_emoji if _cog.name in loaded_cogs else cross_emoji), str(check_emoji if _cog.pinned else cross_emoji))
                else:
                    cogs_table.add_row(str(_cog.name), str(_cog.commit), str(check_emoji if _cog.name in loaded_cogs else cross_emoji), str(check_emoji if _cog.pinned else cross_emoji), str(check_emoji if _cog.name in to_update_cogs else cross_emoji))
            raw_repo_table_str.append(no_colour_rich_markup(cogs_table))
    else:
        raw_repo_table_str = None
    ##################################################
    if cog is not None:
        raw_cogs_table_str = []
        for cog in _cogs:
            cog_table = Table("Key", "Value", title=f"Cog {cog.name}")
            cog_table.add_row("Name", str(cog.name))
            cog_table.add_row("Repo name", str(cog.repo_name))
            cog_table.add_row("Hidden", str(check_emoji if cog.hidden else cross_emoji))
            cog_table.add_row("Disabled", str(check_emoji if cog.disabled else cross_emoji))
            cog_table.add_row("Required cogs", str([r for r in cog.required_cogs]))
            cog_table.add_row("Requirements", str([r for r in cog.requirements]))
            cog_table.add_row("Short", str(cog.short))
            cog_table.add_row("Min bot version", str(cog.min_bot_version))
            cog_table.add_row("Max bot version", str(cog.max_bot_version))
            cog_table.add_row("Min python version", str(cog.min_python_version))
            cog_table.add_row("Author", str([a for a in cog.author]))
            cog_table.add_row("Commit", str(cog.commit))
            raw_cog_table_str = no_colour_rich_markup(cog_table)
            raw_cogs_table_str.append(raw_cog_table_str)
    else:
        raw_cogs_table_str = None
    ##################################################
    if command is not None:
        raw_commands_table_str = []
        for command in _commands:
            command_table = Table("Key", "Value", title=f"Command {command.qualified_name}")
            command_table.add_row("Qualified name", str(command.qualified_name))
            command_table.add_row("Cog name", str(command.cog_name))
            command_table.add_row("Short description", str(command.short_doc))
            command_table.add_row("Syntax", str(f"{ctx.clean_prefix}{command.qualified_name} {command.signature}"))
            command_table.add_row("Hidden", str(command.hidden))
            command_table.add_row("Parents", str(command.full_parent_name if not command.full_parent_name == "" else None))
            command_table.add_row("Can see", str(await command.can_see(ctx)))
            command_table.add_row("Can run", str(await can_run(command)))
            command_table.add_row("Params", str(command.clean_params))
            command_table.add_row("Aliases", str(get_aliases(command, command.qualified_name)))
            command_table.add_row("Requires", str(get_perms(command)))
            command_table.add_row("Cooldowns", str(get_cooldowns(command)))
            command_table.add_row("Is on cooldown", str(command.is_on_cooldown(ctx)))
            if ctx.guild is not None:
                diagnose_result = await get_diagnose(ctx, command)
                c = 0
                for x in diagnose_result:
                    c += 1
                    if c == 1:
                        command_table.add_row("Issue Diagnose", str(x))
                    else:
                        command_table.add_row("", str(x).replace("✅", "").replace("❌", ""))
            raw_command_table_str = no_colour_rich_markup(command_table)
            raw_commands_table_str.append(raw_command_table_str)
            cog = command.cog.__class__.__name__ if command.cog is not None else "None"
            if hasattr(ctx.bot, "last_exceptions_cogs") and cog in ctx.bot.last_exceptions_cogs and command.qualified_name in ctx.bot.last_exceptions_cogs[cog]:
                raw_errors_table = []
                error_table = Table("Last error recorded for this command")
                error_table.add_row(str(ctx.bot.last_exceptions_cogs[cog][command.qualified_name][len(ctx.bot.last_exceptions_cogs[cog][command.qualified_name]) - 1]))
                raw_errors_table.append(no_colour_rich_markup(error_table))
            else:
                raw_errors_table = None
    else:
        raw_commands_table_str = None
        raw_errors_table = None
    ##################################################
    if _cogs is not None and len(_cogs) == 1 and _cogs[0] is not None:
        cog = None
        for name, value in ctx.bot.cogs.items():
            if name.lower() == _cogs[0].name.lower():
                cog = value
                break
        if cog is not None:
            config_table = Table(f"All Config for {cog.__class__.__name__}")
            config_table.add_row(str(await get_all_config(cog)))
            raw_config_table_str = no_colour_rich_markup(config_table)
        else:
            raw_config_table_str = None
    else:
        raw_config_table_str = None
    ##################################################

    response = [raw_os_table_str, raw_red_table_str, raw_context_table_str]
    for x in [raw_repo_table_str, raw_cogs_table_str, raw_commands_table_str, raw_errors_table, raw_config_table_str]:
        if x is not None:
            if isinstance(x, typing.List):
                for y in x:
                    response.append(y)
            elif isinstance(x, str):
                response.append(x)
    to_html = to_html_getallfor.replace("{AVATAR_URL}", str(ctx.bot.user.display_avatar) if CogsUtils().is_dpy2 else str(ctx.bot.user.avatar_url)).replace("{BOT_NAME}", str(ctx.bot.user.name)).replace("{REPO_NAME}", str(getattr(_repos[0], "name", None) if all is None else "All")).replace("{COG_NAME}", str(getattr(_cogs[0], "name", None) if all is None else "All")).replace("{COMMAND_NAME}", str(getattr(_commands[0], "qualified_name", None) if all is None else "All"))
    message_html = message_html_getallfor
    end_html = end_html_getallfor
    count_page = 0
    try:
        if page is not None and page - 1 in [0, 1, 2, 3, 4, 5, 6, 7]:
            response = [response[page - 1]]
    except ValueError:
        pass
    for page in response:
        if page is not None:
            count_page += 1
            if count_page == 1:
                to_html += message_html.replace("{MESSAGE_CONTENT}", str(page).replace("```", "").replace("<", "&lt;").replace("\n", "<br>")).replace("{TIMESTAMP}", str(ctx.message.created_at.strftime("%b %d, %Y %I:%M %p")))
            else:
                to_html += message_html.replace('    <div class="chatlog__messages">', '            </div>            <div class="chatlog__message ">').replace("{MESSAGE_CONTENT}", str(page).replace("```", "").replace("<", "&lt;").replace("\n", "<br>")).replace('<span class="chatlog__timestamp">{TIMESTAMP}</span>            ', "")
            if all is None and "Config" not in page:
                for p in pagify(page):
                    p = p.replace("```", "")
                    p = box(p)
                    await ctx.send(p)
    to_html += end_html
    if CogsUtils().check_permissions_for(channel=ctx.channel, user=ctx.me, check=["send_attachments"]):
        await ctx.send(file=text_to_file(text=to_html, filename="diagnostic.html"))

to_html_getallfor = """
<!--
Thanks to @mahtoid for this transcript! It was retrieved from : https://github.com/mahtoid/DiscordChatExporterPy. Then all unnecessary elements were removed and the header was modified.
-->

<!DOCTYPE html>
<html lang="en">

<head>
    <title>Diagnostic</title>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width" />

    <style>
        @font-face {
            font-family: Whitney;
            src: url(https://cdn.jsdelivr.net/gh/mahtoid/DiscordUtils@master/whitney-300.woff);
            font-weight: 300;
        }

        @font-face {
            font-family: Whitney;
            src: url(https://cdn.jsdelivr.net/gh/mahtoid/DiscordUtils@master/whitney-400.woff);
            font-weight: 400;
        }

        @font-face {
            font-family: Whitney;
            src: url(https://cdn.jsdelivr.net/gh/mahtoid/DiscordUtils@master/whitney-500.woff);
            font-weight: 500;
        }

        @font-face {
            font-family: Whitney;
            src: url(https://cdn.jsdelivr.net/gh/mahtoid/DiscordUtils@master/whitney-600.woff);
            font-weight: 600;
        }

        @font-face {
            font-family: Whitney;
            src: url(https://cdn.jsdelivr.net/gh/mahtoid/DiscordUtils@master/whitney-700.woff);
            font-weight: 700;
        }

        body {
            font-family: "Whitney", "Helvetica Neue", Helvetica, Arial, sans-serif;
            font-size: 17px;
        }

        a {
            text-decoration: none;
        }

        .markdown {
            max-width: 100%;
            line-height: 1.3;
            overflow-wrap: break-word;
        }

        .preserve-whitespace {
            white-space: pre-wrap;
        }

        .pre {
            font-family: "Consolas", "Courier New", Courier, monospace;
        }

        .pre--multiline {
            margin-top: 0.25em;
            padding: 0.5em;
            border: 2px solid;
            border-radius: 5px;
        }

        .pre--inline {
            padding: 2px;
            border-radius: 3px;
            font-size: 0.85em;
        }

        .emoji {
            width: 1.25em;
            height: 1.25em;
            margin: 0 0.06em;
            vertical-align: -0.4em;
        }

        .emoji--small {
            width: 1em;
            height: 1em;
        }

        .emoji--large {
            width: 2.8em;
            height: 2.8em;
        }

        /* Chatlog */

        .chatlog {
            max-width: 100%;
        }

        .chatlog__message-group {
            display: grid;
            margin: 0 0.6em;
            padding: 0.9em 0;
            border-top: 1px solid;
            grid-template-columns: auto 1fr;
        }

        .chatlog__timestamp {
            margin-left: 0.3em;
            font-size: 0.75em;
        }

        /* General */

        body {
            background-color: #36393e;
            color: #dcddde;
        }

        a {
            color: #0096cf;
        }

        .pre {
            background-color: #2f3136 !important;
        }

        .pre--multiline {
            border-color: #282b30 !important;
            color: #b9bbbe !important;
        }

        /* Chatlog */

        .chatlog__message-group {
            border-color: rgba(255, 255, 255, 0.1);
        }

        .chatlog__timestamp {
            color: rgba(255, 255, 255, 0.2);
        }

        /* === INFO === */

        .info {
            display: flex;
            max-width: 100%;
            margin: 0 5px 10px 5px;
        }

        .info__bot-icon-container {
            flex: 0;
        }

        .info__bot-icon {
            max-width: 95px;
            max-height: 95px;
        }

        .info__metadata {
            flex: 1;
            margin-left: 10px;

    </style>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/9.15.6/styles/solarized-dark.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/9.15.6/highlight.min.js"></script>
    <script>
        <!--  Code Block Markdown (```lang```) -->
        document.addEventListener('DOMContentLoaded', () => {
            document.querySelectorAll('.pre--multiline').forEach((block) => {
                hljs.highlightBlock(block);
            });
        });
    </script>
</head>
<body>

<div class="info">
<div class="info__bot-icon-container">
    <img class="info__bot-icon" src="{AVATAR_URL}" />
</div>
<div class="info__metadata">
    <div class="info__report-name">Diagnostic</div>

    <div class="info__report-infos">Bot name: {BOT_NAME}</div>
    <div class="info__report-infos">Repo name: {REPO_NAME}</div>
    <div class="info__report-infos">Cog name: {COG_NAME}</div>
    <div class="info__report-infos">Command name: {COMMAND_NAME}</div>
</div>
</div>

<div class="chatlog">
<div class="chatlog__message-group">"""
message_html_getallfor = """    <div class="chatlog__messages">
    <span class="chatlog__timestamp">{TIMESTAMP}</span>            <div class="chatlog__message ">
            <div class="chatlog__content">
<div class="markdown">
    <span class="preserve-whitespace"><div class="pre pre--multiline nohighlight">{MESSAGE_CONTENT}</div></span>

</div>
</div>"""
end_html_getallfor = """

</div>
</div>

</body>
</html>"""
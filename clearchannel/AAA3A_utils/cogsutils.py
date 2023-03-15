from redbot.core import commands  # isort:skip
from redbot.core.bot import Red  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import asyncio
import datetime
import inspect
import logging
import os
import re
import string
from copy import copy
from functools import partial
from pathlib import Path
from random import choice

import aiohttp
from redbot.core import Config
from redbot.core.data_manager import cog_data_path
from redbot.core.utils.menus import start_adding_reactions
from redbot.logging import RotatingFileHandler

from .cog import Cog
from .dev import DevEnv
from .loop import Loop
from .menus import Reactions
from .shared_cog import SharedCog

if discord.version_info.major >= 2:
    from .views import ConfirmationAskView

__all__ = ["CogsUtils"]


def _(untranslated: str) -> str:
    return untranslated


class CogsUtils(commands.Cog):
    """Tools for AAA3A-cogs!"""

    def __init__(
        self, cog: typing.Optional[commands.Cog] = None, bot: typing.Optional[Red] = None
    ) -> None:
        if cog is not None:
            if isinstance(cog, str):
                cog = bot.get_cog(cog)
            self.cog: commands.Cog = cog
            self.bot: Red = self.cog.bot if hasattr(self.cog, "bot") else bot
            self.data_path: Path = cog_data_path(cog_instance=self.cog)
        elif bot is not None:
            self.cog: typing.Optional[commands.Cog] = None
            self.bot: Red = bot
        else:
            self.cog: typing.Optional[commands.Cog] = None
            self.bot: typing.Optional[Red] = None
        self.__authors__: typing.List[str] = ["AAA3A"]
        self.__version__: float = 1.0
        self.__commit__ = ""
        if self.cog is not None:
            if hasattr(self.cog, "__authors__"):
                if isinstance(self.cog.__authors__, typing.List):
                    self.__authors__: typing.List[str] = self.cog.__authors__
                else:
                    self.__authors__: typing.List[str] = [self.cog.__authors__]
                del self.cog.__authors__
            elif hasattr(self.cog, "__author__"):
                if isinstance(self.cog.__author__, typing.List):
                    self.__authors__: typing.List[str] = self.cog.__author__
                else:
                    self.__authors__: typing.List[str] = [self.cog.__author__]
                del self.cog.__author__
            self.cog.__authors__: typing.List[str] = self.__authors__
            if hasattr(self.cog, "__version__"):
                if isinstance(self.cog.__version__, typing.List):
                    self.__version__: float = self.cog.__version__
                del self.cog.__version__
            self.cog.__version__: float = self.__version__
        self.loops: typing.Dict[str, Loop] = {}
        self.views: typing.List[getattr(getattr(discord, "ui", None), "View", None)] = []
        self.repo_name: str = "AAA3A-cogs"
        # if self.cog is not None:
        #     if (
        #         self.cog.qualified_name in self.all_cogs
        #         and self.cog.qualified_name not in self.all_cogs_dpy2
        #     ):
        #         if self.is_dpy2 or redbot.version_info >= redbot.VersionInfo.from_str("3.5.0"):
        #             raise RuntimeError(
        #                 f"{self.cog.qualified_name} needs to be updated to run on dpy2/Red 3.5.0. It's best to use `[p]cog update` with no arguments to update all your cogs, which may be using new dpy2-specific methods."
        #             )

    @property
    def is_dpy2(self) -> bool:
        """
        Returns True if the current redbot instance is running under dpy2.
        """
        return discord.version_info.major >= 2

    def replace_var_paths(self, text: str, reverse: typing.Optional[bool] = False) -> str:
        if not reverse:
            if "USERPROFILE" in os.environ:
                text = text.replace(os.environ["USERPROFILE"], "{USERPROFILE}")
                text = text.replace(os.environ["USERPROFILE"].lower(), "{USERPROFILE}".lower())
                text = text.replace(
                    os.environ["USERPROFILE"].replace("\\", "\\\\"), "{USERPROFILE}"
                )
                text = text.replace(
                    os.environ["USERPROFILE"].replace("\\", "\\\\").lower(), "{USERPROFILE}.lower("
                )
                text = text.replace(os.environ["USERPROFILE"].replace("\\", "/"), "{USERPROFILE}")
                text = text.replace(
                    os.environ["USERPROFILE"].replace("\\", "/").lower(), "{USERPROFILE}".lower()
                )
            if "HOME" in os.environ:
                text = text.replace(os.environ["HOME"], "{HOME}")
                text = text.replace(os.environ["HOME"].lower(), "{HOME}".lower())
                text = text.replace(os.environ["HOME"].replace("\\", "\\\\"), "{HOME}")
                text = text.replace(
                    os.environ["HOME"].replace("\\", "\\\\").lower(), "{HOME}".lower()
                )
            if "USERNAME" in os.environ:
                text = text.replace(os.environ["USERNAME"], "{USERNAME}")
                text = text.replace(os.environ["USERNAME"].lower(), "{USERNAME}".lower())
            if "COMPUTERNAME" in os.environ:
                text = text.replace(os.environ["COMPUTERNAME"], "{COMPUTERNAME}")
                text = text.replace(os.environ["COMPUTERNAME"].lower(), "{COMPUTERNAME}".lower())
        else:
            if "USERPROFILE" in os.environ:
                text = text.replace("{USERPROFILE}", os.environ["USERPROFILE"])
                text = text.replace("{USERPROFILE}".lower(), os.environ["USERPROFILE"].lower())
            if "HOME" in os.environ:
                text = text.replace("{HOME}", os.environ["HOME"])
                text = text.replace("{HOME}".lower(), os.environ["HOME"].lower())
            if "USERNAME" in os.environ:
                text = text.replace("{USERNAME}", os.environ["USERNAME"])
                text = text.replace("{USERNAME}".lower(), os.environ["USERNAME"].lower())
            if "COMPUTERNAME" in os.environ:
                text = text.replace("{COMPUTERNAME}", os.environ["COMPUTERNAME"])
                text = text.replace("{COMPUTERNAME}".lower(), os.environ["COMPUTERNAME"].lower())
        return text

    async def add_cog(
        self, bot: typing.Optional[Red] = None, cog: typing.Optional[commands.Cog] = None
    ) -> commands.Cog:
        """
        Load a cog by checking whether the required function is awaitable or not.
        """
        if bot is None:
            bot = self.bot
        if cog is None:
            cog = self.cog
        await self.change_config_unique_identifier(cog=cog)
        if hasattr(cog, "cogsutils"):
            cog.cogsutils.init_logger()
        value = bot.add_cog(cog)
        if inspect.isawaitable(value):
            await value
        self._setup()
        if not self.is_dpy2 and hasattr(cog, "cog_load"):
            await cog.cog_load()
        return cog

    def _setup(self) -> None:
        """
        Adding additional functionality to the cog.
        """
        if self.cog is None:
            return
        setattr(self.cog, "cogsutils", self)
        self.init_logger()
        Cog._setup(bot=self.bot, cog=self.cog)
        asyncio.create_task(self._await_setup())

    async def _await_setup(self) -> None:
        """
        Adds dev environment values, slash commands add Views.
        """
        await self.bot.wait_until_red_ready()
        DevEnv.add_dev_env_values(bot=self.bot, cog=self.cog)
        try:
            nb_commits, version, commit = await self.get_cog_version()
            if self.__version__ == 1.0:
                self.cog.__version__ = version
            self.cog.__commit__ = commit
        except (self.DownloaderNotLoaded, asyncio.TimeoutError, ValueError):
            pass
        except Exception as e:  # really doesn't matter if this fails so fine with debug level
            self.cog.log.debug(
                f"Something went wrong checking {self.cog.qualified_name} version.",
                exc_info=e,
            )
        try:
            (
                to_update,
                local_commit,
                online_commit,
                online_commit_for_each_files,
            ) = await self.to_update()
            if to_update and False:
                self.cog.log.warning(
                    f"Your {self.cog.qualified_name} cog, from {self.repo_name}, is out of date. You can update your cogs with the '[p]cog update' command in Discord."
                )
            else:
                self.cog.log.debug(f"{self.cog.qualified_name} cog is up to date.")
        except (
            self.DownloaderNotLoaded,
            asyncio.TimeoutError,
            ValueError,
            asyncio.LimitOverrunError,
        ):
            pass
        except Exception as e:  # really doesn't matter if this fails so fine with debug level
            self.cog.log.debug(
                f"Something went wrong checking if {self.cog.qualified_name} cog is up to date.",
                exc_info=e,
            )
        if self.cog.qualified_name != "AAA3A_utils":
            try:
                old_cog = self.bot.get_cog("AAA3A_utils")
                if self.is_dpy2:
                    await self.bot.remove_cog("AAA3A_utils")
                else:
                    self.bot.remove_cog("AAA3A_utils")
                cog = SharedCog(self.bot, CogsUtils)
                try:
                    if getattr(old_cog, "sentry", None) is not None:
                        cog.sentry = old_cog.sentry
                        cog.sentry.cog = cog
                        cog.sentry.cogsutils = cog.cogsutils
                    cog.cogsutils.loops = old_cog.cogsutils.loops
                except AttributeError:
                    pass
                await cog.cogsutils.add_cog(bot=self.bot, cog=cog)
            except Exception as e:
                self.cog.log.debug("Error when adding the AAA3A_utils cog.", exc_info=e)
        if hasattr(self.cog, "settings") and hasattr(self.cog.settings, "commands_added"):
            await self.cog.settings.commands_added.wait()
        AAA3A_utils = self.bot.get_cog("AAA3A_utils")
        if AAA3A_utils is not None:
            if await AAA3A_utils.check_if_slash(self.cog):
                try:
                    await self.add_hybrid_commands()
                except Exception as e:
                    self.cog.log.error(
                        f"Error when adding [hybrid|slash] commands from the {self.cog.qualified_name} cog.",
                        exc_info=e,
                    )
            await AAA3A_utils.sentry.maybe_send_owners(self.cog)

    def _end(self) -> None:
        """
        Removes dev environment values, slash commands and Views.
        """
        self.close_logger()
        DevEnv.remove_dev_env_values(bot=self.bot, cog=self.cog)
        loops = dict(self.loops.items())
        for loop in loops:
            if self.cog.qualified_name == "AAA3A_utils" and loop == "Sentry Helper":
                continue
            self.loops[loop].stop_all()
        for view in self.views:
            view.stop()
            try:
                self.bot.persistent_views.remove(view)
            except ValueError:
                pass
        self.views.clear()
        asyncio.create_task(self._await_end())

    async def _await_end(self) -> None:
        AAA3A_utils = self.bot.get_cog("AAA3A_utils")
        if AAA3A_utils is not None:
            if getattr(AAA3A_utils, "sentry", None) is not None:
                await AAA3A_utils.sentry.cog_unload(self.cog)
            if not self.at_least_one_cog_loaded():
                try:
                    AAA3A_utils.cogsutils.loops["Sentry Helper"].stop_all()
                except ValueError:
                    pass
                if self.is_dpy2:
                    await self.bot.remove_cog("AAA3A_utils")
                else:
                    self.bot.remove_cog("AAA3A_utils")

    def init_logger(self, name: typing.Optional[str] = None) -> logging.Logger:
        """
        Prepare the logger for the cog.
        Thanks to @laggron42 on GitHub! (https://github.com/laggron42/Laggron-utils/blob/master/laggron_utils/logging.py)
        """
        if name is not None or self.cog is None:
            return (
                logging.getLogger(f"{name}")
                if name.startswith("red.")
                else logging.getLogger(f"red.{self.repo_name}.{name}")
            )
        if hasattr(self.cog, "log") and (isinstance(self.cog.log, (partial, logging.Logger))):
            return self.cog.log
        self.cog.log = logging.getLogger(f"red.{self.repo_name}.{self.cog.qualified_name}")

        __log = partial(logging.Logger._log, self.cog.log)

        def _log(level, msg, args, exc_info=None, extra=None, stack_info=False, stacklevel=1):
            if self.cog is not None:
                if not hasattr(self.cog, "logs") or not isinstance(self.cog.logs, typing.Dict):
                    self.cog.logs: typing.Dict[typing.Union[str, int], typing.Dict] = {}
                from logging import CRITICAL, DEBUG, ERROR, FATAL, INFO, WARN, WARNING

                VERBOSE = DEBUG - 3
                TRACE = DEBUG - 5
                levels = {
                    CRITICAL: "CRITICAL",
                    DEBUG: "DEBUG",
                    ERROR: "ERROR",
                    FATAL: "FATAL",
                    INFO: "INFO",
                    WARN: "WARN",
                    WARNING: "WARNING",
                    VERBOSE: "VERBOSE",
                    TRACE: "TRACE",
                }
                _level = levels.get(level, str(level))
                if _level not in self.cog.logs:
                    self.cog.logs[_level] = []
                self.cog.logs[_level].append(
                    {
                        "time": datetime.datetime.now(),
                        "level": level,
                        "message": msg,
                        "args": args,
                        "exc_info": exc_info,
                        "levelname": _level,
                    }
                )
            __log(
                level=level,
                msg=msg,
                args=args,
                exc_info=exc_info,
                extra=extra,
                stack_info=stack_info,
                stacklevel=stacklevel,
            )

        setattr(self.cog.log, "_log", _log)

        # logging to a log file.
        # (File is automatically created by the module, if the parent foler exists.)
        try:
            cog_path = cog_data_path(cog_instance=self.cog, raw_name=self.cog.qualified_name)
            formatter = logging.Formatter(
                "[{asctime}] {levelname} [{name}] {message}",
                datefmt="%Y-%m-%d %H:%M:%S",
                style="{",
            )
            if cog_path.exists():
                file_handler = RotatingFileHandler(
                    stem=self.cog.qualified_name,
                    directory=cog_path,
                    maxBytes=1_000_0,
                    backupCount=0,
                    encoding="utf-8",
                )
                # file_handler.doRollover()
                file_handler.setLevel(logging.DEBUG)
                file_handler.setFormatter(formatter)
                self.cog.log.addHandler(file_handler)
        except Exception as e:
            self.cog.log.debug("Error when initiating the logger in a separate file.", exc_info=e)
        return self.cog.log

    def close_logger(self) -> None:
        """
        Closes the files for the logger of a cog.
        """
        if not hasattr(self.cog, "log") or not isinstance(self.cog.log, logging.Logger):
            return
        for handler in self.cog.log.handlers:
            handler.close()
        self.cog.log.handlers = []

    async def get_cog_version(
        self, cog: typing.Optional[typing.Union[commands.Cog, str]] = None
    ) -> typing.Tuple[int, float, str]:
        if cog is None:
            cog = self.cog
        cog_name = cog.lower() if isinstance(cog, str) else cog.qualified_name.lower()
        downloader = self.bot.get_cog("Downloader")
        if downloader is None:
            raise self.DownloaderNotLoaded("The Downloader cog is not loaded.")

        if await self.bot._cog_mgr.find_cog(cog_name) is None:
            raise ValueError("This cog was not found in any cog path.")

        from redbot.cogs.downloader.repo_manager import ProcessFormatter, Repo

        repo = None
        path = Path(inspect.getsourcefile(cog.__class__))
        if not path.parent.parent == (await self.bot._cog_mgr.install_path()):
            local = None
            repo = Repo(name="", url="", branch="", commit="", folder_path=path.parent.parent)
        else:
            local = discord.utils.get(await downloader.installed_cogs(), name=cog_name)
            if local is not None:
                repo = local.repo
        if repo is None:
            raise ValueError("This cog is not installed on this bot with Downloader.")

        exists, __ = repo._existing_git_repo()
        if not exists:
            raise ValueError(f"A git repo does not exist at path: {repo.folder_path}")
        git_command = ProcessFormatter().format(
            "git -C {path} rev-list HEAD --count {cog_name}",
            path=repo.folder_path,
            cog_name=cog_name,
        )
        p = await repo._run(git_command)
        if p.returncode != 0:
            raise asyncio.IncompleteReadError(
                "No results could be retrieved from the git command.", None
            )
        nb_commits = p.stdout.decode(encoding="utf-8").strip()
        nb_commits = int(nb_commits)

        version = round(1.0 + (nb_commits / 100), 2)

        if local is not None:
            commit = local.commit
        else:
            git_command = ProcessFormatter().format(
                "git -C {path} log HEAD -1 {cog_name}", path=repo.folder_path, cog_name=cog_name
            )
            p = await repo._run(git_command)
            if p.returncode != 0:
                raise asyncio.IncompleteReadError(
                    "No results could be retrieved from the git command.", None
                )
            commit = p.stdout.decode(encoding="utf-8").strip()
            commit = commit.split("\n")[0][7:]

        return nb_commits, version, commit

    async def to_update(
        self,
        cog: typing.Optional[typing.Union[commands.Cog, str]] = None,
        repo_url: typing.Optional[str] = None,
    ) -> typing.Tuple[bool, str, str]:
        if cog is None:
            cog = self.cog
        cog_name = cog.lower() if isinstance(cog, str) else cog.qualified_name.lower()
        if repo_url is None:
            downloader = self.bot.get_cog("Downloader")
            if downloader is None:
                raise self.DownloaderNotLoaded("The cog downloader is not loaded.")

            if await self.bot._cog_mgr.find_cog(cog_name) is None:
                raise ValueError("This cog was not found in any cog path.")

            local = discord.utils.get(await downloader.installed_cogs(), name=cog_name)
            if local is None:
                raise ValueError("This cog is not installed on this bot with Downloader.")
            local_commit = local.commit
            repo = local.repo
            if repo is None:
                raise ValueError("This cog is not installed on this bot with Downloader.")
            repo_url = repo.url
        else:
            cog = None
            cog_name = None

        if isinstance(repo_url, str):
            repo_owner, repo_name, repo_branch = (
                re.compile(
                    r"(?:https?:\/\/)?git(?:hub|lab).com\/(?P<repo_owner>[A-z0-9-_.]*)\/(?P<repo>[A-z0-9-_.]*)(?:\/tree\/(?P<repo_branch>[A-z0-9-_.]*))?",
                    re.I,
                ).findall(repo_url)
            )[0]
        else:
            repo_owner, repo_name, repo_branch = repo_url
            repo_branch = repo_branch or repo.branch
        async with aiohttp.ClientSession() as session:
            async with session.get(
                (
                    f"https://api.github.com/repos/{repo_owner}/{repo_name}/contents?ref={repo_branch}"
                    if repo_branch
                    else f"https://api.github.com/repos/{repo_owner}/{repo_name}/contents"
                ),  # f"https://api.github.com/repos/{repo_owner}/{repo_name}/git/refs/heads/{repo_branch}",
                timeout=3,
            ) as r:
                online = await r.json()
        if (
            isinstance(online, typing.Dict)
            and "message" in online
            and "API rate limit exceeded" in online["message"]
        ):
            raise asyncio.LimitOverrunError("API rate limit exceeded.", 47)
        if online is None or not isinstance(online, typing.List):
            raise asyncio.IncompleteReadError(
                "No results could be retrieved from the git API.", None
            )
        online_commit_for_each_files = {
            file["name"]: file["sha"] for file in online if file["type"] in ["dir", "file"]
        }
        if cog is None and cog_name is None:
            return online_commit_for_each_files

        if cog_name not in online_commit_for_each_files:
            raise asyncio.IncompleteReadError(
                "No results could be retrieved from the git API.", None
            )
        online_commit = online_commit_for_each_files[cog_name]

        # async with aiohttp.ClientSession() as session:
        #     async with session.get(
        #         f"https://api.github.com/repos/{repo_owner}/{repo_name}/git/refs/heads/{repo_branch}",
        #         timeout=3,
        #     ) as r:
        #         online = await r.json()
        # if online is None or not isinstance(online, typing.Dict) or "object" not in online or "sha" not in online["object"]:
        #     raise asyncio.IncompleteReadError("No results could be retrieved from the git api.", None)
        # online_commit = online["object"]["sha"]

        # async with aiohttp.ClientSession() as session:
        #     async with session.get(
        #         f"https://api.github.com/repos/{repo_owner}/{repo_name}/compare/{local_commit}...{online_commit}",
        #         timeout=3,
        #     ) as r:
        #         compare = await r.json()
        # if compare is None or not isinstance(compare, typing.Dict) or "files" not in compare or not isinstance(compare["files"], typing.List):
        #     raise asyncio.IncompleteReadError("No results could be retrieved from the git api.", None)
        # to_update = True
        # if len(compare["files"]) == 0:
        #     to_update = False
        # files_diff = [file["filename"] for file in compare["files"]]
        # cogs_diff = [cog.split("/")[0] for cog in files_diff]
        # if cog_name not in cogs_diff:
        #     to_update = False
        to_update = local_commit != online_commit

        return to_update, local_commit, online_commit  # , online_commit_for_each_files

    async def add_hybrid_commands(self, cog: typing.Optional[commands.Cog] = None) -> None:
        if cog is None:
            cog = self.cog
        if cog.qualified_name == "Medicat" and hasattr(cog, "CC_added"):
            await cog.CC_added.wait()
        # For new `[p]slash list` in Flame's PR.
        # for _object in cog.walk_commands():
        #     if isinstance(_object, commands.HybridCommand):
        #         if _object.app_command is not None:
        #             _object.app_command.description = _object.app_command.description[:200]
        # await self.remove_hybrid_commands(cog=cog)
        AAA3A_utils = self.bot.get_cog("AAA3A_utils")
        if AAA3A_utils is not None:
            ignored_commands = await AAA3A_utils.config.ignored_slash_commands()
        else:
            ignored_commands = []
        for _object in cog.walk_commands():
            if getattr(_object, "app_command", None) is not None and getattr(_object, "app_command", None) is not discord.utils.MISSING:
                continue
            if getattr(_object, "no_slash", False):
                continue
            if _object.parent is None:
                if _object.qualified_name in ignored_commands:
                    continue
            elif _object.parents[0].qualified_name in ignored_commands:
                continue
            if isinstance(_object, commands.HybridGroup):
                _object.with_app_command = True
                guild_ids = getattr(
                    _object.callback, "__discord_app_commands_default_guilds__", None
                )
                guild_only = getattr(
                    _object.callback, "__discord_app_commands_guild_only__", False
                )
                default_permissions = getattr(
                    _object.callback, "__discord_app_commands_default_permissions__", None
                )
                nsfw = getattr(_object.callback, "__discord_app_commands_is_nsfw__", False)
                _object.app_command = discord.app_commands.Group(
                    name=(_object._locale_name or _object.name).lower(),
                    description=_object._locale_description
                    or _object.description
                    or _object.short_doc
                    or "…",
                    guild_ids=guild_ids,
                    guild_only=guild_only,
                    default_permissions=default_permissions,
                    nsfw=nsfw,
                )
                _object.app_command.parent = (
                    _object.parent.app_command if _object.parent is not None else None
                )
                _object.app_command.module = _object.module
                _object.app_command.description = _object.app_command.description[:100]
            elif isinstance(_object, commands.HybridCommand):
                _object.with_app_command = True
                _object.app_command = discord.ext.commands.hybrid.HybridAppCommand(_object)
                _object.app_command.description = _object.app_command.description[:100]
                for param in _object.app_command._params:
                    if hasattr(cog, f"{_object.name}_{param}_autocomplete"):
                        setattr(
                            cog,
                            f"{_object.name}_{param}_autocomplete",
                            _object.autocomplete(param)(
                                getattr(cog, f"{_object.name}_{param}_autocomplete")
                            ),
                        )
            else:
                continue
            if hasattr(cog, "_cogsutils_add_hybrid_commands"):
                await cog._cogsutils_add_hybrid_commands(_object)
            if _object.parent is not None:
                if getattr(_object.parent, "no_slash", False):
                    continue
                if not _object.parent.invoke_without_command:
                    _object.checks.extend(_object.parent.checks)
                _object.parent.app_command.remove_command(_object.app_command.name)
                _object.parent.app_command.add_command(_object.app_command)
            else:
                self.bot.tree.remove_command(_object.app_command.name)
                self.bot.tree.add_command(_object.app_command)

    async def remove_hybrid_commands(self, cog: typing.Optional[commands.Cog] = None) -> None:
        if cog is None:
            cog = self.cog
        for _object in cog.walk_commands():
            if getattr(_object, "app_command", None) is None:
                continue
            if getattr(_object, "no_slash", False):
                continue
            if isinstance(_object, discord.ext.commands.HybridGroup):
                _object.with_app_command = False
                _object.app_command = None
            elif isinstance(_object, discord.ext.commands.HybridCommand):
                _object.with_app_command = False
                _object.app_command = None
            else:
                continue
            if _object.parent is None:
                self.bot.tree.remove_command(_object.name)

    async def change_config_unique_identifier(
        self, cog: typing.Optional[commands.Cog] = None
    ) -> typing.Union[
        bool, typing.Tuple[bool, typing.Dict[str, typing.Any], typing.Dict[str, typing.Any]]
    ]:
        try:
            if cog is None:
                cog = self.cog
            cogs_with_old_config_custom_ids = {
                "AntiNuke": 947269490247,
                "Calculator": 905683670375,
                "ClearChannel": 837018163805,
                "CmdChannel": 793502759720,
                "DiscordModals": 897374386384,
                "DropdownsTexts": 985347935839,
                "Ip": 969369062738,
                "Medicat": 953864285308,
                "MemberPrefix": 647053803629,
                "ReactToCommand": 703485369742,
                "RolesButtons": 370638632963,
                "Seen": 864398642893,
                "SimpleSanction": 793615829052,
                "TicketTool": 937480369417,
                "UrlButtons": 974269742704,
            }
            if cog.qualified_name not in cogs_with_old_config_custom_ids:
                return False
            if not hasattr(cog, "config"):
                return False
            old_config: Config = Config.get_conf(
                cog,
                identifier=cogs_with_old_config_custom_ids[cog.qualified_name],
                force_registration=True,
            )
            new_config: Config = Config.get_conf(
                cog, identifier=205192943327321000143939875896557571750, force_registration=True
            )
            old_config_all = {}
            new_config_all = {}
            for base_group in [
                old_config.GLOBAL,
                old_config.USER,
                old_config.MEMBER,
                old_config.ROLE,
                old_config.CHANNEL,
                old_config.GUILD,
            ]:
                old_config_all[base_group] = await old_config._get_base_group(base_group).all()
                if old_config_all[base_group] == {}:
                    del old_config_all[base_group]
                new_config_all[base_group] = await new_config._get_base_group(base_group).all()
                if new_config_all[base_group] == {}:
                    new_config_all[base_group] = new_config._defaults.get(base_group, None)
                if new_config_all[base_group] is None:
                    del new_config_all[base_group]
            if old_config_all == old_config._defaults or new_config_all != new_config._defaults:
                return False
            for base_group in [
                old_config.GLOBAL,
                old_config.USER,
                old_config.MEMBER,
                old_config.ROLE,
                old_config.CHANNEL,
                old_config.GUILD,
            ]:
                data = old_config_all.get(base_group, {})
                if data == {}:
                    continue
                if data == old_config._defaults.get(base_group, {}):
                    continue
                await new_config._get_base_group(base_group).set(data)
            old_config_all = {}
            new_config_all = {}
            for base_group in [
                old_config.GLOBAL,
                old_config.USER,
                old_config.MEMBER,
                old_config.ROLE,
                old_config.CHANNEL,
                old_config.GUILD,
            ]:
                old_config_all[base_group] = await old_config._get_base_group(base_group).all()
                if old_config_all[base_group] == {}:
                    del old_config_all[base_group]
                new_config_all[base_group] = await new_config._get_base_group(base_group).all()
                if new_config_all[base_group] == {}:
                    new_config_all[base_group] = new_config._defaults.get(base_group, None)
                if new_config_all[base_group] is None:
                    del new_config_all[base_group]
            await old_config.clear_all()
        except Exception as e:
            self.cog.log.error(
                f"Error in the {self.cog.qualified_name} cog's Config unique identifier change.",
                exc_info=e,
            )
        else:
            self.cog.log.info(
                f"The Config unique identifier has been successfully modified for the {self.cog.qualified_name} cog."
            )
        return True, old_config, new_config

    async def ConfirmationAsk(
        self,
        ctx: commands.Context,
        *args,
        timeout: typing.Optional[int] = 60,
        timeout_message: typing.Optional[str] = _("Timed out, please try again"),
        way: typing.Optional[
            typing.Literal["buttons", "dropdown", "reactions", "message"]
        ] = "buttons",
        delete_message: typing.Optional[bool] = True,
        members_authored: typing.Optional[typing.Iterable[discord.Member]] = [],
        **kwargs,
    ) -> bool:
        """
        Allow confirmation to be requested from the user, in the form of buttons/dropdown/reactions/message, with many additional options.
        """
        check_owner = True
        reactions = ["✅", "✖️"]
        if way in ["buttons", "dropdown"] and not self.is_dpy2:
            way = "reactions"

        if way == "buttons":
            return await ConfirmationAskView(
                ctx=ctx,
                timeout=timeout,
                timeout_message=timeout_message,
                delete_message=delete_message,
                members=members_authored,
            ).start(*args, **kwargs)

        elif way == "reactions":
            message = await ctx.send(*args, **kwargs)
            try:
                start_adding_reactions(message, reactions)
            except discord.HTTPException:
                way = "message"
            view = Reactions(
                bot=ctx.bot,
                message=message,
                remove_reaction=False,
                timeout=timeout,
                reactions=reactions,
                members=[ctx.author.id] + list(ctx.bot.owner_ids)
                if check_owner
                else [] + [x.id for x in members_authored],
            )
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

        elif way == "message":
            message = await ctx.send(*args, **kwargs)

            def check(msg):
                if check_owner:
                    return (
                        msg.author.id == ctx.author.id
                        or msg.author.id in ctx.bot.owner_ids
                        or msg.author.id in [x.id for x in members_authored]
                        and msg.channel == ctx.channel
                        and msg.content in ("yes", "y", "no", "n")
                    )
                else:
                    return (
                        msg.author.id == ctx.author.id
                        or msg.author.id in [x.id for x in members_authored]
                        and msg.channel == ctx.channel
                        and msg.content in ("yes", "y", "no", "n")
                    )

            try:
                end_reaction = False
                msg = await ctx.bot.wait_for("message", timeout=timeout, check=check)
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

    async def delete_message(
        self, message: discord.Message, delay: typing.Optional[float] = None
    ) -> bool:
        """
        Delete a message, ignoring any exceptions.
        Easier than putting these 3 lines at each message deletion for each cog.
        """
        if message is None:
            return None
        try:
            await message.delete(delay=delay)
        except discord.NotFound:  # Already deleted.
            return True
        except discord.HTTPException:
            return False
        else:
            return True

    async def invoke_command(
        self,
        author: discord.User,
        channel: discord.TextChannel,
        command: str,
        prefix: typing.Optional[str] = None,
        message: typing.Optional[discord.Message] = None,
        dispatch_message: typing.Optional[bool] = False,
        __is_mocked__: typing.Optional[bool] = True,
        message_id: typing.Optional[str] = "".join(choice(string.digits) for i in range(18)),
        timestamp: typing.Optional[datetime.datetime] = datetime.datetime.now(),
    ) -> typing.Union[commands.Context, discord.Message]:
        """
        Invoke the specified command with the specified user in the specified channel.
        """
        bot = self.bot
        if prefix == "/":  # For hybrid and slash commands.
            prefix = None
        if prefix is None:
            prefixes = await bot.get_valid_prefixes(guild=channel.guild)
            prefix = prefixes[0] if len(prefixes) < 3 else prefixes[2]
        old_content = f"{command}"
        content = f"{prefix}{old_content}"

        if message is None:
            message_content = content
            author_dict = {
                "id": f"{author.id}",
                "username": author.display_name,
                "avatar": author.avatar,
                "avatar_decoration": None,
                "discriminator": f"{author.discriminator}",
                "public_flags": author.public_flags,
                "bot": author.bot,
            }
            channel_id = channel.id
            timestamp = str(timestamp).replace(" ", "T") + "+00:00"
            data = {
                "id": message_id,
                "type": 0,
                "content": message_content,
                "channel_id": f"{channel_id}",
                "author": author_dict,
                "attachments": [],
                "embeds": [],
                "mentions": [],
                "mention_roles": [],
                "pinned": False,
                "mention_everyone": False,
                "tts": False,
                "timestamp": timestamp,
                "edited_timestamp": None,
                "flags": 0,
                "components": [],
                "referenced_message": None,
            }
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
            if __is_mocked__:
                context.__is_mocked__ = True
            await bot.invoke(context)
        else:
            if dispatch_message:
                message.content = old_content
                message.author = author
                message.channel = channel
                bot.dispatch("message", message)
        return context if context.valid else message

    async def get_hook(self, channel: discord.TextChannel) -> discord.Webhook:
        """
        Create a discord.Webhook object. It tries to retrieve an existing webhook created by the bot or to create it itself.
        """
        hook = next(
            (
                webhook
                for webhook in await channel.webhooks()
                if webhook.user.id == self.bot.user.id
            ),
            None,
        )
        if hook is None:
            hook = await channel.create_webhook(name=f"red_bot_hook_{str(channel.id)}")
        return hook

    def get_embed(
        self, embed_dict: typing.Dict
    ) -> typing.Dict[str, typing.Union[discord.Embed, str]]:
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
            raise commands.BadArgument(f"An error has occurred.\n{e}).")
        return {"embed": embed, "content": content}

    def datetime_to_timestamp(
        self,
        dt: datetime.datetime,
        format: typing.Literal["f", "F", "d", "D", "t", "T", "R"] = "f",
    ) -> str:
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

    def check_permissions_for(
        self,
        channel: typing.Union[discord.TextChannel, discord.VoiceChannel, discord.DMChannel],
        user: discord.User,
        check: typing.Union[typing.List, typing.Dict],
    ) -> bool:
        """
        Check all permissions specified as an argument.
        """
        if getattr(channel, "guild", None) is None:
            return True
        permissions = channel.permissions_for(user)
        if isinstance(check, typing.List):
            new_check = {p: True for p in check}
            check = new_check
        return not any(
            getattr(permissions, f"{p}", None)
            and (
                check[p]
                and not getattr(permissions, f"{p}")
                or not check[p]
                and getattr(permissions, f"{p}")
            )
            for p in check
        )

    def create_loop(
        self,
        function,
        name: typing.Optional[str] = None,
        days: typing.Optional[int] = 0,
        hours: typing.Optional[int] = 0,
        minutes: typing.Optional[int] = 0,
        seconds: typing.Optional[int] = 0,
        function_kwargs: typing.Optional[typing.Dict] = None,
        wait_raw: typing.Optional[bool] = False,
        limit_count: typing.Optional[int] = None,
        limit_date: typing.Optional[datetime.datetime] = None,
        limit_exception: typing.Optional[int] = None,
    ) -> Loop:
        """
        Create a loop like Loop, but with default values and loop object recording functionality.
        """
        if function_kwargs is None:
            function_kwargs = {}
        if name is None:
            name = f"{self.cog.qualified_name}"
        if (
            datetime.timedelta(
                days=days, hours=hours, minutes=minutes, seconds=seconds
            ).total_seconds()
            == 0
        ):
            seconds = 900  # 15 minutes
        loop = Loop(
            cogsutils=self,
            name=name,
            function=function,
            days=days,
            hours=hours,
            minutes=minutes,
            seconds=seconds,
            function_kwargs=function_kwargs,
            wait_raw=wait_raw,
            limit_count=limit_count,
            limit_date=limit_date,
            limit_exception=limit_exception,
        )
        if f"{loop.name}" in self.loops:
            self.loops[f"{loop.name}"].stop_all()
        self.loops[f"{loop.name}"] = loop
        return loop

    def get_all_repo_cogs_objects(self) -> typing.Dict[str, commands.Cog]:
        """
        Get a dictionary containing the objects or None of all my cogs.
        """
        cogs = {}
        for cog in self.bot.cogs.values():
            if cog.qualified_name in ["CogGuide"]:
                continue
            if (
                hasattr(cog, "cogsutils")
                and getattr(cog.cogsutils, "repo_name", None) == "AAA3A-cogs"
                and (f"{cog.qualified_name}" not in cogs or cogs[f"{cog.qualified_name}"] is None)
            ):
                cogs[f"{cog.qualified_name}"] = cog
        return cogs

    def at_least_one_cog_loaded(self) -> bool:
        """
        Return True if at least one cog of all my cogs is loaded.
        """
        return any(object is not None for object in self.get_all_repo_cogs_objects().values())

    def add_all_dev_env_values(self) -> None:
        """
        Add values to the development environment for all my loaded cogs. Not really useful anymore, now that my cogs use AAA3A_utils.
        """
        cogs = self.get_all_repo_cogs_objects()
        for cog in cogs:
            if cogs[cog] is not None:
                try:
                    DevEnv.add_dev_env_values(bot=self.bot, cog=cogs[cog], force=True)
                except Exception:
                    pass

    def generate_key(
        self,
        number: typing.Optional[int] = 10,
        existing_keys: typing.Optional[typing.Union[typing.List, typing.Set]] = None,
        strings_used: typing.Optional[typing.List] = None,
    ) -> str:
        """
        Generate a secret key, with the choice of characters, the number of characters and a list of existing keys.
        """
        if existing_keys is None:
            existing_keys = []
        if strings_used is None:
            strings_used = {
                "ascii_lowercase": True,
                "ascii_uppercase": False,
                "digits": True,
                "punctuation": False,
                "others": [],
            }
        strings = []
        if "ascii_lowercase" in strings_used and strings_used["ascii_lowercase"]:
            strings += string.ascii_lowercase
        if "ascii_uppercase" in strings_used and strings_used["ascii_uppercase"]:
            strings += string.ascii_uppercase
        if "digits" in strings_used and strings_used["digits"]:
            strings += string.digits
        if "punctuation" in strings_used and strings_used["punctuation"]:
            strings += string.punctuation
        if "others" in strings_used and isinstance(strings_used["others"], typing.List):
            strings += strings_used["others"]
        while True:
            # This probably won't turn into an endless loop.
            key = "".join(choice(strings) for _ in range(number))
            if key not in existing_keys:
                return key

    async def check_in_listener(
        self, output, allowed_by_whitelist_blacklist: typing.Optional[bool] = True
    ) -> bool:
        """
        Check all parameters for the output of any listener.
        Thanks to Jack! (https://discord.com/channels/133049272517001216/160386989819035648/825373605000511518)
        """
        try:
            if isinstance(output, discord.Message):
                # check whether the message was sent by a webhook
                if output.webhook_id is not None:
                    raise discord.ext.commands.BadArgument()
                # check whether the message was sent in a guild
                if output.guild is None:
                    raise discord.ext.commands.BadArgument()
                # check whether the message author isn't a bot
                if output.author is None:
                    raise discord.ext.commands.BadArgument()
                if output.author.bot:
                    raise discord.ext.commands.BadArgument()
                # check whether the bot can send messages in the given channel
                if output.channel is None:
                    raise discord.ext.commands.BadArgument()
                if not self.check_permissions_for(
                    channel=output.channel, user=output.guild.me, check=["send_messages"]
                ):
                    raise discord.ext.commands.BadArgument()
                # check whether the cog isn't disabled
                if self.cog is not None and await self.bot.cog_disabled_in_guild(
                    self.cog, output.guild
                ):
                    raise discord.ext.commands.BadArgument()
                # check whether the channel isn't on the ignore list
                if not await self.bot.ignored_channel_or_guild(output):
                    raise discord.ext.commands.BadArgument()
                # check whether the message author isn't on allowlist/blocklist
                if (
                    allowed_by_whitelist_blacklist
                    and not await self.bot.allowed_by_whitelist_blacklist(output.author)
                ):
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
                if not self.check_permissions_for(
                    channel=output.channel, user=output.guild.me, check=["send_messages"]
                ):
                    raise discord.ext.commands.BadArgument()
                # check whether the cog isn't disabled
                if self.cog is not None and await self.bot.cog_disabled_in_guild(
                    self.cog, output.guild
                ):
                    raise discord.ext.commands.BadArgument()
                # check whether the channel isn't on the ignore list
                if not await self.bot.ignored_channel_or_guild(output):
                    raise discord.ext.commands.BadArgument()
                # check whether the message author isn't on allowlist/blocklist
                if (
                    allowed_by_whitelist_blacklist
                    and not await self.bot.allowed_by_whitelist_blacklist(output.author)
                ):
                    raise discord.ext.commands.BadArgument()
            if self.is_dpy2 and isinstance(output, discord.Interaction):
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
                if not self.check_permissions_for(
                    channel=output.channel, user=output.guild.me, check=["send_messages"]
                ):
                    raise discord.ext.commands.BadArgument()
                    # check whether the cog isn't disabled
                if self.cog is not None and await self.bot.cog_disabled_in_guild(
                    self.cog, output.guild
                ):
                    raise discord.ext.commands.BadArgument()
                    # check whether the message author isn't on allowlist/blocklist
                if (
                    allowed_by_whitelist_blacklist
                    and not await self.bot.allowed_by_whitelist_blacklist(output.author)
                ):
                    raise discord.ext.commands.BadArgument()
        except commands.BadArgument:
            return False
        return True

    class DownloaderNotLoaded(Exception):
        pass

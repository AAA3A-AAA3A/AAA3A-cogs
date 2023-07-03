from AAA3A_utils import Cog, CogsUtils, Menu  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
from redbot.core.bot import Red  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import datetime
import logging
import re

from collections import Counter
from colorama import Fore
from dataclasses import dataclass

from redbot import __version__ as red_version
from redbot.core import data_manager
from redbot.core.utils.chat_formatting import box, humanize_list, pagify
try:
    from redbot.core._events import INTRO
except ModuleNotFoundError:  # Lemon's fork.
    INTRO = ""

from rich import box as rich_box
from rich.table import Table
from rich.columns import Columns
from rich.panel import Panel

from .dashboard_integration import DashboardIntegration

# Credits:
# General repo credits.
# Thanks to Tobotimus for the part to get logs files lines (https://github.com/Tobotimus/Tobo-Cogs/blob/V3/errorlogs/errorlogs.py).

_ = Translator("ConsoleLogs", __file__)

LATEST_LOG_RE = re.compile(r"latest(?:-part(?P<part>\d+))?\.log")
CONSOLE_LOG_RE = re.compile(r"^\[(?P<time_str>.*?)\] \[(?P<level>.*?)\] (?P<logger_name>.*?): (?P<message>.*)")


@dataclass(frozen=False)
class ConsoleLog:
    time: datetime.datetime
    time_timestamp: int
    time_str: str
    level: typing.Literal["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "TRACE", "NODE"]
    logger_name: str
    message: str
    display_without_informations: bool = False

    @property
    def logger(self) -> logging.Logger:
        return logging.getLogger(self.logger_name)

    def __str__(self, with_ansi: bool = False, with_extra_break_line: bool = True) -> str:
        if self.display_without_informations:
            return self.message
        BREAK_LINE = "\n"
        if not with_ansi:
            return f"[{self.time_str}] {self.level} [{self.logger_name}] {self.message.split(BREAK_LINE)[0]}\n{BREAK_LINE if with_extra_break_line else ''}{BREAK_LINE.join(self.message.split(BREAK_LINE)[1:])}"
        levels_colors = {
            "CRITICAL": Fore.RED,
            "ERROR": Fore.RED,
            "WARNING": Fore.YELLOW,
            "INFO": Fore.BLUE,
            "DEBUG": Fore.GREEN,
            "TRACE": Fore.CYAN,
            "NODE": Fore.MAGENTA,
        }
        level_color = levels_colors.get(self.level, Fore.MAGENTA)
        return f"{Fore.BLACK}[{self.time_str}] {level_color}{self.level} {Fore.WHITE}[{Fore.MAGENTA}{self.logger_name}{Fore.WHITE}] {Fore.WHITE}{self.message.split(BREAK_LINE)[0]}\n{BREAK_LINE if with_extra_break_line else ''}{Fore.RESET}{BREAK_LINE.join(self.message.split(BREAK_LINE)[1:])}"


@cog_i18n(_)
class ConsoleLogs(Cog, DashboardIntegration):
    """A cog to display the console logs, with buttons and filter options!"""

    def __init__(self, bot: Red) -> None:
        super().__init__(bot=bot)
        self.__authors__: typing.List[str] = ["AAA3A", "Tobotimus"]

        self.RED_INTRO: str = None

    async def cog_load(self) -> None:
        await super().cog_load()

        self.RED_INTRO: str = INTRO
        guilds = len(self.bot.guilds)
        users = len(set(list(self.bot.get_all_members())))
        prefixes = getattr(self.bot._cli_flags, "prefix", None) or (await self.bot._config.prefix())
        lang = await self.bot._config.locale()
        dpy_version = discord.__version__
        table_general_info = Table(show_edge=False, show_header=False, box=rich_box.MINIMAL)
        table_general_info.add_row("Prefixes", ", ".join(prefixes))
        table_general_info.add_row("Language", lang)
        table_general_info.add_row("Red version", red_version)
        table_general_info.add_row("Discord.py version", dpy_version)
        table_general_info.add_row("Storage type", data_manager.storage_type())
        table_counts = Table(show_edge=False, show_header=False, box=rich_box.MINIMAL)
        table_counts.add_row("Shards", str(self.bot.shard_count))
        table_counts.add_row("Servers", str(guilds))
        if self.bot.intents.members:
            table_counts.add_row("Unique Users", str(users))
        self.RED_INTRO += str(
            Columns(
                [Panel(table_general_info, title=self.bot.user.display_name), Panel(table_counts)],
                equal=True,
                align="center",
            )
        )
        self.RED_INTRO += f"\nLoaded {len(self.bot.cogs)} cogs with {len(self.bot.commands)} commands"

    @property
    def console_logs(self) -> typing.List[ConsoleLog]:
        # Thanks to Tobotimus for this part!
        console_logs_files = [
            path
            for path in (data_manager.core_data_path() / "logs").iterdir()
            if LATEST_LOG_RE.match(path.name) is not None
        ]
        if not console_logs_files:
            return []
        console_logs_lines = []
        for console_logs_file in console_logs_files:
            with console_logs_file.open(mode="rt") as f:
                console_logs_lines.extend([line.strip() for line in f.readlines()])

        # Parse logs.
        console_logs = []
        for console_log_line in console_logs_lines:
            if (
                match := re.match(CONSOLE_LOG_RE, console_log_line)
            ) is None and console_logs:
                console_logs[-1].message += f"\n{CogsUtils.replace_var_paths(console_log_line)}"
                continue
            kwargs = match.groupdict()
            time = datetime.datetime.strptime(kwargs["time_str"], "%Y-%m-%d %H:%M:%S")
            kwargs["time"] = time
            kwargs["time_timestamp"] = int(time.timestamp())
            console_logs.append(ConsoleLog(**kwargs))

        # Add Red INTRO.
        if (red_ready_console_log := discord.utils.get(console_logs, logger_name="red", message="Connected to Discord. Getting ready...")):
            console_logs.insert(
                console_logs.index(red_ready_console_log) + 1,
                ConsoleLog(
                    time=red_ready_console_log.time,
                    time_timestamp=red_ready_console_log.time_timestamp,
                    time_str=red_ready_console_log.time_str,
                    level="INFO",
                    logger_name="red",
                    message=self.RED_INTRO,
                    display_without_informations=True
                )
            )

        return console_logs

    async def red_delete_data_for_user(self, *args, **kwargs) -> None:
        """Nothing to delete."""
        return

    async def red_get_data_for_user(self, *args, **kwargs) -> typing.Dict[str, typing.Any]:
        """Nothing to get."""
        return {}

    async def send_console_logs(self, ctx: commands.Context, level: typing.Optional[typing.Literal["critical", "error", "warning", "info", "debug", "trace", "node"]] = None, logger_name: typing.Optional[str] = None, view: typing.Optional[int] = -1, lines_break: int = 2) -> None:
        console_logs = self.console_logs
        console_logs_to_display = [
            console_log for console_log in console_logs
            if (level is None or console_log.level == level)
            and (logger_name is None or console_log.logger_name == logger_name)
        ]
        if not console_logs_to_display:
            raise commands.UserFeedbackCheckFailure(_("No logs to display."))
        console_logs_to_display_str = [
                console_log.__str__(with_ansi=not ctx.author.is_on_mobile(), with_extra_break_line=view is not None)
                for console_log in console_logs_to_display
        ]
        levels = ["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "TRACE", "NODE"]
        prefix = [
            f"{len(console_logs)} logs",
            f"{len({console_log.logger_name for console_log in console_logs})} loggers",
            *[
                f"{stat[1]} {stat[0]}"
                for stat in sorted(
                    Counter(
                        [console_log.level for console_log in console_logs]
                    ).items(),
                    key=lambda x: levels.index(x[0]) if x[0] in levels else 10,
                )
            ],
        ]
        prefix = box(f"Total stats: {humanize_list(prefix)}", lang="py")
        if view is not None:
            try:
                view = console_logs_to_display_str.index(console_logs_to_display_str[view])  # Handle negative index.
            except IndexError:
                view = len(console_logs_to_display_str)
            pages = []
            for i, console_log_to_display_str in enumerate(console_logs_to_display_str):
                if i == view:
                    page_index = len(pages)
                pages.extend(list(pagify(console_log_to_display_str, shorten_by=10 + len(prefix))))
        else:
            pages = list(pagify(("\n" * lines_break).join(console_logs_to_display_str), shorten_by=10 + len(prefix)))
            page_index = [i for i, page in enumerate(pages) if any(line.startswith(("[", f"{Fore.BLACK}[")) for line in page.split("\n"))][-1]
        menu = Menu(pages=pages, prefix=prefix, lang="py" if ctx.author.is_on_mobile() else "ansi")
        menu._current_page = page_index
        await menu.start(ctx)

    @commands.is_owner()
    @commands.hybrid_group(invoke_without_command=True)
    async def consolelogs(self, ctx: commands.Context, index: typing.Optional[int] = -1, level: typing.Optional[typing.Literal["critical", "error", "warning", "info", "debug", "trace", "node"]] = None, logger_name: typing.Optional[str] = None) -> None:
        """View a console log, for a provided level/logger name."""
        await self.view(ctx, index=index, level=level.upper() if level is not None else None, logger_name=logger_name)

    @consolelogs.command()
    async def view(self, ctx: commands.Context, index: typing.Optional[int] = -1, level: typing.Optional[typing.Literal["critical", "error", "warning", "info", "debug", "trace", "node"]] = None, logger_name: typing.Optional[str] = None) -> None:
        """View the console logs one by one, for all levels/loggers or provided level/logger name."""
        await self.send_console_logs(ctx, level=level.upper() if level is not None else None, logger_name=logger_name, view=index)

    @consolelogs.command(aliases=["error"])
    async def errors(self, ctx: commands.Context, index: typing.Optional[int] = -1, logger_name: typing.Optional[str] = None) -> None:
        """View the `ERROR` console logs one by one, for all loggers or a provided logger name."""
        await self.send_console_logs(ctx, level="ERROR", logger_name=logger_name, view=index)

    @consolelogs.command()
    async def scroll(self, ctx: commands.Context, lines_break: typing.Optional[commands.Range[int, 1, 5]] = 2, level: typing.Optional[typing.Literal["critical", "error", "warning", "info", "debug", "trace", "node"]] = None, logger_name: typing.Optional[str] = None) -> None:
        """Scroll the console logs, for all levels/loggers or provided level/logger name."""
        await self.send_console_logs(ctx, level=level.upper() if level is not None else None, logger_name=logger_name, view=None, lines_break=lines_break)

    @consolelogs.command(aliases=["listloggers"])
    async def stats(self, ctx: commands.Context) -> None:
        """Scroll the console logs, for all levels/loggers or provided level/logger name."""
        console_logs = self.console_logs
        console_logs_for_each_logger = {"Global Stats": console_logs}
        for console_log in console_logs:
            if console_log.logger_name not in console_logs_for_each_logger:
                console_logs_for_each_logger[console_log.logger_name] = []
            console_logs_for_each_logger[console_log.logger_name].append(console_log)
        stats = ""
        for logger_name, logs in console_logs_for_each_logger.items():
            stats += f"\n\n---------- {logger_name} ----------"
            stats += f"\n• {len(logs)} logs"
            levels = ["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "TRACE", "NODE"]
            for stat in sorted(
                Counter(
                    [console_log.level for console_log in logs]
                ).items(),
                key=lambda x: levels.index(x[0]) if x[0] in levels else 10,
            ):
                stats += f"\n• {stat[1]} {stat[0]}"
        await Menu(pages=list(pagify(stats, page_length=500)), lang="py").start(ctx)

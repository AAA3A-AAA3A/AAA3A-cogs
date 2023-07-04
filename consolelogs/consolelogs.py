from AAA3A_utils import Cog, CogsUtils, Menu, Loop  # isort:skip
from redbot.core import commands, Config  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
from redbot.core.bot import Red  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import datetime
import logging
import re
import traceback

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
# Thanks to Tobotimus for the part to get logs files lines (https://github.com/Tobotimus/Tobo-Cogs/blob/V3/errorlogs/errorlogs.py)!
# Thanks to Trusty for the part to get the "message" content for slash commands (https://github.com/TrustyJAID/Trusty-cogs/blob/master/extendedmodlog/eventmixin.py#L222-L249!

_ = Translator("ConsoleLogs", __file__)

LATEST_LOG_RE = re.compile(r"latest(?:-part(?P<part>\d+))?\.log")
CONSOLE_LOG_RE = re.compile(r"^\[(?P<time_str>.*?)\] \[(?P<level>.*?)\] (?P<logger_name>.*?): (?P<message>.*)")

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
    """A cog to display the console logs, with buttons and filter options, and to send commands errors in configured channels!"""

    def __init__(self, bot: Red) -> None:
        super().__init__(bot=bot)
        self.__authors__: typing.List[str] = ["AAA3A", "Tobotimus"]

        self.config: Config = Config.get_conf(
            self,
            identifier=205192943327321000143939875896557571750,
            force_registration=True,
        )
        self.consolelogs_channel = {
            "enabled": False,
            "global_errors": False,
            "prefixed_commands_errors": True,
            "slash_commands_errors": True,
            "dpy_ignored_exceptions": False,
        }
        self.config.register_channel(**self.consolelogs_channel)

        self.RED_INTRO: str = None
        self._last_console_log_sent_timestamp: int = None

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

        self._last_console_log_sent_timestamp: int = int(datetime.datetime.now(tz=datetime.timezone.utc).timestamp())
        self.loops.append(
            Loop(
                cog=self,
                name="Check Console Logs",
                function=self.check_console_logs,
                minutes=1,
            )
        )

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
        console_logs_files.reverse()
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
            message = kwargs["message"].split("\n")
            kwargs["message"] = (
                f"{message[0]}{'.' if not message[0].endswith(('.', '!', '?')) and message[0][0] == message[0][0].upper() else ''}\n"
                + "\n".join(kwargs["message"].split("\n")[1:])
            ).strip()
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
            and (logger_name is None or ".".join(console_log.logger_name.split(".")[:len(logger_name.split("."))]) == logger_name)
        ]
        if not console_logs_to_display:
            raise commands.UserFeedbackCheckFailure(_("No logs to display."))
        console_logs_to_display_str = [
                console_log.__str__(with_ansi=not ctx.author.is_on_mobile(), with_extra_break_line=view is not None)
                for console_log in console_logs_to_display
        ]
        levels = ["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "TRACE", "NODE"]
        total_stats = [
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
        current_stats = [
            f"{len(console_logs_to_display)} logs",
            f"{len({console_log.logger_name for console_log in console_logs_to_display})} loggers",
            *[
                f"{stat[1]} {stat[0]}"
                for stat in sorted(
                    Counter(
                        [console_log.level for console_log in console_logs_to_display]
                    ).items(),
                    key=lambda x: levels.index(x[0]) if x[0] in levels else 10,
                )
            ],
        ]
        prefix = box(f"Total stats: {humanize_list(total_stats)}." + (f"\nCurrent stats: {humanize_list(current_stats)}." if total_stats != current_stats else ""), lang="py")
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
    async def consolelogs(self, ctx: commands.Context, index: typing.Optional[int] = -1, level: typing.Optional[typing.Literal["critical", "error", "warning", "info", "debug", "trace", "node", "criticals", "errors", "warnings", "infos", "debugs", "traces", "nodes"]] = None, logger_name: typing.Optional[str] = None) -> None:
        """View a console log, for a provided level/logger name."""
        await self.view(ctx, index=index, level=level.upper().rstrip("s") if level is not None else None, logger_name=logger_name)

    @consolelogs.command()
    async def view(self, ctx: commands.Context, index: typing.Optional[int] = -1, level: typing.Optional[typing.Literal["critical", "error", "warning", "info", "debug", "trace", "node", "criticals", "errors", "warnings", "infos", "debugs", "traces", "nodes"]] = None, logger_name: typing.Optional[str] = None) -> None:
        """View the console logs one by one, for all levels/loggers or provided level/logger name."""
        await self.send_console_logs(ctx, level=level.upper().rstrip("s") if level is not None else None, logger_name=logger_name, view=index)

    @consolelogs.command(aliases=["error"])
    async def errors(self, ctx: commands.Context, index: typing.Optional[int] = -1, logger_name: typing.Optional[str] = None) -> None:
        """View the `ERROR` console logs one by one, for all loggers or a provided logger name."""
        await self.send_console_logs(ctx, level="ERROR", logger_name=logger_name, view=index)

    @consolelogs.command()
    async def scroll(self, ctx: commands.Context, lines_break: typing.Optional[commands.Range[int, 1, 5]] = 2, level: typing.Optional[typing.Literal["critical", "error", "warning", "info", "debug", "trace", "node", "criticals", "errors", "warnings", "infos", "debugs", "traces", "nodes"]] = None, logger_name: typing.Optional[str] = None) -> None:
        """Scroll the console logs, for all levels/loggers or provided level/logger name."""
        await self.send_console_logs(ctx, level=level.upper().rstrip("s") if level is not None else None, logger_name=logger_name, view=None, lines_break=lines_break)

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

    @consolelogs.command(aliases=["+"])
    async def addchannel(self, ctx: commands.Context, channel: discord.TextChannel, global_errors: typing.Optional[bool] = True, prefixed_commands_errors: typing.Optional[bool] = True, slash_commands_errors: typing.Optional[bool] = True, dpy_ignored_exceptions: typing.Optional[bool] = False) -> None:
        """Enable errors logging in a channel.

        **Parameters:**
        - `channel`: The channel where the commands errors will be sent.
        - `global_errors`: Log errors for the entire bot, not just the channel server.
        - `prefixed_commands_errors`: Log prefixed commands errors.
        - `slash_commands_errors`: Log slash commands errors.
        - `dpy_ignored_exceptions`: Log dpy ignored exceptions (events listeners and Views errors).
        """
        channel_permissions = channel.permissions_for(ctx.me)
        if not all([channel_permissions.view_channel, channel_permissions.send_messages, channel_permissions.embed_links]):
            raise commands.UserFeedbackCheckFailure(_("I don't have the permissions to send embeds in this channel."))
        await self.config.channel(channel).enabled.set(True)
        await self.config.channel(channel).global_errors.set(global_errors)
        await self.config.channel(channel).prefixed_commands_errors.set(prefixed_commands_errors)
        await self.config.channel(channel).slash_commands_errors.set(slash_commands_errors)
        await self.config.channel(channel).dpy_ignored_exceptions.set(dpy_ignored_exceptions)
        await ctx.send(_("Errors logging enabled in {channel.mention}.").format(channel=channel))

    @consolelogs.command(aliases=["-"])
    async def removechannel(self, ctx: commands.Context, channel: discord.TextChannel) -> None:
        """Disable errors logging in a channel."""
        if not await self.config.channel(channel).enabled():
            raise commands.UserFeedbackCheckFailure(_("Errors logging isn't enabled in this channel."))
        await self.config.channel(channel).clear()
        await ctx.send(_("Errors logging disabled in {channel.mention}.").format(channel=channel))

    @consolelogs.command(hidden=True)
    async def getdebugloopsstatus(self, ctx: commands.Context) -> None:
        """Get an embed to check loops status."""
        embeds = [loop.get_debug_embed() for loop in self.loops]
        await Menu(pages=embeds).start(ctx)

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError, unhandled_by_cog: bool = False) -> None:
        if await self.bot.cog_disabled_in_guild(cog=self, guild=ctx.guild):
            return
        if isinstance(error, IGNORED_ERRORS):
            return
        destinations = {
            channel: config
            for channel_id, config in (await self.config.all_channels()).items()
            if config["enabled"] and (channel := ctx.bot.get_channel(channel_id)) is not None and channel.permissions_for(channel.guild.me).send_messages
        }
        if not destinations:
            return

        # Thanks to Trusty for this part.
        if ctx.interaction:
            data = ctx.interaction.data
            com_id = data.get("id")
            root_command = data.get("name")
            sub_commands = ""
            arguments = ""
            for option in data.get("options", []):
                if option["type"] in (1, 2):
                    sub_commands += " " + option["name"]
                else:
                    option_name = option["name"]
                    option_value = option.get("value")
                    arguments += f"{option_name}: {option_value}"
                for sub_option in option.get("options", []):
                    if sub_option["type"] in (1, 2):
                        sub_commands += " " + sub_option["name"]
                    else:
                        sub_option_name = sub_option.get("name")
                        sub_option_value = sub_option.get("value")
                        arguments += f"{sub_option_name}: {sub_option_value}"
                    for arg in sub_option.get("options", []):
                        arg_option_name = arg.get("name")
                        arg_option_value = arg.get("value")
                        arguments += f"{arg_option_name}: {arg_option_value} "
            command_name = f"{root_command}{sub_commands}"
            com_str = f"</{command_name}:{com_id}> {arguments}"
        else:
            com_str = ctx.message.content

        embed = discord.Embed(
            title=f"⚠ Exception in command `{ctx.command.qualified_name}`! ¯\\_(ツ)_/¯",
            color=discord.Color.red(),
            timestamp=ctx.message.created_at,
            description=f">>> {com_str}",
        )
        embed.add_field(name="Invoker:", value=f"{ctx.author.mention}\n{ctx.author} ({ctx.author.id})")
        embed.add_field(name="Message:", value=f"[Jump to message.]({ctx.message.jump_url})")
        embed.add_field(name="Channel:", value=f"{ctx.channel.mention}\n{ctx.channel} ({ctx.channel.id})" if ctx.guild is not None else str(ctx.channel))
        if ctx.guild is not None:
            embed.add_field(name="Guild:", value=f"{ctx.guild.name} ({ctx.guild.id})")
        view = discord.ui.View()
        view.add_item(discord.ui.Button(style=discord.ButtonStyle.url, label="Jump to Message", url=ctx.message.jump_url))
        if ctx.guild is not None and "COMMUNITY" in ctx.guild.features:
            guild_invite = None
            if "VANITY_URL" in ctx.guild.features:
                try:
                    guild_invite = await ctx.guild.vanity_invite()
                except discord.HTTPException:
                    pass
            if guild_invite is None:
                try:
                    invites = await ctx.guild.invites()
                except discord.HTTPException:
                    pass
                else:
                    for inv in invites:
                        if not (inv.max_uses or inv.max_age or inv.temporary):
                            guild_invite = inv
            if guild_invite is None:
                channels_and_perms = zip(
                    ctx.guild.text_channels,
                    map(lambda x: x.permissions_for(ctx.guild.me), ctx.guild.text_channels),
                )
                channel = next(
                    (channel for channel, perms in channels_and_perms if perms.create_instant_invite),
                    None,
                )
                if channel is not None:
                    try:
                        guild_invite = await channel.create_invite(max_age=86400)
                    except discord.HTTPException:
                        pass
            if guild_invite is not None:
                view.add_item(discord.ui.Button(style=discord.ButtonStyle.url, label="Guild Invite", url=guild_invite.url))
        traceback_error = "".join(
            traceback.format_exception(type(error), error, error.__traceback__)
        )
        _traceback_error = traceback_error.split("\n")
        _traceback_error[0] = _traceback_error[0] + (
            "" if _traceback_error[0].endswith(":") else ":\n"
        )
        traceback_error = "\n".join(_traceback_error)
        traceback_error = CogsUtils.replace_var_paths(traceback_error)
        pages = [box(page, lang="py") for page in pagify(traceback_error, shorten_by=10)]
        for channel, config in destinations.items():
            if not config["global_errors"] and ctx.guild != channel.guild:
                continue
            if not config["prefixed_commands_errors"] and ctx.interaction is None:
                continue
            if not config["slash_commands_errors"] and ctx.interaction is not None:
                continue
            await channel.send(embed=embed, view=view)
            for page in pages:
                await channel.send(page)

    async def check_console_logs(self) -> None:
        destinations = {
            channel: config
            for channel_id, config in (await self.config.all_channels()).items()
            if config["enabled"] and config["dpy_ignored_exceptions"] and (channel := self.bot.get_channel(channel_id)) is not None and channel.permissions_for(channel.guild.me).send_messages
        }
        if not destinations:
            return
        console_logs = self.console_logs
        console_logs_to_send: typing.List[typing.Tuple[discord.Embed, typing.List[str]]] = []
        for console_log in console_logs:
            if self._last_console_log_sent_timestamp is None or self._last_console_log_sent_timestamp >= console_log.time_timestamp:
                self._last_console_log_sent_timestamp = console_log.time_timestamp
                continue
            self._last_console_log_sent_timestamp = console_log.time_timestamp
            if (
                console_log.level not in ["CRITICAL", "ERROR"]
                or console_log.logger_name.split(".")[0] != "discord"
                or not console_log.message.split("\n")[0].startswith("Ignoring exception ")
            ):
                continue
            embed: discord.Embed = discord.Embed(color=discord.Color.dark_embed())
            embed.title = console_log.message.split("\n")[0]
            embed.timestamp = console_log.time
            embed.add_field(name="Logger name:", value=f"`{console_log.logger_name}`")
            embed.add_field(name="Error level:", value=f"`{console_log.level}`")
            pages = [box(page, lang="py") for page in list(pagify(console_log.__str__(with_ansi=False, with_extra_break_line=True), shorten_by=10))]
            console_logs_to_send.append((embed, pages))
        for channel in destinations:
            for (embed, pages) in console_logs_to_send:
                await channel.send(embed=embed)
                for page in pages:
                    await channel.send(page)

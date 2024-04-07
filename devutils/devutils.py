from AAA3A_utils import Cog, CogsUtils, Menu  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
from redbot.core.bot import Red  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import asyncio
import importlib
import json
import logging
import re
import sys
import time

from discord.http import Route
from red_commons.logging import TRACE, VERBOSE, getLogger
from redbot.core.utils.chat_formatting import humanize_list

# Credits:
# General repo credits.
# Thanks to Phen for the original code (https://github.com/phenom4n4n/phen-cogs/tree/master/phenutils)!

_ = Translator("Devutils", __file__)

SLEEP_FLAG = re.compile(r"(?:--|—)sleep (\d+)$")


class LogLevelConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> int:
        levels = {
            "CRITICAL": logging.CRITICAL,
            "ERROR": logging.ERROR,
            "WARNING": logging.WARNING,
            "INFO": logging.INFO,
            "DEBUG": logging.DEBUG,
            "VERBOSE": VERBOSE,
            "TRACE": TRACE,
        }
        if argument.upper() in levels:
            return levels[argument.upper()]
        try:
            argument = int(argument)
        except ValueError:
            pass
        else:
            try:
                return list(levels.values())[argument]
            except IndexError:
                pass
        raise commands.BadArgument(_("No valid log level provided."))


class StrConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> str:
        return argument


class RawRequestConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str):
        _types = [
            discord.Guild,
            discord.abc.GuildChannel,
            discord.Thread,
            discord.Member,
            discord.User,
            discord.Role,
            discord.Emoji,
            discord.Message,
            discord.Invite,
        ]
        # _types = list(discord.ext.commands.converter.CONVERTER_MAPPING.keys())[1:]
        for _type in _types:
            try:
                return await discord.ext.commands.converter.CONVERTER_MAPPING[_type]().convert(
                    ctx, argument
                )
            except commands.BadArgument:
                pass
        raise commands.BadArgument(_("No valid discord object provided."))


@cog_i18n(_)
class DevUtils(Cog):
    """Various development utilities!"""

    def __init__(self, bot: Red) -> None:
        super().__init__(bot=bot)
        self.__authors__: typing.List[str] = ["PhenoM4n4n", "AAA3A"]

    @commands.Cog.listener()
    async def on_message_without_command(self, message: discord.Message):
        if await self.bot.cog_disabled_in_guild(
            cog=self, guild=message.guild
        ) or not await self.bot.allowed_by_whitelist_blacklist(who=message.author):
            return
        if message.webhook_id is not None or message.author.bot:
            return
        context = await self.bot.get_context(message)
        if context.prefix is None:
            return
        command = context.message.content[len(str(context.prefix)) :]
        if len(command.split(" ")) == 0:
            return
        command_name = command.split(" ")[0]
        if command_name not in [
            "do",
            "execute",
            "bypass",
            "timing",
            "reinvoke",
            "loglevel",
            "reloadmodule",
            "rawrequest",
        ]:
            return
        await CogsUtils.invoke_command(
            bot=self.bot,
            author=context.author,
            channel=context.channel,
            command=f"devutils {command}",
            prefix=context.prefix,
            message=context.message,
        )

    @commands.is_owner()
    @commands.hybrid_group()
    async def devutils(self, ctx: commands.Context) -> None:
        """Various development utilities."""
        pass

    @devutils.command()
    async def do(
        self, ctx, times: int, sequential: typing.Optional[bool] = True, *, command: str
    ) -> None:
        """
        Repeats a command a specified number of times.

        `--sleep <int>` is an optional flag specifying how much time to wait between command invocations.
        """
        if match := SLEEP_FLAG.search(command):  # too lazy to use argparse
            sleep = int(match.group(1))
            command = command[: -len(match.group(0))]
        else:
            sleep = 1

        new_ctx = await CogsUtils.invoke_command(
            bot=ctx.bot,
            author=ctx.author,
            channel=ctx.channel,
            command=command,
            prefix=ctx.prefix,
            message=ctx.message,
            invoke=False,
        )
        if not new_ctx.valid:
            raise commands.UserFeedbackCheckFailure(_("You have not specified a correct command."))
        if not await discord.utils.async_all([check(new_ctx) for check in new_ctx.command.checks]):
            raise commands.UserFeedbackCheckFailure(_("You can't execute yourself this command."))
        if sequential:
            for __ in range(times):
                await ctx.bot.invoke(new_ctx)
                await asyncio.sleep(sleep)
        else:
            todo = [ctx.bot.invoke(new_ctx) for _ in range(times)]
            await asyncio.gather(*todo)

    @devutils.command()
    async def execute(
        self, ctx: commands.Context, sequential: typing.Optional[bool] = True, *, commands: str
    ) -> None:
        """Execute multiple commands at once. Split them using |."""
        commands = [command.strip() for command in commands.split("|")]
        if sequential:
            for command in commands:
                new_ctx = await CogsUtils.invoke_command(
                    bot=ctx.bot,
                    author=ctx.author,
                    channel=ctx.channel,
                    command=command,
                    prefix=ctx.prefix,
                    message=ctx.message,
                    invoke=True,
                )
                if not new_ctx.valid:
                    raise commands.UserFeedbackCheckFailure(
                        _("`{command}` isn't a valid command.").format(command=command)
                    )
                if not await discord.utils.async_all(
                    [check(new_ctx) for check in new_ctx.command.checks]
                ):
                    raise commands.UserFeedbackCheckFailure(
                        _("You can't execute yourself `{command}`.").format(command=command)
                    )
        else:
            todo = []
            for command in commands:
                new_ctx = await CogsUtils.invoke_command(
                    bot=ctx.bot,
                    author=ctx.author,
                    channel=ctx.channel,
                    command=command,
                    prefix=ctx.prefix,
                    message=ctx.message,
                    invoke=False,
                )
                if not new_ctx.valid:
                    raise commands.UserFeedbackCheckFailure(
                        _("`{command}` isn't a valid command.").format(command=command)
                    )
                if not await discord.utils.async_all(
                    [check(new_ctx) for check in new_ctx.command.checks]
                ):
                    raise commands.UserFeedbackCheckFailure(
                        _("You can't execute yourself `{command}`.").format(command=command)
                    )
                todo.append(ctx.bot.invoke(new_ctx))
            await asyncio.gather(*todo)

    @devutils.command()
    async def bypass(self, ctx: commands.Context, *, command: str) -> None:
        """Bypass a command's checks and cooldowns."""
        new_ctx = await CogsUtils.invoke_command(
            bot=ctx.bot,
            author=ctx.author,
            channel=ctx.channel,
            command=command,
            prefix=ctx.prefix,
            message=ctx.message,
            invoke=False,
        )
        if not new_ctx.valid:
            raise commands.UserFeedbackCheckFailure(_("You have not specified a correct command."))
        await new_ctx.reinvoke()

    @devutils.command()
    async def timing(self, ctx: commands.Context, *, command: str) -> None:
        """Run a command timing execution and catching exceptions."""
        new_ctx = await CogsUtils.invoke_command(
            bot=ctx.bot,
            author=ctx.author,
            channel=ctx.channel,
            command=command,
            prefix=ctx.prefix,
            message=ctx.message,
            invoke=False,
        )
        if not new_ctx.valid:
            raise commands.UserFeedbackCheckFailure(_("You have not specified a correct command."))
        if not await discord.utils.async_all([check(new_ctx) for check in new_ctx.command.checks]):
            raise commands.UserFeedbackCheckFailure(_("You can't execute yourself this command."))

        start = time.perf_counter()
        await ctx.bot.invoke(new_ctx)
        end = time.perf_counter()
        return await ctx.send(
            _("Command `{command}` finished in `{timing}`s.").format(
                command=new_ctx.command.qualified_name, timing=f"{end - start:.3f}"
            )
        )

    @devutils.command()
    async def reinvoke(self, ctx: commands.Context, message: discord.Message = None) -> None:
        """Reinvoke a command message.

        You may reply to a message to reinvoke it or pass a message ID/link.
        The command will be invoked with the author and the channel of the specified message.
        """
        if message is None:
            if not (
                hasattr(ctx.message, "reference")
                and ctx.message.reference is not None
                and isinstance((message := ctx.message.reference.resolved), discord.Message)
            ):
                raise commands.UserInputError()
        new_ctx = await CogsUtils.invoke_command(
            bot=ctx.bot,
            author=message.author,
            channel=message.channel,
            command=message.content,
            prefix="",
            message=message,
        )
        if not new_ctx.valid:
            raise commands.UserFeedbackCheckFailure(_("The command isn't valid.."))
        if not await discord.utils.async_all([check(new_ctx) for check in new_ctx.command.checks]):
            raise commands.UserFeedbackCheckFailure(_("This command can't be executed."))

    @devutils.command()
    async def loglevel(
        self, ctx: commands.Context, level: LogLevelConverter, logger_name: str = "red"
    ) -> None:
        """Change the logging level for a logger. if no name is provided, the root logger (red) is used.

        Levels are the following:
        - `0`: `CRITICAL`
        - `1`: `ERROR`
        - `2`: `WARNING`
        - `3`: `INFO`
        - `4`: `DEBUG`
        - `5`: `VERBOSE`
        - `6`: `TRACE`
        """
        logger = getLogger(logger_name)
        logger.setLevel(level)
        await ctx.send(
            _("Logger `{logger_name}` level set to `{level}`.").format(
                level=logging.getLevelName(logger.level), logger_name=logger_name
            )
        )

    @devutils.command()
    async def reloadmodule(
        self, ctx: commands.Context, modules: commands.Greedy[StrConverter]
    ) -> None:
        """Force reload a module (to use code changes without restarting your bot).

        ⚠️ Please only use this if you know what you're doing.
        """
        _modules = []
        for module in modules:
            _modules.extend(
                [
                    m
                    for m in sys.modules
                    if m.split(".")[: len(module.split("."))] == module.split(".")
                ]
            )
        modules = sorted(_modules, reverse=True)
        if not modules:
            raise commands.UserFeedbackCheckFailure(
                _("I couldn't find any module with this name.")
            )
        for module in modules:
            importlib.reload(sys.modules[module])
        text = _("Module(s) {modules} reloaded.").format(
            modules=humanize_list([f"`{module}`" for module in modules])
        )
        if len(text) <= 2000:
            await ctx.send(text)
        else:
            await ctx.send(_("Modules [...] reloaded."))

    @devutils.command(aliases=["rawcontent"])
    async def rawrequest(self, ctx: commands.Context, *, thing: RawRequestConverter) -> None:
        """Display the JSON of a Discord object with a raw request."""
        if isinstance(thing, discord.Guild):
            raw_content = await ctx.bot.http.request(
                route=Route(method="GET", path="/guilds/{guild_id}", guild_id=thing.id)
            )
        elif isinstance(thing, (discord.abc.GuildChannel, discord.Thread)):
            raw_content = await ctx.bot.http.request(
                route=Route(method="GET", path="/channels/{channel_id}", channel_id=thing.id)
            )
        elif isinstance(thing, discord.Member):
            raw_content = await ctx.bot.http.request(
                route=Route(
                    method="GET",
                    path="/guilds/{guild_id}/members/{user_id}",
                    guild_id=thing.guild.id,
                    user_id=thing.id,
                )
            )
        elif isinstance(thing, discord.User):
            raw_content = await ctx.bot.http.request(
                route=Route(method="GET", path="/users/{user_id}", user_id=thing.id)
            )
        elif isinstance(thing, discord.Role):
            raw_content = [
                role
                for role in await ctx.bot.http.request(
                    route=Route(
                        method="GET", path="/guilds/{guild_id}/roles", guild_id=thing.guild.id
                    )
                )
                if int(role["id"]) == thing.id
            ][0]
        elif isinstance(thing, discord.Emoji):
            raw_content = await ctx.bot.http.request(
                route=Route(
                    method="GET",
                    path="/guilds/{guild_id}/emojis/{emoji_id}",
                    guild_id=thing.guild.id,
                    emoji_id=thing.id,
                )
            )
        elif isinstance(thing, discord.Message):
            raw_content = await ctx.bot.http.request(
                route=Route(
                    method="GET",
                    path="/channels/{channel_id}/messages/{message_id}",
                    channel_id=thing.channel.id,
                    message_id=thing.id,
                )
            )
        elif isinstance(thing, discord.Invite):
            raw_content = await ctx.bot.http.request(
                route=Route(method="GET", path="/invites/{invite_code}", invite_code=thing.code)
            )
        await Menu(json.dumps(raw_content, indent=4), lang="py").start(ctx)

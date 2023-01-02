from redbot.core import commands  # isort:skip
from redbot.core.bot import Red  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import asyncio
import traceback

from redbot.core.utils.chat_formatting import humanize_list, inline, warning

from .context import is_dev, Context

__all__ = ["Cog"]


def _(untranslated: str):
    return untranslated


class Cog:
    def __init__(self, bot: Red):
        self.bot: Red = bot
        self.cog: commands.Cog = None

    @classmethod
    def _setup(cls, bot: Red, cog: commands.Cog):
        """
        Adding additional functionality to the cog.
        """
        # for command in self.cog.walk_commands():
        #     setattr(command, 'format_text_for_context', self.format_text_for_context)
        #     setattr(command, 'format_shortdoc_for_context', self.format_shortdoc_for_context)
        specials = [
            "_setup",
            "get_formatted_text",
            "format_text_for_context",
            "format_shortdoc_for_context",
            "unsupported",
        ]
        self = cls(bot=bot)
        self.cog = cog
        for attr in dir(self):
            if attr.startswith("__") and attr.endswith("__"):
                continue
            if attr in specials:
                continue
            if not getattr(getattr(cog, attr, None), "__func__", "None1") == getattr(
                commands.Cog, attr, "None2"
            ):
                continue
            setattr(cog, attr, getattr(self, attr))

    def get_formatted_text(self, context: str):
        s = "s" if len(self.cog.__authors__) > 1 else ""
        text = f"{context}\n\n**Author{s}**: {humanize_list(self.cog.__authors__)}\n**Cog version**: {self.cog.__version__}\n**Cog commit**: {self.cog.__commit__}"
        if self.cog.qualified_name not in ["AAA3A_utils"]:
            text += f"\n**Cog documentation**: https://aaa3a-cogs.readthedocs.io/en/latest/cog_{self.cog.qualified_name.lower()}.html\n**Translate my cogs**: https://crowdin.com/project/aaa3a-cogs"
        return text

    def format_help_for_context(self, ctx: commands.Context):
        """Thanks Simbad!"""
        context = super(type(self.cog), self.cog).format_help_for_context(ctx)
        return self.get_formatted_text(context)

    def format_text_for_context(
        self, ctx: commands.Context, text: str, shortdoc: typing.Optional[bool] = False
    ):
        text = text.replace("        ", "")
        context = super(type(ctx.command), ctx.command).format_text_for_context(ctx, text)
        if shortdoc:
            return context
        return self.get_formatted_text(context)

    def format_shortdoc_for_context(self, ctx: commands.Context):
        sh = super(type(ctx.command), ctx.command).short_doc
        try:
            return (
                super(type(ctx.command), ctx.command).format_text_for_context(
                    ctx, sh, shortdoc=True
                )
                if sh
                else sh
            )
        except Exception:
            return (
                super(type(ctx.command), ctx.command).format_text_for_context(ctx, sh)
                if sh
                else sh
            )

    async def red_delete_data_for_user(self, *args, **kwargs):
        """Nothing to delete."""
        return

    async def red_get_data_for_user(self, *args, **kwargs) -> typing.Dict[typing.Any, typing.Any]:
        """Nothing to get."""
        return {}

    if discord.version_info.major >= 2:

        async def cog_unload(self):
            self.cog.cogsutils._end()

    else:

        def cog_unload(self):
            self.cog.cogsutils._end()

    async def unsupported(self, ctx: commands.Context) -> None:
        """Thanks to Vexed for this (https://github.com/Vexed01/Vex-Cogs/blob/master/status/commands/statusdev_com.py#L33-L56)."""
        if is_dev(ctx.bot, ctx.author):
            return
        content = warning(
            "\nTHIS COMMAND IS INTENDED FOR DEVELOPMENT PURPOSES ONLY.\n\nUnintended "
            "things can happen.\n\nRepeat: THIS COMMAND IS NOT SUPPORTED.\nAre you sure "
            "you want to continue?"
        )
        try:
            result = await self.cog.cogsutils.ConfirmationAsk(ctx, content=content)
        except TimeoutError:
            await ctx.send("Timeout, aborting.")
            raise commands.CheckFailure("Confirmation timed out.")
        if result:
            return True
        else:
            await ctx.send("Aborting.")
            raise commands.CheckFailure("User choose no.")

    async def cog_before_invoke(self, ctx: commands.Context):
        if self.cog is None:
            return
        if isinstance(ctx.command, commands.Group):
            view = ctx.view
            previous = view.index
            view.skip_ws()
            trigger = view.get_word()
            invoked_subcommand = ctx.command.all_commands.get(trigger, None)
            view.index = previous
            if invoked_subcommand is not None or not ctx.command.invoke_without_command:
                return
        context = await Context.from_context(ctx)
        if getattr(ctx.command, "__is_dev__", False):
            await self.unsupported(ctx)
        if getattr(context, "interaction", None) is None:
            for index, arg in enumerate(ctx.args.copy()):
                if isinstance(arg, commands.Context):
                    ctx.args[index] = context
            context._typing = context.channel.typing()
            await context._typing.__aenter__()
        else:
            if context.command.__commands_is_hybrid__ and hasattr(context.command, "app_command"):
                __do_call = getattr(context.command.app_command, "_do_call")
                async def _do_call(interaction, params):
                    await __do_call(interaction=context, params=params)
                setattr(context.command.app_command, "_do_call", _do_call)
            try:
                await context.interaction.response.defer(ephemeral=False, thinking=True)
            except discord.InteractionResponded:
                pass
            context._typing = context.channel.typing()
            try:
                await context._typing.__aenter__()
            except discord.InteractionResponded:
                pass
        return context

    async def cog_after_invoke(self, ctx: commands.Context, force: typing.Optional[bool] = False):
        if self.cog is None:
            return
        if isinstance(ctx.command, commands.Group):
            if ctx.invoked_subcommand is not None or not ctx.command.invoke_without_command:
                return
        context = await Context.from_context(ctx)
        if hasattr(context, "_typing"):
            if hasattr(context._typing, "task") and hasattr(context._typing.task, "cancel"):
                context._typing.task.cancel()
        if not ctx.command_failed:
            await context.tick()
        else:
            await context.tick(reaction="❌")
        # from .menus import Menu
        # await Menu(pages=str("\n".join([str((x.function, x.frame)) for x in __import__("inspect").stack(30)])), box_language_py=True).start(context)
        return context

    async def cog_command_error(self, ctx: commands.Context, error: Exception):
        if self.cog is None:
            return
        if isinstance(error, commands.CommandInvokeError):
            if self.cog.cogsutils.is_dpy2 and isinstance(
                ctx.command, discord.ext.commands.HybridCommand
            ):
                _type = "[hybrid|text]"
            else:
                _type = "[text]"
            message = await self.cog.cogsutils.bot._config.invoke_error_msg()
            if not message:
                message = f"Error in {_type} command '{ctx.command.qualified_name}'."
                if ctx.author.id in ctx.bot.owner_ids:
                    message += " Check your console or logs for details.\nIf necessary, please inform the creator of the cog in which this command is located. Thank you."
                message = inline(message)
            else:
                message = message.replace("{command}", ctx.command.qualified_name)
            await ctx.send(message)
            asyncio.create_task(ctx.bot._delete_delay(ctx))
            self.cog.log.exception(
                f"Exception in {_type} command '{ctx.command.qualified_name}'.",
                exc_info=error.original,
            )
            exception_log = f"Exception in {_type} command '{ctx.command.qualified_name}':\n"
            exception_log += "".join(
                traceback.format_exception(type(error), error, error.__traceback__)
            )
            exception_log = self.cog.cogsutils.replace_var_paths(exception_log)
            ctx.bot._last_exception = exception_log
        elif self.cog.cogsutils.is_dpy2 and isinstance(error, commands.HybridCommandError):
            _type = "[hybrid|slash]"
            message = await self.cog.cogsutils.bot._config.invoke_error_msg()
            if not message:
                message = f"Error in {_type} command '{ctx.command.qualified_name}'."
                if ctx.author.id in ctx.bot.owner_ids:
                    message += " Check your console or logs for details.\nIf necessary, please inform the creator of the cog in which this command is located. Thank you."
                message = inline(message)
            else:
                message = message.replace("{command}", ctx.command.qualified_name)
            await ctx.send(message)
            asyncio.create_task(ctx.bot._delete_delay(ctx))
            self.cog.log.exception(
                f"Exception in {_type} command '{ctx.command.qualified_name}'.",
                exc_info=error.original,
            )
            exception_log = f"Exception in {_type} command '{ctx.command.qualified_name}':\n"
            exception_log += "".join(
                traceback.format_exception(type(error), error, error.__traceback__)
            )
            exception_log = self.cog.cogsutils.replace_var_paths(exception_log)
            ctx.bot._last_exception = exception_log
        elif isinstance(error, commands.CheckFailure):
            if getattr(ctx, "interaction", None) is not None:
                await ctx.send(
                    inline("You are not allowed to execute this command in this context."),
                    ephemeral=True,
                )
        else:
            await ctx.bot.on_command_error(ctx=ctx, error=error, unhandled_by_cog=True)

from redbot.core import commands  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import asyncio
import traceback

from redbot.core.utils.chat_formatting import humanize_list, inline

__all__ = ["Cog"]

def _(untranslated: str):
    return untranslated

class Cog():

    def __init__(self, cog):
        self.cog = cog

    def format_help_for_context(self, ctx: commands.Context):
        """Thanks Simbad!"""
        context = super(type(self.cog), self.cog).format_help_for_context(ctx)
        s = "s" if len(self.cog.__authors__) > 1 else ""
        text_help = f"{context}\n\n**Author{s}**: {humanize_list(self.cog.__authors__)}\n**Cog version**: {self.cog.__version__}"
        if self.cog.qualified_name not in ["AAA3A_utils"]:
            text_help = text_help + f"\n**Cog documentation**: https://aaa3a-cogs.readthedocs.io/en/latest/cog_{self.cog.qualified_name.lower()}.html\n**Translate my cogs**: https://crowdin.com/project/aaa3a-cogs"
        return text_help

    def format_text_for_context(self, ctx: commands.Context, text: str, shortdoc: typing.Optional[bool]=False):
        text = text.replace("        ", "")
        context = super(type(ctx.command), ctx.command).format_text_for_context(ctx, text)
        if shortdoc:
            return context
        s = "s" if len(self.cog.__authors__) > 1 else ""
        text_help = f"{context}\n\n**Author{s}**: {humanize_list(self.cog.__authors__)}\n**Cog version**: {self.cog.__version__}"
        if self.cog.qualified_name not in ["AAA3A_utils"]:
            text_help = text_help + f"\n**Cog documentation**: https://aaa3a-cogs.readthedocs.io/en/latest/cog_{self.cog.qualified_name.lower()}.html\n**Translate my cogs**: https://crowdin.com/project/aaa3a-cogs"
        return text_help

    def format_shortdoc_for_context(self, ctx: commands.Context):
        sh = super(type(ctx.command), ctx.command).short_doc
        try:
            return super(type(ctx.command), ctx.command).format_text_for_context(ctx, sh, shortdoc=True) if sh else sh
        except Exception:
            return super(type(ctx.command), ctx.command).format_text_for_context(ctx, sh) if sh else sh

    async def red_delete_data_for_user(self, *args, **kwargs):
        """Nothing to delete."""
        return

    async def red_get_data_for_user(self, *args, **kwargs) -> typing.Dict[typing.Any, typing.Any]:
        """Nothing to get."""
        return {}

    if discord.version_info.major >= 2:
        async def cog_unload(self):
            self._end()
    else:
        def cog_unload(self):
            self._end()

    async def cog_command_error(self, ctx: commands.Context, error: Exception):
        if self.cog is None:
            return
        if isinstance(error, commands.CommandInvokeError):
            if self.cog.cogsutils.is_dpy2 and isinstance(ctx.command, discord.ext.commands.HybridCommand):
                _type = "[hybrid|text]"
            else:
                _type = "[text]"
            message = f"Error in {_type} command '{ctx.command.qualified_name}'. Check your console or logs for details."
            if ctx.author.id in ctx.bot.owner_ids:
                message += "\nIf necessary, please inform the creator of the cog in which this command is located. Thank you."
            await ctx.send(inline(message))
            asyncio.create_task(ctx.bot._delete_delay(ctx))
            self.cog.log.exception(f"Exception in {_type} command '{ctx.command.qualified_name}'.", exc_info=error.original)
            exception_log = f"Exception in {_type} command '{ctx.command.qualified_name}'.\n"
            exception_log += "".join(traceback.format_exception(type(error), error, error.__traceback__))
            exception_log = self.cog.cogsutils.replace_var_paths(exception_log)
            ctx.bot._last_exception = exception_log
        elif isinstance(error, getattr(commands, "HybridCommandError", None)):
            _type = "[hybrid|slash]"
            message = f"Error in {_type} command '{ctx.command.qualified_name}'. Check your console or logs for details."
            if ctx.author.id in ctx.bot.owner_ids:
                message += "\nIf necessary, please inform the creator of the cog in which this command is located. Thank you."
            await ctx.send(inline(message))
            asyncio.create_task(ctx.bot._delete_delay(ctx))
            self.cog.log.exception(f"Exception in {_type} command '{ctx.command.qualified_name}'.", exc_info=error.original)
            exception_log = f"Exception in {_type} command '{ctx.command.qualified_name}'.\n"
            exception_log += "".join(traceback.format_exception(type(error), error, error.__traceback__))
            exception_log = self.cog.cogsutils.replace_var_paths(exception_log)
            ctx.bot._last_exception = exception_log
        elif isinstance(error, commands.CheckFailure):
            if getattr(ctx, "interaction", None) is not None:
                await ctx.send(inline("You are not allowed to execute this command in this context."), ephemeral=True)
        else:
            await ctx.bot.on_command_error(ctx=ctx, error=error, unhandled_by_cog=True)

    def _setup(self):
        """
        Adding additional functionality to the cog.
        """
        # for command in self.cog.walk_commands():
        #     setattr(command, 'format_text_for_context', self.format_text_for_context)
        #     setattr(command, 'format_shortdoc_for_context', self.format_shortdoc_for_context)
        specials = ["_setup", "format_text_for_context", "format_shortdoc_for_context"]
        for attr in dir(self):
            if attr.startswith("__") and attr.endswith("__"):
                continue
            if attr in specials:
                continue
            if not getattr(getattr(self.cog, attr, None), "__func__", "None1") == getattr(commands.Cog, attr, "None2"):
                continue
            setattr(self.cog, attr, getattr(self, attr))
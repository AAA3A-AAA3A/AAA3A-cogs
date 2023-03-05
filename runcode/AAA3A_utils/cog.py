from redbot.core import commands  # isort:skip
from redbot.core.bot import Red  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import asyncio
import re
import traceback
from uuid import uuid4

from redbot.core.utils.chat_formatting import humanize_list, inline, warning

from .context import Context, is_dev

__all__ = ["Cog"]


def _(untranslated: str) -> str:
    return untranslated


class Cog:
    def __init__(self, bot: Red) -> None:
        self.bot: Red = bot
        self.cog: commands.Cog = None

    @classmethod
    def _setup(cls, bot: Red, cog: commands.Cog) -> None:
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
            "verbose_forbidden_exception",
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

    def get_formatted_text(self, context: str) -> str:
        s = "s" if len(self.cog.__authors__) > 1 else ""
        text = f"{context}\n\n**Author{s}**: {humanize_list(self.cog.__authors__)}\n**Cog version**: {self.cog.__version__}\n**Cog commit**: {self.cog.__commit__}"
        if self.cog.qualified_name not in ["AAA3A_utils"]:
            text += f"\n**Cog documentation**: https://aaa3a-cogs.readthedocs.io/en/latest/cog_{self.cog.qualified_name.lower()}.html\n**Translate my cogs**: https://crowdin.com/project/aaa3a-cogs"
        return text

    def format_help_for_context(self, ctx: commands.Context) -> str:
        """Thanks Simbad!"""
        context = super(type(self.cog), self.cog).format_help_for_context(ctx)
        return self.get_formatted_text(context)

    def format_text_for_context(
        self, ctx: commands.Context, text: str, shortdoc: typing.Optional[bool] = False
    ) -> str:
        text = text.replace("        ", "")
        context = super(type(ctx.command), ctx.command).format_text_for_context(ctx, text)
        if shortdoc:
            return context
        return self.get_formatted_text(context)

    def format_shortdoc_for_context(self, ctx: commands.Context) -> str:
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

    async def red_delete_data_for_user(self, *args, **kwargs) -> None:
        """Nothing to delete."""
        return

    async def red_get_data_for_user(self, *args, **kwargs) -> typing.Dict[typing.Any, typing.Any]:
        """Nothing to get."""
        return {}

    if discord.version_info.major >= 2:

        async def cog_unload(self) -> None:
            self.cog.cogsutils._end()

    else:

        def cog_unload(self) -> None:
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

    async def cog_before_invoke(self, ctx: commands.Context) -> None:
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
            except (discord.InteractionResponded, discord.NotFound):
                pass
            context._typing = context.channel.typing()
            try:
                await context._typing.__aenter__()
            except discord.InteractionResponded:
                pass
        return context

    async def cog_after_invoke(self, ctx: commands.Context) -> None:
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

    async def cog_command_error(self, ctx: commands.Context, error: Exception) -> None:
        if self.cog is None or not hasattr(self.cog, "cogsutils"):
            await ctx.bot.on_command_error(ctx=ctx, error=error, unhandled_by_cog=True)
            return
        no_sentry = False
        AAA3A_utils = ctx.bot.get_cog("AAA3A_utils")
        if AAA3A_utils is not None:
            if getattr(AAA3A_utils, "sentry", None) is None:
                no_sentry = True
        is_command_error = False
        if isinstance(error, commands.CommandInvokeError):
            is_command_error = True
        elif self.cog.cogsutils.is_dpy2 and isinstance(error, commands.HybridCommandError):
            is_command_error = True

        if is_command_error:
            if isinstance(
                error.original, discord.Forbidden
            ):  # Error can be changed into `commands.BotMissingPermissions` or not.
                e = self.verbose_forbidden_exception(ctx, error.original)
                if e is not None and isinstance(e, commands.BotMissingPermissions):
                    error = e
            uuid = uuid4().hex
            if not no_sentry:
                AAA3A_utils.sentry.last_errors[uuid] = {"ctx": ctx, "error": error}
            if self.cog.cogsutils.is_dpy2 and isinstance(
                ctx.command, discord.ext.commands.HybridCommand
            ):
                if getattr(ctx, "interaction", None) is None:
                    _type = "[hybrid|text]"
                else:
                    _type = "[hybrid|slash]"
            elif getattr(ctx, "interaction", None) is not None:
                _type = "[slash]"
            else:
                _type = "[text]"
            message = await self.cog.cogsutils.bot._config.invoke_error_msg()
            if not message:
                message = f"Error in {_type} command '{ctx.command.qualified_name}'."
                if ctx.author.id in ctx.bot.owner_ids:
                    message += " Check your console or logs for details. If necessary, please inform the creator of the cog in which this command is located. Thank you."
                message = inline(message)
            else:
                message = message.replace("{command}", ctx.command.qualified_name)
            if (
                not no_sentry
                and not AAA3A_utils.sentry.sentry_enabled
                and await AAA3A_utils.senderrorwithsentry.can_run(ctx)
                and not getattr(AAA3A_utils.senderrorwithsentry, "__is_dev__", False)
            ):
                message += "\n" + inline(
                    f"You can send this error to the developer by running the following command:\n{ctx.prefix}AAA3A_utils senderrorwithsentry {uuid}"
                )
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
            if not no_sentry:
                await AAA3A_utils.sentry.send_command_error(ctx, error)
        elif isinstance(error, commands.UserFeedbackCheckFailure):
            if error.message:
                message = error.message
                message = warning(message)
                await ctx.send(message)
        elif isinstance(error, commands.CheckFailure) and not isinstance(
            error, commands.BotMissingPermissions
        ):
            if getattr(ctx, "interaction", None) is not None:
                await ctx.send(
                    inline("You are not allowed to execute this command in this context."),
                    ephemeral=True,
                )
        else:
            await ctx.bot.on_command_error(ctx=ctx, error=error, unhandled_by_cog=True)

    def verbose_forbidden_exception(self, ctx: commands.Context, error: discord.Forbidden) -> None:
        if not isinstance(error, discord.Forbidden):
            return ValueError(error)
        method = error.response.request_info.method
        url = str(error.response.request_info.url)
        url = url[len(discord.http.Route.BASE) :]
        url = url.split("?")[0]
        url = re.sub(r"\b\d{17,20}\b", "{snowflake}", url)
        key = f"{method.upper()} {url}"
        end_points = {
            "GET /guilds/{guild.id}/audit-logs": ["VIEW_AUDIT_LOG"],
            "GET /guilds/{guild.id}/auto-moderation/rules": ["MANAGE_GUILD"],
            "GET /guilds/{guild.id}/auto-moderation/rules/{auto_moderation_rule.id}": [
                "MANAGE_GUILD"
            ],
            "POST /guilds/{guild.id}/auto-moderation/rules": ["MANAGE_GUILD"],
            "PATCH /guilds/{guild.id}/auto-moderation/rules/{auto_moderation_rule.id}": [
                "MANAGE_GUILD"
            ],
            "DELETE /guilds/{guild.id}/auto-moderation/rules/{auto_moderation_rule.id}": [
                "MANAGE_GUILD"
            ],
            "PATCH /channels/{channel.id}": ["MANAGE_CHANNELS"],  # &! MANAGE_THREADS
            "DELETE /channels/{channel.id}": ["MANAGE_CHANNELS"],  # &! MANAGE_THREADS
            "GET /channels/{channel.id}/messages": [
                "VIEW_CHANNEL",
                "READ_MESSAGE_HISTORY",
            ],  # empty messages list
            "GET /channels/{channel.id}/messages/{message.id}": [
                "VIEW_CHANNEL",
                "READ_MESSAGE_HISTORY",
            ],
            "POST /channels/{channel.id}/messages": [
                "VIEW_CHANNEL",
                "SEND_MESSAGES",
            ],  # [SEND_TTS_MESSAGES (tts), READ_MESSAGE_HISTORY (reply)]
            "POST /channels/{channel.id}/messages/{message.id}/crosspost": [
                "MANAGE_MESSAGES"
            ],  # not own message
            "PUT /channels/{channel.id}/messages/{message.id}/reactions/{emoji}/@me": [
                "ADD_REACTIONS"
            ],
            "DELETE /channels/{channel.id}/messages/{message.id}/reactions/{emoji}/@me": [],
            "DELETE /channels/{channel.id}/messages/{message.id}/reactions/{emoji}/{user.id}": [
                "MANAGE_MESSAGES"
            ],
            "GET /channels/{channel.id}/messages/{message.id}/reactions/{emoji}": [],
            "DELETE /channels/{channel.id}/messages/{message.id}/reactions": ["MANAGE_MESSAGES"],
            "DELETE /channels/{channel.id}/messages/{message.id}/reactions/{emoji}": [
                "MANAGE_MESSAGES"
            ],
            "PATCH /channels/{channel.id}/messages/{message.id}": [],
            "DELETE /channels/{channel.id}/messages/{message.id}": ["MANAGE_MESSAGES"],
            "POST /channels/{channel.id}/messages/bulk-delete": [
                "VIEW_CHANNEL",
                "READ_MESSAGE_HISTORY",
                "MANAGE_MESSAGES",
            ],
            "PUT /channels/{channel.id}/permissions/{overwrite.id}": ["MANAGE_ROLES"],
            "GET /channels/{channel.id}/invites": ["MANAGE_CHANNELS"],
            "POST /channels/{channel.id}/invites": ["CREATE_INSTANT_INVITE"],
            "DELETE /channels/{channel.id}/permissions/{overwrite.id}": ["MANAGE_ROLES"],
            "POST /channels/{channel.id}/followers": ["MANAGE_WEBHOOKS"],
            "POST /channels/{channel.id}/typing": ["VIEW_CHANNEL", "SEND_MESSAGES"],
            "GET /channels/{channel.id}/pins": ["VIEW_CHANNEL", "VIEW_MESSAGE_HISTORY"],
            "PUT /channels/{channel.id}/pins/{message.id}": ["MANAGE_MESSAGES"],
            "DELETE /channels/{channel.id}/pins/{message.id}": ["MANAGE_MESSAGES"],
            "POST /channels/{channel.id}/messages/{message.id}/threads": ["CREATE_PUBLIC_THREADS"],
            "POST /channels/{channel.id}/threads": [
                "CREATE_PUBLIC_THREADS",
                "CREATE_PRIVATE_THREADS",
                "SEND_MESSAGES",
            ],
            "PUT /channels/{channel.id}/thread-members/@me": [],
            "DELETE /channels/{channel.id}/thread-members/@me": [],
            "DELETE /channels/{channel.id}/thread-members/{user.id}": ["MANAGE_THREADS"],
            "GET /channels/{channel.id}/thread-members/{user.id}": [],
            "GET /channels/{channel.id}/thread-members": [],
            "GET /channels/{channel.id}/threads/archived/public": [
                "VIEW_CHANNEl",
                "READ_MESSAGE_HISTORY",
            ],
            "GET /channels/{channel.id}/threads/archived/private": [
                "VIEW_CHANNEL",
                "READ_MESSAGE_HISTORY",
                "MANAGE_THREADS",
            ],
            "GET /channels/{channel.id}/users/@me/threads/archived/private": [
                "VIEW_CHANNEL",
                "READ_MESSAGE_HISTORY",
            ],
            "GET /guilds/{guild.id}/emojis": [],
            "GET /guilds/{guild.id}/emojis/{emoji.id}": [],
            "POST /guilds/{guild.id}/emojis": ["MANAGE_EMOJIS_AND_STICKERS"],
            "PATCH /guilds/{guild.id}/emojis/{emoji.id}": ["MANAGE_EMOJIS_AND_STICKERS"],
            "DELETE /guilds/{guild.id}/emojis/{emoji.id}": ["MANAGE_EMOJIS_AND_STICKERS"],
            "GET /guilds/{guild.id}/preview": [],
            "PATCH /guilds/{guild.id}": ["MANAGE_GUILD"],
            "DELETE /guilds/{guild.id}": [],
            "GET /guilds/{guild.id}/channels": [],
            "POST /guilds/{guild.id}/channels": ["MANAGE_CHANNELS"],
            "PATCH /guilds/{guild.id}/channels": ["MANAGE_CHANNELS"],
            "GET /guilds/{guild.id}/threads/active": [],
            "GET /guilds/{guild.id}/members/{user.id}": [],
            "GET /guilds/{guild.id}/members": [],
            "GET /guilds/{guild.id}/members/search": [],
            "PUT /guilds/{guild.id}/members/{user.id}": [],
            "PATCH /guilds/{guild.id}/members/{user.id}": ["MANAGE_MEMBERS", "MOVE_MEMBERS"],
            "PATCH /guilds/{guild.id}/members/@me": [],
            "PUT /guilds/{guild.id}/members/{user.id}/roles/{role.id}": ["MANAGE_ROLES"],
            "DELETE /guilds/{guild.id}/members/{user.id}/roles/{role.id}": ["MANAGE_ROLES"],
            "DELETE /guilds/{guild.id}/members/{user.id}": ["KICK_MEMBERS"],
            "GET /guilds/{guild.id}/bans": ["BAN_MEMBERS"],
            "GET /guilds/{guild.id}/bans/{user.id}": ["BAN_MEMBERS"],
            "PUT /guilds/{guild.id}/bans/{user.id}": ["BAN_MEMBERS"],
            "DELETE /guilds/{guild.id}/bans/{user.id}": ["BAN_MEMBERS"],
            "GET /guilds/{guild.id}/roles": [],
            "POST /guilds/{guild.id}/roles": ["MANAGE_ROLES"],
            "PATCH /guilds/{guild.id}/roles": ["MANAGE_ROLES"],
            "PATCH /guilds/{guild.id}/roles/{role.id}": ["MANAGE_ROLES"],
            "POST /guilds/{guild.id}/mfa": ["MANAGE_GUILD"],
            "DELETE /guilds/{guild.id}/roles/{role.id}": ["MANAGE_ROLES"],
            "GET /guilds/{guild.id}/prune": ["KICK_MEMBERS"],
            "POST /guilds/{guild.id}/prune": ["KICK_MEMBERS"],
            "GET /guilds/{guild.id}/regions": [],
            "GET /guilds/{guild.id}/invites": ["MANAGE_GUILD"],
            "GET /guilds/{guild.id}/integrations": ["MANAGE_GUILD"],
            "DELETE /guilds/{guild.id}/integrations/{integration.id}": ["MANAGE_GUILD"],
            "GET /guilds/{guild.id}/widget": ["MANAGE_GUILD"],
            "PATCH /guilds/{guild.id}/widget": ["MANAGE_GUILD"],
            "GET /guilds/{guild.id}/widget.json": [],
            "GET /guilds/{guild.id}/vanity-url": ["MANAGE_GUILD"],
            "GET /guilds/{guild.id}/widget.png": [],
            "GET /guilds/{guild.id}/welcome-screen": ["MANAGE_GUILD"],
            "PATCH /guilds/{guild.id}/welcome-screen": ["MANAGE_GUILD"],
            "PATCH /guilds/{guild.id}/voice-states/@me": ["MUTE_MEMBERS", "REQUEST_TO_SPEAK"],
            "PATCH /guilds/{guild.id}/voice-states/{user.id}": ["MUTE_MEMBERS"],
            "GET /guilds/{guild.id}/scheduled-events": [],
            "POST /guilds/{guild.id}/scheduled-events": ["MANAGE_EVENTS"],
            "GET /guilds/{guild.id}/scheduled-events/{guild_scheduled_event.id}": [],
            "PATCH /guilds/{guild.id}/scheduled-events/{guild_scheduled_event.id}": [
                "MANAGE_EVENTS"
            ],
            "DELETE /guilds/{guild.id}/scheduled-events/{guild_scheduled_event.id}": [
                "MANAGE_EVENTS"
            ],
            "GET /guilds/{guild.id}/scheduled-events/{guild_scheduled_event.id}/users": [],
            "GET /guilds/templates/{template.code}": [],
            "POST /guilds/templates/{template.code}": [],
            "GET /guilds/{guild.id}/templates": ["MANAGE_GUILD"],
            "POST /guilds/{guild.id}/templates": ["MANAGE_GUILD"],
            "PUT /guilds/{guild.id}/templates/{template.code}": ["MANAGE_GUILD"],
            "PATCH /guilds/{guild.id}/templates/{template.code}": ["MANAGE_GUILD"],
            "DELETE /guilds/{guild.id}/templates/{template.code}": ["MANAGE_GUILD"],
            "GET /invites/{invite.code}": [],
            "DELETE /invites/{invite.code}": ["MANAGE_CHANNEL"],
            "POST /stage-instances": ["MANAGE_CHANNELS"],
            "GET /stage-instances/{channel.id}": [],
            "PATCH /stage-instances/{channel.id}": ["MANAGE_CHANNEL"],
            "DELETE /stage-instances/{channel.id}": ["MANAGE_CHANNEL"],
            "GET /stickers/{sticker.id}": [],
            "GET /sticker-packs": [],
            "GET /guilds/{guild.id}/stickers": ["MANAGE_EMOJIS_AND_STICKERS"],
            "GET /guilds/{guild.id}/stickers/{sticker.id}": ["MANAGE_EMOJIS_AND_STICKERS"],
            "POST /guilds/{guild.id}/stickers": ["MANAGE_EMOJIS_AND_STICKERS"],
            "PATCH /guilds/{guild.id}/stickers/{sticker.id}": ["MANAGE_EMOJIS_AND_STICKERS"],
            "DELETE/guilds/{guild.id}/stickers/{sticker.id}": ["MANAGE_EMOJIS_AND_STICKERS"],
            "GET /users/@me": [],
            "GET /users/{user.id}": [],
            "PATCH /users/@me": [],
            "GET /users/@me/guilds": [],
            "GET /users/@me/guilds/{guild.id}/member": [],
            "DELETE /users/@me/guilds/{guild.id}": [],
            "POST /users/@me/channels": [],
            "GET /users/@me/connections": [],
            "GET /users/@me/applications/{application.id}/role-connection": [],
            "PUT /users/@me/applications/{application.id}/role-connection": [],
            "GET /voice/regions": [],
            "POST /channels/{channel.id}/webhooks": ["MANAGE_WEBHOOKS"],
            "GET /channels/{channel.id}/webhooks": ["MANAGE_WEBHOOKS"],
            "GET /guilds/{guild.id}/webhooks": ["MANAGE_WEBHOOKS"],
            "GET /webhooks/{webhook.id}": [],
            "GET /webhooks/{webhook.id}/{webhook.token}": [],
            "PATCH /webhooks/{webhook.id}": ["MANAGE_WEBHOOKS"],
            "PATCH /webhooks/{webhook.id}/{webhook.token}": ["MANAGE_WEBHOOKS"],
            "DELETE /webhooks/{webhook.id}": ["MANAGE_WEBHOOKS"],
            "DELETE /webhooks/{webhook.id}/{webhook.token}": ["MANAGE_WEBHOOKS"],
            "POST /webhooks/{webhook.id}/{webhook.token}": [],
            "POST /webhooks/{webhook.id}/{webhook.token}/slack": [],
            "POST /webhooks/{webhook.id}/{webhook.token}/github": [],
            "GET /webhooks/{webhook.id}/{webhook.token}/messages/{message.id}": [],
            "PATCH /webhooks/{webhook.id}/{webhook.token}/messages/{message.id}": [],
            "DELETE /webhooks/{webhook.id}/{webhook.token}/messages/{message.id}": [],
        }

        class FakeObject:
            id: str = "{snowflake}"
            token: str = "{snowflake}"
            code: str = "{snowflake}"

            def __str__(self):
                return "{snowflake}"

        class FakeDict(dict):
            def __getitem__(self, *args, **kwargs):
                return FakeObject()

        end_points = {_key.format_map(FakeDict()): _value for _key, _value in end_points.items()}
        if key not in end_points:
            return None
        _permissions = end_points[key]
        permissions = {}
        for permission in _permissions:
            if not permission.lower() in discord.Permissions.VALID_FLAGS:
                continue
            if getattr(
                (
                    ctx.bot_permissions
                    if self.cog.cogsutils.is_dpy2
                    else ctx.channel.permissions_for(ctx.me)
                ),
                permission.lower(),
            ):
                continue
            permissions[permission.lower()] = True
        if len(permissions) == 0:
            return None
        return commands.BotMissingPermissions(discord.Permissions(**permissions))

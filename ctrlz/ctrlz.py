from AAA3A_utils import Cog, Loop  # isort:skip
from redbot.core import commands, Config  # isort:skip
from redbot.core.bot import Red  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

from redbot.core.utils.chat_formatting import box

import datetime
import json

from .converters import AuditLogActionConverter, DateTimeConverter
from .views import CtrlZView, CtrlZMassView

# Credits:
# General repo credits.

_: Translator = Translator("CtrlZ", __file__)

REASON = "Reverted by CtrlZ."
def default_delete_method(audit_log: discord.AuditLogEntry) -> None:
    if isinstance(audit_log.target, discord.Object):
        raise RuntimeError(_("The target of the audit log was not found."))
    return audit_log.target.delete(reason=REASON)
async def default_edit_method(audit_log: discord.AuditLogEntry) -> None:
    if isinstance(audit_log.target, discord.Object):
        raise RuntimeError(_("The target of the audit log was not found."))
    kwargs = dict(audit_log.changes.after)
    for key, value in kwargs.copy().items():
        if isinstance(value, discord.asset.Asset):
            try:
                kwargs[key] = await value.read()
            except discord.HTTPException:
                del kwargs[key]
        elif isinstance(value, discord.Object):
            del kwargs[key]
    await audit_log.target.edit(**kwargs, reason=REASON)
def delete_overwrite_method(audit_log: discord.AuditLogEntry) -> None:
    if isinstance(audit_log.extra, discord.Object):
        raise RuntimeError(_("The target of the audit log was not found."))
    return audit_log.target.set_permissions(audit_log.extra, overwrite=None, reason=REASON)
def delete_bot_add_method(audit_log: discord.AuditLogEntry) -> None:
    if not isinstance(audit_log.target, discord.Member):
        raise RuntimeError(_("The target of the audit log was not found."))
    return audit_log.target.kick(reason=REASON)
def update_overwrite_method(audit_log: discord.AuditLogEntry) -> None:
    if isinstance(audit_log.extra, discord.Object):
        raise RuntimeError(_("The target of the audit log was not found."))
    return audit_log.target.set_permissions(
        audit_log.extra,
        overwrite=discord.PermissionOverwrite.from_pair(allow=audit_log.before.allow, deny=audit_log.before.deny),
        reason=REASON,
    )
def update_member_role_method(audit_log: discord.AuditLogEntry) -> None:
    if isinstance(audit_log.target, discord.Object):
        raise RuntimeError(_("The target of the audit log was not found."))
    return audit_log.target.add_roles(*[role for role in audit_log.changes.before.roles if role not in audit_log.changes.after.roles], reason=REASON)
def create_channel_method(audit_log: discord.AuditLogEntry) -> None:
    kwargs = dict(audit_log.before)
    return audit_log.guild._create_channel(
        channel_type=kwargs.pop("type"),
        overwrites=dict(kwargs.pop("overwrites", tuple())),
        **kwargs,
        reason=REASON,
    )
def create_overwrite_method(audit_log: discord.AuditLogEntry) -> None:
    return audit_log.target.set_permissions(
        audit_log.extra,
        overwrite=discord.PermissionOverwrite.from_pair(allow=audit_log.before.allow, deny=audit_log.before.deny),
        reason=REASON,
    )
def create_invite_method(audit_log: discord.AuditLogEntry) -> None:
    kwargs = dict(audit_log.before)
    return kwargs.pop("channel").create_invite(**kwargs, reason=REASON)
def create_webhook_method(audit_log: discord.AuditLogEntry) -> None:
    kwargs = dict(audit_log.before)
    return kwargs.pop("channel").create_webhook(**kwargs, reason=REASON)
async def create_scheduled_event_method(audit_log: discord.AuditLogEntry) -> None:
    kwargs = dict(audit_log.before)
    del kwargs["status"]
    for key, value in kwargs.copy().items():
        if isinstance(value, discord.asset.Asset):
            try:
                kwargs[key] = await value.read()
            except discord.HTTPException:
                del kwargs[key]
    return audit_log.guild.create_scheduled_event(image=kwargs.pop("cover_image", None), **kwargs, reason=REASON)
REVERT_METHODS: typing.Dict[str, typing.Dict[discord.AuditLogAction, typing.Callable[[discord.AuditLogEntry], None]]] = {
    "create": {
        discord.AuditLogAction.channel_create: default_delete_method,
        discord.AuditLogAction.overwrite_create: delete_overwrite_method,
        discord.AuditLogAction.ban: lambda audit_log: audit_log.guild.unban(audit_log.target, reason=REASON),
        discord.AuditLogAction.bot_add: lambda audit_log: audit_log.target.kick(reason=REASON),
        discord.AuditLogAction.role_create: default_delete_method,
        discord.AuditLogAction.invite_create: default_delete_method,
        discord.AuditLogAction.webhook_create: default_delete_method,
        discord.AuditLogAction.emoji_create: default_delete_method,
        discord.AuditLogAction.message_pin: lambda audit_log: audit_log.extra.channel.get_partial_message(audit_log.extra.message_id).unpin(reason=REASON),
        discord.AuditLogAction.integration_create: default_delete_method,
        discord.AuditLogAction.stage_instance_create: default_delete_method,
        discord.AuditLogAction.sticker_create: default_delete_method,
        discord.AuditLogAction.scheduled_event_create: default_delete_method,
        discord.AuditLogAction.thread_create: default_delete_method,
        discord.AuditLogAction.automod_rule_create: default_delete_method,
    },
    "update": {
        discord.AuditLogAction.guild_update: default_edit_method,
        discord.AuditLogAction.channel_update: default_edit_method,
        discord.AuditLogAction.overwrite_update: update_overwrite_method,
        discord.AuditLogAction.member_update: default_edit_method,
        discord.AuditLogAction.member_role_update: update_member_role_method,
        discord.AuditLogAction.role_update: default_edit_method,
        discord.AuditLogAction.webhook_update: default_edit_method,
        discord.AuditLogAction.emoji_update: default_edit_method,
        discord.AuditLogAction.stage_instance_update: default_edit_method,
        discord.AuditLogAction.sticker_update: default_edit_method,
        discord.AuditLogAction.scheduled_event_update: default_edit_method,
        discord.AuditLogAction.thread_update: default_edit_method,
        discord.AuditLogAction.automod_rule_update: default_edit_method,
    },
    "delete": {
        discord.AuditLogAction.channel_delete: create_channel_method,
        discord.AuditLogAction.overwrite_delete: delete_overwrite_method,
        discord.AuditLogAction.unban: lambda audit_log: audit_log.guild.ban(audit_log.target, reason=REASON),
        discord.AuditLogAction.role_delete: lambda audit_log: audit_log.guild.create_role(**dict(audit_log.before), reason=REASON),
        discord.AuditLogAction.invite_delete: create_invite_method,
        discord.AuditLogAction.webhook_delete: create_webhook_method,
        discord.AuditLogAction.message_unpin: lambda audit_log: audit_log.extra.channel.get_partial_message(audit_log.extra.message_id).pin(reason=REASON),
        discord.AuditLogAction.scheduled_event_delete: create_scheduled_event_method,
        discord.AuditLogAction.automod_rule_delete: lambda audit_log: audit_log.guild.create_automod_rule(**dict(audit_log.before), reason=REASON),
    },
}


@cog_i18n(_)
class CtrlZ(Cog):
    """Revert some actions in servers, from the audit logs!"""

    def __init__(self, bot: Red) -> None:
        super().__init__(bot=bot)

        self.config: Config = Config.get_conf(
            self,
            identifier=205192943327321000143939875896557571750,
            force_registration=True,
        )
        self.config.register_guild(
            reverted_audit_logs=[],
        )

    async def cog_load(self) -> None:
        await super().cog_load()
        self.loops.append(
            Loop(
                cog=self,
                name="Cleanup Old Reverted Audit Logs",
                function=self.cleanup_old_reverted_audit_logs,
                hours=1,
            )
        )

    async def get_audit_logs(
        self,
        guild: discord.Guild,
        user: typing.Optional[discord.User] = None,
        after: typing.Optional[datetime.datetime] = None,
        before: typing.Optional[datetime.datetime] = None,
        include_already_reverted: bool = True,
    ) -> typing.List[discord.AuditLogEntry]:
        _after = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(days=7)
        after = max(after, _after) if after is not None else _after
        reverted_audit_logs = await self.config.guild(guild).reverted_audit_logs()
        return [
            audit_log
            async for audit_log in guild.audit_logs(
                limit=None,
                oldest_first=True,
                user=user or discord.utils.MISSING,
                after=after,
                before=before,
            )
            if (
                await self.is_audit_log_revertable(audit_log)
                and (include_already_reverted or audit_log.id not in reverted_audit_logs)
            )
        ]

    async def get_audit_logs_actions(self) -> typing.Dict[str, typing.Dict[str, str]]:
        return {
            "create": {
                discord.AuditLogAction.channel_create: _("Channel Create"),
                discord.AuditLogAction.overwrite_create: _("Overwrite Create"),
                discord.AuditLogAction.ban: _("Ban"),
                discord.AuditLogAction.bot_add: _("Bot Add"),
                discord.AuditLogAction.role_create: _("Role Create"),
                discord.AuditLogAction.invite_create: _("Invite Create"),
                discord.AuditLogAction.webhook_create: _("Webhook Create"),
                discord.AuditLogAction.emoji_create: _("Emoji Create"),
                discord.AuditLogAction.message_pin: _("Message Pin"),
                discord.AuditLogAction.integration_create: _("Integration Create"),
                discord.AuditLogAction.stage_instance_create: _("Stage Instance Create"),
                discord.AuditLogAction.sticker_create: _("Sticker Create"),
                discord.AuditLogAction.scheduled_event_create: _("Scheduled Event Create"),
                discord.AuditLogAction.thread_create: _("Thread Create"),
                discord.AuditLogAction.automod_rule_create: _("Automod Rule Create"),
            },
            "update": {
                discord.AuditLogAction.guild_update: _("Guild Update"),
                discord.AuditLogAction.channel_update: _("Channel Update"),
                discord.AuditLogAction.overwrite_update: _("Overwrite Update"),
                discord.AuditLogAction.member_update: _("Member Update"),
                discord.AuditLogAction.member_role_update: _("Member Role Update"),
                discord.AuditLogAction.role_update: _("Role Update"),
                discord.AuditLogAction.webhook_update: _("Webhook Update"),
                discord.AuditLogAction.emoji_update: _("Emoji Update"),
                discord.AuditLogAction.stage_instance_update: _("Stage Instance Update"),
                discord.AuditLogAction.sticker_update: _("Sticker Update"),
                discord.AuditLogAction.scheduled_event_update: _("Scheduled Event Update"),
                discord.AuditLogAction.thread_update: _("Thread Update"),
                discord.AuditLogAction.automod_rule_update: _("Automod Rule Update"),
            },
            "delete": {
                discord.AuditLogAction.channel_delete: _("Channel Delete"),
                discord.AuditLogAction.overwrite_delete: _("Overwrite Delete"),
                discord.AuditLogAction.unban: _("Unban"),
                discord.AuditLogAction.role_delete: _("Role Delete"),
                discord.AuditLogAction.invite_delete: _("Invite Delete"),
                discord.AuditLogAction.webhook_delete: _("Webhook Delete"),
                discord.AuditLogAction.message_unpin: _("Message Unpin"),
                discord.AuditLogAction.scheduled_event_delete: _("Scheduled Event Delete"),
                discord.AuditLogAction.automod_rule_delete: _("Automod Rule Delete"),
            },
        }

    async def is_audit_log_revertable(self, audit_log: discord.AuditLogEntry) -> bool:
        audit_logs_actions = await self.get_audit_logs_actions()
        return any(
            audit_log.action in action_actions
            for action_actions in audit_logs_actions.values()
        )

    async def get_audit_log_embed(self, audit_log: discord.AuditLogEntry) -> discord.Embed:
        audit_log_action = audit_log.action
        audit_logs_actions = await self.get_audit_logs_actions()
        if (label := next(
            (
                action_actions[audit_log_action]
                for action_actions in audit_logs_actions.values()
                if audit_log_action in action_actions
            ),
            None,
        )) is None:
            raise RuntimeError(_("Unknown audit log action."))
        embed = discord.Embed(
            title=_("Audit Log — {label}").format(label=label),
            color=await self.bot.get_embed_color(audit_log),
            timestamp=audit_log.created_at,
        )
        embed.set_author(
            name=f"{audit_log.user.display_name} ({audit_log.user.id}){' 🤖' if audit_log.user.bot else ''}",
            icon_url=audit_log.user.display_avatar,
        )
        if audit_log.target is not None:
            embed.add_field(
                name=_("Target:"),
                value=(
                    f"{getattr(audit_log.target, 'mention', getattr(audit_log.target, 'name', repr(audit_log.target)))} ({audit_log.target.id})"
                    if not isinstance(audit_log.target, discord.Object)
                    else f"Unknown ({audit_log.target.id})" + (f" - Type {audit_log.target.type.__name__}" if audit_log.target.type != discord.Object else "")
                ),
            )
        if audit_log.reason is not None:
            embed.add_field(
                name=_("Reason:"),
                value=f">>> {audit_log.reason}",
                inline=False,
            )
        def display_diff(element: typing.Any) -> str:
            if isinstance(element, discord.AuditLogDiff):
                return display_diff(dict(element))
            elif isinstance(element, typing.Dict):
                return {key: display_diff(value) for key, value in element.items()}
            elif isinstance(element, typing.List):
                return [display_diff(value) for value in element]
            elif isinstance(element, typing.Tuple):
                return tuple(display_diff(value) for value in element)
            elif isinstance(element, (str, int)):
                return element
            return repr(element)
        if audit_log.changes.before:
            embed.add_field(
                name=_("Before:"),
                value=box(
                    json.dumps(
                        display_diff(audit_log.changes.before),
                        indent=4,
                    ),
                    lang="py",
                ),
                # value="\n".join(
                #     [
                #         f"**•** `{key}` -> `{value if isinstance(value, (str, int)) else repr(value)}`"
                #         for key, value in dict(audit_log.changes.before).items()
                #     ]
                # ),
                inline=False,
            )
        if audit_log.changes.after:
            embed.add_field(
                name=_("After:"),
                value=box(
                    json.dumps(
                        display_diff(audit_log.changes.after),
                        indent=4,
                    ),
                    lang="py",
                ),
            )
        embed.set_footer(text=audit_log.guild.name, icon_url=audit_log.guild.icon)
        return embed

    async def revert_audit_log(self, audit_log: discord.AuditLogEntry) -> None:
        audit_log_action = audit_log.action
        audit_logs_actions = await self.get_audit_logs_actions()
        if (action := next(
            (
                action
                for action, action_actions in audit_logs_actions.items()
                if audit_log_action in action_actions
            ),
            None,
        )) is None:
            raise RuntimeError(_("Unknown audit log action."))
        if audit_log.id in await self.config.guild(audit_log.guild).reverted_audit_logs():
            raise RuntimeError(_("The audit log has already been reverted."))
        try:
            await REVERT_METHODS[action][audit_log_action](audit_log)
        # except discord.NotFound:
        #     raise RuntimeError(_("The target of the audit log was not found."))
        except discord.Forbidden:
            raise RuntimeError(_("I don't have the necessary permissions or the target of the audit log is higher than me."))
        except Exception as e:
            raise RuntimeError(_("An error occurred while reverting the audit log:\n") + box(str(e), lang="py"))
        else:
            async with self.config.guild(audit_log.guild).reverted_audit_logs() as reverted_audit_logs:
                reverted_audit_logs.append(audit_log.id)

    async def cleanup_old_reverted_audit_logs(self) -> None:
        for guild_id, guild_data in (await self.config.all_guilds()).items():
            reverted_audit_logs = [
                audit_log_id
                for audit_log_id in guild_data["reverted_audit_logs"]
                if (datetime.datetime.now(tz=datetime.timezone.utc) - discord.utils.snowflake_time(audit_log_id)) < datetime.timedelta(days=7)
            ]
            await self.config.guild_from_id(guild_id).reverted_audit_logs.set(reverted_audit_logs)

    @commands.guild_only()
    @commands.guildowner()
    @commands.bot_has_guild_permissions(view_audit_log=True, embed_links=True)
    @commands.hybrid_group()
    async def ctrlz(self, ctx: commands.Context) -> None:
        """Revert some actions in servers, from the audit logs."""
        pass

    @ctrlz.command()
    async def view(
        self,
        ctx: commands.Context,
        include_already_reverted: typing.Optional[bool] = True,
        displayed_actions: commands.Greedy[AuditLogActionConverter] = None,
        user: typing.Optional[discord.User] = None,
        after: DateTimeConverter = None,
        before: DateTimeConverter = None,
    ) -> None:
        """View the audit logs that can be reverted."""
        audit_logs = await self.get_audit_logs(
            ctx.guild,
            user=user,
            after=after,
            before=before,
            include_already_reverted=include_already_reverted,
        )
        if not audit_logs:
            raise commands.UserFeedbackCheckFailure(_("No audit logs found."))
        await CtrlZView(self).start(ctx=ctx, audit_logs=audit_logs, displayed_actions=displayed_actions)

    @ctrlz.command()
    async def mass(
        self,
        ctx: commands.Context,
        displayed_actions: commands.Greedy[AuditLogActionConverter] = None,
        user: typing.Optional[discord.User] = None,
        after: DateTimeConverter = None,
        before: DateTimeConverter = None,
    ) -> None:
        """Revert all the audit logs that can be reverted.

        You can choose the audit logs to ignore.
        """
        audit_logs = await self.get_audit_logs(
            ctx.guild,
            user=user,
            after=after,
            before=before,
            include_already_reverted=False,
        )
        if not audit_logs:
            raise commands.UserFeedbackCheckFailure(_("No audit logs found."))
        await CtrlZMassView(self).start(ctx=ctx, audit_logs=audit_logs, displayed_actions=displayed_actions)

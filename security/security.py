from AAA3A_utils import Cog, CogsUtils, Loop  # isort:skip
from redbot.core import commands, Config  # isort:skip
from redbot.core.bot import Red  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import base64
import datetime
import secrets
from io import BytesIO

import numpy as np
import onetimepass
import qrcode
from PIL import Image, ImageDraw
from redbot.core import modlog
from redbot.core.utils.chat_formatting import humanize_list, box, text_to_file

from .constants import WHITELIST_TYPES, Colors, Emojis, Levels, MemberEmojis
from .modules import MODULES, Module
from .views import OBJECT_TYPING, ActionsView, SettingsView, WhitelistView

# Credits:
# General repo credits.
# Thanks to Wick's developers for some ideas of the features to include!
# Thanks to LDNOOBW for the premade lists of bad words in serveral languages (https://github.com/LDNOOBW/List-of-Dirty-Naughty-Obscene-and-Otherwise-Bad-Words)!

_: Translator = Translator("Security", __file__)


class ObjectConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> OBJECT_TYPING:
        for converter in (
            commands.MemberConverter,
            commands.RoleConverter,
            commands.TextChannelConverter,
            commands.VoiceChannelConverter,
            commands.CategoryChannelConverter,
            commands.ForumChannelConverter,
        ):
            try:
                return await converter().convert(ctx, argument)
            except commands.BadArgument:
                pass
        try:
            return discord.Webhook.from_url(argument)
        except ValueError:
            pass
        try:
            return await ctx.bot.fetch_webhook(argument)
        except discord.NotFound:
            pass
        raise commands.BadArgument(
            _(
                "Could not find a member, role, text channel, voice channel, category channel, or webhook."
            )
        )


@cog_i18n(_)
class Security(Cog):
    """Protect your servers from unwanted members, spam, but also from nuke attacks and more! This includes a quarantine/modlog system, and many modules like Auto Mod, Reports, Logging, Anti Nuke, Protected Roles, and more!"""

    def __init__(self, bot: Red) -> None:
        super().__init__(bot=bot)

        self.config: Config = Config.get_conf(
            self,
            identifier=205192943327321000143939875896557571750,
            force_registration=True,
        )
        self.config.register_guild(
            quarantine_role=None,
            # ModLog.
            modlog_channel=None,
            modlog_ping_role=None,
            # Modules.
            modules={module.key_name(): module.default_config for module in MODULES},
            recovery_key=None,
        )
        self.config.register_member(
            level=None,
            whitelist={whitelist_type["value"]: False for whitelist_type in WHITELIST_TYPES},
            # Quarantine.
            quarantined=False,
            roles_before_quarantine=[],
            integration_role_permissions_before_quarantine=None,
        )
        self.config.register_role(
            whitelist={whitelist_type["value"]: False for whitelist_type in WHITELIST_TYPES},
        )
        self.config.register_channel(
            whitelist={
                whitelist_type["value"]: False
                for whitelist_type in WHITELIST_TYPES
                if whitelist_type["channels"] or whitelist_type["categories"]
            },
        )
        self.config.init_custom("webhook", 1)
        self.config.register_custom(
            "webhook",
            whitelist={
                whitelist_type["value"]: False
                for whitelist_type in WHITELIST_TYPES
                if whitelist_type["webhooks"]
            },
        )

        self.modules: typing.Dict[str, Module] = {}

    async def cog_load(self) -> None:
        await super().cog_load()
        for module in MODULES:
            module = module(self)
            self.modules[module.key_name()] = module
            await module.load()
        await modlog.register_casetypes(
            [
                {
                    "name": "quarantine",
                    "default_setting": True,
                    "image": Emojis.QUARANTINE.value,
                    "case_str": _("Quarantined"),
                },
                {
                    "name": "unquarantine",
                    "default_setting": True,
                    "image": Emojis.UNQUARANTINE.value,
                    "case_str": _("Unquarantined"),
                },
                {
                    "name": "timeout",
                    "default_setting": True,
                    "image": Emojis.TIMEOUT.value,
                    "case_str": _("Timed Out"),
                },
                {
                    "name": "untimeout",
                    "default_setting": True,
                    "image": Emojis.TIMEOUT.value,
                    "case_str": _("Untimed Out"),
                },
                {
                    "name": "notify",
                    "default_setting": True,
                    "image": Emojis.NOTIFY.value,
                    "case_str": _("Detected"),
                },
            ]
        )
        self.loops.append(
            Loop(
                cog=self,
                name="Cleanup Task",
                function=self.cleanup_task,
                minutes=1,
            )
        )

    async def cog_unload(self) -> None:
        await super().cog_unload()
        for module in self.modules.values():
            await module.unload()
        self.modules.clear()

    async def get_member_level(self, member: discord.Member) -> Levels:
        if member == member.guild.me:
            return Levels.ME
        elif member == member.guild.owner:
            return Levels.OWNER
        level = await self.config.member(member).level()
        if level == "EXTRA_OWNER":
            return Levels.EXTRA_OWNER
        elif level == "TRUSTED_ADMIN":
            return Levels.TRUSTED_ADMIN
        elif member.bot:
            return Levels.BOT
        elif member.guild_permissions.administrator or await self.bot.is_admin(member):
            return Levels.ADMIN
        elif member.guild_permissions.manage_messages or await self.bot.is_mod(member):
            return Levels.MODERATOR
        elif datetime.datetime.now(
            tz=datetime.timezone.utc
        ) - member.joined_at >= datetime.timedelta(days=7):
            return Levels.MEMBER
        return Levels.NEW

    async def is_owner_or_higher(self, member: discord.Member) -> bool:
        return (await self.get_member_level(member)).value <= Levels.OWNER.value

    async def is_extra_owner_or_higher(self, member: discord.Member) -> bool:
        return (await self.get_member_level(member)).value <= Levels.EXTRA_OWNER.value

    async def is_trusted_admin_or_higher(self, member: discord.Member) -> bool:
        return (await self.get_member_level(member)).value <= Levels.TRUSTED_ADMIN.value

    def is_trusted_admin_or_higher_level() -> commands.check:
        async def predicate(ctx: commands.Context) -> bool:
            cog = ctx.bot.get_cog("Security")
            return await cog.is_trusted_admin_or_higher(ctx.author)

        return commands.check(predicate)

    async def is_admin_or_higher(self, member: discord.Member) -> bool:
        return (await self.get_member_level(member)).value <= Levels.ADMIN.value

    async def is_moderator_or_higher(self, member: discord.Member) -> bool:
        return (await self.get_member_level(member)).value <= Levels.MODERATOR.value

    async def get_member_emojis(self, member: discord.Member) -> str:
        level = await self.get_member_level(member)
        return MemberEmojis[level.name].value

    async def is_whitelisted(
        self,
        _object: OBJECT_TYPING,
        whitelist_type: str,
    ) -> bool:
        if (
            _whitelist_type := next(
                (item for item in WHITELIST_TYPES if item["value"] == whitelist_type),
            )
        ) is None:
            raise ValueError("Invalid whitelist type: `{whitelist_type}`.")
        _type = _object.__class__ if not isinstance(_object, discord.Object) else _object.type
        if (
            _type in (discord.TextChannel, discord.VoiceChannel, discord.ForumChannel, discord.Thread)
            and not _whitelist_type["channels"]
        ) or (_type is discord.CategoryChannel and not _whitelist_type["categories"]):
            raise ValueError(
                f"Whitelist type `{whitelist_type}` is not applicable to {_object.__class__.__name__}."
            )
        if _type is discord.Member:
            if await self.is_trusted_admin_or_higher(_object):
                return True
            if _whitelist_type["staff_allowed"] and await self.is_moderator_or_higher(_object):
                return True
            return await self.config.member(_object).whitelist.get_raw(whitelist_type) or any(
                [await self.is_whitelisted(role, whitelist_type) for role in _object.roles]
            )
        elif _type is discord.Role:
            return await self.config.role(_object).whitelist.get_raw(whitelist_type)
        elif _type in (discord.TextChannel, discord.VoiceChannel, discord.ForumChannel):
            return await self.config.channel(_object).whitelist.get_raw(whitelist_type) or (
                _object.category is not None
                and await self.is_whitelisted(_object.category, whitelist_type)
            )
        elif _type is discord.CategoryChannel:
            return await self.config.channel(_object).whitelist.get_raw(whitelist_type)
        elif _type is discord.Thread:
            return await self.is_whitelisted(_object.parent, whitelist_type)
        elif _type is discord.Webhook:
            return await self.config.custom("webhook", _object.id).whitelist.get_raw(
                whitelist_type
            ) or (
                hasattr(_object, "channel")
                and await self.is_whitelisted(_object.channel, whitelist_type)
            )

    async def is_message_whitelisted(
        self,
        message: discord.Message,
        whitelist_type: str,
    ) -> bool:
        return (
            await self.is_whitelisted(message.author, whitelist_type)
            or await self.is_whitelisted(message.channel, whitelist_type)
            or (
                message.webhook_id is not None
                and await self.is_whitelisted(
                    discord.Object(message.webhook_id, type=discord.Webhook), whitelist_type
                )
            )
        )

    async def is_quarantined(self, member: discord.Member) -> bool:
        return await self.config.member(member).quarantined()

    async def cleanup_task(self) -> None:
        for guild in self.bot.guilds:
            member_configs = await self.config.all_members(guild)
            for member_id, member_config in member_configs.items():
                if (
                    member_config["level"] is not None or any(member_config["whitelist"].values())
                ) and guild.get_member(member_id) is None:
                    await self.config.member_from_ids(guild.id, member_id).level.clear()
                    await self.config.member_from_ids(guild.id, member_id).whitelist.clear()
            if protected_role_ids := await self.config.guild(
                guild
            ).modules.protected_roles.protected_roles():
                for role_id in protected_role_ids:
                    if guild.get_role(int(role_id)) is None:
                        await self.config.guild(
                            guild
                        ).modules.protected_roles.protected_roles.clear_raw(role_id)

    async def quarantine_member(
        self,
        member: discord.Member,
        issued_by: typing.Optional[discord.Member] = None,
        reason: typing.Optional[str] = None,
        logs: typing.List[str] = None,
        trigger_messages: typing.List[discord.Message] = [],
        current_ctx: typing.Optional[commands.Context] = None,
        context_message: typing.Optional[discord.Message] = None,
    ) -> None:
        member_config = await self.config.member(member).all()
        if member_config["quarantined"]:
            raise RuntimeError(_("This member is already quarantined."))
        if await self.is_trusted_admin_or_higher(member):
            raise RuntimeError(_("You can't quarantine a trusted admin or higher."))
        if member.top_role >= member.guild.me.top_role:
            raise RuntimeError(
                _(
                    "This member is immune to quarantine because they are higher or equal than me in the role hierarchy."
                )
            )
        if not member.guild.me.guild_permissions.manage_roles:
            raise RuntimeError(_("I don't have permission to manage roles in this guild."))
        if current_ctx is not None:
            embed: discord.Embed = discord.Embed(
                title=_("Confirm Quarantine"),
                description=_("Are you sure you want to quarantine {member.mention}?").format(
                    member=member
                ),
                color=Colors.QUARANTINE.value,
            )
            if not await CogsUtils.ConfirmationAsk(
                current_ctx,
                embed=embed,
            ):
                return
        member_config["quarantined"] = True
        await self.send_modlog(  # Send modlog entry before making changes to the member.
            action="quarantine",
            member=member,
            issued_by=issued_by,
            reason=reason,
            logs=logs,
            trigger_messages=trigger_messages,
            context_message=context_message or (current_ctx.message if current_ctx else None),
            current_ctx=current_ctx,
        )
        quarantine_role: discord.Role = await self.create_or_update_quarantine_role(
            guild=member.guild
        )
        audit_log_reason = (
            f"Automated quarantine with Security."
            if issued_by is None
            else f"Quarantine issued by {issued_by.display_name} ({issued_by.id}) with Security."
        )
        try:
            unassignable_roles = [role for role in member.roles if not role.is_assignable()]
            if (
                integration_role := next(
                    (role for role in member.roles if role.is_bot_managed()), None
                )
            ) is not None:
                member_config[
                    "integration_role_permissions_before_quarantine"
                ] = integration_role.permissions.value
                await integration_role.edit(
                    permissions=discord.Permissions.none(),
                    reason=audit_log_reason,
                )
            member_config["roles_before_quarantine"] = [
                role.id for role in member.roles if role.is_assignable()
            ]
            await member.edit(
                roles=[quarantine_role] + unassignable_roles,
                reason=audit_log_reason,
            )
        except discord.HTTPException as e:
            raise RuntimeError(
                _("Failed to quarantine {member.mention}: {error}").format(
                    member=member, error=str(e)
                )
            )
        await self.config.member(member).set(member_config)

    async def unquarantine_member(
        self,
        member: discord.Member,
        issued_by: typing.Optional[discord.Member] = None,
        reason: typing.Optional[str] = None,
        logs: typing.List[str] = None,
        trigger_messages: typing.List[discord.Message] = [],
        context_message: typing.Optional[discord.Message] = None,
        current_ctx: typing.Optional[commands.Context] = None,
    ) -> None:
        member_config = await self.config.member(member).all()
        if not member_config["quarantined"]:
            raise RuntimeError(_("This member is not quarantined."))
        if not member.guild.me.guild_permissions.manage_roles:
            raise RuntimeError(_("I don't have permission to manage roles in this guild."))
        if current_ctx is not None:
            embed: discord.Embed = discord.Embed(
                title=_("Confirm Unquarantine"),
                description=_("Are you sure you want to unquarantine {member.mention}?").format(
                    member=member
                ),
                color=Colors.QUARANTINE.value,
            )
            if not await CogsUtils.ConfirmationAsk(
                current_ctx,
                embed=embed,
            ):
                return
        member_config["quarantined"] = False
        audit_log_reason = (
            f"Automated unquarantine with Security."
            if issued_by is None
            else f"Unquarantine issued by {issued_by.display_name} ({issued_by.id}) with Security."
        )
        try:
            roles_to_assign = [
                role
                for role_id in member_config["roles_before_quarantine"]
                if (role := member.guild.get_role(role_id)) is not None
            ]
            unassignable_roles = [role for role in member.roles if not role.is_assignable()]
            await member.edit(
                roles=roles_to_assign + unassignable_roles,
                reason=audit_log_reason,
            )
            member_config["roles_before_quarantine"] = []
            if (
                integration_role_permissions := member_config.get(
                    "integration_role_permissions_before_quarantine"
                )
            ) is not None:
                integration_role = next(
                    (role for role in member.roles if role.is_bot_managed()), None
                )
                if integration_role is not None:
                    await integration_role.edit(
                        permissions=discord.Permissions(integration_role_permissions),
                        reason=audit_log_reason,
                    )
                member_config["integration_role_permissions_before_quarantine"] = None
        except discord.HTTPException as e:
            raise RuntimeError(
                _("Failed to unquarantine {member.mention}: {error}").format(
                    member=member, error=str(e)
                )
            )
        await self.config.member(member).set(member_config)
        await self.send_modlog(  # Send modlog entry after making changes to the member.
            action="unquarantine",
            member=member,
            issued_by=issued_by,
            reason=reason,
            logs=logs,
            trigger_messages=trigger_messages,
            context_message=context_message or (current_ctx.message if current_ctx else None),
            current_ctx=current_ctx,
        )

    async def get_modlog_embed(
        self,
        action: typing.Literal[
            "quarantine", "unquarantine", "timeout", "untimeout", "mute", "unmute", "kick", "ban", "notify"
        ],
        member: discord.Member,
        issued_by: typing.Optional[discord.Member] = None,
        reason: typing.Optional[str] = None,
        logs: typing.List[str] = None,
        duration: typing.Optional[datetime.timedelta] = None,
    ) -> discord.Embed:
        embed: discord.Embed = discord.Embed(
            title={
                "quarantine": _("{member.display_name} has been quarantined! {emoji}").format(
                    emoji=Emojis.QUARANTINE.value, member=member
                ),
                "unquarantine": _("{member.display_name} has been unquarantined! {emoji}").format(
                    emoji=Emojis.UNQUARANTINE.value, member=member
                ),
                "timeout": _(
                    "{member.display_name} has been timed out for {duration}! {emoji}"
                ).format(
                    emoji=Emojis.TIMEOUT.value,
                    member=member,
                    duration=CogsUtils.get_interval_string(duration),
                ),
                "untimeout": _("{member.display_name} has been untimed out! {emoji}").format(
                    emoji=Emojis.TIMEOUT.value, member=member
                ),
                "mute": _("{member.display_name} has been muted for {duration}! {emoji}").format(
                    emoji=Emojis.MUTE.value,
                    member=member,
                    duration=CogsUtils.get_interval_string(duration),
                ),
                "unmute": _("{member.display_name} has been unmuted! {emoji}").format(
                    emoji=Emojis.MUTE.value, member=member
                ),
                "kick": _("{member.display_name} has been kicked! {emoji}").format(
                    emoji=Emojis.KICK.value, member=member
                ),
                "ban": _("{member.display_name} has been banned! {emoji}").format(
                    emoji=Emojis.BAN.value, member=member
                ),
                "notify": _("{member.display_name} has been detected! {emoji}").format(
                    emoji=Emojis.NOTIFY.value, member=member
                ),
            }[action],
            color=getattr(Colors, action.upper().removeprefix("UN")).value,
            timestamp=datetime.datetime.now(tz=datetime.timezone.utc),
        )
        embed.set_thumbnail(url=member.display_avatar)
        embed.set_footer(text=member.guild.name, icon_url=member.guild.icon)
        description = _(
            "{emoji} **Member:** {member.mention} (`{member}`) {member_emojis}"
        ).format(
            emoji=Emojis.MEMBER.value,
            member=member,
            member_emojis=await self.get_member_emojis(member),
        )
        if issued_by is not None:
            description += _(
                "\n{emoji} **Issued by:** {issued_by.mention} (`{issued_by}`) {issued_by_emojis}"
            ).format(
                emoji=Emojis.ISSUED_BY.value,
                issued_by=issued_by,
                issued_by_emojis=await self.get_member_emojis(issued_by),
            )
        description += _("\n{emoji} **Reason:** *{reason}*").format(
            emoji=Emojis.REASON.value, reason=reason or _("No reason provided.")
        )
        if logs:
            description += f"\n{Emojis.LOGS.value} **Logs:**\n" + "\n".join(
                f"- {log}" for log in logs
            )
        embed.description = description
        return embed

    async def send_in_modlog_channel(
        self, guild: discord.Guild, ping_role: bool = True, **kwargs
    ) -> discord.Message:
        modlog_channel: discord.TextChannel = await self.create_modlog_channel(guild=guild)
        return await modlog_channel.send(
            (
                modlog_ping_role.mention
                if (
                    ping_role
                    and (modlog_ping_role_id := await self.config.guild(guild).modlog_ping_role())
                    is not None
                    and (modlog_ping_role := guild.get_role(modlog_ping_role_id)) is not None
                )
                else None
            ),
            allowed_mentions=discord.AllowedMentions(roles=True),
            **kwargs,
        )

    async def send_modlog(
        self,
        action: typing.Literal[
            "quarantine", "unquarantine", "timeout", "untimeout", "mute", "unmute", "kick", "ban", "notify"
        ],
        member: discord.Member,
        issued_by: typing.Optional[discord.Member] = None,
        reason: typing.Optional[str] = None,
        logs: typing.List[str] = None,
        duration: typing.Optional[datetime.timedelta] = None,
        trigger_messages: typing.List[discord.Message] = [],
        context_message: typing.Optional[discord.Message] = None,
        current_ctx: typing.Optional[typing.Union[commands.Context, discord.Message]] = None,
    ) -> None:
        embed: discord.Embed = await self.get_modlog_embed(
            member=member,
            action=action,
            issued_by=issued_by,
            reason=reason,
            logs=logs,
            duration=duration,
        )
        if current_ctx is not None:
            await current_ctx.channel.send(embed=embed)
        if trigger_messages:
            raw_trigger_messages = [
                f"[{message.created_at.strftime('%Y-%m-%d %H:%M:%S')} (UTC)] #{message.channel.name}: {message.content}"
                for message in trigger_messages
            ]
            file = text_to_file(
                "\n".join(raw_trigger_messages),
                filename="auto_mod_trigger_messages.txt",
            )
            embed.description += _("\n{emoji} **Trigger Message{s}:**\n").format(
                emoji=Emojis.MESSAGE.value,
                s="" if len(trigger_messages) == 1 else "s",
            )
            to_include = [raw_trigger_messages[-1]]
            for message in reversed(raw_trigger_messages[:-1]):
                if len(embed.description) + 8 + sum(map(len, to_include)) + len(message) <= 4000:
                    to_include.insert(-2, message)
            embed.description += box("\n".join(to_include))
        else:
            file = None
        unaction = action in ("unquarantine", "untimeout", "unmute")
        view: ActionsView = ActionsView(self, member, context_message=context_message)
        await view.populate(
            include_actions=not unaction,
            action=action,
        )
        view._message = await self.send_in_modlog_channel(
            member.guild,
            ping_role=not unaction,
            embed=embed,
            file=file,
            view=view,
        )
        self.views[view._message] = view
        await modlog.create_case(
            bot=self.bot,
            guild=member.guild,
            created_at=datetime.datetime.now(tz=datetime.timezone.utc),
            action_type=action if action not in ("mute", "unmute") else f"s{action}",  # server mute/unmute
            user=member,
            moderator=issued_by,
        )
        if issued_by is None and not member.bot:
            embed.title = {
                "quarantine": _(
                    "{member.display_name}, you have been quarantined! {emoji}"
                ).format(emoji=Emojis.QUARANTINE.value, member=member),
                "unquarantine": _(
                    "{member.display_name}, you have been unquarantined! {emoji}"
                ).format(emoji=Emojis.UNQUARANTINE.value, member=member),
                "timeout": _(
                    "{member.display_name}, you have been timed out for {duration}! {emoji}"
                ).format(
                    emoji=Emojis.TIMEOUT.value,
                    member=member,
                    duration=CogsUtils.get_interval_string(duration),
                ),
                "untimeout": _("{member.display_name}, you have been untimed out! {emoji}").format(
                    emoji=Emojis.TIMEOUT.value, member=member
                ),
                "mute": _(
                    "{member.display_name}, you have been muted for {duration}! {emoji}"
                ).format(
                    emoji=Emojis.MUTE.value,
                    member=member,
                    duration=CogsUtils.get_interval_string(duration),
                ),
                "unmute": _("{member.display_name}, you have been unmuted! {emoji}").format(
                    emoji=Emojis.MUTE.value, member=member
                ),
                "kick": _("{member.display_name}, you have been kicked! {emoji}").format(
                    emoji=Emojis.KICK.value, member=member
                ),
                "ban": _("{member.display_name}, you have been banned! {emoji}").format(
                    emoji=Emojis.BAN.value, member=member
                ),
                "notify": _("{member.display_name}, you have been detected! {emoji}").format(
                    emoji=Emojis.NOTIFY.value, member=member
                ),
            }
            embed.description = embed.description.split("\n", maxsplit=1)[1]
            try:
                await member.send(
                    embed=embed,
                )
            except discord.HTTPException:
                pass

    async def create_or_update_quarantine_role(
        self,
        guild: discord.Guild,
        role_name: str = "Security Quarantine",
        color: discord.Color = Colors.QUARANTINE.value,
    ) -> discord.Role:
        if (quarantine_role_id := await self.config.guild(guild).quarantine_role()) is None or (
            quarantine_role := guild.get_role(quarantine_role_id)
        ) is None:
            try:
                quarantine_role = await guild.create_role(
                    name=role_name,
                    permissions=discord.Permissions.none(),
                    color=color,
                    reason="Creating the quarantine role used by Security.",
                )
                await quarantine_role.edit(
                    position=guild.me.top_role.position - 1,
                    reason="Setting the quarantine role position below the bot's top role.",
                )
                await self.config.guild(guild).quarantine_role.set(quarantine_role.id)
            except discord.HTTPException as e:
                raise RuntimeError(
                    _("Failed to create the quarantine role: {error}").format(error=str(e))
                )
        else:
            if quarantine_role._permissions:
                try:
                    await quarantine_role.edit(
                        permissions=discord.Permissions.none(),
                        reason="Updating the quarantine role used by Security.",
                    )
                except discord.HTTPException as e:
                    raise RuntimeError(
                        _("Failed to update the quarantine role: {error}").format(error=str(e))
                    )
        for channel in guild.channels:
            if quarantine_role not in channel.overwrites:
                overwrites = {
                    "view_channel": False,
                    "create_instant_invite": False,
                    "create_public_threads": False,
                    "create_private_threads": False,
                    "send_messages_in_threads": False,
                }
                if not isinstance(channel, discord.ForumChannel):
                    overwrites.update(
                        {
                            "send_messages": False,
                            "read_message_history": False,
                            "add_reactions": False,
                            "embed_links": False,
                        }
                    )
                if isinstance(channel, (discord.VoiceChannel, discord.CategoryChannel)):
                    overwrites.update(
                        {
                            "connect": False,
                            "speak": False,
                            "stream": False,
                        }
                    )
                await channel.set_permissions(
                    quarantine_role,
                    overwrite=discord.PermissionOverwrite(**overwrites),
                    reason="Updating the quarantine role overwrites in the channel used by Security.",
                )
        return quarantine_role

    async def create_modlog_channel(
        self,
        guild: discord.Guild,
        channel_name: str = "🛡️・security-modlog",
        channel_category: typing.Optional[discord.CategoryChannel] = None,
    ) -> discord.TextChannel:
        if (
            (modlog_channel_id := await self.config.guild(guild).modlog_channel()) is not None
            and (modlog_channel := guild.get_channel(modlog_channel_id)) is not None
            and modlog_channel.permissions_for(guild.me).view_channel
            and modlog_channel.permissions_for(guild.me).send_messages
        ):
            return modlog_channel
        try:
            modlog_channel = await guild.create_text_channel(
                name=channel_name,
                category=channel_category,
                topic=_("This channel is used for modlogs by Security."),
                overwrites={
                    guild.default_role: discord.PermissionOverwrite(view_channel=False),
                    guild.me: discord.PermissionOverwrite(
                        view_channel=True,
                        send_messages=True,
                    ),
                },
                reason="Creating the modlog channel used by Security.",
            )
            await self.config.guild(guild).modlog_channel.set(modlog_channel.id)
            return modlog_channel
        except discord.HTTPException as e:
            raise RuntimeError(
                _("Failed to create the modlog channel: {error}").format(error=str(e))
            )

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        if await self.is_quarantined(member):
            await self.config.member(member).quarantined.set(
                False
            )  # Reset quarantine status to allow re-quarantine.
            await self.quarantine_member(
                member,
                reason=_("Member joined while already quarantined."),
                logs=[
                    _(
                        "Member {member.mention} [{member}] was quarantined before leaving the server."
                    ).format(
                        member=member,
                    ),
                    _(
                        "{member.mention} [{member}] has joined again while already quarantined."
                    ).format(
                        member=member,
                    ),
                ],
            )

    @commands.Cog.listener()
    async def on_audit_log_entry_create(self, entry: discord.AuditLogEntry) -> None:
        if entry.action != discord.AuditLogAction.member_role_update:
            return
        if not isinstance(entry.target, discord.Member):
            try:
                entry.target = await entry.guild.fetch_member(entry.target.id)
            except discord.HTTPException:
                return
        if not await self.is_quarantined(entry.target):
            return
        if await self.is_whitelisted(entry.user, "quarantine"):
            return
        try:
            await entry.target.edit(
                roles=entry.before.roles,
                reason="Reverting role changes made on a quarantined member.",
            )
        except discord.HTTPException:
            return
        await self.quarantine_member(
            entry.user,
            reason=_("Tried to edit roles of a quarantined member."),
            logs=[
                _(
                    "Member {member.mention} [{member}] tried to {action} to/from the quarantined member {quarantined_member.mention} [{quarantined_member}]."
                ).format(
                    member=entry.user,
                    quarantined_member=entry.target,
                    action=humanize_list(
                        (
                            [
                                _("add the role{s} {roles}").format(
                                    roles=humanize_list(
                                        [
                                            f"{role.mention} (`{role}`)"
                                            for role in entry.after.roles
                                        ]
                                    ),
                                    s="" if len(entry.after.roles) == 1 else "s",
                                )
                            ]
                            if entry.after.roles
                            else []
                        )
                        + (
                            [
                                _("remove the role{s} {roles}").format(
                                    roles=humanize_list(
                                        [
                                            f"{role.mention} (`{role}`)"
                                            for role in entry.before.roles
                                        ]
                                    ),
                                    s="" if len(entry.before.roles) == 1 else "s",
                                )
                            ]
                            if entry.before.roles
                            else []
                        )
                    ),
                ),
            ],
        )

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel) -> None:
        if (
            (quarantine_role_id := await self.config.guild(channel.guild).quarantine_role()) is None
            or channel.guild.get_role(quarantine_role_id) is None
        ):
            return
        await self.create_or_update_quarantine_role(channel.guild)

    @commands.Cog.listener()
    async def on_command_completion(
        self, ctx: commands.Context
    ) -> None:  # Handle commands to find the right responsible of an action.
        if ctx.guild is None:
            return
        if not ctx.guild.me.guild_permissions.view_audit_log:
            return
        if ctx.command.name == "addrole":
            action, target, role = (
                discord.AuditLogAction.member_role_update,
                ctx.kwargs["user"] or ctx.author,
                ctx.args[2],
            )
        elif ctx.command.name == "kick":
            action, target, role = discord.AuditLogAction.kick, ctx.args[2], None
        elif ctx.command.name == "ban":
            action, target, role = discord.AuditLogAction.ban, ctx.args[2], None
        else:
            return
        async for entry in ctx.guild.audit_logs(action=action, user=ctx.guild.me, limit=3):
            if entry.target.id == target.id and (role is None or role.id in entry.after.roles):
                entry.user = ctx.author  # Set the user to the command author.
                for key, module in self.modules.items():
                    if key != "logging" and hasattr(module, "on_audit_log_entry_create"):
                        await module.on_audit_log_entry_create(entry)
                break

    @is_trusted_admin_or_higher_level()
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    @commands.hybrid_command(aliases=["q"])
    async def quarantine(
        self,
        ctx: commands.Context,
        member: discord.Member,
        *,
        reason: commands.Range[str, 1, 1000] = None,
    ) -> None:
        """Quarantine a member."""
        try:
            await self.quarantine_member(
                member=member,
                issued_by=ctx.author,
                reason=reason,
                current_ctx=ctx,
            )
        except RuntimeError as e:
            raise commands.UserFeedbackCheckFailure(str(e))

    @is_trusted_admin_or_higher_level()
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    @commands.hybrid_command(aliases=["uq"])
    async def unquarantine(
        self,
        ctx: commands.Context,
        member: discord.Member,
        *,
        reason: commands.Range[str, 1, 1000] = None,
    ) -> None:
        """Unquarantine a member."""
        try:
            await self.unquarantine_member(
                member=member,
                issued_by=ctx.author,
                reason=reason,
                current_ctx=ctx,
            )
        except RuntimeError as e:
            raise commands.UserFeedbackCheckFailure(str(e))

    @is_trusted_admin_or_higher_level()
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    @commands.hybrid_command(aliases=["swl"])
    async def swhitelist(
        self,
        ctx: commands.Context,
        _object: ObjectConverter,
    ) -> None:
        """Whitelist a member, role, text channel, voice channel, category channel, or webhook from Security."""
        if isinstance(_object, discord.Member) and await self.is_trusted_admin_or_higher(_object):
            raise commands.UserFeedbackCheckFailure(
                _(
                    "You can't whitelist a trusted admin or higher, they are already fully whitelisted from Security."
                )
            )
        await WhitelistView(self).start(ctx, _object)

    @is_trusted_admin_or_higher_level()
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    @commands.hybrid_command()
    async def security(
        self,
        ctx: commands.Context,
        page: typing.Literal[
            "overview",
            "authority_members",
            "join_gate",
            "auto_mod",
            "reports",
            "logging",
            "anti_nuke",
            "protected_roles",
            "lockdown",
            "unauthorized_text_channel_deletions",
        ] = "overview",
    ) -> None:
        """Manage Security settings."""
        await SettingsView(self).start(ctx, page=page)

    async def send_recovery_key(
        self,
        guild: discord.Guild,
    ) -> None:
        raw_secret = secrets.token_bytes(20)
        recovery_key = base64.b32encode(raw_secret).decode("utf-8").replace("=", "")
        data = f"otpauth://totp/{guild.name} Security?secret={recovery_key}&issuer={self.bot.user.name}"
        colors = [
            (0, 200, 100),  # Soft green
            (100, 100, 255),  # Light purple
            (255, 0, 255),  # Magenta
        ]
        qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H)
        qr.add_data(data)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGBA")
        width, height = qr_img.size
        gradient = Image.new("RGBA", (width, height), color=0)
        draw = ImageDraw.Draw(gradient)
        segments = len(colors) - 1
        for y in range(height):
            seg = int(y / height * segments)
            start = colors[seg]
            end = colors[seg + 1]
            ratio = (y - seg * height / segments) / (height / segments)
            r = int(start[0] + (end[0] - start[0]) * ratio)
            g = int(start[1] + (end[1] - start[1]) * ratio)
            b = int(start[2] + (end[2] - start[2]) * ratio)
            draw.line([(0, y), (width, y)], fill=(r, g, b, 255))
        qr_data = np.array(qr_img)
        mask = qr_data[:, :, 0] < 128  # black pixels mask
        result = Image.new("RGBA", qr_img.size, (255, 255, 255, 255))  # white background
        for y in range(height):
            for x in range(width):
                if mask[y, x]:
                    result.putpixel((x, y), gradient.getpixel((x, y)))
        buffer = BytesIO()
        result.save(buffer, format="PNG")
        buffer.seek(0)
        file = discord.File(buffer, filename="recovery_key.png")
        embed: discord.Embed = discord.Embed(
            title=_("Security Recovery Key"),
            description=_(
                "- Use [**Google Authenticator**](https://play.google.com/store/apps/details?id=com.google.android.apps.authenticator2) or a similar app to scan the QR code below.\n"
                "- This will allow you to recover access to Security in this guild, as an extra owner.\n"
                "- **Keep this key safe**, as it is the only way to recover access to Security if you lose your account.\n"
                "- This key is only valid for this guild and will not work in other guilds, and won't give you Discord ownership.\n"
                "**Do not share this key with anyone else!**"
            ),
            color=discord.Color.red(),
        )
        embed.add_field(
            name="\u200b",
            value=f"||`{recovery_key}`||",
        )
        embed.set_image(url="attachment://recovery_key.png")
        embed.set_footer(text=guild.name, icon_url=guild.icon)
        await guild.owner.send(
            embed=embed,
            file=file,
        )
        await self.config.guild(guild).recovery_key.set(recovery_key)

    @commands.dm_only()
    @commands.command()
    async def recoversecurityaccess(
        self,
        ctx: commands.Context,
        guild: discord.Guild,
        recovery_key_or_code: str,
    ) -> None:
        """Recover access to Security."""
        if (member := guild.get_member(ctx.author.id)) is None:
            raise commands.UserFeedbackCheckFailure(_("You are not a member of this guild."))
        if await self.is_extra_owner_or_higher(member):
            raise commands.UserFeedbackCheckFailure(
                _("You already have access to Security as an Extra Owner or higher in this guild.")
            )
        recovery_key = await self.config.guild(guild).recovery_key()
        if recovery_key is None:
            raise commands.UserFeedbackCheckFailure(
                _("This guild does not have a recovery key set.")
            )
        if recovery_key_or_code == recovery_key or onetimepass.valid_totp(
            recovery_key_or_code,
            secret=recovery_key,
        ):
            raise commands.UserFeedbackCheckFailure(
                _("The provided recovery key or code is invalid.")
            )
        await self.config.member(member).level.set(Levels.EXTRA_OWNER.value)
        if await self.is_quarantined(member):
            await self.unquarantine_member(
                member,
                issued_by=None,
                reason=_("Recovered access to Security."),
                current_ctx=ctx,
            )
        await ctx.send(
            _("✅ You have successfully recovered access to Security in **{guild.name}**.").format(
                guild=guild
            )
        )

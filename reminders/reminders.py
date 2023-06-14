from AAA3A_utils import Cog, CogsUtils, Settings, Loop, Menu  # isort:skip
from redbot.core import commands, app_commands, Config  # isort:skip
from redbot.core.bot import Red  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import datetime
import io
from copy import deepcopy
from inspect import cleandoc

import dateutil
import pytz

from redbot.core.utils.chat_formatting import humanize_list

from .converters import (
    DurationParser,
    ExistingReminderConverter,
    ParseException,
    TimeConverter,
    TimezoneConverter,
)  # NOQA
from .types import Content, Data, RepeatRule, Repeat, Reminder
from .views import ReminderView

# Credits:
# General repo credits.
# Thanks to PhasecoreX for the Reminder design and several ideas with his RemindMe cog (not the code)!
# Thanks to PhasecoreX for the code to parse relative durations (https://github.com/PhasecoreX/PCXCogs/blob/master/remindme/reminder_parse.py)! I added myself `òn` kwarg, allow the converter to parse `ìn` and `every` in the same time, and did many improvents.

_ = Translator("Reminders", __file__)

MAX_REMINDER_LENGTH = 1500


@app_commands.context_menu(name="Remind Me this Message")
async def remind_message_context_menu(interaction: discord.Interaction, message: discord.Message):
    cog = interaction.client.get_cog("Reminders")
    modal = discord.ui.Modal(title="Remind Me this Message")
    time_input = discord.ui.TextInput(
        label="Time",
        style=discord.TextStyle.short,
        placeholder="Reminder time",
        custom_id="reminder_time",
        required=True,
    )
    modal.add_item(time_input)
    modal.on_submit = lambda interaction: interaction.response.defer()
    await interaction.response.send_modal(modal)
    timeout = await modal.wait()
    if timeout:
        return
    context = await cog.cogsutils.invoke_command(
        author=interaction.user,
        channel=interaction.channel,
        command=f"remindme {time_input.value} {message.jump_url}",
    )
    if not await context.command.can_run(context):
        await interaction.followup.send(
            _("You're not allowed to execute the `[p]remindme` command in this channel."),
            ephemeral=True,
        )
        return


@cog_i18n(_)
class Reminders(Cog):
    """Don't forget anything anymore! Reminders in DMs, channels, FIFO commands sheduler, say sheduler... With 'Me Too', snooze and buttons."""

    # To prevent circular imports...
    Reminder = Reminder
    Repeat = Repeat
    RepeatRule = RepeatRule

    def __init__(self, bot: Red) -> None:
        self.bot: Red = bot

        self.config: Config = Config.get_conf(
            self,
            identifier=205192943327321000143939875896557571750,
            force_registration=True,
        )
        self.reminders_global: typing.Dict[str, typing.Union[int, bool]] = {
            "total_sent": 0,
            "maximum_user_reminders": 20,  # except bot owners
            "me_too": True,
            "repeat_allowed": True,
            "minimum_repeat": 60 * 1,  # minutes, so 1 hour.
            "fifo_allowed": False,
            "snooze_view": True,
        }
        self.reminders_user: typing.Dict[str, typing.List[Data]] = {
            "timezone": None,
            "reminders": {},
        }
        self.config.register_global(**self.reminders_global)
        self.config.register_user(**self.reminders_user)

        self.cache: typing.Dict[int, typing.Dict[int, Reminder]] = {}

        self.cogsutils: CogsUtils = CogsUtils(cog=self)

        _settings: typing.Dict[
            str, typing.Dict[str, typing.Union[typing.List[str], bool, str]]
        ] = {
            "maximum_user_reminders": {
                "path": ["maximum_user_reminders"],
                "converter": commands.Range[int, 1, 125],
                "description": "Change the reminders limit for a user.",
                "aliases": ["maxuserreminders"],
            },
            "me_too": {
                "path": ["me_too"],
                "converter": bool,
                "description": "Show a `Me too` button in reminders.",
            },
            "repeat_allowed": {
                "path": ["repeat_allowed"],
                "converter": bool,
                "description": "Enable or disabled repeat option for users.",
            },
            "minimum_repeat": {
                "path": ["minimum_repeat"],
                "converter": commands.Range[int, 10, None],
                "description": "Change the minimum minutes number for a repeat time.",
            },
            "fifo_allowed": {
                "path": ["fifo_allowed"],
                "converter": bool,
                "description": "Allow or deny commands reminders for users (except bot owners).",
            },
            "snooze_view": {
                "path": ["snooze_view"],
                "converter": bool,
                "description": "Send Snooze view/buttons when reminders sending.",
            },
        }
        self.settings: Settings = Settings(
            bot=self.bot,
            cog=self,
            config=self.config,
            group=self.config.GLOBAL,
            settings=_settings,
            global_path=[],
            use_profiles_system=False,
            can_edit=True,
            commands_group=self.configuration,
        )

    @property
    def loops(self) -> typing.List[Loop]:
        return list(self.cogsutils.loops.values())

    async def cog_load(self) -> None:
        await self.settings.add_commands()
        self.bot.tree.add_command(remind_message_context_menu)
        all_reminders = await self.config.all_users()
        for user_id in all_reminders:
            for reminder_id, reminder_data in all_reminders[user_id].get("reminders", {}).items():
                reminder = Reminder.from_json(cog=self, user_id=user_id, data=reminder_data)
                if user_id not in self.cache:
                    self.cache[user_id] = {}
                self.cache[user_id][int(reminder_id)] = reminder
        self.cogsutils.create_loop(function=self.reminders_loop, name="Reminders", minutes=1)

    async def cog_unload(self) -> None:
        self.bot.tree.remove_command(remind_message_context_menu.name)
        await super().cog_unload()

    async def red_delete_data_for_user(
        self,
        *,
        requester: typing.Literal["discord_deleted_user", "owner", "user", "user_strict"],
        user_id: int,
    ) -> None:
        """Delete all user reminders."""
        if requester not in ["discord_deleted_user", "owner", "user", "user_strict"]:
            return
        try:
            del self.cache[user_id]
        except KeyError:
            pass
        await self.config.user_from_id(user_id).clear()

    async def red_get_data_for_user(self, *, user_id: int) -> typing.Dict[str, io.BytesIO]:
        """Get all data about the user."""
        # sourcery skip: merge-dict-assign
        data = {
            Config.GLOBAL: {},
            Config.USER: {},
            Config.MEMBER: {},
            Config.ROLE: {},
            Config.CHANNEL: {},
            Config.GUILD: {},
        }

        data[Config.USER] = await self.config.user_from_id(user_id).all()

        _data = deepcopy(data)
        for key, value in _data.items():
            if not value:
                del data[key]
        if not data:
            return {}
        file = io.BytesIO(str(data).encode(encoding="utf-8"))
        return {f"{self.qualified_name}.json": file}

    async def reminders_loop(self) -> bool:
        executed = False
        utc_now = datetime.datetime.now(datetime.timezone.utc)
        cache = {user_id: reminders.copy() for user_id, reminders in self.cache.copy().items()}
        for reminders in cache.values():
            for reminder in reminders.values():
                reminder: Reminder
                if reminder.next_expires_at is None:
                    await reminder.delete()
                    continue
                if reminder.next_expires_at <= utc_now:
                    executed = True
                    try:
                        await reminder.process(utc_now=utc_now)
                    except RuntimeError as e:
                        self.log.error(str(e), exc_info=e)
        return executed

    def get_interval_string(
        self,
        expires: typing.Optional[
            typing.Union[
                datetime.datetime, dateutil.relativedelta.relativedelta, datetime.timedelta
            ]
        ],
        utc_now: datetime.datetime = datetime.datetime.now(datetime.timezone.utc),
        use_timestamp: bool = False,
    ) -> str:
        if expires is None:
            return "No future occurrence."
        if use_timestamp:
            expires = expires.replace(tzinfo=datetime.timezone.utc)
            return f"<t:{int(expires.timestamp())}:R>"
        if isinstance(expires, datetime.datetime):
            delta = expires - utc_now
        elif isinstance(expires, datetime.timedelta):
            delta = expires
        elif isinstance(expires, dateutil.relativedelta.relativedelta):
            delta = (utc_now + expires) - utc_now
        else:
            delta = datetime.timedelta(seconds=expires)
        result = []
        total_secs = int(max(0, delta.total_seconds()))
        years, rem = divmod(total_secs, 3600 * 24 * 365)
        if years > 0:
            result.append(f"{years} year" + ("s" if years > 1 else ""))
        weeks, rem = divmod(rem, 3600 * 24 * 7)
        if weeks > 0:
            result.append(f"{weeks} week" + ("s" if weeks > 1 else ""))
        days, rem = divmod(rem, 3600 * 24)
        if days > 0:
            result.append(f"{days} day" + ("s" if days > 1 else ""))
        hours, rem = divmod(rem, 3600)
        if hours > 0:
            result.append(f"{hours} hour" + ("s" if hours > 1 else ""))
        mins, rem = divmod(rem, 60)
        if mins > 0:
            result.append(f"{mins} minute" + ("s" if mins > 1 else ""))
        return humanize_list(result) if result else "just now"  # "0 minute"

    async def create_reminder(
        self,
        ctx: commands.Context,
        content: Content,
        expires_at: datetime.datetime,
        repeat: typing.Optional[Repeat] = None,
        created_at: datetime.datetime = datetime.datetime.now(datetime.timezone.utc),
        **kwargs,
    ) -> Reminder:
        reminder_id = 1
        while reminder_id in self.cache.get(ctx.author.id, {}):
            reminder_id += 1
        reminder_kwargs = dict(
            cog=self,
            user_id=ctx.author.id,
            id=reminder_id,
            jump_url=ctx.message.jump_url,
            snooze=False,
            me_too=False,
            content=content,
            destination=None,
            target=None,
            created_at=created_at,
            expires_at=expires_at,
            last_expires_at=None,
            next_expires_at=expires_at,
            repeat=repeat,
        )
        reminder_kwargs.update(**kwargs)
        reminder = Reminder(**reminder_kwargs)
        await reminder.save()
        return reminder

    @commands.hybrid_command()
    async def remindme(
        self, ctx: commands.Context, time: str, *, message_or_text: str = None
    ) -> None:
        """Create a reminder with optional reminder text or message.

        The specified time can be fuzzy parsed or use the kwargs `in`, `on` and `every` to find a repeat rule and your text.
        You don't have to put quotes around the time argument. For more precise parsing, you can place quotation marks around the text. Put quotation marks around the time too, if it contains spaces.
        Use `[p]reminder timetips` to display tips for time parsing.
        """
        minimum_user_reminders = await self.config.maximum_user_reminders()
        if (
            len(self.cache.get(ctx.author.id, {})) > minimum_user_reminders
            and ctx.author.id not in ctx.bot.owner_ids
        ):
            raise commands.UserFeedbackCheckFailure(
                _(
                    "You have reached the limit of {minimum_user_reminders} reminders per user."
                ).format(minimum_user_reminders=minimum_user_reminders)
            )
        try:
            if message_or_text is not None:
                utc_now, expires_at, repeat, message_or_text = await TimeConverter().convert(
                    ctx, argument=time, content=message_or_text
                )
                try:
                    message_or_text: discord.Message = await commands.MessageConverter().convert(ctx, argument=message_or_text)
                except commands.BadArgument:
                    pass
            else:
                utc_now, expires_at, repeat = await TimeConverter().convert(ctx, argument=time)
        except commands.BadArgument as e:
            raise commands.UserFeedbackCheckFailure(str(e))
        if repeat is not None:
            if not await self.config.repeat_allowed() and ctx.author.id not in ctx.bot.owner_ids:
                raise commands.UserFeedbackCheckFailure(
                    _("You are not allowed to create repeating reminders.")
                )
            for rule in repeat.rules:
                if rule.type == "sample":
                    _repeat_dict = rule.value.copy()
                    _repeat_dict.pop("years", None)
                    _repeat_dict.pop("months", None)
                    repeat_delta = datetime.timedelta(**_repeat_dict)
                    minimum_repeat = await self.config.minimum_repeat()
                    if (
                        repeat_delta < datetime.timedelta(minutes=minimum_repeat)
                        and ctx.author.id not in ctx.bot.owner_ids
                    ):
                        raise commands.UserFeedbackCheckFailure(
                            _(
                                "The repeat timedelta must be greater than {minimum_repeat} minutes."
                            ).format(minimum_repeat=minimum_repeat)
                        )
        content = {}
        message_or_text = message_or_text or (
            ctx.message.reference.cached_message if ctx.message.reference is not None else None
        )
        if isinstance(message_or_text, discord.Message):
            content = {
                "type": "message",
                "text": (
                    f"{message_or_text.clean_content[:MAX_REMINDER_LENGTH - 4]}\n..."
                    if len(message_or_text.clean_content) > MAX_REMINDER_LENGTH
                    else message_or_text.clean_content
                )
                if message_or_text.clean_content
                else None,
                "embed": message_or_text.embeds[0] if message_or_text.embeds else None,
                "message_author": {
                    "display_name": message_or_text.author.display_name,
                    "display_avatar": message_or_text.author.display_avatar.url,
                    "mention": message_or_text.author.mention,
                    "id": message_or_text.author.id,
                },
                "message_jump_url": message_or_text.jump_url,
                "files": {
                    attachment.filename: attachment.url for attachment in ctx.message.attachments
                },
            }
        elif message_or_text is not None and len(message_or_text) > MAX_REMINDER_LENGTH:
            raise commands.UserFeedbackCheckFailure(_("Your reminder text is too long."))
        else:
            content = {
                "type": "text",
                "text": message_or_text,
                "files": {
                    attachment.filename: attachment.url for attachment in ctx.message.attachments
                },
            }
        if not content["files"]:
            del content["files"]
        reminder = await self.create_reminder(
            ctx,
            content=content,
            expires_at=expires_at,
            repeat=repeat,
            created_at=utc_now,
        )
        view = ReminderView(cog=self, reminder=reminder, me_too=await self.config.me_too())
        view._message = await ctx.send(
            reminder.__str__(utc_now=utc_now),
            view=view,
            reference=discord.MessageReference.from_message(ctx.message, fail_if_not_exists=False),
            allowed_mentions=discord.AllowedMentions(replied_user=False),
        )

    @commands.guild_only()
    @commands.mod_or_permissions(mention_everyone=True)
    @commands.hybrid_command()
    async def remind(
        self,
        ctx: commands.Context,
        destination: typing.Optional[
            typing.Union[discord.TextChannel, discord.VoiceChannel, discord.Thread]
        ],
        target: typing.Optional[typing.Union[discord.User, discord.Role]],
        time: str,
        *,
        message_or_text: str = None,
    ) -> None:
        """Create a reminder with optional reminder text or message, in a channel with an user/role ping.

        The specified time can be fuzzy parsed or use the kwargs `in`, `on` and `every` to find a repeat rule and your text.
        You don't have to put quotes around the time argument. For more precise parsing, you can place quotation marks around the text. Put quotation marks around the time too, if it contains spaces.
        Use `[p]reminder timetips` to display tips for time parsing.
        """
        minimum_user_reminders = await self.config.maximum_user_reminders()
        if (
            len(self.cache.get(ctx.author.id, {})) > minimum_user_reminders
            and ctx.author.id not in ctx.bot.owner_ids
        ):
            raise commands.UserFeedbackCheckFailure(
                _(
                    "You have reached the limit of {minimum_user_reminders} reminders per user."
                ).format(minimum_user_reminders=minimum_user_reminders)
            )
        try:
            if message_or_text is not None:
                utc_now, expires_at, repeat, message_or_text = await TimeConverter().convert(
                    ctx, argument=time, content=message_or_text
                )
                try:
                    message_or_text: discord.Message = await commands.MessageConverter().convert(ctx, argument=message_or_text)
                except commands.BadArgument:
                    pass
            else:
                utc_now, expires_at, repeat = await TimeConverter().convert(ctx, argument=time)
        except commands.BadArgument as e:
            raise commands.UserFeedbackCheckFailure(str(e))
        if repeat is not None:
            if not await self.config.repeat_allowed() and ctx.author.id not in ctx.bot.owner_ids:
                raise commands.UserFeedbackCheckFailure(
                    _("You are not allowed to create repeating reminders.")
                )
            for rule in repeat.rules:
                if rule.type == "sample":
                    _repeat_dict = rule.value.copy()
                    _repeat_dict.pop("years", None)
                    _repeat_dict.pop("months", None)
                    repeat_delta = datetime.timedelta(**_repeat_dict)
                    minimum_repeat = await self.config.minimum_repeat()
                    if (
                        repeat_delta < datetime.timedelta(minutes=minimum_repeat)
                        and ctx.author.id not in ctx.bot.owner_ids
                    ):
                        raise commands.UserFeedbackCheckFailure(
                            _(
                                "The repeat timedelta must be greater than {minimum_repeat} minutes."
                            ).format(minimum_repeat=minimum_repeat)
                        )
        if destination is None:
            destination = ctx.channel
        else:
            destination_user_permissions = destination.permissions_for(ctx.author)
            destination_bot_permissions = destination.permissions_for(ctx.me)
            context = await self.cogsutils.invoke_command(
                author=ctx.author,
                channel=destination,
                command="remind",
                message=ctx.message,
                invoke=False,
            )
            if (
                not await context.command.can_run(context)
                or not destination_user_permissions.send_messages
                or not destination_bot_permissions.send_messages
            ):
                raise commands.UserFeedbackCheckFailure(
                    _("You can't create a reminder in {destination}.").format(
                        destination=destination.mention
                    )
                )
        channel_permissions = destination.permissions_for(ctx.me)
        if not channel_permissions.send_messages:
            raise commands.UserFeedbackCheckFailure(_("I can't send messages in this channel."))
        elif not channel_permissions.embed_links:
            raise commands.UserFeedbackCheckFailure(_("I can't send embeds in this channel."))
        if target is None:
            target = ctx.author
        elif (
            isinstance(target, discord.Role)
            and not destination.permissions_for(ctx.author).mention_everyone
        ):
            raise commands.UserFeedbackCheckFailure(
                _("You can't mention roles in {destination}.").format(
                    destination=destination.mention
                )
            )
        message_or_text = message_or_text or (
            ctx.message.reference.cached_message if ctx.message.reference is not None else None
        )
        if isinstance(message_or_text, discord.Message):
            content = {
                "type": "message",
                "text": (
                    f"{message_or_text.clean_content[:MAX_REMINDER_LENGTH - 4]}\n..."
                    if len(message_or_text.clean_content) > MAX_REMINDER_LENGTH
                    else message_or_text.clean_content
                )
                if message_or_text.clean_content
                else None,
                "embed": message_or_text.embeds[0] if message_or_text.embeds else None,
                "message_author": {
                    "display_name": message_or_text.author.display_name,
                    "display_avatar": message_or_text.author.display_avatar.url,
                    "mention": message_or_text.author.mention,
                    "id": message_or_text.author.id,
                },
                "message_jump_url": message_or_text.jump_url,
                "files": {
                    attachment.filename: attachment.url for attachment in ctx.message.attachments
                },
            }
        elif message_or_text is not None and len(message_or_text) > MAX_REMINDER_LENGTH:
            raise commands.UserFeedbackCheckFailure(_("Your reminder text is too long."))
        else:
            content = {
                "type": "text",
                "text": message_or_text,
                "files": {
                    attachment.filename: attachment.url for attachment in ctx.message.attachments
                },
            }
        if not content["files"]:
            del content["files"]
        reminder = await self.create_reminder(
            ctx,
            content=content,
            expires_at=expires_at,
            repeat=repeat,
            destination=destination.id,
            target={"id": target.id, "mention": target.mention},
            created_at=utc_now,
        )
        view = ReminderView(cog=self, reminder=reminder, me_too=await self.config.me_too())
        view._message = await ctx.send(
            reminder.__str__(utc_now=utc_now),
            view=view,
            reference=discord.MessageReference.from_message(ctx.message, fail_if_not_exists=False),
            allowed_mentions=discord.AllowedMentions(
                everyone=False, users=False, roles=False, replied_user=False
            ),
        )

    @commands.hybrid_group(aliases=["reminders"])
    async def reminder(self, ctx: commands.Context) -> None:
        """List, edit and delete existing reminders, or create FIFO/commands reminders."""
        pass

    @commands.guild_only()
    @commands.admin_or_permissions(administrator=True)
    @reminder.command(aliases=["command"])
    async def fifo(
        self,
        ctx: commands.Context,
        destination: typing.Optional[
            typing.Union[discord.TextChannel, discord.VoiceChannel, discord.Thread]
        ],
        time: str,
        *,
        command: str,
    ) -> None:
        """Create a FIFO/command reminder. The chosen command will be executed with you as invoker. Don't provide the prefix.

        The specified time can be fuzzy parsed or use the kwargs `in`, `on` and `every` to find a repeat rule and your text.
        You don't have to put quotes around the time argument. For more precise parsing, you can place quotation marks around the text. Put quotation marks around the time too, if it contains spaces.
        Use `[p]reminder timetips` to display tips for time parsing.
        """
        minimum_user_reminders = await self.config.maximum_user_reminders()
        if (
            len(self.cache.get(ctx.author.id, {})) > minimum_user_reminders
            and ctx.author.id not in ctx.bot.owner_ids
        ):
            raise commands.UserFeedbackCheckFailure(
                _(
                    "You have reached the limit of {minimum_user_reminders} reminders per user."
                ).format(minimum_user_reminders=minimum_user_reminders)
            )
        if not await self.config.fifo_allowed() and ctx.author.id not in ctx.bot.owner_ids:
            raise commands.UserFeedbackCheckFailure(
                _("You're not allowed to create FIFO/commands reminders.")
            )
        try:
            utc_now, expires_at, repeat, command = await TimeConverter().convert(ctx, argument=time, content=command)
        except commands.BadArgument as e:
            raise commands.UserFeedbackCheckFailure(str(e))
        if repeat is not None:
            if not await self.config.repeat_allowed() and ctx.author.id not in ctx.bot.owner_ids:
                raise commands.UserFeedbackCheckFailure(
                    _("You are not allowed to create repeating reminders.")
                )
            for rule in repeat.rules:
                if rule.type == "sample":
                    _repeat_dict = rule.value.copy()
                    _repeat_dict.pop("years", None)
                    _repeat_dict.pop("months", None)
                    repeat_delta = datetime.timedelta(**_repeat_dict)
                    minimum_repeat = await self.config.minimum_repeat()
                    if (
                        repeat_delta < datetime.timedelta(minutes=minimum_repeat)
                        and ctx.author.id not in ctx.bot.owner_ids
                    ):
                        raise commands.UserFeedbackCheckFailure(
                            _(
                                "The repeat timedelta must be greater than {minimum_repeat} minutes."
                            ).format(minimum_repeat=minimum_repeat)
                        )
        if destination is None:
            destination = ctx.channel
        destination_user_permissions = destination.permissions_for(ctx.author)
        destination_bot_permissions = destination.permissions_for(ctx.me)
        context = await self.cogsutils.invoke_command(
            author=ctx.author,
            channel=destination,
            command=command,
            message=ctx.message,
            invoke=False,
        )
        if not context.valid:
            raise commands.UserFeedbackCheckFailure(_("This command doesn't exist."))
        elif (
            not await context.command.can_run(context)
            or not destination_user_permissions.send_messages
            or not destination_bot_permissions.send_messages
        ):
            raise commands.UserFeedbackCheckFailure(
                _("You can't execute this command, in this context.")
            )
        elif context.command.qualified_name in ["shutdown", "restart", "load", "unload", "reload"]:
            raise commands.UserFeedbackCheckFailure(_("The command `{command.qualified_name}` can't be scheduled, because it's a suspicious command.").format(command=context.command))
        content = {"type": "command", "command": command, "command_invoker": ctx.author.id}
        reminder = await self.create_reminder(
            ctx,
            content=content,
            expires_at=expires_at,
            repeat=repeat,
            destination=destination.id,
            created_at=utc_now,
        )
        view = ReminderView(cog=self, reminder=reminder, me_too=await self.config.me_too())
        view._message = await ctx.send(
            reminder.__str__(utc_now=utc_now),
            view=view,
            reference=discord.MessageReference.from_message(ctx.message, fail_if_not_exists=False),
            allowed_mentions=discord.AllowedMentions(replied_user=False),
        )

    @commands.guild_only()
    @commands.guildowner_or_permissions(administrator=True)
    @reminder.command()
    async def say(
        self,
        ctx: commands.Context,
        destination: typing.Optional[
            typing.Union[discord.TextChannel, discord.VoiceChannel, discord.Thread]
        ],
        time: str,
        *,
        text: str,
    ) -> None:
        """Create a reminder who will say/send text.

        The specified time can be fuzzy parsed or use the kwargs `in`, `on` and `every` to find a repeat rule and your text.
        You don't have to put quotes around the time argument. For more precise parsing, you can place quotation marks around the text. Put quotation marks around the time too, if it contains spaces.
        Use `[p]reminder timetips` to display tips for time parsing.
        """
        minimum_user_reminders = await self.config.maximum_user_reminders()
        if (
            len(self.cache.get(ctx.author.id, {})) > minimum_user_reminders
            and ctx.author.id not in ctx.bot.owner_ids
        ):
            raise commands.UserFeedbackCheckFailure(
                _(
                    "You have reached the limit of {minimum_user_reminders} reminders per user."
                ).format(minimum_user_reminders=minimum_user_reminders)
            )
        try:
            utc_now, expires_at, repeat, text = await TimeConverter().convert(ctx, argument=time, content=text)
        except commands.BadArgument as e:
            raise commands.UserFeedbackCheckFailure(str(e))
        if repeat is not None:
            if not await self.config.repeat_allowed() and ctx.author.id not in ctx.bot.owner_ids:
                raise commands.UserFeedbackCheckFailure(
                    _("You are not allowed to create repeating reminders.")
                )
            for rule in repeat.rules:
                if rule.type == "sample":
                    _repeat_dict = rule.value.copy()
                    _repeat_dict.pop("years", None)
                    _repeat_dict.pop("months", None)
                    repeat_delta = datetime.timedelta(**_repeat_dict)
                    minimum_repeat = await self.config.minimum_repeat()
                    if (
                        repeat_delta < datetime.timedelta(minutes=minimum_repeat)
                        and ctx.author.id not in ctx.bot.owner_ids
                    ):
                        raise commands.UserFeedbackCheckFailure(
                            _(
                                "The repeat timedelta must be greater than {minimum_repeat} minutes."
                            ).format(minimum_repeat=minimum_repeat)
                        )
        if destination is None:
            destination = ctx.channel
        channel_permissions = destination.permissions_for(ctx.me)
        if not channel_permissions.send_messages:
            raise commands.UserFeedbackCheckFailure(_("I can't send messages in this channel."))
        destination_user_permissions = destination.permissions_for(ctx.author)
        destination_bot_permissions = destination.permissions_for(ctx.me)
        if not destination_user_permissions.send_messages or not destination_bot_permissions.send_messages:
            raise commands.UserFeedbackCheckFailure(
                _("You can't or I can't send messages in this channel.")
            )
        content = {
            "type": "say",
            "text": text,
            "files": {
                attachment.filename: attachment.url for attachment in ctx.message.attachments
            },
        }
        reminder = await self.create_reminder(
            ctx,
            content=content,
            expires_at=expires_at,
            repeat=repeat,
            destination=destination.id,
            created_at=utc_now,
        )
        view = ReminderView(cog=self, reminder=reminder, me_too=await self.config.me_too())
        view._message = await ctx.send(
            reminder.__str__(utc_now=utc_now),
            view=view,
            reference=discord.MessageReference.from_message(ctx.message, fail_if_not_exists=False),
            allowed_mentions=discord.AllowedMentions(replied_user=False),
        )

    @commands.bot_has_permissions(embed_links=True)
    @reminder.command(aliases=["parsingtips"])
    async def timetips(self, ctx: commands.Context) -> None:
        """Show time parsing tips."""
        tips = _(
            """
            Allowed **absolutes** are:
            • `eoy` - Remind at end of year at 17:00.
            • `eom` - Remind at end of month at 17:00.
            • `eow` - Remind at end of working week (or next friday) at 17:00.
            • `eod` - Remind at end of day at 17:00.

            Allowed **intervals** are:
            • `years`/`year`/`y`
            • `months`/`month`/`mo`
            • `weeks`/`week`/`w`
            • `days`/`day`/`d`
            • `hours`/`hour`/`hrs`/`hr`/`h`
            • `minutes`/`minute`/`mins`/`min`/`m`

            You can combine **relative intervals** like this:
            • `[in] 1y 1mo 2 days, and -5h`
            • `on 29th may at 18h, and every year`

            **Timestamps** and **iso-timestamps** are supported:
            • For ISO, be aware that specifying a timezone will ignore your timezone.

            **Dates** are supported, you can try different formats:
            • `5 jul`, `5th july`, `july 5`
            • `23 sept at 3pm`, `23 sept at 15:00`
            • `2030`
            • `[at] 10pm`
            • `friday at 9h`
            Note: the parser uses day-first and year-last (`01/02/03` -> `1st February 2003`).

            **Cron triggers** are supported:
            • Check https://crontab.guru/.
            """
        )
        embed: discord.Embed = discord.Embed(title="Time parsing tips", color=await ctx.embed_color())
        embed.description = cleandoc(tips)
        await ctx.send(embed=embed)

    @reminder.command()
    async def timezone(self, ctx: commands.Context, timezone: TimezoneConverter) -> None:
        """Set your timezone for the time converter.

        `Europe/Paris`, `America/New_York`...
        """
        await self.config.user(ctx.author).timezone.set(timezone)
        await ctx.send(_("Your timezone has been set to `{timezone}`.").format(timezone=timezone))

    @reminder.command()
    async def list(
        self,
        ctx: commands.Context,
        card: typing.Optional[bool] = False,
        sort: typing.Literal["expire", "created", "id"] = "expire",
    ) -> None:
        """List your existing reminders.

        Sort options:
        - `expire`: Display them in order of next triggering.
        - `created`: Display them in order of creating.
        - `id`: Display them in order of their ID.
        """
        if ctx.author.id not in self.cache or not (reminders := self.cache[ctx.author.id]):
            raise commands.BadArgument(_("You haven't any reminders."))
        if sort == "expire":
            reminders = list(sorted(reminders.values(), key=lambda r: r.next_expires_at))
        elif sort == "created":
            reminders = list(sorted(reminders.values(), key=lambda r: r.created_at))
        elif sort == "id":
            reminders = list(sorted(reminders.values(), key=lambda r: r.id))
        lists = []
        _reminders = reminders.copy()
        while _reminders != []:
            li = _reminders[: 15 if card else 5]
            _reminders = _reminders[15 if card else 5:]
            lists.append(li)
        embeds = []
        for li in lists:
            embed: discord.Embed = discord.Embed(
                title=_("Your Reminders"),
                description=_("You have {len_reminders} reminders. Use `{clean_prefix}reminder edit #ID` to edit a reminder.").format(
                    len_reminders=len(reminders), clean_prefix=ctx.clean_prefix
                ),
                color=await ctx.embed_color(),
            )
            embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar)
            for reminder in li:
                embed.add_field(
                    name=f"Reminder #{reminder.id}", value=reminder.get_info(), inline=card
                )
            embeds.append(embed)
        await Menu(pages=embeds).start(ctx)

    @reminder.command(aliases=["delete", "-"])
    async def remove(self, ctx: commands.Context, reminder: ExistingReminderConverter) -> None:
        """Remove an existing Reminder from its ID.

        - Use `last` to remove your last created reminder.
        - Use `next` to remove your next triggered reminder.
        """
        await reminder.delete()
        await ctx.send(
            _("The reminder **#{reminder_id}** has been successfully removed.").format(
                reminder_id=reminder.id
            )
        )

    @reminder.command()
    async def edit(self, ctx: commands.Context, reminder: ExistingReminderConverter) -> None:
        """Edit an existing Reminder from its ID.

        - Use `last` to edit your last created reminder.
        - Use `next` to edit your next triggered reminder.
        """
        embed: discord.Embed = discord.Embed(
            title=f"Reminder **#{reminder.id}**", color=await ctx.embed_color()
        )
        embed.description = reminder.get_info()
        view = ReminderView(cog=self, reminder=reminder, me_too=False)
        view._message = await ctx.send(embed=embed, view=view)

    @reminder.command()
    async def text(
        self, ctx: commands.Context, reminder: ExistingReminderConverter, *, text: str
    ) -> None:
        """Edit the text of an existing Reminder from its ID.

        - Use `last` to edit your last created reminder.
        - Use `next` to edit your next triggered reminder.
        """
        if len(text) > MAX_REMINDER_LENGTH:
            raise commands.UserFeedbackCheckFailure(_("Your reminder text is too long."))
        content = {
            "type": "text",
            "text": text,
        }
        if "files" in reminder.content:
            content["files"] = reminder.content["files"]
        reminder.content = content
        await reminder.save()
        await ctx.send(
            _("The reminder **#{reminder_id}** has been successfully edited.").format(
                reminder_id=reminder.id
            )
        )

    @reminder.command(aliases=["expiresat"])
    async def expires(
        self, ctx: commands.Context, reminder: ExistingReminderConverter, *, time: str
    ) -> None:
        """Edit the expires time of an existing Reminder from its ID.

        - Use `last` to edit your last created reminder.
        - Use `next` to edit your next triggered reminder.
        It's the same converter as for creation, but without the option of repetition.
        """
        try:
            __, expires_at, __ = await TimeConverter().convert(ctx, time)
        except commands.BadArgument as e:
            raise commands.UserFeedbackCheckFailure(str(e))
        if reminder.expires_at == reminder.next_expires_at:
            reminder.expires_at = expires_at
        reminder.next_expires_at = expires_at
        await reminder.save()
        await ctx.send(
            _("The reminder **#{reminder_id}** has been successfully edited.").format(
                reminder_id=reminder.id
            )
        )

    @reminder.command()
    async def repeat(
        self, ctx: commands.Context, reminder: ExistingReminderConverter, *, repeat: str
    ) -> None:
        """Edit the repeat of an existing Reminder from its ID.

        - Use `last` to edit your last created reminder.
        - Use `next` to edit your next triggered reminder.

        Allowed **intervals** are:
        • `years`/`year`/`y`
        • `months`/`month`/`mo`
        • `weeks`/`week`/`w`
        • `days`/`day`/`d`
        • `hours`/`hour`/`hrs`/`hr`/`h`
        • `minutes`/`minute`/`mins`/`min`/`m`

        You can combine **relative intervals** like this:
        • `1y 1mo 2 days -5h`
        """
        try:
            parse_result = DurationParser().parse(text=repeat)
        except ParseException as e:
            raise commands.UserFeedbackCheckFailure(
                f"• Relative date parsing: Impossible to parse this date. {str(e)[:100]}"
            )
        repeat_dict = parse_result["every"] if "every" in parse_result else None
        if not repeat_dict:
            raise commands.UserFeedbackCheckFailure(
                "• Relative date parsing: Impossible to parse this date."
            )
        repeat_dict = {"type": "sample", "value": repeat_dict}
        if not await self.config.repeat_allowed() and ctx.author.id not in ctx.bot.owner_ids:
            raise commands.UserFeedbackCheckFailure(
                _("You are not allowed to create repeating reminders.")
            )
        if repeat_dict["type"] == "sample":
            _repeat_dict = repeat_dict["value"].copy()
            if "years" in _repeat_dict:
                if "days" not in _repeat_dict:
                    _repeat_dict["days"] = 0
                _repeat_dict["days"] += _repeat_dict.pop("years") * 365
            repeat_delta = dateutil.relativedelta.relativedelta(**_repeat_dict)
            minimum_repeat = await self.config.minimum_repeat()
            if (
                repeat_delta < dateutil.relativedelta.relativedelta(minutes=minimum_repeat)
                and ctx.author.id not in ctx.bot.owner_ids
            ):
                raise commands.UserFeedbackCheckFailure(
                    _(
                        "The repeat timedelta must be greater than {minimum_repeat} minutes."
                    ).format(minimum_repeat=minimum_repeat)
                )
        reminder.intervals = Intervals.from_json([repeat_dict])
        await reminder.save()
        await ctx.send(
            _("The reminder **#{reminder_id}** has been successfully edited.").format(
                reminder_id=reminder.id
            )
        )

    @reminder.command()
    async def clear(self, ctx: commands.Context, confirmation: bool = False) -> None:
        """Clear all your existing reminders."""
        if ctx.author.id not in self.cache or not self.cache[ctx.author.id]:
            raise commands.BadArgument(_("You haven't any reminders."))
        if not confirmation and not ctx.assume_yes:
            embed: discord.Embed = discord.Embed()
            embed.title = _("⚠️ - Reminders")
            embed.description = _("Do you really want to remove ALL your reminders?")
            embed.color = 0xF00020
            if not await self.cogsutils.ConfirmationAsk(
                ctx, content=f"{ctx.author.mention}", embed=embed
            ):
                await self.cogsutils.delete_message(ctx.message)
                return
        await self.config.user(ctx.author).reminders.clear()
        try:
            del self.cache[ctx.author.id]
        except KeyError:
            pass
        await ctx.send(_("All your reminders have been successfully removed."))

    async def _cogsutils_add_hybrid_commands(
        self, command: typing.Union[commands.HybridCommand, commands.HybridGroup]
    ) -> None:
        if command.app_command is None:
            return
        if not isinstance(command, commands.HybridCommand):
            return
        if "message_or_text" in command.app_command._params:
            command.app_command._params["message_or_text"].required = True
        if "target" in command.app_command._params and command.qualified_name == "remind":
            command.app_command._params["target"].required = True
        _params1 = command.app_command._params.copy()
        _params2 = list(command.app_command._params.keys())
        _params2 = sorted(_params2, key=lambda x: _params1[x].required, reverse=True)
        _params3 = {key: _params1[key] for key in _params2}
        command.app_command._params = _params3

    @timezone.autocomplete("timezone")
    async def timezone_timezone_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> typing.List[app_commands.Choice[str]]:
        return (
            [
                app_commands.Choice(name=timezone, value=timezone)
                for timezone in list(pytz.common_timezones)
                if timezone.lower().startswith(current.lower())
            ][:25]
            if current
            else [
                app_commands.Choice(name=timezone, value=timezone)
                for timezone in list(pytz.common_timezones)[:25]
            ]
        )

    @commands.is_owner()
    @commands.hybrid_group(name="setreminders")
    async def configuration(self, ctx: commands.Context) -> None:
        """Configure Reminders."""
        pass

    @configuration.command()
    async def clearuserreminders(
        self, ctx: commands.Context, user: discord.User, confirmation: bool = False
    ) -> None:
        """Clear all existing reminders for a user."""
        if user.id not in self.cache or not self.cache[user.id]:
            raise commands.BadArgument(_("This user haven't any reminders."))
        if not confirmation and not ctx.assume_yes:
            embed: discord.Embed = discord.Embed()
            embed.title = _("⚠️ - Reminders")
            embed.description = _(
                "Do you really want to remove ALL {user.display_name}'s reminders?"
            ).format(user=user)
            embed.color = 0xF00020
            if not await self.cogsutils.ConfirmationAsk(
                ctx, content=f"{ctx.author.mention}", embed=embed
            ):
                await self.cogsutils.delete_message(ctx.message)
                return
        await self.config.user(user).reminders.clear()
        try:
            del self.cache[user.id]
        except KeyError:
            pass
        await ctx.send(_("All user's reminders have been successfully removed."))

    @configuration.command(hidden=True)
    async def getdebugloopsstatus(self, ctx: commands.Context) -> None:
        """Get an embed to check loops status."""
        embeds = [loop.get_debug_embed() for loop in self.cogsutils.loops.values()]
        await Menu(pages=embeds).start(ctx)

    @configuration.command()
    async def migratefromremindme(self, ctx: commands.Context) -> None:
        """Migrate Reminders from RemindMe by PhasecoreX."""
        old_config: Config = Config.get_conf(
            "RemindMe", identifier=1224364860, force_registration=True, cog_name="RemindMe"
        )
        old_global_data = await old_config.all()
        if "schema_version" not in old_global_data:
            raise commands.UserFeedbackCheckFailure(
                _("RemindMe by PhasecoreX has no data in this bot.")
            )
        elif old_global_data["schema_version"] != 2:
            raise commands.UserFeedbackCheckFailure(
                _(
                    "RemindMe by PhasecoreX use an old/new data schema version and isn't compatible with this cog actually."
                )
            )
        new_global_data = await self.config.all()
        new_global_data["total_sent"] += old_global_data.get("total_sent", 0)
        new_global_data["me_too"] = old_global_data.get(
            "me_too", self.config._defaults[Config.GLOBAL]["me_too"]
        )
        new_global_data["maximum_user_reminders"] = old_global_data.get(
            "max_user_reminders", self.config._defaults[Config.GLOBAL]["maximum_user_reminders"]
        )
        await self.config.set(new_global_data)
        utc_now = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
        old_reminders_data = await old_config.custom("REMINDER").all()
        for user_id in old_reminders_data:
            reminder_id = 1
            for __, reminder_data in old_reminders_data[user_id].items():
                if (
                    ctx.bot.get_user(int(user_id)) is not None
                    and reminder_data["expires"] >= utc_now
                ):
                    while reminder_id in self.cache.get(int(user_id), {}):
                        reminder_id += 1
                    reminder = Reminder(
                        cog=self,
                        user_id=int(user_id),
                        id=reminder_id,
                        jump_url=reminder_data["jump_link"],
                        snooze=False,
                        title=None,
                        content={"type": "text", "text": reminder_data["text"]},
                        destination=None,
                        target=None,
                        created_at=datetime.datetime.fromtimestamp(
                            reminder_data["created"], tz=datetime.timezone.utc
                        ),
                        expires_at=datetime.datetime.fromtimestamp(
                            reminder_data["expires"], tz=datetime.timezone.utc
                        ),
                        last_expires_at=None,
                        next_expires_at=datetime.datetime.fromtimestamp(
                            reminder_data["expires"], tz=datetime.timezone.utc
                        ),
                        repeat=Repeat.from_json(
                            [{"type": "sample", "value": reminder_data["repeat"]}]
                        )
                        if reminder_data.get("repeat")
                        else None,
                    )
                    await reminder.save()

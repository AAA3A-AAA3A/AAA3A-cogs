from AAA3A_utils import CogsUtils  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import asyncio
import datetime

import dateutil
import pytz
import validators

from .converters import TimeConverter

_ = Translator("Reminders", __file__)

MAX_REMINDER_LENGTH = 1500


class EditReminderModal(discord.ui.Modal):
    def __init__(
        self,
        parent: discord.ui.View,
        timezone: typing.Optional[pytz.timezone] = pytz.timezone("UTC"),
    ) -> None:
        self._parent: discord.ui.View = parent
        self.reminder = self._parent.reminder
        self.timezone: pytz.timezone = timezone

        super().__init__(title=f"Edit Reminder #{self.reminder.id}")

        if self.reminder.content["type"] not in ["command", "say"]:
            self.title_input: discord.ui.TextInput = discord.ui.TextInput(
                label="Title",
                placeholder="(optional)",
                default=self.reminder.content.get("title"),
                style=discord.TextStyle.short,
                max_length=200,
                custom_id="title",
                required=False,
            )
            self.add_item(self.title_input)
        else:
            self.title_input = None
        if self.reminder.content["type"] in ["text", "say"]:
            self.content: discord.ui.TextInput = discord.ui.TextInput(
                label="Text",
                placeholder="(required)"
                if self.reminder.content["type"] == "say"
                else "(optional)",
                default=self.reminder.content["text"],
                style=discord.TextStyle.paragraph,
                max_length=MAX_REMINDER_LENGTH,
                custom_id="text",
                required=self.reminder.content["type"] == "say",
            )
            self.add_item(self.content)
        elif self.reminder.content["type"] == "command":
            self.content: discord.ui.TextInput = discord.ui.TextInput(
                label="Command",
                placeholder="(required)",
                default=self.reminder.content["command"],
                style=discord.TextStyle.paragraph,
                max_length=MAX_REMINDER_LENGTH,
                custom_id="command",
                required=True,
            )
            self.add_item(self.content)
        else:
            self.content = None
        if self.reminder.content["type"] not in ["command", "say"]:
            self.image_url: discord.ui.TextInput = discord.ui.TextInput(
                label="Image URL",
                placeholder="(optional)",
                default=self.reminder.content.get("image_url"),
                style=discord.TextStyle.short,
                custom_id="image_url",
                required=False,
            )
            self.add_item(self.image_url)
        else:
            self.image_url = None
        self.next_expires_at: discord.ui.TextInput = discord.ui.TextInput(
            label="Next Expires at",
            placeholder="(required)",
            default=self.reminder.next_expires_at.astimezone(tz=self.timezone).isoformat(),
            style=discord.TextStyle.short,
            custom_id="next_expires_at",
            required=True,
        )
        self.add_item(self.next_expires_at)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if self.image_url is not None and self.image_url.value is not None:
            try:
                validators.url(self.image_url.value, public=True)
            except validators.ValidationFailure:
                await interaction.response.send_message(
                    _("The image URL must be a valid URL.").format(reminder_id=self.reminder.id),
                    ephemeral=True,
                )
                return
        if (
            self.next_expires_at.value
            != self.reminder.next_expires_at.astimezone(tz=self.timezone).isoformat()
        ):
            try:
                fake_context: commands.Context = await interaction.client.get_context(
                    interaction.message
                )
                fake_context.author = interaction.user
                __, expires_at, __ = await TimeConverter().convert(
                    fake_context,
                    self.next_expires_at.value,
                )
            except commands.BadArgument as e:
                await interaction.response.send_message(str(e), ephemeral=True)
                return
            if self.reminder.expires_at == self.reminder.next_expires_at:
                self.reminder.expires_at = expires_at
            self.reminder.next_expires_at = expires_at
        first_message = self.reminder.expires_at == self.reminder.next_expires_at
        if self.reminder.content["type"] == "text":
            self.reminder.content["text"] = self.content.value or None
        elif self.reminder.content["type"] == "say":
            self.reminder.content["text"] = self.content.value
        elif self.reminder.content["type"] == "command":
            self.reminder.content["command"] = self.content.value
        if self.title_input is not None and self.title_input.value is not None:
            self.reminder.content["title"] = self.title_input.value or None
        if self.image_url is not None and self.image_url.value is not None:
            self.reminder.content["image_url"] = self.image_url.value or None
        await self.reminder.save()
        if self._parent._message is not None:
            try:
                if self._parent._message.embeds:
                    embed = self._parent._message.embeds[0].copy()
                    embed.description = self.reminder.get_info()
                    if embed.description != self._parent._message.embeds[0].description:
                        self._parent._message = await self._parent._message.edit(embed=embed)
                elif first_message:
                    content = self.reminder.__str__(utc_now=self.reminder.created_at)
                    if content != self._parent._message.content:
                        self._parent._message = await self._parent._message.edit(
                            content=content,
                            allowed_mentions=discord.AllowedMentions(
                                everyone=False, users=False, roles=False, replied_user=False
                            ),
                        )
            except discord.HTTPException:
                pass
        await interaction.response.send_message(
            _("Your reminder **#{reminder_id}** has been successfully edited.").format(
                reminder_id=self.reminder.id
            ),
            ephemeral=True,
        )


class ReminderView(discord.ui.View):
    def __init__(self, cog: commands.Cog, reminder, me_too: bool = True) -> None:
        super().__init__(timeout=3600 * 12)
        self.cog: commands.Cog = cog

        self.reminder = reminder
        if not me_too or self.reminder.content["type"] in ["command", "say"]:
            self.remove_item(self.me_too)
        self.me_too_members: typing.Dict[discord.Member, typing.Any] = {}

        self._message: discord.Message = None
        self._ready: asyncio.Event = asyncio.Event()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if (
            self.reminder.next_expires_at is None
            and interaction.data["custom_id"] != "cross_button"
        ):
            await interaction.response.send_message(
                "This reminder is already expired.", ephemeral=True
            )
            await self.on_timeout()
            self.stop()
            return False
        if interaction.data["custom_id"] == "me_too":
            return True
        if interaction.user.id not in [self.reminder.user_id] + list(self.cog.bot.owner_ids):
            await interaction.response.send_message(
                "You are not allowed to use this interaction.", ephemeral=True
            )
            return False
        return True

    async def on_timeout(self) -> None:
        for child in self.children:
            child: discord.ui.Item
            if hasattr(child, "disabled") and not (
                isinstance(child, discord.ui.Button) and child.style == discord.ButtonStyle.url
            ):
                child.disabled = True
        try:
            await self._message.edit(view=self)
        except discord.HTTPException:
            pass
        self._ready.set()

    @discord.ui.button(
        label="Edit Reminder",
        emoji="🛠️",
        style=discord.ButtonStyle.secondary,
        custom_id="edit_reminder",
    )
    async def edit_reminder(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        timezone = pytz.timezone(
            await self.cog.config.user_from_id(self.reminder.user_id).timezone() or "UTC"
        )
        await interaction.response.send_modal(EditReminderModal(self, timezone=timezone))

    @discord.ui.button(
        label="Add/Edit Repeat Rule(s)",
        emoji="🛠️",
        style=discord.ButtonStyle.secondary,
        custom_id="add_edit_repeat_rules",
    )
    async def add_edit_repeat_rules(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        embed: discord.Embed = discord.Embed(
            title=_("Reminder #{reminder_id} Repeat Rules").format(reminder_id=self.reminder.id),
            color=discord.Color.green(),
        )
        if self.reminder.repeat is None:
            embed.description = _("No existing repeat rule(s).")
        else:
            embed.description = self.reminder.repeat.get_info()
        view = RepeatView(cog=self.cog, reminder=self.reminder)
        await interaction.response.send_message(embed=embed, view=view)
        view._message = await interaction.original_response()

    @discord.ui.button(
        label="Me Too", emoji="🔔", style=discord.ButtonStyle.secondary, custom_id="me_too"
    )
    async def me_too(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if interaction.user.id == self.reminder.user_id:
            await interaction.response.send_message(
                "You are not allowed to create the same reminder several times.",
                ephemeral=True,
            )
            return
        elif interaction.user in self.me_too_members:
            reminder = self.me_too_members[interaction.user]
            reminder.next_expires_at = None
            await reminder.delete()
            await interaction.response.send_message(
                _("Reminder **#{reminder_id}** deleted.").format(reminder_id=reminder.id),
                ephemeral=True,
            )
        reminder_id = 1
        while reminder_id in self.cog.cache.get(interaction.user.id, {}):
            reminder_id += 1
        utc_now = datetime.datetime.now(tz=datetime.timezone.utc)
        reminder = self.cog.Reminder(
            cog=self.cog,
            user_id=interaction.user.id,
            id=reminder_id,
            jump_url=interaction.message.jump_url,
            snooze=False,
            me_too=True,
            content=self.reminder.content,
            destination=None,
            targets=None,
            created_at=utc_now,
            expires_at=self.reminder.next_expires_at,
            last_expires_at=None,
            next_expires_at=self.reminder.next_expires_at,
            repeat=self.reminder.repeat,
        )
        await reminder.save()
        self.me_too_members[interaction.user] = reminder
        await interaction.response.send_message(
            reminder.__str__(utc_now=utc_now),
            ephemeral=True,
        )

    @discord.ui.button(
        label="Delete Reminder",
        emoji="🗑️",
        style=discord.ButtonStyle.danger,
        custom_id="delete_reminder",
    )
    async def delete_reminder(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        self.reminder.next_expires_at = None
        await self.reminder.delete()
        await interaction.response.send_message(
            _("Reminder **#{reminder_id}** deleted.").format(reminder_id=self.reminder.id)
        )
        await self.on_timeout()
        self.stop()

    @discord.ui.button(emoji="✖️", style=discord.ButtonStyle.danger, custom_id="cross_button")
    async def cross_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await CogsUtils.delete_message(self._message)
        self.stop()


class AddRepeatRuleModal(discord.ui.Modal):
    def __init__(
        self,
        parent: discord.ui.View,
    ) -> None:
        self._parent: discord.ui.View = parent
        self.reminder = self._parent.reminder

        super().__init__(title=f"Add Repeat Rule to Reminder #{self.reminder.id}")

        self.repeat_rule: discord.ui.TextInput = discord.ui.TextInput(
            label="Repeat Rule",
            placeholder="(required)",
            default=None,
            style=discord.TextStyle.short,
            max_length=200,
            custom_id="repeat_rule",
            required=True,
        )
        self.add_item(self.repeat_rule)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        try:
            fake_context: commands.Context = await interaction.client.get_context(
                interaction.message
            )
            fake_context.author = interaction.user
            utc_now, expires_at, repeat = await TimeConverter().convert(
                fake_context,
                argument=self.repeat_rule.value,
            )
        except commands.BadArgument as e:
            await interaction.response.send_message(str(e), ephemeral=True)
            return
        # if repeat is None:
        #     await interaction.response.send_message(_("No repeat rule found in your input."), ephemeral=True)
        #     return
        if self.reminder.repeat is None:
            self.reminder.repeat = self._parent.cog.Repeat(rules=[])
        if repeat is not None:
            self.reminder.repeat.rules.append(repeat.rules[0])
        else:
            self.reminder.repeat.rules.append(
                self._parent.cog.RepeatRule.from_json(
                    {
                        "type": "date",
                        "value": int(expires_at.timestamp()),
                        "start_trigger": int(utc_now.timestamp()),
                        "first_trigger": None,
                        "last_trigger": None,
                    }
                )
            )
        await self.reminder.save()
        if self._parent._message is not None:
            try:
                embed = self._parent._message.embeds[0]
                embed.description = self.reminder.repeat.get_info()
                self._parent.remove_repeat_rule.disabled = False
                self._parent.stop_repeat.disabled = False
                self._parent._message = await self._parent._message.edit(
                    embed=embed, view=self._parent
                )
            except discord.HTTPException:
                pass
        await interaction.response.send_message(
            _("Your reminder **#{reminder_id}** has been successfully edited.").format(
                reminder_id=self.reminder.id
            ),
            ephemeral=True,
        )


class RemoveRepeatRuleModal(discord.ui.Modal):
    def __init__(
        self,
        parent: discord.ui.View,
    ) -> None:
        self._parent: discord.ui.View = parent
        self.reminder = self._parent.reminder

        super().__init__(title=f"Remove Repeat Rule from Reminder #{self.reminder.id}")

        self.index_number_repeat_rule: discord.ui.TextInput = discord.ui.TextInput(
            label="Index Number Repeat Rule",
            placeholder="(required)",
            default=None,
            style=discord.TextStyle.short,
            max_length=str(len(self.reminder.repeat.rules)),
            custom_id="index_number_repeat_rule",
            required=True,
        )
        self.add_item(self.index_number_repeat_rule)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        try:
            index_number_repeat_rule = int(self.index_number_repeat_rule.value)
        except ValueError as e:
            await interaction.response.send_message(str(e), ephemeral=True)
            return
        if self.reminder.repeat is None:
            await interaction.response.send_message(
                _("No existing repeat rule(s)."), ephemeral=True
            )
            return
        try:
            del self.reminder.repeat.rules[index_number_repeat_rule - 1]
        except ValueError:
            await interaction.response.send_message(
                _("No existing repeat rule found with this index number."), ephemeral=True
            )
            return
        await self.reminder.save()
        if self._parent._message is not None:
            try:
                embed = self._parent._message.embeds[0]
                embed.description = self.reminder.repeat.get_info() or _(
                    "No existing repeat rule(s)."
                )
                self._parent.remove_repeat_rule.disabled = not self.reminder.repeat.rules
                self._parent.stop_repeat.disabled = not self.reminder.repeat.rules
                self._parent._message = await self._parent._message.edit(
                    embed=embed, view=self._parent
                )
            except discord.HTTPException:
                pass
        await interaction.response.send_message(
            _("Your reminder **#{reminder_id}** has been successfully edited.").format(
                reminder_id=self.reminder.id
            ),
            ephemeral=True,
        )


class RepeatView(discord.ui.View):
    def __init__(self, cog: commands.Cog, reminder) -> None:
        super().__init__(timeout=60 * 10)
        self.cog: commands.Cog = cog

        self.reminder = reminder
        self.remove_repeat_rule.disabled = (
            self.reminder.repeat is None or not self.reminder.repeat.rules
        )
        self.stop_repeat.disabled = self.reminder.repeat is None or not self.reminder.repeat.rules

        self._message: discord.Message = None
        self._ready: asyncio.Event = asyncio.Event()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id not in [self.reminder.user_id] + list(self.cog.bot.owner_ids):
            await interaction.response.send_message(
                "You are not allowed to use this interaction.", ephemeral=True
            )
            return False
        if (
            self.reminder.next_expires_at is None
            and interaction.data["custom_id"] != "cross_button"
        ):
            await interaction.response.send_message(
                "This reminder is already expired.", ephemeral=True
            )
            await self.on_timeout()
            self.stop()
            return False
        return True

    async def on_timeout(self) -> None:
        if self._message is not None:
            try:
                await self._message.edit(view=None)
            except discord.HTTPException:
                pass
        self._ready.set()

    @discord.ui.button(
        label="Add Repeat Rule",
        emoji="🛠️",
        style=discord.ButtonStyle.secondary,
        custom_id="add_repeat_rule",
    )
    async def add_repeat_rule(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        if self.reminder.repeat is not None and len(self.reminder.repeat.rules) > 10:
            await interaction.response.send_message(
                _("A maximum of 10 repeat rules per reminder is supported."), ephemeral=True
            )
            return
        await interaction.response.send_modal(AddRepeatRuleModal(self))

    @discord.ui.button(
        label="Remove Repeat Rule",
        emoji="🛠️",
        style=discord.ButtonStyle.secondary,
        custom_id="remove_repeat_rule",
    )
    async def remove_repeat_rule(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        if self.reminder.repeat is None:
            await interaction.response.send_message(
                _("No existing repeat rule(s)."), ephemeral=True
            )
            return
        await interaction.response.send_modal(RemoveRepeatRuleModal(self))

    @discord.ui.button(
        label="Stop Repeat",
        emoji="🗑️",
        style=discord.ButtonStyle.danger,
        custom_id="stop_repeat",
    )
    async def stop_repeat(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        self.reminder.repeat = None
        if self._message is not None:
            try:
                embed = self._message.embeds[0]
                embed.description = _("No existing repeat rule(s).")
                self._message = await self._message.edit(embed=embed)
            except discord.HTTPException:
                pass
        await interaction.response.send_message(
            _("Reminder **#{reminder_id}** edited.").format(reminder_id=self.reminder.id)
        )

    @discord.ui.button(emoji="✖️", style=discord.ButtonStyle.danger, custom_id="cross_button")
    async def cross_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await CogsUtils.delete_message(self._message)
        self.stop()


class SnoozeView(discord.ui.View):
    def __init__(self, cog: commands.Cog, reminder) -> None:
        super().__init__(timeout=3600 * 12)
        self.cog: commands.Cog = cog

        self.reminder = reminder
        if self.reminder.repeat is None:
            self.remove_item(self.stop_repeat)
        if self.reminder.jump_url is not None:
            self.add_item(
                discord.ui.Button(
                    style=discord.ButtonStyle.url,
                    label=_("Jump to original message"),
                    url=self.reminder.jump_url,
                    row=1,
                )
            )

        self._message: discord.Message = None
        self._ready: asyncio.Event = asyncio.Event()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id not in [self.reminder.user_id] + list(self.cog.bot.owner_ids):
            await interaction.response.send_message(
                "You are not allowed to use this interaction.", ephemeral=True
            )
            return False
        return True

    async def on_timeout(self) -> None:
        to_remove = []
        for child in self.children:
            child: discord.ui.Item
            if hasattr(child, "disabled") and not (
                isinstance(child, discord.ui.Button) and child.style == discord.ButtonStyle.url
            ):
                to_remove.append(child)
        for child in to_remove:
            self.remove_item(child)
        try:
            await self._message.edit(view=self)
        except discord.HTTPException:
            pass
        self._ready.set()

    async def create_snooze_reminder(
        self, interaction: discord.Interaction, timedelta: dateutil.relativedelta.relativedelta
    ) -> typing.Any:
        reminder_id = 1
        while reminder_id in self.cog.cache.get(self.reminder.user_id, {}):
            reminder_id += 1
        utc_now = datetime.datetime.now(tz=datetime.timezone.utc)
        expires_at = utc_now + timedelta
        reminder = self.cog.Reminder(
            cog=self.cog,
            user_id=self.reminder.user_id,
            id=reminder_id,
            jump_url=self._message.jump_url,
            snooze=True,
            me_too=self.reminder.me_too,
            content=self.reminder.content,
            destination=self.reminder.destination,
            targets=self.reminder.targets,
            created_at=utc_now,
            expires_at=expires_at,
            last_expires_at=None,
            next_expires_at=expires_at,
            repeat=None,
        )
        await reminder.save()
        await interaction.response.send_message(
            reminder.__str__(utc_now=utc_now),
            ephemeral=True,
        )
        await self.on_timeout()
        self.stop()

    @discord.ui.button(
        label="Completed",
        emoji="✅",
        style=discord.ButtonStyle.success,
        custom_id="mark_as_completed",
    )
    async def mark_as_completed(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await interaction.response.defer()
        await self.on_timeout()
        self.stop()

    @discord.ui.button(
        label="In 20 Minutes",
        emoji="⏱️",
        style=discord.ButtonStyle.secondary,
        custom_id="in_20_minutes",
    )
    async def in_20_minutes(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await self.create_snooze_reminder(
            interaction=interaction, timedelta=dateutil.relativedelta.relativedelta(minutes=20)
        )

    @discord.ui.button(
        label="In 1 Hour", emoji="⏱️", style=discord.ButtonStyle.secondary, custom_id="in_1_hour"
    )
    async def in_1_hour(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.create_snooze_reminder(
            interaction=interaction, timedelta=dateutil.relativedelta.relativedelta(hours=1)
        )

    @discord.ui.button(
        label="In 3 Hours", emoji="⏱️", style=discord.ButtonStyle.secondary, custom_id="in_3_hours"
    )
    async def in_3_hours(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await self.create_snooze_reminder(
            interaction=interaction, timedelta=dateutil.relativedelta.relativedelta(hours=3)
        )

    @discord.ui.button(
        label="Tomorrow at 9am",
        emoji="⏱️",
        style=discord.ButtonStyle.secondary,
        custom_id="tomorrow",
        row=1,
    )
    async def tomorrow(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        timezone = (await self.cog.config.user_from_id(self.reminder.user_id).timezone()) or "UTC"
        tz = pytz.timezone(timezone)
        now = datetime.datetime.now(tz=tz)
        tomorrow = (now + dateutil.relativedelta.relativedelta(days=1)).replace(
            hour=9, minute=0, second=0, microsecond=0
        )
        delta = tomorrow - now
        await self.create_snooze_reminder(interaction=interaction, timedelta=delta)

    @discord.ui.button(
        label="Monday at 9am",
        emoji="⏱️",
        style=discord.ButtonStyle.secondary,
        custom_id="monday",
        row=1,
    )
    async def monday(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        timezone = (await self.cog.config.user_from_id(self.reminder.user_id).timezone()) or "UTC"
        tz = pytz.timezone(timezone)
        now = datetime.datetime.now(tz=tz)
        next_monday = now + dateutil.relativedelta.relativedelta(days=(7 - now.weekday()))
        next_monday_9am = datetime.datetime(
            next_monday.year, next_monday.month, next_monday.day, 9, 0, 0, tzinfo=tz
        )
        delta = next_monday_9am - now
        await self.create_snooze_reminder(interaction=interaction, timedelta=delta)

    @discord.ui.button(
        label="Stop Repeat",
        emoji="🗑️",
        style=discord.ButtonStyle.danger,
        custom_id="stop_repeat",
        row=1,
    )
    async def stop_repeat(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        self.reminder.next_expires_at = None
        await self.reminder.delete()
        await interaction.response.send_message(
            _("Reminder **#{reminder_id}** deleted.").format(reminder_id=self.reminder.id)
        )
        await self.on_timeout()
        self.stop()

    @discord.ui.button(
        emoji="✖️", style=discord.ButtonStyle.danger, custom_id="cross_button", row=1
    )
    async def cross_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await CogsUtils.delete_message(self._message)
        self.stop()

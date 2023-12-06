from AAA3A_utils import CogsUtils  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator  # isort:skip
import discord  # isort:skip
import typing  # isort:skip
import typing_extensions  # isort:skip

import asyncio
import datetime
import functools
import re
from dataclasses import dataclass
from io import BytesIO

import aiohttp
import dateutil
import dateutil.rrule
import pytz
from apscheduler.triggers.cron import CronTrigger
from cron_descriptor import CasingTypeEnum, ExpressionDescriptor
from recurrent.event_parser import RecurringEvent
from redbot.core.utils.chat_formatting import humanize_list

from .views import ReminderView, RepeatView, SnoozeView

_ = Translator("Reminders", __file__)

try:
    from typing import TypeAlias
except ImportError:
    from typing_extensions import TypeAlias
Content: TypeAlias = typing.Dict[
    str, typing.Union[str, typing.Dict[str, typing.Union[str, typing.Dict[str, str]]]]
]
Data: TypeAlias = typing.Dict[
    str, typing.Union[str, int, bool, Content, typing.Dict[str, typing.Union[int, str]]]
]


CT = typing.TypeVar(
    "CT", bound=typing.Callable[..., typing.Any]
)  # defined CT as a type variable that is bound to a callable that can take any argument and return any value.


async def run_blocking_func(
    func: typing.Callable[..., typing.Any], *args: typing.Any, **kwargs: typing.Any
) -> typing.Any:
    partial = functools.partial(func, *args, **kwargs)
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, partial)


def executor(executor: typing.Any = None) -> typing.Callable[[CT], CT]:
    def decorator(func: CT) -> CT:
        @functools.wraps(func)
        def wrapper(*args: typing.Any, **kwargs: typing.Any):
            return run_blocking_func(func, *args, **kwargs)

        return wrapper

    return decorator


@dataclass(frozen=False)
class RepeatRule:
    type: str
    value: typing.Optional[typing.Dict[str, int]]

    start_trigger: typing.Optional[datetime.datetime]
    first_trigger: typing.Optional[datetime.datetime]
    last_trigger: typing.Optional[datetime.datetime]

    def to_json(self) -> typing.Dict[str, typing.Union[str, typing.Dict[str, int]]]:
        return {
            "type": self.type,
            "value": int(self.value.timestamp()) if self.type == "date" else self.value,
            "start_trigger": int(self.start_trigger.timestamp())
            if self.start_trigger is not None
            else None,
            "first_trigger": int(self.first_trigger.timestamp())
            if self.first_trigger is not None
            else None,
            "last_trigger": int(self.last_trigger.timestamp())
            if self.last_trigger is not None
            else None,
        }

    @classmethod
    def from_json(
        cls, data: typing.Dict[str, typing.Union[str, typing.Dict[str, int]]]
    ) -> typing_extensions.Self:
        if data["type"] == "date":
            return cls(
                type=data["type"],
                value=datetime.datetime.fromtimestamp(
                    int(data["value"]), tz=datetime.timezone.utc
                ),
                start_trigger=datetime.datetime.fromtimestamp(
                    data["start_trigger"], tz=datetime.timezone.utc
                )
                if data.get("start_trigger") is not None
                else None,
                first_trigger=datetime.datetime.fromtimestamp(
                    data["first_trigger"], tz=datetime.timezone.utc
                )
                if data.get("first_trigger") is not None
                else None,
                last_trigger=datetime.datetime.fromtimestamp(
                    data["last_trigger"], tz=datetime.timezone.utc
                )
                if data.get("last_trigger") is not None
                else None,
            )
        return cls(
            type=data["type"],
            value=data["value"],
            start_trigger=datetime.datetime.fromtimestamp(
                data["start_trigger"], tz=datetime.timezone.utc
            )
            if data.get("start_trigger") is not None
            else None,
            first_trigger=datetime.datetime.fromtimestamp(
                data["first_trigger"], tz=datetime.timezone.utc
            )
            if data.get("first_trigger") is not None
            else None,
            last_trigger=datetime.datetime.fromtimestamp(
                data["last_trigger"], tz=datetime.timezone.utc
            )
            if data.get("last_trigger") is not None
            else None,
        )

    @executor()
    def next_trigger(
        self,
        last_expires_at: datetime.datetime = datetime.datetime.now(tz=datetime.timezone.utc),
        utc_now: datetime.datetime = datetime.datetime.now(tz=datetime.timezone.utc),
        timezone: str = "UTC",
    ) -> typing.Optional[datetime.datetime]:
        self.last_trigger = self.last_trigger or last_expires_at
        if self.last_trigger > last_expires_at and self.last_trigger >= utc_now:
            return self.last_trigger
        if utc_now is None:
            utc_now = datetime.datetime.now(tz=datetime.timezone.utc)
        if self.type == "sample":
            repeat_delta = dateutil.relativedelta.relativedelta(**self.value)
            next_expires_at = last_expires_at + repeat_delta
            while next_expires_at < utc_now:
                next_expires_at += repeat_delta
        elif self.type == "cron":
            tz = pytz.timezone(timezone)
            cron_trigger = CronTrigger.from_crontab(self.value, timezone=tz)
            next_expires_at = last_expires_at
            if next_expires_at is None:
                return None
            while next_expires_at == last_expires_at or next_expires_at < utc_now:
                next_expires_at = cron_trigger.get_next_fire_time(
                    previous_fire_time=last_expires_at, now=utc_now.astimezone(tz=tz)
                )
                if next_expires_at is None:
                    return None
                next_expires_at = next_expires_at.astimezone(tz=datetime.timezone.utc)
        elif self.type == "rrule":
            tz = pytz.timezone(timezone)
            rrule = dateutil.rrule.rrulestr(
                self.value, dtstart=self.start_trigger.replace(tzinfo=None)
            )
            # next_expires_at = last_expires_at
            # while next_expires_at == last_expires_at or next_expires_at < utc_now:
            #     next_expires_at = rrule.after(next_expires_at.replace(tzinfo=None), inc=False)
            #     if next_expires_at is None:
            #         return None
            #     next_expires_at = next_expires_at.astimezone(tz=datetime.timezone.utc)  # `astimezone` is not required
            next_expires_at = rrule.after(
                utc_now.astimezone(tz=tz).replace(tzinfo=None), inc=False
            )
            if next_expires_at is None:
                return None
            next_expires_at = next_expires_at.astimezone(
                tz=datetime.timezone.utc
            )  # `astimezone` is not required
        elif self.type == "date":
            return self.value
        else:
            return None
        if self.first_trigger is None:
            self.first_trigger = next_expires_at
        self.last_trigger = next_expires_at
        return next_expires_at

    def get_info(self) -> str:
        if self.type == "sample":
            value = self.value.copy()
            if "years" in value:
                if "days" not in value:
                    value["days"] = 0
                value["days"] += value.pop("years") * 365
            if "months" in value:
                if "days" not in value:
                    value["days"] = 0
                value["days"] += value.pop("months") * 7 * 4
            return f"[{self.type.upper()}] Every {CogsUtils.get_interval_string(datetime.timedelta(**value))}."
        elif self.type == "cron":
            descriptor = ExpressionDescriptor(
                expression=self.value,
                verbose=True,
                casing_type=CasingTypeEnum.Sentence,
                locale_code="en_US",
                use_24hour_time_format=True,
            )
            return f"[{self.type.upper()}] {descriptor.get_full_description()}."
        elif self.type == "rrule":
            r = RecurringEvent(preferred_time_range=(0, 12))
            value = self.value
            if (count_match := re.search(r"COUNT=(\d+)", value)) is not None:
                value = value.replace(
                    f"COUNT={count_match[1]}", f"COUNT={int(count_match[1]) - 1}"
                )
            return f"[{self.type.upper()}] {r.format(value).title()}."
        elif self.type == "date":
            return f"[{self.type.upper()}] <t:{int(self.value.timestamp())}:F> (<t:{int(self.value.timestamp())}:R>)."
        else:
            return None


@dataclass(frozen=False)
class Repeat:
    rules: typing.List[RepeatRule]

    def to_json(self) -> typing.List[typing.Dict[str, typing.Union[str, typing.Dict[str, int]]]]:
        return [rule.to_json() for rule in self.rules]

    @classmethod
    def from_json(
        cls, data: typing.List[typing.Dict[str, typing.Union[str, typing.Dict[str, int]]]]
    ) -> typing_extensions.Self:
        return cls(rules=[RepeatRule.from_json(rule) for rule in data])

    async def next_trigger(
        self,
        last_expires_at: datetime.datetime = datetime.datetime.now(tz=datetime.timezone.utc),
        utc_now: datetime.datetime = None,
        timezone: str = "UTC",
    ) -> typing.Optional[datetime.datetime]:
        if utc_now is None:
            utc_now = datetime.datetime.now(tz=datetime.timezone.utc)
        next_triggers = [
            await rule.next_trigger(
                last_expires_at=last_expires_at, utc_now=utc_now, timezone=timezone
            )
            for rule in self.rules
        ]
        next_triggers = [
            next_trigger for next_trigger in next_triggers if next_trigger is not None
        ]
        return min(next_triggers, default=None)

    def get_info(self) -> str:
        return "\n".join(
            [f"**•** **{i}.** - {rule.get_info()}" for i, rule in enumerate(self.rules, start=1)]
        )


@dataclass(frozen=False)
class Reminder:
    cog: commands.Cog
    user_id: int

    id: int
    jump_url: typing.Optional[str]
    snooze: bool
    me_too: bool

    content: Content  # {"type": ..., "title": None, "text": None, "embed": ..., "message_author": {"display_name": ..., "display_avatar": ..., "mention": ...}, "image_url": ..., "command": ..., "invoker": ...}
    destination: typing.Optional[int]  # channel or dm
    targets: typing.Optional[typing.List[typing.Dict[str, typing.Union[int, str]]]]

    created_at: datetime.datetime
    expires_at: datetime.datetime
    last_expires_at: typing.Optional[datetime.datetime]
    next_expires_at: datetime.datetime
    repeat: typing.Optional[Repeat]

    def __hash__(self) -> str:
        return hash(
            (
                self.user_id,
                self.id,
                self.jump_url,
                # self.content,
                self.snooze,
                self.me_too,
                self.created_at,
                self.expires_at,
                # self.next_expires_at,
            )
        )

    def __eq__(self, other: "Reminder") -> bool:
        return (self.next_expires_at or datetime.datetime.now(tz=datetime.timezone.utc)) == (
            other.next_expires_at or datetime.datetime.now(tz=datetime.timezone.utc)
        )

    def __lt__(self, other: "Reminder") -> bool:
        return (self.next_expires_at or datetime.datetime.now(tz=datetime.timezone.utc)) < (
            other.next_expires_at or datetime.datetime.now(tz=datetime.timezone.utc)
        )

    def __le__(self, other: "Reminder") -> bool:
        return (self.next_expires_at or datetime.datetime.now(tz=datetime.timezone.utc)) <= (
            other.next_expires_at or datetime.datetime.now(tz=datetime.timezone.utc)
        )

    def __gt__(self, other: "Reminder") -> bool:
        return (self.next_expires_at or datetime.datetime.now(tz=datetime.timezone.utc)) > (
            other.next_expires_at or datetime.datetime.now(tz=datetime.timezone.utc)
        )

    def __ge__(self, other: "Reminder") -> bool:
        return (self.next_expires_at or datetime.datetime.now(tz=datetime.timezone.utc)) >= (
            other.next_expires_at or datetime.datetime.now(tz=datetime.timezone.utc)
        )

    def to_json(self, clean: bool = True) -> Data:
        data = {
            "id": self.id,
            "jump_url": self.jump_url,
            "snooze": self.snooze,
            "me_too": self.me_too,
            "content": self.content,
            "destination": self.destination,
            "targets": self.targets,
            "created_at": int(self.created_at.timestamp()),
            "expires_at": int(self.expires_at.timestamp()),
            "last_expires_at": int(self.next_expires_at.timestamp()),
            "next_expires_at": int(self.next_expires_at.timestamp()),
            "repeat": self.repeat.to_json() if self.repeat is not None else self.repeat,
        }
        if clean:
            for attr in [
                "jump_url",
                "snooze",
                "me_too",
                "destination",
                "targets",
                "repeat",
                "last_expires_at",
            ]:
                if not getattr(self, attr):
                    del data[attr]
        return data

    @classmethod
    def from_json(cls, cog: commands.Cog, user_id: int, data: Data) -> typing_extensions.Self:
        return cls(
            cog=cog,
            user_id=user_id,
            id=data["id"],
            jump_url=data.get("jump_url"),
            snooze=data.get("snooze", False),
            me_too=data.get("me_too", False),
            content=data["content"],
            destination=data.get("destination"),
            targets=data.get(
                "targets", [data.get("target")] if data.get("target") is not None else None
            ),
            created_at=datetime.datetime.fromtimestamp(
                int(data["created_at"]), tz=datetime.timezone.utc
            ),
            expires_at=datetime.datetime.fromtimestamp(
                int(data["expires_at"]), tz=datetime.timezone.utc
            ),
            last_expires_at=datetime.datetime.fromtimestamp(
                int(data["last_expires_at"]), tz=datetime.timezone.utc
            )
            if data.get("last_expires_at") is not None
            else None,
            next_expires_at=datetime.datetime.fromtimestamp(
                int(data["next_expires_at"]), tz=datetime.timezone.utc
            ),
            repeat=Repeat.from_json((data.get("repeat") or data.get("intervals")))
            if (data.get("repeat") or data.get("intervals")) is not None
            else None,
        )

    def __str__(self, utc_now: datetime.datetime = None) -> str:
        if utc_now is None:
            utc_now = datetime.datetime.now(tz=datetime.timezone.utc)
        and_every = ""
        if self.repeat is not None:
            if len(self.repeat.rules) == 1:
                and_every = _(", and then **{interval}**").format(
                    interval=self.repeat.rules[0].get_info().lower().split("]")[-1].rstrip(".")[1:]
                )
            else:
                and_every = _(", with **{nb_repeat_rules} repeat rules**").format(
                    nb_repeat_rules=len(self.repeat.rules)
                )
        interval_string = CogsUtils.get_interval_string(
            int(self.expires_at.timestamp() - utc_now.timestamp())
        )
        if interval_string != "just now":
            interval_string = f"in {interval_string}"
        return (
            _(
                "{state}Okay, I will dispatch {this} **{interval_string}** ({timestamp}){and_every}. [Reminder **#{reminder_id}**]"
            )
            if self.content["type"] == "event" else
            (
                _(
                    "{state}Okay, I will execute this command{destination_mention} **{interval_string}** ({timestamp}){and_every}. [Reminder **#{reminder_id}**]"
                )
                if self.content["type"] == "command"
                else (
                    _(
                        "{state}Okay, I will say {this}{destination_mention} **{interval_string}** ({timestamp}){and_every}. [Reminder **#{reminder_id}**]"
                    )
                    if self.content["type"] == "say"
                    else _(
                        "{state}Okay, I will remind {targets_mentions} of {this}{destination_mention} **{interval_string}** ({timestamp}){and_every}. [Reminder **#{reminder_id}**]"
                    )
                )
            )
        ).format(
            state=f"{'[Snooze] ' if self.snooze else ''}{'[Me Too] ' if self.me_too else ''}",
            targets_mentions=humanize_list([target["mention"] for target in self.targets])
            if self.targets is not None
            else _("you"),
            this=(
                _("the event `{event_name}`").format(event_name=self.content["event_name"])
                if self.content["type"] == "event" else
                (
                    _("this command")
                    if self.content["type"] == "command" else
                    (
                        (
                            _("this message")
                            if self.content["type"] == "message"
                            else _(
                                "this"
                            )  # (_("this command") if self.content["type"] == "command" else _("this"))
                        )
                        if self.content["text"] is not None else
                        _("that")
                    )
                )
            ),
            destination_mention=(
                (
                    _(" in {destination_mention}").format(
                        destination_mention=(
                            f"{destination.recipient}'s DMs"
                            if isinstance(destination, discord.DMChannel)
                            else destination.mention
                        )
                    )
                    if (destination := self.cog.bot.get_channel(self.destination)) is not None
                    else _(" in {destination} (Not found.)").format(destination=self.destination)
                )
                if self.destination is not None
                else ""
            ),
            interval_string=interval_string,
            timestamp=f"<t:{int(self.expires_at.timestamp())}:F>",
            and_every=and_every,
            reminder_id=self.id,
        )

    def get_info(self) -> str:
        return _(
            "• **Next Expires at**: {expires_at_timestamp} ({expires_in_timestamp})\n"
            "• **Created at**: {created_at_timestamp} ({created_in_timestamp})\n"
            "• **Repeat**: {repeat}\n"
            "• **Title**: {title}\n"
            "• **Content type**: `{content_type}`\n"
            "• **Content**: {content}\n"
            "• **Targets**: {targets}\n"
            "• **Destination**: {destination}\n"
            "• **Jump URL**: {jump_url}\n"
        ).format(
            expires_at_timestamp=f"<t:{int(self.next_expires_at.timestamp())}:F>",
            expires_in_timestamp=CogsUtils.get_interval_string(
                self.next_expires_at, use_timestamp=True
            ),
            created_at_timestamp=f"<t:{int(self.created_at.timestamp())}:F>",
            created_in_timestamp=CogsUtils.get_interval_string(
                self.created_at, use_timestamp=True
            ),
            repeat=_("No existing repeat rule(s).")
            if self.repeat is None
            else (
                _("{nb_repeat_rules} repeat rules.").format(nb_repeat_rules=len(self.repeat.rules))
                if len(self.repeat.rules) > 1
                else self.repeat.rules[0].get_info()
            ),
            title=self.content.get("title") or _("Not provided."),
            content_type=self.content["type"],
            content=(
                f"Dispatch the event `{self.content['event_name']}`."
                if self.content["type"] == "event" else
                (
                    (
                        (
                            f"{self.content['text'][:200]}..."
                            if len(self.content["text"]) > 200
                            else self.content["text"]
                        )
                        if self.content["text"] is not None
                        else _("No content.")
                    )
                    if self.content["type"] in ["text", "say"]
                    else (
                        f"Message {self.content['message_jump_url']}."
                        if self.content["type"] == "message"
                        else f"Command `[p]{self.content['command']}` executed with your privilege rights."
                    )
                )
            ),
            targets=humanize_list(
                [f"{target['mention']} ({target['id']})" for target in self.targets]
            )
            if self.targets is not None
            else _("No target(s)."),
            destination=_("In DMs")
            if self.destination is None
            else (
                f"{destination.recipient}'s DMs ({destination.id})"
                if isinstance(destination, discord.DMChannel)
                else f"{destination.mention} ({destination.id})"
            )
            if (destination := self.cog.bot.get_channel(self.destination)) is not None
            else f"{self.destination} (Not found.)",
            jump_url=self.jump_url,
        )

    async def save(self) -> None:
        if self.user_id not in self.cog.cache:
            self.cog.cache[self.user_id] = {}
        self.cog.cache[self.user_id][self.id] = self
        data = self.to_json()
        await self.cog.config.user_from_id(self.user_id).set_raw("reminders", self.id, value=data)
        return self

    async def delete(self) -> None:
        for view in self.cog.views.values():
            if (
                isinstance(view, (ReminderView, RepeatView))
                and view.reminder == self
                and not view.is_finished()
            ):
                await view.on_timeout()
                view.stop()
        self.next_expires_at = None
        try:
            del self.cog.cache[self.user_id][self.id]
        except KeyError:
            pass
        await self.cog.config.user_from_id(self.user_id).clear_raw("reminders", self.id)

    def to_embed(
        self,
        utc_now: datetime.datetime = None,
        embed_color: discord.Color = discord.Color.green(),
    ) -> discord.Embed:
        if utc_now is None:
            utc_now = datetime.datetime.now(tz=datetime.timezone.utc)
        delayed = int(
            utc_now.timestamp() - (self.last_expires_at or self.next_expires_at).timestamp()
        )
        if delayed <= 60:
            delayed = 0
        embed: discord.Embed = discord.Embed(
            title=f"🔔 {'(Delayed) ' if delayed else ''}{'[Snoozed] ' if self.snooze else ''}{'[Me Too] ' if self.me_too else ''}{'Repeating ' if self.next_expires_at is not None else ''}Reminder #{self.id}! 🔔",
            url=self.jump_url,
            color=embed_color,
        )
        if (
            self.destination is not None
            and (
                self.targets is None
                or len(self.targets) != 1
                or self.targets[0]["id"] != self.user_id
            )
            and (user := self.cog.bot.get_user(self.user_id))
        ):
            embed.set_author(name=user.display_name, icon_url=user.display_avatar)
        embed.add_field(
            name="\u200B",
            value=(
                f"[Jump to the original message.]({self.jump_url}) • "
                if self.jump_url is not None
                else ""
            )
            + f"Created the <t:{int(self.created_at.timestamp())}:F>.",
            inline=False,
        )
        interval_string = CogsUtils.get_interval_string(
            int(
                (self.last_expires_at or self.next_expires_at).timestamp()
                - self.created_at.timestamp()
            )
        )
        if interval_string != "just now":
            interval_string += " ago"
        if self.content["type"] == "text":
            embed.description = _(
                "You asked me to remind you about {this}, {interval_string}.\n\n"
            ).format(
                this="this" if self.content["text"] else "that", interval_string=interval_string
            )
        else:  # message
            embed.description = _(
                "You asked me to remind you about [this message]({message_jump_url}) from {author_mention} ({author_id}), {interval_string}.\n\n"
            ).format(
                message_jump_url=self.content["message_jump_url"],
                author_mention=self.content["message_author"]["mention"],
                author_id=self.content["message_author"]["id"],
                interval_string=interval_string,
            )
        if self.content.get("title") is not None:
            embed.description += f"# **{self.content['title']}**\n\n"
        if self.content["text"]:
            embed.description += f">>> {self.content['text']}"
        if self.content.get("image_url") is not None:
            embed.set_image(url=self.content["image_url"])
        footer = ""
        if delayed:
            footer += _(
                "This was supposed to send {interval_string} ago. I might be having network or server issues, or perhaps I just started up. Sorry about that!\n\n"
            ).format(interval_string=CogsUtils.get_interval_string(delayed))
        if self.next_expires_at is not None:
            footer += _("Next trigger in {interval_string}.").format(
                interval_string=CogsUtils.get_interval_string(self.next_expires_at)
            )
        embed.set_footer(text=footer or None)
        return embed

    async def process(
        self,
        utc_now: datetime.datetime = None,
        testing: bool = False,
    ) -> None:
        if utc_now is None:
            utc_now = datetime.datetime.now(tz=datetime.timezone.utc)
        if not testing:
            self.last_expires_at = self.next_expires_at
            timezone = (await self.cog.config.user_from_id(self.user_id).timezone()) or "UTC"
            if self.repeat is not None:
                self.next_expires_at = await self.repeat.next_trigger(
                    last_expires_at=self.last_expires_at, utc_now=utc_now, timezone=timezone
                )
                await self.save()
            else:
                self.next_expires_at = None
        try:
            user: discord.User = await self.cog.bot.fetch_user(self.user_id)
            if not user.mutual_guilds:
                raise ValueError(user)
        except (discord.NotFound, ValueError):
            if not testing:
                await self.delete()
            raise RuntimeError(
                f"User {self.user_id} not found for the reminder {self.user_id}#{self.id}@{self.content['type']}. The reminder has been deleted."
            )
        if self.destination is None:
            destination: discord.abc.Messageable = await user.create_dm()
        elif (destination := self.cog.bot.get_channel(self.destination)) is None:
            if not testing:
                await self.delete()
            raise RuntimeError(
                f"Destination {self.destination} not found for the reminder {self.user_id}#{self.id}@{self.content['type']}. The reminder has been deleted."
            )
        else:
            if destination.guild is not None and destination.guild.get_member(user.id) is None:
                raise RuntimeError(
                    f"Member {self.user_id} not found in the guild {destination.guild.id} for the reminder {self.user_id}#{self.id}@{self.content['type']}. The reminder has been deleted."
                )
        if not self.content or "type" not in self.content:
            await self.delete()
            raise RuntimeError(
                f"No content in the reminder {self.user_id}#{self.id}@{self.content['type']}. The reminder has been deleted."
            )

        if self.content["type"] == "event":
            if "event_name" not in self.content:
                await self.delete()
                raise RuntimeError(
                    f"No key `event_name` in the reminder {self.user_id}#{self.id}@{self.content['type']}. The reminder has been deleted."
                )
            self.cog.bot.dispatch(self.content["event_name"], self, *self.content.get("args", []), **self.content.get("kwargs", []))

        elif self.content["type"] == "command":
            if (invoker := self.cog.bot.get_user(self.content["command_invoker"])) is None or (getattr(destination, "guild", None) is not None and (invoker := destination.guild.get_member(invoker.id)) is None):
                if not testing:
                    await self.delete()
                raise RuntimeError(
                    f"Command invoker not found for the reminder {self.user_id}#{self.id}@{self.content['type']}. The reminder has been deleted."
                )
            context: commands.Context = await CogsUtils.invoke_command(
                bot=self.cog.bot,
                author=invoker,
                channel=destination,
                command=self.content["command"],
                assume_yes=True,
            )
            # for cog_name in ("CustomCommands", "Alias"):
            #     if (cog := self.cog.bot.get_cog(cog_name)) is not None:
            #         for handler_name in ("on_message", "on_message_without_command"):
            #             if (msg_handler := getattr(cog, handler_name, None)) is not None:
            #                 await msg_handler(context.message)
            #                 break
            if not context.valid:  # Don't delete the reminder (cog unloaded for example).
                raise RuntimeError(
                    f"Command not found for the reminder {self.user_id}#{self.id}@{self.content['type']}. The reminder has not been deleted."
                )
            elif not await discord.utils.async_all(
                [check(context) for check in context.command.checks]
            ):  # To prevent an user with important permissions a time to execute dangerous command with a reminder.
                if not testing:
                    await self.delete()
                raise RuntimeError(
                    f"The invoker can't execute the command for the reminder {self.user_id}#{self.id}@{self.content['type']}. The reminder has been deleted."
                )

        else:
            if self.content["type"] in ["text", "message"]:
                embeds = [self.to_embed(utc_now=utc_now, embed_color=self.cog.bot._color)]
            else:
                embeds = []
            if self.content.get("embed") is not None:
                e = discord.Embed.from_dict(self.content["embed"])
                e.set_author(
                    name=self.content["message_author"]["display_name"],
                    icon_url=self.content["message_author"]["display_avatar"],
                )
                e.color = None
                embeds.append(e)
            files = []
            if self.content.get("files"):
                for file_name, file_url in self.content["files"].items():
                    async with aiohttp.ClientSession() as session:
                        async with session.get(file_url) as r:
                            file_content = await r.read()
                    files.append(discord.File(BytesIO(file_content), filename=file_name))
            try:
                if destination.guild is None:
                    member = user
                elif (member := destination.guild.get_member(user.id)) is None:
                    raise RuntimeError(
                        f"Member {self.user_id} not found in the guild {destination.guild.id} for the reminder {self.user_id}#{self.id}@{self.content['type']}. The reminder has been deleted."
                    )
                reference = None
                if self.content["type"] in ["text", "message"]:
                    if self.content["type"] == "message" and destination.id == int(
                        self.content["message_jump_url"].split("/")[-2]
                    ):
                        if (
                            message := destination.get_partial_message(
                                int(self.content["message_jump_url"].split("/")[-1])
                            )
                        ) is not None:
                            reference = message
                    elif destination.id == int(self.jump_url.split("/")[-2]):
                        if (
                            message := destination.get_partial_message(
                                int(self.jump_url.split("/")[-1])
                            )
                        ) is not None:
                            reference = message
                    snooze_view_enabled = await self.cog.config.snooze_view()
                    if snooze_view_enabled:
                        view = SnoozeView(cog=self.cog, reminder=self)
                    else:
                        view = discord.ui.View()
                        view.add_item(
                            discord.ui.Button(label=_("Jump to original message"), style=discord.ButtonStyle.url, url=self.jump_url)
                        )
                    message = await destination.send(
                        embeds=embeds,
                        files=files,
                        content=humanize_list([target["mention"] for target in self.targets])
                        if self.targets is not None
                        else None,
                        allowed_mentions=discord.AllowedMentions(
                            everyone=destination.permissions_for(member).mention_everyone,
                            users=True,
                            roles=destination.permissions_for(member).mention_everyone,
                            replied_user=False,
                        ),
                        view=view,
                        reference=reference,
                    )
                    if snooze_view_enabled:
                        view._message = message
                        self.cog.views[message] = view
                else:  # type `say`
                    message = await destination.send(
                        content=self.content["text"],
                        embeds=embeds,
                        files=files,
                        allowed_mentions=discord.AllowedMentions(
                            everyone=destination.permissions_for(member).mention_everyone,
                            users=True,
                            roles=destination.permissions_for(member).mention_everyone,
                            replied_user=False,
                        ),
                    )
            except discord.HTTPException:
                if not testing:
                    await self.delete()
                raise RuntimeError(
                    f"The message was not sent correctly for the reminder {self.user_id}#{self.id}@{self.content['type']}. The reminder has been deleted."
                )
            total_sent = await self.cog.config.total_sent()
            total_sent += 1
            await self.cog.config.total_sent.set(total_sent)
            if self.next_expires_at is None and not testing:
                await self.delete()
            return (context if self.content["type"] == "command" else message) if self.content["type"] != "event" else None

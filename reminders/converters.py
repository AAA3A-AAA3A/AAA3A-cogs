from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import asyncio
import datetime
import functools
import re

import dateparser
import dateutil
import dateutil.rrule
import pytz
from apscheduler.triggers.cron import CronTrigger
from pyparsing import (
    CaselessLiteral,
    Combine,
    FollowedBy,
    Group,
    Keyword,
    Literal,
    Optional,
    ParseException,
    ParserElement,
    Regex,
    SkipTo,
    StringEnd,
    Suppress,
    Word,
    WordEnd,
    ZeroOrMore,
    nums,
    oneOf,
    tokenMap,
)  # NOQA
from recurrent.event_parser import RecurringEvent

_ = Translator("Reminders", __file__)


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


class TimezoneConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> str:
        # timezones_dict = {
        #     "GMT": ("UTC", "Greenwich Mean Time"),
        #     "CEST": ("UTC +1", "Central European Summer Time"),
        #     "EET": ("UTC +2", "Eastern European Time"),
        #     "EAT": ("UTC +3", "Eastern African Time"),
        #     "NET": ("UTC +4", "Near East Time"),
        #     "PLT": ("UTC +5", "Pakistan Lahore Time"),
        #     "BST": ("UTC +6", "Bangladesh Standard Time"),
        #     "VST": ("UTC +7", "Vietnam Standard Time"),
        #     "CTT": ("UTC +8", "China Taiwan Time"),
        #     "JST": ("UTC +9", "Japan Standard Time"),
        #     "AET": ("UTC +10", "Australia Eastern Time"),
        #     "SBT": ("UTC +11", "Solomon Islands Time"),
        #     "NST": ("UTC +12", "New Zealand Standard Time"),
        #     "MIT": ("UTC -11", "Midway Islands Time"),
        #     "HST": ("UTC -10", "Hawaii Standard Time"),
        #     "AST": ("UTC -9", "Alaska Standard Time"),
        #     "PST": ("UTC -8", "Pacific Standard Time"),
        #     "MST": ("UTC -7", "Mountain Standard Time"),
        #     "CST": ("UTC -6", "Central Standard Time"),
        #     "EST": ("UTC -5", "Eastern Standard Time"),
        #     "ALT": ("UTC -4", "Amazon Time"),
        #     "WGST": ("UTC -3", "West Greenland Time"),
        #     "GST": ("UTC -2", "South Georgia Time"),
        #     "AZOT": ("UTC -1", "Azores Standard Time")
        # }
        # if argument in timezones_dict:
        #     return argument
        # options = [discord.SelectOption(label=f"{key} ({value[0]})", value=key, description=value[1]) for key, value in timezones_dict.items()]
        # select_menu = discord.ui.Select(custom_id="timezones_select", placeholder="Select your timezone", min_values=1, max_values=1, options=options)
        # view = discord.ui.View()
        # async def callback(interaction: discord.Interaction):
        #     await interaction.response.defer()
        #     view.stop()
        # select_menu.callback = callback
        # view.add_item(select_menu)
        # message = await ctx.send(_("To create your first reminder, we need to know your timezone. Please choose from the options below."), view=view)
        # timeout = await view.wait()
        # select_menu.disabled = True
        # await message.edit(view=view)
        # if timeout:
        #     raise commands.BadArgument("Timeout.")
        # return select_menu.values[0]
        if argument not in pytz.common_timezones:
            raise commands.BadArgument(_("Invalid timezone provided."))
        return argument


class TimeConverter(commands.Converter):
    async def convert(
        self, ctx: commands.Context, argument: str, content: typing.Optional[str] = None
    ) -> typing.Union[
        typing.Tuple[datetime.datetime, datetime.datetime, typing.Optional[dict], str],
        typing.Tuple[datetime.datetime, datetime.datetime, typing.Optional[dict]],
    ]:
        cog = ctx.bot.get_cog("Reminders")
        utc_now = datetime.datetime.now(tz=datetime.timezone.utc).replace(second=0, microsecond=0)
        timezone = await cog.config.user(ctx.author).timezone()
        if timezone is None:
            if (timezone_cog := ctx.bot.get_cog("Timezone")) is not None:
                try:
                    timezone = await timezone_cog.config.user(ctx.author).usertime()
                except AttributeError:
                    pass
            if timezone is not None:
                await cog.config.user(ctx.author).timezone.set(timezone)
            else:
                timezone = "UTC"
        tz = pytz.timezone(timezone)
        local_now = utc_now.astimezone(tz=tz)

        @executor()
        def parse_iso_date(arg: str) -> datetime.datetime:
            try:
                dt: datetime.datetime = dateutil.parser.isoparse(arg)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=tz)
                dt = dt.astimezone(tz=datetime.timezone.utc)
                return dt
            except ValueError as e:
                raise ValueError(f"• Iso parsing: {' '.join(e.args)}.")

        @executor()
        def parse_cron_trigger(arg: str, text: typing.Optional[str] = None) -> datetime.datetime:
            if (
                ctx.interaction is None
                and text is not None
                and " " not in arg
                and not (
                    text.startswith(tuple(discord.ext.commands.view._all_quotes))
                    and text.endswith(tuple(discord.ext.commands.view._all_quotes))
                )
            ):
                to_parse = f"{arg} {' '.join(text.split(' ')[:4])}"
                text = " ".join(text.split(" ")[4:])
            else:
                to_parse = arg
            try:
                cron_trigger = CronTrigger.from_crontab(to_parse, timezone=tz)
            except ValueError as e:
                raise ValueError(
                    f"• Cron trigger parsing: {' '.join([f'{arg}.' for arg in e.args])}."
                )
            expires_at = cron_trigger.get_next_fire_time(previous_fire_time=None, now=local_now)
            expires_at = expires_at.astimezone(tz=datetime.timezone.utc)
            try:
                return (
                    expires_at,
                    cog.Repeat.from_json(
                        [
                            {
                                "type": "cron",
                                "value": to_parse,
                                "start_trigger": int(utc_now.timestamp()),
                                "first_trigger": None,
                                "last_trigger": None,
                            }
                        ]
                    ),
                    text,
                )
            except OSError as e:
                raise ValueError(f"• Cron trigger parsing: {e}.")

        @executor()
        def parse_timestamp(arg: str) -> datetime.datetime:
            try:
                timestamp = float(arg)
                expires_at = datetime.datetime.fromtimestamp(timestamp, tz=datetime.timezone.utc)
            except ValueError as e:
                raise ValueError(
                    f"• Timestamp parsing: {' '.join([f'{e_arg}.' for e_arg in e.args])}."
                )
            else:
                if expires_at < utc_now:
                    raise ValueError("• Timestamp parsing: The timestamp isn't in the future.")
                return expires_at

        @executor()
        def parse_relative_date(
            arg: str, text: typing.Optional[str] = None
        ) -> typing.Tuple[datetime.datetime, typing.Optional[str], str]:
            if (
                ctx.interaction is None
                and text is not None
                and " " not in arg
                and not (
                    text.startswith(tuple(discord.ext.commands.view._all_quotes))
                    and text.endswith(tuple(discord.ext.commands.view._all_quotes))
                )
            ):
                return_text = True
                to_parse = f"{arg} {text}"
            else:
                return_text = False
                to_parse = arg
            try:
                parse_result = DurationParser().parse(text=to_parse)
            except ParseException as e:
                raise ValueError(
                    f"• Relative date parsing: Impossible to parse this date. {str(e)[:100]}"
                )
            repeat = None
            repeat_dict = parse_result["every"] if "every" in parse_result else None
            if "in" in parse_result:
                expires_dict = parse_result["in"]
            elif "on" in parse_result or "at" in parse_result:
                try:
                    expires_at: datetime.datetime = dateutil.parser.parse(
                        (parse_result.get("on") if "on" in parse_result else "at").strip(),
                        fuzzy=True,
                        dayfirst=True,
                        yearfirst=False,
                        ignoretz=False,
                        default=local_now.replace(hour=9, minute=0, second=0, microsecond=0),
                    )
                    if expires_at.replace(
                        hour=0, minute=0, second=0, microsecond=0
                    ) == local_now.replace(hour=0, minute=0, second=0, microsecond=0) and (
                        expires_at.hour < local_now.hour or expires_at.minute < local_now.minute
                    ):
                        expires_at = expires_at.replace(day=expires_at.day + 1)
                except (dateutil.parser.ParserError, OverflowError):
                    expires_dict = None
                else:
                    expires_dict = expires_at
            else:
                expires_dict = repeat_dict
            if not expires_dict:
                raise ValueError("• Relative date parsing: Impossible to parse this date.")
            if not isinstance(expires_dict, datetime.datetime):  # no "on" kwarg
                expires_delta = dateutil.relativedelta.relativedelta(**expires_dict)
                try:
                    expires_at = local_now + expires_delta
                except OverflowError as e:
                    raise ValueError(f"• Relative date parsing: {e}.")
            reminder_text = parse_result["text"] or None if "text" in parse_result else None
            expires_at = expires_at.astimezone(tz=datetime.timezone.utc)
            if repeat_dict is not None:
                try:
                    repeat = cog.Repeat.from_json(
                        [
                            {
                                "type": "sample",
                                "value": repeat_dict,
                                "start_trigger": int(utc_now.timestamp()),
                                "first_trigger": None,
                                "last_trigger": None,
                            }
                        ]
                    )
                except OSError as e:
                    raise ValueError(f"• Relative date parsing: {e}.")
            return (
                expires_at,
                repeat,
                reminder_text.strip()
                if return_text and reminder_text
                else text,
            )

        @executor()
        def parse_recurrent(arg: str) -> typing.Tuple[datetime.datetime, typing.Any]:
            r = RecurringEvent(
                now_date=local_now.replace(hour=9, minute=0, second=0, microsecond=0),
                preferred_time_range=(0, 12),
            )
            rrule_string = r.parse(arg)
            if rrule_string is None:
                raise ValueError("• Recurrent parsing: Impossible to parse this RRULE.")
            elif isinstance(
                rrule_string, datetime.datetime
            ):  # `parse_fuzzy_date` is better for this.
                # return rrule_string.astimezone(tz=datetime.timezone.utc), None
                raise ValueError("• Recurrent parsing: Impossible to parse this RRULE.")
            rrule = dateutil.rrule.rrulestr(rrule_string)
            expires_at = rrule.after(local_now.replace(tzinfo=None), inc=True)
            if expires_at is None:
                raise ValueError("• Recurrent parsing: Impossible to parse this RRULE.")
            expires_at = expires_at.astimezone(tz=datetime.timezone.utc)
            # if expires_at <= utc_now.replace(minute=utc_now.minute + 1):
            #     expires_at += dateutil.relativedelta.relativedelta(minutes=2)
            try:
                return expires_at, cog.Repeat.from_json(
                    [
                        {
                            "type": "rrule",
                            "value": rrule_string,
                            "start_trigger": int(utc_now.timestamp()),
                            "first_trigger": None,
                            "last_trigger": None,
                        }
                    ]
                )
            except OSError as e:
                raise ValueError(f"• Recurrent parsing: {e}.")

        @executor()
        def parse_fuzzy_date(arg: str, text: typing.Optional[str] = None) -> datetime.datetime:
            if (
                ctx.interaction is None
                and text is not None
                and " " not in arg
                and not (
                    text.startswith(tuple(discord.ext.commands.view._all_quotes))
                    and text.endswith(tuple(discord.ext.commands.view._all_quotes))
                )
            ):
                return_text = True
                to_parse = f"{arg} {text}"
            else:
                return_text = False
                to_parse = arg
            parsed_date = None
            eod_re = re.compile(r"\b(end of day)|eod\b", re.IGNORECASE)
            eow_re = re.compile(r"\b(end of week)|eow\b", re.IGNORECASE)
            eom_re = re.compile(r"\b(end of month)|eom\b", re.IGNORECASE)
            eoy_re = re.compile(r"\b(end of year)|eoy\b", re.IGNORECASE)
            if match := eod_re.search(to_parse):
                if local_now.hour >= 17:
                    today_or_next_day = local_now.replace(day=local_now.day + 1)
                else:
                    today_or_next_day = local_now
                parsed_date = today_or_next_day.replace(
                    hour=0, minute=0, second=0, microsecond=0
                ) + dateutil.relativedelta.relativedelta(
                    hours=17
                )  # 17:00
                reminder_text = to_parse[: match.start()] + to_parse[match.end() :]
            elif match := eow_re.search(to_parse):
                if local_now.weekday() == 4 and local_now.hour >= 17:
                    days_ahead = 7
                else:
                    days_ahead = (4 - local_now.weekday()) % 7
                next_friday = local_now + dateutil.relativedelta.relativedelta(days=days_ahead)
                parsed_date = next_friday.replace(
                    hour=17, minute=0, second=0, microsecond=0
                )  # 17:00 on last day of week/next friday
                reminder_text = to_parse[: match.start()] + to_parse[match.end() :]
            elif match := eom_re.search(to_parse):
                parsed_date = local_now.replace(
                    day=1, hour=0, minute=0, second=0, microsecond=0
                ) + dateutil.relativedelta.relativedelta(
                    months=1, hours=-12
                )  # 12:00 on last day of month
                reminder_text = to_parse[: match.start()] + to_parse[match.end() :]
            elif match := eoy_re.search(to_parse):
                parsed_date = local_now.replace(
                    month=1, day=1, hour=0, minute=0, second=0, microsecond=0
                ) + dateutil.relativedelta.relativedelta(
                    years=1, hours=-15
                )  # 9:00 on last day of year
                reminder_text = to_parse[: match.start()] + to_parse[match.end() :]
            else:
                try:
                    parsed_date, text_tuple = dateutil.parser.parse(
                        to_parse,
                        fuzzy=True,
                        fuzzy_with_tokens=True,
                        dayfirst=True,
                        yearfirst=False,
                        ignoretz=False,
                        default=local_now.replace(hour=9, minute=0, second=0, microsecond=0),
                    )
                except OverflowError as e:
                    raise ValueError(f"• Fuzzy parsing: {e}")
                except dateutil.parser.ParserError as e:
                    dateutil_error = e
                    try:
                        parsed_date = dateparser.parse(arg, settings={"TIMEZONE": timezone})
                    except OverflowError as e:
                        raise ValueError(f"• Fuzzy parsing: {e}")
                    reminder_text = text
                else:
                    if parsed_date.replace(
                        hour=0, minute=0, second=0, microsecond=0
                    ) == local_now.replace(hour=0, minute=0, second=0, microsecond=0) and (
                        parsed_date.hour < local_now.hour
                        or (
                            parsed_date.hour == local_now.hour
                            and parsed_date.minute < local_now.minute
                        )
                    ):
                        parsed_date = parsed_date.replace(day=parsed_date.day + 1)
                    reminder_text = (
                        "".join(
                            [
                                t
                                for t in text_tuple
                                if t.strip() not in ["", "\n", ",", " ,", "in", "on", "at", "the"]
                            ]
                        ).strip()
                        or text
                    )
            if parsed_date is None:
                raise ValueError(
                    f"• Fuzzy parsing: Impossible to parse this date. {' '.join([f'{e_arg}.' for e_arg in dateutil_error.args])}"
                )

            # if parsed_date.hour == 0 and parsed_date.minute == 0:
            #     parsed_date = parsed_date.replace(tzinfo=tz)
            #     parsed_date = parsed_date.replace(hour=9)
            # parsed_date = parsed_date.replace(tzinfo=tz)
            parsed_date = parsed_date.astimezone(tz=datetime.timezone.utc)
            return parsed_date, reminder_text.strip() if return_text and reminder_text else text

        expires_at = None
        repeat = None
        text = content
        info = []
        try:
            expires_at = await parse_iso_date(argument)
        except ValueError as e:
            info.append(e.args[0])
            try:
                expires_at, repeat, text = await parse_cron_trigger(argument, text=content)
            except ValueError as e:
                info.append(e.args[0])
                try:
                    expires_at = await parse_timestamp(argument)
                except ValueError as e:
                    info.append(e.args[0])
                    try:
                        expires_at, repeat, text = await parse_relative_date(
                            argument, text=content
                        )
                    except ValueError as e:
                        info.append(e.args[0])
                        try:
                            expires_at, repeat = await parse_recurrent(argument)
                        except ValueError as e:
                            info.append(e.args[0])
                            try:
                                expires_at, text = await parse_fuzzy_date(argument, text=content)
                            except ValueError as e:
                                info.append(e.args[0])

        if expires_at is not None and isinstance(expires_at, datetime.datetime):
            expires_at = expires_at.replace(microsecond=0)
            if not await cog.config.seconds_allowed() or 0 <= expires_at.second < 30:
                expires_at.replace(second=0)
            else:
                expires_at.replace(second=30)
            if (
                expires_at < utc_now.replace(second=0, microsecond=0)
            ):  # Negative intervals are not allowed.
                info = [  # info.append(
                    f"• Global check: The given date must be in the future. Interpreted date: <t:{int(expires_at.timestamp())}:F>."
                ]
                expires_at = None
            else:
                try:
                    datetime.datetime.timestamp(expires_at)
                except OSError:  # protect against out of epoch dates
                    info = [  # info.append(
                        "• Global check: The given date is exceeding the linux epoch. Please choose an earlier date."
                    ]
                    expires_at = None
                else:
                    if expires_at < utc_now + dateutil.relativedelta.relativedelta(minutes=1):
                        info = [  # info.append(
                            "• Global check: Reminder time must be at least 1 minute."  # RRULES don't understand that...
                        ]
                        expires_at = None
                    # else:
                    #     if expires_at.second != 0:
                    #         if expires_at.minute == 59 or expires_at.second <= 30:
                    #             expires_at = expires_at.replace(day=(expires_at.day + 1) if expires_at.minute == 59 and expires_at.hour == 23 else expires_at.day, hour=(0 if expires_at.hour == 23 else (expires_at.hour + 1)) if expires_at.minute == 59 else expires_at.hour, minute=0 if expires_at.minute == 59 else (expires_at.minute + 1), second=0, microsecond=0)
                    #         else:
                    #             expires_at = expires_at.replace(second=0, microsecond=0)
        if expires_at is None:
            info = "\n".join(info)
            raise commands.BadArgument(f"Error(s) during parsing the input:\n{info}")
        if text is not None and len(text.split(" ")) > 2:
            if text.split(" ")[0].lower() == "tomorrow" and text.split(" ")[1].lower() == "at":
                text = text[12:]
            if text.split(" ")[0].lower() == "to" and text.split(" ")[1].lower() != "do:":
                text = text[3:]
            elif text.split(" ")[0].lower() == "that":
                text = text[5:]

        if content is None:
            return utc_now, expires_at, repeat
        else:
            return utc_now, expires_at, repeat, text.strip().strip("".join(discord.ext.commands.view._all_quotes)) if text is not None else None


class ContentConverter(commands.Converter):  # no longer used
    async def convert(
        self, ctx: commands.Context, argument: str
    ) -> typing.Union[discord.Message, str]:
        try:
            return await commands.MessageConverter().convert(ctx, argument=argument)
        except commands.BadArgument:
            pass
        return argument


class ExistingReminderConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> typing.Any:
        cog = ctx.bot.get_cog("Reminders")
        if ctx.author.id not in cog.cache or not (reminders := cog.cache[ctx.author.id]):
            raise commands.BadArgument(_("You haven't any reminders."))
        if argument == "last":
            return sorted(reminders.values(), key=lambda r: r.created_at)[-1]
        elif argument == "next":
            return sorted(reminders.values(), key=lambda r: r.next_expires_at)[0]
        else:
            try:
                reminder_id = int(argument.lstrip("#"))
            except ValueError:
                raise commands.BadArgument(_("Reminder ID must be an integer."))
            if reminder_id in reminders:
                return reminders[reminder_id]
            else:
                raise commands.BadArgument(_("You haven't any reminder with this id."))


class DurationParser:
    """Thanks to PhasecoreX for this code (https://github.com/PhasecoreX/PCXCogs/blob/master/remindme/reminder_parse.py)!"""

    def __init__(self):
        ParserElement.enablePackrat()

        unit_years = (
            CaselessLiteral("years") | CaselessLiteral("year") | CaselessLiteral("y")
        ) + (FollowedBy(Regex(r"\d+[a-zA-Z]+")) | WordEnd())
        years = (
            Combine(Optional(oneOf("+ -")) + Optional(Word(nums), default="1")).setParseAction(
                lambda token_list: [int(token_list[0])]
            )("years")
            + unit_years
        )
        unit_months = (
            CaselessLiteral("months") | CaselessLiteral("month") | CaselessLiteral("mo")
        ) + (FollowedBy(Regex(r"\d+[a-zA-Z]+")) | WordEnd())
        months = (
            Combine(Optional(oneOf("+ -")) + Optional(Word(nums), default="1")).setParseAction(
                lambda token_list: [int(token_list[0])]
            )("months")
            + unit_months
        )
        unit_weeks = (
            CaselessLiteral("weeks") | CaselessLiteral("week") | CaselessLiteral("w")
        ) + (FollowedBy(Regex(r"\d+[a-zA-Z]+")) | WordEnd())
        weeks = (
            Combine(Optional(oneOf("+ -")) + Optional(Word(nums), default="1")).setParseAction(
                lambda token_list: [int(token_list[0])]
            )("weeks")
            + unit_weeks
        )
        unit_days = (CaselessLiteral("days") | CaselessLiteral("day") | CaselessLiteral("d")) + (
            FollowedBy(Regex(r"\d+[a-zA-Z]+")) | WordEnd()
        )
        days = (
            Combine(Optional(oneOf("+ -")) + Optional(Word(nums), default="1")).setParseAction(
                lambda token_list: [int(token_list[0])]
            )("days")
            + unit_days
        )
        unit_hours = (
            CaselessLiteral("hours")
            | CaselessLiteral("hour")
            | CaselessLiteral("hrs")
            | CaselessLiteral("hr")
            | CaselessLiteral("h")
        ) + (FollowedBy(Regex(r"\d+[a-zA-Z]+")) | WordEnd())
        hours = (
            Combine(Optional(oneOf("+ -")) + Optional(Word(nums), default="1")).setParseAction(
                lambda token_list: [int(token_list[0])]
            )("hours")
            + unit_hours
        )
        unit_minutes = (
            CaselessLiteral("minutes")
            | CaselessLiteral("minute")
            | CaselessLiteral("mins")
            | CaselessLiteral("min")
            | CaselessLiteral("m")
        ) + (FollowedBy(Regex(r"\d+[a-zA-Z]+")) | WordEnd())
        minutes = (
            Combine(Optional(oneOf("+ -")) + Optional(Word(nums), default="1")).setParseAction(
                lambda token_list: [int(token_list[0])]
            )("minutes")
            + unit_minutes
        )
        unit_seconds = (
            CaselessLiteral("seconds")
            | CaselessLiteral("second")
            | CaselessLiteral("secs")
            | CaselessLiteral("sec")
            | CaselessLiteral("s")
        ) + (FollowedBy(Regex(r"\d+[a-zA-Z]+")) | WordEnd())
        seconds = (
            Combine(Optional(oneOf("+ -")) + Optional(Word(nums), default="1")).setParseAction(
                lambda token_list: [int(token_list[0])]
            )("seconds")
            + unit_seconds
        )

        time_unit = years | months | weeks | days | hours | minutes | seconds
        time_unit_separators = Optional(Literal(",")) + Optional(CaselessLiteral("and"))
        full_time = time_unit + ZeroOrMore(Suppress(Optional(time_unit_separators)) + time_unit)

        in_opt_time = Group(Optional(Keyword("in")) + full_time)("in")
        in_req_time = Group(Keyword("in") + full_time)("in")
        every_time = Group(Keyword("every") + full_time)("every")
        on_time = Group(Keyword("on") + SkipTo(every_time | StringEnd())("on"))("on")
        at_time = Group(Keyword("at") + SkipTo(every_time | StringEnd())("at"))("at")

        reminder_text_capture = SkipTo(
            every_time | in_req_time | on_time | StringEnd()
        ).setParseAction(tokenMap(str.strip))
        reminder_text_optional_prefix = Optional(Suppress(Keyword("to")))
        reminder_text = reminder_text_optional_prefix + reminder_text_capture("text")

        in_every_text = in_opt_time + every_time + reminder_text
        every_in_text = every_time + in_req_time + reminder_text
        in_text_every = in_opt_time + reminder_text + every_time
        every_text_in = every_time + reminder_text + in_req_time
        text_in_every = reminder_text + in_req_time + every_time
        text_every_in = reminder_text + every_time + in_req_time

        in_text = in_opt_time + reminder_text
        text_in = reminder_text + in_req_time
        every_text = every_time + reminder_text
        text_every = reminder_text + every_time

        on_every_text = on_time + every_time + reminder_text
        text_on_every = reminder_text + on_time + every_time
        at_every_text = at_time + every_time + reminder_text
        text_at_every = reminder_text + at_time + every_time
        every_at_text = every_time + at_time + reminder_text
        text_every_at = reminder_text + every_time + at_time

        template = (
            in_every_text
            | every_in_text
            | in_text_every
            | every_text_in
            | text_in_every
            | text_every_in
            | in_text
            | text_in
            | on_every_text
            | text_on_every
            | at_every_text
            | text_at_every
            | every_at_text
            | text_every_at
            | every_text
            | text_every
        )

        self.parser = template

    def parse(self, text: str) -> typing.Dict[str, typing.Any]:
        parsed = self.parser.parseString(text, parseAll=True)
        parsed_dict = parsed.asDict()
        if "on" in parsed_dict:
            parsed_dict["on"] = parsed_dict["on"]["on"]
        elif "at" in parsed_dict:
            parsed_dict["at"] = parsed_dict["at"]["at"]
        if "in" in parsed_dict:
            parsed_dict["in"] = self.process_operations(parsed_dict["in"])
        if "every" in parsed_dict:
            parsed_dict["every"] = self.process_operations(parsed_dict["every"])
        return parsed_dict

    def process_operations(self, time_units: typing.Dict[str, int]) -> typing.Dict[str, int]:
        time_units = time_units.copy()
        for unit, value in time_units.copy().items():
            if value >= 0:
                continue
            del time_units[unit]
            if unit == "months":
                months = value
                years = time_units.get("years", 0)
                time_units["months"] = months % 12
                time_units["years"] = years + months // 12 - (1 if time_units["months"] < 0 else 0)
            elif unit == "weeks":
                weeks = value
                months = time_units.get("months", 0)
                time_units["weeks"] = weeks % 4
                time_units["months"] = months + weeks // 4 - (1 if time_units["weeks"] < 0 else 0)
            elif unit == "days":
                days = value
                weeks = time_units.get("weeks", 0)
                time_units["days"] = days % 7
                time_units["weeks"] = weeks + days // 7 - (1 if time_units["days"] < 0 else 0)
            elif unit == "hours":
                hours = value
                days = time_units.get("days", 0)
                time_units["hours"] = hours % 24
                time_units["days"] = days + hours // 24 - (1 if time_units["hours"] < 0 else 0)
            elif unit == "minutes":
                minutes = value
                hours = time_units.get("hours", 0)
                time_units["minutes"] = minutes % 60
                time_units["hours"] = (
                    hours + minutes // 60 - (1 if time_units["minutes"] < 0 else 0)
                )
            elif unit == "seconds":
                seconds = value
                minutes = time_units.get("minutes", 0)
                time_units["seconds"] = seconds % 60
                time_units["minutes"] = (
                    minutes + seconds // 60 - (1 if time_units["seconds"] < 0 else 0)
                )
        return time_units

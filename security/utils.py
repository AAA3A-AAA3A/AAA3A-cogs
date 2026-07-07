import datetime

import discord
from fuzzywuzzy import StringMatcher

from redbot.core import commands

from .constants import WHITELIST_TYPES


class WhitelistTypeConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> str:
        cog = ctx.bot.get_cog("Security")
        for whitelist_type in WHITELIST_TYPES:
            value = whitelist_type["value"]
            if argument == value:
                return value
            if (
                module_key := next(m for m in cog.modules if value.startswith(m))
            ) is not None and argument == value.removeprefix(f"{module_key}_"):
                return value
        raise commands.BadArgument(f"Unknown whitelist type: {argument}")


def get_correct_timeout_duration(
    member: discord.Member,
    duration: datetime.timedelta,
) -> datetime.timedelta:
    if member.is_timed_out():
        duration += member.timed_out_until - datetime.datetime.now(datetime.timezone.utc)
    return min(duration, datetime.timedelta(days=28))


def get_non_animated_asset(
    asset: discord.Asset | None = None,
) -> discord.Asset | None:
    if asset is None:
        return None
    if not asset.is_animated():
        return asset
    return discord.Asset(
        asset._state,
        url=asset.url.replace("/a_", "/").replace(".gif", ".png"),
        key=asset.key.removeprefix("a_"),
        animated=False,
    )


def clean_backticks(text: str) -> str:
    return text.replace("`", "\u02cb")


def get_health_grade(score: int) -> str:
    if score >= 90:
        return "A"
    if score >= 75:
        return "B"
    if score >= 50:
        return "C"
    if score >= 25:
        return "D"
    return "F"


def get_next_monday_timestamp(from_time: datetime.datetime | None = None) -> int:
    now = from_time or datetime.datetime.now(datetime.timezone.utc)
    days_ahead = (7 - now.weekday()) % 7 or 7
    next_monday = (now + datetime.timedelta(days=days_ahead)).replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )
    return int(next_monday.timestamp())


def similarity_ratio_check(left: str, right: str, similarity_ratio: float) -> bool:
    if not left or not right:
        return False
    return StringMatcher.ratio(left.lower(), right.lower()) >= similarity_ratio

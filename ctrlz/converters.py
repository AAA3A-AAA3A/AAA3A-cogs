import datetime as dt

import discord

from redbot.core import commands
from redbot.core.i18n import Translator

_: Translator = Translator("CtrlZ", __file__)


class AuditLogActionConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> discord.AuditLogAction:
        try:
            action = discord.AuditLogAction[argument]
        except KeyError:
            raise commands.BadArgument(_("Invalid action."))
        return action


class DateTimeConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> dt.datetime:
        try:
            date_time = dt.datetime.fromisoformat(argument).replace(
                tzinfo=dt.timezone.utc,
            )
        except ValueError:
            raise commands.BadArgument(
                _("Invalid datetime format. Expected format is ISO (`YYYY-MM-DDTHH:MM:SS`)."),
            )
        if (
            not (dt.datetime.now(tz=dt.timezone.utc) - dt.timedelta(days=7))
            <= date_time
            <= dt.datetime.now(tz=dt.timezone.utc)
        ):
            raise commands.BadArgument(_("The date must be within the last 7 days."))
        return date_time

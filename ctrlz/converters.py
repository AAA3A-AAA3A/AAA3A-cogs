import datetime

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
    async def convert(self, ctx: commands.Context, argument: str) -> datetime.datetime:
        try:
            date_time = datetime.datetime.fromisoformat(argument).replace(
                tzinfo=datetime.UTC,
            )
        except ValueError:
            raise commands.BadArgument(
                _("Invalid datetime format. Expected format is ISO (`YYYY-MM-DDTHH:MM:SS`)."),
            )
        if (
            not (datetime.datetime.now(tz=datetime.UTC) - datetime.timedelta(days=7))
            <= date_time
            <= datetime.datetime.now(tz=datetime.UTC)
        ):
            raise commands.BadArgument(_("The date must be within the last 7 days."))
        return date_time

from redbot.core import commands  # isort:skip
from redbot.core.bot import Red  # isort:skip
from redbot.core.i18n import Translator  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import datetime
from collections import Counter
from pathlib import Path


def dashboard_page(*args, **kwargs):
    def decorator(func: typing.Callable):
        func.__dashboard_decorator_params__ = (args, kwargs)
        return func

    return decorator


_: Translator = Translator("DisurlVotesTracker", __file__)

LEADERBOARD_SOURCE_PATH: Path = Path(__file__).parent / "leaderboard.html"


class DashboardIntegration:
    bot: Red

    @commands.Cog.listener()
    async def on_dashboard_cog_add(self, dashboard_cog: commands.Cog) -> None:
        if hasattr(self, "settings") and hasattr(self.settings, "commands_added"):
            await self.settings.commands_added.wait()
        dashboard_cog.rpc.third_parties_handler.add_third_party(self)

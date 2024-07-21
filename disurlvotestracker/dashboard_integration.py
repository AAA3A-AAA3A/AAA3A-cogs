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

_ = Translator("DisurlVotesTracker", __file__)

LEADERBOARD_SOURCE_PATH: Path = Path(__file__).parent / "leaderboard.html"


class DashboardIntegration:
    bot: Red

    @commands.Cog.listener()
    async def on_dashboard_cog_add(self, dashboard_cog: commands.Cog) -> None:
        if hasattr(self, "settings") and hasattr(self.settings, "commands_added"):
            await self.settings.commands_added.wait()
        dashboard_cog.rpc.third_parties_handler.add_third_party(self)

    @dashboard_page(name="leaderboard", description="Display the Disurl lifetime votes leaderboard.")
    async def lifetime_leaderboard_page(
        self, user: discord.User, guild: discord.Guild, query: typing.Optional[str] = None, **kwargs
    ) -> typing.Dict[str, typing.Any]:
        if not await self.config.guild(guild).enabled():
            return {"status": 1, "error_title": "DisurlVotesTracker not enabled", "error_message": _("DisurlVotesTracker is not enabled in this server.")}
        members_data = await self.config.all_members(guild)
        counter = Counter({
            member: len(member_data["votes"])
            for member_id, member_data in members_data.items()
            if member_data["votes"] and (member := guild.get_member(member_id)) is not None
        })
        if not counter:
            return {"status": 1, "error_title": "No votes found", "error_message": _("No votes found in this server.")}
        members = [
            {"position": i, "display_name": member.display_name, "id": member.id, "votes": votes}
            for i, (member, votes) in enumerate(counter.most_common(), start=1)
            if query is None or query.lower() in member.display_name.lower() or query == str(member.id) or query.lstrip("#") == str(i)
        ]
        return {
            "status": 0,
            "web_content": {
                "source": LEADERBOARD_SOURCE_PATH.read_text(encoding="utf-8"),
                "members": kwargs["Pagination"].from_list(
                    members,
                    per_page=kwargs["extra_kwargs"].get("per_page"),
                    page=kwargs["extra_kwargs"].get("page"),
                    default_per_page=100,
                ),
                "total": _("Total: {total} vote{s}").format(total=counter.total(), s="" if counter.total() == 1 else "s"),
                "query": query,
            },
        }

    @dashboard_page(name="montly-leaderboard", description="Display the Disurl monthly votes leaderboard.")
    async def montly_leaderboard_page(
        self, user: discord.User, guild: discord.Guild, query: typing.Optional[str] = None, **kwargs
    ) -> typing.Dict[str, typing.Any]:
        if not await self.config.guild(guild).enabled():
            return {"status": 1, "error_title": "DisurlVotesTracker not enabled", "error_message": _("DisurlVotesTracker is not enabled in this server.")}
        members_data = await self.config.all_members(guild)
        counter = Counter({
            member: len(
                [
                    vote
                    for vote in member_data["votes"]
                    if datetime.datetime.now(tz=datetime.timezone.utc)
                    - datetime.datetime.fromtimestamp(
                        vote, tz=datetime.timezone.utc
                    )
                    < datetime.timedelta(days=30)
                ]
            )
            for member_id, member_data in members_data.items()
            if member_data["votes"] and (member := guild.get_member(member_id)) is not None
        })
        if not counter:
            return {"status": 1, "error_title": "No votes found", "error_message": _("No monthly votes found in this server.")}
        members = [
            {"position": i, "display_name": member.display_name, "id": member.id, "votes": votes}
            for i, (member, votes) in enumerate(counter.most_common(), start=1)
            if query is None or query.lower() in member.display_name.lower() or query == str(member.id) or query.lstrip("#") == str(i)
        ]
        return {
            "status": 0,
            "web_content": {
                "source": LEADERBOARD_SOURCE_PATH.read_text(encoding="utf-8"),
                "members": kwargs["Pagination"].from_list(
                    members,
                    per_page=kwargs["extra_kwargs"].get("per_page"),
                    page=kwargs["extra_kwargs"].get("page"),
                    default_per_page=100,
                ),
                "total": _("Total: {total} vote{s}").format(total=counter.total(), s="" if counter.total() == 1 else "s"),
                "query": query,
            },
        }

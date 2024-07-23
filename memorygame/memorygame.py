from AAA3A_utils import Cog, CogsUtils, Menu, Settings  # isort:skip
from redbot.core import commands, Config  # isort:skip
from redbot.core.bot import Red  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import io
from copy import deepcopy

from prettytable import PrettyTable
from redbot.core.utils.chat_formatting import box, pagify

from .dashboard_integration import DashboardIntegration
from .view import MemoryGameView

# Credits:
# General repo credits.
# Thanks to Flame for his tests which allowed to discover several errors!
# Thanks to Vertyco for ideas, and leaderboard code (https://github.com/vertyco/vrt-cogs/blob/main/pixl/pixl.py)!

_: Translator = Translator("MemoryGame", __file__)


@cog_i18n(_)
class MemoryGame(DashboardIntegration, Cog):
    """A cog to play to Memory game, with buttons, leaderboard and Red bank!"""

    def __init__(self, bot: Red) -> None:
        super().__init__(bot=bot)

        self.config: Config = Config.get_conf(
            self,
            identifier=205192943327321000143939875896557571750,
            force_registration=True,
        )
        self.config.register_guild(
            max_wrong_matches=None,
            red_economy=False,
            max_prize=5000,
            reduction_per_second=5,
            reduction_per_wrong_match=15,
        )
        self.config.register_member(
            score=0,
            wins=0,
            games=0,
        )

        _settings: typing.Dict[
            str, typing.Dict[str, typing.Union[typing.List[str], bool, str]]
        ] = {
            "max_wrong_matches": {
                "converter": commands.Range[int, 0, 50],
                "description": "Set the maximum tries for each game. Use `0` for no limit.",
            },
            "red_economy": {
                "converter": bool,
                "description": "If this option is enabled, the cog will give credits to the user each time the game is won.",
            },
            "max_prize": {
                "converter": commands.Range[int, 1000, 50000],
                "description": "Set the max prize for Red bank system and cog leaderboard. Default is 5000.",
            },
            "reduction_per_second": {
                "converter": commands.Range[int, 0, 30],
                "description": "Set the reduction per second of prize for Red bank system and cog leaderboard. Default is 5.",
            },
            "reduction_per_wrong_match": {
                "converter": commands.Range[int, 0, 30],
                "description": "Set the reduction per wrong match of prize for Red bank system and cog leaderboard. Default is 15.",
            },
        }
        self.settings: Settings = Settings(
            bot=self.bot,
            cog=self,
            config=self.config,
            group=self.config.GUILD,
            settings=_settings,
            global_path=[],
            use_profiles_system=False,
            can_edit=True,
            commands_group=self.configuration,
        )

    async def cog_load(self) -> None:
        await super().cog_load()
        await self.settings.add_commands()

    async def red_delete_data_for_user(
        self,
        *,
        requester: typing.Literal["discord_deleted_user", "owner", "user", "user_strict"],
        user_id: int,
    ) -> None:
        """Delete all user's levels/xp in each guild."""
        if requester not in ("discord_deleted_user", "owner", "user", "user_strict"):
            return
        guild_group = self.config._get_base_group(self.config.GUILD)
        async with guild_group.all() as guilds_data:
            _guilds_data = deepcopy(guilds_data)
            for guild in _guilds_data:
                if str(user_id) in _guilds_data[guild]:
                    del _guilds_data[guild][str(user_id)]
                if _guilds_data[guild] == {}:
                    del _guilds_data[guild]

    async def red_get_data_for_user(self, *, user_id: int) -> typing.Dict[str, io.BytesIO]:
        """Get all data about the user."""
        data = {
            Config.GLOBAL: {},
            Config.USER: {},
            Config.MEMBER: {},
            Config.ROLE: {},
            Config.CHANNEL: {},
            Config.GUILD: {},
        }

        guild_group = self.config._get_base_group(self.config.GUILD)
        async with guild_group.all() as guilds_data:
            for guild in guilds_data:
                if str(user_id) in guilds_data[guild]:
                    data[Config.GUILD][guild] = {str(user_id): guilds_data[guild][str(user_id)]}

        _data = deepcopy(data)
        for key, value in _data.items():
            if not value:
                del data[key]
        if not data:
            return {}
        file = io.BytesIO(str(data).encode(encoding="utf-8"))
        return {f"{self.qualified_name}.json": file}

    @property
    def games(self) -> typing.Dict[discord.Message, MemoryGameView]:
        return self.views

    @commands.bot_has_permissions(embed_links=True)
    @commands.hybrid_command()
    async def memorygame(
        self, ctx: commands.Context, difficulty: typing.Literal["3x3", "4x4", "5x5"] = "5x5"
    ) -> None:
        """
        Play to Memory game. Choose between `3x3`, `4x4` and `5x5` versions.
        """
        if ctx.guild is not None:
            max_wrong_matches = await self.config.guild(ctx.guild).max_wrong_matches()
        else:
            max_wrong_matches = None
        await MemoryGameView(
            cog=self, difficulty=difficulty, max_wrong_matches=max_wrong_matches
        ).start(ctx)

    @commands.bot_has_permissions(embed_links=True)
    @commands.hybrid_command()
    async def memorygameleaderboard(self, ctx: commands.Context) -> None:
        """
        Show MemoryGame leaderboard.
        """
        all_members = await self.config.all_members(ctx.guild)
        all_members = {
            ctx.guild.get_member(member): data
            for member, data in all_members.items()
            if ctx.guild.get_member(member) is not None
        }
        if not all_members:
            raise commands.UserFeedbackCheckFailure(_("No one has played this game yet."))
        sorted_members = sorted(all_members.items(), key=lambda x: x[1]["score"], reverse=True)
        you = next(
            (
                f"You: {num}/{len(all_members)}"
                for num, data in enumerate(sorted_members, start=1)
                if data[0] == ctx.author
            ),
            None,
        )
        embeds = []
        table = PrettyTable()
        table.field_names = ["#", "Name", "Score", "Wins", "Games"]
        for num in range(len(sorted_members)):
            place = num + 1
            member: discord.Member = sorted_members[num][0]
            data = sorted_members[num][1]
            table.add_row(
                [
                    place,
                    member.display_name,
                    data["score"],
                    data["wins"],
                    data["games"],
                ]
            )
        for page in pagify(str(table), page_length=2000):
            embed = discord.Embed(title="MemoryGame Leaderboard")
            embed.description = box(page, lang="py")
            if you:
                embed.set_footer(text=you)
            embeds.append(embed)
        await Menu(pages=embeds).start(ctx)

    @commands.guild_only()
    @commands.admin_or_permissions(administrator=True)
    @commands.hybrid_group(name="setmemorygame")
    async def configuration(self, ctx: commands.Context) -> None:
        """Group of commands to set MemoryGame."""
        pass

    @configuration.command()
    async def resetleaderboard(self, ctx: commands.Context) -> None:
        """Reset leaderboard in the guild."""
        await self.config.clear_all_members(ctx.guild)

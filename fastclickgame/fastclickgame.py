from AAA3A_utils import Cog, Menu, Settings, CogsUtils  # isort:skip
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
from .view import FastClickGameView

# Credits:
# General repo credits.

_: Translator = Translator("FastClickGame", __file__)


@cog_i18n(_)
class FastClickGame(DashboardIntegration, Cog):
    """Play to click on the right button as fast as you can!"""

    def __init__(self, bot: Red) -> None:
        super().__init__(bot=bot)

        self.config: Config = Config.get_conf(
            self,
            identifier=205192943327321000143939875896557571750,
            force_registration=True,
        )
        self.config.register_guild(
            red_economy=False,
            prize=2500,
        )
        self.config.register_member(
            score=0,
            wins=0,
            games=0,
        )

        _settings: typing.Dict[
            str, typing.Dict[str, typing.Union[typing.List[str], bool, str]]
        ] = {
            "red_economy": {
                "converter": bool,
                "description": "If this option is enabled, the cog will give credits to the user each time the game is won.",
            },
            "prize": {
                "converter": commands.Range[int, 1000, 50000],
                "description": "Set the prize for Red bank system and cog leaderboard. Default is 5000.",
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
            commands_group=self.setfastclickgame,
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
    def games(self) -> typing.Dict[discord.Message, FastClickGameView]:
        return self.views

    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    @commands.hybrid_group(aliases=["fastclick", "fcg"])
    async def fastclickgame(self, ctx: commands.Context) -> None:
        """Play to click on the right button as fast as you can!"""
        pass

    @fastclickgame.command()
    async def multi(
        self,
        ctx: commands.Context,
        rounds: commands.Range[int, 1, 10] = 3,
        buttons: commands.Range[int, 5, 25] = 25,
    ) -> None:
        """Play Fast Click Game with multiple rounds."""
        await FastClickGameView(cog=self, rounds=rounds, buttons=buttons, players=[]).start(ctx)

    @fastclickgame.command(aliases=["single"])
    async def duel(self, ctx: commands.Context, *, player: discord.Member) -> None:
        """Play Fast Click Game with another player."""
        if player == ctx.author:
            raise commands.UserFeedbackCheckFailure(_("You can't play with yourself."))
        embed = discord.Embed(
            title=_("Fast Click Game"),
            color=await ctx.embed_color(),
            description=_("Do you want to play Fast Click Game with {ctx.author.mention}?").format(
                ctx=ctx
            ),
        )
        fake_ctx = type(
            "FakeContext",
            (object,),
            {"author": player, "send": ctx.send, "channel": ctx.channel, "bot": ctx.bot},
        )
        if not await CogsUtils.ConfirmationAsk(fake_ctx, content=player.mention, embed=embed):
            return
        await FastClickGameView(cog=self, rounds=1, buttons=5, players=[ctx.author, player]).start(
            ctx
        )

    @fastclickgame.command(aliases=["lb"])
    async def leaderboard(self, ctx: commands.Context) -> None:
        """Show Fast Click Game leaderboard."""
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
            embed = discord.Embed(title="Fast Click Game - Leaderboard")
            embed.description = box(page, lang="py")
            if you:
                embed.set_footer(text=you)
            embeds.append(embed)
        await Menu(pages=embeds).start(ctx)

    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    @commands.hybrid_group()
    async def setfastclickgame(self, ctx: commands.Context) -> None:
        """Group of commands to set FastClickGame."""
        pass

    @setfastclickgame.command()
    async def resetleaderboard(self, ctx: commands.Context) -> None:
        """Reset leaderboard in the guild."""
        await self.config.clear_all_members(ctx.guild)

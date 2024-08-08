from AAA3A_utils import Cog, Settings, Menu  # isort:skip
from redbot.core import commands, Config  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

from redbot.core import bank
from redbot.core.errors import BalanceTooHigh
from redbot.core.utils.chat_formatting import pagify, box

import asyncio
from prettytable import PrettyTable

from .views import JoinGameView, RolloutGameView

# Credits:
# General repo credits.
# Thanks to Shoyo and C for the cog idea!

_: Translator = Translator("RolloutGame", __file__)


@cog_i18n(_)
class RolloutGame(Cog):
    """Play a match of Rollout game, with buttons!"""

    def __init__(self, bot: commands.Bot) -> None:
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
            commands_group=self.setrolloutgame,
        )

    async def cog_load(self) -> None:
        await super().cog_load()
        await self.settings.add_commands()

    @property
    def games(self) -> typing.Dict[discord.Message, JoinGameView]:
        return self.views

    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    @commands.hybrid_command(aliases=["rollout"])
    async def rolloutgame(self, ctx: commands.Context) -> None:
        """Play a match of Rollout game."""
        join_view: JoinGameView = JoinGameView(self)
        await join_view.start(ctx)
        await join_view.wait()
        players = join_view.players
        if join_view.cancelled:
            return
        for player in players:
            member_config = await self.config.member(player).all()
            member_config["games"] += 1
            await self.config.member(player).set(member_config)
        disabled_numbers = []
        round = 0
        while len(players) > 1:
            round += 1
            view: RolloutGameView = RolloutGameView(self)
            await view.start(
                ctx, players=players, round=round, disabled_numbers=disabled_numbers,
            )
            for __ in range(30):
                if len(view._choices) == len(view.players):
                    break
                await asyncio.sleep(1)
            await view.on_timeout()
            view.stop()
            try:
                __, players, __ = await view.choose_number()
            except RuntimeError:
                round -= 1
            except TimeoutError:
                return
        winner = players[0]

        config = await self.config.guild(ctx.guild).all()
        prize = config["prize"]
        member_config = await self.config.member(winner).all()
        member_config["score"] += prize
        member_config["wins"] += 1
        await self.config.member(winner).set(member_config)
        if config["red_economy"]:
            # https://canary.discord.com/channels/133049272517001216/133251234164375552/1089212578279997521
            try:
                await bank.deposit_credits(winner, prize)
            except BalanceTooHigh as e:
                await bank.set_balance(winner, e.max_balance)

        embed = discord.Embed(
            title=_("Congratulations **{winner.display_name}**! You won the game!").format(winner=winner),
            color=await ctx.embed_color(),
            timestamp=ctx.message.created_at,
        )
        await ctx.send(content=winner.mention, embed=embed)

    @commands.bot_has_permissions(embed_links=True)
    @commands.hybrid_command(aliases=["rolloutlb"])
    async def rolloutgameleaderboard(self, ctx: commands.Context) -> None:
        """Show RollOutGame leaderboard."""
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
            embed = discord.Embed(title="RolloutGame Leaderboard")
            embed.description = box(page, lang="py")
            if you:
                embed.set_footer(text=you)
            embeds.append(embed)
        await Menu(pages=embeds).start(ctx)

    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    @commands.hybrid_group()
    async def setrolloutgame(self, ctx: commands.Context) -> None:
        """Group of commands to set RollOutGame."""
        pass

    @setrolloutgame.command()
    async def resetleaderboard(self, ctx: commands.Context) -> None:
        """Reset leaderboard in the guild."""
        await self.config.clear_all_members(ctx.guild)

from AAA3A_utils import Cog  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

from redbot.core.utils.chat_formatting import humanize_list
from redbot.core.utils.menus import start_adding_reactions

import asyncio
import datetime
import random

from .tests import TESTS
from .view import JoinGameView

# Credits:
# General repo credits.

_: Translator = Translator("BotSaysGame", __file__)


@cog_i18n(_)
class BotSaysGame(Cog):
    """Play the Bot Says... game, where the bot says something easy to do, and you have to do it to not be eliminated!"""

    @property
    def games(self) -> typing.Dict[discord.Message, JoinGameView]:
        return self.views

    @commands.guild_only()
    @commands.max_concurrency(1, per=commands.BucketType.channel)
    @commands.mod_or_permissions(manage_messages=True)
    @commands.bot_has_permissions(embed_links=True)
    @commands.hybrid_command(aliases=["botsaysgame"])
    async def botsays(self, ctx: commands.Context) -> None:
        """Play the Bot Says... game, where the bot says something easy to do, and you have to do it to not be eliminated."""
        join_view: JoinGameView = JoinGameView(self)
        await join_view.start(ctx)
        await join_view.wait()
        if join_view.cancelled:
            return
        players = join_view.players

        round = 0
        while len(players) > 1:
            round += 1
            embed: discord.Embed = discord.Embed(
                title=_("Round {round}").format(round=round),
                color=await ctx.embed_color(),
            )
            test = random.choice(TESTS)(ctx, players)
            request, view, reactions = await test.initialize()
            embed.description = _(
                "-# Remaining players...\n"
                "{players}\n\n"
                "{bot.display_name} says...\n"
                "> # {request}\n\n"
                "-# Time ends {timestamp}"
            ).format(
                players=humanize_list(
                    [player.mention for player in players]
                ),
                bot=ctx.guild.me,
                request=request,
                timestamp=f"<t:{int((datetime.datetime.now(tz=datetime.timezone.utc) + datetime.timedelta(seconds=20)).timestamp())}:R>",
            )
            message = await ctx.send(embed=embed, view=view)
            if view is not None:
                view._message = message
            if reactions:
                await start_adding_reactions(
                    message, reactions
                )
            for i in range(20):
                await asyncio.sleep(1)
                if len(test.success) + len(test.fail) == len(players):
                    break
            if view is not None:
                await view.on_timeout()
            eliminated = await test.get_eliminated_players()
            if len(eliminated) == len(players):
                await ctx.send(
                    embed=discord.Embed(
                        title=_("All players would be eliminated this round! I let you continue..."),
                        color=await ctx.embed_color(),
                    )
                )
                continue
            elif not eliminated:
                await ctx.send(
                    embed=discord.Embed(
                        title=_("No one was eliminated this round!"),
                        color=await ctx.embed_color(),
                    )
                )
                continue
            players = [player for player in players if player not in eliminated]
            await ctx.send(
                embed=discord.Embed(
                    title=_("Eliminated players this round..."),
                    description="\n".join(
                        f"**•** {player.mention}"
                        for player in eliminated
                    ),
                    color=await ctx.embed_color(),
                ),
            )

        winner = list(players)[0]
        embed: discord.Embed = discord.Embed(
            title=_("Congratulations **{winner.display_name}**! You won the game!").format(
                winner=winner
            ),
            color=await ctx.embed_color(),
            timestamp=ctx.message.created_at,
        )
        embed.set_thumbnail(url=winner.display_avatar)
        embed.set_footer(text=ctx.guild.name, icon_url=ctx.guild.icon)
        await ctx.send(content=winner.mention, embed=embed)

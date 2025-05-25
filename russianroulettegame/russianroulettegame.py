from AAA3A_utils import Cog  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import asyncio
import random

from .views import JoinGameView, ShotView

# Credits:
# General repo credits.

_: Translator = Translator("RussianRouletteGame", __file__)


@cog_i18n(_)
class RussianRouletteGame(Cog):
    """Play the Russian Roulette game!"""

    @property
    def games(self) -> typing.Dict[discord.Message, JoinGameView]:
        return self.views

    @commands.guild_only()
    @commands.max_concurrency(1, per=commands.BucketType.channel)
    @commands.mod_or_permissions(manage_messages=True)
    @commands.bot_has_permissions(embed_links=True)
    @commands.hybrid_command(aliases=["russianroulettegame"])
    async def russianroulette(self, ctx: commands.Context) -> None:
        """Play the Russian Roulette game."""
        join_view: JoinGameView = JoinGameView(self)
        await join_view.start(ctx)
        await join_view.wait()
        if join_view.cancelled:
            return
        players = join_view.players

        round = 0
        while len(players) > 1:
            round += 1
            await ctx.send(
                embed=discord.Embed(
                    title=_("Round {round}").format(round=round),
                    description=_("There are {count} players left.").format(count=len(players)),
                    color=await ctx.embed_color(),
                ),
            )
            bullet = random.randint(0, len(players) - 1)
            random.shuffle(players)
            for i, player in enumerate(players):
                view: ShotView = ShotView(self, player)
                view._message = await ctx.send(
                    _("{player.mention}, it's your turn to shoot!").format(player=player),
                    view=view,
                )
                if await view.wait():
                    players.remove(player)
                    await ctx.send(
                        _("I got tired of waiting, so I decided to shoot {player.mention} myself.").format(
                            player=player
                        )
                    )
                    continue
                await ctx.send(
                    _("{player.mention} put the gun up to their head and pulled the trigger...").format(
                        player=player
                    )
                )
                await asyncio.sleep(2)
                if i == bullet:
                    if random.random() >= 0.1:
                        players.remove(player)
                        await ctx.send(
                            _("**💥 BANG!** {player.mention} is dead.").format(player=player)
                        )
                    else:
                        p = random.choice(
                            [p for p in players if p != player]
                        )
                        players.remove(p)
                        await ctx.send(
                            _("**💥 BANG!** {player.mention} made a mistake and put their gun in the wrong direction, shooting {p.mention}.").format(
                                player=player,
                                p=p,
                            )
                        )
                    break
                else:
                    await ctx.send(_("Click. Nothing happened."))

        winner = list(players)[0]
        embed = discord.Embed(
            title=_("Congratulations **{winner.display_name}**! You won the game!").format(
                winner=winner
            ),
            color=await ctx.embed_color(),
            timestamp=ctx.message.created_at,
        )
        embed.set_thumbnail(url=winner.display_avatar)
        embed.set_footer(text=ctx.guild.name, icon_url=ctx.guild.icon)
        await ctx.send(content=winner.mention, embed=embed)

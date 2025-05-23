from AAA3A_utils import Cog  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.bot import Red  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

from redbot.core.data_manager import bundled_data_path
from redbot.core.utils.menus import start_adding_reactions

import asyncio
import random
from collections import defaultdict

from .view import Lang, JoinGameView

# Credits:
# General repo credits.

_: Translator = Translator("BlackTeaGame", __file__)


DIACRITIC_SYMBOLS: typing.Dict[str, str] = {
    "a": "àáâãäå",
    "c": "ç",
    "e": "èéêë",
    "i": "ìíîï",
    "n": "ñ",
    "o": "òóôõö",
    "u": "ùúûü",
    "y": "ýÿ",
}


@cog_i18n(_)
class BlackTeaGame(Cog):
    """Play the Black Tea game, in multiple languages!"""

    def __init__(self, bot: Red) -> None:
        super().__init__(bot=bot)
        self.dictionaries: typing.Dict[str, typing.List[str]] = defaultdict(list)

    async def cog_load(self) -> None:
        await super().cog_load()
        data_path = bundled_data_path(self)
        for lang in Lang:
            with (data_path / f"{lang.value}.txt").open(
                mode="rt", encoding="utf-8"
            ) as file:
                for word in file.read().split("\n"):
                    self.dictionaries[lang.value].append(word)

    @property
    def games(self) -> typing.Dict[discord.Message, JoinGameView]:
        return self.views

    @commands.guild_only()
    @commands.max_concurrency(1, per=commands.BucketType.channel)
    @commands.mod_or_permissions(manage_messages=True)
    @commands.bot_has_permissions(embed_links=True)
    @commands.hybrid_command(aliases=["blackteagame"])
    async def blacktea(
        self,
        ctx: commands.Context,
        lang: Lang = Lang.ENGLISH,
        base_hp: commands.Range[int, 1, 20] = 2,
    ) -> None:
        """Play the Black Tea game, in multiple languages."""
        join_view: JoinGameView = JoinGameView(self, lang=lang)
        await join_view.start(ctx)
        await join_view.wait()
        if join_view.cancelled:
            return
        players = {
            player: base_hp
            for player in join_view.players
        }

        used_words: typing.List[str] = []
        player = None
        while len(players) > 1:
            player = random.choice(
                [p for p in players if p != player]
            )
            random_word = None
            while random_word is None or len(random_word) < 3:
                random_word = random.choice(
                    self.dictionaries[lang.value]
                )
            i = random.randint(0, len(random_word) - 3)
            letters = random_word[i:i + 3].upper()
            message = await ctx.send(
                _("☕ {player.mention}, type a word containing: **{letters}**").format(
                    player=player, letters=letters
                )
            )
            async def task() -> None:
                await asyncio.sleep(7)
                for reaction in ("3️⃣", "2️⃣", "1️⃣"):
                    start_adding_reactions(message, (reaction,))
                    await asyncio.sleep(1)
            _task = asyncio.create_task(task())
            try:
                def check(m: discord.Message) -> bool:
                    word = m.content.lower().translate(
                        str.maketrans(
                            {v: key for key, value in DIACRITIC_SYMBOLS.items() for v in value}
                        )
                    )
                    if (
                        m.author == player
                        and m.channel == ctx.channel
                        and letters.lower() in word
                        and word in self.dictionaries[lang.value]
                        and word not in used_words
                    ):
                        used_words.append(word)
                        return True
                    return False
                m = await self.bot.wait_for(
                    "message_without_command",
                    timeout=10,
                    check=check,
                )
                start_adding_reactions(m, ("✅",))
            except asyncio.TimeoutError:
                start_adding_reactions(message, ("💥",))
                players[player] -= 1
                await ctx.send(
                    _("💥 Time's up: -1 HP (Left: **{left}** HP)").format(
                        left=players[player]
                    )
                )
                if players[player] == 0:
                    del players[player]
                    await ctx.send(
                        _("🚪 **{player.mention} eliminated!**").format(
                            player=player
                        )
                    )
            else:
                _task.cancel()

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

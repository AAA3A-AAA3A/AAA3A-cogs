from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import asyncio
import datetime
import functools
import time
from collections import Counter
from random import randint

from redbot.core import bank
from redbot.core.errors import BalanceTooHigh
from redbot.core.utils.chat_formatting import humanize_list

_: Translator = Translator("FastClickGame", __file__)


class FastClickGameView(discord.ui.View):
    def __init__(
        self,
        cog: commands.Cog,
        rounds: int = 1,
        buttons: int = 5,
        players: typing.List[discord.Member] = [],
    ) -> None:
        super().__init__(timeout=60 * 10)
        self.ctx: commands.Context = None
        self.cog: commands.Cog = cog
        self.rounds: int = rounds
        self.buttons: int = buttons
        self.players: typing.List[discord.Member] = players

        self._message: discord.Message = None
        self.winners: typing.List[discord.Member] = []
        self.times: typing.List[float] = []
        self.start_time: float = 0
        self.event: asyncio.Event = asyncio.Event()
        self.lock: asyncio.Lock = asyncio.Lock()

    async def start(self, ctx: commands.Context) -> discord.Message:
        self.ctx: commands.Context = ctx

        for __ in range(self.buttons):
            button = discord.ui.Button(
                style=discord.ButtonStyle.secondary,
                disabled=True,
                label="\u200b",
            )
            button.callback = functools.partial(self.callback, button=button)
            self.add_item(button)

        embed: discord.Embed = discord.Embed(
            title=_("Fast Click Game"), color=await self.ctx.embed_color()
        )
        embed.set_footer(text=ctx.guild.name, icon_url=ctx.guild.icon)
        embed.description = _(
            "⏳ The game will start {timestamp}, first one to click the 🟩 button wins.\n> **{rounds} round{s}** to play."
        ).format(
            timestamp=discord.utils.format_dt(
                datetime.datetime.now(tz=datetime.timezone.utc) + datetime.timedelta(seconds=5),
                "R",
            ),
            rounds=self.rounds,
            s="s" if self.rounds > 1 else "",
        )
        self._message: discord.Message = await self.ctx.send(embed=embed, view=self)
        self.cog.views[self._message] = self

        for current_round in range(1, self.rounds + 1):
            self.event.clear()
            await asyncio.sleep(5 if current_round == 1 else 3)
            embed.title = _("Fast Click Game - Round {current_round}/{total_rounds}").format(
                current_round=current_round, total_rounds=self.rounds
            )
            embed.description = _("🖱️ To win you must be the first to press the 🟩 button.")
            success_i = randint(0, self.buttons - 1)
            success_button = self.children[success_i]
            success_button.style = discord.ButtonStyle.success
            success_button.emoji = "🖱️"
            success_button.label = None
            success_button.disabled = False
            await self._message.edit(embed=embed, view=self)
            self.start_time = time.time()
            try:
                await asyncio.wait_for(self.event.wait(), timeout=180)
            except asyncio.TimeoutError:
                await self.on_timeout()
                await self._message.reply(_("No one clicked the button in time."))
                return
            winner = self.winners[-1]
            embed.description = (
                _("🏆 {winner.mention} has won this round!\n")
                + _("🖱️ They clicked the button in **{click_time}s**.\n")
                + (
                    _("⏳ Next round starting {timestamp}...\n")
                    if current_round < self.rounds
                    else ""
                )
            ).format(
                winner=winner,
                click_time=self.times[-1],
                timestamp=discord.utils.format_dt(
                    datetime.datetime.now(tz=datetime.timezone.utc)
                    + datetime.timedelta(seconds=3),
                    "R",
                ),
            )
            success_button.style = discord.ButtonStyle.secondary
            success_button.emoji = None
            success_button.label = "\u200b"
            success_button.disabled = True
            await self._message.edit(embed=embed, view=self)

        counter = Counter({winner: self.winners.count(winner) for winner in self.winners})
        max_fastest_clicks = max(counter.values())
        winners = [
            winner
            for winner, fastest_clicks in counter.items()
            if fastest_clicks == max_fastest_clicks
        ]
        winners_mentions = humanize_list([winner.mention for winner in winners])
        embed.title = _("Fast Click Game - Winner{s}").format(s="s" if len(winners) > 1 else "")
        embed.description = _(
            "**🏆 {winners} won with {fastest_clicks} fastest click{s}!**"
        ).format(
            winners=winners_mentions,
            fastest_clicks=max_fastest_clicks,
            s="s" if max_fastest_clicks > 1 else "",
        )
        embed.add_field(
            name=_("🖱️ Clicks"),
            value="\n".join(
                f"**•** {winner.mention}: {counter[winner]} {_('click')}{'s' if counter[winner] > 1 else ''} ({humanize_list([f'`{self.times[i]}s`' for i, w in enumerate(self.winners) if w == winner])}s)"
                for winner in counter
            ),
        )
        await self._message.reply(content=winners_mentions, embed=embed)

        for winner in self.winners:
            games = await self.cog.config.member(winner).games()
            await self.cog.config.member(winner).games.set(games + 1)
        config = await self.cog.config.guild(self.ctx.guild).all()
        prize = config["prize"]
        for winner in winners:
            member_config = await self.cog.config.member(winner).all()
            member_config["score"] += prize
            member_config["wins"] += 1
            await self.cog.config.member(winner).set(member_config)
            if config["red_economy"]:
                try:
                    await bank.deposit_credits(winner, prize)
                except BalanceTooHigh as e:
                    await bank.set_balance(self.ctx.author, e.max_balance)

        return self._message

    @property
    def is_duel(self) -> bool:
        return bool(self.players)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if self.is_duel and interaction.user not in self.players:
            await interaction.response.send_message(
                _("You are not allowed to use this interaction."), ephemeral=True
            )
            return False
        return True

    async def on_timeout(self) -> None:
        for child in self.children:
            child: discord.ui.Item
            if hasattr(child, "disabled") and not (
                isinstance(child, discord.ui.Button) and child.style == discord.ButtonStyle.url
            ):
                child.disabled = True
        try:
            await self._message.edit(view=self)
        except discord.HTTPException:
            pass

    async def callback(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer()
        if button.style != discord.ButtonStyle.success:
            return
        async with self.lock:
            if self.event.is_set():
                return
            self.times.append(round(time.time() - self.start_time, 2))
            self.winners.append(interaction.user)
            self.event.set()

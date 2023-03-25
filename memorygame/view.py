from redbot.core import commands  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import asyncio
import random
import time

from redbot.core import bank
from redbot.core.errors import BalanceTooHigh

# GAME_EMOJIS = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l"]
GAME_EMOJIS = ["🏆", "🎯", "🎲", "⚽", "🏀", "🏓", "🥁", "🎮", "🎳", "🎻", "🎖️", "🏹"]

class MemoryGameView(discord.ui.View):
    def __init__(self, cog: commands.Cog, max_wrong_matches: typing.Optional[int] = None) -> None:
        super().__init__(timeout=60 * 10)
        self.ctx: commands.Context = None
        self.cog: commands.Cog = cog
        self.max_wrong_matches: typing.Optional[int] = max_wrong_matches

        self._message: discord.Message = None
        self._solution: typing.List[str] = []
        self._solution_display: typing.List[typing.List[str]] = []
        self._custom_ids: typing.Dict[str, str] = {}
        self._found: typing.List[str] = []
        self._selected: typing.Optional[str] = None

        self._start: typing.Optional[float] = None
        self._end: typing.Optional[float] = None
        self._tries: int = 0
        self._wrong_matches: int = 0

        self._lock: asyncio.Lock = asyncio.Lock()
   
    async def start(self, ctx: commands.Context) -> None:
        self.ctx: commands.Context = ctx
        self._solution, self._solution_display = self.get_emojis()
        for _list in self._solution_display:
            for emoji in _list:
                if emoji != "​":
                    custom_id = self.cog.cogsutils.generate_key(length=5, existing_keys=self._custom_ids)
                    self._custom_ids[custom_id] = emoji
                else:
                    custom_id = emoji
                button = discord.ui.Button(label="​", custom_id=custom_id)
                if emoji == "​":
                    button.disabled = True
                button.callback = self.callback
                self.add_item(button)
        embed: discord.Embed = discord.Embed(title="Memory Game", color=discord.Color.green())
        embed.set_author(name=self.ctx.author.display_name, icon_url=self.ctx.author.display_avatar)
        self._message = await self.ctx.send(embed=embed, view=self)
        self.cog.games[self._message] = self
        self._start = time.monotonic()
        return self._message

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id not in [self.ctx.author.id] + list(self.ctx.bot.owner_ids):
            await interaction.response.send_message(
                "You are not allowed to use this interaction.", ephemeral=True
            )
            return False
        return True

    async def on_timeout(self) -> None:
        for child in self.children:
            child: discord.ui.Item
            if isinstance(child, discord.ui.Button) and child.style != discord.ButtonStyle.url and child.custom_id != "​":
                child.disabled = True
        try:
            await self._message.edit(view=self)
        except discord.HTTPException:
            pass

    def get_emojis(self) -> typing.Tuple[typing.List[str], typing.List[typing.List[str]]]:
        solution = GAME_EMOJIS.copy() * 2
        random.shuffle(solution)
        raw = solution.copy()
        raw.insert(12, "​")  # invisible character
        solution_display = [
            raw[:5],
            raw[5:10],
            raw[10:15],
            raw[15:20],
            raw[20:25]
        ]
        return solution, solution_display

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        async with self._lock:
            if interaction.data["custom_id"] == "​" or self._custom_ids[interaction.data["custom_id"]] in self._found:
                return
            if self._selected is None:
                self._selected = interaction.data["custom_id"]
                button: discord.ui.Button = discord.utils.get(self.children, custom_id=self._selected)
                button.label = self._custom_ids[self._selected]
                self._message = await self._message.edit(view=self)
                return
            self._tries += 1
            if self._custom_ids[self._selected] != self._custom_ids[interaction.data["custom_id"]] or self._selected == interaction.data["custom_id"]:
                button1: discord.ui.Button = discord.utils.get(self.children, custom_id=self._selected)
                button2: discord.ui.Button = discord.utils.get(self.children, custom_id=interaction.data["custom_id"])
                button1.style = discord.ButtonStyle.danger
                button2.style = discord.ButtonStyle.danger
                button2.label = self._custom_ids[interaction.data["custom_id"]]
                self._message = await self._message.edit(view=self)
                await asyncio.sleep(1)
                button1.style = discord.ButtonStyle.secondary
                button2.style = discord.ButtonStyle.secondary
                button1.label = "​"
                button2.label = "​"
                self._message = await self._message.edit(view=self)
                self._selected = None
                self._wrong_matches += 1
                if self.max_wrong_matches and self._wrong_matches >= self.max_wrong_matches:
                    await self.lose()
                return
            button1: discord.ui.Button = discord.utils.get(self.children, custom_id=self._selected)
            button2: discord.ui.Button = discord.utils.get(self.children, custom_id=interaction.data["custom_id"])
            button1.style = discord.ButtonStyle.success
            button2.style = discord.ButtonStyle.success
            button2.label = self._custom_ids[interaction.data["custom_id"]]
            self._message = await self._message.edit(view=self)
            self._found.append(self._custom_ids[interaction.data["custom_id"]])
            self._selected = None
            if len(GAME_EMOJIS) != len(self._found):
                return
            await self.win()

    async def win(self):
        self._selected = None
        for child in self._children:
            if isinstance(child, discord.ui.Button) and child.custom_id != "​":
                child.label = self._custom_ids[child.custom_id]
                child.style = discord.ButtonStyle.success
                if self._custom_ids[child.custom_id] not in self._found:
                    self._found.append(self._custom_ids[child.custom_id])
        if self._tries == 0:
            self._tries = len(self._found)
        self._end = time.monotonic()
        game_time = int(self._end - self._start)
        config = await self.cog.config.guild(self.ctx.guild).all()
        max_prize = config["max_prize"]
        reduction_per_second = config["reduction_per_second"]
        reduction_per_wrong_match = config["reduction_per_wrong_match"]
        member_config = await self.cog.config.member(self.ctx.author).all()
        member_config["score"] += max_prize - (game_time * reduction_per_second) - (self._wrong_matches * reduction_per_wrong_match)
        member_config["wins"] += 1
        member_config["games"] += 1
        await self.cog.config.member(self.ctx.author).set(member_config)
        if self.cog.config.guild(self.ctx.guild).red_economy():
            # https://canary.discord.com/channels/133049272517001216/133251234164375552/1089212578279997521
            final_prize = max_prize - (game_time * reduction_per_second) - (self._wrong_matches * reduction_per_wrong_match)
            try:
                await bank.deposit_credits(self.ctx.author, final_prize)
            except BalanceTooHigh as e:
                await bank.set_balance(self.ctx.author, e.max_balance)
        embed: discord.Embed = discord.Embed(title="Memory Game", color=discord.Color.green())
        embed.set_author(name=self.ctx.author.display_name, icon_url=self.ctx.author.display_avatar)
        embed.description = f"You won in {game_time} seconds, with {self._tries} tries and {self._wrong_matches} wrong matches!"
        self._message = await self._message.edit(embed=embed, view=self)
        await self.on_timeout()
        self.stop()

    async def lose(self):
        self._selected = None
        self._end = time.monotonic()
        member_config = await self.cog.config.member(self.ctx.author).all()
        member_config["games"] += 1
        await self.cog.config.member(self.ctx.author).set(member_config)
        embed: discord.Embed = discord.Embed(title="Memory Game", color=discord.Color.green())
        embed.set_author(name=self.ctx.author.display_name, icon_url=self.ctx.author.display_avatar)
        embed.description = f"You lose, because you tried too many times ({self._tries} tries and {self._wrong_matches} wrong matches)."
        self._message = await self._message.edit(embed=embed, view=self)
        await self.on_timeout()
        self.stop()

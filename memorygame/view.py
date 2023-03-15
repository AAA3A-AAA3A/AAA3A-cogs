from redbot.core import commands  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import asyncio
import random
import time

# GAME_EMOJIS = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l"]
GAME_EMOJIS = ["🏆", "🎯", "🎲", "⚽", "🏀", "🏓", "🥁", "🎮", "🎳", "🎻", "🎖️", "🏹"]

class MemoryGameView(discord.ui.View):
    def __init__(self, cog: commands.Cog) -> None:
        super().__init__(timeout=60 * 10)
        self.ctx: commands.Context = None
        self.cog: commands.Cog = cog

        self._message: discord.Message = None
        self._solution: typing.List[str] = []
        self._solution_display: typing.List[typing.List[str]] = []
        self._custom_ids: typing.Dict[str, str] = {}
        self._found: typing.List[str] = []
        self._selected: typing.Optional[str] = None

        self._start: typing.Optional[float] = None
        self._end: typing.Optional[float] = None

        self._lock: asyncio.Lock = asyncio.Lock()

    async def start(self, ctx: commands.Context) -> None:
        self.ctx: commands.Context = ctx
        self._solution = GAME_EMOJIS.copy() * 2
        random.shuffle(self._solution)
        raw = self._solution.copy()
        raw.insert(12, "​")  # invisible character
        self._solution_display = [
            raw[:5],
            raw[5:10],
            raw[10:15],
            raw[15:20],
            raw[20:25]
        ]
        for _list in self._solution_display:
            for emoji in _list:
                custom_id = self.cog.cogsutils.generate_key(length=5, existing_keys=self._custom_ids)
                self._custom_ids[custom_id] = emoji
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
            if isinstance(child, discord.ui.Button) and child.style != discord.ButtonStyle.url:
                child.label = self._custom_ids[child.custom_id]
                child.disabled = True
        try:
            await self._message.edit(view=self)
        except discord.HTTPException:
            pass

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        async with self._lock:
            if self._selected is None:
                self._selected = interaction.data["custom_id"]
                button: discord.ui.Button = discord.utils.get(self.children, custom_id=self._selected)
                button.label = self._custom_ids[self._selected]
                self._message = await self._message.edit(view=self)
                return
            if self._custom_ids[self._selected] != self._custom_ids[interaction.data["custom_id"]]:
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
                return
            button1: discord.ui.Button = discord.utils.get(self.children, custom_id=self._selected)
            button2: discord.ui.Button = discord.utils.get(self.children, custom_id=interaction.data["custom_id"])
            button1.style = discord.ButtonStyle.success
            button2.style = discord.ButtonStyle.success
            button2.label = self._custom_ids[interaction.data["custom_id"]]
            self._message = await self._message.edit(view=self)
            if len(GAME_EMOJIS) != len(self.found):
                return
            await self.win()

    async def win(self):
        self._selected = None
        for child in self._children:
            if isinstance(child, discord.ui.Button):
                child.style = discord.ButtonStyle.success
        self._end = time.monotonic()
        embed: discord.Embed = discord.Embed(title="Memory Game", color=discord.Color.green())
        embed.set_author(name=self.ctx.author.display_name, icon_url=self.ctx.author.display_avatar)
        embed.description = f"You won in {int(self._end - self._start)} seconds!"
        self._message = await self._message.edit(embed=embed, view=self)
        await self.on_timeout()
        self.stop()
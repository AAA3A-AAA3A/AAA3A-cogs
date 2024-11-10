from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import asyncio
import datetime
import random

_: Translator = Translator("GuessTheCandyGame", __file__)


class GuessTheCandyGameView(discord.ui.View):
    def __init__(
        self,
        cog: commands.Cog,
        difficulty: int = 5,
    ) -> None:
        super().__init__(timeout=180)
        self.ctx: commands.Context = None
        self.cog: commands.Cog = cog
        self.difficulty: int = difficulty

        self.candies: typing.List[str] = []
        self.candy: str = None
        self.start_time: datetime.datetime = None
        self.lock: asyncio.Lock = asyncio.Lock()
        self.is_ended: bool = False

    async def start(self, ctx: commands.Context) -> None:
        self.ctx: commands.Context = ctx
        self.candies = random.sample(list(self.cog.candies.keys()), k=self.difficulty)
        self.candy = random.choice(self.candies)
        embed: discord.Embed = discord.Embed(
            title=_("🎃 Guess The Candy 🎃"),
            description=_("Recognise the correct candy as fast as you can, from the displayed shadow!"),
            color=await self.ctx.embed_color(),
        )
        embed.set_image(url="attachment://shadow.png")
        embed.set_footer(text=self.ctx.guild.name, icon_url=self.ctx.guild.icon)
        self.clear_items()
        for candy in self.candies:
            button: discord.ui.Button = discord.ui.Button(
                label=candy,
                custom_id=candy,
            )
            button.callback = self.callback
            self.add_item(button)
        self._message: discord.Message = await self.ctx.send(
            embed=embed,
            view=self,
            file=discord.File(self.cog.shadows[self.candy], filename="shadow.png"),
        )
        self.cog.views[self._message] = self
        self.start_time: datetime.datetime = datetime.datetime.now(tz=datetime.timezone.utc)

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

    async def callback(self, interaction: discord.Interaction) -> None:
        async with self.lock:
            if self.is_ended:
                return
            guessed = interaction.data["custom_id"]
            if guessed != self.candy:
                await interaction.response.send_message(
                    _("You guessed wrong! Try again!"),
                    ephemeral=True,
                )
                return
            await interaction.response.defer()
            self.is_ended = True
            await self.on_timeout()
            embed: discord.Embed = discord.Embed(
                title=_("🎃 Guess The Candy 🎃"),
                description=_("**Congratulations!** You guessed it was **{candy}** correctly, in **{time} seconds**!").format(
                    candy=self.candy,
                    time=f"{(datetime.datetime.now(tz=datetime.timezone.utc) - self.start_time).total_seconds():.2f}",
                ),
                color=await self.ctx.embed_color(),
            )
            embed.set_image(url="attachment://candy.png")
            await self._message.reply(
                content=interaction.user.mention,
                embed=embed,
                file=discord.File(self.cog.candies[self.candy], filename="candy.png"),
            )

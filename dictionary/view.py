from AAA3A_utils import Menu, CogsUtils  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator  # isort:skip
import discord  # isort:skip

import asyncio
from io import BytesIO

import aiohttp

from .types import Word

_ = Translator("Dictionary", __file__)


class DictionaryView(discord.ui.View):
    def __init__(self, cog: commands.Cog, word: Word) -> None:
        super().__init__(timeout=180)
        self.cog: commands.Cog = cog
        self.ctx: commands.Context = None

        self.word: Word = word

        self._message: discord.Message = None
        self._ready: asyncio.Event = asyncio.Event()

    async def start(self, ctx: commands.Context) -> None:
        self.ctx: commands.Context = ctx
        embed = self.word.to_embed(embed_color=await ctx.embed_color())
        if self.word.source_url:
            self.add_item(
                discord.ui.Button(
                    label=_("View the source"),
                    url=self.word.source_url,
                    style=discord.ButtonStyle.url,
                )
            )
        self._message: discord.Message = await self.ctx.send(embed=embed, view=self)
        self.cog.views[self._message] = self
        await self._ready.wait()
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
            if hasattr(child, "disabled") and not (
                isinstance(child, discord.ui.Button) and child.style == discord.ButtonStyle.url
            ):
                child.disabled = True
        try:
            await self._message.edit(view=self)
        except discord.HTTPException:
            pass
        self._ready.set()

    @discord.ui.button(style=discord.ButtonStyle.danger, emoji="✖️", custom_id="close_page")
    async def close_page(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        try:
            await interaction.response.defer()
        except discord.errors.NotFound:
            pass
        self.stop()
        await CogsUtils.delete_message(self._message)
        self._ready.set()

    @discord.ui.button(
        label="Phonetics", custom_id="show_phonetics", style=discord.ButtonStyle.secondary
    )
    async def show_phonetics(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await interaction.response.defer()
        embed: discord.Embed = discord.Embed(title="Phonetics", color=await self.ctx.embed_color())
        embed.description = "\n".join(
            [
                (
                    f"**•** [**`{phonetic['text'] or 'Name not provided'}`**]({phonetic['audio_url']})"
                    + (
                        f" ({phonetic['audio_url'].split('/')[-1]})"
                        if phonetic["audio_url"]
                        else ""
                    )
                )
                if phonetic["audio_url"]
                else f"**•** **`{phonetic['text']}`**"
                for phonetic in self.word.phonetics
            ]
        )
        files = []
        if self.ctx.bot_permissions.attach_files:
            for phonetic in self.word.phonetics:
                if phonetic["audio_url"] is None:
                    continue
                if phonetic["audio_file"] is not None:
                    files.append(phonetic["audio_file"])
                    continue
                try:
                    async with self.cog._session.get(
                        phonetic["audio_url"], raise_for_status=True
                    ) as r:
                        file = discord.File(
                            BytesIO(await r.read()), filename=phonetic["audio_url"].split("/")[-1]
                        )
                except (aiohttp.InvalidURL, aiohttp.ClientResponseError):
                    continue
                phonetic["audio_file"] = file
                files.append(file)
        await Menu(pages=[{"embed": embed, "files": files}]).start(self.ctx)

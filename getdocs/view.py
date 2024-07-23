from AAA3A_utils import CogsUtils  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import asyncio

from redbot.core.utils.chat_formatting import pagify

from .types import Documentation

_ = Translator("GetDocs", __file__)


class DocsSelect(discord.ui.Select):
    def __init__(self, parent: discord.ui.View, results: typing.List[str]) -> None:
        self._parent: discord.ui.View = parent
        self._options = [discord.SelectOption(label=name, value=name) for name in results]
        super().__init__(
            placeholder=_("Select an option."),
            options=self._options,
            row=0,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        await self._parent._update(self.values[0])


class GetDocsView(discord.ui.View):
    def __init__(self, cog: commands.Cog, query: str, source) -> None:
        super().__init__(timeout=60 * 5)
        self.ctx: commands.Context = None
        self.cog: commands.Cog = cog

        self.query: str = query
        self.source = source
        self.results: typing.List[str] = None

        self._message: discord.Message = None
        self._current: Documentation = None
        self._mode: typing.Literal[
            "documentation", "parameters", "examples", "attributes"
        ] = "documentation"
        self._ready: asyncio.Event = asyncio.Event()

    async def start(self, ctx: commands.Context) -> None:
        self.ctx: commands.Context = ctx
        self.results = await self.source.search(
            self.query, limit=25, exclude_std=True, with_raw_search=True
        )
        if not self.results:
            raise RuntimeError(_("No results found."))
        if self.source.name == "discordapi":
            self.show_parameters.label = "Show fields"
        if self.query != "random" and len(self.results) > 1:
            select = DocsSelect(self, self.results)
            self.add_item(select)
        await self._update(self.results[0])
        await self._ready.wait()
        return self._message

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id not in [self.ctx.author.id] + list(self.ctx.bot.owner_ids):
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

    async def _update(self, name: str) -> None:
        documentation: Documentation = await self.source.get_documentation(name)
        i = 1
        while documentation is None and i < len(self.results):
            documentation = await self.source.get_documentation(self.results[i])
            if documentation is not None:
                break
            i += 1
        if documentation is None:
            raise RuntimeError(_("No results found."))

        self.show_parameters.label = "Show Parameters"
        self.show_examples.label = "Show Examples"
        self.show_attributes.label = "Show Attributes"
        self.show_parameters.disabled = not documentation.parameters and (
            self.source.name != "discordapi" or not documentation.fields
        )
        self.show_examples.disabled = not bool(documentation.examples)
        self.show_attributes.disabled = not bool(documentation.attributes)

        if back_button := discord.utils.get(self.children, custom_id="back_button"):
            self.remove_item(back_button)
        if next_button := discord.utils.get(self.children, custom_id="next_button"):
            self.remove_item(next_button)

        self._current = documentation
        embed = documentation.to_embed(embed_color=await self.ctx.embed_color())
        content = None
        # if (
        #     self.source._docs_caching_task is not None
        #     and self.source._docs_caching_task.currently_running
        # ):
        #     content = "⚠️ The documentation cache is not yet fully built, building now."
        if self._message is None:
            self._message: discord.Message = await self.ctx.send(
                content=content, embed=embed, view=self
            )
            self.cog.views[self._message] = self
        else:
            self._message: discord.Message = await self._message.edit(
                content=content, embed=embed, view=self
            )
        self._mode = "documentation"

    @discord.ui.button(label="Show Parameters", custom_id="show_parameters", row=1)
    async def show_parameters(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        if not self._current:
            return await interaction.response.send_message(
                "Current variable is somehow empty, so attributes aren't loaded.",
                ephemeral=True,
            )
        if not self._current.parameters and not (
            self.source.name == "discordapi" and self._current.fields
        ):
            return await interaction.response.send_message(
                "There are no attributes available for this option.",
                ephemeral=True,
            )
        await interaction.response.defer()
        if (
            self._mode == "parameters"
        ):  # back / self._message.embeds[0].title.startswith("Parameters")
            await self._update(self._current.name)
            return
        else:
            self.show_parameters.label = "Hide Parameters"
            self.show_examples.label = "Show Examples"
            self.show_attributes.label = "Show Attributes"

        # Attributes pagination
        back_button: discord.ui.Button = discord.utils.get(self.children, custom_id="back_button")
        if back_button:
            self.remove_item(back_button)
        next_button: discord.ui.Button = discord.utils.get(self.children, custom_id="next_button")
        if next_button:
            self.remove_item(next_button)

        if self.source.name == "discordapi":
            description = ""
            for name, value in self._current.fields.items():
                description += f"\n\n**{name}:**\n{value}"
            embeds = []
            pages = list(pagify(description, page_length=4000, delims=["\n• ", "\n**"]))
            if len(pages) == 1:
                embed = discord.Embed(
                    title="Fields:",
                    description=description,
                    color=await self.ctx.embed_color(),
                )
                embeds.append(embed)
            else:
                embeds = []
                for i, page in enumerate(pages, start=1):
                    embed = discord.Embed(
                        title=f"Fields {i}:",
                        description=page,
                        color=await self.ctx.embed_color(),
                    )
                    embeds.append(embed)
        elif isinstance(self._current.parameters, str):
            description = self._current.parameters
            embeds = []
            pages = list(pagify(description, page_length=4000))
            if len(pages) == 1:
                embed = discord.Embed(
                    title="Parameters:",
                    description=description,
                    color=await self.ctx.embed_color(),
                )
                embeds.append(embed)
            else:
                embeds = []
                for i, page in enumerate(pages, start=1):
                    embed = discord.Embed(
                        title=f"Parameters {i}:",
                        description=page,
                        color=await self.ctx.embed_color(),
                    )
                    embeds.append(embed)
        else:
            embeds = self._current.parameters.to_embeds(embed_color=await self.ctx.embed_color())

        if len(embeds) == 1:
            self._message: discord.Message = await self._message.edit(embed=embeds[0], view=self)
        else:

            async def _back_button(interaction: discord.Interaction):
                await interaction.response.defer()
                current = discord.utils.get(embeds, title=self._message.embeds[0].title)
                current = embeds.index(current)
                current_embed = embeds[current - 1]
                self._message: discord.Message = await self._message.edit(embed=current_embed)

            async def _next_button(interaction: discord.Interaction):
                await interaction.response.defer()
                current = discord.utils.get(embeds, title=self._message.embeds[0].title)
                current = embeds.index(current)
                try:
                    current_embed = embeds[current + 1]
                except IndexError:
                    current_embed = embeds[0]
                self._message: discord.Message = await self._message.edit(embed=current_embed)

            back_button = discord.ui.Button(emoji="◀️", custom_id="back_button", row=2)
            back_button.callback = _back_button
            self.add_item(back_button)
            next_button = discord.ui.Button(emoji="▶️", custom_id="next_button", row=2)
            next_button.callback = _next_button
            self.add_item(next_button)
            self._message: discord.Message = await self._message.edit(embed=embeds[0], view=self)
        self._mode = "parameters"

    @discord.ui.button(label="Show Examples", custom_id="show_examples", row=1)
    async def show_examples(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        if not self._current:
            return await interaction.response.send_message(
                "Current variable is somehow empty, so examples aren't loaded.",
                ephemeral=True,
            )
        if not self._current.examples:
            return await interaction.response.send_message(
                "There are no examples available for this option.",
                ephemeral=True,
            )
        await interaction.response.defer()
        if (
            self._mode == "examples"
        ):  # back / self._message.embeds[0].title.startswith("Example") and self._message.embeds[0].title.endswith(":")
            await self._update(self._current.name)
            return
        else:
            self.show_parameters.label = "Show Parameters"
            self.show_examples.label = "Hide Examples"
            self.show_attributes.label = "Show Attributes"

        if back_button := discord.utils.get(self.children, custom_id="back_button"):
            self.remove_item(back_button)
        if next_button := discord.utils.get(self.children, custom_id="next_button"):
            self.remove_item(next_button)

        embeds = self._current.examples.to_embeds(
            self.ctx, embed_color=await self.ctx.embed_color()
        )
        self._message: discord.Message = await self._message.edit(embeds=embeds[:10], view=self)
        self._mode = "examples"

    @discord.ui.button(label="Show Attributes", custom_id="show_attributes", row=1)
    async def show_attributes(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        if not self._current:
            return await interaction.response.send_message(
                "Current variable is somehow empty, so attributes aren't loaded.",
                ephemeral=True,
            )
        if not self._current.attributes:
            return await interaction.response.send_message(
                "There are no attributes available for this option.",
                ephemeral=True,
            )
        await interaction.response.defer()
        if (
            self._mode == "attributes"
        ):  # back / self._message.embeds[0].title.startswith(tuple([x.title() for x in self._current.attributes.__dataclass_fields__.keys()]))
            await self._update(self._current.name)
            return
        else:
            self.show_parameters.label = "Show Parameters"
            self.show_examples.label = "Show Examples"
            self.show_attributes.label = "Hide Attributes"

        # Attributes pagination
        if back_button := discord.utils.get(self.children, custom_id="back_button"):
            self.remove_item(back_button)
        if next_button := discord.utils.get(self.children, custom_id="next_button"):
            self.remove_item(next_button)

        embeds = self._current.attributes.to_embeds(embed_color=await self.ctx.embed_color())
        if sum(len(embed) for embed in embeds) > 6000:

            async def _back_button(interaction: discord.Interaction):
                await interaction.response.defer()
                current = discord.utils.get(embeds, title=self._message.embeds[0].title)
                current = embeds.index(current)
                current_embed = embeds[current - 1]
                self._message: discord.Message = await self._message.edit(embed=current_embed)

            async def _next_button(interaction: discord.Interaction):
                await interaction.response.defer()
                current = discord.utils.get(embeds, title=self._message.embeds[0].title)
                current = embeds.index(current)
                try:
                    current_embed = embeds[current + 1]
                except IndexError:
                    current_embed = embeds[0]
                self._message: discord.Message = await self._message.edit(embed=current_embed)

            back_button = discord.ui.Button(emoji="◀️", custom_id="back_button", row=2)
            back_button.callback = _back_button
            self.add_item(back_button)
            next_button = discord.ui.Button(emoji="▶️", custom_id="next_button", row=2)
            next_button.callback = _next_button
            self.add_item(next_button)
            self._message: discord.Message = await self._message.edit(embed=embeds[0], view=self)
        else:
            self._message: discord.Message = await self._message.edit(embeds=embeds, view=self)
        self._mode = "attributes"

    @discord.ui.button(style=discord.ButtonStyle.danger, emoji="✖️", custom_id="close_page", row=1)
    async def close_page(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        try:
            await interaction.response.defer()
        except discord.errors.NotFound:
            pass
        self.stop()
        await CogsUtils.delete_message(self._message)

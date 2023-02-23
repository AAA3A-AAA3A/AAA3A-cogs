from redbot.core import commands  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

from .types import SearchResults, Documentation


class DocsSelectOption(discord.SelectOption):
    def __init__(self, original_name: str, *args, **kwargs) -> None:
        self.original_name: str = original_name
        super().__init__(*args, **kwargs)


class DocsSelect(discord.ui.Select):
    def __init__(self, parent: discord.ui.View, results: SearchResults) -> None:
        self._parent: discord.ui.View = parent
        self.texts: typing.Dict[str, typing.Tuple[str, str]] = {}
        for name, original_name, url, _ in results.results:
            if name not in self.texts.keys():
                self.texts[name] = url, original_name
        self._options = [
            DocsSelectOption(label=name, original_name=original_name)
            for name, (_, original_name) in self.texts.items()
        ]
        super().__init__(
            placeholder="Select an option.",
            options=self._options,
            row=0,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        option = discord.utils.get(self._options, label=self.values[0])
        await self._parent._callback(interaction, option)


class DocsView(discord.ui.View):
    def __init__(
        self,
        ctx: commands.Context,
        query: str,
        source,
    ) -> None:
        super().__init__(timeout=60 * 5)
        self.ctx: commands.Context = ctx
        self.query: str = query
        self.source = source

        self._message: discord.Message = None
        self._current: Documentation = None
        self._mode: typing.Literal["documentation", "parameters", "examples", "attributes"] = "documentation"

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id not in [self.ctx.author.id] + list(self.ctx.bot.owner_ids):
            await interaction.response.send_message(
                "You are not allowed to use this interaction.", ephemeral=True
            )
            return False
        return True

    async def on_timeout(self) -> None:
        for child in self.children:
            if not child.style == discord.ButtonStyle.url:
                child.disabled = True
        try:
            await self._message.edit(view=self)
        except discord.HTTPException:
            pass

    async def _update(self, name: str) -> None:
        doc = None
        i = 0
        doc: Documentation = self.source.get_documentation(name)
        while doc is None and i < len(self.results.results):
            doc = self.source.get_documentation(self.results.results[i][0])
            if doc is not None:
                break
            i += 1
        if doc is None:
            raise RuntimeError("No results found.")
        parameters_button: discord.ui.Button = discord.utils.get(
            self.children, custom_id="show_parameters"
        )
        if parameters_button:
            parameters_button.disabled = not doc.parameters
        examples_button: discord.ui.Button = discord.utils.get(
            self.children, custom_id="show_examples"
        )
        if examples_button:
            examples_button.disabled = not bool(doc.examples)
        attributes_button: discord.ui.Button = discord.utils.get(
            self.children, custom_id="show_attributes"
        )
        if attributes_button:
            attributes_button.disabled = not bool(doc.attributes)

        # Attributes pagination
        back_button: discord.ui.Button = discord.utils.get(
            self.children, custom_id="back_button"
        )
        if back_button:
            self.remove_item(back_button)
        next_button: discord.ui.Button = discord.utils.get(
            self.children, custom_id="next_button"
        )
        if next_button:
            self.remove_item(next_button)

        self._current = doc
        embed = doc.to_embed()
        content = None
        if self.source._docs_caching_task is not None and self.source._docs_caching_task.currently_running:
            content = "⚠️ The documentation cache is not yet fully built, building now."
        if self._message is None:
            self._message = await self.ctx.send(content=content, embed=embed, view=self)
        else:
            self._message = await self._message.edit(content=content, embed=embed)
        self._mode = "documentation"

    async def _callback(
        self, interaction: discord.Interaction, option: discord.SelectOption
    ) -> None:
        await interaction.response.defer()
        await self._update(option.original_name)

    @discord.ui.button(style=discord.ButtonStyle.grey, label="Show Parameters", custom_id="show_parameters", row=1)
    async def show_parameters(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not self._current:
            return await interaction.response.send_message(
                "Current variable is somehow empty, so attributes aren't loaded.",
                ephemeral=True,
            )
        if not self._current.parameters:
            return await interaction.response.send_message(
                "There are no attributes available for this option.",
                ephemeral=True,
            )
        await interaction.response.defer()
        if self._mode == "parameters":  # back / self._message.embeds[0].title.startswith("Parameters")
            await self._update(self._current.name)
            return

        # Attributes pagination
        back_button: discord.ui.Button = discord.utils.get(
            self.children, custom_id="back_button"
        )
        if back_button:
            self.remove_item(back_button)
        next_button: discord.ui.Button = discord.utils.get(
            self.children, custom_id="next_button"
        )
        if next_button:
            self.remove_item(next_button)

        embeds = self._current.parameters.to_embeds()
        if len(embeds) == 1:
            self._message = await self._message.edit(embed=embeds[0])
        else:
            async def _back_button(interaction: discord.Interaction):
                await interaction.response.defer()
                current = discord.utils.get(embeds, title=self._message.embeds[0].title)
                current_embed = embeds[current - 1]
                self._message = await self._message.edit(embed=current_embed)
            async def _next_button(interaction: discord.Interaction):
                await interaction.response.defer()
                current = discord.utils.get(embeds, title=self._message.embeds[0].title)
                try:
                    current_embed = embeds[current + 1]
                except IndexError:
                    current_embed = embeds[0]
                self._message = await self._message.edit(embed=current_embed)
            back_button = discord.ui.Button(
                emoji="◀️",
                custom_id="back_button",
                style=discord.ButtonStyle.grey,
                row=2,
            )
            back_button.callback = _back_button
            self.add_item(back_button)
            next_button = discord.ui.Button(
                emoji="▶️",
                custom_id="next_button",
                style=discord.ButtonStyle.grey,
                row=2,
            )
            next_button.callback = _next_button
            self.add_item(next_button)
            self._message = await self._message.edit(embed=embeds[0], view=self)
            self._mode = "parameters"

    @discord.ui.button(style=discord.ButtonStyle.grey, label="Show Examples", custom_id="show_examples", row=1)
    async def show_examples(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
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
        if self._mode == "examples":  # back / self._message.embeds[0].title.startswith("Example") and self._message.embeds[0].title.endswith(":")
            await self._update(self._current.name)
            return

        # Attributes pagination
        back_button: discord.ui.Button = discord.utils.get(
            self.children, custom_id="back_button"
        )
        if back_button:
            self.remove_item(back_button)
        next_button: discord.ui.Button = discord.utils.get(
            self.children, custom_id="next_button"
        )
        if next_button:
            self.remove_item(next_button)

        embeds = self._current.examples.to_embeds()
        self._message = await self._message.edit(embeds=embeds, view=self)
        self._mode = "examples"

    @discord.ui.button(style=discord.ButtonStyle.grey, label="Show Attributes", custom_id="show_attributes", row=1)
    async def show_attributes(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
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
        if self._mode == "attributes":  # back / self._message.embeds[0].title.startswith(tuple([x.title() for x in self._current.attributes.__dataclass_fields__.keys()]))
            await self._update(self._current.name)
            return

        # Attributes pagination
        back_button: discord.ui.Button = discord.utils.get(
            self.children, custom_id="back_button"
        )
        if back_button:
            self.remove_item(back_button)
        next_button: discord.ui.Button = discord.utils.get(
            self.children, custom_id="next_button"
        )
        if next_button:
            self.remove_item(next_button)

        embeds = self._current.attributes.to_embeds()
        if sum(len(embed) for embed in embeds) > 6000:
            async def _back_button(interaction: discord.Interaction):
                await interaction.response.defer()
                current = discord.utils.get(embeds, title=self._message.embeds[0].title)
                current = embeds.index(current)
                current_embed = embeds[current - 1]
                self._message = await self._message.edit(embed=current_embed)
            async def _next_button(interaction: discord.Interaction):
                await interaction.response.defer()
                current = discord.utils.get(embeds, title=self._message.embeds[0].title)
                current = embeds.index(current)
                try:
                    current_embed = embeds[current + 1]
                except IndexError:
                    current_embed = embeds[0]
                self._message = await self._message.edit(embed=current_embed)
            back_button = discord.ui.Button(
                emoji="◀️",
                custom_id="back_button",
                style=discord.ButtonStyle.grey,
                row=2,
            )
            back_button.callback = _back_button
            self.add_item(back_button)
            next_button = discord.ui.Button(
                emoji="▶️",
                custom_id="next_button",
                style=discord.ButtonStyle.grey,
                row=2,
            )
            next_button.callback = _next_button
            self.add_item(next_button)
            self._message = await self._message.edit(embed=embeds[0], view=self)
        else:
            self._message = await self._message.edit(embeds=embeds)
        self._mode = "attributes"

    @discord.ui.button(style=discord.ButtonStyle.grey, emoji="❌", custom_id="close_page", row=2)
    async def close_page(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        try:
            await interaction.response.defer()
        except discord.errors.NotFound:
            pass
        self.stop()
        try:
            await self._message.delete()
        except discord.HTTPException:
            pass

    async def start(self) -> None:
        results = await self.source.search(self.query, limit=25, exclude_std=True)
        self.results = results
        if not results or not results.results:
            raise RuntimeError("No results found.")
        select = DocsSelect(self, results)
        self.add_item(select)
        await self._update(results.results[0][1])

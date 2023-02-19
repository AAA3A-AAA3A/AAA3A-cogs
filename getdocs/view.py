from redbot.core import commands  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

from redbot.core.utils.chat_formatting import box, pagify

from .types import SearchResults


class DocsSelectOption(discord.SelectOption):
    def __init__(self, original_name: str, *args, **kwargs) -> None:
        self.original_name = original_name
        super().__init__(*args, **kwargs)


class DocsSelect(discord.ui.Select):
    def __init__(self, parent: discord.ui.View, results: SearchResults):
        self._parent = parent
        self.texts = {}
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

    async def callback(self, interaction: discord.Interaction):
        option = discord.utils.get(self._options, label=self.values[0])
        await self._parent._callback(interaction, option)


class DocsView(discord.ui.View):
    def __init__(
        self,
        ctx: commands.Context,
        query: str,
        source,
    ):
        super().__init__(timeout=60 * 5)
        self.ctx = ctx
        self.query = query
        self.source = source
        self._message: discord.Message = None
        self._current = None

    async def _callback(
        self, interaction: discord.Interaction, option: discord.SelectOption
    ):
        await interaction.response.defer()
        await self._update(option.original_name)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id not in [self.ctx.author.id] + list(self.ctx.bot.owner_ids):
            await interaction.response.send_message(
                "You are not allowed to use this interaction.", ephemeral=True
            )
            return False
        return True

    async def on_timeout(self) -> None:
        for child in self.children:
            child.disabled = True
        await self._message.edit(view=self)

    async def _update(self, name: str):
        doc = None
        i = 0
        doc = self.source.get_documentation(name)
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
            parameters_button.disabled = "Parameters" not in doc.fields
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

    async def show_parameters(self, interaction: discord.Interaction) -> None:
        if not self._current:
            return await interaction.response.send_message(
                "Current variable is somehow empty, so attributes aren't loaded.",
                ephemeral=True,
            )
        if "Parameters" not in self._current.fields:
            return await interaction.response.send_message(
                "There are no attributes available for this option.",
                ephemeral=True,
            )
        await interaction.response.defer()
        if self._message.embeds[0].title.startswith("Parameters"):  # back
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

        description = self._current.fields["Parameters"]
        pages = list(pagify(description, page_length=4000, delims=["\n• "]))
        if len(pages) == 1:
            embed = discord.Embed(
                    title="Parameters:",
                    description=description,
                    color=discord.Color.green(),
            )
            self._message = await self._message.edit(embed=embed)
        else:
            embeds = []
            for i, page in enumerate(pages, start=1):
                embed = discord.Embed(
                        title=f"Parameters {i}:",
                        description=page,
                        color=discord.Color.green(),
                )
                embeds.append(embed)
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

    async def show_examples(self, interaction: discord.Interaction) -> None:
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
        if self._message.embeds[0].title.startswith("Example") and self._message.embeds[0].title.endswith(":"):  # back
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

        embeds = []
        for i, example in enumerate(self._current.examples, start=1):
            embed = discord.Embed(
                title=f"Example {i}:" if len(self._current.examples) > 1 else "Example:",
                description=box(example, lang="py"),
                color=discord.Color.green(),
            )
            embeds.append(embed)
        self._message = await self._message.edit(embeds=embeds, view=self)

    async def show_attributes(self, interaction: discord.Interaction) -> None:
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
        if self._message.embeds[0].title.startswith(tuple([x.title() for x in self._current.attributes.keys()])):  # back
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

        def format_attribute(name: str, role: str, url: str, description: str, show_description: typing.Optional[bool] = True):
            return "• " + (f"{role} " if role is not None else "") + f"[{name}]({url})" + (f"\n> {description}" if description is not None and show_description else "")
        embeds = []
        for name, attributes in self._current.attributes.items():
            formatted_attributes = []
            for attribute in attributes:
                formatted_attributes.append(format_attribute(attribute, attributes[attribute]["role"], attributes[attribute]["url"], attributes[attribute]["description"]))
            description = "\n".join(formatted_attributes)
            pages = list(pagify(description, page_length=4000, delims=["\n• "]))
            if len(pages) == 1:
                embed = discord.Embed(
                    title=name.title() + ":",
                    description=description,
                    color=discord.Color.green(),
                )
                embeds.append(embed)
            else:
                for i, page in enumerate(pages, start=1):
                    embed = discord.Embed(
                        title=name.title() + f" {i}:",
                        description=page,
                        color=discord.Color.green(),
                    )
                    embeds.append(embed)
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

    async def close_page(self, interaction: discord.Interaction) -> None:
        try:
            await interaction.response.defer()
        except discord.errors.NotFound:
            pass
        self.stop()
        try:
            await self._message.delete()
        except discord.HTTPException:
            pass

    async def start(self):
        results = await self.source.search(self.query, limit=25, exclude_std=True)
        self.results = results
        if not results or not results.results:
            raise RuntimeError("No results found.")
        select = DocsSelect(self, results)
        self.add_item(select)
        parameters_button = discord.ui.Button(
            label="Show Parameters", custom_id="show_parameters", style=discord.ButtonStyle.grey, row=1
        )
        parameters_button.callback = self.show_parameters
        self.add_item(parameters_button)
        example_button = discord.ui.Button(
            label="Show Examples", custom_id="show_examples", style=discord.ButtonStyle.grey, row=1
        )
        example_button.callback = self.show_examples
        self.add_item(example_button)
        attributes_button = discord.ui.Button(
            label="Show Attributes",
            custom_id="show_attributes",
            style=discord.ButtonStyle.grey,
            row=1,
        )
        attributes_button.callback = self.show_attributes
        self.add_item(attributes_button)
        close_button = discord.ui.Button(
            emoji="❌",
            custom_id="close_page",
            style=discord.ButtonStyle.grey,
            row=2,
        )
        close_button.callback = self.close_page
        self.add_item(close_button)
        await self._update(results.results[0][1])

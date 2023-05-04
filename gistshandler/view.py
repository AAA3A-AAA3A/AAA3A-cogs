from AAA3A_utils import Menu  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import asyncio
import datetime
import gists

from redbot.core.utils.chat_formatting import box

_ = Translator("GistsHandler", __file__)


class FilesSelect(discord.ui.Select):
    def __init__(self, parent: discord.ui.View, files: typing.List[gists.File], current_file: typing.Optional[gists.File] = None) -> None:
        self._parent: discord.ui.View = parent
        self._options = [
            discord.SelectOption(label=file.name, value=file.name, default=file == current_file)
            for file in files[:25]
        ]
        super().__init__(
            placeholder="Select a file.",
            options=self._options,
            row=1,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        option = discord.utils.get(self._options, value=self.values[0])
        await self._parent._callback(interaction, option)


class CreateGistModal(discord.ui.Modal):
    def __init__(self, parent: discord.ui.View) -> None:
        super().__init__(title="Create new Gist")
        self._parent: discord.ui.View = parent
        self.description: discord.ui.TextInput = discord.ui.TextInput(
            label="Description",
            placeholder="Description of the gist",
            default=None,
            style=discord.TextStyle.short,
            custom_id="description",
            required=False,
        )
        self.add_item(self.description)
        self.filename: discord.ui.TextInput = discord.ui.TextInput(
            label="Create a new file",
            placeholder="File name",
            default="output.py",
            style=discord.TextStyle.short,
            custom_id="new_file_name",
            required=True,
        )
        self.add_item(self.filename)
        self.content: discord.ui.TextInput = discord.ui.TextInput(
            label="Content",
            placeholder="File content",
            default=None,
            style=discord.TextStyle.paragraph,
            custom_id="new_file_content",
            required=True,
        )
        self.add_item(self.content)
        self.public: discord.ui.TextInput = discord.ui.TextInput(
            label="Public",
            placeholder="Public state",
            default="False",
            style=discord.TextStyle.short,
            custom_id="public_state",
            required=True,
        )
        self.add_item(self.public)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        description = self.description.value
        filename = self.filename.value
        content = self.content.value
        file = gists.File(name=filename, content=content)
        lowered = self.public.value.lower()
        if lowered in ("yes", "y", "true", "t", "1", "enable", "on"):
            public = True
        elif lowered in ("no", "n", "false", "f", "0", "disable", "off"):
            public = False
        else:
            await interaction.response.send_message(_("{public.value} is not a recognised boolean option.").format(public=self.public), ephemeral=True)
            return
        try:
            gist = await self._parent.cog.gists_client.create_gist(files=[file], description=description, public=public)
        except gists.AuthorizationFailure:
            await interaction.response.send_message(_("GitHub token is invalid or expired."))
            return
        self._parent.gist = gist
        self._parent.file = file
        self._parent._deleted: bool = False
        self._parent._deleted_at: datetime.datetime = None
        await self._parent._update()
        await interaction.response.send_message(_("Gist `{gist.id}` created.").format(gist=gist), ephemeral=True)


class EditGistModal(discord.ui.Modal):
    def __init__(self, parent: discord.ui.View, gist: gists.Gist, file: gists.File) -> None:
        super().__init__(title="Edit Gist")
        self._parent: discord.ui.View = parent
        self.gist: gists.Gist = gist
        self.file: gists.File = file
        self.description: discord.ui.TextInput = discord.ui.TextInput(
            label="Description",
            placeholder="Description of the gist",
            default=self.gist.description,
            style=discord.TextStyle.short,
            custom_id="description",
            required=False,
        )
        self.add_item(self.description)

        self.old_file_filename: discord.ui.TextInput = discord.ui.TextInput(
            label=f"Edit {self.file.name[:33]}'s name",
            placeholder="Edit File name",
            default=self.file.name,
            style=discord.TextStyle.short,
            custom_id="old_file_name",
            required=True,
        )
        self.add_item(self.old_file_filename)
        self.old_file_content: discord.ui.TextInput = discord.ui.TextInput(
            label=f"Edit {self.file.name[:30]}'s content",
            placeholder="Edit File content "
            + (
                "(Leave empty to delete the file)"
                if len(self.gist.files) > 1
                else "(Cannot delete last file)"
            ),
            default=self.file.content[:4000],
            style=discord.TextStyle.paragraph,
            custom_id="old_file_content",
            required=len(self.gist.files) <= 1,
        )
        self.add_item(self.old_file_content)

        self.new_file_filename: discord.ui.TextInput = discord.ui.TextInput(
            label="Create a new file",
            placeholder="New File name",
            default=None,
            style=discord.TextStyle.short,
            custom_id="new_file_name",
            required=False,
        )
        self.add_item(self.new_file_filename)
        self.new_file_content: discord.ui.TextInput = discord.ui.TextInput(
            label="Content",
            placeholder="New File content",
            default=None,
            style=discord.TextStyle.paragraph,
            custom_id="new_file_content",
            required=False,
        )
        self.add_item(self.new_file_content)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        description = self.description.value
        old_file_old_name = self.file.name
        old_file_name = self.old_file_filename.value
        old_file_content = self.old_file_content.value
        if old_file_content == self.file.content[:4000]:
            old_file_content = self.file.content
        files = self.gist.files
        files.remove(self.file)
        if old_file_content != "":
            old_file = gists.File(name=old_file_old_name, new_name=old_file_name, content=old_file_content)
            files.append(old_file)
        else:
            old_file = None

        new_file_name = self.new_file_filename.value
        new_file_content = self.new_file_content.value
        if new_file_name != "" and new_file_content != "":
            new_file = gists.File(name=new_file_name, content=new_file_content)
            files.append(new_file)
        else:
            new_file = None
        try:
            await self.gist.edit(files=files, description=description)
        except gists.AuthorizationFailure:
            await interaction.response.send_message(_("GitHub token is invalid or expired."))
            return
        except gists.NotFound:
            await interaction.response.send_message(_("You're not allowed to edit this gist."), ephemeral=True)
            return
        self._parent.file = old_file or new_file
        await self._parent._update()
        await interaction.response.send_message(_("Gist `{gist.id}` updated.").format(gist=self.gist), ephemeral=True)


class GistsHandlerView(discord.ui.View):
    def __init__(self, cog: commands.Cog, gist: typing.Optional[gists.Gist] = None, file: typing.Optional[gists.File] = None) -> None:
        super().__init__()
        self.cog: commands.Cog = cog
        self.ctx: commands.Context = None

        self.gist: typing.Optional[gists.Gist] = gist
        self.file: typing.Optional[gists.File] = file

        self._message: discord.Message = None
        self._embed: discord.Embed = None

        self._deleted: bool = False
        self._deleted_at: datetime.datetime = None
        self._files_select: FilesSelect = None
        self._button_url: discord.ui.Button = None
        self._ready: asyncio.Event = asyncio.Event()

    async def start(self, ctx: commands.Context) -> None:
        self.ctx: commands.Context = ctx
        if self.gist is not None and self.file is None:
            self.file = self.gist.files[0]
        await self._update()
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
            if hasattr(child, "disabled") and not (isinstance(child, discord.ui.Button) and child.style == discord.ButtonStyle.url):
                child.disabled = True
        try:
            await self._message.edit(view=self)
        except discord.HTTPException:
            pass
        self._ready.set()

    async def _update(self) -> None:
        self._embed: discord.Embed = await self.get_embed(self.ctx, gist=self.gist, file=self.file)
        if self.gist is None:
            self.edit_gist.disabled = True
            self.delete_gist.disabled = True
            if self._files_select is not None:
                self.remove_item(self._files_select)
                self._files_select = None
            if self._button_url is not None:
                self.remove_item(self._button_url)
                self._button_url = None
        else:
            self.edit_gist.disabled = False
            self.delete_gist.disabled = False
            if self._files_select is not None:
                self.remove_item(self._files_select)
            self._files_select: FilesSelect = FilesSelect(parent=self, files=self.gist.files, current_file=self.file)
            self.add_item(self._files_select)
            if self._button_url is not None:
                self.remove_item(self._button_url)
            self._button_url: discord.ui.Button = discord.ui.Button(label="View on GitHub", url=self.gist.url, style=discord.ButtonStyle.url)
            self.add_item(self._button_url)
        if self._message is None:
            self._message: discord.Message = await self.ctx.send(embed=self._embed, view=self)
        else:
            self._message: discord.Message = await self._message.edit(embed=self._embed, view=self)

    async def get_embed(self, ctx: commands.Context, gist: typing.Optional[gists.Gist] = None, file: typing.Optional[gists.File] = None) -> discord.Embed:
        embed: discord.Embed = discord.Embed(color=await ctx.embed_color())
        if gist is None:
            embed.title = "Gist not provided."
            embed.description = None
        else:
            embed.title = f"[DELETED] {gist.id}" if self._deleted else gist.id
            embed.url = gist.url
            embed.description = gist.description
            embed.set_author(name=self.gist.owner["login"], url=self.gist.owner["html_url"], icon_url=self.gist.owner["avatar_url"])
            updated_at = f"{discord.utils.format_dt(gist.updated_at)} ({discord.utils.format_dt(gist.updated_at, style='R')})"
            created_at = f"{discord.utils.format_dt(gist.created_at)} ({discord.utils.format_dt(gist.created_at, style='R')})"
            if self._deleted_at is not None:
                deleted_at = f"{discord.utils.format_dt(self._deleted_at)} ({discord.utils.format_dt(self._deleted_at, style='R')})"
            embed.add_field(
                name="Updates:",
                value=f"Created at: {created_at}\nLast updated at: {updated_at}" + (f"\nDeleted at: {deleted_at}" if self._deleted_at is not None else ""),
                inline=True,
            )
            embed.add_field(name="Public State:", value=str(gist.public), inline=True)
            embed.url = f"{gist.url}#file-{file.name.replace('.', '-').replace('/', '-')}"
            length = len(f"```{file.name.split('.')[-1]}\n\n```") if file.name.split(".")[-1] != "md" else 0
            content = file.content.replace("`", "`\u200b")
            content = (f"{content[:1024 - 4 - length]}\n..." if len(content) > (1024 - length) else content)
            if file.name.split(".")[-1] != "md":
                content = box(content, lang=file.name.split(".")[-1])
            embed.add_field(name=file.name, value=content, inline=False)
        return embed

    @discord.ui.button(style=discord.ButtonStyle.danger, emoji="✖️", custom_id="close_page")
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
        self._ready.set()

    @discord.ui.button(label="Create new Gist", style=discord.ButtonStyle.success)
    async def create_gist(self, interaction: discord.Interaction, button: discord.Button) -> None:
        modal = CreateGistModal(self)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="View File Content", style=discord.ButtonStyle.secondary)
    async def view_content(self, interaction: discord.Interaction, button: discord.Button) -> None:
        await interaction.response.defer()
        if self.file.name.split(".")[-1] != "md":
            await Menu(pages=self.file.content, lang=self.file.name.split(".")[-1]).start(self.ctx)
        else:
            await Menu(pages=self.file.content).start(self.ctx)

    @discord.ui.button(label="Edit Gist/File", style=discord.ButtonStyle.primary)
    async def edit_gist(self, interaction: discord.Interaction, button: discord.Button) -> None:
        modal = EditGistModal(self, gist=self.gist, file=self.file)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Delete Gist", style=discord.ButtonStyle.danger)
    async def delete_gist(self, interaction: discord.Interaction, button: discord.Button) -> None:
        try:
            await self.gist.delete()
        except gists.AuthorizationFailure:
            await interaction.response.send_message(_("GitHub token is invalid or expired."))
            return
        except gists.NotFound:
            await interaction.response.send_message(_("You're not allowed to delete this gist."), ephemeral=True)
            return
        self._deleted: bool = True
        self._deleted_at: datetime.datetime = datetime.datetime.now(
            datetime.timezone.utc
        )
        await interaction.response.send_message(_("Gist `{gist.id}` deleted.").format(gist=self.gist), ephemeral=True)
        await self._update()

    async def _callback(
        self, interaction: discord.Interaction, option: discord.SelectOption
    ) -> None:
        await interaction.response.defer()
        self.file: gists.File = discord.utils.get(self.gist.files, name=option.value)
        await self._update()

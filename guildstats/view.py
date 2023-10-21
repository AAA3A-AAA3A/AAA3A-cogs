from AAA3A_utils import CogsUtils  # isort:skip
from redbot.core import commands  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import asyncio


class GuildStatsView(discord.ui.View):
    def __init__(
        self,
        cog: commands.Cog,
        _object: typing.Union[
            discord.Member,
            discord.Role,
            discord.Guild,
            typing.Tuple[
                discord.Guild,
                typing.Union[
                    typing.Literal["messages", "voice", "activities"],
                    typing.Tuple[
                        typing.Literal["top"],
                        typing.Literal["messages", "voice"],
                        typing.Literal["members", "channels"],
                    ],
                    typing.Tuple[typing.Literal["activity"], str],
                ],
            ],
            discord.CategoryChannel,
            discord.TextChannel,
            discord.VoiceChannel,
        ],
        members_type: typing.Literal["humans", "bots", "both"] = "humans",
        show_graphic_in_main: bool = False,
        graphic_mode: bool = False,
    ) -> None:
        super().__init__(timeout=60 * 60)
        self.cog: commands.Cog = cog
        self.ctx: commands.Context = None

        self._object: typing.Union[
            discord.Member,
            discord.Role,
            discord.Guild,
            typing.Tuple[
                discord.Guild,
                typing.Union[
                    typing.Literal["messages", "voice", "activities"],
                    typing.Tuple[
                        typing.Literal["top"],
                        typing.Literal["messages", "voice"],
                        typing.Literal["members", "channels"],
                    ],
                    typing.Tuple[typing.Literal["activity"], str],
                ],
            ],
            discord.CategoryChannel,
            discord.TextChannel,
            discord.VoiceChannel,
        ] = _object
        self.members_type: typing.Literal["humans", "bots", "both"] = members_type
        self.show_graphic_in_main: bool = show_graphic_in_main
        self.graphic_mode: bool = graphic_mode

        self._message: discord.Message = None
        self._ready: asyncio.Event = asyncio.Event()

    async def start(self, ctx: commands.Context) -> None:
        self.ctx: commands.Context = ctx
        if self.graphic_mode:
            file: discord.File = await self.cog.generate_graphic(
                self._object, members_type=self.members_type, to_file=True
            )
        else:
            file: discord.File = await self.cog.generate_image(
                self._object,
                members_type=self.members_type,
                show_graphic=self.show_graphic_in_main,
                to_file=True,
            )
        self._message: discord.Message = await self.ctx.send(file=file, view=self)
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

    @discord.ui.button(emoji="📈", custom_id="change_mode", style=discord.ButtonStyle.secondary)
    async def change_mode(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await interaction.response.defer(thinking=False)  # thinking=True
        self.graphic_mode: bool = not self.graphic_mode
        if self.graphic_mode:
            file: discord.File = await self.cog.generate_graphic(
                self._object, members_type=self.members_type, to_file=True
            )
        else:
            file: discord.File = await self.cog.generate_image(
                self._object,
                members_type=self.members_type,
                show_graphic=self.show_graphic_in_main,
                to_file=True,
            )
        # try:
        #     await interaction.delete_original_response()
        # except discord.HTTPException:
        #     pass
        await self._message.edit(attachments=[file])

    @discord.ui.button(emoji="🔄", custom_id="reload_page", style=discord.ButtonStyle.secondary)
    async def reload_page(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await interaction.response.defer(thinking=False)  # thinking=True
        if self.graphic_mode:
            file: discord.File = await self.cog.generate_graphic(
                self._object, members_type=self.members_type, to_file=True
            )
        else:
            file: discord.File = await self.cog.generate_image(
                self._object,
                members_type=self.members_type,
                show_graphic=self.show_graphic_in_main,
                to_file=True,
            )
        # try:
        #     await interaction.delete_original_response()
        # except discord.HTTPException:
        #     pass
        await self._message.edit(attachments=[file])

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

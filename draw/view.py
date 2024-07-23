from AAA3A_utils import CogsUtils  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.bot import Red  # isort:skip
from redbot.core.i18n import Translator  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import asyncio
import re

import emoji as _emoji
from redbot.core.utils.chat_formatting import humanize_list

from .board import Board
from .color import Color
from .constants import (
    ALPHABETS,
    IMAGE_EXTENSION,
    LETTER_TO_NUMBER,
    MAIN_COLORS_DICT,
    NUMBERS,
    base_colors_options,
)  # NOQA
from .tools import (
    BrushTool,
    DarkenTool,
    EraseTool,
    EyedropperTool,
    FillTool,
    InverseTool,
    LightenTool,
    ReplaceTool,
    Tool,
)  # NOQA

_: Translator = Translator("Draw", __file__)

ADD_COLORS_EMOJI = "🏳️‍🌈"
ADD_EMOJIS_EMOJI = discord.PartialEmoji(name="emojismiley", id=1056857231125123152)  # "😃"
MIX_COLORS_EMOJI = "🔀"
SET_CURSOR_EMOJI = discord.PartialEmoji(name="ABCD", id=1032565203608547328)
AUTO_DRAW_EMOJI = discord.PartialEmoji(name="auto_draw", id=1032565224903016449)  # "🔄"
SELECT_EMOJI = discord.PartialEmoji(name="select_tool", id=1037847279169704028)  # "📓"
CURSOR_DISPLAY_EMOJI = "📍"
RAW_PAINT_EMOJI = "📤"

UP_LEFT_EMOJI = discord.PartialEmoji(name="up_left", id=1032565175930343484)  # "↖️"
UP_EMOJI = discord.PartialEmoji(name="up", id=1032564978676400148)  # "⬆️"
UP_RIGHT_EMOJI = discord.PartialEmoji(name="up_right", id=1032564997869543464)  # "↗️"
LEFT_EMOJI = discord.PartialEmoji(name="left", id=1032565106934022185)  # "⬅️"
RIGHT_EMOJI = discord.PartialEmoji(name="right", id=1032565019352764438)  # "➡️"
DOWN_LEFT_EMOJI = discord.PartialEmoji(name="down_left", id=1032565090223935518)  # "↙️"
DOWN_EMOJI = discord.PartialEmoji(name="down", id=1032565072981131324)  # "⬇️"
DOWN_RIGHT_EMOJI = discord.PartialEmoji(name="down_right", id=1032565043604230214)  # "↘️"


class Notification:
    def __init__(
        self,
        content: typing.Optional[str] = "",
        *,
        emoji: typing.Optional[
            typing.Union[discord.PartialEmoji, discord.Emoji]
        ] = discord.PartialEmoji.from_str("🔔"),
        view: discord.ui.View,
    ):
        self.emoji: typing.Union[discord.PartialEmoji, discord.Emoji] = emoji
        self.content: str = content
        self.view: discord.ui.View = view

    async def edit(
        self,
        content: typing.Optional[str] = None,
        *,
        emoji: typing.Optional[typing.Union[discord.PartialEmoji, discord.Emoji]] = None,
    ) -> None:
        if emoji is not None:
            self.emoji = emoji
        else:
            emoji = self.emoji
        self.content = content
        await self.view._update()

    def get_truncated_content(self, length: typing.Optional[int] = None) -> str:
        if length is None:
            trunc = self.content.split("\n")[0]
        else:
            trunc = self.content[:length]
        return trunc + (" ..." if len(self.content) > len(trunc) else "")


class ToolsMenu(discord.ui.Select):
    def __init__(
        self,
        view: discord.ui.View,
        *,
        options: typing.Optional[typing.List[discord.SelectOption]] = None,
    ) -> None:
        self.tool_list: typing.List[Tool] = [
            BrushTool(view),
            EraseTool(view),
            EyedropperTool(view),
            FillTool(view),
            ReplaceTool(view),
            DarkenTool(view),
            LightenTool(view),
            InverseTool(view),
        ]
        default_options: typing.List[discord.SelectOption] = [
            discord.SelectOption(
                label=tool.name,
                emoji=tool.emoji,
                value=tool.name.lower(),
                description=f"{tool.description}{' (Used automatically)' if tool.auto_use is True else ''}",
            )
            for tool in self.tool_list
        ]
        options = options or default_options
        self.END_INDEX = len(default_options)  # The ending index of default options.
        super().__init__(
            placeholder="🖌️ Tools",
            max_values=1,
            options=options,
        )
        self._view: discord.ui.View = view

    @property
    def tools(self) -> typing.Dict[str, Tool]:
        return {tool.name.lower(): tool for tool in self.tool_list}

    @property
    def value_to_option_dict(self) -> typing.Dict[str, discord.SelectOption]:
        return {option.value: option for option in self.options}

    def value_to_option(
        self, value: typing.Union[str, int]
    ) -> typing.Union[None, discord.SelectOption]:
        return self.value_to_option_dict.get(value)

    def set_default(self, def_option: discord.SelectOption):
        for option in self.options:
            option.default = False
        def_option.default = True

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        value = self.values[0]
        tool = self.tools[value]
        # If the tool selected is one of these, use it directly instead of equipping.
        if tool.auto_use:
            if await tool.use(
                interaction=interaction
            ):  # This is to decide whether or not to edit the message, depending on if the tool was used successfully.
                await self.view._update()
        # Else, equip the tool (to the primary tool button slot).
        else:
            self.view.primary_tool = tool
            self.view.load_items()
            self.set_default(self.value_to_option(value))
            await self.view._update()


class ColorsMenu(discord.ui.Select):
    def __init__(
        self,
        view: discord.ui.View,
        *,
        options: typing.Optional[typing.List[discord.SelectOption]] = None,
        background: str,
    ) -> None:
        default_options: typing.List[discord.SelectOption] = [
            *base_colors_options(),
            discord.SelectOption(
                label="Add Color(s)",
                emoji=ADD_COLORS_EMOJI,
                value="color",
            ),
            discord.SelectOption(
                label="Add Emoji(s)",
                emoji=ADD_EMOJIS_EMOJI,
                value="emoji",
            ),
            discord.SelectOption(label="Mix Colors", emoji=MIX_COLORS_EMOJI, value="mix"),
        ]
        options = options or default_options
        self.END_INDEX = len(default_options)  # The ending index of default options
        for option in options:
            if str(option.emoji) == background and not option.label.endswith(" (bg)"):
                option.label += " (bg)"
        super().__init__(
            placeholder="🎨 Palette",
            options=options,
        )
        self._view: discord.ui.View = view
        self.bot: Red = self._view.cog.bot
        self.board: Board = self._view.board

    @property
    def value_to_option_dict(self) -> typing.Dict[str, discord.SelectOption]:
        return {option.value: option for option in self.options}

    def value_to_option(
        self, value: typing.Union[str, int]
    ) -> typing.Union[None, discord.SelectOption]:
        return self.value_to_option_dict.get(value)

    def emoji_to_option(
        self, emoji: typing.Union[discord.Emoji, discord.PartialEmoji, Color]
    ) -> typing.Union[None, discord.SelectOption]:
        if isinstance(emoji, discord.Emoji):
            identifier = emoji.id
        elif isinstance(emoji, discord.PartialEmoji):
            identifier = emoji.name if emoji.is_unicode_emoji() else emoji.id
        else:
            identifier = f"#{emoji.hex}"
        return self.value_to_option_dict.get(str(identifier))

    def append_option(
        self, option: discord.SelectOption
    ) -> typing.Tuple[bool, typing.Union[discord.SelectOption, None]]:
        if (found_option := self.value_to_option(option.value)) is not None:
            return False, found_option
        replaced_option = None
        if len(self.options) == 25:
            replaced_option = self.options.pop(self.END_INDEX)
            replaced_option.emoji.name = replaced_option.label
        super().append_option(option)
        return replaced_option is not None, replaced_option

    def set_default(self, def_option: discord.SelectOption) -> None:
        for option in self.options:
            option.default = False
        def_option.default = True

    async def append_sent_emojis(
        self, sent_emojis: typing.List[typing.Union[discord.Emoji, discord.PartialEmoji, Color]]
    ) -> typing.Dict[typing.Union[discord.Emoji, discord.PartialEmoji, Color], str]:
        added_emojis = {
            sent_emoji: "Already exists." if self.emoji_to_option(sent_emoji) else "Added."
            for sent_emoji in sent_emojis
        }
        replaced_emojis = {}
        for added_emoji, status in added_emojis.items():
            if status != "Added.":
                continue
            if isinstance(added_emoji, discord.Emoji) or (
                isinstance(added_emoji, discord.PartialEmoji) and added_emoji.is_custom_emoji()
            ):
                name = f"{added_emoji.name} ({added_emoji.id})"
                emoji = added_emoji
                value = str(added_emoji.id)
            elif (
                isinstance(added_emoji, discord.PartialEmoji) and not added_emoji.is_custom_emoji()
            ):
                name = added_emoji.name
                emoji = added_emoji
                value = added_emoji.name
            elif isinstance(added_emoji, Color):
                name = (await added_emoji.get_name()) + f" ({added_emoji.hex})"
                emoji = None
                value = f"#{added_emoji.hex}"
            else:
                continue
            option = discord.SelectOption(
                label=name,
                emoji=emoji,
                value=value,
            )
            replaced, returned_option = self.append_option(option)
            if replaced:
                replaced_emoji = returned_option.value
                replaced_emojis[added_emoji] = replaced_emoji
        for added_emoji, replaced_emoji in replaced_emojis.items():
            added_emojis[added_emoji] = f"Added (replaced {replaced_emoji})."
        return added_emojis

    async def added_emojis_respond(
        self,
        added_emojis: typing.Dict[typing.Union[discord.Emoji, discord.PartialEmoji, Color], str],
        *,
        notification: Notification,
        interaction: discord.Interaction,
    ) -> None:
        if not added_emojis:
            return await notification.edit("Aborted.")
        response = [f"{added_emoji} - {status}" for added_emoji, status in added_emojis.items()]
        if any("Added." in status for status in added_emojis.values()):
            value = self.options[-1].value
            if value.startswith("#"):
                value = Color.from_hex(value[1:])
            self.board.cursor = value
            self.set_default(self.options[-1])
        response = "\n".join(response)
        await notification.edit(f"{response}..." if len(response) > 2500 else response)
        await self.view._update()

    def extract_emojis(
        self, content: str
    ) -> typing.List[typing.Union[discord.PartialEmoji, Color]]:
        # Get any unicode emojis from the content and list them as SentEmoji objects.
        unicode_emojis = [
            discord.PartialEmoji.from_str(emoji) for emoji in _emoji.distinct_emoji_list(content)
        ]
        # Get any flag/regional indicator emojis from the content and list them as SentEmoji objects.
        FLAG_EMOJI_REGEX = re.compile("[\U0001F1E6-\U0001F1FF]")
        flag_emojis = [
            discord.PartialEmoji.from_str(emoji.group(0))
            for emoji in FLAG_EMOJI_REGEX.finditer(content)
        ]
        # Get any custom emojis from the content and list them as SentEmoji objects.
        CUSTOM_EMOJI_REGEX = re.compile("<a?:[a-zA-Z0-9_]+:\\d+>")
        custom_emojis = [
            discord.PartialEmoji.from_str(emoji.group(0))
            for emoji in CUSTOM_EMOJI_REGEX.finditer(content)
        ]
        return unicode_emojis + flag_emojis + custom_emojis

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()

        # Set max values to 1 everytime the menu is used.
        initial_max_values = self.max_values
        self.max_values = 1

        # If the "Add Color(s)" option was selected. Always takes first priority.
        if "color" in self.values:

            def check(m):
                return m.author == interaction.user and m.channel == interaction.channel

            notification = await self.view.create_notification(
                _(
                    "Please type all the colors you want to add. They can be either or all of:"
                    "\n• The hex codes (e.g. `ff64c4` or `ff64c4ff` to include alpha) **separated by space**,"
                    "\n• The RGB(A) values separated by space or comma or both (e.g. `(255 100 196)` or `(255, 100, 196, 125)`) of each color **surrounded by brackets**"
                    "\n• Any emoji whose main color you want to extract (e.g. 🐸 will give 77b255)"
                    "\n• Any image file (first 5 abundant colors will be extracted)."
                ),
                interaction=interaction,
            )
            try:
                msg = await self.bot.wait_for("message", timeout=30, check=check)
            except asyncio.TimeoutError:
                await notification.edit("Timed out, aborted.")
                return
            await CogsUtils.delete_message(msg)

            CHANNEL = "[a-fA-F0-9]{2}"
            HEX_REGEX = re.compile(
                rf"\b(?P<red>{CHANNEL})(?P<green>{CHANNEL})(?P<blue>{CHANNEL})(?P<alpha>{CHANNEL})?\b"
            )
            ZERO_TO_255 = "0*25[0-5]|0*2[0-4][0-9]|0*1[0-9]{2}|0*[1-9][0-9]|0*[0-9]"
            RGB_A_REGEX = re.compile(
                rf"\((?P<red>{ZERO_TO_255}) *,? +(?P<green>{ZERO_TO_255}) *,? +(?P<blue>{ZERO_TO_255})(?: *,? +(?P<alpha>{ZERO_TO_255}))?\)"
            )

            content = msg.content.lower().strip()

            # Get any hex codes from the content
            hex_matches = list(HEX_REGEX.finditer(content))
            # Get any RGB/A values from the content
            rgb_a_matches = list(RGB_A_REGEX.finditer(content))
            total_matches = hex_matches + rgb_a_matches
            # Organize all the matches into SentEmoji objects.
            sent_emojis = []
            for match in total_matches:
                base = 16 if match in hex_matches else 10
                red = int(match.group("red"), base)
                green = int(match.group("green"), base)
                blue = int(match.group("blue"), base)
                alpha = int(
                    match.group("alpha") or ("ff" if match in hex_matches else "255"),
                    base,
                )
                color = Color((red, green, blue, alpha))
                sent_emojis.append(color)

            # Extract from emoji.
            emoji_matches = self.extract_emojis(content)
            for match in emoji_matches:
                color = await Color.from_emoji(cog=self._view.cog, emoji=match)
                sent_emojis.append(color)

            # Extract from first attachment.
            if msg.attachments:
                attachment_colors = await Color.from_attachment(msg.attachments[0])
                for color in attachment_colors:
                    sent_emojis.append(color)

            added_emojis = await self.append_sent_emojis(sent_emojis)
            await self.added_emojis_respond(
                added_emojis, notification=notification, interaction=interaction
            )

        # First it checks if the "Add Emoji(s)" option was selected. Takes second priority.
        elif "emoji" in self.values:

            def check(m):
                return m.author == interaction.user and m.channel == interaction.channel

            notification = await self.view.create_notification(
                _(
                    "Please send a message containing the emojis you want to add to your palette. E.g. `😎 I like turtles 🐢`."
                ),
                interaction=interaction,
            )
            try:
                msg = await self.bot.wait_for("message", timeout=30, check=check)
            except asyncio.TimeoutError:
                await notification.edit("Timed out, aborted.")
                return
            await CogsUtils.delete_message(msg)

            content = msg.content.strip()
            sent_emojis = self.extract_emojis(content)
            added_emojis = await self.append_sent_emojis(sent_emojis)
            await self.added_emojis_respond(
                added_emojis, notification=notification, interaction=interaction
            )

        # If user has chosen to "Mix Colors".
        elif "mix" in self.values:
            if initial_max_values > 1:
                self.max_values = 1
                await self.view.create_notification(
                    f"Mixing disabled.",
                    emoji="🔀",
                    interaction=interaction,
                )
            else:
                self.max_values = len(self.options)
                await self.view.create_notification(
                    f"Mixing enabled. You can now select multiple colors/emojis to mix their primary colors.",
                    emoji="🔀",
                    interaction=interaction,
                )

        # If multiple options were selected.
        elif len(self.values) > 1:
            selected_options = [self.value_to_option(value) for value in self.values]
            selected_colors = [
                str(option.value)
                for option in selected_options
                if option.value.startswith("#") or option.value in MAIN_COLORS_DICT
            ]
            notification = await self.view.create_notification(
                f"Mixing colors {humanize_list(selected_colors)}...",
                emoji="🔀",
                interaction=interaction,
            )
            colors = [
                MAIN_COLORS_DICT.get(str(color)) or (Color.from_hex(color[1:]))
                for color in selected_colors
            ]
            mixed_color = Color.mix_colors(colors)
            label = (await mixed_color.get_name()) + f" (#{mixed_color.hex})"
            option = discord.SelectOption(
                label=label,
                value=f"#{mixed_color.hex}",
            )
            replaced, returned_option = self.append_option(option)
            self.board.cursor = mixed_color
            self.set_default(option)
            await notification.edit(
                f"Mixed colors:\n{' + '.join(selected_colors)} = {label}"
                + (f" (replaced {returned_option.emoji})." if replaced else "")
            )
            await self.view._update()

        # If only one option was selected.
        elif self.board.cursor != (value := self.values[0]):
            if value.startswith("#"):
                value = Color.from_hex(value[1:])
            self.board.cursor = value
            self.set_default(self.value_to_option(value))
            await self.view._update()


class DrawView(discord.ui.View):
    def __init__(
        self,
        cog: commands.Cog,
        board: Board,
        tool_options: typing.Optional[typing.List[discord.SelectOption]] = None,
        color_options: typing.Optional[typing.List[discord.SelectOption]] = None,
    ) -> None:
        super().__init__(timeout=600)
        self.cog: commands.Cog = cog
        self.ctx: commands.Context = None

        self.board: Board = board

        self.tool_menu: ToolsMenu = ToolsMenu(self, options=tool_options)
        self.color_menu: ColorsMenu = ColorsMenu(
            self, options=color_options, background=board.background
        )
        self.primary_tool: Tool = self.tool_menu.tools["brush"]

        self.auto: bool = False
        self.select: bool = False
        self.disabled: bool = False
        self.secondary_page: bool = False

        self.lock: asyncio.Lock = asyncio.Lock()
        self.notifications: typing.List[Notification] = [Notification(view=self)]

        self._message: discord.Message = None

        self._ready: asyncio.Event = asyncio.Event()

    async def start(
        self, ctx: commands.Context, message: typing.Optional[discord.Message] = None
    ) -> None:
        self.ctx: commands.Context = ctx
        self._message = message
        await self._update()
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
        self.board.clear_cursors(empty=True)
        for child in self.children:
            child: discord.ui.Item
            if hasattr(child, "disabled") and not (
                isinstance(child, discord.ui.Button) and child.style == discord.ButtonStyle.url
            ):
                child.disabled = True
        try:
            await self._update(empty=True)
        except discord.HTTPException:
            pass
        self._ready.set()

    async def _update(self, empty: bool = False) -> None:
        self._embed: discord.Embed = await self.get_embed(self.ctx)
        file = await self.board.to_file()
        if not empty:
            self.load_items()
        if self._message is None:
            self._message: discord.Message = await self.ctx.send(
                embed=self._embed,
                file=file,
                view=self,
            )
            self.cog.views[self._message] = self
        else:
            self._message: discord.Message = await self._message.edit(
                content=None,
                embed=self._embed,
                attachments=[file],
                view=self,
            )

    async def get_embed(self, ctx: commands.Context) -> discord.Embed:
        embed: discord.Embed = discord.Embed(title="Draw Board", color=await ctx.embed_color())
        # embed.description = str(self.board)
        embed.set_image(url=f"attachment://image.{IMAGE_EXTENSION.lower()}")
        # This section adds the notification field only if any one
        # of the notifications is not empty. In such a case, it only
        # shows the notification(s) that is not empty
        if any((len(n.content) != 0 for n in self.notifications)):
            embed.add_field(
                name="Notifications",
                value="\n\n".join(
                    [
                        (
                            f"{str(n.emoji)} "
                            + (n.content if idx == 0 else n.get_truncated_content()).replace(
                                "\n", "\n> "
                            )
                        )  # Put each notification into seperate quotes
                        if len(n.content) != 0
                        else ""  # Show only non-empty notifications
                        for idx, n in enumerate(self.notifications)
                    ]
                ),
            )
        # The embed footer.
        embed.set_footer(
            text=(
                f"The board looks wack? Try decreasing its size! Do {self.ctx.clean_prefix}help draw for more info."
                if any((len(self.board.row_labels) >= 10, len(self.board.col_labels) >= 10))
                else f"You can customize this board! Do {self.ctx.clean_prefix}help draw for more info."
            )
        )
        return embed

    async def create_notification(
        self,
        content: typing.Optional[str] = None,
        *,
        emoji: typing.Optional[
            typing.Union[discord.PartialEmoji, discord.Emoji]
        ] = discord.PartialEmoji.from_str("🔔"),
        interaction: typing.Optional[discord.Interaction] = None,
    ) -> Notification:
        self.notifications = self.notifications[:2]
        notification = Notification(content, emoji=emoji, view=self)
        self.notifications.insert(0, notification)
        if interaction is not None:
            await self._update()
        return notification

    @property
    def placeholder_button(self) -> discord.ui.Button:
        button = discord.ui.Button(
            label="\u200b",
            style=discord.ButtonStyle.gray,
            custom_id=str(len(self.children)),
        )
        button.callback = lambda interaction: interaction.response.defer()
        return button

    def load_items(self) -> None:
        self.clear_items()
        self.add_item(self.tool_menu)
        self.add_item(self.color_menu)
        # This is necessary for "paginating" the view and different buttons.
        if self.secondary_page is False:
            self.add_item(self.undo)
            self.add_item(self.up_left)
            self.add_item(self.up)
            self.add_item(self.up_right)
            self.add_item(self.secondary_page_button)

            self.add_item(self.redo)
            self.add_item(self.left)
            self.add_item(self.set_cursor)
            self.add_item(self.right)
            # self.add_item(self.placeholder_button)
            self.add_item(self.set_auto_draw)

            self.add_item(self.primary_tool)
            self.add_item(self.down_left)
            self.add_item(self.down)
            self.add_item(self.down_right)
            # self.add_item(self.placeholder_button)
            self.add_item(self.select_area)
        elif self.secondary_page is True:
            self.add_item(self.stop_button)
            self.add_item(self.up_left)
            self.add_item(self.up)
            self.add_item(self.up_right)
            self.add_item(self.secondary_page_button)

            self.add_item(self.clear)
            self.add_item(self.left)
            self.add_item(self.set_cursor)
            self.add_item(self.right)
            # self.add_item(self.placeholder_button)
            self.add_item(self.raw_paint)

            self.add_item(self.primary_tool)
            self.add_item(self.down_left)
            self.add_item(self.down)
            self.add_item(self.down_right)
            # self.add_item(self.placeholder_button)
            self.add_item(self.set_cursor_display)
        self.update_buttons()

    def update_buttons(self) -> None:
        self.secondary_page_button.style = (
            discord.ButtonStyle.success if self.secondary_page else discord.ButtonStyle.secondary
        )
        self.undo.disabled = self.board.board_index == 0 or self.disabled
        self.undo.label = f"{self.board.board_index} ↶"
        self.redo.disabled = (
            self.board.board_index == len(self.board.board_history) - 1
        ) or self.disabled
        self.redo.label = f"↷ {(len(self.board.board_history) - 1) - self.board.board_index}"

    async def move_cursor(
        self,
        interaction: discord.Interaction,
        row_move: typing.Optional[int] = 0,
        col_move: typing.Optional[int] = 0,
    ) -> None:
        self.board.move_cursor(row_move, col_move, self.select)
        if self.auto:
            await self.primary_tool.use(interaction=interaction)
        await self._update()

    # Buttons

    # 1st row
    @discord.ui.button(label="↶", style=discord.ButtonStyle.secondary)
    async def undo(self, interaction: discord.Interaction, button: discord.Button) -> None:
        await interaction.response.defer()
        if self.board.board_index > 0:
            self.board.board_index -= 1
        await self._update()

    @discord.ui.button(style=discord.ButtonStyle.danger, emoji="✖️", custom_id="close_page")
    async def stop_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        try:
            await interaction.response.defer()
        except discord.errors.NotFound:
            pass
        self.stop()
        await CogsUtils.delete_message(self._message)
        self._ready.set()

    @discord.ui.button(emoji=UP_LEFT_EMOJI, style=discord.ButtonStyle.primary)
    async def up_left(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer()
        row_move = -1
        col_move = -1
        await self.move_cursor(interaction, row_move=row_move, col_move=col_move)

    @discord.ui.button(emoji=UP_EMOJI, style=discord.ButtonStyle.primary)
    async def up(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer()
        row_move = -1
        col_move = 0
        await self.move_cursor(interaction, row_move=row_move, col_move=col_move)

    @discord.ui.button(emoji=UP_RIGHT_EMOJI, style=discord.ButtonStyle.primary)
    async def up_right(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer()
        row_move = -1
        col_move = 1
        await self.move_cursor(interaction, row_move=row_move, col_move=col_move)

    @discord.ui.button(label="2nd", style=discord.ButtonStyle.secondary)
    async def secondary_page_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await interaction.response.defer()
        self.secondary_page = not self.secondary_page

        self.load_items()
        await self._update()

    # 2nd Row
    @discord.ui.button(label="↷", style=discord.ButtonStyle.secondary)
    async def redo(self, interaction: discord.Interaction, button: discord.Button) -> None:
        await interaction.response.defer()
        if self.board.board_index < len(self.board.board_history) - 1:
            self.board.board_index += 1
        await self._update()

    @discord.ui.button(label="Clear", style=discord.ButtonStyle.danger)
    async def clear(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer()
        self.secondary_page = False
        self.auto = False
        self.select = False
        self.board.clear()
        self.load_items()
        await self._update()

    @discord.ui.button(emoji=LEFT_EMOJI, style=discord.ButtonStyle.primary)
    async def left(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer()
        row_move = 0
        col_move = -1
        await self.move_cursor(interaction, row_move=row_move, col_move=col_move)

    @discord.ui.button(emoji=RIGHT_EMOJI, style=discord.ButtonStyle.primary)
    async def right(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer()
        row_move = 0
        col_move = 1
        await self.move_cursor(interaction, row_move=row_move, col_move=col_move)

    # 3rd / Last Row
    @discord.ui.button(emoji=DOWN_LEFT_EMOJI, style=discord.ButtonStyle.primary)
    async def down_left(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer()
        row_move = 1
        col_move = -1
        await self.move_cursor(interaction, row_move=row_move, col_move=col_move)

    @discord.ui.button(emoji=DOWN_EMOJI, style=discord.ButtonStyle.primary)
    async def down(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer()
        row_move = 1
        col_move = 0
        await self.move_cursor(interaction, row_move=row_move, col_move=col_move)

    @discord.ui.button(emoji=DOWN_RIGHT_EMOJI, style=discord.ButtonStyle.primary)
    async def down_right(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await interaction.response.defer()
        row_move = 1
        col_move = 1
        await self.move_cursor(interaction, row_move=row_move, col_move=col_move)

    @discord.ui.button(emoji=SET_CURSOR_EMOJI, style=discord.ButtonStyle.secondary)
    async def set_cursor(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await interaction.response.defer()

        def check(m):
            return m.author == interaction.user and m.channel == interaction.channel

        notification = await self.create_notification(
            _(
                "Please type the cell you want to move the cursor to. e.g. `A1`, `a1`, `A10`, `A`, `10`, etc."
            ),
            emoji="🔠",
            interaction=interaction,
        )
        try:
            msg = await self.ctx.bot.wait_for("message", timeout=30, check=check)
        except asyncio.TimeoutError:
            await notification.edit("Timed out, aborted.")
            return
        await CogsUtils.delete_message(msg)

        cell: str = msg.content.upper()
        ABC = ALPHABETS[: self.board.cursor_row_max + 1]
        NUM = NUMBERS[: self.board.cursor_col_max + 1]
        end_row_key = None
        end_col_key = None

        CELL_REGEX = (
            f"^(?P<start_row>[A-{ABC[-1]}])(?P<start_col>[0-9]|(?:1[0-{NUM[-1] % 10}]))"
            f"(-(?P<end_row>[A-{ABC[-1]}])(?P<end_col>[0-9]|(?:1[0-{NUM[-1] % 10}]))?)?$"
        )
        ROW_OR_COL_REGEX = (
            f"(?:^(?P<row>[A-{ABC[-1]}])$)|(?:^(?P<col>[0-9]|(?:1[0-{NUM[-1] % 10}]))$)"
        )
        match = re.match(CELL_REGEX, cell)
        if match is not None:
            start_row_key = match["start_row"]
            start_col_key = int(match["start_col"])
            if match["end_row"] is not None:
                end_row_key = match["end_row"]
                end_col_key = (
                    int(match["end_col"]) if match["end_col"] is not None else start_col_key
                )
        else:
            match = re.match(ROW_OR_COL_REGEX, cell)
            if match is not None:
                start_row_key = (
                    match["row"] if match["row"] is not None else ABC[self.board.cursor_row]
                )
                start_col_key = (
                    int(match["col"]) if match["col"] is not None else self.board.cursor_col
                )
            else:
                return await notification.edit("Aborted.")

        if (
            start_row_key not in ABC
            or start_col_key not in NUM
            or (end_row_key is not None and end_row_key not in ABC)
            or (end_col_key is not None and end_col_key not in NUM)
        ):
            return await notification.edit("Aborted.")

        if end_row_key is None and end_col_key is None:
            row_move = LETTER_TO_NUMBER[start_row_key] - self.board.cursor_row
            col_move = start_col_key - self.board.cursor_col
            await notification.edit(
                f"Moved cursor to **{cell}** ({LETTER_TO_NUMBER[start_row_key]}, {start_col_key}).",
            )
            await self.move_cursor(interaction, row_move=row_move, col_move=col_move)
        else:
            row_move = LETTER_TO_NUMBER[start_row_key] - self.board.cursor_row
            col_move = start_col_key - self.board.cursor_col
            self.board.move_cursor(row_move, col_move, self.select)
            self.board.initial_coords = (
                self.board.cursor_row,
                self.board.cursor_col,
            )
            (
                self.board.initial_row,
                self.board.initial_col,
            ) = self.board.initial_coords
            self.select = not self.select
            row_move = LETTER_TO_NUMBER[end_row_key] - self.board.cursor_row
            col_move = end_col_key - self.board.cursor_col
            await notification.edit(
                f"Moved cursor to select **{cell}** ({LETTER_TO_NUMBER[start_row_key]}, {start_col_key} | {LETTER_TO_NUMBER[end_row_key]}, {end_col_key}).",
            )
            await self.move_cursor(interaction, row_move=row_move, col_move=col_move)

    @discord.ui.button(
        label="Auto Draw", emoji=AUTO_DRAW_EMOJI, style=discord.ButtonStyle.secondary
    )
    async def set_auto_draw(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await interaction.response.defer()
        self.auto = not self.auto
        state = "enabled" if self.auto else "disabled"
        await self.create_notification(
            f"Auto Draw {state}.",
            emoji="🔄",
            interaction=interaction,
        )

    @discord.ui.button(
        label="Select an Area", emoji=SELECT_EMOJI, style=discord.ButtonStyle.secondary
    )
    async def select_area(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await interaction.response.defer()
        if self.select is False:
            self.board.initial_coords = (
                self.board.cursor_row,
                self.board.cursor_col,
            )
            (
                self.board.initial_row,
                self.board.initial_col,
            ) = self.board.initial_coords
            self.select = not self.select
        elif self.select is True:
            self.board.clear_cursors()
            self.select = not self.select
        await self._update()

    @discord.ui.button(
        label="Raw Paint", emoji=RAW_PAINT_EMOJI, style=discord.ButtonStyle.secondary
    )
    async def raw_paint(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer()

        def check(m):
            return m.author == interaction.user and m.channel == interaction.channel

        notification = await self.create_notification(
            _(
                'Please type the cells with the main colors names. One color for each line, separated from the cell by a ":". Example: `A1:red\nB7-C9:green`.'
            ),
            emoji=RAW_PAINT_EMOJI,
            interaction=interaction,
        )
        try:
            msg = await self.ctx.bot.wait_for("message", timeout=30, check=check)
        except asyncio.TimeoutError:
            await notification.edit("Timed out, aborted.")
            return
        await CogsUtils.delete_message(msg)

        for i, line in enumerate(msg.content.split("\n"), start=1):
            if len(line.split(":")) != 2:
                return await notification.edit(f"Aborted. No `:` in line {i}.")
            cell: str = line.split(":")[0].strip().upper()
            color: str = line.split(":")[1].strip().lower()

            ABC = ALPHABETS[: self.board.cursor_row_max + 1]
            NUM = NUMBERS[: self.board.cursor_col_max + 1]
            end_row_key = None
            end_col_key = None

            CELL_REGEX = (
                f"^(?P<start_row>[A-{ABC[-1]}])(?P<start_col>[0-9]|(?:1[0-{NUM[-1] % 10}]))"
                f"(-(?P<end_row>[A-{ABC[-1]}])(?P<end_col>[0-9]|(?:1[0-{NUM[-1] % 10}]))?)?$"
            )
            ROW_OR_COL_REGEX = (
                f"(?:^(?P<row>[A-{ABC[-1]}])$)|(?:^(?P<col>[0-9]|(?:1[0-{NUM[-1] % 10}]))$)"
            )
            match = re.match(CELL_REGEX, cell)
            if match is not None:
                start_row_key = match["start_row"]
                start_col_key = int(match["start_col"])
                if match["end_row"] is not None:
                    end_row_key = match["end_row"]
                    end_col_key = (
                        int(match["end_col"]) if match["end_col"] is not None else start_col_key
                    )
            else:
                match = re.match(ROW_OR_COL_REGEX, cell)
                if match is not None:
                    start_row_key = (
                        match["row"] if match["row"] is not None else ABC[self.board.cursor_row]
                    )
                    start_col_key = (
                        int(match["col"]) if match["col"] is not None else self.board.cursor_col
                    )
                else:
                    return await notification.edit(f"Aborted. No cell match in line {i}.")

            if (
                start_row_key not in ABC
                or start_col_key not in NUM
                or (end_row_key is not None and end_row_key not in ABC)
                or (end_col_key is not None and end_col_key not in NUM)
            ):
                return await notification.edit(
                    f"Aborted. Wrong letter/num for cell(s) in line {i}."
                )

            colors = {option.label.lower(): option.value for option in base_colors_options()}
            if color not in colors:
                return await notification.edit(f"Aborted. Invalid color in line {i}.")
            color = colors[color]

            if end_row_key is None and end_col_key is None:
                self.board.draw(
                    color=color, coords=[(LETTER_TO_NUMBER[start_row_key], start_col_key)]
                )
            else:
                self.board.draw(
                    color=color,
                    coords=[
                        (row, col)
                        for col in range(
                            min(start_col_key, end_col_key),
                            max(start_col_key, end_col_key) + 1,
                        )
                        for row in range(
                            min(LETTER_TO_NUMBER[start_row_key], LETTER_TO_NUMBER[end_row_key]),
                            max(LETTER_TO_NUMBER[start_row_key], LETTER_TO_NUMBER[end_row_key])
                            + 1,
                        )
                    ],
                )

        await notification.edit("Draw paint successful.")

    @discord.ui.button(
        label="Cursor Display", emoji=CURSOR_DISPLAY_EMOJI, style=discord.ButtonStyle.success
    )
    async def set_cursor_display(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await interaction.response.defer()
        self.board.cursor_display = not self.board.cursor_display
        state = "enabled" if self.board.cursor_display else "disabled"
        await self.create_notification(
            f"Cursor Display {state}.",
            emoji="📍",
            interaction=interaction,
        )

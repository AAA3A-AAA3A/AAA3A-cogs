import discord

from redbot.core import commands
from redbot.core.i18n import Translator
from redbot.core.utils.chat_formatting import box

_: Translator = Translator("Calculator", __file__)

NORMAL_BUTTONS = [
    {"style": 2, "label": "1", "emoji": None, "custom_id": "1"},
    {"style": 2, "label": "2", "emoji": None, "custom_id": "2"},
    {"style": 2, "label": "3", "emoji": None, "custom_id": "3"},
    {"style": 1, "label": "x", "emoji": None, "custom_id": "x"},
    {
        "style": 4,
        "label": _("Exit"),
        "emoji": None,
        "custom_id": "exit_button",
    },
    {"style": 2, "label": "4", "emoji": None, "custom_id": "4"},
    {"style": 2, "label": "5", "emoji": None, "custom_id": "5"},
    {"style": 2, "label": "6", "emoji": None, "custom_id": "6"},
    {"style": 1, "label": "÷", "emoji": None, "custom_id": "÷"},
    {
        "style": 4,
        "label": "⌫",
        "emoji": None,
        "custom_id": "back_button",
    },
    {"style": 2, "label": "7", "emoji": None, "custom_id": "7"},
    {"style": 2, "label": "8", "emoji": None, "custom_id": "8"},
    {"style": 2, "label": "9", "emoji": None, "custom_id": "9"},
    {"style": 1, "label": "+", "emoji": None, "custom_id": "+"},
    {
        "style": 4,
        "label": _("Clear"),
        "emoji": None,
        "custom_id": "clear_button",
    },
    {
        "style": 2,
        "label": None,
        "emoji": "📄",
        "custom_id": "history_button",
    },
    {"style": 2, "label": "0", "emoji": None, "custom_id": "0"},
    {"style": 2, "label": ".", "emoji": None, "custom_id": "."},
    {"style": 1, "label": "-", "emoji": None, "custom_id": "-"},
    {
        "style": 3,
        "label": "=",
        "emoji": None,
        "custom_id": "result_button",
    },
    {"style": 2, "label": "(", "emoji": None, "custom_id": "("},
    {"style": 2, "label": ")", "emoji": None, "custom_id": ")"},
    {
        "style": 2,
        "label": None,
        "emoji": "🧑‍🔬",
        "custom_id": "mode_button",
    },
    {
        "style": 3,
        "label": "<",
        "emoji": None,
        "custom_id": "left_button",
    },
    {
        "style": 3,
        "label": ">",
        "emoji": None,
        "custom_id": "right_button",
    },
]
SCIENTIST_BUTTONS = [
    {"style": 2, "label": "e", "emoji": None, "custom_id": "e"},
    {"style": 2, "label": "π", "emoji": None, "custom_id": "π"},
    {"style": 2, "label": "|x|", "emoji": None, "custom_id": "abs"},
    {"style": 1, "label": "x", "emoji": None, "custom_id": "x"},
    {
        "style": 4,
        "label": _("Exit"),
        "emoji": None,
        "custom_id": "exit_button",
    },
    {"style": 2, "label": "X²", "emoji": None, "custom_id": "X²"},
    {"style": 2, "label": "X³", "emoji": None, "custom_id": "X³"},
    {"style": 2, "label": "Xˣ", "emoji": None, "custom_id": "Xˣ"},
    {"style": 1, "label": "÷", "emoji": None, "custom_id": "÷"},
    {
        "style": 4,
        "label": "⌫",
        "emoji": None,
        "custom_id": "back_button",
    },
    {"style": 2, "label": "cos", "emoji": None, "custom_id": "cos"},
    {"style": 2, "label": "sin", "emoji": None, "custom_id": "sin"},
    {"style": 2, "label": "tan", "emoji": None, "custom_id": "tan"},
    {"style": 1, "label": "+", "emoji": None, "custom_id": "+"},
    {
        "style": 4,
        "label": _("Clear"),
        "emoji": None,
        "custom_id": "clear_button",
    },
    {
        "style": 2,
        "label": None,
        "emoji": "📄",
        "custom_id": "history_button",
    },
    {"style": 2, "label": "ln", "emoji": None, "custom_id": "ln"},
    {"style": 2, "label": "√", "emoji": None, "custom_id": "√"},
    {"style": 1, "label": "-", "emoji": None, "custom_id": "-"},
    {
        "style": 3,
        "label": "=",
        "emoji": None,
        "custom_id": "result_button",
    },
    {"style": 2, "label": "(", "emoji": None, "custom_id": "("},
    {"style": 2, "label": ")", "emoji": None, "custom_id": ")"},
    {
        "style": 2,
        "label": None,
        "emoji": "👨‍🏫",
        "custom_id": "mode_button",
    },
    {
        "style": 3,
        "label": "<",
        "emoji": None,
        "custom_id": "left_button",
    },
    {
        "style": 3,
        "label": ">",
        "emoji": None,
        "custom_id": "right_button",
    },
]


class CalculatorView(discord.ui.View):
    def __init__(self, cog: commands.Cog) -> None:
        super().__init__(timeout=60 * 5)
        self.ctx: commands.Context = None
        self.cog: commands.Cog = cog

        self._message: discord.Message = None
        self._expression: str | None = None
        self._result: str | None = None
        self._is_normal: bool = True

        self.NORMAL_BUTTONS: list[discord.ui.Button] = []
        self.SCIENTIST_BUTTONS: list[discord.ui.Button] = []

    async def start(self, ctx: commands.Context) -> discord.Message:
        self.ctx: commands.Context = ctx
        for button in NORMAL_BUTTONS:
            button = button.copy()
            if "style" in button:
                button["style"] = discord.ButtonStyle(button["style"])
            button = discord.ui.Button(**button)
            button.callback = self._callback
            self.NORMAL_BUTTONS.append(button)
        for button in SCIENTIST_BUTTONS:
            button = button.copy()
            if "style" in button:
                button["style"] = discord.ButtonStyle(button["style"])
            button = discord.ui.Button(**button)
            button.callback = self._callback
            self.SCIENTIST_BUTTONS.append(button)
        current_buttons = self.NORMAL_BUTTONS if self._is_normal else self.SCIENTIST_BUTTONS
        self.clear_items()
        for button in current_buttons:
            self.add_item(button)
        self._message: discord.Message = await self.ctx.send(
            embed=await self.cog.get_embed(self.ctx, self._expression, self._result),
            view=self,
        )
        self.cog.views[self._message] = self
        return self._message

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id not in [self.ctx.author.id] + list(self.ctx.bot.owner_ids):
            await interaction.response.send_message(
                _("You are not allowed to use this interaction."),
                ephemeral=True,
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

    async def _callback(self, interaction: discord.Interaction) -> None:
        if self._result in (_("Error!"), "∞", ""):
            self._result = None
        if self._result is not None and interaction.data["custom_id"] != "result_button":
            self._expression = f"{self._result}|"
            self._result = None
        if (
            self._expression is None
            or self._expression == _("Error!")
            or self._expression == "∞"
            or self._expression == ""
        ):
            self._expression = "|"
        if interaction.data["custom_id"] == "result_button":
            self._result = f"{await self.cog.calculate(self._expression)}"
            if self.ctx.author not in self.cog.history:
                self.cog.history[self.ctx.author] = []
            self.cog.history[self.ctx.author].append(
                (self._expression.replace("|", ""), self._result.replace("|", "")),
            )
        elif interaction.data["custom_id"] == "exit_button":
            await interaction.response.defer()
            await self.on_timeout()
            self.stop()
            return
        elif interaction.data["custom_id"] == "clear_button":
            self._expression = None
            self._result = None
        elif interaction.data["custom_id"] == "back_button":
            lst = list(self._expression)
            if len(lst) > 1:
                try:
                    index = lst.index("|")
                    lst.pop(index - 1)
                    self._expression = "".join(lst)
                except (ValueError, IndexError):
                    self._expression = None
        elif interaction.data["custom_id"] == "left_button":
            lst = list(self._expression)
            if len(lst) > 1:
                try:
                    index = lst.index("|")
                    lst.remove("|")
                    lst.insert(index - 1, "|")
                except (ValueError, IndexError):
                    lst = ["|"]
            self._expression = "".join(lst)
            if self._expression == "|":
                self._expression = None
        elif interaction.data["custom_id"] == "right_button":
            lst = list(self._expression)
            if len(lst) > 1:
                try:
                    index = lst.index("|")
                    lst.remove("|")
                    lst.insert(index + 1, "|")
                except (ValueError, IndexError):
                    lst = ["|"]
            self._expression = "".join(lst)
            if self._expression == "|":
                self._expression = None
        elif interaction.data["custom_id"] == "mode_button":
            self._is_normal = not self._is_normal
            current_buttons = self.NORMAL_BUTTONS if self._is_normal else self.SCIENTIST_BUTTONS
            self.clear_items()
            for button in current_buttons:
                self.add_item(button)
            await interaction.response.edit_message(view=self)
            return
        elif interaction.data["custom_id"] == "history_button":
            embed: discord.Embed = discord.Embed()
            embed.title = f"{self.ctx.author.display_name}'s history"
            history = self.cog.history.get(self.ctx.author, [])[-25:][::-1]
            if len(history) == 0:
                embed.description = _("Nothing in your history.")
            else:
                for count, entry in enumerate(history, start=0):
                    all_count = list(range(1, len(self.cog.history.get(self.ctx.author, [])) + 1))[
                        ::-1
                    ]
                    count = all_count[count]
                    _expression, _result = entry
                    embed.add_field(
                        name=f"Entry {count}:",
                        value=box(f"> {str(_expression)}", lang="fix")
                        + box(f"= {str(_result)}", lang="fix")
                        + "\n",
                    )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        else:
            self._expression = await self.cog.input_formatter(
                self._expression,
                interaction.data["custom_id"],
            )
        if self._expression is not None:
            self._expression = self._expression.replace(",", ".")
        await interaction.response.edit_message(
            embed=await self.cog.get_embed(self.ctx, self._expression, self._result),
        )

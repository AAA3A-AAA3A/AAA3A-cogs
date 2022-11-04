from .AAA3A_utils import CogsUtils  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
from redbot.core.bot import Red  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

if CogsUtils().is_dpy2:
    from .AAA3A_utils import Buttons  # isort:skip
else:
    from dislash import ActionRow, Button, ButtonStyle, ResponseType  # isort:skip

import asyncio
import datetime
from math import *

from redbot.core import Config
from redbot.core.utils.chat_formatting import box
from TagScriptEngine import Interpreter, block

# Credits:
# Thanks to @epic guy on Discord for the basic syntax (command groups, commands) and also commands (await ctx.send, await ctx.author.send, await ctx.message.delete())!
# Thanks to @YamiKaitou on Discord for the technique in the init file to load the interaction client only if it is not loaded! Before this fix, when a user clicked on a button, the actions would be launched about 10 times, which caused huge spam and a loop in the channel!
# Thanks to the developers of the cogs I added features to as it taught me how to make a cog! (Chessgame by WildStriker, Captcha by Kreusada, Speak by Epic guy and Rommer by Dav)
# Thanks to all the people who helped me with some commands in the #coding channel of the redbot support server!

_ = Translator("Calculator", __file__)

if CogsUtils().is_dpy2:
    from functools import partial

    hybrid_command = partial(commands.hybrid_command, with_app_command=False)
    hybrid_group = partial(commands.hybrid_group, with_app_command=False)
else:
    hybrid_command = commands.command
    hybrid_group = commands.group


@cog_i18n(_)
class Calculator(commands.Cog):
    """A cog to do calculations from Discord with buttons!"""

    def __init__(self, bot: Red):
        self.bot: Red = bot
        self.config: Config = Config.get_conf(
            self,
            identifier=205192943327321000143939875896557571750,  # 905683670375
            force_registration=True,
        )
        self.calculator_global = {
            "settings": {
                "time_max": 180,
                "color": 0x01D758,
                "thumbnail": "https://cdn.pixabay.com/photo/2017/07/06/17/13/calculator-2478633_960_720.png",
            },
        }
        self.config.register_global(**self.calculator_global)

        blocks = [
            block.MathBlock(),
            block.RandomBlock(),
            block.RangeBlock(),
        ]
        self.engine = Interpreter(blocks)

        self.x = {
            "1": "¹",
            "2": "²",
            "3": "³",
            "4": "⁴",
            "5": "⁵",
            "6": "⁶",
            "7": "⁷",
            "8": "⁸",
            "9": "⁹",
        }

        self.normal_buttons_dict = [
            {"style": 2, "label": "1", "emoji": None, "custom_id": "1", "disabled": False},
            {"style": 2, "label": "2", "emoji": None, "custom_id": "2", "disabled": False},
            {"style": 2, "label": "3", "emoji": None, "custom_id": "3", "disabled": False},
            {"style": 1, "label": "x", "emoji": None, "custom_id": "x", "disabled": False},
            {
                "style": 4,
                "label": _("Exit").format(**locals()),
                "emoji": None,
                "custom_id": "exit_button",
                "disabled": False,
            },
            {"style": 2, "label": "4", "emoji": None, "custom_id": "4", "disabled": False},
            {"style": 2, "label": "5", "emoji": None, "custom_id": "5", "disabled": False},
            {"style": 2, "label": "6", "emoji": None, "custom_id": "6", "disabled": False},
            {"style": 1, "label": "÷", "emoji": None, "custom_id": "÷", "disabled": False},
            {
                "style": 4,
                "label": "⌫",
                "emoji": None,
                "custom_id": "back_button",
                "disabled": False,
            },
            {"style": 2, "label": "7", "emoji": None, "custom_id": "7", "disabled": False},
            {"style": 2, "label": "8", "emoji": None, "custom_id": "8", "disabled": False},
            {"style": 2, "label": "9", "emoji": None, "custom_id": "9", "disabled": False},
            {"style": 1, "label": "+", "emoji": None, "custom_id": "+", "disabled": False},
            {
                "style": 4,
                "label": _("Clear").format(**locals()),
                "emoji": None,
                "custom_id": "clear_button",
                "disabled": False,
            },
            {
                "style": 2,
                "label": None,
                "emoji": "📄",
                "custom_id": "history_button",
                "disabled": False,
            },
            {"style": 2, "label": "0", "emoji": None, "custom_id": "0", "disabled": False},
            {"style": 2, "label": ".", "emoji": None, "custom_id": ".", "disabled": False},
            {"style": 1, "label": "-", "emoji": None, "custom_id": "-", "disabled": False},
            {
                "style": 3,
                "label": "=",
                "emoji": None,
                "custom_id": "result_button",
                "disabled": False,
            },
            {"style": 2, "label": "(", "emoji": None, "custom_id": "(", "disabled": False},
            {"style": 2, "label": ")", "emoji": None, "custom_id": ")", "disabled": False},
            {"style": 2, "label": None, "emoji": "🧑‍🔬", "custom_id": "mode_button", "disabled": False},
            {
                "style": 3,
                "label": "<",
                "emoji": None,
                "custom_id": "left_button",
                "disabled": False,
            },
            {
                "style": 3,
                "label": ">",
                "emoji": None,
                "custom_id": "right_button",
                "disabled": False,
            },
        ]
        self.scientist_buttons_dict = [
            {"style": 2, "label": "e", "emoji": None, "custom_id": "e", "disabled": False},
            {"style": 2, "label": "π", "emoji": None, "custom_id": "π", "disabled": False},
            {"style": 2, "label": "|x|", "emoji": None, "custom_id": "abs", "disabled": False},
            {"style": 1, "label": "x", "emoji": None, "custom_id": "x", "disabled": False},
            {
                "style": 4,
                "label": _("Exit").format(**locals()),
                "emoji": None,
                "custom_id": "exit_button",
                "disabled": False,
            },
            {"style": 2, "label": "X²", "emoji": None, "custom_id": "X²", "disabled": False},
            {"style": 2, "label": "X³", "emoji": None, "custom_id": "X³", "disabled": False},
            {"style": 2, "label": "Xˣ", "emoji": None, "custom_id": "Xˣ", "disabled": False},
            {"style": 1, "label": "÷", "emoji": None, "custom_id": "÷", "disabled": False},
            {
                "style": 4,
                "label": "⌫",
                "emoji": None,
                "custom_id": "back_button",
                "disabled": False,
            },
            {"style": 2, "label": "cos", "emoji": None, "custom_id": "cos", "disabled": False},
            {"style": 2, "label": "sin", "emoji": None, "custom_id": "sin", "disabled": False},
            {"style": 2, "label": "tan", "emoji": None, "custom_id": "tan", "disabled": False},
            {"style": 1, "label": "+", "emoji": None, "custom_id": "+", "disabled": False},
            {
                "style": 4,
                "label": _("Clear").format(**locals()),
                "emoji": None,
                "custom_id": "clear_button",
                "disabled": False,
            },
            {
                "style": 2,
                "label": None,
                "emoji": "📄",
                "custom_id": "history_button",
                "disabled": False,
            },
            {"style": 2, "label": "In", "emoji": None, "custom_id": "In", "disabled": False},
            {"style": 2, "label": "√", "emoji": None, "custom_id": "√", "disabled": False},
            {"style": 1, "label": "-", "emoji": None, "custom_id": "-", "disabled": False},
            {
                "style": 3,
                "label": "=",
                "emoji": None,
                "custom_id": "result_button",
                "disabled": False,
            },
            {"style": 2, "label": "(", "emoji": None, "custom_id": "(", "disabled": False},
            {"style": 2, "label": ")", "emoji": None, "custom_id": ")", "disabled": False},
            {"style": 2, "label": None, "emoji": "👨‍🏫", "custom_id": "mode_button", "disabled": False},
            {
                "style": 3,
                "label": "<",
                "emoji": None,
                "custom_id": "left_button",
                "disabled": False,
            },
            {
                "style": 3,
                "label": ">",
                "emoji": None,
                "custom_id": "right_button",
                "disabled": False,
            },
        ]
        self.disabled_normal_buttons_dict = [
            {"style": 2, "label": "1", "emoji": None, "custom_id": "1", "disabled": True},
            {"style": 2, "label": "2", "emoji": None, "custom_id": "2", "disabled": True},
            {"style": 2, "label": "3", "emoji": None, "custom_id": "3", "disabled": True},
            {"style": 1, "label": "x", "emoji": None, "custom_id": "x", "disabled": True},
            {
                "style": 4,
                "label": _("Exit").format(**locals()),
                "emoji": None,
                "custom_id": "exit_button",
                "disabled": True,
            },
            {"style": 2, "label": "4", "emoji": None, "custom_id": "4", "disabled": True},
            {"style": 2, "label": "5", "emoji": None, "custom_id": "5", "disabled": True},
            {"style": 2, "label": "6", "emoji": None, "custom_id": "6", "disabled": True},
            {"style": 1, "label": "÷", "emoji": None, "custom_id": "÷", "disabled": True},
            {
                "style": 4,
                "label": "⌫",
                "emoji": None,
                "custom_id": "back_button",
                "disabled": True,
            },
            {"style": 2, "label": "7", "emoji": None, "custom_id": "7", "disabled": True},
            {"style": 2, "label": "8", "emoji": None, "custom_id": "8", "disabled": True},
            {"style": 2, "label": "9", "emoji": None, "custom_id": "9", "disabled": True},
            {"style": 1, "label": "+", "emoji": None, "custom_id": "+", "disabled": True},
            {
                "style": 4,
                "label": _("Clear").format(**locals()),
                "emoji": None,
                "custom_id": "clear_button",
                "disabled": True,
            },
            {
                "style": 2,
                "label": None,
                "emoji": "📄",
                "custom_id": "history_button",
                "disabled": True,
            },
            {"style": 2, "label": "0", "emoji": None, "custom_id": "0", "disabled": True},
            {"style": 2, "label": ".", "emoji": None, "custom_id": ".", "disabled": True},
            {"style": 1, "label": "-", "emoji": None, "custom_id": "-", "disabled": True},
            {
                "style": 3,
                "label": "=",
                "emoji": None,
                "custom_id": "result_button",
                "disabled": True,
            },
            {"style": 2, "label": "(", "emoji": None, "custom_id": "(", "disabled": True},
            {"style": 2, "label": ")", "emoji": None, "custom_id": ")", "disabled": True},
            {"style": 2, "label": None, "emoji": "🧑‍🔬", "custom_id": "mode_button", "disabled": True},
            {
                "style": 3,
                "label": "<",
                "emoji": None,
                "custom_id": "left_button",
                "disabled": True,
            },
            {
                "style": 3,
                "label": ">",
                "emoji": None,
                "custom_id": "right_button",
                "disabled": True,
            },
        ]
        self.disabled_scientist_buttons_dict = [
            {"style": 2, "label": "e", "emoji": None, "custom_id": "e", "disabled": True},
            {"style": 2, "label": "π", "emoji": None, "custom_id": "π", "disabled": True},
            {"style": 2, "label": "|x|", "emoji": None, "custom_id": "abs", "disabled": True},
            {"style": 1, "label": "x", "emoji": None, "custom_id": "x", "disabled": True},
            {
                "style": 4,
                "label": _("Exit").format(**locals()),
                "emoji": None,
                "custom_id": "exit_button",
                "disabled": True,
            },
            {"style": 2, "label": "X²", "emoji": None, "custom_id": "X²", "disabled": True},
            {"style": 2, "label": "X³", "emoji": None, "custom_id": "X³", "disabled": True},
            {"style": 2, "label": "Xˣ", "emoji": None, "custom_id": "Xˣ", "disabled": True},
            {"style": 1, "label": "÷", "emoji": None, "custom_id": "÷", "disabled": True},
            {
                "style": 4,
                "label": "⌫",
                "emoji": None,
                "custom_id": "back_button",
                "disabled": True,
            },
            {"style": 2, "label": "cos", "emoji": None, "custom_id": "cos", "disabled": True},
            {"style": 2, "label": "sin", "emoji": None, "custom_id": "sin", "disabled": True},
            {"style": 2, "label": "tan", "emoji": None, "custom_id": "tan", "disabled": True},
            {"style": 1, "label": "+", "emoji": None, "custom_id": "+", "disabled": True},
            {
                "style": 4,
                "label": _("Clear").format(**locals()),
                "emoji": None,
                "custom_id": "clear_button",
                "disabled": True,
            },
            {
                "style": 2,
                "label": None,
                "emoji": "📄",
                "custom_id": "history_button",
                "disabled": True,
            },
            {"style": 2, "label": "In", "emoji": None, "custom_id": "In", "disabled": True},
            {"style": 2, "label": "√", "emoji": None, "custom_id": "√", "disabled": True},
            {"style": 1, "label": "-", "emoji": None, "custom_id": "-", "disabled": True},
            {
                "style": 3,
                "label": "=",
                "emoji": None,
                "custom_id": "result_button",
                "disabled": True,
            },
            {"style": 2, "label": "(", "emoji": None, "custom_id": "(", "disabled": True},
            {"style": 2, "label": ")", "emoji": None, "custom_id": ")", "disabled": True},
            {"style": 2, "label": None, "emoji": "👨‍🏫", "custom_id": "mode_button", "disabled": True},
            {
                "style": 3,
                "label": "<",
                "emoji": None,
                "custom_id": "left_button",
                "disabled": True,
            },
            {
                "style": 3,
                "label": ">",
                "emoji": None,
                "custom_id": "right_button",
                "disabled": True,
            },
        ]

        self.history: typing.Dict[
            typing.Union[discord.Member, discord.User], typing.List[str]
        ] = {}

        self.cogsutils = CogsUtils(cog=self)
        self.cogsutils._setup()

    async def calculate(self, expression: str):
        lst = list(expression)
        try:
            lst.remove("|")
        except Exception:
            pass
        expression = "".join(lst)
        expression = expression.replace(",", ".")
        expression = expression.replace(":", "/")
        expression = expression.replace(" ", "")
        expression = expression.replace("π", str(pi))
        expression = expression.replace("pi", str(pi))
        expression = expression.replace("τ", str(tau))
        expression = expression.replace("tau", str(tau))
        expression = expression.replace("e", str(e))
        expression = expression.replace("x", "*")
        expression = expression.replace("÷", "/")
        expression = expression.replace("**2", "^2")
        expression = expression.replace("**3", "^3")
        expression = expression.replace("**", "^")
        expression = expression.replace("√", "sqrt")
        expression = expression.replace(",", "")
        for x in self.x:
            if self.x[x] in expression:
                expression = expression.replace(self.x[x], f"^{x}")
        if "sqrt" in expression and "^" not in expression:
            expression = expression.replace("^2", "**2")
            expression = expression.replace("^3", "**3")
            expression = expression.replace("^", "**")
            try:
                result = f"{eval(expression)}"
            except Exception:
                result = None
        else:
            engine_input = "{m:" + expression + "}"
            result = self.engine.process(engine_input).body
            result = result.replace("{m:", "").replace("}", "")
        try:
            result = f"{float(result):,}"
            if result == "inf":
                result = "∞"
        except Exception:
            result = None
        if result is not None:
            result = f"{result}"
        else:
            result = _("Error!").format(**locals())
        return result

    async def get_embed(self, ctx: commands.Context, expression: str, result: str):
        if expression == "":
            expression = None
        if expression is None:
            expression = "|"
        config = await self.config.settings.all()
        actual_color = config["color"]
        actual_thumbnail = config["thumbnail"]
        embed: discord.Embed = discord.Embed()
        embed.title = _("{ctx.me.display_name}'s Calculator").format(**locals())
        if result is None:
            embed.description = box(f"{str(expression)}", lang="fix")
        else:
            expression = str(expression).replace("|", "")
            embed.description = box(f"> {str(expression)}", lang="fix") + box(f"= {str(result)}", lang="fix") + "\n"
        embed.set_thumbnail(url=actual_thumbnail)
        embed.color = actual_color
        embed.timestamp = datetime.datetime.now(tz=datetime.timezone.utc)
        if ctx.guild:
            embed.set_footer(
                text=ctx.guild.name,
                icon_url=ctx.guild.icon or ""
                if self.cogsutils.is_dpy2
                else ctx.guild.icon_url or "",
            )
        else:
            embed.set_footer(
                text=ctx.author.name,
                icon_url=ctx.author.display_avatar
                if self.cogsutils.is_dpy2
                else ctx.author.avatar_url,
            )
        return embed

    async def input_formatter(self, expression: str, new: str):
        if expression is None:
            expression = "|"
        lst = list(expression)
        try:
            index = lst.index("|")
            lst.remove("|")
        except Exception:
            index = 0
        if new in ["abs", "cos", "sin", "tan", "In", "√"]:
            lst.insert(index, new + "(")
            lst.insert(index + 1, ")")
        elif new == 'X²':
            lst.insert(index, "²")
        elif new == 'X³':
            lst.insert(index, "³")
        elif new == 'Xˣ':
            lst.insert(index, "^")
        else:
            if len(lst) > 1 and lst[index - 1] == "^":
                try:
                    lst.insert(index, self.x[new])
                    lst.remove("^")
                    index -= 1
                except Exception:
                    lst.insert(index, new)
            else:
                lst.insert(index, new)
        lst.insert(index + 1, "|")
        expression = "".join(lst)
        return expression

    async def get_buttons(self, disabled: bool):
        buttons_one = ActionRow(
            Button(
                style=ButtonStyle.grey, label="1", emoji=None, custom_id="1", disabled=disabled
            ),
            Button(
                style=ButtonStyle.grey, label="2", emoji=None, custom_id="2", disabled=disabled
            ),
            Button(
                style=ButtonStyle.grey, label="3", emoji=None, custom_id="3", disabled=disabled
            ),
            Button(
                style=ButtonStyle.blurple, label="x", emoji=None, custom_id="x", disabled=disabled
            ),
            Button(
                style=ButtonStyle.red,
                label=_("Exit").format(**locals()),
                emoji=None,
                custom_id="exit_button",
                disabled=disabled,
            ),
        )
        buttons_two = ActionRow(
            Button(
                style=ButtonStyle.grey, label="4", emoji=None, custom_id="4", disabled=disabled
            ),
            Button(
                style=ButtonStyle.grey, label="5", emoji=None, custom_id="5", disabled=disabled
            ),
            Button(
                style=ButtonStyle.grey, label="6", emoji=None, custom_id="6", disabled=disabled
            ),
            Button(
                style=ButtonStyle.blurple, label="÷", emoji=None, custom_id="÷", disabled=disabled
            ),
            Button(
                style=ButtonStyle.red,
                label="⌫",
                emoji=None,
                custom_id="back_button",
                disabled=disabled,
            ),
        )
        buttons_three = ActionRow(
            Button(
                style=ButtonStyle.grey, label="7", emoji=None, custom_id="7", disabled=disabled
            ),
            Button(
                style=ButtonStyle.grey, label="8", emoji=None, custom_id="8", disabled=disabled
            ),
            Button(
                style=ButtonStyle.grey, label="9", emoji=None, custom_id="9", disabled=disabled
            ),
            Button(
                style=ButtonStyle.blurple, label="+", emoji=None, custom_id="+", disabled=disabled
            ),
            Button(
                style=ButtonStyle.red,
                label=_("Clear").format(**locals()),
                emoji=None,
                custom_id="clear_button",
                disabled=disabled,
            ),
        )
        buttons_four = ActionRow(
            Button(
                style=ButtonStyle.grey,
                label="📄",
                emoji=None,
                custom_id="history_button",
                disabled=disabled,
            ),
            Button(
                style=ButtonStyle.grey, label="0", emoji=None, custom_id="0", disabled=disabled
            ),
            Button(
                style=ButtonStyle.grey, label=".", emoji=None, custom_id=".", disabled=disabled
            ),
            Button(
                style=ButtonStyle.blurple, label="-", emoji=None, custom_id="-", disabled=disabled
            ),
            Button(
                style=ButtonStyle.green,
                label="=",
                emoji=None,
                custom_id="result_button",
                disabled=disabled,
            ),
        )
        buttons_five = ActionRow(
            Button(
                style=ButtonStyle.grey, label="(", emoji=None, custom_id="(", disabled=disabled
            ),
            Button(
                style=ButtonStyle.grey, label=")", emoji=None, custom_id=")", disabled=disabled
            ),
            Button(
                style=ButtonStyle.grey, label="√", emoji=None, custom_id="√", disabled=disabled
            ),
            Button(
                style=ButtonStyle.green,
                label="<",
                emoji=None,
                custom_id="left_button",
                disabled=disabled,
            ),
            Button(
                style=ButtonStyle.green,
                label=">",
                emoji=None,
                custom_id="right_button",
                disabled=disabled,
            ),
        )
        return buttons_one, buttons_two, buttons_three, buttons_four, buttons_five

    @hybrid_command(name="calculate", aliases=["calc"])
    async def _calculate(self, ctx: commands.Context, calculation: typing.Optional[str] = None):
        """Calculate a simple expression."""
        config = await self.config.settings.all()
        if calculation is not None:
            result = f"{await self.calculate(calculation)}"
            if ctx.author not in self.history:
                self.history[ctx.author] = []
            self.history[ctx.author].append(
                (calculation.replace("|", ""), result.replace("|", ""))
            )
            message = await ctx.send(embed=await self.get_embed(ctx, calculation, result))
            return
        expression = None
        result = None
        is_normal = True
        if self.cogsutils.is_dpy2:
            view = Buttons(
                timeout=config["time_max"],
                buttons=self.normal_buttons_dict if is_normal else self.scientist_buttons_dict,
                members=[ctx.author] + list(ctx.bot.owner_ids),
            )
            message = await ctx.send(
                embed=await self.get_embed(ctx, expression, result), view=view
            )
        else:
            (
                buttons_one,
                buttons_two,
                buttons_three,
                buttons_four,
                buttons_five,
            ) = await self.get_buttons(False)
            message = await ctx.send(
                embed=await self.get_embed(ctx, expression, result),
                components=[buttons_one, buttons_two, buttons_three, buttons_four, buttons_five],
            )
        if self.cogsutils.is_dpy2:
            try:
                while True:
                    interaction, function_result = await view.wait_result()
                    if result == _("Error!").format(**locals()) or result == "∞" or result == "":
                        result = None
                    if result is not None:
                        if not interaction.data["custom_id"] == "result_button":
                            expression = f"{result}|"
                            result = None
                    if (
                        expression is None
                        or expression == _("Error!").format(**locals())
                        or expression == "∞"
                        or expression == ""
                    ):
                        expression = "|"
                    if interaction.data["custom_id"] == "result_button":
                        result = f"{await self.calculate(expression)}"
                        if ctx.author not in self.history:
                            self.history[ctx.author] = []
                        self.history[ctx.author].append(
                            (expression.replace("|", ""), result.replace("|", ""))
                        )
                    elif interaction.data["custom_id"] == "exit_button":
                        view = Buttons(
                            timeout=config["time_max"],
                            buttons=self.disabled_normal_buttons_dict if is_normal else self.disabled_scientist_buttons_dict,
                            members=[],
                        )
                        await interaction.response.edit_message(view=view)
                        return
                    elif interaction.data["custom_id"] == "clear_button":
                        expression = None
                        result = None
                    elif interaction.data["custom_id"] == "back_button":
                        lst = list(expression)
                        if len(lst) > 1:
                            try:
                                index = lst.index("|")
                                lst.pop(index - 1)
                                expression = "".join(lst)
                            except Exception:
                                expression = None
                    elif interaction.data["custom_id"] == "left_button":
                        lst = list(expression)
                        if len(lst) > 1:
                            try:
                                index = lst.index("|")
                                lst.remove("|")
                                lst.insert(index - 1, "|")
                            except Exception:
                                lst = ["|"]
                        expression = "".join(lst)
                        if expression == "|":
                            expression = None
                    elif interaction.data["custom_id"] == "right_button":
                        lst = list(expression)
                        if len(lst) > 1:
                            try:
                                index = lst.index("|")
                                lst.remove("|")
                                lst.insert(index + 1, "|")
                            except Exception:
                                lst = ["|"]
                        expression = "".join(lst)
                        if expression == "|":
                            expression = None
                    elif interaction.data["custom_id"] == "mode_button":
                        is_normal = not is_normal
                    elif interaction.data["custom_id"] == "history_button":
                        embed: discord.Embed = discord.Embed()
                        embed.title = f"{ctx.author.display_name}'s history"
                        history = self.history.get(ctx.author, [])[-25:]
                        history.reverse()
                        if len(history) == 0:
                            embed.description = _("Nothing in your history.").format(**locals())
                        else:
                            for count, entry in enumerate(history, start=0):
                                all_count = list(range(1, len(self.history.get(ctx.author, [])) + 1))
                                all_count.reverse()
                                count = all_count[count]
                                _expression, _result = entry
                                embed.add_field(name=f"Entry {count}:", value=box(f"> {str(_expression)}", lang="fix") + box(f"= {str(_result)}", lang="fix") + "\n")
                        await interaction.response.send_message(embed=embed, ephemeral=True)
                        view = Buttons(
                            timeout=config["time_max"],
                            buttons=self.normal_buttons_dict if is_normal else self.scientist_buttons_dict,
                            members=[ctx.author] + list(ctx.bot.owner_ids),
                        )
                        await interaction.message.edit(view=view)
                        continue
                    else:
                        expression = await self.input_formatter(
                            expression, str(interaction.data["custom_id"])
                        )
                    view = Buttons(
                        timeout=config["time_max"],
                        buttons=self.normal_buttons_dict if is_normal else self.scientist_buttons_dict,
                        members=[ctx.author] + list(ctx.bot.owner_ids),
                    )
                    await interaction.response.edit_message(
                        embed=await self.get_embed(ctx, expression, result), view=view
                    )
            except TimeoutError:
                view = Buttons(
                    timeout=config["time_max"], buttons=self.disabled_normal_buttons_dict if is_normal else self.disabled_scientist_buttons_dict, members=[]
                )
                await message.edit(view=view)
                return
        else:

            def check(inter):
                return (
                    inter.guild == ctx.guild
                    and inter.channel == ctx.channel
                    and inter.message.id == message.id
                )

            try:
                while True:
                    inter = await ctx.wait_for_button_click(
                        timeout=config["time_max"], check=check
                    )
                    if not inter.author == ctx.author and ctx.author.id not in ctx.bot.owner_ids:
                        await inter.respond(
                            _(
                                "Only the author of the command `{ctx.prefix}{ctx.command.name}` can interact with this message."
                            ).format(**locals()),
                            ephemeral=True,
                        )
                        continue
                    if result == _("Error!").format(**locals()) or result == "∞" or result == "":
                        result = None
                    if result is not None:
                        if not inter.clicked_button.custom_id == "result_button":
                            expression = f"{result}|"
                            result = None
                    if (
                        expression is None
                        or expression == _("Error!").format(**locals())
                        or expression == "∞"
                        or expression == ""
                    ):
                        expression = "|"
                    if inter.clicked_button.custom_id == "result_button":
                        result = f"{await self.calculate(expression)}"
                        if ctx.author not in self.history:
                            self.history[ctx.author] = []
                        self.history[ctx.author].append(
                            (expression.replace("|", ""), result.replace("|", ""))
                        )
                    elif inter.clicked_button.custom_id == "exit_button":
                        (
                            buttons_one,
                            buttons_two,
                            buttons_three,
                            buttons_four,
                            buttons_five,
                        ) = await self.get_buttons(True)
                        await message.edit(
                            components=[
                                buttons_one,
                                buttons_two,
                                buttons_three,
                                buttons_four,
                                buttons_five,
                            ]
                        )
                        await inter.respond(type=ResponseType.DeferredUpdateMessage)
                        return
                    elif inter.clicked_button.custom_id == "clear_button":
                        expression = None
                        result = None
                    elif inter.clicked_button.custom_id == "back_button":
                        lst = list(expression)
                        if len(lst) > 1:
                            try:
                                index = lst.index("|")
                                lst.pop(index - 1)
                                expression = "".join(lst)
                            except Exception:
                                expression = None
                    elif inter.clicked_button.custom_id == "left_button":
                        lst = list(expression)
                        if len(lst) > 1:
                            try:
                                index = lst.index("|")
                                lst.remove("|")
                                lst.insert(index - 1, "|")
                            except Exception:
                                lst = ["|"]
                        expression = "".join(lst)
                        if expression == "|":
                            expression = None
                    elif inter.clicked_button.custom_id == "right_button":
                        lst = list(expression)
                        if len(lst) > 1:
                            try:
                                index = lst.index("|")
                                lst.remove("|")
                                lst.insert(index + 1, "|")
                            except Exception:
                                lst = ["|"]
                        expression = "".join(lst)
                        if expression == "|":
                            expression = None
                    elif inter.clicked_button.custom_id == "mode_button":
                        is_normal = not is_normal
                    elif inter.clicked_button.custom_id == "history_button":
                        embed: discord.Embed = discord.Embed()
                        embed.title = f"{ctx.author.display_name}'s history"
                        history = self.history.get(ctx.author, [])[-25:]
                        history.reverse()
                        if len(history) == 0:
                            embed.description = _("Nothing in your history.").format(**locals())
                        else:
                            for count, entry in enumerate(history, start=0):
                                all_count = list(range(1, len(self.history.get(ctx.author, [])) + 1))
                                all_count.reverse()
                                count = all_count[count]
                                _expression, _result = entry
                                embed.add_field(name=f"Entry {count}:", value=box(f"> {str(_expression)}", lang="fix") + box(f"= {str(_result)}", lang="fix") + "\n")
                        await inter.respond(embed=embed, ephemeral=True)
                        continue
                    else:
                        expression = await self.input_formatter(
                            expression, str(inter.clicked_button.custom_id)
                        )
                    await message.edit(embed=await self.get_embed(ctx, expression, result))
                    await inter.respond(type=ResponseType.DeferredUpdateMessage)
            except asyncio.TimeoutError:
                (
                    buttons_one,
                    buttons_two,
                    buttons_three,
                    buttons_four,
                    buttons_five,
                ) = await self.get_buttons(True)
                await message.edit(
                    components=[
                        buttons_one,
                        buttons_two,
                        buttons_three,
                        buttons_four,
                        buttons_five,
                    ]
                )
                return

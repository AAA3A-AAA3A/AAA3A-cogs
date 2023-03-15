from .AAA3A_utils import CogsUtils  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
from redbot.core.bot import Red  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

if CogsUtils().is_dpy2:
    from .view import CalculatorView  # isort:skip
else:
    from dislash import ActionRow, Button, ButtonStyle, ResponseType  # isort:skip

import asyncio
import datetime
from math import *

from redbot.core import Config
from redbot.core.utils.chat_formatting import box
from TagScriptEngine import Interpreter, block

# Credits:
# General repo credits.
# Thanks to Yami for the technique in the init file of some cogs to load the interaction client only if it is not already loaded! Before this fix, when a user clicked a button, the actions would be run about 10 times, causing a huge spam and loop in the channel.

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

    def __init__(self, bot: Red) -> None:
        self.bot: Red = bot

        self.config: Config = Config.get_conf(
            self,
            identifier=205192943327321000143939875896557571750,  # 905683670375
            force_registration=True,
        )
        self.calculator_global: typing.Dict[str, typing.Dict[str, typing.Union[int, str]]] = {
            "settings": {
                "time_max": 180,
                "color": 0x01D758,
                "thumbnail": "https://cdn.pixabay.com/photo/2017/07/06/17/13/calculator-2478633_960_720.png",
            },
        }
        self.config.register_global(**self.calculator_global)

        blocks: typing.List[block.Block] = [
            block.MathBlock(),
            block.RandomBlock(),
            block.RangeBlock(),
        ]
        self.engine: Interpreter = Interpreter(blocks)
        self.x: typing.Dict[str, str] = {
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
        self.history: typing.Dict[
            typing.Union[discord.Member, discord.User], typing.Tuple[str]
        ] = {}

        self.cogsutils: CogsUtils = CogsUtils(cog=self)

    async def calculate(self, expression: str) -> str:
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
            result = _("Error!")
        return result

    async def get_embed(
        self, ctx: commands.Context, expression: str, result: str
    ) -> discord.Embed:
        if expression == "":
            expression = None
        if expression is None:
            expression = "|"
        config = await self.config.settings.all()
        actual_color = config["color"]
        actual_thumbnail = config["thumbnail"]
        embed: discord.Embed = discord.Embed()
        embed.title = _("{ctx.me.display_name}'s Calculator").format(ctx=ctx)
        if result is None:
            embed.description = box(f"{str(expression)}", lang="fix")
        else:
            expression = str(expression).replace("|", "")
            embed.description = (
                box(f"> {str(expression)}", lang="fix")
                + box(f"= {str(result)}", lang="fix")
                + "\n"
            )
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

    async def input_formatter(self, expression: str, new: str) -> str:
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
        elif new == "X²":
            lst.insert(index, "²")
        elif new == "X³":
            lst.insert(index, "³")
        elif new == "Xˣ":
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

    async def get_buttons(self, disabled: bool) -> typing.Tuple:
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
                label=_("Exit"),
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
                label=_("Clear"),
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
    async def _calculate(
        self, ctx: commands.Context, calculation: typing.Optional[str] = None
    ) -> None:
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
        if self.cogsutils.is_dpy2:
            await CalculatorView(cog=self).start(ctx)
            return
        expression = None
        result = None
        is_normal = True
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

        def check(inter):
            return (
                inter.guild == ctx.guild
                and inter.channel == ctx.channel
                and inter.message.id == message.id
            )

        try:
            while True:
                inter = await ctx.wait_for_button_click(timeout=config["time_max"], check=check)
                if not inter.author == ctx.author and ctx.author.id not in ctx.bot.owner_ids:
                    await inter.respond(
                        _(
                            "Only the author of the command `{ctx.prefix}{ctx.command.name}` can interact with this message."
                        ).format(ctx=ctx),
                        ephemeral=True,
                    )
                    continue
                if result == _("Error!") or result == "∞" or result == "":
                    result = None
                if result is not None:
                    if not inter.clicked_button.custom_id == "result_button":
                        expression = f"{result}|"
                        result = None
                if (
                    expression is None
                    or expression == _("Error!")
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
                    try:
                        await inter.respond(type=ResponseType.DeferredUpdateMessage)
                    except discord.HTTPException:
                        pass
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
                        embed.description = _("Nothing in your history.")
                    else:
                        for count, entry in enumerate(history, start=0):
                            all_count = list(range(1, len(self.history.get(ctx.author, [])) + 1))
                            all_count.reverse()
                            count = all_count[count]
                            _expression, _result = entry
                            embed.add_field(
                                name=f"Entry {count}:",
                                value=box(f"> {str(_expression)}", lang="fix")
                                + box(f"= {str(_result)}", lang="fix")
                                + "\n",
                            )
                    await inter.respond(embed=embed, ephemeral=True)
                    continue
                else:
                    expression = await self.input_formatter(
                        expression, str(inter.clicked_button.custom_id)
                    )
                await message.edit(embed=await self.get_embed(ctx, expression, result))
                try:
                    await inter.respond(type=ResponseType.DeferredUpdateMessage)
                except discord.HTTPException:
                    pass
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

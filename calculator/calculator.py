from AAA3A_utils import Cog, CogsUtils  # isort:skip
from redbot.core import commands, Config  # isort:skip
from redbot.core.bot import Red  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

from .view import CalculatorView  # isort:skip

import datetime
from math import e, pi, tau

from redbot.core.utils.chat_formatting import box
from TagScriptEngine import Interpreter, block

# Credits:
# General repo credits.
# Thanks to Yami for the technique in the init file of some cogs to load the interaction client only if it is not already loaded! Before this fix, when a user clicked a button, the actions would be run about 10 times, causing a huge spam and loop in the channel.

_ = Translator("Calculator", __file__)


@cog_i18n(_)
class Calculator(Cog):
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
        return f"{result}" if result is not None else _("Error!")

    async def get_embed(
        self, ctx: commands.Context, expression: str, result: str
    ) -> discord.Embed:
        if not expression:
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
                box(f"> {expression}", lang="fix") + box(f"= {result}", lang="fix")
            ) + "\n"
        embed.set_thumbnail(url=actual_thumbnail)
        embed.color = actual_color
        embed.timestamp = datetime.datetime.now(tz=datetime.timezone.utc)
        if ctx.guild:
            embed.set_footer(
                text=ctx.guild.name,
                icon_url=ctx.guild.icon
            )
        else:
            embed.set_footer(
                text=ctx.author.name,
                icon_url=ctx.author.display_avatar
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
        if new in {"abs", "cos", "sin", "tan", "In", "√"}:
            lst.insert(index, f"{new}(")
            lst.insert(index + 1, ")")
        elif new == "X²":
            lst.insert(index, "²")
        elif new == "X³":
            lst.insert(index, "³")
        elif new == "Xˣ":
            lst.insert(index, "^")
        elif len(lst) > 1 and lst[index - 1] == "^":
            try:
                lst.insert(index, self.x[new])
                lst.remove("^")
                index -= 1
            except Exception:
                lst.insert(index, new)
        else:
            lst.insert(index, new)
        lst.insert(index + 1, "|")
        return "".join(lst)

    @commands.hybrid_command(name="calculate", aliases=["calc"])
    async def _calculate(self, ctx: commands.Context, *, calculation: str = None) -> None:
        """Calculate a simple expression."""
        if calculation is not None:
            result = f"{await self.calculate(calculation)}"
            if ctx.author not in self.history:
                self.history[ctx.author] = []
            self.history[ctx.author].append(
                (calculation.replace("|", ""), result.replace("|", ""))
            )
            await ctx.send(embed=await self.get_embed(ctx, calculation, result))
            return
        await CalculatorView(cog=self).start(ctx)

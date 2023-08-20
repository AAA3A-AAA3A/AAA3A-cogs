from AAA3A_utils import Cog, CogsUtils  # isort:skip
from redbot.core import commands, Config  # isort:skip
from redbot.core.bot import Red  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

from .view import CalculatorView  # isort:skip

import datetime

from expr import EvaluatorError, evaluate
from expr.builtin import pi, tau
from redbot.core.utils.chat_formatting import box

# from TagScriptEngine import Interpreter, block


# Credits:
# General repo credits.
# Thanks to Yami for the technique in the init file of some cogs to load the interaction client only if it is not already loaded! Before this fix, when a user clicked a button, the actions would be run about 10 times, causing a huge spam and loop in the channel.
# Thanks to Flame for fixing an RCE in the cog!

_ = Translator("Calculator", __file__)


@cog_i18n(_)
class Calculator(Cog):
    """A cog to do calculations from Discord with buttons!"""

    def __init__(self, bot: Red) -> None:
        super().__init__(bot=bot)

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

        # blocks: typing.List[block.Block] = [
        #     block.MathBlock(),
        #     block.RandomBlock(),
        #     block.RangeBlock(),
        # ]
        # self.engine: Interpreter = Interpreter(blocks)
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

        self.cache: typing.List[discord.Message] = []

    async def red_delete_data_for_user(self, *args, **kwargs) -> None:
        """Nothing to delete."""
        return

    async def red_get_data_for_user(self, *args, **kwargs) -> typing.Dict[str, typing.Any]:
        """Nothing to get."""
        return {}

    async def calculate(self, expression: str) -> str:
        lst = list(expression)
        try:
            lst.remove("|")
        except Exception:
            pass
        expression = "".join(lst)
        expression = expression.replace(",", ".")
        expression = expression.replace(" ", "")
        expression = expression.replace(":", "/")
        expression = expression.replace("÷", "/")
        expression = expression.replace("**", "^")
        expression = expression.replace("x", "*")
        expression = expression.replace("√", "sqrt")
        for x in self.x:
            if self.x[x] in expression:
                expression = expression.replace(self.x[x], f"^{x}")
        builtins = {
            "abs": abs,
        }
        constants = {
            "π": pi,
            "τ": tau,
        }
        try:
            result = evaluate(expression, builtins=builtins, constants=constants)
        except (
            EvaluatorError,
            TypeError,
        ):  # TypeError: 'Token' object is not subscriptable, for `A(5)`.
            result = None
        # if "sqrt" in expression and "^" not in expression:
        #     ...
        # else:
        #     engine_input = "{m:" + expression + "}"
        #     result = self.engine.process(engine_input).body
        #     result = result.replace("{m:", "").replace("}", "")
        try:
            result = f"{float(result):,}"
            if result == "inf":
                result = "∞"
        except Exception:
            result = None
        return f"{result}".replace(",", " ") if result is not None else _("Error!")

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
            embed.set_footer(text=ctx.guild.name, icon_url=ctx.guild.icon)
        else:
            embed.set_footer(text=ctx.author.name, icon_url=ctx.author.display_avatar)
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
        if new in {"abs", "cos", "sin", "tan", "ln", "√"}:
            lst.insert(index, f"{new}(")
            lst.insert(index + 1, ")")
        elif new == "X²":
            lst.insert(index, "²")
        elif new == "X³":
            lst.insert(index, "³")
        elif new == "Xˣ":
            # lst.insert(index, "^")
            lst.insert(index, "^(")
            lst.insert(index + 1, ")")
        # elif len(lst) > 1 and lst[index - 1] == "^":
        #     try:
        #         lst.insert(index, self.x[new])
        #         lst.remove("^")
        #         index -= 1
        #     except Exception:
        #         lst.insert(index, new)
        else:
            lst.insert(index, new)
        lst.insert(index + 1, "|")
        return "".join(lst)

    @commands.bot_has_permissions(embed_links=True)
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

    @commands.Cog.listener()
    async def on_message_without_command(self, message: discord.Message) -> None:
        if await self.bot.cog_disabled_in_guild(
            cog=self, guild=message.guild
        ) or not await self.bot.allowed_by_whitelist_blacklist(who=message.author):
            return
        if message.webhook_id is not None or message.author.bot:
            return
        if not message.content or message.content.replace(" ", "").isdecimal():
            return
        if not await discord.utils.async_all(
            check(await self.bot.get_context(message)) for check in self._calculate.checks
        ):
            return
        if (result := await self.calculate(message.content)) == _("Error!") or result == message.content:
            return
        if message.guild is not None:
            channel_permissions = message.channel.permissions_for(message.guild.me)
            if not channel_permissions.add_reactions or not channel_permissions.send_messages:
                return
        try:
            await message.add_reaction("🔢")
        except discord.HTTPException:
            pass
        finally:
            self.cache.append(message)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
        if str(payload.emoji).strip("\N{VARIATION SELECTOR-16}") != "🔢":
            return
        if (message := discord.utils.get(self.cache, channel__id=payload.channel_id, id=payload.message_id)) is None:
            return
        if payload.user_id != message.author.id:
            return
        self.cache.remove(message)
        if sorted([user.id async for user in discord.utils.get((await message.channel.fetch_message(message.id)).reactions, emoji="🔢").users() if user.bot]).index(self.bot.user.id) != 0:
            return
        await CogsUtils.invoke_command(
            bot=self.bot,
            author=message.author,
            channel=message.channel,
            command=f"calculate {message.content}",
            message=message,
        )

from AAA3A_utils import Cog, CogsUtils, Settings  # isort:skip
from redbot.core import commands, Config  # isort:skip
from redbot.core.bot import Red  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import datetime

from expr import EvaluatorError, evaluate
from expr.builtin import pi, tau
from redbot.core.utils.chat_formatting import box

from .view import CalculatorView  # isort:skip

# from TagScriptEngine import Interpreter, block


# Credits:
# General repo credits.
# Thanks to Yami for the technique in the init file of some cogs to load the interaction client only if it is not already loaded! Before this fix, when a user clicked a button, the actions would be run about 10 times, causing a huge spam and loop in the channel.
# Thanks to Flame for fixing an RCE in the cog!

_: Translator = Translator("Calculator", __file__)


@cog_i18n(_)
class Calculator(Cog):
    """A cog to do calculations from Discord with buttons!"""

    def __init__(self, bot: Red) -> None:
        super().__init__(bot=bot)

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

        self.config: Config = Config.get_conf(
            self,
            identifier=205192943327321000143939875896557571750,  # 905683670375
            force_registration=True,
        )
        self.config.register_guild(
            auto_calculations=None,
            auto_calculations_ignored_channels=[],
            react_calculations=None,
            react_calculations_ignored_channels=[],
            simple_embed=None,
            result_codeblock=None,
            calculate_reaction_enabled=True,  # calculate reaction default state
        )
        self.config.register_global(
            default_react_calculations=True,
            default_auto_calculations=False,
            default_simple_embed=False,
            default_result_codeblock=True,
        )

        _settings: typing.Dict[str, typing.Dict[str, typing.Any]] = {
            "auto_calculations": {
                "converter": bool,
                "description": "Toggle the auto calculations.",
            },
            "auto_calculations_ignored_channels": {
                "converter": commands.Greedy[typing.Union[discord.TextChannel, discord.VoiceChannel, discord.Thread, discord.CategoryChannel]],
                "description": "The channels to ignore for the auto calculations.",
            },
            "react_calculations": {
                "converter": bool,
                "description": "Toggle the reaction calculations.",
            },
            "react_calculations_ignored_channels": {
                "converter": commands.Greedy[typing.Union[discord.TextChannel, discord.VoiceChannel, discord.Thread, discord.CategoryChannel]],
                "description": "The channels to ignore for the reaction calculations.",
            },
            "simple_embed": {
                "converter": bool,
                "description": "Toggle the simple embed mode.",
            },
            "result_codeblock": {
                "converter": bool,
                "description": "Toggle the codeblock mode.",
            },
            "calculate_reaction_enabled": {
                "converter": bool,
                "description": "Toggle the calculate reaction feature.",
            },
        }
        self.settings: Settings = Settings(
            bot=self.bot,
            cog=self,
            config=self.config,
            group=self.config.GUILD,
            settings=_settings,
            global_path=[],
            use_profiles_system=False,
            can_edit=True,
            commands_group=self.setcalculator,
        )

    async def cog_load(self) -> None:
        await super().cog_load()
        await self.settings.add_commands()

    async def calculate(self, expression: str) -> str:
        lst = list(expression)
        try:
            lst.remove("|")
        except ValueError:
            pass
        expression = "".join(lst)
        expression = expression.replace(",", ".")
        expression = expression.replace(" ", "")
        expression = expression.replace(":", "/")
        expression = expression.replace("÷", "/")
        expression = expression.replace("**", "^")
        expression = expression.replace("x", "*")
        expression = expression.replace("√", "sqrt")
        expression = expression.replace("e", "E")
        for x in self.x:
            if self.x[x] in expression:
                expression = expression.replace(self.x[x], f"^{x}")
        builtins = {
            "abs": abs,
            # "min": min,
            # "max": max,
        }
        constants = {
            "π": pi,
            "τ": tau,
            "k": 1_000,
        }
        suffixes = [
            "k",
            "m",
            "b",
            "t",
            "q",
            "Q",
            "s",
            "S",
            "o",
            "n",
            "d",
            "U",
            "D",
            "T",
            "Qa",
            "Qi",
            "Sx",
            "Sp",
            "Oc",
            "No",
            "Vi",
        ]  # ["k", "M", "B", "T", "P", "E", "Z", "Y"]
        number = 1000
        for suffix in suffixes:
            constants[suffix] = number
            number *= 1000
        try:
            result = evaluate(
                expression,
                builtins=builtins,
                constants=constants,
                max_safe_number=9e1000,  # 9e9
                max_exponent=2_097_152,  # 128 * 128 * 128
                max_factorial=262_144,  # 64 * 64 * 64
            )
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
        except (ValueError, TypeError, OverflowError):
            result = None
        return f"{result}".replace(",", " ") if result is not None else _("Error!")

    async def get_embed(
        self, ctx: commands.Context, expression: typing.Optional[str], result: typing.Optional[str]
    ) -> discord.Embed:
        if not expression:
            expression = None
        if expression is None:
            expression = "|"
        embed: discord.Embed = discord.Embed(
            title=_("{ctx.me.display_name}'s Calculator").format(ctx=ctx),
            color=await ctx.embed_color(),
        )
        result_codeblock = await self.config.guild(ctx.guild).result_codeblock() if ctx.guild is not None else None
        if result_codeblock is None:
            result_codeblock = await self.config.default_result_codeblock()
        if result is None:
            embed.description = box(f"{str(expression)}", lang="fix") if result_codeblock else f"`{str(expression)}`"
        else:
            expression = str(expression).replace("|", "")
            if result_codeblock:
                embed.description = (
                    box(f"> {expression}", lang="fix") + box(f"= {result}", lang="fix")
                )
            else:
                embed.description = f"`> {expression}`\n= **{result}**"
        simple_embed = await self.config.guild(ctx.guild).simple_embed() if ctx.guild is not None else None
        if simple_embed is None:
            simple_embed = await self.config.default_simple_embed()
        if not simple_embed:
            embed.set_thumbnail(url="https://cdn.pixabay.com/photo/2017/07/06/17/13/calculator-2478633_960_720.png")
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
        except ValueError:
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
            calculation = calculation.replace(",", ".")
            result = f"{await self.calculate(calculation)}"
            if ctx.author not in self.history:
                self.history[ctx.author] = []
            self.history[ctx.author].append(
                (calculation.replace("|", ""), result.replace("|", ""))
            )
            await ctx.send(
                embed=await self.get_embed(ctx, calculation, result),
                reference=ctx.message.to_reference(fail_if_not_exists=False),
                allowed_mentions=discord.AllowedMentions.none(),
            )
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
        auto_calculations = await self.config.guild(message.guild).auto_calculations() if message.guild is not None else None
        if auto_calculations is None:
            auto_calculations = await self.config.default_auto_calculations()
        react_calculations = await self.config.guild(message.guild).react_calculations() if message.guild is not None else None
        if react_calculations is None:
            react_calculations = await self.config.default_react_calculations()
        if not auto_calculations and not react_calculations:
            return

        content_to_check = message.content.split("#")[0].replace(" ", "").lstrip("+-").strip().removesuffix(".")
        if (
            not content_to_check
            or content_to_check.isdecimal()
            or content_to_check
            in (
                "k",
                "m",
                "b",
                "t",
                "q",
                "Q",
                "s",
                "S",
                "o",
                "n",
                "d",
                "U",
                "D",
                "T",
                "Qa",
                "Qi",
                "Sx",
                "Sp",
                "Oc",
                "No",
                "Vi",
            )
        ):
            return
        fake_context = await CogsUtils.invoke_command(
            bot=self.bot,
            author=message.author,
            channel=message.channel,
            command=message.content,
            prefix="",
            invoke=False,
        )
        if fake_context.valid:  # Prevent CCs, aliases and tags from triggering.
            return
        if not await discord.utils.async_all(
            [check(await self.bot.get_context(message)) for check in self._calculate.checks]
        ):
            return
        if (result := await self.calculate(message.content)) == _(
            "Error!"
        ) or result == message.content:
            return

        auto_calculations_ignored_channels = await self.config.guild(message.guild).auto_calculations_ignored_channels() if message.guild is not None else []
        react_calculations_ignored_channels = await self.config.guild(message.guild).react_calculations_ignored_channels() if message.guild is not None else []
        if (
            auto_calculations
            and message.channel.id not in auto_calculations_ignored_channels
            and message.channel.category_id not in auto_calculations_ignored_channels
        ):
            await CogsUtils.invoke_command(
                bot=self.bot,
                author=message.author,
                channel=message.channel,
                command=f"calculate {message.content}",
                message=message,
            )
            return
        elif (
            react_calculations
            and message.channel.id not in react_calculations_ignored_channels
            and message.channel.category_id not in react_calculations_ignored_channels
        ):
            if message.guild is not None:
                channel_permissions = message.channel.permissions_for(message.guild.me)
                if not channel_permissions.add_reactions or not channel_permissions.send_messages:
                    return
            try:
                await message.add_reaction("🔢")
            except discord.HTTPException:
                pass
            else:
                self.cache.append(message)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
        if str(payload.emoji).strip("\N{VARIATION SELECTOR-16}") != "🔢":
            return
        guild = self.bot.get_guild(payload.guild_id)
        if guild:
            calculate_reaction_enabled = await self.config.guild(guild).calculate_reaction_enabled()
            if not calculate_reaction_enabled:
                return
        if (
            message := discord.utils.get(
                self.cache, channel__id=payload.channel_id, id=payload.message_id
            )
        ) is None:
            return
        if payload.user_id != message.author.id and payload.user_id not in self.bot.owner_ids:
            return
        self.cache.remove(message)
        if (
            sorted(
                [
                    user.id
                    async for user in discord.utils.get(
                        (await message.channel.fetch_message(message.id)).reactions, emoji="🔢"
                    ).users()
                    if user.bot
                ]
            ).index(self.bot.user.id)
            != 0
        ):
            return
        await CogsUtils.invoke_command(
            bot=self.bot,
            author=message.author,
            channel=message.channel,
            command=f"calculate {message.content}",
            message=message,
        )

    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    @commands.hybrid_group()
    async def setcalculator(self, ctx: commands.Context) -> None:
        """Commands to configure Calculator."""
        pass

    @commands.is_owner()
    @setcalculator.command()
    async def defaultreactcalculations(self, ctx: commands.Context, default_react_calculations: bool) -> None:
        """Set the default state of the react calculations."""
        await self.config.default_react_calculations.set(default_react_calculations)

    @commands.is_owner()
    @setcalculator.command()
    async def defaultautocalculations(self, ctx: commands.Context, default_auto_calculations: bool) -> None:
        """Set the default state of the auto calculations."""
        await self.config.default_auto_calculations.set(default_auto_calculations)

    @commands.is_owner()
    @setcalculator.command()
    async def defaultsimpleembed(self, ctx: commands.Context, default_simple_embed: bool) -> None:
        """Set the default state of the simple embed mode."""
        await self.config.default_simple_embed.set(default_simple_embed)

    @commands.is_owner()
    @setcalculator.command()
    async def defaultresultcodeblock(self, ctx: commands.Context, default_result_codeblock: bool) -> None:
        """Set the default state of the result codeblock mode."""
        await self.config.default_result_codeblock.set(default_result_codeblock)

    @commands.admin_or_permissions(manage_guild=True)
    @setcalculator.command()
    async def togglecalculatereaction(self, ctx: commands.Context):
        """Toggle the calculate reaction feature on or off."""
        current_state = await self.config.guild(ctx.guild).calculate_reaction_enabled()
        new_state = not current_state
        await self.config.guild(ctx.guild).calculate_reaction_enabled.set(new_state)
        state_str = "enabled" if new_state else "disabled"
        await ctx.send(f"The calculate reaction feature has been {state_str}.")

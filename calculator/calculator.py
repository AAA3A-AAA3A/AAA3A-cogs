from .AAA3A_utils.cogsutils import CogsUtils  # isort:skip
if CogsUtils().is_dpy2:
    from .AAA3A_utils.cogsutils import Buttons  # isort:skip
else:
    from dislash import ActionRow, Button, ButtonStyle  # isort:skip
from redbot.core import commands  # isort:skip
import discord  # isort:skip
import typing  # isort:skip
import asyncio
import datetime
from redbot.core import Config
from math import *
from TagScriptEngine import Interpreter, block

# Credits:
# Thanks to @epic guy on Discord for the basic syntax (command groups, commands) and also commands (await ctx.send, await ctx.author.send, await ctx.message.delete())!
# Thanks to @YamiKaitou on Discord for the technique in the init file to load the interaction client only if it is not loaded! Before this fix, when a user clicked on a button, the actions would be launched about 10 times, which caused huge spam and a loop in the channel.
# Thanks to the developers of the cogs I added features to as it taught me how to make a cog! (Chessgame by WildStriker, Captcha by Kreusada, Speak by Epic guy and Rommer by Dav)
# Thanks to all the people who helped me with some commands in the #coding channel of the redbot support server!

def _(untranslated: str):
    return untranslated

class Calculator(commands.Cog):
    """A cog to do simple calculations from Discord with buttons!"""

    def __init__(self, bot):
        self.bot = bot
        self.data: Config = Config.get_conf(
            self,
            identifier=905683670375,
            force_registration=True,
        )
        self.calculator_global = {
            "settings": {
                "time_max": 180,
                "color": 0x01d758,
                "thumbnail": "https://cdn.pixabay.com/photo/2017/07/06/17/13/calculator-2478633_960_720.png",
            },
        }

        self.data.register_global(**self.calculator_global)

        blocks = [
            block.MathBlock(),
            block.RandomBlock(),
            block.RangeBlock(),
        ]
        self.engine = Interpreter(blocks)

        self.x = {
            "1":"¹",
            "2":"²",
            "3":"³",
            "4":"⁴",
            "5":"⁵",
            "6":"⁶",
            "7":"⁷",
            "8":"⁸",
            "9":"⁹"
        }

        self.buttons_dict = [
                                {"style": 2, "label": "1", "emoji": None, "custom_id": "1", "disabled": False},
                                {"style": 2, "label": "2", "emoji": None, "custom_id": "2", "disabled": False},
                                {"style": 2, "label": "3", "emoji": None, "custom_id": "3", "disabled": False},
                                {"style": 1, "label": "x", "emoji": None, "custom_id": "x", "disabled": False},
                                {"style": 4, "label": _("Exit").format(**locals()), "emoji": None, "custom_id": "exit_button", "disabled": False},
                                {"style": 2, "label": "4", "emoji": None, "custom_id": "4", "disabled": False},
                                {"style": 2, "label": "5", "emoji": None, "custom_id": "5", "disabled": False},
                                {"style": 2, "label": "6", "emoji": None, "custom_id": "6", "disabled": False},
                                {"style": 1, "label": "÷", "emoji": None, "custom_id": "÷", "disabled": False},
                                {"style": 4, "label": "⌫", "emoji": None, "custom_id": "back_button", "disabled": False},
                                {"style": 2, "label": "7", "emoji": None, "custom_id": "7", "disabled": False},
                                {"style": 2, "label": "8", "emoji": None, "custom_id": "8", "disabled": False},
                                {"style": 2, "label": "9", "emoji": None, "custom_id": "9", "disabled": False},
                                {"style": 1, "label": "+", "emoji": None, "custom_id": "+", "disabled": False},
                                {"style": 4, "label": _("Clear").format(**locals()), "emoji": None, "custom_id": "clear_button", "disabled": False},
                                {"style": 2, "label": "00", "emoji": None, "custom_id": "00", "disabled": False},
                                {"style": 2, "label": "0", "emoji": None, "custom_id": "0", "disabled": False},
                                {"style": 2, "label": ".", "emoji": None, "custom_id": ".", "disabled": False},
                                {"style": 1, "label": "-", "emoji": None, "custom_id": "-", "disabled": False},
                                {"style": 3, "label": "=", "emoji": None, "custom_id": "result_button", "disabled": False},
                                {"style": 2, "label": "(", "emoji": None, "custom_id": "(", "disabled": False},
                                {"style": 2, "label": ")", "emoji": None, "custom_id": ")", "disabled": False},
                                {"style": 2, "label": "√", "emoji": None, "custom_id": "√", "disabled": False},
                                {"style": 3, "label": "<", "emoji": None, "custom_id": "left_button", "disabled": False},
                                {"style": 3, "label": ">", "emoji": None, "custom_id": "right_button", "disabled": False}
                            ]
        self.disabled_buttons_dict = [
                                {"style": 2, "label": "1", "emoji": None, "custom_id": "1", "disabled": True},
                                {"style": 2, "label": "2", "emoji": None, "custom_id": "2", "disabled": True},
                                {"style": 2, "label": "3", "emoji": None, "custom_id": "3", "disabled": True},
                                {"style": 1, "label": "x", "emoji": None, "custom_id": "x", "disabled": True},
                                {"style": 4, "label": _("Exit").format(**locals()), "emoji": None, "custom_id": "exit_button", "disabled": True},
                                {"style": 2, "label": "4", "emoji": None, "custom_id": "4", "disabled": True},
                                {"style": 2, "label": "5", "emoji": None, "custom_id": "5", "disabled": True},
                                {"style": 2, "label": "6", "emoji": None, "custom_id": "6", "disabled": True},
                                {"style": 1, "label": "÷", "emoji": None, "custom_id": "÷", "disabled": True},
                                {"style": 4, "label": "⌫", "emoji": None, "custom_id": "back_button", "disabled": True},
                                {"style": 2, "label": "7", "emoji": None, "custom_id": "7", "disabled": True},
                                {"style": 2, "label": "8", "emoji": None, "custom_id": "8", "disabled": True},
                                {"style": 2, "label": "9", "emoji": None, "custom_id": "9", "disabled": True},
                                {"style": 1, "label": "+", "emoji": None, "custom_id": "+", "disabled": True},
                                {"style": 4, "label": _("Clear").format(**locals()), "emoji": None, "custom_id": "clear_button", "disabled": True},
                                {"style": 2, "label": "00", "emoji": None, "custom_id": "00", "disabled": True},
                                {"style": 2, "label": "0", "emoji": None, "custom_id": "0", "disabled": True},
                                {"style": 2, "label": ".", "emoji": None, "custom_id": ".", "disabled": True},
                                {"style": 1, "label": "-", "emoji": None, "custom_id": "-", "disabled": True},
                                {"style": 3, "label": "=", "emoji": None, "custom_id": "result_button", "disabled": True},
                                {"style": 2, "label": "(", "emoji": None, "custom_id": "(", "disabled": True},
                                {"style": 2, "label": ")", "emoji": None, "custom_id": ")", "disabled": True},
                                {"style": 2, "label": "√", "emoji": None, "custom_id": "√", "disabled": True},
                                {"style": 3, "label": "<", "emoji": None, "custom_id": "left_button", "disabled": True},
                                {"style": 3, "label": ">", "emoji": None, "custom_id": "right_button", "disabled": True}
                            ]

        self.cogsutils = CogsUtils(cog=self)
        self.cogsutils._setup()

    async def calculate(self, expression: str, ASCII_one_hundred_and_twenty_four: bool):
        lst = list(expression)
        try:
            lst.remove("|")
        except Exception:
            pass
        expression = "".join(lst)
        expression = expression.replace(',', '.')
        expression = expression.replace(':', '/')
        expression = expression.replace(' ', '')
        expression = expression.replace('π', str(pi))
        expression = expression.replace('pi', str(pi))
        expression = expression.replace('τ', str(tau))
        expression = expression.replace('tau', str(tau))
        expression = expression.replace('e', str(e))
        expression = expression.replace('x', '*')
        expression = expression.replace('÷', '/')
        expression = expression.replace('**2', '^2')
        expression = expression.replace('**3', '^3')
        expression = expression.replace('**', '^')
        expression = expression.replace('√', 'sqrt')
        expression = expression.replace(',', '')
        for x in self.x:
            if self.x[x] in expression:
                expression = expression.replace(self.x[x], f"^{x}")
        if "sqrt" in expression and not "^" in expression:
            expression = expression.replace('^2', '**2')
            expression = expression.replace('^3', '**3')
            expression = expression.replace('^', '**')
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
        except Exception:
            result = None
        if result is not None:
            if ASCII_one_hundred_and_twenty_four:
                result = f"{result}|"
            else:
                result = f"{result}"
        if result is None:
            result = _("Error!").format(**locals())
        return result

    async def get_embed(self, ctx: commands.Context, expression: str):
        if expression == "":
            expression = None
        if expression is None:
            expression = "|"
        config = await self.data.settings.all()
        actual_color = config["color"]
        actual_thumbnail = config["thumbnail"]
        embed: discord.Embed = discord.Embed()
        embed.title = _("Calculator").format(**locals())
        embed.description = f"```{str(expression)}```"
        embed.set_thumbnail(url=actual_thumbnail)
        embed.color = actual_color
        embed.timestamp = datetime.datetime.now(tz=datetime.timezone.utc)
        if ctx.guild:
            embed.set_footer(text=ctx.guild.name, icon_url=ctx.guild.icon or "" if self.cogsutils.is_dpy2 else ctx.guild.icon_url or "")
        else:
            embed.set_footer(text=ctx.author.name, icon_url=ctx.author.display_avatar if self.cogsutils.is_dpy2 else ctx.author.avatar_url)
        return embed

    async def input_formatter(self, expression: str, new: str):
        if expression is None:
            expression = "|"
        lst = list(expression)
        try:
            index = lst.index("|")
            lst.remove("|")
        except Exception:
            index=0
        lst.insert(index, new)
        lst.insert(index+1, "|")
        expression = "".join(lst)
        return expression

    async def get_buttons(self, disabled: bool):
        buttons_one = ActionRow(
            Button(
                style=ButtonStyle.grey,
                label="1",
                emoji=None,
                custom_id="1",
                disabled=disabled
            ),
            Button(
                style=ButtonStyle.grey,
                label="2",
                emoji=None,
                custom_id="2",
                disabled=disabled
            ),
            Button(
                style=ButtonStyle.grey,
                label="3",
                emoji=None,
                custom_id="3",
                disabled=disabled
            ),
            Button(
                style=ButtonStyle.blurple,
                label="x",
                emoji=None,
                custom_id="x",
                disabled=disabled
            ),
            Button(
                style=ButtonStyle.red,
                label=_("Exit").format(**locals()),
                emoji=None,
                custom_id="exit_button",
                disabled=disabled
            )
        )
        buttons_two = ActionRow(
            Button(
                style=ButtonStyle.grey,
                label="4",
                emoji=None,
                custom_id="4",
                disabled=disabled
            ),
            Button(
                style=ButtonStyle.grey,
                label="5",
                emoji=None,
                custom_id="5",
                disabled=disabled
            ),
            Button(
                style=ButtonStyle.grey,
                label="6",
                emoji=None,
                custom_id="6",
                disabled=disabled
            ),
            Button(
                style=ButtonStyle.blurple,
                label="÷",
                emoji=None,
                custom_id="÷",
                disabled=disabled
            ),
            Button(
                style=ButtonStyle.red,
                label="⌫",
                emoji=None,
                custom_id="back_button",
                disabled=disabled
            )
        )
        buttons_three = ActionRow(
            Button(
                style=ButtonStyle.grey,
                label="7",
                emoji=None,
                custom_id="7",
                disabled=disabled
            ),
            Button(
                style=ButtonStyle.grey,
                label="8",
                emoji=None,
                custom_id="8",
                disabled=disabled
            ),
            Button(
                style=ButtonStyle.grey,
                label="9",
                emoji=None,
                custom_id="9",
                disabled=disabled
            ),
            Button(
                style=ButtonStyle.blurple,
                label="+",
                emoji=None,
                custom_id="+",
                disabled=disabled
            ),
            Button(
                style=ButtonStyle.red,
                label=_("Clear").format(**locals()),
                emoji=None,
                custom_id="clear_button",
                disabled=disabled
            )
        )
        buttons_four = ActionRow(
            Button(
                style=ButtonStyle.grey,
                label="00",
                emoji=None,
                custom_id="00",
                disabled=disabled
            ),
            Button(
                style=ButtonStyle.grey,
                label="0",
                emoji=None,
                custom_id="0",
                disabled=disabled
            ),
            Button(
                style=ButtonStyle.grey,
                label=".",
                emoji=None,
                custom_id=".",
                disabled=disabled
            ),
            Button(
                style=ButtonStyle.blurple,
                label="-",
                emoji=None,
                custom_id="-",
                disabled=disabled
            ),
            Button(
                style=ButtonStyle.green,
                label="=",
                emoji=None,
                custom_id="result_button",
                disabled=disabled
            )
        )
        buttons_five = ActionRow(
            Button(
                style=ButtonStyle.grey,
                label="(",
                emoji=None,
                custom_id="(",
                disabled=disabled
            ),
            Button(
                style=ButtonStyle.grey,
                label=")",
                emoji=None,
                custom_id=")",
                disabled=disabled
            ),
            Button(
                style=ButtonStyle.grey,
                label="√",
                emoji=None,
                custom_id="√",
                disabled=disabled
            ),
            Button(
                style=ButtonStyle.green,
                label="<",
                emoji=None,
                custom_id="left_button",
                disabled=disabled
            ),
            Button(
                style=ButtonStyle.green,
                label=">",
                emoji=None,
                custom_id="right_button",
                disabled=disabled
            )
        )
        return buttons_one, buttons_two, buttons_three, buttons_four, buttons_five

    @commands.command(aliases=["calculate"])
    async def calc(self, ctx: commands.Context, calculation: typing.Optional[str]=None):
        """Calculate a simple expression."""
        config = await self.data.settings.all()
        if calculation is not None:
            expression = await self.calculate(calculation, False)
            message = await ctx.send(embed=await self.get_embed(ctx, expression))
            return
        expression = None
        if self.cogsutils.is_dpy2:
            view = Buttons(timeout=config["time_max"], buttons=self.buttons_dict, members=[ctx.author.id])
            message = await ctx.send(embed=await self.get_embed(ctx, expression), view=view)
        else:
            buttons_one, buttons_two, buttons_three, buttons_four, buttons_five = await self.get_buttons(False)
            message = await ctx.send(embed=await self.get_embed(ctx, expression), components=[buttons_one, buttons_two, buttons_three, buttons_four, buttons_five])
        if self.cogsutils.is_dpy2:
            while True:
                try:
                    interaction, function_result = await view.wait_result()
                    if expression is None or expression == _("Error!").format(**locals()) or expression == "∞":
                        expression = None
                    if interaction.data["custom_id"] == "result_button":
                        expression = f"{await self.calculate(expression, True)}"
                    elif interaction.data["custom_id"] == "exit_button":
                        await message.delete()
                        return
                    elif interaction.data["custom_id"] == "clear_button":
                        expression = None
                    elif interaction.data["custom_id"] == "back_button":
                        if expression == "":
                            expression = None
                        if expression is None or expression == _("Error!").format(**locals()):
                            expression = "|"
                        lst = list(expression)
                        if len(lst) > 1:
                            try:
                                index = lst.index("|")
                                lst.pop(index-1)
                                expression = "".join(lst)
                            except Exception:
                                expression = None
                    elif interaction.data["custom_id"] == "left_button":
                        if expression == "":
                            expression = None
                        if expression is None or expression == "Error!":
                            expression = "|"
                        lst = list(expression)
                        if len(lst) > 1:
                            try:
                                index = lst.index("|")
                                lst.remove("|")
                                lst.insert(index-1, "|")
                            except Exception:
                                lst = ["|"]
                        expression = "".join(lst)
                        if expression == "|":
                            expression = None
                    elif interaction.data["custom_id"] == "right_button":
                        if expression == "":
                            expression = None
                        if expression is None or expression == _("Error!").format(**locals()):
                            expression = "|"
                        lst = list(expression)
                        if len(lst) > 1:
                            try:
                                index = lst.index("|")
                                lst.remove("|")
                                lst.insert(index+1, "|")
                            except Exception:
                                lst = ["|"]
                        expression = "".join(lst)
                        if expression == "|":
                            expression = None
                    else:
                        if expression is None or expression == _("Error!").format(**locals()):
                            expression = "|"
                        expression = await self.input_formatter(expression, str(interaction.data["custom_id"]))
                    view = Buttons(timeout=config["time_max"], buttons=self.buttons_dict, members=[ctx.author.id])
                    await message.edit(embed=await self.get_embed(ctx, expression), view=view)
                except TimeoutError:
                    view = Buttons(timeout=config["time_max"], buttons=self.disabled_buttons_dict, members=[])
                    await message.edit(view=view)
                    return
        else:
            def check(inter):
                return inter.guild == ctx.guild or inter.channel == ctx.channel or inter.message == message
                # This makes sure nobody except the command sender can interact with the "menu"
            while True:
                try:
                    inter = await ctx.wait_for_button_click(timeout=config["time_max"], check=check)
                    # waiting for a reaction to be added - times out after x seconds, 30 in this
                    if not inter.author == ctx.author:
                        await inter.respond(_("Only the author of the command `{ctx.prefix}calc` can interact with this message.").format(**locals()), ephemeral=True)
                    else:
                        if expression is None or expression == _("Error!").format(**locals()) or expression == "∞":
                            expression = None
                        if inter.clicked_button.custom_id == "result_button":
                            expression = f"{await self.calculate(expression, True)}"
                        elif inter.clicked_button.custom_id == "exit_button":
                            await message.delete()
                            return
                        elif inter.clicked_button.custom_id == "clear_button":
                            expression = None
                        elif inter.clicked_button.custom_id == "back_button":
                            if expression == "":
                                expression = None
                            if expression is None or expression == _("Error!").format(**locals()):
                                expression = "|"
                            lst = list(expression)
                            if len(lst) > 1:
                                try:
                                    index = lst.index("|")
                                    lst.pop(index-1)
                                    expression = "".join(lst)
                                except Exception:
                                    expression = None
                        elif inter.clicked_button.custom_id == "left_button":
                            if expression == "":
                                expression = None
                            if expression is None or expression == "Error!":
                                expression = "|"
                            lst = list(expression)
                            if len(lst) > 1:
                                try:
                                    index = lst.index("|")
                                    lst.remove("|")
                                    lst.insert(index-1, "|")
                                except Exception:
                                    lst = ["|"]
                            expression = "".join(lst)
                            if expression == "|":
                                expression = None
                        elif inter.clicked_button.custom_id == "right_button":
                            if expression == "":
                                expression = None
                            if expression is None or expression == _("Error!").format(**locals()):
                                expression = "|"
                            lst = list(expression)
                            if len(lst) > 1:
                                try:
                                    index = lst.index("|")
                                    lst.remove("|")
                                    lst.insert(index+1, "|")
                                except Exception:
                                    lst = ["|"]
                            expression = "".join(lst)
                            if expression == "|":
                                expression = None
                        else:
                            if expression is None or expression == _("Error!").format(**locals()):
                                expression = "|"
                            expression = await self.input_formatter(expression, str(inter.clicked_button.custom_id))
                        await message.edit(embed=await self.get_embed(ctx, expression))
                        await inter.respond(f"```{expression}```", ephemeral=True)
                except asyncio.TimeoutError:
                    buttons_one, buttons_two, buttons_three, buttons_four, buttons_five = await self.get_buttons(True)
                    await message.edit(components=[buttons_one, buttons_two, buttons_three, buttons_four, buttons_five])
                    return

from .AAA3A_utils import CogsUtils, Menu  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
from redbot.core.bot import Red  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import ast
import inspect
import io
import traceback
from copy import copy

import rich
from redbot.core.utils.chat_formatting import bold, box, pagify

# Credits:
# Thanks to @epic guy on Discord for the basic syntax (command groups, commands) and also commands (await ctx.send, await ctx.author.send, await ctx.message.delete())!
# Thanks to @YamiKaitou on Discord for the technique in the init file to load the interaction client only if it is not loaded! Before this fix, when a user clicked on a button, the actions would be launched about 10 times, which caused huge spam and a loop in the channel.
# Thanks to the developers of the cogs I added features to as it taught me how to make a cog! (Chessgame by WildStriker, Captcha by Kreusada, Speak by Epic guy and Rommer by Dav)
# Thanks to all the people who helped me with some commands in the #coding channel of the redbot support server!

_ = Translator("CtxVar", __file__)

if CogsUtils().is_dpy2:
    from functools import partial

    hybrid_command = partial(commands.hybrid_command, with_app_command=False)
    hybrid_group = partial(commands.hybrid_group, with_app_command=False)
else:
    hybrid_command = commands.command
    hybrid_group = commands.group


@cog_i18n(_)
class CtxVar(commands.Cog):
    """A cog to list and display the contents of all sub-functions of `ctx`!"""

    def __init__(self, bot: Red):
        self.bot: Red = bot

        self.cogsutils = CogsUtils(cog=self)

    @commands.is_owner()
    @commands.bot_has_permissions(embed_links=True, add_reactions=True)
    @hybrid_group()
    async def ctxvar(self, ctx: commands.Context):
        """Commands for CtxVar."""
        pass

    @ctxvar.command()
    async def ctx(
        self,
        ctx: commands.Context,
        message: typing.Optional[discord.ext.commands.converter.MessageConverter] = None,
        args: typing.Optional[str] = None,
    ):
        """Display a list of all attributes and their values of the 'ctx' class instance or its sub-attributes."""
        Dev = ctx.bot.get_cog("Dev")
        if not Dev:
            raise commands.UserFeedbackCheckFailure("The cog Dev must be loaded, to make sure you know what you are doing.")
        if message is None:
            message = ctx.message
        instance = await ctx.bot.get_context(message)
        full_instance_name = "ctx" + (f"{args}" if args is not None else "")
        if args is not None:
            args = args.split(".")
            for arg in args:
                if not hasattr(instance, arg):
                    raise commands.UserFeedbackCheckFailure(
                        _("The argument you specified is not a subclass of the instance.").format(
                            **locals()
                        )
                    )
                instance = getattr(instance, arg)
        if len(f"{bold(full_instance_name)}") > 256:
            full_instance_name = bold(full_instance_name[:248] + "|...")
        embed: discord.Embed = discord.Embed()
        embed.title = f"**{full_instance_name}**"
        embed.description = _(
            "Here are all the variables and their associated values that can be used in this instance class."
        ).format(**locals())
        embed.color = 0x01D758
        embed.set_thumbnail(
            url="https://upload.wikimedia.org/wikipedia/commons/thumb/c/c3/Python-logo-notext.svg/2048px-Python-logo-notext.svg.png"
        )
        one_l = []
        for x in dir(instance):
            try:
                if not (x.startswith("__") and x.endswith("__")):
                    one_l.append(x)
            except Exception:
                pass
        lists = []
        while True:
            lst = one_l[0:20]
            one_l = one_l[20:]
            lists.append(lst)
            if one_l == []:
                break
        embeds = []
        for lst in lists:
            e = copy(embed)
            for x in lst:
                if not len(f"{x}") > 256:
                    try:
                        e.add_field(
                            inline=True,
                            name=f"{x}",
                            value=box(
                                self.cogsutils.replace_var_paths(
                                    Dev.sanitize_output(ctx, str(getattr(instance, x))[:100])
                                ),
                                "py",
                            ),
                        )
                    except Exception:
                        pass
            embeds.append(e)

        await Menu(pages=embeds).start(ctx)

    @ctxvar.command(name="dir")
    async def _dir(self, ctx: commands.Context, thing: str, search: typing.Optional[str] = None):
        """Display a list of all attributes of the provided object (debug not async)."""
        Dev = ctx.bot.get_cog("Dev")
        if not Dev:
            raise commands.UserFeedbackCheckFailure("The cog Dev must be loaded, to make sure you know what you are doing.")
        thing = Dev.cleanup_code(thing)
        env = Dev.get_environment(ctx)
        env["getattr_static"] = inspect.getattr_static
        try:
            tree = ast.parse(thing, "<dir>", "eval")
            if isinstance(tree.body, ast.Attribute) and isinstance(tree.body.ctx, ast.Load):
                tree.body = ast.Call(
                    func=ast.Name(id="getattr_static", ctx=ast.Load()),
                    args=[tree.body.value, ast.Constant(value=tree.body.attr)],
                    keywords=[],
                )
                tree = ast.fix_missing_locations(tree)
            object = eval(compile(tree, "<dir>", "eval"), env)
        except NameError:
            raise commands.UserFeedbackCheckFailure(f"I couldn't find any cog, command, or object named `{thing}`.")
        except Exception as e:
            raise commands.UserFeedbackCheckFailure(box("".join(traceback.format_exception_only(type(e), e)), lang="py"))

        result = "[\n"
        if search is None:
            result += "\n".join([f"    '{attr}'," for attr in dir(object)])
        else:
            result += "\n".join(
                [f"    '{attr}'," for attr in dir(object) if search.lower() in attr.lower()]
            )
        if result[-1] == ",":
            result = list(result)
            del result[-1]
            result = "".join(result)
        result += "\n]"
        result = self.cogsutils.replace_var_paths(Dev.sanitize_output(ctx, result))

        await Menu(
            pages=[box(page, "py") for page in pagify(result, page_length=2000 - 10)]
        ).start(ctx)

    @ctxvar.command(name="inspect")
    async def _inspect(
        self, ctx: commands.Context, show_all: typing.Optional[bool], *, thing: str
    ):
        """Execute `rich.help(obj=object, ...)` on the provided object (debug not async)."""
        Dev = ctx.bot.get_cog("Dev")
        if not Dev:
            raise commands.UserFeedbackCheckFailure("The cog Dev must be loaded, to make sure you know what you are doing.")
        thing = Dev.cleanup_code(thing)
        env = Dev.get_environment(ctx)
        env["getattr_static"] = inspect.getattr_static
        try:
            tree = ast.parse(thing, "<dir>", "eval")
            if isinstance(tree.body, ast.Attribute) and isinstance(tree.body.ctx, ast.Load):
                tree.body = ast.Call(
                    func=ast.Name(id="getattr_static", ctx=ast.Load()),
                    args=[tree.body.value, ast.Constant(value=tree.body.attr)],
                    keywords=[],
                )
                tree = ast.fix_missing_locations(tree)
            object = eval(compile(tree, "<dir>", "eval"), env)
        except NameError:
            raise commands.UserFeedbackCheckFailure(f"I couldn't find any cog, command, or object named `{thing}`.")
        except Exception as e:
            raise commands.UserFeedbackCheckFailure(box("".join(traceback.format_exception_only(type(e), e)), lang="py"))

        kwargs: typing.Dict[str, typing.Any] = {
            "width": 80,
            "no_color": True,
            "color_system": None,
            "tab_size": 2,
            "soft_wrap": False,
        }
        with io.StringIO() as file:
            console = rich.console.Console(file=file, **kwargs)
            if show_all:
                rich.inspect(
                    obj=object,
                    title=repr(object),
                    help=True,
                    methods=True,
                    docs=True,
                    private=True,
                    dunder=True,
                    all=True,
                    sort=True,
                    value=True,
                    console=console,
                )
            else:
                rich.inspect(
                    obj=object,
                    title=repr(object),
                    help=True,
                    methods=False,
                    docs=True,
                    private=False,
                    dunder=False,
                    all=False,
                    sort=True,
                    value=True,
                    console=console,
                )
            result = console.file.getvalue()
        result = self.cogsutils.replace_var_paths(Dev.sanitize_output(ctx, result))

        await Menu(
            pages=[box(page, "py") for page in pagify(result.strip(), page_length=2000 - 10)]
        ).start(ctx)

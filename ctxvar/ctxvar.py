from .AAA3A_utils import Cog, CogsUtils, Menu  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
from redbot.core.bot import Red  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import ast
import datetime
import inspect
import io
import rich
import time
import traceback
import types
from copy import copy

from redbot.core.utils.chat_formatting import bold, box, pagify

# Credits:
# General repo credits.
# Thanks to @YamiKaitou on Discord for the technique in the init file to load the interaction client only if it is not loaded! Before this fix, when a user clicked on a button, the actions would be launched about 10 times, which caused huge spam and a loop in the channel.

_ = Translator("CtxVar", __file__)

if CogsUtils().is_dpy2:
    hybrid_command = commands.hybrid_command
    hybrid_group = commands.hybrid_group
else:
    hybrid_command = commands.command
    hybrid_group = commands.group


@cog_i18n(_)
class CtxVar(Cog):
    """A cog to list and display the contents of all sub-functions of `ctx`!"""

    def __init__(self, bot: Red) -> None:
        self.bot: Red = bot

        self.cogsutils: CogsUtils = CogsUtils(cog=self)

    @commands.is_owner()
    @commands.bot_has_permissions(embed_links=True, add_reactions=True)
    @hybrid_group()
    async def ctxvar(self, ctx: commands.Context) -> None:
        """Commands for CtxVar."""
        pass

    @ctxvar.command()
    async def ctx(
        self,
        ctx: commands.Context,
        message: typing.Optional[discord.ext.commands.converter.MessageConverter] = None,
        args: typing.Optional[str] = None,
    ) -> None:
        """Display a list of all attributes and their values of the 'ctx' class instance or its sub-attributes."""
        Dev = ctx.bot.get_cog("Dev")
        if not Dev:
            raise commands.UserFeedbackCheckFailure(
                _("The cog Dev must be loaded, to make sure you know what you are doing.")
            )
        if message is None:
            message = ctx.message
        instance = await ctx.bot.get_context(message)
        full_instance_name = "ctx" + (f"{args}" if args is not None else "")
        if args is not None:
            args = args.split(".")
            for arg in args:
                if not hasattr(instance, arg):
                    raise commands.UserFeedbackCheckFailure(
                        _("The argument you specified is not a subclass of the instance.")
                    )
                instance = getattr(instance, arg)
        if len(f"{bold(full_instance_name)}") > 256:
            full_instance_name = bold(f"{full_instance_name[:248]}|...")
        embed: discord.Embed = discord.Embed()
        embed.title = f"**{full_instance_name}**"
        embed.description = _("Here are all the variables and their associated values that can be used in this instance class.")
        embed.color = 0x01D758
        embed.set_thumbnail(
            url="https://upload.wikimedia.org/wikipedia/commons/thumb/c/c3/Python-logo-notext.svg/2048px-Python-logo-notext.svg.png"
        )
        one_l = [
            x
            for x in dir(instance)
            if not (x.startswith("__") and x.endswith("__"))
        ]
        lists = []
        while one_l != []:
            li = one_l[:20]
            one_l = one_l[20:]
            lists.append(li)
        embeds = []
        for li in lists:
            e = copy(embed)
            for x in li:
                if len(f"{x}") <= 256:
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
                    except AttributeError:
                        pass
            embeds.append(e)

        await Menu(pages=embeds).start(ctx)

    @ctxvar.command(name="dir")
    async def _dir(
        self, ctx: commands.Context, thing: str, search: typing.Optional[str] = None
    ) -> None:
        """Display a list of all attributes of the provided object (debug not async)."""
        Dev = ctx.bot.get_cog("Dev")
        if not Dev:
            raise commands.UserFeedbackCheckFailure(
                _("The cog Dev must be loaded, to make sure you know what you are doing.")
            )
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
            _object = eval(compile(tree, "<dir>", "eval"), env)
        except NameError:
            raise commands.UserFeedbackCheckFailure(
                _("I couldn't find any cog, command, or object named `{thing}`.").format(
                    thing=thing
                )
            )
        except Exception as e:
            raise commands.UserFeedbackCheckFailure(
                box("".join(traceback.format_exception_only(type(e), e)), lang="py")
            )

        result = "[\n" + (
            "\n".join([f"    '{attr}'," for attr in dir(_object)])
            if search is None
            else "\n".join(
                [
                    f"    '{attr}',"
                    for attr in dir(_object)
                    if search.lower() in attr.lower()
                ]
            )
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
    ) -> None:
        """Execute `rich.help(obj=object, ...)` on the provided object (debug not async)."""
        Dev = ctx.bot.get_cog("Dev")
        if not Dev:
            raise commands.UserFeedbackCheckFailure(
                _("The cog Dev must be loaded, to make sure you know what you are doing.")
            )
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
            _object = eval(compile(tree, "<dir>", "eval"), env)
        except NameError:
            raise commands.UserFeedbackCheckFailure(
                _("I couldn't find any cog, command, or object named `{thing}`.").format(
                    thing=thing
                )
            )
        except Exception as e:
            raise commands.UserFeedbackCheckFailure(
                box("".join(traceback.format_exception_only(type(e), e)), lang="py")
            )

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
                    obj=_object,
                    title=repr(_object),
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
                    obj=_object,
                    title=repr(_object),
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

    class WhatIsConverter(commands.Converter):
        async def convert(self, ctx: commands.Context, argument: str):
            _types = [discord.Guild, discord.TextChannel, discord.VoiceChannel, discord.Member, discord.User, discord.Role, discord.Emoji]
            try:
                _types.extend([discord.Thread, discord.ForumChannel])
            except AttributeError:
                pass
            for _type in _types:
                try:
                    return await discord.ext.commands.converter.CONVERTER_MAPPING[_type]().convert(ctx, argument)
                except commands.BadArgument:
                    pass
            return argument

    @ctxvar.command(name="whatis")
    async def _whatis(
        self, ctx: commands.Context, *, thing: WhatIsConverter
    ) -> None:
        """List attributes of the provided object like dpy objects (debug not async)."""
        Dev = ctx.bot.get_cog("Dev")
        if not Dev:
            raise commands.UserFeedbackCheckFailure(
                _("The cog Dev must be loaded, to make sure you know what you are doing.")
            )
        if isinstance(thing, str):
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
                _object = eval(compile(tree, "<dir>", "eval"), env)
            except NameError:
                raise commands.UserFeedbackCheckFailure(
                    _("I couldn't find any cog, command, or object named `{thing}`.").format(
                        thing=thing
                    )
                )
            except Exception as e:
                raise commands.UserFeedbackCheckFailure(
                    box("".join(traceback.format_exception_only(type(e), e)), lang="py")
                )
        else:
            _object = thing
        if hasattr(_object, "original_context") and isinstance(_object.original_context, commands.Context):
            _object = _object.original_context
        result = {}
        result2 = {}
        for attr in dir(_object):
            if attr.startswith("_"):
                continue
            try:
                value = getattr(_object, attr)
            except AttributeError:
                continue
            if hasattr(value, "__func__"):
                continue
            if isinstance(value, (typing.List, typing.Tuple, typing.Dict, typing.Set, types.MappingProxyType, discord.utils.SequenceProxy)):
                result2[attr.replace("_", " ").capitalize()] = f"{value.__class__.__name__} - {len(value)}"
                continue
            elif isinstance(value, datetime.datetime):
                _time = int(value.timestamp())
                now = int(time.time())
                time_elapsed = int(now - _time)
                m, s = divmod(time_elapsed, 60)
                h, m = divmod(m, 60)
                d, h = divmod(h, 24)
                output = d, h, m
                if output[2] < 1:
                    ts = "just now"
                else:
                    ts = ""
                    if output[0] == 1:
                        ts += f"{output[0]} day, "
                    elif output[0] > 1:
                        ts += f"{output[0]} days, "
                    if output[1] == 1:
                        ts += f"{output[1]} hour, "
                    elif output[1] > 1:
                        ts += f"{output[1]} hours, "
                    if output[2] == 1:
                        ts += f"{output[2]} minute ago"
                    elif output[2] > 1:
                        ts += f"{output[2]} minutes ago"
                value = ts
            elif isinstance(value, discord.Asset):
                value = str(value)
            elif hasattr(value, "display_name") and hasattr(value, "id"):
                value = f"{value.display_name} ({value.id})"
            elif hasattr(value, "id"):
                value = f"{value} ({value.id})"
            elif isinstance(value, discord.Activity):
                value = f"{value.type.name.capitalize()} to {value.name}" + (f" ({value.url})" if value.url else "")
            elif isinstance(value, discord.flags.BaseFlags):
                value = tuple(v for v in dict(value) if dict(value)[v])
            result[attr.replace("_", " ").capitalize()] = value if isinstance(value, str) else repr(value)
        result.update(**result2)
        _result = Dev.sanitize_output(ctx, "".join(f"\n[{k}] : {r}" for k, r in result.items()))
        await Menu(
            pages=[box(page, "ini") for page in pagify(_result.strip(), page_length=2000 - 11)]
        ).start(ctx)

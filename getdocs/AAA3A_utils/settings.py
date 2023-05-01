from redbot.core import commands  # isort:skip
import redbot  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

# import typing_extensions  # isort:skip

import asyncio
import inspect
import json
from copy import deepcopy
from io import StringIO

from redbot.core import Config
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import box
from rich.console import Console
from rich.table import Table

from .menus import Menu
from .views import Buttons, Modal

setattr(commands, "Literal", typing.Literal)

__all__ = ["Settings", "CustomMessageConverter"]


def _(untranslated: str) -> str:
    return untranslated


def dashboard_page(*args, **kwargs):
    def decorator(func: typing.Callable):
        func.__dashboard_decorator_params__ = (args, kwargs)
        return func

    return decorator


def no_colour_rich_markup(
    *objects: typing.Any, lang: str = "", no_box: typing.Optional[bool] = False
) -> str:
    """
    Slimmed down version of rich_markup which ensure no colours (/ANSI) can exist
    https://github.com/Cog-Creators/Red-DiscordBot/pull/5538/files (Kowlin)
    """
    temp_console = Console(  # Prevent messing with STDOUT's console
        color_system=None,
        file=StringIO(),
        force_terminal=True,
        width=80,
    )
    temp_console.print(*objects)
    if no_box:
        return temp_console.file.getvalue()
    return box(temp_console.file.getvalue(), lang=lang)  # type: ignore


if not hasattr(discord.utils, "MISSING"):

    class _MissingSentinel:
        __slots__ = ()

        def __eq__(self, other) -> bool:
            return False

        def __bool__(self) -> bool:
            return False

        def __hash__(self) -> int:
            return 0

        def __repr__(self):
            return "..."

    discord.utils.MISSING = _MissingSentinel()


class CustomMessageConverter(commands.Converter, dict):
    def __init__(self, **kwargs) -> None:
        if "embed" in kwargs and not isinstance(kwargs["embed"], discord.Embed):
            kwargs["embed"] = discord.Embed.from_dict(kwargs["embed"])
        self.__dict__.clear()
        self.__dict__.update(**kwargs)

    async def convert(
        self, ctx: commands.Context, argument: str
    ) -> typing.Any:  # typing_extensions.Self
        if not argument.startswith("{"):
            # If argument is not a JSON, convert it with MessageConverter.
            try:
                message = await commands.MessageConverter().convert(ctx, argument)
            except commands.BadArgument:
                raise
            kwargs = {
                key: getattr(message, key)
                for key in ["content", "embeds"]
                if getattr(message, key)
            }
        else:
            try:
                kwargs = json.loads(argument)
            except json.JSONDecodeError:
                raise commands.BadArgument(_("Invalid JSON format."))
        if not isinstance(kwargs, typing.Dict):
            raise commands.BadArgument(_("Invalid type, expected `dict`."))
        if "embeds" in kwargs:
            if len(kwargs["embeds"]) == 0:
                del kwargs["embeds"]
            elif len(kwargs["embeds"]) == 1 and "embed" not in kwargs:
                kwargs["embed"] = kwargs["embeds"][0]
                del kwargs["embeds"]
            else:
                raise commands.BadArgument(_("`embeds` field is not supported."))
        for x in ["attachments", "files"]:
            if x in kwargs:
                del kwargs[x]
        for x in kwargs:
            if x not in ["content", "embed"]:
                raise commands.BadArgument(_("`{x}` field is not supported.").format(x=x))
        if "content" not in kwargs and "embed" not in kwargs:
            raise commands.BadArgument(_("Missing `content` or `embed` field."))
        if "embed" in kwargs:
            embed = kwargs["embed"]
            if not isinstance(embed, discord.Embed):
                if not isinstance(embed, (typing.Dict)):
                    raise commands.BadArgument(_("Invalid type for `embed`, expected `dict`."))
                for x in embed:
                    if embed[x] is None:
                        del embed[x]
                    elif isinstance(embed[x], typing.Dict):
                        for y in embed[x]:
                            if embed[x][y] is None:
                                del embed[x][y]
                try:
                    embed = discord.Embed.from_dict(embed)
                except Exception:
                    pass
            if not embed:
                raise commands.BadArgument(_("Missing fields in `embed` field."))
            length = len(embed)
            if length > 6000:
                raise commands.BadArgument(
                    _(
                        "Embed size exceeds Discord limit of 6000 characters, provided one of {length}."
                    ).format(length=length)
                )
            kwargs["embed"] = embed
        # Attempt to send message.
        if not getattr(ctx, "__dashboard_fake__", False):
            try:
                message = await ctx.send(**kwargs)
            except discord.HTTPException as e:
                raise commands.BadArgument(
                    _("Invalid message params (error when sending message).\n{e}").format(e=e)
                )
        self.__dict__.update(**kwargs)
        return self

    async def send_message(
        self,
        ctx: commands.Context,
        channel: typing.Optional[discord.abc.Messageable] = None,
        **kwargs,
    ):
        if channel is None:
            channel = ctx
        _kwargs = self.__dict__.copy()
        if (env := kwargs.pop("env", None)) is not None:

            class _Env(typing.Dict):
                def __getitem__(self, key: str):
                    return env.__getitem__(key)

                def __missing__(self, key: str):
                    return "{" + f"{key}" + "}"

            _env = _Env()
            if "content" in _kwargs and _kwargs["content"] is not None:
                _kwargs["content"] = _kwargs["content"].format_map(_env)
            if "embed" in _kwargs and _kwargs["embed"] is not None:
                embed = _kwargs["embed"].copy()
                if embed.title is not None:
                    embed.title = embed.title.format_map(_env)
                if embed.description is not None:
                    embed.description = embed.description.format_map(_env)
                if getattr(embed, "_author", None) is not None:
                    if "name" in embed._author:
                        embed._author["name"] = embed._author["name"].format_map(_env)
                    if "icon_url" in embed._author:
                        embed._author["icon_url"] = embed._author["icon_url"].format_map(_env)
                if getattr(embed, "_footer", None) is not None and "text" in embed._footer:
                    embed._footer["text"] = embed._footer["text"].format_map(_env)
                _kwargs["embed"] = embed
        _kwargs.update(**kwargs)
        return await channel.send(**_kwargs)

    def to_dict(self) -> typing.Dict[str, typing.Any]:
        kwargs = self.__dict__
        if "embed" in kwargs:
            kwargs["embed"] = kwargs["embed"].to_dict()
        return kwargs

    # Copied from `AAA3A_utils.dev.DevSpace`.
    def __repr__(self) -> str:
        items = [f"{k}={v!r}" for k, v in self.__dict__.items()]
        return (
            f"<{self.__class__.__name__} {' '.join(items)}>"
            if items
            else f"<{self.__class__.__name__} [Nothing]>"
        )

    def __eq__(self, other: object) -> bool:
        if isinstance(self, self.__class__) and isinstance(other, self.__class__):
            return self.__dict__ == other.__dict__
        return NotImplemented

    def __len__(self) -> int:
        return len(self.__dict__)

    def __contains__(self, key: str) -> bool:
        return key in self.__dict__

    def __iter__(self) -> typing.Iterator[typing.Tuple[str, typing.Any]]:
        yield from self.__dict__.items()

    def __reversed__(self) -> typing.Dict:
        return self.__dict__.__reversed__()

    def __getattr__(self, attr: str) -> typing.Any:
        raise AttributeError(attr)

    def __setattr__(self, attr: str, value: typing.Any) -> None:
        self.__dict__[attr] = value

    def __delattr__(self, attr: str) -> None:
        del self.__dict__[attr]

    def __getitem__(self, key: str) -> typing.Any:
        return self.__dict__[key]

    def __setitem__(self, key: str, value: typing.Any) -> None:
        self.__dict__[key] = value

    def __delitem__(self, key: str) -> None:
        del self.__dict__[key]

    def clear(self) -> None:
        self.__dict__.clear()

    def update(self, **kwargs) -> None:
        self.__dict__.update(**kwargs)

    def copy(self) -> typing.Any:  # typing_extensions.Self
        return self.__class__(**self.__dict__)

    def items(self):
        return self.__dict__.items()

    def keys(self):
        return self.__dict__.keys()

    def values(self):
        return self.__dict__.values()

    def get(self, key: str, _default: typing.Optional[typing.Any] = None) -> typing.Any:
        return self.__dict__.get(key, _default)

    def pop(self, key: str, _default: typing.Optional[typing.Any] = None) -> typing.Any:
        return self.__dict__.pop(key, _default)

    def popitem(self) -> typing.Any:
        return self.__dict__.popitem()

    def _update_with_defaults(
        self, defaults: typing.Iterable[typing.Tuple[str, typing.Any]]
    ) -> None:
        for key, value in defaults:
            self.__dict__.setdefault(key, value)


class Settings:
    def __init__(
        self,
        bot: Red,
        cog: commands.Cog,
        config: Config,
        group: str,
        settings: typing.Dict[str, typing.Dict[str, typing.Any]],
        global_path: typing.List = None,
        use_profiles_system: typing.Optional[bool] = False,
        can_edit: bool = True,
        commands_group: typing.Optional[typing.Union[commands.Group, str]] = None,
    ) -> None:
        if global_path is None:
            global_path = []
        # {"enable": {"path": ["settings", "enabled"], "converter": bool, "command_name": "enable", "label": "Enable", "description": "Enable the system.", "usage": "enable", "style": 1}}
        self.bot: Red = bot
        self.cog: commands.Cog = cog
        self.config: Config = config
        self.group: str = group
        self.global_path: typing.List[str] = global_path
        self.use_profiles_system: bool = use_profiles_system
        self.can_edit: bool = can_edit
        self.commands_group: commands.Group = commands_group
        self.commands: typing.Dict[str, commands.Command] = {}
        self.commands_added: asyncio.Event = asyncio.Event()
        for setting in settings:
            if "path" not in settings[setting]:
                settings[setting]["path"] = [setting]
            if "converter" not in settings[setting]:
                settings[setting]["converter"] = bool
            if "command_name" not in settings[setting]:
                settings[setting]["command_name"] = setting.replace("_", "").lower()
            if "label" not in settings[setting]:
                settings[setting]["label"] = setting.replace("_", " ").capitalize()
            if "description" not in settings[setting]:
                label = settings[setting]["label"]
                settings[setting]["description"] = f"Set `{label}`."
            if "usage" not in settings[setting]:
                if settings[setting]["converter"] in discord.ext.commands.converter.CONVERTER_MAPPING:
                    x = settings[setting]["converter"].__name__.replace(" ", "_")
                    usage = x[0]
                    for y in x[1:]:
                        if y.isupper():
                            usage += " "
                        usage += y
                    settings[setting]["usage"] = usage.lower()
                else:
                    settings[setting]["usage"] = setting.replace(" ", "_").lower()
            if "no_slash" not in settings[setting]:
                settings[setting]["no_slash"] = False
            settings[setting]["param"] = discord.ext.commands.parameters.Parameter(
                name=setting,
                kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                annotation=settings[setting]["converter"],
            )
            if "style" not in settings[setting]:
                settings[setting]["style"] = discord.TextStyle.short
            elif isinstance(settings[setting]["style"], int):
                settings[setting]["style"] = discord.TextStyle(settings[setting]["style"])
        self.settings: typing.Dict[str, typing.Dict[str, typing.Any]] = settings

    async def add_commands(self, force: typing.Optional[bool] = False) -> None:

        if not isinstance(self.commands_group, commands.Group):
            name = "set" + (
                self.commands_group
                if isinstance(self.commands_group, str)
                else self.cog.qualified_name.lower()
            )
            aliases = [
                (
                    (
                        self.commands_group
                        if isinstance(self.commands_group, str)
                        else self.cog.qualified_name.lower()
                    )
                    + "set"
                )
            ]
            _help = f"Commands to edit {self.cog.qualified_name}'s settings."
            if force:
                self.bot.remove_command(name)

            async def commands_group(self, ctx: commands.Context):
                pass

            commands_group.__qualname__ = f"{self.cog.qualified_name}.{name}"
            commands_group: commands.Group = commands.admin_or_permissions(administrator=True)(
                commands.hybrid_group(name=name, aliases=aliases, help=_help)(commands_group)
            )
            commands_group.name = name
            # commands_group.brief = _help
            # commands_group.description = _help
            commands_group.callback.__doc__ = _help
            commands_group.cog = self.cog
            if "ctx" in commands_group.params:
                del commands_group.params["ctx"]
            self.bot.add_command(commands_group)
            cog_commands = list(self.cog.__cog_commands__)
            cog_commands.append(commands_group)
            self.cog.__cog_commands__ = tuple(cog_commands)
            self.commands_group = commands_group
            setattr(self, f"{name}", commands_group)

        class ProfileConverter(commands.Converter):
            async def convert(_self, ctx: commands.Context, argument: str):
                if len(argument) > 10:
                    raise commands.BadArgument(_("This profile does not exist."))
                if self.group == Config.GLOBAL:
                    _object = None
                elif self.group == Config.GUILD:
                    _object = ctx.guild
                elif self.group == Config.MEMBER:
                    _object = ctx.author
                elif self.group == Config.CHANNEL:
                    _object = ctx.author
                elif self.group == Config.ROLE:
                    _object = ctx.author.top_role
                elif self.group == Config.USER:
                    _object = ctx.author
                data = self.get_data(_object)
                profiles = await data.get_raw(*self.global_path)
                if argument.lower() not in profiles:
                    raise commands.BadArgument(_("This profile does not exist."))
                return argument.lower()

        if not self.use_profiles_system:

            async def reset_setting(_self, ctx: commands.Context, setting: str):
                """Reset a setting."""
                for _setting in self.settings:
                    if self.settings[_setting]["command_name"] == setting:
                        key = _setting
                        break
                else:
                    raise commands.UserFeedbackCheckFailure(_("No setting found."))
                await self.command(ctx, key=key, value=discord.utils.MISSING)

            async def show_settings(
                _self, ctx: commands.Context, with_dev: typing.Optional[bool] = False
            ):
                """Show all settings for the cog with defaults and values."""
                await self.show_settings(ctx, with_dev=with_dev)

            async def modal_config(
                _self, ctx: commands.Context, confirmation: typing.Optional[bool] = False
            ):
                """Set all settings for the cog with a Discord Modal."""
                await self.send_modal(ctx, confirmation=confirmation)

            to_add = {
                "resetsetting": reset_setting,
                "showsettings": show_settings,
                "modalconfig": modal_config,
            }
        else:

            async def reset_setting(
                _self, ctx: commands.Context, profile: ProfileConverter, setting: str
            ):
                """Reset a setting."""
                for _setting in self.settings:
                    if self.settings[_setting]["command_name"] == setting:
                        key = _setting
                        break
                else:
                    raise commands.UserFeedbackCheckFailure(_("No setting found."))
                await self.command(ctx, key=key, value=discord.utils.MISSING, profile=profile)

            async def show_settings(
                _self,
                ctx: commands.Context,
                profile: ProfileConverter,
                with_dev: typing.Optional[bool] = False,
            ):
                """Show all settings for the cog with defaults and values."""
                await self.show_settings(ctx, profile=profile, with_dev=with_dev)

            async def modal_config(
                _self,
                ctx: commands.Context,
                profile: ProfileConverter,
                confirmation: typing.Optional[bool] = False,
            ):
                """Set all settings for the cog with a Discord Modal."""
                await self.send_modal(ctx, profile=profile, confirmation=confirmation)

            async def add_profile(_self, ctx: commands.Context, profile: str):
                """Create a new profile with defaults settings."""
                await self.add_profile(ctx, profile=profile)

            async def clone_profile(
                _self, ctx: commands.Context, old_profile: ProfileConverter, profile: str
            ):
                """Clone an existing profile with his settings."""
                await self.clone_profile(ctx, old_profile=old_profile, profile=profile)

            async def remove_profile(
                _self,
                ctx: commands.Context,
                profile: ProfileConverter,
                confirmation: typing.Optional[bool] = False,
            ):
                """Remove an existing profile."""
                await self.remove_profile(ctx, profile=profile, confirmation=confirmation)

            async def rename_profile(
                _self, ctx: commands.Context, old_profile: ProfileConverter, profile: str
            ):
                """Clone an existing profile with his settings."""
                await self.rename_profile(ctx, old_profile=old_profile, profile=profile)

            async def list_profiles(_self, ctx: commands.Context):
                """List the existing profiles."""
                await self.list_profiles(ctx)

            to_add = {
                "resetsetting": reset_setting,
                "showsettings": show_settings,
                "modalconfig": modal_config,
                "profileadd": add_profile,
                "profileclone": clone_profile,
                "profileremove": remove_profile,
                "profilerename": rename_profile,
                "profileslist": list_profiles,
            }
        aliases = {
            "modalconfig": ["configmodal"],
            "profileadd": ["addprofile"],
            "profileclone": ["cloneprofile"],
            "profileremove": ["removeprofile"],
            "profilerename": ["renameprofile"],
            "profileslist": ["listprofiles"],
        }
        if not (self.can_edit or force):
            for name in [
                "resetsetting",
                "modalconfig",
                "profileadd",
                "profileclone",
                "profileremove",
                "profilerename",
            ]:
                try:
                    del to_add[name]
                except KeyError:
                    pass
        for name, command in to_add.items():
            command.__qualname__ = f"{self.cog.qualified_name}.settings_{name}"
            command: commands.Command = self.commands_group.command(
                name=name, aliases=aliases.get(name, [])
            )(command)
            command.name = name
            command.cog = self.cog
            self.bot.dispatch("command_add", command)
            if self.bot.get_cog("permissions") is None:
                command.requires.ready_event.set()
            if "ctx" in command.params:
                del command.params["ctx"]
            setattr(self, f"settings_{name}", command)
            cog_commands = list(self.cog.__cog_commands__)
            cog_commands.append(command)
            self.cog.__cog_commands__ = tuple(cog_commands)
            self.commands[f"_{name}"] = command

        if self.can_edit or force:
            for setting in self.settings:
                name = self.settings[setting]["command_name"]
                _converter = self.settings[setting]["converter"]
                self.commands_group.remove_command(name)
                _help = self.settings[setting]["description"]
                _help += f"\n\nDev: {repr(_converter)}"
                _usage = self.settings[setting]["usage"]

                if not self.use_profiles_system:

                    async def command(_self, ctx: commands.Context, *, value: _converter):
                        await self.command(ctx, key=None, value=value)

                else:

                    async def command(
                        _self,
                        ctx: commands.Context,
                        profile: ProfileConverter,
                        *,
                        value: _converter,
                    ):
                        await self.command(ctx, key=None, value=value, profile=profile)

                command.__qualname__ = f"{self.cog.qualified_name}.settings_{name}"
                if (
                    self.settings[setting]["no_slash"]
                    and isinstance(self.commands_group, commands.HybridGroup)
                ):
                    command: commands.Command = self.commands_group.command(
                        name=name,
                        usage=f"<profile> <{_usage}>"
                        if self.use_profiles_system
                        else f"<{_usage}>",
                        help=_help,
                        with_app_command=False,
                    )(command)
                else:
                    command: commands.Command = self.commands_group.command(
                        name=name,
                        usage=f"<profile> <{_usage}>"
                        if self.use_profiles_system
                        else f"<{_usage}>",
                        help=_help,
                    )(command)

                command.name = name
                # command.brief = _help
                # command.description = _help
                command.callback.__doc__ = _help
                command.cog = self.cog
                self.bot.dispatch("command_add", command)
                if self.bot.get_cog("permissions") is None:
                    command.requires.ready_event.set()
                if "ctx" in command.params:
                    del command.params["ctx"]
                setattr(self, f"settings_{name}", command)
                cog_commands = list(self.cog.__cog_commands__)
                cog_commands.append(command)
                self.cog.__cog_commands__ = tuple(cog_commands)
                self.commands[f"{name}"] = command

        if self.group != Config.GLOBAL:
            self.rpc_callback_settings.__dashboard_decorator_params__[1]["context_ids"] = ["guild_id", f"{self.group.lower()}_id"]
        setattr(self.cog, "rpc_callback_settings", self.rpc_callback_settings)
        self.commands_added.set()

    async def command(
        self,
        ctx: commands.Context,
        key: typing.Optional[str] = None,
        value: typing.Optional[typing.Any] = None,
        _object: typing.Optional[
            typing.Union[
                discord.Guild, discord.Member, discord.abc.Messageable, discord.Role, discord.User
            ]
        ] = None,
        profile: typing.Optional[str] = None,
    ) -> None:
        if key is None:
            for setting in self.settings:
                if self.settings[setting]["command_name"] == ctx.command.name:
                    key = setting
                    break
            else:
                raise commands.UserFeedbackCheckFailure(_("No setting found."))
        if value is None:
            value = ctx.kwargs["value"]
        if _object is None:
            if self.group == Config.GLOBAL:
                _object = None
            elif self.group == Config.GUILD:
                _object = ctx.guild
            elif self.group == Config.MEMBER:
                _object = ctx.author
            elif self.group == Config.CHANNEL:
                _object = ctx.author
            elif self.group == Config.ROLE:
                _object = ctx.author.top_role
            elif self.group == Config.USER:
                _object = ctx.author
        if value is not discord.utils.MISSING:
            if isinstance(value, CustomMessageConverter):
                value = value.to_dict()
            try:
                await self.set_raw(
                    key=key,
                    value=getattr(value, "id", None) or getattr(value, "value", None) or value,
                    _object=_object,
                    profile=profile,
                )
            except self.NotExistingPanel:
                await ctx.send("This profile don't exist.")
                return
        else:
            try:
                await self.clear_raw(key=key, _object=_object, profile=profile)
            except self.NotExistingPanel:
                await ctx.send("This profile don't exist.")
                return

    async def add_profile(self, ctx: commands.Context, profile: str) -> None:
        if len(profile) > 10:
            await ctx.send(_("The name of a profile must be less than or equal to 10 characters."))
            return
        data = self.get_data(ctx=ctx)
        profiles = await data.get_raw(*self.global_path)
        if profile.lower() in profiles:
            await ctx.send(_("This profile already exists."))
            return
        await data.set_raw(
            *self.global_path,
            profile.lower(),
            value=self.config._defaults[self.group]["default_profile_settings"],
        )

    async def clone_profile(self, ctx: commands.Context, old_profile: str, profile: str) -> None:
        if len(profile) > 10:
            await ctx.send(_("The name of a profile must be less than or equal to 10 characters."))
            return
        data = self.get_data(ctx=ctx)
        profiles = await data.get_raw(*self.global_path)
        if profile in profiles:
            await ctx.send(_("This profile already exists."))
            return
        await data.set_raw(
            *self.global_path, profile, value=await data.get_raw(*self.global_path, old_profile)
        )
        if self.cog.qualified_name == "TicketTool":
            await data.set_raw(*self.global_path, profile, "last_nb", value=0)

    async def remove_profile(
        self, ctx: commands.Context, profile: str, confirmation: typing.Optional[bool] = False
    ) -> None:
        if not confirmation:
            embed: discord.Embed = discord.Embed()
            embed.title = _("Do you really want to remove this profile?")
            if self.cog.qualified_name == "TicketTool":
                embed.description = _(
                    "All tickets associated with this profile will be removed from the Config, but the channels will still exist. Commands related to the tickets will no longer work."
                )
            embed.color = 0xF00020
            response = await self.cog.cogsutils.ConfirmationAsk(ctx, embed=embed)
            if not response:
                return
        data = self.get_data(ctx=ctx)
        await data.clear_raw(*self.global_path, profile)
        if self.cog.qualified_name == "TicketTool":
            data = await self.cog.config.guild(ctx.guild).tickets.all()
            to_remove = [
                channel for channel in data if data[channel].get("panel", "main") == profile
            ]
            for channel in to_remove:
                try:
                    del data[channel]
                except KeyError:
                    pass
            await self.cog.config.guild(ctx.guild).tickets.set(data)

    async def rename_profile(self, ctx: commands.Context, old_profile: str, profile: str) -> None:
        if len(profile) > 10:
            await ctx.send(_("The name of a profile must be less than or equal to 10 characters."))
            return
        data = self.get_data(ctx=ctx)
        profiles = await data.get_raw(*self.global_path)
        if profile in profiles:
            await ctx.send(_("A panel with this name already exists."))
            return
        await data.set_raw(
            *self.global_path, profile, value=await data.get_raw(*self.global_path, old_profile)
        )
        await data.clear_raw(*self.global_path, old_profile)
        if self.cog.qualified_name == "TicketTool":
            guild_group = self.config._get_base_group(self.config.GUILD)
            async with guild_group.all() as guilds_data:
                _guilds_data = deepcopy(guilds_data)
                for guild in _guilds_data:
                    if "tickets" in guilds_data[guild]:
                        for channel_id in guilds_data[guild]["tickets"]:
                            if "profile" not in guilds_data[guild]["tickets"][channel_id]:
                                continue
                            if guilds_data[guild]["tickets"][channel_id]["profile"] != old_profile:
                                continue
                            guilds_data[guild]["tickets"][channel_id]["profile"] = profile
                    if "buttons" in guilds_data[guild]:
                        for message_id in guilds_data[guild]["buttons"]:
                            if "profile" not in guilds_data[guild]["buttons"][message_id]:
                                continue
                            if guilds_data[guild]["buttons"][message_id]["profile"] != old_profile:
                                continue
                            guilds_data[guild]["buttons"][message_id]["profile"] = profile
                    if "dropdowns" in guilds_data[guild]:
                        for message_id in guilds_data[guild]["dropdowns"]:
                            if "profile" not in guilds_data[guild]["dropdowns"][message_id]:
                                continue
                            if guilds_data[guild]["dropdowns"][message_id]["profile"] != old_profile:
                                continue
                            guilds_data[guild]["dropdowns"][message_id]["profile"] = profile

    async def list_profiles(self, ctx: commands.Context) -> None:
        """List the existing profiles."""
        data = self.get_data(ctx=ctx)
        profiles = await data.get_raw(*self.global_path)
        message = f"---------- Profiles in {self.cog.qualified_name} ----------\n\n"
        message += "\n".join([f"- {profile}" for profile in profiles])
        await Menu(pages=message, lang="py").start(ctx)

    async def show_settings(
        self,
        ctx: commands.Context,
        _object: typing.Optional[
            typing.Union[
                discord.Guild, discord.Member, discord.abc.Messageable, discord.Role, discord.User
            ]
        ] = None,
        profile: typing.Optional[str] = None,
        with_dev: typing.Optional[bool] = False,
    ) -> None:
        if _object is None:
            if self.group == Config.GLOBAL:
                _object = None
            elif self.group == Config.GUILD:
                _object = ctx.guild
            elif self.group == Config.MEMBER:
                _object = ctx.author
            elif self.group == Config.CHANNEL:
                _object = ctx.author
            elif self.group == Config.ROLE:
                _object = ctx.author.top_role
            elif self.group == Config.USER:
                _object = ctx.author
        message = (
            f"---------- {self.cog.qualified_name}'s Settings for `{profile}` profile ----------\n```\n\n```py\n"
            if self.use_profiles_system
            else f"---------- {self.cog.qualified_name}'s Settings ----------\n```\n\n```py\n"
        )
        try:
            values = await self.get_values(_object=_object, profile=profile)
        except self.NotExistingPanel:
            await ctx.send("This profile don't exist.")
            return
        if not with_dev:
            raw_table = Table("Key", "Default", "Value", "Converter")
            for value in values:
                raw_table.add_row(
                    value.replace("_", " ").title().replace(" ", ""),
                    repr(values[value]["default"]),
                    repr(values[value]["value"]),
                    (
                        "|".join(
                            f'"{v}"' if isinstance(v, str) else str(v)
                            for v in self.settings[value]["converter"].__args__
                        )
                    )
                    if self.settings[value]["converter"] is typing.Literal
                    else getattr(self.settings[value]["converter"], "__name__", ""),
                )
        else:
            raw_table = Table("Key", "Default", "Value", "Converter", "Path")
            for value in values:
                raw_table.add_row(
                    value.replace("_", " ").title().replace(" ", ""),
                    repr(values[value]["default"]),
                    repr(values[value]["value"]),
                    (
                        "|".join(
                            f'"{v}"' if isinstance(v, str) else str(v)
                            for v in self.settings[value]["converter"].__args__
                        )
                    )
                    if self.settings[value]["converter"] is typing.Literal
                    else getattr(self.settings[value]["converter"], "__name__", ""),
                    str([self.group] + self.global_path + [profile] + self.settings[value]["path"])
                    if self.use_profiles_system
                    else str([self.group] + self.global_path + self.settings[value]["path"]),
                )
        raw_table_str = no_colour_rich_markup(raw_table, no_box=True)
        message += raw_table_str
        await Menu(pages=message, lang="py").start(ctx)

    async def send_modal(
        self,
        ctx: commands.Context,
        _object: typing.Optional[
            typing.Union[
                discord.Guild, discord.Member, discord.abc.Messageable, discord.Role, discord.User
            ]
        ] = None,
        profile: typing.Optional[str] = None,
        confirmation: typing.Optional[bool] = False,
    ) -> None:
        if _object is None:
            if self.group == Config.GLOBAL:
                _object = None
            elif self.group == Config.GUILD:
                _object = ctx.guild
            elif self.group == Config.MEMBER:
                _object = ctx.author
            elif self.group == Config.CHANNEL:
                _object = ctx.author
            elif self.group == Config.ROLE:
                _object = ctx.author.top_role
            elif self.group == Config.USER:
                _object = ctx.author
        values = await self.get_values(_object=_object, profile=profile)
        data = self.get_data(_object)
        config = (
            await data.get_raw(*self.global_path, profile)
            if self.use_profiles_system
            else await data.get_raw(*self.global_path)
        )
        one_l = list(self.settings)
        two_l = []
        three_l = {}
        while True:
            lst = one_l[:5]
            one_l = one_l[5:]
            two_l.append(lst)
            if one_l == []:
                break
        for i, l in enumerate(two_l, start=1):
            three_l[i] = l

        async def on_modal(
            view: Modal, interaction: discord.Interaction, inputs: typing.List, config: typing.Dict
        ):
            if not interaction.response.is_done():
                await interaction.response.defer()
            for _input in inputs:
                custom_id = _input.custom_id[21:]
                if _input.value == "":
                    assert self.settings[custom_id]["path"]
                    if len(self.settings[custom_id]["path"]) == 1:
                        c = config
                    else:
                        for x in self.settings[custom_id]["path"][:-1]:
                            c = config.get(x, {})
                    c[self.settings[custom_id]["path"][-1]] = values[custom_id]["default"]
                    continue
                if (
                    getattr(_input.value, "id", None)
                    or getattr(_input.value, "value", None)
                    or _input.value
                ) == values[custom_id]["value"]:
                    continue
                try:
                    value = await discord.ext.commands.converter.run_converters(
                        ctx,
                        converter=self.settings[custom_id]["converter"],
                        argument=str(_input.value),
                        param=self.settings[custom_id]["param"],
                    )
                except discord.ext.commands.errors.CommandError as e:
                    await ctx.send(
                        f"An error occurred when using the `{_input.label}` converter:\n{box(e, lang='py')}"
                    )
                    return None
                if (
                    getattr(value, "id", None) or getattr(value, "value", None) or value
                ) == values[custom_id]["value"]:
                    continue
                assert self.settings[custom_id]["path"]
                if len(self.settings[custom_id]["path"]) == 1:
                    c = config
                else:
                    for x in self.settings[custom_id]["path"][:-1]:
                        c = config.get(x, {})
                c[self.settings[custom_id]["path"][-1]] = (
                    getattr(value, "id", None) or getattr(value, "value", None) or value
                )

        async def on_button(
            view: Buttons,
            interaction: discord.Interaction,
            config: typing.Dict,
            three_l: typing.Dict,
        ):
            if not interaction.response.is_done():
                await interaction.response.defer()
            if interaction.data["custom_id"] == "Settings_ModalConfig_cancel":
                view.stop()
            elif interaction.data["custom_id"] == "Settings_ModalConfig_done":
                if not confirmation:
                    embed: discord.Embed = discord.Embed()
                    embed.title = _(
                        "⚙️ Do you want to replace the entire Config of {cog.qualified_name} with what you specified?"
                    ).format(cog=self.cog)
                    if await self.cog.cogsutils.ConfirmationAsk(ctx, embed=embed):
                        if self.use_profiles_system:
                            await data.set_raw(*self.global_path, profile, value=config)
                        else:
                            await data.set_raw(*self.global_path, value=config)
                view.stop()
            elif interaction.data["custom_id"] == "Settings_ModalConfig_view":
                await Menu(pages=str(config), leng="py").start(ctx)
            elif interaction.data["custom_id"].startswith("Settings_ModalConfig_configure_"):
                inputs = three_l[int(interaction.data["custom_id"][31:])]
                view_modal = Modal(
                    title=f"{self.cog.qualified_name} Config",
                    inputs=[
                        {
                            "label": (
                                self.settings[setting]["label"]
                                + " ("
                                + (
                                    (
                                        "|".join(
                                            f'"{v}"'
                                            if isinstance(v, str)
                                            else str(v)
                                            for v in self.settings[setting][
                                                "converter"
                                            ].__args__
                                        )
                                    )
                                    if self.settings[setting]["converter"]
                                    is typing.Literal
                                    else getattr(
                                        self.settings[setting]["converter"],
                                        "__name__",
                                        "",
                                    )
                                )
                                + ")"
                            )[:44],
                            "style": self.settings[setting]["style"],
                            "placeholder": str(values[setting]["default"]),
                            "default": (
                                str(values[setting]["value"])
                                if self.settings[setting]["converter"]
                                is not CustomMessageConverter
                                else json.dumps(values[setting]["value"])
                            )
                            if str(values[setting]["value"])
                            != str(values[setting]["default"])
                            else None,
                            "required": False,
                            "custom_id": f"Settings_ModalConfig_{setting}",
                        }
                        for setting in inputs
                    ],
                    function=on_modal,
                    function_kwargs={"config": config},
                    custom_id=f"Settings_ModalConfig_{self.cog.qualified_name}",
                )
                await interaction.response.send_modal(view_modal)

        buttons = [
            {
                "label": "Cancel",
                "emoji": "❌",
                "style": 4,
                "disabled": False,
                "custom_id": "Settings_ModalConfig_cancel",
            },
            {
                "label": "Save",
                "emoji": "✅",
                "style": 3,
                "disabled": False,
                "custom_id": "Settings_ModalConfig_done",
            },
            {
                "label": "View",
                "emoji": "🔍",
                "style": 1,
                "disabled": False,
                "custom_id": "Settings_ModalConfig_view",
            },
        ]
        for i in three_l:
            buttons.append(
                {
                    "label": f"Configure {i}",
                    "emoji": "⚙️",
                    "disabled": False,
                    "custom_id": f"Settings_ModalConfig_configure_{i}",
                }
            )
        view_button = Buttons(
            timeout=360,
            buttons=buttons,
            members=[ctx.author.id] + list(ctx.bot.owner_ids),
            function=on_button,
            function_kwargs={"config": config, "three_l": three_l},
            infinity=True,
        )
        message = await ctx.send(
            _("Click on the buttons below to fully set up the cog {cog.qualified_name}.").format(
                cog=self.cog
            ),
            view=view_button,
        )
        await view_button.wait()
        for i, button in enumerate(buttons):
            buttons[i]["disabled"] = True
        await message.edit(view=Buttons(timeout=None, buttons=buttons))
        return config

    @dashboard_page(name="settings", methods=["GET", "POST"])
    async def rpc_callback_settings(
        self,
        method: str,
        user: discord.User,
        profile: typing.Optional[str] = None,
        **kwargs,
    ):
        if "guild" in kwargs:
            guild = kwargs["guild"]
            context = await self.cog.cogsutils.invoke_command(
                author=user,
                channel=kwargs.get("channel", guild.text_channels[0]),
                command=f"{self.commands_group.qualified_name}",
                invoke=False,
            )
            context.__dashboard_fake__ = True
            if not await self.commands_group.can_run(context):
                return {"status": 1, "error_message": "You are not allowed to access these settings."}
        else:
            context = await self.cog.cogsutils.invoke_command(
                author=user,
                channel=list(self.bot.get_all_channels())[0],
                command=f"{self.commands_group.qualified_name}",
                invoke=False,
            )
            context.__dashboard_fake__ = True
        try:
            if self.group == Config.GLOBAL:
                _object = None
            elif self.group == Config.GUILD:
                _object = kwargs["guild"]
            elif self.group == Config.MEMBER:
                _object = kwargs["member"]
            elif self.group == Config.CHANNEL:
                _object = kwargs["channel"]
            elif self.group == Config.ROLE:
                _object = kwargs["role"]
        except KeyError:
            return {"status": 1, "error_message": f"Missing `{self.group.lower()}_id` argument."}
        values = await self.get_values(_object=_object, profile=profile)
        data = self.get_data(_object)
        if self.use_profiles_system:
            profiles = list(await data.get_raw(*self.global_path))
            if profile is None:
                web_content = """
                {% extends "base-site.html" %}

                {% block title %} {{ _('{COG_NAME} Config') }} {% endblock title %}

                {% block content %}
                <h2>{COG_NAME} Config</h2>
                <div class="row">
                    <div class="col-md-12">
                        <div class="card">
                            <div class="card-body">
                                <div id="profiles-table">
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                {% endblock content %}

                {% block javascripts %}
                <script>
                    let currentUrlParams = new URLSearchParams(window.location.search);
                    let profiles = {{ profiles | tojson }};
                    let profileLinks = profiles.map(profile => {
                        let linkUrlParams = new URLSearchParams(currentUrlParams);
                        linkUrlParams.set("profile", profile);
                        let linkUrl = `${window.location.pathname}?${linkUrlParams.toString()}`;
                        let linkText = profile;
                        return [`<a href="${linkUrl}">${linkText}</a>`];
                    });
                    $.showTableRegular(element=$("#profiles-table"), columns=["Profiles:"], data=profileLinks);
                </script>
                {% endblock javascripts %}
                """.replace(
                    "{COG_NAME}", self.cog.qualified_name
                )
                return {"status": 1, "web-content": web_content, "profiles": profiles}
            elif profile.lower() not in profiles:
                return {"status": 1, "error_message": "This profile does not exist."}
        config = (
            await data.get_raw(*self.global_path, profile)
            if self.use_profiles_system
            else await data.get_raw(*self.global_path)
        )
        if method == "GET":
            web_content = """
            {% extends "base-site.html" %}

            {% block title %} {{ _('{COG_NAME} Config') }} {% endblock title %}

            {% block content %}
            <h2>{COG_NAME} Config</h2>
            <div class="row">
                <div class="col-md-12">
                    <div class="card">
                        <div class="card-body">
                            <div id="settings-form">
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            {% endblock content %}

            {% block javascripts %}
            <script>
                let fields = {{ fields | tojson }};
                $.generateForm(element=$("#settings-form"), fields=fields, formID=null, resetForm=false);
            </script>
            {% endblock javascripts %}
            """.replace(
                "{COG_NAME}", self.cog.qualified_name
            )
            fields = []
            for setting in list(self.settings):
                field = {
                    "label": (
                        self.settings[setting]["label"]
                        + " ("
                        + (
                            (
                                "|".join(
                                    f'"{v}"' if isinstance(v, str) else str(v)
                                    for v in self.settings[setting]["converter"].__args__
                                )
                            )
                            if self.settings[setting]["converter"] is typing.Literal
                            else getattr(
                                self.settings[setting]["converter"],
                                "__name__",
                                "",
                            )
                        )
                        + ")"
                    ),
                    "type": "text",
                    "placeholder": str(values[setting]["default"]),
                    "name": setting,  # custom id
                }
                if str(values[setting]["value"]) != str(values[setting]["default"]):
                    field["value"] = (
                        str(values[setting]["value"])
                        if self.settings[setting]["converter"]
                        is not CustomMessageConverter
                        else json.dumps(values[setting]["value"])
                    )
                # field["required"] = False
                if not self.can_edit:
                    field["disabled"] = True
                fields.append(field)
            return {"status": 0, "web-content": web_content, "fields": fields}
        elif method == "POST":
            _data = kwargs["data"]["form_data"]
            errors = {}
            for setting in self.settings:
                custom_id = setting
                _input = _data[setting]
                if _input == "":
                    if len(self.settings[custom_id]["path"]) == 1:
                        c = config
                    else:
                        for x in self.settings[custom_id]["path"][:-1]:
                            c = config.get(x, {})
                    c[self.settings[custom_id]["path"][-1]] = values[custom_id]["default"]
                    continue
                if _input == values[custom_id]["value"]:
                    continue
                try:
                    value = await discord.ext.commands.converter.run_converters(
                        context,
                        converter=self.settings[custom_id]["converter"],
                        argument=str(_input),
                        param=self.settings[custom_id]["param"],
                    )
                except discord.ext.commands.errors.CommandError as e:
                    errors[setting] = str(e)
                    continue
                if (
                    getattr(value, "id", None) or getattr(value, "value", None) or value
                ) == values[custom_id]["value"]:
                    continue
                assert self.settings[custom_id]["path"]
                if len(self.settings[custom_id]["path"]) == 1:
                    c = config
                else:
                    for x in self.settings[custom_id]["path"][:-1]:
                        c = config.get(x, {})
                c[self.settings[custom_id]["path"][-1]] = (
                    getattr(value, "id", None) or getattr(value, "value", None) or value
                )
            if errors:
                return {
                    "status": 1,
                    "notifications": [
                        {
                            "type": "warning",
                            "message": "An error occurred when using the settings converters.",
                        }
                    ],
                    "errors": errors,
                }
            if self.use_profiles_system:
                await data.set_raw(*self.global_path, profile, value=config)
            else:
                await data.set_raw(*self.global_path, value=config)
            return {
                "status": 0,
                "notifications": [{"type": "success", "message": "Data successfully saved."}],
            }

    async def get_raw(
        self,
        key: str,
        _object: typing.Optional[
            typing.Union[
                discord.Guild, discord.Member, discord.abc.Messageable, discord.Role, discord.User
            ]
        ] = None,
        profile: typing.Optional[str] = None,
    ) -> typing.Any:
        if key not in self.settings:
            raise KeyError(key)
        data = self.get_data(_object)
        setting = self.settings[key]
        if not self.use_profiles_system:
            return await data.get_raw(*self.global_path, *setting["path"])
        try:
            profiles = await data.get_raw(*self.global_path)
        except KeyError:
            profiles = {}
        try:
            profiles[profile]
        except KeyError:
            raise self.NotExistingPanel(profile)
        return await data.get_raw(*self.global_path, profile, *setting["path"])

    async def set_raw(
        self,
        key: str,
        value: typing.Any,
        _object: typing.Optional[
            typing.Union[
                discord.Guild, discord.Member, discord.abc.Messageable, discord.Role, discord.User
            ]
        ] = None,
        profile: typing.Optional[str] = None,
    ) -> None:
        if key not in self.settings:
            raise KeyError(key)
        data = self.get_data(_object)
        setting = self.settings[key]
        if not self.use_profiles_system:
            await data.set_raw(*self.global_path, *setting["path"], value=value)
        else:
            try:
                profiles = await data.get_raw(*self.global_path)
            except KeyError:
                profiles = {}
            try:
                profiles[profile]
            except KeyError:
                raise self.NotExistingPanel(profile)
            await data.set_raw(*self.global_path, profile, *setting["path"], value=value)

    async def clear_raw(
        self,
        key: str,
        _object: typing.Optional[
            typing.Union[
                discord.Guild, discord.Member, discord.abc.Messageable, discord.Role, discord.User
            ]
        ] = None,
        profile: typing.Optional[str] = None,
    ) -> None:
        if key not in self.settings:
            raise KeyError(key)
        data = self.get_data(_object)
        setting = self.settings[key]
        if not self.use_profiles_system:
            await data.clear_raw(*self.global_path, setting["path"])
        else:
            try:
                profiles = await data.get_raw(*self.global_path)
            except KeyError:
                profiles = {}
            try:
                profiles[profile]
            except KeyError:
                raise self.NotExistingPanel(profile)
            await data.clear_raw(*self.global_path, profile, *setting["path"])

    def get_data(
        self,
        _object: typing.Optional[
            typing.Union[
                discord.Guild, discord.Member, discord.abc.Messageable, discord.Role, discord.User
            ]
        ] = None,
        ctx: typing.Optional[commands.Context] = None,
    ) -> redbot.core.config.Group:
        if _object is None and ctx is not None:
            if self.group == Config.GLOBAL:
                _object = None
            elif self.group == Config.GUILD:
                _object = ctx.guild
            elif self.group == Config.MEMBER:
                _object = ctx.author
            elif self.group == Config.CHANNEL:
                _object = ctx.author
            elif self.group == Config.ROLE:
                _object = ctx.author.top_role
            elif self.group == Config.USER:
                _object = ctx.author
        data = {}
        if self.group == Config.GLOBAL:
            data = self.config
        elif self.group == Config.GUILD:
            if isinstance(_object, discord.Guild):
                data = self.config.guild(_object)
            elif isinstance(_object, int):
                data = self.config.guild_from_id(_object)
        elif self.group == Config.MEMBER:
            if isinstance(_object, discord.Member):
                data = self.config.member(_object)
            elif isinstance(_object, typing.List) and len(_object) == 2:
                data = self.config.member_from_ids(*_object)
        elif self.group == Config.CHANNEL:
            if isinstance(_object, discord.abc.Messageable):
                data = self.config.channel(_object)
            elif isinstance(_object, int):
                data = self.config.channel_from_id(_object)
        elif self.group == Config.ROLE:
            if isinstance(_object, discord.Role):
                data = self.config.role(_object).all()
            elif isinstance(_object, int):
                data = self.config.role_from_id(_object)
        elif self.group == Config.USER:
            if isinstance(_object, discord.User):
                data = self.config.user(_object)
            elif isinstance(_object, int):
                data = self.config.user_from_id(_object)
        else:
            return self.config.custom(self.group if _object is None else _object)
        return data

    async def get_values(
        self,
        _object: typing.Optional[
            typing.Union[
                discord.Guild, discord.Member, discord.abc.Messageable, discord.Role, discord.User
            ]
        ] = None,
        profile: typing.Optional[str] = None,
    ) -> typing.Dict[str, typing.Dict[str, typing.Any]]:
        result = {}
        data = self.get_data(_object)
        for setting in self.settings:
            if not self.use_profiles_system:
                default = self.config._defaults.get(self.group, {})
                for x in self.global_path:
                    default = default.get(x, {})
            else:
                default = await data.get_raw(*self.global_path[:-1], "default_profile_settings")
            for x in self.settings[setting]["path"]:
                default = default.get(x, {})
            if default == {}:
                default = discord.utils.MISSING
            try:
                if not self.use_profiles_system:
                    value = await data.get_raw(*self.global_path, *self.settings[setting]["path"])
                else:
                    try:
                        profiles = await data.get_raw(*self.global_path)
                    except KeyError:
                        profiles = {}
                    try:
                        profiles[profile]
                    except KeyError:
                        raise self.NotExistingPanel(profile)
                    value = await data.get_raw(
                        *self.global_path, profile, *self.settings[setting]["path"]
                    )
            except KeyError:
                value = default
            result[setting] = {"default": default, "value": value}
        return result

    class NotExistingPanel(KeyError):
        pass

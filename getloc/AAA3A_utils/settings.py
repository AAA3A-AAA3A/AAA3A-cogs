from redbot.core import commands  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import asyncio
import inspect
from io import StringIO

from redbot.core import Config
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import box
from rich.console import Console
from rich.table import Table

from .menus import Menu
if discord.version_info.major >= 2:
    from .views import Buttons, Modal

__all__ = ["Settings"]

if discord.version_info.major >= 2:
    from functools import partial

    hybrid_command = partial(commands.hybrid_command, with_app_command=False)
    hybrid_group = partial(commands.hybrid_group, with_app_command=False)
else:
    hybrid_command = commands.command
    hybrid_group = commands.group


def _(untranslated: str):
    return untranslated


def no_colour_rich_markup(*objects: typing.Any, lang: str = "", no_box: typing.Optional[bool] = False) -> str:
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
            return '...'
    discord.utils.MISSING = _MissingSentinel()

class Settings():

    def __init__(self, bot: Red, cog: commands.Cog, config: Config, group: str, settings: typing.Dict[str, typing.Dict[str, typing.Any]], global_path: typing.Optional[typing.List] = [], use_profiles_system: typing.Optional[bool] = False, can_edit: typing.Optional[bool] = True, commands_group: typing.Optional[typing.Union[commands.Group, str]] = None):
        # {"enable": {"path": ["settings", "enabled"], "converter": bool, "command_name": "enable", "label": "Enable", "description": "Enable the system.", "usage": "enable", "style": 1}}
        self.bot = bot
        self.cog = cog
        self.config = config
        self.group = group
        self.global_path = global_path
        self.use_profiles_system = use_profiles_system
        self.can_edit = can_edit
        self.commands_group = commands_group
        self.commands_added = asyncio.Event()
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
                if self.cog.cogsutils.is_dpy2 and settings[setting]["converter"] in discord.ext.commands.converter.CONVERTER_MAPPING:
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
            if self.cog.cogsutils.is_dpy2:
                settings[setting]["param"] = discord.ext.commands.parameters.Parameter(
                    name=setting,
                    kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    annotation=settings[setting]["converter"],
                )
            else:
                settings[setting]["param"] = inspect.Parameter(
                    name=setting,
                    kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    annotation=settings[setting]["converter"],
                )
            if self.cog.cogsutils.is_dpy2:
                if "style" not in settings[setting]:
                    settings[setting]["style"] = discord.TextStyle.short
                else:
                    if isinstance(settings[setting]["style"], int):
                        settings[setting]["style"] = discord.TextStyle(settings[setting]["style"])
        self.settings = settings

    async def add_commands(self, force: typing.Optional[bool] = False):

        if not isinstance(self.commands_group, commands.Group):
            name = "set" + (self.commands_group if isinstance(self.commands_group, str) else self.cog.qualified_name.lower())
            aliases = [((self.commands_group if isinstance(self.commands_group, str) else self.cog.qualified_name.lower()) + "set")]
            _help = f"Commands to edit {self.cog.qualified_name}'s settings."
            if force:
                self.bot.remove_command(name)

            async def commands_group(self, ctx: commands.Context):
                pass

            commands_group.__qualname__ = f"{self.cog.qualified_name}.{name}"
            commands_group: commands.Group = commands.admin_or_permissions(administrator=True)(hybrid_group(name=name, aliases=aliases, help=_help)(commands_group))
            commands_group.name = name
            # commands_group.brief = _help
            # commands_group.description = _help
            commands_group.callback.__doc__ = _help
            commands_group.cog = self.cog
            if self.cog.cogsutils.is_dpy2:
                if "ctx" in commands_group.params:
                    del commands_group.params["ctx"]
            self.bot.add_command(commands_group)
            cog_commands = list(self.cog.__cog_commands__)
            cog_commands.append(commands_group)
            self.cog.__cog_commands__ = tuple(cog_commands)
            self.commands_group = commands_group
            setattr(self, f"{name}", commands_group)

        class ProfileConverter(commands.Converter):
            async def convert(_self, ctx: commands.Context, arg: str):
                if len(arg) > 10:
                    raise commands.BadArgument(_("This profile does not exist."))
                if self.group == Config.GLOBAL:
                    object = None
                elif self.group == Config.GUILD:
                    object = ctx.guild
                elif self.group == Config.MEMBER:
                    object = ctx.author
                elif self.group == Config.CHANNEL:
                    object = ctx.author
                elif self.group == Config.ROLE:
                    object = ctx.author.top_role
                elif self.group == Config.USER:
                    object = ctx.author
                data = self.get_data(object)
                profiles = await data.get_raw(*self.global_path)
                if arg.lower() not in profiles:
                    raise commands.BadArgument(_("This profile does not exist."))
                return arg.lower()

        if not self.use_profiles_system:
            async def show_settings(_self, ctx: commands.Context, with_dev: typing.Optional[bool] = False):
                """Show all settings for the cog with defaults and values."""
                await self.show_settings(ctx, with_dev=with_dev)
            async def modal_config(_self, ctx: commands.Context, confirmation: typing.Optional[bool] = False):
                """Set all settings for the cog with a Discord Modal."""
                await self.send_modal(ctx, confirmation=confirmation)
        else:
            async def show_settings(_self, ctx: commands.Context, profile: ProfileConverter, with_dev: typing.Optional[bool] = False):
                """Show all settings for the cog with defaults and values."""
                await self.show_settings(ctx, profile=profile, with_dev=with_dev)
            async def modal_config(_self, ctx: commands.Context, profile: ProfileConverter, confirmation: typing.Optional[bool] = False):
                """Set all settings for the cog with a Discord Modal."""
                await self.send_modal(ctx, profile=profile, confirmation=confirmation)
            async def add_profile(_self, ctx: commands.Context, profile: str):
                """Create a new profile with defaults settings."""
                await self.add_profile(ctx, profile=profile)
            async def clone_profile(_self, ctx: commands.Context, old_profile: ProfileConverter, profile: str):
                """Clone an existing profile with his settings."""
                await self.clone_profile(ctx, old_profile=old_profile, profile=profile)
            async def remove_profile(_self, ctx: commands.Context, profile: ProfileConverter, confirmation: typing.Optional[bool]=False):
                """Remove an existing profile."""
                await self.remove_profile(ctx, profile=profile, confirmation=confirmation)
            async def rename_profile(_self, ctx: commands.Context, old_profile: ProfileConverter, profile: str):
                """Clone an existing profile with his settings."""
                await self.rename_profile(ctx, old_profile=old_profile, profile=profile)
            async def list_profiles(_self, ctx: commands.Context):
                """List the existing profiles."""
                await self.list_profiles(ctx)
        to_add = {"showsettings": show_settings, "modalconfig": modal_config, "profileadd": add_profile, "profileclone": clone_profile, "profileremove": remove_profile, "profilerename": rename_profile, "profileslist": list_profiles}
        aliases = {"modalconfig": ["configmodal"], "profileadd": ["addprofile"], "profileclone": ["cloneprofile"], "profileremove": ["removeprofile"], "profilerename": ["renameprofile"], "profileslist": ["listprofiles"]}
        if not self.use_profiles_system:
            for name in ["profileadd", "profileclone", "profileremove", "profilerename", "profileslist"]:
                try:
                    del to_add[name]
                except KeyError:
                    pass
        if not (self.can_edit or force):
            for name in ["modalconfig", "profileadd", "profileclone", "profileremove", "profilerename"]:
                try:
                    del to_add[name]
                except KeyError:
                    pass
        for name, command in to_add.items():
            command.__qualname__ = f"{self.cog.qualified_name}.settings_{name}"
            command: commands.Command = self.commands_group.command(name=name, aliases=aliases.get(name, []))(command)
            command.name = name
            command.cog = self.cog
            self.bot.dispatch("command_add", command)
            if self.bot.get_cog("permissions") is None:
                command.requires.ready_event.set()
            if self.cog.cogsutils.is_dpy2:
                if "ctx" in command.params:
                    del command.params["ctx"]
            setattr(self, f"settings_{name}", command)
            cog_commands = list(self.cog.__cog_commands__)
            cog_commands.append(command)
            self.cog.__cog_commands__ = tuple(cog_commands)

        if self.can_edit or force:
            for setting in self.settings:
                name = self.settings[setting]["command_name"]
                self.commands_group.remove_command(name)
                _help = self.settings[setting]["description"]
                _help += "\n\nIf you do not specify a value, the default value will be restored.\nDev: " + repr(self.settings[setting]["converter"])
                _usage = self.settings[setting]["usage"]

                if not self.use_profiles_system:
                    async def command(_self, ctx: commands.Context, *, value: typing.Optional[self.settings[setting]["converter"]] = None):
                        if value is None:
                            value = discord.utils.MISSING
                        await self.command(ctx, key=None, value=value)
                else:
                    async def command(_self, ctx: commands.Context, profile: ProfileConverter, *, value: typing.Optional[self.settings[setting]["converter"]] = None):
                        if value is None:
                            value = discord.utils.MISSING
                        await self.command(ctx, key=None, value=value, profile=profile)
                command.__qualname__ = f"{self.cog.qualified_name}.settings_{name}"
                command: commands.Command = self.commands_group.command(name=name, usage=(f"[{_usage}]" if not self.use_profiles_system else f"<profile> [{_usage}]"), help=_help)(command)
                if self.settings[setting]["no_slash"]:
                    command.no_slash = True

                command.name = name
                # command.brief = _help
                # command.description = _help
                command.callback.__doc__ = _help
                command.cog = self.cog
                self.bot.dispatch("command_add", command)
                if self.bot.get_cog("permissions") is None:
                    command.requires.ready_event.set()
                if self.cog.cogsutils.is_dpy2:
                    if "ctx" in command.params:
                        del command.params["ctx"]
                setattr(self, f"settings_{name}", command)
                cog_commands = list(self.cog.__cog_commands__)
                cog_commands.append(command)
                self.cog.__cog_commands__ = tuple(cog_commands)

        self.commands_added.set()

    async def command(self, ctx: commands.Context, key: typing.Optional[str] = None, value: typing.Optional[typing.Any] = None, object: typing.Optional[typing.Union[discord.Guild, discord.Member, discord.abc.Messageable, discord.Role, discord.User]] = None, profile: typing.Optional[str] = None):
        if key is None:
            for setting in self.settings:
                if self.settings[setting]["command_name"] == ctx.command.name:
                    key = setting
                    break
            else:
                await ctx.send("No setting found.")
                return
        if value is None:
            value = ctx.kwargs["value"]
        if object is None:
            if self.group == Config.GLOBAL:
                object = None
            elif self.group == Config.GUILD:
                object = ctx.guild
            elif self.group == Config.MEMBER:
                object = ctx.author
            elif self.group == Config.CHANNEL:
                object = ctx.author
            elif self.group == Config.ROLE:
                object = ctx.author.top_role
            elif self.group == Config.USER:
                object = ctx.author
        if value is not discord.utils.MISSING:
            try:
                await self.set_raw(key=key, value=getattr(value, "id", None) or getattr(value, "value", None) or value, object=object, profile=profile)
            except self.NotExistingPanel:
                await ctx.send("This profile don't exist.")
                return
        else:
            try:
                await self.clear_raw(key=key, object=object, profile=profile)
            except self.NotExistingPanel:
                await ctx.send("This profile don't exist.")
                return

    async def add_profile(self, ctx: commands.Context, profile: str):
        if len(profile) > 10:
            await ctx.send(_("The name of a profile must be less than or equal to 10 characters."))
            return
        data = self.get_data(ctx=ctx)
        profiles = await data.get_raw(*self.global_path)
        if profile in profiles:
            await ctx.send(_("This profile already exists."))
            return
        await data.set_raw(*self.global_path, profile, value=self.config._defaults[self.group]["default_profile_settings"]) 

    async def clone_profile(self, ctx: commands.Context, old_profile: str, profile: str):
        if len(profile) > 10:
            await ctx.send(_("The name of a profile must be less than or equal to 10 characters."))
            return
        data = self.get_data(ctx=ctx)
        profiles = await data.get_raw(*self.global_path)
        if profile in profiles:
            await ctx.send(_("This profile already exists."))
            return
        await data.set_raw(*self.global_path, profile, value=await data.get_raw(*self.global_path, old_profile))
        if self.cog.qualified_name == "TicketTool":
            await data.set_raw(*self.global_path, profile, "last_nb", value=0)

    async def remove_profile(self, ctx: commands.Context, profile: str, confirmation: typing.Optional[bool]=False):
        if not confirmation:
            embed: discord.Embed = discord.Embed()
            embed.title = _(
                "Do you really want to remove this profile?"
            )
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
            to_remove = []
            for channel in data:
                if data[channel].get("panel", "main") == profile:
                    to_remove.append(channel)
            for channel in to_remove:
                try:
                    del data[channel]
                except KeyError:
                    pass
            await self.cog.config.guild(ctx.guild).tickets.set(data)

    async def rename_profile(self, ctx: commands.Context, old_profile: str, profile: str):
        if len(profile) > 10:
            await ctx.send(_("The name of a profile must be less than or equal to 10 characters.")
            return
        data = self.get_data(ctx=ctx)
        profiles = await data.get_raw(*self.global_path)
        if profile in profiles:
            await ctx.send(_("A panel with this name already exists.")
            return
        await data.set_raw(*self.global_path, profile, value=await data.get_raw(*self.global_path, old_profile))
        await data.clear_raw(*self.global_path, old_profile)
        if self.cog.qualified_name == "TicketTool":
            data = await self.cog.config.guild(ctx.guild).tickets.all()
            to_edit = []
            for channel in data:
                if data[channel]["panel"] == old_profile:
                    to_edit.append(channel)
            for channel in to_edit:
                try:
                    data[channel]["panel"] = profile
                except KeyError:
                    pass
            await self.cog.config.guild(ctx.guild).tickets.set(data)

    async def list_profiles(self, ctx: commands.Context):
        """List the existing profiles."""
        data = self.get_data(ctx=ctx)
        profiles = await data.get_raw(*self.global_path)
        message = f"---------- Profiles in {self.cog.qualified_name} ----------\n\n"
        message += "\n".join([f"- {profile}" for profile in profiles])
        await Menu(pages=message, box_language_py=True).start(ctx)

    async def show_settings(self, ctx: commands.Context, object: typing.Optional[typing.Union[discord.Guild, discord.Member, discord.abc.Messageable, discord.Role, discord.User]] = None, profile: typing.Optional[str] = None, with_dev: typing.Optional[bool] = False):
        if object is None:
            if self.group == Config.GLOBAL:
                object = None
            elif self.group == Config.GUILD:
                object = ctx.guild
            elif self.group == Config.MEMBER:
                object = ctx.author
            elif self.group == Config.CHANNEL:
                object = ctx.author
            elif self.group == Config.ROLE:
                object = ctx.author.top_role
            elif self.group == Config.USER:
                object = ctx.author
        if not self.use_profiles_system:
            message = f"---------- {self.cog.qualified_name}'s Settings ----------\n```\n\n```py\n"
        else:
            message = f"---------- {self.cog.qualified_name}'s Settings for `{profile}` profile ----------\n```\n\n```py\n"
        try:
            values = await self.get_values(object=object, profile=profile)
        except self.NotExistingPanel:
            await ctx.send("This profile don't exist.")
            return
        if not with_dev:
            raw_table = Table("Key", "Default", "Value", "Converter")
            for value in values:
                raw_table.add_row(value.replace("_", " ").capitalize().replace(" ", ""), repr(values[value]["default"]), repr(values[value]["value"]), str((("|".join(f'"{v}"' if isinstance(v, str) else str(v)for v in self.settings[value]["converter"].__args__)) if self.settings[value]["converter"] is typing.Literal else getattr(self.settings[value]["converter"], "__name__", ""))))
        else:
            raw_table = Table("Key", "Default", "Value", "Converter", "Path")
            for value in values:
                raw_table.add_row(value.replace("_", " ").capitalize().replace(" ", ""), repr(values[value]["default"]), repr(values[value]["value"]), str((("|".join(f'"{v}"' if isinstance(v, str) else str(v)for v in self.settings[value]["converter"].__args__)) if self.settings[value]["converter"] is typing.Literal else getattr(self.settings[value]["converter"], "__name__", ""))), (str([self.group] + self.global_path + self.settings[value]["path"]) if not self.use_profiles_system else str([self.group] + self.global_path + [profile] + self.settings[value]["path"])))
        raw_table_str = no_colour_rich_markup(raw_table, no_box=True)
        message += raw_table_str
        await Menu(pages=message, box_language_py=True).start(ctx)

    async def send_modal(self, ctx: commands.Context, object: typing.Optional[typing.Union[discord.Guild, discord.Member, discord.abc.Messageable, discord.Role, discord.User]] = None, profile: typing.Optional[str] = None, confirmation: typing.Optional[bool] = False):
        if not self.cog.cogsutils.is_dpy2:
            raise RuntimeError()
        if object is None:
            if self.group == Config.GLOBAL:
                object = None
            elif self.group == Config.GUILD:
                object = ctx.guild
            elif self.group == Config.MEMBER:
                object = ctx.author
            elif self.group == Config.CHANNEL:
                object = ctx.author
            elif self.group == Config.ROLE:
                object = ctx.author.top_role
            elif self.group == Config.USER:
                object = ctx.author
        values = await self.get_values(object=object, profile=profile)
        data = self.get_data(object)
        if not self.use_profiles_system:
            config = await data.get_raw(*self.global_path)
        else:
            config = await data.get_raw(*self.global_path, profile)
        one_l = list(self.settings)
        two_l = []
        three_l = {}
        while True:
            lst = one_l[0:5]
            one_l = one_l[5:]
            two_l.append(lst)
            if one_l == []:
                break
        for i, l in enumerate(two_l, start=1):
            three_l[i] = l

        async def on_modal(view: Modal, interaction: discord.Interaction, inputs: typing.List, config: typing.Dict):
            if not interaction.response.is_done():
                await interaction.response.defer()
            for input in inputs:
                custom_id = input.custom_id[21:]
                if input.value == "":
                    assert self.settings[custom_id]["path"]
                    if len(self.settings[custom_id]["path"]) == 1:
                        c = config
                    else:
                        for x in self.settings[custom_id]["path"][:-1]:
                            c = config.get(x, {})
                    c[self.settings[custom_id]["path"][-1]] = values[custom_id]["default"]
                    continue
                if (getattr(input.value, "id", None) or getattr(input.value, "value", None) or input.value) == values[custom_id]["value"]:
                    continue
                try:
                    if self.cog.cogsutils.is_dpu2:
                        value = await discord.ext.commands.converter.run_converters(
                            ctx,
                            converter=self.settings[custom_id]["converter"],
                            argument=str(input.value),
                            param=self.settings[custom_id]["param"],
                        )
                    else:
                        value = await ctx.command.do_conversion(
                            ctx,
                            converter=self.settings[custom_id]["converter"],
                            argument=str(input.value),
                            param=self.settings[custom_id]["param"],
                        )
                except discord.ext.commands.errors.CommandError as e:
                    await ctx.send(
                        f"An error occurred when using the `{input.label}` converter:\n{box(e, lang='py')}"
                    )
                    return None
                if (getattr(value, "id", None) or getattr(value, "value", None) or value) == values[custom_id]["value"]:
                    continue
                assert self.settings[custom_id]["path"]
                if len(self.settings[custom_id]["path"]) == 1:
                    c = config
                else:
                    for x in self.settings[custom_id]["path"][:-1]:
                        c = config.get(x, {})
                c[self.settings[custom_id]["path"][-1]] = getattr(value, "id", None) or getattr(value, "value", None) or value

        async def on_button(view: Buttons, interaction: discord.Interaction, config: typing.Dict, three_l: typing.Dict):
            if not interaction.data["custom_id"].startswith("Settings_ModalConfig_configure"):
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
                        if not self.use_profiles_system:
                            config = await data.set_raw(*self.global_path, value=config)
                        else:
                            config = await data.set_raw(*self.global_path, profile, value=config)
                view.stop()
            elif interaction.data["custom_id"] == "Settings_ModalConfig_view":
                await Menu(pages=str(config), box_language_py=True).start(ctx)
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
                                            f'"{v}"' if isinstance(v, str) else str(v)
                                            for v in self.settings[setting]["converter"].__args__
                                        )
                                    )
                                    if self.settings[setting]["converter"] is typing.Literal
                                    else getattr(self.settings[setting]["converter"], "__name__", "")
                                )
                                + ")"
                            )[:44],
                            "style": self.settings[setting]["style"],
                            "placeholder": str(values[setting]["default"]),
                            "default": (
                                str(values[setting]["value"])
                                if not str(values[setting]["value"]) == str(values[setting]["default"])
                                else None
                            ),
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

        buttons = [{"label": "Cancel", "emoji": "❌", "style": 4, "disabled": False, "custom_id": "Settings_ModalConfig_cancel"}, {"label": "Save", "emoji": "✅", "style": 3, "disabled": False, "custom_id": "Settings_ModalConfig_done"}, {"label": "View", "emoji": "🔍", "style": 1, "disabled": False, "custom_id": "Settings_ModalConfig_view"}]
        for i in three_l:
            buttons.append({"label": f"Configure {i}", "emoji": "⚙️", "disabled": False, "custom_id": f"Settings_ModalConfig_configure_{i}"})
        view_button = Buttons(
            timeout=360,
            buttons=buttons,
            members=[ctx.author.id] + list(ctx.bot.owner_ids),
            function=on_button,
            function_kwargs={"config": config, "three_l": three_l},
            infinity=True,
        )
        message = await ctx.send(
            _(
                "Click on the buttons below to fully set up the cog {cog.qualified_name}."
            ).format(cog=self.cog),
            view=view_button,
        )
        await view_button.wait()
        for i, button in enumerate(buttons):
            buttons[i]["disabled"] = True
        await message.edit(
            view=Buttons(
                timeout=None, buttons=buttons
            )
        )
        return config

    async def get_raw(self, key: str, object: typing.Optional[typing.Union[discord.Guild, discord.Member, discord.abc.Messageable, discord.Role, discord.User]] = None, profile: typing.Optional[str] = None):
        if key not in self.settings:
            raise KeyError(key)
        data = self.get_data(object)
        setting = self.settings[key]
        if not self.use_profiles_system:
            return await data.get_raw(*self.global_path, *setting["path"])
        else:
            try:
                profiles = await data.get_raw(*self.global_path)
            except KeyError:
                profiles = {}
            try:
                profiles[profile]
            except KeyError:
                raise self.NotExistingPanel(profile)
            return await data.get_raw(*self.global_path, profile, *setting["path"])

    async def set_raw(self, key: str, value: typing.Any, object: typing.Optional[typing.Union[discord.Guild, discord.Member, discord.abc.Messageable, discord.Role, discord.User]] = None, profile: typing.Optional[str] = None):
        if key not in self.settings:
            raise KeyError(key)
        data = self.get_data(object)
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

    async def clear_raw(self, key: str, object: typing.Optional[typing.Union[discord.Guild, discord.Member, discord.abc.Messageable, discord.Role, discord.User]] = None, profile: typing.Optional[str] = None):
        if key not in self.settings:
            raise KeyError(key)
        data = self.get_data(object)
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

    def get_data(self, object: typing.Optional[typing.Union[discord.Guild, discord.Member, discord.abc.Messageable, discord.Role, discord.User]] = None, ctx: typing.Optional[commands.Context] = None):
        if object is None and ctx is not None:
            if self.group == Config.GLOBAL:
                object = None
            elif self.group == Config.GUILD:
                object = ctx.guild
            elif self.group == Config.MEMBER:
                object = ctx.author
            elif self.group == Config.CHANNEL:
                object = ctx.author
            elif self.group == Config.ROLE:
                object = ctx.author.top_role
            elif self.group == Config.USER:
                object = ctx.author
        data = {}
        if self.group == Config.GLOBAL:
            data = self.config
        elif self.group == Config.GUILD:
            if isinstance(object, discord.Guild):
                data = self.config.guild(object)
            elif isinstance(object, int):
                data = self.config.guild_from_id(object)
        elif self.group == Config.MEMBER:
            if isinstance(object, discord.Member):
                data = self.config.member(object)
            elif isinstance(object, typing.List) and len(object) == 2:
                data = self.config.member_from_ids(*object)
        elif self.group == Config.CHANNEL:
            if isinstance(object, discord.abc.Messageable):
                data = self.config.channel(object)
            elif isinstance(object, int):
                data = self.config.channel_from_id(object)
        elif self.group == Config.ROLE:
            if isinstance(object, discord.Role):
                data = self.config.role(object).all()
            elif isinstance(object, int):
                data = self.config.role_from_id(object)
        elif self.group == Config.USER:
            if isinstance(object, discord.User):
                data = self.config.user(object)
            elif isinstance(object, int):
                data = self.config.user_from_id(object)
        else:
            return self.config.custom(self.group if object is None else object)
        return data

    async def get_values(self, object: typing.Optional[typing.Union[discord.Guild, discord.Member, discord.abc.Messageable, discord.Role, discord.User]] = None, profile: typing.Optional[str] = None):
        result = {}
        data = self.get_data(object)
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
                    value = await data.get_raw(*self.global_path, profile, *self.settings[setting]["path"])
            except KeyError:
                value = default
            result[setting] = {"default": default, "value": value}
        return result

    class NotExistingPanel(KeyError):
        pass

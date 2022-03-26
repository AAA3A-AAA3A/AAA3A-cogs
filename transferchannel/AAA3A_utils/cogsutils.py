import discord
from redbot.core import commands

import asyncio
import contextlib
import datetime
import inspect
import logging
import math
import os
import platform
import string
import sys
import traceback
import typing
from io import StringIO
from pathlib import Path
from random import choice
from time import monotonic

import pip
import redbot
from redbot import version_info as red_version_info
from redbot.cogs.downloader.converters import InstalledCog
from redbot.cogs.downloader.repo_manager import Repo
from redbot.core._diagnoser import IssueDiagnoser
from redbot.core.bot import Red
from redbot.core.data_manager import basic_config, cog_data_path, config_file, instance_name, storage_type
from redbot.core.utils.chat_formatting import bold, box, error, humanize_list, humanize_timedelta, pagify, text_to_file, warning
from redbot.core.utils.menus import start_adding_reactions
from redbot.core.utils.predicates import MessagePredicate, ReactionPredicate
from rich.console import Console
from rich.table import Table

# Menu

def _(untranslated: str):
    return untranslated

def no_colour_rich_markup(*objects: typing.Any, lang: str = "") -> str:
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
    return box(temp_console.file.getvalue(), lang=lang)  # type: ignore

__all__ = ["CogsUtils", "Loop", "Captcha", "Buttons", "Dropdown", "Modal"]
TimestampFormat = typing.Literal["f", "F", "d", "D", "t", "T", "R"]

class CogsUtils(commands.Cog):
    """Tools for AAA3A-cogs!"""

    def __init__(self, cog: typing.Optional[commands.Cog]=None, bot: typing.Optional[Red]=None):
        if cog is not None:
            if isinstance(cog, str):
                cog = bot.get_cog(cog)
            self.cog: commands.Cog = cog
            self.bot: Red = self.cog.bot
            self.DataPath: Path = cog_data_path(raw_name=self.cog.__class__.__name__.lower())
        elif bot is not None:
            self.cog: commands.Cog = None
            self.bot: Red = bot
        else:
            self.cog: commands.Cog = None
            self.bot: Red = None
        self.__authors__ = ["AAA3A"]
        self.__version__ = 1.0
        self.interactions = {"slash": [], "buttons": [], "dropdowns": [], "added": False, "removed": False}
        if self.cog is not None:
            if hasattr(self.cog, '__authors__'):
                if isinstance(self.cog.__authors__, typing.List):
                    self.__authors__ = self.cog.__authors__
                else:
                    self.__authors__ = [self.cog.__authors__]
            elif hasattr(self.cog, '__author__'):
                if isinstance(self.cog.__author__, typing.List):
                    self.__authors__ = self.cog.__author__
                else:
                    self.__authors__ = [self.cog.__author__]
            if hasattr(self.cog, '__version__'):
                if isinstance(self.cog.__version__, typing.List):
                    self.__version__ = self.cog.__version__
            if hasattr(self.cog, '__func_red__'):
                if not isinstance(self.cog.__func_red__, typing.List):
                    self.cog.__func_red__ = []
            else:
                self.cog.__func_red__ = []
            if hasattr(self.cog, 'interactions'):
                if isinstance(self.cog.interactions, typing.Dict):
                    self.interactions = self.cog.interactions
        self.loops: typing.Dict = {}
        self.repo_name: str = "AAA3A-cogs"
        self.all_cogs: typing.List = [
                                        "AntiNuke",
                                        "AutoTraceback",
                                        "Calculator",
                                        "ClearChannel",
                                        "CmdChannel",
                                        "CtxVar",
                                        "DiscordModals",
                                        "EditFile",
                                        "Ip",
                                        "MemberPrefix",
                                        "ReactToCommand",
                                        "RolesButtons",
                                        "SimpleSanction",
                                        "Sudo",
                                        "TicketTool",
                                        "TransferChannel"
                                    ]
        self.all_cogs_dpy2: typing.List = [
                                        "AntiNuke",
                                        "AutoTraceback",
                                        "Calculator",
                                        "ClearChannel",
                                        "CmdChannel",
                                        "CtxVar",
                                        "DiscordModals",
                                        "EditFile",
                                        "Ip",
                                        "MemberPrefix",
                                        "ReactToCommand",
                                        "RolesButtons",
                                        "SimpleSanction",
                                        "Sudo",
                                        "TicketTool",
                                        "TransferChannel"
                                    ]
        if self.cog is not None:
            if self.cog.__class__.__name__ not in self.all_cogs_dpy2:
                if self.is_dpy2 or redbot.version_info >= redbot.VersionInfo.from_str("3.5.0"):
                    raise RuntimeError(f"{self.cog.__class__.__name__} needs to be updated to run on dpy2/Red 3.5.0. It's best to use `[p]cog update` with no arguments to update all your cogs, which may be using new dpy2-specific methods.")

    @property
    def is_dpy2(self) -> bool:
        """
        Returns True if the current redbot instance is running under dpy2.
        """
        return discord.version_info.major >= 2

    def format_help_for_context(self, ctx):
        """Thanks Simbad!"""
        context = super(type(self.cog), self.cog).format_help_for_context(ctx)
        s = "s" if len(self.__authors__) > 1 else ""
        return f"{context}\n\n**Author{s}**: {humanize_list(self.__authors__)}\n**Version**: {self.__version__}"

    async def red_delete_data_for_user(self, **kwargs):
        """Nothing to delete"""
        return

    async def red_get_data_for_user(self, *args, **kwargs) -> typing.Dict[typing.Any, typing.Any]:
        return {}

    def cog_unload(self):
        self._end()

    async def add_cog(self, bot: Red, cog: commands.Cog):
        """
        Load a cog by checking whether the required function is awaitable or not.
        """
        value = bot.add_cog(cog)
        if inspect.isawaitable(value):
            cog = await value
        else:
            cog = value
        if hasattr(cog, 'initialize'):
            await bot.initialize()
        return cog

    def _setup(self):
        """
        Adding additional functionality to the cog.
        """
        self.cog.cogsutils = self
        self.cog.log = logging.getLogger(f"red.{self.repo_name}.{self.cog.__class__.__name__}")
        if "format_help_for_context" not in self.cog.__func_red__:
            setattr(self.cog, 'format_help_for_context', self.format_help_for_context)
        if "red_delete_data_for_user" not in self.cog.__func_red__:
            setattr(self.cog, 'red_delete_data_for_user', self.red_delete_data_for_user)
        if "red_get_data_for_user" not in self.cog.__func_red__:
            setattr(self.cog, 'red_get_data_for_user', self.red_get_data_for_user)
        if "cog_unload" not in self.cog.__func_red__:
            setattr(self.cog, 'cog_unload', self.cog_unload)
        self.bot.remove_listener(self.on_command_error)
        self.bot.add_listener(self.on_command_error)
        self.bot.remove_command("getallfor")
        self.bot.add_command(getallfor)
        asyncio.create_task(self._await_setup())

    async def _await_setup(self):
        """
        Adds dev environment values, slash commands add Views.
        """
        await self.bot.wait_until_red_ready()
        self.add_dev_env_value()
        if self.is_dpy2:
            if not hasattr(self.bot, "tree"):
                self.bot.tree = discord.app_commands.CommandTree(self.bot)
            if not self.interactions == {}:
                if "added" in self.interactions:
                    if not self.interactions["added"]:
                        if "slash" in self.interactions:
                            for slash in self.interactions["slash"]:
                                try:
                                    self.bot.tree.add_command(slash, guild=None)
                                except Exception as e:
                                    if hasattr(self.cog, 'log'):
                                        self.cog.log.error(f"The slash command `{slash.name}` could not be added correctly.", exc_info=e)
                        if "button" in self.interactions:
                            for button in self.interactions["button"]:
                                try:
                                    self.bot.add_view(button, guild=None)
                                except Exception:
                                    pass
                        self.interactions["removed"] = False
                        self.interactions["added"] = True
                    await self.bot.tree.sync(guild=None)

    def _end(self):
        """
        Removes dev environment values, slash commands add Views.
        """
        self.remove_dev_env_value()
        for loop in self.loops:
            self.loops[loop].end_all()
        if not self.at_least_one_cog_loaded:
            self.bot.remove_listener(self.on_command_error)
            self.bot.remove_command("getallfor")
        asyncio.create_task(self._await_end())

    async def _await_end(self):
        if self.is_dpy2:
            if not self.interactions == {}:
                if "removed" in self.interactions:
                    if not self.interactions["removed"]:
                        if "slash" in self.interactions:
                            for slash in self.interactions["slash"]:
                                try:
                                    self.bot.tree.remove_command(slash, guild=None)
                                except Exception as e:
                                    if hasattr(self.cog, 'log'):
                                        self.cog.log.error(f"The slash command `{slash.name}` could not be removed correctly.", exc_info=e)
                        if "button" in self.interactions:
                            for button in self.interactions["button"]:
                                try:
                                    self.bot.remove_view(button, guild=None)
                                except Exception:
                                    pass
                        self.interactions["added"] = False
                        self.interactions["removed"] = True
            await asyncio.sleep(2)
            await self.bot.tree.sync(guild=None)

    def add_dev_env_value(self):
        """
        If the bot owner is X, then add several values to the development environment, if they don't already exist.
        Even checks the id of the bot owner in the variable of my Sudo cog, if it is installed and loaded.
        """
        sudo_cog = self.bot.get_cog("Sudo")
        if sudo_cog is None:
            owner_ids = self.bot.owner_ids
        else:
            if hasattr(sudo_cog, "all_owner_ids"):
                if len(sudo_cog.all_owner_ids) == 0:
                    owner_ids = self.bot.owner_ids
                else:
                    owner_ids = sudo_cog.all_owner_ids
            else:
                owner_ids = self.bot.owner_ids
        if 829612600059887649 in owner_ids:
            if self.is_dpy2:
                to_add = {
                    self.cog.__class__.__name__: lambda x: self.cog,
                    "CogsUtils": lambda x: CogsUtils,
                    "Loop": lambda x: Loop,
                    "Captcha": lambda x: Captcha,
                    "Buttons": lambda x: Buttons,
                    "Dropdown": lambda x: Dropdown,
                    "Modal": lambda x: Modal,
                    "discord": lambda x: discord,
                    "typing": lambda x: typing,
                    "redbot": lambda x: redbot,
                    "cog": lambda ctx: ctx.bot.get_cog
                }
            else:
                to_add = {
                    self.cog.__class__.__name__: lambda x: self.cog,
                    "CogsUtils": lambda x: CogsUtils,
                    "Loop": lambda x: Loop,
                    "Captcha": lambda x: Captcha,
                    "discord": lambda x: discord,
                    "typing": lambda x: typing,
                    "redbot": lambda x: redbot,
                    "cog": lambda ctx: ctx.bot.get_cog
                }
            for name, value in to_add.items():
                try:
                    self.bot.add_dev_env_value(name, value)
                except RuntimeError:
                    pass
                except Exception as e:
                    self.cog.log.error(f"Error when adding the value `{name}` to the development environment.", exc_info=e)

    def remove_dev_env_value(self):
        """
        If the bot owner is X, then remove several values to the development environment, if they don't already exist.
        Even checks the id of the bot owner in the variable of my Sudo cog, if it is installed and loaded.
        """
        sudo_cog = self.bot.get_cog("Sudo")
        if sudo_cog is None:
            owner_ids = self.bot.owner_ids
        else:
            if hasattr(sudo_cog, "all_owner_ids"):
                owner_ids = sudo_cog.all_owner_ids
            else:
                owner_ids = self.bot.owner_ids
        if 829612600059887649 in owner_ids:
            try:
                self.bot.remove_dev_env_value(self.cog.__class__.__name__)
            except Exception:
                pass

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        """
        Record all exceptions generated by commands by cog and by command in `bot.last_exceptions_cogs`.
        All my cogs will add this listener if it doesn't exist, so I need to record this in a common variable. Also, this may be useful to others.
        """
        try:
            IGNORED_ERRORS = (
                commands.UserInputError,
                commands.DisabledCommand,
                commands.CommandNotFound,
                commands.CheckFailure,
                commands.NoPrivateMessage,
                commands.CommandOnCooldown,
                commands.MaxConcurrencyReached,
                commands.BadArgument,
                commands.BadBoolArgument,
            )
            if ctx.cog is not None:
                cog = ctx.cog.__class__.__name__
            else:
                cog = "None"
            if ctx.command is None:
                return
            if isinstance(error, IGNORED_ERRORS):
                return
            if not hasattr(self.bot, 'last_exceptions_cogs'):
                self.bot.last_exceptions_cogs = {}
            if "global" not in self.bot.last_exceptions_cogs:
                self.bot.last_exceptions_cogs["global"] = []
            if error in self.bot.last_exceptions_cogs["global"]:
                return
            self.bot.last_exceptions_cogs["global"].append(error)
            if isinstance(error, commands.CommandError):
                traceback_error = "".join(traceback.format_exception(type(error), error, error.__traceback__)).replace(os.environ["USERPROFILE"], "{USERPROFILE}")
            else:
                traceback_error = f"Traceback (most recent call last): {error}"
            if "USERPROFILE" in os.environ:
                traceback_error = traceback_error.replace(os.environ["USERPROFILE"], "{USERPROFILE}")
            if "HOME" in os.environ:
                traceback_error = traceback_error.replace(os.environ["HOME"], "{HOME}")
            if cog not in self.bot.last_exceptions_cogs:
                self.bot.last_exceptions_cogs[cog] = {}
            if ctx.command.qualified_name not in self.bot.last_exceptions_cogs[cog]:
                self.bot.last_exceptions_cogs[cog][ctx.command.qualified_name] = []
            self.bot.last_exceptions_cogs[cog][ctx.command.qualified_name].append(traceback_error)
        except Exception:
            pass

    _ReactableEmoji = typing.Union[str, discord.Emoji]

    async def ConfirmationAsk(
            self,
            ctx: commands.Context,
            text: typing.Optional[str]=None,
            embed: typing.Optional[discord.Embed]=None,
            file: typing.Optional[discord.File]=None,
            timeout: typing.Optional[int]=60,
            timeout_message: typing.Optional[str]=_("Timed out, please try again").format(**locals()),
            way: typing.Optional[typing.Literal["buttons", "dropdown", "reactions", "message"]] = "buttons",
            message: typing.Optional[discord.Message]=None,
            put_reactions: typing.Optional[bool]=True,
            delete_message: typing.Optional[bool]=True,
            reactions: typing.Optional[typing.Iterable[_ReactableEmoji]]=["✅", "❌"],
            check_owner: typing.Optional[bool]=True,
            members_authored: typing.Optional[typing.Iterable[discord.Member]]=[]):
        """
        Allow confirmation to be requested from the user, in the form of buttons/dropdown/reactions/message, with many additional options.
        """
        if not self.is_dpy2 and way == "buttons" or not self.is_dpy2 and way == "dropdown":
            way = "reactions"
        if message is None:
            if not text and not embed and not file:
                if way == "buttons":
                    text = _("To confirm the current action, please use the buttons below this message.").format(**locals())
                if way == "dropdown":
                    text = _("To confirm the current action, please use the dropdown below this message.").format(**locals())
                if way == "reactions":
                    text = _("To confirm the current action, please use the reactions below this message.").format(**locals())
                if way == "message":
                    text = _("To confirm the current action, please send yes/no in this channel.").format(**locals())
            if not way == "buttons" and not way == "dropdown":
                message = await ctx.send(content=text, embed=embed, file=file)
        if way == "reactions":
            if put_reactions:
                try:
                    start_adding_reactions(message, reactions)
                except discord.HTTPException:
                    way = "message"
        async def delete_message(message: discord.Message):
            try:
                return await message.delete()
            except discord.HTTPException:
                pass
        if way == "buttons":
            view = Buttons(timeout=timeout, buttons=[{"style": 3, "label": "Yes", "emoji": reactions[0], "custom_id": "ConfirmationAsk_Yes"}, {"style": 4, "label": "No", "emoji": reactions[1], "custom_id": "ConfirmationAsk_No"}], members=[ctx.author.id] + list(ctx.bot.owner_ids)if check_owner else [] + [x.id for x in members_authored])
            message = await ctx.send(content=text, embed=embed, file=file, view=view)
            try:
                interaction, function_result = await view.wait_result()
                if str(interaction.data["custom_id"]) == "ConfirmationAsk_Yes":
                    if delete_message:
                        await delete_message(message)
                    return True
                elif str(interaction.data["custom_id"]) == "ConfirmationAsk_No":
                    if delete_message:
                        await delete_message(message)
                    return False
            except TimeoutError:
                if delete_message:
                    await delete_message(message)
                if timeout_message is not None:
                    await ctx.send(timeout_message)
                return None
        if way == "dropdown":
            view = Dropdown(timeout=timeout, options=[{"label": "Yes", "emoji": reactions[0], "value": "ConfirmationAsk_Yes"}, {"label": "No", "emoji": reactions[1], "value": "ConfirmationAsk_No"}], members=[ctx.author.id] + list(ctx.bot.owner_ids)if check_owner else [] + [x.id for x in members_authored])
            message = await ctx.send(content=text, embed=embed, file=file, view=view)
            try:
                interaction, values, function_result = await view.wait_result()
                if str(values[0]) == "ConfirmationAsk_Yes":
                    if delete_message:
                        await delete_message(message)
                    return True
                elif str(values[0]) == "ConfirmationAsk_No":
                    if delete_message:
                        await delete_message(message)
                    return False
            except TimeoutError:
                if delete_message:
                    await delete_message(message)
                if timeout_message is not None:
                    await ctx.send(timeout_message)
                return None
        if way == "reactions":
            end_reaction = False
            def check(reaction, user):
                if check_owner:
                    return user.id == ctx.author.id or user.id in ctx.bot.owner_ids or user in [x.id for x in members_authored] and str(reaction.emoji) in reactions
                else:
                    return user.id == ctx.author.id or user.id in [x.id for x in members_authored] and str(reaction.emoji) in reactions
                # This makes sure nobody except the command sender can interact with the "menu"
            while True:
                try:
                    reaction, abc_author = await ctx.bot.wait_for("reaction_add", timeout=timeout, check=check)
                    # waiting for a reaction to be added - times out after x seconds
                    if str(reaction.emoji) == reactions[0]:
                        end_reaction = True
                        if delete_message:
                            await delete_message(message)
                        return True
                    elif str(reaction.emoji) == reactions[1]:
                        end_reaction = True
                        if delete_message:
                            await delete_message(message)
                        return False
                    else:
                        try:
                            await message.remove_reaction(reaction, abc_author)
                        except discord.HTTPException:
                            pass
                except asyncio.TimeoutError:
                    if not end_reaction:
                        if delete_message:
                            await delete_message(message)
                        if timeout_message is not None:
                            await ctx.send(timeout_message)
                        return None
        if way == "message":
            def check(msg):
                if check_owner:
                    return msg.author.id == ctx.author.id or msg.author.id in ctx.bot.owner_ids or msg.author.id in [x.id for x in members_authored] and msg.channel is ctx.channel
                else:
                    return msg.author.id == ctx.author.id or msg.author.id in [x.id for x in members_authored] and msg.channel is ctx.channel
                # This makes sure nobody except the command sender can interact with the "menu"
            try:
                end_reaction = False
                check = MessagePredicate.yes_or_no(ctx)
                msg = await ctx.bot.wait_for("message", timeout=timeout, check=check)
                # waiting for a a message to be sended - times out after x seconds
                if check.result:
                    end_reaction = True
                    if delete_message:
                        await delete_message(message)
                    await delete_message(msg)
                    return True
                else:
                    end_reaction = True
                    if delete_message:
                        await delete_message(message)
                    await delete_message(msg)
                    return False
            except asyncio.TimeoutError:
                if not end_reaction:
                    if delete_message:
                        await delete_message(message)
                    if timeout_message is not None:
                        await ctx.send(timeout_message)
                    return None

    def datetime_to_timestamp(self, dt: datetime.datetime, format: TimestampFormat = "f") -> str:
        """
        Generate a Discord timestamp from a datetime object.
        <t:TIMESTAMP:FORMAT>
        Parameters
        ----------
        dt : datetime.datetime
            The datetime object to use
        format : TimestampFormat, by default `f`
            The format to pass to Discord.
            - `f` short date time | `18 June 2021 02:50`
            - `F` long date time  | `Friday, 18 June 2021 02:50`
            - `d` short date      | `18/06/2021`
            - `D` long date       | `18 June 2021`
            - `t` short time      | `02:50`
            - `T` long time       | `02:50:15`
            - `R` relative time   | `8 days ago`
        Returns
        -------
        str
            Formatted timestamp
        Thanks to vexutils from Vexed01 in GitHub! (https://github.com/Vexed01/Vex-Cogs/blob/master/timechannel/vexutils/chat.py)
        """
        t = str(int(dt.timestamp()))
        return f"<t:{t}:{format}>"

    async def get_hook(self, channel: discord.TextChannel):
        """
        Create a discord.Webhook object. It tries to retrieve an existing webhook created by the bot or to create it itself.
        """
        try:
            for webhook in await channel.webhooks():
                if webhook.user.id == self.bot.user.id:
                    hook = webhook
                    break
            else:
                hook = await channel.create_webhook(
                    name="red_bot_hook_" + str(channel.id)
                )
        except discord.errors.NotFound:  # Probably user deleted the hook
            hook = await channel.create_webhook(name="red_bot_hook_" + str(channel.id))
        return hook

    def check_permissions_for(self, channel: typing.Union[discord.TextChannel, discord.VoiceChannel, discord.DMChannel], user: discord.User, check: typing.Union[typing.List, typing.Dict]):
        """
        Check all permissions specified as an argument.
        """
        if getattr(channel, "guild", None) is None:
            return True
        permissions = channel.permissions_for(user)
        if isinstance(check, typing.List):
            new_check = {}
            for p in check:
                new_check[p] = True
            check = new_check
        for p in check:
            if getattr(permissions, f'{p}', None):
                if check[p]:
                    if not getattr(permissions, f"{p}"):
                        return False
                else:
                    if getattr(permissions, f"{p}"):
                        return False
        return True

    def create_loop(self, function, name: typing.Optional[str]=None, days: typing.Optional[int]=0, hours: typing.Optional[int]=0, minutes: typing.Optional[int]=0, seconds: typing.Optional[int]=0, function_args: typing.Optional[typing.Dict]={}, limit_count: typing.Optional[int]=None, limit_date: typing.Optional[datetime.datetime]=None, limit_exception: typing.Optional[int]=None):
        """
        Create a loop like Loop, but with default values and loop object recording functionality.
        """
        if name is None:
            name = f"{self.cog.__class__.__name__}"
        if datetime.timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds).total_seconds() == 0:
            seconds = 900  # 15 minutes
        loop = Loop(cogsutils=self, name=name, function=function, days=days, hours=hours, minutes=minutes, seconds=seconds, function_args=function_args, limit_count=limit_count, limit_date=limit_date, limit_exception=limit_exception)
        if f"{loop.name}" in self.loops:
            self.loops[f"{loop.name}"].stop_all()
        self.loops[f"{loop.name}"] = loop
        return loop

    async def captcha(self, member: discord.Member, channel: discord.TextChannel, limit: typing.Optional[int]=3, timeout: typing.Optional[int]=60, why: typing.Optional[str]=""):
        """
        Create a Captcha challenge like Captcha, but with default values.
        """
        return await Captcha(cogsutils=self, member=member, channel=channel, limit=limit, timeout=timeout, why=why).realize_challenge()

    def get_all_repo_cogs_objects(self):
        """
        Get a dictionary containing the objects or None of all my cogs.
        """
        cogs = {}
        for cog in self.all_cogs:
            object = self.bot.get_cog(f"{cog}")
            if object is not None:
                cogs[f"{cog}"] = object if hasattr(object, 'cogsutils') else None
            else:
                cogs[f"{cog}"] = None
        return cogs

    def at_least_one_cog_loaded(self):
        """
        Return True if at least one cog of all my cogs is loaded.
        """
        at_least_one_cog_loaded = False
        for object in self.get_all_repo_cogs_objects().values:
            if object is not None:
                at_least_one_cog_loaded = True
                break
        return at_least_one_cog_loaded

    def add_all_dev_env_values(self):
        """
        Add values to the development environment for all my loaded cogs. Not really useful anymore, now that my cogs use AAA3A_utils.
        """
        cogs = self.get_all_repo_cogs_objects()
        for cog in cogs:
            if cogs[cog] is not None:
                try:
                    CogsUtils(cog=cogs[cog]).add_dev_env_value()
                except Exception:
                    pass

    def class_instance_to_dict(self, instance):
        """
        Convert a class instance into a dictionary, while using ids for all sub-attributes.
        """
        original_dict = instance.__dict__
        new_dict = self.to_id(original_dict)
        return new_dict

    def to_id(self, original_dict: typing.Dict):
        """
        Return a dict with ids for all sub-attributes
        """
        new_dict = {}
        for e in original_dict:
            if isinstance(original_dict[e], typing.Dict):
                new_dict[e] = self.to_id(original_dict[e])
            elif hasattr(original_dict[e], 'id'):
                new_dict[e] = int(original_dict[e].id)
            elif isinstance(original_dict[e], datetime.datetime):
                new_dict[e] = float(datetime.datetime.timestamp(original_dict[e]))
            else:
                new_dict[e] = original_dict[e]
        return new_dict

    def generate_key(self, number: typing.Optional[int]=15, existing_keys: typing.Optional[typing.List]=[], strings_used: typing.Optional[typing.List]={"ascii_lowercase": True, "ascii_uppercase": False, "digits": True, "punctuation": False, "others": []}):
        """
        Generate a secret key, with the choice of characters, the number of characters and a list of existing keys.
        """
        strings = []
        if "ascii_lowercase" in strings_used:
            if strings_used["ascii_lowercase"]:
                strings += string.ascii_lowercase
        if "ascii_uppercase" in strings_used:
            if strings_used["ascii_uppercase"]:
                strings += string.ascii_uppercase
        if "digits" in strings_used:
            if strings_used["digits"]:
                strings += string.digits
        if "punctuation" in strings_used:
            if strings_used["punctuation"]:
                strings += string.punctuation
        if "others" in strings_used:
            if isinstance(strings_used["others"], typing.List):
                strings += strings_used["others"]
        while True:
            # This probably won't turn into an endless loop
            key = "".join(choice(strings) for i in range(number))
            if key not in existing_keys:
                return key

    def await_function(self, function, function_args: typing.Optional[typing.Dict]={}):
        """
        Allow to use an asynchronous function, from a non-asynchronous function.
        """
        task = asyncio.create_task(self.do_await_function(function=function, function_args=function_args))
        return task

    async def do_await_function(self, function, function_args: typing.Optional[typing.Dict]={}):
        try:
            await function(**function_args)
        except Exception as e:
            if hasattr(self.cogsutils.cog, 'log'):
                self.cog.log.error(f"An error occurred with the {function.__name__} function.", exc_info=e)

    async def delete_message(self, message: discord.Message):
        """
        Delete a message, ignoring any exceptions.
        Easier than putting these 3 lines at each message deletion for each cog.
        """
        try:
            await message.delete()
        except discord.HTTPException:
            pass

    async def check_in_listener(self, output, allowed_by_whitelist_blacklist: typing.Optional[bool]=True):
        """
        Check all parameters for the output of any listener.
        Thanks to Jack! (https://discord.com/channels/133049272517001216/160386989819035648/825373605000511518)
        """
        if isinstance(output, discord.Message):
            # check whether the message was sent in a guild
            if output.guild is None:
                raise discord.ext.commands.BadArgument()
            # check whether the message author isn't a bot
            if output.author is None:
                raise discord.ext.commands.BadArgument()
            if output.author.bot:
                raise discord.ext.commands.BadArgument()
            # check whether the bot can send message in the given channel
            if not self.check_permissions_for(channel=output.channel, user=output.guild.me, check=["send_messages"]):
                raise discord.ext.commands.BadArgument()
            # check whether the cog isn't disabled
            if self.cog is not None:
                if await self.bot.cog_disabled_in_guild(self.cog, output.guild):
                    raise discord.ext.commands.BadArgument()
            # check whether the channel isn't on the ignore list
            if not await self.bot.ignored_channel_or_guild(output):
                raise discord.ext.commands.BadArgument()
            # check whether the message author isn't on allowlist/blocklist
            if allowed_by_whitelist_blacklist:
                if not await self.bot.allowed_by_whitelist_blacklist(output.author):
                    raise discord.ext.commands.BadArgument()
        if isinstance(output, discord.RawReactionActionEvent):
            # check whether the message was sent in a guild
            output.guild = self.bot.get_guild(output.guild_id)
            if output.guild is None:
                raise discord.ext.commands.BadArgument()
            # check whether the message author isn't a bot
            output.author = output.guild.get_member(output.user_id)
            if output.author is None:
                raise discord.ext.commands.BadArgument()
            if output.author.bot:
                raise discord.ext.commands.BadArgument()
            # check whether the bot can send message in the given channel
            output.channel = output.guild.get_channel(output.channel_id)
            if not self.check_permissions_for(channel=output.channel, user=output.guild.me, check=["send_messages"]):
                raise discord.ext.commands.BadArgument()
            # check whether the cog isn't disabled
            if self.cog is not None:
                if await self.bot.cog_disabled_in_guild(self.cog, output.guild):
                    raise discord.ext.commands.BadArgument()
            # check whether the channel isn't on the ignore list
            if not await self.bot.ignored_channel_or_guild(output):
                raise discord.ext.commands.BadArgument()
            # check whether the message author isn't on allowlist/blocklist
            if allowed_by_whitelist_blacklist:
                if not await self.bot.allowed_by_whitelist_blacklist(output.author):
                    raise discord.ext.commands.BadArgument()
        return

    async def autodestruction(self):
        """
        Cog self-destruct.
        Will of course never be used, just a test.
        """
        downloader = self.bot.get_cog("Downloader")
        if downloader is not None:
            poss_installed_path = (await downloader.cog_install_path()) / self.cog.__class__.__name__.lower()
            if poss_installed_path.exists():
                with contextlib.suppress(commands.ExtensionNotLoaded):
                    self.bot.unload_extension(self.cog.__class__.__name__.lower())
                    await self.bot.remove_loaded_package(self.cog.__class__.__name__.lower())
                await downloader._delete_cog(poss_installed_path)
            await downloader._remove_from_installed([discord.utils.get(await downloader.installed_cogs(), name=self.cog.__class__.__name__.lower())])
        else:
            raise self.DownloaderNotLoaded(_("The cog downloader is not loaded.").format(**locals()))

    class DownloaderNotLoaded(Exception):
        pass

class Loop():
    """
    Create a loop, with many features.
    Thanks to Vexed01 on GitHub! (https://github.com/Vexed01/Vex-Cogs/blob/master/timechannel/loop.py)
    """
    def __init__(self, cogsutils: CogsUtils, name: str, function, days: typing.Optional[int]=0, hours: typing.Optional[int]=0, minutes: typing.Optional[int]=0, seconds: typing.Optional[int]=0, function_args: typing.Optional[typing.Dict]={}, limit_count: typing.Optional[int]=None, limit_date: typing.Optional[datetime.datetime]=None, limit_exception: typing.Optional[int]=None) -> None:
        self.cogsutils: CogsUtils = cogsutils

        self.name: str = name
        self.function = function
        self.function_args = function_args
        self.interval: float = datetime.timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds).total_seconds()
        self.limit_count: int = limit_count
        self.limit_date: datetime.datetime = limit_date
        self.limit_exception: int = limit_exception
        self.loop = self.cogsutils.bot.loop.create_task(self.loop())
        self.stop_manually: bool = False
        self.stop: bool = False

        self.expected_interval = datetime.timedelta(seconds=self.interval)
        self.iter_count: int = 0
        self.iter_exception: int = 0
        self.currently_running: bool = False  # whether the loop is running or sleeping
        self.last_result = None
        self.last_exc: str = "No exception has occurred yet."
        self.last_exc_raw: typing.Optional[BaseException] = None
        self.last_iter: typing.Optional[datetime.datetime] = None
        self.next_iter: typing.Optional[datetime.datetime] = None

    async def start(self):
        if self.cogsutils.is_dpy2:
            async with self.cogsutils.bot:
                self.cogsutils.bot.loop.create_task(self.loop())
        else:
            self.cogsutils.bot.loop.create_task(self.loop())

    async def wait_until_iter(self) -> None:
        now = datetime.datetime.utcnow()
        time = now.timestamp()
        time = math.ceil(time / self.interval) * self.interval
        next_iter = datetime.datetime.fromtimestamp(time) - now
        seconds_to_sleep = (next_iter).total_seconds()
        if not self.interval <= 60:
            if hasattr(self.cogsutils.cog, 'log'):
                self.cogsutils.cog.log.debug(f"Sleeping for {seconds_to_sleep} seconds until next iter...")
        await asyncio.sleep(seconds_to_sleep)

    async def loop(self) -> None:
        await self.cogsutils.bot.wait_until_red_ready()
        await asyncio.sleep(1)
        if hasattr(self.cogsutils.cog, 'log'):
            self.cogsutils.cog.log.debug(f"{self.name} loop has started.")
        if float(self.interval) % float(3600) == 0:
            try:
                start = monotonic()
                self.iter_start()
                self.last_result = await self.function(**self.function_args)
                self.iter_finish()
                end = monotonic()
                total = round(end - start, 1)
                if not self.interval <= 60:
                    if hasattr(self.cogsutils.cog, 'log'):
                        self.cogsutils.cog.log.debug(f"{self.name} initial loop finished in {total}s.")
            except Exception as e:
                if hasattr(self.cogsutils.cog, 'log'):
                    self.cogsutils.cog.log.exception(f"Something went wrong in the {self.name} loop.", exc_info=e)
                self.iter_error(e)
                self.iter_exception += 1
            # both iter_finish and iter_error set next_iter as not None
            assert self.next_iter is not None
            self.next_iter = self.next_iter.replace(
                minute=0
            )  # ensure further iterations are on the hour
            if await self.maybe_stop():
                return
            await self.sleep_until_next()
        while True:
            try:
                start = monotonic()
                self.iter_start()
                self.last_result = await self.function(**self.function_args)
                self.iter_finish()
                end = monotonic()
                total = round(end - start, 1)
                if not self.interval <= 60:
                    if hasattr(self.cogsutils.cog, 'log'):
                        self.cogsutils.cog.log.debug(f"{self.name} iteration finished in {total}s.")
            except Exception as e:
                if hasattr(self.cogsutils.cog, 'log'):
                    self.cogsutils.cog.log.exception(f"Something went wrong in the {self.name} loop.", exc_info=e)
                self.iter_error(e)
            if await self.maybe_stop():
                return
            if float(self.interval) % float(3600) == 0:
                await self.sleep_until_next()
            else:
                if not self.interval == 0:
                    await self.wait_until_iter()

    async def maybe_stop(self):
        if self.stop_manually:
            self.stop_all()
        if self.limit_count is not None:
            if self.iter_count >= self.limit_count:
                self.stop_all()
        if self.limit_date is not None:
            if datetime.datetime.timestamp(datetime.datetime.now()) >= datetime.datetime.timestamp(self.limit_date):
                self.stop_all()
        if self.limit_exception:
            if self.iter_exception >= self.limit_exception:
                self.stop_all()
        if self.stop:
            return True
        return False

    def stop_all(self):
        self.stop = True
        self.next_iter = None
        self.loop.cancel()
        if f"{self.name}" in self.cogsutils.loops:
            if self.cogsutils.loops[f"{self.name}"] == self:
                del self.cogsutils.loops[f"{self.name}"]
        return self

    def __repr__(self) -> str:
        return (
            f"<friendly_name={self.name} iter_count={self.iter_count} "
            f"currently_running={self.currently_running} last_iter={self.last_iter} "
            f"next_iter={self.next_iter} integrity={self.integrity}>"
        )

    @property
    def integrity(self) -> bool:
        """
        If the loop is running on time (whether or not next expected iteration is in the future)
        """
        if self.next_iter is None:  # not started yet
            return False
        return self.next_iter > datetime.datetime.utcnow()

    @property
    def until_next(self) -> float:
        """
        Positive float with the seconds until the next iteration, based off the last
        iteration and the interval.
        If the expected time of the next iteration is in the past, this will return `0.0`
        """
        if self.next_iter is None:  # not started yet
            return 0.0

        raw_until_next = (self.next_iter - datetime.datetime.utcnow()).total_seconds()
        if raw_until_next > self.expected_interval.total_seconds():  # should never happen
            return self.expected_interval.total_seconds()
        elif raw_until_next > 0.0:
            return raw_until_next
        else:
            return 0.0

    async def sleep_until_next(self) -> None:
        """Sleep until the next iteration. Basically an "all-in-one" version of `until_next`."""
        await asyncio.sleep(self.until_next)

    def iter_start(self) -> None:
        """Register an iteration as starting."""
        self.iter_count += 1
        self.currently_running = True
        self.last_iter = datetime.datetime.utcnow()
        self.next_iter = datetime.datetime.utcnow() + self.expected_interval
        # this isn't accurate, it will be "corrected" when finishing is called

    def iter_finish(self) -> None:
        """Register an iteration as finished successfully."""
        self.currently_running = False
        # now this is accurate. imo its better to have something than nothing

    def iter_error(self, error: BaseException) -> None:
        """Register an iteration's error."""
        self.currently_running = False
        self.last_exc_raw = error
        self.last_exc = "".join(
            traceback.format_exception(type(error), error, error.__traceback__)
        )

    def get_debug_embed(self) -> discord.Embed:
        """Get an embed with infomation on this loop."""
        table = Table("Key", "Value")

        table.add_row("expected_interval", str(self.expected_interval))
        table.add_row("iter_count", str(self.iter_count))
        table.add_row("currently_running", str(self.currently_running))
        table.add_row("last_iterstr", str(self.last_iter) or "Loop not started")
        table.add_row("next_iterstr", str(self.next_iter) or "Loop not started")

        raw_table_str = no_colour_rich_markup(table)

        now = datetime.datetime.utcnow()

        if self.next_iter and self.last_iter:
            table = Table("Key", "Value")
            table.add_row("Seconds until next", str((self.next_iter - now).total_seconds()))
            table.add_row("Seconds since last", str((now - self.last_iter).total_seconds()))
            processed_table_str = no_colour_rich_markup(table)
        else:
            processed_table_str = "Loop hasn't started yet."

        emoji = "✅" if self.integrity else "❌"
        embed = discord.Embed(title=f"{self.name}: `{emoji}`")
        embed.add_field(name="Raw data", value=raw_table_str, inline=False)
        embed.add_field(
            name="Processed data",
            value=processed_table_str,
            inline=False,
        )
        exc = self.last_exc
        if len(exc) > 1024:
            exc = list(pagify(exc, page_length=1024))[0] + "\n..."
        embed.add_field(name="Exception", value=box(exc), inline=False)

        return embed

class Captcha():
    """
    Captcha for an member in a text channel.
    Thanks to Kreusada for this code! (https://github.com/Kreusada/Kreusada-Cogs/blob/master/captcha/)
    """

    def __init__(self, cogsutils: CogsUtils, member: discord.Member, channel: discord.TextChannel, limit: typing.Optional[int]=3, timeout: typing.Optional[int]=60, why: typing.Optional[str]=""):
        self.cogsutils: CogsUtils = cogsutils

        self.member: discord.Member = member
        self.guild: discord.Guild = member.guild
        self.channel: discord.TextChannel = channel
        self.why: str = why

        self.limit: int = limit
        self.timeout: int = timeout

        self.message: discord.Message = None
        self.code: str = None
        self.running: bool = False
        self.tasks: list = []
        self.trynum: int = 0
        self.escape_char = "\u200B"

    async def realize_challenge(self) -> None:
        is_ok = None
        timeout = False
        try:
            while is_ok is not True:
                if self.trynum > self.limit:
                    break
                try:
                    self.code = self.generate_code()
                    await self.send_message()
                    this = await self.try_challenging()
                except TimeoutError:
                    timeout = True
                    break
                except self.AskedForReload:
                    self.trynum += 1
                    continue
                except TypeError:
                    continue
                except self.LeftGuildError:
                    leave_guild = True
                    break
                if this is False:
                    self.trynum += 1
                    is_ok = False
                else:
                    is_ok = True
            if self.message is not None:
                try:
                    await self.message.delete()
                except discord.HTTPException:
                    pass
            failed = self.trynum > self.limit
        except self.MissingPermissions as e:
            raise self.MissingPermissions(e)
        except Exception as e:
            if hasattr(self.cogsutils.cog, 'log'):
                self.cogsutils.cog.log.error("An unsupported error occurred during the captcha.", exc_info=e)
            raise self.OtherException(e)
        finally:
            if timeout:
                raise TimeoutError
            if failed:
                return False
            if leave_guild:
                raise self.LeftGuildError("User has left guild.")
            return True

    async def try_challenging(self) -> bool:
        """Do challenging in one function!
        """
        self.running = True
        try:
            received = await self.wait_for_action()
            if received is None:
                raise self.LeftGuildError("User has left guild.")
            if hasattr(received, "content"):
                # It's a message!
                try:
                    await received.delete()
                except discord.HTTPException:
                    pass
                error_message = ""
                try:
                    state = await self.verify(received.content)
                except self.SameCodeError:
                    error_message += error(bold(_("Code invalid. Do not copy and paste.").format(**locals())))
                    state = False
                else:
                    if not state:
                        error_message += warning("Code invalid.")
                if error_message:
                    await self.channel.send(error_message, delete_after=3)
                return state
            else:
                raise self.AskedForReload("User want to reload Captcha.")
        except TimeoutError:
            raise TimeoutError
        finally:
            self.running = False

    def generate_code(self, put_fake_espace: typing.Optional[bool] = True):
        code = self.cogsutils.generate_key(number=8, existing_keys=[], strings_used={"ascii_lowercase": False, "ascii_uppercase": True, "digits": True, "punctuation": False})
        if put_fake_espace:
            code = self.escape_char.join(list(code))
        return code

    def get_embed(self) -> discord.Embed:
        """
        Get the embed containing the captcha code.
        """
        embed_dict = {
                        "embeds": [
                            {
                                "title": _("Captcha").format(**locals()) + _(" for {self.why}").format(**locals()) if not self.why == "" else "",
                                "description": _("Please return me the following code:\n{box(str(self.code))}\nDo not copy and paste.").format(**locals()),
                                "author": {
                                    "name": f"{self.member.display_name}",
                                    "icon_url": self.member.display_avatar if self.is_dpy2 else self.member.avatar_url
                                },
                                "footer": {
                                    "text": _("Tries: {self.trynum} / Limit: {self.limit}").format(**locals())
                                }
                            }
                        ]
                    }
        embed = self.cogsutils.get_embed(embed_dict)["embed"]
        return embed

    async def send_message(self) -> None:
        """
        Send a message with new code.
        """
        if self.message is not None:
            try:
                await self.message.delete()
            except discord.HTTPException:
                pass
        embed = self.get_embed()
        try:
            self.message = await self.channel.send(
                            embed=embed,
                            delete_after=900,  # Delete after 15 minutes.
                        )
        except discord.HTTPException:
            raise self.MissingPermissions("Cannot send message in verification channel.")
        try:
            await self.message.add_reaction("🔁")
        except discord.HTTPException:
            raise self.MissingPermissions("Cannot react in verification channel.")

    async def verify(self, code_input: str) -> bool:
        """Verify a code."""
        if self.escape_char in code_input:
            raise self.SameCodeError
        if code_input.lower() == self.code.replace(self.escape_char, "").lower():
            return True
        else:
            return False

    async def wait_for_action(self) -> typing.Union[discord.Reaction, discord.Message, None]:
        """Wait for an action from the user.
        It will return an object of discord.Message or discord.Reaction depending what the user
        did.
        """
        self.cancel_tasks()  # Just in case...
        self.tasks = self._give_me_tasks()
        done, pending = await asyncio.wait(
            self.tasks,
            timeout=self.timeout,
            return_when=asyncio.FIRST_COMPLETED,
        )
        self.cancel_tasks()
        if len(done) == 0:
            raise TimeoutError("User didn't answer.")
        try:  # An error is raised if we return the result and when the task got cancelled.
            return done.pop().result()
        except asyncio.CancelledError:
            return None

    def cancel_tasks(self) -> None:
        """Cancel the ongoing tasks."""
        for task in self.tasks:
            task: asyncio.Task
            if not task.done():
                task.cancel()

    def _give_me_tasks(self) -> typing.List:
        def leave_check(u):
            return u.id == self.member.id
        return [
            asyncio.create_task(
                self.cogsutils.bot.wait_for(
                    "reaction_add",
                    check=ReactionPredicate.with_emojis(
                        "🔁", message=self.message, user=self.member
                    )
                )
            ),
            asyncio.create_task(
                self.cogsutils.bot.wait_for(
                    "message",
                    check=MessagePredicate.same_context(
                        channel=self.channel,
                        user=self.member,
                    )
                )
            ),
            asyncio.create_task(self.cogsutils.bot.wait_for("user_remove", check=leave_check))
        ]

    class MissingPermissions(Exception):
        pass

    class AskedForReload(Exception):
        pass

    class SameCodeError(Exception):
        pass

    class LeftGuildError(Exception):
        pass

    class OtherException(Exception):
        pass

if CogsUtils().is_dpy2:

    class Buttons(discord.ui.View):
        """Create Buttons easily."""

        def __init__(self, timeout: typing.Optional[float]=180, buttons: typing.Optional[typing.List]=[], members: typing.Optional[typing.List]=None, check: typing.Optional[typing.Any]=None, function: typing.Optional[typing.Any]=None, function_args: typing.Optional[typing.Dict]={}, infinity: typing.Optional[bool]=False):
            """style: ButtonStyle, label: Optional[str], disabled: bool, custom_id: Optional[str], url: Optional[str], emoji: Optional[Union[str, Emoji, PartialEmoji]], row: Optional[int]"""
            self.buttons_dict_instance = {"timeout": timeout, "buttons": [b.copy() for b in buttons], "members": members, "check": check, "function": function, "function_args": function_args, "infinity": infinity}
            super().__init__(timeout=timeout)
            self.infinity = infinity
            self.interaction_result = None
            self.function_result = None
            self.members = members
            self.check = check
            self.function = function
            self.function_args = function_args
            self.clear_items()
            self.buttons = []
            self.buttons_dict = []
            self.done = asyncio.Event()
            for button_dict in buttons:
                if "style" not in button_dict:
                    button_dict["style"] = int(discord.ButtonStyle(2))
                if "label" not in button_dict:
                    button_dict["label"] = "Test"
                button = discord.ui.Button(**button_dict)
                self.add_item(button)
                self.buttons.append(button)
                self.buttons_dict.append(button_dict)

        def to_dict_cogsutils(self, for_Config: typing.Optional[bool]=False):
            buttons_dict_instance = self.buttons_dict_instance
            if for_Config:
                buttons_dict_instance["check"] = None
                buttons_dict_instance["function"] = None
            return buttons_dict_instance

        @classmethod
        def from_dict_cogsutils(cls, buttons_dict_instance: typing.Dict):
            return cls(**buttons_dict_instance)

        async def interaction_check(self, interaction: discord.Interaction):
            if self.check is not None:
                if not self.check(interaction):
                    await interaction.response.send_message("You are not allowed to use this interaction.", ephemeral=True)
                    return True
            if self.members is not None:
                if interaction.user.id not in self.members:
                    await interaction.response.send_message("You are not allowed to use this interaction.", ephemeral=True)
                    return True
            if self.function is not None:
                self.function_result = await self.function(self, interaction, **self.function_args)
            self.interaction_result = interaction
            self.done.set()
            if not self.infinity:
                self.stop()
            return True

        async def on_timeout(self):
            self.done.set()
            self.stop()

        async def wait_result(self):
            self.done = asyncio.Event()
            await self.done.wait()
            interaction, function_result = self.get_result()
            if interaction is None:
                raise TimeoutError
            return interaction, function_result

        def get_result(self):
            return self.interaction_result, self.function_result

    class Dropdown(discord.ui.View):
        """Create Dropdown easily."""

        def __init__(self, timeout: typing.Optional[float]=180, placeholder: typing.Optional[str]="Choose a option.", min_values: typing.Optional[int]=1, max_values: typing.Optional[int]=1, *, options: typing.Optional[typing.List]=[], members: typing.Optional[typing.List]=None, check: typing.Optional[typing.Any]=None, function: typing.Optional[typing.Any]=None, function_args: typing.Optional[typing.Dict]={}, infinity: typing.Optional[bool]=False):
            """label: str, value: str, description: Optional[str], emoji: Optional[Union[str, Emoji, PartialEmoji]], default: bool"""
            self.dropdown_dict_instance = {"timeout": timeout, "placeholder": placeholder, "min_values": min_values, "max_values": max_values, "options": [o.copy() for o in options], "members": members, "check": check, "function": function, "function_args": function_args, "infinity": infinity}
            super().__init__(timeout=timeout)
            self.infinity = infinity
            self.dropdown = self.Dropdown(placeholder=placeholder, min_values=min_values, max_values=max_values, options=options, members=members, check=check, function=function, function_args=function_args, infinity=self.infinity)
            self.add_item(self.dropdown)

        def to_dict_cogsutils(self, for_Config: typing.Optional[bool]=False):
            dropdown_dict_instance = self.dropdown_dict_instance
            if for_Config:
                dropdown_dict_instance["check"] = None
                dropdown_dict_instance["function"] = None
            return dropdown_dict_instance

        @classmethod
        def from_dict_cogsutils(cls, dropdown_dict_instance: typing.Dict):
            return cls(**dropdown_dict_instance)

        async def on_timeout(self):
            self.dropdown.done.set()
            self.stop()

        async def wait_result(self):
            self.done = asyncio.Event()
            await self.dropdown.done.wait()
            interaction, values, function_result = self.get_result()
            if interaction is None:
                raise TimeoutError
            return interaction, values, function_result

        def get_result(self):
            return self.dropdown.interaction_result, self.dropdown.values_result, self.dropdown.function_result

        class Dropdown(discord.ui.Select):

            def __init__(self, placeholder: typing.Optional[str]="Choose a option.", min_values: typing.Optional[int]=1, max_values: typing.Optional[int]=1, *, options: typing.Optional[typing.List]=[], members: typing.Optional[typing.List]=None, check: typing.Optional[typing.Any]=None, function: typing.Optional[typing.Any]=None, function_args: typing.Optional[typing.Dict]={}, infinity: typing.Optional[bool]=False):
                self.infinity = infinity
                self.interaction_result = None
                self.values_result = None
                self.function_result = None
                self.members = members
                self.check = check
                self.function = function
                self.function_args = function_args
                self._options = []
                self.options_dict = []
                self.done = asyncio.Event()
                for option_dict in options:
                    if "label" not in option_dict:
                        option_dict["label"] = "Test"
                    option = discord.SelectOption(**option_dict)
                    self._options.append(option)
                    self.options_dict.append(option_dict)
                super().__init__(placeholder=placeholder, min_values=min_values, max_values=max_values, options=self._options)

            async def callback(self, interaction: discord.Interaction):
                if self.check is not None:
                    if not self.check(interaction):
                        await interaction.response.send_message("You are not allowed to use this interaction.", ephemeral=True)
                        return True
                if self.members is not None:
                    if interaction.user.id not in self.members:
                        await interaction.response.send_message("You are not allowed to use this interaction.", ephemeral=True)
                        return True
                if self.function is not None:
                    self.function_result = await self.function(self, interaction, self.values, **self.function_args)
                self.interaction_result = interaction
                self.values_result = self.values
                self.done.set()
                if not self.infinity:
                    self.view.stop()

    class Modal(discord.ui.Modal):
        """Create Modal easily."""

        def __init__(self, title: typing.Optional[str]="Form", timeout: typing.Optional[float]=None, inputs: typing.Optional[typing.List]=[], function: typing.Optional[typing.Any]=None, function_args: typing.Optional[typing.Dict]={}):
            """name: str, label: str, style: TextStyle, custom_id: str, placeholder: Optional[str], default: Optional[str], required: bool, min_length: Optional[int], max_length: Optional[int], row: Optional[int]"""
            self.modal_dict_instance = {"title": title, "timeout": timeout, "inputs": [i.copy() for i in inputs], "function": function, "function_args": function_args}
            super().__init__(title=title, timeout=timeout)
            self.title = title
            self.interaction_result = None
            self.values_result = None
            self.function_result = None
            self.function = function
            self.function_args = function_args
            self.inputs = []
            self.inputs_dict = []
            self.done = asyncio.Event()
            for input_dict in inputs:
                if "style" in input_dict:
                    if isinstance(input_dict["style"], int):
                        input_dict["style"] = discord.ui.text_input.TextStyle(input_dict["style"])
                input = discord.ui.text_input.TextInput(**input_dict)
                self.add_item(input)
                self.inputs.append(input)
                self.inputs_dict.append(input_dict)

        def to_dict_cogsutils(self, for_Config: typing.Optional[bool]=False):
            modal_dict_instance = self.modal_dict_instance
            if for_Config:
                modal_dict_instance["function"] = None
            return modal_dict_instance

        @classmethod
        def from_dict_cogsutils(cls, modal_dict_instance: typing.Dict):
            return cls(**modal_dict_instance)

        async def on_submit(self, interaction: discord.Interaction):
            self.interaction_result = interaction
            self.values_result = self.inputs
            if self.function is not None:
                self.function_result = await self.function(self, self.interaction_result, self.values_result, **self.function_args)
            self.done.set()
            self.stop()

        async def on_timeout(self):
            self.done.set()
            self.stop()

        async def wait_result(self):
            self.done = asyncio.Event()
            await self.done.wait()
            interaction, values, function_result = self.get_result()
            if interaction is None:
                raise TimeoutError
            return interaction, values, function_result

        def get_result(self):
            return self.interaction_result, self.values_result, self.function_result

@commands.is_owner()
@commands.command(hidden=True)
async def getallfor(ctx: commands.Context, all: typing.Optional[typing.Literal["all", "ALL"]]=None, repo: typing.Optional[typing.Union[Repo, typing.Literal["AAA3A", "aaa3a"]]]=None, check_updates: typing.Optional[bool]=False, cog: typing.Optional[InstalledCog]=None, command: typing.Optional[str]=None):
    """Get all the necessary information to get support on a bot/repo/cog/command.
    With a html file.
    """
    if all is not None:
        repo = None
        cog = None
        command = None
        check_updates = False
    if repo is not None:
        repos = [repo]
    else:
        repos = [None]
    if cog is not None:
        cogs = [cog]
    else:
        cogs = [None]
    if command is not None:
        commands = [command]
    else:
        commands = [None]
    if command is not None:
        object_command = ctx.bot.get_command(commands[0])
        if object_command is None:
            await ctx.send(_("The command `{command}` does not exist.").format(**locals()))
            return
        commands = [object_command]
    downloader = ctx.bot.get_cog("Downloader")
    if downloader is None:
        if CogsUtils(bot=ctx.bot).ConfirmationAsk(ctx, _("The cog downloader is not loaded. I can't continue. Do you want me to do it?").format(**locals())):
            await ctx.invoke(ctx.bot.get_command("load"), "downloader")
            downloader = ctx.bot.get_cog("Downloader")
        else:
            return
    installed_cogs = await downloader.config.installed_cogs()
    loaded_cogs = [c.lower() for c in ctx.bot.cogs]
    if repo is not None:
        rp = repos[0]
        if not isinstance(rp, Repo) and not "AAA3A".lower() in rp.lower():
            await ctx.send(_("Repo by the name `{rp}` does not exist.").format(**locals()))
            return
        if not isinstance(repo, Repo):
            found = False
            for r in await downloader.config.installed_cogs():
                if "AAA3A".lower() in str(r).lower():
                    repos = [downloader._repo_manager.get_repo(str(r))]
                    found = True
                    break
            if not found:
                await ctx.send(_("Repo by the name `{rp}` does not exist.").format(**locals()))
                return
        if check_updates:
            cogs_to_check, failed = await downloader._get_cogs_to_check(repos={repos[0]})
            cogs_to_update, libs_to_update = await downloader._available_updates(cogs_to_check)
            cogs_to_update, filter_message = downloader._filter_incorrect_cogs(cogs_to_update)
            to_update_cogs = [c.name.lower() for c in cogs_to_update]

    if all is not None:
        repos = []
        for r in installed_cogs:
            repos.append(downloader._repo_manager.get_repo(str(r)))
        cogs = []
        for r in installed_cogs:
            for c in installed_cogs[r]:
                cogs.append(await InstalledCog.convert(ctx, str(c)))
        commands = []
        for c in ctx.bot.all_commands:
            cmd = ctx.bot.get_command(str(c))
            if cmd.cog is not None:
                commands.append(cmd)
        repo = True
        cog = True
        command = True

    IS_WINDOWS = os.name == "nt"
    IS_MAC = sys.platform == "darwin"
    IS_LINUX = sys.platform == "linux"
    if IS_LINUX:
        import distro  # pylint: disable=import-error
    python_executable = sys.executable
    python_version = ".".join(map(str, sys.version_info[:3]))
    pyver = f"{python_version} ({platform.architecture()[0]})"
    pipver = pip.__version__
    redver = red_version_info
    dpy_version = discord.__version__
    if IS_WINDOWS:
        os_info = platform.uname()
        osver = f"{os_info.system} {os_info.release} (version {os_info.version})"
    elif IS_MAC:
        os_info = platform.mac_ver()
        osver = f"Mac OSX {os_info[0]} {os_info[2]}"
    elif IS_LINUX:
        osver = f"{distro.name()} {distro.version()}".strip()
    else:
        osver = "Could not parse OS, report this on Github."
    driver = storage_type()
    data_path_original = Path(basic_config["DATA_PATH"])
    if "USERPROFILE" in os.environ:
        data_path = Path(str(data_path_original).replace(os.environ["USERPROFILE"], "{USERPROFILE}"))
        _config_file = Path(str(config_file).replace(os.environ["USERPROFILE"], "{USERPROFILE}"))
        python_executable = Path(str(python_executable).replace(os.environ["USERPROFILE"], "{USERPROFILE}"))
    if "HOME" in os.environ:
        data_path = Path(str(data_path_original).replace(os.environ["HOME"], "{HOME}"))
        _config_file = Path(str(config_file).replace(os.environ["HOME"], "{HOME}"))
        python_executable = Path(str(python_executable).replace(os.environ["HOME"], "{HOME}"))
    disabled_intents = (
        ", ".join(
            intent_name.replace("_", " ").title()
            for intent_name, enabled in ctx.bot.intents
            if not enabled
        )
        or "None"
    )
    async def can_run(command):
        try:
            await command.can_run(ctx, check_all_parents=True, change_permission_state=False)
        except Exception:
            return False
        else:
            return True
    def get_aliases(command, original):
        if alias := list(command.aliases):
            if original in alias:
                alias.remove(original)
                alias.append(command.name)
            return alias
    def get_perms(command):
        final_perms = ""
        def neat_format(x):
            return " ".join(i.capitalize() for i in x.replace("_", " ").split())
        user_perms = []
        if perms := getattr(command.requires, "user_perms"):
            user_perms.extend(neat_format(i) for i, j in perms if j)
        if perms := command.requires.privilege_level:
            if perms.name != "NONE":
                user_perms.append(neat_format(perms.name))
        if user_perms:
            final_perms += "User Permission(s): " + ", ".join(user_perms) + "\n"
        if perms := getattr(command.requires, "bot_perms"):
            if perms_list := ", ".join(neat_format(i) for i, j in perms if j):
                final_perms += "Bot Permission(s): " + perms_list
        return final_perms
    def get_cooldowns(command):
        cooldowns = []
        if s := command._buckets._cooldown:
            txt = f"{s.rate} time{'s' if s.rate>1 else ''} in {humanize_timedelta(seconds=s.per)}"
            try:
                txt += f" per {s.type.name.capitalize()}"
            # This is to avoid custom bucketype erroring out stuff (eg:licenseinfo)
            except AttributeError:
                pass
            cooldowns.append(txt)
        if s := command._max_concurrency:
            cooldowns.append(f"Max concurrent uses: {s.number} per {s.per.name.capitalize()}")
        return cooldowns
    async def get_diagnose(ctx, command):
        issue_diagnoser = IssueDiagnoser(ctx.bot, ctx, ctx.channel, ctx.author, command)
        await issue_diagnoser._prepare()
        diagnose_result = []
        result = await issue_diagnoser._check_until_fail(
            "",
            (
                issue_diagnoser._check_global_call_once_checks_issues,
                issue_diagnoser._check_disabled_command_issues,
                issue_diagnoser._check_can_run_issues,
            ),
        )
        if result.success:
            diagnose_result.append(_("All checks passed and no issues were detected."))
        else:
            diagnose_result.append(_("The bot has been able to identify the issue."))
        details = issue_diagnoser._get_details_from_check_result(result)
        if details:
            diagnose_result.append(bold(_("Detected issue: ")) + details)
        if result.resolution:
            diagnose_result.append(bold(_("Solution: ")) + result.resolution)
        diagnose_result.extend(issue_diagnoser._get_message_from_check_result(result))
        return diagnose_result

    use_emojis = False
    check_emoji = "✅" if use_emojis else True
    cross_emoji = "❌" if use_emojis else False
    os_table = Table("Key", "Value", title="Host machine informations")
    os_table.add_row("OS version", str(osver))
    os_table.add_row("Python executable", str(python_executable))
    os_table.add_row("Python version", str(pyver))
    os_table.add_row("Pip version", str(pipver))
    raw_os_table_str = no_colour_rich_markup(os_table)
    red_table = Table("Key", "Value", title="Red instance informations")
    red_table.add_row("Red version", str(redver))
    red_table.add_row("Discord.py version", str(dpy_version))
    red_table.add_row("Instance name", str(instance_name))
    red_table.add_row("Storage type", str(driver))
    red_table.add_row("Disabled intents", str(disabled_intents))
    red_table.add_row("Data path", str(data_path))
    red_table.add_row("Metadata file", str(_config_file))
    red_table.add_row("Global prefixe(s)", str(await ctx.bot.get_valid_prefixes()))
    raw_red_table_str = no_colour_rich_markup(red_table)
    if repo is not None:
        raw_cogs_table_str = []
        for repo in repos:
            if not check_updates:
                cogs_table = Table("Name", "Commit", "Loaded", "Pinned", title=f"Cogs installed for {repo.name}")
            else:
                cogs_table = Table("Name", "Commit", "Loaded", "Pinned", "To update", title=f"Cogs installed for {repo.name}")
            for _cog in installed_cogs[repo.name]:
                _cog = await InstalledCog.convert(ctx, _cog)
                if not check_updates:
                    cogs_table.add_row(str(_cog.name), str(_cog.commit), str(check_emoji if _cog.name in loaded_cogs else cross_emoji), str(check_emoji if _cog.pinned else cross_emoji))
                else:
                    cogs_table.add_row(str(_cog.name), str(_cog.commit), str(check_emoji if _cog.name in loaded_cogs else cross_emoji), str(check_emoji if _cog.pinned else cross_emoji), str(check_emoji if _cog.name in to_update_cogs else cross_emoji))
            raw_cogs_table_str.append(no_colour_rich_markup(cogs_table))
    else:
        raw_cogs_table_str = None
    if cog is not None:
        raw_cog_table_str = []
        for cog in cogs:
            cog_table = Table("Key", "Value", title=f"Cog {cog.name}")
            cog_table.add_row("Name", str(cog.name))
            cog_table.add_row("Repo name", str(cog.repo_name))
            cog_table.add_row("Hidden", str(check_emoji if cog.hidden else cross_emoji))
            cog_table.add_row("Disabled", str(check_emoji if cog.disabled else cross_emoji))
            cog_table.add_row("Required cogs", str([r for r in cog.required_cogs]))
            cog_table.add_row("Requirements", str([r for r in cog.requirements]))
            cog_table.add_row("Short", str(cog.short))
            cog_table.add_row("Min bot version", str(cog.min_bot_version))
            cog_table.add_row("Max bot version", str(cog.max_bot_version))
            cog_table.add_row("Min python version", str(cog.min_python_version))
            cog_table.add_row("Author", str([a for a in cog.author]))
            cog_table.add_row("Commit", str(cog.commit))
            raw_cog_table_str.append(no_colour_rich_markup(cog_table))
    else:
        raw_cog_table_str = None
    if command is not None:
        raw_command_table_str = []
        for command in commands:
            command_table = Table("Key", "Value", title=f"Command {command.qualified_name}")
            command_table.add_row("Qualified name", str(command.qualified_name))
            command_table.add_row("Cog name", str(command.cog_name))
            command_table.add_row("Short description", str(command.short_doc))
            command_table.add_row("Syntax", str(f"{ctx.clean_prefix}{command.qualified_name} {command.signature}"))
            command_table.add_row("Hidden", str(command.hidden))
            command_table.add_row("Parents", str(command.full_parent_name if not command.full_parent_name == "" else None))
            command_table.add_row("Can see", str(await command.can_see(ctx)))
            command_table.add_row("Can run", str(await can_run(command)))
            command_table.add_row("Params", str(command.clean_params))
            command_table.add_row("Aliases", str(get_aliases(command, command.qualified_name)))
            command_table.add_row("Requires", str(get_perms(command)))
            command_table.add_row("Cooldowns", str(get_cooldowns(command)))
            command_table.add_row("Is on cooldown", str(command.is_on_cooldown(ctx)))
            if ctx.guild is not None:
                diagnose_result = await get_diagnose(ctx, command)
                c = 0
                for x in diagnose_result:
                    c += 1
                    if c == 1:
                        command_table.add_row("Issue Diagnose", str(x))
                    else:
                        command_table.add_row("", str(x).replace("✅", "").replace("❌", ""))
            raw_command_table_str.append(no_colour_rich_markup(command_table))
            cog = command.cog.__class__.__name__ if command.cog is not None else "None"
            if hasattr(ctx.bot, 'last_exceptions_cogs') and cog in ctx.bot.last_exceptions_cogs and command.qualified_name in ctx.bot.last_exceptions_cogs[cog]:
                raw_error_table = []
                error_table = Table("Last error recorded for this command")
                error_table.add_row(str(ctx.bot.last_exceptions_cogs[cog][command.qualified_name][len(ctx.bot.last_exceptions_cogs[cog][command.qualified_name]) - 1]))
                raw_error_table.append(no_colour_rich_markup(error_table))
            else:
                raw_error_table = None
    else:
        raw_command_table_str = None
        raw_error_table = None

    response = [raw_os_table_str, raw_red_table_str]
    for x in [raw_cogs_table_str, raw_cog_table_str, raw_command_table_str, raw_error_table]:
        if x is not None:
            for y in x:
                response.append(y)
    to_html = to_html_getallfor.replace("{AVATAR_URL}", str(ctx.bot.user.display_avatar) if CogsUtils().is_dpy2 else str(ctx.bot.user.avatar_url)).replace("{BOT_NAME}", str(ctx.bot.user.name)).replace("{REPO_NAME}", str(getattr(repos[0], "name", None) if all is None else "All")).replace("{COG_NAME}", str(getattr(cogs[0], "name", None) if all is None else "All")).replace("{COMMAND_NAME}", str(getattr(commands[0], "qualified_name", None) if all is None else "All"))
    message_html = message_html_getallfor
    end_html = end_html_getallfor
    count_page = 0
    for page in response:
        if page is not None:
            count_page += 1
            if count_page == 1:
                to_html += message_html.replace("{MESSAGE_CONTENT}", str(page).replace("```", "").replace("<", "&lt;").replace("\n", "<br>")).replace("{TIMESTAMP}", str(ctx.message.created_at.strftime("%b %d, %Y %I:%M %p")))
            else:
                to_html += message_html.replace('    <div class="chatlog__messages">', '            </div>            <div class="chatlog__message ">').replace("{MESSAGE_CONTENT}", str(page).replace("```", "").replace("<", "&lt;").replace("\n", "<br>")).replace('<span class="chatlog__timestamp">{TIMESTAMP}</span>            ', "")
            if all is None:
                for p in pagify(page):
                    p = p.replace("```", "")
                    p = box(p)
                    await ctx.send(p)
    to_html += end_html
    if CogsUtils().check_permissions_for(channel=ctx.channel, user=ctx.me, check=["send_attachments"]):
        await ctx.send(file=text_to_file(text=to_html, filename="diagnostic.html"))

to_html_getallfor = """
<!--
Thanks to @mahtoid for this transcript! It was retrieved from : https://github.com/mahtoid/DiscordChatExporterPy. Then all unnecessary elements were removed and the header was modified.
-->

<!DOCTYPE html>
<html lang="en">

<head>
    <title>Diagnostic</title>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width" />

    <style>
        @font-face {
            font-family: Whitney;
            src: url(https://cdn.jsdelivr.net/gh/mahtoid/DiscordUtils@master/whitney-300.woff);
            font-weight: 300;
        }

        @font-face {
            font-family: Whitney;
            src: url(https://cdn.jsdelivr.net/gh/mahtoid/DiscordUtils@master/whitney-400.woff);
            font-weight: 400;
        }

        @font-face {
            font-family: Whitney;
            src: url(https://cdn.jsdelivr.net/gh/mahtoid/DiscordUtils@master/whitney-500.woff);
            font-weight: 500;
        }

        @font-face {
            font-family: Whitney;
            src: url(https://cdn.jsdelivr.net/gh/mahtoid/DiscordUtils@master/whitney-600.woff);
            font-weight: 600;
        }

        @font-face {
            font-family: Whitney;
            src: url(https://cdn.jsdelivr.net/gh/mahtoid/DiscordUtils@master/whitney-700.woff);
            font-weight: 700;
        }

        body {
            font-family: "Whitney", "Helvetica Neue", Helvetica, Arial, sans-serif;
            font-size: 17px;
        }

        a {
            text-decoration: none;
        }

        .markdown {
            max-width: 100%;
            line-height: 1.3;
            overflow-wrap: break-word;
        }

        .preserve-whitespace {
            white-space: pre-wrap;
        }

        .pre {
            font-family: "Consolas", "Courier New", Courier, monospace;
        }

        .pre--multiline {
            margin-top: 0.25em;
            padding: 0.5em;
            border: 2px solid;
            border-radius: 5px;
        }

        .pre--inline {
            padding: 2px;
            border-radius: 3px;
            font-size: 0.85em;
        }

        .emoji {
            width: 1.25em;
            height: 1.25em;
            margin: 0 0.06em;
            vertical-align: -0.4em;
        }

        .emoji--small {
            width: 1em;
            height: 1em;
        }

        .emoji--large {
            width: 2.8em;
            height: 2.8em;
        }

        /* Chatlog */

        .chatlog {
            max-width: 100%;
        }

        .chatlog__message-group {
            display: grid;
            margin: 0 0.6em;
            padding: 0.9em 0;
            border-top: 1px solid;
            grid-template-columns: auto 1fr;
        }

        .chatlog__timestamp {
            margin-left: 0.3em;
            font-size: 0.75em;
        }

        /* General */

        body {
            background-color: #36393e;
            color: #dcddde;
        }

        a {
            color: #0096cf;
        }

        .pre {
            background-color: #2f3136 !important;
        }

        .pre--multiline {
            border-color: #282b30 !important;
            color: #b9bbbe !important;
        }

        /* Chatlog */

        .chatlog__message-group {
            border-color: rgba(255, 255, 255, 0.1);
        }

        .chatlog__timestamp {
            color: rgba(255, 255, 255, 0.2);
        }

        /* === INFO === */

        .info {
            display: flex;
            max-width: 100%;
            margin: 0 5px 10px 5px;
        }

        .info__bot-icon-container {
            flex: 0;
        }

        .info__bot-icon {
            max-width: 95px;
            max-height: 95px;
        }

        .info__metadata {
            flex: 1;
            margin-left: 10px;

    </style>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/9.15.6/styles/solarized-dark.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/9.15.6/highlight.min.js"></script>
    <script>
        <!--  Code Block Markdown (```lang```) -->
        document.addEventListener('DOMContentLoaded', () => {
            document.querySelectorAll('.pre--multiline').forEach((block) => {
                hljs.highlightBlock(block);
            });
        });
    </script>
</head>
<body>

<div class="info">
<div class="info__bot-icon-container">
    <img class="info__bot-icon" src="{AVATAR_URL}" />
</div>
<div class="info__metadata">
    <div class="info__report-name">Diagnostic</div>

    <div class="info__report-infos">Bot name: {BOT_NAME}</div>
    <div class="info__report-infos">Repo name: {REPO_NAME}</div>
    <div class="info__report-infos">Cog name: {COG_NAME}</div>
    <div class="info__report-infos">Command name: {COMMAND_NAME}</div>
</div>
</div>

<div class="chatlog">
<div class="chatlog__message-group">"""
message_html_getallfor = """    <div class="chatlog__messages">
    <span class="chatlog__timestamp">{TIMESTAMP}</span>            <div class="chatlog__message ">
            <div class="chatlog__content">
<div class="markdown">
    <span class="preserve-whitespace"><div class="pre pre--multiline nohighlight">{MESSAGE_CONTENT}</div></span>

</div>
</div>"""
end_html_getallfor = """

</div>
</div>

</body>
</html>"""
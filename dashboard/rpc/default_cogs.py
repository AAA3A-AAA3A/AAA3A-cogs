from AAA3A_utils import CogsUtils  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.bot import Red  # isort:skip
from redbot.core.i18n import Translator  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

from redbot.cogs.customcom.customcom import ArgParseError

from .utils import rpc_check

_: Translator = Translator("Dashboard", __file__)


class DashboardRPC_DefaultCogs:
    def __init__(self, cog: commands.Cog) -> None:
        self.bot: Red = cog.bot
        self.cog: commands.Cog = cog

        self.bot.register_rpc_handler(self.get_aliases)
        self.bot.register_rpc_handler(self.set_aliases)
        self.bot.register_rpc_handler(self.get_custom_commands)
        self.bot.register_rpc_handler(self.set_custom_commands)

    def unload(self) -> None:
        self.bot.unregister_rpc_handler(self.get_aliases)
        self.bot.unregister_rpc_handler(self.set_aliases)
        self.bot.unregister_rpc_handler(self.get_custom_commands)
        self.bot.unregister_rpc_handler(self.set_custom_commands)

    @rpc_check()
    async def get_aliases(self, user_id: int, guild_id: typing.Optional[int]):
        if guild_id is not None:
            guild = self.bot.get_guild(guild_id)
            if guild is None:
                return {"status": 1}
            member = guild.get_member(user_id)
            if user_id not in self.bot.owner_ids and (
                member is None
                or not (await self.bot.is_mod(member) or member.guild_permissions.manage_guild)
            ):
                return {"status": 1}
        else:
            guild = None
            if user_id not in self.bot.owner_ids:
                return {"status": 1}
        Alias = self.bot.get_cog("Alias")
        if Alias is None:
            return {"status": 2}
        if guild is not None:
            aliases = await Alias._aliases.get_guild_aliases(guild)
        else:
            aliases = await Alias._aliases.get_global_aliases()
        return {
            "status": 0,
            "aliases": {
                alias.name: alias.command
                for alias in sorted(aliases, key=lambda alias: alias.name)
            },
        }

    @rpc_check()
    async def set_aliases(
        self, user_id: int, guild_id: typing.Optional[int], aliases: typing.Dict[str, str]
    ):
        if guild_id is not None:
            guild = self.bot.get_guild(guild_id)
            if guild is None:
                return {"status": 1}
            member = guild.get_member(user_id)
            if user_id not in self.bot.owner_ids and (
                member is None
                or not (await self.bot.is_mod(member) or member.guild_permissions.manage_guild)
            ):
                return {"status": 1}
        else:
            guild, member = None, None
            if user_id not in self.bot.owner_ids:
                return {"status": 1}
        Alias = self.bot.get_cog("Alias")
        if Alias is None:
            return {"status": 2}

        if guild is not None:
            existing_aliases = await Alias._aliases.get_guild_aliases(guild)
        else:
            existing_aliases = await Alias._aliases.get_global_aliases()
        ctx = await CogsUtils.invoke_command(
            bot=self.bot,
            author=member or self.bot.get_user(user_id),
            channel=discord.Object(id=0) if guild is None else guild.text_channels[0],
            command="alias",
            invoke=False,
        )
        existing_aliases = {alias.name: alias for alias in existing_aliases}
        errors = []
        for alias, command in aliases.items():
            if alias not in existing_aliases:
                if Alias.is_command(alias):
                    errors.append(
                        _(
                            "You attempted to create a new alias with the name {name}, but that name is already a command on this bot."
                        ).format(name=alias)
                    )
                    continue
                if self.bot.get_command(command.split(maxsplit=1)[0]) is None:
                    errors.append(
                        _(
                            "You attempted to create a new alias with the name {name}, but the command {command} does not exist."
                        ).format(name=alias, command=command)
                    )
                    continue
                await Alias._aliases.add_alias(ctx, alias, command, global_=guild is None)
            elif command != existing_aliases[alias]:
                await Alias._aliases.edit_alias(ctx, alias, command, global_=guild is None)
        for alias in existing_aliases:
            if alias not in aliases:
                await Alias._aliases.delete_alias(ctx, alias, global_=guild is None)
        if errors:
            return {"status": 1, "errors": errors}
        return {"status": 0}

    @rpc_check()
    async def get_custom_commands(self, user_id: int, guild_id: int):
        guild = self.bot.get_guild(guild_id)
        if guild is None:
            return {"status": 1}
        member = guild.get_member(user_id)
        if user_id not in self.bot.owner_ids and (
            member is None
            or not (await self.bot.is_mod(member) or member.guild_permissions.administrator)
        ):
            return {"status": 1}
        CustomCommands = self.bot.get_cog("CustomCommands")
        if CustomCommands is None:
            return {"status": 2}
        custom_commands = (
            await CustomCommands.commandobj.get_commands(CustomCommands.config.guild(guild))
        ).values()
        return {
            "status": 0,
            "custom_commands": {
                custom_command["command"]: custom_command["response"]
                for custom_command in sorted(
                    custom_commands, key=lambda custom_command: custom_command["command"]
                )
            },
        }

    @rpc_check()
    async def set_custom_commands(
        self, user_id: int, guild_id: int, custom_commands: typing.Dict[str, str]
    ):
        guild = self.bot.get_guild(guild_id)
        if guild is None:
            return {"status": 1}
        member = guild.get_member(user_id)
        if user_id not in self.bot.owner_ids and (
            member is None
            or not (await self.bot.is_mod(member) or member.guild_permissions.administrator)
        ):
            return {"status": 1}
        CustomCommands = self.bot.get_cog("CustomCommands")
        if CustomCommands is None:
            return {"status": 2}
        ctx = await CogsUtils.invoke_command(
            bot=self.bot,
            author=member,
            channel=guild.text_channels[0],
            command="customcom",
            invoke=False,
        )
        existing_custom_commands = await CustomCommands.commandobj.get_commands(
            CustomCommands.config.guild(guild)
        )
        errors = []
        for command, responses in custom_commands.items():
            if command not in existing_custom_commands:
                try:
                    await CustomCommands.commandobj.create(ctx, command, response=responses)
                except ArgParseError as e:
                    errors.append(_("`{command}`: ").format(command=command) + e.args[0])
            elif responses != existing_custom_commands[command]["response"]:
                await CustomCommands.commandobj.edit(
                    ctx, command, response=responses, ask_for=False
                )
        for command in existing_custom_commands:
            if command not in custom_commands:
                await CustomCommands.commandobj.delete(ctx, command)
        if errors:
            return {"status": 1, "errors": errors}
        return {"status": 0}

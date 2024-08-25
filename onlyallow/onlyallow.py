from AAA3A_utils import Cog, Menu  # isort:skip
from redbot.core import commands, Config  # isort:skip
from redbot.core.bot import Red  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

from redbot.core.utils.chat_formatting import humanize_list

# Credits:
# General repo credits.

_: Translator = Translator("OnlyAllow", __file__)

class GuildConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> discord.Guild:
        return await commands.GuildConverter().convert(ctx, argument)


@cog_i18n(_)
class OnlyAllow(Cog):
    """Only allow users to execute specific commands or commands from specific cogs, on specific servers! If nothing is set in a server, all cogs/commands are permitted."""

    def __init__(self, bot: Red) -> None:
        super().__init__(bot=bot)

        self.config: Config = Config.get_conf(
            self,
            identifier=205192943327321000143939875896557571750,
            force_registration=True,
        )
        self.config.register_guild(
            allowed_cogs=[],
            allowed_commands=[],
        )

        self.cache: typing.Dict[int, typing.Dict[typing.Literal["allowed_cogs", "allowed_commands"], typing.List[str]]] = {}

    async def cog_load(self) -> None:
        await super().cog_load()
        for guild_id, data in (await self.config.all_guilds()).items():
            if data["allowed_cogs"] or data["allowed_commands"]:
                self.cache[guild_id] = data
        self.bot.add_check(self.bot_check)

    async def cog_unload(self) -> None:
        self.bot.remove_check(self.bot_check)
        await super().cog_unload()

    async def bot_check(self, ctx: commands.Context) -> bool:
        if not await self.check_command(ctx):
            raise commands.CheckFailure(
                _("Only specific cogs and commands are allowed in this server. Ask to a bot owner to add the cog(s) or the command(s) you want to use.")
            )
        return True

    async def check_command(self, ctx: commands.Context, command: typing.Optional[commands.Command] = None) -> bool:
        if command is None:
            command = ctx.command
            if isinstance(command, commands.Group):
                view = ctx.view
                previous = view.index
                view.skip_ws()
                trigger = view.get_word()
                invoked_subcommand = command.all_commands.get(trigger, None)
                view.index = previous
                if invoked_subcommand is not None or not command.invoke_without_command:
                    return True
        return (
            ctx.author.id in ctx.bot.owner_ids
            or ctx.guild is None
            or (data := self.cache.get(ctx.guild.id)) is None
            or (
                command is None
                or command.cog is None  # This condition can be removed, without any issues.
                or isinstance(command, commands.commands._AlwaysAvailableCommand)
                or command.qualified_name == "help"
                or (command.cog is not None and command.cog.qualified_name in ("Core", self.qualified_name))
            )
            or (
                (
                    command.cog is not None
                    and command.cog.qualified_name in data["allowed_cogs"]
                ) or any(
                    command.qualified_name.split(" ")[:len(allowed_command.split(" "))] == allowed_command.split(" ")
                    for allowed_command in data["allowed_commands"]
                )
            )
        )
        

    @commands.guild_only()
    @commands.is_owner()
    @commands.hybrid_group()
    async def onlyallow(self, ctx: commands.Context) -> None:
        """Only allow users to execute specific commands or commands from specific cogs, on specific servers!

        If nothing is set in a server, all cogs/commands are permitted.
        """
        pass

    @onlyallow.command()
    async def addcog(
        self,
        ctx: commands.Context,
        guild: typing.Optional[GuildConverter],
        *,
        cog: commands.converter.CogConverter,
    ) -> None:
        """Add a cog to the allowed cogs list in a server or the current one."""
        guild = guild or ctx.guild
        async with self.config.guild(guild).all() as data:
            if cog.qualified_name in data["allowed_cogs"]:
                raise commands.BadArgument(_("This cog is already in the allowed cogs list."))
            data["allowed_cogs"].append(cog.qualified_name)
        self.cache[guild.id] = data

    @onlyallow.command()
    async def addcommand(
        self,
        ctx: commands.Context,
        guild: typing.Optional[GuildConverter],
        *,
        command: commands.converter.CommandConverter,
    ) -> None:
        """Add a command to the allowed commands list in a server or the current one."""
        guild = guild or ctx.guild
        async with self.config.guild(guild).all() as data:
            if command.qualified_name in data["allowed_commands"]:
                raise commands.BadArgument(_("This command is already in the allowed commands list."))
            data["allowed_commands"].append(command.qualified_name)
        self.cache[guild.id] = data

    @onlyallow.command()
    async def removecog(
        self,
        ctx: commands.Context,
        guild: typing.Optional[GuildConverter],
        *,
        cog: commands.converter.CogConverter,
    ) -> None:
        """Remove a cog from the allowed cogs list in a server or the current one."""
        guild = guild or ctx.guild
        async with self.config.guild(guild).all() as data:
            if cog.qualified_name not in data["allowed_cogs"]:
                raise commands.BadArgument(_("This cog isn't in the allowed cogs list."))
            data["allowed_cogs"].remove(cog.qualified_name)
        if not data["allowed_cogs"] and not data["allowed_commands"]:
            self.cache.pop(guild.id, None)
        self.cache[guild.id] = data

    @onlyallow.command()
    async def removecommand(
        self,
        ctx: commands.Context,
        guild: typing.Optional[GuildConverter],
        *,
        command: commands.converter.CommandConverter,
    ) -> None:
        """Remove a command from the allowed commands list in a server or the current one."""
        guild = guild or ctx.guild
        async with self.config.guild(guild).all() as data:
            if command.qualified_name not in data["allowed_commands"]:
                raise commands.BadArgument(_("This command isn't in the allowed commands list."))
            data["allowed_commands"].remove(command.qualified_name)
        if not data["allowed_cogs"] and not data["allowed_commands"]:
            self.cache.pop(guild.id, None)
        self.cache[guild.id] = data

    @onlyallow.command()
    async def clear(self, ctx: commands.Context, guild: typing.Optional[GuildConverter]) -> None:
        """Clear the allowed cogs and commands list in a server or the current one."""
        guild = guild or ctx.guild
        await self.config.guild(guild).clear()
        self.cache.pop(guild.id, None)

    @commands.bot_has_permissions(embed_links=True)
    @onlyallow.command()
    async def list(self, ctx: commands.Context) -> None:
        """List the allowed cogs and commands in the server."""
        data = self.cache.get(ctx.guild.id)
        if data is None:
            await ctx.send(_("All cogs and commands are allowed in this server."))
            return
        embeds = []
        for title, items in [
            (_("Allowed Cogs"), data["allowed_cogs"]),
            (_("Allowed Commands"), data["allowed_commands"]),
        ]:
            if items:
                embed = discord.Embed(
                    title=title,
                    description=humanize_list([f"`{item}`" for item in items]),
                    color=await ctx.embed_color(),
                )
                embeds.append(embed)
        await Menu(pages=[{"embeds": embeds}]).start(ctx=ctx)

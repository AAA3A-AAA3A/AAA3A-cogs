from .AAA3A_utils import CogsUtils  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
from redbot.core.bot import Red  # isort:skip
import discord  # isort:skip

import asyncio

from redbot.core import Config
from redbot.core.utils.chat_formatting import inline
from redbot.core.utils.menus import start_adding_reactions

try:
    from emoji import UNICODE_EMOJI_ENGLISH as EMOJI_DATA  # emoji<2.0.0
except ImportError:
    from emoji import EMOJI_DATA  # emoji>=2.0.0

# Credits:
# The idea for this cog came from @fulksayyan on the cogboard! (https://cogboard.discord.red/t/hired-will-pay-custom-reaction-commands/782)
# Thanks to Kuro for the emoji converter!(https://canary.discord.com/channels/133049272517001216/133251234164375552/1014520590239019048)
# Thanks to @epic guy on Discord for the basic syntax (command groups, commands) and also commands (await ctx.send, await ctx.author.send, await ctx.message.delete())!
# Thanks to the developers of the cogs I added features to as it taught me how to make a cog! (Chessgame by WildStriker, Captcha by Kreusada, Speak by Epic guy and Rommer by Dav)
# Thanks to all the people who helped me with some commands in the #coding channel of the redbot support server!

_ = Translator("ReactToCommand", __file__)

if CogsUtils().is_dpy2:
    from functools import partial

    hybrid_command = partial(commands.hybrid_command, with_app_command=False)
    hybrid_group = partial(commands.hybrid_group, with_app_command=False)
else:
    hybrid_command = commands.command
    hybrid_group = commands.group


class Emoji(commands.EmojiConverter):
    async def convert(self, ctx: commands.Context, argument: str):
        argument = argument.strip("\N{VARIATION SELECTOR-16}")
        if argument in EMOJI_DATA:
            return argument
        return await super().convert(ctx, argument)


@cog_i18n(_)
class ReactToCommand(commands.Cog):
    """A cog to allow a user to execute a command by clicking on a reaction!"""

    def __init__(self, bot: Red):
        self.bot: Red = bot

        self.config: Config = Config.get_conf(
            self,
            identifier=205192943327321000143939875896557571750,  # 703485369742
            force_registration=True,
        )
        self.CONFIG_SCHEMA = 2
        self.reacttocommand_global = {
            "CONFIG_SCHEMA": None,
        }
        self.reacttocommand_guild = {
            "react_commands": {},
        }
        self.config.register_global(**self.reacttocommand_global)
        self.config.register_guild(**self.reacttocommand_guild)

        self.cogsutils = CogsUtils(cog=self)
        self.cogsutils._setup()
        self.purge.very_hidden = True

        self.cache = []

    async def cog_load(self):
        await self.edit_config_schema()

    async def edit_config_schema(self):
        CONFIG_SCHEMA = await self.config.CONFIG_SCHEMA()
        ALL_CONFIG_GUILD = await self.config.all()
        if ALL_CONFIG_GUILD == self.reacttocommand_guild:
            CONFIG_SCHEMA = self.CONFIG_SCHEMA
            await self.config.CONFIG_SCHEMA.set(CONFIG_SCHEMA)
            return
        if CONFIG_SCHEMA is None:
            CONFIG_SCHEMA = 1
            await self.config.CONFIG_SCHEMA(CONFIG_SCHEMA)
        if CONFIG_SCHEMA == self.CONFIG_SCHEMA:
            return
        if CONFIG_SCHEMA == 1:
            for guild in await self.config.all_guilds():
                react_commands = await self.config.guild_from_id(guild).react_command()
                await self.config.guild_from_id(guild).react_commands.set(react_commands)
                await self.config.guild_from_id(guild).react_command.clear()
            CONFIG_SCHEMA = 2
            await self.config.CONFIG_SCHEMA.set(CONFIG_SCHEMA)
        if CONFIG_SCHEMA < self.CONFIG_SCHEMA:
            CONFIG_SCHEMA = self.CONFIG_SCHEMA
            await self.config.CONFIG_SCHEMA.set(CONFIG_SCHEMA)
        self.log.info(
            f"The Config schema has been successfully modified to {self.CONFIG_SCHEMA} for the {self.__class__.__name__} cog."
        )

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            return
        channel = guild.get_channel(payload.channel_id)
        payload.member = guild.get_member(payload.user_id)
        if payload.member is None:
            return
        if guild is None:
            return
        if payload.member.bot:
            return
        if await self.bot.cog_disabled_in_guild(self, guild):
            return
        config = await self.config.guild(guild).react_commands.all()
        if f"{payload.channel_id}-{payload.message_id}" not in config:
            return
        if getattr(payload.emoji, "id", None):
            payload.emoji = str(payload.emoji.id)
        else:
            payload.emoji = str(payload.emoji).strip("\N{VARIATION SELECTOR-16}")
        message = await channel.fetch_message(payload.message_id)
        try:
            await message.remove_reaction(f"{payload.emoji}", payload.member)
        except discord.HTTPException:
            pass
        if f"{payload.emoji}" not in config[f"{payload.channel_id}-{payload.message_id}"]:
            return
        permissions = channel.permissions_for(payload.member)
        if (
            not permissions.read_message_history
            or not permissions.read_messages
            or not permissions.send_messages
            or not permissions.view_channel
        ):
            return
        command = config[f"{payload.channel_id}-{payload.message_id}"][f"{payload.emoji}"]
        context = await self.cogsutils.invoke_command(
            author=payload.member,
            channel=channel,
            command=command,
            message=message,
            __is_mocked__=True,
        )
        self.cache.append(context)

    @commands.Cog.listener()
    async def on_command_completion(self, ctx: commands.Context):
        if ctx in self.cache:
            self.cache.remove(ctx)

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: Exception):
        if ctx not in self.cache:
            return
        self.cache.remove(ctx)
        if isinstance(error, commands.CommandInvokeError):
            await asyncio.sleep(0.7)
            self.log.exception(
                f"This exception in the '{ctx.command.qualified_name}' command may have been triggered by the use of ReactToCommand. Check that the same error occurs with the text command, before reporting it.",
                exc_info=None,
            )
            message = f"This error in the '{ctx.command.qualified_name}' command may have been triggered by the use of ReactToCommand.\nCheck that the same error occurs with the text command, before reporting it."
            await ctx.send(inline(message))

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if not message.guild:
            return
        config = await self.config.guild(message.guild).react_commands.all()
        if f"{message.channel.id}-{message.id}" not in config:
            return
        del config[f"{message.channel.id}-{message.id}"]
        await self.config.guild(message.guild).react_commands.set(config)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent) -> None:
        guild = self.bot.get_guild(payload.guild_id)
        payload.member = guild.get_member(payload.user_id)
        if payload.member is None:
            return
        if guild is None:
            return
        if not payload.member.id == guild.me.id:
            return
        config = await self.config.guild(guild).react_commands.all()
        if f"{payload.channel_id}-{payload.message_id}" not in config:
            return
        if getattr(payload.emoji, "id", None):
            payload.emoji = str(payload.emoji.id)
        else:
            payload.emoji = str(payload.emoji).strip("\N{VARIATION SELECTOR-16}")
        if f"{payload.emoji}" not in config[f"{payload.channel_id}-{payload.message_id}"]:
            return
        del config[f"{payload.channel_id}-{payload.message_id}"][f"{payload.emoji}"]
        if config[f"{payload.channel_id}-{payload.message_id}"] == {}:
            del config[f"{payload.channel_id}-{payload.message_id}"]
        await self.config.guild(guild).react_commands.set(config)

    @commands.guild_only()
    @commands.is_owner()
    @hybrid_group(aliases=["rtc"])
    async def reacttocommand(self, ctx: commands.Context):
        """Group of commands for use ReactToCommand."""
        pass

    @reacttocommand.command()
    async def add(
        self, ctx: commands.Context, message: discord.Message, react: Emoji, *, command: str
    ):
        """Add a command-reaction to a message.
        There should be no prefix in the command.
        The command will be invoked with the permissions of the user who clicked on the reaction.
        This user must be able to see writing in the channel.
        """
        permissions = message.channel.permissions_for(ctx.guild.me)
        if (
            not permissions.add_reactions
            or not permissions.read_message_history
            or not permissions.read_messages
            or not permissions.view_channel
        ):
            await ctx.send(
                _(
                    "I don't have sufficient permissions on the channel where the message you specified is located.\nI need the permissions to add reactions and to see the messages in that channel."
                ).format(**locals())
            )
            return
        if not ctx.prefix == "/":
            msg = ctx.message
            msg.content = f"{ctx.prefix}{command}"
            new_ctx = await ctx.bot.get_context(msg)
            if not new_ctx.valid:
                await ctx.send(_("You have not specified a correct command.").format(**locals()))
                return
        try:
            await start_adding_reactions(message, [react])
        except discord.HTTPException:
            await ctx.send(
                _(
                    "An error has occurred. It is possible that the emoji you provided is invalid."
                ).format(**locals())
            )
            return
        config = await self.config.guild(ctx.guild).react_commands.all()
        if f"{message.channel.id}-{message.id}" not in config:
            config[f"{message.channel.id}-{message.id}"] = {}
        config[f"{message.channel.id}-{message.id}"][f"{react}"] = command
        await self.config.guild(ctx.guild).react_commands.set(config)
        await ctx.tick(message="Done.")

    @reacttocommand.command()
    async def remove(self, ctx: commands.Context, message: discord.Message, react: Emoji):
        """Remove a command-reaction to a message."""
        await start_adding_reactions(message, [react])
        config = await self.config.guild(ctx.guild).react_commands.all()
        if f"{message.channel.id}-{message.id}" not in config:
            await ctx.send(
                _("No command-reaction is configured for this message.").format(**locals())
            )
            return
        if f"{getattr(react, 'id', react)}" not in config[f"{message.channel.id}-{message.id}"]:
            await ctx.send(
                _("I wasn't watching for this reaction on this message.").format(**locals())
            )
            return
        if hasattr(react, "id"):
            del config[f"{message.channel.id}-{message.id}"][f"{react.id}"]
        else:
            del config[f"{message.channel.id}-{message.id}"][f"{react}"]
        if config[f"{message.channel.id}-{message.id}"] == {}:
            del config[f"{message.channel.id}-{message.id}"]
        try:
            await message.remove_reaction(f"{react}", ctx.guild.me)
        except discord.HTTPException:
            pass
        await self.config.guild(ctx.guild).react_commands.set(config)
        await ctx.tick(message="Done.")

    @reacttocommand.command()
    async def clear(self, ctx: commands.Context, message: discord.Message):
        """Clear all commands-reactions to a message."""
        config = await self.config.guild(ctx.guild).react_commands.all()
        if f"{message.channel.id}-{message.id}" not in config:
            await ctx.send(
                _("No command-reaction is configured for this message.").format(**locals())
            )
            return
        for react in config[f"{message.channel.id}-{message.id}"]:
            try:
                await message.remove_reaction(f"{react}", ctx.guild.me)
            except discord.HTTPException:
                pass
        del config[f"{message.channel.id}-{message.id}"]
        await self.config.guild(ctx.guild).react_commands.set(config)
        await ctx.tick(message="Done.")

    @reacttocommand.command(hidden=True)
    async def purge(self, ctx: commands.Context):
        """Clear all commands-reactions to a **guild**."""
        await self.config.guild(ctx.guild).react_commands.clear()
        await ctx.tick(message="Done.")

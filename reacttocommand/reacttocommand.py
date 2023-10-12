from AAA3A_utils import Cog, CogsUtils  # isort:skip
from redbot.core import commands, Config  # isort:skip
from redbot.core.bot import Red  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import asyncio

from redbot.core.utils.chat_formatting import inline

try:
    from emoji import UNICODE_EMOJI_ENGLISH as EMOJI_DATA  # emoji<2.0.0
except ImportError:
    from emoji import EMOJI_DATA  # emoji>=2.0.0

# Credits:
# General repo credits.
# The idea for this cog came from @fulksayyan on the cogboard! (https://cogboard.discord.red/t/hired-will-pay-custom-reaction-commands/782)
# Thanks to Kuro for the emoji converter (https://canary.discord.com/channels/133049272517001216/133251234164375552/1014520590239019048)!

_ = Translator("ReactToCommand", __file__)


class Emoji(commands.EmojiConverter):
    async def convert(
        self, ctx: commands.Context, argument: str
    ) -> typing.Union[str, discord.Emoji]:
        # argument = argument.strip("\N{VARIATION SELECTOR-16}")
        if argument in EMOJI_DATA:
            return argument
        if argument in {
            "0",
            "1",
            "2",
            "3",
            "4",
            "5",
            "6",
            "7",
            "8",
            "9",
            "#",
            "*",
            "🇦",
            "🇧",
            "🇨",
            "🇩",
            "🇪",
            "🇫",
            "🇬",
            "🇭",
            "🇮",
            "🇯",
            "🇰",
            "🇱",
            "🇲",
            "🇳",
            "🇴",
            "🇵",
            "🇶",
            "🇷",
            "🇸",
            "🇹",
            "🇺",
            "🇻",
            "🇼",
            "🇽",
            "🇾",
            "🇿",
        }:
            return argument
        return await super().convert(ctx, argument=argument)


@cog_i18n(_)
class ReactToCommand(Cog):
    """A cog to allow a user to execute a command by clicking on a reaction!"""

    def __init__(self, bot: Red) -> None:
        super().__init__(bot=bot)

        self.config: Config = Config.get_conf(
            self,
            identifier=205192943327321000143939875896557571750,  # 703485369742
            force_registration=True,
        )
        self.CONFIG_SCHEMA = 2
        self.reacttocommand_global: typing.Dict[str, typing.Optional[int]] = {
            "CONFIG_SCHEMA": None,
        }
        self.reacttocommand_guild: typing.Dict[
            str, typing.Dict[str, typing.Dict[str, typing.Dict[str, str]]]
        ] = {
            "react_commands": {},
        }
        self.config.register_global(**self.reacttocommand_global)
        self.config.register_guild(**self.reacttocommand_guild)

        self.cache: typing.List[commands.Context] = []

    async def cog_load(self) -> None:
        await super().cog_load()
        await self.edit_config_schema()

    async def red_delete_data_for_user(self, *args, **kwargs) -> None:
        """Nothing to delete."""
        return

    async def red_get_data_for_user(self, *args, **kwargs) -> typing.Dict[str, typing.Any]:
        """Nothing to get."""
        return {}

    async def edit_config_schema(self) -> None:
        CONFIG_SCHEMA = await self.config.CONFIG_SCHEMA()
        if CONFIG_SCHEMA is None:
            CONFIG_SCHEMA = 1
            await self.config.CONFIG_SCHEMA(CONFIG_SCHEMA)
        if CONFIG_SCHEMA == self.CONFIG_SCHEMA:
            return
        if CONFIG_SCHEMA == 1:
            for guild_id in await self.config.all_guilds():
                react_commands = await self.config.guild_from_id(guild_id).react_command()
                await self.config.guild_from_id(guild_id).react_commands.set(react_commands)
                await self.config.guild_from_id(guild_id).react_command.clear()
            CONFIG_SCHEMA = 2
            await self.config.CONFIG_SCHEMA.set(CONFIG_SCHEMA)
        if CONFIG_SCHEMA < self.CONFIG_SCHEMA:
            CONFIG_SCHEMA = self.CONFIG_SCHEMA
            await self.config.CONFIG_SCHEMA.set(CONFIG_SCHEMA)
        self.log.info(
            f"The Config schema has been successfully modified to {self.CONFIG_SCHEMA} for the {self.qualified_name} cog."
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
        if payload.member.bot:
            return
        if await self.bot.cog_disabled_in_guild(
            cog=self, guild=guild
        ) or not await self.bot.allowed_by_whitelist_blacklist(who=payload.member):
            return
        config = await self.config.guild(guild).react_commands.all()
        if f"{payload.channel_id}-{payload.message_id}" not in config:
            return
        emoji = payload.emoji

        class FakeContext:
            def __init__(
                self,
                bot: Red,
                author: discord.Member,
                guild: discord.Guild,
                channel: discord.TextChannel,
            ):
                self.bot: Red = bot
                self.author: discord.Member = author
                self.guild: discord.Guild = guild
                self.channel: discord.TextChannel = channel

        fake_context = FakeContext(self.bot, payload.member, guild, channel)
        emoji = await Emoji().convert(fake_context, str(emoji))
        emoji = f"{getattr(emoji, 'id', emoji)}"
        message = await channel.fetch_message(payload.message_id)
        try:
            await message.remove_reaction(emoji, payload.member)
        except discord.HTTPException:
            pass
        if emoji not in config[f"{payload.channel_id}-{payload.message_id}"]:
            return
        permissions = channel.permissions_for(payload.member)
        if (
            not permissions.read_message_history
            or not permissions.read_messages
            or not permissions.send_messages
            or not permissions.view_channel
        ):
            return
        command = config[f"{payload.channel_id}-{payload.message_id}"][emoji]
        context = await CogsUtils.invoke_command(
            bot=self.bot,
            author=payload.member,
            channel=channel,
            command=command,
            __is_mocked__=True,
        )
        self.cache.append(context)

    @commands.Cog.listener()
    async def on_command_completion(self, ctx: commands.Context) -> None:
        if ctx in self.cache:
            self.cache.remove(ctx)

    @commands.Cog.listener()
    async def on_command_error(
        self, ctx: commands.Context, error: commands.CommandError, unhandled_by_cog: bool = False
    ) -> None:
        if ctx not in self.cache:
            return
        self.cache.remove(ctx)
        if isinstance(error, commands.CommandInvokeError):
            await asyncio.sleep(0.7)
            self.log.error(
                f"This exception in the '{ctx.command.qualified_name}' command may have been triggered by the use of ReactToCommand. Check that the same error occurs with the text command, before reporting it.",
                exc_info=None,
            )
            message = f"This error in the '{ctx.command.qualified_name}' command may have been triggered by the use of ReactToCommand.\nCheck that the same error occurs with the text command, before reporting it."
            await ctx.send(inline(message))

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message) -> None:
        if message.guild is None:
            return
        config = await self.config.guild(message.guild).react_commands.all()
        if f"{message.channel.id}-{message.id}" not in config:
            return
        del config[f"{message.channel.id}-{message.id}"]
        await self.config.guild(message.guild).react_commands.set(config)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent) -> None:
        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            return
        channel = guild.get_channel(payload.channel_id)
        payload.member = guild.get_member(payload.user_id)
        if payload.member is None:
            return
        if payload.member.id != guild.me.id:
            return
        config = await self.config.guild(guild).react_commands.all()
        if f"{payload.channel_id}-{payload.message_id}" not in config:
            return
        emoji = payload.emoji

        class FakeContext:
            def __init__(
                self,
                bot: Red,
                author: discord.Member,
                guild: discord.Guild,
                channel: discord.TextChannel,
            ):
                self.bot: Red = bot
                self.author: discord.Member = author
                self.guild: discord.Guild = guild
                self.channel: discord.TextChannel = channel

        fake_context = FakeContext(self.bot, payload.member, guild, channel)
        emoji = await Emoji().convert(fake_context, str(emoji))
        emoji = f"{getattr(emoji, 'id', emoji)}"
        if emoji not in config[f"{payload.channel_id}-{payload.message_id}"]:
            return
        del config[f"{payload.channel_id}-{payload.message_id}"][emoji]
        if config[f"{payload.channel_id}-{payload.message_id}"] == {}:
            del config[f"{payload.channel_id}-{payload.message_id}"]
        await self.config.guild(guild).react_commands.set(config)

    @commands.guild_only()
    @commands.is_owner()
    @commands.hybrid_group(aliases=["rtc"])
    async def reacttocommand(self, ctx: commands.Context) -> None:
        """Group of commands to use ReactToCommand."""
        pass

    @reacttocommand.command(aliases=["+"])
    async def add(
        self, ctx: commands.Context, message: discord.Message, emoji: Emoji, *, command: str
    ) -> None:
        """Add a reaction-command for a message.

        There should be no prefix in the command.
        The command will be invoked with the permissions of the user who clicked on the reaction.
        This user must be able to see writing in the channel.
        """
        channel_permissions = message.channel.permissions_for(ctx.me)
        if (
            not channel_permissions.view_channel
            or not channel_permissions.read_messages
            or not channel_permissions.read_message_history
            or not channel_permissions.add_reactions
        ):
            raise commands.UserFeedbackCheckFailure(
                _(
                    "I don't have sufficient permissions on the channel where the message you specified is located.\nI need the permissions to add reactions and to see the messages in that channel."
                )
            )
        if ctx.prefix != "/":
            msg = ctx.message
            msg.content = f"{ctx.prefix}{command}"
            new_ctx = await ctx.bot.get_context(msg)
            if not new_ctx.valid:
                raise commands.UserFeedbackCheckFailure(
                    _("You have not specified a correct command.")
                )
        try:
            await message.add_reaction(emoji)
        except discord.HTTPException:
            raise commands.UserFeedbackCheckFailure(
                _("An error has occurred. It is possible that the emoji you provided is invalid.")
            )
        config = await self.config.guild(ctx.guild).react_commands.all()
        if f"{message.channel.id}-{message.id}" not in config:
            config[f"{message.channel.id}-{message.id}"] = {}
        config[f"{message.channel.id}-{message.id}"][f"{getattr(emoji, 'id', emoji)}"] = command
        await self.config.guild(ctx.guild).react_commands.set(config)
        await ctx.send(_("Reaction-command added to this message."))

    @reacttocommand.command(aliases=["-"])
    async def remove(self, ctx: commands.Context, message: discord.Message, emoji: Emoji) -> None:
        """Remove a reaction-command for a message."""
        config = await self.config.guild(ctx.guild).react_commands.all()
        if f"{message.channel.id}-{message.id}" not in config:
            raise commands.UserFeedbackCheckFailure(
                _("No reaction-command is configured for this message.")
            )
        if f"{getattr(emoji, 'id', emoji)}" not in config[f"{message.channel.id}-{message.id}"]:
            raise commands.UserFeedbackCheckFailure(
                _("I wasn't watching for this reaction on this message.")
            )
        del config[f"{message.channel.id}-{message.id}"][f"{getattr(emoji, 'id', emoji)}"]
        if config[f"{message.channel.id}-{message.id}"] == {}:
            del config[f"{message.channel.id}-{message.id}"]
        try:
            await message.remove_reaction(f"{emoji}", ctx.me)
        except discord.HTTPException:
            pass
        await self.config.guild(ctx.guild).react_commands.set(config)
        await ctx.send(_("Reaction-command removed from this message."))

    @reacttocommand.command()
    async def clear(self, ctx: commands.Context, message: discord.Message) -> None:
        """Clear all reactions-commands for a message."""
        config = await self.config.guild(ctx.guild).react_commands.all()
        if f"{message.channel.id}-{message.id}" not in config:
            raise commands.UserFeedbackCheckFailure(
                _("No reaction-command is configured for this message.")
            )
        for react in config[f"{message.channel.id}-{message.id}"]:
            try:
                await message.remove_reaction(f"{react}", ctx.me)
            except discord.HTTPException:
                pass
        del config[f"{message.channel.id}-{message.id}"]
        await self.config.guild(ctx.guild).react_commands.set(config)
        await ctx.send(_("Reactions-commands cleared for this message."))

    @reacttocommand.command(hidden=True)
    async def purge(self, ctx: commands.Context) -> None:
        """Clear all reactions-commands for a guild."""
        await self.config.guild(ctx.guild).react_commands.clear()
        await ctx.send(_("All reactions-commands purged."))

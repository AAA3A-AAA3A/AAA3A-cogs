from AAA3A_utils import Cog, CogsUtils  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.bot import Red  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

# Credits:
# General repo credits.
# Removed, but: Thanks to TrustyJAID for the code (a bit modified to work here and to improve as needed) for the log messages sent (https://github.com/TrustyJAID/Trusty-cogs/tree/master/extendedmodlog)!

_ = Translator("CmdChannel", __file__)


@cog_i18n(_)
class CmdChannel(Cog):
    """A cog to send the result of a command to another channel!"""

    def __init__(self, bot: Red) -> None:
        super().__init__(bot=bot)

        # self.config: Config = Config.get_conf(
        #     self,
        #     identifier=205192943327321000143939875896557571750,  # 793502759720
        #     force_registration=True,
        # )
        # self.config.register_guild(
            # logschannel=None,
            # enabled=True,
            # confirmation=False,
            # delete_message=False,
            # information_message=False,
        # )

    @commands.Cog.listener()
    async def on_message_without_command(self, message: discord.Message) -> None:
        if await self.bot.cog_disabled_in_guild(
            cog=self, guild=message.guild
        ) or not await self.bot.allowed_by_whitelist_blacklist(who=message.author):
            return
        if message.webhook_id is not None or message.author.bot:
            return
        context = await self.bot.get_context(message)
        if context.prefix is None:
            return
        command = context.message.content[len(str(context.prefix)) :]
        if len(command.split(" ")) == 0:
            return
        command_name = command.split(" ")[0]
        if command_name not in ("cmduser", "cmduserchannel"):
            return
        command = command[3:]
        await CogsUtils.invoke_command(
            bot=self.bot,
            author=context.author,
            channel=context.channel,
            command=f"cmdchannel {command}",
            prefix=context.prefix,
            message=context.message,
        )

    @commands.hybrid_group(aliases=["cmdmock"], invoke_without_command=True)
    async def cmdchannel(
        self, ctx: commands.Context, channel: discord.TextChannel, *, command: str
    ):
        """Use `[p]cmdchannel`, `[p]cmduser` and `[p]cmduserchannel`."""
        if ctx.invoked_subcommand is None:
            await self.channel(ctx, channel=channel, command=command)

    @commands.mod()
    @cmdchannel.command()
    async def channel(
        self, ctx: commands.Context, channel: discord.TextChannel, *, command: str
    ) -> None:
        """Act as if the command had been typed in the channel of your choice.
        The prefix must not be entered if it is a command. It will be a message only, if the command is invalid.

        Use `[p]cmdchannel`!
        """
        guild = channel.guild
        if ctx.author not in guild.members:
            raise commands.UserFeedbackCheckFailure(
                _("To send commands to another server, you must be there.")
            )
        if not command and not ctx.message.embeds and not ctx.message.attachments:
            raise commands.UserInputError()
        await CogsUtils.invoke_command(
            bot=ctx.bot,
            author=ctx.author,
            channel=channel,
            command=command,
            prefix=ctx.prefix,
            message=ctx.message,
            dispatch_message=True,
        )

    @commands.is_owner()
    @cmdchannel.command()
    async def user(
        self,
        ctx: commands.Context,
        user: typing.Union[discord.Member, discord.User],
        *,
        command: str,
    ) -> None:
        """Act as if the command had been typed by imitating the specified user.
        The prefix must not be entered if it is a command. It will be a message only, if the command is invalid.

        Use `[p]cmduser`!
        """
        if user is None:
            user = ctx.author
        if ctx.bot.get_cog("Dev") is None:
            raise commands.UserFeedbackCheckFailure(
                _(
                    "To be able to run a command as another user, the cog Dev must be loaded, to make sure you know what you are doing."
                )
            )
        await CogsUtils.invoke_command(
            bot=ctx.bot,
            author=user,
            channel=ctx.channel,
            command=command,
            prefix=ctx.prefix,
            message=ctx.message,
            dispatch_message=True,
        )

    @commands.is_owner()
    @cmdchannel.command()
    async def userchannel(
        self,
        ctx: commands.Context,
        user: discord.User,
        channel: typing.Optional[discord.TextChannel] = None,
        *,
        command: str,
    ) -> None:
        """Act as if the command had been typed in the channel of your choice by imitating the specified user.
        The prefix must not be entered if it is a command. It will be a message only, if the command is invalid.

        Use `[p]cmduserchannel`!
        """
        if user is None:
            user = ctx.author
        if channel is None:
            channel = ctx.channel
        if channel.guild is not None:
            if ctx.author not in channel.guild.members:
                raise commands.UserFeedbackCheckFailure(
                    _("To send commands to another server, you must be there.")
                )
            user = channel.guild.get_member(user.id) or user
        if ctx.bot.get_cog("Dev") is None:
            raise commands.UserFeedbackCheckFailure(
                _(
                    "To be able to run a command as another user, the cog Dev must be loaded, to make sure you know what you are doing."
                )
            )

        await CogsUtils.invoke_command(
            bot=ctx.bot,
            author=user,
            channel=channel,
            command=command,
            prefix=ctx.prefix,
            message=ctx.message,
            dispatch_message=True,
        )

    @cmdchannel.command()
    async def testvar(self, ctx: commands.Context) -> None:
        """Test variables."""
        embed: discord.Embed = discord.Embed()
        embed.title = _("Testvar")
        embed.description = _("Variables:")
        embed.add_field(name=_("Author:"), value=f"{ctx.author}")
        embed.add_field(name=_("Channel:"), value=f"{ctx.channel}")
        await ctx.send(embed=embed)

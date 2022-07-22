from .AAA3A_utils.cogsutils import CogsUtils  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
from redbot.core.bot import Red  # isort:skip
import discord  # isort:skip
import typing  # isort:skip
from redbot.core import Config

# Credits:
# Thanks to @epic guy on Discord for the basic syntax (command groups, commands) and also commands (await ctx.send, await ctx.author.send, await ctx.message.delete())!
# Thanks to TrustyJAID for the code (a bit modified to work here and to improve as needed) for the log messages sent! (https://github.com/TrustyJAID/Trusty-cogs/tree/master/extendedmodlog)
# Thanks to Kreusada for the code (with modifications to make it work and match the syntax of the rest) to add a log channel or remove it if no channel is specified! (https://github.com/Kreusada/Kreusada-Cogs/tree/master/captcha)
# Thanks to the developers of the cogs I added features to as it taught me how to make a cog! (Chessgame by WildStriker, Captcha by Kreusada, Speak by Epic guy and Rommer by Dav)
# Thanks to all the people who helped me with some commands in the #coding channel of the redbot support server!

_ = Translator("CmdChannel", __file__)

@cog_i18n(_)
class CmdChannel(commands.Cog):
    """A cog to send the result of a command to another channel!"""

    def __init__(self, bot: Red):
        self.bot: Red = bot

        self.config: Config = Config.get_conf(
            self,
            identifier=793502759720,
            force_registration=True,
        )
        self.cmd_guild = {
            "logschannel": None,  # The channel for logs.
            "enabled_cmdchannel": True,  # Enable the possibility of commands.
            "confirmation_cmdchannel": False,  # Enable the confirmation.
            "deletemessage_cmdchannel": False,  # Enable the message delete.
            "informationmessage_cmdchannel": False,  # Enable the information message.
            "enabled_cmduser": True,  # Enable the possibility of commands.
            "confirmation_cmduser": False,  # Enable the confirmation.
            "deletemessage_cmduser": False,  # Enable the message delete.
            "informationmessage_cmduser": False,  # Enable the information message.
            "enabled_cmduserchannel": True,  # Enable the possibility of commands.
            "confirmation_cmduserchannel": False,  # Enable the confirmation.
            "deletemessage_cmduserchannel": False,  # Enable the message delete.
            "informationmessage_cmduserchannel": False,  # Enable the information message.
        }
        self.config.register_guild(**self.cmd_guild)

        self.cogsutils = CogsUtils(cog=self)
        self.cogsutils._setup()

    @commands.guild_only()
    @commands.mod()
    @commands.command(aliases=["channelcmd"])
    async def cmdchannel(self, ctx: commands.Context, guild: typing.Optional[discord.Guild]=None, channel: typing.Optional[typing.Union[discord.TextChannel, int]]=None, *, command: str = ""):
        """Act as if the command had been typed in the channel of your choice.
        The prefix must be entered if it is a command. Otherwise, it will be a message only.
        If you do not specify a channel, the current one will be used, unless the command you want to use is the name of an existing channel (help or test for example).
        """
        if channel is not None:
            if isinstance(channel, int):
                if guild is not None:
                    channel = guild.get_channel(channel)
                else:
                    if ctx.author.id in ctx.bot.owner_ids:
                        await ctx.send(_("Please specify a server if you want to use a command in another server.").format(**locals()))
                        return
                    else:
                        channel = None

        if channel is None:
            channel = ctx.channel

        guild = channel.guild

        if channel not in ctx.guild.channels and ctx.author.id not in ctx.bot.owner_ids:
            await ctx.send(_("Only a bot owner can use a command from another server.").format(**locals()))
            return

        member = guild.get_member(ctx.author.id)
        if member is None:
            await ctx.send(_("To send commands to another server, you must be there.").format(**locals()))
            return

        if not command and not ctx.message.embeds and not ctx.message.attachments:
            await ctx.send_help()
            return

        config = await self.config.guild(guild).all()
        logschannel = config["logschannel"]
        actual_state_enabled = config["enabled_cmdchannel"]
        actual_state_confirmation = config["confirmation_cmdchannel"]
        actual_state_deletemessage = config["deletemessage_cmdchannel"]
        actual_state_information = config["informationmessage_cmdchannel"]
        cmd_colour = await self.bot.get_embed_colour(guild.text_channels[0])
        if actual_state_enabled:
            permissions = channel.permissions_for(ctx.author)
            if permissions.read_messages and permissions.send_messages:
                if actual_state_information:
                    await channel.send(_("The command issued in this channel is:\n```{command}```").format(**locals()))
                if logschannel:
                    can_run = await self.member_can_run(ctx)
                    embed = discord.Embed(
                        description=f"CmdChannel - Command used: {command}",
                        colour=cmd_colour,
                    )
                    embed.add_field(name=(_("Imitated user").format(**locals())), value=ctx.author.mention)
                    embed.add_field(name=(_("Channel").format(**locals())), value=channel.mention)
                    embed.add_field(name=(_("Can Run").format(**locals())), value=str(can_run))
                    author_title = _("{ctx.author} ({ctx.author.id}) - Used a Command").format(**locals())
                    embed.set_author(name=author_title, icon_url=ctx.author.display_avatar if self.cogsutils.is_dpy2 else ctx.author.avatar_url)
                    logschannel = ctx.bot.get_channel(logschannel)
                    await logschannel.send(embed=embed)
                await self.cogsutils.invoke_command(author=ctx.author, channel=channel, command=command)
                if actual_state_confirmation:
                    try:
                        await ctx.author.send(_("The `{command}` command has been launched in the {channel} channel. You can check if it worked.").format(**locals()))
                    except discord.Forbidden:
                        await ctx.send(_("The `{command}` command has been launched in the {channel} channel. You can check if it worked.").format(**locals()))
            else:
                try:
                    await ctx.author.send(_("You cannot run this command because you do not have the permissions to send messages in the {channel} channel.").format(**locals()))
                except discord.Forbidden:
                    await ctx.send(_("You cannot run this command because you do not have the permissions to send messages in the {channel} channel.").format(**locals()))
        else:
            try:
                await ctx.author.send(_("CommandChannel have been disabled by an administrator of this server.").format(**locals()))
            except discord.Forbidden:
                await ctx.send(_("CommandChannel have been disabled by an administrator of this server.").format(**locals()))
            return

    @commands.guild_only()
    @commands.is_owner()
    @commands.command(aliases=["usercmd"])
    async def cmduser(self, ctx: commands.Context, user: typing.Optional[discord.Member]=None, *, command: str = ""):
        """Act as if the command had been typed by imitating the specified user.
        The prefix must be entered if it is a command. Otherwise, it will be a message only.
        If you do not specify a user, the author will be used.
        """
        if user is None:
            user = ctx.author

        if not command and not ctx.message.embeds and not ctx.message.attachments:
            await ctx.send_help()
            return

        config = await self.config.guild(ctx.guild).all()
        logschannel = config["logschannel"]
        actual_state_enabled = config["enabled_cmduser"]
        actual_state_confirmation = config["confirmation_cmduser"]
        actual_state_deletemessage = config["deletemessage_cmduser"]
        actual_state_information = config["informationmessage_cmduser"]
        cmd_colour = await self.bot.get_embed_colour(ctx.guild.text_channels[0])
        if actual_state_enabled:
            permissions = ctx.channel.permissions_for(ctx.author)
            if permissions.read_messages and permissions.send_messages:
                if actual_state_information:
                    await ctx.channel.send(_("The command issued in this channel is:\n```{command}```").format(**locals()))
                if logschannel:
                    can_run = await self.member_can_run(ctx)
                    embed = discord.Embed(
                        description=_("CmdUser - Command used: {command}").format(**locals()),
                        colour=cmd_colour,
                    )
                    embed.add_field(name=(_("Imitated user").format(**locals())), value=user)
                    embed.add_field(name=(_("Channel").format(**locals())), value=ctx.channel.mention)
                    embed.add_field(name=(_("Can Run").format(**locals())), value=str(can_run))
                    author_title = _("{ctx.author} ({ctx.author.id}) - Used a Command").format(**locals())
                    embed.set_author(name=author_title, icon_url=ctx.author.display_avatar if self.cogsutils.is_dpy2 else ctx.author.avatar_url)
                    logschannel = ctx.bot.get_channel(logschannel)
                    await logschannel.send(embed=embed)
                await self.cogsutils.invoke_command(author=user, channel=ctx.channel, command=command)
                if actual_state_confirmation:
                    try:
                        await ctx.author.send(_("The `{command}` command has been launched in the {ctx.channel} channel by imitating the {user} user. You can check if it worked.").format(**locals()))
                    except discord.Forbidden:
                        await ctx.send(_("The `{command}` command has been launched in the {ctx.channel} channel by imitating the {user} user. You can check if it worked.").format(**locals()))
            else:
                try:
                    await ctx.author.send(_("You cannot run this command because you do not have the permissions to send messages in the {ctx.channel} channel.").format(**locals()))
                except discord.Forbidden:
                    await ctx.send(_("You cannot run this command because you do not have the permissions to send messages in the {ctx.channel} channel.").format(**locals()))
        else:
            try:
                await ctx.author.send(_("CommandUser have been disabled by an administrator of this server.").format(**locals()))
            except discord.Forbidden:
                await ctx.send(_("CommandUser have been disabled by an administrator of this server.").format(**locals()))
            return

    @commands.guild_only()
    @commands.is_owner()
    @commands.command(aliases=["userchannelcmd"])
    async def cmduserchannel(self, ctx: commands.Context, user: typing.Optional[discord.Member]=None, channel: typing.Optional[discord.TextChannel]=None, *, command: str = ""):
        """Act as if the command had been typed in the channel of your choice by imitating the specified user.
        The prefix must be entered if it is a command. Otherwise, it will be a message only.
        If you do not specify a user, the author will be used.
        """
        if channel is None:
            channel = ctx.channel

        if user is None:
            user = ctx.author

        if not command and not ctx.message.embeds and not ctx.message.attachments:
            await ctx.send_help()
            return

        config = await self.config.guild(ctx.guild).all()
        logschannel = config["logschannel"]
        actual_state_enabled = config["enabled_cmduserchannel"]
        actual_state_confirmation = config["confirmation_cmduserchannel"]
        actual_state_deletemessage = config["deletemessage_cmduserchannel"]
        actual_state_information = config["informationmessage_cmduserchannel"]
        cmd_colour = await self.bot.get_embed_colour(ctx.guild.text_channels[0])
        if actual_state_enabled:
            permissions = channel.permissions_for(ctx.author)
            if permissions.read_messages and permissions.send_messages:
                if actual_state_information:
                    await channel.send(_("The command issued in this channel is:\n```{command}```").format(**locals()))
                if logschannel:
                    can_run = await self.member_can_run(ctx)
                    embed = discord.Embed(
                        description=_("CmdUserChannel - Command used: {command}").format(**locals()),
                        colour=cmd_colour,
                    )
                    embed.add_field(name=(_("Imitated user").format(**locals())), value=user)
                    embed.add_field(name=(_("Channel").format(**locals())), value=channel.mention)
                    embed.add_field(name=(_("Can Run").format(**locals())), value=str(can_run))
                    author_title = _("{ctx.author} ({ctx.author.id}) - Used a Command").format(**locals())
                    embed.set_author(name=author_title, icon_url=ctx.author.display_avatar if self.cogsutils.is_dpy2 else ctx.author.avatar_url)
                    logschannel = ctx.bot.get_channel(logschannel)
                    await logschannel.send(embed=embed)
                await self.cogsutils.invoke_command(author=user, channel=channel, command=command)
                if actual_state_confirmation:
                    try:
                        await ctx.author.send(_("The `{command}` command has been launched in the {channel} channel by imitating the {user} user. You can check if it worked.").format(**locals()))
                    except discord.Forbidden:
                        await ctx.send(_("The `{command}` command has been launched in the {channel} channel by imitating the {user} user. You can check if it worked.").format(**locals()))
            else:
                try:
                    await ctx.author.send(_("You cannot run this command because you do not have the permissions to send messages in the {channel} channel.").format(**locals()))
                except discord.Forbidden:
                    await ctx.send(_("You cannot run this command because you do not have the permissions to send messages in the {channel} channel.").format(**locals()))
        else:
            try:
                await ctx.author.send(_("CommandUserChannel have been disabled by an administrator of this server.").format(**locals()))
            except discord.Forbidden:
                await ctx.send(_("CommandUserChannel have been disabled by an administrator of this server.").format(**locals()))
            return

    @commands.command()
    async def testvar(self, ctx: commands.Context):
        """Test variables.
        """
        embed: discord.Embed = discord.Embed()
        embed.title = _("Testvar").format(**locals())
        embed.description = _("Variables:").format(**locals())
        embed.add_field(
            name=_("Author:").format(**locals()),
            value=f"{ctx.author}")
        embed.add_field(
            name=_("Channel:").format(**locals()),
            value=f"{ctx.channel}")
        await ctx.send(embed=embed)

    @commands.guild_only()
    @commands.guildowner_or_permissions(administrator=True)
    @commands.group(name="cmdset", aliases=["setcmd"])
    async def configuration(self, ctx: commands.Context):
        """Configure Command for your server."""

    @configuration.command(aliases=["lchann", "lchannel", "logschan", "logchannel", "logsc"], usage="<text_channel_or_'none'>")
    async def logschannel(self, ctx: commands.Context, *, channel: typing.Optional[discord.TextChannel]=None):
        """Set a channel where events are registered.

        ``channel``: Text channel.
        You can also use "None" if you wish to remove the logging channel.
        """
        if not ctx.author.id == ctx.guild.owner.id:
            await ctx.send(_("Only the owner of this server can access these commands!").format(**locals()))
            return

        if channel is None:
            await self.config.guild(ctx.guild).logschannel.clear()
            await ctx.send(_("Logging channel removed.").format(**locals()))
            return

        needperm = await self.check_permissions_in_channel(["embed_links", "read_messages", "read_message_history", "send_messages", "attach_files"], channel)
        if needperm:
            await ctx.send(_("The bot does not have at least one of the following permissions in this channel: `embed_links`, `read_messages`, `read_message_history`, `send_messages`, `attach_files`.")).format(**locals())
            return

        await self.config.guild(ctx.guild).logschannel.set(channel.id)
        await ctx.send(_("Logging channel registered: {channel.mention}.").format(**locals()))

    async def check_permissions_in_channel(self, permissions: typing.List[str], channel: discord.TextChannel):
        """Function to checks if the permissions are available in a guild.
        This will return a list of the missing permissions.
        """
        return [
            permission
            for permission in permissions
            if not getattr(channel.permissions_for(channel.guild.me), permission)
        ]

    @commands.guildowner_or_permissions(administrator=True)
    @configuration.group(name="cmdchannel", aliases=["channelcmd"])
    async def cmdchannelconfig(self, ctx: commands.Context):
        """Configure CmdChannel for your server."""

    @cmdchannelconfig.command(name="enable", aliases=["activate"], usage="<true_or_false>")
    async def activatecmdchannel(self, ctx: commands.Context, state: bool):
        """Enable or disable CommandChannel.

        Use `True` (Or `yes`) to enable or `False` (or `no`) to disable.
        """
        if not ctx.author.id == ctx.guild.owner.id:
            await ctx.send(_("Only the owner of this server can access these commands!").format(**locals()))
            return

        config = await self.config.guild(ctx.guild).all()

        actual_state_enabled = config["enabled_cmdchannel"]
        if actual_state_enabled is state:
            await ctx.send(_("CommandChannel is already set on {state}.").format(**locals()))
            return

        await self.config.guild(ctx.guild).enabled_cmdchannel.set(state)
        await ctx.send(_("CommandChannel state registered: {state}.").format(**locals()))

    @cmdchannelconfig.command(name="confirmation", aliases=["confirm"], usage="<true_or_false>")
    async def confirmationcmdchannel(self, ctx: commands.Context, state: bool):
        """Enable or disable confirmation.

        Use `True` (Or `yes`) to enable or `False` (or `no`) to disable.
        """
        if not ctx.author.id == ctx.guild.owner.id:
            await ctx.send(_("Only the owner of this server can access these commands!").format(**locals()))
            return

        config = await self.config.guild(ctx.guild).all()

        actual_state_confirmation = config["confirmation_cmdchannel"]
        if actual_state_confirmation is state:
            await ctx.send(_("Confirmation is already set on {state}.").format(**locals()))
            return

        await self.config.guild(ctx.guild).confirmation_cmdchannel.set(state)
        await ctx.send(f"Confirmation state registered: {state}.")

    @cmdchannelconfig.command(name="delete", aliases=["deletemessage"], usage="<true_or_false>")
    async def deletemessagecmdchannel(self, ctx: commands.Context, state: bool):
        """Enable or disable message delete.

        Use `True` (Or `yes`) to enable or `False` (or `no`) to disable.
        """
        if not ctx.author.id == ctx.guild.owner.id:
            await ctx.send(_("Only the owner of this server can access these commands!").format(**locals()))
            return

        config = await self.config.guild(ctx.guild).all()

        actual_state_delete = config["deletemessage_cmdchannel"]
        if actual_state_delete is state:
            await ctx.send(_("Message delete is already set on {state}.").format(**locals()))
            return

        await self.config.guild(ctx.guild).deletemessage_cmdchannel.set(state)
        await ctx.send(_("Message delete state registered: {state}.").format(**locals()))

    @cmdchannelconfig.command(name="information", aliases=["info"], usage="<true_or_false>")
    async def informationcmdchannel(self, ctx: commands.Context, state: bool):
        """Enable or disable information message.

        Use `True` (Or `yes`) to enable or `False` (or `no`) to disable.
        """
        if not ctx.author.id == ctx.guild.owner.id:
            await ctx.send(_("Only the owner of this server can access these commands!").format(**locals()))
            return

        config = await self.config.guild(ctx.guild).all()

        actual_state_information = config["informationmessage_cmdchannel"]
        if actual_state_information is state:
            await ctx.send(_("Information message is already set on {state}.").format(**locals()))
            return

        await self.config.guild(ctx.guild).informationmessage_cmdchannel.set(state)
        await ctx.send(_("Information message state registered: {state}.").format(**locals()))

    @commands.guildowner_or_permissions(administrator=True)
    @configuration.group(name="cmduser", aliases=["usercmd"])
    async def cmduserconfig(self, ctx: commands.Context):
        """Configure CmdUser for your server."""

    @cmduserconfig.command(name="enable", aliases=["activate"], usage="<true_or_false>")
    async def activatecmduser(self, ctx: commands.Context, state: bool):
        """Enable or disable CommandUser.

        Use `True` (Or `yes`) to enable or `False` (or `no`) to disable.
        """
        if not ctx.author.id == ctx.guild.owner.id:
            await ctx.send(_("Only the owner of this server can access these commands!").format(**locals()))
            return

        config = await self.config.guild(ctx.guild).all()

        actual_state_enabled = config["enabled_cmduser"]
        if actual_state_enabled is state:
            await ctx.send(_("CommandUser is already set on {state}.").format(**locals()))
            return

        await self.config.guild(ctx.guild).enabled_cmduser.set(state)
        await ctx.send(_("CommandUser state registered: {state}.").format(**locals()))

    @cmduserconfig.command(name="confirmation", aliases=["confirm"], usage="<true_or_false>")
    async def confirmationcmduser(self, ctx: commands.Context, state: bool):
        """Enable or disable confirmation.

        Use `True` (Or `yes`) to enable or `False` (or `no`) to disable.
        """
        if not ctx.author.id == ctx.guild.owner.id:
            await ctx.send(_("Only the owner of this server can access these commands!").format(**locals()))
            return

        config = await self.config.guild(ctx.guild).all()

        actual_state_confirmation = config["confirmation_cmduser"]
        if actual_state_confirmation is state:
            await ctx.send(_("CommandUser confirmation is already set on {state}.").format(**locals()))
            return

        await self.config.guild(ctx.guild).confirmation_cmduser.set(state)
        await ctx.send(_("CommandUser confirmation state registered: {state}.").format(**locals()))

    @cmduserconfig.command(name="delete", aliases=["deletemessage"], usage="<true_or_false>")
    async def deletemessagecmduser(self, ctx: commands.Context, state: bool):
        """Enable or disable message delete.

        Use `True` (Or `yes`) to enable or `False` (or `no`) to disable.
        """
        if not ctx.author.id == ctx.guild.owner.id:
            await ctx.send(_("Only the owner of this server can access these commands!").format(**locals()))
            return

        config = await self.config.guild(ctx.guild).all()

        actual_state_delete = config["deletemessage_cmduser"]
        if actual_state_delete is state:
            await ctx.send(_("CommandUser message delete is already set on {state}.").format(**locals()))
            return

        await self.config.guild(ctx.guild).deletemessage_cmduser.set(state)
        await ctx.send(_("CommandUser message delete state registered: {state}.").format(**locals()))

    @cmduserconfig.command(name="information", aliases=["info"], usage="<true_or_false>")
    async def informationcmduser(self, ctx: commands.Context, state: bool):
        """Enable or disable information message.

        Use `True` (Or `yes`) to enable or `False` (or `no`) to disable.
        """
        if not ctx.author.id == ctx.guild.owner.id:
            await ctx.send(_("Only the owner of this server can access these commands!").format(**locals()))
            return

        config = await self.config.guild(ctx.guild).all()

        actual_state_information = config["informationmessage_cmduser"]
        if actual_state_information is state:
            await ctx.send(_("CommandUser information message is already set on {state}.").format(**locals()))
            return

        await self.config.guild(ctx.guild).informationmessage_cmduser.set(state)
        await ctx.send(_("CommandUser information message state registered: {state}.").format(**locals()))

    @commands.guildowner_or_permissions(administrator=True)
    @configuration.group(name="cmduserchannel", aliases=["userchannelcmd"])
    async def cmduserchannelconfig(self, ctx: commands.Context):
        """Configure CmdUserChannel for your server."""

    @cmduserchannelconfig.command(name="enable", aliases=["activate"], usage="<true_or_false>")
    async def activatecmduserchannel(self, ctx: commands.Context, state: bool):
        """Enable or disable CommandUserChannel.

        Use `True` (Or `yes`) to enable or `False` (or `no`) to disable.
        """
        if not ctx.author.id == ctx.guild.owner.id:
            await ctx.send(_("Only the owner of this server can access these commands!").format(**locals()))
            return

        config = await self.config.guild(ctx.guild).all()

        actual_state_enabled = config["enabled_cmduserchannel"]
        if actual_state_enabled is state:
            await ctx.send(_("CommandUserChannel is already set on {state}.").format(**locals()))
            return

        await self.config.guild(ctx.guild).enabled_cmduserchannel.set(state)
        await ctx.send(_("CommandUserChannel state registered: {state}.").format(**locals()))

    @cmduserchannelconfig.command(name="confirmation", aliases=["confirm"], usage="<true_or_false>")
    async def confirmationcmduserchannel(self, ctx: commands.Context, state: bool):
        """Enable or disable confirmation.

        Use `True` (Or `yes`) to enable or `False` (or `no`) to disable.
        """
        if not ctx.author.id == ctx.guild.owner.id:
            await ctx.send(_("Only the owner of this server can access these commands!").format(**locals()))
            return

        config = await self.config.guild(ctx.guild).all()

        actual_state_confirmation = config["confirmation_cmduserchannel"]
        if actual_state_confirmation is state:
            await ctx.send(_("CommandUserChannel confirmation is already set on {state}."))
            return

        await self.config.guild(ctx.guild).confirmation_cmduserchannel.set(state)
        await ctx.send(_("CommandUserChannel confirmation state registered: {state}.").format(**locals()))

    @cmduserchannelconfig.command(name="delete", aliases=["deletemessage"], usage="<true_or_false>")
    async def deletemessagecmduserchannel(self, ctx: commands.Context, state: bool):
        """Enable or disable message delete.

        Use `True` (Or `yes`) to enable or `False` (or `no`) to disable.
        """
        if not ctx.author.id == ctx.guild.owner.id:
            await ctx.send(_("Only the owner of this server can access these commands!").format(**locals()))
            return

        config = await self.config.guild(ctx.guild).all()

        actual_state_delete = config["deletemessage_cmduserchannel"]
        if actual_state_delete is state:
            await ctx.send(_("CommandUserChannel message delete is already set on {state}.").format(**locals()))
            return

        await self.config.guild(ctx.guild).deletemessage_cmduserchannel.set(state)
        await ctx.send(_("CommandUserChannel message delete state registered: {state}.").format(**locals()))

    @cmduserchannelconfig.command(name="information", aliases=["info"], usage="<true_or_false>")
    async def informationcmduserchannel(self, ctx: commands.Context, state: bool):
        """Enable or disable information message.

        Use `True` (Or `yes`) to enable or `False` (or `no`) to disable.
        """
        if not ctx.author.id == ctx.guild.owner.id:
            await ctx.send(_("Only the owner of this server can access these commands!").format(**locals()))
            return

        config = await self.config.guild(ctx.guild).all()

        actual_state_information = config["informationmessage_cmduserchannel"]
        if actual_state_information is state:
            await ctx.send(_("CommandUserChannel information message is already set on {state}.").format(**locals()))
            return

        await self.config.guild(ctx.guild).informationmessage_cmduserchannel.set(state)
        await ctx.send(_("CommandUserChannel information message state registered: {state}.").format(**locals()))

    async def member_can_run(self, ctx: commands.Context) -> bool:
        """Check if a user can run a command.
        This will take the current context into account, such as the
        server and text channel.
        https://github.com/Cog-Creators/Red-DiscordBot/blob/V3/release/3.0.0/redbot/cogs/permissions/permissions.py
        """
        command = ctx.message.content.replace(ctx.prefix, "")
        com = ctx.bot.get_command(command)
        if com is None:
            return False
        else:
            try:
                testcontext = await ctx.bot.get_context(ctx.message, cls=commands.Context)
                to_check = [*reversed(com.parents)] + [com]
                can = False
                for cmd in to_check:
                    can = await cmd.can_run(testcontext)
                    if can is False:
                        break
            except (commands.CheckFailure, commands.DisabledCommand):
                can = False
        return can
from .AAA3A_utils.cogsutils import CogsUtils # isort:skip
import typing
import discord
from redbot.core import checks, commands
from .helpers import embed_from_msg
from redbot.core.utils.tunnel import Tunnel

if CogsUtils().is_dpy2: # To remove
    setattr(commands, 'Literal', typing.Literal)

# Credits:
# Thanks to TrustyJAID's Backup for starting the command to list the latest source channel messages! (https://github.com/TrustyJAID/Trusty-cogs/tree/master/backup)
# Thanks to QuoteTools from SimBad for the embed!
# Thanks to Speak from @epic guy for the webhooks! (https://github.com/npc203/npc-cogs/tree/main/speak)
# Thanks to Say from LaggronsDumb for the attachments in the single messages and webhooks! (https://github.com/laggron42/Laggrons-Dumb-Cogs/tree/v3/say)
# Thanks to CruxCraft on GitHub for the idea of allowing channels from other servers! (https://github.com/AAA3A-AAA3A/AAA3A-cogs/issues/1)
# Thanks to @epic guy on Discord for the basic syntax (command groups, commands) and also commands (await ctx.send, await ctx.author.send, await ctx.message.delete())!
# Thanks to the developers of the cogs I added features to as it taught me how to make a cog! (Chessgame by WildStriker, Captcha by Kreusada, Speak by Epic guy and Rommer by Dav)
# Thanks to all the people who helped me with some commands in the #coding channel of the redbot support server!

def _(untranslated: str):
    return untranslated

class TextChannelGuildConverter(discord.ext.commands.TextChannelConverter):
    """Similar to d.py's TextChannelConverter but only returns if we have already
    passed our hierarchy checks and find in all guilds.
    """

    async def convert(self, ctx: commands.Context, argument: str) -> discord.TextChannel:
        try:
            channel: discord.TextChannel = await discord.ext.commands.TextChannelConverter().convert(ctx, argument)
        except Exception:
            channel = None
        if channel is not None:
            if channel.guild == ctx.guild:
                if not ctx.author.id in ctx.bot.owner_ids and not channel.permissions_for(ctx.author).manage_guild:
                    raise discord.ext.commands.BadArgument(_("You must have permissions to manage this server to use this command.").format(**locals()))
                permissions = channel.permissions_for(channel.guild.me)
                if not permissions.read_messages or not permissions.read_message_history or not permissions.send_messages or not permissions.view_channel:
                    raise discord.ext.commands.BadArgument(_("I need to have all the following permissions for the {channel.mention} channel ({channel.id}).\n`read_messages`, `read_message_history`, `send_messages` and `view_channel`.").format(**locals()))
                return channel
        if not ctx.author.id in ctx.bot.owner_ids:
            raise discord.ext.commands.BadArgument(_("This channel cannot be found.").format(**locals()))
        try:
            argument = int(argument)
        except NameError:
            pass
        channel: discord.TextChannel = ctx.bot.get_channel(argument)
        if channel is None:
            raise discord.ext.commands.BadArgument(_("This channel cannot be found. If this channel is in another Discord server, please give the id of a valid text channel.").format(**locals()))
        if not isinstance(channel, discord.TextChannel):
            raise discord.ext.commands.BadArgument(_("The specified channel must be a text channel in a server where the bot is located.").format(**locals()))
        permissions = channel.permissions_for(channel.guild.me)
        if not permissions.read_messages or not permissions.read_message_history or not permissions.send_messages or not permissions.view_channel:
            raise discord.ext.commands.BadArgument(_("I need to have all the following permissions for the {channel.name} channel ({channel.id}) in {destination.guild.name} ({destination.guild.id}).\n`read_messages`, `read_message_history`, `send_messages` and `view_channel`.").format(**locals()))
        return channel

class TransferChannel(commands.Cog):
    """A cog to transfer all messages channel in a other channel!"""

    def __init__(self, bot):
        self.bot = bot
        self.cache = {}

        self.cogsutils = CogsUtils(cog=self)
        self.cogsutils._setup()

    @commands.command(aliases=["channeltransfer"])
    @checks.admin_or_permissions(manage_guild=True)
    @commands.guild_only()
    async def transferchannel(self, ctx: commands.Context, source: TextChannelGuildConverter, destination: TextChannelGuildConverter, limit: int, way: commands.Literal["embed", "webhook", "message"]):
        """
        Transfer all messages channel in a other channel. This might take a long time.
        You can specify the id of a channel from another server.

        `source` is partial name or ID of the source channel
        `destination` is partial name or ID of the destination channel
        `way` is the used way
          - `embed` Do you want to transfer the message as an embed?
          - `webhook` Do you want to send the messages with webhooks (name and avatar of the original author)?
          - `message`Do you want to transfer the message as a simple message?
        """
        permissions = destination.permissions_for(destination.guild.me)
        if way == "embed":
            if not permissions.embed_links:
                await ctx.send(_("I need to have all the following permissions for the {destination.name} channel ({destination.id}) in {destination.guild.name} ({destination.guild.id}).\n`embed_links`.").format(**locals()))
                return
        elif way == "webhook":
            if not permissions.manage_guild:
                await ctx.send(_("I need to have all the following permissions for the {destination.name} channel ({destination.id}) in {destination.guild.name} ({destination.guild.id}).\n`manage_channels`").format(**locals()))
                return
        count = 0
        if self.cogsutils.is_dpy2:
            msgList = [message async for message in source.history(limit=limit+1, oldest_first=False)]
        else:
            msgList = await source.history(limit=limit+1, oldest_first=False).flatten()
        msgList.reverse()
        for message in msgList:
            if not message.id == ctx.message.id:
                count += 1
                files = await Tunnel.files_from_attatch(message)
                if way == "embed":
                    em = embed_from_msg(message, self.cogsutils)
                    await destination.send(embed=em)
                elif way == "webhook":
                    hook = await self.cogsutils.get_hook(destination)
                    await hook.send(
                        username=message.author.display_name,
                        avatar_url=message.author.display_avatar if self.cogsutils.is_dpy2 else message.author.avatar_url,
                        content=message.content,
                        files=files,
                    )
                elif way == "message":
                    iso_format = message.created_at.isoformat()
                    msg1 = "\n".join(
                        [
                            _("**Author:** {message.author}({message.author.id}").format(**locals()),
                            _("**Channel:** <#{message.channel.id}>").format(**locals()),
                            _("**Time(UTC):** {isoformat}").format(**locals())
                        ]
                    )
                    if len(msg1) + len(message.content) < 2000:
                        await ctx.send(msg1 + "\n\n" + message.content, files=files)
                    else:
                        await ctx.send(msg1)
                        await ctx.send(message.content, files=files)
        await ctx.send(_("{count} messages transfered from {source.mention} to {destination.mention}").format(**locals()))
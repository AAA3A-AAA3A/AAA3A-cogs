from .AAA3A_utils.cogsutils import CogsUtils  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
from redbot.core.bot import Red  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import chat_exporter
import io

if CogsUtils().is_dpy2:
    from redbot.core.commands import RawUserIdConverter

# Credits:
# Thanks to Red's `Cleanup` cog for the converters and help with the message retrieval function! (https://github.com/Cog-Creators/Red-DiscordBot/blob/V3/develop/redbot/cogs/cleanup/converters.py#L12)
# Thanks to @epic guy on Discord for the basic syntax (command groups, commands) and also commands (await ctx.send, await ctx.author.send, await ctx.message.delete())!
# Thanks to the developers of the cogs I added features to as it taught me how to make a cog! (Chessgame by WildStriker, Captcha by Kreusada, Speak by Epic guy and Rommer by Dav)
# Thanks to all the people who helped me with some commands in the #coding channel of the redbot support server!

_ = Translator("ExportChannel", __file__)

@cog_i18n(_)
class ExportChannel(commands.Cog):
    """A cog to export all or part of a channel's messages to an html file!"""

    def __init__(self, bot: Red):
        self.bot: Red = bot

        self.cogsutils = CogsUtils(cog=self)
        self.cogsutils._setup()

    async def get_messages(self, channel: discord.TextChannel, number: typing.Optional[int]=None, limit: typing.Optional[int]=None, before: typing.Optional[discord.Message]=None, after: typing.Optional[discord.Message]=None, user_id: typing.Optional[int]=None, bot: typing.Optional[bool]=None):
        messages = []
        async for message in channel.history(limit=limit, before=before, after=after, oldest_first=False):
            if user_id is not None:
                if not message.author.id == user_id:
                    continue
            if bot is not None:
                if not message.author.bot == bot:
                    continue
            messages.append(message)
            if number is not None and number <= len(messages):
                break
        return messages

    @commands.admin_or_permissions(administrator=True)
    @commands.guild_only()
    @commands.group(name="exportchannel")
    async def exportchannel(self, ctx: commands.Context):
        """Commands for export all or part of a channel's messages to an html file."""

    @exportchannel.command()
    async def all(self, ctx: commands.Context, channel: typing.Optional[discord.TextChannel]=None):
        """Export all of a channel's messages to an html file.

        Please note: all attachments and user avatars are saved with the Discord link in this file.
        Remember that exporting other users' messages from Discord does not respect the TOS.
        """
        async with ctx.typing():
            if channel is None:
                channel = ctx.channel
            if not self.cogsutils.check_permissions_for(channel=channel, user=ctx.me, check=["view_channel", "read_messages", "read_message_history"]):
                await ctx.send(_("Sorry, I can't read the content of the messages in {channel.mention} ({channel.id}).").format())
                return
            messages = await self.get_messages(channel=channel)
            messages = [message for message in messages if not message.id == ctx.message.id]
            count_messages = len(messages)
            if count_messages == 0:
                await ctx.send(_("Sorry. I could not find any message.").format(**locals()))
                return
            transcript = await chat_exporter.raw_export(channel=channel, messages=messages, tz_info="UTC", guild=channel.guild, bot=ctx.bot)
            file = discord.File(io.BytesIO(transcript.encode()),
                                filename=f"transcript-{channel.id}.html")
        await ctx.send(_("Here is the html file of the transcript of all the messages in the channel {channel.mention} ({channel.id}).\nPlease note: all attachments and user avatars are saved with the Discord link in this file.\nThere are {count_messages} exported messages.\nRemember that exporting other users' messages from Discord does not respect the TOS.").format(**locals()), file=file)
        await ctx.tick()

    @exportchannel.command()
    async def messages(self, ctx: commands.Context, channel: typing.Optional[discord.TextChannel], limit: int):
        """Export part of a channel's messages to an html file.

        Specify the number of messages since the end of the channel.
        Please note: all attachments and user avatars are saved with the Discord link in this file.
        Remember that exporting other users' messages from Discord does not respect the TOS.
        """
        async with ctx.typing():
            if channel is None:
                channel = ctx.channel
            if not self.cogsutils.check_permissions_for(channel=channel, user=ctx.me, check=["view_channel", "read_messages", "read_message_history"]):
                await ctx.send(_("Sorry, I can't read the content of the messages in {channel.mention} ({channel.id}).").format())
                return
            messages = await self.get_messages(channel=channel, limit=limit if not channel == ctx.channel else limit + 1)
            messages = [message for message in messages if not message.id == ctx.message.id]
            count_messages = len(messages)
            if count_messages == 0:
                await ctx.send(_("Sorry. I could not find any message.").format(**locals()))
                return
            transcript = await chat_exporter.raw_export(channel=channel, messages=messages, tz_info="UTC", guild=channel.guild, bot=ctx.bot)
            file = discord.File(io.BytesIO(transcript.encode()),
                                filename=f"transcript-{channel.id}.html")
        await ctx.send(_("Here is the html file of the transcript of part the messages in the channel {channel.mention} ({channel.id}).\nThere are {count_messages} exported messages.\nPlease note: all attachments and user avatars are saved with the Discord link in this file.\nRemember that exporting other users' messages from Discord does not respect the TOS.").format(**locals()), file=file)
        await ctx.tick()

    @exportchannel.command()
    async def before(self, ctx: commands.Context, channel: typing.Optional[discord.TextChannel], before: discord.Message):
        """Export part of a channel's messages to an html file.

        Specify the before message (id or link).
        Please note: all attachments and user avatars are saved with the Discord link in this file.
        Remember that exporting other users' messages from Discord does not respect the TOS.
        """
        async with ctx.typing():
            if channel is None:
                channel = ctx.channel
            if not self.cogsutils.check_permissions_for(channel=channel, user=ctx.me, check=["view_channel", "read_messages", "read_message_history"]):
                await ctx.send(_("Sorry, I can't read the content of the messages in {channel.mention} ({channel.id}).").format())
                return
            messages = await self.get_messages(channel=channel, before=before)
            messages = [message for message in messages if not message.id == ctx.message.id]
            count_messages = len(messages)
            transcript = await chat_exporter.raw_export(channel=channel, messages=messages, tz_info="UTC", guild=channel.guild, bot=ctx.bot)
            file = discord.File(io.BytesIO(transcript.encode()),
                                filename=f"transcript-{channel.id}.html")
        await ctx.send(_("Here is the html file of the transcript of part the messages in the channel {channel.mention} ({channel.id}).\nThere are {count_messages} exported messages.\nPlease note: all attachments and user avatars are saved with the Discord link in this file.\nRemember that exporting other users' messages from Discord does not respect the TOS.").format(**locals()), file=file)
        await ctx.tick()

    @exportchannel.command()
    async def after(self, ctx: commands.Context, channel: typing.Optional[discord.TextChannel], after: discord.Message):
        """Export part of a channel's messages to an html file.

        Specify the after message (id or link).
        Please note: all attachments and user avatars are saved with the Discord link in this file.
        Remember that exporting other users' messages from Discord does not respect the TOS.
        """
        async with ctx.typing():
            if channel is None:
                channel = ctx.channel
            if not self.cogsutils.check_permissions_for(channel=channel, user=ctx.me, check=["view_channel", "read_messages", "read_message_history"]):
                await ctx.send(_("Sorry, I can't read the content of the messages in {channel.mention} ({channel.id}).").format())
                return
            messages = await self.get_messages(channel=channel, after=after)
            messages = [message for message in messages if not message.id == ctx.message.id]
            count_messages = len(messages)
            if count_messages == 0:
                await ctx.send(_("Sorry. I could not find any message.").format(**locals()))
                return
            transcript = await chat_exporter.raw_export(channel=channel, messages=messages, tz_info="UTC", guild=channel.guild, bot=ctx.bot)
            file = discord.File(io.BytesIO(transcript.encode()),
                                filename=f"transcript-{channel.id}.html")
        await ctx.send(_("Here is the html file of the transcript of part the messages in the channel {channel.mention} ({channel.id}).\nThere are {count_messages} exported messages.\nPlease note: all attachments and user avatars are saved with the Discord link in this file.\nRemember that exporting other users' messages from Discord does not respect the TOS.").format(**locals()), file=file)
        await ctx.tick()

    @exportchannel.command()
    async def between(self, ctx: commands.Context, channel: typing.Optional[discord.TextChannel], before: discord.Message, after: discord.Message):
        """Export part of a channel's messages to an html file.

        Specify the between messages (id or link).
        Please note: all attachments and user avatars are saved with the Discord link in this file.
        Remember that exporting other users' messages from Discord does not respect the TOS.
        """
        async with ctx.typing():
            if channel is None:
                channel = ctx.channel
            if not self.cogsutils.check_permissions_for(channel=channel, user=ctx.me, check=["view_channel", "read_messages", "read_message_history"]):
                await ctx.send(_("Sorry, I can't read the content of the messages in {channel.mention} ({channel.id}).").format())
                return
            messages = await self.get_messages(channel=channel, before=before, after=after)
            messages = [message for message in messages if not message.id == ctx.message.id]
            count_messages = len(messages)
            if count_messages == 0:
                await ctx.send(_("Sorry. I could not find any message.").format(**locals()))
                return
            transcript = await chat_exporter.raw_export(channel=channel, messages=messages, tz_info="UTC", guild=channel.guild, bot=ctx.bot)
            file = discord.File(io.BytesIO(transcript.encode()),
                                filename=f"transcript-{channel.id}.html")
        await ctx.send(_("Here is the html file of the transcript of part the messages in the channel {channel.mention} ({channel.id}).\nThere are {count_messages} exported messages.\nPlease note: all attachments and user avatars are saved with the Discord link in this file.\nRemember that exporting other users' messages from Discord does not respect the TOS.").format(**locals()), file=file)
        await ctx.tick()

    if CogsUtils().is_dpy2:
        @exportchannel.command()
        async def user(self, ctx: commands.Context, channel: typing.Optional[discord.TextChannel], user: typing.Union[discord.Member, RawUserIdConverter]):
            """Export part of a channel's messages to an html file.

            Specify the member (id, name or mention).
            Please note: all attachments and user avatars are saved with the Discord link in this file.
            Remember that exporting other users' messages from Discord does not respect the TOS.
            """
            async with ctx.typing():
                if channel is None:
                    channel = ctx.channel
                if not self.cogsutils.check_permissions_for(channel=channel, user=ctx.me, check=["view_channel", "read_messages", "read_message_history"]):
                    await ctx.send(_("Sorry, I can't read the content of the messages in {channel.mention} ({channel.id}).").format())
                    return
                messages = await self.get_messages(channel=channel, user_id=user.id if isinstance(user, discord.Member) else user)
                messages = [message for message in messages if not message.id == ctx.message.id]
                count_messages = len(messages)
                if count_messages == 0:
                    await ctx.send(_("Sorry. I could not find any message.").format(**locals()))
                    return
                transcript = await chat_exporter.raw_export(channel=channel, messages=messages, tz_info="UTC", guild=channel.guild, bot=ctx.bot)
                file = discord.File(io.BytesIO(transcript.encode()),
                                    filename=f"transcript-{channel.id}.html")
            await ctx.send(_("Here is the html file of the transcript of part the messages in the channel {channel.mention} ({channel.id}).\nThere are {count_messages} exported messages.\nPlease note: all attachments and user avatars are saved with the Discord link in this file.\nRemember that exporting other users' messages from Discord does not respect the TOS.").format(**locals()), file=file)
            await ctx.tick()

    @exportchannel.command()
    async def bot(self, ctx: commands.Context, channel: typing.Optional[discord.TextChannel], bot: typing.Optional[bool]=True):
        """Export part of a channel's messages to an html file.

        Specify the bool option.
        Please note: all attachments and user avatars are saved with the Discord link in this file.
        Remember that exporting other users' messages from Discord does not respect the TOS.
        """
        async with ctx.typing():
            if channel is None:
                channel = ctx.channel
            if not self.cogsutils.check_permissions_for(channel=channel, user=ctx.me, check=["view_channel", "read_messages", "read_message_history"]):
                await ctx.send(_("Sorry, I can't read the content of the messages in {channel.mention} ({channel.id}).").format())
                return
            messages = await self.get_messages(channel=channel, bot=bot)
            messages = [message for message in messages if not message.id == ctx.message.id]
            count_messages = len(messages)
            if count_messages == 0:
                await ctx.send(_("Sorry. I could not find any message.").format(**locals()))
                return
            transcript = await chat_exporter.raw_export(channel=channel, messages=messages, tz_info="UTC", guild=channel.guild, bot=ctx.bot)
            file = discord.File(io.BytesIO(transcript.encode()),
                                filename=f"transcript-{channel.id}.html")
        await ctx.send(_("Here is the html file of the transcript of part the messages in the channel {channel.mention} ({channel.id}).\nThere are {count_messages} exported messages.\nPlease note: all attachments and user avatars are saved with the Discord link in this file.\nRemember that exporting other users' messages from Discord does not respect the TOS.").format(**locals()), file=file)
        await ctx.tick()
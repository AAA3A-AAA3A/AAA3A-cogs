from .AAA3A_utils import Cog, CogsUtils  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
from redbot.core.bot import Red  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import io

import chat_exporter

# Credits:
# General repo credits.
# Thanks to Red's Cleanup cog for the converters and help with the message retrieval function! (https://github.com/Cog-Creators/Red-DiscordBot/blob/V3/develop/redbot/cogs/cleanup/converters.py#L12)

_ = Translator("ExportChannel", __file__)

if CogsUtils().is_dpy2:
    from functools import partial

    hybrid_command = partial(commands.hybrid_command, with_app_command=False)
    hybrid_group = partial(commands.hybrid_group, with_app_command=False)
else:
    hybrid_command = commands.command
    hybrid_group = commands.group

RESULT_MESSAGE = "Here is the transcript's html file of the messages in the channel {channel.mention} ({channel.id}).\nPlease note: all attachments and user avatars are saved with the Discord link in this file.\nThere are {count_messages} exported messages.\nRemember that exporting other users' messages from Discord does not respect the TOS."
LINK_MESSAGE = "[Click here to view the transcript.]({url})"


@cog_i18n(_)
class ExportChannel(Cog):
    """A cog to export all or part of a channel's messages to an html file!"""

    def __init__(self, bot: Red) -> None:
        self.bot: Red = bot

        self.cogsutils: CogsUtils = CogsUtils(cog=self)

    async def check_channel(self, ctx: commands.Context, channel: discord.TextChannel) -> None:
        if not self.cogsutils.check_permissions_for(
            channel=channel,
            user=ctx.me,
            check=["view_channel", "read_messages", "read_message_history"],
        ):
            raise commands.UserFeedbackCheckFailure(
                _(
                    "Sorry, I can't read the content of the messages in {channel.mention} ({channel.id})."
                ).format()
            )

    async def get_messages(
        self,
        ctx: commands.Context,
        channel: discord.TextChannel,
        number: typing.Optional[int] = None,
        limit: typing.Optional[int] = None,
        before: typing.Optional[discord.Message] = None,
        after: typing.Optional[discord.Message] = None,
        user_id: typing.Optional[int] = None,
        bot: typing.Optional[bool] = None,
    ) -> typing.Tuple[int, typing.List[discord.Message]]:
        messages = []
        async for message in channel.history(
            limit=limit, before=before, after=after, oldest_first=False
        ):
            if user_id is not None and message.author.id != user_id:
                continue
            if bot is not None and message.author.bot != bot:
                continue
            messages.append(message)
            if number is not None and number <= len(messages):
                break
        messages = [message for message in messages if message.id != ctx.message.id]
        count_messages = len(messages)
        if count_messages == 0:
            raise commands.UserFeedbackCheckFailure(_("Sorry. I could not find any message."))
        return count_messages, messages

    async def export_messages(
        self, ctx: commands.Context, channel: discord.TextChannel, **kwargs
    ) -> typing.Union[int, typing.List[discord.Message], discord.File]:
        count_messages, messages = await self.get_messages(ctx, channel=channel, **kwargs)
        if self.cogsutils.is_dpy2:
            class Transcript(chat_exporter.construct.transcript.TranscriptDAO):
                @classmethod
                async def export(
                    cls,
                    channel: discord.TextChannel,
                    messages: typing.List[discord.Message],
                    tz_info="UTC",
                    guild: typing.Optional[discord.Guild] = None,
                    bot: typing.Optional[discord.Client] = None,
                    military_time: typing.Optional[bool] = False,
                    fancy_times: typing.Optional[bool] = True,
                    support_dev: typing.Optional[bool] = True
                ):
                    self = cls(
                        channel=channel,
                        limit=None,
                        messages=messages,
                        pytz_timezone=tz_info,
                        military_time=military_time,
                        fancy_times=fancy_times,
                        before=None,
                        after=None,
                        support_dev=support_dev,
                        bot=bot
                    )
                    if not self.after:
                        self.messages.reverse()
                    return (await self.build_transcript()).html
            # transcript = await chat_exporter.raw_export(
            #     channel=channel,
            #     messages=messages,
            #     tz_info="UTC",
            #     guild=channel.guild,
            #     bot=ctx.bot,
            # )
            transcript = await Transcript.export(
                channel=channel,
                messages=messages,
                tz_info="UTC",
                guild=channel.guild,
                bot=ctx.bot,
            )
        else:
            transcript = await chat_exporter.raw_export(
                channel=channel, messages=messages, guild=channel.guild
            )
        file = discord.File(
            io.BytesIO(transcript.encode()), filename=f"transcript-{channel.id}.html"
        )
        return count_messages, messages, file

    @commands.guild_only()
    @commands.guildowner_or_permissions(administrator=True)
    @hybrid_group(name="exportchannel", aliases=["exportmessages"])
    async def exportchannel(self, ctx: commands.Context) -> None:
        """Commands for export all or part of a channel's messages to an html file."""

    @exportchannel.command()
    async def all(
        self, ctx: commands.Context, channel: typing.Optional[discord.TextChannel] = None
    ) -> None:
        """Export all of a channel's messages to an html file.

        Please note: all attachments and user avatars are saved with the Discord link in this file.
        Remember that exporting other users' messages from Discord does not respect the TOS.
        """
        if channel is None:
            channel = ctx.channel
        await self.check_channel(ctx, channel)
        count_messages, messages, file = await self.export_messages(ctx, channel=channel)
        message = await ctx.send(
            _(RESULT_MESSAGE).format(channel=channel, count_messages=count_messages), file=file
        )
        url = f"https://mahto.id/chat-exporter?url={message.attachments[0].url}"
        embed = discord.Embed(
            title="Transcript Link",
            description=LINK_MESSAGE.format(url=url),
            colour=discord.Colour.green(),
        )
        if self.cogsutils.is_dpy2:
            view = discord.ui.View()
            view.add_item(discord.ui.Button(style=discord.ButtonStyle.url, label="View transcript", url=url))
            await message.edit(embed=embed, view=view)
        else:
            await message.edit(embed=embed)

    @exportchannel.command()
    async def messages(
        self, ctx: commands.Context, channel: typing.Optional[discord.TextChannel], limit: int
    ) -> None:
        """Export part of a channel's messages to an html file.

        Specify the number of messages since the end of the channel.
        Please note: all attachments and user avatars are saved with the Discord link in this file.
        Remember that exporting other users' messages from Discord does not respect the TOS.
        """
        if channel is None:
            channel = ctx.channel
        await self.check_channel(ctx, channel)
        count_messages, messages, file = await self.export_messages(
            ctx,
            channel=channel,
            limit=limit if channel != ctx.channel else limit + 1,
        )
        message = await ctx.send(
            _(RESULT_MESSAGE).format(channel=channel, count_messages=count_messages), file=file
        )
        url = f"https://mahto.id/chat-exporter?url={message.attachments[0].url}"
        embed = discord.Embed(
            title="Transcript Link",
            description=LINK_MESSAGE.format(url=url),
            colour=discord.Colour.green(),
        )
        if self.cogsutils.is_dpy2:
            view = discord.ui.View()
            view.add_item(discord.ui.Button(style=discord.ButtonStyle.url, label="View transcript", url=url))
            await message.edit(embed=embed, view=view)
        else:
            await message.edit(embed=embed)

    @exportchannel.command()
    async def before(
        self,
        ctx: commands.Context,
        channel: typing.Optional[discord.TextChannel],
        before: discord.Message,
    ) -> None:
        """Export part of a channel's messages to an html file.

        Specify the before message (id or link).
        Please note: all attachments and user avatars are saved with the Discord link in this file.
        Remember that exporting other users' messages from Discord does not respect the TOS.
        """
        if channel is None:
            channel = ctx.channel
        await self.check_channel(ctx, channel)
        count_messages, messages, file = await self.export_messages(
            ctx, channel=channel, before=before
        )
        message = await ctx.send(
            _(RESULT_MESSAGE).format(channel=channel, count_messages=count_messages), file=file
        )
        url = f"https://mahto.id/chat-exporter?url={message.attachments[0].url}"
        embed = discord.Embed(
            title="Transcript Link",
            description=LINK_MESSAGE.format(url=url),
            colour=discord.Colour.green(),
        )
        if self.cogsutils.is_dpy2:
            view = discord.ui.View()
            view.add_item(discord.ui.Button(style=discord.ButtonStyle.url, label="View transcript", url=url))
            await message.edit(embed=embed, view=view)
        else:
            await message.edit(embed=embed)

    @exportchannel.command()
    async def after(
        self,
        ctx: commands.Context,
        channel: typing.Optional[discord.TextChannel],
        after: discord.Message,
    ) -> None:
        """Export part of a channel's messages to an html file.

        Specify the after message (id or link).
        Please note: all attachments and user avatars are saved with the Discord link in this file.
        Remember that exporting other users' messages from Discord does not respect the TOS.
        """
        if channel is None:
            channel = ctx.channel
        await self.check_channel(ctx, channel)
        count_messages, messages, file = await self.export_messages(
            ctx, channel=channel, after=after
        )
        message = await ctx.send(
            _(RESULT_MESSAGE).format(channel=channel, count_messages=count_messages), file=file
        )
        url = f"https://mahto.id/chat-exporter?url={message.attachments[0].url}"
        embed = discord.Embed(
            title="Transcript Link",
            description=LINK_MESSAGE.format(url=url),
            colour=discord.Colour.green(),
        )
        if self.cogsutils.is_dpy2:
            view = discord.ui.View()
            view.add_item(discord.ui.Button(style=discord.ButtonStyle.url, label="View transcript", url=url))
            await message.edit(embed=embed, view=view)
        else:
            await message.edit(embed=embed)

    @exportchannel.command()
    async def between(
        self,
        ctx: commands.Context,
        channel: typing.Optional[discord.TextChannel],
        before: discord.Message,
        after: discord.Message,
    ) -> None:
        """Export part of a channel's messages to an html file.

        Specify the before and after messages (id or link).
        Please note: all attachments and user avatars are saved with the Discord link in this file.
        Remember that exporting other users' messages from Discord does not respect the TOS.
        """
        if channel is None:
            channel = ctx.channel
        await self.check_channel(ctx, channel)
        count_messages, messages, file = await self.export_messages(
            ctx, channel=channel, before=before, after=after
        )
        message = await ctx.send(
            _(RESULT_MESSAGE).format(channel=channel, count_messages=count_messages), file=file
        )
        url = f"https://mahto.id/chat-exporter?url={message.attachments[0].url}"
        embed = discord.Embed(
            title="Transcript Link",
            description=LINK_MESSAGE.format(url=url),
            colour=discord.Colour.green(),
        )
        if self.cogsutils.is_dpy2:
            view = discord.ui.View()
            view.add_item(discord.ui.Button(style=discord.ButtonStyle.url, label="View transcript", url=url))
            await message.edit(embed=embed, view=view)
        else:
            await message.edit(embed=embed)

    @exportchannel.command()
    async def user(
        self,
        ctx: commands.Context,
        channel: typing.Optional[discord.TextChannel],
        user: discord.User,
        limit: typing.Optional[int] = None,
    ) -> None:
        """Export part of a channel's messages to an html file.

        Specify the member (id, name or mention).
        Please note: all attachments and user avatars are saved with the Discord link in this file.
        Remember that exporting other users' messages from Discord does not respect the TOS.
        """
        if channel is None:
            channel = ctx.channel
        await self.check_channel(ctx, channel)
        count_messages, messages, file = await self.export_messages(
            ctx,
            channel=channel,
            user_id=user.id if isinstance(user, discord.Member) else user,
            limit=limit,
        )
        message = await ctx.send(
            _(RESULT_MESSAGE).format(channel=channel, count_messages=count_messages), file=file
        )
        url = f"https://mahto.id/chat-exporter?url={message.attachments[0].url}"
        embed = discord.Embed(
            title="Transcript Link",
            description=LINK_MESSAGE.format(url=url),
            colour=discord.Colour.green(),
        )
        if self.cogsutils.is_dpy2:
            view = discord.ui.View()
            view.add_item(discord.ui.Button(style=discord.ButtonStyle.url, label="View transcript", url=url))
            await message.edit(embed=embed, view=view)
        else:
            await message.edit(embed=embed)

    @exportchannel.command()
    async def bot(
        self,
        ctx: commands.Context,
        channel: typing.Optional[discord.TextChannel],
        bot: typing.Optional[bool] = True,
        limit: typing.Optional[int] = None,
    ) -> None:
        """Export part of a channel's messages to an html file.

        Specify the bool option.
        Please note: all attachments and user avatars are saved with the Discord link in this file.
        Remember that exporting other users' messages from Discord does not respect the TOS.
        """
        if channel is None:
            channel = ctx.channel
        await self.check_channel(ctx, channel)
        count_messages, messages, file = await self.export_messages(
            ctx, channel=channel, bot=bot, limit=limit
        )
        message = await ctx.send(
            _(RESULT_MESSAGE).format(channel=channel, count_messages=count_messages), file=file
        )
        url = f"https://mahto.id/chat-exporter?url={message.attachments[0].url}"
        embed = discord.Embed(
            title="Transcript Link",
            description=LINK_MESSAGE.format(url=url),
            colour=discord.Colour.green(),
        )
        if self.cogsutils.is_dpy2:
            view = discord.ui.View()
            view.add_item(discord.ui.Button(style=discord.ButtonStyle.url, label="View transcript", url=url))
            await message.edit(embed=embed, view=view)
        else:
            await message.edit(embed=embed)

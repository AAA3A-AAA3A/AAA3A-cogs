from AAA3A_utils import Cog  # isort:skip
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


def _(untranslated: str) -> str:  # `redgettext` will found these strings.
    return untranslated


RESULT_MESSAGE = _(
    "Here is the transcript's html file of the messages in the channel {channel.mention} ({channel.id}).\nPlease note: all attachments and user avatars are saved with the Discord link in this file.\nThere are {count_messages} exported messages.\nRemember that exporting other users' messages from Discord does not respect the TOS."
)
LINK_MESSAGE = _("[Click here to view the transcript.]({url})")

_ = Translator("ExportChannel", __file__)


class MessageOrObjectConverter(commands.Converter):
    async def convert(
        self, ctx: commands.Context, argument: str
    ) -> typing.Union[discord.Message, discord.Object]:
        try:
            return await commands.MessageConverter().convert(ctx, argument=argument)
        except commands.BadArgument as e:
            try:
                return await commands.ObjectConverter().convert(ctx, argument=argument)
            except commands.BadArgument:
                raise e


@cog_i18n(_)
class ExportChannel(Cog):
    """A cog to export all or a part of the messages of a channel in an html file!"""

    def __init__(self, bot: Red) -> None:
        super().__init__(bot=bot)

    async def red_delete_data_for_user(self, *args, **kwargs) -> None:
        """Nothing to delete."""
        return

    async def red_get_data_for_user(self, *args, **kwargs) -> typing.Dict[str, typing.Any]:
        """Nothing to get."""
        return {}

    async def check_channel(self, ctx: commands.Context, channel: discord.TextChannel) -> None:
        channel_permissions = channel.permissions_for(ctx.me)
        if not all(
            [
                channel_permissions.view_channel,
                channel_permissions.read_messages,
                channel_permissions.read_message_history,
            ]
        ):
            raise commands.UserFeedbackCheckFailure(
                _(
                    "Sorry, I can't read the content of the messages in {channel.mention} ({channel.id})."
                ).format(channel=channel)
            )

    async def get_messages(
        self,
        ctx: commands.Context,
        channel: typing.Union[discord.TextChannel, discord.VoiceChannel, discord.Thread],
        number: typing.Optional[int] = None,
        limit: typing.Optional[int] = None,
        before: typing.Optional[typing.Union[discord.Message, discord.Object]] = None,
        after: typing.Optional[typing.Union[discord.Message, discord.Object]] = None,
        user_id: typing.Optional[int] = None,
        bot: typing.Optional[bool] = None,
    ) -> typing.Tuple[int, typing.List[discord.Message]]:
        messages = []
        async for message in channel.history(
            limit=(
                limit if channel != ctx.message.channel and ctx.interaction is None else limit + 1
            )
            if limit is not None
            else None,
            before=before,
            after=after,
            oldest_first=False,
        ):
            if user_id is not None and message.author.id != user_id:
                continue
            if bot is not None and message.author.bot != bot:
                continue
            messages.append(message)
            if number is not None and number <= len(messages):
                break
        if channel == ctx.message.channel:
            messages = [message for message in messages if message.id != ctx.message.id]
            # If the message has been deleted for some reason, keep the limit requested.
            if limit is not None:
                messages = messages[-limit:]
        count_messages = len(messages)
        if count_messages == 0:
            raise commands.UserFeedbackCheckFailure(_("Sorry. I could not find any messages."))
        return count_messages, messages

    async def export_messages(
        self,
        ctx: commands.Context,
        channel: typing.Union[discord.TextChannel, discord.VoiceChannel, discord.Thread],
        **kwargs,
    ) -> typing.Union[int, typing.List[discord.Message], discord.File]:
        if "messages" in kwargs:
            messages = kwargs["messages"]
            count_messages = len(messages)
        else:
            count_messages, messages = await self.get_messages(ctx, channel=channel, **kwargs)

        class Transcript(chat_exporter.construct.transcript.TranscriptDAO):
            @classmethod
            async def export(
                cls,
                channel: typing.Union[discord.TextChannel, discord.VoiceChannel, discord.Thread],
                messages: typing.List[discord.Message],
                tz_info="UTC",
                guild: typing.Optional[discord.Guild] = None,
                bot: typing.Optional[discord.Client] = None,
                military_time: typing.Optional[bool] = False,
                fancy_times: typing.Optional[bool] = True,
                support_dev: typing.Optional[bool] = True,
                attachment_handler: typing.Optional[typing.Any] = None,
            ):
                if guild:
                    channel.guild = guild
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
                    bot=bot,
                    attachment_handler=attachment_handler,
                )
                if not self.after:
                    self.messages.reverse()
                return (await self.build_transcript()).html

        transcript = await Transcript.export(
            channel=channel,
            messages=messages,
            tz_info="UTC",
            guild=channel.guild,
            bot=ctx.bot,
        )
        file = discord.File(
            io.BytesIO(transcript.encode()), filename=f"transcript-{channel.id}.html"
        )
        return count_messages, messages, file

    @commands.guild_only()
    @commands.guildowner_or_permissions(administrator=True)
    @commands.bot_has_permissions(attach_files=True, embed_links=True)
    @commands.hybrid_group(name="exportchannel", aliases=["exportmessages"])
    async def exportchannel(self, ctx: commands.Context) -> None:
        """Export all or a part of the messages of a channel in an html file."""

    @exportchannel.command()
    async def all(
        self,
        ctx: commands.Context,
        channel: typing.Union[discord.TextChannel, discord.VoiceChannel, discord.Thread] = None,
    ) -> None:
        """Export all of a channel's messages to an html file.

        Please note: all attachments and user avatars are saved with the Discord link in this file.
        Remember that exporting other users' messages from Discord does not respect the TOS.
        """
        if channel is None:
            channel = ctx.channel
        await self.check_channel(ctx, channel)
        count_messages, __, file = await self.export_messages(ctx, channel=channel)
        message = await ctx.send(
            _(RESULT_MESSAGE).format(channel=channel, count_messages=count_messages), file=file
        )
        url = f"https://mahto.id/chat-exporter?url={message.attachments[0].url}"
        embed = discord.Embed(
            title="Transcript Link",
            description=_(LINK_MESSAGE).format(url=url),
            color=await ctx.embed_color(),
        )
        view = discord.ui.View()
        view.add_item(
            discord.ui.Button(style=discord.ButtonStyle.url, label="View transcript", url=url)
        )
        await message.edit(embed=embed, view=view)

    @exportchannel.command()
    async def message(self, ctx: commands.Context, message: discord.Message) -> None:
        """Export a specific file in an html file.

        Specify the message to export, with its ID or its link.
        Please note: all attachments and user avatars are saved with the Discord link in this file.
        Remember that exporting other users' messages from Discord does not respect the TOS.
        """
        await self.check_channel(ctx, message.channel)
        count_messages, __, file = await self.export_messages(
            ctx,
            channel=message.channel,
            messages=[message],
        )
        message = await ctx.send(
            _(RESULT_MESSAGE).format(channel=message.channel, count_messages=count_messages),
            file=file,
        )
        url = f"https://mahto.id/chat-exporter?url={message.attachments[0].url}"
        embed = discord.Embed(
            title="Transcript Link",
            description=_(LINK_MESSAGE).format(url=url),
            color=await ctx.embed_color(),
        )
        view = discord.ui.View()
        view.add_item(
            discord.ui.Button(style=discord.ButtonStyle.url, label="View transcript", url=url)
        )
        await message.edit(embed=embed, view=view)

    @exportchannel.command()
    async def messages(
        self,
        ctx: commands.Context,
        channel: typing.Optional[
            typing.Union[discord.TextChannel, discord.VoiceChannel, discord.Thread]
        ],
        limit: int,
    ) -> None:
        """Export a part of the messages of a channel in an html file.

        Specify the number of messages since the end of the channel.
        Please note: all attachments and user avatars are saved with the Discord link in this file.
        Remember that exporting other users' messages from Discord does not respect the TOS.
        """
        if channel is None:
            channel = ctx.channel
        await self.check_channel(ctx, channel)
        count_messages, __, file = await self.export_messages(
            ctx,
            channel=channel,
            limit=limit,
        )
        message = await ctx.send(
            _(RESULT_MESSAGE).format(channel=channel, count_messages=count_messages), file=file
        )
        url = f"https://mahto.id/chat-exporter?url={message.attachments[0].url}"
        embed = discord.Embed(
            title="Transcript Link",
            description=_(LINK_MESSAGE).format(url=url),
            color=await ctx.embed_color(),
        )
        view = discord.ui.View()
        view.add_item(
            discord.ui.Button(style=discord.ButtonStyle.url, label="View transcript", url=url)
        )
        await message.edit(embed=embed, view=view)

    @exportchannel.command()
    async def before(
        self,
        ctx: commands.Context,
        channel: typing.Optional[
            typing.Union[discord.TextChannel, discord.VoiceChannel, discord.Thread]
        ],
        before: MessageOrObjectConverter,
    ) -> None:
        """Export a part of the messages of a channel in an html file.

        Specify the before message (id or link) or a valid snowflake.
        Please note: all attachments and user avatars are saved with the Discord link in this file.
        Remember that exporting other users' messages from Discord does not respect the TOS.
        """
        if channel is None:
            channel = ctx.channel
        await self.check_channel(ctx, channel)
        count_messages, __, file = await self.export_messages(ctx, channel=channel, before=before)
        message = await ctx.send(
            _(RESULT_MESSAGE).format(channel=channel, count_messages=count_messages), file=file
        )
        url = f"https://mahto.id/chat-exporter?url={message.attachments[0].url}"
        embed = discord.Embed(
            title="Transcript Link",
            description=_(LINK_MESSAGE).format(url=url),
            color=await ctx.embed_color(),
        )
        view = discord.ui.View()
        view.add_item(
            discord.ui.Button(style=discord.ButtonStyle.url, label="View transcript", url=url)
        )
        await message.edit(embed=embed, view=view)

    @exportchannel.command()
    async def after(
        self,
        ctx: commands.Context,
        channel: typing.Optional[
            typing.Union[discord.TextChannel, discord.VoiceChannel, discord.Thread]
        ],
        after: MessageOrObjectConverter,
    ) -> None:
        """Export a part of the messages of a channel in an html file.

        Specify the after message (id or link) or a valid snowflake.
        Please note: all attachments and user avatars are saved with the Discord link in this file.
        Remember that exporting other users' messages from Discord does not respect the TOS.
        """
        if channel is None:
            channel = ctx.channel
        await self.check_channel(ctx, channel)
        count_messages, __, file = await self.export_messages(ctx, channel=channel, after=after)
        message = await ctx.send(
            _(RESULT_MESSAGE).format(channel=channel, count_messages=count_messages), file=file
        )
        url = f"https://mahto.id/chat-exporter?url={message.attachments[0].url}"
        embed = discord.Embed(
            title="Transcript Link",
            description=_(LINK_MESSAGE).format(url=url),
            color=await ctx.embed_color(),
        )
        view = discord.ui.View()
        view.add_item(
            discord.ui.Button(style=discord.ButtonStyle.url, label="View transcript", url=url)
        )
        await message.edit(embed=embed, view=view)

    @exportchannel.command()
    async def between(
        self,
        ctx: commands.Context,
        channel: typing.Optional[
            typing.Union[discord.TextChannel, discord.VoiceChannel, discord.Thread]
        ],
        before: MessageOrObjectConverter,
        after: MessageOrObjectConverter,
    ) -> None:
        """Export a part of the messages of a channel in an html file.

        Specify the before and after messages (id or link) or a valid snowflake.
        Please note: all attachments and user avatars are saved with the Discord link in this file.
        Remember that exporting other users' messages from Discord does not respect the TOS.
        """
        if channel is None:
            channel = ctx.channel
        await self.check_channel(ctx, channel)
        count_messages, __, file = await self.export_messages(
            ctx, channel=channel, before=before, after=after
        )
        message = await ctx.send(
            _(RESULT_MESSAGE).format(channel=channel, count_messages=count_messages), file=file
        )
        url = f"https://mahto.id/chat-exporter?url={message.attachments[0].url}"
        embed = discord.Embed(
            title="Transcript Link",
            description=_(LINK_MESSAGE).format(url=url),
            color=await ctx.embed_color(),
        )
        view = discord.ui.View()
        view.add_item(
            discord.ui.Button(style=discord.ButtonStyle.url, label="View transcript", url=url)
        )
        await message.edit(embed=embed, view=view)

    @exportchannel.command()
    async def user(
        self,
        ctx: commands.Context,
        channel: typing.Optional[
            typing.Union[discord.TextChannel, discord.VoiceChannel, discord.Thread]
        ],
        user: discord.User,
        limit: typing.Optional[int] = None,
    ) -> None:
        """Export a part of the messages of a channel in an html file.

        Specify the user/member (id, name or mention).
        Please note: all attachments and user avatars are saved with the Discord link in this file.
        Remember that exporting other users' messages from Discord does not respect the TOS.
        """
        if channel is None:
            channel = ctx.channel
        await self.check_channel(ctx, channel)
        count_messages, __, file = await self.export_messages(
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
            description=_(LINK_MESSAGE).format(url=url),
            color=await ctx.embed_color(),
        )
        view = discord.ui.View()
        view.add_item(
            discord.ui.Button(style=discord.ButtonStyle.url, label="View transcript", url=url)
        )
        await message.edit(embed=embed, view=view)

    @exportchannel.command()
    async def bot(
        self,
        ctx: commands.Context,
        channel: typing.Optional[
            typing.Union[discord.TextChannel, discord.VoiceChannel, discord.Thread]
        ],
        bot: typing.Optional[bool] = True,
        limit: typing.Optional[int] = None,
    ) -> None:
        """Export a part of the messages of a channel in an html file.

        Specify the bool option.
        Please note: all attachments and user avatars are saved with the Discord link in this file.
        Remember that exporting other users' messages from Discord does not respect the TOS.
        """
        if channel is None:
            channel = ctx.channel
        await self.check_channel(ctx, channel)
        count_messages, __, file = await self.export_messages(
            ctx, channel=channel, bot=bot, limit=limit
        )
        message = await ctx.send(
            _(RESULT_MESSAGE).format(channel=channel, count_messages=count_messages), file=file
        )
        url = f"https://mahto.id/chat-exporter?url={message.attachments[0].url}"
        embed = discord.Embed(
            title="Transcript Link",
            description=_(LINK_MESSAGE).format(url=url),
            color=await ctx.embed_color(),
        )
        view = discord.ui.View()
        view.add_item(
            discord.ui.Button(style=discord.ButtonStyle.url, label="View transcript", url=url)
        )
        await message.edit(embed=embed, view=view)

from AAA3A_utils import Cog, CogsUtils, Menu  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
from redbot.core.bot import Red  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

from redbot.core.utils.chat_formatting import pagify
from redbot.core.utils.tunnel import Tunnel

# Credits:
# General repo credits.
# Thanks to TrustyJAID's Backup for starting the command to list the latest source channel messages! (https://github.com/TrustyJAID/Trusty-cogs/tree/master/backup)
# Thanks to QuoteTools from SimBad for the embed!
# Thanks to Speak from @epic guy for the webhooks! (https://github.com/npc203/npc-cogs/tree/main/speak)
# Thanks to Say from LaggronsDumb for the attachments in the single messages and webhooks! (https://github.com/laggron42/Laggrons-Dumb-Cogs/tree/v3/say)
# Thanks to CruxCraft on GitHub for the idea of allowing channels from other servers! (https://github.com/AAA3A-AAA3A/AAA3A-cogs/issues/1)


def _(untranslated: str) -> str:  # `redgettext` will found these strings.
    return untranslated


RESULT_MESSAGE = _(
    "There are {count_messages} transfered messages from {source.mention} to {destination.mention}."
)

_ = Translator("TransferChannel", __file__)


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
class TransferChannel(Cog):
    """A cog to transfer messages from a channel to another channel, with many options!"""

    def embed_from_msg(self, message: discord.Message) -> discord.Embed:
        content = message.content
        channel = message.channel
        guild = channel.guild
        author = message.author
        avatar = author.display_avatar
        footer = f"Said in {guild.name} #{channel.name}."
        try:
            color = author.color if author.color.value != 0 else None
        except AttributeError:  # happens if message author not in guild anymore.
            color = None
        em = discord.Embed(description=content, timestamp=message.created_at)
        if color:
            em.color = color
        em.set_author(name=f"{author.name}", icon_url=avatar)
        em.set_footer(
            icon_url=guild.icon,
            text=footer,
        )
        if message.attachments:
            a = message.attachments[0]
            fname = a.filename
            url = a.url
            if fname.split(".")[-1] in ["WEBP", "jpg", "gif", "jpeg"]:
                em.set_image(url=url)
            else:
                em.add_field(
                    name="Message has an attachment.", value=f"[{fname}]({url})", inline=True
                )
        return em

    async def check_channels(
        self,
        source: typing.Union[discord.TextChannel, discord.VoiceChannel, discord.Thread],
        destination: typing.Union[discord.TextChannel, discord.VoiceChannel, discord.Thread],
        way: str,
    ) -> None:
        source_permissions = source.permissions_for(source.guild.me)
        if not all(
            [
                source_permissions.view_channel,
                source_permissions.read_messages,
                source_permissions.read_message_history,
            ]
        ):
            raise commands.UserFeedbackCheckFailure(
                _(
                    "Sorry, I can't read the content of the messages in {source.mention} ({source.id})."
                ).format(source=source)
            )
        destination_permissions = destination.permissions_for(destination.guild.me)
        if not destination_permissions.send_messages or not destination_permissions.embed_links:
            raise commands.UserFeedbackCheckFailure(
                _(
                    "I need to have all the permissions to send messages with embeds in {destination.guild.name} ({destination.guild.id})."
                ).format(destination=destination)
            )
        if way == "webhooks" and not destination_permissions.manage_webhooks:
            raise commands.UserFeedbackCheckFailure(
                _(
                    "I need to have all the permission to create webhooks in {destination.guild.name} ({destination.guild.id}). You can use embeds or text messages by adding `embeds`/`messages` to your command."
                ).format(destination=destination)
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
            if message.type not in (discord.MessageType.default, discord.MessageType.reply):
                continue
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

    async def transfer_messages(
        self,
        ctx: commands.Context,
        source: typing.Union[discord.TextChannel, discord.VoiceChannel, discord.Thread],
        destination: typing.Union[discord.TextChannel, discord.VoiceChannel, discord.Thread],
        way: typing.Literal["webhooks", "embeds", "messages"],
        **kwargs,
    ) -> typing.Tuple[int, typing.List[discord.Message]]:
        if "messages" in kwargs:
            messages = kwargs["messages"]
            count_messages = len(messages)
        else:
            count_messages, messages = await self.get_messages(ctx, channel=source, **kwargs)
        messages.reverse()
        if way == "webhooks":
            hook = await CogsUtils.get_hook(
                bot=ctx.bot,
                channel=destination.parent
                if isinstance(destination, discord.Thread)
                else destination,
            )
        for message in messages:
            if destination.permissions_for(destination.guild.me).attach_files:
                files = await Tunnel.files_from_attatch(message)
            else:
                files = []
            if way == "webhooks":
                if not any([message.content, message.embeds, message.attachments]):
                    continue
                for page in pagify(message.content):
                    await hook.send(
                        username=message.author.display_name,
                        avatar_url=message.author.display_avatar,
                        content=page,
                        embeds=message.embeds,
                        files=files,
                        allowed_mentions=discord.AllowedMentions(
                            everyone=False, users=False, roles=False
                        ),
                        thread=destination
                        if isinstance(destination, discord.Thread)
                        else discord.utils.MISSING,
                        wait=True,
                    )
            elif way == "embeds":
                embed = self.embed_from_msg(message)
                try:
                    await destination.send(
                        embeds=[embed] + message.embeds,
                        files=files,
                        stickers=message.stickers,
                        allowed_mentions=discord.AllowedMentions(
                            everyone=False, users=False, roles=False
                        ),
                    )
                except discord.HTTPException:
                    try:
                        await destination.send(
                            embeds=[embed] + message.embeds[:-1],
                            files=files,
                            stickers=message.stickers,
                            allowed_mentions=discord.AllowedMentions(
                                everyone=False, users=False, roles=False
                            ),
                        )
                    except discord.HTTPException:
                        await destination.send(
                            embed=embed,
                            files=files,
                            stickers=message.stickers,
                            allowed_mentions=discord.AllowedMentions(
                                everyone=False, users=False, roles=False
                            ),
                        )
            elif way == "messages":
                iso_format = message.created_at.isoformat()
                msg = "\n".join(
                    [
                        _("**Author:** {message.author.mention} ({message.author.id})").format(
                            message=message
                        ),
                        _("**Channel:** <#{message.channel.id}>").format(message=message),
                        _("**Time (UTC):** {iso_format}").format(iso_format=iso_format),
                    ]
                )
                if len(f"{msg}\n\n{message.content}") <= 2000:
                    await destination.send(
                        f"{msg}\n\n{message.content}",
                        embeds=message.embeds,
                        files=files,
                        stickers=message.stickers,
                        allowed_mentions=discord.AllowedMentions(
                            everyone=False, users=False, roles=False
                        ),
                    )
                else:
                    await destination.send(msg, allowed_mentions=discord.AllowedMentions.none())
                    for page in pagify(message.content):
                        await destination.send(
                            page,
                            embeds=message.embeds,
                            files=files,
                            stickers=message.stickers,
                            allowed_mentions=discord.AllowedMentions(
                                everyone=False, users=False, roles=False
                            ),
                        )
        return count_messages, messages

    @commands.guildowner_or_permissions(administrator=True)
    @commands.hybrid_group(name="transferchannel", aliases=["channeltransfer"])
    async def transferchannel(self, ctx: commands.Context) -> None:
        """Transfer messages from a channel to another channel, with many options. This might take a long time.
        You can specify the id of a channel from another server.

        `source` is partial name or ID of the source channel
        `destination` is partial name or ID of the destination channel
        `way` is the used way
        - `embed` Do you want to transfer the message as an embed?
        - `webhook` Do you want to send the messages with webhooks (name and avatar of the original author)?
        - `message`Do you want to transfer the message as a simple message?
        Remember that transfering other users' messages does not respect the TOS."""

    @transferchannel.command()
    async def all(
        self,
        ctx: commands.Context,
        source: typing.Union[discord.TextChannel, discord.VoiceChannel, discord.Thread],
        destination: typing.Union[discord.TextChannel, discord.VoiceChannel, discord.Thread],
        way: typing.Literal["webhooks", "embeds", "messages"] = "webhooks",
    ) -> None:
        """Transfer all messages from a channel to another channel. This might take a long time.

        Remember that transfering other users' messages does not respect the TOS.
        """
        if ctx.guild is None and ctx.author.id not in ctx.bot.owner_ids:
            raise commands.UserInputError()
        await self.check_channels(source=source, destination=destination, way=way)
        count_messages, __ = await self.transfer_messages(
            ctx, source=source, destination=destination, way=way
        )
        await Menu(
            pages=_(RESULT_MESSAGE).format(
                count_messages=count_messages, source=source, destination=destination
            )
        ).start(ctx)

    @transferchannel.command()
    async def message(
        self,
        ctx: commands.Context,
        message: discord.Message,
        destination: typing.Union[discord.TextChannel, discord.VoiceChannel, discord.Thread],
        way: typing.Literal["webhooks", "embeds", "messages"] = "webhooks",
    ) -> None:
        """Transfer a specific message to another channel. This might take a long time.

        Specify the message to transfer, with its ID or its link.
        Remember that transfering other users' messages does not respect the TOS.
        """
        if ctx.guild is None and ctx.author.id not in ctx.bot.owner_ids:
            raise commands.UserInputError()
        await self.check_channels(source=message.channel, destination=destination, way=way)
        count_messages, __ = await self.transfer_messages(
            ctx,
            source=message.channel,
            destination=destination,
            way=way,
            messages=[message],
        )
        await ctx.send(
            _(
                "There are {count_messages} transfered messages from {source.mention} to {destination.mention}."
            ).format(
                count_messages=count_messages, source=message.channel, destination=destination
            )
        )

    @transferchannel.command()
    async def messages(
        self,
        ctx: commands.Context,
        source: typing.Union[discord.TextChannel, discord.VoiceChannel, discord.Thread],
        destination: typing.Union[discord.TextChannel, discord.VoiceChannel, discord.Thread],
        limit: int,
        way: typing.Literal["webhooks", "embeds", "messages"] = "webhooks",
    ) -> None:
        """Transfer a part of the messages from a channel to another channel. This might take a long time.

        Specify the number of messages since the end of the channel.
        Remember that transfering other users' messages does not respect the TOS.
        """
        if ctx.guild is None and ctx.author.id not in ctx.bot.owner_ids:
            raise commands.UserInputError()
        await self.check_channels(source=source, destination=destination, way=way)
        count_messages, __ = await self.transfer_messages(
            ctx,
            source=source,
            destination=destination,
            way=way,
            limit=limit,
        )
        await ctx.send(
            _(
                "There are {count_messages} transfered messages from {source.mention} to {destination.mention}."
            ).format(count_messages=count_messages, source=source, destination=destination)
        )

    @transferchannel.command()
    async def before(
        self,
        ctx: commands.Context,
        source: typing.Union[discord.TextChannel, discord.VoiceChannel, discord.Thread],
        destination: typing.Union[discord.TextChannel, discord.VoiceChannel, discord.Thread],
        before: MessageOrObjectConverter,
        way: typing.Literal["webhooks", "embeds", "messages"] = "webhooks",
    ) -> None:
        """Transfer a part of the messages from a channel to another channel. This might take a long time.

        Specify the before message (id or link) or a valid Discord snowflake.
        Remember that transfering other users' messages does not respect the TOS.
        """
        if ctx.guild is None and ctx.author.id not in ctx.bot.owner_ids:
            raise commands.UserInputError()
        await self.check_channels(source=source, destination=destination, way=way)
        count_messages, __ = await self.transfer_messages(
            ctx, source=source, destination=destination, way=way, before=before
        )
        await Menu(
            pages=_(RESULT_MESSAGE).format(
                count_messages=count_messages, source=source, destination=destination
            )
        ).start(ctx)

    @transferchannel.command()
    async def after(
        self,
        ctx: commands.Context,
        source: typing.Union[discord.TextChannel, discord.VoiceChannel, discord.Thread],
        destination: typing.Union[discord.TextChannel, discord.VoiceChannel, discord.Thread],
        after: MessageOrObjectConverter,
        way: typing.Literal["webhooks", "embeds", "messages"] = "webhooks",
    ) -> None:
        """Transfer a part of the messages from a channel to another channel. This might take a long time.

        Specify the after message (id or link) or a valid Discord snowflake.
        Remember that transfering other users' messages does not respect the TOS.
        """
        if ctx.guild is None and ctx.author.id not in ctx.bot.owner_ids:
            raise commands.UserInputError()
        await self.check_channels(source=source, destination=destination, way=way)
        count_messages, __ = await self.transfer_messages(
            ctx, source=source, destination=destination, way=way, after=after
        )
        await Menu(
            pages=_(RESULT_MESSAGE).format(
                count_messages=count_messages, source=source, destination=destination
            )
        ).start(ctx)

    @transferchannel.command()
    async def between(
        self,
        ctx: commands.Context,
        source: typing.Union[discord.TextChannel, discord.VoiceChannel, discord.Thread],
        destination: typing.Union[discord.TextChannel, discord.VoiceChannel, discord.Thread],
        before: MessageOrObjectConverter,
        after: MessageOrObjectConverter,
        way: typing.Literal["webhooks", "embeds", "messages"] = "webhooks",
    ) -> None:
        """Transfer a part of the messages from a channel to another channel. This might take a long time.

        Specify the between messages (id or link) or a valid snowflake.
        Remember that transfering other users' messages does not respect the TOS.
        """
        if ctx.guild is None and ctx.author.id not in ctx.bot.owner_ids:
            raise commands.UserInputError()
        await self.check_channels(source=source, destination=destination, way=way)
        count_messages, __ = await self.transfer_messages(
            ctx, source=source, destination=destination, way=way, before=before, after=after
        )
        await Menu(
            pages=_(RESULT_MESSAGE).format(
                count_messages=count_messages, source=source, destination=destination
            )
        ).start(ctx)

    @transferchannel.command()
    async def user(
        self,
        ctx: commands.Context,
        source: typing.Union[discord.TextChannel, discord.VoiceChannel, discord.Thread],
        destination: typing.Union[discord.TextChannel, discord.VoiceChannel, discord.Thread],
        user: discord.User,
        limit: typing.Optional[int] = None,
        way: typing.Literal["webhooks", "embeds", "messages"] = "webhooks",
    ) -> None:
        """Transfer a part of the messages from a channel to another channel. This might take a long time.

        Specify the user/member (id, name or mention).
        Remember that transfering other users' messages does not respect the TOS.
        """
        if ctx.guild is None and ctx.author.id not in ctx.bot.owner_ids:
            raise commands.UserInputError()
        await self.check_channels(source=source, destination=destination, way=way)
        count_messages, __ = await self.transfer_messages(
            ctx,
            source=source,
            destination=destination,
            way=way,
            user_id=user.id if isinstance(user, discord.Member) else user,
            limit=limit,
        )
        await Menu(
            pages=_(RESULT_MESSAGE).format(
                count_messages=count_messages, source=source, destination=destination
            )
        ).start(ctx)

    @transferchannel.command()
    async def bot(
        self,
        ctx: commands.Context,
        source: typing.Union[discord.TextChannel, discord.VoiceChannel, discord.Thread],
        destination: typing.Union[discord.TextChannel, discord.VoiceChannel, discord.Thread],
        bot: typing.Optional[bool] = True,
        limit: typing.Optional[int] = None,
        way: typing.Literal["webhooks", "embeds", "messages"] = "webhooks",
    ) -> None:
        """Transfer a part of the messages from a channel to another channel. This might take a long time.

        Specify the bool option.
        Remember that transfering other users' messages does not respect the TOS.
        """
        if ctx.guild is None and ctx.author.id not in ctx.bot.owner_ids:
            raise commands.UserInputError()
        await self.check_channels(source=source, destination=destination, way=way)
        count_messages, __ = await self.transfer_messages(
            ctx, source=source, destination=destination, way=way, bot=bot, limit=limit
        )
        await Menu(
            pages=_(RESULT_MESSAGE).format(
                count_messages=count_messages, source=source, destination=destination
            )
        ).start(ctx)

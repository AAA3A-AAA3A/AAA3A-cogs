from .AAA3A_utils import Cog, CogsUtils  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
from redbot.core.bot import Red  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

from redbot.core.utils.tunnel import Tunnel

if CogsUtils().is_dpy2:
    setattr(commands, "Literal", typing.Literal)  # To remove

# Credits:
# General repo credits.
# Thanks to TrustyJAID's Backup for starting the command to list the latest source channel messages! (https://github.com/TrustyJAID/Trusty-cogs/tree/master/backup)
# Thanks to QuoteTools from SimBad for the embed!
# Thanks to Speak from @epic guy for the webhooks! (https://github.com/npc203/npc-cogs/tree/main/speak)
# Thanks to Say from LaggronsDumb for the attachments in the single messages and webhooks! (https://github.com/laggron42/Laggrons-Dumb-Cogs/tree/v3/say)
# Thanks to CruxCraft on GitHub for the idea of allowing channels from other servers! (https://github.com/AAA3A-AAA3A/AAA3A-cogs/issues/1)

_ = Translator("TransferChannel", __file__)

if CogsUtils().is_dpy2:
    from functools import partial

    hybrid_command = partial(commands.hybrid_command, with_app_command=False)
    hybrid_group = partial(commands.hybrid_group, with_app_command=False)
else:
    hybrid_command = commands.command
    hybrid_group = commands.group

RESULT_MESSAGE = _(
    "There are {count_messages} transfered messages from {source.mention} to {destination.mention}."
)


@cog_i18n(_)
class TransferChannel(Cog):
    """A cog to transfer all messages channel in a other channel!"""

    def __init__(self, bot: Red) -> None:
        self.bot: Red = bot

        self.cogsutils: CogsUtils = CogsUtils(cog=self)

    def embed_from_msg(self, message: discord.Message) -> discord.Embed:
        content = message.content
        channel = message.channel
        assert isinstance(channel, discord.TextChannel), "mypy"  # nosec
        guild = channel.guild
        author = message.author
        avatar = author.display_avatar if self.cogsutils.is_dpy2 else author.avatar_url
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
            icon_url=guild.icon or "" if self.cogsutils.is_dpy2 else guild.icon_url or "",
            text=footer,
        )
        if message.attachments:
            a = message.attachments[0]
            fname = a.filename
            url = a.url
            if fname.split(".")[-1] in ["png", "jpg", "gif", "jpeg"]:
                em.set_image(url=url)
            else:
                em.add_field(
                    name="Message has an attachment.", value=f"[{fname}]({url})", inline=True
                )
        return em

    async def check_channels(
        self,
        ctx: commands.Context,
        source: discord.TextChannel,
        destination: discord.TextChannel,
        way: str,
    ) -> None:
        if not self.cogsutils.check_permissions_for(
            channel=source,
            user=ctx.me,
            check=["view_channel", "read_messages", "read_message_history"],
        ):
            raise commands.UserFeedbackCheckFailure(
                _(
                    "Sorry, I can't read the content of the messages in {source.mention} ({source.id})."
                ).format()
            )
        permissions = destination.permissions_for(destination.guild.me)
        if way == "embed":
            if not permissions.embed_links:
                raise commands.UserFeedbackCheckFailure(
                    _(
                        "I need to have all the following permissions for {destination.mention} ({destination.id}) in {destination.guild.name} ({destination.guild.id}).\n`embed_links`."
                    ).format(destination=destination)
                )
        elif way == "webhook":
            if not permissions.manage_webhooks:
                raise commands.UserFeedbackCheckFailure(
                    _(
                        "I need to have all the following permissions for {destination.mention} ({destination.id}) in {destination.guild.name} ({destination.guild.id}).\n`manage_channels`"
                    ).format(destination=destination)
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
            if user_id is not None:
                if not message.author.id == user_id:
                    continue
            if bot is not None:
                if not message.author.bot == bot:
                    continue
            messages.append(message)
            if number is not None and number <= len(messages):
                break
        messages = [message for message in messages if not message.id == ctx.message.id]
        count_messages = len(messages)
        if count_messages == 0:
            raise commands.UserFeedbackCheckFailure(_("Sorry. I could not find any message."))
        return count_messages, messages

    async def transfer_messages(
        self,
        ctx: commands.Context,
        source: discord.TextChannel,
        destination: discord.TextChannel,
        way: typing.Literal["embeds", "webhooks", "messages"],
        **kwargs,
    ) -> typing.Tuple[int, typing.List[discord.Message]]:
        count_messages, messages = await self.get_messages(ctx, channel=source, **kwargs)
        messages.reverse()
        for message in messages:
            files = await Tunnel.files_from_attatch(message)
            if way == "embeds":
                embed = self.embed_from_msg(message)
                await destination.send(embed=embed)
            elif way == "webhooks":
                hook = await self.cogsutils.get_hook(destination)
                await hook.send(
                    username=message.author.display_name,
                    avatar_url=message.author.display_avatar
                    if self.cogsutils.is_dpy2
                    else message.author.avatar_url,
                    content=message.content,
                    files=files,
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
                        files=files,
                        allowed_mentions=discord.AllowedMentions.none(),
                    )
                else:
                    await destination.send(msg, allowed_mentions=discord.AllowedMentions.none())
                    await destination.send(
                        message.content,
                        files=files,
                        allowed_mentions=discord.AllowedMentions.none(),
                    )
        return count_messages, messages

    @commands.guildowner_or_permissions(administrator=True)
    @hybrid_group(name="transferchannel", aliases=["channeltransfer"])
    async def transferchannel(self, ctx: commands.Context) -> None:
        """Transfer all messages channel in a other channel. This might take a long time.
        You can specify the id of a channel from another server.

        `source` is partial name or ID of the source channel
        `destination` is partial name or ID of the destination channel
        `way` is the used way
          - `embed` Do you want to transfer the message as an embed?
          - `webhook` Do you want to send the messages with webhooks (name and avatar of the original author)?
          - `message`Do you want to transfer the message as a simple message?
        Remember that transfering other users' messages in does not respect the TOS."""

    @transferchannel.command()
    async def all(
        self,
        ctx: commands.Context,
        source: discord.TextChannel,
        destination: discord.TextChannel,
        way: commands.Literal["embeds", "webhooks", "messages"],
    ) -> None:
        """Transfer all messages channel in a other channel. This might take a long time.

        Remember that transfering other users' messages in does not respect the TOS.
        """
        if ctx.guild is None:
            if ctx.author.id not in ctx.bot.owner_ids:
                await ctx.send_help()
                return
        await self.check_channels(ctx, source, destination, way)
        count_messages, messages = await self.transfer_messages(
            ctx, source=source, destination=destination, way=way
        )
        await ctx.send(
            _(RESULT_MESSAGE).format(
                count_messages=count_messages, source=source, destination=destination
            )
        )

    @transferchannel.command()
    async def messages(
        self,
        ctx: commands.Context,
        source: discord.TextChannel,
        destination: discord.TextChannel,
        way: commands.Literal["embeds", "webhooks", "messages"],
        limit: int,
    ) -> None:
        """Transfer a part of a channel's messages channel in a other channel. This might take a long time.

        Specify the number of messages since the end of the channel.
        Remember that transfering other users' messages in does not respect the TOS.
        """
        if ctx.guild is None:
            if ctx.author.id not in ctx.bot.owner_ids:
                await ctx.send_help()
                return
        await self.check_channels(ctx, source, destination, way)
        count_messages, messages = await self.transfer_messages(
            ctx,
            source=source,
            destination=destination,
            way=way,
            limit=limit if not source == ctx.channel else limit + 1,
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
        source: discord.TextChannel,
        destination: discord.TextChannel,
        way: commands.Literal["embeds", "webhooks", "messages"],
        before: discord.Message,
    ) -> None:
        """Transfer a part of a channel's messages channel in a other channel. This might take a long time.

        Specify the before message (id or link).
        Remember that transfering other users' messages in does not respect the TOS.
        """
        if ctx.guild is None:
            if ctx.author.id not in ctx.bot.owner_ids:
                await ctx.send_help()
                return
        await self.check_channels(ctx, source, destination, way)
        count_messages, messages = await self.transfer_messages(
            ctx, source=source, destination=destination, way=way, before=before
        )
        await ctx.send(
            _(RESULT_MESSAGE).format(
                count_messages=count_messages, source=source, destination=destination
            )
        )

    @transferchannel.command()
    async def after(
        self,
        ctx: commands.Context,
        source: discord.TextChannel,
        destination: discord.TextChannel,
        way: commands.Literal["embeds", "webhooks", "messages"],
        after: discord.Message,
    ) -> None:
        """Transfer a part of a channel's messages channel in a other channel. This might take a long time.

        Specify the after message (id or link).
        Remember that transfering other users' messages in does not respect the TOS.
        """
        if ctx.guild is None:
            if ctx.author.id not in ctx.bot.owner_ids:
                await ctx.send_help()
                return
        await self.check_channels(ctx, source, destination, way)
        count_messages, messages = await self.transfer_messages(
            ctx, source=source, destination=destination, way=way, after=after
        )
        await ctx.send(
            _(RESULT_MESSAGE).format(
                count_messages=count_messages, source=source, destination=destination
            )
        )

    @transferchannel.command()
    async def between(
        self,
        ctx: commands.Context,
        source: discord.TextChannel,
        destination: discord.TextChannel,
        way: commands.Literal["embeds", "webhooks", "messages"],
        before: discord.Message,
        after: discord.Message,
    ) -> None:
        """Transfer a part of a channel's messages channel in a other channel. This might take a long time.

        Specify the between messages (id or link).
        Remember that transfering other users' messages in does not respect the TOS.
        """
        if ctx.guild is None:
            if ctx.author.id not in ctx.bot.owner_ids:
                await ctx.send_help()
                return
        await self.check_channels(ctx, source, destination, way)
        count_messages, messages = await self.transfer_messages(
            ctx, source=source, destination=destination, way=way, before=before, after=after
        )
        await ctx.send(
            _(RESULT_MESSAGE).format(
                count_messages=count_messages, source=source, destination=destination
            )
        )

    if CogsUtils().is_dpy2:

        @transferchannel.command()
        async def user(
            self,
            ctx: commands.Context,
            source: discord.TextChannel,
            destination: discord.TextChannel,
            way: commands.Literal["embeds", "webhooks", "messages"],
            user: discord.User,
            limit: typing.Optional[int] = None,
        ) -> None:
            """Transfer a part of a channel's messages channel in a other channel. This might take a long time.

            Specify the member (id, name or mention).
            Remember that transfering other users' messages in does not respect the TOS.
            """
            if ctx.guild is None:
                if ctx.author.id not in ctx.bot.owner_ids:
                    await ctx.send_help()
                    return
            await self.check_channels(ctx, source, destination, way)
            count_messages, messages = await self.transfer_messages(
                ctx,
                source=source,
                destination=destination,
                way=way,
                user_id=user.id if isinstance(user, discord.Member) else user,
                limit=limit,
            )
            await ctx.send(
                _(RESULT_MESSAGE).format(
                    count_messages=count_messages, source=source, destination=destination
                )
            )

    @transferchannel.command()
    async def bot(
        self,
        ctx: commands.Context,
        source: discord.TextChannel,
        destination: discord.TextChannel,
        way: commands.Literal["embeds", "webhooks", "messages"],
        bot: typing.Optional[bool] = True,
        limit: typing.Optional[int] = None,
    ) -> None:
        """Transfer a part of a channel's messages channel in a other channel. This might take a long time.

        Specify the bool option.
        Remember that transfering other users' messages in does not respect the TOS.
        """
        if ctx.guild is None:
            if ctx.author.id not in ctx.bot.owner_ids:
                await ctx.send_help()
                return
        await self.check_channels(ctx, source, destination, way)
        count_messages, messages = await self.transfer_messages(
            ctx, source=source, destination=destination, way=way, bot=bot, limit=limit
        )
        await ctx.send(
            _(RESULT_MESSAGE).format(
                count_messages=count_messages, source=source, destination=destination
            )
        )

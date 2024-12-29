from AAA3A_utils import Cog, CogsUtils, Menu  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.bot import Red  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import re

from redbot.core.utils.chat_formatting import box, humanize_list, pagify
from redbot.core.utils.tunnel import Tunnel

# Credits:
# General repo credits.
# Thanks to Phen for the original code (https://github.com/phenom4n4n/phen-cogs/tree/master/webhook)!

_: Translator = Translator("Webhook", __file__)

WEBHOOK_RE = re.compile(
    r"discord(?:app)?.com/api/webhooks/(?P<id>[0-9]{17,21})/(?P<token>[A-Za-z0-9\.\-\_]{60,68})"
)


class WebhookLinkConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> discord.Webhook:
        try:
            return ctx.bot.get_cog("Webhook").get_webhook_from_link(argument)
        except ValueError as e:
            raise commands.BadArgument(str(e)) from e


class Session:
    def __init__(
        self,
        cog: commands.Cog,
        author: discord.Member,
        channel: typing.Union[discord.TextChannel, discord.VoiceChannel, discord.Thread],
        webhook: discord.Webhook,
    ) -> None:
        self.cog: commands.Cog = cog
        self.author: discord.Member = author

        self.channel: typing.Union[discord.TextChannel, discord.VoiceChannel, discord.Thread] = (
            channel
        )
        self.webhook: discord.Webhook = webhook

    async def initialize(self, ctx: commands.Context):
        embed: discord.Embed = discord.Embed(
            title=_("Webhook Session Initiated"),
            description=_("Session Created by {author.display_name} ({author.id}).").format(
                author=self.author
            ),
            color=await ctx.embed_color(),
        )
        try:
            await self.webhook.send(
                embed=embed,
                username="Webhook Session",
                avatar_url="https://imgur.com/BMeddyn.png",
            )
        except (ValueError, discord.HTTPException):
            raise commands.UserFeedbackCheckFailure(
                _("Session initialization failed as provided webhook link was invalid.")
            )
        else:
            self.cog.webhook_sessions[self.channel.id] = self
            await self.channel_send(
                _(
                    "I will send all messages in this channel to the webhook until the session is closed with `{ctx.clean_prefix}webhook session close` or there are 2 minutes of inactivity."
                ).format(ctx=ctx),
                embed=embed,
            )

    async def send(self, *args, **kwargs) -> discord.WebhookMessage:
        try:
            return await self.webhook.send(*args, **kwargs)
        except (ValueError, discord.HTTPException):
            await self.close()

    async def channel_send(
        self, content: str = None, **kwargs
    ) -> typing.Optional[discord.Message]:
        if self.channel.permissions_for(self.channel.guild.me).send_messages:
            return await self.channel.send(content, **kwargs)

    async def close(self, *, reason: str = "Webhook session closed."):
        await self.channel_send(reason)
        try:
            del self.cog.webhook_sessions[self.channel.id]
        except KeyError:
            pass


@cog_i18n(_)
class Webhook(Cog):
    """Various webhook commands to create and send messages along webhooks!"""

    __authors__: typing.List[str] = ["PhenoM4n4n", "AAA3A"]

    def __init__(self, bot: Red) -> None:
        super().__init__(bot=bot)

        self.links_cache: typing.Dict[int, discord.Webhook] = {}
        self.webhook_sessions: typing.Dict[int, Session] = {}

    def get_webhook_from_link(
        self, link: typing.Union[discord.Webhook, int, str]
    ) -> typing.Optional[discord.Webhook]:
        if isinstance(link, int):
            return self.links_cache.get(link)
        elif isinstance(link, discord.Webhook):
            if link.id not in self.links_cache:
                self.links_cache[link.id] = link
            return link
        else:
            match = WEBHOOK_RE.search(link)
            if not match:
                raise ValueError(_("That doesn't look like a webhook link."))
            webhook_id = int(match.group("id"))
            if not (webhook := self.links_cache.get(webhook_id)):
                webhook = discord.Webhook.from_url(
                    match.group(0), session=self.bot.http._HTTPClient__session
                )
                self.links_cache[webhook.id] = webhook
            return webhook

    @staticmethod
    async def webhook_error(ctx: commands.Context, error_type: str, error: Exception) -> None:
        embed: discord.Embed = discord.Embed(
            title=f"{error_type}: `{type(error).__name__}`",
            description=box(str(error), lang="py"),
            color=await ctx.embed_color(),
        )
        embed.set_footer(
            text=_(
                "Use `{ctx.prefix}help {ctx.command.qualified_name}` to see an example."
            ).format(ctx=ctx)
        )
        await Menu(pages=[embed]).start(ctx)

    async def check_channel(
        self,
        ctx: commands.Context,
        channel: typing.Union[discord.TextChannel, discord.VoiceChannel, discord.Thread],
    ) -> bool:
        # if (
        #     not channel.permissions_for(ctx.author).manage_webhooks
        #     and ctx.author.id != ctx.guild.owner.id
        #     and ctx.author.id not in ctx.bot.owner_ids
        # ):
        #     raise commands.UserFeedbackCheckFailure(
        #         _(
        #             "I can not let you do that because you don't have the `manage_webhooks` permission."
        #         ).format(channel=channel)
        #     )
        if not channel.permissions_for(ctx.me).manage_webhooks:
            raise commands.UserFeedbackCheckFailure(
                _(
                    "I can not do that because I don't have the `manage_webhooks` permission."
                ).format(channel=channel)
            )
        return True

    @commands.guild_only()
    @commands.admin_or_permissions(manage_webhooks=True)
    @commands.bot_has_permissions(manage_webhooks=True)
    @commands.hybrid_group(aliases=["webhooks"])
    async def webhook(self, ctx: commands.Context) -> None:
        """Various webhook commands to create and send messages along webhooks."""
        pass

    @webhook.command(name="create")
    async def webhook_create(
        self,
        ctx: commands.Context,
        channel: typing.Optional[typing.Union[discord.TextChannel, discord.VoiceChannel]],
        *,
        webhook_name: str = None,
    ) -> None:
        """Creates a webhook in the channel specified with the name specified.

        If no channel is specified then it will default to the current channel.
        """
        channel = channel or ctx.channel
        await self.check_channel(ctx, channel=channel)
        webhook_name = webhook_name or f"{ctx.me.display_name} Webhook"
        try:
            await channel.create_webhook(
                name=webhook_name,
                reason=f"Webhook creation requested by {ctx.author} ({ctx.author.id}).",
            )
        except discord.HTTPException as error:
            await self.webhook_error(ctx, "Webhook Creation Error", error)

    @webhook.command(name="send")
    async def webhook_send(
        self,
        ctx: commands.Context,
        webhook_link: WebhookLinkConverter,
        *,
        content: commands.Range[str, 1, 2000],
    ) -> None:
        """Sends a message to the specified webhook using your display name and you avatar."""
        try:
            await webhook_link.send(
                content=content,
                username=ctx.author.display_name,
                avatar_url=ctx.author.display_avatar,
            )
        except discord.HTTPException as error:
            await self.webhook_error(ctx, "Webhook Creation Error", error)

    @webhook.command(name="say", aliases=["speak"])
    async def webhook_say(
        self,
        ctx: commands.Context,
        channel: typing.Optional[
            typing.Union[discord.TextChannel, discord.VoiceChannel, discord.Thread]
        ],
        *,
        content: commands.Range[str, 1, 2000] = None,
    ) -> None:
        """Sends a message in a channel as a webhook using your display name and your avatar.

        You can attach files to the command.
        """
        channel = channel or ctx.channel
        await self.check_channel(ctx, channel=channel)
        files = await Tunnel.files_from_attatch(ctx.message)
        if not content and not files:
            raise commands.UserInputError()
        try:
            hook = await CogsUtils.get_hook(
                bot=ctx.bot, channel=getattr(channel, "parent", channel)
            )
            await hook.send(
                content=content,
                files=files,
                username=ctx.author.display_name,
                avatar_url=ctx.author.display_avatar,
                thread=channel if isinstance(channel, discord.Thread) else discord.utils.MISSING,
            )
        except discord.HTTPException as error:
            await self.webhook_error(ctx, "Webhook Sending Error", error)

    @webhook.command(name="sudo")
    async def webhook_sudo(
        self,
        ctx: commands.Context,
        channel: typing.Optional[
            typing.Union[discord.TextChannel, discord.VoiceChannel, discord.Thread]
        ],
        member: discord.Member,
        *,
        content: commands.Range[str, 1, 2000] = None,
    ) -> None:
        """Sends a message in a channel as a webhook using the display name and the avatar of a specified member.

        You can attach files to the command.
        """
        channel = channel or ctx.channel
        await self.check_channel(ctx, channel=channel)
        files = await Tunnel.files_from_attatch(ctx.message)
        if not content and not files:
            raise commands.UserInputError()
        try:
            hook = await CogsUtils.get_hook(
                bot=ctx.bot, channel=getattr(channel, "parent", channel)
            )
            await hook.send(
                content=content,
                files=files,
                username=member.display_name,
                avatar_url=member.display_avatar,
                thread=channel if isinstance(channel, discord.Thread) else discord.utils.MISSING,
            )
        except discord.HTTPException as error:
            await self.webhook_error(ctx, "Webhook Sending Error", error)

    @webhook.command(name="reverse")
    async def webhook_reverse(
        self,
        ctx: commands.Context,
        channel: typing.Optional[
            typing.Union[discord.TextChannel, discord.VoiceChannel, discord.Thread]
        ],
        member: discord.Member,
        *,
        content: commands.Range[str, 1, 2000] = None,
    ) -> None:
        channel = channel or ctx.channel
        await self.check_channel(ctx, channel=channel)
        files = await Tunnel.files_from_attatch(ctx.message)
        if not content and not files:
            raise commands.UserInputError()
        try:
            hook = await CogsUtils.get_hook(
                bot=ctx.bot, channel=getattr(channel, "parent", channel)
            )
            await hook.send(
                content=content,
                files=files,
                username=member.display_name[::-1],
                avatar_url=member.display_avatar,
                thread=channel if isinstance(channel, discord.Thread) else discord.utils.MISSING,
            )
        except discord.HTTPException as error:
            await self.webhook_error(ctx, "Webhook Sending Error", error)

    @webhook.command(name="freverse")
    async def webhook_freverse(
        self,
        ctx: commands.Context,
        channel: typing.Optional[
            typing.Union[discord.TextChannel, discord.VoiceChannel, discord.Thread]
        ],
        member: discord.Member,
        *,
        content: commands.Range[str, 1, 2000] = None,
    ) -> None:
        channel = channel or ctx.channel
        await self.check_channel(ctx, channel=channel)
        files = await Tunnel.files_from_attatch(ctx.message)
        if not content and not files:
            raise commands.UserInputError()
        try:
            hook = await CogsUtils.get_hook(
                bot=ctx.bot, channel=getattr(channel, "parent", channel)
            )
            await hook.send(
                content=content[::-1],
                files=files,
                username=member.display_name[::-1],
                avatar_url=member.display_avatar,
                thread=channel if isinstance(channel, discord.Thread) else discord.utils.MISSING,
            )
        except discord.HTTPException as error:
            await self.webhook_error(ctx, "Webhook Sending Error", error)

    @webhook.command(name="reversed")
    async def webhook_reversed(
        self,
        ctx: commands.Context,
        channel: typing.Optional[
            typing.Union[discord.TextChannel, discord.VoiceChannel, discord.Thread]
        ],
        *,
        message: discord.Message,
    ) -> None:
        channel = channel or ctx.channel
        await self.check_channel(ctx, channel=channel)
        files = await Tunnel.files_from_attatch(message)
        try:
            hook = await CogsUtils.get_hook(
                bot=ctx.bot, channel=getattr(channel, "parent", channel)
            )
            await hook.send(
                content=message.content[::-1],
                files=files,
                username=message.author.display_name[::-1],
                avatar_url=message.author.display_avatar,
                thread=channel if isinstance(channel, discord.Thread) else discord.utils.MISSING,
            )
        except discord.HTTPException as error:
            await self.webhook_error(ctx, "Webhook Sending Error", error)

    @webhook.command(name="custom")
    async def webhook_custom(
        self,
        ctx: commands.Context,
        channel: typing.Optional[
            typing.Union[discord.TextChannel, discord.VoiceChannel, discord.Thread]
        ],
        username: commands.Range[str, 1, 80],
        avatar_url: str,
        *,
        content: commands.Range[str, 1, 2000] = None,
    ) -> None:
        """Sends a message a channel as a webhook using a specified display name and a specified avatar url.

        You can attach files to the command.
        """
        channel = channel or ctx.channel
        await self.check_channel(ctx, channel=channel)
        files = await Tunnel.files_from_attatch(ctx.message)
        if not content and not files:
            raise commands.UserInputError()
        try:
            hook = await CogsUtils.get_hook(
                bot=ctx.bot, channel=getattr(channel, "parent", channel)
            )
            await hook.send(
                content=content,
                files=files,
                username=username,
                avatar_url=avatar_url,
                thread=channel if isinstance(channel, discord.Thread) else discord.utils.MISSING,
            )
        except discord.HTTPException as error:
            await self.webhook_error(ctx, "Webhook Sending Error", error)

    @commands.admin_or_permissions(manage_webhooks=True, manage_guild=True)
    @webhook.command(name="clyde", hidden=True)
    async def webhook_clyde(
        self,
        ctx: commands.Context,
        channel: typing.Optional[
            typing.Union[discord.TextChannel, discord.VoiceChannel, discord.Thread]
        ],
        *,
        content: commands.Range[str, 1, 2000] = None,
    ) -> None:
        """Sends a message a channel as a webhook using Clyde's display name and avatar.

        You can attach files to the command.
        """
        channel = channel or ctx.channel
        await self.check_channel(ctx, channel=channel)
        files = await Tunnel.files_from_attatch(ctx.message)
        if not content and not files:
            raise commands.UserInputError()
        try:
            hook = await CogsUtils.get_hook(
                bot=ctx.bot, channel=getattr(channel, "parent", channel)
            )
            await hook.send(
                content=content,
                files=files,
                username="CIyde",
                avatar_url="https://discordapp.com/assets/f78426a064bc9dd24847519259bc42af.png",
                thread=channel if isinstance(channel, discord.Thread) else discord.utils.MISSING,
            )
        except discord.HTTPException as error:
            await self.webhook_error(ctx, "Webhook Sending Error", error)

    @commands.mod_or_permissions(ban_members=True)
    @webhook.command("permissions", aliases=["perms"])
    async def webhook_permissions(self, ctx: commands.Context) -> None:
        """Show all members in the server that have the permission `manage_webhooks`."""
        roles = []
        lines = []
        total_members = set()

        for role in ctx.guild.roles:
            perms = role.permissions
            if perms.administrator or perms.manage_webhooks:
                roles.append(role)
                lines.append(f"**{role.name}** | {role.mention}")
                members = []
                for member in filter(lambda m: m not in total_members, role.members):
                    total_members.add(member)
                    member_string = f"{member.display_name} ({member.id})"
                    if member.bot:
                        member_string = f"[{member_string}](https://www.youtube.com/watch?v=dQw4w9WgXcQ&ab_channel=RickAstleyVEVO 'This user is a bot')"
                    members.append(member_string)
                if members:
                    lines.append(humanize_list(members))

        if not lines:
            raise commands.UserFeedbackCheckFailure(
                _("No one here has the permission `manage_webhooks` other than the owner.")
            )

        embed = discord.Embed(
            color=await ctx.embed_color(), title=_("Members with the permission `manage_webhooks`")
        )
        embed.set_footer(text=f"{len(roles)} roles | {len(total_members)} members")
        embeds = []
        for page in pagify("\n".join(lines)):
            e = embed.copy()
            e.description = page
            embeds.append(e)

        await Menu(pages=embeds).start(ctx)

    @commands.admin_or_permissions(manage_webhooks=True)
    @webhook.command(name="edit")
    async def webhook_edit(
        self, ctx: commands.Context, message: discord.Message, *, content: str = None
    ) -> None:
        """Edit a message sent by a webhook.

        You can attach files to the command.
        """
        if not message.webhook_id:
            raise commands.UserInputError()
        await self.check_channel(ctx, channel=message.channel)
        webhooks = await getattr(message.channel, "parent", message.channel).webhooks()
        webhook = next(
            (
                channel_webhook
                for channel_webhook in webhooks
                if (
                    channel_webhook.type == discord.WebhookType.incoming
                    and channel_webhook.id == message.webhook_id
                )
            ),
            None,
        )
        if not webhook:
            raise commands.UserFeedbackCheckFailure(_("No webhook found for this message."))
        files = await Tunnel.files_from_attatch(ctx.message)
        if not content and not files:
            raise commands.UserInputError()
        try:
            await webhook.edit_message(message.id, content=content, attachments=files)
        except discord.HTTPException as error:
            await self.webhook_error(ctx, "Webhook Editing Error", error)

    @commands.guildowner_or_permissions(administrator=True)
    @commands.bot_has_guild_permissions(manage_webhooks=True)
    @webhook.command(name="clear")
    async def webhook_clear(self, ctx: commands.Context, confirmation: bool = False):
        """Delete all webhooks in this server."""
        webhooks = await ctx.guild.webhooks()
        if not webhooks:
            raise commands.UserFeedbackCheckFailure(_("There are no webhooks in this server."))

        if not confirmation and not ctx.assume_yes:
            embed: discord.Embed = discord.Embed()
            embed.title = _("⚠️ - Webhooks Deletion")
            embed.description = _(
                "This will delete all webhooks in the server. Are you sure you want to do this?"
            )
            embed.color = 0xF00020
            if not await CogsUtils.ConfirmationAsk(
                ctx, content=f"{ctx.author.mention}", embed=embed
            ):
                await CogsUtils.delete_message(ctx.message)
                return

        msg = await ctx.send(_("Deleting all webhooks..."))
        count = 0
        for webhook in webhooks:
            try:
                await webhook.delete(
                    reason=f"Mass webhook deletion requested by {ctx.author} ({ctx.author.id})."
                )
            except ValueError:
                pass
            else:
                count += 1
        try:
            await msg.edit(content=_("{count} webhooks deleted.").format(count=count))
        except discord.NotFound:
            await ctx.send(_("{count} webhooks deleted.").format(count=count))

    @commands.max_concurrency(1, commands.BucketType.channel)
    @webhook.command(name="session")
    async def webhook_session(self, ctx: commands.Context, webhook_link: WebhookLinkConverter):
        """Initiate a session within this channel sending messages to a specified webhook link."""
        if ctx.channel.id in self.webhook_sessions:
            return await ctx.send(
                _(
                    "This channel already has an ongoing session. Use `{ctx.clean_prefix}webhook session close` to close it."
                ).format(ctx=ctx)
            )
        session = Session(cog=self, author=ctx.author, channel=ctx.channel, webhook=webhook_link)
        await session.initialize(ctx)

    @webhook.command(name="closesession", aliases=["sessionclose"])
    async def webhook_closesession(
        self, ctx: commands.Context, channel: discord.TextChannel = None
    ):
        """Close an ongoing webhook session in a channel."""
        channel = channel or ctx.channel
        if (session := self.webhook_sessions.get(channel.id)) is None:
            raise commands.UserFeedbackCheckFailure(
                _(
                    "This channel does not have an ongoing webhook session. Start one with `{ctx.clean_prefix}webhook session`."
                ).format(ctx=ctx)
            )
        await session.close()

    @commands.Cog.listener()
    async def on_message_without_command(self, message: discord.Message):
        if message.author.bot:
            return
        try:
            session: Session = self.webhook_sessions[message.channel.id]
        except KeyError:
            return
        files = await Tunnel.files_from_attatch(message)
        await session.send(
            message.content,
            embeds=message.embeds,
            files=files,
            username=message.author.display_name,
            avatar_url=message.author.display_avatar,
            allowed_mentions=discord.AllowedMentions(everyone=False, users=False, roles=False),
        )

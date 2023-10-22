from AAA3A_utils import Cog, CogsUtils, Menu  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
from redbot.core.bot import Red  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import datetime
import re

from redbot.core.commands.converter import get_timedelta_converter
from redbot.core.utils.chat_formatting import box, pagify

try:
    from emoji import UNICODE_EMOJI_ENGLISH as EMOJI_DATA  # emoji<2.0.0
except ImportError:
    from emoji import EMOJI_DATA  # emoji>=2.0.0

from .view import DiscordEditView

TimedeltaConverter = get_timedelta_converter(
    default_unit="s",
    maximum=datetime.timedelta(seconds=21600),
    minimum=datetime.timedelta(seconds=0),
)


def _(untranslated: str) -> str:  # `redgettext` will found these strings.
    return untranslated


ERROR_MESSAGE = _(
    "I attempted to do something that Discord denied me permissions for. Your command failed to successfully complete.\n{error}"
)

_ = Translator("DiscordEdit", __file__)


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


class ForumTagConverter(discord.ext.commands.Converter):
    async def convert(
        self, ctx: commands.Context, argument: str
    ) -> typing.Tuple[discord.Role, typing.Union[discord.PartialEmoji, str]]:
        arg_split = re.split(r";|,|\||-", argument)
        try:
            try:
                name, emoji, moderated = arg_split
            except Exception:
                name, emoji = arg_split
                moderated = False
        except Exception:
            raise commands.BadArgument(
                _(
                    "Emoji Role must be an emoji followed by a role separated by either `;`, `,`, `|`, or `-`."
                )
            )
        emoji = await Emoji().convert(ctx, emoji.strip())
        return discord.ForumTag(name=name, emoji=emoji, moderated=moderated)


@cog_i18n(_)
class EditThread(Cog):
    """A cog to edit threads!"""

    def __init__(self, bot: Red) -> None:  # Never executed except manually.
        super().__init__(bot=bot)

    async def check_thread(
        self, ctx: commands.Context, thread: typing.Optional[discord.Thread]
    ) -> bool:
        # if (
        #     not thread.permissions_for(ctx.author).manage_channels
        #     and ctx.author.id != ctx.guild.owner.id
        #     and ctx.author.id not in ctx.bot.owner_ids
        #     and ctx.author != thread.owner
        # ):
        #     raise commands.UserFeedbackCheckFailure(
        #         _(
        #             "I can not let you edit the thread {thread.mention} ({thread.id}) because I don't have the `manage_channel` permission."
        #         ).format(thread=thread)
        #     )
        if not thread.permissions_for(ctx.me).manage_channels:
            raise commands.UserFeedbackCheckFailure(
                _(
                    "I can not edit the thread {thread.mention} ({thread.id}) because you don't have the `manage_channel` permission."
                ).format(thread=thread)
            )
        return True

    @commands.guild_only()
    @commands.admin_or_can_manage_channel(allow_thread_owner=True)
    @commands.bot_has_permissions(manage_channels=True)
    @commands.hybrid_group()
    async def editthread(self, ctx: commands.Context) -> None:
        """Commands for edit a text channel."""
        pass

    @commands.admin_or_permissions(manage_channels=True)
    @editthread.command(name="create", aliases=["new", "+"])
    async def editthread_create(
        self,
        ctx: commands.Context,
        channel: typing.Optional[discord.TextChannel] = None,
        message: typing.Optional[commands.MessageConverter] = None,
        *,
        name: commands.Range[str, 1, 100],
    ) -> None:
        """Create a thread.

        You'll join it automatically.
        """
        if channel is None:
            channel = ctx.channel
        try:
            thread = await channel.create_thread(
                name=name,
                message=message,
                reason=f"{ctx.author} ({ctx.author.id}) has created the thread #{name}.",
            )
            await thread.add_user(ctx.author)
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @commands.bot_has_permissions(embed_links=True)
    @editthread.command(name="list")
    async def editthread_list(
        self,
        ctx: commands.Context,
    ) -> None:
        """List all threads in the current guild."""
        description = "\n".join(
            [
                f"**•** {thread.mention} ({thread.id}) - {len(await thread.fetch_members())} members"
                for thread in ctx.guild.threads
            ]
        )
        embed: discord.Embed = discord.Embed(color=await ctx.embed_color())
        embed.title = _("List of threads in {guild.name} ({guild.id})").format(guild=ctx.guild)
        embeds = []
        pages = pagify(description, page_length=4096)
        for page in pages:
            e = embed.copy()
            e.description = page
            embeds.append(e)
        await Menu(pages=embeds).start(ctx)

    @editthread.command(name="name")
    async def editthread_name(
        self,
        ctx: commands.Context,
        thread: typing.Optional[discord.Thread],
        name: commands.Range[str, 1, 100],
    ) -> None:
        """Edit thread name."""
        if thread is None:
            if isinstance(ctx.channel, discord.Thread):
                thread = ctx.channel
            else:
                raise commands.UserInputError()
        await self.check_thread(ctx, thread)
        try:
            await thread.edit(
                name=name,
                reason=f"{ctx.author} ({ctx.author.id}) has edited the thread #{thread.name} ({thread.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @editthread.command(name="archived")
    async def editthread_archived(
        self, ctx: commands.Context, thread: typing.Optional[discord.Thread], archived: bool = None
    ) -> None:
        """Edit thread archived."""
        if thread is None:
            if isinstance(ctx.channel, discord.Thread):
                thread = ctx.channel
            else:
                raise commands.UserInputError()
        await self.check_thread(ctx, thread)
        archived = not thread.archived
        try:
            await thread.edit(
                archived=archived,
                reason=f"{ctx.author} ({ctx.author.id}) has edited the thread #{thread.name} ({thread.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @editthread.command(name="locked")
    async def editthread_locked(
        self, ctx: commands.Context, thread: typing.Optional[discord.Thread], locked: bool = None
    ) -> None:
        """Edit thread locked."""
        if thread is None:
            if isinstance(ctx.channel, discord.Thread):
                thread = ctx.channel
            else:
                raise commands.UserInputError()
        await self.check_thread(ctx, thread)
        if locked is None:
            locked = not thread.locked
        try:
            await thread.edit(
                locked=locked,
                reason=f"{ctx.author} ({ctx.author.id}) has edited the thread #{thread.name} ({thread.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @editthread.command(name="pinned")
    async def editthread_pinned(
        self, ctx: commands.Context, thread: typing.Optional[discord.Thread], pinned: bool
    ) -> None:
        """Edit thread pinned."""
        if thread is None:
            if isinstance(ctx.channel, discord.Thread):
                thread = ctx.channel
            else:
                raise commands.UserInputError()
        await self.check_thread(ctx, thread)
        try:
            await thread.edit(
                pinned=pinned,
                reason=f"{ctx.author} ({ctx.author.id}) has edited the thread #{thread.name} ({thread.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @editthread.command(name="invitable")
    async def editthread_invitable(
        self,
        ctx: commands.Context,
        thread: typing.Optional[discord.Thread],
        invitable: bool = None,
    ) -> None:
        """Edit thread invitable."""
        if thread is None:
            if isinstance(ctx.channel, discord.Thread):
                thread = ctx.channel
            else:
                raise commands.UserInputError()
        await self.check_thread(ctx, thread)
        if invitable is None:
            invitable = not thread.invitable
        try:
            await thread.edit(
                invitable=invitable,
                reason=f"{ctx.author} ({ctx.author.id}) has edited the thread #{thread.name} ({thread.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @editthread.command(name="autoarchiveduration", aliases=["auto_archive_duration"])
    async def editthread_auto_archive_duration(
        self,
        ctx: commands.Context,
        thread: typing.Optional[discord.Thread],
        auto_archive_duration: typing.Literal[60, 1440, 4320, 10080],
    ) -> None:
        """Edit thread auto archive duration."""
        if thread is None:
            if isinstance(ctx.channel, discord.Thread):
                thread = ctx.channel
            else:
                raise commands.UserInputError()
        await self.check_thread(ctx, thread)
        try:
            await thread.edit(
                auto_archive_duration=auto_archive_duration,
                reason=f"{ctx.author} ({ctx.author.id}) has edited the thread #{thread.name} ({thread.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @editthread.command(name="slowmodedelay", aliases=["slowmode_delay"])
    async def editthread_slowmode_delay(
        self,
        ctx: commands.Context,
        thread: typing.Optional[discord.Thread],
        slowmode_delay: TimedeltaConverter,
    ) -> None:
        """Edit thread slowmode delay."""
        if thread is None:
            if isinstance(ctx.channel, discord.Thread):
                thread = ctx.channel
            else:
                raise commands.UserInputError()
        await self.check_thread(ctx, thread)
        try:
            await thread.edit(
                slowmode_delay=slowmode_delay,
                reason=f"{ctx.author} ({ctx.author.id}) has edited the thread #{thread.name} ({thread.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @editthread.command(name="appliedtags", aliases=["applied_tags"])
    async def editthread_applied_tags(
        self,
        ctx: commands.Context,
        thread: typing.Optional[discord.Thread],
        applied_tags: commands.Greedy[ForumTagConverter],
    ) -> None:
        """Edit thread applied tags.

        ```
        [p]editthread appliedtags "<name>|<emoji>|[moderated]"
        [p]editthread appliedtags "Reporting|⚠️|True" "Bug|🐛"
        ```
        """
        if thread is None:
            if isinstance(ctx.channel, discord.Thread):
                thread = ctx.channel
            else:
                raise commands.UserInputError()
        await self.check_thread(ctx, thread)
        try:
            await thread.edit(
                applied_tags=list(applied_tags),
                reason=f"{ctx.author} ({ctx.author.id}) has edited the thread #{thread.name} ({thread.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @editthread.command(name="adduser", aliases=["addmember", "add_user", "add_member"])
    async def editthread_add_user(
        self,
        ctx: commands.Context,
        thread: typing.Optional[discord.Thread],
        member: discord.Member,
    ) -> None:
        """Add member to thread."""
        if thread is None:
            if isinstance(ctx.channel, discord.Thread):
                thread = ctx.channel
            else:
                raise commands.UserInputError()
        if discord.utils.get(await thread.fetch_members(), id=member.id) is not None:
            raise commands.UserFeedbackCheckFailure("This member is already in this thread.")
        await self.check_thread(ctx, thread)
        try:
            await thread.add_user(member)
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @editthread.command(
        name="removeuser", aliases=["removemember", "remove_user", "remove_member"]
    )
    async def editthread_remove_user(
        self,
        ctx: commands.Context,
        thread: typing.Optional[discord.Thread],
        member: discord.Member,
    ) -> None:
        """Remove member from thread."""
        if thread is None:
            if isinstance(ctx.channel, discord.Thread):
                thread = ctx.channel
            else:
                raise commands.UserInputError()
        await self.check_thread(ctx, thread)
        try:
            await thread.remove_user(member)
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @editthread.command(name="delete")
    async def editthread_delete(
        self,
        ctx: commands.Context,
        thread: typing.Optional[discord.Thread],
        confirmation: bool = False,
    ) -> None:
        """Delete a thread."""
        if thread is None:
            if isinstance(ctx.channel, discord.Thread):
                thread = ctx.channel
            else:
                raise commands.UserInputError()
        await self.check_thread(ctx, thread)
        if not confirmation and not ctx.assume_yes:
            if ctx.bot_permissions.embed_links:
                embed: discord.Embed = discord.Embed()
                embed.title = _("⚠️ - Delete thread")
                embed.description = _(
                    "Do you really want to delete the thread {thread.mention} ({thread.id})?"
                ).format(thread=thread)
                embed.color = 0xF00020
                content = ctx.author.mention
            else:
                embed = None
                content = f"{ctx.author.mention} " + _(
                    "Do you really want to delete the thread {thread.mention} ({thread.id})?"
                ).format(thread=thread)
            if not await CogsUtils.ConfirmationAsk(ctx, content=content, embed=embed):
                await CogsUtils.delete_message(ctx.message)
                return
        try:
            await thread.delete()  # Not supported: reason=f"{ctx.author} ({ctx.author.id}) has deleted the thread #{thread.name} ({thread.id})."
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @editthread.command(name="view", aliases=["-"])
    async def editthread_view(self, ctx: commands.Context, thread: discord.Thread = None) -> None:
        """View and edit thread."""
        if thread is None:
            if isinstance(ctx.channel, discord.Thread):
                thread = ctx.channel
            else:
                raise commands.UserInputError()
        await self.check_thread(ctx, thread)
        embed_color = await ctx.embed_color()

        parameters = {
            "name": {"converter": commands.Range[str, 1, 100]},
            "archived": {"converter": bool},
            "locked": {"converter": bool},
            "pinned": {"converter": bool},
            "invitable": {"converter": bool},
            "auto_archive_duration": {"converter": typing.Literal[60, 1440, 4320, 10080]},
            "slowmode_delay": {"converter": commands.Range[int, 0, 21_600]},
        }

        def get_embed() -> discord.Embed:
            embed: discord.Embed = discord.Embed(
                title=f"Thread #{thread.name} ({thread.id})", color=embed_color
            )
            embed.timestamp = datetime.datetime.now(tz=datetime.timezone.utc)
            embed.description = "\n".join(
                [
                    f"• `{parameter}`: {repr(getattr(thread, parameters[parameter].get('attribute_name', parameter)))}"
                    for parameter in parameters
                    if hasattr(thread, parameter)
                ]
            )
            return embed

        await DiscordEditView(
            cog=self,
            _object=thread,
            parameters=parameters,
            get_embed_function=get_embed,
            audit_log_reason=f"{ctx.author} ({ctx.author.id}) has edited the thread #{thread.name} ({thread.id}).",
            _object_qualified_name="Thread",
        ).start(ctx)

from AAA3A_utils import Cog, CogsUtils, Menu  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
from redbot.core.bot import Red  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import datetime

from redbot.core.commands.converter import get_timedelta_converter
from redbot.core.utils.chat_formatting import box, pagify

try:
    from emoji import UNICODE_EMOJI_ENGLISH as EMOJI_DATA  # emoji<2.0.0
except ImportError:
    from emoji import EMOJI_DATA  # emoji>=2.0.0

TimedeltaConverter = get_timedelta_converter(
    default_unit="s",
    maximum=datetime.timedelta(seconds=21600),
    minimum=datetime.timedelta(seconds=0),
)

def _(untranslated: str) -> str:  # `redgettext` will found these strings.
    return untranslated
ERROR_MESSAGE = _("I attempted to do something that Discord denied me permissions for. Your command failed to successfully complete.\n{error}")

_ = Translator("DiscordEdit", __file__)


class Emoji(commands.EmojiConverter):
    async def convert(
        self, ctx: commands.Context, argument: str
    ) -> typing.Union[discord.PartialEmoji, str]:
        argument = argument.strip("\N{VARIATION SELECTOR-16}")
        if argument in EMOJI_DATA:
            return argument
        return await super().convert(ctx, argument)


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
            raise discord.ext.commands.BadArgument(
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
        self.bot: Red = bot

        self.cogsutils: CogsUtils = CogsUtils(cog=self)

    async def check_thread(self, ctx: commands.Context, thread: discord.Thread) -> bool:
        if (
            not self.cogsutils.check_permissions_for(
                channel=thread, user=ctx.author, check=["manage_channel"]
            )
            and ctx.author.id != ctx.guild.owner.id
            and ctx.author.id not in ctx.bot.owner_ids
        ):
            raise commands.UserFeedbackCheckFailure(
                _(
                    "I can not let you edit the thread {thread.mention} ({thread.id}) because I don't have the `manage_channel` permission."
                ).format(thread=thread)
            )
        if not self.cogsutils.check_permissions_for(
            channel=thread, user=ctx.guild.me, check=["manage_channel"]
        ):
            raise commands.UserFeedbackCheckFailure(
                _(
                    "I can not edit the thread {thread.mention} ({thread.id}) because you don't have the `manage_channel` permission."
                ).format(thread=thread)
            )
        return True

    @commands.guild_only()
    @commands.admin_or_permissions(manage_channels=True)
    @commands.hybrid_group()
    async def editthread(self, ctx: commands.Context) -> None:
        """Commands for edit a text channel."""
        pass

    @editthread.command(name="create")
    async def editthread_create(
        self,
        ctx: commands.Context,
        channel: typing.Optional[discord.TextChannel] = None,
        message: typing.Optional[commands.MessageConverter] = None,
        *,
        name: str,
    ) -> None:
        """Create a thread."""
        if channel is None:
            channel = ctx.channel
        try:
            await channel.create_thread(
                name=name,
                message=message,
                reason=f"{ctx.author} ({ctx.author.id}) has created the thread #{name}.",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

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
        self, ctx: commands.Context, thread: discord.Thread, name: str
    ) -> None:
        """Edit thread name."""
        await self.check_thread(ctx, thread)
        try:
            await thread.edit(
                name=name,
                reason=f"{ctx.author} ({ctx.author.id}) has modified the thread #{thread.name} ({thread.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @editthread.command(name="archived")
    async def editthread_archived(
        self, ctx: commands.Context, thread: discord.Thread, archived: bool
    ) -> None:
        """Edit thread archived."""
        await self.check_thread(ctx, thread)
        try:
            await thread.edit(
                archived=archived,
                reason=f"{ctx.author} ({ctx.author.id}) has modified the thread #{thread.name} ({thread.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @editthread.command(name="locked")
    async def editthread_locked(
        self, ctx: commands.Context, thread: discord.Thread, locked: bool
    ) -> None:
        """Edit thread locked."""
        await self.check_thread(ctx, thread)
        try:
            await thread.edit(
                locked=locked,
                reason=f"{ctx.author} ({ctx.author.id}) has modified the thread #{thread.name} ({thread.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @editthread.command(name="pinned")
    async def editthread_pinned(
        self, ctx: commands.Context, thread: discord.Thread, pinned: bool
    ) -> None:
        """Edit thread pinned."""
        await self.check_thread(ctx, thread)
        try:
            await thread.edit(
                pinned=pinned,
                reason=f"{ctx.author} ({ctx.author.id}) has modified the thread #{thread.name} ({thread.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @editthread.command(name="invitable")
    async def editthread_invitable(
        self, ctx: commands.Context, thread: discord.Thread, invitable: bool
    ) -> None:
        """Edit thread invitable."""
        await self.check_thread(ctx, thread)
        try:
            await thread.edit(
                invitable=invitable,
                reason=f"{ctx.author} ({ctx.author.id}) has modified the thread #{thread.name} ({thread.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @editthread.command(name="autoarchiveduration")
    async def editthread_auto_archive_duration(
        self,
        ctx: commands.Context,
        thread: discord.Thread,
        auto_archive_duration: typing.Literal["60", "1440", "4320", "10080"],
    ) -> None:
        """Edit thread auto archive duration."""
        await self.check_thread(ctx, thread)
        try:
            await thread.edit(
                auto_archive_duration=auto_archive_duration,
                reason=f"{ctx.author} ({ctx.author.id}) has modified the thread #{thread.name} ({thread.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @editthread.command(name="slowmodedelay")
    async def editthread_slowmode_delay(
        self, ctx: commands.Context, thread: discord.Thread, slowmode_delay: TimedeltaConverter
    ) -> None:
        """Edit thread slowmode delay."""
        await self.check_thread(ctx, thread)
        try:
            await thread.edit(
                slowmode_delay=slowmode_delay,
                reason=f"{ctx.author} ({ctx.author.id}) has modified the thread #{thread.name} ({thread.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @editthread.command(name="appliedtags")
    async def editthread_applied_tags(
        self,
        ctx: commands.Context,
        thread: discord.Thread,
        applied_tags: commands.Greedy[ForumTagConverter],
    ) -> None:
        """Edit thread applied tags.

        ```
        [p]editthread appliedtags "<name>|<emoji>|[moderated]"
        [p]editthread appliedtags "Reporting|⚠️|True" "Bug|🐛"
        ```
        """
        await self.check_thread(ctx, thread)
        try:
            await thread.edit(
                applied_tags=list(applied_tags),
                reason=f"{ctx.author} ({ctx.author.id}) has modified the thread #{thread.name} ({thread.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @editthread.command(name="delete")
    async def editthread_delete(
        self,
        ctx: commands.Context,
        thread: discord.Thread,
        confirmation: bool = False,
    ) -> None:
        """Delete a thread."""
        await self.check_thread(ctx, thread)
        if not confirmation:
            embed: discord.Embed = discord.Embed()
            embed.title = _("⚠️ - Delete thread")
            embed.description = _(
                "Do you really want to delete the thread {thread.mention} ({thread.id})?"
            ).format(thread=thread)
            embed.color = 0xF00020
            if not await self.cogsutils.ConfirmationAsk(
                ctx, content=f"{ctx.author.mention}", embed=embed
            ):
                await self.cogsutils.delete_message(ctx.message)
                return
        try:
            await thread.delete()  # Not supported: reason=f"{ctx.author} ({ctx.author.id}) has deleted the thread #{thread.name} ({thread.id})."
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

from .AAA3A_utils import CogsUtils  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
from redbot.core.bot import Red  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import datetime

from redbot.core.commands.converter import get_timedelta_converter

TimedeltaConverter = get_timedelta_converter(
    default_unit="s",
    maximum=datetime.timedelta(seconds=21600),
    minimum=datetime.timedelta(seconds=0),
)

if CogsUtils().is_dpy2:  # To remove
    setattr(commands, "Literal", typing.Literal)

_ = Translator("DiscordEdit", __file__)

if CogsUtils().is_dpy2:
    from functools import partial

    hybrid_command = partial(commands.hybrid_command, with_app_command=False)
    hybrid_group = partial(commands.hybrid_group, with_app_command=False)
else:
    hybrid_command = commands.command
    hybrid_group = commands.group


@cog_i18n(_)
class EditTextChannel(commands.Cog):
    """A cog to edit text channels!"""

    def __init__(self, bot: Red):  # Never executed except manually.
        self.bot: Red = bot

        self.cogsutils = CogsUtils(cog=self)

    async def check_text_channel(self, ctx: commands.Context, channel: discord.TextChannel):
        if not self.cogsutils.check_permissions_for(
            channel=channel, user=ctx.guild.me, check=["manage_channel"]
        ):
            await ctx.send(
                _(
                    "I can not let you edit the text channel {channel.mention} ({channel.id}) because I don't have the `manage_channel` permission."
                ).format(**locals())
            )
            return False
        if (
            not self.cogsutils.check_permissions_for(
                channel=channel, user=ctx.author, check=["manage_channel"]
            )
            and ctx.author.id not in ctx.bot.owner_ids
        ):
            await ctx.send(
                _(
                    "I can not edit the text channel {channel.mention} ({channel.id}) because you don't have the `manage_channel` permission."
                ).format(**locals())
            )
            return False
        return True

    @commands.guild_only()
    @commands.admin_or_permissions(manage_channels=True)
    @hybrid_group()
    async def edittextchannel(self, ctx: commands.Context):
        """Commands for edit a text channel."""
        pass

    @edittextchannel.command(name="create")
    async def edittextchannel_create(
        self,
        ctx: commands.Context,
        category: typing.Optional[discord.CategoryChannel] = None,
        *,
        name: str,
    ):
        """Create a text channel."""
        try:
            await ctx.guild.create_text_channel(
                name=name,
                category=category,
                reason=f"{ctx.author} ({ctx.author.id}) has created the text channel #{name}.",
            )
        except discord.HTTPException:
            await ctx.send(
                _(
                    "I attempted to do something that Discord denied me permissions for. Your command failed to successfully complete."
                ).format(**locals())
            )

    @edittextchannel.command(name="clone")
    async def edittextchannel_clone(
        self, ctx: commands.Context, channel: typing.Optional[discord.TextChannel], *, name: str
    ):
        """Clone a text channel."""
        if channel is None:
            channel = ctx.channel
        if not await self.check_text_channel(ctx, channel):
            return
        try:
            await channel.clone(
                name=name,
                reason=f"{ctx.author} ({ctx.author.id}) has cloned the text channel #{channel.name} ({channel.id}).",
            )
        except discord.HTTPException:
            await ctx.send(
                _(
                    "I attempted to do something that Discord denied me permissions for. Your command failed to successfully complete."
                ).format(**locals())
            )

    @edittextchannel.command(name="name")
    async def edittextchannel_name(
        self, ctx: commands.Context, channel: typing.Optional[discord.TextChannel], name: str
    ):
        """Edit text channel name."""
        if channel is None:
            channel = ctx.channel
        if not await self.check_text_channel(ctx, channel):
            return
        try:
            await channel.edit(
                name=name,
                reason=f"{ctx.author} ({ctx.author.id}) has modified the text channel #{channel.name} ({channel.id}).",
            )
        except discord.HTTPException:
            await ctx.send(
                _(
                    "I attempted to do something that Discord denied me permissions for. Your command failed to successfully complete."
                ).format(**locals())
            )

    @edittextchannel.command(name="topic")
    async def edittextchannel_topic(
        self, ctx: commands.Context, channel: typing.Optional[discord.TextChannel], *, topic: str
    ):
        """Edit text channel topic."""
        if channel is None:
            channel = ctx.channel
        if not await self.check_text_channel(ctx, channel):
            return
        try:
            await channel.edit(
                topic=topic,
                reason=f"{ctx.author} ({ctx.author.id}) has modified the text channel #{channel.name} ({channel.id}).",
            )
        except discord.HTTPException:
            await ctx.send(
                _(
                    "I attempted to do something that Discord denied me permissions for. Your command failed to successfully complete."
                ).format(**locals())
            )

    @edittextchannel.command(name="position")
    async def edittextchannel_position(
        self,
        ctx: commands.Context,
        channel: typing.Optional[discord.TextChannel],
        *,
        position: int,
    ):
        """Edit text channel position.

        Warning: Only text channels are taken into account. Channel 1 is the highest positioned text channel.
        Channels cannot be moved to a position that takes them out of their current category.
        """
        if channel is None:
            channel = ctx.channel
        if not await self.check_text_channel(ctx, channel):
            return
        max_guild_text_channels_position = len(
            [c for c in ctx.guild.channels if isinstance(c, discord.TextChannel)]
        )
        if not position > 0 or not position < max_guild_text_channels_position + 1:
            await ctx.send(
                _(
                    "The indicated position must be between 1 and {max_guild_text_channels_position}."
                ).format(**locals())
            )
            return
        position = position - 1
        try:
            await channel.edit(
                position=position,
                reason=f"{ctx.author} ({ctx.author.id}) has modified the text channel #{channel.name} ({channel.id}).",
            )
        except discord.HTTPException:
            await ctx.send(
                _(
                    "I attempted to do something that Discord denied me permissions for. Your command failed to successfully complete."
                ).format(**locals())
            )

    @edittextchannel.command(name="nsfw")
    async def edittextchannel_nsfw(
        self, ctx: commands.Context, channel: typing.Optional[discord.TextChannel], nsfw: bool
    ):
        """Edit text channel nsfw."""
        if channel is None:
            channel = ctx.channel
        if not await self.check_text_channel(ctx, channel):
            return
        try:
            await channel.edit(
                nsfw=nsfw,
                reason=f"{ctx.author} ({ctx.author.id}) has modified the text channel #{channel.name} ({channel.id}).",
            )
        except discord.HTTPException:
            await ctx.send(
                _(
                    "I attempted to do something that Discord denied me permissions for. Your command failed to successfully complete."
                ).format(**locals())
            )

    @edittextchannel.command(name="syncpermissions")
    async def edittextchannel_syncpermissions(
        self,
        ctx: commands.Context,
        channel: typing.Optional[discord.TextChannel],
        sync_permissions: bool,
    ):
        """Edit text channel syncpermissions with category."""
        if channel is None:
            channel = ctx.channel
        if not await self.check_text_channel(ctx, channel):
            return
        try:
            await channel.edit(
                sync_permissions=sync_permissions,
                reason=f"{ctx.author} ({ctx.author.id}) has modified the text channel #{channel.name} ({channel.id}).",
            )
        except discord.HTTPException:
            await ctx.send(
                _(
                    "I attempted to do something that Discord denied me permissions for. Your command failed to successfully complete."
                ).format(**locals())
            )

    @edittextchannel.command(name="category")
    async def edittextchannel_category(
        self,
        ctx: commands.Context,
        channel: typing.Optional[discord.TextChannel],
        category: discord.CategoryChannel,
    ):
        """Edit text channel category."""
        if channel is None:
            channel = ctx.channel
        if not await self.check_text_channel(ctx, channel):
            return
        try:
            await channel.edit(
                category=category,
                reason=f"{ctx.author} ({ctx.author.id}) has modified the text channel #{channel.name} ({channel.id}).",
            )
        except discord.HTTPException:
            await ctx.send(
                _(
                    "I attempted to do something that Discord denied me permissions for. Your command failed to successfully complete."
                ).format(**locals())
            )

    @edittextchannel.command(name="slowmodedelay")
    async def edittextchannel_slowmodedelay(
        self,
        ctx: commands.Context,
        channel: typing.Optional[discord.TextChannel],
        slowmode_delay: TimedeltaConverter,
    ):
        """Edit text channel slowmode delay.

        Specifies the slowmode rate limit for user in this channel, in seconds. A value of 0s disables slowmode. The maximum value possible is 21600s.
        """
        if channel is None:
            channel = ctx.channel
        if not await self.check_text_channel(ctx, channel):
            return
        slowmode_delay = int(slowmode_delay.total_seconds())
        if not slowmode_delay >= 0 or not slowmode_delay <= 21600:
            await ctx.send_help()
            return
        try:
            await channel.edit(
                slowmode_delay=slowmode_delay,
                reason=f"{ctx.author} ({ctx.author.id}) has modified the text channel #{channel.name} ({channel.id}).",
            )
        except discord.HTTPException:
            await ctx.send(
                _(
                    "I attempted to do something that Discord denied me permissions for. Your command failed to successfully complete."
                ).format(**locals())
            )

    @edittextchannel.command(name="type")
    async def edittextchannel_type(
        self,
        ctx: commands.Context,
        channel: typing.Optional[discord.TextChannel],
        type: commands.Literal["0", "5"],
    ):
        """Edit text channel type.

        `text`: 0
        `news`: 5
        Currently, only conversion between ChannelType.text and ChannelType.news is supported. This is only available to guilds that contain NEWS in Guild.features.
        """
        if channel is None:
            channel = ctx.channel
        if not await self.check_text_channel(ctx, channel):
            return
        type = discord.ChannelType(int(type))
        try:
            await channel.edit(
                type=type,
                reason=f"{ctx.author} ({ctx.author.id}) has modified the text channel #{channel.name} ({channel.id}).",
            )
        except discord.HTTPException:
            await ctx.send(
                _(
                    "I attempted to do something that Discord denied me permissions for. Your command failed to successfully complete."
                ).format(**locals())
            )

    @edittextchannel.command(name="defaultautoarchiveduration")
    async def edittextchannel_defaultautoarchiveduration(
        self,
        ctx: commands.Context,
        channel: typing.Optional[discord.TextChannel],
        default_auto_archive_duration: commands.Literal["60", "1440", "4320", "10080"],
    ):
        """Edit text channel default auto archive duration.

        The new default auto archive duration in minutes for threads created in this channel. Must be one of `60`, `1440`, `4320`, or `10080`.
        """
        if channel is None:
            channel = ctx.channel
        if not await self.check_text_channel(ctx, channel):
            return
        try:
            await channel.edit(
                default_auto_archive_duration=int(default_auto_archive_duration),
                reason=f"{ctx.author} ({ctx.author.id}) has modified the text channel #{channel.name} ({channel.id}).",
            )
        except discord.HTTPException:
            await ctx.send(
                _(
                    "I attempted to do something that Discord denied me permissions for. Your command failed to successfully complete."
                ).format(**locals())
            )

    @edittextchannel.command(name="delete")
    async def edittextchannel_delete(
        self,
        ctx: commands.Context,
        channel: typing.Optional[discord.TextChannel],
        confirmation: typing.Optional[bool] = False,
    ):
        """Delete text channel."""
        if channel is None:
            channel = ctx.channel
        if not await self.check_text_channel(ctx, channel):
            return
        if not confirmation:
            embed: discord.Embed = discord.Embed()
            embed.title = _(":warning: - Delete text channel").format(**locals())
            embed.description = _(
                "Do you really want to delete the text channel {channel.mention} ({channel.id})?"
            ).format(**locals())
            embed.color = 0xF00020
            if not await self.cogsutils.ConfirmationAsk(
                ctx, text=f"{ctx.author.mention}", embed=embed
            ):
                await self.cogsutils.delete_message(ctx.message)
                return
        try:
            await channel.delete(
                reason=f"{ctx.author} ({ctx.author.id}) has deleted the text channel #{channel.name} ({channel.id})."
            )
        except discord.HTTPException:
            await ctx.send(
                _(
                    "I attempted to do something that Discord denied me permissions for. Your command failed to successfully complete."
                ).format(**locals())
            )

from .AAA3A_utils import CogsUtils  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
from redbot.core.bot import Red  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

if CogsUtils().is_dpy2:  # To remove
    setattr(commands, "Literal", typing.Literal)

# Credits:
# Thanks to @epic guy on Discord for the basic syntax (command groups, commands) and also commands (await ctx.send, await ctx.author.send, await ctx.message.delete())!
# Thanks to the developers of the cogs I added features to as it taught me how to make a cog! (Chessgame by WildStriker, Captcha by Kreusada, Speak by Epic guy and Rommer by Dav)
# Thanks to all the people who helped me with some commands in the #coding channel of the redbot support server!

_ = Translator("EditTextChannel", __file__)

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

    def __init__(self, bot: Red):
        self.bot: Red = bot

        self.cogsutils = CogsUtils(cog=self)
        self.cogsutils._setup()

    async def check_text_channel(self, ctx: commands.Context, channel: discord.TextChannel):
        if not self.cogsutils.check_permissions_for(channel=channel, user=ctx.guild.me, check=["manage_channel"]):
            await ctx.send(_("I can not let you edit the text channel {channel.mention} ({channel.id}) because I don't have the `manage_channel` permission.").format(**locals()))
            return False
        if not self.cogsutils.check_permissions_for(channel=channel, user=ctx.author, check=["manage_channel"]) and ctx.author.id not in ctx.bot.owner_ids:
            await ctx.send(_("I can not edit the text channel {channel.mention} ({channel.id}) because you don't have the `manage_channel` permission.").format(**locals()))
            return False
        return True

    @commands.guild_only()
    @commands.admin_or_permissions(manage_channels=True)
    @hybrid_group()
    async def edittextchannel(self, ctx: commands.Context):
        """Commands for edit a text channel."""
        pass

    @edittextchannel.command()
    async def create(self, ctx: commands.Context, category: typing.Optional[discord.CategoryChannel]=None, *, name: str):
        """Create a text channel.
        """
        try:
            await ctx.guild.create_text_channel(name=name, category=category, reason=f"{ctx.author} ({ctx.author.id}) has created the text channel #{name}.")
        except discord.HTTPException:
            await ctx.send(_("I attempted to do something that Discord denied me permissions for. Your command failed to successfully complete.").format(**locals()))
        else:
            await ctx.tick(message="Done.")

    @edittextchannel.command()
    async def name(self, ctx: commands.Context, channel: typing.Optional[discord.TextChannel], name: str):
        """Edit text channel name.
        """
        if channel is None:
            channel = ctx.channel
        if not await self.check_text_channel(ctx, channel):
            return
        try:
            await channel.edit(name=name, reason=f"{ctx.author} ({ctx.author.id}) has modified the text channel #{channel.name} ({channel.id}).")
        except discord.HTTPException:
            await ctx.send(_("I attempted to do something that Discord denied me permissions for. Your command failed to successfully complete.").format(**locals()))
        else:
            await ctx.tick(message="Done.")

    @edittextchannel.command()
    async def topic(self, ctx: commands.Context, channel: typing.Optional[discord.TextChannel], *, topic: str):
        """Edit text channel topic.
        """
        if channel is None:
            channel = ctx.channel
        if not await self.check_text_channel(ctx, channel):
            return
        try:
            await channel.edit(topic=topic, reason=f"{ctx.author} ({ctx.author.id}) has modified the text channel #{channel.name} ({channel.id}).")
        except discord.HTTPException:
            await ctx.send(_("I attempted to do something that Discord denied me permissions for. Your command failed to successfully complete.").format(**locals()))
        else:
            await ctx.tick(message="Done.")

    @edittextchannel.command()
    async def position(self, ctx: commands.Context, channel: typing.Optional[discord.TextChannel], *, position: int):
        """Edit text channel position.
        
        Warning: Only text channels are taken into account. Channel 1 is the highest positioned text channel.
        Channels cannot be moved to a position that takes them out of their current category.
        """
        if channel is None:
            channel = ctx.channel
        if not await self.check_text_channel(ctx, channel):
            return
        max_guild_text_channels_position = len([c for c in ctx.guild.channels if isinstance(c, discord.TextChannel)])
        if not position > 0 or not position < max_guild_text_channels_position + 1:
            await ctx.send(_("The indicated position must be between 1 and {max_guild_text_channels_position}.").format(**locals()))
            return
        position = position - 1
        try:
            await channel.edit(position=position, reason=f"{ctx.author} ({ctx.author.id}) has modified the text channel #{channel.name} ({channel.id}).")
        except discord.HTTPException:
            await ctx.send(_("I attempted to do something that Discord denied me permissions for. Your command failed to successfully complete.").format(**locals()))
        else:
            await ctx.tick(message="Done.")

    @edittextchannel.command()
    async def nsfw(self, ctx: commands.Context, channel: typing.Optional[discord.TextChannel], nsfw: bool):
        """Edit text channel nsfw.
        """
        if channel is None:
            channel = ctx.channel
        if not await self.check_text_channel(ctx, channel):
            return
        try:
            await channel.edit(nsfw=nsfw, reason=f"{ctx.author} ({ctx.author.id}) has modified the text channel #{channel.name} ({channel.id}).")
        except discord.HTTPException:
            await ctx.send(_("I attempted to do something that Discord denied me permissions for. Your command failed to successfully complete.").format(**locals()))
        else:
            await ctx.tick(message="Done.")

    @edittextchannel.command()
    async def syncpermissions(self, ctx: commands.Context, channel: typing.Optional[discord.TextChannel], sync_permissions: bool):
        """Edit text channel syncpermissions with category.
        """
        if channel is None:
            channel = ctx.channel
        if not await self.check_text_channel(ctx, channel):
            return
        try:
            await channel.edit(sync_permissions=sync_permissions, reason=f"{ctx.author} ({ctx.author.id}) has modified the text channel #{channel.name} ({channel.id}).")
        except discord.HTTPException:
            await ctx.send(_("I attempted to do something that Discord denied me permissions for. Your command failed to successfully complete.").format(**locals()))
        else:
            await ctx.tick(message="Done.")

    @edittextchannel.command()
    async def category(self, ctx: commands.Context, channel: typing.Optional[discord.TextChannel], category: discord.CategoryChannel):
        """Edit text channel category.
        """
        if channel is None:
            channel = ctx.channel
        if not await self.check_text_channel(ctx, channel):
            return
        try:
            await channel.edit(category=category, reason=f"{ctx.author} ({ctx.author.id}) has modified the text channel #{channel.name} ({channel.id}).")
        except discord.HTTPException:
            await ctx.send(_("I attempted to do something that Discord denied me permissions for. Your command failed to successfully complete.").format(**locals()))
        else:
            await ctx.tick(message="Done.")

    @edittextchannel.command()
    async def slowmodedelay(self, ctx: commands.Context, channel: typing.Optional[discord.TextChannel], slowmode_delay: int):
        """Edit text channel slowmode delay.

        Specifies the slowmode rate limit for user in this channel, in seconds. A value of 0 disables slowmode. The maximum value possible is 21600.
        """
        if channel is None:
            channel = ctx.channel
        if not await self.check_text_channel(ctx, channel):
            return
        if not slowmode_delay > 0 or not slowmode_delay < 21600:
            await ctx.send_help()
            return
        try:
            await channel.edit(slowmode_delay=slowmode_delay, reason=f"{ctx.author} ({ctx.author.id}) has modified the text channel #{channel.name} ({channel.id}).")
        except discord.HTTPException:
            await ctx.send(_("I attempted to do something that Discord denied me permissions for. Your command failed to successfully complete.").format(**locals()))
        else:
            await ctx.tick(message="Done.")

    @edittextchannel.command()
    async def type(self, ctx: commands.Context, channel: typing.Optional[discord.TextChannel], type: commands.Literal["0", "5"]):
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
            await channel.edit(type=type, reason=f"{ctx.author} ({ctx.author.id}) has modified the text channel #{channel.name} ({channel.id}).")
        except discord.HTTPException:
            await ctx.send(_("I attempted to do something that Discord denied me permissions for. Your command failed to successfully complete.").format(**locals()))
        else:
            await ctx.tick(message="Done.")

    @edittextchannel.command()
    async def defaultautoarchiveduration(self, ctx: commands.Context, channel: typing.Optional[discord.TextChannel], default_auto_archive_duration: commands.Literal["60", "1440", "4320", "10080"]):
        """Edit text channel default auto archive duration.
        
        The new default auto archive duration in minutes for threads created in this channel. Must be one of `60`, `1440`, `4320`, or `10080`.
        """
        if channel is None:
            channel = ctx.channel
        if not await self.check_text_channel(ctx, channel):
            return
        try:
            await channel.edit(default_auto_archive_duration=int(default_auto_archive_duration), reason=f"{ctx.author} ({ctx.author.id}) has modified the text channel #{channel.name} ({channel.id}).")
        except discord.HTTPException:
            await ctx.send(_("I attempted to do something that Discord denied me permissions for. Your command failed to successfully complete.").format(**locals()))
        else:
            await ctx.tick(message="Done.")

    @edittextchannel.command()
    async def delete(self, ctx: commands.Context, channel: typing.Optional[discord.TextChannel], confirmation: typing.Optional[bool]=False):
        """Delete text channel.
        """
        if channel is None:
            channel = ctx.channel
        if not await self.check_text_channel(ctx, channel):
            return
        if not confirmation:
            embed: discord.Embed = discord.Embed()
            embed.title = _(":warning: - Delete text channel").format(**locals())
            embed.description = _("Do you really want to delete the text channel {channel.mention} ({channel.id})?").format(**locals())
            embed.color = 0xf00020
            if not await self.cogsutils.ConfirmationAsk(ctx, text=f"{ctx.author.mention}", embed=embed):
                await self.cogsutils.delete_message(ctx.message)
                return
        try:
            await channel.delete(reason=f"{ctx.author} ({ctx.author.id}) has deleted the text channel #{channel.name} ({channel.id}).")
        except discord.HTTPException:
            await ctx.send(_("I attempted to do something that Discord denied me permissions for. Your command failed to successfully complete.").format(**locals()))
        else:
            await ctx.tick(message="Done.")
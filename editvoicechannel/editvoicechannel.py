from .AAA3A_utils.cogsutils import CogsUtils  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
from redbot.core.bot import Red  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

# Credits:
# Thanks to @epic guy on Discord for the basic syntax (command groups, commands) and also commands (await ctx.send, await ctx.author.send, await ctx.message.delete())!
# Thanks to the developers of the cogs I added features to as it taught me how to make a cog! (Chessgame by WildStriker, Captcha by Kreusada, Speak by Epic guy and Rommer by Dav)
# Thanks to all the people who helped me with some commands in the #coding channel of the redbot support server!

_ = Translator("EditVoiceChannel", __file__)

@cog_i18n(_)
class EditVoiceChannel(commands.Cog):
    """A cog to edit voice channels!"""

    def __init__(self, bot):
        self.bot: Red = bot

        self.cogsutils = CogsUtils(cog=self)
        self.cogsutils._setup()

    async def check_voice_channel(self, ctx: commands.Context, channel: discord.VoiceChannel):
        if not self.cogsutils.check_permissions_for(channel=channel, user=ctx.guild.me, check=["manage_channel"]):
            await ctx.send(_("I can not let you edit the voice channel {channel.mention} ({channel.id}) because I don't have the `manage_channel` permission.").format(**locals()))
            return False
        if not self.cogsutils.check_permissions_for(channel=channel, user=ctx.author, check=["manage_channel"]) and ctx.author.id not in ctx.bot.owner_ids:
            await ctx.send(_("I can not edit the voice channel {channel.mention} ({channel.id}) because you don't have the `manage_channel` permission.").format(**locals()))
            return False
        return True

    @commands.guild_only()
    @commands.admin_or_permissions(manage_channels=True)
    @commands.group(aliases=["editvoiceroom"])
    async def editvoicechannel(self, ctx: commands.Context):
        """Commands for edit a voice channel."""
        pass

    @editvoicechannel.command()
    async def name(self, ctx: commands.Context, channel: discord.VoiceChannel, name: str):
        """Edit voice channel name.
        """
        if not await self.check_voice_channel(ctx, channel):
            return
        try:
            await channel.edit(name=name, reason=f"{ctx.author} ({ctx.author.id}) has modified the voice channel #!{channel.name} ({channel.id}).")
        except discord.HTTPException:
            await ctx.send(_("I attempted to do something that Discord denied me permissions for. Your command failed to successfully complete.").format(**locals()))
        else:
            await ctx.tick()

    @editvoicechannel.command()
    async def bitrate(self, ctx: commands.Context, channel: discord.VoiceChannel, bitrate: int):
        """Edit voice channel bitrate.

        It must be a number between 8000 and
        Level 1: 128000
        Level 2: 256000
        Level 3: 384000
        """
        if not await self.check_voice_channel(ctx, channel):
            return
        if not bitrate > 7999 or not bitrate < ctx.guild.bitrate_limit + 1:
            await ctx.send_help()
            return
        try:
            await channel.edit(bitrate=bitrate, reason=f"{ctx.author} ({ctx.author.id}) has modified the voice channel #!{channel.name} ({channel.id}).")
        except discord.HTTPException:
            await ctx.send(_("I attempted to do something that Discord denied me permissions for. Your command failed to successfully complete.").format(**locals()))
        else:
            await ctx.tick()

    @editvoicechannel.command()
    async def nsfw(self, ctx: commands.Context, channel: discord.VoiceChannel, nsfw: bool):
        """Edit voice channel nsfw.
        """
        if not await self.check_voice_channel(ctx, channel):
            return
        try:
            await channel.edit(nsfw=nsfw, reason=f"{ctx.author} ({ctx.author.id}) has modified the voice channel #!{channel.name} ({channel.id}).")
        except discord.HTTPException:
            await ctx.send(_("I attempted to do something that Discord denied me permissions for. Your command failed to successfully complete.").format(**locals()))
        else:
            await ctx.tick()

    @editvoicechannel.command()
    async def userlimit(self, ctx: commands.Context, channel: discord.VoiceChannel, user_limit: int):
        """Edit voice channel user limit.

        It must be a number between 0 and 99.
        """
        if not await self.check_voice_channel(ctx, channel):
            return
        if not user_limit > -1 or not user_limit < 100:
            await ctx.send_help()
            return
        try:
            await channel.edit(user_limit=user_limit, reason=f"{ctx.author} ({ctx.author.id}) has modified the voice channel #!{channel.name} ({channel.id}).")
        except discord.HTTPException:
            await ctx.send(_("I attempted to do something that Discord denied me permissions for. Your command failed to successfully complete.").format(**locals()))
        else:
            await ctx.tick()

    @editvoicechannel.command()
    async def position(self, ctx: commands.Context, channel: discord.VoiceChannel, *, position: int):
        """Edit voice channel position.
        
        Warning: Only voice channels are taken into account. Channel 1 is the highest positioned voice channel.
        Channels cannot be moved to a position that takes them out of their current category.
        """
        if not await self.check_voice_channel(ctx, channel):
            return
        max_guild_voice_channels_position = len([c for c in ctx.guild.channels if isinstance(c, discord.VoiceChannel)])
        if not position > 0 or not position < max_guild_voice_channels_position + 1:
            await ctx.send(_("The indicated position must be between 1 and {max_guild_voice_channels_position}.").format(**locals()))
            return
        position = position - 1
        try:
            await channel.edit(position=position, reason=f"{ctx.author} ({ctx.author.id}) has modified the voice channel !{channel.name} ({channel.id}).")
        except discord.HTTPException:
            await ctx.send(_("I attempted to do something that Discord denied me permissions for. Your command failed to successfully complete.").format(**locals()))
        else:
            await ctx.tick()

    @editvoicechannel.command()
    async def syncpermissions(self, ctx: commands.Context, channel: discord.VoiceChannel, sync_permissions: bool):
        """Edit voice channel sync permissions.
        """
        if not await self.check_voice_channel(ctx, channel):
            return
        try:
            await channel.edit(sync_permissions=sync_permissions, reason=f"{ctx.author} ({ctx.author.id}) has modified the voice channel #!{channel.name} ({channel.id}).")
        except discord.HTTPException:
            await ctx.send(_("I attempted to do something that Discord denied me permissions for. Your command failed to successfully complete.").format(**locals()))
        else:
            await ctx.tick()

    @editvoicechannel.command()
    async def category(self, ctx: commands.Context, channel: discord.VoiceChannel, category: discord.CategoryChannel):
        """Edit voice channel category.
        """
        if not await self.check_voice_channel(ctx, channel):
            return
        try:
            await channel.edit(category=category, reason=f"{ctx.author} ({ctx.author.id}) has modified the voice channel #!{channel.name} ({channel.id}).")
        except discord.HTTPException:
            await ctx.send(_("I attempted to do something that Discord denied me permissions for. Your command failed to successfully complete.").format(**locals()))
        else:
            await ctx.tick()

    @editvoicechannel.command()
    async def videoqualitymode(self, ctx: commands.Context, channel: discord.VoiceChannel, video_quality_mode: typing.Literal[1, 2]):
        """Edit voice channel video quality mode.

        auto = 1
        full = 2
        """
        if not await self.check_voice_channel(ctx, channel):
            return
        video_quality_mode = discord.VideoQualityMode(video_quality_mode)
        try:
            await channel.edit(video_quality_mode=video_quality_mode, reason=f"{ctx.author} ({ctx.author.id}) has modified the voice channel #!{channel.name} ({channel.id}).")
        except discord.HTTPException:
            await ctx.send(_("I attempted to do something that Discord denied me permissions for. Your command failed to successfully complete.").format(**locals()))
        else:
            await ctx.tick()

    @editvoicechannel.command()
    async def delete(self, ctx: commands.Context, channel: discord.VoiceChannel, confirmation: typing.Optional[bool]=False):
        """Delete voice channel.
        """
        if not await self.check_voice_channel(ctx, channel):
            return
        if not confirmation:
            embed: discord.Embed = discord.Embed()
            embed.title = _(":warning: - Delete voice channel").format(**locals())
            embed.description = _("Do you really want to delete the voice channel {channel.mention} ({channel.id})?").format(**locals())
            embed.color = 0xf00020
            if not await self.cogsutils.ConfirmationAsk(ctx, text=f"{ctx.author.mention}", embed=embed):
                await self.cogsutils.delete_message(ctx.message)
                return
        try:
            await channel.delete(reason=f"{ctx.author} ({ctx.author.id}) has deleted the voice channel #!{channel.name} ({channel.id}).")
        except discord.HTTPException:
            await ctx.send(_("I attempted to do something that Discord denied me permissions for. Your command failed to successfully complete.").format(**locals()))
        else:
            await ctx.tick()
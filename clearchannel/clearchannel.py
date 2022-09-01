from .AAA3A_utils import CogsUtils  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
from redbot.core.bot import Red  # isort:skip
import discord  # isort:skip

from redbot.core import Config

# Credits:
# Thanks to @epic guy on Discord for the basic syntax (command groups, commands) and also commands (await ctx.send, await ctx.author.send, await ctx.message.delete())!
# Thanks to the developers of the cogs I added features to as it taught me how to make a cog! (Chessgame by WildStriker, Captcha by Kreusada, Speak by Epic guy and Rommer by Dav)
# Thanks to all the people who helped me with some commands in the #coding channel of the redbot support server!

_ = Translator("ClearChannel", __file__)

if CogsUtils().is_dpy2:
    from functools import partial
    hybrid_command = partial(commands.hybrid_command, with_app_command=False)
    hybrid_group = partial(commands.hybrid_group, with_app_command=False)
else:
    hybrid_command = commands.command
    hybrid_group = commands.group

@cog_i18n(_)
class ClearChannel(commands.Cog):
    """A cog to transfer all messages channel in a other channel!"""

    def __init__(self, bot: Red):
        self.bot: Red = bot

        self.config: Config = Config.get_conf(
            self,
            identifier=837018163805,
            force_registration=True,
        )
        self.clearchannel_guild = {
            "channel_delete": True,
            "first_message": True,
            "author_dm": False,
        }
        self.config.register_guild(**self.clearchannel_guild)

        self.cogsutils = CogsUtils(cog=self)
        self.cogsutils._setup()

    @commands.guild_only()
    @commands.guildowner()
    @commands.bot_has_permissions(manage_channels=True)
    @hybrid_command(name="clearchannel")
    async def cleanup_channel(
        self, ctx: commands.Context, confirmation: bool=False
    ):
        """Delete ALL messages from the current channel by duplicating it and then deleting it.
        For security reasons, only the server owner and the bot owner can use the command. Use the "permissions" tool for more options.
        """
        config = await self.config.guild(ctx.guild).all()
        actual_author_dm = config["author_dm"]
        actual_channel_delete = config["channel_delete"]
        actual_first_message = config["first_message"]

        old_channel = ctx.channel
        channel_position = old_channel.position

        if not confirmation:
            embed: discord.Embed = discord.Embed()
            embed.title = _(":warning: - ClearChannel").format(**locals())
            embed.description = _("Do you really want to delete ALL messages from channel {old_channel.mention} ({old_channel.id})?").format(**locals())
            embed.color = 0xf00020
            if not await self.cogsutils.ConfirmationAsk(ctx, text=f"{ctx.author.mention}", embed=embed):
                await self.cogsutils.delete_message(ctx.message)
                return

        new_channel = await old_channel.clone(reason=_("Clear Channel requested by {ctx.author} ({ctx.author.id}).").format(**locals()))
        if actual_channel_delete:
            await old_channel.delete(reason=_("Clear Channel requested by {ctx.author} ({ctx.author.id}).").format(**locals()))
        else:
            await old_channel.edit(name=_("🗑️-Deleted-{old_channel.name}").format(**locals()), position=len(ctx.guild.channels), reason=_("Clear Channel requested by {ctx.author} ({ctx.author.id}).").format(**locals()))
        await new_channel.edit(position=channel_position, reason=_("Clear Channel requested by {ctx.author} ({ctx.author.id}).").format(**locals()))
        self.log.info(
            _("%s (%s) deleted ALL messages in channel %s (%s).").format(**locals()),
            ctx.author,
            ctx.author.id,
            ctx.channel,
            ctx.channel.id,
        )
        if actual_first_message:
            embed: discord.Embed = discord.Embed()
            embed.title = _("ClearChannel").format(**locals())
            embed.description = _("ALL the messages in this channel have been deleted...").format(**locals())
            embed.color = 0xf00020
            embed.set_author(name=ctx.author, url=ctx.author.display_avatar if self.cogsutils.is_dpy2 else ctx.author.avatar_url, icon_url=ctx.author.display_avatar if self.cogsutils.is_dpy2 else ctx.author.avatar_url)
            message = await new_channel.send(embed=embed)
        if actual_author_dm:
            await ctx.author.send(_("All messages in channel #{old_channel.name} ({old_channel.id}) have been deleted! You can find the new channel, with the same permissions: #{new_channel.name} ({new_channel.id}).").format(**locals()))

    @commands.guild_only()
    @commands.guildowner()
    @hybrid_group(name="setclearchannel", aliases=["clearchannelset"])
    async def configuration(self, ctx: commands.Context):
        """Configure ClearChannel for your server."""

    @configuration.command(name="channeldelete", aliases=["delete"], usage="<true_or_false>")
    async def channeldelete(self, ctx: commands.Context, state: bool):
        """Enable or disable Channel Delete
        If this option is enabled, the bot will not delete the original channel: it will duplicate it as normal, but move it to the end of the server's channel list.
        Use `True` (Or `yes`) to enable or `False` (or `no`) to disable.
        """
        if not ctx.author.id == ctx.guild.owner.id:
            await ctx.send(_("Only the owner of this server can access these commands!").format(**locals()))
            return

        config = await self.config.guild(ctx.guild).all()

        actual_channel_delete = config["channel_delete"]
        if actual_channel_delete is state:
            await ctx.send(_("Channel Delete is already set on {state}.").format(**locals()))
            return

        await self.config.guild(ctx.guild).channel_delete.set(state)
        await ctx.send(_("Channel Delete state registered: {state}.").format(**locals()))

    @configuration.command(name="firstmessage", aliases=["message"], usage="<true_or_false>")
    async def firstmessage(self, ctx: commands.Context, state: bool):
        """Enable or disable First Message
        If this option is enabled, the bot will send a message to the emptied channel to warn that it has been emptied.
        Use `True` (Or `yes`) to enable or `False` (or `no`) to disable.
        """
        if not ctx.author.id == ctx.guild.owner.id:
            await ctx.send(_("Only the owner of this server can access these commands!").format(**locals()))
            return

        config = await self.config.guild(ctx.guild).all()

        actual_first_message = config["first_message"]
        if actual_first_message is state:
            await ctx.send(_("First Message is already set on {state}.").format(**locals()))
            return

        await self.config.guild(ctx.guild).first_message.set(state)
        await ctx.send(f"First Message state registered: {state}.")

    @configuration.command(name="authordm", aliases=["dmauthor"], usage="<true_or_false>")
    async def authordm(self, ctx: commands.Context, state: bool):
        """Enable or disable Author dm
        If this option is enabled, the bot will try to send a dm to the author of the order to confirm that everything went well.
        Use `True` (Or `yes`) to enable or `False` (or `no`) to disable.
        """
        if not ctx.author.id == ctx.guild.owner.id:
            await ctx.send(_("Only the owner of this server can access these commands!").format(**locals()))
            return

        config = await self.config.guild(ctx.guild).all()

        actual_author_dm = config["author_dm"]
        if actual_author_dm is state:
            await ctx.send(_("Author dm is already set on {state}.").format(**locals()))
            return

        await self.config.guild(ctx.guild).author_dm.set(state)
        await ctx.send(_("Author dm state registered: {state}.").format(**locals()))
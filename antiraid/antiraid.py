from random import choice

import discord, typing, logging, datetime
from typing import Sequence, Union, cast, Optional, Tuple, Dict, List, Any
from redbot.core import checks, Config, commands, data_manager
from copy import copy

# Credits:
# Thanks to @epic guy on Discord for the basic syntax (command groups, commands) and also commands (await ctx.send, await ctx.author.send, await ctx.message.delete())!
# Thanks to TrustyJAID for the code (a bit modified to work here and to improve as needed) for the log messages sent! (https://github.com/TrustyJAID/Trusty-cogs/tree/master/extendedmodlog)
# Thanks to the developers of the cogs I added features to as it taught me how to make a cog! (Chessgame by WildStriker, Captcha by Kreusada, Speak by Epic guy and Rommer by Dav)
# Thanks to all the people who helped me with some commands in the #coding channel of the redbot support server!

class AntiRaid(commands.Cog):
    """A cog to remove all permissions from a person who deletes a channel!"""

    def __init__(self, bot):
        self.bot = bot
        self.data: Config = Config.get_conf(
            self,
            identifier=947269490247,
            force_registration=True,
        )
        self.cmd_guild = {
            "logschannel": None, # The channel for logs.
            "enabled": False, # Enable the possibility.
            "user_dm": True, # Enable the user dm.
            "bots": True, # Enable bots.
        }

        self.data.register_guild(**self.cmd_guild)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, old_channel: discord.abc.GuildChannel):
        """Remove all permissions from a user if they delete a channel.
        """
        config = await self.data.guild(old_channel.guild).all()
        logschannel = config["logschannel"]
        actual_state_enabled = config["enabled"]
        actual_state_user_dm = config["user_dm"]
        actual_state_bots = config["bots"]
        perp, reason = await self.get_audit_log_reason(
            old_channel.guild, old_channel, discord.AuditLogAction.channel_delete
        )
        if perp.id == old_channel.guild.owner.id:
            return
        if not actual_state_bots:
            if perp.bot:
                return
        if actual_state_enabled:
            rolelist_name = [r.name for r in perp.roles if r != old_channel.guild.default_role]
            rolelist_mention = [r.mention for r in perp.roles if r != old_channel.guild.default_role]
            if actual_state_user_dm:
                await perp.send(f"All your roles have been taken away because you have deleted channel #{old_channel}.\nYour former roles: {rolelist_name}")
            for r in perp.roles:
                if r != old_channel.guild.default_role:
                    await perp.remove_roles(r)
            if logschannel:
                embed: discord.Embed = discord.Embed()
                embed.title = f"The user {perp.name}#{perp.discriminator} has deleted the channel #{old_channel.name}!"
                embed.description = f"To prevent him from doing anything else, I took away as many roles as my current permissions would allow.\nUser mention: {perp.mention} - User ID: {perp.id}"
                embed.color = discord.Colour.dark_teal()
                embed.set_author(name=perp, url=perp.avatar_url, icon_url=perp.avatar_url)
                embed.add_field(
                    inline=False,
                    name="Before I intervened, the user had the following roles:",
                    value=rolelist_mention)
                logschannel = self.bot.get_channel(logschannel)
                await logschannel.send(embed=embed)
        else:
            return

    async def get_audit_log_reason(
        self,
        guild: discord.Guild,
        target: Union[discord.abc.GuildChannel, discord.Member, discord.Role],
        action: discord.AuditLogAction,
    ) -> Tuple[Optional[discord.abc.User], Optional[str]]:
        perp = None
        reason = None
        if guild.me.guild_permissions.view_audit_log:
            async for log in guild.audit_logs(limit=5, action=action):
                if log.target.id == target.id:
                    perp = log.user
                    if log.reason:
                        reason = log.reason
                    break
        return perp, reason

    @commands.guildowner()
    @commands.group(name="setantiraid", aliases=["antiraidset"])
    async def config(self, ctx):
        """Configure AntiRaid for your server."""

    @config.command(aliases=["lchann", "lchannel", "logschan", "logchannel", "logsc"], usage="<text_channel_or_'none'>")
    async def logschannel(self, ctx, *, channel: typing.Optional[discord.TextChannel]=None):
        """Set a channel where events are registered.

        ``channel``: Text channel.
        You can also use "None" if you wish to remove the logging channel.
        """
        if not ctx.author.id == ctx.guild.owner.id:
            await ctx.send("Only the owner of this server can access these commands!")
            return

        if channel is None:
            await self.data.guild(ctx.guild).logschannel.clear()
            await ctx.send("Logging channel removed.")
            return

        needperm = await self.check_permissions_in_channel(["embed_links", "read_messages", "read_message_history", "send_messages", "attach_files"], channel)
        if needperm:
            await ctx.send("The bot does not have at least one of the following permissions in this channel: `embed_links`, `read_messages`, `read_message_history`, `send_messages`, `attach_files`.")
            return

        await self.data.guild(ctx.guild).logschannel.set(channel.id)
        await ctx.send(f"Logging channel registered: {channel.mention}.")

    async def check_permissions_in_channel(self, permissions: List[str], channel: discord.TextChannel):
        """Function to checks if the permissions are available in a guild.
        This will return a list of the missing permissions.
        """
        return [
            permission
            for permission in permissions
            if not getattr(channel.permissions_for(channel.guild.me), permission)
        ]

    @config.command(name="enable", aliases=["activate"], usage="<true_or_false>")
    async def enable(self, ctx, state: bool):
        """Enable or disable AntiRaid.

        Use `True` (Or `yes`) to enable or `False` (or `no`) to disable.
        """
        if not ctx.author.id == ctx.guild.owner.id:
            await ctx.send("Only the owner of this server can access these commands!")
            return

        config = await self.data.guild(ctx.guild).all()

        actual_state_enabled = config["enabled"]
        if actual_state_enabled is state:
            await ctx.send(f"AntiRaid is already set on {state}.")
            return

        await self.data.guild(ctx.guild).enabled.set(state)
        await ctx.send(f"AntiRaid state registered: {state}.")

    @config.command(name="userdm", aliases=["dm"], usage="<true_or_false>")
    async def userdm(self, ctx, state: bool):
        """Enable or disable User DM.

        Use `True` (Or `yes`) to enable or `False` (or `no`) to disable.
        """
        if not ctx.author.id == ctx.guild.owner.id:
            await ctx.send("Only the owner of this server can access these commands!")
            return

        config = await self.data.guild(ctx.guild).all()

        actual_state_user_dm = config["user_dm"]
        if actual_state_user_dm is state:
            await ctx.send(f"User DM is already set on {state}.")
            return

        await self.data.guild(ctx.guild).user_dm.set(state)
        await ctx.send(f"User DM state registered: {state}.")

    @config.command(name="bots", aliases=["nobots"], usage="<true_or_false>")
    async def bots(self, ctx, state: bool):
        """Enable or disable Bots.

        Use `True` (Or `yes`) to enable or `False` (or `no`) to disable.
        """
        if not ctx.author.id == ctx.guild.owner.id:
            await ctx.send("Only the owner of this server can access these commands!")
            return

        config = await self.data.guild(ctx.guild).all()

        actual_state_bots = config["bots"]
        if actual_state_bots is state:
            await ctx.send(f"Bots is already set on {state}.")
            return

        await self.data.guild(ctx.guild).bots.set(state)
        await ctx.send(f"Bots state registered: {state}.")

from .AAA3A_utils.cogsutils import CogsUtils
import discord
import typing
from typing import List, Optional, Tuple, Union
from redbot.core import Config, commands

# Credits:
# Thanks to @epic guy on Discord for the basic syntax (command groups, commands) and also commands (await ctx.send, await ctx.author.send, await ctx.message.delete())!
# Thanks to TrustyJAID for the code (a bit modified to work here and to improve as needed) for the log messages sent! (https://github.com/TrustyJAID/Trusty-cogs/tree/master/extendedmodlog)
# Thanks to the developers of the cogs I added features to as it taught me how to make a cog! (Chessgame by WildStriker, Captcha by Kreusada, Speak by Epic guy and Rommer by Dav)
# Thanks to all the people who helped me with some commands in the #coding channel of the redbot support server!

class AntiNuke(commands.Cog):
    """A cog to remove all permissions from a person who deletes a channel!"""

    def __init__(self, bot):
        self.bot = bot
        self.config: Config = Config.get_conf(
            self,
            identifier=947269490247,
            force_registration=True,
        )
        self.antinuke_guild = {
            "logschannel": None, # The channel for logs.
            "enabled": False, # Enable the possibility.
            "user_dm": True, # Enable the user dm.
            "number_detected_member": 1, # Number.
            "number_detected_bot": 1, # Number.
        }
        self.antinuke_member = {
            "count": 0, # The count of channel's deletes.
            "old_roles": [], # The roles to be handed in if it wasn't a nuke.
        }

        self.config.register_guild(**self.antinuke_guild)
        self.config.register_member(**self.antinuke_member)

        self.cogsutils = CogsUtils(cog=self)
        self.cogsutils._setup()

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, old_channel: discord.abc.GuildChannel):
        """Remove all permissions from a user if they delete a channel.
        """
        config = await self.config.guild(old_channel.guild).all()
        logschannel = config["logschannel"]
        actual_state_enabled = config["enabled"]
        actual_state_user_dm = config["user_dm"]
        actual_number_detected_member = config["number_detected_member"]
        actual_number_detected_bot = config["number_detected_bot"]
        logschannel = config["logschannel"]
        perp, reason = await self.get_audit_log_reason(
            old_channel.guild, old_channel, discord.AuditLogAction.channel_delete
        )
        logschannel = self.bot.get_channel(logschannel)
        if perp is None:
            return
        if perp == old_channel.guild.owner:
            return
        if perp == old_channel.guild.me:
            return
        actual_count = await self.config.member(perp).count()
        if actual_state_enabled:
            if not perp.bot:
                actual_number_detected = actual_number_detected_member
                if actual_number_detected == 0:
                    return
            else:
                actual_number_detected = actual_number_detected_bot
                if actual_number_detected == 0:
                    return
            actual_count += 1
            if actual_count >= actual_number_detected:
                await self.config.member(perp).count.clear()
                old_roles = perp.roles.copy()
                old_roles.remove(old_channel.guild.default_role)
                old_roles = [
                    r for r in old_roles if r.position < old_channel.guild.me.top_role.position and not r.managed
                ]
                rolelist_name = [r.name for r in old_roles]
                rolelist_mention = [r.mention for r in old_roles]
                if actual_state_user_dm:
                    await perp.send(f"All your roles have been taken away because you have deleted channel #{old_channel}.\nYour former roles: {rolelist_name}")
                if old_channel.guild.me.guild_permissions.manage_roles:
                    # await perp.edit(roles=[], reason=f"All roles in {perp} ({perp.id}) roles have been removed as a result of the antinuke system being triggered on this server.")
                    for role in old_roles:
                        try:
                            await perp.remove_roles(role, reason=f"All roles in {perp} ({perp.id}) roles have been removed as a result of the antinuke system being triggered on this server.")
                        except Exception:
                            pass
                    await self.config.member(perp).old_roles.set(old_roles)
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
                await self.config.member(perp).count.set(actual_count)
                return
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

    @commands.guild_only()
    @commands.guildowner()
    @commands.group(name="setantinuke", aliases=["antinukeset"])
    async def configuration(self, ctx: commands.Context):
        """Configure AntiNuke for your server."""

    @configuration.command(aliases=["lchann", "lchannel", "logschan", "logchannel", "logsc"], usage="<text_channel_or_'none'>")
    async def logschannel(self, ctx: commands.Context, *, channel: typing.Optional[discord.TextChannel]=None):
        """Set a channel where events are registered.

        ``channel``: Text channel.
        You can also use "None" if you wish to remove the logging channel.
        """
        if not ctx.author.id == ctx.guild.owner.id:
            await ctx.send("Only the owner of this server can access these commands!")
            return

        if channel is None:
            await self.config.guild(ctx.guild).logschannel.clear()
            await ctx.send("Logging channel removed.")
            return

        needperm = await self.check_permissions_in_channel(["embed_links", "read_messages", "read_message_history", "send_messages", "attach_files"], channel)
        if needperm:
            await ctx.send("The bot does not have at least one of the following permissions in this channel: `embed_links`, `read_messages`, `read_message_history`, `send_messages`, `attach_files`.")
            return

        await self.config.guild(ctx.guild).logschannel.set(channel.id)
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

    @configuration.command(name="enable", aliases=["activate"], usage="<true_or_false>")
    async def enable(self, ctx: commands.Context, state: bool):
        """Enable or disable AntiNuke.

        Use `True` (Or `yes`) to enable or `False` (or `no`) to disable.
        """
        if not ctx.author.id == ctx.guild.owner.id:
            await ctx.send("Only the owner of this server can access these commands!")
            return

        config = await self.config.guild(ctx.guild).all()
        actual_state_enabled = config["enabled"]
        if actual_state_enabled is state:
            await ctx.send(f"AntiNuke is already set on {state}.")
            return

        await self.config.guild(ctx.guild).enabled.set(state)
        await ctx.send(f"AntiNuke state registered: {state}.")

    @configuration.command(name="userdm", aliases=["dm"], usage="<true_or_false>")
    async def userdm(self, ctx: commands.Context, state: bool):
        """Enable or disable User DM.

        Use `True` (Or `yes`) to enable or `False` (or `no`) to disable.
        """
        if not ctx.author.id == ctx.guild.owner.id:
            await ctx.send("Only the owner of this server can access these commands!")
            return

        config = await self.config.guild(ctx.guild).all()

        actual_state_user_dm = config["user_dm"]
        if actual_state_user_dm is state:
            await ctx.send(f"User DM is already set on {state}.")
            return

        await self.config.guild(ctx.guild).user_dm.set(state)
        await ctx.send(f"User DM state registered: {state}.")
        
    @configuration.command(name="nbmember", aliases=["membernb"], usage="<int>")
    async def nbmember(self, ctx: commands.Context, int: int):
        """Number Detected - Member

        Before action, how many deleted channels should be detected?
        `0' to disable this protection.
        """
        if not ctx.author.id == ctx.guild.owner.id:
            await ctx.send("Only the owner of this server can access these commands!")
            return

        config = await self.config.guild(ctx.guild).all()

        await self.config.guild(ctx.guild).number_detected_member.set(int)
        await ctx.send(f"Number Detected - Member registered: {int}.")

    @configuration.command(name="nbbot", aliases=["botsnb"], usage="<int>")
    async def nbbot(self, ctx: commands.Context, int: int):
        """Number Detected - Bot

        Before action, how many deleted channels should be detected?
        `0' to disable this protection.
        """
        if not ctx.author.id == ctx.guild.owner.id:
            await ctx.send("Only the owner of this server can access these commands!")
            return

        config = await self.config.guild(ctx.guild).all()

        await self.config.guild(ctx.guild).number_detected_bot.set(int)
        await ctx.send(f"Number Detected - Bot registered: {int}.")
        
    @configuration.command(name="resetuser", aliases=["userreset"], usage="<int>")
    async def resetuser(self, ctx: commands.Context, user: discord.Member, give_roles: bool = False):
        """Reset number detected for a user
        """
        if not ctx.author.id == ctx.guild.owner.id:
            await ctx.send("Only the owner of this server can access these commands!")
            return

        config = await self.config.member(user).all()

        if give_roles:
            old_roles = config["old_roles"]
            old_roles = [ctx.guild.get_role(r) for r in old_roles]
            old_roles = [
                r for r in old_roles if r.position < ctx.guild.me.top_role.position and not r.managed
            ]
            if not old_roles == []:
                # await user.edit(roles=old_roles, reason=f"All former roles of {user} ({user.id}) have been restored at the request of the server owner.")
                await user.add_roles(*old_roles, reason=f"All former roles of {user} ({user.id}) have been restored at the request of the server owner.")
                await ctx.send(f"Restored roles for {user.name} ({user.id}).")

        await self.config.member(user).count.clear()
        await self.config.member(user).old_roles.clear()
        await ctx.send(f"Count removed for {user.name} ({user.id}).")
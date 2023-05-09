from AAA3A_utils import Cog, CogsUtils, Settings  # isort:skip
from redbot.core import commands, Config  # isort:skip
from redbot.core.bot import Red  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import io
from copy import deepcopy

from .dashboard_integration import DashboardIntegration

# Credits:
# General repo credits.

_ = Translator("AntiNuke", __file__)


@cog_i18n(_)
class AntiNuke(DashboardIntegration, Cog):
    """A cog to remove all permissions from a person who deletes a channel!"""

    def __init__(self, bot: Red) -> None:
        self.bot: Red = bot

        self.config: Config = Config.get_conf(
            self,
            identifier=205192943327321000143939875896557571750,  # 947269490247
            force_registration=True,
        )
        self.antinuke_guild: typing.Dict[str, typing.Union[bool, int]] = {
            "logschannel": None,  # The channel for logs.
            "enabled": False,  # Enable the possibility.
            "user_dm": True,  # Enable the user dm.
            "number_detected_member": 1,  # Number.
            "number_detected_bot": 1,  # Number.
        }
        self.antinuke_member: typing.Dict[str, typing.Union[int, typing.List[int]]] = {
            "count": 0,  # The count of channel's deletes.
            "old_roles": [],  # The roles to be handed in if it wasn't a nuke.
        }
        self.config.register_guild(**self.antinuke_guild)
        self.config.register_member(**self.antinuke_member)

        self.cogsutils: CogsUtils = CogsUtils(cog=self)

        _settings: typing.Dict[
            str, typing.Dict[str, typing.Union[typing.List[str], bool, str]]
        ] = {
            "enabled": {
                "path": ["enabled"],
                "converter": bool,
                "description": "Enable of disable AntiNuke system.",
            },
            "logschannel": {
                "path": ["logschannel"],
                "converter": discord.TextChannel,
                "description": "Set a channel where events will be sent.",
            },
            "user_dm": {
                "path": ["user_dm"],
                "converter": bool,
                "description": "If enabled, the detected user will receive a DM.",
                "aliases": ["dmuser"],
            },
            "nbmember": {
                "path": ["number_detected_member"],
                "converter": bool,
                "description": "Before action, how many deleted channels should be detected for a member? `0` to disable this protection.",
            },
            "nbbot": {
                "path": ["number_detected_bot"],
                "converter": bool,
                "description": "Before action, how many deleted channels should be detected for a bot? `0` to disable this protection.",
            },
        }
        self.settings: Settings = Settings(
            bot=self.bot,
            cog=self,
            config=self.config,
            group=self.config.GUILD,
            settings=_settings,
            global_path=[],
            use_profiles_system=False,
            can_edit=True,
            commands_group=self.configuration,
        )

    async def cog_load(self) -> None:
        await self.settings.add_commands()

    async def red_delete_data_for_user(
        self,
        *,
        requester: typing.Literal["discord_deleted_user", "owner", "user", "user_strict"],
        user_id: int,
    ) -> None:
        """Delete actions count and old roles, if the requester is `discord_deleted_user` or `owner`."""
        if requester not in ["discord_deleted_user", "owner", "user", "user_strict"]:
            return
        if requester not in ["discord_deleted_user", "owner"]:
            return
        member_group = self.config._get_base_group(self.config.MEMBER)
        async with member_group.all() as members_data:
            _members_data = deepcopy(members_data)
            for guild in _members_data:
                if str(user_id) in _members_data[guild]:
                    del members_data[guild][str(user_id)]
                if members_data[guild] == {}:
                    del members_data[guild]

    async def red_get_data_for_user(self, *, user_id: int) -> typing.Dict[str, io.BytesIO]:
        """Get all data about the user."""
        data = {
            Config.GLOBAL: {},
            Config.USER: {},
            Config.MEMBER: {},
            Config.ROLE: {},
            Config.CHANNEL: {},
            Config.GUILD: {},
        }

        member_group = self.config._get_base_group(self.config.MEMBER)
        async with member_group.all() as members_data:
            for guild in members_data:
                if str(user_id) in members_data[guild]:
                    data[Config.MEMBER][guild] = {str(user_id): members_data[guild][str(user_id)]}

        _data = deepcopy(data)
        for key, value in _data.items():
            if not value:
                del data[key]
        if not data:
            return {}
        file = io.BytesIO(str(data).encode(encoding="utf-8"))
        return {f"{self.qualified_name}.json": file}

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, old_channel: discord.abc.GuildChannel) -> None:
        """Remove all permissions from a user if they delete a channel."""
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
        if not actual_state_enabled:
            return
        actual_number_detected = (
            actual_number_detected_bot if perp.bot else actual_number_detected_member
        )
        if actual_number_detected == 0:
            return
        actual_count += 1
        if actual_count >= actual_number_detected:
            await self.config.member(perp).count.clear()
            old_roles = perp.roles.copy()
            old_roles.remove(old_channel.guild.default_role)
            old_roles = [
                r
                for r in old_roles
                if r.position < old_channel.guild.me.top_role.position and not r.managed
            ]
            rolelist_name = [r.name for r in old_roles]
            rolelist_mention = [r.mention for r in old_roles]
            if actual_state_user_dm:
                try:
                    await perp.send(
                        _(
                            "All your roles have been taken away because you have deleted channel #{old_channel}.\nYour previous roles: {rolelist_name}"
                        ).format(old_channel=old_channel, rolelist_name=rolelist_name)
                    )
                except Exception:
                    pass
            if old_channel.guild.me.guild_permissions.manage_roles:
                # await perp.edit(roles=[], reason=f"All roles in {perp} ({perp.id}) roles have been removed as a result of the antinuke system being triggered on this server.")
                for role in old_roles:
                    try:
                        await perp.remove_roles(
                            role,
                            reason=_(
                                "All roles in {perp} ({perp.id}) roles have been removed as a result of the antinuke system being triggered on this server."
                            ).format(perp=perp),
                        )
                    except Exception:
                        pass
                await self.config.member(perp).old_roles.set(old_roles)
            if logschannel:
                embed: discord.Embed = discord.Embed()
                embed.title = _(
                    "The user {perp} has deleted the channel #{old_channel.name}!"
                ).format(perp=perp, old_channel=old_channel)
                embed.description = _(
                    "To prevent him from doing anything else, I took away as many roles as my current permissions would allow.\nUser mention: {perp.mention} - User ID: {perp.id}"
                ).format(perp=perp)
                embed.color = discord.Color.dark_teal()
                embed.set_author(
                    name=perp,
                    url=perp.display_avatar,
                    icon_url=perp.display_avatar,
                )
                embed.add_field(
                    inline=False,
                    name=_("Before I intervened, the user had the following roles:"),
                    value=rolelist_mention,
                )
                logschannel = self.bot.get_channel(logschannel)
                await logschannel.send(embed=embed)
        else:
            await self.config.member(perp).count.set(actual_count)
            return

    async def get_audit_log_reason(
        self,
        guild: discord.Guild,
        target: typing.Union[discord.abc.GuildChannel, discord.Member, discord.Role],
        action: discord.AuditLogAction,
    ) -> typing.Tuple[typing.Optional[discord.abc.User], typing.Optional[str]]:
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
    @commands.hybrid_group(name="setantinuke", aliases=["antinukeset"])
    async def configuration(self, ctx: commands.Context) -> None:
        """Configure AntiNuke for your server."""

    @configuration.command(name="resetuser", aliases=["userreset"], usage="<int>")
    async def resetuser(
        self, ctx: commands.Context, user: discord.Member, give_roles: bool = False
    ) -> None:
        """Reset number detected for a user."""
        if ctx.author.id != ctx.guild.owner.id:
            await ctx.send(_("Only the owner of this server can access these commands!"))
            return

        config = await self.config.member(user).all()

        if give_roles:
            old_roles = config["old_roles"]
            old_roles = [ctx.guild.get_role(r) for r in old_roles]
            if old_roles := [
                r
                for r in old_roles
                if r.position < ctx.guild.me.top_role.position and not r.managed
            ]:
                # await user.edit(roles=old_roles, reason=f"All former roles of {user} ({user.id}) have been restored at the request of the server owner.")
                await user.add_roles(
                    *old_roles,
                    reason=_(
                        "All former roles of {user} ({user.id}) have been restored at the request of the server owner."
                    ).format(user=user),
                )
                await ctx.send(_("Restored roles for {user.name} ({user.id}).").format(user=user))

        await self.config.member(user).count.clear()
        await self.config.member(user).old_roles.clear()
        await ctx.send(_("Count reset for {user.name} ({user.id}).").format(user=user))

from AAA3A_utils import Cog, Settings, Menu  # isort:skip
from redbot.core import commands, Config  # isort:skip
from redbot.core.bot import Red  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import datetime
import re
from collections import defaultdict

from redbot.core.utils.chat_formatting import pagify

from .converter import RoleHierarchyConverter

# Credits:
# General repo credits.

_: Translator = Translator("ServerSupporters", __file__)


def get_non_animated_asset(
    asset: typing.Optional[discord.Asset] = None,
) -> typing.Optional[discord.Asset]:
    if asset is None:
        return None
    if not asset.is_animated():
        return asset
    return discord.Asset(
        asset._state,
        url=asset.url.replace("/a_", "/").replace(".gif", ".png"),
        key=asset.key.removeprefix("a_"),
        animated=False,
    )


@cog_i18n(_)
class ServerSupporters(Cog):
    """Track and give roles to supporters, members using the server tag or having a server invite link in their status!"""

    def __init__(self, bot: Red) -> None:
        super().__init__(bot=bot)

        self.config: Config = Config.get_conf(
            self,
            identifier=205192943327321000143939875896557571750,
            force_registration=True,
        )
        self.config.register_guild(
            enabled=False,
            logs_channel=None,
            tag_supporter_role=None,
            status_supporter_role=None,
            tag_abandon_channel=None,
        )

        _settings: typing.Dict[str, typing.Dict[str, typing.Any]] = {
            "enabled": {
                "converter": bool,
                "description": "Whether the server supporters system is enabled.",
            },
            "logs_channel": {
                "converter": typing.Union[
                    discord.TextChannel, discord.VoiceChannel, discord.Thread
                ],
                "description": "The channel where logs will be sent.",
            },
            "tag_supporter_role": {
                "converter": RoleHierarchyConverter,
                "description": "The role given to users who use the server tag.",
            },
            "status_supporter_role": {
                "converter": RoleHierarchyConverter,
                "description": "The role given to users who have the server invite link in their status.",
            },
            "tag_abandon_channel": {
                "converter": discord.TextChannel,
                "description": "The channel where users can abandon the server tag.",
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
            commands_group=self.setserversupporters,
        )

        self.cache: typing.Dict[discord.Member, bool] = defaultdict(bool)

    async def cog_load(self) -> None:
        await super().cog_load()
        await self.settings.add_commands()

    async def get_role(
        self, member: discord.Member, _type: typing.Literal["tag", "status"]
    ) -> typing.Optional[discord.Role]:
        if not member.guild.me.guild_permissions.manage_roles:
            return None
        if _type == "tag":
            role_id = await self.config.guild(member.guild).tag_supporter_role()
        else:
            role_id = await self.config.guild(member.guild).status_supporter_role()
        if (
            role_id is None
            or (role := member.guild.get_role(role_id)) is None
            or not role.is_assignable()
        ):
            return None
        return role

    async def get_embed(
        self, member: discord.Member, _type: typing.Literal["tag", "status"], enabled: bool = True
    ) -> discord.Embed:
        embed: discord.Embed = discord.Embed(
            title=(
                _("New Server {_type} Supporter!")
                if enabled
                else _("Server {_type} Supporter Removed...")
            ).format(_type=_("Tag") if _type == "tag" else _("Status")),
            color=discord.Color.green() if enabled else discord.Color.red(),
            timestamp=datetime.datetime.now(tz=datetime.timezone.utc),
        )
        embed.set_author(
            name=member.display_name,
            icon_url=get_non_animated_asset(member.display_avatar),
        )
        embed.set_thumbnail(url=get_non_animated_asset(member.display_avatar))
        if (role := await self.get_role(member, _type)) is not None:
            if enabled:
                embed.description = _(
                    "{member.mention} has been given the **{role.mention}** role for being a server supporter."
                ).format(member=member, role=role, _type=_type)
            else:
                embed.description = _(
                    "{member.mention} has been removed from the **{role.mention}** role for no longer being a server supporter."
                ).format(member=member, role=role, _type=_type)
        embed.set_footer(text=member.guild.name, icon_url=get_non_animated_asset(member.guild.icon))
        return embed

    async def log(
        self, member: discord.Member, _type: typing.Literal["tag", "status"], enabled: bool = True
    ) -> None:
        if (logs_channel_id := await self.config.guild(member.guild).logs_channel()) is None or (
            logs_channel := member.guild.get_channel_or_thread(logs_channel_id)
        ) is None:
            return
        try:
            await logs_channel.send(embed=await self.get_embed(member, _type, enabled))
        except discord.HTTPException as e:
            self.logger.error(
                f"Failed to send log message for member `{member.name}` ({member.id}) in guild `{member.guild.name}` ({member.guild.id}).",
                exc_info=e,
            )
        if _type == "tag" and not enabled:
            if (
                (
                    tag_abandon_channel_id := await self.config.guild(
                        member.guild
                    ).tag_abandon_channel()
                )
                is None
                or (tag_abandon_channel := member.guild.get_channel(tag_abandon_channel_id))
                is None
                or (tag_supporter_role := await self.get_role(member, "tag")) is None
            ):
                return
            try:
                await tag_abandon_channel.send(
                    _(
                        "Hello {member.mention}! By taking the **{member.guild.name}** tag off, you will lose access to the {tag_supporter_role.mention} role and its perks..."
                    ).format(member=member, tag_supporter_role=tag_supporter_role)
                )
            except discord.HTTPException as e:
                self.logger.error(
                    f"Failed to send tag abandon message in channel `{tag_abandon_channel.name}` ({tag_abandon_channel.id}) in guild `{member.guild.name}` ({member.guild.id}).",
                    exc_info=e,
                )

    async def update_roles(
        self, member: discord.Member, _type: typing.Literal["tag", "status"], should_have_role: bool
    ) -> bool:
        if (role := await self.get_role(member, _type)) is None:
            return False

        has_role = role in member.roles
        if has_role == should_have_role:
            return False

        if should_have_role:
            try:
                await member.add_roles(role, reason="Server Supporters system.")
                return True
            except discord.HTTPException as e:
                self.logger.error(
                    f"Failed to add role `{role.name}` ({role.id}) to member `{member.name}` ({member.id}) in guild `{member.guild.name}` ({member.guild.id}).",
                    exc_info=e,
                )
                return False
        else:
            try:
                await member.remove_roles(role, reason="Server Supporters system.")
                return True
            except discord.HTTPException as e:
                self.logger.error(
                    f"Failed to remove role `{role.name}` ({role.id}) from member `{member.name}` ({member.id}) in guild `{member.guild.name}` ({member.guild.id}).",
                    exc_info=e,
                )
                return False

    async def check_invites_in_status(self, guild: discord.Guild, status: str) -> bool:
        for invite_link in re.compile(
            r"(discord\.(?:gg|io|me|li)|discord(?:app)?\.com\/invite|\.gg)\/(\S+)", re.I
        ).findall(status):
            if guild.vanity_url_code is not None and invite_link[1] == guild.vanity_url_code:
                return True
            if guild.me.guild_permissions.manage_guild:
                for invite in await guild.invites():
                    if invite.code == invite_link[1]:
                        return True
        return False

    async def check(
        self,
        member: discord.Member,
        _type: typing.Literal["tag", "status"],
        user_payload: typing.Optional[typing.Dict[str, typing.Any]] = None,
    ) -> bool:
        if _type == "tag":
            if discord.__version__ >= "2.6.0":
                return (
                    member.primary_guild is not None
                    and member.primary_guild.identity_enabled
                    and member.primary_guild.id == member.guild.id
                )
            else:
                if user_payload is None:
                    try:
                        user_payload = await self.bot.http.request(
                            discord.http.Route(
                                "GET",
                                "/users/{user_id}",
                                user_id=member.id,
                            )
                        )
                    except discord.HTTPException:
                        return False
                return (
                    user_payload["clan"] is not None
                    and user_payload["clan"]["identity_enabled"]
                    and user_payload["clan"]["identity_guild_id"] == str(member.guild.id)
                )
        elif _type == "status":
            return (
                bool(member.activities)
                and (
                    status := next(
                        (a for a in member.activities if isinstance(a, discord.CustomActivity)),
                        None,
                    )
                )
                is not None
                and await self.check_invites_in_status(member.guild, status.name)
            )
        return False

    @commands.Cog.listener()
    async def on_presence_update(self, before: discord.Member, after: discord.Member) -> None:
        if after.bot:
            return
        if (
            not await self.config.guild(after.guild).enabled()
            or await self.bot.cog_disabled_in_guild(self, after.guild)
            or await self.get_role(after, "status") is None
        ):
            return
        if self.cache[after]:
            return
        self.cache[after] = True

        try:
            before_qualifies = await self.check(before, "status")
            after_qualifies = await self.check(after, "status")
            if before_qualifies == after_qualifies:
                return
            role_changed = await self.update_roles(after, "status", after_qualifies)
            if role_changed:
                await self.log(after, "status", after_qualifies)
        finally:
            self.cache.pop(after, None)

    @commands.Cog.listener()
    async def on_member_update(
        self,
        before: discord.Member,
        after: discord.Member,
        user_payload: typing.Optional[typing.Dict[str, typing.Any]] = None,
    ) -> None:
        if after.bot:
            return
        if (
            not await self.config.guild(after.guild).enabled()
            or await self.bot.cog_disabled_in_guild(self, after.guild)
            or (tag_supporter_role := await self.get_role(after, "tag")) is None
        ):
            return
        if self.cache[after]:
            return
        self.cache[after] = True

        try:
            if discord.__version__ >= "2.6.0":
                before_qualifies = await self.check(before, "tag")
                after_qualifies = await self.check(after, "tag")
            else:
                before_qualifies = tag_supporter_role in before.roles
                after_qualifies = await self.check(after, "tag", user_payload)
            if before_qualifies == after_qualifies:
                return
            role_changed = await self.update_roles(after, "tag", after_qualifies)
            if role_changed:
                await self.log(after, "tag", after_qualifies)
        finally:
            self.cache.pop(after, None)

    @commands.admin_or_permissions(manage_guild=True, manage_roles=True)
    @commands.bot_has_guild_permissions(manage_roles=True)
    @commands.hybrid_group()
    async def setserversupporters(self, ctx: commands.Context) -> None:
        """Settings for the Server Supporters system."""
        pass

    @setserversupporters.command(aliases=["list"])
    async def listsupporters(
        self, ctx: commands.Context, _type: typing.Literal["tag", "status"]
    ) -> None:
        """List all members with the status supporter role."""
        if _type == "tag":
            if discord.__version__ >= "2.6.0":
                members = [
                    member for member in ctx.guild.members
                    if await self.check(member, "tag")
                ]
            else:
                retrieve, after = 1000, discord.guild.OLDEST_OBJECT
                members = []
                while True:
                    after_id = after.id if after else None
                    data = await ctx.bot.http.get_members(ctx.guild.id, retrieve, after_id)
                    if not data:
                        break
                    after = discord.Object(id=int(data[-1]["user"]["id"]))
                    for raw_member in reversed(data):
                        member = discord.Member(
                            data=raw_member, guild=ctx.guild, state=ctx.guild._state
                        )
                        if member.bot:
                            continue
                        if await self.check(member, "tag", raw_member["user"]):
                            members.append(member)
                    if len(data) < 1000:
                        break
        else:
            members = [
                member for member in ctx.guild.members
                if await self.check(member, "status")
            ]
        embed: discord.Embed = discord.Embed(
            title=_("{count} Server {_type} Supporter{s}").format(
                count=len(members),
                _type=_("Tag") if _type == "tag" else _("Status"),
                s="" if len(members) == 1 else "s",
            ),
            color=await ctx.embed_color(),
            timestamp=ctx.message.created_at,
        )
        embed.set_footer(text=ctx.guild.name, icon_url=ctx.guild.icon)
        description = "\n".join(f"- {member.mention}" for member in members)
        embeds = []
        for page in pagify(description, page_length=2000):
            e = embed.copy()
            e.description = page
            embeds.append(e)
        await Menu(pages=embeds).start(ctx)

    @setserversupporters.command()
    async def forceupdate(self, ctx: commands.Context) -> None:
        """Force update the roles of all members in the guild."""
        if not await self.config.guild(ctx.guild).enabled():
            raise commands.UserFeedbackCheckFailure(
                _("The Server Supporters system is not enabled.")
            )
            
        updated_count = 0

        if discord.__version__ >= "2.6.0":
            for member in ctx.guild.members:
                if member.bot:
                    continue
                tag_qualifies = await self.check(member, "tag")
                status_qualifies = await self.check(member, "status")
                if await self.update_roles(member, "tag", tag_qualifies):
                    updated_count += 1
                if await self.update_roles(member, "status", status_qualifies):
                    updated_count += 1
        else:
            retrieve, after = 1000, discord.guild.OLDEST_OBJECT
            while True:
                after_id = after.id if after else None
                data = await ctx.bot.http.get_members(ctx.guild.id, retrieve, after_id)
                if not data:
                    break
                after = discord.Object(id=int(data[-1]["user"]["id"]))
                for raw_member in reversed(data):
                    member = discord.Member(data=raw_member, guild=ctx.guild, state=ctx.guild._state)
                    if member.bot:
                        continue
                    tag_qualifies = await self.check(member, "tag", raw_member["user"])
                    status_qualifies = await self.check(member, "status")
                    if await self.update_roles(member, "tag", tag_qualifies):
                        updated_count += 1
                    if await self.update_roles(member, "status", status_qualifies):
                        updated_count += 1
                if len(data) < 1000:
                    break

        await ctx.send(_("Force update complete. {count} role changes made.").format(count=updated_count))

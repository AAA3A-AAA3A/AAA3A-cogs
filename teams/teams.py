from AAA3A_utils import Cog, Menu, CogsUtils  # isort:skip
from redbot.core import commands, Config  # isort:skip
from redbot.core.bot import Red  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import asyncio
import random
from collections import defaultdict

from redbot.core.utils.chat_formatting import pagify

from .converters import Emoji, TeamConverter, TeamOrMemberConverter, UrlConverter
from .types import Point, Team

# Credits:
# General repo credits.

_: Translator = Translator("Teams", __file__)


@cog_i18n(_)
class Teams(Cog):
    """Manage teams with captains, vice captains and members, and points, leaderboard and contributor leaderboard!"""

    def __init__(self, bot: Red) -> None:
        super().__init__(bot=bot)

        self.config: Config = Config.get_conf(
            self,
            identifier=205192943327321000143939875896557571750,
            force_registration=True,
        )
        self.config.register_guild(teams={})

        self.teams: typing.Dict[int, typing.Dict[int, Team]] = {}

    async def cog_load(self) -> None:
        await super().cog_load()
        asyncio.create_task(self.load_teams())

    async def load_teams(self) -> None:
        await self.bot.wait_until_red_ready()
        for guild_id, guild_data in (await self.config.all_guilds()).items():
            for team_id, team_data in guild_data["teams"].items():
                team_data["points"] = [Point(**point_data) for point_data in team_data["points"]]
                team = Team(bot=self.bot, cog=self, **team_data)
                self.teams.setdefault(guild_id, {})[team_id] = team

    @commands.Cog.listener()
    async def on_audit_log_entry_create(self, entry: discord.AuditLogEntry) -> None:
        if entry.action != discord.AuditLogAction.member_role_update:
            return
        if not entry.before or not entry.after:
            return
        for role in list(entry.before.roles) + list(entry.after.roles):
            if (
                team := next(
                    (
                        t
                        for t in self.teams.get(entry.guild.id, {}).values()
                        if t.member_role_id is not None and t.member_role_id == role.id
                    ),
                    None,
                )
            ) is None:
                continue
            if role not in entry.before.roles and role in entry.after.roles:
                if entry.target.id not in team.member_ids:
                    try:
                        await team.add_member(entry.target)
                    except RuntimeError:
                        try:
                            await entry.target.remove_roles(
                                role, reason="Removing team member role due to a failed team addition."
                            )
                        except discord.HTTPException:
                            pass
            elif role in entry.before.roles and role not in entry.after.roles:
                if entry.target.id in team.member_ids and entry.target != team.captain:
                    try:
                        await team.remove_member(entry.target)
                    except RuntimeError:
                        try:
                            await entry.target.add_roles(
                                role, reason="Re-adding team member role due to a failed team removal."
                            )
                        except discord.HTTPException:
                            pass

    @commands.guild_only()
    @commands.hybrid_group(aliases=["teams"])
    async def team(self, ctx: commands.Context) -> None:
        """Make incredible teams, with a unique user experience to claim prizes!"""
        pass

    @commands.admin_or_permissions(manage_guild=True)
    @commands.bot_has_permissions(embed_links=True)
    @team.command(aliases=["+"])
    async def create(
        self,
        ctx: commands.Context,
        name: str,
        captain: typing.Optional[discord.Member] = commands.Author,
        emoji: typing.Optional[Emoji] = None,
        logo_url: typing.Optional[UrlConverter] = None,
        color: typing.Optional[commands.ColorConverter] = None,
        use_roles: bool = False,
        *,
        description: str = None,
    ) -> None:
        """Create a new team."""
        if any(captain in team.members for team in self.teams.get(ctx.guild.id, {}).values()):
            raise commands.UserFeedbackCheckFailure(
                _(
                    "A team with this member already exists. Please remove them from the existing team first."
                )
            )
        roles = {}
        if use_roles:
            if not ctx.guild.me.guild_permissions.manage_roles:
                raise commands.UserFeedbackCheckFailure(
                    _("I need the `Manage Roles` permission to create roles.")
                )
            for key, role_name in {
                "captain": _("{name} Captain"),
                "vice_captain": _("{name} Vice-Captain"),
                "member": _("{name} Member"),
            }.items():
                role = await ctx.guild.create_role(
                    name=role_name.format(name=name),
                    color=color
                    if key == "member" and color is not None
                    else discord.Color.default(),
                    display_icon=(
                        logo_url
                        or (await emoji.read() if isinstance(emoji, discord.Emoji) else emoji)
                        if key == "member" and "ROLE_ICONS" in ctx.guild.features
                        else None
                    ),
                    reason="Creating team role.",
                )
                roles[f"{key}_role_id"] = role.id
        team: Team = Team(
            bot=ctx.bot,
            cog=self,
            guild_id=ctx.guild.id,
            name=name,
            captain_id=captain.id,
            member_ids=[captain.id],
            emoji=getattr(emoji, "id", emoji),
            logo_url=logo_url,
            color_value=color.value if color is not None else None,
            description=description,
            **roles,
        )
        await team.save()
        if ctx.guild.me.guild_permissions.manage_roles:
            if (captain_role := team.captain_role) is not None:
                try:
                    await captain.add_roles(captain_role, reason="Adding captain role to team member.")
                except discord.HTTPException:
                    pass
            if (member_role := team.member_role) is not None:
                try:
                    await captain.add_roles(member_role, reason="Adding member role to team member.")
                except discord.HTTPException:
                    pass
        await ctx.send(
            _("✅ Team **{team.display_name}** created successfully!").format(team=team),
            embed=await team.get_embed(),
        )

    @commands.bot_has_permissions(embed_links=True)
    @team.command(aliases=["details"])
    async def info(self, ctx: commands.Context, team: TeamConverter) -> None:
        """Show information about a specific team."""
        embed: discord.Embed = await team.get_embed()
        await Menu(pages=[embed]).start(ctx)

    @commands.bot_has_permissions(embed_links=True)
    @team.command()
    async def members(self, ctx: commands.Context, team: TeamConverter) -> None:
        """Show the members of a specific team."""
        embed: discord.Embed = await team.get_embed(sample=True)
        embed.title += _(" — {member_count} Member{s}").format(
            member_count=len(team.members), s="" if len(team.members) == 1 else "s"
        )
        description = "\n".join(
            f"- {member.mention}"
            + (
                _(" (Captain)")
                if member == team.captain
                else (_(" (Vice Captain)") if member in team.vice_captains else "")
            )
            for member in sorted(
                team.members,
                key=lambda member: (not member == team.captain, member not in team.vice_captains),
            )
        )
        embeds = []
        for page in pagify(description, page_length=1024):
            e = embed.copy()
            e.description = page
            embeds.append(e)
        await Menu(pages=embeds).start(ctx)

    @commands.admin_or_permissions(manage_guild=True)
    @team.command()
    async def addmember(
        self, ctx: commands.Context, team: TeamConverter, *, member: discord.Member
    ) -> None:
        """Add a member to a specific team."""
        try:
            await team.add_member(member)
        except RuntimeError as e:
            raise commands.UserFeedbackCheckFailure(str(e))
        await ctx.send(
            _(
                "✅ Member {member.mention} added successfully to **{team.display_name}** team!"
            ).format(member=member, team=team)
        )

    async def is_admin(self, member: discord.Member) -> bool:
        return (
            await self.bot.is_admin(member)
            or member.guild_permissions.manage_guild
            or member.id in self.bot.owner_ids
        )

    def is_captain_or_vice_captain_or_admin():
        async def predicate(ctx: typing.Union[commands.Context, discord.Interaction]) -> bool:
            bot = ctx.client if isinstance(ctx, discord.Interaction) else ctx.bot
            author = ctx.user if isinstance(ctx, discord.Interaction) else ctx.author
            if await bot.get_cog("Teams").is_admin(author):
                return True
            if (
                team := (ctx.data if isinstance(ctx, discord.Interaction) else ctx.kwargs).get(
                    "team"
                )
            ) is not None and (author == team.captain or author in team.vice_captains):
                return True
            return False

        return predicate

    @commands.permissions_check(is_captain_or_vice_captain_or_admin())
    @team.command()
    async def removemember(
        self, ctx: commands.Context, team: TeamConverter, *, member: discord.Member
    ) -> None:
        """Remove a member from a specific team."""
        try:
            await team.remove_member(member)
        except RuntimeError as e:
            raise commands.UserFeedbackCheckFailure(str(e))
        await ctx.send(
            _(
                "✅ Member {member.mention} removed successfully from **{team.display_name}** team!"
            ).format(member=member, team=team)
        )

    @commands.permissions_check(is_captain_or_vice_captain_or_admin())
    @team.command()
    async def invite(
        self, ctx: commands.Context, team: TeamConverter, *, member: discord.Member
    ) -> None:
        """Invite a member to a specific team."""
        embed: discord.Embed = await team.get_embed(sample=True)
        embed.title += _(" — Invite")
        embed.description = _("Do you want to join this team?").format(team=team)
        if not await CogsUtils.ConfirmationAsk(
            type(
                "FakeContext",
                (),
                {
                    "bot": ctx.bot,
                    "guild": ctx.guild,
                    "channel": ctx.channel,
                    "author": member,
                    "message": ctx.message,
                    "send": ctx.send,
                },
            )(),
            member.mention,
            embed=embed,
            timeout=10 * 60,
        ):
            return
        try:
            await team.add_member(member)
        except RuntimeError as e:
            raise commands.UserFeedbackCheckFailure(str(e))
        await ctx.send(
            _(
                "✅ Member {member.mention} added successfully to **{team.display_name}** team!"
            ).format(member=member, team=team)
        )

    def is_team_captain_or_admin():
        async def predicate(ctx: typing.Union[commands.Context, discord.Interaction]) -> bool:
            bot = ctx.client if isinstance(ctx, discord.Interaction) else ctx.bot
            author = ctx.user if isinstance(ctx, discord.Interaction) else ctx.author
            if await bot.get_cog("Teams").is_admin(author):
                return True
            if (
                team := (ctx.data if isinstance(ctx, discord.Interaction) else ctx.kwargs).get(
                    "team"
                )
            ) is not None and author == team.captain:
                return True
            return False

        return predicate

    @commands.permissions_check(is_team_captain_or_admin())
    @team.command()
    async def promote(
        self, ctx: commands.Context, team: TeamConverter, *, member: discord.Member
    ) -> None:
        """Promote a member to captain in a specific team."""
        try:
            await team.promote_member(member)
        except RuntimeError as e:
            raise commands.UserFeedbackCheckFailure(str(e))
        await ctx.send(
            _(
                "✅ Member {member.mention} promoted successfully to Vice-Captain in **{team.display_name}** team!"
            ).format(member=member, team=team)
        )

    @commands.permissions_check(is_team_captain_or_admin())
    @team.command()
    async def demote(
        self, ctx: commands.Context, team: TeamConverter, *, member: discord.Member
    ) -> None:
        """Demote a member from captain in a specific team."""
        try:
            await team.demote_member(member)
        except RuntimeError as e:
            raise commands.UserFeedbackCheckFailure(str(e))
        await ctx.send(
            _(
                "✅ Member {member.mention} demoted successfully in **{team.display_name}** team!"
            ).format(member=member, team=team)
        )

    @commands.permissions_check(is_team_captain_or_admin())
    @team.command()
    async def transfercaptaincy(
        self, ctx: commands.Context, team: TeamConverter, *, new_captain: discord.Member
    ) -> None:
        """Transfer captaincy to a new member in a specific team."""
        if not await CogsUtils.ConfirmationAsk(
            ctx,
            _("Are you sure you want to transfer captaincy to {new_captain.mention}?").format(
                new_captain=new_captain
            ),
        ):
            return
        try:
            await team.transfer_captaincy(new_captain)
        except RuntimeError as e:
            raise commands.UserFeedbackCheckFailure(str(e))
        await ctx.send(
            _(
                "✅ Team **{team.display_name}** captaincy transferred to {new_captain.mention} successfully!"
            ).format(team=team, new_captain=new_captain)
        )

    @commands.permissions_check(is_team_captain_or_admin())
    @team.command()
    async def edit(
        self,
        ctx: commands.Context,
        team: TeamConverter,
        key: typing.Literal[
            "name", "emoji", "logo_url", "color", "description", "slogan", "image_url"
        ],
        *,
        value: str = None,
    ) -> None:
        """Edit a specific team."""
        if not value and key == "name":
            raise commands.UserFeedbackCheckFailure(_("You must provide a new name for the team."))
        if value is not None:
            if key == "emoji":
                converter = Emoji
            elif key in ("logo_url", "image_url"):
                converter = UrlConverter
            elif key == "color":
                converter = commands.ColorConverter
            else:
                converter = None
            if converter is not None:
                value = await converter().convert(ctx, value)
        old_id = team.id
        setattr(team, key if key != "emoji" else "display_emoji", value)
        await team.save()
        if old_id != team.id:
            del self.teams[ctx.guild.id][old_id]
            await self.config.guild(ctx.guild).teams.clear_raw(old_id)
        await ctx.send(
            _("✅ Team **{team.display_name}** {key} updated successfully!").format(
                team=team, key=key
            )
        )

    @commands.permissions_check(is_team_captain_or_admin())
    @team.command(aliases=["-"])
    async def delete(self, ctx: commands.Context, team: TeamConverter) -> None:
        """Delete a specific team."""
        if not await CogsUtils.ConfirmationAsk(
            ctx, _("Are you sure you want to delete the team `{team.name}`?").format(team=team)
        ):
            return
        await team.delete()
        await ctx.send(_("✅ Team **{team.display_name}** deleted successfully!").format(team=team))

    @commands.bot_has_permissions(embed_links=True)
    @team.command()
    async def list(self, ctx: commands.Context) -> None:
        """List all teams in this server."""
        if ctx.guild.id not in self.teams:
            raise commands.UserFeedbackCheckFailure(_("No teams found in this server."))
        embed: discord.Embed = discord.Embed(
            title=_("Teams:"),
            description="\n".join(
                _("- **{display_name}** (Captain: {captain}) — **{count}** Member{s}").format(
                    display_name=team.display_name,
                    captain=f"<@{captain_id}>",
                    count=len(team.members),
                    s="" if len(team.members) == 1 else "s",
                )
                for team in sorted(
                    self.teams[ctx.guild.id].values(),
                    key=lambda t: (-len(t.members), t.name),
                )
            ),
            color=await ctx.embed_color(),
            timestamp=ctx.message.created_at,
        )
        embed.set_footer(
            text=ctx.guild.name,
            icon_url=ctx.guild.icon,
        )
        await Menu(pages=[embed]).start(ctx)

    @commands.bot_has_permissions(embed_links=True)
    @team.command()
    async def member(self, ctx: commands.Context, *, member: discord.Member) -> None:
        """Show the team of a member."""
        team = next(
            (t for t in self.teams.get(ctx.guild.id, {}).values() if member in t.members),
            None,
        )
        if not team:
            if member == ctx.author:
                raise commands.UserFeedbackCheckFailure(_("You are not in any team."))
            else:
                raise commands.UserFeedbackCheckFailure(_("This member is not in any team."))
        embed = await team.get_embed()
        embed.title += _(" — Member Info")
        embed.set_author(
            name=member.display_name,
            icon_url=member.display_avatar,
        )
        await Menu(pages=[embed]).start(ctx)

    @team.command()
    async def me(self, ctx: commands.Context) -> None:
        """Show your team."""
        await self.member(ctx, member=ctx.author)

    @team.command()
    async def leave(self, ctx: commands.Context) -> None:
        """Leave your current team."""
        team = next(
            (t for t in self.teams.get(ctx.guild.id, {}).values() if ctx.author in t.members),
            None,
        )
        if not team:
            raise commands.UserFeedbackCheckFailure(_("You are not in any team."))
        try:
            await team.remove_member(ctx.author)
        except RuntimeError as e:
            raise commands.UserFeedbackCheckFailure(str(e))
        await ctx.send(
            _("✅ You have left the team **{team.display_name}**!").format(team=team)
        )

    @commands.admin_or_permissions(manage_guild=True)
    @team.command()
    async def addpoints(
        self,
        ctx: commands.Context,
        team_or_member: TeamOrMemberConverter,
        amount: commands.Range[int, 1, 1000],
    ) -> None:
        """Add points to a specific team or team member."""
        if isinstance(team_or_member, Team):
            team, member = team_or_member, None
        elif (
            team := next(
                (
                    t
                    for t in self.teams.get(ctx.guild.id, {}).values()
                    if team_or_member in t.members
                ),
                None,
            )
        ) is not None:
            member = team_or_member
        else:
            raise commands.UserFeedbackCheckFailure(_("This member is not in any team."))
        try:
            await team.add_points(amount, member, ctx.author)
        except RuntimeError as e:
            raise commands.UserFeedbackCheckFailure(str(e))
        await ctx.send(
            _("✅ **{amount} points** added successfully to **{team.display_name}** team!").format(
                amount=amount, team=team
            )
        )

    @commands.admin_or_permissions(manage_guild=True)
    @team.command()
    async def removepoints(
        self,
        ctx: commands.Context,
        team_or_member: TeamOrMemberConverter,
        amount: commands.Range[int, 1, 1000],
    ) -> None:
        """Remove points from a specific team or team member."""
        if isinstance(team_or_member, Team):
            team, member = team_or_member, None
        elif (
            team := next(
                (
                    t
                    for t in self.teams.get(ctx.guild.id, {}).values()
                    if team_or_member in t.members
                ),
                None,
            )
        ) is not None:
            member = team_or_member
        else:
            raise commands.UserFeedbackCheckFailure(_("This member is not in any team."))
        try:
            await team.remove_points(amount, member, ctx.author)
        except RuntimeError as e:
            raise commands.UserFeedbackCheckFailure(str(e))
        await ctx.send(
            _(
                "✅ **{amount} points** removed successfully from **{team.display_name}** team!"
            ).format(amount=amount, team=team)
        )

    @commands.admin_or_permissions(manage_guild=True)
    @team.command()
    async def resetpoints(
        self, ctx: commands.Context, team: typing.Optional[TeamConverter] = None
    ) -> None:
        """Reset the points for a specific team."""
        if team is None:
            if not await CogsUtils.ConfirmationAsk(
                ctx,
                _(
                    "Are you sure you want to reset points for all teams? This action cannot be undone."
                ),
            ):
                return
            for guild_teams in self.teams.values():
                for team in guild_teams.values():
                    await team.reset_points()
        else:
            await team.reset_points()
        await ctx.send(_("✅ Points have been reset successfully!"))

    @commands.permissions_check(is_captain_or_vice_captain_or_admin())
    @commands.bot_has_permissions(embed_links=True)
    @team.command()
    async def history(self, ctx: commands.Context, team: TeamConverter) -> None:
        """Show the point history for a specific team."""
        if not team.points:
            raise commands.UserFeedbackCheckFailure(_("No points found for this team."))
        embed: discord.Embed = await team.get_embed(sample=True)
        embed.title += _(" — Point History")
        description = "\n".join(
            _("- **{point.amount}** points{member}{managed_by} - {timestamp}").format(
                point=point,
                member=_(" for {member.mention}").format(member=member)
                if (member := point.get_member(ctx.guild)) is not None
                else "",
                managed_by=_(" (managed by {managed_by.mention})").format(managed_by=managed_by)
                if (managed_by := point.get_managed_by(ctx.guild)) is not None
                else "",
                timestamp=discord.utils.format_dt(point.managed_at, style="R"),
            )
            for point in team.points
        )
        embeds = []
        for page in pagify(description, page_length=2000):
            e = embed.copy()
            e.description = page
            embeds.append(e)
        await Menu(pages=embeds, page_start=-1).start(ctx)

    @commands.bot_has_permissions(embed_links=True)
    @team.command(aliases=["lb"])
    async def leaderboard(self, ctx: commands.Context) -> None:
        """Show the team leaderboard for this server."""
        if ctx.guild.id not in self.teams:
            raise commands.UserFeedbackCheckFailure(_("No teams found in this server."))
        leaderboard = []
        for team in self.teams[ctx.guild.id].values():
            if team.points:
                leaderboard.append((team, sum(point.amount for point in team.points)))
        if not leaderboard:
            raise commands.UserFeedbackCheckFailure(_("No points found for any team."))
        leaderboard.sort(key=lambda x: x[1], reverse=True)
        embed = discord.Embed(
            title=_("Team Leaderboard"),
            color=await ctx.embed_color(),
            timestamp=ctx.message.created_at,
        )
        for i, (team, points) in enumerate(leaderboard, start=1):
            embed.add_field(
                name=_("**{i}. {team.display_name}**").format(i=i, team=team),
                value=_("=> **{points}** point{s}").format(
                    points=points,
                    s="" if points == 1 else "s",
                ),
                inline=False,
            )
        embed.set_footer(
            text=ctx.guild.name,
            icon_url=ctx.guild.icon,
        )
        await Menu(pages=[embed]).start(ctx)

    @commands.permissions_check(is_captain_or_vice_captain_or_admin())
    @commands.bot_has_permissions(embed_links=True)
    @team.command()
    async def contributors(
        self, ctx: commands.Context, team: typing.Optional[TeamConverter] = None
    ) -> None:
        """List all point contributors globally or in a specific team."""
        if team is not None:
            embed: discord.Embed = await team.get_embed(sample=True)
            embed.title += _(" — Contributors")
            points = team.points
        else:
            embed: discord.Embed = discord.Embed(
                title=_("Contributors for **All Teams**"),
                color=await ctx.embed_color(),
                timestamp=ctx.message.created_at,
            )
            embed.set_footer(
                text=ctx.guild.name,
                icon_url=ctx.guild.icon,
            )
            points = []
            for guild_teams in self.teams.values():
                for team in guild_teams.values():
                    points.extend(team.points)
        if not points:
            raise commands.UserFeedbackCheckFailure(_("No contributors found."))
        counter = defaultdict(int)
        for point in points:
            if (member := point.get_member(ctx.guild)) is not None:
                counter[member] += point.amount
        description = "\n".join(
            _("**{i}.** {member}: **{points}** point{s}").format(
                i=i,
                member=member.mention,
                points=points,
                s="" if points == 1 else "s",
            )
            for i, (member, points) in enumerate(counter.items(), start=1)
        )
        embeds = []
        for page in pagify(description):
            e = embed.copy()
            e.description = page
            embeds.append(e)
        await Menu(pages=embeds).start(ctx)

    @commands.admin_or_permissions(manage_guild=True)
    @team.command()
    async def addmembersfromrole(
        self, ctx: commands.Context, team: TeamConverter, role: discord.Role
    ) -> None:
        """Add all members from a role to a team."""
        if not role.members:
            raise commands.UserFeedbackCheckFailure(_("No members found in this role."))
        count = 0
        for member in role.members:
            if member not in team.members:
                try:
                    await team.add_member(member)
                except RuntimeError as e:
                    await ctx.send(
                        _(
                            "⚠️ Could not add {member.mention} to **{team.display_name}** team: {error}"
                        ).format(member=member, team=team, error=str(e))
                    )
                else:
                    count += 1
        await ctx.send(
            _("✅ **{count} members** added to **{team.display_name}** team!").format(
                count=count, team=team
            )
        )

    @commands.admin_or_permissions(manage_guild=True)
    @team.command()
    async def splitmembersfromrole(self, ctx: commands.Context, role: discord.Role) -> None:
        """Split members from a role into separate teams."""
        members = role.members
        count, teams = len(members), self.teams.get(ctx.guild.id, {}).values()
        if count == 0:
            raise commands.UserFeedbackCheckFailure(_("No members found in this role."))
        if not teams:
            raise commands.UserFeedbackCheckFailure(_("No teams found in this server."))
        random.shuffle(members)
        div, mod = divmod(count, len(teams))
        for team, member_count in {
            team: div + (1 if i < mod else 0) for i, team in enumerate(teams)
        }.items():
            for member in members[:member_count]:
                try:
                    await team.add_member(member)
                except RuntimeError as e:
                    await ctx.send(
                        _(
                            "⚠️ Could not add {member.mention} to **{team.display_name}** team: {error}"
                        ).format(member=member, team=team, error=str(e))
                    )
            members = members[member_count:]
        await ctx.send(
            _("✅ **{count} members** split into **{team_count} teams**!").format(
                count=count, team_count=len(teams)
            )
        )

    @commands.admin_or_permissions(manage_guild=True)
    @team.command()
    async def clearall(self, ctx: commands.Context) -> None:
        """Delete all teams in this server."""
        if not self.teams.get(ctx.guild.id):
            raise commands.UserFeedbackCheckFailure(_("No teams found in this server."))
        if not await CogsUtils.ConfirmationAsk(
            ctx,
            _(
                "Are you sure you want to delete all teams in this server? This action can't be undone."
            ),
        ):
            return
        for team in self.teams[ctx.guild.id].values():
            await team.delete()
        await ctx.send(_("✅ All teams deleted in this server!"))

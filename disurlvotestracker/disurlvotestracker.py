from AAA3A_utils import Cog, CogsUtils, Loop, Menu, Settings  # isort:skip
from AAA3A_utils.settings import CustomMessageConverter  # isort:skip
from redbot.core import commands, Config  # isort:skip
from redbot.core.bot import Red  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

from redbot.core.utils.chat_formatting import pagify

import datetime
import io
from copy import deepcopy
from collections import Counter

from .converter import RoleHierarchyConverter
from .dashboard_integration import DashboardIntegration

# Credits:
# General repo credits.

_ = Translator("DisurlVotesTracker", __file__)


@cog_i18n(_)
class DisurlVotesTracker(DashboardIntegration, Cog):
    """Track votes on Disurl, assign roles to voters and remind them to vote!"""

    __authors__: typing.List[str] = ["AAA3A"]

    def __init__(self, bot: Red) -> None:
        super().__init__(bot=bot)

        self.config: Config = Config.get_conf(
            self,
            identifier=205192943327321000143939875896557571750,
            force_registration=True,
        )
        self.config.register_guild(
            enabled=False,
            votes_channel=None,
            disurl_authaurization_key=None,
            voters_role=None,
            vote_reminder=False,
            custom_vote_message=None,
            custom_vote_reminder_message=None,
        )
        self.config.register_member(
            votes=[],
            last_reminder_sent=True,
        )

        _settings: typing.Dict[str, typing.Dict[str, typing.Any]] = {
            "enabled": {
                "converter": bool,
                "description": "Toggle the cog. WARNING: Red-Dashboard has to be installed and started for this to work.",
            },
            "votes_channel": {
                "converter": typing.Union[discord.TextChannel, discord.VoiceChannel, discord.Thread],
                "description": "The channel where votes notifications will be sent.",
            },
            "disurl_authaurization_key": {
                "converter": str,
                "description": "Your Disurl authorization key, used to secure the Dashboard webhook. That's the key which you set on https://disurl.me/dashboard/server/GUILD_ID/webhooks.",
            },
            "voters_role": {
                "converter": RoleHierarchyConverter,
                "description": "The role that will be assigned to voters.",
            },
            "vote_reminder": {
                "converter": bool,
                "description": "Toggle vote reminders. A reminder will be sent to voters 12 hours after their vote.",
            },
            "custom_vote_message": {
                "converter": CustomMessageConverter,
                "description": "Custom vote message. You can specify the ID or the link of an existing message, or provide an embed payload. Use the variables `{member_name}`, `{member_avatar_url}`, `{member_mention}`, `{member_id}`, `{guild_name}`, `{guild_icon_url}`, `{guild_id}`, `{votes_channel_name}`, `{votes_channel_mention}`, `{votes_channel_id}`, `{voters_role_name}`, `{voters_role_mention}`, `{voters_role_id}`, `{number_member_votes}`, `{number_member_monthly_votes}`, `{s_1}` (`number_member_votes` plural) and `{s_2}` (`number_member_monthly_votes` plural).",
            },
            "custom_vote_reminder_message": {
                "converter": CustomMessageConverter,
                "description": "Custom vote reminder message. You can specify the ID or the link of an existing message, or provide an embed payload. Use the variables `{member_name}`, `{member_avatar_url}`, `{member_mention}`, `{member_id}`, `{guild_name}`, `{guild_icon_url}`, `{guild_id}`, `{votes_channel_name}`, `{votes_channel_mention}`, `{votes_channel_id}`, `{voters_role_name}`, `{voters_role_mention}`, `{voters_role_id}`, `{number_member_votes}`, `{number_member_monthly_votes}`, `{s_1}` (`number_member_votes` plural) and `{s_2}` (`number_member_monthly_votes` plural).",
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
            commands_group=self.setdisurlvotestracker,
        )

    async def cog_load(self) -> None:
        await super().cog_load()
        await self.settings.add_commands()
        self.loops.append(
            Loop(
                cog=self,
                name="Check 12h after Votes",
                function=self.check_12h_after_votes,
                minutes=1,
            )
        )

    async def red_delete_data_for_user(
        self,
        *,
        requester: typing.Literal["discord_deleted_user", "owner", "user", "user_strict"],
        user_id: int,
    ) -> None:
        """Delete all DisurlVotesTracker data for a user."""
        if requester not in ("discord_deleted_user", "owner", "user", "user_strict"):
            return
        member_group = self.config._get_base_group(self.config.MEMBER)
        async with member_group.all() as members_data:
            for guild in members_data.copy():
                if str(user_id) in members_data[guild]:
                    del members_data[guild][str(user_id)]
                if not members_data[guild]:
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
    async def on_webhook_receive(self, payload: typing.Dict[str, typing.Any]) -> None:
        if payload.get("type") not in ("vote", "testVote"):
            return
        if "guildId" not in payload or "userId" not in payload:
            return
        try:
            guild_id: int = int(payload["guildId"])
        except ValueError:
            return
        if (
            (guild := self.bot.get_guild(guild_id)) is None
            or await self.bot.cog_disabled_in_guild(cog=self, guild=guild)
            or not await self.config.guild(guild).enabled()
            or (votes_channel_id := await self.config.guild(guild).votes_channel()) is None
            or (votes_channel := guild.get_channel_or_thread(votes_channel_id)) is None
        ):
            return
        if payload["headers"].get("Authorization") != ("Basic " + await self.config.guild(guild).disurl_authaurization_key()):
            return
        if (
            member := guild.get_member(int(payload["userId"]))
            or not await self.bot.allowed_by_whitelist_blacklist(who=member)
        ) is None:
            return

        if (
            (voters_role_id := await self.config.guild(guild).voters_role()) is not None
            and (voters_role := guild.get_role(voters_role_id)) is not None
            and voters_role not in member.roles
        ):
            try:
                await member.add_roles(voters_role, reason=_("Voted on Disurl! (12 hours)"))
            except discord.HTTPException as e:
                self.logger.error(
                    f"Failed to assign the voters role to {member} ({member.id}) in {guild} ({guild.id}): {e}"
                )

        member_data = await self.config.member(member).all()
        number_member_votes = len(member_data["votes"]) + 1
        number_member_monthly_votes = len(
            [vote for vote in member_data["votes"] if datetime.datetime.now(tz=datetime.timezone.utc) - datetime.datetime.fromtimestamp(vote, tz=datetime.timezone.utc) < datetime.timedelta(days=30)]
        ) + 1
        s_1 = "" if number_member_votes == 1 else "s"
        s_2 = "" if number_member_monthly_votes == 1 else "s"
        if (custom_vote_message := await self.config.guild(guild).custom_vote_message()) is None:
            embed: discord.Embed = discord.Embed(color=discord.Color.green())
            embed.title = _("New vote for {guild.name}!").format(guild=guild)
            embed.set_author(name=member.display_name, icon_url=member.display_avatar)
            embed.set_thumbnail(url=member.display_avatar)
            embed.description = _(
                "{member.mention} voted on Disurl!\n"
                "`{number_member_votes} vote{s_1} this month & {number_member_monthly_votes} lifetime vote{s_2}`"
            ).format(
                member=member,
                number_member_votes=number_member_votes, s_1=s_1,
                number_member_monthly_votes=number_member_monthly_votes, s_2=s_2,
            )
            if voters_role is not None:
                embed.description += _("\n\n{member.display_name} received the role {voters_role.mention} for the next 12 hours.").format(member=member, voters_role=voters_role)
            embed.description += _("\n\nYou could vote on [Disurl](https://disurl.me/server/{guild.id}/vote) here again in 12 hours!").format(guild=guild)
            embed.set_footer(text=_("Thanks for supporting the server! | User ID: {member.id}").format(member=member), icon_url=guild.icon)
            await votes_channel.send(embed=embed)
        else:
            env = {
                "member_name": member.display_name,
                "member_avatar_url": member.display_avatar.url,
                "member_mention": member.mention,
                "member_id": member.id,
                "guild_name": guild.name,
                "guild_icon_url": guild.icon.url,
                "guild_id": guild.id,
                "votes_channel_name": votes_channel.name,
                "votes_channel_mention": votes_channel.mention,
                "votes_channel_id": votes_channel.id,
                "voters_role_name": voters_role.name if voters_role is not None else None,
                "voters_role_mention": voters_role.mention if voters_role is not None else None,
                "voters_role_id": voters_role.id if voters_role is not None else None,
                "number_member_votes": number_member_votes, "s_1": s_1,
                "number_member_monthly_votes": number_member_monthly_votes, "s_2": s_2,
            }
            await CustomMessageConverter(**custom_vote_message).send_message(
                None, channel=votes_channel, env=env
            )

        votes = await self.config.member(member).votes()
        votes.append(int(datetime.datetime.now(tz=datetime.timezone.utc).timestamp()))
        await self.config.member(member).votes.set(votes)
        await self.config.member(member).last_reminder_sent.set(False)

    async def check_12h_after_votes(self) -> None:
        for guild_id, guild_data in (await self.config.all_guilds()).items():
            if (
                (guild := self.bot.get_guild(guild_id)) is None
                or await self.bot.cog_disabled_in_guild(cog=self, guild=guild)
                or not guild_data["enabled"]
                or (votes_channel_id := guild_data["votes_channel"]) is None
                or (votes_channel := guild.get_channel_or_thread(votes_channel_id)) is None
            ):
                continue
            for member_id, member_data in (await self.config.all_members(guild)).items():
                if member_data["last_reminder_sent"] or not (
                    votes := member_data["votes"]
                ):
                    continue
                if datetime.datetime.now(tz=datetime.timezone.utc) - datetime.datetime.fromtimestamp(votes[-1], tz=datetime.timezone.utc) < datetime.timedelta(hours=12):
                    continue
                await self.config.member_from_ids(guild_id, member_id).last_reminder_sent.set(True)
                if (member := guild.get_member(member_id)) is None:
                    continue

                if (
                    (voters_role_id := guild_data["voters_role"]) is not None
                    and (voters_role := guild.get_role(voters_role_id)) is not None
                    and voters_role in member.roles
                ):
                    try:
                        await member.remove_roles(voters_role, reason=_("Voters role expired! (12 hours)"))
                    except discord.HTTPException as e:
                        self.logger.error(
                            f"Failed to remove the voters role from {member} ({member.id}) in {guild} ({guild.id}): {e}"
                        )

                if await self.config.guild(guild).vote_reminder():
                    if (custom_vote_reminder_message := guild_data["custom_vote_reminder_message"]) is None:
                        view = discord.ui.View()
                        view.add_item(discord.ui.Button(label=_("Vote on Disurl!"), url=f"https://disurl.me/server/{guild.id}/vote"))
                        await votes_channel.send(
                            _(
                                "{member.mention}, don't forget to vote on **[Disurl](https://disurl.me/server/{guild.id}/vote)**! You could vote again 12 hours after this vote. **Thanks for supporting the server!**"
                            ).format(member=member, guild=guild),
                            view=view,
                        )
                    else:
                        number_member_votes = len(member_data["votes"])
                        number_member_monthly_votes = len(
                            [vote for vote in member_data["votes"] if datetime.datetime.now(tz=datetime.timezone.utc) - datetime.datetime.fromtimestamp(vote, tz=datetime.timezone.utc) < datetime.timedelta(days=30)]
                        )
                        s_1 = "" if number_member_votes == 1 else "s"
                        s_2 = "" if number_member_monthly_votes == 1 else "s"
                        env = {
                            "member_name": member.display_name,
                            "member_avatar_url": member.display_avatar.url,
                            "member_mention": member.mention,
                            "member_id": member.id,
                            "guild_name": guild.name,
                            "guild_icon_url": guild.icon.url,
                            "guild_id": guild.id,
                            "votes_channel_name": votes_channel.name,
                            "votes_channel_mention": votes_channel.mention,
                            "votes_channel_id": votes_channel.id,
                            "voters_role_name": voters_role.name if voters_role is not None else None,
                            "voters_role_mention": voters_role.mention if voters_role is not None else None,
                            "voters_role_id": voters_role.id if voters_role is not None else None,
                            "number_member_votes": number_member_votes, "s_1": s_1,
                            "number_member_monthly_votes": number_member_monthly_votes, "s_2": s_2,
                        }
                        await CustomMessageConverter(**custom_vote_reminder_message).send_message(
                            None, channel=votes_channel, env=env
                        )

    @commands.bot_has_permissions(embed_links=True)
    @commands.hybrid_group(aliases=["dvt"])
    async def disurlvotestracker(self, ctx: commands.Context) -> None:
        """Commands to interact with DisurlVotesTracker."""
        pass

    @disurlvotestracker.command()
    async def leaderboard(self, ctx: commands.Context) -> None:
        """Show the lifetime leaderboard of voters."""
        if not await self.config.guild(ctx.guild).enabled():
            raise commands.UserFeedbackCheckFailure(_("DisurlVotesTracker is not enabled in this server."))
        members_data = await self.config.all_members(ctx.guild)
        counter = Counter({
            member: len(member_data["votes"])
            for member_id, member_data in members_data.items()
            if member_data["votes"] and (member := ctx.guild.get_member(member_id)) is not None
        })
        if not counter:
            raise commands.UserFeedbackCheckFailure(_("No voters found."))
        embed: discord.Embed = discord.Embed(
            title=_("Leaderboard"),
            color=await ctx.embed_color(),
        )
        embed.set_author(name=_("{ctx.guild.name} | {total} Lifetime Votes").format(ctx=ctx, total=counter.total()), icon_url=ctx.guild.icon.url)
        if ctx.author in counter:
            author_index = list(counter.keys()).index(ctx.author) + 1
            embed.set_footer(text=_("You are at position {author_index} with {number_member_lifetime_votes} vote{s}.").format(author_index=author_index, s="" if counter[ctx.author] == 1 else "s", number_member_lifetime_votes=counter[ctx.author]))
        description = [
            f"{i}. **{member.display_name}**: {number_member_lifetime_votes} vote{'' if number_member_lifetime_votes == 1 else 's'}"
            for i, (member, number_member_lifetime_votes) in enumerate(counter.most_common(), start=1)
        ]
        embeds = []
        for page in discord.utils.as_chunks(description, 10):
            e = embed.copy()
            e.description = "\n".join(page)
            embeds.append(e)
        await Menu(pages=embeds).start(ctx)

    @disurlvotestracker.command()
    async def monthlyleaderboard(self, ctx: commands.Context) -> None:
        """Show the monthly leaderboard of voters."""
        if not await self.config.guild(ctx.guild).enabled():
            raise commands.UserFeedbackCheckFailure(_("DisurlVotesTracker is not enabled in this server."))
        members_data = await self.config.all_members(ctx.guild)
        counter = Counter({
            member: len(
                [
                    vote
                    for vote in member_data["votes"]
                    if datetime.datetime.now(tz=datetime.timezone.utc)
                    - datetime.datetime.fromtimestamp(
                        vote, tz=datetime.timezone.utc
                    )
                    < datetime.timedelta(days=30)
                ]
            )
            for member_id, member_data in members_data.items()
            if member_data["votes"] and (member := ctx.guild.get_member(member_id)) is not None
        })
        if not counter:
            raise commands.UserFeedbackCheckFailure(_("No voters found."))
        embed: discord.Embed = discord.Embed(
            title=_("Monthly Leaderboard"),
            color=await ctx.embed_color(),
        )
        embed.set_author(name=_("{ctx.guild.name} | {total} Monthly Votes").format(ctx=ctx, total=counter.total()), icon_url=ctx.guild.icon.url)
        if ctx.author in counter:
            author_index = list(counter.keys()).index(ctx.author) + 1
            embed.set_footer(text=_("You are at position {author_index} with {number_member_monthly_votes} vote{s}.").format(author_index=author_index, s="" if counter[ctx.author] == 1 else "s", number_member_monthly_votes=counter[ctx.author]))
        description = [
            f"{i}. **{member.display_name}**: {number_member_monthly_votes} vote{'' if number_member_monthly_votes == 1 else 's'}"
            for i, (member, number_member_monthly_votes) in enumerate(counter.most_common(), start=1)
        ]
        embeds = []
        for page in discord.utils.as_chunks(description, 10):
            e = embed.copy()
            e.description = "\n".join(page)
            embeds.append(e)
        await Menu(pages=embeds).start(ctx)

    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    @commands.hybrid_group(aliases=["setdvt"])
    async def setdisurlvotestracker(self, ctx: commands.Context) -> None:
        """Commands to configure DisurlVotesTracker."""
        pass

    @commands.bot_has_permissions(embed_links=True)
    @setdisurlvotestracker.command()
    async def instructions(self, ctx: commands.Context) -> None:
        """Instructions on how to set up DisurlVotesTracker."""
        if (dashboard_url := getattr(ctx.bot, "dashboard_url", None)) is None:
            raise commands.UserFeedbackCheckFailure(
                _(
                    "Red-Dashboard is not installed. Check <https://red-web-dashboard.readthedocs.io>."
                )
            )
        if not dashboard_url[1] and ctx.author.id not in ctx.bot.owner_ids:
            raise commands.UserFeedbackCheckFailure(_("You can't access the Dashboard."))
        embed: discord.Embed = discord.Embed(
            title=_("DisurlVotesTracker Instructions"),
            color=await ctx.embed_color(),
            description=_(
                "1. Go to [Disurl Dashboard](https://disurl.me/dashboard/server/{guild_id}/webhooks) and set the webhook URL to `{webhook_url}`.\n"
                "2. Set the Disurl API authorization key with the key which you provided on Disurl.\n"
                "3. Set the votes channel where vote notifications will be sent.\n"
                "4. Set the optional the voters role that will be assigned to voters.\n"
                "5. Optionally, toggle the vote reminder.\n"
                "6. Optionally, set the `custom_vote_message` and `custom_vote_reminder_message`."
                "7. Enable the cog."
            ).format(guild_id=ctx.guild.id, webhook_url=f"{dashboard_url[0]}/api/webhook"),
        )
        await ctx.send(embed=embed)

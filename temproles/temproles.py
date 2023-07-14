from AAA3A_utils import Cog, Loop, CogsUtils, Menu  # isort:skip
from redbot.core import commands, Config  # isort:skip
from redbot.core.bot import Red  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import datetime
import io

from copy import deepcopy

from redbot.core.utils.chat_formatting import humanize_list, pagify

# Credits:
# General repo credits.
# Thanks to Obi-Wan3 for the cog idea and the strings of some messages (https://github.com/Obi-Wan3/OB13-Cogs/tree/main/temprole)!

_ = Translator("TempRoles", __file__)

TimeConverter: commands.converter.TimedeltaConverter = commands.converter.TimedeltaConverter(
    minimum=datetime.timedelta(minutes=1),
    maximum=None,
    allowed_units=None,
    default_unit="days",
)

class OptionalTimeConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> typing.Optional[datetime.timedelta]:
        if argument.lower() == "none":
            return None
        return await TimeConverter.convert(ctx, argument=argument)


@cog_i18n(_)
class TempRoles(Cog):
    """A cog to assign temporary roles to users, expiring after a set time!"""

    def __init__(self, bot: Red) -> None:
        super().__init__(bot=bot)
        self.__authors__: typing.List[str] = ["Obi-Wan3", "AAA3A"]

        self.config: Config = Config.get_conf(
            self,
            identifier=205192943327321000143939875896557571750,  # 969369062738
            force_registration=True,
        )
        self.temproles_member: typing.Dict[str, typing.Dict[int, int]] = {
            "temp_roles": {},
        }
        self.temproles_guild: typing.Dict[str, typing.Union[typing.Optional[int], typing.Dict[int, typing.Dict[str, typing.Optional[int]]]]] = {
            "logs_channel": None,
            "allowed_self_temp_roles": {},
        }
        self.config.register_member(**self.temproles_member)
        self.config.register_guild(**self.temproles_guild)

    async def cog_load(self) -> None:
        await super().cog_load()
        self.loops.append(
            Loop(
                cog=self,
                name="Check TempRoles",
                function=self.temp_roles_loop,
                seconds=30,
            )
        )

    async def red_delete_data_for_user(
        self,
        *,
        requester: typing.Literal["discord_deleted_user", "owner", "user", "user_strict"],
        user_id: int,
    ) -> None:
        """Delete temporary roles only in cog data for the user."""
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

        members_data = await self.config.all_members()
        for guild in members_data:
            if user_id in members_data[guild]:
                data[Config.MEMBER][guild] = members_data[guild][user_id]

        _data = deepcopy(data)
        for key, value in _data.items():
            if not value:
                del data[key]
        if not data:
            return {}
        file = io.BytesIO(str(data).encode(encoding="utf-8"))
        return {f"{self.qualified_name}.json": file}

    async def temp_roles_loop(self, utc_now: datetime.datetime = None) -> bool:
        if utc_now is None:
            utc_now = datetime.datetime.now(datetime.timezone.utc)
        executed = False
        member_group = self.config._get_base_group(self.config.MEMBER)
        async with member_group.all() as members_data:
            _members_data = deepcopy(members_data)
            for guild_id in _members_data:
                if (guild := self.bot.get_guild(int(guild_id))) is None:
                    continue
                for member_id in _members_data[guild_id]:
                    if (member := guild.get_member(int(member_id))) is None:
                        del members_data[guild_id][member_id]
                        continue
                    for temp_role_id, expires_times in _members_data[guild_id][member_id]["temp_roles"].items():
                        if datetime.datetime.fromtimestamp(expires_times, tz=datetime.timezone.utc) <= utc_now.replace(microsecond=0):
                            executed = True
                            if (temp_role := guild.get_role(int(temp_role_id))) is not None:
                                try:
                                    await member.remove_roles(temp_role, reason="Temp Role automatically unassigned.")
                                except discord.HTTPException as e:
                                    self.log.error(f"Error when removing the Temp Role {temp_role.name} ({temp_role.id}) from {member} ({member.id}) in {guild.name} ({guild.id}).", exc_info=e)
                                else:
                                    if (
                                        (logs_channel_id := await self.config.guild(guild).logs_channel()) is not None
                                        and (logs_channel := guild.get_channel(logs_channel_id)) is not None
                                        and logs_channel.permissions_for(guild.me).embed_links
                                    ):
                                        await logs_channel.send(
                                            embed=discord.Embed(
                                                title=_("Temp Roles"),
                                                description=_("Temp Role {temp_role.mention} ({role.id}) has been automatically unassigned from {member.mention} ({member.id}).").format(temp_role=temp_role, member=member),
                                                color=await self.bot.get_embed_color(logs_channel)
                                            )
                                        )
                            del members_data[guild_id][member_id]["temp_roles"][temp_role_id]
                    if not members_data[guild_id][member_id]["temp_roles"]:
                        del members_data[guild_id][member_id]
                if not members_data[guild_id]:
                    del members_data[guild_id]
        return executed

    @commands.guild_only()
    @commands.bot_has_permissions(manage_roles=True)
    @commands.hybrid_group(aliases=["temprole"])
    async def temproles(self, ctx: commands.Context) -> None:
        """Assign TempRoles roles to users, expiring after a set time."""
        pass

    @commands.admin_or_permissions(manage_roles=True)
    @temproles.command(aliases=["add", "+"])
    async def assign(self, ctx: commands.Context, member: discord.Member, role: discord.Role, *, time: TimeConverter) -> None:
        """Assign/Add a TempRole to a member, for a specified duration."""
        if role in member.roles:
            raise commands.UserFeedbackCheckFailure(_("This member already has {role.mention} ({role.id}).").format(role=role))
        if role >= ctx.guild.me.top_role or (role >= ctx.author.top_role and ctx.author != ctx.guild.owner):
            raise commands.UserFeedbackCheckFailure(_("This role cannot be assigned due to the Discord role hierarchy."))
        if ctx.author != ctx.guild.owner and (member.top_role >= ctx.author.top_role or member == ctx.guild.owner):
            raise commands.UserFeedbackCheckFailure(_("You can't assign this role to this member, due to the Discord role hierarchy."))
        member_temp_roles = await self.config.member(member).temp_roles()
        if str(role.id) in member_temp_roles:
            raise commands.UserFeedbackCheckFailure(_("This role is already a temprole of this member."))
        try:
            end_time: datetime.datetime = datetime.datetime.now(datetime.timezone.utc) + time
        except OverflowError:
            raise commands.UserFeedbackCheckFailure(_("The time set is way too high, consider setting something reasonable."))
        end_time = end_time.replace(second=0 if end_time.second < 30 else 30)
        time_string = CogsUtils.get_interval_string(time)
        await member.add_roles(
            role,
            reason=("Self " if ctx.command.name == "selfassign" else "") + f"Temp Role assigned by {ctx.author} ({ctx.author.id}), expires in {time_string}."
        )
        member_temp_roles[str(role.id)] = int(end_time.replace(microsecond=0).timestamp())
        await self.config.member(member).temp_roles.set(member_temp_roles)
        if (
            (logs_channel_id := await self.config.guild(ctx.guild).logs_channel()) is not None
            and (logs_channel := ctx.guild.get_channel(logs_channel_id)) is not None
            and logs_channel.permissions_for(ctx.guild.me).embed_links
        ):
            await logs_channel.send(
                embed=discord.Embed(
                    title=_("Temp Roles"),
                    description=(_("Self ") if ctx.command.name == "selfassign" else "") + _("Temp Role {role.mention} ({role.id}) has been assigned to {member.mention} ({member.id}) by {author.mention} ({author.id}). Expires in {time_string}.").format(role=role, member=member, author=ctx.author, time_string=time_string),
                    color=await ctx.bot.get_embed_color(logs_channel)
                )
            )
        await ctx.send(
            (_("Self ") if ctx.command.name == "selfassign" else "") + _("Temp Role {role.mention} ({role.id}) has been assigned to {member.mention} ({member.id}). Expires in {time_string}.").format(role=role, member=member, time_string=time_string),
            allowed_mentions=discord.AllowedMentions(roles=False, users=False)
        )

    @commands.admin_or_permissions(manage_roles=True)
    @temproles.command(aliases=["remove", "-"])
    async def unassign(self, ctx: commands.Context, member: discord.Member, role: discord.Role) -> None:
        """Unassign/Remove a TempRole from a member."""
        member_temp_roles = await self.config.member(member).temp_roles()
        if str(role.id) not in member_temp_roles:
            raise commands.UserFeedbackCheckFailure(_("This role isn't a temprole of this member."))
        try:
            await member.remove_roles(
                role,
                reason=f"Temp Role unassigned by {ctx.author} ({ctx.author.id})."
            )
        except discord.HTTPException:
            pass
        del member_temp_roles[str(role.id)]
        await self.config.member(member).temp_roles.set(member_temp_roles)
        if (
            (logs_channel_id := await self.config.guild(ctx.guild).logs_channel()) is not None
            and (logs_channel := ctx.guild.get_channel(logs_channel_id)) is not None
            and logs_channel.permissions_for(ctx.guild.me).embed_links
        ):
            await logs_channel.send(
                embed=discord.Embed(
                    title=_("Temp Roles"),
                    description=_("TempRole {role.mention} ({role.id}) has been unassigned from {member.mention} ({member.id}) by {author.mention} ({author.id}).").format(role=role, member=member, author=ctx.author),
                    color=await ctx.bot.get_embed_color(logs_channel)
                )
            )
        await ctx.send(
            _("Temp Role {role.mention} ({role.id}) has been unassigned from {member.mention} ({member.id}).").format(role=role, member=member),
            allowed_mentions=discord.AllowedMentions(roles=False, users=False)
        )

    @commands.admin_or_permissions(manage_roles=True)
    @commands.bot_has_permissions(embed_links=True)
    @temproles.command()
    async def list(self, ctx: commands.Context, member: typing.Optional[discord.Member] = None, role: typing.Optional[discord.Role] = None) -> None:
        """List active Temp Roles on this server, for optional specified member and/or role."""
        if member is not None and role is not None:
            if str(role.id) in await self.config.member(member).temp_roles():
                description = _("This member has this Temp Role.")
            else:
                description = _("This member hasn't this Temp Role.")
        elif member is not None:
            if not (temp_roles := await self.config.member(member).temp_roles()):
                description = _("This member hasn't any Temp Roles.")
            else:
                description = _("This member has these Temp Roles: {temp_roles}.").format(temp_roles=humanize_list([f"{temp_role.mention} ({temp_role_id})" for temp_role_id in temp_roles if (temp_role := ctx.guild.get_role(int(temp_role_id))) is not None]))
        elif role is not None:
            members_data = await self.config.all_members(guild=ctx.guild)
            temp_roles_members = []
            for member_id, data in members_data.items():
                if str(role.id) not in data["temp_roles"]:
                    continue
                if (member := ctx.guild.get_member(member_id)) is None:
                    continue
                temp_roles_members.append(member)
            if not temp_roles_members:
                description = _("No members have this Temp Role.")
            else:
                description = _("These members have this Temp Role: {temp_roles_members}.").format(temp_roles_members=humanize_list([f"{member.mention} ({member.id})" for member in temp_roles_members]))
        else:
            description = []
            members_data = await self.config.all_members(guild=ctx.guild)
            for member_id, data in members_data.items():
                if (member := ctx.guild.get_member(member_id)) is None:
                    continue
                if (member_temp_roles := [temp_role for temp_role_id in data["temp_roles"] if (temp_role := ctx.guild.get_role(int(temp_role_id))) is not None]):
                    description.append(f"• {member.mention} ({member.id}): {humanize_list([f'{temp_role.mention} ({temp_role.id})' for temp_role in member_temp_roles])}.")
            if description:
                description = "\n".join(description)
            else:
                description = _("No active Temp Roles on this server.")
        embeds = []
        pages = list(pagify(description, page_length=3000))
        for page in pages:
            embed: discord.Embed = discord.Embed(title=_("Temp Roles"), color=await ctx.embed_color())
            embed.description = page
            embeds.append(embed)
        await Menu(pages=embeds).start(ctx)

    @commands.admin_or_permissions(administrator=True)
    @temproles.command()
    async def logschannel(self, ctx: commands.Context, logs_channel: discord.TextChannel = None) -> None:
        """Set the logs channel for Temp Roles."""
        if logs_channel is None:
            await self.config.guild(ctx.guild).logs_channel.clear()
            await ctx.send(_("Logs channel unset."))
        else:
            if not logs_channel.permissions_for(ctx.me).embed_links:
                raise commands.UserFeedbackCheckFailure(_("I need of the `embed_links` permission in the logs channel."))
            await self.config.guild(ctx.guild).logs_channel.set(logs_channel.id)
            await ctx.send(_("Logs channel set."))

    @commands.admin_or_permissions(administrator=True)
    @temproles.command()
    async def addallowedselftemprole(self, ctx: commands.Context, role: discord.Role, min_time: typing.Optional[OptionalTimeConverter] = datetime.timedelta(days=1), max_time: typing.Optional[OptionalTimeConverter] = datetime.timedelta(days=365)) -> None:
        """Add an allowed self Temp Role.

        **Parameters:**
        - `min_time`: The minimum time for the self temp role. `none` to disable. Defaults is 1 day.
        - `max_time`: The minimum time for the self temp role. `none` to disable. Defaults is 365 days.
        """
        if role >= ctx.guild.me.top_role or (role >= ctx.author.top_role and ctx.author != ctx.guild.owner):
            raise commands.UserFeedbackCheckFailure(_("The role {role.mention} ({role.id}) cannot be assigned due to the Discord role hierarchy.").format(role=role))
        allowed_self_temp_roles = await self.config.guild(ctx.guild).allowed_self_temp_roles()
        if str(role.id) in allowed_self_temp_roles:
            raise commands.UserFeedbackCheckFailure(_("This role is already an allowed self temp role."))
        allowed_self_temp_roles[str(role.id)] = {"min_time": None if min_time is None else int(min_time.total_seconds()), "max_time": None if max_time is None else int(max_time.total_seconds())}
        await self.config.guild(ctx.guild).allowed_self_temp_roles.set(allowed_self_temp_roles)
        await ctx.send(_("Allowed self Temp Role added."))

    @commands.admin_or_permissions(administrator=True)
    @temproles.command()
    async def removeallowedselftemprole(self, ctx: commands.Context, role: discord.Role) -> None:
        """Remove an allowed self Temp Role."""
        allowed_self_temp_roles = await self.config.guild(ctx.guild).allowed_self_temp_roles()
        if str(role.id) not in allowed_self_temp_roles:
            raise commands.UserFeedbackCheckFailure(_("This role isn't an allowed self temp role."))
        del allowed_self_temp_roles[str(role.id)]
        await self.config.guild(ctx.guild).allowed_self_temp_roles.set(allowed_self_temp_roles)
        await ctx.send(_("Allowed self Temp Role removed."))

    @temproles.command(aliases=["selfadd"])
    async def selfassign(self, ctx: commands.Context, role: discord.Role, *, time: TimeConverter) -> None:
        """Assign/Add an allowed self Temp Role to yourself, for a specified duration."""
        if str(role.id) not in (allowed_self_temp_roles := await self.config.guild(ctx.guild).allowed_self_temp_roles()):
            raise commands.UserFeedbackCheckFailure(_("This role isn't an allowed self Temp Role on this server."))
        if allowed_self_temp_roles[str(role.id)]["min_time"] is not None:
            min_time = datetime.timedelta(seconds=allowed_self_temp_roles[str(role.id)]["min_time"])
            if time < min_time:
                raise commands.UserFeedbackCheckFailure(_("The time for this role must be greater than {min_time_string}.").format(min_time_string=CogsUtils.get_interval_string(min_time)))
        if allowed_self_temp_roles[str(role.id)]["max_time"] is not None:
            max_time = datetime.timedelta(seconds=allowed_self_temp_roles[str(role.id)]["max_time"])
            if time > max_time:
                raise commands.UserFeedbackCheckFailure(_("The time for this role must be less than {max_time_string}.").format(max_time_string=CogsUtils.get_interval_string(max_time)))
        await self.assign.callback(self, ctx, member=ctx.author, role=role, time=time)

    @temproles.command(aliases=["selfremove"])
    async def selfunassign(self, ctx: commands.Context, role: discord.Role) -> None:
        """Unassign/Remove an allowed self Temp Role from yourself."""
        if str(role.id) not in await self.config.guild(ctx.guild).allowed_self_temp_roles():
            raise commands.UserFeedbackCheckFailure(_("You can't remove this role from yourself."))
        await self.unassign.callback(self, ctx, member=ctx.author, role=role)

    @temproles.command()
    async def selflist(self, ctx: commands.Context) -> None:
        """Unassign/Remove an allowed self Temp Role from yourself."""
        description = ""
        BREAK_LINE = "\n"
        if (member_temp_roles := {temp_role: end_time for temp_role_id, end_time in (await self.config.member(ctx.author).temp_roles()).items() if (temp_role := ctx.guild.get_role(int(temp_role_id))) is not None}):
            description += f"**Your current Temp Roles:**\n{BREAK_LINE.join([f'• {temp_role.mention} ({temp_role.id}) - Expires <t:{int(end_time)}:R>.' for temp_role, end_time in member_temp_roles.items()])}\n\n"
        if (allowed_self_temp_roles := {role: (data["min_time"], data["max_time"]) for role_id, data in (await self.config.guild(ctx.guild).allowed_self_temp_roles()).items() if (role := ctx.guild.get_role(int(role_id))) is not None}):
            description += f"**Allowed self Temp Roles on this server:**\n{BREAK_LINE.join([f'• {role.mention} ({role.id}) - Min time `{CogsUtils.get_interval_string(min_time) if min_time is not None else None}`. - Max time `{CogsUtils.get_interval_string(max_time) if max_time is not None else None}`.' for role, (min_time, max_time) in allowed_self_temp_roles.items()])}"
        embeds = []
        pages = list(pagify(description, page_length=3000))
        for page in pages:
            embed: discord.Embed = discord.Embed(title=_("Self Temp Roles"), color=await ctx.embed_color())
            embed.description = page
            embeds.append(embed)
        await Menu(pages=embeds).start(ctx)

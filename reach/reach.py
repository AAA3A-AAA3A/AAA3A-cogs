from AAA3A_utils import Cog, Menu  # isort:skip
from redbot.core import commands, Config  # isort:skip
from redbot.core.bot import Red  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import itertools
import time

from collections import Counter

from redbot.core.utils.chat_formatting import humanize_list, humanize_number

# Credits:
# General repo credits.
# Thanks to evanroby for the idea (including the search command) and the initial implementation!

_: Translator = Translator("Reach", __file__)

STATUS_EMOJIS: typing.Dict[str, str] = {
    "online": "🟢",
    "idle": "🟡",
    "dnd": "🔴",
    "offline": "⚫",
    "invisible": "⚫",
}


@cog_i18n(_)
class Reach(Cog):
    """Check the reach of ping roles in specific channels and find the closest ping roles for the number of members you want to ping!"""

    __authors__: typing.List[str] = ["AAA3A", "evanroby"]

    def __init__(self, bot: Red) -> None:
        super().__init__(bot=bot)

        self.config: Config = Config.get_conf(
            self,
            identifier=205192943327321000143939875896557571750,
            force_registration=True,
        )
        self.config.register_guild(roles_for_search=[])

    @commands.guild_only()
    @commands.admin_or_permissions(mention_everyone=True)
    @commands.hybrid_group()
    async def reach(self, ctx: commands.Context) -> None:
        """Check the reach of ping roles in specific channels and find the closest ping roles for the number of members you want to ping!"""
        pass

    @reach.command()
    async def check(
        self,
        ctx: commands.Context,
        channel: typing.Optional[discord.TextChannel],
        roles: commands.Greedy[discord.Role],
        include_statuses: bool = False,
    ) -> None:
        """Check the reach of specific ping roles in a specific channel."""
        channel = channel or ctx.channel
        if not roles:
            raise commands.UserFeedbackCheckFailure(_("You must provide at least one role to check reach for."))
        embed: discord.Embed = discord.Embed(
            title=_("Reach Check"),
            description=_("**Channel:** {channel.mention} (`{channel.id}`)\n").format(channel=channel),
            color=await ctx.embed_color(),
            timestamp=ctx.message.created_at,
        )
        channel_members = set(channel.members)
        total_human_count, total_access_count, total_statuses = 0, 0, Counter()
        for i, role in enumerate(roles, start=1):
            human_members = [member for member in role.members if not member.bot]
            access_members = set(channel_members) & set(role.members)
            human_count, access_count = len(human_members), len(access_members)
            total_access_count += access_count
            total_human_count += human_count
            reach = access_count / human_count * 100 if human_count > 0 else 0.00
            if include_statuses:
                access_member_statuses = Counter(
                    member.status.value
                    for member in access_members
                )
                total_statuses.update(access_member_statuses)
            embed.description += _(
                "\n{i}. **{role.mention}** (`{role.id}`)\n"
                "  - Human members: **{human_count}**\n"
                "  - Members with channel access: **{access_count}**\n"
                "  - Reach: **{reach}**"
            ).format(
                i=i,
                role=role,
                human_count=humanize_number(human_count),
                access_count=humanize_number(access_count),
                reach=f"{reach:.2f}%",
            ) + (
                _("\n  - Statuses: {statuses}").format(
                    statuses=humanize_list(
                        [f"{STATUS_EMOJIS[name]} {count}" for name, count in access_member_statuses.most_common()]
                    )
                ) if include_statuses and access_member_statuses else ""
            )
        embed.add_field(
            name=_("**Total:**"),
            value=_(
                "- Human members: **{human_count}**\n"
                "- Members with channel access: **{access_count}**\n"
                "- Reach: **{reach}**"
            ).format(
                human_count=humanize_number(total_human_count),
                access_count=humanize_number(total_access_count),
                reach=f"{total_access_count / total_human_count * 100:.2f}%",
            ) + (
                _("\n- Statuses: {statuses}").format(
                    statuses=humanize_list(
                        [f"{STATUS_EMOJIS[name]} {count}" for name, count in total_statuses.most_common()]
                    )
                ) if include_statuses and total_statuses else ""
            ),
        )
        embed.set_footer(text=ctx.guild.name, icon_url=ctx.guild.icon)
        await Menu(pages=[embed]).start(ctx)

    @reach.command()
    async def search(
        self,
        ctx: commands.Context,
        channel: typing.Optional[discord.TextChannel],
        amount: commands.Range[int, 1, None],
        possible_combinations: typing.Optional[commands.Range[int, 1, 3]] = 1,
        possible_roles: commands.Greedy[discord.Role] = [],
        include_statuses: bool = False,
    ) -> None:
        """Find the closest ping roles for the amount of members you want to ping in a specific channel."""
        channel = channel or ctx.channel
        if possible_roles:
            roles = possible_roles
        elif not (roles_for_search := await self.config.guild(ctx.guild).roles_for_search()):
            roles = ctx.guild.roles
        else:
            roles = [
                role
                for role_id in roles_for_search
                if (role := ctx.guild.get_role(role_id)) is not None
            ]
        if not roles:
            raise commands.UserFeedbackCheckFailure(_("There are no roles to search for."))
        start = time.time()
        channel_members = set(channel.members)
        role_members = {role: set(role.members) for role in roles}
        result = []
        for i in range(1, possible_combinations + 1):
            for combination in itertools.combinations(roles, i):
                human_members = set(member for role in combination for member in role_members[role] if not member.bot)
                access_members = channel_members & human_members
                human_count, access_count = len(human_members), len(access_members)
                reach = access_count / human_count * 100 if human_count > 0 else 0.00
                if include_statuses:
                    access_member_statuses = Counter(
                        member.status.value
                        for member in channel_members & human_members
                    )
                else:
                    access_member_statuses = {}
                result.append(
                    {
                        "roles": combination,
                        "human_count": human_count,
                        "access_count": access_count,
                        "reach": reach,
                        "difference": access_count - amount,
                        "statuses": access_member_statuses,
                    }
                )
        result.sort(
            key=lambda x: (abs(x["difference"]), len(x["roles"]), -x["reach"]),
        )
        embed: discord.Embed = discord.Embed(
            title=_("Reach Search Results"),
            description=_("**Channel:** {channel.mention} (`{channel.id}`)\n**Target amount:** {amount}\n").format(
                channel=channel,
                amount=humanize_number(amount),
            ),
            color=await ctx.embed_color(),
            timestamp=ctx.message.created_at,
        )
        for i, item in enumerate(result[:5], start=1):
            embed.description += _(
                "\n{i}. **{roles}**\n"
                "  - Human members: **{human_count}**\n"
                "  - Members with channel access: **{access_count}**\n"
                "  - Reach: **{reach}**\n"
                "  - Difference from requested amount: **{difference}**"
            ).format(
                i=i,
                roles=humanize_list([role.mention for role in item["roles"]]),
                human_count=humanize_number(item["human_count"]),
                access_count=humanize_number(item["access_count"]),
                reach=f"{item['reach']:.2f}%",
                difference=item["difference"],
            ) + (
                _("\n  - Statuses: {statuses}").format(
                    statuses=humanize_list(
                        [f"{STATUS_EMOJIS[name]} {count}" for name, count in item["statuses"].most_common()]
                    )
                ) if include_statuses and item["statuses"] else ""
            )
        end = time.time()
        embed.set_footer(
            text=_("{ctx.guild.name} | Checked in {time} seconds.").format(
                ctx=ctx,
                time=f"{end - start:.2f}",
            ),
            icon_url=ctx.guild.icon,
        )
        await Menu(pages=[embed]).start(ctx)

    @reach.command()
    async def setrolesforsearch(self, ctx: commands.Context, roles: commands.Greedy[discord.Role]) -> None:
        """Set the roles to search for. This will replace the current list of roles to search for."""
        if not roles:
            raise commands.UserFeedbackCheckFailure(_("You must provide at least one role to search for."))
        await self.config.guild(ctx.guild).roles_for_search.set([role.id for role in roles])

    @reach.command()
    async def addroleforsearch(self, ctx: commands.Context, role: discord.Role) -> None:
        """Add a role to the list of roles to search for."""
        async with self.config.guild(ctx.guild).roles_for_search() as roles_for_search:
            if role.id in roles_for_search:
                raise commands.UserFeedbackCheckFailure(_("This role is already in the list of roles to search for."))
            roles_for_search.append(role.id)

    @reach.command()
    async def removeroleforsearch(self, ctx: commands.Context, role: discord.Role) -> None:
        """Remove a role from the list of roles to search for."""
        async with self.config.guild(ctx.guild).roles_for_search() as roles_for_search:
            if role.id not in roles_for_search:
                raise commands.UserFeedbackCheckFailure(_("This role is not in the list of roles to search for."))
            roles_for_search.remove(role.id)

    @reach.command()
    async def listrolesforsearch(self, ctx: commands.Context) -> None:
        """List the roles that are in the list of roles to search for."""
        roles_for_search = await self.config.guild(ctx.guild).roles_for_search()
        if not roles_for_search:
            raise commands.UserFeedbackCheckFailure(_("There are no roles in the list of roles to search for."))
        embed: discord.Embed = discord.Embed(
            title=_("Roles to search for"),
            description=humanize_list(
                [
                    f"- {role.mention} (`{role.id}`) - {humanize_number(len(role.members))} members"
                    for role_id in roles_for_search
                    if (role := ctx.guild.get_role(role_id)) is not None
                ]
            ),
            color=await ctx.embed_color(),
            timestamp=ctx.message.created_at,
        )
        embed.set_footer(text=ctx.guild.name, icon_url=ctx.guild.icon)
        await Menu(pages=[embed]).start(ctx)

    @reach.command()
    async def clearrolesforsearch(self, ctx: commands.Context) -> None:
        """Clear the list of roles to search for."""
        await self.config.guild(ctx.guild).roles_for_search.clear()

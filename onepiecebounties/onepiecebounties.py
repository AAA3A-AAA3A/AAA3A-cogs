from AAA3A_utils import Cog, Settings, Menu  # isort:skip
from redbot.core import commands, Config  # isort:skip
from redbot.core.bot import Red  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

from redbot.core.utils.chat_formatting import pagify

import datetime
import random
import re
from io import BytesIO
from wantedposter.wantedposter import WantedPoster, CaptureCondition

from .plugins.welcome import WelcomePlugin

# Credits:
# General repo credits.

_: Translator = Translator("OnePieceBounties", __file__)


class BountyConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> int:
        argument = argument.replace(",", "")
        try:
            bounty = int(argument)
        except ValueError:
            ext = argument[-1].lower()
            exts = {
                "k": 1_000,
                "m": 1_000_000,
                "b": 1_000_000_000,
            }
            if ext not in exts:
                raise commands.BadArgument(
                    _("The bounty must be a number or a number with a suffix (`k`, `m`, `b`).")
                )
            bounty = int(float(argument[:-1]) * exts[ext])
        # if bounty < 0:
        #     raise commands.BadArgument(_("The bounty can't be negative."))
        if abs(bounty) > 100_000_000_000:
            raise commands.BadArgument(_("The bounty can't be higher than 100 billion."))
        return bounty


class LabelLinkConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> typing.List[typing.Union[str, int]]:
        arg_split = re.split(r"[;,|\-]", argument)
        try:
            label, link = arg_split
        except ValueError:
            raise commands.BadArgument(
                _(
                    "LabelChannel must be a label followed by a channel separated by either `;`, `,`, `|`, or `-`."
                )
            )
        if not 1 <= len(label) <= 50:
            raise commands.BadArgument(_("The label must be between 1 and 50 characters long."))
        if not link.startswith("https://"):
            raise commands.BadArgument(_("The link must start with `https://`."))
        return [label, link]


@cog_i18n(_)
class OnePieceBounties(WelcomePlugin, Cog):
    """Give One Piece's bounties to your members, based on their time in the server, their level and their roles, then generate their wanted posters, and also welcome them when they join!"""

    __authors__: typing.List[str] = ["AAA3A", "ultpanda"]

    def __init__(self, bot: Red) -> None:
        super().__init__(bot=bot)

        self.config: Config = Config.get_conf(
            self,
            identifier=205192943327321000143939875896557571750,
            force_registration=True,
        )
        self.config.register_guild(
            base_bounty=0,
            random_base_bounty=True,
            include_months_since_joining=True,
            include_levelup_levels=True,
            bonus_roles={},
            only_roles={},
            plugins={
                "Welcome": {
                    "enabled": False,
                    "channel": None,
                    "log_pose_channels": [],
                    "link_buttons": [],
                },
            },
        )
        self.config.register_member(
            bonus=0,
            accurate_joined_at=None,
        )

        _settings: typing.Dict[
            str, typing.Dict[str, typing.Union[typing.List[str], bool, str]]
        ] = {
            "base_bounty": {
                "converter": BountyConverter,
                "description": "Set the base bounty for all members.",
            },
            "random_base_bounty": {
                "converter": bool,
                "description": "Enable or disable randomization of the base bounty.",
            },
            "include_months_since_joining": {
                "converter": bool,
                "description": "Include months since joining in bounty calculation.",
            },
            "include_levelup_levels": {
                "converter": bool,
                "description": "Include LevelUp levels in bounty calculation.",
            },
            # Welcome plugin.
            "welcome_enabled": {
                "converter": bool,
                "description": "Enable or disable the welcome message.",
                "path": ["plugins", "Welcome", "enabled"],
            },
            "welcome_channel": {
                "converter": typing.Union[discord.TextChannel, discord.VoiceChannel, discord.Thread],
                "description": "Set the welcome channel.",
                "path": ["plugins", "Welcome", "channel"],
            },
            "welcome_log_pose_channels": {
                "converter": commands.Greedy[typing.Union[discord.TextChannel, discord.VoiceChannel, discord.Thread]],
                "description": "Set the log pose channels for the welcome message.",
                "path": ["plugins", "Welcome", "log_pose_channels"],
            },
            "welcome_link_buttons": {
                "converter": commands.Greedy[LabelLinkConverter],
                "description": "Set the link buttons for the welcome message.",
                "path": ["plugins", "Welcome", "link_buttons"],
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
            commands_group=self.setonepiecebounties,
        )

    async def cog_load(self) -> None:
        await super().cog_load()
        await self.settings.add_commands()

    async def get_bounty(self, member: discord.Member) -> int:
        guild = member.guild
        config = await self.config.guild(guild).all()

        bounty = config["base_bounty"]
        if config["random_base_bounty"]:
            random.seed(f"{member.id}-base-1")
            larger = random.random() < 0.1
            random.seed(f"{member.id}-base-2")
            if larger:
                bounty += random.randint(1_000_000, 10_000_000)
            else:
                bounty += random.randint(10_000_000, 20_000_000)
        
        if config["include_months_since_joining"]:
            if (
                joined_at := (
                    member.joined_at
                    if (accurate_joined_at := await self.config.member(member).accurate_joined_at()) is None
                    else datetime.datetime.fromisoformat(accurate_joined_at).replace(tzinfo=datetime.timezone.utc)
                )
            ) is not None:
                months = (datetime.datetime.now(tz=datetime.timezone.utc) - joined_at).days / 30
                for i in range(1, int(months) + 2):
                    random.seed(f"{member.id}-month-{i}")
                    year = i // 12
                    min_bounty = 4_000_000 + (year * 1_500_000)
                    max_bounty = 8_000_000 + (year * 1_500_000)
                    bounty += int(
                        random.randint(min_bounty, max_bounty) * (
                            months - i if i == int(months) else 1
                        )
                    )
        
        if (
            config["include_levelup_levels"]
            and (LevelUp := self.bot.get_cog("LevelUp")) is not None
            and (conf := LevelUp.db.get_conf(guild)).enabled
        ):
            level = conf.get_profile(member.id).level
            for i in range(1, level + 1):
                random.seed(f"{member.id}-level-{i}")
                l10 = i // 10
                min_bounty = 10_000_000 + (l10 * 2_000_000)
                max_bounty = 20_000_000 + (l10 * 2_000_000)
                bounty += random.randint(min_bounty, max_bounty)
        
        if config["bonus_roles"]:
            for role in member.roles:
                if str(role.id) in config["bonus_roles"]:
                    random.seed(f"{member.id}-role-{role.id}")
                    bounty += random.randint(
                        config["bonus_roles"][str(role.id)][0], config["bonus_roles"][str(role.id)][1]
                    )
        
        bounty += await self.config.member(member).bonus()

        if bounty <= 1:
            return 1
        if bounty > 1_000_000_000:
            return round(bounty, -7)
        elif bounty > 100_000_000:
            return round(bounty, -6)
        elif bounty > 10_000_000:
            return round(bounty, -5)
        elif bounty > 1_000_000:
            return round(bounty, -4)
        elif bounty > 100_000:
            return round(bounty, -3)
        elif bounty > 10_000:
            return round(bounty, -2)
        elif bounty > 1_000:
            return round(bounty, -1)
        return bounty

    async def generate_wanted_poster(self, member: discord.Member, bounty: int = None) -> discord.File:
        names = ["display_name", "global_name", "name"]
        for attr in names:
            value = getattr(member, attr)
            if value is None:
                continue
            name = value
            if len([c for c in name if c.isalpha()]) >= 3:
                break
        wanted_poster = WantedPoster(
            portrait=BytesIO(await member.display_avatar.read()),
            first_name=name,
            bounty=bounty or await OnePieceBounties.get_bounty(member),
        )
        capture_condition = CaptureCondition.DEAD_OR_ALIVE
        only_roles = await self.config.guild(member.guild).only_roles()
        for role in reversed(member.roles):
            if str(role.id) in only_roles:
                capture_condition = (
                    CaptureCondition.ONLY_ALIVE
                    if only_roles[str(role.id)] == "alive"
                    else CaptureCondition.ONLY_DEAD
                )
                break
        buffer = BytesIO()
        buffer.name = "wanted_poster.png"
        wanted_poster.generate(
            buffer,
            capture_condition=capture_condition,
        )
        buffer.seek(0)
        return discord.File(buffer, filename="wanted_poster.png")

    def get_bounty_tiers(self) -> typing.List[typing.Tuple[str, int]]:
        return [
            (_("Pirate King"), 3_000_000_000),
            (_("Emperor"), 1_000_000_000),
            (_("Yonko Commander"), 500_000_000),
            (_("Supernova"), 100_000_000),
            (_("Grand Line"), 50_000_000),
            (_("East Blue"), 10_000_000),
            (_("Sailing Rookie"), 1_000_000),
            (_("Sailor"), 1),
        ]

    def get_bounty_tier(self, bounty: int) -> str:
        return next(
            (tier for tier, min_bounty in self.get_bounty_tiers() if bounty >= min_bounty)
        )

    async def get_kwargs(self, member: discord.Member) -> typing.Dict[str, typing.Union[discord.Embed, discord.File]]:
        bounty = await self.get_bounty(member)
        bounty_tier = self.get_bounty_tier(bounty)
        embed: discord.Embed = discord.Embed(
            title=_("Marine HQ has issued a bounty of **{bounty:,}** {berries} for **{member.display_name}**, worthy of a **{bounty_tier} Level Threat**!").format(
                member=member,
                bounty=bounty,
                berries=_("berries") if bounty > 1 else _("berry"),
                bounty_tier=bounty_tier,
            ),
            color=await self.bot.get_embed_color(member),
            timestamp=datetime.datetime.now(tz=datetime.timezone.utc),
        )
        embed.set_footer(
            text=member.guild.name,
            icon_url=member.guild.icon,
        )
        embed.set_image(
            url="attachment://wanted_poster.png",
        )
        file = await self.generate_wanted_poster(member, bounty)
        return {
            "embed": embed,
            "file": file,
        }

    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    @commands.hybrid_command(aliases=["wantedposter", "wanted"])
    async def bounty(
        self,
        ctx: commands.Context,
        *,
        member: discord.Member = commands.Author,
    ) -> None:
        """🏴‍☠️ Get the bounty of a member."""
        if member.bot:
            return await ctx.send(_("Bots don't have a bounty!"))
        await ctx.send(**await self.get_kwargs(member))

    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    @commands.hybrid_command(aliases=["wantedlb", "bountyleaderboard", "wantedleaderboard"])
    async def bountylb(self, ctx: commands.Context) -> None:
        """🏴‍☠️ Get the bounty leaderboard."""
        embed: discord.Embed = discord.Embed(
            title=_("🏴‍☠️ Bounty Leaderboard 🏴‍☠️"),
            color=await ctx.embed_color(),
        )
        embed.set_footer(
            text=ctx.guild.name,
            icon_url=ctx.guild.icon,
        )
        description = "\n".join(
            [
                _("**{i}.** {member.display_name}: **{bounty:,}** {berries}").format(
                    i=i,
                    member=member,
                    bounty=bounty,
                    berries=_("berries") if bounty > 1 else _("berry"),
                )
                for i, (member, bounty) in enumerate(
                    sorted(
                        [
                            (member, await self.get_bounty(member))
                            for member in ctx.guild.members
                            if not member.bot
                        ],
                        key=lambda x: x[1],
                        reverse=True,
                    ),
                    start=1,
                )
            ]
        )
        if not description:
            raise commands.UserFeedbackCheckFailure(_("There are no bounties."))
        embeds = []
        for page in pagify(description, page_length=3000):
            e = embed.copy()
            e.description = page
            embeds.append(e)
        await Menu(pages=embeds).start(ctx)

    @commands.admin_or_permissions(manage_guild=True)
    @commands.hybrid_group(aliases=["setopb"])
    async def setonepiecebounties(self, ctx: commands.Context) -> None:
        """Configure One Piece Bounties."""
        pass

    @setonepiecebounties.command(aliases=["addbr"])
    async def addbonusrole(
        self,
        ctx: commands.Context,
        role: discord.Role,
        min_bounty: BountyConverter,
        max_bounty: BountyConverter = None,
    ) -> None:
        """Add a bonus role to the bounty calculation."""
        max_bounty = max_bounty or min_bounty
        if min_bounty > max_bounty:
            return await ctx.send(_("The minimum bounty can't be higher than the maximum bounty!"))
        async with self.config.guild(ctx.guild).bonus_roles() as bonus_roles:
            bonus_roles[str(role.id)] = (min_bounty, max_bounty)

    @setonepiecebounties.command(aliases=["removebr"])
    async def removebonusrole(self, ctx: commands.Context, role: discord.Role) -> None:
        """Remove a bonus role from the bounty calculation."""
        async with self.config.guild(ctx.guild).bonus_roles() as bonus_roles:
            if str(role.id) in bonus_roles:
                del bonus_roles[str(role.id)]
            else:
                raise commands.UserFeedbackCheckFailure(_("This role is not in the list of bonus roles."))

    @setonepiecebounties.command(aliases=["listbr"])
    async def listbonusroles(self, ctx: commands.Context) -> None:
        """List all bonus roles."""
        bonus_roles = await self.config.guild(ctx.guild).bonus_roles()
        if not bonus_roles:
            raise commands.UserFeedbackCheckFailure(_("There are no bonus roles."))
        description = "\n".join(
            [
                _("{role.mention}: {min_bounty:,} - {max_bounty:,} {berries}").format(
                    role=role,
                    min_bounty=bounties[0], max_bounty=bounties[1],
                    berries=_("berries") if abs(bounties[0]) > 1 else _("berry"),
                )
                for role_id, bounties in bonus_roles.items()
                if (role := ctx.guild.get_role(int(role_id))) is not None
            ]
        )
        embed: discord.Embed = discord.Embed(
            title=_("Bonus Roles"),
            description=_("The following roles give a bonus to the bounty calculation:"),
            color=await ctx.embed_color(),
        )
        embed.set_footer(
            text=ctx.guild.name,
            icon_url=ctx.guild.icon,
        )
        embeds = []
        for page in pagify(description, page_length=3000):
            e = embed.copy()
            e.description = page
            embeds.append(e)
        await Menu(pages=embeds).start(ctx)

    @setonepiecebounties.command(aliases=["addor"])
    async def addonlyrole(
        self,
        ctx: commands.Context,
        role: discord.Role,
        only: typing.Literal["alive", "dead"],
    ) -> None:
        """Add a role to the only roles list."""
        async with self.config.guild(ctx.guild).only_roles() as only_roles:
            if str(role.id) in only_roles:
                raise commands.UserFeedbackCheckFailure(_("This role is already in the list of only roles."))
            only_roles[str(role.id)] = only

    @setonepiecebounties.command(aliases=["removeor"])
    async def removeonlyrole(self, ctx: commands.Context, role: discord.Role) -> None:
        """Remove a role from the only roles list."""
        async with self.config.guild(ctx.guild).only_roles() as only_roles:
            if str(role.id) in only_roles:
                del only_roles[str(role.id)]
            else:
                raise commands.UserFeedbackCheckFailure(_("This role is not in the list of only roles."))

    @setonepiecebounties.command(aliases=["listor"])
    async def listonlyroles(self, ctx: commands.Context) -> None:
        """List all only roles."""
        only_roles = await self.config.guild(ctx.guild).only_roles()
        if not only_roles:
            raise commands.UserFeedbackCheckFailure(_("There are no only roles."))
        description = "\n".join(
            [
                _("{role.mention}: ONLY {only}").format(role=role, only=only.upper())
                for role_id, only in only_roles.items()
                if (role := ctx.guild.get_role(int(role_id))) is not None
            ]
        )
        embed: discord.Embed = discord.Embed(
            title=_("Only Roles"),
            color=await ctx.embed_color(),
        )
        embed.set_footer(
            text=ctx.guild.name,
            icon_url=ctx.guild.icon,
        )
        embeds = []
        for page in pagify(description, page_length=3000):
            e = embed.copy()
            e.description = page
            embeds.append(e)
        await Menu(pages=embeds).start(ctx)

    @setonepiecebounties.command(aliases=["addb"])
    async def addbonus(
        self,
        ctx: commands.Context,
        member: typing.Optional[discord.Member],
        bonus: BountyConverter,
    ) -> None:
        """Add a bonus to a member's bounty."""
        member = member or ctx.author
        if member.bot:
            return await ctx.send(_("Bots don't have a bounty!"))
        current_bonus = await self.config.member(member).bonus()
        current_bonus += bonus
        await self.config.member(member).bonus.set(current_bonus)

    @setonepiecebounties.command(aliases=["removeb"])
    async def removebonus(
        self,
        ctx: commands.Context,
        member: typing.Optional[discord.Member],
        bonus: BountyConverter,
    ) -> None:
        """Remove a bonus from a member's bounty."""
        member = member or ctx.author
        if member.bot:
            return await ctx.send(_("Bots don't have a bounty!"))
        current_bonus = await self.config.member(member).bonus()
        current_bonus -= bonus
        await self.config.member(member).bonus.set(current_bonus)

    @setonepiecebounties.command(aliases=["clearb"])
    async def clearbonus(self, ctx: commands.Context, member: typing.Optional[discord.Member]) -> None:
        """Clear a member's bonus."""
        member = member or ctx.author
        if member.bot:
            return await ctx.send(_("Bots don't have a bounty!"))
        await self.config.member(member).bonus.clear()

    @setonepiecebounties.command(aliases=["listbonus", "listb"])
    async def listbonuses(self, ctx: commands.Context) -> None:
        """List all bonuses."""
        bonuses = await self.config.all_members(guild=ctx.guild)
        if not bonuses:
            raise commands.UserFeedbackCheckFailure(_("There are no bonuses."))
        description = "\n".join(
            [
                _("{member.mention}: {bonus:,} {berries}").format(
                    member=member,
                    bonus=bonus["bonus"],
                    berries=_("berries") if abs(bonus["bonus"]) > 1 else _("berry"),
                )
                for member_id, bonus in bonuses.items()
                if (
                    (member := ctx.guild.get_member(member_id)) is not None
                    and bonus["bonus"] > 0
                )
            ]
        )
        embed: discord.Embed = discord.Embed(
            title=_("Bonuses"),
            description=_("The following members have a bonus to their bounty:"),
            color=await ctx.embed_color(),
        )
        embed.set_footer(
            text=ctx.guild.name,
            icon_url=ctx.guild.icon,
        )
        embeds = []
        for page in pagify(description, page_length=3000):
            e = embed.copy()
            e.description = page
            embeds.append(e)
        await Menu(pages=embeds).start(ctx)

    @setonepiecebounties.command()
    async def setaccuratejoinedat(
        self,
        ctx: commands.Context,
        member: discord.Member = commands.Author,
        date: str = None,
    ) -> None:
        """Set the accurate joined at date of a member in the format `YYYY-MM-DD`."""
        try:
            accurate_joined_at = datetime.datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise commands.UserFeedbackCheckFailure(_("Please provide a date in the format `YYYY-MM-DD`."))
        await self.config.member(member).accurate_joined_at.set(accurate_joined_at.isoformat())

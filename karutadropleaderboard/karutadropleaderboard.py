from AAA3A_utils import Cog, Menu, Settings, Loop  # isort:skip
from redbot.core import commands, Config  # isort:skip
from redbot.core.bot import Red  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

from redbot.core.utils.chat_formatting import pagify

import datetime

from .dashboard_integration import DashboardIntegration

# Credits:
# General repo credits.

_: Translator = Translator("KarutaDropLeaderboard", __file__)

KARUTA_BOT_ID: int = 646937666251915264


@cog_i18n(_)
class KarutaDropLeaderboard(DashboardIntegration, Cog):
    """Get a leaderboard of Karuta drops in your server!"""

    def __init__(self, bot: Red) -> None:
        super().__init__(bot=bot)

        self.config: Config = Config.get_conf(
            self,
            identifier=205192943327321000143939875896557571750,
            force_registration=True,
        )
        self.config.register_guild(
            enabled=False,
            channels=[],
            drop_requirement=3,
        )
        self.config.register_member(
            drops=0,
            last_drops={},
        )

        _settings: typing.Dict[
            str, typing.Dict[str, typing.Union[typing.List[str], bool, str]]
        ] = {
            "enabled": {
                "converter": bool,
                "description": "Enable or disable the feature.",
            },
            "channels": {
                "converter": commands.Greedy[
                    typing.Union[discord.TextChannel, discord.VoiceChannel, discord.Thread]
                ],
                "description": "List of channels to track.",
            },
            "drop_requirement": {
                "converter": commands.Range[int, 1, 50],
                "description": "Number of drops required in the last 12 hours to meet the requirement.",
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
            commands_group=self.setkarutadropleaderboard,
        )

    async def cog_load(self) -> None:
        await super().cog_load()
        await self.settings.add_commands()
        self.loops.append(
            Loop(
                cog=self,
                name="Cleanup Last Drops",
                function=self.cleanup_last_drops,
                hours=1,
            )
        )

    @commands.Cog.listener()
    async def on_message_without_command(self, message: discord.Message) -> None:
        if message.guild is None:
            return
        if not message.author.bot or message.author.id != KARUTA_BOT_ID:
            return
        if "is dropping" not in message.content or not message.attachments:
            return
        config = await self.config.guild(message.guild).all()
        if not config["enabled"]:
            return
        if message.channel.id not in config["channels"]:
            return
        member = message.mentions[0]
        member_data = await self.config.member(member).all()
        member_data["drops"] += 1
        member_data["last_drops"][str(int(message.created_at.timestamp()))] = message.jump_url
        await self.config.member(member).set(member_data)

    async def cleanup_last_drops(self) -> None:
        now_timestamp = int(datetime.datetime.now(tz=datetime.timezone.utc).timestamp())
        for guild_id, data in (await self.config.all_members()).items():
            for member_id, member_data in data.items():
                if "last_drops" not in member_data:
                    continue
                new_last_drops = {
                    drop: message_link
                    for drop, message_link in member_data["last_drops"].items()
                    if int(drop) > (now_timestamp - 86400)
                }
                if new_last_drops != member_data["last_drops"]:
                    member_data["last_drops"] = new_last_drops
                    await self.config.member_from_ids(guild_id, member_id).set(member_data)

    @commands.bot_has_permissions(embed_links=True)
    @commands.hybrid_command(aliases=["karutadroplb", "karutadlb"])
    async def karutadropleaderboard(self, ctx: commands.Context) -> None:
        """Show leaderboard of Karuta drops."""
        all_members = await self.config.all_members(ctx.guild)
        all_members = {
            ctx.guild.get_member(member): data["drops"]
            for member, data in all_members.items()
            if ctx.guild.get_member(member) is not None
        }
        if not all_members:
            raise commands.UserFeedbackCheckFailure(_("No one has dropped cards yet."))
        sorted_members = sorted(all_members.items(), key=lambda x: x[1], reverse=True)
        you = next(
            (
                f"You: {num}/{len(all_members)}"
                for num, data in enumerate(sorted_members, start=1)
                if data[0] == ctx.author
            ),
            None,
        )
        embed: discord.Embed = discord.Embed(
            title=_("Leaderboard of Karuta drops"),
            color=await ctx.embed_color(),
            timestamp=ctx.message.created_at,
        )
        embed.set_footer(
            text=ctx.guild.name + (f" | {you}" if you is not None else ""),
            icon_url=ctx.guild.icon,
        )
        description = "\n".join(
            f"**{num}.** {member.mention} - **{drops}** {_('drops') if drops != 1 else _('drop')}"
            for num, (member, drops) in enumerate(sorted_members, start=1)
        )
        embeds = []
        for page in pagify(description, page_length=2000):
            e = embed.copy()
            e.description = page
            embeds.append(e)
        await Menu(pages=embeds).start(ctx)

    @commands.guild_only()
    @commands.hybrid_command(aliases=["karutadropreq", "dropreq"])
    async def karutadroprequirement(
        self,
        ctx: commands.Context,
        *,
        member: discord.Member = commands.Author,
    ) -> None:
        """Check Karuta drop requirement for a member."""
        embed: discord.Embed = discord.Embed(
            title=_("Karuta Drop Requirement"),
            timestamp=ctx.message.created_at,
        )
        embed.set_author(
            name=member.display_name,
            icon_url=member.display_avatar,
        )
        member_data = await self.config.member(member).all()
        now_timestamp = int(datetime.datetime.now(tz=datetime.timezone.utc).timestamp())
        embed.description = "\n".join(
            f"- {'✅' if int(drop) > (now_timestamp - 43200) else '⏲️'} {discord.utils.format_dt(datetime.datetime.fromtimestamp(int(drop)), style='R')} {message_jump_url}"
            for drop, message_jump_url in list(member_data["last_drops"].items())[-10:]
        )
        within_last_12_hours = sum(
            int(drop) > (now_timestamp - 43200)
            for drop in member_data["last_drops"]
        )
        drop_requirement = await self.config.guild(ctx.guild).drop_requirement()
        requirement_met = within_last_12_hours >= drop_requirement
        embed.color = discord.Color.green() if requirement_met else discord.Color.red()
        embed.add_field(
            name=(
                _("✅ Requirement met!")
                if requirement_met
                else _("❌ Requirement not met!")
            ),
            value=_("{within_last_12_hours} drop{s}/{drop_requirement} in the last 12 hours...").format(
                within_last_12_hours=within_last_12_hours,
                s="" if within_last_12_hours == 1 else "s",
                drop_requirement=drop_requirement,
            ),
        )
        embed.set_footer(text=ctx.guild.name, icon_url=ctx.guild.icon)
        await Menu(pages=[embed]).start(ctx)

    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    @commands.hybrid_group()
    async def setkarutadropleaderboard(self, ctx: commands.Context) -> None:
        """Group of commands to set up Karuta Drop Leaderboard."""
        pass

    @setkarutadropleaderboard.command()
    async def resetleaderboard(self, ctx: commands.Context) -> None:
        """Reset leaderboard in the guild."""
        await self.config.clear_all_members(ctx.guild)

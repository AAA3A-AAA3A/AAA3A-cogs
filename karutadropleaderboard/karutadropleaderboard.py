from AAA3A_utils import Cog, Menu, Settings  # isort:skip
from redbot.core import commands, Config  # isort:skip
from redbot.core.bot import Red  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

from redbot.core.utils.chat_formatting import pagify

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
        )
        self.config.register_member(drops=0)

        _settings: typing.Dict[
            str, typing.Dict[str, typing.Union[typing.List[str], bool, str]]
        ] = {
            "enabled": {
                "converter": bool,
                "description": "Enable or disable the feature.",
            },
            "channels": {
                "converter": commands.Greedy[typing.Union[discord.TextChannel, discord.VoiceChannel, discord.Thread]],
                "description": "List of channels to track.",
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

    @commands.Cog.listener()
    async def on_message_without_command(
        self, message: discord.Message
    ) -> None:
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
        drops = await self.config.member(member).drops()
        drops += 1
        await self.config.member(member).drops.set(drops)

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
    @commands.admin_or_permissions(manage_guild=True)
    @commands.hybrid_group()
    async def setkarutadropleaderboard(self, ctx: commands.Context) -> None:
        """Group of commands to set up Karuta Drop Leaderboard."""
        pass

    @setkarutadropleaderboard.command()
    async def resetleaderboard(self, ctx: commands.Context) -> None:
        """Reset leaderboard in the guild."""
        await self.config.clear_all_members(ctx.guild)

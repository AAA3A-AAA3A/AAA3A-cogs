from AAA3A_utils import Cog, Settings, Menu, Loop  # isort:skip
from AAA3A_utils.context import is_dev  # isort:skip
from redbot.core import commands, app_commands, Config  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import asyncio
import datetime
import os
from copy import deepcopy

from redbot.core.utils.chat_formatting import humanize_timedelta

from .anomalies import ANOMALIES, Anomaly
from .constants import ACHIEVEMENTS_COLOR, DEVELOPER, HELPERS, TESTERS, SUPPORTERS
from .game import Game
from .modes import MODES, Mode
from .roles import ACHIEVEMENTS, ROLES, GodFather, Role, Villager
from .utils import get_image
from .views import ExplainView, JoinGameView

# Credits:
# General repo credits.
# Thanks to C & Masterodeath22 for all their explanations and help!
# Thanks to the existing Mafia bots for the inspiration!
# A part of the text for the roles' `description` and `ability` fields has been taken from the Mafia Wiki (https://mafiabot.fandom.com/wiki/Roles)!
# All the images have been generated with Microsoft Copilot (https://copilot.microsoft.com/)!

_: Translator = Translator("MafiaGame", __file__)


class RoleConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> Role:
        argument = argument.lower().replace(" ", "")
        for role in ROLES:
            if argument == role.name.lower().replace(" ", ""):
                if ctx.command.name == "disabledroles" and isinstance(role, (GodFather, Villager)):
                    raise commands.BadArgument(
                        _("You can't disable the GodFather or the Villager role.")
                    )
                return role
        raise commands.BadArgument(_("Invalid Mafia role."))


class RoleNameConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> str:
        return (await RoleConverter().convert(ctx, argument)).name


class ModeConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> Mode:
        argument = argument.lower()
        for mode in MODES:
            if argument == mode.name.lower():
                return mode
        raise commands.BadArgument(_("Invalid Mafia mode."))


class ModeNameConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> str:
        return (await ModeConverter().convert(ctx, argument)).name


class AnomalyConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> Anomaly:
        argument = argument.lower()
        for anomaly in ANOMALIES:
            if argument == anomaly.name.lower():
                return anomaly
        raise commands.BadArgument(_("Invalid Mafia anomaly."))


class AnomalyNameConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> str:
        return (await AnomalyConverter().convert(ctx, argument)).name


DurationConverter: commands.converter.TimedeltaConverter = commands.converter.TimedeltaConverter(
    minimum=datetime.timedelta(minutes=30),
    maximum=None,
    allowed_units=["weeks", "days", "hours", "minutes"],
    default_unit="hours",
)


@cog_i18n(_)
class MafiaGame(Cog):
    """Play the Mafia game, with many roles (Mafia/Villagers/Neutral), modes (including Random and Custom), anomalies...!"""

    def __init__(self, bot: commands.Bot) -> None:
        super().__init__(bot=bot)
        self.config: Config = Config.get_conf(
            self,
            identifier=205192943327321000143939875896557571750,
            force_registration=True,
        )
        self.config.register_guild(
            # General settings.
            category=None,
            allow_spectators=True,
            add_reactions=True,
            default_mode="Classic",
            disabled_roles=[],
            more_roles=True,
            custom_roles=[],
            display_roles_when_starting=False,
            afk_days_before_kick=None,
            afk_temp_ban_duration=None,
            channel_auto_delete=False,
            game_logs=False,
            # Game settings.
            show_dead_role=True,
            dying_message=False,
            anonymous_voting=False,
            defend_judgement=True,
            anonymous_judgement=False,
            mafia_communication=True,
            town_traitor=False,
            town_vip=False,
            anomalies=False,
            disabled_anomalies=[],
            # Roles settings.
            vigilante_shoot_night_1=False,
            alchemist_lethal_potion_night_1=True,
            hoarder_hoard_same_player_if_failed=False,
            judge_prosecute_day_1=True,
            # Timeouts.
            perform_action_timeout=60,
            talk_timeout=50,
            voting_timeout=45,
            defend_timeout=30,
            judgement_timeout=20,
        )
        self.config.register_user(
            wins={},
            games={},
            achievements={},
            default_dying_message=None,
        )
        self.config.register_member(
            temp_banned_until=None,
        )

        _settings: typing.Dict[
            str, typing.Dict[str, typing.Union[typing.List[str], bool, str]]
        ] = {
            # General settings.
            "category": {
                "converter": discord.CategoryChannel,
                "description": "The category where the channel will be created.",
            },
            "allow_spectators": {
                "converter": bool,
                "description": "If this option is enabled, the cog will allow spectators to watch the game.",
            },
            "add_reactions": {
                "converter": bool,
                "description": "If this option is enabled, the alive players will be able to react to the messages.",
            },
            "default_mode": {
                "converter": ModeNameConverter,
                "description": "The default mode that will be used.",
            },
            "disabled_roles": {
                "converter": commands.Greedy[RoleNameConverter],
                "description": "The roles that will be disabled.",
                "aliases": ["droles"],
            },
            "more_roles": {
                "converter": bool,
                "description": "If this option is enabled, the cog will add more roles to the game.",
            },
            "custom_roles": {
                "converter": commands.Greedy[RoleNameConverter],
                "description": "The roles that will be assigned at the beginning of the game, if the mode is `Custom`.",
                "aliases": ["croles"],
            },
            "display_roles_when_starting": {
                "converter": bool,
                "description": "If this option is enabled, the cog will display the roles in game and their abilities when starting.",
            },
            "afk_days_before_kick": {
                "converter": commands.Range[int, 2, 30],
                "description": "The number of days before a player is kicked for being AFK.",
            },
            "afk_temp_ban_duration": {
                "converter": commands.Range[int, 1, None],
                "description": "The duration in hours of the temp ban for being AFK.",
            },
            "channel_auto_delete": {
                "converter": bool,
                "description": "If this option is enabled, the channel will be automatically deleted after the game.",
            },
            "game_logs": {
                "converter": bool,
                "description": "If this option is enabled, the cog will log the game in an HTML file.",
            },
            # Game settings.
            "show_dead_role": {
                "converter": bool,
                "description": "If this option is enabled, the cog will show the dead role to the players.",
            },
            "dying_message": {
                "converter": bool,
                "description": "If this option is enabled, the players will be able to set a custom death message.",
            },
            "anonymous_voting": {
                "converter": bool,
                "description": "If this option is enabled, the voting will be anonymous.",
            },
            "defend_judgement": {
                "converter": bool,
                "description": "If this option is enabled, the player who has been voted will be able to defend.",
            },
            "anonymous_judgement": {
                "converter": bool,
                "description": "If this option is enabled, the judgement will be anonymous.",
            },
            "mafia_communication": {
                "converter": bool,
                "description": "If this option is enabled, the Mafia members will be able to communicate.",
            },
            "town_traitor": {
                "converter": bool,
                "description": "If this option is enabled, the town will have a Traitor. The Traitor has to be killed within 3 days of last mafia death.",
            },
            "town_vip": {
                "converter": bool,
                "description": "If this option is enabled, the town will have a VIP who have to be killed by Mafia before win.",
            },
            "anomalies": {
                "converter": bool,
                "description": "If this option is enabled, the anomalies will be enabled.",
            },
            "disabled_anomalies": {
                "converter": commands.Greedy[AnomalyNameConverter],
                "description": "The anomalies that will be disabled.",
                "aliases": ["danomalies"],
            },
            # Roles settings.
            "vigilante_shoot_night_1": {
                "converter": bool,
                "description": "If this option is enabled, the Vigilante will be able to shoot on Night 1.",
                "no_slash": True,
            },
            "alchemist_lethal_potion_night_1": {
                "converter": bool,
                "description": "If this option is enabled, the Alchemist will be able to use the lethal potion on Night 1.",
                "no_slash": True,
            },
            "hoarder_hoard_same_player_if_failed": {
                "converter": bool,
                "description": "If this option is enabled, the Hoarder can hoard the same player again if they failed previously.",
                "no_slash": True,
            },
            "judge_prosecute_day_1": {
                "converter": bool,
                "description": "If this option is enabled, the Judge will be able to prosecute on Day 1.",
                "no_slash": True,
            },
            # Timeouts.
            "perform_action_timeout": {
                "converter": commands.Range[int, 10, 300],
                "description": "The time in seconds to perform an action.",
                "no_slash": True,
            },
            "talk_timeout": {
                "converter": commands.Range[int, 10, 300],
                "description": "The time in seconds to talk.",
                "no_slash": True,
            },
            "voting_timeout": {
                "converter": commands.Range[int, 10, 300],
                "description": "The time in seconds to vote.",
                "no_slash": True,
            },
            "defend_timeout": {
                "converter": commands.Range[int, 10, 300],
                "description": "The time in seconds to defend.",
                "no_slash": True,
            },
            "judgement_timeout": {
                "converter": commands.Range[int, 10, 300],
                "description": "The time in seconds to judge.",
                "no_slash": True,
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
            commands_group=self.setmafia,
        )

        self.games: typing.Dict[discord.Guild, Game] = {}
        self.last_games: typing.Dict[discord.Guild, Game] = {}

    async def cog_load(self) -> None:
        await super().cog_load()
        await self.settings.add_commands()
        self.loops.append(
            Loop(
                cog=self,
                name="Check Temp Bans",
                function=self.check_temp_bans,
                seconds=30,
            )
        )
        if is_dev(self.bot):
            self.bot.add_dev_env_value(
                name="mafia_game",
                value=lambda ctx: self.games.get(ctx.guild) or self.last_games.get(ctx.guild),
            )

    async def cog_unload(self) -> None:
        if is_dev(self.bot):
            self.bot.remove_dev_env_value("mafia_game")
        await super().cog_unload()

    async def check_temp_bans(self) -> None:
        member_group = self.config._get_base_group(self.config.MEMBER)
        async with member_group.all() as members_data:
            _members_data = deepcopy(members_data)
            for guild_id in _members_data:
                for member_id in _members_data[guild_id]:
                    if (
                        temp_banned_until := _members_data[guild_id][member_id].get(
                            "temp_banned_until"
                        )
                    ) is not None and datetime.datetime.now(
                        tz=datetime.timezone.utc
                    ) > datetime.datetime.fromtimestamp(
                        temp_banned_until, tz=datetime.timezone.utc
                    ):
                        del members_data[guild_id][member_id]["temp_banned_until"]

    @commands.Cog.listener()
    async def on_message_without_command(self, message: discord.Message) -> None:
        if message.author.bot:
            return
        if message.guild is None:  # Communication between Mafia side's players.
            if (
                (
                    games := [
                        game
                        for game in self.games.values()
                        if game.get_player(message.author) is not None
                    ]
                )
                and len(games) == 1
                and (game := games[0])
                and game.config["mafia_communication"]
                and (player := game.get_player(message.author))
                and not player.is_dead
                and player.role is not None
                and (
                    (player.role.side == "Mafia" and player.role.name != "Alchemist")
                    or player.is_town_traitor
                )
            ):
                for p in game.alive_players:
                    if p.role is not None and (
                        (p.role.side == "Mafia" and p.role.name != "Alchemist")
                        or p.is_town_traitor
                    ):  # and p != player
                        try:
                            await p.member.send(
                                f"📨 **{player.member.display_name} ({player.role.name}{_(' - Town Traitor') if player.is_town_traitor else ''})**: {message.content}"
                            )
                        except discord.HTTPException:
                            pass
        elif (  # AFK management.
            (game := self.games.get(message.guild)) is not None
            and message.channel == game.channel
            and (player := game.get_player(message.author)) is not None
        ):
            game.afk_players.pop(player, None)

    async def cog_check(self, ctx: commands.Context) -> bool:
        if (
            ctx.interaction is not None
            and ctx.interaction.is_user_integration()
            and ctx.command.name in ("start", "tempban", "unban", "afkkill")
        ):
            raise commands.UserFeedbackCheckFailure(
                _("This command doesn't work as user installable.")
            )
        return True

    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    @commands.hybrid_group(aliases=["mafiagame"])
    @app_commands.allowed_installs(guilds=True, users=True)
    async def mafia(self, ctx: commands.Context) -> None:
        """Play the Mafia game, with many roles (Mafia/Villagers/Neutral), modes (including Random and Custom), anomalies..."""
        pass

    @commands.admin_or_permissions(manage_guild=True)
    # commands.bot_has_permissions(manage_channels=True)
    @mafia.command()
    async def start(
        self, ctx: commands.Context, mode: typing.Optional[ModeConverter] = None
    ) -> None:
        """Start a game of Mafia!"""
        if self.games.get(ctx.guild) is not None:
            raise commands.UserFeedbackCheckFailure(_("A game is already running in this guild."))
        config = await self.config.guild(ctx.guild).all()
        category = (
            category
            if (
                (category_id := config["category"]) is not None
                and (category := ctx.guild.get_channel(category_id)) is not None
            )
            else ctx.channel.category
        )
        if not (
            category.permissions_for(ctx.guild.me)
            if category is not None
            else ctx.me.guild_permissions
        ).manage_channels:
            raise commands.UserFeedbackCheckFailure(
                _("I don't have the permission to create channels in the category.")
            )
        join_view: JoinGameView = JoinGameView(
            self,
            MODES=MODES,
            mode=(
                mode
                if mode is not None
                else discord.utils.get(MODES, name=config["default_mode"] or "Classic")
            ),
            config=config,
        )
        await join_view.start(ctx)
        await join_view.wait()
        if join_view.cancelled:
            return
        config = await self.config.guild(ctx.guild).all()
        for key in ("show_dead_role", "dying_message", "town_traitor", "town_vip", "anomalies"):
            config[key] = join_view.config[key]
        players = join_view.players
        game: Game = Game(self, mode=join_view.mode, config=config)
        asyncio.create_task(game.start(ctx, players=players))

    @mafia.command(aliases=["e"])
    async def explain(self, ctx: commands.Context, page: str = "main") -> None:
        """Explain how to play the Mafia game."""
        await ExplainView(
            ROLES=ROLES,
            MODES=MODES,
            ANOMALIES=ANOMALIES,
            page=page,
        ).start(ctx)

    @mafia.command()
    async def role(self, ctx: commands.Context, *, role: RoleConverter) -> None:
        """Show the informations about a specific role."""
        await Menu(pages=[role.get_kwargs()]).start(ctx)

    @mafia.command()
    async def roles(self, ctx: commands.Context) -> None:
        """Show the different roles of the Mafia game"""
        await Menu(
            pages=[role.get_kwargs() for role in ROLES],
        ).start(ctx)

    @mafia.command()
    async def mode(self, ctx: commands.Context, *, mode: ModeConverter) -> None:
        """Show the informations about a specific mode."""
        await Menu(pages=[mode.get_kwargs()]).start(ctx)

    @mafia.command()
    async def modes(self, ctx: commands.Context) -> None:
        """Show the different modes of the Mafia game."""
        await Menu(
            pages=[mode.get_kwargs() for mode in MODES],
        ).start(ctx)

    @mafia.command(aliases=["dmsg"])
    async def defaultdyingmessage(
        self,
        ctx: commands.Context,
        *,
        default_dying_message: commands.Range[str, 1, 200] = None,
    ) -> None:
        """Set your default custom dying message."""
        if default_dying_message is not None:
            await self.config.user(ctx.author).default_dying_message.set(default_dying_message)
        else:
            await self.config.user(ctx.author).default_dying_message.clear()

    @mafia.command()
    async def anomaly(self, ctx: commands.Context, *, anomaly: AnomalyConverter) -> None:
        """Show the information about a specific anomaly."""
        await Menu(pages=[anomaly.get_kwargs()]).start(ctx)

    @mafia.command()
    async def anomalies(self, ctx: commands.Context) -> None:
        """Show the different anomalies of the Mafia game."""
        await Menu(
            pages=[anomaly.get_kwargs() for anomaly in ANOMALIES],
        ).start(ctx)

    @anomaly.autocomplete("anomaly")
    async def mafia_anomaly_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> typing.List[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=anomaly.name, value=anomaly.name)
            for anomaly in ANOMALIES
            if anomaly.name.lower().startswith(current.lower())
        ][:25]

    @mafia.command()
    async def achievements(
        self,
        ctx: commands.Context,
        role: typing.Optional[RoleConverter] = None,
        *,
        user: typing.Optional[discord.User] = commands.Author,
    ) -> None:
        """Show your achievements or the achievements of a specific member."""
        if user.bot:
            raise commands.UserFeedbackCheckFailure(_("A bot can't play the Mafia game."))
        achievements = ACHIEVEMENTS if role is None else role.achievements
        user_data = await self.config.user(user).all()
        user_achievements = user_data["achievements"]
        embed: discord.Embed = discord.Embed(
            title=(
                _("General Achievements")
                if role is None
                else _("Achievements — {role.name}").format(role=role)
            ),
            color=ACHIEVEMENTS_COLOR,
        )
        embed.set_author(name=user.display_name, icon_url=user.display_avatar)
        for achievement, data in achievements.items():
            embed.add_field(
                name=(
                    f"✅ ~~{achievement}~~"
                    if achievement
                    in user_achievements.get(str(None) if role is None else role.name, [])
                    else f"🔒 {achievement}"
                    + (
                        f" ({(
                            len(user_data[data['check']].values())
                            if role is None else 
                            user_data[data['check']].get(role.name, 0)
                        )}/{data['value']})"
                        if data["check"] in ("games", "wins")
                        else ""
                    )
                ),
                value=_(data["description"]),
                inline=True,
            )
        completed = len(user_achievements.get(str(None) if role is None else role.name, []))
        if completed == len(achievements):
            embed.set_footer(text=_("✅ All achievements completed!"))
        else:
            embed.set_footer(
                text=_(
                    "Completed {completed} out of {total} achievements ({percentage}%)!"
                ).format(
                    completed=completed,
                    total=len(achievements),
                    percentage=f"{completed/len(achievements)*100:.2f}",
                ),
            )
        if role is None:
            if user.id == DEVELOPER:
                embed.add_field(
                    name=_("✨ Developer ✨"),
                    value=_("Has developed this Mafia game."),
                    inline=True,
                )
            if user.id in HELPERS:
                embed.add_field(
                    name=_("✨ Helper ✨"),
                    value=_("Has helped to create this Mafia game."),
                    inline=True,
                )
            if user.id in TESTERS:
                embed.add_field(
                    name=_("✨ Tester ✨"),
                    value=_("Has helped to test this Mafia game."),
                    inline=True,
                )
            if user.id in SUPPORTERS:
                embed.add_field(
                    name=_("✨ Supporter ✨"),
                    value=_("Has donated to support the developper."),
                    inline=True,
                )
        else:
            image = role.name.lower().replace(" ", "_")
            embed.set_thumbnail(url=f"attachment://{image}.png")
        await Menu(
            pages=[
                {
                    "embed": embed,
                    "file": get_image(os.path.join("roles", image)) if role is not None else None,
                }
            ],
        ).start(ctx)

    @achievements.autocomplete("role")
    @role.autocomplete("role")
    async def mafia_role_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> typing.List[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=role.name, value=role.name)
            for role in ROLES
            if role.name.lower().startswith(current.lower())
        ][:25]

    @commands.mod_or_permissions(manage_guild=True)
    @mafia.command()
    async def tempban(
        self,
        ctx: commands.Context,
        member: discord.Member,
        duration: DurationConverter,
    ) -> None:
        """Ban a member temporary from the Mafia game in this server."""
        if member.bot:
            raise commands.UserFeedbackCheckFailure(_("A bot can't play the Mafia game."))
        await self.config.member(member).temp_banned_until.set(
            int(
                (datetime.datetime.now(tz=datetime.timezone.utc) + duration)
                .replace(second=0, microsecond=0)
                .timestamp()
            )
        )
        await ctx.send(
            _(
                "This member has been **temporarily banned for {duration}** from the Mafia game in this server."
            ).format(duration=humanize_timedelta(timedelta=duration))
        )

    @commands.mod_or_permissions(manage_guild=True)
    @mafia.command()
    async def unban(self, ctx: commands.Context, *, member: discord.Member) -> None:
        """Unban a member from the Mafia game in this server."""
        if member.bot:
            raise commands.UserFeedbackCheckFailure(_("A bot can't play the Mafia game."))
        if await self.config.member(member).temp_banned_until() is None:
            raise commands.UserFeedbackCheckFailure(
                _("The member is not banned from the Mafia game in this server.")
            )
        await self.config.member(member).temp_banned_until.clear()
        await ctx.send(_("This member has been **unbanned** from the Mafia game in this server."))

    @commands.mod_or_permissions(manage_guild=True)
    @mafia.command()
    async def afkkill(self, ctx: commands.Context, *, member: discord.Member) -> None:
        """Kill a member for AFK from the Mafia game in this server."""
        if member.bot:
            raise commands.UserFeedbackCheckFailure(_("A bot can't play the Mafia game."))
        if (game := self.games.get(ctx.guild)) is None:
            raise commands.UserFeedbackCheckFailure(_("A game is not running in this guild."))
        if (player := game.get_player(member)) is None:
            raise commands.UserFeedbackCheckFailure(
                _("This member is not playing the Mafia game in this server.")
            )
        if player.is_dead:
            raise commands.UserFeedbackCheckFailure(
                _("This player is already dead in the Mafia game in this server.")
            )
        await player.kill(cause="afk")
        await ctx.send(_("This player has been **killed** from the Mafia game in this server."))

    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    @commands.hybrid_group(alias="setmafiagame")
    async def setmafia(self, ctx: commands.Context) -> None:
        """Settings for MafiaGame."""
        pass

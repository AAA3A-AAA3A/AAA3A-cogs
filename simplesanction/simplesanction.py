from .AAA3A_utils import CogsUtils  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
from redbot.core.bot import Red  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

if CogsUtils().is_dpy2:
    from .AAA3A_utils import Buttons, Dropdown  # isort:skip
else:
    from dislash import user_command, message_command, slash_command, Option, OptionType

import asyncio

from discord.ext.commands import BadArgument
from redbot.core import Config
from redbot.core.commands.converter import parse_timedelta, timedelta
from redbot.core.utils.menus import start_adding_reactions
from redbot.core.utils.predicates import MessagePredicate

from .settings import settings
from .utils import utils

# Credits:
# General repo credits.
# Thanks to Laggrons-dumb's WarnSystem cog (https://github.com/laggron42/Laggrons-Dumb-Cogs/tree/v3/warnsystem) for giving me some ideas and code for subcommands for a main command!
# Thanks to Yami for the technique in the init file of some cogs to load the interaction client only if it is not already loaded! Before this fix, when a user clicked a button, the actions would be run about 10 times, causing a huge spam and loop in the channel.
# Thanks to @Aikaterna on the Redbot support server for help on displaying the main command help menu and other commands!

_ = Translator("SimpleSanction", __file__)

if CogsUtils().is_dpy2:
    from functools import partial

    hybrid_command = partial(commands.hybrid_command, with_app_command=False)
    hybrid_group = partial(commands.hybrid_group, with_app_command=False)
else:
    hybrid_command = commands.command
    hybrid_group = commands.group


class TimeDeltaConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> timedelta:
        delta = parse_timedelta(argument)
        if delta is not None:
            return argument
        else:
            raise BadArgument()


@cog_i18n(_)
class SimpleSanction(settings, commands.Cog):
    """A cog to sanction a user!"""

    def __init__(self, bot: Red) -> None:
        self.bot: Red = bot

        self.config: Config = Config.get_conf(
            self,
            identifier=205192943327321000143939875896557571750,  # 793615829052
            force_registration=True,
        )
        self.sanction_guild: typing.Dict[str, typing.Union[str, bool, int]] = {
            "color": 0xF00020,
            "thumbnail": "https://i.imgur.com/Bl62rGd.png",
            "show_author": True,
            "action_confirmation": True,
            "finish_message": True,
            "warn_system_use": True,
            "way": "buttons",
            "reason_required": True,
            "delete_embed": True,
            "delete_message": True,
            "timeout": 180,
        }
        self.config.register_guild(**self.sanction_guild)

        self.buttons_dict: typing.List[typing.Dict[str, typing.Union[int, str, bool]]] = [
            {
                "style": 2,
                "label": "UserInfo",
                "emoji": "ℹ️",
                "custom_id": "SimpleSanction_userinfo_button",
                "disabled": False,
            },
            {
                "style": 2,
                "label": "Warn",
                "emoji": "⚠️",
                "custom_id": "SimpleSanction_warn_button",
                "disabled": False,
            },
            {
                "style": 2,
                "label": "Ban",
                "emoji": "🔨",
                "custom_id": "SimpleSanction_ban_button",
                "disabled": False,
            },
            {
                "style": 2,
                "label": "SoftBan",
                "emoji": "🔂",
                "custom_id": "SimpleSanction_softban_button",
                "disabled": False,
            },
            {
                "style": 2,
                "label": "TempBan",
                "emoji": "💨",
                "custom_id": "SimpleSanction_tempban_button",
                "disabled": False,
            },
            {
                "style": 2,
                "label": "Kick",
                "emoji": "👢",
                "custom_id": "SimpleSanction_kick_button",
                "disabled": False,
            },
            {
                "style": 2,
                "label": "Mute",
                "emoji": "🔇",
                "custom_id": "SimpleSanction_mute_button",
                "disabled": False,
            },
            {
                "style": 2,
                "label": "MuteChannel",
                "emoji": "👊",
                "custom_id": "SimpleSanction_mutechannel_button",
                "disabled": False,
            },
            {
                "style": 2,
                "label": "TempMute",
                "emoji": "⏳",
                "custom_id": "SimpleSanction_tempmute_button",
                "disabled": False,
            },
            {
                "style": 2,
                "label": "TempMuteChannel",
                "emoji": "⌛",
                "custom_id": "SimpleSanction_tempmutechannel_button",
                "disabled": False,
            },
            {
                "style": 2,
                "label": "Close",
                "emoji": "❌",
                "custom_id": "SimpleSanction_close_button",
                "disabled": False,
            },
        ]
        self.disabled_buttons_dict: typing.List[typing.Dict[str, typing.Union[int, str, bool]]] = [
            {
                "style": 2,
                "label": "UserInfo",
                "emoji": "ℹ️",
                "custom_id": "SimpleSanction_userinfo_button",
                "disabled": True,
            },
            {
                "style": 2,
                "label": "Warn",
                "emoji": "⚠️",
                "custom_id": "SimpleSanction_warn_button",
                "disabled": True,
            },
            {
                "style": 2,
                "label": "Ban",
                "emoji": "🔨",
                "custom_id": "SimpleSanction_ban_button",
                "disabled": True,
            },
            {
                "style": 2,
                "label": "SoftBan",
                "emoji": "🔂",
                "custom_id": "SimpleSanction_softban_button",
                "disabled": True,
            },
            {
                "style": 2,
                "label": "TempBan",
                "emoji": "💨",
                "custom_id": "SimpleSanction_tempban_button",
                "disabled": True,
            },
            {
                "style": 2,
                "label": "Kick",
                "emoji": "👢",
                "custom_id": "SimpleSanction_kick_button",
                "disabled": True,
            },
            {
                "style": 2,
                "label": "Mute",
                "emoji": "🔇",
                "custom_id": "SimpleSanction_mute_button",
                "disabled": True,
            },
            {
                "style": 2,
                "label": "MuteChannel",
                "emoji": "👊",
                "custom_id": "SimpleSanction_mutechannel_button",
                "disabled": True,
            },
            {
                "style": 2,
                "label": "TempMute",
                "emoji": "⏳",
                "custom_id": "SimpleSanction_tempmute_button",
                "disabled": True,
            },
            {
                "style": 2,
                "label": "TempMuteChannel",
                "emoji": "⌛",
                "custom_id": "SimpleSanction_tempmutechannel_button",
                "disabled": True,
            },
            {
                "style": 2,
                "label": "Close",
                "emoji": "❌",
                "custom_id": "SimpleSanction_close_button",
                "disabled": True,
            },
        ]
        self.options_dict: typing.List[typing.Dict[str, typing.Union[int, str]]] = [
            {"label": "UserInfo", "emoji": "ℹ️", "value": "SimpleSanction_userinfo_button"},
            {"label": "Warn", "emoji": "⚠️", "value": "SimpleSanction_warn_button"},
            {"label": "Ban", "emoji": "🔨", "value": "SimpleSanction_ban_button"},
            {"label": "SoftBan", "emoji": "🔂", "value": "SimpleSanction_softban_button"},
            {"label": "TempBan", "emoji": "💨", "value": "SimpleSanction_tempban_button"},
            {"label": "Kick", "emoji": "👢", "value": "SimpleSanction_kick_button"},
            {"label": "Mute", "emoji": "🔇", "value": "SimpleSanction_mute_button"},
            {"label": "MuteChannel", "emoji": "👊", "value": "SimpleSanction_mutechannel_button"},
            {"label": "TempMute", "emoji": "⏳", "value": "SimpleSanction_tempmute_button"},
            {
                "label": "TempMuteChannel",
                "emoji": "⌛",
                "value": "SimpleSanction_tempmutechannel_button",
            },
            {"label": "Close", "emoji": "❌", "value": "SimpleSanction_close_button"},
        ]

        self.cogsutils: CogsUtils = CogsUtils(cog=self)

    if not CogsUtils().is_dpy2:

        @user_command(name="Sanction user")
        async def sanctionusermenu(self, inter) -> None:
            try:
                await self.cogsutils.invoke_command(
                    author=inter.author, channel=inter.channel, command=f"sanction {inter.user.id}"
                )
                await inter.respond(
                    _(
                        "You have chosen to sanction {inter.user.mention} ({inter.user.id}) in {inter.channel.mention}."
                    ).format(inter=inter),
                    ephemeral=True,
                )
            except Exception:
                await inter.respond(
                    _(
                        "An error has occurred in your interaction. Please try to use the real command instead of this contextual menu."
                    ),
                    ephemeral=True,
                )

        @message_command(name="Sanction author")
        async def sanctionmessagemenu(self, inter) -> None:
            try:
                await self.cogsutils.invoke_command(
                    author=inter.author,
                    channel=inter.channel,
                    command=f"sanction {inter.message.author.id}",
                )
                await inter.respond(
                    _(
                        "You have chosen to sanction {inter.message.author.mention} ({inter.message.author.id}) in {inter.channel.mention}."
                    ).format(inter=inter),
                    ephemeral=True,
                )
            except Exception:
                await inter.respond(
                    _(
                        "An error has occurred in your interaction. Please try to use the real command instead of this contextual menu."
                    ),
                    ephemeral=True,
                )

        @slash_command(
            name="sanction",
            description="Sanction user",
            options=[
                Option("user", "Enter the user.", OptionType.USER, required=True),
                Option(
                    "confirmation",
                    "Ask for confirmation from you before the action?",
                    OptionType.BOOLEAN,
                    required=False,
                ),
                Option(
                    "show_author",
                    "Show in embeds who is the author of the command?",
                    OptionType.BOOLEAN,
                    required=False,
                ),
                Option(
                    "finish_message",
                    "Show an embed just before the action?",
                    OptionType.BOOLEAN,
                    required=False,
                ),
                Option(
                    "fake_action",
                    "Do everything as usual, but (unintentionally) forget to execute the action?",
                    OptionType.BOOLEAN,
                    required=False,
                ),
                Option(
                    "args",
                    "Enter the arguments of the command.",
                    OptionType.STRING,
                    required=False,
                ),
            ],
        )
        async def sanctionslash(
            self,
            inter,
            user,
            confirmation: typing.Optional[bool] = "",
            show_author: typing.Optional[bool] = "",
            finish_message: typing.Optional[bool] = "",
            fake_action: typing.Optional[bool] = "",
            args: typing.Optional[str] = "",
        ) -> None:
            try:
                if not confirmation == "":
                    confirmation = f" {confirmation}"
                if not show_author == "":
                    show_author = f" {show_author}"
                if not finish_message == "":
                    finish_message = f" {finish_message}"
                if not fake_action == "":
                    fake_action = f" {fake_action}"
                if not args == "":
                    args = f" {args}"
                await self.cogsutils.invoke_command(
                    author=inter.author,
                    channel=inter.channel,
                    command=f"sanction {user.id}{confirmation}{show_author}{finish_message}{fake_action}{args}",
                )
                await inter.respond(
                    _(
                        "You have chosen to sanction {user.mention} ({user.id}) in {inter.channel.mention}."
                    ).format(inter=inter),
                    ephemeral=True,
                )
            except Exception:
                await inter.respond(
                    _(
                        "An error has occurred in this interaction. Please try to use the real command instead of this contextual menu."
                    ),
                    ephemeral=True,
                )

    @commands.guild_only()
    @commands.mod_or_permissions(administrator=True)
    @commands.bot_has_permissions(add_reactions=True, embed_links=True)
    @hybrid_group(
        invoke_without_command=True,
        name="sanction",
        aliases=["punishuser"],
        usage="[user] [confirmation] [show_author] [finish_message] [fake_action] [duration_for_mute_or_ban] [reason_or_`not`]",
    )
    async def _sanction(
        self,
        ctx: commands.Context,
        user: typing.Optional[discord.Member] = None,
        confirmation: typing.Optional[bool] = None,
        show_author: typing.Optional[bool] = None,
        finish_message: typing.Optional[bool] = None,
        fake_action: typing.Optional[bool] = False,
        delete_embed: typing.Optional[bool] = None,
        delete_message: typing.Optional[bool] = None,
        duration: typing.Optional[TimeDeltaConverter] = None,
        *,
        reason: str = None,
    ) -> None:
        """
        Sanction a user quickly and easily.

        All arguments are optional and will be requested during the course of the action if necessary.
        For "Confirmation", "Show_author" and "finish_message", a `true` or `false` is expected.
        In this order, you must put the arguments and it is mandatory to specify the ones before if you want to specify one after.

        ``user``: Server member.			    Who is the user concerned?
        ``confirmation``: True or False.		Do you want the bot to ask for confirmation from you before the action? (Default is the recorded value)
        ``show_author``: True or False.			Do you want the bot to show in its embeds who is the author of the command/sanction? (Default is the recorded value)
        ``finish_message``: True or False.		Do you want the bot to show an embed just before the action summarising the action and giving the sanctioned user and the reason? (Default is the recorded value)
        ``fake_action``: True or False.		    Do you want the command to do everything as usual, but (unintentionally) forget to execute the action?
        ``duration``: Duration. (5d, 8h, 1m...)	If you choose a TempBan, TempMute or TempMuteChanne, this value will be used for the duration of that action.
        ``reason``: Text.				        The reason for this action. (`not` to not specify one, unless the reason has been made falcutative in the parameters)

        Short version: [p]sanction
        Long version:  [p]sanction 10 @user true true true true true true 3d Spam.
        """
        await self.call_sanction(
            ctx,
            0,
            user,
            confirmation,
            show_author,
            finish_message,
            fake_action,
            delete_embed,
            delete_message,
            duration,
            reason,
        )

    @commands.guild_only()
    @_sanction.command(
        name="00",
        aliases=["0", "sanction"],
        usage="[user] [confirmation] [show_author] [finish_message] [fake_action] [duration_for_mute_or_ban] [reason_or_`not`]",
    )
    async def sanction_0(
        self,
        ctx: commands.Context,
        user: typing.Optional[discord.Member] = None,
        confirmation: typing.Optional[bool] = None,
        show_author: typing.Optional[bool] = None,
        finish_message: typing.Optional[bool] = None,
        fake_action: typing.Optional[bool] = False,
        delete_embed: typing.Optional[bool] = None,
        delete_message: typing.Optional[bool] = None,
        duration: typing.Optional[TimeDeltaConverter] = None,
        *,
        reason: str = None,
    ) -> None:
        """
        - Sanction a user quickly and easily.

        Examples:
        - `[p]sanction 0 @user`
        - `[p]sanction 0 @user What are these roles?`
        - `[p]sanction 0 012345678987654321`
        """
        await self.call_sanction(
            ctx,
            0,
            user,
            confirmation,
            show_author,
            finish_message,
            fake_action,
            delete_embed,
            delete_message,
            duration,
            reason,
        )

    @commands.guild_only()
    @_sanction.command(
        name="01",
        aliases=["1", "userinfo", "info"],
        usage="[user] [confirmation] [show_author] [finish_message] [fake_action] [duration_for_mute_or_ban] [reason_or_`not`]",
    )
    async def sanction_1(
        self,
        ctx: commands.Context,
        user: typing.Optional[discord.Member] = None,
        confirmation: typing.Optional[bool] = None,
        show_author: typing.Optional[bool] = None,
        finish_message: typing.Optional[bool] = None,
        fake_action: typing.Optional[bool] = False,
        delete_embed: typing.Optional[bool] = None,
        delete_message: typing.Optional[bool] = None,
        duration: typing.Optional[TimeDeltaConverter] = None,
        *,
        reason: str = None,
    ) -> None:
        """
         - :information_source: Show info on a user.

        Examples:
        - `[p]sanction 1 @user`: UserInfo for no reason
        - `[p]sanction 1 @user What are these roles?`: UserInfo for the reason "What are these roles?"
        - `[p]sanction 1 012345678987654321`: UserInfo with the ID provided.
        """
        await self.call_sanction(
            ctx,
            1,
            user,
            confirmation,
            show_author,
            finish_message,
            fake_action,
            delete_embed,
            delete_message,
            duration,
            reason,
        )

    @commands.guild_only()
    @_sanction.command(
        name="02",
        aliases=["2", "warn"],
        usage="[user] [confirmation] [show_author] [finish_message] [fake_action] [duration_for_mute_or_ban] [reason_or_`not`]",
    )
    async def sanction_2(
        self,
        ctx: commands.Context,
        user: typing.Optional[discord.Member] = None,
        confirmation: typing.Optional[bool] = None,
        show_author: typing.Optional[bool] = None,
        finish_message: typing.Optional[bool] = None,
        fake_action: typing.Optional[bool] = False,
        delete_embed: typing.Optional[bool] = None,
        delete_message: typing.Optional[bool] = None,
        duration: typing.Optional[TimeDeltaConverter] = None,
        *,
        reason: str = None,
    ) -> None:
        """
         - ⚠️ Set a simple warning on a user.

        Examples:
        - `[p]sanction 2 @user not`: Warn for no reason
        - `[p]sanction 2 @user Insults`: Warn for the reason "Insults"
        - `[p]sanction 2 012345678987654321 Advertising`: Warn the user with the ID provided.
        """
        await self.call_sanction(
            ctx,
            2,
            user,
            confirmation,
            show_author,
            finish_message,
            fake_action,
            delete_embed,
            delete_message,
            duration,
            reason,
        )

    @commands.guild_only()
    @_sanction.command(
        name="03",
        aliases=["3", "ban"],
        usage="[user] [confirmation] [show_author] [finish_message] [fake_action] [duration_for_mute_or_ban] [reason_or_`not`]",
    )
    async def sanction_3(
        self,
        ctx: commands.Context,
        user: typing.Optional[discord.Member] = None,
        confirmation: typing.Optional[bool] = None,
        show_author: typing.Optional[bool] = None,
        finish_message: typing.Optional[bool] = None,
        fake_action: typing.Optional[bool] = False,
        delete_embed: typing.Optional[bool] = None,
        delete_message: typing.Optional[bool] = None,
        duration: typing.Optional[TimeDeltaConverter] = None,
        *,
        reason: str = None,
    ) -> None:
        """
         - :hammer: Ban the member from the server.

        It won't delete messages by default.

        Examples:
        - `[p]sanction 3 @user not`: Ban for no reason
        - `[p]sanction 3 @user Insults`: Ban for the reason "Insults"
        - `[p]sanction 3 012345678987654321 Advertising`: Ban the user with the ID provided.
        """
        await self.call_sanction(
            ctx,
            3,
            user,
            confirmation,
            show_author,
            finish_message,
            fake_action,
            delete_embed,
            delete_message,
            duration,
            reason,
        )

    @commands.guild_only()
    @_sanction.command(
        name="04",
        aliases=["4", "softban"],
        usage="[user] [confirmation] [show_author] [finish_message] [fake_action] [duration_for_mute_or_ban] [reason_or_`not`]",
    )
    async def sanction_4(
        self,
        ctx: commands.Context,
        user: typing.Optional[discord.Member] = None,
        confirmation: typing.Optional[bool] = None,
        show_author: typing.Optional[bool] = None,
        finish_message: typing.Optional[bool] = None,
        fake_action: typing.Optional[bool] = False,
        delete_embed: typing.Optional[bool] = None,
        delete_message: typing.Optional[bool] = None,
        duration: typing.Optional[TimeDeltaConverter] = None,
        *,
        reason: str = None,
    ) -> None:
        """
         - :repeat_one: Softban the member from the server.

        This means that the user will be banned and immediately unbanned, so it will purge their messages in all channels.

        Examples:
        - `[p]sanction 4 @user not`: SoftBan for no reason
        - `[p]sanction 4 @user Insults`: SoftBan for the reason "Insults"
        - `[p]sanction 4 012345678987654321 Advertising`: SoftBan the user with the ID provided.
        """
        await self.call_sanction(
            ctx,
            4,
            user,
            confirmation,
            show_author,
            finish_message,
            fake_action,
            delete_embed,
            delete_message,
            duration,
            reason,
        )

    @commands.guild_only()
    @_sanction.command(
        name="05",
        aliases=["5", "tempban"],
        usage="[user] [confirmation] [show_author] [finish_message] [fake_action] [duration_for_mute_or_ban] [reason_or_`not`]",
    )
    async def sanction_5(
        self,
        ctx: commands.Context,
        user: typing.Optional[discord.Member] = None,
        confirmation: typing.Optional[bool] = None,
        show_author: typing.Optional[bool] = None,
        finish_message: typing.Optional[bool] = None,
        fake_action: typing.Optional[bool] = False,
        delete_embed: typing.Optional[bool] = None,
        delete_message: typing.Optional[bool] = None,
        duration: typing.Optional[TimeDeltaConverter] = None,
        *,
        reason: str = None,
    ) -> None:
        """
         - :dash: Tempban the member from the server.

        It won't delete messages by default.

        If you want to perform a temporary ban, provide the time before the reason.

        Examples:
        - `[p]sanction 5 @user not`: Ban for no reason
        - `[p]sanction 5 @user 7d Insults`: 7 days ban for the reason "Insults"
        - `[p]sanction 5 012345678987654321 Advertising`: Ban the user with the ID provided.
        """
        await self.call_sanction(
            ctx,
            5,
            user,
            confirmation,
            show_author,
            finish_message,
            fake_action,
            delete_embed,
            delete_message,
            duration,
            reason,
        )

    @commands.guild_only()
    @_sanction.command(
        name="06",
        aliases=["6", "kick"],
        usage="[user] [confirmation] [show_author] [finish_message] [fake_action] [duration_for_mute_or_ban] [reason_or_`not`]",
    )
    async def sanction_6(
        self,
        ctx: commands.Context,
        user: typing.Optional[discord.Member] = None,
        confirmation: typing.Optional[bool] = None,
        show_author: typing.Optional[bool] = None,
        finish_message: typing.Optional[bool] = None,
        fake_action: typing.Optional[bool] = False,
        delete_embed: typing.Optional[bool] = None,
        delete_message: typing.Optional[bool] = None,
        duration: typing.Optional[TimeDeltaConverter] = None,
        *,
        reason: str = None,
    ) -> None:
        """
         - :boot: Kick the member from the server.

        Examples:
        - `[p]sanction 6 @user not`: Kick for no reason
        - `[p]sanction 6 @user Insults`: Kick for the reason "Insults"
        - `[p]sanction 6 012345678987654321 Advertising`: Kick the user with the ID provided.
        """
        await self.call_sanction(
            ctx,
            6,
            user,
            confirmation,
            show_author,
            finish_message,
            fake_action,
            delete_embed,
            delete_message,
            duration,
            reason,
        )

    @commands.guild_only()
    @_sanction.command(
        name="07",
        aliases=["7", "mute"],
        usage="[user] [confirmation] [show_author] [finish_message] [fake_action] [duration_for_mute_or_ban] [reason_or_`not`]",
    )
    async def sanction_7(
        self,
        ctx: commands.Context,
        user: typing.Optional[discord.Member] = None,
        confirmation: typing.Optional[bool] = None,
        show_author: typing.Optional[bool] = None,
        finish_message: typing.Optional[bool] = None,
        fake_action: typing.Optional[bool] = False,
        delete_embed: typing.Optional[bool] = None,
        delete_message: typing.Optional[bool] = None,
        duration: typing.Optional[TimeDeltaConverter] = None,
        *,
        reason: str = None,
    ) -> None:
        """
         - :mute: Mute the user in all channels, including voice channels.

        Examples:
        - `[p]sanction 7 @user not`: Infinite mute for no reason
        - `[p]sanction 7 @user Spam`:Infinite  mute for the reason "Spam"
        - `[p]sanction 7 @user Advertising`: Infinite mute for the reason "Advertising"
        """
        await self.call_sanction(
            ctx,
            7,
            user,
            confirmation,
            show_author,
            finish_message,
            fake_action,
            delete_embed,
            delete_message,
            duration,
            reason,
        )

    @commands.guild_only()
    @_sanction.command(
        name="08",
        aliases=["8", "mutechannel"],
        usage="[user] [confirmation] [show_author] [finish_message] [fake_action] [duration_for_mute_or_ban] [reason_or_`not`]",
    )
    async def sanction_8(
        self,
        ctx: commands.Context,
        user: typing.Optional[discord.Member] = None,
        confirmation: typing.Optional[bool] = None,
        show_author: typing.Optional[bool] = None,
        finish_message: typing.Optional[bool] = None,
        fake_action: typing.Optional[bool] = False,
        delete_embed: typing.Optional[bool] = None,
        delete_message: typing.Optional[bool] = None,
        duration: typing.Optional[TimeDeltaConverter] = None,
        *,
        reason: str = None,
    ) -> None:
        """
         - :punch: Mute the user in this channel.

        Examples:
        - `[p]sanction 8 @user not`: Infinite mute for no reason
        - `[p]sanction 8 @user Spam`: Infinite mute for the reason "Spam"
        - `[p]sanction 8 @user Advertising`: Infinite mute for the reason "Advertising"
        """
        await self.call_sanction(
            ctx,
            8,
            user,
            confirmation,
            show_author,
            finish_message,
            fake_action,
            delete_embed,
            delete_message,
            duration,
            reason,
        )

    @commands.guild_only()
    @_sanction.command(
        name="09",
        aliases=["9", "tempmute"],
        usage="[user] [confirmation] [show_author] [finish_message] [fake_action] [duration_for_mute_or_ban] [reason_or_`not`]",
    )
    async def sanction_9(
        self,
        ctx: commands.Context,
        user: typing.Optional[discord.Member] = None,
        confirmation: typing.Optional[bool] = None,
        show_author: typing.Optional[bool] = None,
        finish_message: typing.Optional[bool] = None,
        fake_action: typing.Optional[bool] = False,
        delete_embed: typing.Optional[bool] = None,
        delete_message: typing.Optional[bool] = None,
        duration: typing.Optional[TimeDeltaConverter] = None,
        *,
        reason: str = None,
    ) -> None:
        """
         - :hourglass_flowing_sand: TempMute the user in all channels, including voice channels.

        You can set a timed mute by providing a valid time before the reason.

        Examples:
        - `[p]sanction 9 @user 30m not`: 30 minutes mute for no reason
        - `[p]sanction 9 @user 5h Spam`: 5 hours mute for the reason "Spam"
        - `[p]sanction 9 @user 3d Advertising`: 3 days mute for the reason "Advertising"
        """
        await self.call_sanction(
            ctx,
            9,
            user,
            confirmation,
            show_author,
            finish_message,
            fake_action,
            delete_embed,
            delete_message,
            duration,
            reason,
        )

    @commands.guild_only()
    @_sanction.command(
        name="10",
        aliases=["tempmutechannel"],
        usage="[user] [confirmation] [show_author] [finish_message] [fake_action] [duration_for_mute_or_ban] [reason_or_`not`]",
    )
    async def sanction_10(
        self,
        ctx: commands.Context,
        user: typing.Optional[discord.Member] = None,
        confirmation: typing.Optional[bool] = None,
        show_author: typing.Optional[bool] = None,
        finish_message: typing.Optional[bool] = None,
        fake_action: typing.Optional[bool] = False,
        delete_embed: typing.Optional[bool] = None,
        delete_message: typing.Optional[bool] = None,
        duration: typing.Optional[TimeDeltaConverter] = None,
        *,
        reason: str = None,
    ) -> None:
        """
         - :hourglass: TempMute the user in this channel.

        You can set a timed mute by providing a valid time before the reason.

        Examples:
        - `[p]sanction 10 @user 30m not`: 30 minutes mute for no reason
        - `[p]sanction 10 @user 5h Spam`: 5 hours mute for the reason "Spam"
        - `[p]sanction 10 @user 3d Advertising`: 3 days mute for the reason "Advertising"
        """
        await self.call_sanction(
            ctx,
            10,
            user,
            confirmation,
            show_author,
            finish_message,
            fake_action,
            delete_embed,
            delete_message,
            duration,
            reason,
        )

    @commands.guild_only()
    async def call_sanction(
        self,
        ctx: commands.Context,
        action: typing.Optional[int] = None,
        user: typing.Optional[discord.Member] = None,
        confirmation: typing.Optional[bool] = None,
        show_author: typing.Optional[bool] = None,
        finish_message: typing.Optional[bool] = None,
        fake_action: typing.Optional[bool] = False,
        delete_embed: typing.Optional[bool] = None,
        delete_message: typing.Optional[bool] = None,
        duration: typing.Optional[TimeDeltaConverter] = None,
        reason: str = None,
    ) -> None:
        """Sanction a user quickly and easily."""
        config = await self.config.guild(ctx.guild).all()
        actual_thumbnail = config["thumbnail"]
        actual_color = config["color"]
        actual_show_author = config["show_author"]
        actual_action_confirmation = config["action_confirmation"]
        actual_finish_message = config["finish_message"]
        actual_way = config["way"]
        if actual_way == "dropdown" and not self.cogsutils.is_dpy2:
            actual_way = "buttons"
        actual_delete_embed = config["delete_embed"]
        actual_delete_message = config["delete_message"]
        actual_timeout = config["timeout"]
        if action == 0:
            action = None
        if confirmation is None:
            confirmation = actual_action_confirmation
        if show_author is None:
            show_author = actual_show_author
        if finish_message is None:
            finish_message = actual_finish_message
        if delete_embed is None:
            delete_embed = actual_delete_embed
        if delete_message is None:
            delete_message = actual_delete_message
        if reason is not None:
            if reason.lower() == "not":
                reason = "not"
        if delete_message and ctx.author == ctx.message.author:
            try:
                await self.cogsutils.delete_message(ctx.message)
            except discord.HTTPException:
                pass
        if user is None:
            embed: discord.Embed = discord.Embed()
            embed.title = _("Sanctioning a member")
            embed.description = _(
                "Which member do you want to sanction? (Set `cancel` to cancel.)"
            )
            embed.color = actual_color
            message = await ctx.send(embed=embed)
            try:
                pred = MessagePredicate.valid_member(ctx)
                msg = await self.bot.wait_for(
                    "message",
                    timeout=actual_timeout,
                    check=pred,
                )
                if msg.content.lower() == "cancel":
                    await self.cogsutils.delete_message(message)
                    await self.cogsutils.delete_message(msg)
                    return
                await self.cogsutils.delete_message(ctx.message)
                await self.cogsutils.delete_message(msg)
                user = pred.result
            except asyncio.TimeoutError:
                raise commands.UserFeedbackCheckFailure(_("Timed out, please try again."))

        if action is None:
            embed: discord.Embed = discord.Embed()
            embed.title = _("Sanctioning a member")
            embed.description = _(
                "This tool allows you to easily sanction a server member.\nUser mention: {user.mention} - User ID: {user.id}"
            ).format(user=user)
            embed.set_thumbnail(url=actual_thumbnail)
            embed.color = actual_color
            embed.set_author(
                name=user,
                url=user.display_avatar if self.cogsutils.is_dpy2 else user.avatar_url,
                icon_url=user.display_avatar if self.cogsutils.is_dpy2 else user.avatar_url,
            )
            if show_author:
                embed.set_footer(
                    text=ctx.author,
                    icon_url=ctx.author.display_avatar
                    if self.cogsutils.is_dpy2
                    else ctx.author.avatar_url,
                )
            embed.add_field(
                inline=False,
                name="Possible actions:",
                value=f"ℹ️ UserInfo - ⚠️ Warn - 🔨 Ban - 🔂 SoftBan - 💨 TempBan\n👢 Kick - 🔇 Mute - 👊 MuteChannel - ⏳ TempMute\n⌛ TempMuteChannel - ❌ Cancel",
            )
            if reason == "not":
                embed.add_field(
                    inline=False,
                    name=_("Reason:"),
                    value=_("The reason was not given and will not be asked later."),
                )
            else:
                if reason is not None:
                    embed.add_field(inline=False, name=_("Reason:"), value=f"{reason}")
            if duration is not None:
                embed.add_field(
                    inline=False, name=_("Duration:"), value=f"{parse_timedelta(duration)}"
                )
            if self.cogsutils.is_dpy2:

                async def send_fake_epheremal(
                    view: discord.ui.View, interaction: discord.Interaction, fake_action: bool
                ):
                    if fake_action:
                        await interaction.response.send_message(
                            _(
                                "You are using this command in Fake mode, so no action will be taken, but I will pretend it is not the case."
                            ),
                            ephemeral=True,
                        )

            if actual_way == "buttons":
                if self.cogsutils.is_dpy2:
                    view = Buttons(
                        timeout=actual_timeout,
                        buttons=self.buttons_dict,
                        members=[ctx.author] + list(ctx.bot.owner_ids),
                        function=send_fake_epheremal,
                        function_kwargs={"fake_action": fake_action},
                    )
                    message = await ctx.send(embed=embed, view=view)
                else:
                    buttons, buttons_one, buttons_two, buttons_three = await utils.emojis(
                        disabled=False
                    )
                    message = await ctx.send(
                        embed=embed, components=[buttons_one, buttons_two, buttons_three]
                    )
            elif actual_way == "dropdown":
                view = Dropdown(
                    timeout=actual_timeout,
                    options=self.options_dict,
                    members=[ctx.author] + list(ctx.bot.owner_ids),
                    function=send_fake_epheremal,
                    function_kwargs={"fake_action": fake_action},
                )
                message = await ctx.send(embed=embed, view=view)
            elif actual_way == "reactions":
                message = await ctx.send(embed=embed)
                reactions = ["ℹ️", "⚠️", "🔨", "🔂", "💨", "👢", "🔇", "👊", "⏳", "⌛", "❌"]
                start_adding_reactions(message, reactions)
            # "\N{information_source}", "\N{warning}", "\N{hammer}", "\N{repeat_one}", "\N{dash}", "\N{boot}", "\N{mute}", "\N{hourglass_flowing_sand}", "\N{punch}", "\N{x}"
            end_reaction = False

        if action is not None:
            await self.call_actions(
                ctx,
                action,
                user,
                confirmation,
                show_author,
                finish_message,
                fake_action,
                delete_embed,
                delete_message,
                duration,
                reason,
            )

        if action is None and actual_way == "buttons" and self.cogsutils.is_dpy2:
            try:
                interaction, function_result = await view.wait_result()
                if interaction.data["custom_id"] == "SimpleSanction_userinfo_button":
                    action = 1
                    await self.cogsutils.delete_message(message)
                    await self.call_actions(
                        ctx,
                        action,
                        user,
                        confirmation,
                        show_author,
                        finish_message,
                        fake_action,
                        delete_embed,
                        delete_message,
                        duration,
                        reason,
                    )
                    return
                if interaction.data["custom_id"] == "SimpleSanction_warn_button":
                    action = 2
                    await self.cogsutils.delete_message(message)
                    await self.call_actions(
                        ctx,
                        action,
                        user,
                        confirmation,
                        show_author,
                        finish_message,
                        fake_action,
                        delete_embed,
                        delete_message,
                        duration,
                        reason,
                    )
                    return
                if interaction.data["custom_id"] == "SimpleSanction_ban_button":
                    action = 3
                    await self.cogsutils.delete_message(message)
                    await self.call_actions(
                        ctx,
                        action,
                        user,
                        confirmation,
                        show_author,
                        finish_message,
                        fake_action,
                        delete_embed,
                        delete_message,
                        duration,
                        reason,
                    )
                    return
                if interaction.data["custom_id"] == "SimpleSanction_softban_button":
                    action = 4
                    await self.cogsutils.delete_message(message)
                    await self.call_actions(
                        ctx,
                        action,
                        user,
                        confirmation,
                        show_author,
                        finish_message,
                        fake_action,
                        delete_embed,
                        delete_message,
                        duration,
                        reason,
                    )
                    return
                if interaction.data["custom_id"] == "SimpleSanction_tempban_button":
                    action = 5
                    await self.cogsutils.delete_message(message)
                    await self.call_actions(
                        ctx,
                        action,
                        user,
                        confirmation,
                        show_author,
                        finish_message,
                        fake_action,
                        delete_embed,
                        delete_message,
                        duration,
                        reason,
                    )
                    return
                if interaction.data["custom_id"] == "SimpleSanction_kick_button":
                    action = 6
                    await self.cogsutils.delete_message(message)
                    await self.call_actions(
                        ctx,
                        action,
                        user,
                        confirmation,
                        show_author,
                        finish_message,
                        fake_action,
                        delete_embed,
                        delete_message,
                        duration,
                        reason,
                    )
                    return
                if interaction.data["custom_id"] == "SimpleSanction_mute_button":
                    action = 7
                    await self.cogsutils.delete_message(message)
                    await self.call_actions(
                        ctx,
                        action,
                        user,
                        confirmation,
                        show_author,
                        finish_message,
                        fake_action,
                        delete_embed,
                        delete_message,
                        duration,
                        reason,
                    )
                    return
                if interaction.data["custom_id"] == "SimpleSanction_mutechannel_button":
                    action = 8
                    await self.cogsutils.delete_message(message)
                    await self.call_actions(
                        ctx,
                        action,
                        user,
                        confirmation,
                        show_author,
                        finish_message,
                        fake_action,
                        delete_embed,
                        delete_message,
                        duration,
                        reason,
                    )
                    return
                if interaction.data["custom_id"] == "SimpleSanction_tempmute_button":
                    action = 9
                    await self.cogsutils.delete_message(message)
                    await self.call_actions(
                        ctx,
                        action,
                        user,
                        confirmation,
                        show_author,
                        finish_message,
                        fake_action,
                        delete_embed,
                        delete_message,
                        duration,
                        reason,
                    )
                    return
                if interaction.data["custom_id"] == "SimpleSanction_tempmutechannel_button":
                    action = 10
                    await self.cogsutils.delete_message(message)
                    await self.call_actions(
                        ctx,
                        action,
                        user,
                        confirmation,
                        show_author,
                        finish_message,
                        fake_action,
                        delete_embed,
                        delete_message,
                        duration,
                        reason,
                    )
                    return
                if interaction.data["custom_id"] == "SimpleSanction_close_button":
                    action = 11
                    await self.cogsutils.delete_message(message)
                    await self.call_actions(
                        ctx,
                        action,
                        user,
                        confirmation,
                        show_author,
                        finish_message,
                        fake_action,
                        delete_embed,
                        delete_message,
                        duration,
                        reason,
                    )
                    return
            except TimeoutError:
                if delete_embed:
                    await self.cogsutils.delete_message(message)
                else:
                    view = Buttons(
                        timeout=actual_timeout, buttons=self.disabled_buttons_dict, members=[]
                    )
                    await message.edit(embed=embed, view=view)
                return

        if action is None and actual_way == "dropdown" and self.cogsutils.is_dpy2:
            try:
                interaction, values, function_result = await view.wait_result()
                if str(values[0]) == "SimpleSanction_userinfo_button":
                    action = 1
                    await self.cogsutils.delete_message(message)
                    await self.call_actions(
                        ctx,
                        action,
                        user,
                        confirmation,
                        show_author,
                        finish_message,
                        fake_action,
                        delete_embed,
                        delete_message,
                        duration,
                        reason,
                    )
                    return
                if str(values[0]) == "SimpleSanction_warn_button":
                    action = 2
                    await self.cogsutils.delete_message(message)
                    await self.call_actions(
                        ctx,
                        action,
                        user,
                        confirmation,
                        show_author,
                        finish_message,
                        fake_action,
                        delete_embed,
                        delete_message,
                        duration,
                        reason,
                    )
                    return
                if str(values[0]) == "SimpleSanction_ban_button":
                    action = 3
                    await self.cogsutils.delete_message(message)
                    await self.call_actions(
                        ctx,
                        action,
                        user,
                        confirmation,
                        show_author,
                        finish_message,
                        fake_action,
                        delete_embed,
                        delete_message,
                        duration,
                        reason,
                    )
                    return
                if str(values[0]) == "SimpleSanction_softban_button":
                    action = 4
                    await self.cogsutils.delete_message(message)
                    await self.call_actions(
                        ctx,
                        action,
                        user,
                        confirmation,
                        show_author,
                        finish_message,
                        fake_action,
                        delete_embed,
                        delete_message,
                        duration,
                        reason,
                    )
                    return
                if str(values[0]) == "SimpleSanction_tempban_button":
                    action = 5
                    await self.cogsutils.delete_message(message)
                    await self.call_actions(
                        ctx,
                        action,
                        user,
                        confirmation,
                        show_author,
                        finish_message,
                        fake_action,
                        delete_embed,
                        delete_message,
                        duration,
                        reason,
                    )
                    return
                if str(values[0]) == "SimpleSanction_kick_button":
                    action = 6
                    await self.cogsutils.delete_message(message)
                    await self.call_actions(
                        ctx,
                        action,
                        user,
                        confirmation,
                        show_author,
                        finish_message,
                        fake_action,
                        delete_embed,
                        delete_message,
                        duration,
                        reason,
                    )
                    return
                if str(values[0]) == "SimpleSanction_mute_button":
                    action = 7
                    await self.cogsutils.delete_message(message)
                    await self.call_actions(
                        ctx,
                        action,
                        user,
                        confirmation,
                        show_author,
                        finish_message,
                        fake_action,
                        delete_embed,
                        delete_message,
                        duration,
                        reason,
                    )
                    return
                if str(values[0]) == "SimpleSanction_mutechannel_button":
                    action = 8
                    await self.cogsutils.delete_message(message)
                    await self.call_actions(
                        ctx,
                        action,
                        user,
                        confirmation,
                        show_author,
                        finish_message,
                        fake_action,
                        delete_embed,
                        delete_message,
                        duration,
                        reason,
                    )
                    return
                if str(values[0]) == "SimpleSanction_tempmute_button":
                    action = 9
                    await self.cogsutils.delete_message(message)
                    await self.call_actions(
                        ctx,
                        action,
                        user,
                        confirmation,
                        show_author,
                        finish_message,
                        fake_action,
                        delete_embed,
                        delete_message,
                        duration,
                        reason,
                    )
                    return
                if str(values[0]) == "SimpleSanction_tempmutechannel_button":
                    action = 10
                    await self.cogsutils.delete_message(message)
                    await self.call_actions(
                        ctx,
                        action,
                        user,
                        confirmation,
                        show_author,
                        finish_message,
                        fake_action,
                        delete_embed,
                        delete_message,
                        duration,
                        reason,
                    )
                    return
                if str(values[0]) == "SimpleSanction_close_button":
                    action = 11
                    await self.cogsutils.delete_message(message)
                    await self.call_actions(
                        ctx,
                        action,
                        user,
                        confirmation,
                        show_author,
                        finish_message,
                        fake_action,
                        delete_embed,
                        delete_message,
                        duration,
                        reason,
                    )
                    return
            except TimeoutError:
                if delete_embed:
                    await self.cogsutils.delete_message(message)
                else:
                    await message.edit(embed=embed, view=None)
                return

        if action is None and actual_way == "reactions":

            def check(reaction, abc_author):
                return (
                    abc_author == ctx.author
                    or abc_author.id in ctx.bot.owner_ids
                    and str(reaction.emoji) in reactions
                )
                # This makes sure nobody except the command sender can interact with the "menu"

            while True:
                try:
                    reaction, abc_author = await ctx.bot.wait_for(
                        "reaction_add", timeout=actual_timeout, check=check
                    )
                    # waiting for a reaction to be added - times out after x seconds, 30 in this
                    if str(reaction.emoji) == "ℹ️":
                        end_reaction = True
                        action = 1
                        await self.cogsutils.delete_message(message)
                        await self.call_actions(
                            ctx,
                            action,
                            user,
                            confirmation,
                            show_author,
                            finish_message,
                            fake_action,
                            delete_embed,
                            delete_message,
                            duration,
                            reason,
                        )
                        break
                    elif str(reaction.emoji) == "⚠️":
                        end_reaction = True
                        action = 2
                        await self.cogsutils.delete_message(message)
                        await self.call_actions(
                            ctx,
                            action,
                            user,
                            confirmation,
                            show_author,
                            finish_message,
                            fake_action,
                            delete_embed,
                            delete_message,
                            duration,
                            reason,
                        )
                        break
                    elif str(reaction.emoji) == "🔨":
                        end_reaction = True
                        action = 3
                        await self.cogsutils.delete_message(message)
                        await self.call_actions(
                            ctx,
                            action,
                            user,
                            confirmation,
                            show_author,
                            finish_message,
                            fake_action,
                            delete_embed,
                            delete_message,
                            duration,
                            reason,
                        )
                        break
                    elif str(reaction.emoji) == "🔂":
                        end_reaction = True
                        action = 4
                        await self.cogsutils.delete_message(message)
                        await self.call_actions(
                            ctx,
                            action,
                            user,
                            confirmation,
                            show_author,
                            finish_message,
                            fake_action,
                            delete_embed,
                            delete_message,
                            duration,
                            reason,
                        )
                        break
                    elif str(reaction.emoji) == "💨":
                        end_reaction = True
                        action = 5
                        await self.cogsutils.delete_message(message)
                        await self.call_actions(
                            ctx,
                            action,
                            user,
                            confirmation,
                            show_author,
                            finish_message,
                            fake_action,
                            delete_embed,
                            delete_message,
                            duration,
                            reason,
                        )
                        break
                    elif str(reaction.emoji) == "👢":
                        end_reaction = True
                        action = 6
                        await self.cogsutils.delete_message(message)
                        await self.call_actions(
                            ctx,
                            action,
                            user,
                            confirmation,
                            show_author,
                            finish_message,
                            fake_action,
                            delete_embed,
                            delete_message,
                            duration,
                            reason,
                        )
                        break
                    elif str(reaction.emoji) == "🔇":
                        end_reaction = True
                        action = 7
                        await self.cogsutils.delete_message(message)
                        await self.call_actions(
                            ctx,
                            action,
                            user,
                            confirmation,
                            show_author,
                            finish_message,
                            fake_action,
                            delete_embed,
                            delete_message,
                            duration,
                            reason,
                        )
                        break
                    elif str(reaction.emoji) == "👊":
                        end_reaction = True
                        action = 8
                        await self.cogsutils.delete_message(message)
                        await self.call_actions(
                            ctx,
                            action,
                            user,
                            confirmation,
                            show_author,
                            finish_message,
                            fake_action,
                            delete_embed,
                            delete_message,
                            duration,
                            reason,
                        )
                        break
                    elif str(reaction.emoji) == "⏳":
                        end_reaction = True
                        action = 9
                        await self.cogsutils.delete_message(message)
                        await self.call_actions(
                            ctx,
                            action,
                            user,
                            confirmation,
                            show_author,
                            finish_message,
                            fake_action,
                            delete_embed,
                            delete_message,
                            duration,
                            reason,
                        )
                        break
                    elif str(reaction.emoji) == "⌛":
                        end_reaction = True
                        action = 10
                        await self.cogsutils.delete_message(message)
                        await self.call_actions(
                            ctx,
                            action,
                            user,
                            confirmation,
                            show_author,
                            finish_message,
                            fake_action,
                            delete_embed,
                            delete_message,
                            duration,
                            reason,
                        )
                        break
                    elif str(reaction.emoji) == "❌":
                        end_reaction = True
                        action = 11
                        await self.cogsutils.delete_message(message)
                        await self.call_actions(
                            ctx,
                            action,
                            user,
                            confirmation,
                            show_author,
                            finish_message,
                            fake_action,
                            delete_embed,
                            delete_message,
                            duration,
                            reason,
                        )
                        break
                    else:
                        await message.remove_reaction(reaction, user)
                except asyncio.TimeoutError:
                    if not end_reaction:
                        if delete_embed:
                            await self.cogsutils.delete_message(message)
                        await ctx.send("Timed out, please try again.")
                        return

        if action is None and actual_way == "buttons" and not self.cogsutils.is_dpy2:
            on_click = message.create_click_listener(timeout=actual_timeout)

            @on_click.not_from_user(ctx.author, cancel_others=True, reset_timeout=False)
            async def on_wrong_user(inter):
                # This function is called in case a button was clicked not by the author
                # cancel_others=True prevents all on_click-functions under this function from working
                # regardless of their checks
                # reset_timeout=False makes the timer keep going after this function is called
                await inter.respond(_("You are not the author of this command."), ephemeral=True)

            @on_click.matching_id("userinfo_button")
            async def on_userinfo_button(inter):
                if fake_action:
                    await inter.respond(
                        _(
                            "You are using this command in Fake mode, so no action will be taken, but I will pretend it is not the case."
                        ),
                        ephemeral=True,
                    )
                action = 1
                await self.cogsutils.delete_message(message)
                await self.call_actions(
                    ctx,
                    action,
                    user,
                    confirmation,
                    show_author,
                    finish_message,
                    fake_action,
                    delete_embed,
                    delete_message,
                    duration,
                    reason,
                )
                return

            @on_click.matching_id("warn_button")
            async def on_warn_button(inter):
                if fake_action:
                    await inter.respond(
                        _(
                            "You are using this command in Fake mode, so no action will be taken, but I will pretend it is not the case."
                        ),
                        ephemeral=True,
                    )
                action = 2
                await self.cogsutils.delete_message(message)
                await self.call_actions(
                    ctx,
                    action,
                    user,
                    confirmation,
                    show_author,
                    finish_message,
                    fake_action,
                    delete_embed,
                    delete_message,
                    duration,
                    reason,
                )
                return

            @on_click.matching_id("ban_button")
            async def on_ban_button(inter):
                if fake_action:
                    await inter.respond(
                        _(
                            "You are using this command in Fake mode, so no action will be taken, but I will pretend it is not the case."
                        ),
                        ephemeral=True,
                    )
                action = 3
                await self.cogsutils.delete_message(message)
                await self.call_actions(
                    ctx,
                    action,
                    user,
                    confirmation,
                    show_author,
                    finish_message,
                    fake_action,
                    delete_embed,
                    delete_message,
                    duration,
                    reason,
                )
                return

            @on_click.matching_id("softban_button")
            async def on_softban_button(inter):
                if fake_action:
                    await inter.respond(
                        _(
                            "You are using this command in Fake mode, so no action will be taken, but I will pretend it is not the case."
                        ),
                        ephemeral=True,
                    )
                action = 4
                await self.cogsutils.delete_message(message)
                await self.call_actions(
                    ctx,
                    action,
                    user,
                    confirmation,
                    show_author,
                    finish_message,
                    fake_action,
                    delete_embed,
                    delete_message,
                    duration,
                    reason,
                )
                return

            @on_click.matching_id("tempban_button")
            async def on_tempban_button(inter):
                if fake_action:
                    await inter.respond(
                        _(
                            "You are using this command in Fake mode, so no action will be taken, but I will pretend it is not the case."
                        ),
                        ephemeral=True,
                    )
                action = 5
                await self.cogsutils.delete_message(message)
                await self.call_actions(
                    ctx,
                    action,
                    user,
                    confirmation,
                    show_author,
                    finish_message,
                    fake_action,
                    delete_embed,
                    delete_message,
                    duration,
                    reason,
                )
                return

            @on_click.matching_id("kick_button")
            async def on_kick_button(inter):
                if fake_action:
                    await inter.respond(
                        _(
                            "You are using this command in Fake mode, so no action will be taken, but I will pretend it is not the case."
                        ),
                        ephemeral=True,
                    )
                action = 6
                await self.cogsutils.delete_message(message)
                await self.call_actions(
                    ctx,
                    action,
                    user,
                    confirmation,
                    show_author,
                    finish_message,
                    fake_action,
                    delete_embed,
                    delete_message,
                    duration,
                    reason,
                )
                return

            @on_click.matching_id("mute_button")
            async def on_mute_button(inter):
                if fake_action:
                    await inter.respond(
                        _(
                            "You are using this command in Fake mode, so no action will be taken, but I will pretend it is not the case."
                        ),
                        ephemeral=True,
                    )
                action = 7
                await self.cogsutils.delete_message(message)
                await self.call_actions(
                    ctx,
                    action,
                    user,
                    confirmation,
                    show_author,
                    finish_message,
                    fake_action,
                    delete_embed,
                    delete_message,
                    duration,
                    reason,
                )
                return

            @on_click.matching_id("mutechannel_button")
            async def on_mutechannel_button(inter):
                if fake_action:
                    await inter.respond(
                        _(
                            "You are using this command in Fake mode, so no action will be taken, but I will pretend it is not the case."
                        ),
                        ephemeral=True,
                    )
                action = 8
                await self.cogsutils.delete_message(message)
                await self.call_actions(
                    ctx,
                    action,
                    user,
                    confirmation,
                    show_author,
                    finish_message,
                    fake_action,
                    delete_embed,
                    delete_message,
                    duration,
                    reason,
                )
                return

            @on_click.matching_id("tempmute_button")
            async def on_tempmute_button(inter):
                if fake_action:
                    await inter.respond(
                        _(
                            "You are using this command in Fake mode, so no action will be taken, but I will pretend it is not the case."
                        ),
                        ephemeral=True,
                    )
                action = 9
                await self.cogsutils.delete_message(message)
                await self.call_actions(
                    ctx,
                    action,
                    user,
                    confirmation,
                    show_author,
                    finish_message,
                    fake_action,
                    delete_embed,
                    delete_message,
                    duration,
                    reason,
                )
                return

            @on_click.matching_id("tempmutechannel_button")
            async def on_tempmutechannel_button(inter):
                if fake_action:
                    await inter.respond(
                        _(
                            "You are using this command in Fake mode, so no action will be taken, but I will pretend it is not the case."
                        ),
                        ephemeral=True,
                    )
                action = 10
                await self.cogsutils.delete_message(message)
                await self.call_actions(
                    ctx,
                    action,
                    user,
                    confirmation,
                    show_author,
                    finish_message,
                    fake_action,
                    delete_embed,
                    delete_message,
                    duration,
                    reason,
                )
                return

            @on_click.matching_id("close_button")
            async def on_test_button(inter):
                action = 11
                await self.cogsutils.delete_message(message)
                await self.call_actions(
                    ctx,
                    action,
                    user,
                    confirmation,
                    show_author,
                    finish_message,
                    fake_action,
                    delete_embed,
                    delete_message,
                    duration,
                    reason,
                )
                return

            @on_click.timeout
            async def on_timeout():
                if not end_reaction:
                    if delete_embed:
                        await self.cogsutils.delete_message(message)
                    else:
                        (
                            reactions,
                            buttons,
                            buttons_one,
                            buttons_two,
                            buttons_three,
                        ) = await utils.emojis(disabled=True)
                        await message.edit(
                            embed=embed, components=[buttons_one, buttons_two, buttons_three]
                        )
                    return

    async def call_actions(
        self,
        ctx: commands.Context,
        action: typing.Optional[int] = None,
        user: typing.Optional[discord.Member] = None,
        confirmation: typing.Optional[bool] = None,
        show_author: typing.Optional[bool] = None,
        finish_message: typing.Optional[bool] = None,
        fake_action: typing.Optional[bool] = False,
        delete_embed: typing.Optional[bool] = None,
        delete_message: typing.Optional[bool] = None,
        duration: typing.Optional[TimeDeltaConverter] = None,
        reason: str = None,
    ) -> None:
        config = await self.config.guild(ctx.guild).all()
        actual_thumbnail = config["thumbnail"]
        actual_color = config["color"]
        actual_warn_system_use = config["warn_system_use"]
        actual_reason_required = config["reason_required"]
        actual_timeout = config["timeout"]
        if ctx.bot.get_cog("WarnSystem"):
            if actual_warn_system_use:
                warn_system_exist = True
            else:
                warn_system_exist = False
        else:
            warn_system_exist = False

        if action == 1:
            message = await utils.finish_message(
                ctx,
                finish_message,
                _("Sanctioning a member - ℹ️ UserInfo"),
                _("Here is the information about the user {user.name}!").format(user=user),
                actual_thumbnail,
                actual_color,
                user,
                show_author,
                None,
                reason,
            )
            if not fake_action:
                if not ctx.bot.get_cog("Mod"):
                    await ctx.send(
                        _(
                            "The cog Mod is not loaded. To load it, do `{ctx.prefix}load mod`."
                        ).format(ctx=ctx)
                    )
                command = f"userinfo {user.id}"
                await self.cogsutils.invoke_command(
                    author=ctx.author,
                    channel=ctx.channel,
                    command=command,
                    prefix=ctx.prefix,
                    message=ctx.message,
                )
            reactions = ["✅"]
            start_adding_reactions(message, reactions)
            return

        elif action == 2:
            try:
                reason = await utils.reason_ask(
                    ctx,
                    reason,
                    actual_reason_required,
                    _("Sanctioning a member - ⚠️ Warn"),
                    _(
                        "Why do you want warn {user}? (Set `cancel` to cancel or `not` for none)"
                    ).format(user=user),
                    actual_color,
                    user,
                    actual_timeout,
                )
            except TimeoutError:
                return
            confirmation = await utils.confirmation_ask(
                ctx,
                confirmation,
                _("Sanctioning a member - ⚠️ Warn"),
                _("Do you really want to warn {user}?").format(user=user),
                actual_color,
                user,
                reason,
                None,
                actual_timeout,
            )
            if not confirmation:
                return
            message = await utils.finish_message(
                ctx,
                finish_message,
                _("Sanctioning a member - ⚠️ Warn"),
                _("The user {user} has been received a warning!").format(user=user),
                actual_thumbnail,
                actual_color,
                user,
                show_author,
                None,
                reason,
            )
            if not fake_action:
                if not warn_system_exist:
                    if not ctx.bot.get_cog("Warnings"):
                        await ctx.send(
                            _(
                                "The cog Warnings is not loaded. To load it, do `{ctx.prefix}load warnings`. You can also install/load the WarnSystem cog.".format(
                                    ctx=ctx
                                )
                            )
                        )
                    if reason == "not":
                        command = f"warn {user.id} The reason was not given."
                    else:
                        command = f"warn {user.id} {reason}"
                else:
                    if reason == "not":
                        command = f"warn 1 {user.id}"
                    else:
                        command = f"warn 1 {user.id} {reason}"
                await self.cogsutils.invoke_command(
                    author=ctx.author,
                    channel=ctx.channel,
                    command=command,
                    prefix=ctx.prefix,
                    message=ctx.message,
                )
            reactions = ["✅"]
            start_adding_reactions(message, reactions)
            return

        elif action == 3:
            try:
                reason = await utils.reason_ask(
                    ctx,
                    reason,
                    actual_reason_required,
                    _("Sanctioning a member - 🔨 Ban"),
                    _(
                        "Why do you want to ban {user}? (Set `cancel` to cancel or `not` to none)"
                    ).format(user=user),
                    actual_color,
                    user,
                    actual_timeout,
                )
            except TimeoutError:
                return
            confirmation = await utils.confirmation_ask(
                ctx,
                confirmation,
                _("Sanctioning a member - 🔨 Ban"),
                _("Do you really want to ban {user}?").format(user=user),
                actual_color,
                user,
                reason,
                None,
                actual_timeout,
            )
            if not confirmation:
                return
            message = await utils.finish_message(
                ctx,
                finish_message,
                _("Sanctioning a member - 🔨 Ban"),
                _("The user {user} has been banned!").format(user=user),
                actual_thumbnail,
                actual_color,
                user,
                show_author,
                None,
                reason,
            )
            if not fake_action:
                if not warn_system_exist:
                    if not ctx.bot.get_cog("Mod"):
                        await ctx.send(
                            _(
                                "The cog Mod is not loaded. To load it, do `{ctx.prefix}load mod`. You can also install/load the WarnSystem cog."
                            ).format(ctx=ctx)
                        )
                    if reason == "not":
                        command = f"ban {user.id}"
                    else:
                        command = f"ban {user.id} {reason}"
                else:
                    if reason == "not":
                        command = f"warn 5 {user.id}"
                    else:
                        command = f"warn 5 {user.id} {reason}"
                await self.cogsutils.invoke_command(
                    author=ctx.author,
                    channel=ctx.channel,
                    command=command,
                    prefix=ctx.prefix,
                    message=ctx.message,
                )
            reactions = ["✅"]
            start_adding_reactions(message, reactions)
            return

        elif action == 4:
            try:
                reason = await utils.reason_ask(
                    ctx,
                    reason,
                    actual_reason_required,
                    _("Sanctioning a member - 🔂 SoftBan"),
                    _(
                        "Why do you want to softban {user}? (Set `cancel` to cancel or `not` to none)"
                    ).format(user=user),
                    actual_color,
                    user,
                    actual_timeout,
                )
            except TimeoutError:
                return
            confirmation = await utils.confirmation_ask(
                ctx,
                confirmation,
                _("Sanctioning a member - 🔂 SoftBan"),
                _("Do you really want to softban {user}?").format(user=user),
                actual_color,
                user,
                reason,
                None,
                actual_timeout,
            )
            if not confirmation:
                return
            message = await utils.finish_message(
                ctx,
                finish_message,
                _("Sanctioning a member - 🔂 SoftBan"),
                _("The user {user} has been softbanned!").format(user=user),
                actual_thumbnail,
                actual_color,
                user,
                show_author,
                None,
                reason,
            )
            if not fake_action:
                if not warn_system_exist:
                    if not ctx.bot.get_cog("Mod"):
                        await ctx.send(
                            _(
                                "The cog Mod is not loaded. To load it, do `{ctx.prefix}load mod`. You can also install/load the WarnSystem cog."
                            ).format(ctx=ctx)
                        )
                    if reason == "not":
                        command = f"softban {user.id}"
                    else:
                        command = f"softban {user.id} {reason}"
                else:
                    if reason == "not":
                        command = f"warn 4 {user.id}"
                    else:
                        command = f"warn 4 {user.id} {reason}"
                await self.cogsutils.invoke_command(
                    author=ctx.author,
                    channel=ctx.channel,
                    command=command,
                    prefix=ctx.prefix,
                    message=ctx.message,
                )
            reactions = ["✅"]
            start_adding_reactions(message, reactions)
            return

        elif action == 5:
            try:
                duration = await utils.duration_ask(
                    ctx,
                    duration,
                    _("Sanctioning a member - 💨 TempBan"),
                    _("How long do you want to tempban {user}? (Set `cancel` to cancel)").format(
                        user=user
                    ),
                    actual_color,
                    user,
                    actual_timeout,
                )
            except TimeoutError:
                return
            try:
                reason = await utils.reason_ask(
                    ctx,
                    reason,
                    actual_reason_required,
                    _("Sanctioning a member - 💨 TempBan"),
                    _(
                        "Why do you want to tempban {user}? (Set `cancel` to cancel or `not` to none)"
                    ).format(user=user),
                    actual_color,
                    user,
                    actual_timeout,
                )
            except TimeoutError:
                return
            confirmation = await utils.confirmation_ask(
                ctx,
                confirmation,
                _("Sanctioning a member - 💨 TempBan"),
                _("Do you really want to tempban {user}?").format(user=user),
                actual_color,
                user,
                reason,
                duration,
                actual_timeout,
            )
            if not confirmation:
                return
            message = await utils.finish_message(
                ctx,
                finish_message,
                _("Sanctioning a member - 💨 TempBan"),
                _("The user {user} has been tempban!").format(user=user),
                actual_thumbnail,
                actual_color,
                user,
                show_author,
                duration,
                reason,
            )
            if not fake_action:
                if not warn_system_exist:
                    if not ctx.bot.get_cog("Mod"):
                        await ctx.send(
                            _(
                                "The cog Mod is not loaded. To load it, do `{ctx.prefix}load mod`. You can also install/load the WarnSystem cog."
                            ).format(ctx=ctx)
                        )
                    if reason == "not":
                        command = f"tempban {user.id} {duration}"
                    else:
                        command = f"tempban {user.id} {duration} {reason}"
                else:
                    if reason == "not":
                        command = f"warn 5 {user.id} {duration}"
                    else:
                        command = f"warn 5 {user.id} {duration} {reason}"
                await self.cogsutils.invoke_command(
                    author=ctx.author,
                    channel=ctx.channel,
                    command=command,
                    prefix=ctx.prefix,
                    message=ctx.message,
                )
            reactions = ["✅"]
            start_adding_reactions(message, reactions)
            return

        elif action == 6:
            try:
                reason = await utils.reason_ask(
                    ctx,
                    reason,
                    actual_reason_required,
                    _("Sanctioning a member - 👢 Kick"),
                    _(
                        "Why do you want to kick {user}? (Set `cancel` to cancel or `not` to none)"
                    ).format(user=user),
                    actual_color,
                    user,
                    actual_timeout,
                )
            except TimeoutError:
                return
            confirmation = await utils.confirmation_ask(
                ctx,
                confirmation,
                _("Sanctioning a member - 👢 Kick"),
                _(
                    "Why do you want to kick {user}? (Set `cancel` to cancel or `not` to none)"
                ).format(user=user),
                actual_color,
                user,
                reason,
                None,
                actual_timeout,
            )
            if not confirmation:
                return
            message = await utils.finish_message(
                ctx,
                finish_message,
                _("Sanctioning a member - 👢 Kick"),
                _("The user {user} has been kicked!").format(user=user),
                actual_thumbnail,
                actual_color,
                user,
                show_author,
                None,
                reason,
            )
            if not fake_action:
                if not warn_system_exist:
                    if not ctx.bot.get_cog("Mod"):
                        await ctx.send(
                            _(
                                "The cog Mod is not loaded. To load it, do `{ctx.prefix}load mod`. You can also install/load the WarnSystem cog."
                            ).format(ctx=ctx)
                        )
                    if reason == "not":
                        command = f"kick {user.id}"
                    else:
                        command = f"kick {user.id} {reason}"
                else:
                    if reason == "not":
                        command = f"warn 3 {user.id}"
                    else:
                        command = f"warn 3 {user.id} {reason}"
                await self.cogsutils.invoke_command(
                    author=ctx.author,
                    channel=ctx.channel,
                    command=command,
                    prefix=ctx.prefix,
                    message=ctx.message,
                )
            reactions = ["✅"]
            start_adding_reactions(message, reactions)
            return

        elif action == 7:
            try:
                reason = await utils.reason_ask(
                    ctx,
                    reason,
                    actual_reason_required,
                    _("Sanctioning a member - 🔇 Mute"),
                    _(
                        "Why do you want to mute {user}? (Set `cancel` to cancel or `not` to none)"
                    ).format(user=user),
                    actual_color,
                    user,
                    actual_timeout,
                )
            except TimeoutError:
                return
            confirmation = await utils.confirmation_ask(
                ctx,
                confirmation,
                _("Sanctioning a member - 🔇 Mute"),
                _("Do you really want to mute {user}?").format(user=user),
                actual_color,
                user,
                reason,
                None,
                actual_timeout,
            )
            if not confirmation:
                return
            message = await utils.finish_message(
                ctx,
                finish_message,
                _("Sanctioning a member - 🔇 Mute"),
                _("The user {user} has been muted!").format(user=user),
                actual_thumbnail,
                actual_color,
                user,
                show_author,
                None,
                reason,
            )
            if not fake_action:
                if not warn_system_exist:
                    if not ctx.bot.get_cog("Mutes"):
                        await ctx.send(
                            _(
                                "The cog Mutes is not loaded. To load it, do `{ctx.prefix}load mutes`. You can also install/load the WarnSystem cog."
                            ).format(ctx=ctx)
                        )
                    if reason == "not":
                        command = f"mute {user.id}"
                    else:
                        command = f"mute {user.id}"
                else:
                    if reason == "not":
                        command = f"warn 2 {user.id}"
                    else:
                        command = f"warn 2 {user.id} {reason}"
                await self.cogsutils.invoke_command(
                    author=ctx.author,
                    channel=ctx.channel,
                    command=command,
                    prefix=ctx.prefix,
                    message=ctx.message,
                )
            reactions = ["✅"]
            start_adding_reactions(message, reactions)
            return

        elif action == 8:
            try:
                reason = await utils.reason_ask(
                    ctx,
                    reason,
                    actual_reason_required,
                    _("Sanctioning a member - 👊 MuteChannel"),
                    _(
                        "Why do you want to mute {user} in {ctx.channel.mention}? (Set `cancel` to cancel or `not` to none)"
                    ).format(user=user, ctx=ctx),
                    actual_color,
                    user,
                    actual_timeout,
                )
            except TimeoutError:
                return
            confirmation = await utils.confirmation_ask(
                ctx,
                confirmation,
                _("Sanctioning a member - 👊 MuteChannel"),
                _("Do you really want to mute {user} in {ctx.channel.mention}?").format(
                    user=user, ctx=ctx
                ),
                actual_color,
                user,
                reason,
                None,
                actual_timeout,
            )
            if not confirmation:
                return
            message = await utils.finish_message(
                ctx,
                finish_message,
                _("Sanctioning a member - 👊 MuteChannel"),
                _("The user {user} has been muted in #{ctx.channel.name}!").format(
                    user=user, ctx=ctx
                ),
                actual_thumbnail,
                actual_color,
                user,
                show_author,
                None,
                reason,
            )
            if not fake_action:
                if not ctx.bot.get_cog("Mutes"):
                    await ctx.send(
                        _(
                            "The cog Mutes is not loaded. To load it, do `{ctx.prefix}load mutes`."
                        ).format(ctx=ctx)
                    )
                if reason == "not":
                    command = f"mutechannel {user.id}"
                else:
                    command = f"mutechannel {user.id}"
                await self.cogsutils.invoke_command(
                    author=ctx.author,
                    channel=ctx.channel,
                    command=command,
                    prefix=ctx.prefix,
                    message=ctx.message,
                )
            reactions = ["✅"]
            start_adding_reactions(message, reactions)
            return

        elif action == 9:
            try:
                duration = await utils.duration_ask(
                    ctx,
                    duration,
                    _("Sanctioning a member - ⏳ TempMute"),
                    _("How long do you want to tempmute {user}? (Set `cancel` to cancel)").format(
                        user=user
                    ),
                    actual_color,
                    user,
                    actual_timeout,
                )
            except TimeoutError:
                return
            try:
                reason = await utils.reason_ask(
                    ctx,
                    reason,
                    actual_reason_required,
                    _("Sanctioning a member - ⏳ TempMute"),
                    _(
                        "Why do you want to tempmute {user}? (Set `cancel` to cancel or `not` to none)"
                    ).format(user=user),
                    actual_color,
                    user,
                    actual_timeout,
                )
            except TimeoutError:
                return
            confirmation = await utils.confirmation_ask(
                ctx,
                confirmation,
                _("Sanctioning a member - ⏳ TempMute"),
                _("Do you really want to tempmute {user}?").format(user=user),
                actual_color,
                user,
                reason,
                duration,
                actual_timeout,
            )
            if not confirmation:
                return
            message = await utils.finish_message(
                ctx,
                finish_message,
                _("Sanctioning a member - ⏳ TempMute"),
                _("The user {user} has been tempmuted!").format(user=user),
                actual_thumbnail,
                actual_color,
                user,
                show_author,
                duration,
                reason,
            )
            if not fake_action:
                if not warn_system_exist:
                    if not ctx.bot.get_cog("Mutes"):
                        await ctx.send(
                            _(
                                "The cog Mutes is not loaded. To load it, do `{ctx.prefix}load mutes`. You can also install/load the WarnSystem cog."
                            ).format(ctx=ctx)
                        )
                    if reason == "not":
                        command = f"mute {user.id} {duration}"
                    else:
                        command = f"mute {user.id} {duration} {reason}"
                else:
                    if reason == "not":
                        command = f"warn 2 {user.id} {duration}"
                    else:
                        command = f"warn 2 {user.id} {duration} {reason}"
                await self.cogsutils.invoke_command(
                    author=ctx.author,
                    channel=ctx.channel,
                    command=command,
                    prefix=ctx.prefix,
                    message=ctx.message,
                )
            reactions = ["✅"]
            start_adding_reactions(message, reactions)
            return

        elif action == 10:
            try:
                duration = await utils.duration_ask(
                    ctx,
                    duration,
                    _("Sanctioning a member - ⌛ TempMuteChannel"),
                    _(
                        "How long do you want to tempmute {user} in {ctx.channel.mention}? (Set `cancel` to cancel)"
                    ).format(user=user, ctx=ctx),
                    actual_color,
                    user,
                    actual_timeout,
                )
            except TimeoutError:
                return
            try:
                reason = await utils.reason_ask(
                    ctx,
                    reason,
                    actual_reason_required,
                    _("Sanctioning a member - ⌛ TempMuteChannel"),
                    _(
                        "Why do you want to tempmute {user} in {ctx.channel.mention}? (Set `cancel` to cancel or `not` to none)"
                    ).format(user=user, ctx=ctx),
                    actual_color,
                    user,
                    actual_timeout,
                )
            except TimeoutError:
                return
            confirmation = await utils.confirmation_ask(
                ctx,
                confirmation,
                _("Sanctioning a member - ⌛ TempMuteChannel"),
                _("Do you really want to tempmute {user} in {ctx.channel.mention}?").format(
                    user=user, ctx=ctx
                ),
                actual_color,
                user,
                reason,
                duration,
                actual_timeout,
            )
            if not confirmation:
                return
            message = await utils.finish_message(
                ctx,
                finish_message,
                _("Sanctioning a member - ⌛ TempMuteChannel"),
                _("The user {user} has been tempmuted in #{ctx.channel.name}!").format(
                    user=user, ctx=ctx
                ),
                actual_thumbnail,
                actual_color,
                user,
                show_author,
                duration,
                reason,
            )
            if not fake_action:
                if not ctx.bot.get_cog("Mutes"):
                    await ctx.send(
                        _(
                            "The cog Mutes is not loaded. To load it, do `{ctx.prefix}load mutes`."
                        ).format(ctx=ctx)
                    )
                if reason == "not":
                    command = f"mutechannel {user.id} {duration}"
                else:
                    command = f"mutechannel {user.id} {duration} {reason}"
                await self.cogsutils.invoke_command(
                    author=ctx.author,
                    channel=ctx.channel,
                    command=command,
                    prefix=ctx.prefix,
                    message=ctx.message,
                )
            reactions = ["✅"]
            start_adding_reactions(message, reactions)
            return

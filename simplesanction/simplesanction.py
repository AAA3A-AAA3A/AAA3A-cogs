from AAA3A_utils import Cog, CogsUtils, Settings  # isort:skip
from redbot.core import commands, app_commands, Config  # isort:skip
from redbot.core.bot import Red  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import asyncio

from discord.ext.commands import BadArgument
from redbot.core.commands.converter import parse_timedelta, timedelta
from redbot.core.utils.predicates import MessagePredicate

from .constants import ACTIONS_DICT
from .types import Action
from .view import SimpleSanctionView

# Credits:
# General repo credits.
# Thanks to Laggrons-dumb's WarnSystem cog (https://github.com/laggron42/Laggrons-Dumb-Cogs/tree/v3/warnsystem) for giving me ideas and code for subcommands of a main command!
# Thanks to Yami for the technique in the init file of some cogs to load the interaction client only if it is not already loaded! Before this fix, when a user clicked a button, the actions would be run about 10 times, causing a huge spam and loop in the channel.
# Thanks to @Aikaterna on the Red support server for help on displaying the main command help menu and other commands!

_ = Translator("SimpleSanction", __file__)


class TimeDeltaConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> timedelta:
        delta = parse_timedelta(argument)
        if delta is not None:
            return argument
        else:
            raise BadArgument()


@app_commands.context_menu(name="Sanction Member")
async def sanction_member_context_menu(interaction: discord.Interaction, member: discord.Member):
    await interaction.response.defer()
    cog = interaction.client.get_cog("SimpleSanction")
    context = await CogsUtils.invoke_command(
        bot=interaction.client,
        author=interaction.user,
        channel=interaction.channel,
        command=f"sanction {member.id}",
        interaction=interaction,
    )
    if not await context.command.can_run(context):
        await interaction.followup.send(
            _("You're not allowed to execute the `[p]sanction` command in this channel."),
            ephemeral=True,
        )
        return


@cog_i18n(_)
class SimpleSanction(Cog):
    """A cog to sanction members, with buttons!"""

    def __init__(self, bot: Red) -> None:
        super().__init__(bot=bot)

        self.config: Config = Config.get_conf(
            self,
            identifier=205192943327321000143939875896557571750,  # 793615829052
            force_registration=True,
        )
        self.sanction_guild: typing.Dict[str, typing.Union[str, bool, int]] = {
            "use_warn_system": True,
            "reason_required": True,
            "show_author": True,
            "action_confirmation": True,
            "finish_message": True,
            "thumbnail": "https://i.imgur.com/Bl62rGd.png",
        }
        self.config.register_guild(**self.sanction_guild)

        self.actions: typing.Dict[str, Action] = {key: Action(cog=self, key=key, **value) for key, value in ACTIONS_DICT.items()}

        _settings: typing.Dict[
            str, typing.Dict[str, typing.Union[typing.List[str], typing.Any, str]]
        ] = {
            "use_warn_system": {
                "path": ["use_warn_system"],
                "converter": bool,
                "description": "Use WarnSystem by Laggron for the sanctions.",
                "aliases": ["warnsystemuse"]
            },
            "reason_required": {
                "path": ["reason_required"],
                "converter": bool,
                "description": "Require a reason for each sanction (except userinfo).",
            },
            "show_author": {
                "path": ["show_author"],
                "converter": bool,
                "description": "Show the command author in embeds.",
            },
            "action_confirmation": {
                "path": ["action_confirmation"],
                "converter": bool,
                "description": "Require a confirmation for each sanction (except userinfo).",
            },
            "finish_message": {
                "path": ["finish_message"],
                "converter": bool,
                "description": "Send an embed after a sanction command execution.",
            },
            "thumbnail": {
                "path": ["thumbnail"],
                "converter": str,
                "description": "Set the embed thumbnail.",
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
            commands_group=self.configuration,
        )

    async def cog_load(self) -> None:
        await super().cog_load()
        await self.settings.add_commands()
        self.bot.tree.add_command(sanction_member_context_menu)

    async def cog_unload(self) -> None:
        self.bot.tree.remove_command(sanction_member_context_menu.name)
        await super().cog_unload()

    @commands.guild_only()
    @commands.admin_or_permissions(administrator=True)
    @commands.hybrid_group(name="setsimplesanction", aliases=["simplesanctionset"])
    async def configuration(self, ctx: commands.Context) -> None:
        """Configure SimpleSanction for your server."""
        pass

    @commands.guild_only()
    @commands.mod_or_permissions(administrator=True)
    @commands.bot_has_permissions(add_reactions=True, embed_links=True)
    @commands.hybrid_group(
        invoke_without_command=True,
        name="sanction",
        aliases=["punishmember", "punishuser"],
    )
    async def _sanction(
        self,
        ctx: commands.Context,
        member: typing.Optional[discord.Member] = None,
        confirmation: typing.Optional[bool] = None,
        show_author: typing.Optional[bool] = None,
        finish_message: typing.Optional[bool] = None,
        fake_action: typing.Optional[bool] = False,
        duration_for_mute_or_ban: typing.Optional[TimeDeltaConverter] = None,
        *,
        reason: str = None,
    ) -> None:
        """
        Sanction a member quickly and easily.

        All arguments are optional and will be requested during the action if necessary. You must specify the parameters in this order.

        Parameters:
        - `user`: Server member.			    Who is the user concerned?
        - `confirmation`: True or False.		Confirm the action directly. (Default is the recorded value)
        - `show_author`: True or False.			Do you want the bot to show in its embeds who is the author of the command/sanction? (Default is the recorded value)
        - `finish_message`: True or False.		Do you want the bot to show an embed just before the action summarising the action and giving the sanctioned user and the reason? (Default is the recorded value)
        - `fake_action`: True or False.		    Do you want the command to do everything as usual, but (unintentionally) forget to execute the action?
        - `duration`: Duration. (5d, 8h, 1m...)	If you choose a TempBan, TempMute or TempMuteChanne, this value will be used for the duration of that action.
        - `reason`: Text.				        The reason for this action. (`not` to not specify one, unless the reason has been made falcutative in the parameters)

        Short version: [p]sanction
        Long version:  [p]sanction 10 @member true true true true true true 3d Spam.
        """
        await self.call_sanction(
            ctx,
            action=None,
            member=member,
            confirmation=confirmation,
            show_author=show_author,
            finish_message=finish_message,
            fake_action=fake_action,
            duration=duration_for_mute_or_ban,
            reason=reason,
        )

    @_sanction.command(
        name="00",
        aliases=["0", "sanction"],
    )
    async def sanction_0(
        self,
        ctx: commands.Context,
        member: typing.Optional[discord.Member] = None,
        confirmation: typing.Optional[bool] = None,
        show_author: typing.Optional[bool] = None,
        finish_message: typing.Optional[bool] = None,
        fake_action: typing.Optional[bool] = False,
        duration_for_mute_or_ban: typing.Optional[TimeDeltaConverter] = None,
        *,
        reason: str = None,
    ) -> None:
        """
        - Sanction a member quickly and easily.

        Examples:
        - `[p]sanction 0 @member`
        - `[p]sanction 0 @member What are these roles?`
        - `[p]sanction 0 012345678987654321`
        """
        await self.call_sanction(
            ctx,
            action=None,
            member=member,
            confirmation=confirmation,
            show_author=show_author,
            finish_message=finish_message,
            fake_action=fake_action,
            duration=duration_for_mute_or_ban,
            reason=reason,
        )

    @_sanction.command(
        name="01",
        aliases=["1", "userinfo", "memberinfo", "info"],
    )
    async def sanction_1(
        self,
        ctx: commands.Context,
        member: typing.Optional[discord.Member] = None,
        confirmation: typing.Optional[bool] = None,
        show_author: typing.Optional[bool] = None,
        finish_message: typing.Optional[bool] = None,
        fake_action: typing.Optional[bool] = False,
        *,
        reason: str = None,
    ) -> None:
        """
         - ℹ️ Show informations about a member.

        Examples:
        - `[p]sanction 1 @member`: UserInfo for no reason.
        - `[p]sanction 1 @member What are these roles?`: UserInfo for the reason "What are these roles?".
        - `[p]sanction 1 012345678987654321`: UserInfo with the ID provided.
        """
        await self.call_sanction(
            ctx,
            action=self.actions["userinfo"],
            member=member,
            confirmation=confirmation,
            show_author=show_author,
            finish_message=finish_message,
            fake_action=fake_action,
            duration=None,
            reason=reason,
        )

    @_sanction.command(
        name="02",
        aliases=["2", "warn"],
    )
    async def sanction_2(
        self,
        ctx: commands.Context,
        member: typing.Optional[discord.Member] = None,
        confirmation: typing.Optional[bool] = None,
        show_author: typing.Optional[bool] = None,
        finish_message: typing.Optional[bool] = None,
        fake_action: typing.Optional[bool] = False,
        duration_for_mute_or_ban: typing.Optional[TimeDeltaConverter] = None,
        *,
        reason: str = None,
    ) -> None:
        """
         - ⚠️ Add a simple warning on a member.

        Examples:
        - `[p]sanction 2 @member not`: Warn for no reason.
        - `[p]sanction 2 @member Insults`: Warn for the reason "Insults".
        - `[p]sanction 2 012345678987654321 Advertising`: Warn the user with the ID provided.
        """
        await self.call_sanction(
            ctx,
            action=self.actions["warn"],
            member=member,
            confirmation=confirmation,
            show_author=show_author,
            finish_message=finish_message,
            fake_action=fake_action,
            duration=duration_for_mute_or_ban,
            reason=reason,
        )

    @_sanction.command(
        name="03",
        aliases=["3", "ban"],
    )
    async def sanction_3(
        self,
        ctx: commands.Context,
        member: typing.Optional[discord.Member] = None,
        confirmation: typing.Optional[bool] = None,
        show_author: typing.Optional[bool] = None,
        finish_message: typing.Optional[bool] = None,
        fake_action: typing.Optional[bool] = False,
        *,
        reason: str = None,
    ) -> None:
        """
         - 🔨 Ban a member from this server.

        It won't delete messages by default.

        Examples:
        - `[p]sanction 3 @member not`: Ban for no reason.
        - `[p]sanction 3 @member Insults`: Ban for the reason "Insults".
        - `[p]sanction 3 012345678987654321 Advertising`: Ban the user with the ID provided.
        """
        await self.call_sanction(
            ctx,
            action=self.actions["ban"],
            member=member,
            confirmation=confirmation,
            show_author=show_author,
            finish_message=finish_message,
            fake_action=fake_action,
            duration=None,
            reason=reason,
        )

    @_sanction.command(
        name="04",
        aliases=["4", "softban"],
    )
    async def sanction_4(
        self,
        ctx: commands.Context,
        member: typing.Optional[discord.Member] = None,
        confirmation: typing.Optional[bool] = None,
        show_author: typing.Optional[bool] = None,
        finish_message: typing.Optional[bool] = None,
        fake_action: typing.Optional[bool] = False,
        *,
        reason: str = None,
    ) -> None:
        """
         - 🔂 SoftBan a member from this server.

        This means that the user will be banned and immediately unbanned, so it will purge their messages in a period, in all channels.

        Examples:
        - `[p]sanction 4 @member not`: SoftBan for no reason
        - `[p]sanction 4 @member Insults`: SoftBan for the reason "Insults"
        - `[p]sanction 4 012345678987654321 Advertising`: SoftBan the user with the ID provided.
        """
        await self.call_sanction(
            ctx,
            action=self.actions["softban"],
            member=member,
            confirmation=confirmation,
            show_author=show_author,
            finish_message=finish_message,
            fake_action=fake_action,
            duration=None,
            reason=reason,
        )

    @_sanction.command(
        name="05",
        aliases=["5", "tempban"],
    )
    async def sanction_5(
        self,
        ctx: commands.Context,
        member: typing.Optional[discord.Member] = None,
        confirmation: typing.Optional[bool] = None,
        show_author: typing.Optional[bool] = None,
        finish_message: typing.Optional[bool] = None,
        fake_action: typing.Optional[bool] = False,
        duration_for_mute_or_ban: typing.Optional[TimeDeltaConverter] = None,
        *,
        reason: str = None,
    ) -> None:
        """
         - 💨 TempBan a member from this server.

        It won't delete messages by default.
        If you want to perform a temporary ban, provide the time before the reason.

        Examples:
        - `[p]sanction 5 @member not`: Ban for no reason.
        - `[p]sanction 5 @member 7d Insults`: 7 days ban for the reason "Insults".
        - `[p]sanction 5 012345678987654321 Advertising`: Ban the user with the ID provided.
        """
        await self.call_sanction(
            ctx,
            action=self.actions["tempban"],
            member=member,
            confirmation=confirmation,
            show_author=show_author,
            finish_message=finish_message,
            fake_action=fake_action,
            duration=duration_for_mute_or_ban,
            reason=reason,
        )

    @_sanction.command(
        name="06",
        aliases=["6", "kick"],
    )
    async def sanction_6(
        self,
        ctx: commands.Context,
        member: typing.Optional[discord.Member] = None,
        confirmation: typing.Optional[bool] = None,
        show_author: typing.Optional[bool] = None,
        finish_message: typing.Optional[bool] = None,
        fake_action: typing.Optional[bool] = False,
        *,
        reason: str = None,
    ) -> None:
        """
         - 👢 Kick a member from this server.

        Examples:
        - `[p]sanction 6 @member not`: Kick for no reason.
        - `[p]sanction 6 @member Insults`: Kick for the reason "Insults".
        - `[p]sanction 6 012345678987654321 Advertising`: Kick the user with the ID provided.
        """
        await self.call_sanction(
            ctx,
            action=self.actions["kick"],
            member=member,
            confirmation=confirmation,
            show_author=show_author,
            finish_message=finish_message,
            fake_action=fake_action,
            duration=None,
            reason=reason,
        )

    @_sanction.command(
        name="07",
        aliases=["7", "mute"],
    )
    async def sanction_7(
        self,
        ctx: commands.Context,
        member: typing.Optional[discord.Member] = None,
        confirmation: typing.Optional[bool] = None,
        show_author: typing.Optional[bool] = None,
        finish_message: typing.Optional[bool] = None,
        fake_action: typing.Optional[bool] = False,
        *,
        reason: str = None,
    ) -> None:
        """
         - 🔇 Mute a member in all channels, including voice channels.

        Examples:
        - `[p]sanction 7 @member not`: Infinite mute for no reason.
        - `[p]sanction 7 @member Spam`:Infinite  mute for the reason "Spam".
        - `[p]sanction 7 @member Advertising`: Infinite mute for the reason "Advertising".
        """
        await self.call_sanction(
            ctx,
            action=self.actions["mute"],
            member=member,
            confirmation=confirmation,
            show_author=show_author,
            finish_message=finish_message,
            fake_action=fake_action,
            duration=None,
            reason=reason,
        )

    @_sanction.command(
        name="08",
        aliases=["8", "mutechannel"],
    )
    async def sanction_8(
        self,
        ctx: commands.Context,
        member: typing.Optional[discord.Member] = None,
        confirmation: typing.Optional[bool] = None,
        show_author: typing.Optional[bool] = None,
        finish_message: typing.Optional[bool] = None,
        fake_action: typing.Optional[bool] = False,
        *,
        reason: str = None,
    ) -> None:
        """
         - 👊 Mute a member in this channel.

        Examples:
        - `[p]sanction 8 @member not`: Infinite mute for no reason.
        - `[p]sanction 8 @member Spam`: Infinite mute for the reason "Spam".
        - `[p]sanction 8 @member Advertising`: Infinite mute for the reason "Advertising".
        """
        await self.call_sanction(
            ctx,
            action=self.actions["mutechannel"],
            member=member,
            confirmation=confirmation,
            show_author=show_author,
            finish_message=finish_message,
            fake_action=fake_action,
            duration=None,
            reason=reason,
        )

    @_sanction.command(
        name="09",
        aliases=["9", "tempmute"],
    )
    async def sanction_9(
        self,
        ctx: commands.Context,
        member: typing.Optional[discord.Member] = None,
        confirmation: typing.Optional[bool] = None,
        show_author: typing.Optional[bool] = None,
        finish_message: typing.Optional[bool] = None,
        fake_action: typing.Optional[bool] = False,
        duration_for_mute_or_ban: typing.Optional[TimeDeltaConverter] = None,
        *,
        reason: str = None,
    ) -> None:
        """
         - ⏳ TempMute a member in all channels, including voice channels.

        You can set a timed mute by providing a valid time before the reason.

        Examples:
        - `[p]sanction 9 @member 30m not`: 30 minutes mute for no reason.
        - `[p]sanction 9 @member 5h Spam`: 5 hours mute for the reason "Spam".
        - `[p]sanction 9 @member 3d Advertising`: 3 days mute for the reason "Advertising".
        """
        await self.call_sanction(
            ctx,
            action=self.actions["tempmute"],
            member=member,
            confirmation=confirmation,
            show_author=show_author,
            finish_message=finish_message,
            fake_action=fake_action,
            duration=duration_for_mute_or_ban,
            reason=reason,
        )

    @_sanction.command(
        name="10",
        aliases=["tempmutechannel"],
    )
    async def sanction_10(
        self,
        ctx: commands.Context,
        member: typing.Optional[discord.Member] = None,
        confirmation: typing.Optional[bool] = None,
        show_author: typing.Optional[bool] = None,
        finish_message: typing.Optional[bool] = None,
        fake_action: typing.Optional[bool] = False,
        duration_for_mute_or_ban: typing.Optional[TimeDeltaConverter] = None,
        *,
        reason: str = None,
    ) -> None:
        """
         - ⌛ TempMute a member in this channel.

        You can set a timed mute by providing a valid time before the reason.

        Examples:
        - `[p]sanction 10 @member 30m not`: 30 minutes mute for no reason.
        - `[p]sanction 10 @member 5h Spam`: 5 hours mute for the reason "Spam".
        - `[p]sanction 10 @member 3d Advertising`: 3 days mute for the reason "Advertising".
        """
        await self.call_sanction(
            ctx,
            action=self.actions["tempmutechannel"],
            member=member,
            confirmation=confirmation,
            show_author=show_author,
            finish_message=finish_message,
            fake_action=fake_action,
            duration=duration_for_mute_or_ban,
            reason=reason,
        )

    async def call_sanction(
        self,
        ctx: commands.Context,
        action: typing.Optional[Action] = None,
        member: typing.Optional[discord.Member] = None,
        confirmation: typing.Optional[bool] = None,
        show_author: typing.Optional[bool] = None,
        finish_message: typing.Optional[bool] = None,
        fake_action: typing.Optional[bool] = False,
        duration: typing.Optional[TimeDeltaConverter] = None,
        reason: str = None,
    ) -> None:
        config = await self.config.guild(ctx.guild).all()
        if show_author is None:
            show_author = config["show_author"]
        if confirmation is None:
            confirmation = not config["action_confirmation"]
        if finish_message is None:
            finish_message = config["finish_message"]
        if reason is not None and reason.lower() == "not":
            reason = _("The reason was not given.")

        if member is None:
            embed: discord.Embed = discord.Embed()
            embed.title = _("Sanction Member")
            embed.description = _(
                "Which member do you want to sanction? (Type `cancel` to cancel.)"
            )
            embed.color = await ctx.embed_color()
            message = await ctx.send(embed=embed)
            try:
                pred = MessagePredicate.valid_member(ctx)
                msg = await self.bot.wait_for(
                    "message",
                    timeout=60,
                    check=pred,
                )
                await CogsUtils.delete_message(message)
                await CogsUtils.delete_message(msg)
                if msg.content.lower() == "cancel":
                    return
                member = pred.result
            except asyncio.TimeoutError:
                raise commands.UserFeedbackCheckFailure(_("Timed out, please try again."))

        if action is not None:
            await action.process(ctx, interaction=None, member=member, duration=duration, reason=reason, finish_message_enabled=finish_message, reason_required=await self.config.guild(ctx.guild).reason_required(), confirmation=confirmation, show_author=show_author, fake_action=fake_action)
        else:
            await SimpleSanctionView(cog=self, member=member, duration=duration, reason=reason, finish_message_enabled=finish_message, reason_required=await self.config.guild(ctx.guild).reason_required(), confirmation=confirmation, show_author=show_author, fake_action=fake_action).start(ctx)

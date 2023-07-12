from AAA3A_utils import Cog, CogsUtils  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
from redbot.core.bot import Red  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import datetime
import inspect
import functools

from redbot.core.commands.converter import get_timedelta_converter
from redbot.core.utils.chat_formatting import box

TimedeltaConverter = get_timedelta_converter(
    default_unit="s",
    maximum=datetime.timedelta(seconds=21600),
    minimum=datetime.timedelta(seconds=0),
)

def _(untranslated: str) -> str:  # `redgettext` will found these strings.
    return untranslated
ERROR_MESSAGE = _("I attempted to do something that Discord denied me permissions for. Your command failed to successfully complete.\n{error}")

_ = Translator("DiscordEdit", __file__)


class LocaleConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str):
        try:
            return discord.Locale(argument)
        except ValueError:
            raise commands.BadArgument(
                _("Converting to `Locale` failed for parameter `preferred_locale`.")
            )


@cog_i18n(_)
class EditGuild(Cog):
    """A cog to edit guilds!"""

    def __init__(self, bot: Red) -> None:  # Never executed except manually.
        super().__init__(bot=bot)

    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    @commands.bot_has_permissions(manage_guild=True)
    @commands.hybrid_group()
    async def editguild(self, ctx: commands.Context) -> None:
        """Commands for edit a guild."""
        pass

    @commands.is_owner()
    @editguild.command(name="create")
    async def editguild_create(
        self, ctx: commands.Context, name: commands.Range[str, 2, 100], template_code: typing.Optional[str] = None
    ) -> None:
        """Create a guild with the bot as owner."""
        try:
            guild = await ctx.bot.create_guild(name=name, code=template_code)
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )
        channel = next((c for c in guild.channels if c.type == discord.ChannelType.text), None)
        if channel is None:
            channel = await guild.create_text_channel(name="general")
        invite_url = (await channel.create_invite()).url
        await ctx.send(
            f"**Guild name:** {guild.name}\n**Guild ID:** {guild.id}\n**First channel's ID**: {channel.id}\n**Invite URL:** {invite_url}"
        )

    @commands.is_owner()
    @editguild.command(name="clone")
    async def editguild_clone(self, ctx: commands.Context, *, name: str) -> None:
        """Clone a guild."""
        guild = ctx.guild
        try:
            template = await guild.create_template(name="Template for guild clone.")
            guild = await ctx.bot.create_guild(name=name, code=template.code)
            await template.delete()
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )
        channel = next((c for c in guild.channels if c.type == discord.ChannelType.text), None)
        if channel is None:
            channel = await guild.create_text_channel(name="general")
        invite_url = (await channel.create_invite()).url
        await ctx.send(
            f"**Guild name:** {guild.name}\n**Guild ID:** {guild.id}\n**First channel's ID**: {channel.id}\n**Invite URL:** {invite_url}"
        )

    @editguild.command(name="name")
    async def editguild_name(self, ctx: commands.Context, *, name: commands.Range[str, 2, 100]) -> None:
        """Edit guild name."""
        guild = ctx.guild
        try:
            await guild.edit(
                name=name,
                reason=f"{ctx.author} ({ctx.author.id}) has edited the guild {guild.name} ({guild.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @editguild.command(name="description")
    async def editguild_description(
        self, ctx: commands.Context, *, description: typing.Optional[str] = None
    ) -> None:
        """Edit guild description."""
        guild = ctx.guild
        try:
            await guild.edit(
                description=description,
                reason=f"{ctx.author} ({ctx.author.id}) has edited the guild {guild.name} ({guild.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @editguild.command(name="community")
    async def editguild_community(self, ctx: commands.Context, community: bool) -> None:
        """Edit guild community state."""
        guild = ctx.guild
        try:
            await guild.edit(
                community=community,
                reason=f"{ctx.author} ({ctx.author.id}) has edited the guild {guild.name} ({guild.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @editguild.command(name="afkchannel")
    async def editguild_afk_channel(
        self, ctx: commands.Context, *, afk_channel: typing.Optional[discord.VoiceChannel] = None
    ) -> None:
        """Edit guild afkchannel."""
        guild = ctx.guild
        try:
            await guild.edit(
                afk_channel=afk_channel,
                reason=f"{ctx.author} ({ctx.author.id}) has edited the guild {guild.name} ({guild.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @editguild.command(name="afktimeout")
    async def editguild_afk_timeout(self, ctx: commands.Context, afk_timeout: int) -> None:
        """Edit guild afktimeout."""
        guild = ctx.guild
        try:
            await guild.edit(
                afk_timeout=afk_timeout,
                reason=f"{ctx.author} ({ctx.author.id}) has edited the guild {guild.name} ({guild.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @commands.is_owner()
    @editguild.command(name="owner")
    async def editguild_owner(
        self,
        ctx: commands.Context,
        owner: discord.Member,
        confirmation: bool = False,
    ) -> None:
        """Edit guild owner (if the bot is bot owner)."""
        guild = ctx.guild
        if not confirmation and not ctx.assume_yes:
            if ctx.bot_permissions.embed_links:
                embed: discord.Embed = discord.Embed()
                embed.title = _(":⚠️ - Change Guild Owner")
                embed.description = _(
                    "Do you really want to change guild owner of the guild {guild.name} ({guild.id})?"
                ).format(guild=guild)
                embed.color = 0xF00020
                content = ctx.author.mention
            else:
                embed = None
                content = f"{ctx.author.mention} " + _(
                    "Do you really want to change guild owner of the guild {guild.name} ({guild.id})?"
                ).format(guild=guild)
            if not await CogsUtils.ConfirmationAsk(
                ctx, content=content, embed=embed
            ):
                await CogsUtils.delete_message(ctx.message)
                return
        try:
            await guild.edit(
                owner=owner,
                reason=f"{ctx.author} ({ctx.author.id}) has edited the guild {guild.name} ({guild.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @editguild.command(name="verificationlevel")
    async def editguild_verification_level(
        self, ctx: commands.Context, verification_level: discord.VerificationLevel
    ) -> None:
        """Edit guild verification level."""
        guild = ctx.guild
        try:
            await guild.edit(
                verification_level=verification_level,
                reason=f"{ctx.author} ({ctx.author.id}) has edited the guild {guild.name} ({guild.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @editguild.command(name="defaultnotifications", aliases=["notificationslevel"])
    async def editguild_default_notifications(
        self, ctx: commands.Context, default_notifications: typing.Literal["0", "1"]
    ) -> None:
        """Edit guild notification level."""
        guild = ctx.guild
        default_notifications = discord.NotificationLevel(int(default_notifications))
        try:
            await guild.edit(
                default_notifications=default_notifications,
                reason=f"{ctx.author} ({ctx.author.id}) has edited the guild {guild.name} ({guild.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @editguild.command(name="explicitcontentfilter")
    async def editguild_explicit_content_filter(
        self, ctx: commands.Context, explicit_content_filter: discord.ContentFilter
    ) -> None:
        """Edit guild explicit content filter."""
        guild = ctx.guild
        try:
            await guild.edit(
                explicit_content_filter=explicit_content_filter,
                reason=f"{ctx.author} ({ctx.author.id}) has edited the guild {guild.name} ({guild.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @editguild.command(name="vanitycode")
    async def editguild_vanity_code(self, ctx: commands.Context, vanity_code: str) -> None:
        """Edit guild vanity code."""
        guild = ctx.guild
        try:
            await guild.edit(
                vanity_code=vanity_code,
                reason=f"{ctx.author} ({ctx.author.id}) has edited the guild {guild.name} ({guild.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @editguild.command(name="systemchannel")
    async def editguild_system_channel(
        self, ctx: commands.Context, system_channel: typing.Optional[discord.TextChannel] = None
    ) -> None:
        """Edit guild system channel."""
        guild = ctx.guild
        try:
            await guild.edit(
                system_channel=system_channel,
                reason=f"{ctx.author} ({ctx.author.id}) has edited the guild {guild.name} ({guild.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @editguild.command(name="systemchannelflags")
    async def editguild_system_channel_flags(
        self, ctx: commands.Context, system_channel_flags: int
    ) -> None:
        """Edit guild system channel flags."""
        guild = ctx.guild
        _system_channel_flags = discord.SystemChannelFlags()
        _system_channel_flags.value = system_channel_flags
        try:
            await guild.edit(
                system_channel_flags=_system_channel_flags,
                reason=f"{ctx.author} ({ctx.author.id}) has edited the guild {guild.name} ({guild.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @editguild.command(name="preferredlocale")
    async def editguild_preferred_locale(
        self, ctx: commands.Context, preferred_locale: LocaleConverter
    ) -> None:
        """Edit guild preferred locale.

        american_english = 'en-US'
        british_english = 'en-GB'
        bulgarian = 'bg'
        chinese = 'zh-CN'
        taiwan_chinese = 'zh-TW'
        croatian = 'hr'
        czech = 'cs'
        danish = 'da'
        dutch = 'nl'
        finnish = 'fi'
        french = 'fr'
        german = 'de'
        greek = 'el'
        hindi = 'hi'
        hungarian = 'hu'
        italian = 'it'
        japanese = 'ja'
        korean = 'ko'
        lithuanian = 'lt'
        norwegian = 'no'
        polish = 'pl'
        brazil_portuguese = 'pt-BR'
        romanian = 'ro'
        russian = 'ru'
        spain_spanish = 'es-ES'
        swedish = 'sv-SE'
        thai = 'th'
        turkish = 'tr'
        ukrainian = 'uk'
        vietnamese = 'vi'
        """
        guild = ctx.guild
        try:
            await guild.edit(
                preferred_locale=preferred_locale,
                reason=f"{ctx.author} ({ctx.author.id}) has edited the guild {guild.name} ({guild.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @editguild.command(name="ruleschannel")
    async def editguild_rules_channel(
        self, ctx: commands.Context, rules_channel: typing.Optional[discord.TextChannel] = None
    ) -> None:
        """Edit guild rules channel."""
        guild = ctx.guild
        try:
            await guild.edit(
                rules_channel=rules_channel,
                reason=f"{ctx.author} ({ctx.author.id}) has edited the guild {guild.name} ({guild.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @editguild.command(name="publicupdateschannel")
    async def editguild_public_updates_channel(
        self,
        ctx: commands.Context,
        public_updates_channel: typing.Optional[discord.TextChannel] = None,
    ) -> None:
        """Edit guild public updates channel."""
        guild = ctx.guild
        try:
            await guild.edit(
                public_updates_channel=public_updates_channel,
                reason=f"{ctx.author} ({ctx.author.id}) has edited the guild {guild.name} ({guild.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @editguild.command(name="premiumprogressbarenabled")
    async def editguild_premium_progress_bar_enabled(
        self, ctx: commands.Context, premium_progress_bar_enabled: bool = None
    ) -> None:
        """Edit guild premium progress bar enabled."""
        guild = ctx.guild
        if premium_progress_bar_enabled is None:
            premium_progress_bar_enabled = not guild.premium_progress_bar_enabled
        try:
            await guild.edit(
                premium_progress_bar_enabled=premium_progress_bar_enabled,
                reason=f"{ctx.author} ({ctx.author.id}) has edited the guild {guild.name} ({guild.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @editguild.command(name="discoverable")
    async def editguild_discoverable(self, ctx: commands.Context, discoverable: bool) -> None:
        """Edit guild discoverable state."""
        guild = ctx.guild
        try:
            await guild.edit(
                discoverable=discoverable,
                reason=f"{ctx.author} ({ctx.author.id}) has edited the guild {guild.name} ({guild.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @editguild.command(name="invitesdisabled")
    async def editguild_invites_disabled(
        self, ctx: commands.Context, invites_disabled: bool
    ) -> None:
        """Edit guild invites disabled state."""
        guild = ctx.guild
        try:
            await guild.edit(
                invites_disabled=invites_disabled,
                reason=f"{ctx.author} ({ctx.author.id}) has edited the guild {guild.name} ({guild.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @editguild.command(name="widgetenabled", with_app_command=False)
    async def editguild_widget_enabled(
        self, ctx: commands.Context, widget_enabled: bool
    ) -> None:
        """Edit guild invites widget enabled state."""
        guild = ctx.guild
        try:
            await guild.edit(
                widget_enabled=widget_enabled,
                reason=f"{ctx.author} ({ctx.author.id}) has edited the guild {guild.name} ({guild.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @editguild.command(name="widgetchannel", with_app_command=False)
    async def editguild_widget_channel(
        self, ctx: commands.Context, widget_channel: discord.abc.GuildChannel = None
    ) -> None:
        """Edit guild invites widget channel."""
        guild = ctx.guild
        try:
            await guild.edit(
                widget_channel=widget_channel,
                reason=f"{ctx.author} ({ctx.author.id}) has edited the guild {guild.name} ({guild.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @editguild.command(name="raidalertsdisabled", with_app_command=False)
    async def editguild_raid_alerts_disabled(
        self, ctx: commands.Context, raid_alerts_disabled: bool
    ) -> None:
        """Edit guild invites raid alerts disabled state."""
        guild = ctx.guild
        try:
            await guild.edit(
                raid_alerts_disabled=raid_alerts_disabled,
                reason=f"{ctx.author} ({ctx.author.id}) has edited the guild {guild.name} ({guild.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @editguild.command(name="safetyalertschannel", with_app_command=False)
    async def editguild_safety_alerts_channel(
        self, ctx: commands.Context, safety_alerts_channel: discord.TextChannel = None
    ) -> None:
        """Edit guild invites safety alerts channel."""
        guild = ctx.guild
        try:
            await guild.edit(
                safety_alerts_channel=safety_alerts_channel,
                reason=f"{ctx.author} ({ctx.author.id}) has edited the guild {guild.name} ({guild.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @commands.is_owner()
    @editguild.command(name="delete")
    async def editguild_delete(
        self,
        ctx: commands.Context,
        confirmation: bool = False,
    ) -> None:
        """Delete guild (if the bot is owner)."""
        guild = ctx.guild
        if not confirmation and not ctx.assume_yes:
            if ctx.bot_permissions.embed_links:
                embed: discord.Embed = discord.Embed()
                embed.title = _("⚠️ - Delete Guild")
                embed.description = _(
                    "Do you really want to delete the guild {guild.name} ({guild.id})?"
                ).format(guild=guild)
                embed.color = 0xF00020
                content = ctx.author.mention
            else:
                embed = None
                content = f"{ctx.author.mention} " + _(
                    "Do you really want to delete the guild {guild.name} ({guild.id})?"
                ).format(guild=guild)
            if not await CogsUtils.ConfirmationAsk(
                ctx, content=content, embed=embed
            ):
                await CogsUtils.delete_message(ctx.message)
                return
        try:
            await guild.delete()
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @editguild.command(name="view")
    async def editguild_view(
        self,
        ctx: commands.Context,
    ) -> None:
        """View and edit guild."""
        guild = ctx.guild
        embed_color = await ctx.embed_color()

        parameters = {
            "name": {"converter": commands.Range[str, 2, 100]},
            "description": {"converter": str},
            "community": {"converter": bool},
            "afk_channel": {"converter": discord.VoiceChannel},
            "afk_timeout": {"converter": int},
            "verification_level": {"converter": discord.VerificationLevel},
            "default_notifications": {"converter": discord.NotificationLevel},
            "system_channel": {"converter": discord.TextChannel},
            "system_channel_flags": {"converter": int},
            "preferred_locale": {"converter": LocaleConverter},
            "rules_channel": {"converter": discord.TextChannel},
            "public_updates_channel": {"converter": discord.TextChannel},
            "premium_progress_bar_enabled": {"converter": bool},
            "discoverable": {"converter": bool},
            "invites_disabled": {"converter": bool},
            "widget_enabled": {"converter": bool},
            "widget_channel": {"converter": bool},
            "raid_alerts_disabled": {"converter": bool},
            "safety_alerts_channel": {"converter": discord.TextChannel},
        }
        parameters_to_split = list(parameters)
        splitted_parameters = []
        while parameters_to_split != []:
            li = parameters_to_split[:5]
            parameters_to_split = parameters_to_split[5:]
            splitted_parameters.append(li)

        def get_embed() -> discord.Embed:
            embed: discord.Embed = discord.Embed(title=f"Guild {guild.name} ({guild.id})", color=embed_color)
            embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
            embed.description = "\n".join([f"• `{parameter}`: {repr(getattr(guild, parameters[parameter].get('attribute_name', parameter)))}" for parameter in parameters if hasattr(guild, parameter)])
            return embed

        async def button_edit_guild(interaction: discord.Interaction, button_index: int) -> None:
            modal: discord.ui.Modal = discord.ui.Modal(title="Edit Guild")
            modal.on_submit = lambda interaction: interaction.response.defer()
            text_inputs: typing.Dict[str, discord.ui.TextInput] = {}
            for parameter in splitted_parameters[button_index]:
                text_input = discord.ui.TextInput(
                    label=parameter.replace("_", " ").title(),
                    style=discord.TextStyle.short,
                    placeholder=repr(parameters[parameter]["converter"]),
                    default=str(attribute) if (attribute := getattr(guild, parameters[parameter].get("attribute_name", parameter), None)) is not None else None,
                    required=False,
                )
                text_inputs[parameter] = text_input
                modal.add_item(text_input)
            await interaction.response.send_modal(modal)
            if await modal.wait():
                return  # Timeout.
            kwargs = {}
            for parameter in text_inputs:
                if not text_inputs[parameter].value:
                    if parameters[parameter]["converter"] is bool:
                        continue
                    kwargs[parameter] = None
                    continue
                if text_inputs[parameter].value == str(text_inputs[parameter].default):
                    continue
                try:
                    value = await discord.ext.commands.converter.run_converters(
                        ctx,
                        converter=parameters[parameter]["converter"],
                        argument=text_inputs[parameter].value,
                        param=discord.ext.commands.parameters.Parameter(
                            name=parameter,
                            kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                            annotation=parameters[parameter]["converter"],
                        ),
                    )
                except discord.ext.commands.errors.CommandError as e:
                    await ctx.send(
                        f"An error occurred when using the `{parameter}`"
                        f" converter:\n{box(e, lang='py')}"
                    )
                    return None
                else:
                    if parameter == "default_notifications":
                        value = int(value)
                    elif parameter == "system_channel_flags":
                        _system_channel_flags = discord.SystemChannelFlags()
                        _system_channel_flags.value = value
                        value = _system_channel_flags
                    elif parameter == "video_quality_mode":
                        value = int(value)
                    kwargs[parameter] = value
            try:
                await guild.edit(
                    **kwargs,
                    reason=f"{ctx.author} ({ctx.author.id}) has edited the guild {guild.name} ({guild.id}).",
                )
            except discord.HTTPException as e:
                raise commands.UserFeedbackCheckFailure(
                    _(ERROR_MESSAGE).format(error=box(e, lang="py"))
                )
            else:
                try:
                    await interaction.message.edit(embed=get_embed())
                except discord.HTTPException:
                    pass

        view: discord.ui.View = discord.ui.View()

        async def interaction_check(interaction: discord.Interaction) -> bool:
            if interaction.user.id not in [ctx.author.id] + list(ctx.bot.owner_ids):
                await interaction.response.send_message(
                    "You are not allowed to use this interaction.", ephemeral=True
                )
                return False
            return True

        view.interaction_check = interaction_check

        for button_index in range(len(splitted_parameters)):
            button = discord.ui.Button(label=f"Edit Guild {button_index + 1}"if len(splitted_parameters) > 1 else "Edit Guild", style=discord.ButtonStyle.secondary)
            button.callback = functools.partial(button_edit_guild, button_index=button_index)
            view.add_item(button)

        async def delete_button_callback(interaction: discord.Interaction) -> None:
            await interaction.response.defer()
            ctx = await CogsUtils.invoke_command(
                bot=interaction.client,
                author=interaction.user,
                channel=interaction.channel,
                command="editguild delete",
            )
            if not await discord.utils.async_all(
                check(ctx) for check in ctx.command.checks
            ):
                await interaction.followup.send(
                    _("You are not allowed to execute this command."), ephemeral=True
                )
                return
        delete_button = discord.ui.Button(label="Delete Guild", style=discord.ButtonStyle.danger)
        delete_button.callback = delete_button_callback
        view.add_item(delete_button)

        message = await ctx.send(embed=get_embed(), view=view)

        async def on_timeout() -> None:
            for child in view.children:
                child: discord.ui.Item
                if hasattr(child, "disabled") and not (
                    isinstance(child, discord.ui.Button) and child.style == discord.ButtonStyle.url
                ):
                    child.disabled = True
            try:
                await message.edit(view=view)
            except discord.HTTPException:
                pass

        view.on_timeout = on_timeout

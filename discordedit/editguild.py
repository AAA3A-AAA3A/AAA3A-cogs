from AAA3A_utils import Cog, CogsUtils  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
from redbot.core.bot import Red  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import datetime

import aiohttp
from redbot.core.commands.converter import get_timedelta_converter
from redbot.core.utils.chat_formatting import box

from .view import DiscordEditView

TimedeltaConverter = get_timedelta_converter(
    default_unit="s",
    maximum=datetime.timedelta(seconds=21600),
    minimum=datetime.timedelta(seconds=0),
)


def _(untranslated: str) -> str:  # `redgettext` will found these strings.
    return untranslated


ERROR_MESSAGE = _(
    "I attempted to do something that Discord denied me permissions for. Your command failed to successfully complete.\n{error}"
)

_ = Translator("DiscordEdit", __file__)


class UrlConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str):
        if argument.startswith("<") and argument.endswith(">"):
            argument = argument[1:-1]
        return argument


class LocaleConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str):
        try:
            return discord.Locale(argument)
        except ValueError:
            raise commands.BadArgument(
                _("Converting to `Locale` failed for parameter `preferred_locale`.")
            )


class VerificationLevelConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> int:
        if argument.lower() in discord.VerificationLevel._enum_member_names_:
            return getattr(discord.VerificationLevel, argument.lower())
        try:
            verification_level = int(argument)
        except ValueError:
            raise commands.BadArgument(
                _(
                    "The verification level must be `none`, `low`, `medium`, `high`, `highest`, `0`, `1`, `2`, `3` or `4`."
                )
            )
        if verification_level in {0, 1, 2, 3, 4}:
            return discord.VerificationLevel(verification_level)
        else:
            raise commands.BadArgument(
                _(
                    "The verification level must be `none`, `low`, `medium`, `high`, `highest`, `0`, `1`, `2`, `3` or `4`."
                )
            )


class DefaultNotificationsConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> int:
        try:
            notifications_level = int(argument)
        except ValueError:
            raise commands.BadArgument(_("The video quality mode must be `0` or `1`."))
        if notifications_level in {0, 1}:
            return discord.NotificationLevel(notifications_level)
        else:
            raise commands.BadArgument(_("The video quality mode must be `0` or `1`."))


class SystemChannelFlagsConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> int:
        try:
            _system_channel_flags = int(argument)
        except ValueError:
            raise commands.BadArgument(_("The video quality mode must be `0` or `1`."))
        system_channel_flags = discord.SystemChannelFlags()
        system_channel_flags.value = _system_channel_flags
        return system_channel_flags


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
    @editguild.command(name="create", aliases=["new", "+"])
    async def editguild_create(
        self,
        ctx: commands.Context,
        name: commands.Range[str, 2, 100],
        template_code: typing.Optional[str] = None,
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
    async def editguild_name(
        self, ctx: commands.Context, *, name: commands.Range[str, 2, 100]
    ) -> None:
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

    @editguild.command(name="icon")
    async def editguild_icon(
        self,
        ctx: commands.Context,
        icon: UrlConverter = None,
    ) -> None:
        """Edit guild icon.

        You can use an URL or upload an attachment.
        """
        guild = ctx.guild
        if len(ctx.message.attachments) > 0:
            icon = await ctx.message.attachments[0].read()  # Read an optional attachment.
        elif icon is not None:
            url = icon
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(url) as r:
                        icon = await r.read()  # Get URL data.
                except aiohttp.InvalidURL:
                    return await ctx.send("That URL is invalid.")
                except aiohttp.ClientError:
                    return await ctx.send("Something went wrong while trying to get the image.")
        # else:
        #     raise commands.UserInputError()  # Send the command help if no attachment and no URL.
        try:
            await guild.edit(
                icon=icon,
                reason=f"{ctx.author} ({ctx.author.id}) has edited the guild {guild.name} ({guild.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @editguild.command(name="banner")
    async def editguild_banner(
        self,
        ctx: commands.Context,
        banner: UrlConverter = None,
    ) -> None:
        """Edit guild banner.

        You can use an URL or upload an attachment.
        """
        guild = ctx.guild
        if "BANNER" not in ctx.guild.features:
            raise commands.UserFeedbackCheckFailure(
                _(
                    "This server doesn't have the `BANNER` feature. This server needs more boosts to perform this action."
                )
            )
        if len(ctx.message.attachments) > 0:
            banner = await ctx.message.attachments[0].read()  # Read an optional attachment.
        elif banner is not None:
            url = banner
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(url) as r:
                        banner = await r.read()  # Get URL data.
                except aiohttp.InvalidURL:
                    return await ctx.send("That URL is invalid.")
                except aiohttp.ClientError:
                    return await ctx.send("Something went wrong while trying to get the image.")
        # else:
        #     raise commands.UserInputError()  # Send the command help if no attachment and no URL.
        try:
            await guild.edit(
                banner=banner,
                reason=f"{ctx.author} ({ctx.author.id}) has edited the guild {guild.name} ({guild.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @editguild.command(name="splash", aliases=["invite_splash"])
    async def editguild_splash(
        self,
        ctx: commands.Context,
        splash: UrlConverter = None,
    ) -> None:
        """Edit guild splash.

        You can use an URL or upload an attachment.
        """
        guild = ctx.guild
        if "INVITE_SPLASH" not in ctx.guild.features:
            raise commands.UserFeedbackCheckFailure(
                _(
                    "This server doesn't have the `INVITE_SPLASH` feature. This server needs more boosts to perform this action."
                )
            )
        if len(ctx.message.attachments) > 0:
            splash = await ctx.message.attachments[0].read()  # Read an optional attachment.
        elif splash is not None:
            url = splash
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(url) as r:
                        splash = await r.read()  # Get URL data.
                except aiohttp.InvalidURL:
                    return await ctx.send("That URL is invalid.")
                except aiohttp.ClientError:
                    return await ctx.send("Something went wrong while trying to get the image.")
        # else:
        #     raise commands.UserInputError()  # Send the command help if no attachment and no URL.
        try:
            await guild.edit(
                splash=splash,
                reason=f"{ctx.author} ({ctx.author.id}) has edited the guild {guild.name} ({guild.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @editguild.command(name="discoverysplash", aliases=["discovery_splash"])
    async def editguild_discovery_splash(
        self,
        ctx: commands.Context,
        discovery_splash: UrlConverter = None,
    ) -> None:
        """Edit guild discovery splash.

        You can use an URL or upload an attachment.
        """
        guild = ctx.guild
        if "DISCOVERABLE" not in ctx.guild.features:
            raise commands.UserFeedbackCheckFailure(
                _(
                    "This server doesn't have the `DISCOVERABLE` feature. This server needs more boosts to perform this action."
                )
            )
        if len(ctx.message.attachments) > 0:
            discovery_splash = await ctx.message.attachments[
                0
            ].read()  # Read an optional attachment.
        elif discovery_splash is not None:
            url = discovery_splash
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(url) as r:
                        discovery_splash = await r.read()  # Get URL data.
                except aiohttp.InvalidURL:
                    return await ctx.send("That URL is invalid.")
                except aiohttp.ClientError:
                    return await ctx.send("Something went wrong while trying to get the image.")
        # else:
        #     raise commands.UserInputError()  # Send the command help if no attachment and no URL.
        try:
            await guild.edit(
                discovery_splash=discovery_splash,
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

    @editguild.command(name="afkchannel", aliases=["afk_channel"])
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

    @editguild.command(name="afktimeout", aliases=["afk_timeout"])
    async def editguild_afk_timeout(self, ctx: commands.Context, afk_timeout: int) -> None:
        """Edit guild afk timeout."""
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
            if not await CogsUtils.ConfirmationAsk(ctx, content=content, embed=embed):
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

    @editguild.command(name="verificationlevel", aliases=["verification_level"])
    async def editguild_verification_level(
        self, ctx: commands.Context, verification_level: VerificationLevelConverter
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

    @editguild.command(
        name="defaultnotifications", aliases=["notificationslevel", "default_notifications"]
    )
    async def editguild_default_notifications(
        self, ctx: commands.Context, default_notifications: DefaultNotificationsConverter
    ) -> None:
        """Edit guild notification level."""
        guild = ctx.guild
        try:
            await guild.edit(
                default_notifications=default_notifications,
                reason=f"{ctx.author} ({ctx.author.id}) has edited the guild {guild.name} ({guild.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @editguild.command(name="explicitcontentfilter", aliases=["explicit_content_filter"])
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

    @editguild.command(name="vanitycode", aliases=["vanity_code"])
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

    @editguild.command(name="systemchannel", aliases=["system_channel"])
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

    @editguild.command(name="systemchannelflags", aliases=["system_channel_flags"])
    async def editguild_system_channel_flags(
        self, ctx: commands.Context, system_channel_flags: SystemChannelFlagsConverter
    ) -> None:
        """Edit guild system channel flags."""
        guild = ctx.guild
        try:
            await guild.edit(
                system_channel_flags=system_channel_flags,
                reason=f"{ctx.author} ({ctx.author.id}) has edited the guild {guild.name} ({guild.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @editguild.command(name="preferredlocale", aliases=["preferred_locale"])
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

    @editguild.command(name="ruleschannel", aliases=["rules_channel"])
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

    @editguild.command(name="publicupdateschannel", aliases=["public_updates_channel"])
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

    @editguild.command(
        name="premiumprogressbarenabled",
        aliases=["premium_progress_bar_enabled"],
        with_app_command=False,
    )
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

    @editguild.command(name="invitesdisabled", aliases=["invites_disabled"])
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

    @editguild.command(name="widgetenabled", aliases=["widget_enabled"], with_app_command=False)
    async def editguild_widget_enabled(self, ctx: commands.Context, widget_enabled: bool) -> None:
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

    @editguild.command(name="widgetchannel", aliases=["widget_channel"], with_app_command=False)
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

    @editguild.command(
        name="raidalertsdisabled", aliases=["raid_alerts_disabled"], with_app_command=False
    )
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

    @editguild.command(
        name="safetyalertschannel", aliases=["safety_alerts_channel"], with_app_command=False
    )
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
    @editguild.command(name="delete", aliases=["-"])
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
            if not await CogsUtils.ConfirmationAsk(ctx, content=content, embed=embed):
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
            "verification_level": {"converter": VerificationLevelConverter},
            "default_notifications": {"converter": DefaultNotificationsConverter},
            "system_channel": {"converter": discord.TextChannel},
            "system_channel_flags": {"converter": SystemChannelFlagsConverter},
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

        def get_embed() -> discord.Embed:
            embed: discord.Embed = discord.Embed(
                title=f"Guild {guild.name} ({guild.id})", color=embed_color
            )
            embed.timestamp = datetime.datetime.now(tz=datetime.timezone.utc)
            embed.description = "\n".join(
                [
                    f"• `{parameter}`: {repr(getattr(guild, parameters[parameter].get('attribute_name', parameter)))}"
                    for parameter in parameters
                    if hasattr(guild, parameter)
                ]
            )
            return embed

        await DiscordEditView(
            cog=self,
            _object=guild,
            parameters=parameters,
            get_embed_function=get_embed,
            audit_log_reason=f"{ctx.author} ({ctx.author.id}) has edited the guild {guild.name} ({guild.id}).",
            _object_qualified_name="Guild",
        ).start(ctx)

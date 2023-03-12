from .AAA3A_utils import CogsUtils  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
from redbot.core.bot import Red  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import datetime

from redbot.core.commands.converter import get_timedelta_converter
from redbot.core.utils.chat_formatting import box

TimedeltaConverter = get_timedelta_converter(
    default_unit="s",
    maximum=datetime.timedelta(seconds=21600),
    minimum=datetime.timedelta(seconds=0),
)

if CogsUtils().is_dpy2:  # To remove
    setattr(commands, "Literal", typing.Literal)

_ = Translator("DiscordEdit", __file__)

if CogsUtils().is_dpy2:
    from functools import partial

    hybrid_command = partial(commands.hybrid_command, with_app_command=False)
    hybrid_group = partial(commands.hybrid_group, with_app_command=False)
else:
    hybrid_command = commands.command
    hybrid_group = commands.group

ERROR_MESSAGE = "I attempted to do something that Discord denied me permissions for. Your command failed to successfully complete.\n{error}"


@cog_i18n(_)
class EditGuild(commands.Cog):
    """A cog to edit guilds!"""

    def __init__(self, bot: Red) -> None:  # Never executed except manually.
        self.bot: Red = bot

        self.cogsutils: CogsUtils = CogsUtils(cog=self)

    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    @commands.bot_has_guild_permissions(manage_guild=True)
    @hybrid_group()
    async def editguild(self, ctx: commands.Context) -> None:
        """Commands for edit a guild."""
        pass

    @commands.is_owner()
    @editguild.command(name="create")
    async def editguild_create(
        self, ctx: commands.Context, name: str, template_code: typing.Optional[str] = None
    ) -> None:
        """Create a guild with the bot as owner."""
        try:
            guild = await ctx.bot.create_guild(name=name, code=template_code)
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )
        channel = next(
            (c for c in guild.channels if c.type == discord.ChannelType.text), None
        )
        if channel is None:
            channel = await guild.create_text_channel(name="general")
        invite_url = (await channel.create_invite()).url
        await ctx.send(f"**Guild name:** {guild.name}\n**Guild ID:** {guild.id}\n**First channel's ID**: {channel.id}\n**Invite URL:** {invite_url}")

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
        channel = next(
            (c for c in guild.channels if c.type == discord.ChannelType.text), None
        )
        if channel is None:
            channel = await guild.create_text_channel(name="general")
        invite_url = (await channel.create_invite()).url
        await ctx.send(f"**Guild name:** {guild.name}\n**Guild ID:** {guild.id}\n**First channel's ID**: {channel.id}\n**Invite URL:** {invite_url}")

    @editguild.command(name="name")
    async def editguild_name(self, ctx: commands.Context, *, name: str) -> None:
        """Edit guild name."""
        guild = ctx.guild
        try:
            await guild.edit(
                name=name,
                reason=f"{ctx.author} ({ctx.author.id}) has modified the guild #{guild.name} ({guild.id}).",
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
                reason=f"{ctx.author} ({ctx.author.id}) has modified the guild #{guild.name} ({guild.id}).",
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
                reason=f"{ctx.author} ({ctx.author.id}) has modified the guild #{guild.name} ({guild.id}).",
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
                reason=f"{ctx.author} ({ctx.author.id}) has modified the guild #{guild.name} ({guild.id}).",
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
                reason=f"{ctx.author} ({ctx.author.id}) has modified the guild #{guild.name} ({guild.id}).",
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
        confirmation: typing.Optional[bool] = False,
    ) -> None:
        """Edit guild owner (if the bot is bot owner)."""
        guild = ctx.guild
        if not confirmation:
            embed: discord.Embed = discord.Embed()
            embed.title = _(":⚠️ - Change Guild Owner")
            embed.description = _(
                "Do you really want to change guild owner of the guild {guild.name} ({guild.id})?"
            ).format(guild=guild)
            embed.color = 0xF00020
            if not await self.cogsutils.ConfirmationAsk(
                ctx, content=f"{ctx.author.mention}", embed=embed
            ):
                await self.cogsutils.delete_message(ctx.message)
                return
        try:
            await guild.edit(
                owner=owner,
                reason=f"{ctx.author} ({ctx.author.id}) has modified the guild #{guild.name} ({guild.id}).",
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
                reason=f"{ctx.author} ({ctx.author.id}) has modified the guild #{guild.name} ({guild.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @editguild.command(name="defaultnotifications", aliases=["notificationslevel"])
    async def editguild_default_notifications(
        self, ctx: commands.Context, default_notifications: commands.Literal["0", "1"]
    ) -> None:
        """Edit guild notification level."""
        guild = ctx.guild
        default_notifications = discord.NotificationLevel(int(default_notifications))
        try:
            await guild.edit(
                default_notifications=default_notifications,
                reason=f"{ctx.author} ({ctx.author.id}) has modified the guild #{guild.name} ({guild.id}).",
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
                reason=f"{ctx.author} ({ctx.author.id}) has modified the guild #{guild.name} ({guild.id}).",
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
                reason=f"{ctx.author} ({ctx.author.id}) has modified the guild #{guild.name} ({guild.id}).",
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
                reason=f"{ctx.author} ({ctx.author.id}) has modified the guild #{guild.name} ({guild.id}).",
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
                reason=f"{ctx.author} ({ctx.author.id}) has modified the guild #{guild.name} ({guild.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    class LocaleConverter(commands.Converter):
        async def convert(self, ctx: commands.Context, argument: str):
            try:
                return discord.Locale(argument)
            except ValueError:
                raise commands.BadArgument(
                    _("Converting to `Locale` failed for parameter `preferred_locale`.")
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
                reason=f"{ctx.author} ({ctx.author.id}) has modified the guild #{guild.name} ({guild.id}).",
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
                reason=f"{ctx.author} ({ctx.author.id}) has modified the guild #{guild.name} ({guild.id}).",
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
                reason=f"{ctx.author} ({ctx.author.id}) has modified the guild #{guild.name} ({guild.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @editguild.command(name="premiumprogressbarenabled")
    async def editguild_premium_progress_bar_enabled(
        self, ctx: commands.Context, premium_progress_bar_enabled: bool
    ) -> None:
        """Edit guild premium progress bar enabled."""
        guild = ctx.guild
        try:
            await guild.edit(
                premium_progress_bar_enabled=premium_progress_bar_enabled,
                reason=f"{ctx.author} ({ctx.author.id}) has modified the guild #{guild.name} ({guild.id}).",
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
                reason=f"{ctx.author} ({ctx.author.id}) has modified the guild #{guild.name} ({guild.id}).",
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
                reason=f"{ctx.author} ({ctx.author.id}) has modified the guild #{guild.name} ({guild.id}).",
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
        confirmation: typing.Optional[bool] = False,
    ) -> None:
        """Delete guild (if the bot is owner)."""
        guild = ctx.guild
        if not confirmation:
            embed: discord.Embed = discord.Embed()
            embed.title = _("⚠️ - Delete Guild")
            embed.description = _(
                "Do you really want to delete the guild {guild.name} ({guild.id})?"
            ).format(guild=guild)
            embed.color = 0xF00020
            if not await self.cogsutils.ConfirmationAsk(
                ctx, content=f"{ctx.author.mention}", embed=embed
            ):
                await self.cogsutils.delete_message(ctx.message)
                return
        try:
            await guild.delete()
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

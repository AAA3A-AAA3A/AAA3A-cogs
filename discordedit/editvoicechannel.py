from AAA3A_utils import Cog, CogsUtils, Menu  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
from redbot.core.bot import Red  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import datetime
from copy import copy

from redbot.core.commands.converter import get_timedelta_converter
from redbot.core.utils.chat_formatting import box, pagify

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


class PositionConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> int:
        try:
            position = int(argument)
        except ValueError:
            raise commands.BadArgument("The position must be an integer.")
        max_guild_text_channels_position = len(
            [c for c in ctx.guild.channels if isinstance(c, discord.TextChannel)]
        )
        if position <= 0 or position >= max_guild_text_channels_position + 1:
            raise commands.BadArgument(
                f"The indicated position must be between 1 and {max_guild_text_channels_position}."
            )
        position -= 1
        return position


class PermissionConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> str:
        permissions = [
            key for key, value in dict(discord.Permissions.all_channel()).items() if value
        ]
        if argument not in permissions:
            raise commands.BadArgument(_("This permission is invalid."))
        return argument


class VideoQualityModeConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> int:
        try:
            video_quality_mode = int(argument)
        except ValueError:
            raise commands.BadArgument(_("The video quality mode must be `1` or `2`."))
        if video_quality_mode in {1, 2}:
            return discord.VideoQualityMode(video_quality_mode)
        else:
            raise commands.BadArgument(_("The video quality mode must be `1` or `2`."))


@cog_i18n(_)
class EditVoiceChannel(Cog):
    """A cog to edit voice channels!"""

    def __init__(self, bot: Red) -> None:  # Never executed except manually.
        super().__init__(bot=bot)

    async def check_voice_channel(
        self, ctx: commands.Context, channel: discord.VoiceChannel
    ) -> bool:
        # if (
        #     not channel.permissions_for(ctx.author).manage_channels
        #     and ctx.author.id != ctx.guild.owner.id
        #     and ctx.author.id not in ctx.bot.owner_ids
        # ):
        #     raise commands.UserFeedbackCheckFailure(
        #         _(
        #             "I can not let you edit the voice channel {channel.mention} ({channel.id}) because you don't have the `manage_channel` permission."
        #         ).format(channel=channel)
        #     )
        if not channel.permissions_for(ctx.me).manage_channels:
            raise commands.UserFeedbackCheckFailure(
                _(
                    "I can not edit the voice channel {channel.mention} ({channel.id}) because I don't have the `manage_channel` permission."
                ).format(channel=channel)
            )
        return True

    @commands.guild_only()
    @commands.admin_or_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    @commands.hybrid_group(aliases=["editvoiceroom"])
    async def editvoicechannel(self, ctx: commands.Context) -> None:
        """Commands for edit a voice channel."""
        pass

    @editvoicechannel.command(name="create", aliases=["new", "+"])
    async def editvoicechannel_create(
        self,
        ctx: commands.Context,
        category: typing.Optional[discord.CategoryChannel] = None,
        *,
        name: commands.Range[str, 1, 100],
    ) -> None:
        """Create a voice channel."""
        try:
            await ctx.guild.create_voice_channel(
                name=name,
                category=category,
                reason=f"{ctx.author} ({ctx.author.id}) has edited the voice channel #!{name}.",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @commands.bot_has_permissions(embed_links=True)
    @editvoicechannel.command(name="list")
    async def editvoicechannel_list(
        self,
        ctx: commands.Context,
    ) -> None:
        """List all voice channels in the current guild."""
        description = "".join(
            f"\n**•** **{channel.position + 1}** - {channel.mention} - #!{channel.name} ({channel.id}) - {len(channel.members)} members"
            for channel in sorted(ctx.guild.voice_channels, key=lambda x: x.position)
        )
        embed: discord.Embed = discord.Embed(color=await ctx.embed_color())
        embed.title = _("List of voice channels in {guild.name} ({guild.id})").format(
            guild=ctx.guild
        )
        embeds = []
        pages = pagify(description, page_length=4096)
        for page in pages:
            e = embed.copy()
            e.description = page
            embeds.append(e)
        await Menu(pages=embeds).start(ctx)

    @editvoicechannel.command(name="clone")
    async def editvoicechannel_clone(
        self,
        ctx: commands.Context,
        channel: discord.VoiceChannel,
        *,
        name: commands.Range[str, 1, 100],
    ) -> None:
        """Clone a voice channel."""
        await self.check_voice_channel(ctx, channel)
        try:
            await channel.clone(
                name=name,
                reason=f"{ctx.author} ({ctx.author.id}) has cloned the voice channel #!{channel.name} ({channel.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @editvoicechannel.command(name="invite")
    async def editvoicechannel_invite(
        self,
        ctx: commands.Context,
        channel: discord.VoiceChannel,
        max_age: typing.Optional[float] = None,
        max_uses: typing.Optional[int] = None,
        temporary: typing.Optional[bool] = False,
        unique: typing.Optional[bool] = True,
    ) -> None:
        """Create an invite for a voice channel.

        `max_age`: How long the invite should last in days. If it's 0 then the invite doesn't expire.
        `max_uses`: How many uses the invite could be used for. If it's 0 then there are unlimited uses.
        `temporary`: Denotes that the invite grants temporary membership (i.e. they get kicked after they disconnect).
        `unique`: Indicates if a unique invite URL should be created. Defaults to True. If this is set to False then it will return a previously created invite.
        """
        await self.check_voice_channel(ctx, channel)
        try:
            invite = await channel.create_invite(
                max_age=(max_age or 0) * 86400,
                max_uses=max_uses,
                temporary=temporary,
                unique=unique,
                reason=f"{ctx.author} ({ctx.author.id}) has created an invite for the voice channel #{channel.name} ({channel.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )
        else:
            await ctx.send(invite.url)

    @editvoicechannel.command(name="name")
    async def editvoicechannel_name(
        self,
        ctx: commands.Context,
        channel: discord.VoiceChannel,
        name: commands.Range[str, 1, 100],
    ) -> None:
        """Edit voice channel name."""
        await self.check_voice_channel(ctx, channel)
        try:
            await channel.edit(
                name=name,
                reason=f"{ctx.author} ({ctx.author.id}) has edited the voice channel #!{channel.name} ({channel.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @editvoicechannel.command(name="bitrate")
    async def editvoicechannel_bitrate(
        self, ctx: commands.Context, channel: discord.VoiceChannel, bitrate: int
    ) -> None:
        """Edit voice channel bitrate.

        It must be a number between 8000 and
        Level 1: 128000
        Level 2: 256000
        Level 3: 384000
        """
        await self.check_voice_channel(ctx, channel)
        if bitrate < 8000 or bitrate > ctx.guild.bitrate_limit:
            raise commands.UserInputError()
        try:
            await channel.edit(
                bitrate=bitrate,
                reason=f"{ctx.author} ({ctx.author.id}) has edited the voice channel #!{channel.name} ({channel.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @editvoicechannel.command(name="nsfw")
    async def editvoicechannel_nsfw(
        self, ctx: commands.Context, channel: discord.VoiceChannel, nsfw: bool = None
    ) -> None:
        """Edit voice channel nsfw."""
        await self.check_voice_channel(ctx, channel)
        if nsfw is None:
            nsfw = not channel.nsfw
        try:
            await channel.edit(
                nsfw=nsfw,
                reason=f"{ctx.author} ({ctx.author.id}) has edited the voice channel #!{channel.name} ({channel.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @editvoicechannel.command(name="userlimit", aliases=["user_limit"])
    async def editvoicechannel_user_limit(
        self,
        ctx: commands.Context,
        channel: discord.VoiceChannel,
        user_limit: commands.Range[int, 0, 99],
    ) -> None:
        """Edit voice channel user limit.

        It must be a number between 0 and 99.
        """
        await self.check_voice_channel(ctx, channel)
        try:
            await channel.edit(
                user_limit=user_limit,
                reason=f"{ctx.author} ({ctx.author.id}) has edited the voice channel #!{channel.name} ({channel.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @editvoicechannel.command(name="position")
    async def editvoicechannel_position(
        self, ctx: commands.Context, channel: discord.VoiceChannel, *, position: PositionConverter
    ) -> None:
        """Edit voice channel position.

        Warning: Only voice channels are taken into account. Channel 1 is the highest positioned voice channel.
        Channels cannot be moved to a position that takes them out of their current category.
        """
        await self.check_voice_channel(ctx, channel)
        try:
            await channel.edit(
                position=position,
                reason=f"{ctx.author} ({ctx.author.id}) has edited the voice channel !{channel.name} ({channel.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @editvoicechannel.command(name="syncpermissions", aliases=["sync_permissions"])
    async def editvoicechannel_sync_permissions(
        self, ctx: commands.Context, channel: discord.VoiceChannel, sync_permissions: bool = None
    ) -> None:
        """Edit voice channel sync permissions."""
        await self.check_voice_channel(ctx, channel)
        if sync_permissions is None:
            sync_permissions = not channel.permissions_synced
        try:
            await channel.edit(
                sync_permissions=sync_permissions,
                reason=f"{ctx.author} ({ctx.author.id}) has edited the voice channel #!{channel.name} ({channel.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @editvoicechannel.command(name="category")
    async def editvoicechannel_category(
        self,
        ctx: commands.Context,
        channel: discord.VoiceChannel,
        category: discord.CategoryChannel,
    ) -> None:
        """Edit voice channel category."""
        await self.check_voice_channel(ctx, channel)
        try:
            await channel.edit(
                category=category,
                reason=f"{ctx.author} ({ctx.author.id}) has edited the voice channel #!{channel.name} ({channel.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @editvoicechannel.command(name="slowmodedelay", aliases=["slowmode_delay"])
    async def editvoicechannel_slowmode_delay(
        self,
        ctx: commands.Context,
        channel: discord.VoiceChannel,
        slowmode_delay: TimedeltaConverter,
    ) -> None:
        """Edit voice channel slowmode delay.

        Specifies the slowmode rate limit for user in this channel. A value of 0s disables slowmode. The maximum value possible is 21600s.
        """
        await self.check_voice_channel(ctx, channel)
        slowmode_delay = int(slowmode_delay.total_seconds())
        if slowmode_delay < 0 or slowmode_delay > 21600:
            raise commands.UserInputError()
        try:
            await channel.edit(
                slowmode_delay=slowmode_delay,
                reason=f"{ctx.author} ({ctx.author.id}) has edited the voice channel #!{channel.name} ({channel.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @editvoicechannel.command(name="videoqualitymode", aliases=["video_quality_mode"])
    async def editvoicechannel_video_quality_mode(
        self,
        ctx: commands.Context,
        channel: discord.VoiceChannel,
        video_quality_mode: VideoQualityModeConverter,
    ) -> None:
        """Edit voice channel video quality mode.

        auto = 1
        full = 2
        """
        await self.check_voice_channel(ctx, channel)
        try:
            await channel.edit(
                video_quality_mode=video_quality_mode,
                reason=f"{ctx.author} ({ctx.author.id}) has edited the voice channel #!{channel.name} ({channel.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    @editvoicechannel.command(name="overwrites", aliases=["permissions", "perms"])
    async def editvoicechannel_overwrites(
        self,
        ctx: commands.Context,
        channel: discord.VoiceChannel,
        roles_or_users: commands.Greedy[
            typing.Union[discord.Member, discord.Role, typing.Literal["everyone"]]
        ],
        true_or_false: typing.Optional[bool],
        permissions: commands.Greedy[PermissionConverter],
    ) -> None:
        """Edit voice channel overwrites/permissions.

        You may not specify `True` or `False` to reset the overwrite(s).
        You must possess the permissions you wish to modify.

        • `create_instant_invite`
        • `manage_channels`
        • `add_reactions`
        • `priority_speaker`
        • `stream`
        • `read_messages`
        • `send_messages`
        • `send_tts_messages`
        • `manage_messages`
        • `embed_links`
        • `attach_files`
        • `read_message_history`
        • `mention_everyone`
        • `external_emojis`
        • `connect`
        • `speak`
        • `mute_members`
        • `deafen_members`
        • `move_members`
        • `use_voice_activation`
        • `manage_roles`
        • `manage_webhooks`
        • `use_application_commands`
        • `request_to_speak`
        • `manage_threads`
        • `create_public_threads`
        • `create_private_threads`
        • `external_stickers`
        • `send_messages_in_threads`
        """
        await self.check_voice_channel(ctx, channel)
        targets = list(roles_or_users)
        for r in roles_or_users:
            if r == "everyone":
                targets.remove(r)
                targets.append(ctx.guild.default_role)
        if not targets:
            raise commands.UserFeedbackCheckFailure(
                _("You need to provide a role or user you want to edit permissions for.")
            )
        # for target in targets:
        #     if (
        #         ctx.author != ctx.guild.owner
        #         and (
        #             target if isinstance(target, discord.Role) else target.top_role
        #         )
        #         >= ctx.author.top_role
        #     ):
        #         raise commands.UserFeedbackCheckFailure(_("You cannot change the permissions of a role/member higher up the hierarchy than your top role."))
        #     if (target if isinstance(target, discord.Role) else target.top_role) >= ctx.me.top_role:
        #         raise commands.UserFeedbackCheckFailure(_("I cannot change the permissions of a role/member higher up the hierarchy than my top role."))
        if not permissions:
            raise commands.UserFeedbackCheckFailure(
                _("You need to provide at least one permission.")
            )
        channel_permissions = channel.permissions_for(ctx.author)
        for permission in permissions:
            if not getattr(channel_permissions, permission):
                raise commands.UserFeedbackCheckFailure(
                    _("You don't have the permission {permission_name} in this channel.").format(
                        permission_name=permission
                    )
                )
        bot_channel_permissions = channel.permissions_for(ctx.me)
        fake_channel_object = copy(channel)
        overwrites = fake_channel_object.overwrites
        for target in targets:
            if target in overwrites:
                overwrites[target].update(
                    **{permission: true_or_false for permission in permissions}
                )
            else:
                perm = discord.PermissionOverwrite(
                    **{permission: true_or_false for permission in permissions}
                )
                overwrites[target] = perm
        new_channel_permissions = fake_channel_object.permissions_for(ctx.author)
        if [
            permission
            for permission in dict(new_channel_permissions)
            if getattr(channel_permissions, permission) is True
            and getattr(new_channel_permissions, permission) is False
        ]:
            raise commands.UserFeedbackCheckFailure(
                _("You cannot remove permissions from you in this channel.")
            )
        new_bot_channel_permissions = fake_channel_object.permissions_for(ctx.me)
        if [
            permission
            for permission in dict(new_bot_channel_permissions)
            if getattr(bot_channel_permissions, permission) is True
            and getattr(new_bot_channel_permissions, permission) is False
        ]:
            raise commands.UserFeedbackCheckFailure(
                _("You cannot remove permissions from the bot in this channel.")
            )
        try:
            await channel.edit(
                overwrites=overwrites,
                reason=f"{ctx.author} ({ctx.author.id}) has edited the voice channel #{channel.name} ({channel.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @editvoicechannel.command(name="delete")
    async def editvoicechannel_delete(
        self,
        ctx: commands.Context,
        channel: discord.VoiceChannel,
        confirmation: bool = False,
    ) -> None:
        """Delete voice channel."""
        await self.check_voice_channel(ctx, channel)
        if not confirmation and not ctx.assume_yes:
            if ctx.bot_permissions.embed_links:
                embed: discord.Embed = discord.Embed()
                embed.title = _("⚠️ - Delete voice channel")
                embed.description = _(
                    "Do you really want to delete the voice channel {channel.mention} ({channel.id})?"
                ).format(channel=channel)
                embed.color = 0xF00020
                content = ctx.author.mention
            else:
                embed = None
                content = f"{ctx.author.mention} " + _(
                    "Do you really want to delete the voice channel {channel.mention} ({channel.id})?"
                ).format(channel=channel)
            if not await CogsUtils.ConfirmationAsk(ctx, content=content, embed=embed):
                await CogsUtils.delete_message(ctx.message)
                return
        try:
            await channel.delete(
                reason=f"{ctx.author} ({ctx.author.id}) has deleted the voice channel #!{channel.name} ({channel.id})."
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @editvoicechannel.command(name="view", aliases=["-"])
    async def editvoicechannel_view(
        self, ctx: commands.Context, channel: discord.VoiceChannel
    ) -> None:
        """View and edit voice channel."""
        await self.check_voice_channel(ctx, channel)
        embed_color = await ctx.embed_color()

        parameters = {
            "name": {"converter": commands.Range[str, 1, 100]},
            "bitrate": {"converter": int},
            "nsfw": {"converter": bool},
            "user_limit": {"converter": commands.Range[int, 0, 99]},
            "position": {"converter": PositionConverter},
            "sync_permissions": {"converter": bool, "attribute_name": "permissions_synced"},
            "category": {"converter": discord.CategoryChannel},
            "slowmode_delay": {"converter": commands.Range[int, 0, 21_600]},
            "video_quality_mode": {"converter": VideoQualityModeConverter},
        }

        def get_embed() -> discord.Embed:
            embed: discord.Embed = discord.Embed(
                title=f"Voice Channel #!{channel.name} ({channel.id})", color=embed_color
            )
            embed.timestamp = datetime.datetime.now(tz=datetime.timezone.utc)
            embed.description = "\n".join(
                [
                    f"• `{parameter}`: {repr(getattr(channel, parameters[parameter].get('attribute_name', parameter)))}"
                    for parameter in parameters
                ]
            )
            return embed

        await DiscordEditView(
            cog=self,
            _object=channel,
            parameters=parameters,
            get_embed_function=get_embed,
            audit_log_reason=f"{ctx.author} ({ctx.author.id}) has edited the voice channel #{channel.name} ({channel.id}).",
            _object_qualified_name="Voice Channel",
        ).start(ctx)

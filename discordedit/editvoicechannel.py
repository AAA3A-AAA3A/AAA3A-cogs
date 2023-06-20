from AAA3A_utils import Cog, CogsUtils, Menu  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
from redbot.core.bot import Red  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

from redbot.core.utils.chat_formatting import box, pagify

def _(untranslated: str) -> str:  # `redgettext` will found these strings.
    return untranslated
ERROR_MESSAGE = _("I attempted to do something that Discord denied me permissions for. Your command failed to successfully complete.\n{error}")

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


@cog_i18n(_)
class EditVoiceChannel(Cog):
    """A cog to edit voice channels!"""

    def __init__(self, bot: Red) -> None:  # Never executed except manually.
        self.bot: Red = bot

        self.cogsutils: CogsUtils = CogsUtils(cog=self)

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

    @editvoicechannel.command(name="create")
    async def editvoicechannel_create(
        self,
        ctx: commands.Context,
        category: typing.Optional[discord.CategoryChannel] = None,
        *,
        name: str,
    ) -> None:
        """Create a voice channel."""
        try:
            await ctx.guild.create_voice_channel(
                name=name,
                category=category,
                reason=f"{ctx.author} ({ctx.author.id}) has modified the voice channel #!{name}.",
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
        self, ctx: commands.Context, channel: discord.VoiceChannel, *, name: str
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
                reason=f"{ctx.author} ({ctx.author.id}) has create an invite for the voice channel #{channel.name} ({channel.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )
        else:
            await ctx.send(invite.url)

    @editvoicechannel.command(name="name")
    async def editvoicechannel_name(
        self, ctx: commands.Context, channel: discord.VoiceChannel, name: str
    ) -> None:
        """Edit voice channel name."""
        await self.check_voice_channel(ctx, channel)
        try:
            await channel.edit(
                name=name,
                reason=f"{ctx.author} ({ctx.author.id}) has modified the voice channel #!{channel.name} ({channel.id}).",
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
            await ctx.send_help()
            return
        try:
            await channel.edit(
                bitrate=bitrate,
                reason=f"{ctx.author} ({ctx.author.id}) has modified the voice channel #!{channel.name} ({channel.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @editvoicechannel.command(name="nsfw")
    async def editvoicechannel_nsfw(
        self, ctx: commands.Context, channel: discord.VoiceChannel, nsfw: bool
    ) -> None:
        """Edit voice channel nsfw."""
        await self.check_voice_channel(ctx, channel)
        try:
            await channel.edit(
                nsfw=nsfw,
                reason=f"{ctx.author} ({ctx.author.id}) has modified the voice channel #!{channel.name} ({channel.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @editvoicechannel.command(name="userlimit")
    async def editvoicechannel_user_limit(
        self, ctx: commands.Context, channel: discord.VoiceChannel, user_limit: int
    ) -> None:
        """Edit voice channel user limit.

        It must be a number between 0 and 99.
        """
        await self.check_voice_channel(ctx, channel)
        if user_limit < 0 or user_limit > 99:
            await ctx.send_help()
            return
        try:
            await channel.edit(
                user_limit=user_limit,
                reason=f"{ctx.author} ({ctx.author.id}) has modified the voice channel #!{channel.name} ({channel.id}).",
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
                reason=f"{ctx.author} ({ctx.author.id}) has modified the voice channel !{channel.name} ({channel.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @editvoicechannel.command(name="syncpermissions")
    async def editvoicechannel_sync_permissions(
        self, ctx: commands.Context, channel: discord.VoiceChannel, sync_permissions: bool
    ) -> None:
        """Edit voice channel sync permissions."""
        await self.check_voice_channel(ctx, channel)
        try:
            await channel.edit(
                sync_permissions=sync_permissions,
                reason=f"{ctx.author} ({ctx.author.id}) has modified the voice channel #!{channel.name} ({channel.id}).",
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
                reason=f"{ctx.author} ({ctx.author.id}) has modified the voice channel #!{channel.name} ({channel.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @editvoicechannel.command(name="videoqualitymode")
    async def editvoicechannel_video_quality_mode(
        self,
        ctx: commands.Context,
        channel: discord.VoiceChannel,
        video_quality_mode: typing.Literal["1", "2"],
    ) -> None:
        """Edit voice channel video quality mode.

        auto = 1
        full = 2
        """
        await self.check_voice_channel(ctx, channel)
        video_quality_mode = discord.VideoQualityMode(int(video_quality_mode))
        try:
            await channel.edit(
                video_quality_mode=video_quality_mode,
                reason=f"{ctx.author} ({ctx.author.id}) has modified the voice channel #!{channel.name} ({channel.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    @editvoicechannel.command(name="permissions", aliases=["overwrites", "perms"])
    async def editvoicechannel_permissions(
        self,
        ctx: commands.Context,
        channel: discord.VoiceChannel,
        roles_or_users: commands.Greedy[
            typing.Union[discord.Member, discord.Role, typing.Literal["everyone"]]
        ],
        true_or_false: typing.Optional[bool],
        permissions: commands.Greedy[PermissionConverter],
    ) -> None:
        """Edit voice channel permissions/overwrites.

        You may not specify `True` or `False` to reset the permission(s).
        With this command, you can only modify the permissions of a role or member below you in the hierarchy. You must possess the permissions you wish to modify.

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
        for target in targets:
            if (
                ctx.author != ctx.guild.owner
                and (
                    target if isinstance(target, discord.Role) else target.top_role
                )
                >= ctx.author.top_role
            ):
                raise commands.UserFeedbackCheckFailure(_("You cannot change the permissions of a role/member higher up the hierarchy than your top role."))
            if (target if isinstance(target, discord.Role) else target.top_role) >= ctx.me.top_role:
                raise commands.UserFeedbackCheckFailure(_("I cannot change the permissions of a role/member higher up the hierarchy than my top role."))
        if not permissions:
            raise commands.UserFeedbackCheckFailure(
                _("You need to provide at least one permission.")
            )
        channel_permissions = channel.permissions_for(ctx.author)
        for permission in permissions:
            if not getattr(channel_permissions, permission):
                raise commands.UserFeedbackCheckFailure(_("You don't have the permission {permission_name} in this channel.").format(permission_name=permission))
        overwrites = channel.overwrites
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
        try:
            await channel.edit(
                overwrites=overwrites,
                reason=f"{ctx.author} ({ctx.author.id}) has modified the voice channel #{channel.name} ({channel.id}).",
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
            if not await self.cogsutils.ConfirmationAsk(
                ctx, content=content, embed=embed
            ):
                await self.cogsutils.delete_message(ctx.message)
                return
        try:
            await channel.delete(
                reason=f"{ctx.author} ({ctx.author.id}) has deleted the voice channel #!{channel.name} ({channel.id})."
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

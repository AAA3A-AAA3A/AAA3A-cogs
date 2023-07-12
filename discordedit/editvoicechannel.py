from AAA3A_utils import Cog, CogsUtils, Menu  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
from redbot.core.bot import Red  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import datetime
import functools
import inspect
from copy import copy

from redbot.core.commands.converter import get_timedelta_converter
from redbot.core.utils.chat_formatting import box, pagify

TimedeltaConverter = get_timedelta_converter(
    default_unit="s",
    maximum=datetime.timedelta(seconds=21600),
    minimum=datetime.timedelta(seconds=0),
)

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

    @editvoicechannel.command(name="create")
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
        self, ctx: commands.Context, channel: discord.VoiceChannel, *, name: commands.Range[str, 1, 100]
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
        self, ctx: commands.Context, channel: discord.VoiceChannel, name: commands.Range[str, 1, 100]
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
            await ctx.send_help()
            return
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

    @editvoicechannel.command(name="userlimit")
    async def editvoicechannel_user_limit(
        self, ctx: commands.Context, channel: discord.VoiceChannel, user_limit: commands.Range[int, 0, 99]
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

    @editvoicechannel.command(name="syncpermissions")
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

    @editvoicechannel.command(name="slowmodedelay")
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
            await ctx.send_help()
            return
        try:
            await channel.edit(
                slowmode_delay=slowmode_delay,
                reason=f"{ctx.author} ({ctx.author.id}) has edited the voice channel #!{channel.name} ({channel.id}).",
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
                raise commands.UserFeedbackCheckFailure(_("You don't have the permission {permission_name} in this channel.").format(permission_name=permission))
        bot_channel_permissions = channel.permissions_for(ctx.me)
        overwrites = channel.overwrites.copy()
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
        fake_channel_object = copy(channel)
        fake_channel_object.overwrites = overwrites
        new_channel_permissions = fake_channel_object.permissions_for(ctx.author)
        if [permission for permission in dict(new_channel_permissions) if getattr(channel_permissions, permission) is True and getattr(new_channel_permissions, permission) is False]:
            raise commands.UserFeedbackCheckFailure(_("You cannot remove permissions from you in this channel."))
        new_bot_channel_permissions = fake_channel_object.permissions_for(ctx.me)
        if [permission for permission in dict(new_bot_channel_permissions) if getattr(bot_channel_permissions, permission) is True and getattr(new_bot_channel_permissions, permission) is False]:
            raise commands.UserFeedbackCheckFailure(_("You cannot remove permissions from the bot in this channel."))
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
            if not await CogsUtils.ConfirmationAsk(
                ctx, content=content, embed=embed
            ):
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

    @editvoicechannel.command(name="view")
    async def editvoicechannel_view(
        self,
        ctx: commands.Context,
        channel: discord.VoiceChannel
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
            "video_quality_mode": {"converter": typing.Literal["1", "2"]},
        }
        parameters_to_split = list(parameters)
        splitted_parameters = []
        while parameters_to_split != []:
            li = parameters_to_split[:5]
            parameters_to_split = parameters_to_split[5:]
            splitted_parameters.append(li)

        def get_embed() -> discord.Embed:
            embed: discord.Embed = discord.Embed(title=f"Voice Channel #!{channel.name} ({channel.id})", color=embed_color)
            embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
            embed.description = "\n".join([f"• `{parameter}`: {repr(getattr(channel, parameters[parameter].get('attribute_name', parameter)))}" for parameter in parameters])
            return embed

        async def button_edit_voice_channel(interaction: discord.Interaction, button_index: int) -> None:
            modal: discord.ui.Modal = discord.ui.Modal(title="Edit Voice Channel")
            modal.on_submit = lambda interaction: interaction.response.defer()
            text_inputs: typing.Dict[str, discord.ui.TextInput] = {}
            for parameter in splitted_parameters[button_index]:
                text_input = discord.ui.TextInput(
                    label=parameter.replace("_", " ").title(),
                    style=discord.TextStyle.short,
                    placeholder=repr(parameters[parameter]["converter"]),
                    default=str(attribute) if (attribute := getattr(channel, parameters[parameter].get("attribute_name", parameter))) is not None else None,
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
                    if parameter == "video_quality_mode":
                        value = int(value)
                    kwargs[parameter] = value
            try:
                await channel.edit(
                    **kwargs,
                    reason=f"{ctx.author} ({ctx.author.id}) has edited the voice channel #!{channel.name} ({channel.id}).",
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
            button = discord.ui.Button(label=f"Edit Voice Channel {button_index + 1}"if len(splitted_parameters) > 1 else "Edit Voice Channel", style=discord.ButtonStyle.secondary)
            button.callback = functools.partial(button_edit_voice_channel, button_index=button_index)
            view.add_item(button)

        async def delete_button_callback(interaction: discord.Interaction) -> None:
            await interaction.response.defer()
            ctx = await CogsUtils.invoke_command(
                bot=interaction.client,
                author=interaction.user,
                channel=interaction.channel,
                command=f"editvoicechannel delete {channel.id}",
            )
            if not await discord.utils.async_all(
                check(ctx) for check in ctx.command.checks
            ):
                await interaction.followup.send(
                    _("You are not allowed to execute this command."), ephemeral=True
                )
                return
        delete_button = discord.ui.Button(label="Delete Voice Channel", style=discord.ButtonStyle.danger)
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

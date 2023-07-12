from AAA3A_utils import Cog, CogsUtils, Menu  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
from redbot.core.bot import Red  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import aiohttp
import datetime
import functools
import inspect

from redbot.core.utils.chat_formatting import box, pagify

try:
    from emoji import UNICODE_EMOJI_ENGLISH as EMOJI_DATA  # emoji<2.0.0
except ImportError:
    from emoji import EMOJI_DATA  # emoji>=2.0.0

def _(untranslated: str) -> str:  # `redgettext` will found these strings.
    return untranslated
ERROR_MESSAGE = _("I attempted to do something that Discord denied me permissions for. Your command failed to successfully complete.\n{error}")

_ = Translator("DiscordEdit", __file__)


class EmojiOrUrlConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str):
        try:
            return await discord.ext.commands.converter.CONVERTER_MAPPING[discord.Emoji]().convert(
                ctx, argument
            )
        except commands.BadArgument:
            pass
        if argument.startswith("<") and argument.endswith(">"):
            argument = argument[1:-1]
        return argument


class PositionConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> int:
        try:
            position = int(argument)
        except ValueError:
            raise commands.BadArgument(_("The position must be an integer."))
        max_guild_roles_position = len(ctx.guild.roles)
        if position <= 0 or position >= max_guild_roles_position + 1:
            raise commands.BadArgument(
                _(
                    "The indicated position must be between 1 and {max_guild_roles_position}."
                ).format(max_guild_roles_position=max_guild_roles_position)
            )
        _list = list(range(max_guild_roles_position - 1))
        _list.reverse()
        position = _list[position - 1]
        return position + 1


class PermissionConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> str:
        permissions = [
            key for key, value in dict(discord.Permissions.all_channel()).items() if value
        ]
        if argument not in permissions:
            raise commands.BadArgument(_("This permission is invalid."))
        return argument


# class PermissionsConverter(commands.Converter):
#     async def convert(self, ctx: commands.Context, argument: str) -> discord.Permissions:
#         try:
#             permissions = int(argument)
#         except ValueError:
#             raise commands.BadArgument(_("The permissions must be an integer."))
#         permissions_none = discord.Permissions.none().value
#         permissions_all = discord.Permissions.all().value
#         if permissions <= permissions_none or permissions >= permissions_all:
#             raise commands.BadArgument(
#                 _(
#                     "The indicated permissions value must be between {permissions_none} and {permissions_all}."
#                 ).format(permissions_none=permissions_none, permissions_all=permissions_all)
#             )
#         return discord.Permissions(permissions=permissions)


@cog_i18n(_)
class EditRole(Cog):
    """A cog to edit roles!"""

    def __init__(self, bot: Red) -> None:  # Never performed except manually.
        super().__init__(bot=bot)

    async def check_role(self, ctx: commands.Context, role: discord.Role) -> bool:
        if (
            not ctx.author.top_role > role
            and ctx.author.id != ctx.guild.owner.id
            and ctx.author.id not in ctx.bot.owner_ids
        ):
            raise commands.UserFeedbackCheckFailure(
                _(
                    "I can not let you edit @{role.name} ({role.id}) because that role is higher than or equal to your highest role in the Discord hierarchy."
                ).format(role=role),
            )
        if not ctx.me.top_role > role:
            raise commands.UserFeedbackCheckFailure(
                _(
                    "I can not edit @{role.name} ({role.id}) because that role is higher than or equal to my highest role in the Discord hierarchy."
                ).format(role=role),
            )
        return True

    @commands.guild_only()
    @commands.admin_or_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    @commands.hybrid_group()
    async def editrole(self, ctx: commands.Context) -> None:
        """Commands for edit a role."""
        pass

    @editrole.command(name="create")
    async def editrole_create(
        self,
        ctx: commands.Context,
        color: typing.Optional[commands.ColorConverter] = None,
        *,
        name: commands.Range[str, 1, 100],
    ) -> None:
        """Create a role."""
        try:
            await ctx.guild.create_role(
                name=name,
                color=color,
                reason=f"{ctx.author} ({ctx.author.id}) has created the role {name}.",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @commands.bot_has_permissions(embed_links=True)
    @editrole.command(name="list")
    async def editrole_list(
        self,
        ctx: commands.Context,
    ) -> None:
        """List all roles in the current guild."""
        description = "".join(
            f"\n**•** **{len(ctx.guild.roles) - role.position}** - {role.mention} ({role.id}) - {len(role.members)} members"
            for role in sorted(ctx.guild.roles, key=lambda x: x.position, reverse=True)
        )
        embed: discord.Embed = discord.Embed(color=await ctx.embed_color())
        embed.title = _("List of roles in {guild.name} ({guild.id})").format(guild=ctx.guild)
        embeds = []
        pages = pagify(description, page_length=4096)
        for page in pages:
            e = embed.copy()
            e.description = page
            embeds.append(e)
        await Menu(pages=embeds).start(ctx)

    @editrole.command(name="name")
    async def editrole_name(self, ctx: commands.Context, role: discord.Role, *, name: commands.Range[str, 1, 100]) -> None:
        """Edit role name."""
        await self.check_role(ctx, role)
        try:
            await role.edit(
                name=name,
                reason=f"{ctx.author} ({ctx.author.id}) has edited the role {role.name} ({role.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @editrole.command(name="color", aliases=["colour"])
    async def editrole_color(
        self, ctx: commands.Context, role: discord.Role, color: discord.Color
    ) -> None:
        """Edit role color."""
        await self.check_role(ctx, role)
        try:
            await role.edit(
                color=color,
                reason=f"{ctx.author} ({ctx.author.id}) has edited the role {role.name} ({role.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @editrole.command(name="hoist")
    async def editrole_hoist(
        self, ctx: commands.Context, role: discord.Role, hoist: bool = None
    ) -> None:
        """Edit role hoist."""
        await self.check_role(ctx, role)
        if hoist is None:
            hoist = not role.hoist
        try:
            await role.edit(
                hoist=hoist,
                reason=f"{ctx.author} ({ctx.author.id}) has edited the role {role.name} ({role.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @editrole.command(name="displayicon", aliases=["icon"])
    async def editrole_display_icon(
        self, ctx: commands.Context, role: discord.Role, display_icon: typing.Optional[EmojiOrUrlConverter] = None
    ) -> None:
        """Edit role display icon.

        `display_icon` can a Unicode emoji, a custom emoji or an url. You can also upload an attachment.
        """
        if "ROLE_ICONS" not in ctx.guild.features:
            raise commands.UserFeedbackCheckFailure(_("This server doesn't have `ROLE_ICONS` feature. This server needs more boosts to perform this action."))
        await self.check_role(ctx, role)
        if len(ctx.message.attachments) > 0:
            display_icon = await ctx.message.attachments[0].read()  # Read an optional attachment.
        elif display_icon is not None:
            if isinstance(display_icon, discord.Emoji):
                # emoji_url = f"https://cdn.discordapp.com/emojis/{display_icon.id}.png"
                # async with aiohttp.ClientSession() as session:
                #     async with session.get(emoji_url) as r:
                #         display_icon = await r.read()  # Get emoji data.
                display_icon = await display_icon.read()
            elif display_icon.strip("\N{VARIATION SELECTOR-16}") in EMOJI_DATA:
                display_icon = display_icon
            else:
                url = display_icon
                async with aiohttp.ClientSession() as session:
                    try:
                        async with session.get(url) as r:
                            display_icon = await r.read()  # Get URL data.
                    except aiohttp.InvalidURL:
                        return await ctx.send("That URL is invalid.")
                    except aiohttp.ClientError:
                        return await ctx.send("Something went wrong while trying to get the image.")
        else:
            await ctx.send_help()  # Send the command help if no attachment, no Unicode/custom emoji and no URL.
            return
        try:
            await role.edit(
                display_icon=display_icon,
                reason=f"{ctx.author} ({ctx.author.id}) has edited the role {role.name} ({role.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @editrole.command(name="mentionable")
    async def editrole_mentionable(
        self, ctx: commands.Context, role: discord.Role, mentionable: bool = None
    ) -> None:
        """Edit role mentionable."""
        await self.check_role(ctx, role)
        if mentionable is None:
            mentionable = not role.mentionable
        try:
            await role.edit(
                mentionable=mentionable,
                reason=f"{ctx.author} ({ctx.author.id}) has edited the role {role.name} ({role.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @editrole.command(name="position")
    async def editrole_position(
        self, ctx: commands.Context, role: discord.Role, position: PositionConverter
    ) -> None:
        """Edit role position.

        Warning: The role with a position 1 is the highest role in the Discord hierarchy.
        """
        await self.check_role(ctx, role)
        try:
            await role.edit(
                position=position,
                reason=f"{ctx.author} ({ctx.author.id}) has edited the role {role.name} ({role.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @editrole.command(name="permissions")
    async def editrole_permissions(
        self, ctx: commands.Context, role: discord.Role, true_or_false: bool, permissions: commands.Greedy[PermissionConverter]
    ) -> None:
        """Edit role permissions.

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
        await self.check_role(ctx, role)
        if not permissions:
            raise commands.UserFeedbackCheckFailure(
                _("You need to provide at least one permission.")
            )
        role_permissions = role.permissions
        for permission in permissions:
            if not getattr(ctx.author.guild_permissions, permission):
                raise commands.UserFeedbackCheckFailure(_("You don't have the permission {permission_name} in this guild.").format(permission_name=permission))
            setattr(role_permissions, permission, true_or_false)
        try:
            await role.edit(
                permissions=role_permissions,
                reason=f"{ctx.author} ({ctx.author.id}) has edited the role {role.name} ({role.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @editrole.command(name="delete")
    async def editrole_delete(
        self,
        ctx: commands.Context,
        role: discord.Role,
        confirmation: bool = False,
    ) -> None:
        """Delete a role."""
        await self.check_role(ctx, role)
        if not confirmation and not ctx.assume_yes:
            if ctx.bot_permissions.embed_links:
                embed: discord.Embed = discord.Embed()
                embed.title = _("⚠️ - Delete role")
                embed.description = _(
                    "Do you really want to delete the role {role.mention} ({role.id})?"
                ).format(role=role)
                embed.color = 0xF00020
                content = ctx.author.mention
            else:
                embed = None
                content = f"{ctx.author.mention} " + _(
                    "Do you really want to delete the role {role.mention} ({role.id})?"
                ).format(role=role)
            if not await CogsUtils.ConfirmationAsk(
                ctx, content=content, embed=embed
            ):
                await CogsUtils.delete_message(ctx.message)
                return
        try:
            await role.delete(
                reason=f"{ctx.author} ({ctx.author.id}) has deleted the role {role.name} ({role.id})."
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @editrole.command(name="view")
    async def editrole_view(
        self,
        ctx: commands.Context,
        role: discord.Role,
    ) -> None:
        """View and edit role."""
        await self.check_role(ctx, role)
        embed_color = await ctx.embed_color()

        parameters = {
            "name": {"converter": commands.Range[str, 1, 100]},
            "color": {"converter": discord.Color},
            "hoist": {"converter": bool},
            "mentionable": {"converter": bool},
            "position": {"converter": PositionConverter},
        }
        parameters_to_split = list(parameters)
        splitted_parameters = []
        while parameters_to_split != []:
            li = parameters_to_split[:5]
            parameters_to_split = parameters_to_split[5:]
            splitted_parameters.append(li)

        def get_embed() -> discord.Embed:
            embed: discord.Embed = discord.Embed(title=f"Role {role.name} ({role.id})", color=embed_color)
            embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
            embed.description = "\n".join([f"• `{parameter}`: {repr(getattr(role, parameters[parameter].get('attribute_name', parameter)))}" for parameter in parameters])
            return embed

        async def button_edit_role(interaction: discord.Interaction, button_index: int) -> None:
            modal: discord.ui.Modal = discord.ui.Modal(title="Edit Role")
            modal.on_submit = lambda interaction: interaction.response.defer()
            text_inputs: typing.Dict[str, discord.ui.TextInput] = {}
            for parameter in splitted_parameters[button_index]:
                text_input = discord.ui.TextInput(
                    label=parameter.replace("_", " ").title(),
                    style=discord.TextStyle.short,
                    placeholder=repr(parameters[parameter]["converter"]),
                    default=str(attribute) if (attribute := getattr(role, parameters[parameter].get("attribute_name", parameter))) is not None else None,
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
                    if parameter == "auto_archive_duration":
                        value = int(value)
                    kwargs[parameter] = value
            try:
                await role.edit(
                    **kwargs,
                    reason=f"{ctx.author} ({ctx.author.id}) has edited the role {role.name} ({role.id}).",
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
            button = discord.ui.Button(label=f"Edit Role {button_index + 1}"if len(splitted_parameters) > 1 else "Edit Role", style=discord.ButtonStyle.secondary)
            button.callback = functools.partial(button_edit_role, button_index=button_index)
            view.add_item(button)

        async def delete_button_callback(interaction: discord.Interaction) -> None:
            await interaction.response.defer()
            ctx = await CogsUtils.invoke_command(
                bot=interaction.client,
                author=interaction.user,
                channel=interaction.channel,
                command=f"editrole delete {role.id}",
            )
            if not await discord.utils.async_all(
                check(ctx) for check in ctx.command.checks
            ):
                await interaction.followup.send(
                    _("You are not allowed to execute this command."), ephemeral=True
                )
                return
        delete_button = discord.ui.Button(label="Delete Role", style=discord.ButtonStyle.danger)
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

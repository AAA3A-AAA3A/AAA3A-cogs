from AAA3A_utils import Cog  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.bot import Red  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import datetime

from redbot.core.utils.chat_formatting import pagify, humanize_list

from .view import PermissionsView

# Credits:
# General repo credits.

_ = Translator("ViewPermissions", __file__)


class PermissionConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> str:
        argument = argument.strip().lower()
        if argument not in discord.Permissions.VALID_FLAGS:
            raise commands.BadArgument(_("`{argument}` isn't a valid permission name").format(argument=argument))
        return argument


@cog_i18n(_)
class ViewPermissions(Cog):
    """A cog to display permissions for roles and members, at guild level or in a specified channel!"""

    def __init__(self, bot: Red) -> None:
        super().__init__(bot=bot)

    async def red_delete_data_for_user(self, *args, **kwargs) -> None:
        """Nothing to delete."""
        return

    async def red_get_data_for_user(self, *args, **kwargs) -> typing.Dict[str, typing.Any]:
        """Nothing to get."""
        return {}

    async def get_permissions(self, guild: discord.Guild, roles: typing.List[discord.Role] = None, members: typing.List[discord.Member] = None, channel: typing.Optional[discord.abc.GuildChannel] = None, permissions: typing.List[str] = None) -> typing.Dict[str, typing.Dict[typing.Literal["qualified_name", "value", "source"], typing.Union[str, bool]]]:
        roles = [] if roles is None else roles.copy()
        if members is None:
            members = []
        for member in members:
            roles.extend(member.roles)
        roles = sorted(set(roles))
        if permissions is None:
            permissions = []

        sources = {}

        if any(member == guild.owner for member in members):  # Guild owner get all permissions -- no questions asked. Otherwise...:
            base = discord.Permissions.all()
            for permission_name in dict(discord.Permissions.all()):
                sources[permission_name] = "Guild owner."
        else:
            base = discord.Permissions(guild.default_role.permissions.value)  # The @everyone role gets the first application.

            # Apply guild roles that the member has.
            for role in roles:
                base.value |= role._permissions
                for permission_name, value in dict(discord.Permissions(role._permissions)).items():
                    if value:
                        sources[permission_name] = f"{role.mention} ({role.id})"
            # Guild-wide Administrator -> True for everything.
            # Bypass all channel-specific overrides.
            if base.administrator:
                base = discord.Permissions.all()
                for permission_name in dict(discord.Permissions.all()):
                    sources[permission_name] = "Guild administrator."
            elif channel is not None:
                # Apply @everyone allow/deny first since it's special.
                try:
                    maybe_everyone = channel._overwrites[0]
                    if maybe_everyone.id == guild.id:
                        base.handle_overwrite(allow=maybe_everyone.allow, deny=maybe_everyone.deny)
                        for permission_name, value in dict(discord.Permissions(maybe_everyone.allow)).items():
                            if value:
                                sources[permission_name] = "Everyone channel overwrite."
                        remaining_overwrites = channel._overwrites[1:]
                    else:
                        remaining_overwrites = channel._overwrites
                except IndexError:
                    remaining_overwrites = channel._overwrites
                denies = 0
                allows = 0
                # Apply channel specific role permission overwrites.
                roles_ids = [role.id for role in roles]
                for overwrite in remaining_overwrites:
                    if overwrite.is_role() and overwrite.id in roles_ids:
                        denies |= overwrite.deny
                        allows |= overwrite.allow
                        for permission_name, value in dict(discord.Permissions(overwrite.allow)).items():
                            if value:
                                role = discord.utils.get(roles, id=overwrite.id)
                                sources[permission_name] = f"Role {role.mention} channel overwrite."
                base.handle_overwrite(allow=allows, deny=denies)
                # Apply member specific permission overwrites.
                members_ids = [member.id for member in members]
                for overwrite in remaining_overwrites:
                    if overwrite.is_member() and overwrite.id in members_ids:
                        base.handle_overwrite(allow=overwrite.allow, deny=overwrite.deny)
                        for permission_name, value in dict(discord.Permissions(overwrite.allow)).items():
                            if value:
                                sources[permission_name] = "Member channel overwrite."
                        break

                if any(member.is_timed_out() for member in members):
                    # Timeout leads to every permission except VIEW_CHANNEL and READ_MESSAGE_HISTORY being explicitly denied.
                    # N.B.: This *must* come last, because it's a conclusive mask.
                    base.value &= discord.Permissions._timeout_mask()

                # Apply implicit channel permissions.
                channel._apply_implicit_permissions(base)
                if isinstance(channel, (discord.TextChannel, discord.ForumChannel)):
                    base.value &= ~discord.Permissions.voice().value  # Text channels do not have voice related permissions.
                elif isinstance(channel, discord.VoiceChannel):
                    # Voice channels cannot be edited by people who can't connect to them.
                    # It also implicitly denies all other voice perms.
                    if not base.connect:
                        denied = discord.Permissions.voice()
                        denied.update(manage_channels=True, manage_roles=True)
                        base.value &= ~denied.value

        permissions_values = [discord.Permissions.VALID_FLAGS[permission_name] for permission_name in permissions]
        permissions_dict = {
            permission_name: {
                "qualified_name": [p for p in discord.Permissions.VALID_FLAGS if discord.Permissions.VALID_FLAGS[p] == discord.Permissions.VALID_FLAGS[permission_name]][-1].replace("_", " ").title(),
                "value": value,
                "source": sources.get(permission_name) if value else None,
            }
            for permission_name, value in dict(base).items()
            if not permissions_values or discord.Permissions.VALID_FLAGS[permission_name] in permissions_values
        }
        return base, permissions_dict

    async def get_embeds(self, guild: discord.Guild, roles: typing.List[discord.Role] = None, members: typing.List[discord.Member] = None, channel: typing.Optional[discord.abc.GuildChannel] = None, permissions: typing.List[str] = None, advanced: bool = False, embed_color: discord.Color = discord.Color.green()) -> typing.List[discord.Embed]:
        roles = [] if roles is None else roles.copy()
        if members is None:
            members = []
        for member in members:
            roles.extend(member.roles)
        roles = sorted(set(roles))
        if permissions is None:
            permissions = []

        embeds: typing.List[discord.Embed] = []
        if not permissions or channel is not None:
            __, permissions_dict = await self.get_permissions(guild=guild, roles=roles, members=members, channel=channel, permissions=permissions)
            embed: discord.Embed = discord.Embed(title=(_("Advanced ") if advanced else "") + _("View Permissions"), color=embed_color)
            embed.set_author(name=guild.name, icon_url=guild.icon)
            embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
            description = ""
            if roles:
                description += _("\n**Role(s):** {roles}").format(roles=humanize_list([f"{role.mention} ({role.id})" for role in roles]))
            if members:
                description += _("\n**Member(s):** {members}").format(members=humanize_list([f"{member.mention} ({member.id})" for member in members]))
            if channel:
                description += _("\n**Channel:** {channel}").format(channel=f"{channel.mention} ({channel.id})")
            if permissions:
                description += _("\n**Permission(s) checked:** {permissions}").format(permissions=humanize_list([f"`{permission_name}`" for permission_name in permissions]))
            embed.description = description if len(description) <= 4000 else f"{description[:3997]}..."
            if not advanced:
                e = embed.copy()
                permissions_strings = "\n".join(
                    f"{'✅' if args['value'] else '❌'} {args['qualified_name']}"
                    for __, args in permissions_dict.items()
                )
                for page in pagify(permissions_strings, page_length=1024 // 3):
                    e.add_field(name="\u200c", value=page, inline=True)
                embeds.append(e)
            else:
                max_len = max(len(args['qualified_name']) for args in permissions_dict.values()) + 2
                permissions_strings = "\n".join(
                    f"`{' ' * (max_len - len(args['qualified_name']) - 2)}{args['qualified_name']}` {'✅' if args['value'] else '❌'}{f' {source}' if (source := args['source']) is not None else ''}"
                    for __, args in permissions_dict.items()
                )
                embeds: typing.List[discord.Embed] = []
                pages = list(pagify(permissions_strings, page_length=1024))
                for i, page in enumerate(pages, start=1):
                    e = embed.copy()
                    e.add_field(name="\u200c", value=page, inline=True)
                    e.set_footer(text=f"Page {i}/{len(pages)}")
                    embeds.append(e)
        else:
            embed: discord.Embed = discord.Embed(title=_("View Permissions"), color=embed_color)
            embed.set_author(name=guild.name, icon_url=guild.icon)
            embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
            description = ""
            if roles:
                description += _("\n**Role(s):** {roles}").format(roles=humanize_list([f"{role.mention} ({role.id})" for role in roles]))
            if members:
                description += _("\n**Member(s):** {members}").format(members=humanize_list([f"{member.mention} ({member.id})" for member in members]))
            if permissions:
                description += _("\n**Permission(s) checked:** {permissions}").format(permissions=humanize_list([f"`{permission_name}`" for permission_name in permissions]))
            embed.description = description if len(description) <= 4000 else f"{description[:3997]}..."
            _description = []
            channels = sorted([channel for channel in guild.text_channels if channel.category is None], key=lambda channel: channel.position)
            channels.extend(sorted([channel for channel in guild.voice_channels if channel.category is None], key=lambda channel: channel.position))
            for category in guild.categories:
                if not category.channels:
                    continue
                channels.append(category)
                channels.extend(sorted(category.channels, key=lambda channel: (1 if channel.type == discord.ChannelType.voice else 0, channel.position)))
            for channel in channels:
                if isinstance(channel, discord.CategoryChannel):
                    _description.append(f"\n**{channel.name.upper()}:**")
                    continue
                __, permissions_dict = await self.get_permissions(guild=guild, roles=roles, members=members, channel=channel, permissions=permissions)
                _description.append(f"• {'✅' if all(value['value'] for value in permissions_dict.values()) else '❌'} {channel.mention} ({channel.id})")
            description = "\n".join(_description)
            embeds: typing.List[discord.Embed] = []
            pages = list(pagify(description, page_length=1024))
            for i, page in enumerate(pages, start=1):
                e = embed.copy()
                e.add_field(name="\u200c", value=page, inline=True)
                e.set_footer(text=f"Page {i}/{len(pages)}")
                embeds.append(e)

        return embeds

    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    @commands.hybrid_command(aliases=["viewperms", "permsview"])
    async def viewpermissions(self, ctx: commands.Context, advanced: typing.Optional[bool] = False, channel: typing.Optional[discord.abc.GuildChannel] = None, permissions: commands.Greedy[PermissionConverter] = None, mentionables: commands.Greedy[typing.Union[discord.Role, discord.Member]] = None) -> None:  # commands.CurrentChannel
        """Display permissions for roles and members, at guild level or in a specified channel.

        - You can specify several roles and members, and their permissions will be added together.
        - If you don't provide a channel, only permissions at the guild level will be displayed.
        - If you provide permission(s) and a channel, only these permissions will be displayed for this channel.
        - If you provide permission(s) and no channel, all guild channels will be displayed, with a tick if all the specified permissions are true in the channel.
        - If you provide permission(s) and no mentionables, the everyone role is used.
        """
        if permissions is None:
            permissions = []
        if mentionables is None:
            mentionables = []
        roles = [mentionable for mentionable in mentionables if isinstance(mentionable, discord.Role)]
        members = [mentionable for mentionable in mentionables if isinstance(mentionable, discord.Member)]
        for member in members:
            roles.extend(member.roles)
        await PermissionsView(
            cog=self,
            guild=ctx.guild,
            roles=sorted(set(roles)),
            members=members,
            channel=getattr(channel, "parent", channel),
            permissions=permissions,
            advanced=advanced,
        ).start(ctx)

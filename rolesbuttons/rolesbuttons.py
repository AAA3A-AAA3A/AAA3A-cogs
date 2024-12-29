from AAA3A_utils import Cog, CogsUtils, Menu  # isort:skip
from redbot.core import commands, Config  # isort:skip
from redbot.core.bot import Red  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import asyncio
from functools import partial

from redbot.core.utils.chat_formatting import pagify

from .converters import Emoji, EmojiRoleConverter

# Credits:
# General repo credits.
# Thanks to TrustyJAID for the two converter for the bulk command arguments! (https://github.com/TrustyJAID/Trusty-cogs/blob/main/roletools/converter.py)
# Thanks to Yami for the technique in the init file of some cogs to load the interaction client only if it is not already loaded! Before this fix, when a user clicked a button, the actions would be run about 10 times, causing a huge spam and loop in the channel.
# Thanks to Kuro for the emoji converter (https://canary.discord.com/channels/133049272517001216/133251234164375552/1014520590239019048)!

_: Translator = Translator("RolesButtons", __file__)


class MyMessageConverter(commands.MessageConverter):
    async def convert(self, ctx: commands.Context, argument: str) -> discord.Message:
        message = await super().convert(ctx, argument=argument)
        if message.author != ctx.me:
            raise commands.UserFeedbackCheckFailure(
                _(
                    "I have to be the author of the message. You can use EmbedUtils by AAA3A to send one."
                )
            )
        return message


@cog_i18n(_)
class RolesButtons(Cog):
    """A cog to have roles-buttons!"""

    def __init__(self, bot: Red) -> None:
        super().__init__(bot=bot)

        self.config: Config = Config.get_conf(
            self,
            identifier=205192943327321000143939875896557571750,  # 370638632963
            force_registration=True,
        )
        self.CONFIG_SCHEMA: int = 2
        self.config.register_global(CONFIG_SCHEMA=None)
        self.config.register_guild(
            roles_buttons={},
            modes={},
        )

    async def cog_load(self) -> None:
        await super().cog_load()
        await self.edit_config_schema()
        asyncio.create_task(self.load_buttons())

    async def edit_config_schema(self) -> None:
        CONFIG_SCHEMA = await self.config.CONFIG_SCHEMA()
        if CONFIG_SCHEMA is None:
            CONFIG_SCHEMA = 1
            await self.config.CONFIG_SCHEMA(CONFIG_SCHEMA)
        if CONFIG_SCHEMA == self.CONFIG_SCHEMA:
            return
        if CONFIG_SCHEMA == 1:
            for guild_id in await self.config.all_guilds():
                roles_buttons = await self.config.guild_from_id(guild_id).roles_buttons()
                for message in roles_buttons:
                    message_data = roles_buttons[message].copy()
                    for emoji in message_data:
                        data = roles_buttons[message].pop(emoji)
                        data["emoji"] = emoji
                        config_identifier = CogsUtils.generate_key(
                            length=5, existing_keys=roles_buttons[message]
                        )
                        roles_buttons[message][config_identifier] = data
                await self.config.guild_from_id(guild_id).roles_buttons.set(roles_buttons)
            CONFIG_SCHEMA = 2
            await self.config.CONFIG_SCHEMA.set(CONFIG_SCHEMA)
        if CONFIG_SCHEMA < self.CONFIG_SCHEMA:
            CONFIG_SCHEMA = self.CONFIG_SCHEMA
            await self.config.CONFIG_SCHEMA.set(CONFIG_SCHEMA)
        self.logger.info(
            f"The Config schema has been successfully modified to {self.CONFIG_SCHEMA} for the {self.qualified_name} cog."
        )

    async def load_buttons(self) -> None:
        await self.bot.wait_until_red_ready()
        all_guilds = await self.config.all_guilds()
        for guild in all_guilds:
            config = all_guilds[guild]["roles_buttons"]
            for message in config:
                channel = self.bot.get_channel(int((str(message).split("-"))[0]))
                if channel is None:
                    continue
                message_id = int((str(message).split("-"))[1])
                try:
                    view = self.get_buttons(config=config, message=message)
                    self.bot.add_view(view, message_id=message_id)
                    self.views[discord.PartialMessage(channel=channel, id=message_id)] = view
                except Exception as e:
                    self.logger.error(
                        f"The Button View could not be added correctly for the `{guild}-{message}` message.",
                        exc_info=e,
                    )

    async def on_button_interaction(
        self, interaction: discord.Interaction, config_identifier: str
    ) -> None:
        if await self.bot.cog_disabled_in_guild(self, interaction.guild):
            return
        if not interaction.data["custom_id"].startswith("roles_buttons"):
            return
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=True)
        config = await self.config.guild(interaction.guild).roles_buttons.all()
        if f"{interaction.channel.id}-{interaction.message.id}" not in config:
            await interaction.followup.send(_("This message is not in Config."), ephemeral=True)
            return
        if config_identifier not in config[f"{interaction.channel.id}-{interaction.message.id}"]:
            await interaction.followup.send(_("This button is not in Config."), ephemeral=True)
            return
        role_id = config[f"{interaction.channel.id}-{interaction.message.id}"][config_identifier][
            "role"
        ]
        role = interaction.guild.get_role(role_id)
        if role is None:
            await interaction.followup.send(
                _(
                    "The role ({role_id}) I have to give you no longer exists. Please notify an administrator of this server."
                ).format(role=role),
                ephemeral=True,
            )
            return
        mode = await self.config.guild(interaction.guild).modes.get_raw(
            f"{interaction.channel.id}-{interaction.message.id}", default="add_or_remove"
        )
        if mode == "add_only":
            add_role = True
        elif mode == "remove_only":
            add_role = False
        else:
            add_role = role not in interaction.user.roles
        if add_role:
            try:
                await interaction.user.add_roles(
                    role,
                    reason=_(
                        "Role-button of {interaction.message.id} in {interaction.channel.id}."
                    ).format(interaction=interaction),
                )
            except discord.HTTPException:
                await interaction.followup.send(
                    _(
                        "I could not add the {role.mention} ({role.id}) role to you. Please notify an administrator of this server."
                    ).format(role=role),
                    ephemeral=True,
                )
                return
            else:
                await interaction.followup.send(
                    _("You now have the {role.mention} ({role.id}) role.").format(role=role),
                    ephemeral=True,
                )
        else:
            try:
                await interaction.user.remove_roles(
                    role,
                    reason=f"Role-button of {interaction.message.id} in {interaction.channel.id}.",
                )
            except discord.HTTPException:
                await interaction.followup.send(
                    _(
                        "I could not remove the role {role.mention} ({role.id}) role from you. Please notify an administrator of this server."
                    ).format(role=role),
                    ephemeral=True,
                )
                return
            else:
                await interaction.followup.send(
                    _("You no longer have the role {role.mention} ({role.id}).").format(role=role),
                    ephemeral=True,
                )
        if mode == "replace":
            for emoji in config[f"{interaction.channel.id}-{interaction.message.id}"]:
                if emoji == config_identifier:
                    continue
                other_role_id = config[f"{interaction.channel.id}-{interaction.message.id}"][
                    emoji
                ]["role"]
                other_role = interaction.guild.get_role(other_role_id)
                if other_role is None or other_role not in interaction.user.roles:
                    continue
                try:
                    await interaction.user.remove_roles(
                        other_role,
                        reason=f"Role-button of {interaction.message.id} in {interaction.channel.id}.",
                    )
                except discord.HTTPException:
                    pass

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message) -> None:
        if message.guild is None:
            return
        config = await self.config.guild(message.guild).roles_buttons.all()
        if f"{message.channel.id}-{message.id}" not in config:
            return
        del config[f"{message.channel.id}-{message.id}"]
        await self.config.guild(message.guild).roles_buttons.set(config)

    @commands.guild_only()
    @commands.admin_or_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True, embed_links=True)
    @commands.hybrid_group()  # aliases=["rb"]
    async def rolesbuttons(self, ctx: commands.Context) -> None:
        """Group of commands to use RolesButtons."""
        pass

    @rolesbuttons.command(aliases=["+"])
    async def add(
        self,
        ctx: commands.Context,
        message: MyMessageConverter,
        role: discord.Role,  # commands.Greedy[discord.Role]
        emoji: typing.Optional[Emoji],
        style_button: typing.Optional[typing.Literal["1", "2", "3", "4"]] = "2",
        *,
        text_button: typing.Optional[commands.Range[str, 1, 100]] = None,
    ) -> None:
        """Add a role-button for a message.

        (Use the number for the color.)
        • `primary`: 1
        • `secondary`: 2
        • `success`: 3
        • `danger`: 4
        # Aliases
        • `blurple`: 1
        • `grey`: 2
        • `gray`: 2
        • `green`: 3
        • `red`: 4
        """
        channel_permissions = message.channel.permissions_for(ctx.me)
        if (
            not channel_permissions.view_channel
            or not channel_permissions.read_messages
            or not channel_permissions.read_message_history
        ):
            raise commands.UserFeedbackCheckFailure(
                _(
                    "I don't have sufficient permissions on the channel where the message you specified is located.\nI need the permissions to see the messages in that channel."
                )
            )
        if emoji is None and text_button is None:
            raise commands.UserFeedbackCheckFailure(
                _("You have to specify at least an emoji or a label.")
            )
        if emoji is not None and ctx.interaction is None and ctx.bot_permissions.add_reactions:
            try:
                await ctx.message.add_reaction(emoji)
            except discord.HTTPException:
                raise commands.UserFeedbackCheckFailure(
                    _(
                        "The emoji you selected seems invalid. Check that it is an emoji. If you have Nitro, you may have used a custom emoji from another server."
                    )
                )
        config = await self.config.guild(ctx.guild).roles_buttons.all()
        if f"{message.channel.id}-{message.id}" not in config:
            if message.components:
                raise commands.UserFeedbackCheckFailure(_("This message already has components."))
            config[f"{message.channel.id}-{message.id}"] = {}
        if len(config[f"{message.channel.id}-{message.id}"]) > 25:
            raise commands.UserFeedbackCheckFailure(
                _("I can't do more than 25 roles-buttons for one message.")
            )
        config_identifier = CogsUtils.generate_key(
            length=5, existing_keys=config[f"{message.channel.id}-{message.id}"]
        )
        config[f"{message.channel.id}-{message.id}"][config_identifier] = {
            "role": role.id,  # [role.id for role in set(roles)]
            "emoji": f"{getattr(emoji, 'id', emoji)}" if emoji is not None else None,
            "style_button": int(style_button),
            "text_button": text_button,
        }
        view = self.get_buttons(config, message)
        message = await message.edit(view=view)
        self.views[message] = view
        await self.config.guild(ctx.guild).roles_buttons.set(config)
        await self.list.callback(self, ctx, message=message)

    @rolesbuttons.command()
    async def bulk(
        self,
        ctx: commands.Context,
        message: MyMessageConverter,
        roles_buttons: commands.Greedy[EmojiRoleConverter],
    ) -> None:
        """Add roles-buttons for a message.

        ```[p]rolesbuttons bulk <message> :reaction1:|@role1 :reaction2:|@role2 :reaction3:|@role3```
        """
        if len(roles_buttons) == 0:
            raise commands.UserFeedbackCheckFailure(
                _("You have not specified any valid role-button.")
            )
        channel_permissions = message.channel.permissions_for(ctx.me)
        if (
            not channel_permissions.view_channel
            or not channel_permissions.read_messages
            or not channel_permissions.read_message_history
        ):
            raise commands.UserFeedbackCheckFailure(
                _(
                    "I don't have sufficient permissions on the channel where the message you specified is located.\nI need the permissions to see the messages in that channel."
                )
            )
        if ctx.interaction is None and ctx.bot_permissions.add_reactions:
            try:
                for emoji, __ in roles_buttons[:19]:
                    if emoji is None:
                        continue
                    await ctx.message.add_reaction(emoji)
            except discord.HTTPException:
                raise commands.UserFeedbackCheckFailure(
                    _(
                        "An emoji you selected seems invalid. Check that it is an emoji. If you have Nitro, you may have used a custom emoji from another server."
                    )
                )
        config = await self.config.guild(ctx.guild).roles_buttons.all()
        if f"{message.channel.id}-{message.id}" not in config:
            if message.components:
                raise commands.UserFeedbackCheckFailure(_("This message already has components."))
            config[f"{message.channel.id}-{message.id}"] = {}
        if len(config[f"{message.channel.id}-{message.id}"]) + len(roles_buttons) > 25:
            raise commands.UserFeedbackCheckFailure(
                _("I can't do more than 25 roles-buttons for one message.")
            )
        for emoji, role in roles_buttons:
            config_identifier = CogsUtils.generate_key(
                length=5, existing_keys=config[f"{message.channel.id}-{message.id}"]
            )
            config[f"{message.channel.id}-{message.id}"][config_identifier] = {
                "role": role.id,
                "emoji": f"{getattr(emoji, 'id', emoji)}" if emoji is not None else None,
                "style_button": 2,
                "text_button": None,
            }
        view = self.get_buttons(config, message)
        message = await message.edit(view=view)
        self.views[message] = view
        await self.config.guild(ctx.guild).roles_buttons.set(config)
        await self.list.callback(self, ctx, message=message)

    @rolesbuttons.command(aliases=["quick"])
    async def create(
        self,
        ctx: commands.Context,
        channel: typing.Optional[
            typing.Union[discord.TextChannel, discord.VoiceChannel, discord.Thread]
        ],
        roles_buttons: commands.Greedy[EmojiRoleConverter],
    ) -> None:
        """Create a message with a nice embed and roles-buttons.

        ```[p]rolesbuttons create #channel :reaction1:|@role1 :reaction2:|@role2 :reaction3:|@role3```
        """
        channel = channel or ctx.channel
        if not channel.permissions_for(ctx.me).send_messages:
            raise commands.UserFeedbackCheckFailure(
                _("I don't have the permission to send messages in this channel.")
            )
        if not channel.permissions_for(ctx.me).add_reactions:
            raise commands.UserFeedbackCheckFailure(
                _("I don't have the permission to add reactions in this channel.")
            )
        if not roles_buttons:
            raise commands.UserFeedbackCheckFailure(
                _("You have not specified any valid role-button.")
            )
        message = await channel.send(
            embed=discord.Embed(
                description="\n".join(
                    [f"**•** {emoji} - {role.mention}" for emoji, role in roles_buttons]
                ),
                color=await ctx.embed_color(),
            ),
        )
        await self.bulk.callback(self, ctx, message=message, roles_buttons=roles_buttons)

    @rolesbuttons.command()
    async def mode(
        self,
        ctx: commands.Context,
        message: MyMessageConverter,
        mode: typing.Literal["add_or_remove", "add_only", "remove_only", "replace"],
    ) -> None:
        """Choose a mode for the roles-buttons of a message.

        Mode `add_or_remove`:
        - Users get the role if they do not already have it, or lose it.
        Mode `add_only`:
        - Users can only get the role, but only manual action will remove it.
        Mode `remove_only`:
        - Users can only lose a role, and will not be able to get it again without a manual action.
        Mode `replace`:
        - Same as `add_or_remove`, but the roles from this message will be mutually exclusive, and getting one will remove the previous.
        """
        config = await self.config.guild(ctx.guild).roles_buttons.all()
        if f"{message.channel.id}-{message.id}" not in config:
            raise commands.UserFeedbackCheckFailure(
                _("No role-button is configured for this message. e")
            )
        await self.config.guild(ctx.guild).modes.set_raw(
            f"{message.channel.id}-{message.id}", value=mode
        )
        await ctx.send(_("Mode set for the roles-buttons of this message."))

    @rolesbuttons.command(aliases=["-"])
    async def remove(
        self, ctx: commands.Context, message: MyMessageConverter, config_identifier: str
    ) -> None:
        """Remove a role-button for a message.

        Use `[p]rolesbuttons list <message>` to find the config identifier.
        """
        config = await self.config.guild(ctx.guild).roles_buttons()
        if f"{message.channel.id}-{message.id}" not in config:
            raise commands.UserFeedbackCheckFailure(
                _("No role-button is configured for this message.")
            )
        if config_identifier not in config[f"{message.channel.id}-{message.id}"]:
            raise commands.UserFeedbackCheckFailure(
                _("I wasn't watching for this button on this message.")
            )
        del config[f"{message.channel.id}-{message.id}"][config_identifier]
        if config[f"{message.channel.id}-{message.id}"] == {}:
            del config[f"{message.channel.id}-{message.id}"]
            await message.edit(view=None)
            await self.config.guild(ctx.guild).modes.clear_raw(
                f"{message.channel.id}-{message.id}"
            )
        else:
            view = self.get_buttons(config, message)
            message = await message.edit(view=view)
            self.views[message] = view
        await self.config.guild(ctx.guild).roles_buttons.set(config)
        if f"{message.channel.id}-{message.id}" in config:
            await self.list.callback(self, ctx, message=message)
        else:
            await ctx.send(_("Roles-buttons cleared for this message."))

    @rolesbuttons.command()
    async def clear(self, ctx: commands.Context, message: MyMessageConverter) -> None:
        """Clear all roles-buttons for a message."""
        config = await self.config.guild(ctx.guild).roles_buttons.all()
        if f"{message.channel.id}-{message.id}" not in config:
            raise commands.UserFeedbackCheckFailure(
                _("No role-button is configured for this message.")
            )
        try:
            await message.edit(view=None)
        except discord.HTTPException:
            pass
        del config[f"{message.channel.id}-{message.id}"]
        await self.config.guild(ctx.guild).roles_buttons.set(config)
        await self.config.guild(ctx.guild).modes.clear_raw(f"{message.channel.id}-{message.id}")
        await ctx.send(_("Roles-buttons cleared for this message."))

    @commands.bot_has_permissions(embed_links=True)
    @rolesbuttons.command()
    async def list(self, ctx: commands.Context, message: MyMessageConverter = None) -> None:
        """List all roles-buttons of this server or display the settings for a specific one."""
        roles_buttons = await self.config.guild(ctx.guild).roles_buttons()
        for role_button in roles_buttons:
            roles_buttons[role_button]["message"] = role_button
        if message is None:
            _roles_buttons = list(roles_buttons.values()).copy()
        elif f"{message.channel.id}-{message.id}" not in roles_buttons:
            raise commands.UserFeedbackCheckFailure(
                _("No role-button is configured for this message.")
            )
        else:
            _roles_buttons = roles_buttons.copy()
            _roles_buttons = [roles_buttons[f"{message.channel.id}-{message.id}"]]
        if not _roles_buttons:
            raise commands.UserFeedbackCheckFailure(_("No roles-buttons in this server."))
        embed: discord.Embed = discord.Embed(
            title=_("Roles Buttons"),
            description=_("There is {len_roles_buttons} roles buttons in this server.").format(
                len_roles_buttons=len(roles_buttons)
            ),
            color=await ctx.embed_color(),
        )
        embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon)
        embeds = []
        for li in discord.utils.as_chunks(_roles_buttons, max_size=5):
            e = embed.copy()
            for role_button in li:
                value = _("Message Jump Link: {message_jump_link}\n").format(
                    message_jump_link=f"https://discord.com/channels/{ctx.guild.id}/{role_button['message'].replace('-', '/')}"
                )
                value += "\n".join(
                    [
                        f"• `{config_identifier}` - Emoji {(ctx.bot.get_emoji(int(data['emoji'])) if data['emoji'].isdigit() else data['emoji']) if data['emoji'] is not None else '`None`'} - Label `{data['text_button']}` - Role {role.mention if (role := ctx.guild.get_role(data['role'])) else 'Role not found.'} ({data['role']})"
                        for config_identifier, data in role_button.items()
                        if config_identifier != "message"
                    ]
                )
                for page in pagify(value, page_length=1024):
                    e.add_field(
                        name="\u200B",
                        value=page,
                        inline=False,
                    )
            embeds.append(e)
        await Menu(pages=embeds).start(ctx)

    @rolesbuttons.command(hidden=True)
    async def purge(self, ctx: commands.Context) -> None:
        """Clear all roles-buttons for a guild."""
        await self.config.guild(ctx.guild).roles_buttons.clear()
        await ctx.send(_("All roles-buttons purged."))

    def get_buttons(
        self, config: typing.Dict[str, dict], message: typing.Union[discord.Message, str]
    ) -> discord.ui.View:
        message = (
            f"{message.channel.id}-{message.id}"
            if isinstance(message, discord.Message)
            else message
        )
        view = discord.ui.View(timeout=None)
        for config_identifier in config[message]:
            if config[message][config_identifier]["emoji"] is not None:
                try:
                    int(config[message][config_identifier]["emoji"])
                except ValueError:
                    b = config[message][config_identifier]["emoji"]
                else:
                    b = str(self.bot.get_emoji(int(config[message][config_identifier]["emoji"])))
            else:
                b = None
            button = discord.ui.Button(
                label=config[message][config_identifier]["text_button"],
                emoji=b,
                style=discord.ButtonStyle(
                    config[message][config_identifier].get("style_button", 2)
                ),
                custom_id=f"roles_buttons {config_identifier}",
                disabled=False,
            )
            button.callback = partial(
                self.on_button_interaction, config_identifier=config_identifier
            )
            view.add_item(button)
        return view

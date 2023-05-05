from AAA3A_utils import Cog, CogsUtils  # isort:skip
from redbot.core import commands, Config  # isort:skip
from redbot.core.bot import Red  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

from .converters import Emoji, EmojiRoleConverter

# Credits:
# General repo credits.
# Thanks to TrustyJAID for the two converter for the bulk command arguments! (https://github.com/TrustyJAID/Trusty-cogs/blob/main/roletools/converter.py)
# Thanks to Yami for the technique in the init file of some cogs to load the interaction client only if it is not already loaded! Before this fix, when a user clicked a button, the actions would be run about 10 times, causing a huge spam and loop in the channel.
# Thanks to Kuro for the emoji converter (https://canary.discord.com/channels/133049272517001216/133251234164375552/1014520590239019048)!

_ = Translator("RolesButtons", __file__)


@cog_i18n(_)
class RolesButtons(Cog):
    """A cog to have roles-buttons!"""

    def __init__(self, bot: Red) -> None:
        self.bot: Red = bot

        self.config: Config = Config.get_conf(
            self,
            identifier=205192943327321000143939875896557571750,  # 370638632963
            force_registration=True,
        )
        self.roles_buttons_guild: typing.Dict[
            str, typing.Dict[str, typing.Dict[str, typing.Dict[str, str]]]
        ] = {"roles_buttons": {}, "modes": {}}
        self.config.register_guild(**self.roles_buttons_guild)

        self.cogsutils: CogsUtils = CogsUtils(cog=self)

    async def cog_load(self) -> None:
        await self.load_buttons()

    async def load_buttons(self) -> None:
        all_guilds = await self.config.all_guilds()
        for guild in all_guilds:
            config = all_guilds[guild]["roles_buttons"]
            for message in config:
                try:
                    view = self.get_buttons(config=config, message=message)
                    self.bot.add_view(view, message_id=int((str(message).split("-"))[1]))
                    self.cogsutils.views.append(view)
                except Exception as e:
                    self.log.error(
                        f"The Button View could not be added correctly for the {guild}-{message} message.",
                        exc_info=e,
                    )

    @staticmethod
    def get_emoji(component: dict) -> str:
        return (
            str(component["emoji"]["name"]).strip("\N{VARIATION SELECTOR-16}")
            if "name" in component["emoji"]
            else str(component["emoji"]["id"])
        )

    async def on_button_interaction(self, interaction: discord.Interaction) -> None:
        if await self.bot.cog_disabled_in_guild(self, interaction.guild):
            return
        if not interaction.data["custom_id"].startswith("roles_buttons"):
            return
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=True)
        config = await self.config.guild(interaction.guild).roles_buttons.all()
        if f"{interaction.channel.id}-{interaction.message.id}" not in config:
            await interaction.followup.send(
                _("This message is not in Config."), ephemeral=True
            )
            return

        class FakeContext:
            def __init__(
                self,
                bot: Red,
                author: discord.Member,
                guild: discord.Guild,
                channel: discord.TextChannel,
            ):
                self.bot: Red = bot
                self.author: discord.Member = author
                self.guild: discord.Guild = guild
                self.channel: discord.TextChannel = channel

        fake_context = FakeContext(
            self.bot, interaction.user, interaction.guild, interaction.channel
        )
        emoji = None
        for _component in interaction.message.components:
            for component in _component.to_dict()["components"]:
                if component["custom_id"] == interaction.data["custom_id"]:
                    emoji = await Emoji().convert(fake_context, self.get_emoji(component))
                    emoji = f"{getattr(emoji, 'id', emoji)}"
                    break
        if emoji not in config[f"{interaction.channel.id}-{interaction.message.id}"]:
            await interaction.followup.send(_("This emoji is not in Config."), ephemeral=True)
            return
        # try:
        #     roles = config[f"{interaction.channel.id}-{interaction.message.id}"][emoji]["roles"]
        # except ValueError:
        role_id = config[f"{interaction.channel.id}-{interaction.message.id}"][emoji]["role"]
        # roles = [role]
        # for role_id in roles:  # Only one role, as the commit has been canceled.
        role = interaction.guild.get_role(role_id)
        if not role:
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
        if add_role:  # interaction.guild.get_role(roles[0])
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
                        "I could not add the {role.mention} role to you. Please notify an administrator of this server."
                    ).format(role=role),
                    ephemeral=True,
                )
                return
            else:
                if mode == "replace":
                    for _component in interaction.message.components:
                        for component in _component.to_dict()["components"]:
                            emoji = await Emoji().convert(fake_context, self.get_emoji(component))
                            emoji = f"{getattr(emoji, 'id', emoji)}"
                            if emoji not in config[f"{interaction.channel.id}-{interaction.message.id}"]:
                                continue
                            other_role_id = config[f"{interaction.channel.id}-{interaction.message.id}"][emoji]["role"]
                            other_role = interaction.guild.get_role(other_role_id)
                            if not other_role or other_role not in interaction.user.roles:
                                continue
                            try:
                                await interaction.user.remove_roles(
                                    other_role,
                                    reason=f"Role-button of {interaction.message.id} in {interaction.channel.id}.",
                                )
                            except discord.HTTPException:
                                pass
                await interaction.followup.send(
                    _("You now have the {role.mention} role.").format(role=role),
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
                        "I could not remove the {role.mention} role from you. Please notify an administrator of this server."
                    ).format(role=role),
                    ephemeral=True,
                )
                return
            else:
                await interaction.followup.send(
                    _("You no longer have the {role.mention} role.").format(role=role),
                    ephemeral=True,
                )

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
    # @commands.bot_has_guild_permissions(manage_roles=True)
    @commands.hybrid_group()
    async def rolesbuttons(self, ctx: commands.Context) -> None:
        """Group of commands to use RolesButtons."""
        pass

    @rolesbuttons.command()
    async def add(
        self,
        ctx: commands.Context,
        message: discord.Message,
        emoji: Emoji,
        role: discord.Role,  # commands.Greedy[discord.Role]
        style_button: typing.Optional[typing.Literal["1", "2", "3", "4"]] = "2",
        *,
        text_button: typing.Optional[str] = None,
    ) -> None:
        """Add a role-button for a message.

        `primary`: 1
        `secondary`: 2
        `success`: 3
        `danger`: 4
        # Aliases
        `blurple`: 1
        `grey`: 2
        `gray`: 2
        `green`: 3
        `red`: 4
        """
        if message.author != ctx.guild.me:
            raise commands.UserFeedbackCheckFailure(
                _("I have to be the author of the message for the role-button to work.")
            )
        permissions = message.channel.permissions_for(ctx.guild.me)
        if (
            not permissions.add_reactions
            or not permissions.read_message_history
            or not permissions.read_messages
            or not permissions.view_channel
        ):
            raise commands.UserFeedbackCheckFailure(
                _(
                    "I don't have sufficient permissions on the channel where the message you specified is located.\nI need the permissions to see the messages in that channel."
                )
            )
        if getattr(ctx, "interaction", None) is None:
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
            config[f"{message.channel.id}-{message.id}"] = {}
        if len(config[f"{message.channel.id}-{message.id}"]) > 25:
            raise commands.UserFeedbackCheckFailure(
                _("I can't do more than 25 roles-buttons for one message.")
            )
        config[f"{message.channel.id}-{message.id}"][f"{getattr(emoji, 'id', emoji)}"] = {
            "role": role.id,  # [role.id for role in set(roles)]
            "style_button": int(style_button),
            "text_button": text_button,
        }
        view = self.get_buttons(config, message)
        await message.edit(view=view)
        self.cogsutils.views.append(view)
        await self.config.guild(ctx.guild).roles_buttons.set(config)

    @rolesbuttons.command()
    async def bulk(
        self,
        ctx: commands.Context,
        message: discord.Message,
        roles_buttons: commands.Greedy[EmojiRoleConverter],
    ) -> None:
        """Add roles-buttons for a message.

        ```[p]rolesbuttons bulk <message> :reaction1:|@role1 :reaction2:|@role2 :reaction3:|@role3```
        """
        if message.author != ctx.guild.me:
            raise commands.UserFeedbackCheckFailure(
                _("I have to be the author of the message for the role-button to work.")
            )
        if len(roles_buttons) == 0:
            raise commands.UserFeedbackCheckFailure(
                _("You have not specified any valid role-button.")
            )
        permissions = message.channel.permissions_for(ctx.guild.me)
        if (
            not permissions.add_reactions
            or not permissions.read_message_history
            or not permissions.read_messages
            or not permissions.view_channel
        ):
            raise commands.UserFeedbackCheckFailure(
                _(
                    "I don't have sufficient permissions on the channel where the message you specified is located.\nI need the permissions to see the messages in that channel."
                )
            )
        if getattr(ctx, "interaction", None) is None:
            try:
                for emoji, role in roles_buttons[:19]:
                    await ctx.message.add_reaction(emoji)
            except discord.HTTPException:
                raise commands.UserFeedbackCheckFailure(
                    _(
                        "An emoji you selected seems invalid. Check that it is an emoji. If you have Nitro, you may have used a custom emoji from another server."
                    )
                )
        config = await self.config.guild(ctx.guild).roles_buttons.all()
        if f"{message.channel.id}-{message.id}" not in config:
            config[f"{message.channel.id}-{message.id}"] = {}
        if len(config[f"{message.channel.id}-{message.id}"]) + len(roles_buttons) > 25:
            raise commands.UserFeedbackCheckFailure(
                _("I can't do more than 25 roles-buttons for one message.")
            )
        for emoji, role in roles_buttons:
            config[f"{message.channel.id}-{message.id}"][f"{getattr(emoji, 'id', emoji)}"] = {
                "role": role.id,
                "style_button": 2,
                "text_button": None,
            }
        view = self.get_buttons(config, message)
        await message.edit(view=view)
        self.cogsutils.views.append(view)
        await self.config.guild(ctx.guild).roles_buttons.set(config)

    @rolesbuttons.command()
    async def mode(
        self,
        ctx: commands.Context,
        message: discord.Message,
        mode: typing.Literal["add_or_remove", "add_only", "remove_only", "replace"],
    ) -> None:
        """Choose a mode for a roles-buttons message.

        Type `add_or_remove`:
        Users get the role if they do not already have it, or lose it.
        Type `add_only`:
        Users can only get the role, but only manual action will remove it.
        Type `remove_only`:
        Users can only lose a role, and will not be able to get it again without a manual action.
        Type `replace`:
        Same as add_or_remove, but the roles from this message will be mutually exclusive, and getting one will remove the previous.
        """
        if message.author != ctx.guild.me:
            raise commands.UserFeedbackCheckFailure(
                _("I have to be the author of the message for the role-button to work.")
            )
        config = await self.config.guild(ctx.guild).roles_buttons.all()
        if f"{message.channel.id}-{message.id}" not in config:
            raise commands.UserFeedbackCheckFailure(
                _("No role-button is configured for this message.")
            )
        await self.config.guild(ctx.guild).modes.set_raw(
            f"{message.channel.id}-{message.id}", value=mode
        )

    @rolesbuttons.command()
    async def remove(self, ctx: commands.Context, message: discord.Message, emoji: Emoji) -> None:
        """Remove a role-button for a message."""
        if message.author != ctx.guild.me:
            raise commands.UserFeedbackCheckFailure(
                _("I have to be the author of the message for the role-button to work.")
            )
        config = await self.config.guild(ctx.guild).roles_buttons.all()
        if f"{message.channel.id}-{message.id}" not in config:
            raise commands.UserFeedbackCheckFailure(
                _("No role-button is configured for this message.")
            )
        if f"{getattr(emoji, 'id', emoji)}" not in config[f"{message.channel.id}-{message.id}"]:
            raise commands.UserFeedbackCheckFailure(
                _("I wasn't watching for this button on this message.")
            )
        del config[f"{message.channel.id}-{message.id}"][f"{getattr(emoji, 'id', emoji)}"]
        if config[f"{message.channel.id}-{message.id}"] == {}:
            del config[f"{message.channel.id}-{message.id}"]
            await message.edit(view=None)
            await self.config.guild(ctx.guild).modes.clear_raw(
                f"{message.channel.id}-{message.id}"
            )
        else:
            view = self.get_buttons(config, message)
            await message.edit(view=view)
            self.cogsutils.views.append(view)
        await self.config.guild(ctx.guild).roles_buttons.set(config)

    @rolesbuttons.command()
    async def clear(self, ctx: commands.Context, message: discord.Message) -> None:
        """Clear all roles-buttons for a message."""
        if message.author != ctx.guild.me:
            raise commands.UserFeedbackCheckFailure(
                _("I have to be the author of the message for the role-button to work.")
            )
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

    @rolesbuttons.command(hidden=True)
    async def purge(self, ctx: commands.Context) -> None:
        """Clear all roles-buttons for a guild."""
        await self.config.guild(ctx.guild).roles_buttons.clear()

    def get_buttons(
        self, config: typing.Dict, message: typing.Union[discord.Message, str]
    ) -> discord.ui.View:
        message = (
            f"{message.channel.id}-{message.id}"
            if isinstance(message, discord.Message)
            else message
        )
        view = discord.ui.View(timeout=None)
        for button in config[message]:
            try:
                int(button)
            except ValueError:
                b = button
            else:
                b = str(self.bot.get_emoji(int(button)))
            button = discord.ui.Button(
                label=config[message][f"{button}"]["text_button"],
                emoji=b,
                style=discord.ButtonStyle(config[message][f"{button}"].get("style_button", 2)),
                custom_id=f"roles_buttons {button}",
                disabled=False,
            )
            button.callback = self.on_button_interaction
            view.add_item(button)
        return view

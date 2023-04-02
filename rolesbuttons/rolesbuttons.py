from .AAA3A_utils import Cog, CogsUtils  # isort:skip
from redbot.core import commands, Config  # isort:skip
from redbot.core.bot import Red  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

if not CogsUtils().is_dpy2:
    from dislash import ActionRow, MessageInteraction, ResponseType  # isort:skip

from .converters import Emoji, EmojiRoleConverter

if CogsUtils().is_dpy2:  # To remove
    setattr(commands, "Literal", typing.Literal)

# Credits:
# General repo credits.
# Thanks to TrustyJAID for the two converter for the bulk command arguments! (https://github.com/TrustyJAID/Trusty-cogs/blob/main/roletools/converter.py)
# Thanks to Yami for the technique in the init file of some cogs to load the interaction client only if it is not already loaded! Before this fix, when a user clicked a button, the actions would be run about 10 times, causing a huge spam and loop in the channel.
# Thanks to Kuro for the emoji converter (https://canary.discord.com/channels/133049272517001216/133251234164375552/1014520590239019048)!

_ = Translator("RolesButtons", __file__)

if CogsUtils().is_dpy2:
    hybrid_command = commands.hybrid_command
    hybrid_group = commands.hybrid_group
else:
    hybrid_command = commands.command
    hybrid_group = commands.group


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
        ] = {
            "roles_buttons": {},
            "modes": {}
        }
        self.config.register_guild(**self.roles_buttons_guild)

        self.cogsutils: CogsUtils = CogsUtils(cog=self)

    async def cog_load(self) -> None:
        if self.cogsutils.is_dpy2:
            await self.load_buttons()

    async def load_buttons(self) -> None:
        all_guilds = await self.config.all_guilds()
        for guild in all_guilds:
            config = all_guilds[guild]["roles_buttons"]
            for message in config:
                try:
                    view = self.get_buttons(config=config, message=message)
                    # view = Buttons(
                    #     timeout=None,
                    #     buttons=[
                    #         {
                    #             "style": all_guilds[guild]["roles_buttons"][role_button][
                    #                 f"{emoji}"
                    #             ]["style_button"]
                    #             if "style_button"
                    #             in all_guilds[guild]["roles_buttons"][role_button][f"{emoji}"]
                    #             else 2,
                    #             "label": all_guilds[guild]["roles_buttons"][role_button][
                    #                 f"{emoji}"
                    #             ]["text_button"],
                    #             "emoji": f"{emoji}",
                    #             "custom_id": f"roles_buttons {emoji}",
                    #             "disabled": False,
                    #         }
                    #         for emoji in all_guilds[guild]["roles_buttons"][role_button]
                    #     ],
                    #     function=self.on_button_interaction,
                    #     infinity=True,
                    # )
                    self.bot.add_view(view, message_id=int((str(message).split("-"))[1]))
                    self.cogsutils.views.append(view)
                except Exception as e:
                    self.log.error(
                        f"The Button View could not be added correctly for the {guild}-{message} message.",
                        exc_info=e,
                    )

    if CogsUtils().is_dpy2:

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
            for _component in interaction.message.components:
                for component in _component.to_dict()["components"]:
                    if component["custom_id"] == interaction.data["custom_id"]:
                        emoji = (
                            str(component["emoji"]["name"]).strip("\N{VARIATION SELECTOR-16}")
                            if "name" in component["emoji"]
                            else str(component["emoji"]["id"])
                        )
                        break

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
            emoji = await Emoji().convert(fake_context, str(emoji))
            emoji = f"{getattr(emoji, 'id', emoji)}"
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
            if role is None:
                await interaction.followup.send(
                    _("The role ({role_id}) I have to put you in no longer exists. Please notify an administrator of this server.").format(role=role),
                    ephemeral=True,
                )
                return
            mode = await self.config.guild(interaction.guild).modes.get_raw(f"{interaction.channel.id}-{interaction.message.id}", default="add_or_remove")
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
                            "I could not add the {role.mention} ({role.id}) role to you. Please notify an administrator of this server."
                        ).format(role=role),
                        ephemeral=True,
                    )
                    return
                else:
                    await interaction.followup.send(
                        _("You now have the role {role.mention} ({role.id}).").format(role=role),
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
                            "I could not remove the {role.mention} ({role.id}) role to you. Please notify an administrator of this server."
                        ).format(role=role),
                        ephemeral=True,
                    )
                    return
                else:
                    await interaction.followup.send(
                        _("I removed the role {role.mention} ({role.id}).").format(role=role),
                        ephemeral=True,
                    )

    else:

        @commands.Cog.listener()
        async def on_button_click(self, inter: MessageInteraction) -> None:
            guild = inter.guild
            channel = inter.channel
            if inter.author is None:
                return
            if inter.guild is None:
                return
            if await self.bot.cog_disabled_in_guild(self, guild):
                return
            if not inter.component.custom_id.startswith("roles_buttons"):
                return
            if not getattr(inter, "_sent", False) and not inter.expired:
                try:
                    await inter.respond(type=ResponseType.DeferredUpdateMessage, ephemeral=True)
                except discord.HTTPException:
                    pass
            config = await self.config.guild(guild).roles_buttons.all()
            if f"{inter.channel.id}-{inter.message.id}" not in config:
                await inter.followup(_("This message is not in Config."), ephemeral=True)
                return
            emoji = inter.component.emoji

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

            fake_context = FakeContext(self.bot, inter.author, inter.guild, inter.channel)
            emoji = await Emoji().convert(fake_context, str(emoji))
            emoji = f"{getattr(emoji, 'id', emoji)}"
            if emoji not in config[f"{inter.channel.id}-{inter.message.id}"]:
                await inter.followup(_("This emoji is not in Config."), ephemeral=True)
                return
            role_id = config[f"{inter.channel.id}-{inter.message.id}"][emoji]["role"]
            role = inter.guild.get_role(role_id)
            if role is None:
                await inter.followup(
                    _("The role ({role_id}) I have to put you in no longer exists. Please notify an administrator of this server.").format(role=role),
                    ephemeral=True,
                )
                return
            mode = await self.config.guild(inter.guild).modes.get_raw(f"{inter.channel.id}-{inter.message.id}", default="add_or_remove")
            if mode == "add_only":
                add_role = True
            elif mode == "remove_only":
                add_role = False
            else:
                add_role = role not in inter.author.roles
            if add_role:
                try:
                    await inter.author.add_roles(
                        role,
                        reason=_("Role-button of {inter.message.id} in {channel.id}.").format(
                            inter=inter, channel=channel
                        ),
                    )
                except discord.HTTPException:
                    await inter.followup(
                        _(
                            "I could not add the {role.mention} ({role.id}) role to you. Please notify an administrator of this server."
                        ).format(role=role),
                        ephemeral=True,
                    )
                    return
                else:
                    await inter.followup(
                        _("You now have the role {role.mention} ({role.id}).").format(role=role),
                        ephemeral=True,
                    )
                    return
            else:
                try:
                    await inter.author.remove_roles(
                        role, reason=f"Role-button of {inter.message.id} in {channel.id}."
                    )
                except discord.HTTPException:
                    await inter.followup(
                        _(
                            "I could not remove the {role.mention} ({role.id}) role to you. Please notify an administrator of this server."
                        ).format(role=role),
                        ephemeral=True,
                    )
                    return
                else:
                    await inter.followup(
                        _("I did remove the role {role.mention} ({role.id}).").format(role=role),
                        ephemeral=True,
                    )
                    return

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
    @hybrid_group()
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
        style_button: typing.Optional[commands.Literal["1", "2", "3", "4"]] = "2",
        *,
        text_button: typing.Optional[str] = None,
    ) -> None:
        """Add a role-button to a message.

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
        if self.cogsutils.is_dpy2:
            view = self.get_buttons(config, message)
            await message.edit(view=view)
            self.cogsutils.views.append(view)
        else:
            await message.edit(components=self.get_buttons(config, message))
        await self.config.guild(ctx.guild).roles_buttons.set(config)

    @rolesbuttons.command()
    async def bulk(
        self,
        ctx: commands.Context,
        message: discord.Message,
        roles_buttons: commands.Greedy[EmojiRoleConverter],
    ) -> None:
        """Add roles-buttons to a message.

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
        if self.cogsutils.is_dpy2:
            view = self.get_buttons(config, message)
            await message.edit(view=view)
            self.cogsutils.views.append(view)
        else:
            await message.edit(components=self.get_buttons(config, message))
        await self.config.guild(ctx.guild).roles_buttons.set(config)

    @rolesbuttons.command()
    async def mode(self, ctx: commands.Context, message: discord.Message, mode: commands.Literal["add_or_remove", "add_only", "remove_only"]) -> None:
        """Choose a mode for a roles-buttons message.

        Type `add_or_remove`:
        Users get the role if they do not already have it, or lose it.
        Type `add_only`:
        Users can only get the role, but only manual action will remove it.
        Type `remove_only`:
        Users can only lose a role, and will not be able to get it again without a manual action.
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
        await self.config.guild(ctx.guild).modes.set_raw(f"{message.channel.id}-{message.id}", value=mode)

    @rolesbuttons.command()
    async def remove(self, ctx: commands.Context, message: discord.Message, emoji: Emoji) -> None:
        """Remove a role-button to a message."""
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
            if self.cogsutils.is_dpy2:
                await message.edit(view=None)
            else:
                await message.edit(components=None)
            await self.config.guild(ctx.guild).modes.clear_raw(f"{message.channel.id}-{message.id}")
        elif self.cogsutils.is_dpy2:
            view = self.get_buttons(config, message)
            await message.edit(view=view)
            self.cogsutils.views.append(view)
        else:
            await message.edit(components=self.get_buttons(config, message))
        await self.config.guild(ctx.guild).roles_buttons.set(config)

    @rolesbuttons.command()
    async def clear(self, ctx: commands.Context, message: discord.Message) -> None:
        """Clear all roles-buttons to a message."""
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
            if self.cogsutils.is_dpy2:
                await message.edit(view=None)
            else:
                await message.edit(components=[])
        except discord.HTTPException:
            pass
        del config[f"{message.channel.id}-{message.id}"]
        await self.config.guild(ctx.guild).roles_buttons.set(config)
        await self.config.guild(ctx.guild).modes.clear_raw(f"{message.channel.id}-{message.id}")

    @rolesbuttons.command(hidden=True)
    async def purge(self, ctx: commands.Context) -> None:
        """Clear all roles-buttons to a **guild**."""
        await self.config.guild(ctx.guild).roles_buttons.clear()

    def get_buttons(self, config: typing.Dict, message: typing.Union[discord.Message, str]):  # dpy2: discord.ui.View
        message = (
            f"{message.channel.id}-{message.id}"
            if isinstance(message, discord.Message)
            else message
        )
        all_buttons = []
        if self.cogsutils.is_dpy2:
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
                    disabled=False
                )
                button.callback = self.on_button_interaction
                view.add_item(button)
                # all_buttons.append(
                #     {
                #         "style": config[f"{message.channel.id}-{message.id}"][f"{button}"][
                #             "style_button"
                #         ],
                #         "label": config[f"{message.channel.id}-{message.id}"][f"{button}"][
                #             "text_button"
                #         ],
                #         "emoji": f"{b}",
                #         "custom_id": f"roles_buttons {button}",
                #         "disabled": False,
                #     }
                # )
            return view
        else:
            lists = []
            one_l = list(config[message])
            while one_l != []:
                li = one_l[:4]
                one_l = one_l[4:]
                lists.append(li)
            for li in lists:
                buttons = {"type": 1, "components": []}
                for button in li:
                    try:
                        int(button)
                    except ValueError:
                        buttons["components"].append(
                            {
                                "type": 2,
                                "style": config[message][f"{button}"][
                                    "style_button"
                                ],
                                "label": config[message][f"{button}"][
                                    "text_button"
                                ],
                                "emoji": {"name": f"{button}"},
                                "custom_id": f"roles_buttons {button}",
                            }
                        )
                    else:
                        buttons["components"].append(
                            {
                                "type": 2,
                                "style": config[message][f"{button}"].get("style_button", 2),
                                "label": config[message][f"{button}"][
                                    "text_button"
                                ],
                                "emoji": {"name": f"{button}", "id": int(button)},
                                "custom_id": f"roles_buttons {button}",
                            }
                        )
                all_buttons.append(ActionRow.from_dict(buttons))
        return all_buttons

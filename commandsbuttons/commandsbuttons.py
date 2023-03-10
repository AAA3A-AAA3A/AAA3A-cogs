from .AAA3A_utils import CogsUtils  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
from redbot.core.bot import Red  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

if not CogsUtils().is_dpy2:
    from dislash import ActionRow, MessageInteraction, ResponseType  # isort:skip

import asyncio

from redbot.core import Config
from redbot.core.utils.chat_formatting import inline

from .converters import Emoji, EmojiCommandConverter

if CogsUtils().is_dpy2:  # To remove
    setattr(commands, "Literal", typing.Literal)

# Credits:
# General repo credits.
# Thanks to TrustyJAID for the two converter for the bulk command arguments! (https://github.com/TrustyJAID/Trusty-cogs/blob/main/roletools/converter.py)
# Thanks to Yami for the technique in the init file of some cogs to load the interaction client only if it is not already loaded! Before this fix, when a user clicked a button, the actions would be run about 10 times, causing a huge spam and loop in the channel.
# Thanks to Kuro for the emoji converter (https://canary.discord.com/channels/133049272517001216/133251234164375552/1014520590239019048)!

_ = Translator("CommandsButtons", __file__)

if CogsUtils().is_dpy2:
    from functools import partial

    hybrid_command = partial(commands.hybrid_command, with_app_command=False)
    hybrid_group = partial(commands.hybrid_group, with_app_command=False)
else:
    hybrid_command = commands.command
    hybrid_group = commands.group


@cog_i18n(_)
class CommandsButtons(commands.Cog):
    """A cog to allow a user to execute a command by clicking on a button!"""

    def __init__(self, bot: Red) -> None:
        self.bot: Red = bot

        self.config: Config = Config.get_conf(
            self,
            identifier=205192943327321000143939875896557571750,  # 370638632963
            force_registration=True,
        )
        self.commands_buttons_guild: typing.Dict[
            str, typing.Dict[str, typing.Dict[str, typing.Dict[str, str]]]
        ] = {
            "commands_buttons": {},
        }
        self.config.register_guild(**self.commands_buttons_guild)

        self.cogsutils: CogsUtils = CogsUtils(cog=self)
        self.purge.no_slash: bool = True

        self.cache: typing.List[commands.Context] = []

    async def cog_load(self) -> None:
        if self.cogsutils.is_dpy2:
            await self.load_buttons()

    async def load_buttons(self) -> None:
        all_guilds = await self.config.all_guilds()
        for guild in all_guilds:
            config = all_guilds[guild]["commands_buttons"]
            for message in config:
                try:
                    view = self.get_buttons(config=config, message=message)
                    # view = Buttons(
                    #     timeout=None,
                    #     buttons=[
                    #         {
                    #             "style": all_guilds[guild]["commands_buttons"][command_button][
                    #                 f"{emoji}"
                    #             ]["style_button"]
                    #             if "style_button"
                    #             in all_guilds[guild]["commands_buttons"][command_button][f"{emoji}"]
                    #             else 2,
                    #             "label": all_guilds[guild]["commands_buttons"][command_button][
                    #                 f"{emoji}"
                    #             ]["text_button"],
                    #             "emoji": f"{emoji}",
                    #             "custom_id": f"commands_buttons {emoji}",
                    #             "disabled": False,
                    #         }
                    #         for emoji in all_guilds[guild]["commands_buttons"][command_button]
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
            if not interaction.data["custom_id"].startswith("commands_buttons"):
                return
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=True)
            config = await self.config.guild(interaction.guild).commands_buttons.all()
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
            command = config[f"{interaction.channel.id}-{interaction.message.id}"][emoji][
                "command"
            ]
            context = await self.cogsutils.invoke_command(
                author=interaction.user,
                channel=interaction.channel,
                command=command,
                message=interaction.message,
                __is_mocked__=True,
            )
            if not isinstance(context, commands.Context) or not context.valid:
                await interaction.followup.send(_("The command don't exist."), ephemeral=True)
                return
            if not await context.command.can_run(context):
                await interaction.followup.send(
                    _("You are not allowed to execute this command."), ephemeral=True
                )
                return
            self.cache.append(context)

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
            if not inter.component.custom_id.startswith("commands_buttons"):
                return
            if not getattr(inter, "_sent", False) and not inter.expired:
                try:
                    await inter.respond(type=ResponseType.DeferredUpdateMessage, ephemeral=True)
                except discord.HTTPException:
                    pass
            config = await self.config.guild(guild).commands_buttons.all()
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
            command = config[f"{inter.channel.id}-{inter.message.id}"][emoji]["command"]
            context = await self.cogsutils.invoke_command(
                author=inter.author,
                channel=channel,
                command=command,
                message=inter.message,
                __is_mocked__=True,
            )
            if not context.valid:
                await inter.followup(_("The command don't exist."), ephemeral=True)
                return
            if not await context.command.can_run(context):
                await inter.followup(
                    _("You are not allowed to execute this command."), ephemeral=True
                )
                return
            self.cache.append(context)

    @commands.Cog.listener()
    async def on_command_completion(self, ctx: commands.Context) -> None:
        if ctx in self.cache:
            self.cache.remove(ctx)

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: Exception) -> None:
        if ctx not in self.cache:
            return
        self.cache.remove(ctx)
        if isinstance(error, commands.CommandInvokeError):
            await asyncio.sleep(0.7)
            self.log.error(
                f"This exception in the '{ctx.command.qualified_name}' command may have been triggered by the use of CommandsButtons. Check that the same error occurs with the text command, before reporting it.",
                exc_info=None,
            )
            message = f"This error in the '{ctx.command.qualified_name}' command may have been triggered by the use of CommandsButtons.\nCheck that the same error occurs with the text command, before reporting it."
            await ctx.send(inline(message))

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message) -> None:
        if message.guild is None:
            return
        config = await self.config.guild(message.guild).commands_buttons.all()
        if f"{message.channel.id}-{message.id}" not in config:
            return
        del config[f"{message.channel.id}-{message.id}"]
        await self.config.guild(message.guild).commands_buttons.set(config)

    @commands.guild_only()
    @commands.is_owner()
    @hybrid_group()
    async def commandsbuttons(self, ctx: commands.Context) -> None:
        """Group of commands for use CommandsButtons."""
        pass

    @commandsbuttons.command()
    async def add(
        self,
        ctx: commands.Context,
        message: discord.Message,
        emoji: Emoji,
        command: str,
        style_button: typing.Optional[commands.Literal["1", "2", "3", "4"]] = "2",
        *,
        text_button: typing.Optional[str] = None,
    ) -> None:
        """Add a command-button to a message.

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
        if not message.author == ctx.guild.me:
            raise commands.UserFeedbackCheckFailure(
                _("I have to be the author of the message for the command-button to work.")
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
        if not ctx.prefix == "/":
            msg = ctx.message
            msg.content = f"{ctx.prefix}{command}"
            new_ctx = await ctx.bot.get_context(msg)
            if not new_ctx.valid:
                raise commands.UserFeedbackCheckFailure(
                    _("You have not specified a correct command.")
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
        config = await self.config.guild(ctx.guild).commands_buttons.all()
        if f"{message.channel.id}-{message.id}" not in config:
            config[f"{message.channel.id}-{message.id}"] = {}
        if len(config[f"{message.channel.id}-{message.id}"]) > 25:
            raise commands.UserFeedbackCheckFailure(
                _("I can't do more than 25 commands-buttons for one message.")
            )
        config[f"{message.channel.id}-{message.id}"][f"{getattr(emoji, 'id', emoji)}"] = {
            "command": command,
            "style_button": int(style_button),
            "text_button": text_button,
        }
        if self.cogsutils.is_dpy2:
            view = self.get_buttons(config, message)
            await message.edit(view=view)
            self.cogsutils.views.append(view)
        else:
            await message.edit(components=self.get_buttons(config, message))
        await self.config.guild(ctx.guild).commands_buttons.set(config)

    @commandsbuttons.command()
    async def bulk(
        self,
        ctx: commands.Context,
        message: discord.Message,
        commands_buttons: commands.Greedy[EmojiCommandConverter],
    ) -> None:
        """Add commands-buttons to a message.

        ```[p]commandsbuttons bulk <message> ":reaction1:|ping" ":reaction2:|ping" :reaction3:|ping"```
        """
        if not message.author == ctx.guild.me:
            raise commands.UserFeedbackCheckFailure(
                _("I have to be the author of the message for the command-button to work.")
            )
        if len(commands_buttons) == 0:
            raise commands.UserFeedbackCheckFailure(
                _("You have not specified any valid command-button.")
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
                for emoji, command in commands_buttons[:19]:
                    await ctx.message.add_reaction(emoji)
            except discord.HTTPException:
                raise commands.UserFeedbackCheckFailure(
                    _(
                        "An emoji you selected seems invalid. Check that it is an emoji. If you have Nitro, you may have used a custom emoji from another server."
                    )
                )
        config = await self.config.guild(ctx.guild).commands_buttons.all()
        if f"{message.channel.id}-{message.id}" not in config:
            config[f"{message.channel.id}-{message.id}"] = {}
        if len(config[f"{message.channel.id}-{message.id}"]) + len(commands_buttons) > 25:
            raise commands.UserFeedbackCheckFailure(
                _("I can't do more than 25 roles-buttons for one message.")
            )
        for emoji, command in commands_buttons:
            config[f"{message.channel.id}-{message.id}"][f"{getattr(emoji, 'id', emoji)}"] = {
                "command": command,
                "style_button": 2,
                "text_button": None,
            }
        if self.cogsutils.is_dpy2:
            view = self.get_buttons(config, message)
            await message.edit(view=view)
            self.cogsutils.views.append(view)
        else:
            await message.edit(components=self.get_buttons(config, message))
        await self.config.guild(ctx.guild).commands_buttons.set(config)

    @commandsbuttons.command()
    async def remove(self, ctx: commands.Context, message: discord.Message, emoji: Emoji) -> None:
        """Remove a command-button to a message."""
        if not message.author == ctx.guild.me:
            raise commands.UserFeedbackCheckFailure(
                _("I have to be the author of the message for the command-button to work.")
            )
        config = await self.config.guild(ctx.guild).commands_buttons.all()
        if f"{message.channel.id}-{message.id}" not in config:
            raise commands.UserFeedbackCheckFailure(
                _("No command-button is configured for this message.")
            )
        if f"{getattr(emoji, 'id', emoji)}" not in config[f"{message.channel.id}-{message.id}"]:
            raise commands.UserFeedbackCheckFailure(
                _("I wasn't watching for this button on this message.")
            )
        del config[f"{message.channel.id}-{message.id}"][f"{getattr(emoji, 'id', emoji)}"]
        if not config[f"{message.channel.id}-{message.id}"] == {}:
            if self.cogsutils.is_dpy2:
                view = self.get_buttons(config, message)
                await message.edit(view=view)
                self.cogsutils.views.append(view)
            else:
                await message.edit(components=self.get_buttons(config, message))
        else:
            del config[f"{message.channel.id}-{message.id}"]
            if self.cogsutils.is_dpy2:
                await message.edit(view=None)
            else:
                await message.edit(components=None)
        await self.config.guild(ctx.guild).commands_buttons.set(config)

    @commandsbuttons.command()
    async def clear(self, ctx: commands.Context, message: discord.Message) -> None:
        """Clear all commands-buttons to a message."""
        if not message.author == ctx.guild.me:
            raise commands.UserFeedbackCheckFailure(
                _("I have to be the author of the message for the role-button to work.")
            )
        config = await self.config.guild(ctx.guild).commands_buttons.all()
        if f"{message.channel.id}-{message.id}" not in config:
            raise commands.UserFeedbackCheckFailure(
                _("No command-button is configured for this message.")
            )
        try:
            if self.cogsutils.is_dpy2:
                await message.edit(view=None)
            else:
                await message.edit(components=[])
        except discord.HTTPException:
            pass
        del config[f"{message.channel.id}-{message.id}"]
        await self.config.guild(ctx.guild).commands_buttons.set(config)

    @commandsbuttons.command(hidden=True)
    async def purge(self, ctx: commands.Context) -> None:
        """Clear all commands-buttons to a **guild**."""
        await self.config.guild(ctx.guild).commands_buttons.clear()

    def get_buttons(self, config: typing.Dict, message: typing.Union[discord.Message, str]) -> typing.List[typing.Any]:  # dpy2: discord.ui.View
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
            return view
        else:
            lists = []
            one_l = [button for button in config[message]]
            while True:
                li = one_l[0:4]
                one_l = one_l[4:]
                lists.append(li)
                if one_l == []:
                    break
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
                                "custom_id": f"commands_buttons {button}",
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
                                "custom_id": f"commands_buttons {button}",
                            }
                        )
                all_buttons.append(ActionRow.from_dict(buttons))
        return all_buttons

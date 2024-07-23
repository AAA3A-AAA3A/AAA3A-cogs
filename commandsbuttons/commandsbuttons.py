from AAA3A_utils import Cog, CogsUtils, Menu  # isort:skip
from redbot.core import commands, Config  # isort:skip
from redbot.core.bot import Red  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import asyncio
import inspect
from functools import partial

from redbot.core.utils.chat_formatting import inline, pagify

from .converters import Emoji, EmojiCommandConverter

# Credits:
# General repo credits.
# Thanks to TrustyJAID for the two converter for the bulk command arguments! (https://github.com/TrustyJAID/Trusty-cogs/blob/main/roletools/converter.py)
# Thanks to Yami for the technique in the init file of some cogs to load the interaction client only if it is not already loaded! Before this fix, when a user clicked a button, the actions would be run about 10 times, causing a huge spam and loop in the channel.
# Thanks to Kuro for the emoji converter (https://canary.discord.com/channels/133049272517001216/133251234164375552/1014520590239019048)!

_: Translator = Translator("CommandsButtons", __file__)


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
class CommandsButtons(Cog):
    """A cog to allow a user to execute a command by clicking on a button!"""

    def __init__(self, bot: Red) -> None:
        super().__init__(bot=bot)

        self.config: Config = Config.get_conf(
            self,
            identifier=205192943327321000143939875896557571750,  # 370638632963
            force_registration=True,
        )
        self.CONFIG_SCHEMA: int = 2
        self.config.register_global(CONFIG_SCHEMA=None)
        self.config.register_guild(commands_buttons={})

        self.cache: typing.List[commands.Context] = []

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
                commands_buttons = await self.config.guild_from_id(guild_id).commands_buttons()
                for message in commands_buttons:
                    message_data = commands_buttons[message].copy()
                    for emoji in message_data:
                        data = commands_buttons[message].pop(emoji)
                        data["emoji"] = emoji
                        config_identifier = CogsUtils.generate_key(
                            length=5, existing_keys=commands_buttons[message]
                        )
                        commands_buttons[message][config_identifier] = data
                await self.config.guild_from_id(guild_id).commands_buttons.set(commands_buttons)
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
            config = all_guilds[guild]["commands_buttons"]
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
        if not interaction.data["custom_id"].startswith("commands_buttons"):
            return
        config = await self.config.guild(interaction.guild).commands_buttons.all()
        if f"{interaction.channel.id}-{interaction.message.id}" not in config:
            await interaction.response.send_message(
                _("This message is not in Config."), ephemeral=True
            )
            return
        if config_identifier not in config[f"{interaction.channel.id}-{interaction.message.id}"]:
            await interaction.response.send_message(
                _("This button is not in Config."), ephemeral=True
            )
            return
        command = config[f"{interaction.channel.id}-{interaction.message.id}"][config_identifier][
            "command"
        ]
        if (
            (command_object := interaction.client.get_command(command)) is not None
            and command == command_object.qualified_name
            and command_object.params
        ):
            params = command_object.params
            if len(params) > 5:
                params = {name: param for name, param in params.items() if not param.required}
            modal = discord.ui.Modal(title="Invoke Command")
            modal.on_submit = lambda interaction: interaction.response.defer()
            text_inputs: typing.List[discord.ui.TextInput] = []
            for name, param in params.items():
                text_input = discord.ui.TextInput(
                    label=name.replace("_", " ").title(),
                    style=discord.TextStyle.short,
                    placeholder=repr(param)[repr(param).index(":", 12) + 1 : -2][:100],
                    default=str(param.default)
                    if param.default != inspect._empty and False
                    else None,
                    required=param.required,
                )
                text_inputs.append(text_input)
                modal.add_item(text_input)
            await interaction.response.send_modal(modal)
            if await modal.wait():
                return  # Timeout.
            command += " " + " ".join(
                [
                    (f'"{text_input.value}"' if " " in text_input.value else text_input.value)
                    for text_input in text_inputs
                    if text_input.value and str(text_input.value) != text_input.default
                ]
            )
        else:
            await interaction.response.defer(ephemeral=True)
        context = await CogsUtils.invoke_command(
            bot=interaction.client,
            author=interaction.user,
            channel=interaction.channel,
            command=command,
            __is_mocked__=True,
        )
        if not isinstance(context, commands.Context) or not context.valid:
            await interaction.followup.send(_("This command doesn't exist."), ephemeral=True)
            return

        if not await discord.utils.async_all([check(context) for check in context.command.checks]):
            await interaction.followup.send(
                _("You are not allowed to execute this command."), ephemeral=True
            )
            return

        self.cache.append(context)

    @commands.Cog.listener()
    async def on_command_completion(self, ctx: commands.Context) -> None:
        if ctx in self.cache:
            self.cache.remove(ctx)

    @commands.Cog.listener()
    async def on_command_error(
        self, ctx: commands.Context, error: commands.CommandError, unhandled_by_cog: bool = False
    ) -> None:
        if ctx not in self.cache:
            return
        self.cache.remove(ctx)
        if isinstance(error, commands.CommandInvokeError):
            await asyncio.sleep(0.7)
            self.logger.error(
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
    @commands.bot_has_permissions(embed_links=True)
    @commands.hybrid_group()
    async def commandsbuttons(self, ctx: commands.Context) -> None:
        """Group of commands to use CommandsButtons."""
        pass

    @commandsbuttons.command(aliases=["+"])
    async def add(
        self,
        ctx: commands.Context,
        message: MyMessageConverter,
        command: str,
        emoji: typing.Optional[Emoji],
        style_button: typing.Optional[typing.Literal["1", "2", "3", "4"]] = "2",
        *,
        text_button: typing.Optional[commands.Range[str, 1, 100]] = None,
    ) -> None:
        """Add a command-button for a message.

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
        # if ctx.prefix != "/":
        new_ctx = await CogsUtils.invoke_command(
            bot=ctx.bot,
            author=ctx.author,
            channel=ctx.channel,
            command=command,
            prefix=ctx.prefix,
            message=ctx.message,
            invoke=False,
        )
        if not new_ctx.valid:
            raise commands.UserFeedbackCheckFailure(_("You have not specified a correct command."))
        if not await discord.utils.async_all([check(new_ctx) for check in new_ctx.command.checks]):
            raise commands.UserFeedbackCheckFailure(_("You can't execute yourself this command."))
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
        config = await self.config.guild(ctx.guild).commands_buttons.all()
        if f"{message.channel.id}-{message.id}" not in config:
            if message.components:
                raise commands.UserFeedbackCheckFailure(_("This message already has components."))
            config[f"{message.channel.id}-{message.id}"] = {}
        if len(config[f"{message.channel.id}-{message.id}"]) > 25:
            raise commands.UserFeedbackCheckFailure(
                _("I can't do more than 25 commands-buttons for one message.")
            )
        config_identifier = CogsUtils.generate_key(
            length=5, existing_keys=config[f"{message.channel.id}-{message.id}"]
        )
        config[f"{message.channel.id}-{message.id}"][config_identifier] = {
            "command": command,
            "emoji": f"{getattr(emoji, 'id', emoji)}" if emoji is not None else None,
            "style_button": int(style_button),
            "text_button": text_button,
        }
        view = self.get_buttons(config, message)
        message = await message.edit(view=view)
        self.views[message] = view
        await self.config.guild(ctx.guild).commands_buttons.set(config)
        await self.list.callback(self, ctx, message=message)

    @commandsbuttons.command()
    async def bulk(
        self,
        ctx: commands.Context,
        message: MyMessageConverter,
        commands_buttons: commands.Greedy[EmojiCommandConverter],
    ) -> None:
        """Add commands-buttons for a message.

        ```[p]commandsbuttons bulk <message> ":reaction1:|ping" ":reaction2:|ping" :reaction3:|ping"```
        """
        if len(commands_buttons) == 0:
            raise commands.UserFeedbackCheckFailure(
                _("You have not specified any valid command-button.")
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
                for emoji, command in commands_buttons[:19]:
                    if ctx.prefix != "/":
                        msg = ctx.message
                        msg.content = f"{ctx.prefix}{command}"
                        new_ctx = await ctx.bot.get_context(msg)
                        if not new_ctx.valid:
                            raise commands.UserFeedbackCheckFailure(
                                _("At least one of these commands is invalid.")
                            )
                    if emoji is None:
                        continue
                    await ctx.message.add_reaction(emoji)
            except discord.HTTPException:
                raise commands.UserFeedbackCheckFailure(
                    _(
                        "An emoji you selected seems invalid. Check that it is an emoji. If you have Nitro, you may have used a custom emoji from another server."
                    )
                )
        config = await self.config.guild(ctx.guild).commands_buttons.all()
        if f"{message.channel.id}-{message.id}" not in config:
            if message.components:
                raise commands.UserFeedbackCheckFailure(_("This message already has components."))
            config[f"{message.channel.id}-{message.id}"] = {}
        if len(config[f"{message.channel.id}-{message.id}"]) + len(commands_buttons) > 25:
            raise commands.UserFeedbackCheckFailure(
                _("I can't do more than 25 roles-buttons for one message.")
            )
        for emoji, command in commands_buttons:
            config_identifier = CogsUtils.generate_key(
                length=5, existing_keys=config[f"{message.channel.id}-{message.id}"]
            )
            config[f"{message.channel.id}-{message.id}"][config_identifier] = {
                "command": command,
                "emoji": f"{getattr(emoji, 'id', emoji)}" if emoji is not None else None,
                "style_button": 2,
                "text_button": None,
            }
        view = self.get_buttons(config, message)
        message = await message.edit(view=view)
        self.views[message] = view
        await self.config.guild(ctx.guild).commands_buttons.set(config)
        await self.list.callback(self, ctx, message=message)

    @commandsbuttons.command(aliases=["-"])
    async def remove(
        self, ctx: commands.Context, message: MyMessageConverter, config_identifier: str
    ) -> None:
        """Remove a command-button for a message.

        Use `[p]commandsbuttons list <message>` to find the config identifier.
        """
        config = await self.config.guild(ctx.guild).commands_buttons.all()
        if f"{message.channel.id}-{message.id}" not in config:
            raise commands.UserFeedbackCheckFailure(
                _("No command-button is configured for this message.")
            )
        if config_identifier not in config[f"{message.channel.id}-{message.id}"]:
            raise commands.UserFeedbackCheckFailure(
                _("I wasn't watching for this button on this message.")
            )
        del config[f"{message.channel.id}-{message.id}"][config_identifier]
        if config[f"{message.channel.id}-{message.id}"] == {}:
            del config[f"{message.channel.id}-{message.id}"]
            await message.edit(view=None)
        else:
            view = self.get_buttons(config, message)
            message = await message.edit(view=view)
            self.views[message] = view
        await self.config.guild(ctx.guild).commands_buttons.set(config)
        if f"{message.channel.id}-{message.id}" in config:
            await self.list.callback(self, ctx, message=message)
        else:
            await ctx.send(_("Commands-buttons cleared for this message."))

    @commandsbuttons.command()
    async def clear(self, ctx: commands.Context, message: MyMessageConverter) -> None:
        """Clear all commands-buttons for a message."""
        config = await self.config.guild(ctx.guild).commands_buttons.all()
        if f"{message.channel.id}-{message.id}" not in config:
            raise commands.UserFeedbackCheckFailure(
                _("No command-button is configured for this message.")
            )
        try:
            await message.edit(view=None)
        except discord.HTTPException:
            pass
        del config[f"{message.channel.id}-{message.id}"]
        await self.config.guild(ctx.guild).commands_buttons.set(config)
        await ctx.send(_("Commands-buttons cleared for this message."))

    @commands.bot_has_permissions(embed_links=True)
    @commandsbuttons.command()
    async def list(self, ctx: commands.Context, message: MyMessageConverter = None) -> None:
        """List all commands-buttons of this server or display the settings for a specific one."""
        commands_buttons = await self.config.guild(ctx.guild).commands_buttons()
        for command_button in commands_buttons:
            commands_buttons[command_button]["message"] = command_button
        if message is None:
            _commands_buttons = list(commands_buttons.values()).copy()
        elif f"{message.channel.id}-{message.id}" not in commands_buttons:
            raise commands.UserFeedbackCheckFailure(
                _("No command-button is configured for this message.")
            )
        else:
            _commands_buttons = commands_buttons.copy()
            _commands_buttons = [commands_buttons[f"{message.channel.id}-{message.id}"]]
        if not _commands_buttons:
            raise commands.UserFeedbackCheckFailure(_("No commands-buttons in this server."))
        embed: discord.Embed = discord.Embed(
            title=_("Commands Buttons"),
            description=_(
                "There is {len_commands_buttons} commands buttons in this server."
            ).format(len_commands_buttons=len(commands_buttons)),
            color=await ctx.embed_color(),
        )
        embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon)
        embeds = []
        for li in discord.utils.as_chunks(_commands_buttons, max_size=5):
            e = embed.copy()
            for command_button in li:
                value = _("Message Jump Link: {message_jump_link}\n").format(
                    message_jump_link=f"https://discord.com/channels/{ctx.guild.id}/{command_button['message'].replace('-', '/')}"
                )
                value += "\n".join(
                    [
                        f"• `{config_identifier}` - Emoji {(ctx.bot.get_emoji(int(data['emoji'])) if data['emoji'].isdigit() else data['emoji']) if data['emoji'] is not None else '`None`'} - Label `{data['text_button']}` - Command `[p]{data['command']}`"
                        for config_identifier, data in command_button.items()
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

    @commandsbuttons.command(hidden=True)
    async def purge(self, ctx: commands.Context) -> None:
        """Clear all commands-buttons for a guild."""
        await self.config.guild(ctx.guild).commands_buttons.clear()
        await ctx.send(_("All commands-buttons purged."))

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
                custom_id=f"commands_buttons {config_identifier}",
                disabled=False,
            )
            button.callback = partial(
                self.on_button_interaction, config_identifier=config_identifier
            )
            view.add_item(button)
        return view

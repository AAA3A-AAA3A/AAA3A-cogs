from AAA3A_utils import Cog, CogsUtils  # isort:skip
from redbot.core import commands, Config  # isort:skip
from redbot.core.bot import Red  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import asyncio

from functools import partial

from redbot.core.utils.chat_formatting import inline

from .converters import Emoji, EmojiCommandConverter


# Credits:
# General repo credits.
# Thanks to TrustyJAID for the two converter for the bulk command arguments! (https://github.com/TrustyJAID/Trusty-cogs/blob/main/roletools/converter.py)
# Thanks to Yami for the technique in the init file of some cogs to load the interaction client only if it is not already loaded! Before this fix, when a user clicked a button, the actions would be run about 10 times, causing a huge spam and loop in the channel.
# Thanks to Kuro for the emoji converter (https://canary.discord.com/channels/133049272517001216/133251234164375552/1014520590239019048)!

_ = Translator("CommandsButtons", __file__)


@cog_i18n(_)
class CommandsButtons(Cog):
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

        self.cache: typing.List[commands.Context] = []

    async def cog_load(self) -> None:
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

    async def on_button_interaction(self, interaction: discord.Interaction, config_identifier: str) -> None:
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
        if config_identifier not in config[f"{interaction.channel.id}-{interaction.message.id}"]:
            await interaction.followup.send(_("This button is not in Config."), ephemeral=True)
            return
        command = config[f"{interaction.channel.id}-{interaction.message.id}"][config_identifier][
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
    @commands.hybrid_group()
    async def commandsbuttons(self, ctx: commands.Context) -> None:
        """Group of commands to use CommandsButtons."""
        pass

    @commandsbuttons.command()
    async def add(
        self,
        ctx: commands.Context,
        message: discord.Message,
        emoji: Emoji,
        command: str,
        style_button: typing.Optional[typing.Literal["1", "2", "3", "4"]] = "2",
        *,
        text_button: typing.Optional[str] = None,
    ) -> None:
        """Add a command-button for a message.

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
        if ctx.prefix != "/":
            msg = ctx.message
            msg.content = f"{ctx.prefix}{command}"
            new_ctx = await ctx.bot.get_context(msg)
            if not new_ctx.valid:
                raise commands.UserFeedbackCheckFailure(
                    _("You have not specified a correct command.")
                )
        if ctx.interaction is None:
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
        view = self.get_buttons(config, message)
        await message.edit(view=view)
        self.cogsutils.views.append(view)
        await self.config.guild(ctx.guild).commands_buttons.set(config)

    @commandsbuttons.command()
    async def bulk(
        self,
        ctx: commands.Context,
        message: discord.Message,
        commands_buttons: commands.Greedy[EmojiCommandConverter],
    ) -> None:
        """Add commands-buttons for a message.

        ```[p]commandsbuttons bulk <message> ":reaction1:|ping" ":reaction2:|ping" :reaction3:|ping"```
        """
        if message.author != ctx.guild.me:
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
        if ctx.interaction is None:
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
        view = self.get_buttons(config, message)
        await message.edit(view=view)
        self.cogsutils.views.append(view)
        await self.config.guild(ctx.guild).commands_buttons.set(config)

    @commandsbuttons.command()
    async def remove(self, ctx: commands.Context, message: discord.Message, emoji: Emoji) -> None:
        """Remove a command-button for a message."""
        if message.author != ctx.guild.me:
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
        if config[f"{message.channel.id}-{message.id}"] == {}:
            del config[f"{message.channel.id}-{message.id}"]
            await message.edit(view=None)
        else:
            view = self.get_buttons(config, message)
            await message.edit(view=view)
        self.cogsutils.views.append(view)
        await self.config.guild(ctx.guild).commands_buttons.set(config)

    @commandsbuttons.command()
    async def clear(self, ctx: commands.Context, message: discord.Message) -> None:
        """Clear all commands-buttons for a message."""
        if message.author != ctx.guild.me:
            raise commands.UserFeedbackCheckFailure(
                _("I have to be the author of the message for the role-button to work.")
            )
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

    @commandsbuttons.command(hidden=True)
    async def purge(self, ctx: commands.Context) -> None:
        """Clear all commands-buttons for a guild."""
        await self.config.guild(ctx.guild).commands_buttons.clear()

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
            try:
                int(config_identifier)
            except ValueError:
                b = config_identifier
            else:
                b = str(self.bot.get_emoji(int(config_identifier)))
            button = discord.ui.Button(
                label=config[message][config_identifier]["text_button"],
                emoji=b,
                style=discord.ButtonStyle(config[message][config_identifier].get("style_button", 2)),
                custom_id=f"roles_buttons {config_identifier}",
                disabled=False,
            )
            button.callback = partial(self.on_button_interaction, config_identifier=config_identifier)
            view.add_item(button)
        return view

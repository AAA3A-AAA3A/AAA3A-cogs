from .AAA3A_utils.cogsutils import CogsUtils  # isort:skip
from .AAA3A_utils.cogsutils import Buttons, Modal  # isort:skip
import discord  # isort:skip
from redbot.core import commands  # isort:skip

import asyncio
import typing

import yaml
from redbot.core import Config

# Credits:
# Thanks to @epic guy on Discord for the basic syntax (command groups, commands) and also commands (await ctx.send, await ctx.author.send, await ctx.message.delete())!
# Thanks to the developers of the cogs I added features to as it taught me how to make a cog! (Chessgame by WildStriker, Captcha by Kreusada, Speak by Epic guy and Rommer by Dav)
# Thanks to all the people who helped me with some commands in the #coding channel of the redbot support server!

def _(untranslated: str):
    return untranslated

class YAMLConverter(commands.Converter):

    async def convert(self, ctx: commands.Context, argument: str) -> typing.Dict:
        try:
            argument_dict = yaml.safe_load(argument)
        except Exception:
            raise discord.ext.commands.BadArgument(_("Error parsing YAML. Please make sure the format is valid (a YAML validator may help)").format(**locals()))
        # general
        required_arguments = ["title", "button", "modal"]
        optional_arguments = ["channel", "messages"]
        for arg in required_arguments:
            if arg not in argument_dict:
                raise discord.ext.commands.BadArgument(_("The argument `/{arg}` is required in the root in the YAML.").format(**locals()))
        for arg in argument_dict:
            if arg is not None in required_arguments + optional_arguments:
                raise discord.ext.commands.BadArgument(_("The agument `/{arg}` is invalid in in the YAML. Check the spelling.").format(**locals()))
        # button
        required_arguments = ["label", "emoji"]
        optional_arguments = ["style"]
        for arg in required_arguments:
            if arg not in argument_dict["button"]:
                raise discord.ext.commands.BadArgument(_("The argument `/button/{arg}` is required in the YAML.").format(**locals()))
        for arg in argument_dict["button"]:
            if arg is not None in required_arguments + optional_arguments:
                raise discord.ext.commands.BadArgument(_("The agument `/button/{arg}` is invalid in the YAML. Check the spelling.").format(**locals()))
        if "style" in argument_dict["button"]:
            argument_dict["button"]["style"] = str(argument_dict["button"]["style"])
            try:
                style = int(argument_dict["button"]["style"])
            except ValueError:
                raise discord.ext.commands.BadArgument(_("The agument `/button/style` must be a number between 1 and 4.").format(**locals()))
            if not 1 <= style <= 4:
                raise discord.ext.commands.BadArgument(_("The agument `/button/style` must be a number between 1 and 4.").format(**locals()))
            argument_dict["button"]["style"] = style
        else:
            argument_dict["button"]["style"] = 2
        # modal
        if not isinstance(argument_dict["modal"], typing.List):
            raise discord.ext.commands.BadArgument(_("The argument `/button/modal` must be a list of TextInputs.").format(**locals()))
        required_arguments = ["label"]
        optional_arguments = ["style", "required", "default"]
        count = 0
        for input in argument_dict["modal"]:
            count += 1
            for arg in required_arguments:
                if arg not in input:
                    raise discord.ext.commands.BadArgument(_("The argument `/modal/{count}/{arg}` is required in the YAML.").format(**locals()))
            for arg in input:
                if arg is not None in required_arguments + optional_arguments:
                    raise discord.ext.commands.BadArgument(_("The agument `/modal/{count}/{arg}` is invalid in the YAML. Check the spelling.").format(**locals()))
            if "style" in input:
                input["style"] = str(input["style"])
                try:
                    style = int(input["style"])
                except ValueError:
                    raise discord.ext.commands.BadArgument(_("The agument `/modal/{count}/style` must be a number between 1 and 2.").format(**locals()))
                if not 1 <= style <= 2:
                    raise discord.ext.commands.BadArgument(_("The agument `/modal/{count}/style` must be a number between 1 and 2.").format(**locals()))
                input["style"] = style
            else:
                input["style"] = 2
            if "required" in input:
                def convert_to_bool(argument: str) -> bool:
                    lowered = argument.lower()
                    if lowered in ('yes', 'y', 'true', 't', '1', 'enable', 'on'):
                        return True
                    elif lowered in ('no', 'n', 'false', 'f', '0', 'disable', 'off'):
                        return False
                    else:
                        raise discord.ext.commands.BadBoolArgument(lowered)
                input["required"] = str(input["required"])
                try:
                    input["required"] = convert_to_bool(input["required"])
                except discord.ext.commands.BadBoolArgument:
                    raise discord.ext.commands.BadArgument(_("The agument `/modal/{count}/required` must be a boolean (True or False).").format(**locals()))
            else:
                input["required"] = True
            if "default" not in input:
                input["default"] = ""
        # channel
        if "channel" in argument_dict:
            argument_dict["channel"] = str(argument_dict["channel"])
            channel = await discord.ext.commands.TextChannelConverter().convert(ctx, argument_dict["channel"])
            if channel is not None and hasattr(channel, 'id'):
                argument_dict["channel"] = channel.id
            else:
                argument_dict["channel"] = ctx.channel.id
        else:
            argument_dict["channel"] = ctx.channel.id
        # messages
        if "messages" in argument_dict:
            if "error" not in argument_dict["messages"]:
                argument_dict["messages"]["error"] = None
            if "done" not in argument_dict["messages"]:
                argument_dict["messages"]["done"] = None
        else:
            argument_dict["messages"] = {"error": None, "done": None}
        return argument_dict

class DiscordModals(commands.Cog):
    """A cog to use Discord Modals, forms with graphic interface!"""

    def __init__(self, bot):
        self.bot = bot
        self.config: Config = Config.get_conf(
            self,
            identifier=897374386384,
            force_registration=True,
        )
        self.discordmodals_guild = {
            "modals": {},
        }

        self.config.register_guild(**self.discordmodals_guild)

        asyncio.create_task(self.load_buttons())

        self.cogsutils = CogsUtils(cog=self)
        self.cogsutils._setup()

    async def load_buttons(self):
        all_guilds = await self.config.all_guilds()
        for guild in all_guilds:
            for modal in all_guilds[guild]["modals"]:
                try:
                    button = all_guilds[guild]["modals"][modal]["button"]
                    button["function"] = self.send_modal
                    self.bot.add_view(Buttons.from_dict_cogsutils(button), message_id=int((str(modal).split("-"))[1]))
                except Exception as e:
                    self.log.error(f"The Button View could not be added correctly for the {guild}-{modal} message.", exc_info=e)

    async def send_modal(self, view: Buttons, interaction: discord.Interaction):
        config = await self.config.guild(interaction.message.guild).modals()
        if f"{interaction.message.channel.id}-{interaction.message.id}" not in config:
            return
        try:
            modal = config[f"{interaction.message.channel.id}-{interaction.message.id}"]["modal"]
            modal["function"] = self.send_embed_with_responses
            await interaction.response.send_modal(Modal.from_dict_cogsutils(modal))
        except Exception as e:
            self.log.error(f"The Modal of the {interaction.message.guild.id}-{interaction.message.channel.id}-{interaction.message.id} message did not work properly.", exc_info=e)
            if not interaction.response.is_done():
                await interaction.response.send_message("Sorry. An error has occurred.", ephemeral=True)

    async def send_embed_with_responses(self, view: Modal, interaction: discord.Interaction, values: typing.List):
        config = await self.config.guild(interaction.message.guild).modals()
        if f"{interaction.message.channel.id}-{interaction.message.id}" not in config:
            return
        config = config[f"{interaction.message.channel.id}-{interaction.message.id}"]
        try:
            channel = interaction.guild.get_channel(config["channel"])
            if channel is None:
                await interaction.response.send_message("The channel in which I was to send the results of this Modal no longer exists. Please notify an administrator of this server.", ephemeral=True)
                return
            if not self.cogsutils.check_permissions_for(channel=channel, user=interaction.guild.me, check=["embed_links", "send_messages", "view_channel"]):
                await interaction.response.send_message("I don't have sufficient permissions in the destination channel (view channel, send messages, send embeds). Please notify an administrator of this server.", ephemeral=True)
                return
            embed: discord.Embed = discord.Embed()
            embed.title = config["title"]
            for value in values:
                if not getattr(value, 'label') or not getattr(value, 'value'):
                    continue
                try:
                    embed.add_field(name=value.label, value=value.value, inline=False)
                except Exception:
                    pass
            embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar)
            embed.set_footer(text=interaction.guild.name, icon_url=interaction.guild.icon)
            await channel.send(embed=embed)
        except Exception as e:
            self.log.error(f"The Modal of the {interaction.message.guild.id}-{interaction.message.channel.id}-{interaction.message.id} message did not work properly.", exc_info=e)
            await interaction.response.send_message(config["messages"]["error"] or "Sorry. An error has occurred.", ephemeral=True)
        else:
            await interaction.response.send_message(config["messages"]["done"] or "Thank you for sending this Modal!", ephemeral=True)

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        await self.cogsutils.check_in_listener(message, False)
        config = await self.config.guild(message.guild).modals.all()
        if f"{message.channel.id}-{message.id}" not in config:
            return
        del config[f"{message.channel.id}-{message.id}"]
        await self.config.guild(message.guild).modals.set(config)

    @commands.guild_only()
    @commands.mod_or_permissions(manage_guild=True)
    @commands.group()
    async def discordmodals(self, ctx: commands.Context):
        """Group of commands for use ReactToCommand.
        """
        pass

    @discordmodals.command()
    async def add(self, ctx: commands.Context, message: discord.Message, *, argument: YAMLConverter):
        """Add a Modal to a message.
        Use YAML syntax to set up everything.

        **Example:**
        ```
        [p]discordmodals add 1234567890
        title: Report a bug
        button:
          label: Report
          emoji: ⚠️
          style: 4 # blurple = 1, grey = 2, green = 3, red = 4
        modal:
          - label: What is the problem?
            style: 2 # short = 1, paragraph = 2
            required: True
            default: None
        channel: général # id, mention, name
        messages:
          error: Error!
          done: Form submitted.
        ```
        The `style`, `default`, `channel`, `required` and `messages` are not required.
        """
        if not message.author == ctx.guild.me:
            await ctx.send(_("I have to be the author of the message for the button to work.").format(**locals()))
            return
        config = await self.config.guild(ctx.guild).modals.all()
        if f"{message.channel.id}-{message.id}" in config:
            await ctx.send(_("This message already has a Modal.").format(**locals()))
            return
        try:
            argument["button"]["custom_id"] = "DiscordModals_" + self.cogsutils.generate_key(number=15)
            view = Buttons(timeout=None, buttons=[argument["button"]], function=self.send_modal, infinity=True)
            await message.edit(view=view)
        except discord.HTTPException:
            await ctx.send(_("Sorry. An error occurred when I tried to put the button on the message.").format(**locals()))
            return
        modal = Modal(title=argument["title"], inputs=argument["modal"], function=self.send_embed_with_responses)
        config[f"{message.channel.id}-{message.id}"] = {"title": argument["title"], "button": view.to_dict_cogsutils(True), "channel": argument["channel"], "modal": modal.to_dict_cogsutils(True), "messages": {"error": argument["messages"]["error"], "done": argument["messages"]["done"]}}
        await self.config.guild(ctx.guild).modals.set(config)
        await ctx.tick()

    @discordmodals.command()
    async def remove(self, ctx: commands.Context, message: discord.Message):
        """Remove a Modal to a message.
        """
        if not message.author == ctx.guild.me:
            await ctx.send(_("I have to be the author of the message for the Modal to work.").format(**locals()))
            return
        config = await self.config.guild(ctx.guild).modals.all()
        if f"{message.channel.id}-{message.id}" not in config:
            await ctx.send(_("No Modal is configured for this message.").format(**locals()))
            return
        try:
            await message.edit(view=None)
        except discord.HTTPException:
            pass
        del config[f"{message.channel.id}-{message.id}"]
        await self.config.guild(ctx.guild).modals.set(config)
        await ctx.tick()

    @discordmodals.command(hidden=True)
    async def purge(self, ctx: commands.Context):
        """Clear all Modals to a **guild**.
        """
        await self.config.guild(ctx.guild).modals.clear()
        await ctx.tick()
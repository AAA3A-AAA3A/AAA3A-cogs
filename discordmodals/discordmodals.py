from .AAA3A_utils import CogsUtils  # isort:skip
from .AAA3A_utils import Buttons, Modal  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
from redbot.core.bot import Red  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import yaml
from redbot.core import Config

# Credits:
# General repo credits.

_ = Translator("DiscordModals", __file__)

if CogsUtils().is_dpy2:
    from functools import partial

    hybrid_command = partial(commands.hybrid_command, with_app_command=False)
    hybrid_group = partial(commands.hybrid_group, with_app_command=False)
else:
    hybrid_command = commands.command
    hybrid_group = commands.group


class YAMLConverter(commands.Converter):
    async def convert(
        self, ctx: commands.Context, argument: str
    ) -> typing.Dict[str, typing.Union[str, bool, typing.Dict, typing.List]]:
        try:
            argument_dict = yaml.safe_load(argument)
        except Exception:
            raise discord.ext.commands.BadArgument(
                _(
                    "Error parsing YAML. Please make sure the format is valid (a YAML validator may help)"
                )
            )
        # general
        required_arguments = ["title", "button", "modal"]
        optional_arguments = ["channel", "anonymous", "messages"]
        for arg in required_arguments:
            if arg not in argument_dict:
                raise discord.ext.commands.BadArgument(
                    _("The argument `/{arg}` is required in the root in the YAML.").format(arg=arg)
                )
        for arg in argument_dict:
            if arg not in required_arguments + optional_arguments:
                raise discord.ext.commands.BadArgument(
                    _(
                        "The agument `/{arg}` is invalid in in the YAML. Check the spelling."
                    ).format(arg=aarg)
                )
        # button
        required_arguments = ["label"]
        optional_arguments = ["emoji", "style"]
        for arg in required_arguments:
            if arg not in argument_dict["button"]:
                raise discord.ext.commands.BadArgument(
                    _("The argument `/button/{arg}` is required in the YAML.").format(arg=arg)
                )
        for arg in argument_dict["button"]:
            if arg is not None in required_arguments + optional_arguments:
                raise discord.ext.commands.BadArgument(
                    _(
                        "The agument `/button/{arg}` is invalid in the YAML. Check the spelling."
                    ).format(arg=arg)
                )
        if "style" in argument_dict["button"]:
            argument_dict["button"]["style"] = str(argument_dict["button"]["style"])
            try:
                style = int(argument_dict["button"]["style"])
            except ValueError:
                raise discord.ext.commands.BadArgument(
                    _("The agument `/button/style` must be a number between 1 and 4.")
                )
            if not 1 <= style <= 4:
                raise discord.ext.commands.BadArgument(
                    _("The agument `/button/style` must be a number between 1 and 4.")
                )
            argument_dict["button"]["style"] = style
        else:
            argument_dict["button"]["style"] = 2
        # modal
        if not isinstance(argument_dict["modal"], typing.List):
            raise discord.ext.commands.BadArgument(
                _("The argument `/button/modal` must be a list of TextInputs.")
            )
        required_arguments = ["label"]
        optional_arguments = ["style", "required", "default", "placeholder"]
        for count, input in enumerate(argument_dict["modal"], start=1):
            count += 1
            for arg in required_arguments:
                if arg not in input:
                    raise discord.ext.commands.BadArgument(
                        _("The argument `/modal/{count}/{arg}` is required in the YAML.").format(
                            count=count, arg=arg
                        )
                    )
            for arg in input:
                if arg is not None in required_arguments + optional_arguments:
                    raise discord.ext.commands.BadArgument(
                        _(
                            "The agument `/modal/{count}/{arg}` is invalid in the YAML. Check the spelling."
                        ).format(count=count, arg=arg)
                    )
            if "style" in input:
                input["style"] = str(input["style"])
                try:
                    style = int(input["style"])
                except ValueError:
                    raise discord.ext.commands.BadArgument(
                        _(
                            "The agument `/modal/{count}/style` must be a number between 1 and 2."
                        ).format(count=count)
                    )
                if not 1 <= style <= 2:
                    raise discord.ext.commands.BadArgument(
                        _(
                            "The agument `/modal/{count}/style` must be a number between 1 and 2."
                        ).format(count=count)
                    )
                input["style"] = style
            else:
                input["style"] = 2
            if "required" in input:

                def convert_to_bool(argument: str) -> bool:
                    lowered = argument.lower()
                    if lowered in {"yes", "y", "true", "t", "1", "enable", "on"}:
                        return True
                    elif lowered in {"no", "n", "false", "f", "0", "disable", "off"}:
                        return False
                    else:
                        raise discord.ext.commands.BadBoolArgument(lowered)

                input["required"] = str(input["required"])
                try:
                    input["required"] = convert_to_bool(input["required"])
                except discord.ext.commands.BadBoolArgument:
                    raise discord.ext.commands.BadArgument(
                        _(
                            "The agument `/modal/{count}/required` must be a boolean (True or False)."
                        ).format(count=count)
                    )
            else:
                input["required"] = True
            if "default" not in input or input["default"] == "None":
                input["default"] = ""
            if "placeholder" not in input or input["placeholder"] == "None":
                input["placeholder"] = ""
            if "min_length" not in input or input["min_length"] == "None":
                input["min_length"] = None
            if "max_length" not in input or input["max_length"] == "None":
                input["max_length"] = None
        # channel
        if "channel" in argument_dict:
            argument_dict["channel"] = str(argument_dict["channel"])
            channel = await discord.ext.commands.TextChannelConverter().convert(
                ctx, argument_dict["channel"]
            )
            if channel is not None and hasattr(channel, "id"):
                argument_dict["channel"] = channel.id
            else:
                argument_dict["channel"] = ctx.channel.id
        else:
            argument_dict["channel"] = ctx.channel.id
        # anonymous
        if "anonymous" not in argument_dict:
            argument_dict["anonymous"] = False
        # messages
        if "messages" in argument_dict:
            if "error" not in argument_dict["messages"]:
                argument_dict["messages"]["error"] = None
            if "done" not in argument_dict["messages"]:
                argument_dict["messages"]["done"] = None
        else:
            argument_dict["messages"] = {"error": None, "done": None}
        return argument_dict


@cog_i18n(_)
class DiscordModals(commands.Cog):
    """A cog to use Discord Modals, forms with graphic interface!"""

    def __init__(self, bot: Red) -> None:
        self.bot: Red = bot

        self.config: Config = Config.get_conf(
            self,
            identifier=205192943327321000143939875896557571750,  # 897374386384
            force_registration=True,
        )
        self.discordmodals_guild: typing.Dict[
            str, typing.Dict[str, typing.Dict[str, typing.Any]]
        ] = {
            "modals": {},
        }
        self.config.register_guild(**self.discordmodals_guild)

        self.cogsutils: CogsUtils = CogsUtils(cog=self)
        self.purge.no_slash = True

    async def cog_load(self) -> None:
        await self.load_buttons()

    async def load_buttons(self) -> None:
        all_guilds = await self.config.all_guilds()
        for guild in all_guilds:
            for modal in all_guilds[guild]["modals"]:
                try:
                    button = all_guilds[guild]["modals"][modal]["button"]
                    button["function"] = self.send_modal
                    view = Buttons.from_dict_cogsutils(button)
                    self.bot.add_view(view, message_id=int((str(modal).split("-"))[1]))
                    self.cogsutils.views.append(view)
                except Exception as e:
                    self.log.error(
                        f"The Button View could not be added correctly for the {guild}-{modal} message.",
                        exc_info=e,
                    )

    async def send_modal(self, view: Buttons, interaction: discord.Interaction) -> None:
        config = await self.config.guild(interaction.message.guild).modals()
        if f"{interaction.message.channel.id}-{interaction.message.id}" not in config:
            return
        try:
            modal = config[f"{interaction.message.channel.id}-{interaction.message.id}"]["modal"]
            modal["function"] = self.send_embed_with_responses
            await interaction.response.send_modal(Modal.from_dict_cogsutils(modal))
        except Exception as e:
            self.log.error(
                f"The Modal of the {interaction.message.guild.id}-{interaction.message.channel.id}-{interaction.message.id} message did not work properly.",
                exc_info=e,
            )
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    _("Sorry. An error has occurred."), ephemeral=True
                )

    async def send_embed_with_responses(
        self, view: Modal, interaction: discord.Interaction, values: typing.List
    ) -> None:
        config = await self.config.guild(interaction.message.guild).modals()
        if f"{interaction.message.channel.id}-{interaction.message.id}" not in config:
            return
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=True)
        config = config[f"{interaction.message.channel.id}-{interaction.message.id}"]
        try:
            channel = interaction.guild.get_channel(config["channel"])
            if channel is None:
                await interaction.followup.send(
                    _(
                        "The channel in which I was to send the results of this Modal no longer exists. Please notify an administrator of this server."
                    ),
                    ephemeral=True,
                )
                return
            if not self.cogsutils.check_permissions_for(
                channel=channel,
                user=interaction.guild.me,
                check=["embed_links", "send_messages", "view_channel"],
            ):
                await interaction.followup.send(
                    _(
                        "I don't have sufficient permissions in the destination channel (view channel, send messages, send embeds). Please notify an administrator of this server."
                    ),
                    ephemeral=True,
                )
                return
            embed: discord.Embed = discord.Embed()
            embed.title = config["title"]
            if "anonymous" not in config:
                embed.set_author(name=interaction.user, icon_url=interaction.user.display_avatar)
            elif not config["anonymous"]:
                embed.set_author(name=interaction.user, icon_url=interaction.user.display_avatar)
                embed.color = interaction.user.color
            else:
                embed.set_author(
                    name="Anonymous",
                    icon_url="https://forum.mtasa.com/uploads/monthly_2016_10/Anonyme.png.4060431ce866962fa496657f752d5613.png",
                )
            for value in values:
                if not hasattr(value, "label") or not hasattr(value, "value"):
                    continue
                try:
                    embed.add_field(name=value.label, value=value.value, inline=False)
                except Exception:
                    pass
            embed.set_footer(text=interaction.guild.name, icon_url=interaction.guild.icon)
            await channel.send(embed=embed)
        except Exception as e:
            self.log.error(
                f"The Modal of the {interaction.message.guild.id}-{interaction.message.channel.id}-{interaction.message.id} message did not work properly.",
                exc_info=e,
            )
            await interaction.followup.send(
                config["messages"]["error"] or _("Sorry. An error has occurred."), ephemeral=True
            )
        else:
            await interaction.followup.send(
                config["messages"]["done"] or _("Thank you for sending this Modal!"),
                ephemeral=True,
            )

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message) -> None:
        if message.guild is None:
            return
        config = await self.config.guild(message.guild).modals.all()
        if f"{message.channel.id}-{message.id}" not in config:
            return
        del config[f"{message.channel.id}-{message.id}"]
        await self.config.guild(message.guild).modals.set(config)

    @commands.guild_only()
    @commands.mod_or_permissions(manage_guild=True)
    @hybrid_group()
    async def discordmodals(self, ctx: commands.Context) -> None:
        """Group of commands for use ReactToCommand."""
        pass

    @discordmodals.command()
    async def add(
        self, ctx: commands.Context, message: discord.Message, *, argument: YAMLConverter
    ) -> None:
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
            placeholder: None
            min_length: None
            max_length: None
        channel: general # id, mention, name
        anonymous: False
        messages:
          error: Error!
          done: Form submitted.
        ```
        The `emoji`, `style`, `required`, `default`, `placeholder`, `min_length`, `max_length`, `channel`, `anonymous` and `messages` are not required.
        """
        if not message.author == ctx.guild.me:
            raise commands.UserFeedbackCheckFailure(
                _("I have to be the author of the message for the button to work.")
            )
        config = await self.config.guild(ctx.guild).modals.all()
        if f"{message.channel.id}-{message.id}" in config:
            raise commands.UserFeedbackCheckFailure(_("This message already has a Modal."))
        try:
            argument["button"][
                "custom_id"
            ] = f"DiscordModals_{self.cogsutils.generate_key(length=10)}"
            view = Buttons(
                timeout=None, buttons=[argument["button"]], function=self.send_modal, infinity=True
            )
            await message.edit(view=view)
            self.cogsutils.views.append(view)
        except discord.HTTPException:
            raise commands.UserFeedbackCheckFailure(
                _("Sorry. An error occurred when I tried to put the button on the message.")
            )
        modal = Modal(
            title=argument["title"],
            inputs=argument["modal"],
            function=self.send_embed_with_responses,
            custom_id=f"DiscordModals_{self.cogsutils.generate_key(length=10)}",
        )
        config[f"{message.channel.id}-{message.id}"] = {
            "title": argument["title"],
            "button": view.to_dict_cogsutils(True),
            "channel": argument["channel"],
            "modal": modal.to_dict_cogsutils(True),
            "anonymous": argument["anonymous"],
            "messages": {
                "error": argument["messages"]["error"],
                "done": argument["messages"]["done"],
            },
        }
        await self.config.guild(ctx.guild).modals.set(config)

    @discordmodals.command()
    async def remove(self, ctx: commands.Context, message: discord.Message) -> None:
        """Remove a Modal to a message."""
        if not message.author == ctx.guild.me:
            raise commands.UserFeedbackCheckFailure(
                _("I have to be the author of the message for the Modal to work.")
            )
        config = await self.config.guild(ctx.guild).modals.all()
        if f"{message.channel.id}-{message.id}" not in config:
            raise commands.UserFeedbackCheckFailure(_("No Modal is configured for this message."))
        try:
            await message.edit(view=None)
        except discord.HTTPException:
            pass
        del config[f"{message.channel.id}-{message.id}"]
        await self.config.guild(ctx.guild).modals.set(config)

    @discordmodals.command(hidden=True)
    async def purge(self, ctx: commands.Context) -> None:
        """Clear all Modals to a **guild**."""
        await self.config.guild(ctx.guild).modals.clear()

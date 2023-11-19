from AAA3A_utils import Cog, CogsUtils, Menu  # isort:skip
from redbot.core import commands, Config  # isort:skip
from redbot.core.bot import Red  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import asyncio
import json
import re
from copy import deepcopy
from functools import partial

import yaml

try:
    from emoji import UNICODE_EMOJI_ENGLISH as EMOJI_DATA  # emoji<2.0.0
except ImportError:
    from emoji import EMOJI_DATA  # emoji>=2.0.0

from redbot.core.utils.chat_formatting import humanize_list, box

# Credits:
# General repo credits.

_ = Translator("DiscordModals", __file__)


class MyMessageConverter(commands.MessageConverter):
    async def convert(self, ctx: commands.Context, argument: str) -> discord.Message:
        message = await super().convert(ctx, argument=argument)
        if message.author != ctx.me:
            raise commands.UserFeedbackCheckFailure(
                _("I have to be the author of the message. You can use EmbedUtils by AAA3A to send one.")
            )
        return message


class Emoji(commands.EmojiConverter):
    async def convert(
        self, ctx: commands.Context, argument: str
    ) -> typing.Union[str, discord.Emoji]:
        # argument = argument.strip("\N{VARIATION SELECTOR-16}")
        if argument in EMOJI_DATA:
            return argument
        if argument in {
            "0",
            "1",
            "2",
            "3",
            "4",
            "5",
            "6",
            "7",
            "8",
            "9",
            "#",
            "*",
            "🇦",
            "🇧",
            "🇨",
            "🇩",
            "🇪",
            "🇫",
            "🇬",
            "🇭",
            "🇮",
            "🇯",
            "🇰",
            "🇱",
            "🇲",
            "🇳",
            "🇴",
            "🇵",
            "🇶",
            "🇷",
            "🇸",
            "🇹",
            "🇺",
            "🇻",
            "🇼",
            "🇽",
            "🇾",
            "🇿",
        }:
            return argument
        return await super().convert(ctx, argument=argument)


class RoleOrMemberConverter(commands.Converter):
    async def convert(
        self, ctx: commands.Context, argument: str
    ) -> typing.Union[discord.Role, discord.Member]:
        try:
            return await commands.RoleConverter().convert(ctx, argument=argument)
        except commands.BadArgument as e:
            try:
                return await commands.MemberConverter().convert(ctx, argument=argument)
            except commands.BadArgument:
                raise e


class ModalConverter(commands.Converter):
    async def convert(
        self, ctx: commands.Context, argument: str
    ) -> typing.Dict[str, typing.Union[str, bool, typing.Dict, typing.List]]:
        try:
            argument_dict = yaml.safe_load(argument)
        except Exception:
            raise commands.BadArgument(
                _(
                    "Error parsing YAML. Please make sure the format is valid (a YAML validator may help)"
                )
            )
        # general
        required_arguments = ["title", "button", "modal"]
        optional_arguments = [
            "channel",
            "anonymous",
            "messages",
            "pings",
            "whitelist_roles",
            "blacklist_roles",
        ]
        for arg in required_arguments:
            if arg not in argument_dict:
                raise commands.BadArgument(
                    _("The argument `/{arg}` is required in the root in the YAML.").format(arg=arg)
                )
        for arg in argument_dict:
            if arg not in required_arguments + optional_arguments:
                raise commands.BadArgument(
                    _(
                        "The argument `/{arg}` is invalid in in the YAML. Check the spelling."
                    ).format(arg=arg)
                )
        # button
        required_arguments = ["label"]
        optional_arguments = ["emoji", "style"]
        for arg in required_arguments:
            if arg not in argument_dict["button"]:
                raise commands.BadArgument(
                    _("The argument `/button/{arg}` is required in the YAML.").format(arg=arg)
                )
        for arg in argument_dict["button"]:
            if arg not in required_arguments + optional_arguments:
                raise commands.BadArgument(
                    _(
                        "The argument `/button/{arg}` is invalid in the YAML. Check the spelling."
                    ).format(arg=arg)
                )
        if "emoji" in argument_dict["button"]:
            argument_dict["button"]["emoji"] = await Emoji().convert(
                ctx, argument=argument_dict["button"]["emoji"]
            )
        if "style" in argument_dict["button"]:
            argument_dict["button"]["style"] = str(argument_dict["button"]["style"])
            try:
                style = int(argument_dict["button"]["style"])
            except ValueError:
                raise commands.BadArgument(
                    _("The argument `/button/style` must be a number between 1 and 4.")
                )
            if not 1 <= style <= 4:
                raise commands.BadArgument(
                    _("The argument `/button/style` must be a number between 1 and 4.")
                )
            argument_dict["button"]["style"] = style
        else:
            argument_dict["button"]["style"] = 2
        # modal
        if not isinstance(argument_dict["modal"], typing.List):
            raise commands.BadArgument(
                _("The argument `/button/modal` must be a list of text inputs.")
            )
        required_arguments = ["label"]
        optional_arguments = [
            "style",
            "required",
            "default",
            "placeholder",
            "min_length",
            "max_length",
        ]
        if len(argument_dict["modal"]) > 5:
            raise commands.BadArgument(_("You can only have 5 text inputs by modal."))
        for count, input in enumerate(argument_dict["modal"], start=1):
            count += 1
            for arg in required_arguments:
                if arg not in input:
                    raise commands.BadArgument(
                        _("The argument `/modal/{count}/{arg}` is required in the YAML.").format(
                            count=count, arg=arg
                        )
                    )
            for arg in input:
                if arg not in required_arguments + optional_arguments:
                    raise commands.BadArgument(
                        _(
                            "The argument `/modal/{count}/{arg}` is invalid in the YAML. Check the spelling."
                        ).format(count=count, arg=arg)
                    )
            if len(input["label"]) > 45:
                raise commands.BadArgument(
                    _(
                        "The argument `/modal/{count}/label` must be less than 45 characters long."
                    ).format(count=count, arg=arg)
                )
            if "style" in input:
                input["style"] = str(input["style"])
                try:
                    style = int(input["style"])
                except ValueError:
                    raise commands.BadArgument(
                        _(
                            "The argument `/modal/{count}/style` must be a number between 1 and 2."
                        ).format(count=count)
                    )
                if not 1 <= style <= 2:
                    raise commands.BadArgument(
                        _(
                            "The argument `/modal/{count}/style` must be a number between 1 and 2."
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
                        raise commands.BadBoolArgument(lowered)

                input["required"] = str(input["required"])
                try:
                    input["required"] = convert_to_bool(input["required"])
                except commands.BadBoolArgument:
                    raise commands.BadArgument(
                        _(
                            "The argument `/modal/{count}/required` must be a boolean (True or False)."
                        ).format(count=count)
                    )
            else:
                input["required"] = True
            if "default" not in input or input["default"] == "None":
                input["default"] = ""
            if len(input["default"]) > 4000:
                raise commands.BadArgument(
                    _(
                        "The argument `/modal/{count}/default` must be less than 4000 characters long."
                    ).format(count=count, arg=arg)
                )
            if "placeholder" not in input or input["placeholder"] == "None":
                input["placeholder"] = ""
            if len(input["placeholder"]) > 100:
                raise commands.BadArgument(
                    _(
                        "The argument `/modal/{count}/placeholder` must be less than 100 characters long."
                    ).format(count=count, arg=arg)
                )
            if "min_length" not in input or input["min_length"] == "None":
                input["min_length"] = None
            elif not 0 <= input["min_length"] <= 4000:
                raise commands.BadArgument(
                    _(
                        "The argument `/modal/{count}/min_length` must be between 0 and 4000."
                    ).format(count=count, arg=arg)
                )
            if "max_length" not in input or input["max_length"] == "None":
                input["max_length"] = None
            elif not 1 <= input["max_length"] <= 4000:
                raise commands.BadArgument(
                    _(
                        "The argument `/modal/{count}/max_length` must be between 0 and 4000."
                    ).format(count=count, arg=arg)
                )
        # channel
        if "channel" in argument_dict:
            argument_dict["channel"] = str(argument_dict["channel"])
            channel = await commands.TextChannelConverter().convert(ctx, argument_dict["channel"])
            if (
                channel is not None
                and hasattr(channel, "id")
                and channel.permissions_for(ctx.me).send_messages
            ):
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
            if "submit" not in argument_dict["messages"]:
                argument_dict["messages"]["submit"] = None
        else:
            argument_dict["messages"] = {"error": None, "submit": None}
        if "pings" not in argument_dict:
            argument_dict["pings"] = None
        else:
            argument_dict["pings"] = [
                (await RoleOrMemberConverter().convert(ctx, argument=ping.strip())).mention
                for ping in re.split(r",|;|\||-", str(argument_dict["pings"]))
            ]
        if "whitelist_roles" not in argument_dict:
            argument_dict["whitelist_roles"] = None
        else:
            argument_dict["whitelist_roles"] = [
                (await commands.RoleConverter().convert(ctx, argument=ping.strip())).id
                for ping in re.split(r",|;|\||-", str(argument_dict["whitelist_roles"]))
            ]
        if "blacklist_roles" not in argument_dict:
            argument_dict["blacklist_roles"] = None
        else:
            argument_dict["blacklist_roles"] = [
                (await commands.RoleConverter().convert(ctx, argument=ping.strip())).id
                for ping in re.split(r",|;|\||-", str(argument_dict["blacklist_roles"]))
            ]
        return argument_dict


@cog_i18n(_)
class DiscordModals(Cog):
    """A cog to use Discord Modals, forms with graphic interface!"""

    def __init__(self, bot: Red) -> None:
        super().__init__(bot=bot)

        self.config: Config = Config.get_conf(
            self,
            identifier=205192943327321000143939875896557571750,  # 897374386384
            force_registration=True,
        )
        self.CONFIG_SCHEMA: int = 2
        self.discordmodals_global: typing.Dict[str, typing.Optional[int]] = {
            "CONFIG_SCHEMA": None,
        }
        self.discordmodals_guild: typing.Dict[
            str, typing.Dict[str, typing.Union[str, typing.Dict[str, typing.Any]]]
        ] = {
            "modals": {},
        }
        self.config.register_global(**self.discordmodals_global)
        self.config.register_guild(**self.discordmodals_guild)

    async def cog_load(self) -> None:
        await super().cog_load()
        await self.edit_config_schema()
        asyncio.create_task(self.load_buttons())

    async def red_delete_data_for_user(self, *args, **kwargs) -> None:
        """Nothing to delete."""
        return

    async def red_get_data_for_user(self, *args, **kwargs) -> typing.Dict[str, typing.Any]:
        """Nothing to get."""
        return {}

    async def edit_config_schema(self) -> None:
        CONFIG_SCHEMA = await self.config.CONFIG_SCHEMA()
        if CONFIG_SCHEMA is None:
            CONFIG_SCHEMA = 1
            await self.config.CONFIG_SCHEMA(CONFIG_SCHEMA)
        if CONFIG_SCHEMA == self.CONFIG_SCHEMA:
            return
        if CONFIG_SCHEMA == 1:
            guild_group = self.config._get_base_group(self.config.GUILD)
            async with guild_group.all() as guilds_data:
                _guilds_data = deepcopy(guilds_data)
                for guild in _guilds_data:
                    if "submit" in list(guilds_data[guild]["modals"].values())[0]["messages"]:
                        break
                    for modal in guilds_data[guild]["modals"]:
                        guilds_data[guild]["modals"][modal]["messages"]["submit"] = guilds_data[
                            guild
                        ]["modals"][modal]["messages"]["done"]
                        del guilds_data[guild]["modals"][modal]["messages"]["done"]
                        button_data = {
                            "style": discord.ButtonStyle.secondary.value,
                            "label": None,
                            "emoji": None,
                            "custom_id": f"DiscordModals_{CogsUtils.generate_key(length=10)}",
                        }
                        button_data.update(
                            **guilds_data[guild]["modals"][modal]["button"]["buttons"][0]
                        )
                        guilds_data[guild]["modals"][modal]["button"] = button_data
                        for key in ["members", "check", "function", "function_args"]:
                            if key in guilds_data[guild]["modals"][modal]["modal"]:
                                del guilds_data[guild]["modals"][modal]["modal"][key]
            CONFIG_SCHEMA = 2
            await self.config.CONFIG_SCHEMA.set(CONFIG_SCHEMA)
        if CONFIG_SCHEMA < self.CONFIG_SCHEMA:
            CONFIG_SCHEMA = self.CONFIG_SCHEMA
            await self.config.CONFIG_SCHEMA.set(CONFIG_SCHEMA)
        self.log.info(
            f"The Config schema has been successfully modified to {self.CONFIG_SCHEMA} for the {self.qualified_name} cog."
        )

    async def load_buttons(self) -> None:
        await self.bot.wait_until_red_ready()
        all_guilds = await self.config.all_guilds()
        for guild in all_guilds:
            for message in all_guilds[guild]["modals"]:
                channel = self.bot.get_channel(int((str(message).split("-"))[0]))
                if channel is None:
                    continue
                message_id = int((str(message).split("-"))[1])
                try:
                    button = all_guilds[guild]["modals"][message]["button"]
                    if "custom_id" not in button:
                        button["custom_id"] = f"DiscordModals_{CogsUtils.generate_key(length=10)}"
                    button["style"] = discord.ButtonStyle(
                        button["style"]
                    )  # if "style" in button else discord.ButtonStyle.secondary  # `style` can don't exist in modals after the data migration
                    button = discord.ui.Button(**button)
                    button.callback = self.send_modal
                    view = discord.ui.View(timeout=None)
                    view.add_item(button)
                    self.bot.add_view(view, message_id=message_id)
                    self.views[discord.PartialMessage(channel=channel, id=message_id)] = view
                except Exception as e:
                    self.log.error(
                        f"The Button View could not be added correctly for the `{guild}-{message}` message.",
                        exc_info=e,
                    )

    async def send_modal(self, interaction: discord.Interaction) -> None:
        if await self.bot.cog_disabled_in_guild(cog=self, guild=interaction.guild):
            await interaction.response.send_message(
                "You are not allowed to use this interaction.", ephemeral=True
            )
            return
        config = await self.config.guild(interaction.message.guild).modals()
        if f"{interaction.message.channel.id}-{interaction.message.id}" not in config:
            await interaction.response.send_message(
                _("This message is not in Config."), ephemeral=True
            )
            return
        whitelist_roles = config[f"{interaction.message.channel.id}-{interaction.message.id}"].get(
            "whitelist_roles"
        )
        blacklist_roles = config[f"{interaction.message.channel.id}-{interaction.message.id}"].get(
            "blacklist_roles"
        )
        if (
            whitelist_roles
            and all(role.id not in whitelist_roles for role in interaction.user.roles)
            or (
                blacklist_roles
                and any(role.id in blacklist_roles for role in interaction.user.roles)
            )
        ):
            await interaction.response.send_message(
                "You are not allowed to use this interaction.", ephemeral=True
            )
            return
        try:
            modal_config = config[f"{interaction.message.channel.id}-{interaction.message.id}"][
                "modal"
            ]
            modal = discord.ui.Modal(
                title=modal_config["title"],
                timeout=modal_config["timeout"],
                # custom_id=modal_config["custom_id"],
            )
            inputs = []
            for _input in modal_config["inputs"]:
                _input["style"] = discord.TextStyle(_input["style"])
                text_input = discord.ui.TextInput(**_input)
                text_input.max_length = (
                    1024 if text_input.max_length is None else min(text_input.max_length, 1024)
                )
                inputs.append(text_input)
                modal.add_item(text_input)
            modal.on_submit = partial(self.send_embed_with_responses, inputs=inputs)
            await interaction.response.send_modal(modal)
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
        self, interaction: discord.Interaction, inputs: typing.List[discord.ui.TextInput]
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
            channel_permissions = channel.permissions_for(interaction.guild.me)
            if not all(
                [
                    channel_permissions.view_channel,
                    channel_permissions.send_messages,
                    channel_permissions.embed_links,
                ]
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
            if not config.get("anonymous"):
                embed.set_author(
                    name=f"{interaction.user.display_name} ({interaction.user.id})", icon_url=interaction.user.display_avatar
                )
                embed.color = interaction.user.color
            else:
                embed.set_author(
                    name="Anonymous",
                    icon_url="https://forum.mtasa.com/uploads/monthly_2016_10/Anonyme.png.4060431ce866962fa496657f752d5613.png",
                )
            for _input in inputs:
                try:
                    embed.add_field(
                        name=_input.label,
                        value=_input.value.strip() or "Not provided.",
                        inline=False,
                    )
                except Exception:
                    pass
            embed.set_footer(text=interaction.guild.name, icon_url=interaction.guild.icon)
            await channel.send(
                None if config.get("pings") is None else humanize_list(config.get("pings"))[:2000],
                embed=embed,
                allowed_mentions=discord.AllowedMentions(everyone=False, users=True, roles=True),
            )
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
                config["messages"]["submit"] or _("Thank you for sending this Modal!"),
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
    @commands.admin_or_permissions(manage_guild=True)
    @commands.hybrid_group()
    async def discordmodals(self, ctx: commands.Context) -> None:
        """Group of commands to use DiscordModals."""
        pass

    @discordmodals.command(aliases=["+"])
    async def add(
        self, ctx: commands.Context, message: MyMessageConverter, *, argument: ModalConverter
    ) -> None:
        """Add a Modal for a message.

        Use YAML syntax to set up everything.

        **Example:**
        ```
        [p]discordmodals add <message>
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
          submit: Form submitted.
        pings: user1, user2, role1, role2
        whitelist_roles: role1, role2
        blacklist_roles: role3, role4
        ```
        The `emoji`, `style`, `required`, `default`, `placeholder`, `min_length`, `max_length`, `channel`, `anonymous`, `messages`, `pings`, `whitelist_roles` and `blacklist_roles` are not required.
        """
        config = await self.config.guild(ctx.guild).modals.all()
        if f"{message.channel.id}-{message.id}" in config:
            raise commands.UserFeedbackCheckFailure(_("This message already has a Modal."))
        elif message.components:
            raise commands.UserFeedbackCheckFailure(_("This message already has components."))
        try:
            button = argument["button"]
            button["style"] = discord.ButtonStyle(button["style"])
            button["custom_id"] = f"DiscordModals_{CogsUtils.generate_key(length=10)}"
            button = discord.ui.Button(**button)
            button.callback = self.send_modal
            view = discord.ui.View(timeout=None)
            view.add_item(button)
            message = await message.edit(view=view)
            self.views[message] = view
        except discord.HTTPException:
            raise commands.UserFeedbackCheckFailure(
                _("Sorry. An error occurred when I tried to put the button on the message.")
            )
        modal = discord.ui.Modal(
            title=argument["title"],
            timeout=None,
            custom_id=f"DiscordModals_{CogsUtils.generate_key(length=10)}",
        )
        inputs = []
        for _input in argument["modal"]:
            _input = _input.copy()
            _input["style"] = discord.TextStyle(_input["style"])
            text_input = discord.ui.TextInput(**_input)
            inputs.append(text_input)
            modal.add_item(text_input)
        modal.on_submit = partial(self.send_embed_with_responses, inputs=inputs)
        config[f"{message.channel.id}-{message.id}"] = {
            "title": argument["title"],
            "button": {
                "style": button.style.value,
                "label": button.label,
                "emoji": str(button.emoji),
                "custom_id": button.custom_id,
            },
            "channel": argument["channel"],
            "modal": {
                "title": modal.title,
                "timeout": modal.timeout,
                "custom_id": modal.custom_id,
                "inputs": argument["modal"],
            },
            "anonymous": argument["anonymous"],
            "messages": {
                "error": argument["messages"]["error"],
                "submit": argument["messages"]["submit"],
            },
            "pings": argument["pings"],
            "whitelist_roles": argument["whitelist_roles"],
            "blacklist_roles": argument["blacklist_roles"],
        }
        await self.config.guild(ctx.guild).modals.set(config)
        await ctx.send(_("Modal created."))

    @commands.bot_has_permissions(embed_links=True)
    @discordmodals.command()
    async def list(self, ctx: commands.Context, message: MyMessageConverter = None) -> None:
        """List all Modals of this server or display the settings for a specific one."""
        modals = await self.config.guild(ctx.guild).modals()
        for modal in modals:
            modals[modal]["message"] = modal
        if message is None:
            _modals = list(modals.values()).copy()
        elif f"{message.channel.id}-{message.id}" not in modals:
            raise commands.UserFeedbackCheckFailure(
                _("No modal is configured for this message.")
            )
        else:
            _modals = modals.copy()
            _modals = [modals[f"{message.channel.id}-{message.id}"]]
        if not _modals:
            raise commands.UserFeedbackCheckFailure(_("No modals in this server."))
        embed: discord.Embed = discord.Embed(
            title=_("Modals"),
            color=await ctx.embed_color(),
        )
        embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon)
        embed.set_footer(text=_("There is {len_modals} modals in this server.").format(len_modals=len(modals)))
        embeds = []
        for modal in _modals:
            e = embed.copy()
            e.description = _("Message Jump Link: {message_jump_link}\n").format(
                message_jump_link=f"https://discord.com/channels/{ctx.guild.id}/{modal['message'].replace('-', '/')}"
            )
            del modal["message"]
            e.description += f"\n{box(json.dumps(modal, indent=4), lang='py')}"
            embeds.append(e)
        await Menu(pages=embeds).start(ctx)

    @discordmodals.command(aliases=["-"])
    async def remove(self, ctx: commands.Context, message: MyMessageConverter) -> None:
        """Remove a Modal for a message."""
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
        """Clear all Modals for a guild."""
        await self.config.guild(ctx.guild).modals.clear()
        await ctx.send(_("All Modals purged."))

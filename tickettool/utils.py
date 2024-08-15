import discord  # isort:skip
import typing  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator  # isort:skip

import re

import yaml

try:
    from emoji import EMOJI_DATA  # emoji>=2.0.0
except ImportError:
    from emoji import UNICODE_EMOJI_ENGLISH as EMOJI_DATA  # emoji<2.0.0


_: Translator = Translator("TicketTool", __file__)


class utils:
    async def get_overwrites(self, ticket):
        config = await ticket.bot.get_cog("TicketTool").get_config(ticket.guild, ticket.profile)
        overwrites = {
            ticket.owner: discord.PermissionOverwrite(
                view_channel=True,
                read_messages=True,
                read_message_history=True,
                send_messages=True,
                attach_files=True,
                use_application_commands=True,
            ),
            ticket.guild.me: discord.PermissionOverwrite(
                view_channel=True,
                read_messages=True,
                read_message_history=True,
                send_messages=True,
                attach_files=True,
                manage_messages=True,
                manage_channels=True,
            ),
            ticket.guild.default_role: discord.PermissionOverwrite(
                view_channel=False,
            ),
        }
        if ticket.claim is not None:
            overwrites[ticket.claim] = discord.PermissionOverwrite(
                view_channel=True,
                read_messages=True,
                read_message_history=True,
                send_messages=True,
                attach_files=True,
                use_application_commands=True,
            )
        if config["admin_roles"]:
            for role in config["admin_roles"]:
                overwrites[role] = discord.PermissionOverwrite(
                    view_channel=True,
                    read_messages=True,
                    read_message_history=True,
                    send_messages=True,
                    attach_files=True,
                    manage_messages=True,
                    use_application_commands=True,
                )
        if config["support_roles"]:
            for role in config["support_roles"]:
                overwrites[role] = discord.PermissionOverwrite(
                    view_channel=True,
                    read_messages=True,
                    read_message_history=True,
                    send_messages=True,
                    attach_files=True,
                    use_application_commands=True,
                )
        if config["view_roles"] is not None:
            for role in config["view_roles"]:
                overwrites[role] = discord.PermissionOverwrite(
                    view_channel=True,
                    read_messages=True,
                    read_message_history=True,
                    add_reactions=False,
                    use_application_commands=False,
                )
        return overwrites


class Emoji(commands.EmojiConverter):
    async def convert(
        self, ctx: commands.Context, argument: str
    ) -> typing.Union[str, discord.Emoji]:
        # argument = argument.strip("\N{VARIATION SELECTOR-16}")
        if argument in EMOJI_DATA:
            return argument
        if argument in {
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


class EmojiLabelDescriptionValueConverter(commands.Converter):
    async def convert(
        self, ctx: commands.Context, argument: str
    ) -> typing.Tuple[str, typing.Union[discord.PartialEmoji, str]]:
        arg_split = re.split(r"[;|\-]", argument)
        try:
            try:
                emoji, label, description, value = arg_split
            except ValueError:
                try:
                    emoji, label, description = arg_split
                    value = label
                except ValueError:
                    emoji, label = arg_split
                    description = None
                    value = label
        except ValueError:
            raise commands.BadArgument(
                _(
                    "Emoji Label must be An emoji followed by a label, and optionnaly by a description and a value (for rename ticket channel), separated by either `;`, `,`, `|`, or `-`."
                )
            )
        emoji = await Emoji().convert(ctx, emoji)
        label = str(label)
        return emoji, label, description, value


class CustomModalConverter(commands.Converter):
    async def convert(
        self, ctx: commands.Context, argument: str
    ) -> typing.Dict[str, typing.Union[str, bool, typing.Dict, typing.List]]:
        try:
            argument_dict = yaml.safe_load(argument)
        except yaml.YAMLError:
            raise commands.BadArgument(
                _(
                    "Error parsing YAML. Please make sure the format is valid (a YAML validator may help)"
                )
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
        if len(argument_dict) > 5:
            raise commands.BadArgument(_("You can only have 5 text inputs."))
        for count, input in enumerate(argument_dict, start=1):
            count += 1
            for arg in required_arguments:
                if arg not in input:
                    raise commands.BadArgument(
                        _("The argument `/{count}/{arg}` is required in the YAML.").format(
                            count=count, arg=arg
                        )
                    )
            for arg in input:
                if arg not in required_arguments + optional_arguments:
                    raise commands.BadArgument(
                        _(
                            "The argument `/{count}/{arg}` is invalid in the YAML. Check the spelling."
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
                            "The argument `/{count}/style` must be a number between 1 and 2."
                        ).format(count=count)
                    )
                if not 1 <= style <= 2:
                    raise commands.BadArgument(
                        _(
                            "The argument `/{count}/style` must be a number between 1 and 2."
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
                            "The argument `/{count}/required` must be a boolean (True or False)."
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
        return argument_dict

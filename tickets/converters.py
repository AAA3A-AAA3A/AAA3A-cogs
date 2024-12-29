from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

from redbot.core.utils.chat_formatting import humanize_list

try:
    from emoji import EMOJI_DATA  # emoji>=2.0.0
except ImportError:
    from emoji import UNICODE_EMOJI_ENGLISH as EMOJI_DATA  # emoji<2.0.0
import yaml

_: Translator = Translator("Tickets", __file__)


class ProfileConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> str:
        profiles = await ctx.cog.config.guild(ctx.guild).profiles()
        if argument not in profiles:
            raise commands.BadArgument(_("This profile doesn't exist."))
        return argument


class ForumTagConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> int:
        cog = ctx.bot.get_cog("Tickets")
        if (
            not isinstance((profile := ctx.args[-1]), str)
            or (
                forum_channel_id := await cog.config.guild(ctx.guild).profiles.get_raw(
                    profile, "forum_channel"
                )
            )
            is None
            or (forum_channel := ctx.guild.get_channel(forum_channel_id)) is None
            or not isinstance(forum_channel, discord.ForumChannel)
        ):
            raise commands.BadArgument(
                _("You must set the forum channel before setting a forum tag.")
            )
        try:
            argument = int(argument)
        except ValueError:
            if (tag := discord.utils.get(forum_channel.available_tags, name=argument)) is not None:
                return tag.id
        if forum_channel.get_tag(argument) is None:
            available_tags = humanize_list(
                [
                    f"`{f'{tag.emoji} ' if tag.emoji is not None else ''}{tag.name}` ({tag.id})"
                    for tag in forum_channel.available_tags
                ]
            )
            raise commands.BadArgument(
                _(
                    "The forum tag ID provided doesn't exist. The available tags are: {available_tags}."
                ).format(available_tags=available_tags)
            )
        return argument


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


class ModalConverter(commands.Converter):
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
            elif not 0 <= input["min_length"] <= 1000:
                raise commands.BadArgument(
                    _(
                        "The argument `/modal/{count}/min_length` must be between 0 and 1000."
                    ).format(count=count, arg=arg)
                )
            if "max_length" not in input or input["max_length"] == "None":
                input["max_length"] = None
            elif not 1 <= input["max_length"] <= 1000:
                raise commands.BadArgument(
                    _(
                        "The argument `/modal/{count}/max_length` must be between 0 and 1000."
                    ).format(count=count, arg=arg)
                )
        return argument_dict

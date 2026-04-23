import discord

from redbot.core import commands
from redbot.core.i18n import Translator

try:
    from emoji import EMOJI_DATA  # emoji>=2.0.0
except ImportError:
    from emoji import UNICODE_EMOJI_ENGLISH as EMOJI_DATA  # emoji<2.0.0

from .types import Team

_: Translator = Translator("Teams", __file__)


class TeamConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> Team:
        cog = ctx.bot.get_cog("Teams")
        try:
            return cog.teams[ctx.guild.id][argument]
        except (ValueError, KeyError):
            if ctx.guild.id in cog.teams:
                if (
                    team := discord.utils.get(cog.teams[ctx.guild.id].values(), name=argument)
                ) is not None:
                    return team
                if (
                    team := discord.utils.get(
                        cog.teams[ctx.guild.id].values(),
                        display_emoji=argument,
                    )
                ) is not None:
                    return team
            raise commands.BadArgument(_("Team not found."))


class Emoji(commands.EmojiConverter):
    async def convert(
        self,
        ctx: commands.Context,
        argument: str,
    ) -> str | discord.Emoji:
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


class UrlConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> str:
        if not argument.startswith(("http://", "https://")):
            raise commands.BadArgument(_("Invalid URL."))
        return argument


class TeamOrMemberConverter(commands.Converter):
    async def convert(
        self,
        ctx: commands.Context,
        argument: str,
    ) -> Team | discord.Member:
        for converter in (TeamConverter, commands.MemberConverter):
            try:
                return await converter().convert(ctx, argument)
            except commands.BadArgument:
                pass
        raise commands.BadArgument(_("Invalid team or member."))

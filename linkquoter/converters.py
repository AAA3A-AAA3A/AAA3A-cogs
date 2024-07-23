from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator  # isort:skip
import discord  # isort:skip

import re

_: Translator = Translator("LinkQuoter", __file__)

MESSAGE_LINK_REGEX = re.compile(
    r"https?:\/\/(?:(?:ptb|canary)\.)?discord(?:app)?\.com"
    r"\/channels\/(?P<guild_id>[0-9]{15,19})\/(?P<channel_id>"
    r"[0-9]{15,19})\/(?P<message_id>[0-9]{15,19})\/?"
)


class LinkToMessageConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> discord.Message:
        try:
            return await self.validate_message(
                ctx, await commands.MessageConverter().convert(ctx, argument=argument)
            )
        except commands.BadArgument:
            pass

        match = re.search(MESSAGE_LINK_REGEX, argument)
        if not match:
            raise commands.MessageNotFound(argument)
        guild_id = int(
            match["guild_id"]
        )  # Note: links can have "@me" here but the regex doesn't match that.
        channel_id = int(match["channel_id"])
        message_id = int(match["message_id"])
        if (message := ctx.bot._connection._get_message(message_id)) is not None:
            return await self.validate_message(ctx, message)
        guild = ctx.bot.get_guild(guild_id)
        if not guild:
            raise commands.GuildNotFound(guild_id)
        channel = guild.get_channel(channel_id)
        if not channel:
            raise commands.ChannelNotFound(channel_id)

        my_perms = channel.permissions_for(guild.me)
        if not my_perms.read_messages:
            raise commands.BadArgument(
                _("Can't read messages in {channel.mention}.").format(channel=channel)
            )
        elif not my_perms.read_message_history:
            raise commands.BadArgument(
                _("Can't read message history in {channel.mention}.").format(channel=channel)
            )
        try:
            message = await channel.fetch_message(message_id)
        except discord.NotFound:
            raise commands.MessageNotFound(argument)
        except discord.Forbidden:
            raise commands.BadArgument(
                _("Can't read messages in {channel.mention}.").format(channel=channel)
            )
        else:
            return await self.validate_message(ctx, message)

    @staticmethod
    async def validate_message(ctx: commands.Context, message: discord.Message) -> discord.Message:
        if not message.guild:
            raise commands.BadArgument(_("I can only quote messages from servers."))
        guild = message.guild
        if message.channel.is_nsfw() and not ctx.channel.is_nsfw():
            raise commands.BadArgument(
                _("Messages from NSFW channels cannot be quoted in non-NSFW channels.")
            )

        if not getattr(ctx, "__is_mocked__", False) and ctx.author.id in ctx.bot.owner_ids:
            return message

        cog = ctx.bot.get_cog("LinkQuoter")
        config = await cog.config.guild(ctx.guild).all()

        if guild != ctx.guild:
            guild_config = await cog.config.guild(guild).all()
            if not config["cross_server"]:
                raise commands.BadArgument(
                    _("This server is not opted in to quote messages from other servers.")
                )
            elif not guild_config["cross_server"]:
                raise commands.BadArgument(
                    _(
                        "That server is not opted in to allow its messages to be quoted in other servers."
                    )
                )

        if (member := guild.get_member(ctx.author.id)) is not None:
            author_perms = message.channel.permissions_for(member)
            if not (author_perms.read_message_history and author_perms.read_messages):
                raise commands.BadArgument(
                    _("You don't have permission to read messages in that channel.")
                )

        return message

from typing import NamedTuple
import datetime
import json
import os
from random import randint
from typing import Union

import discord
from redbot.core import checks, commands
from redbot.core.data_manager import cog_data_path
from .helpers import embed_from_msg
from redbot.core.utils.tunnel import Tunnel

# Credits:
# Thanks to @epic guy on Discord for the basic syntax (command groups, commands) and also commands (await ctx.send, await ctx.author.send, await ctx.message.delete())!
# Thanks to TrustyJAID's Backup for starting the command to list the latest source channel messages! (https://github.com/TrustyJAID/Trusty-cogs/tree/master/backup)
# Thanks to QuoteTools from SimBad for the embed!
# Thanks to Speak from @epic guy for the webhooks! (https://github.com/npc203/npc-cogs/tree/main/speak)
# Thanks to Say from LaggronsDumb for the attachments in the single messages and webhooks! (https://github.com/laggron42/Laggrons-Dumb-Cogs/tree/v3/say)
# Thanks to the developers of the cogs I added features to as it taught me how to make a cog! (Chessgame by WildStriker, Captcha by Kreusada, Speak by Epic guy and Rommer by Dav)
# Thanks to all the people who helped me with some commands in the #coding channel of the redbot support server!


class GuildNotFoundError(Exception):
    pass


class TransferChannel(commands.Cog):
    """
    A cog to transfer all messages channel in a other channel.
    """

    def __init__(self, bot):
        self.bot = bot
        self.cache = {}

    @commands.command(aliases=["channeltransfer"])
    @checks.admin_or_permissions(manage_guild=True)
    @commands.guild_only()
    async def transferchannel(self, ctx: commands.Context, source: discord.TextChannel, destination: discord.TextChannel, limit: int, embed: bool = True, webhooks: bool = True):
        """
        Transfer all messages channel in a other channel. This might take a long time.

        `source` is partial name or ID of the source channel
        `destination` is partial name or ID of the destination channel
        `embed` Do you want to transfer the message as an embed? False for a simple message. True by default.
        `webhooks` If you selected "simple message" with the "embed" argument, do you want to send the messages with webhooks (name and avatar of the original author)? True by default.
        """
        guild = ctx.guild
        today = datetime.date.today().strftime("%Y-%m-%d")
        total_msgs = 0
        msgList = await source.history(limit=limit+1, oldest_first=False).flatten()
        msgList.reverse()
        for message in msgList:
            if not message.id == ctx.message.id:
                total_msgs += 1
                if embed:
                    em = embed_from_msg(message)
                    await destination.send(embed=em)
                else:
                    files = await Tunnel.files_from_attatch(message)
                    if files != []:
                        error_message = (
                            "Has files: yes\n"
                            f"Number of files: {len(files)}\n"
                            f"Files URL: " + ", ".join([x.url for x in ctx.message.attachments])
                        )
                    else:
                        error_message = "Has files: no"
                    if not webhooks:
                        msg1 = "\n".join(
                            [
                                f"**Author:** {message.author}({message.author.id})",
                                f"**Channel:** <#{message.channel.id}>",
                                f"**Time(UTC):** {message.created_at.isoformat()}",
                            ]
                        )
                        if len(msg1) + len(message.content) < 2000:
                            await ctx.send(msg1 + "\n\n" + message.content, files=files)
                        else:
                            await ctx.send(msg1)
                            await ctx.send(message.content, files=files)
                    else:
                        hook = await self.get_hook(destination)
                        await hook.send(
                            username=message.author.display_name,
                            avatar_url=message.author.avatar_url,
                            content=message.content,
                            files=files,
                        )
        await ctx.send("{} messages transfered from {} to {}".format(total_msgs, source.mention, destination.mention))

    async def get_hook(self, destination):
        try:
            if destination.id not in self.cache:
                for i in await destination.webhooks():
                    if i.user.id == self.bot.user.id:
                        hook = i
                        self.cache[destination.id] = hook
                        break
                else:
                    hook = await destination.create_webhook(
                        name="red_bot_hook_" + str(destination.id)
                    )
            else:
                hook = self.cache[destination.id]
        except discord.errors.NotFound:  # Probably user deleted the hook
            hook = await destination.create_webhook(name="red_bot_hook_" + str(destination.id))

        return hook

    async def red_get_data_for_user(self, *, user_id: int):
        # this cog does not store any data
        return {}

    async def red_delete_data_for_user(self, *, requester, user_id: int) -> None:
        # this cog does not store any data
        pass

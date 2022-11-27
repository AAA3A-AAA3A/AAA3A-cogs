"""
Red - A fully customizable Discord bot
Copyright (C) 2017-present Cog Creators
Copyright (C) 2015-2017 Twentysix
This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.
You should have received a copy of the GNU General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.
"""

from .AAA3A_utils import CogsUtils  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
from redbot.core.bot import Red  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import asyncio
import datetime
from copy import copy

# Credits:
# The idea for this cog came from Jack and Draper! This PR will take time, so I'm making it. If one day this one is integrated into Red, this cog may make it easier to manage. (https://github.com/Cog-Creators/Red-DiscordBot/pull/5419)
# Thanks to @epic guy on Discord for the basic syntax (command groups, commands) and also commands (await ctx.send, await ctx.author.send, await ctx.message.delete())!
# Thanks to the developers of the cogs I added features to as it taught me how to make a cog! (Chessgame by WildStriker, Captcha by Kreusada, Speak by Epic guy and Rommer by Dav)
# Thanks to all the people who helped me with some commands in the #coding channel of the redbot support server!

_ = Translator("Sudo", __file__)

if CogsUtils().is_dpy2:
    from functools import partial

    hybrid_command = partial(commands.hybrid_command, with_app_command=False)
    hybrid_group = partial(commands.hybrid_group, with_app_command=False)
else:
    hybrid_command = commands.command
    hybrid_group = commands.group


@cog_i18n(_)
class Sudo(commands.Cog):
    """A cog to allow bot owners to be normal users in terms of permissions!"""

    def __init__(self, bot: Red):
        self.bot: Red = bot

        self.__authors__ = ["AAA3A", "Draper", "jack1142 (Jackenmen#6607)"]
        self.cogsutils = CogsUtils(cog=self)

    async def cog_load(self):
        self.all_owner_ids = copy(self.bot.owner_ids)
        self.bot.owner_ids.clear()

    if CogsUtils().is_dpy2:

        async def cog_unload(self):
            self.bot.owner_ids.update(copy(self.all_owner_ids))
            self.all_owner_ids.clear()
            self.cogsutils._end()

    else:

        def cog_unload(self):
            self.bot.owner_ids.update(copy(self.all_owner_ids))
            self.all_owner_ids.clear()
            self.cogsutils._end()

    @commands.Cog.listener()
    async def on_message_without_command(self, message: discord.Message):
        context = await self.bot.get_context(message)
        if context.prefix is None:
            return
        command = context.message.content[len(str(context.prefix)):]
        if len(command.split(" ")) == 0:
            return
        command_name = command.split(" ")[0]
        if command_name not in ["su", "unsu", "sudo", "sutimeout"]:
            return
        await self.cogsutils.invoke_command(author=context.author, channel=context.channel, command=f"Sudo {command}", prefix=context.prefix, message=context.message)

    def decorator(all_owner_ids: typing.Optional[bool], bot_owner_ids: typing.Optional[bool]):
        async def pred(ctx):
            if all_owner_ids:
                if (
                    ctx.author.id in ctx.bot.get_cog("Sudo").all_owner_ids
                    and ctx.author.id not in ctx.bot.owner_ids
                ):
                    return True
            if bot_owner_ids:
                if ctx.author.id in ctx.bot.owner_ids:
                    return True
            return False

        return commands.check(pred)

    @decorator(all_owner_ids=True, bot_owner_ids=True)
    @hybrid_group(name="SudO", hidden=False)
    async def Sudo(self, ctx: commands.Context):
        """Use `[p]su`, `[p]unsu`, `[p]sudo` and `[p]sutimeout`."""
        pass

    @decorator(all_owner_ids=True, bot_owner_ids=False)
    @Sudo.command(name="su")
    async def _su(self, ctx: commands.Context):
        """Sudo as the owner of the bot.

        Use `[p]su`!
        """
        ctx.bot.owner_ids.add(ctx.author.id)

    @decorator(all_owner_ids=False, bot_owner_ids=True)
    @Sudo.command(name="unsu")
    async def _unsu(self, ctx: commands.Context):
        """Unsudo as normal user.

        Use `[p]unsu`!
        """
        ctx.bot.owner_ids.remove(ctx.author.id)
        if ctx.author.id not in self.all_owner_ids:
            self.all_owner_ids.add(ctx.author.id)

    @decorator(all_owner_ids=True, bot_owner_ids=False)
    @Sudo.command(name="sudo")
    async def _sudo(self, ctx: commands.Context, *, command: str):
        """Rise as the bot owner for the specified command only.

        Use `[p]sudo`!
        """
        ctx.bot.owner_ids.add(ctx.author.id)
        await self.cogsutils.invoke_command(
            author=ctx.author,
            channel=ctx.channel,
            command=command,
            prefix=ctx.prefix,
            message=ctx.message,
        )
        if ctx.bot.get_cog("Sudo") is not None:
            try:
                ctx.bot.owner_ids.remove(ctx.author.id)
            except KeyError:
                pass
        if self.cogsutils.is_dpy2:
            await ctx.defer()

    # Thanks to red#5419 for this command.
    @decorator(all_owner_ids=True, bot_owner_ids=False)
    @Sudo.command(name="sutimeout")
    async def _sutimeout(
        self,
        ctx: commands.Context,
        *,
        interval: commands.TimedeltaConverter(
            minimum=datetime.timedelta(seconds=10),
            maximum=datetime.timedelta(days=1),
            default_unit="m",
        ) = datetime.timedelta(minutes=5),
    ):
        """Sudo as the owner of the bot for the specified timeout.
        The time should be between 10 seconds and 1 day.

        Use `[p]sutimeout`!
        """
        sleep = interval.total_seconds()
        ctx.bot.owner_ids.add(ctx.author.id)
        await asyncio.sleep(sleep)
        if ctx.bot.get_cog("Sudo") is not None:
            ctx.bot.owner_ids.remove(ctx.author.id)

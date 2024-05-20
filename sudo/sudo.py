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

from AAA3A_utils import Cog, CogsUtils  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
from redbot.core.bot import Red  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import asyncio
import datetime
from copy import copy

# Credits:
# General repo credits.
# The idea for this cog came from Jack and Draper! This PR will take time, so I'm making it. If one day this one is integrated into Red, this cog may make it easier to manage. (https://github.com/Cog-Creators/Red-DiscordBot/pull/5419)

_ = Translator("Sudo", __file__)

TimeDeltaConverter: commands.converter.timedelta = commands.TimedeltaConverter(
    minimum=datetime.timedelta(seconds=10), maximum=datetime.timedelta(days=1), default_unit="m"
)


@cog_i18n(_)
class Sudo(Cog):
    """A cog to allow bot owners to be normal users in terms of permissions!

    ⚠️ This cog makes bot owners unable to be perceived as bot owners in commands while the cog is loaded unless the `[p]su` command is used.
    """

    __authors__: typing.List[str] = ["AAA3A", "Draper", "jack1142 (Jackenmen#6607)"]

    async def cog_load(self) -> None:
        await super().cog_load()
        self.all_owner_ids = copy(self.bot.owner_ids)
        self.bot.owner_ids.clear()

    async def cog_unload(self) -> None:
        self.bot.owner_ids.update(copy(self.all_owner_ids))
        self.all_owner_ids.clear()
        await super().cog_unload()

    @commands.Cog.listener()
    async def on_message_without_command(self, message: discord.Message):
        if await self.bot.cog_disabled_in_guild(
            cog=self, guild=message.guild
        ) or not await self.bot.allowed_by_whitelist_blacklist(who=message.author):
            return
        if message.webhook_id is not None or message.author.bot:
            return
        context = await self.bot.get_context(message)
        if context.prefix is None:
            return
        command = context.message.content[len(str(context.prefix)) :]
        if len(command.split(" ")) == 0:
            return
        command_name = command.split(" ")[0]
        if command_name not in ("su", "unsu", "sutimeout"):
            return
        await CogsUtils.invoke_command(
            bot=self.bot,
            author=context.author,
            channel=context.channel,
            command=f"sudo {command}",
            prefix=context.prefix,
            message=context.message,
        )

    def decorator(all_owner_ids: typing.Optional[bool], bot_owner_ids: typing.Optional[bool]):
        async def pred(ctx: commands.Context) -> bool:
            if all_owner_ids and (
                ctx.author.id in ctx.bot.get_cog("Sudo").all_owner_ids
                and ctx.author.id not in ctx.bot.owner_ids
            ):
                return True
            return bool(bot_owner_ids and ctx.author.id in ctx.bot.owner_ids)

        return commands.check(pred)

    @decorator(all_owner_ids=True, bot_owner_ids=True)
    @commands.hybrid_group(name="sudo", invoke_without_command=True)
    async def Sudo(self, ctx: commands.Context, *, command: str):
        """Use `[p]su`, `[p]unsu`, `[p]sudo` and `[p]sutimeout`."""
        if ctx.invoked_subcommand is None:
            await self._sudo(ctx, command=command)

    @decorator(all_owner_ids=True, bot_owner_ids=False)
    @Sudo.command(name="su", hidden=True)
    async def _su(self, ctx: commands.Context):
        """Sudo as the owner of the bot.

        Use `[p]su`!
        """
        ctx.bot.owner_ids.add(ctx.author.id)

    @decorator(all_owner_ids=False, bot_owner_ids=True)
    @Sudo.command(name="unsu", hidden=True)
    async def _unsu(self, ctx: commands.Context):
        """Unsudo as normal user.

        Use `[p]unsu`!
        """
        ctx.bot.owner_ids.remove(ctx.author.id)
        if ctx.author.id not in self.all_owner_ids:
            self.all_owner_ids.add(ctx.author.id)

    @decorator(all_owner_ids=True, bot_owner_ids=False)
    @Sudo.command(name="sudo", hidden=True)
    async def _sudo(self, ctx: commands.Context, *, command: str):
        """Rise as the bot owner for the specified command only.

        Use `[p]sudo`!
        """
        ctx.bot.owner_ids.add(ctx.author.id)
        await CogsUtils.invoke_command(
            bot=ctx.bot,
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
        await ctx.defer()

    # Thanks to red#5419 for this command.
    @decorator(all_owner_ids=True, bot_owner_ids=False)
    @Sudo.command(name="sutimeout", hidden=True)
    async def _sutimeout(
        self,
        ctx: commands.Context,
        *,
        interval: TimeDeltaConverter = datetime.timedelta(minutes=5),
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

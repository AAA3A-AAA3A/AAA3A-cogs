from .AAA3A_utils import CogsUtils  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
from redbot.core.bot import Red  # isort:skip
import typing  # isort:skip

import asyncio
import datetime
from copy import copy

# Credits:
# The idea for this cog came from @Jack1142. This PR will take time, so I'm making it. If one day this one is integrated into Red, this cog may make it easier to manage. (https://github.com/Cog-Creators/Red-DiscordBot/pull/5419)
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
        self.all_owner_ids = copy(self.bot.owner_ids)
        self.bot.owner_ids.clear()

        self.cogsutils = CogsUtils(cog=self)
        self.cogsutils._setup()

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

    def decorator(all_owner_ids: typing.Optional[bool], bot_owner_ids: typing.Optional[bool]):
        async def pred(ctx):
            if all_owner_ids:
                if ctx.author.id in ctx.bot.get_cog("Sudo").all_owner_ids and ctx.author.id not in ctx.bot.owner_ids:
                    return True
            if bot_owner_ids:
                if ctx.author.id in ctx.bot.owner_ids:
                    return True
            return False
        return commands.check(pred)

    @decorator(all_owner_ids=True, bot_owner_ids=True)
    @hybrid_group()
    async def sudo(self, ctx: commands.Context):
        pass

    @decorator(all_owner_ids=True, bot_owner_ids=False)
    @sudo.command()
    async def su(self, ctx: commands.Context):
        """Sudo as the owner of the bot.
        """
        ctx.bot.owner_ids.add(ctx.author.id)
        await ctx.tick(message="Done")

    @decorator(all_owner_ids=False, bot_owner_ids=True)
    @sudo.command()
    async def unsu(self, ctx: commands.Context):
        """Unsudo as normal user.
        """
        ctx.bot.owner_ids.remove(ctx.author.id)
        await ctx.tick(message="Done")

    @decorator(all_owner_ids=True, bot_owner_ids=False)
    @sudo.command(name="sudo")
    async def _sudo(self, ctx: commands.Context, *, command: str):
        """Rise as the bot owner for the specified command only.
        """
        ctx.bot.owner_ids.add(ctx.author.id)
        await self.cogsutils.invoke_command(author=ctx.author, channel=ctx.channel, command=command, prefix=ctx.prefix if not ctx.prefix == "/" else None, message=ctx.message)
        if ctx.bot.get_cog("Sudo") is not None:
            ctx.bot.owner_ids.remove(ctx.author.id)
        if self.cogsutils.is_dpy2:
            await ctx.defer()
        await ctx.tick()

    @decorator(all_owner_ids=True, bot_owner_ids=False)
    @sudo.command()
    async def sutimeout(
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
        """
        sleep = interval.total_seconds()
        ctx.bot.owner_ids.add(ctx.author.id)
        await asyncio.sleep(sleep)
        if ctx.bot.get_cog("Sudo") is not None:
            ctx.bot.owner_ids.remove(ctx.author.id)
        await ctx.tick(message="Done")
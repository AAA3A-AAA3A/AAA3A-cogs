from .AAA3A_utils import CogsUtils  # isort:skip
from redbot.core.bot import Red  # isort:skip
import asyncio

from redbot.core.utils import get_end_user_data_statement

from .autotraceback import AutoTraceback

__red_end_user_data_statement__ = get_end_user_data_statement(file=__file__)

old_traceback = None


async def setup_after_ready(bot):
    global old_traceback
    await bot.wait_until_red_ready()
    cog = AutoTraceback(bot)
    old_traceback = bot.get_command("traceback")
    if old_traceback:
        bot.remove_command(old_traceback.name)
    await CogsUtils().add_cog(bot, cog)


async def setup(bot: Red):
    asyncio.create_task(setup_after_ready(bot))


def teardown(bot: Red):
    bot.add_command(old_traceback)

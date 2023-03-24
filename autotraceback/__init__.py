from redbot.core.bot import Red  # isort:skip
import asyncio

from redbot.core.utils import get_end_user_data_statement

from .autotraceback import AutoTraceback

__red_end_user_data_statement__ = get_end_user_data_statement(file=__file__)

old_traceback = None


async def setup_after_ready(bot) -> None:
    global old_traceback
    await bot.wait_until_red_ready()
    cog = AutoTraceback(bot)
    if old_traceback := bot.get_command("traceback"):
        bot.remove_command(old_traceback.name)
    await cog.cogsutils.add_cog(bot)


async def setup(bot: Red) -> None:
    asyncio.create_task(setup_after_ready(bot))


def teardown(bot: Red) -> None:
    bot.add_command(old_traceback)

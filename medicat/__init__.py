from redbot.core.bot import Red  # isort:skip
import asyncio

from redbot.core.utils import get_end_user_data_statement

from .medicat import Medicat  # , MEDICAT_GUILD, TEST_GUILD

__red_end_user_data_statement__ = get_end_user_data_statement(file=__file__)


async def setup_after_ready(bot) -> None:
    await bot.wait_until_red_ready()
    cog = Medicat(bot)
    await cog.cogsutils.add_cog(bot)


async def setup(bot: Red) -> None:
    # await bot.wait_until_ready()
    # if bot.get_guild(MEDICAT_GUILD) is None and bot.get_guild(TEST_GUILD) is None:
    #     raise RuntimeError(f"The cog Medicat is not intended for use by normal users. All functions are directly based on the id of a server.")
    asyncio.create_task(setup_after_ready(bot))

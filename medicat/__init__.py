from redbot.core.bot import Red  # isort:skip
from redbot.core.utils import get_end_user_data_statement

from .medicat import Medicat  # , MEDICAT_GUILD, TEST_GUILD

__red_end_user_data_statement__ = get_end_user_data_statement(file=__file__)


async def setup(bot: Red):
    # await bot.wait_until_ready()
    # if bot.get_guild(MEDICAT_GUILD) is None and bot.get_guild(TEST_GUILD) is None:
    #     raise RuntimeError(f"The cog Medicat is not intended for use by normal users. All functions are directly based on the id of a server.")
    cog = Medicat(bot)
    await cog.cogsutils.add_cog(bot)

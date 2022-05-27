from .AAA3A_utils.cogsutils import CogsUtils  # isort:skip
from redbot.core.bot import Red  # isort:skip
import json
from pathlib import Path

from .medicat import MEDICAT_GUILD, TEST_GUILD, Medicat

with open(Path(__file__).parent / "info.json") as fp:
    __red_end_user_data_statement__ = json.load(fp)["end_user_data_statement"]

async def setup(bot: Red):
    await bot.wait_until_ready()
    if bot.get_guild(MEDICAT_GUILD) is None and bot.get_guild(TEST_GUILD) is None:
        raise RuntimeError(f"The cog Medicat is not intended for use by normal users. All functions are directly based on the id of a server.")
    cog = Medicat(bot)
    await CogsUtils().add_cog(bot, cog)
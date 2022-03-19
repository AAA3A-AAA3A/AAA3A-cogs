from .AAA3A_utils.cogsutils import CogsUtils
import json
from pathlib import Path

from .autotraceback import AutoTraceback

with open(Path(__file__).parent / "info.json") as fp:
    __red_end_user_data_statement__ = json.load(fp)["end_user_data_statement"]

async def setup(bot):
    cog = AutoTraceback(bot)
    await CogsUtils().add_cog(bot, cog)
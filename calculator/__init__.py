from .AAA3A_utils.cogsutils import CogsUtils # isort:skip
import json
from pathlib import Path
if not CogsUtils().is_dpy2:
    from dislash import InteractionClient

from .calculator import Calculator

with open(Path(__file__).parent / "info.json") as fp:
    __red_end_user_data_statement__ = json.load(fp)["end_user_data_statement"]

async def setup(bot):
    cog = Calculator(bot)
    await CogsUtils().add_cog(bot, cog)
    if not CogsUtils().is_dpy2:
        if not hasattr(bot, "slash"):
            bot.slash = InteractionClient(bot)
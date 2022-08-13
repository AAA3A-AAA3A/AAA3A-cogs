from .AAA3A_utils.cogsutils import CogsUtils  # isort:skip
from redbot.core.bot import Red  # isort:skip
import json
from pathlib import Path

if not CogsUtils().is_dpy2:
    from dislash import InteractionClient

from .urlbuttons import UrlButtons

with open(Path(__file__).parent / "info.json") as fp:
    __red_end_user_data_statement__ = json.load(fp)["end_user_data_statement"]

async def setup(bot: Red):
    cog = UrlButtons(bot)
    await CogsUtils().add_cog(bot, cog)
    if not CogsUtils().is_dpy2:
        if not hasattr(bot, "slash"):
            bot.slash = InteractionClient(bot)
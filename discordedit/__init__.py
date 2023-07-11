from redbot.core import errors  # isort:skip
import importlib
import sys

try:
    import AAA3A_utils
except ModuleNotFoundError:
    raise errors.CogLoadError(
        "The needed utils to run the cog were not found. Please execute the command `[p]pipinstall git+https://github.com/AAA3A-AAA3A/AAA3A_utils.git`. A restart of the bot isn't necessary."
    )
modules = sorted(
    [module for module in sys.modules if module.split(".")[0] == "AAA3A_utils"], reverse=True
)
for module in modules:
    try:
        importlib.reload(sys.modules[module])
    except ModuleNotFoundError:
        pass
del AAA3A_utils
# import AAA3A_utils
# import json
# import os
# __version__ = AAA3A_utils.__version__
# with open(os.path.join(os.path.dirname(__file__), "utils_version.json"), mode="r") as f:
#     data = json.load(f)
# needed_utils_version = data["needed_utils_version"]
# if __version__ > needed_utils_version:
#     raise errors.CogLoadError(
#         "The needed utils to run the cog has a higher version than the one supported by this version of the cog. Please update the cogs of the `AAA3A-cogs` repo."
#     )
# elif __version__ < needed_utils_version:
#     raise errors.CogLoadError(
#         "The needed utils to run the cog has a lower version than the one supported by this version of the cog. Please execute the command `[p]pipinstall --upgrade git+https://github.com/AAA3A-AAA3A/AAA3A_utils.git`. A restart of the bot isn't necessary."
#     )

from redbot.core.bot import Red  # isort:skip
import asyncio

from redbot.core.utils import get_end_user_data_statement

from .discordedit import DiscordEdit

__red_end_user_data_statement__ = get_end_user_data_statement(file=__file__)

old_editrole = None


async def setup_after_ready(bot: Red) -> None:
    await bot.wait_until_red_ready()
    cog = DiscordEdit(bot)
    global old_editrole
    if old_editrole := bot.get_command("editrole"):
        bot.remove_command(old_editrole.name)
    await bot.add_cog(cog)


async def setup(bot: Red) -> None:
    asyncio.create_task(setup_after_ready(bot))


def teardown(bot: Red) -> None:
    if old_editrole is not None:
        bot.add_command(old_editrole)

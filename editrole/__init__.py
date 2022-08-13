from .AAA3A_utils.cogsutils import CogsUtils  # isort:skip
from redbot.core.bot import Red  # isort:skip
import asyncio
import json
from pathlib import Path

from .editrole import EditRole

with open(Path(__file__).parent / "info.json") as fp:
    __red_end_user_data_statement__ = json.load(fp)["end_user_data_statement"]

old_editrole = None

async def setup_after_ready(bot):
    global old_editrole
    await bot.wait_until_red_ready()
    cog = EditRole(bot)
    old_editrole = bot.get_command("editrole")
    if old_editrole:
        bot.remove_command(old_editrole.name)
    await CogsUtils().add_cog(bot, cog)

async def setup(bot: Red):
    asyncio.create_task(setup_after_ready(bot))

def teardown(bot: Red):
    bot.add_command(old_editrole)
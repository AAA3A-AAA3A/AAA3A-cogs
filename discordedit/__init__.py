from redbot.core.bot import Red  # isort:skip
import asyncio

from redbot.core.utils import get_end_user_data_statement

from .discordedit import DiscordEdit

__red_end_user_data_statement__ = get_end_user_data_statement(file=__file__)

old_editrole = None


async def setup_after_ready(bot) -> None:
    global old_editrole
    await bot.wait_until_red_ready()
    cog = DiscordEdit(bot)
    old_editrole = bot.get_command("editrole")
    if old_editrole:
        bot.remove_command(old_editrole.name)
    await cog.cogsutils.add_cog(bot)


async def setup(bot: Red) -> None:
    asyncio.create_task(setup_after_ready(bot))


def teardown(bot: Red) -> None:
    bot.add_command(old_editrole)

from redbot.core.bot import Red  # isort:skip
from redbot.core.utils import get_end_user_data_statement

from .ip import Ip

__red_end_user_data_statement__ = get_end_user_data_statement(file=__file__)


async def setup(bot: Red) -> None:
    cog = Ip(bot)
    await cog.cogsutils.add_cog(bot)

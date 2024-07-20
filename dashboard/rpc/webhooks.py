from redbot.core import commands  # isort:skip
from redbot.core.bot import Red  # isort:skip
import typing  # isort:skip

from .utils import rpc_check


class DashboardRPC_Webhooks:
    def __init__(self, cog: commands.Cog) -> None:
        self.bot: Red = cog.bot
        self.cog: commands.Cog = cog

        self.bot.register_rpc_handler(self.webhook_receive)

    def unload(self) -> None:
        self.bot.unregister_rpc_handler(self.webhook_receive)

    @rpc_check()
    async def webhook_receive(
        self, payload: typing.Dict[str, typing.Any]
    ) -> typing.Dict[str, int]:
        self.bot.dispatch("webhook_receive", payload)
        return {"status": 0}

import typing

from redbot.core import commands

from .utils import rpc_check

if typing.TYPE_CHECKING:
    from redbot.core.bot import Red


class DashboardRPC_Webhooks:
    def __init__(self, cog: commands.Cog) -> None:
        self.bot: Red = cog.bot
        self.cog: commands.Cog = cog

        self.bot.register_rpc_handler(self.webhook_receive)

    def unload(self) -> None:
        self.bot.unregister_rpc_handler(self.webhook_receive)

    @rpc_check()
    async def webhook_receive(self, payload: dict[str, typing.Any]) -> dict[str, int]:
        self.bot.dispatch("webhook_receive", payload)
        return {"status": 0}

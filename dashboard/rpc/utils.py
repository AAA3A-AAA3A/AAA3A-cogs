import typing  # isort:skip

import functools
from inspect import signature


def rpc_check():
    def conditional(func):
        @functools.wraps(func)
        async def rpccheckwrapped(self, *args, **kwargs) -> typing.Dict[str, typing.Any]:
            if self.bot.get_cog("Dashboard") is not None and self.bot.is_ready():
                return await func(self, *args, **kwargs)
            else:
                return {"disconnected": True}

        rpccheckwrapped.__signature__ = signature(
            func
        )  # Because aiohttp json rpc doesn't accept `*args, **kwargs`.
        return rpccheckwrapped

    return conditional

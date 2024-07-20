from redbot.core import commands  # isort:skip
from redbot.core.bot import Red  # isort:skip
import typing  # isort:skip


def dashboard_page(*args, **kwargs):
    def decorator(func: typing.Callable):
        func.__dashboard_decorator_params__ = (args, kwargs)
        return func

    return decorator


class DashboardIntegration:
    bot: Red
    documentations: typing.Dict[str, typing.Any]

    @commands.Cog.listener()
    async def on_dashboard_cog_add(self, dashboard_cog: commands.Cog) -> None:
        if hasattr(self, "settings") and hasattr(self.settings, "commands_added"):
            await self.settings.commands_added.wait()
        dashboard_cog.rpc.third_parties_handler.add_third_party(self)

    @dashboard_page(name="sources", hidden=True)
    async def rpc_callback_sources(self, **kwargs) -> typing.Dict[str, typing.Any]:
        return {"status": 0, "data": {"sources": list(self.documentations.keys())}}

    @dashboard_page(name="rtfm", hidden=True)
    async def rpc_callback_rtfm(
        self,
        source: str,
        query: str,
        limit: typing.Optional[int] = 10,
        with_std: typing.Optional[bool] = True,
        **kwargs,
    ) -> typing.Dict[str, typing.Any]:
        if isinstance(limit, str):
            try:
                limit = int(limit)
            except ValueError:
                return {"status": 1, "message": "`limit` argument must be an integer."}
        if isinstance(with_std, str):
            lowered = with_std.lower()
            if lowered in ("yes", "y", "true", "t", "1", "enable", "on"):
                with_std = True
            elif lowered in ("no", "n", "false", "f", "0", "disable", "off"):
                with_std = False
            else:
                return {"status": 1, "message": "`with_std` argument must be a boolean."}
        if source not in self.documentations:
            return {"status": 1, "message": "Source not found."}
        _source = self.documentations[source]
        results = await _source.search(query=query, limit=limit, exclude_std=not with_std)
        return {"status": 0, "source": source, "results": results.results}

    @dashboard_page(name="documentations", hidden=True)
    async def rpc_callback_documentations(
        self, source: str, documentation: str, **kwargs
    ) -> typing.Dict[str, typing.Any]:
        if source not in self.documentations:
            return {"status": 1, "message": "Source not found."}
        _source = self.documentations[source]
        documentation = await _source.get_documentation(documentation)
        if documentation is None:
            return {"status": 1, "message": "Documentation not found."}
        documentation = documentation.__dict__.copy()
        documentation["source"] = documentation["source"].name
        documentation["attributes"] = {
            key: {k: v.__dict__ for k, v in value.items()}
            for key, value in documentation["attributes"].__dict__.items()
        }
        return {"status": 0, "source": source, "documentation": documentation}

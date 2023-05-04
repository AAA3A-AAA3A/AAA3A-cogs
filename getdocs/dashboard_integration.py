from redbot.core import commands  # isort:skip
from redbot.core.bot import Red  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import types


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
        try:
            from dashboard.rpc.thirdparties import dashboard_page
        except ImportError:  # Should never happen because the event would not be dispatched by the Dashboard cog.
            return
        for attr in dir(self):
            if hasattr((func := getattr(self, attr)), "__dashboard_decorator_params__"):
                setattr(
                    self,
                    attr,
                    types.MethodType(
                        dashboard_page(
                            *func.__dashboard_decorator_params__[0],
                            **func.__dashboard_decorator_params__[1],
                        )(func.__func__),
                        func.__self__,
                    ),
                )
        dashboard_cog.rpc.third_parties_handler.add_third_party(self)

    @dashboard_page(name=None)
    async def rpc_callback(self, user: discord.User, **kwargs) -> dict:
        return {"status": 0, "web-content": web_content}

    @dashboard_page(name="sources", hidden=True)
    async def rpc_callback_sources(self, **kwargs) -> dict:
        return {"status": 0, "sources": list(self.documentations.keys())}

    @dashboard_page(name="rtfm", hidden=True)
    async def rpc_callback_rtfm(self, source: str, query: str, limit: typing.Optional[int] = 10, with_std: typing.Optional[bool] = True, **kwargs) -> dict:
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
    async def rpc_callback_documentations(self, source: str, documentation: str, **kwargs) -> dict:
        if source not in self.documentations:
            return {"status": 1, "message": "Source not found."}
        _source = self.documentations[source]
        documentation = await _source.get_documentation(documentation)
        if documentation is None:
            return {"status": 1, "message": "Documentation not found."}
        documentation = documentation.__dict__.copy()
        documentation["source"] = documentation["source"].name
        documentation["attributes"] = {key: {k: v.__dict__ for k, v in value.items()} for key, value in documentation["attributes"].__dict__.items()}
        return {"status": 0, "source": source, "documentation": documentation}


web_content = """
{% extends "base-site.html" %}

{% block title %} {{ _('GetDocs Cog') }} {% endblock title %}

{% block content %}
<h2>GetDocs Cog</h2>
<div class="row">
    <div class="col-md-12">
        <div class="card">
            <div class="card-body">
                <button class="btn", onclick="window.location.href = window.location.origin + window.location.pathname + '/settings';">Access to Settings</button>
            </div>
        </div>
    </div>
</div>
{% endblock content %}
"""

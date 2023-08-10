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

    @commands.Cog.listener()
    async def on_dashboard_cog_add(self, dashboard_cog: commands.Cog) -> None:
        if hasattr(self, "settings") and hasattr(self.settings, "commands_added"):
            await self.settings.commands_added.wait()
        try:
            from dashboard.rpc.thirdparties import dashboard_page
        except (
            ImportError
        ):  # Should never happen because the event would not be dispatched by the Dashboard cog.
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


web_content = """
{% extends "base-site.html" %}

{% block title %} {{ _('ClearChannel Cog') }} {% endblock title %}

{% block content %}
<h2>ClearChannel Cog</h2>
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

from redbot.core import commands  # isort:skip
from redbot.core.bot import Red  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import os

def dashboard_page(*args, **kwargs):
    def decorator(func: typing.Callable):
        func.__dashboard_decorator_params__ = (args, kwargs)
        return func
    return decorator


class DashboardIntegration:
    bot: Red

    @commands.Cog.listener()
    async def on_dashboard_cog_add(self, dashboard_cog: commands.Cog) -> None:
        dashboard_cog.rpc.third_parties_handler.add_third_party(self)

    # @dashboard_page(name=None, description="Create Embeds!")
    # async def global_callback(self, **kwargs) -> None:
    #     return {"status": 0, "web_content": {"source": '<iframe class="..." src="{{ url_for("third_parties_blueprint.third_party", name=name, page="editor") }}" style="width: 100%; height: 1000px; border: none;"></iframe>', "fullscreen": True}}

    @dashboard_page(name=None, description="Create Embeds!", hidden=True)
    async def dashboard_editor(self, **kwargs) -> None:
        file_path = os.path.join(os.path.dirname(__file__), "editor.html")
        with open(file_path, "rt") as f:
            source = f.read()
        return {"status": 0, "web_content": {"source": source, "standalone": True}}

from redbot.core import commands  # isort:skip
from redbot.core.bot import Red  # isort:skip
from redbot.core.i18n import Translator  # isort:skip
import typing  # isort:skip

_: Translator = Translator("AutoTraceback", __file__)


def dashboard_page(*args, **kwargs):
    def decorator(func: typing.Callable):
        func.__dashboard_decorator_params__ = (args, kwargs)
        return func

    return decorator


class DashboardIntegration:
    bot: Red
    tracebacks = []

    @commands.Cog.listener()
    async def on_dashboard_cog_add(self, dashboard_cog: commands.Cog) -> None:
        if hasattr(self, "settings") and hasattr(self.settings, "commands_added"):
            await self.settings.commands_added.wait()
        dashboard_cog.rpc.third_parties_handler.add_third_party(self)

    @dashboard_page(
        name=None,
        description="Display the traceback of the last occured exceptions.",
        is_owner=True,
    )
    async def rpc_callback(self, **kwargs) -> typing.Dict[str, typing.Any]:
        tracebacks = self.tracebacks.copy()
        if not tracebacks:
            return {"status": 0, "error_title": _("No exception has occurred yet.")}
        source = """
            {% for traceback in tracebacks %}
                {{ traceback|highlight("python") }}
                {% if not loop.last %}
                    <br />
                {% endif %}
            {% endfor %}
        """
        return {
            "status": 0,
            "web_content": {
                "source": source,
                "tracebacks": kwargs["Pagination"].from_list(
                    tracebacks,
                    per_page=kwargs["extra_kwargs"].get("per_page"),
                    page=kwargs["extra_kwargs"].get("page"),
                    default_per_page=1,
                    default_page=len(tracebacks),
                ),
            },
        }

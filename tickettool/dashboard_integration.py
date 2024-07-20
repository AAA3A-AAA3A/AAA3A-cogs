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

    @commands.Cog.listener()
    async def on_dashboard_cog_add(self, dashboard_cog: commands.Cog) -> None:
        if hasattr(self, "settings") and hasattr(self.settings, "commands_added"):
            await self.settings.commands_added.wait()
        dashboard_cog.rpc.third_parties_handler.add_third_party(self)

    @dashboard_page(name="transcript")
    async def rpc_callback_transcript(
        self, attachment_url: str, **kwargs
    ) -> typing.Dict[str, typing.Any]:
        if not attachment_url.startswith("https://cdn.discordapp.com/attachments/"):
            if len(attachment_url.split("-")) >= 3:
                attachment_url = f"{attachment_url.split('-')[0]}/{attachment_url.split('-')[1]}/{'-'.join(attachment_url.split('-')[2:])}"
            elif len(attachment_url.split("_")) >= 3:
                attachment_url = f"{attachment_url.split('_')[0]}/{attachment_url.split('_')[1]}/{'_'.join(attachment_url.split('_')[2:])}"
            attachment_url = f"https://cdn.discordapp.com/attachments/{attachment_url}"
        return {
            "status": 0,
            "web_content": {
                "source": '<iframe src="https://mahto.id/chat-exporter?url={{ attachment_url }}" style="width:100%; height:550px;"></iframe>',
                "attachment_url": attachment_url,
            },
        }

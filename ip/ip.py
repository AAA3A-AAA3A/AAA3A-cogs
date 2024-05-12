from AAA3A_utils import Cog, Settings  # isort:skip
from redbot.core import commands, Config  # isort:skip
from redbot.core.bot import Red  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
import typing  # isort:skip

import aiohttp

from .dashboard_integration import DashboardIntegration

# import socket

# Credits:
# General repo credits.
# Thanks to @AverageGamer on Discord for the cog idea and the code to find the external ip!
# Thanks to @Flanisch on GitHub for the use of Wikipedia headers instead of the site found before (https://github.com/AAA3A-AAA3A/AAA3A-cogs/pull/)!

_ = Translator("Ip", __file__)


@cog_i18n(_)
class Ip(Cog, DashboardIntegration):
    """A cog to get the ip address  of the bot's host machine!"""

    def __init__(self, bot: Red) -> None:
        super().__init__(bot=bot)

        self.config: Config = Config.get_conf(
            self,
            identifier=205192943327321000143939875896557571750,  # 969369062738
            force_registration=True,
        )
        self.config.register_global(port="0000")

        _settings: typing.Dict[
            str, typing.Dict[str, typing.Union[typing.List[str], bool, str]]
        ] = {
            "port": {
                "converter": commands.Range[str, 4, 4],
                "description": "Set the port.",
            },
        }
        self.settings: Settings = Settings(
            bot=self.bot,
            cog=self,
            config=self.config,
            group=self.config.GLOBAL,
            settings=_settings,
            global_path=[],
            use_profiles_system=False,
            can_edit=True,
            commands_group=self.ip_group,
        )

    async def cog_load(self) -> None:
        await super().cog_load()
        await self.settings.add_commands()

    @commands.is_owner()
    @commands.hybrid_group(name="ip")
    async def ip_group(self, ctx: commands.Context) -> None:
        """Commands group for Ip."""
        pass

    @ip_group.command()
    async def ip(self, ctx: commands.Context) -> None:
        """Get the ip address of the bot's host machine."""
        # hostname = socket.gethostname()
        async with aiohttp.ClientSession() as session:
            async with session.get("https://www.wikipedia.org", timeout=3) as r:
                ip = r.headers["X-Client-IP"]  # Gives the "public IP" of the Bot client PC
        await ctx.send(_("The ip address of your bot is `{ip}`.").format(ip=ip))

    @ip_group.command()
    async def website(self, ctx: commands.Context) -> None:
        """Get the ip address website of the bot's host machine."""
        # hostname = socket.gethostname()
        async with aiohttp.ClientSession() as session:
            async with session.get("https://www.wikipedia.org", timeout=3) as r:
                ip = r.headers["X-Client-IP"]  # Gives the "public IP" of the Bot client PC
        port = await self.config.port()
        await ctx.send(
            _("The Administrator Panel website is http://{ip}:{port}/.").format(ip=ip, port=port)
        )

from .AAA3A_utils import CogsUtils  # isort:skip
from redbot.core import Config, commands  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
from redbot.core.bot import Red  # isort:skip

import socket

import aiohttp

# Credits:
# Thanks to @epic guy on Discord for the basic syntax (command groups, commands) and also commands (await ctx.send, await ctx.author.send, await ctx.message.delete())!
# Thanks to @AverageGamer on Discord for the cog idea and the code to find the external ip!
# Thanks to @Flanisch on GitHub for the use of Wikipedia headers instead of the site found above! (https://github.com/AAA3A-AAA3A/AAA3A-cogs/pull/3)

_ = Translator("Ip", __file__)

if CogsUtils().is_dpy2:
    from functools import partial

    hybrid_command = partial(commands.hybrid_command, with_app_command=False)
    hybrid_group = partial(commands.hybrid_group, with_app_command=False)
else:
    hybrid_command = commands.command
    hybrid_group = commands.group


@cog_i18n(_)
class Ip(commands.Cog):
    """A cog to get the ip address of the bot!"""

    def __init__(self, bot: Red):
        self.bot: Red = bot

        self.config: Config = Config.get_conf(
            self,
            identifier=969369062738,
            force_registration=True,
        )
        self.ip_global = {
            "port": "0000",  # Port.
        }
        self.config.register_global(**self.ip_global)

        self.cogsutils = CogsUtils(cog=self)
        self.cogsutils._setup()

    @commands.is_owner()
    @hybrid_group(name="ip")
    async def ip_group(self, ctx: commands.Context):
        """Commands group for Ip."""
        pass

    @ip_group.command()
    async def ip(self, ctx: commands.Context):
        """Get the ip address of the bot."""
        hostname = socket.gethostname()
        async with aiohttp.ClientSession() as session:
            async with session.get("https://www.wikipedia.org", timeout=3) as r:
                ip = r.headers["X-Client-IP"]  # Gives the "public IP" of the Bot client PC
        await ctx.send(_("The ip address of your bot is `{ip}`.").format(**locals()))

    @ip_group.command()
    async def website(self, ctx: commands.Context):
        """Get the ip address website."""
        hostname = socket.gethostname()
        async with aiohttp.ClientSession() as session:
            async with session.get("https://www.wikipedia.org", timeout=3) as r:
                ip = r.headers["X-Client-IP"]  # Gives the "public IP" of the Bot client PC
        config = await self.config.all()
        port = config["port"]
        await ctx.send(
            _("The Administrator Panel website is http://{ip}:{port}/.").format(**locals())
        )

    @ip_group.command(name="setportip", aliases=["ipportset"], usage="<port>")
    async def setportip(self, ctx: commands.Context, *, port):
        """Set the port."""
        config = await self.config.all()

        actual_port = config["port"]
        if actual_port is port:
            await ctx.send(_("Port is already set on {port}.").format(**locals()))
            return

        await self.config.port.set(port)
        await ctx.send(_("Port registered: {port}.").format(**locals()))

from .AAA3A_utils.cogsutils import CogsUtils # isort:skip
import requests, socket
from redbot.core import commands, Config

# Credits:
# Thanks to @ AverageGamer on Discord for the cog idea and the code to find the external ip!
# Thanks to @ epic guy on Discord for the basic syntax (command groups, commands) and also commands (await ctx.send, await ctx.author.send, await ctx.message.delete())!

def _(untranslated: str):
    return untranslated

class Ip(commands.Cog):
    """A cog to get the ip address of the bot!"""

    def __init__(self, bot):
        self.bot = bot
        self.data: Config = Config.get_conf(
            self,
            identifier=969369062738,
            force_registration=True,
        )
        self.ip_global = {
            "port": None, # Port.
        }

        self.data.register_global(**self.ip_global)

        self.cogsutils = CogsUtils(cog=self)
        self.cogsutils._setup()

    @commands.guild_only()
    @commands.is_owner()
    @commands.command()
    async def ip(self, ctx: commands.Context):
        """Get the ip address of the bot."""
        hostname = socket.gethostname()
        ip = requests.get('http://ip.42.pl/raw').text  # Gives the "public IP" of the Bot client PC
        await ctx.send(_("The ip address of your bot is `{ip}`.").format(**locals()))

    @commands.guild_only()
    @commands.is_owner()
    @commands.command()
    async def website(self, ctx: commands.Context):
        """Get the ip adress website."""
        hostname = socket.gethostname()
        ip = requests.get('http://ip.42.pl/raw').text  # Gives the "public IP" of the Bot client PC
        config = await self.data.all()
        port = config["port"]
        await ctx.send(_("The Administrator Panel website is http://{ip}:{port}/.").format(**locals()))

    @commands.command(name="setportip", aliases=["ipportset"], usage="<port>")
    async def deletemessage(self, ctx: commands.Context, *, port):
        """Set the port.
        """
        config = await self.data.all()

        actual_port = config["port"]
        if actual_port is port:
            await ctx.send(_("Port is already set on {port}.").format(**locals()))
            return

        await self.data.port.set(port)
        await ctx.send(_("Port registered: {port}.").format(**locals()))
import discord, requests, socket
from redbot.core import checks, commands, data_manager, Config

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

    @commands.guild_only()
    @commands.is_owner()
    @commands.command()
    async def ip(self, ctx):
        """Get the ip address of the bot."""
        hostname = socket.gethostname()
        ip = requests.get('http://ip.42.pl/raw').text  # Gives the "public IP" of the Bot client PC
        await ctx.send("The ip address of your bot is `"+ip+"`.")

    @commands.guild_only()
    @commands.is_owner()
    @commands.command()
    async def website(self, ctx):
        """Get the ip adress website."""
        hostname = socket.gethostname()
        ip = requests.get('http://ip.42.pl/raw').text  # Gives the "public IP" of the Bot client PC
        config = await self.data.all()
        port = config["port"]
        await ctx.send("The Administrator Panel website is "+"http://"+ip+":"+port+"/"+".")

    async def red_get_data_for_user(self, *, user_id: int):
        # this cog does not store any data
        return {}

    async def red_delete_data_for_user(self, *, requester, user_id: int) -> None:
        # this cog does not store any data
        pass

    @commands.command(name="setportip", aliases=["ipportset"], usage="<port>")
    async def deletemessage(self, ctx, *, port):
        """Set the port.
        """
        config = await self.data.all()

        actual_port = config["port"]
        if actual_port is port:
            await ctx.send(f"Port is already set on {port}.")
            return

        await self.data.port.set(port)
        await ctx.send(f"Port registered: {port}.")

    @commands.is_owner()
    @commands.command()
    async def test(self, ctx):
        """Test"""
        abc = "903633188419682334"
        await abc.delete()
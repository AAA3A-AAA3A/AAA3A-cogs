from .AAA3A_utils.cogsutils import CogsUtils  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
from redbot.core.bot import Red  # isort:skip

import discord
from geopy import Nominatim

# Credits:
# Thanks to @epic guy on Discord for the basic syntax (command groups, commands) and also commands (await ctx.send, await ctx.author.send, await ctx.message.delete())!
# Thanks to the developers of the cogs I added features to as it taught me how to make a cog! (Chessgame by WildStriker, Captcha by Kreusada, Speak by Epic guy and Rommer by Dav)
# Thanks to all the people who helped me with some commands in the #coding channel of the redbot support server!

_ = Translator("GetLoc", __file__)

@cog_i18n(_)
class GetLoc(commands.Cog):
    """A cog to display information about a location based on its address or geographical coordinates!"""

    def __init__(self, bot):
        self.bot: Red = bot

        self.cogsutils = CogsUtils(cog=self)
        self.cogsutils._setup()

    @commands.command()
    async def getloc(self, ctx: commands.Context, *, adress_or_coordinates: str):
        """Display information about a location.
        You can provide a full address or gps coordinates.
        """
        loc = Nominatim(user_agent="GetLoc")
        try:
            localisation = loc.geocode(adress_or_coordinates, addressdetails=True)
        except Exception:
            await ctx.send(_("An error has occurred. Please try again.").format(**locals()))
            return
        if localisation is None:
            await ctx.send(_("The address or contact details you have provided do not lead to any results. Are you sure of your input?").format(**locals()))
            return
        message = {
            "Display Name": str(localisation.raw.get("display_name", None)),
            "Longitude": str(localisation.raw.get("lon", None)),
            "Latitude": str(localisation.raw.get("lat", None)),
            "Country": str(localisation.raw["address"].get("country", None)),
            "Country code": str(localisation.raw["address"].get("country_code", None)),
            "Region": str(localisation.raw["address"].get("region", None)),
            "State": str(localisation.raw["address"].get("state", None)),
            "County": str(localisation.raw["address"].get("county", None)),
            "Municipality": str(localisation.raw["address"].get("municipality", None)),
            "City": str(localisation.raw["address"].get("city", None)),
            "Post code": str(localisation.raw["address"].get("postcode", None)),
            "Road": str(localisation.raw["address"].get("road", None))
        }
        embed: discord.Embed = discord.Embed()
        embed.title = "Location"
        embed.set_thumbnail(url="https://img.myloview.fr/papiers-peints/globe-terrestre-dessin-colore-700-218492153.jpg")
        embed.description = "\n".join([f"**{name}**: {value}" for name, value in message.items()])
        await ctx.send(embed=embed)
from AAA3A_utils import Cog, CogsUtils  # isort:skip
from redbot.core import commands, errors  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
from redbot.core.bot import Red  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import asyncio
import functools
import io
import logging
import time

import matplotlib.pyplot as plt
import numpy as np
from geopy import Nominatim
try:
    from mpl_toolkits.basemap import Basemap
except ImportError:
    raise errors.CogLoadError(
        "The module `mpl_toolkits.basemap` were not found. Please execute the command `[p]pipinstall basemap`. A restart of the bot isn't necessary."
    )

# Credits:
# General repo credits.
# Thanks to this tutorial (https://makersportal.com/blog/2018/8/16/rotating-globe-in-python-using-basemap-toolkit) to generate the map!

_ = Translator("GetLoc", __file__)


CT = typing.TypeVar(
    "CT", bound=typing.Callable[..., typing.Any]
)  # defined CT as a type variable that is bound to a callable that can take any argument and return any value.

async def run_blocking_func(
    func: typing.Callable[..., typing.Any], *args: typing.Any, **kwargs: typing.Any
) -> typing.Any:
    partial = functools.partial(func, *args, **kwargs)
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, partial)


def executor(executor: typing.Any = None) -> typing.Callable[[CT], CT]:
    def decorator(func: CT) -> CT:
        @functools.wraps(func)
        def wrapper(*args: typing.Any, **kwargs: typing.Any):
            return run_blocking_func(func, *args, **kwargs)
        return wrapper
    return decorator


@cog_i18n(_)
class GetLoc(Cog):
    """A cog to display information about a location based on its address or geographical coordinates!"""

    def __init__(self, bot: Red) -> None:
        super().__init__(bot=bot)

    @executor()
    def get_map(self, title: str, latitude: float, longitude: float) -> io.BytesIO:
        # Don't spam the console...
        if "pyproj" in logging.Logger.manager.loggerDict:
            logging.Logger.manager.loggerDict["pyproj"].setLevel(logging.INFO)
        if "matplotlib.font_manager" in logging.Logger.manager.loggerDict:
            logging.Logger.manager.loggerDict["matplotlib.font_manager"].setLevel(logging.INFO)
        # Reset the figure.
        plt.clf()
        # set perspective angle
        lat_viewing_angle = latitude
        lon_viewing_angle = longitude
        # define color maps for water and land
        ocean_map = (plt.get_cmap("ocean"))(210)
        cmap = plt.get_cmap("gist_earth")
        # call the basemap and use orthographic projection at viewing angle
        m1 = Basemap(
            projection="ortho", lat_0=lat_viewing_angle, lon_0=lon_viewing_angle, resolution=None
        )
        # define map coordinates from full-scale globe
        map_coords_xy = [m1.llcrnrx, m1.llcrnry, m1.urcrnrx, m1.urcrnry]
        # map_coords_geo = [m1.llcrnrlat, m1.llcrnrlon, m1.urcrnrlat, m1.urcrnrlon]
        # zoom proportion and re-plot map
        zoom_prop = 2  # use 1.0 for full-scale map
        m = Basemap(
            projection="ortho",
            resolution="l",
            lat_0=lat_viewing_angle,
            lon_0=lon_viewing_angle,
            llcrnrx=-map_coords_xy[2] / zoom_prop,
            llcrnry=-map_coords_xy[3] / zoom_prop,
            urcrnrx=map_coords_xy[2] / zoom_prop,
            urcrnry=map_coords_xy[3] / zoom_prop,
        )
        # coastlines, map boundary, fill continents/water, fill ocean, draw countries
        m.drawmapboundary(fill_color=ocean_map)
        m.fillcontinents(color=cmap(200), lake_color=ocean_map)
        m.drawcoastlines()
        m.drawcountries()
        # latitude/longitude line vectors
        lat_line_range = [-90, 90]
        lat_lines = 8
        lat_line_count = (lat_line_range[1] - lat_line_range[0]) / lat_lines
        merid_range = [-180, 180]
        merid_lines = 8
        merid_count = (merid_range[1] - merid_range[0]) / merid_lines
        m.drawparallels(np.arange(lat_line_range[0], lat_line_range[1], lat_line_count))
        m.drawmeridians(np.arange(merid_range[0], merid_range[1], merid_count))
        # scatter to indicate lat/lon point
        x, y = m(lon_viewing_angle, lat_viewing_angle)
        m.scatter(
            x, y, marker="o", color="#DDDDDD", s=3000, zorder=10, alpha=0.7, edgecolor="#000000"
        )
        m.scatter(
            x, y, marker="o", color="#000000", s=100, zorder=10, alpha=0.7, edgecolor="#000000"
        )
        plt.annotate(
            title,
            xy=(x, y),
            xycoords="data",
            xytext=(-110, -10),
            textcoords="offset points",
            color="k",
            fontsize=12,
            bbox=dict(facecolor="w", alpha=0.5),
            arrowprops=dict(arrowstyle="fancy", color="k"),
            zorder=20,
        )
        # save figure at 150 dpi and show it
        _map = io.BytesIO()
        plt.savefig(_map, dpi=500, transparent=True)
        _map.seek(0)
        return _map

    @commands.cooldown(rate=3, per=3600, type=commands.BucketType.member)
    @commands.hybrid_command()
    async def getloc(
        self,
        ctx: commands.Context,
        with_map: typing.Optional[bool] = True,
        *,
        adress_or_coordinates: str,
    ) -> None:
        """Display information about a location.
        You can provide a full address or gps coordinates.
        """
        start: float = time.monotonic()
        loc = Nominatim(user_agent="GetLoc")
        try:
            localisation = loc.geocode(query=adress_or_coordinates, addressdetails=True)
        except Exception:
            raise commands.UserFeedbackCheckFailure(_("An error has occurred. Please try again."))
        if localisation is None:
            raise commands.UserFeedbackCheckFailure(
                _(
                    "The address or contact details you have provided do not lead to any results. Are you sure of your input?"
                )
            )
        data = {
            "Display Name": localisation.raw.get("display_name", None),
            "Latitude": localisation.latitude,
            "Longitude": localisation.longitude,
            "Country": localisation.raw["address"].get("country", None),
            "Country code": localisation.raw["address"].get("country_code", None),
            "Region": localisation.raw["address"].get("region", None),
            "State": localisation.raw["address"].get("state", None),
            "County": localisation.raw["address"].get("county", None),
            "Municipality": localisation.raw["address"].get("municipality", None),
            "City": localisation.raw["address"].get("city", None),
            "Post code": localisation.raw["address"].get("postcode", None),
            "Road": localisation.raw["address"].get("road", None),
        }
        embed: discord.Embed = discord.Embed()
        embed.title = "Location"
        embed.set_thumbnail(
            url="https://img.myloview.fr/papiers-peints/globe-terrestre-dessin-colore-700-218492153.jpg"
        )
        embed.description = "\n".join([f"**{name}**: {value}" for name, value in data.items()])

        if with_map:
            embed.set_image(url="attachment://map.png")
            _map = await self.get_map(
                title=", ".join(data['Display Name'].split(", ")[:2]),  # (Latitude {localisation.latitude}) ; Longitude {localisation.longitude})",
                latitude=localisation.latitude,
                longitude=localisation.longitude,
            )
            file = discord.File(
                fp=_map,
                filename="map.png",
                description=str(localisation.raw.get("display_name", None)),
            )
        else:
            file = None

        end: float = time.monotonic()
        embed.set_footer(text=f"Generated in {end - start}s.")

        await ctx.reply(
            embed=embed, file=file, allowed_mentions=discord.AllowedMentions(replied_user=False)
        )

    @commands.Cog.listener()
    async def on_assistant_cog_add(self, assistant_cog: typing.Optional[commands.Cog] = None) -> None:  # Vert's Assistant integration/third party.
        schema = {
            "name": "get_informations_about_a_place",
            "description": "Get informations about a place in the world, from a fuzzy location query.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The place to search in the world."
                    },
                },
                "required": [
                    "query"
                ]
            },
        }
        async def get_informations_about_a_place(query: str, *args, **kwargs):
            loc = Nominatim(user_agent="GetLoc")
            try:
                localisation = loc.geocode(query=query, addressdetails=True)
            except Exception:
                return "An error has occurred."
            if localisation is None:
                return "The provided address or contact details do not lead to any results."
            data = {
                "Display Name": localisation.raw.get("display_name", None),
                "Latitude": localisation.latitude,
                "Longitude": localisation.longitude,
                "Country": localisation.raw["address"].get("country", None),
                "Country code": localisation.raw["address"].get("country_code", None),
                "Region": localisation.raw["address"].get("region", None),
                "State": localisation.raw["address"].get("state", None),
                "City": localisation.raw["address"].get("city", None),
                "Post code": localisation.raw["address"].get("postcode", None),
            }
            return [f"{key}: {value}\n" for key, value in data.items() if value is not None]
        if assistant_cog is None:
            return get_informations_about_a_place
        await assistant_cog.register_function(cog=self, schema=schema, function=get_informations_about_a_place)

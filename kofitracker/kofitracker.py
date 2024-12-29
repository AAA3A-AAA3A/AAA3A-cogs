from AAA3A_utils import Cog, Menu  # isort:skip
from redbot.core import commands, Config  # isort:skip
from redbot.core.bot import Red  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

# import aiohttp
import asyncio
import functools
import time

import requests
from bs4 import BeautifulSoup

# Credits:
# General repo credits.

_: Translator = Translator("KoFiTracker", __file__)

HEADERS: typing.Dict[str, str] = {
    "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2227.0 Safari/537.36"
}


def cache_results(duration=60):
    def decorator_cache(func):
        cache = {}

        @functools.wraps(func)
        def wrapper_cache(*args, **kwargs):
            cache_key = (args, frozenset(kwargs.items()))
            if cache_key in cache:
                result, timestamp = cache[cache_key]
                if time.time() - timestamp < duration:
                    return result
            result = func(*args, **kwargs)
            cache[cache_key] = (result, time.time())
            return result

        return wrapper_cache

    return decorator_cache


@cog_i18n(_)
class KoFiTracker(Cog):
    """Track donations, subscriptions and shop orders on KoFi!"""

    def __init__(self, bot: Red) -> None:
        super().__init__(bot=bot)

        self.config: Config = Config.get_conf(
            self,
            identifier=205192943327321000143939875896557571750,
            force_registration=True,
        )
        self.config.register_channel(
            kofi_pages={},
        )

        # self._session: aiohttp.ClientSession = None

    async def cog_load(self) -> None:
        await super().cog_load()
        # self._session: aiohttp.ClientSession = aiohttp.ClientSession(headers=HEADERS, raise_for_status=True)

    async def cog_unload(self) -> None:
        # if self._session is not None:
        #     await self._session.close()
        await super().cog_unload()

    @cache_results()
    async def get_kofi_page_details(self, kofi_page_url: str) -> typing.Dict[str, str]:
        kofi_page_url = kofi_page_url.removeprefix("https://ko-fi.com/").lower()
        # async with self._session.get(f"https://ko-fi.com/{kofi_page_url}") as r:
        #     data = await r.text()
        r = await asyncio.to_thread(
            requests.get, url=f"https://ko-fi.com/{kofi_page_url}", headers=HEADERS
        )
        data = r.text
        soup = BeautifulSoup(data, "lxml")
        data = {
            "url": f"https://ko-fi.com/{kofi_page_url}",
            "display_name": soup.select_one(".kfds-font-size-22 > span").text,
            "avatar_url": (
                soup.select_one("img#profilePicture")["src"]
                if soup.select_one("img#profilePicture") is not None
                else "https://ko-fi.com/img/anon2.png"
            ),
            "banner_url": soup.find("meta", property="og:image")["content"],
            "about_me": soup.select_one(".kfds-btm-mrgn-8 > .kfds-c-para-control").text,
            "received_amount": soup.select_one(".koficounter-value").text + " coffees",
            "goal_title": (
                None
                if soup.select_one(".kfds-btm-mrgn-24 > .text-left").text.startswith("\n")
                and soup.select_one(".kfds-btm-mrgn-24 > .text-left").text.endswith("\n")
                else soup.select_one(".kfds-btm-mrgn-24 > .text-left").text
            ),
            "goal_description": getattr(soup.select_one(".goal-description"), "text", None),
            "current_percentage": (
                soup.select_one(".text-left > .kfds-font-bold").text
                if soup.select_one(".text-left > .kfds-font-bold").text != "Report Abuse"
                else None
            ),
            "of_goal_total": getattr(soup.select_one(".goal-label"), "text", None),
        }
        return data

    @commands.Cog.listener()
    async def on_webhook_receive(self, payload: typing.Dict[str, typing.Any]) -> None:
        if (
            payload.get("type") not in ("Donation", "Subscription", "Shop Order")
            or "verification_token" not in payload
        ):
            return
        for channel_id, channels_data in (await self.config.all_channels()).items():
            for kofi_page_url, data in channels_data["kofi_pages"].items():
                if payload["verification_token"] != data["verification_token"]:
                    continue
                if payload["type"] not in data["types"]:
                    continue
                if not payload["is_public"] and not data["show_private"]:
                    continue
                if (
                    (channel := self.bot.get_channel(channel_id)) is None
                    or (guild := channel.guild) is None
                    or await self.bot.cog_disabled_in_guild(cog=self, guild=guild)
                ):
                    continue

                kofi_page_details = await self.get_kofi_page_details(kofi_page_url)
                embed: discord.Embed = discord.Embed(
                    title=_("New {type} on {display_name}'s KoFi").format(
                        type=payload["type"], display_name=kofi_page_details["display_name"]
                    ),
                    url=payload["url"],
                    color=discord.Color.red(),
                    timestamp=discord.utils.parse_time(payload["timestamp"]),
                )
                embed.set_thumbnail(url=kofi_page_details["avatar_url"])
                # embed.set_image(url=kofi_page_details["banner_url"])

                embed.set_author(
                    name=payload["from_name"],
                    icon_url="https://storage.ko-fi.com/cdn/nav-logo-stroke.png",
                )
                embed.add_field(
                    name=_("Amount:"),
                    value=f"{payload['amount']} {payload['currency']}",
                    inline=False,
                )
                if payload["message"]:
                    embed.add_field(name=_("Message:"), value=payload["message"], inline=False)
                if payload["type"] == "Subscription":
                    if payload["tier_name"]:
                        embed.add_field(name=_("Tier:"), value=payload["tier_name"], inline=True)
                    if payload["is_first_subscription_payment"]:
                        embed.add_field(
                            name="\u200b", value=_("(First Subscription Payment)"), inline=False
                        )
                elif payload["type"] == "Shop Order":
                    embed.add_field(
                        name=_("Shop Items:"),
                        value="\n".join(
                            [
                                f"**•** **{item['quantity']}x** {item['variation_name']}"
                                for item in payload["shop_items"]
                            ]
                        ),
                        inline=True,
                    )
                    if payload["shipping"] and data["show_personal_details"]:
                        embed.add_field(
                            name=_("Shipping Details:"),
                            value=_(
                                "**{full_name}**\n"
                                "{street_address}\n"
                                "{city}, {state_or_province} {postal_code}\n"
                                "{country} ({country_code})\n"
                                "{telephone}"
                            ).format(**payload["shipping"]),
                            inline=False,
                        )
                if data["show_personal_details"]:
                    embed.add_field(
                        name=_("Email:"),
                        value=f"[{payload['email']}](mailto:{payload['email']})",
                        inline=False,
                    )
                embed.add_field(
                    name="\u200b",
                    value=f"||Transaction ID: `{payload['kofi_transaction_id']}`||",
                    inline=False,
                )

                embed.set_footer(
                    text=_("Received from KoFi."),
                    icon_url="https://storage.ko-fi.com/cdn/nav-logo-stroke.png",
                )
                view: discord.ui.View = discord.ui.View()
                view.add_item(
                    discord.ui.Button(
                        emoji="❤️",
                        label=_("Support {display_name} on KoFi!").format(
                            display_name=kofi_page_details["display_name"]
                        ),
                        url=kofi_page_details["url"],
                        style=discord.ButtonStyle.link,
                    )
                )
                try:
                    await channel.send(embed=embed, view=view)
                except discord.HTTPException as e:
                    self.logger.error(
                        f"Error when sending KoFi notification in `{channel.name}` ({channel.id}).",
                        exc_info=e,
                    )

    @commands.hybrid_command()
    async def kofiprofile(self, ctx: commands.Context, kofi_page_url: str) -> None:
        """Get the details of a KoFi profile."""
        kofi_page_url = kofi_page_url.removeprefix("https://ko-fi.com/").lower()
        try:
            kofi_page_details = await self.get_kofi_page_details(kofi_page_url)
        except aiohttp.ClientResponseError:
            raise commands.UserFeedbackCheckFailure(_("This KoFi page does not exist."))

        embed: discord.Embed = discord.Embed(
            title=_("{display_name}'s KoFi").format(
                display_name=kofi_page_details["display_name"]
            ),
            url=kofi_page_details["url"],
            color=discord.Color.red(),
        )
        embed.set_thumbnail(url=kofi_page_details["avatar_url"])
        embed.set_image(url=kofi_page_details["banner_url"])
        embed.add_field(name=_("About Me:"), value=kofi_page_details["about_me"], inline=False)
        embed.add_field(
            name=_("Received Amount:"), value=kofi_page_details["received_amount"], inline=False
        )
        if kofi_page_details["goal_title"] is not None:
            embed.add_field(
                name=_("Goal Title:"), value=kofi_page_details["goal_title"], inline=False
            )
            embed.add_field(
                name=_("Goal Description:"),
                value=kofi_page_details["goal_description"],
                inline=False,
            )
            embed.add_field(
                name=_("Current Percentage:"),
                value=kofi_page_details["current_percentage"],
                inline=False,
            )
            embed.add_field(
                name=_("Of Goal Total:"), value=kofi_page_details["of_goal_total"], inline=False
            )
        embed.set_footer(
            text=_("Fetched from KoFi."),
            icon_url="https://storage.ko-fi.com/cdn/nav-logo-stroke.png",
        )

        view: discord.ui.View = discord.ui.View()
        view.add_item(
            discord.ui.Button(
                emoji="❤️",
                label=_("Support {display_name} on KoFi!").format(
                    display_name=kofi_page_details["display_name"]
                ),
                url=kofi_page_details["url"],
                style=discord.ButtonStyle.link,
            )
        )
        await ctx.send(embed=embed, view=view)

    @commands.guild_only()
    @commands.admin_or_permissions(administrator=True)
    @commands.hybrid_group()
    async def setkofitracker(self, ctx: commands.Context) -> None:
        """Commands to configure KoFiTracker."""
        pass

    @setkofitracker.command(aliases=["+"])
    async def add(
        self,
        ctx: commands.Context,
        channel: typing.Optional[
            typing.Union[discord.TextChannel, discord.VoiceChannel, discord.Thread]
        ],
        kofi_page_url: str,
        verification_token: str,
        types: commands.Greedy[typing.Literal["Donation", "Subscription", "Shop Order"]] = [
            "Donation",
            "Subscription",
            "Shop Order",
        ],
        show_private: bool = False,
        show_personal_details: bool = False,
    ) -> None:
        """Add a KoFi page to track.

        ⚠ **Note:** If you choose to show personal details, the user's email and shipping details will be shown to everyone in the channel.
        """
        if channel is None:
            channel = ctx.channel
        kofi_pages = await self.config.channel(channel).kofi_pages()
        kofi_page_url = kofi_page_url.removeprefix("https://ko-fi.com/").lower()
        if kofi_page_url in kofi_pages:
            raise commands.UserFeedbackCheckFailure(_("This KoFi page is already being tracked."))
        kofi_pages[kofi_page_url] = {
            "verification_token": verification_token,
            "types": types,
            "show_private": show_private,
            "show_personal_details": show_personal_details,
        }
        await self.config.channel(channel).kofi_pages.set(kofi_pages)

    @setkofitracker.command(aliases=["-"])
    async def remove(
        self,
        ctx: commands.Context,
        channel: typing.Optional[
            typing.Union[discord.TextChannel, discord.VoiceChannel, discord.Thread]
        ],
        kofi_page_url: str,
    ) -> None:
        """Remove a KoFi page from tracking."""
        if channel is None:
            channel = ctx.channel
        kofi_pages = await self.config.channel(channel).kofi_pages()
        kofi_page_url = kofi_page_url.removeprefix("https://ko-fi.com/").lower()
        if kofi_page_url not in kofi_pages:
            raise commands.UserFeedbackCheckFailure(_("This KoFi page is not being tracked."))
        del kofi_pages[kofi_page_url]
        await self.config.channel(channel).kofi_pages.set(kofi_pages)

    @setkofitracker.command()
    async def list(
        self,
        ctx: commands.Context,
        channel: typing.Optional[
            typing.Union[discord.TextChannel, discord.VoiceChannel, discord.Thread]
        ],
    ) -> None:
        """List the KoFi pages being tracked."""
        if channel is None:
            channel = ctx.channel
        kofi_pages = await self.config.channel(channel).kofi_pages()
        if not kofi_pages:
            raise commands.UserFeedbackCheckFailure(_("No KoFi pages are being tracked."))
        embed: discord.Embed = discord.Embed(
            title=_("KoFi Pages being tracked in {channel}").format(channel=channel),
            color=await ctx.embed_color(),
        )
        embeds = []
        for k_pages in discord.utils.as_chunks(kofi_pages.items(), max_size=10):
            e = embed.copy()
            e.description = "\n".join(
                [
                    f"**•** **[{kofi_page_url}](https://ko-fi.com/{kofi_page_url})**\n> {data}"
                    for kofi_page_url, data in k_pages
                ]
            )
            embeds.append(e)
        await Menu(pages=embeds).start(ctx)

    @commands.bot_has_permissions(embed_links=True)
    @setkofitracker.command()
    async def instructions(self, ctx: commands.Context) -> None:
        """Instructions on how to set up KoFiTracker."""
        if (dashboard_url := getattr(ctx.bot, "dashboard_url", None)) is None:
            raise commands.UserFeedbackCheckFailure(
                _(
                    "Red-Dashboard is not installed. Check <https://red-web-dashboard.readthedocs.io>."
                )
            )
        if not dashboard_url[1] and ctx.author.id not in ctx.bot.owner_ids:
            raise commands.UserFeedbackCheckFailure(_("You can't access the Dashboard."))
        embed: discord.Embed = discord.Embed(
            title=_("KoFiTracker Instructions"),
            color=await ctx.embed_color(),
            description=_(
                "**1.** Go to [KoFi](https://ko-fi.com) and log in.\n"
                "**2.** Go to your page and click on the `Settings` button.\n"
                "**3.** Go to the `Webhooks` section in `More`.\n"
                "**4.** Set the webhook URL to {webhook_url} and click on `Update`.\n"
                "**5.** Copy the `Verification Token` and use it with the command `{prefix}setkofitracker add <kofi_page_url> <verification_token>`."
            ).format(webhook_url=f"{dashboard_url[0]}/api/webhook", prefix=ctx.prefix),
        )
        await ctx.send(embed=embed)

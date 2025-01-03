from AAA3A_utils import Cog, Loop, Menu  # isort:skip
from redbot.core import commands, Config  # isort:skip
from redbot.core.bot import Red  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
import discord  # isort:skip
import typing  # isort:skip
import typing_extensions  # isort:skip

import asyncio
import base64
import re
from io import BytesIO
from uuid import UUID

import aiohttp
from mcstatus import JavaServer
from redbot.core.utils.chat_formatting import box, pagify

# Credits:
# General repo credits.
# Thanks to Fixator for the code to get informations about Minecraft servers (https://github.com/fixator10/Fixator10-Cogs/blob/V3/minecraftdata/minecraftdata.py)!

_: Translator = Translator("Minecraft", __file__)


class MCPlayer:
    def __init__(self, name: str, uuid: str) -> None:
        self.name: str = name
        self.uuid: str = uuid
        self.dashed_uuid: str = str(UUID(self.uuid))

    def __str__(self) -> str:
        return self.name

    @classmethod
    async def convert(cls, ctx: commands.Context, argument: str) -> typing_extensions.Self:
        cog = ctx.bot.get_cog("Minecraft")
        try:
            async with cog._session.get(
                f"https://api.mojang.com/users/profiles/minecraft/{argument}",
                raise_for_status=True,
            ) as r:
                response_data = await r.json()
        except aiohttp.ContentTypeError:
            response_data = None
        except aiohttp.ClientResponseError as e:
            raise commands.BadArgument(
                _("Unable to get data from Minecraft API: {e.message}.").format(e=e)
            )
        if response_data is None or "id" not in response_data:
            raise commands.BadArgument(
                _("{argument} not found on Mojang servers.").format(argument=argument)
            )
        uuid = str(response_data["id"])
        name = str(response_data["name"])
        try:
            return cls(name=name, uuid=uuid)
        except ValueError:
            raise commands.BadArgument(
                _("{argument} is found, but has incorrect UUID.").format(argument=argument)
            )


@cog_i18n(_)
class Minecraft(Cog):
    """A cog to display informations about Minecraft Java users and servers, and notify for each change of a server!"""

    def __init__(self, bot: Red) -> None:
        super().__init__(bot=bot)

        self._session: aiohttp.ClientSession = None
        self.cache: typing.Dict[int, typing.Dict[str, dict]] = {}

        self.config: Config = Config.get_conf(
            self,
            identifier=205192943327321000143939875896557571750,
            force_registration=True,
        )
        self.config.register_channel(
            servers={},
            check_players=False,
            edit_last_message=False,
        )

    async def cog_load(self) -> None:
        await super().cog_load()
        self._session: aiohttp.ClientSession = aiohttp.ClientSession()
        self.loops.append(
            Loop(
                cog=self,
                name="Check Minecraft Servers",
                function=self.check_servers,
                minutes=1,
            )
        )

    async def cog_unload(self) -> None:
        await self._session.close()
        await super().cog_unload()

    async def check_servers(self) -> None:
        all_channels = await self.config.all_channels()
        for channel_id in all_channels:
            channel = self.bot.get_channel(channel_id)
            if channel is None:
                continue
            if channel.id not in self.cache:
                self.cache[channel.id] = {}
            servers = all_channels[channel_id]["servers"]
            check_players = all_channels[channel_id]["check_players"]
            for server_url in servers:
                try:
                    server: JavaServer = await JavaServer.async_lookup(address=server_url.lower())
                    status = await server.async_status()
                except (asyncio.CancelledError, TimeoutError):
                    continue
                except Exception as e:
                    self.logger.error(
                        f"No data found for {server_url} server in {channel.id} channel in {channel.guild.id} guild.",
                        exc_info=e,
                    )
                    continue
                if check_players and "sample" in status.raw["players"]:
                    players = {player["id"]: player for player in status.raw["players"]["sample"]}
                    players = [players[_id] for _id in set(list(players.keys()))]
                else:
                    players = {}
                status.raw["players"]["sample"] = players
                if server_url not in self.cache[channel.id]:
                    self.cache[channel.id][server_url] = {"server": server, "status": status}
                    continue
                if status.raw != self.cache[channel.id][server_url]["status"].raw:
                    if "This server is offline." in (
                        await self.clear_mcformatting(status.description)
                    ) and "This server is offline." in (
                        await self.clear_mcformatting(
                            self.cache[channel.id][server_url]["status"].description
                        )
                    ):  # Minecraft ADS
                        continue
                    embed, icon = await self.get_embed(server, status)
                    servers = await self.config.channel(channel).servers()
                    if isinstance(servers, typing.List):
                        servers = {server: None for server in servers}
                    if (
                        await self.config.channel(channel).edit_last_message()
                        and servers[server_url] is not None
                    ):
                        try:
                            message = await channel.get_partial_message(servers[server_url]).edit(
                                embed=embed, attachments=[icon]
                            )
                        except discord.HTTPException:
                            message = await channel.send(embed=embed, file=icon)
                    else:
                        message = await channel.send(embed=embed, file=icon)
                    servers[server_url] = message.id
                    await self.config.channel(channel).servers.set(servers)
                    self.cache[channel.id][server_url] = {"server": server, "status": status}

    async def get_embed(self, server: JavaServer, status) -> discord.Embed:
        server_description = await self.clear_mcformatting(status.description)
        embed: discord.Embed = discord.Embed(
            title=f"{server.address.host}:{server.address.port}",
            description=box(server_description),
        )
        embed.color = (
            discord.Color.red()
            if "This server is offline." in server_description
            else (
                discord.Color.orange()
                if "This server is currently stopping." in server_description
                else discord.Color.green()
            )
        )
        icon_file = None
        icon = (
            discord.File(
                icon_file := BytesIO(base64.b64decode(status.icon.removeprefix("data:image/png;base64,"))),
                filename="icon.png",
            )
            if status.icon
            else None
        )
        if icon:
            embed.set_thumbnail(url="attachment://icon.png")
        embed.add_field(name=_("Latency"), value=f"{status.latency:.2f} ms")
        embed.add_field(
            name=_("Players"),
            value="{status.players.online}/{status.players.max}\n{players_list}".format(
                status=status,
                players_list=(
                    box(
                        list(
                            pagify(
                                await self.clear_mcformatting(
                                    "\n".join([p.name for p in status.players.sample])
                                ),
                                page_length=992,
                            )
                        )[0]
                    )
                    if status.players.sample
                    else ""
                ),
            ),
        )
        embed.add_field(
            name=_("Version"),
            value=f"{status.version.name}\nProtocol: {status.version.protocol}",
        )
        if icon_file is not None:
            icon_file.close()
        return embed, icon

    async def clear_mcformatting(self, formatted_str) -> str:
        """Remove Minecraft-formatting"""
        if not isinstance(formatted_str, dict):
            return re.sub(r"\xA7[0-9A-FK-OR]", "", formatted_str, flags=re.IGNORECASE)
        clean = ""
        async for text in self.gen_dict_extract("text", formatted_str):
            clean += text
        return re.sub(r"\xA7[0-9A-FK-OR]", "", clean, flags=re.IGNORECASE)

    async def gen_dict_extract(self, key: str, var: dict) -> str:
        if not hasattr(var, "items"):
            return
        for k, v in var.items():
            if k == key:
                yield v
            if isinstance(v, typing.Dict):
                async for result in self.gen_dict_extract(key, v):
                    yield result
            elif isinstance(v, typing.List):
                for d in v:
                    async for result in self.gen_dict_extract(key, d):
                        yield result

    @commands.hybrid_group()
    async def minecraft(self, ctx: commands.Context):
        """Get informations about Minecraft Java."""
        pass

    @commands.bot_has_permissions(attach_files=True, embed_links=True)
    @minecraft.command()
    async def getplayerskin(
        self, ctx: commands.Context, player: MCPlayer, overlay: bool = False
    ) -> None:
        """Get Minecraft Java player skin by name."""
        uuid = player.uuid
        stripname = player.name.strip("_")
        files = []
        try:
            async with self._session.get(
                f"https://crafatar.com/renders/head/{uuid}",
                params="overlay" if overlay else None,
            ) as s:
                files.append(
                    discord.File(BytesIO(await s.read()), filename=f"{stripname}_head.png")
                )
            async with self._session.get(f"https://crafatar.com/skins/{uuid}") as s:
                files.append(discord.File(BytesIO(await s.read()), filename=f"{stripname}.png"))
            async with self._session.get(
                f"https://crafatar.com/renders/body/{uuid}.png",
                params="overlay" if overlay else None,
            ) as s:
                files.append(
                    discord.File(BytesIO(await s.read()), filename=f"{stripname}_body.png")
                )
        except aiohttp.ClientResponseError as e:
            raise commands.UserFeedbackCheckFailure(
                _("Unable to get data from Crafatar: {}").format(e.message)
            )
        embed: discord.Embed = discord.Embed(
            timestamp=ctx.message.created_at, color=await ctx.embed_color()
        )
        embed.set_author(
            name=player.name,
            icon_url=f"attachment://{stripname}_head.png",
            url=f"https://crafatar.com/skins/{uuid}",
        )
        embed.set_thumbnail(url=f"attachment://{stripname}.png")
        embed.set_image(url=f"attachment://{stripname}_body.png")
        embed.set_footer(text=_("Provided by Crafatar."), icon_url="https://crafatar.com/logo.png")
        await ctx.send(embed=embed, files=files)

    @commands.bot_has_permissions(attach_files=True, embed_links=True)
    @minecraft.command()
    async def getserver(self, ctx: commands.Context, server_url: str) -> None:
        """Get informations about a Minecraft Java server."""
        try:
            server: JavaServer = await JavaServer.async_lookup(address=server_url.lower())
            status = await server.async_status()
        except Exception:
            raise commands.UserFeedbackCheckFailure(
                _(
                    "No data found for this Minecraft server. Maybe it doesn't exist or its data are temporarily unavailable."
                )
            )
        embed, icon = await self.get_embed(server, status)
        await ctx.send(embed=embed, file=icon)

    @commands.admin_or_permissions(manage_guild=True)
    @minecraft.command(aliases=["add", "+"])
    async def addserver(
        self, ctx: commands.Context, channel: typing.Optional[discord.TextChannel], server_url: str
    ) -> None:
        """Add a Minecraft Java server in Config to get automatically new status."""
        if channel is None:
            channel = ctx.channel
        channel_permissions = channel.permissions_for(ctx.me)
        if (
            not channel_permissions.view_channel
            or not channel_permissions.read_messages
            or not channel_permissions.read_message_history
            or not channel_permissions.embed_links
        ):
            raise commands.UserFeedbackCheckFailure(
                _(
                    "I don't have sufficient permissions in this channel to send messages with embeds."
                )
            )
        servers = await self.config.channel(channel).servers()
        if server_url.lower() in servers:
            raise commands.UserFeedbackCheckFailure(_("This server has already been added."))
        try:
            server: JavaServer = await JavaServer.async_lookup(address=server_url.lower())
            await server.async_status()
        except Exception:
            raise commands.UserFeedbackCheckFailure(
                _(
                    "No data found for this Minecraft server. Maybe it doesn't exist or its data are temporarily unavailable."
                )
            )
        if isinstance(servers, typing.List):
            servers = {server: None for server in servers}
        servers[server_url.lower()] = None  # last message
        await self.config.channel(channel).servers.set(servers)
        await ctx.send(_("Server added to this channel."))

    @commands.admin_or_permissions(manage_guild=True)
    @minecraft.command(aliases=["remove", "-"])
    async def removeserver(
        self, ctx: commands.Context, channel: typing.Optional[discord.TextChannel], server_url: str
    ) -> None:
        """Remove a Minecraft Java server in Config."""
        if channel is None:
            channel = ctx.channel
        servers = await self.config.channel(channel).servers()
        if server_url.lower() not in servers:
            raise commands.UserFeedbackCheckFailure(_("This server isn't in the Config."))
        if isinstance(servers, typing.List):
            servers = {server: None for server in servers}
        del servers[server_url.lower()]
        await self.config.channel(channel).servers.set(servers)
        await ctx.send(_("Server removed from this channel."))

    @commands.admin_or_permissions(manage_guild=True)
    @minecraft.command()
    async def checkplayers(
        self, ctx: commands.Context, channel: typing.Optional[discord.TextChannel], state: bool
    ) -> None:
        """Include players joining or leaving the server in notifications."""
        if channel is None:
            channel = ctx.channel
        await self.config.channel(channel).check_players.set(state)
        if not state:
            for server_url in self.cache[channel.id]:
                self.cache[channel.id][server_url]["status"].raw["players"]["sample"] = {}
            await ctx.send(_("I will not check players for the notifications."))
        else:
            await ctx.send(_("I will check players for the notifications."))

    @commands.admin_or_permissions(manage_guild=True)
    @minecraft.command()
    async def editlastmessage(
        self, ctx: commands.Context, channel: typing.Optional[discord.TextChannel], state: bool
    ) -> None:
        """Edit the last message sent for changes."""
        if channel is None:
            channel = ctx.channel
        await self.config.channel(channel).edit_last_message.set(state)
        if not state:
            await ctx.send(_("I will not edit my last message for the notifications."))
        else:
            await ctx.send(_("I will edit my last message for the notifications."))

    @commands.is_owner()
    @minecraft.command(hidden=True)
    async def forcecheck(self, ctx: commands.Context) -> None:
        """Force check Minecraft Java servers in Config."""
        await self.check_servers()
        await ctx.send(_("Servers checked."))

    @commands.is_owner()
    @commands.bot_has_permissions(embed_links=True)
    @minecraft.command(hidden=True)
    async def getdebugloopsstatus(self, ctx: commands.Context):
        """Get an embed for check loop status."""
        embeds = [loop.get_debug_embed() for loop in self.loops]
        await Menu(pages=embeds).start(ctx)

    @commands.Cog.listener()
    async def on_assistant_cog_add(
        self, assistant_cog: typing.Optional[commands.Cog] = None
    ) -> None:  # Vert's Assistant integration/third party.
        if assistant_cog is None:
            return self.get_minecraft_java_server_for_assistant
        schema = {
            "name": "get_minecraft_java_server_for_assistant",
            "description": "Get informations about a Minecraft Java server.",
            "parameters": {
                "type": "object",
                "properties": {
                    "server_url": {
                        "type": "string",
                        "description": "The URL of the Minecraft Java server.",
                    },
                },
                "required": ["server_url"],
            },
        }
        await assistant_cog.register_function(cog_name=self.qualified_name, schema=schema)

    async def get_minecraft_java_server_for_assistant(self, server_url: str, *args, **kwargs):
        try:
            server: JavaServer = await JavaServer.async_lookup(address=server_url.lower())
            status = await server.async_status()
        except Exception:
            return "No data found for this Minecraft Java server."
        server_description = await self.clear_mcformatting(status.description)
        data = {
            "Host & Port": f"{server.address.host}:{server.address.port}",
            "Description": box(server_description),
            "Status": (
                "Offline."
                if "This server is offline." in server_description
                else (
                    "Currently stopping."
                    if "This server is currently stopping." in server_description
                    else "Online."
                )
            ),
            "Latency": f"{status.latency:.2f} ms",
            "Players": f"{status.players.online}/{status.players.max}",
            "Version": status.version.name,
            "Protocol": status.version.protocol,
        }
        return [f"{key}: {value}\n" for key, value in data.items() if value is not None]

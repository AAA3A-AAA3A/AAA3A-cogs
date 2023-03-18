from .AAA3A_utils import Cog, CogsUtils, Menu, Loop  # isort:skip
from redbot.core import commands, Config  # isort:skip
from redbot.core.bot import Red  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import asyncio
import functools
import os
import pathlib
import random
import re
import subprocess
import tempfile
import time

# from playwright._impl._api_types import TimeoutError as PlaywrightTimeoutError
# from playwright.async_api import async_playwright
from urllib.parse import ParseResult, urljoin, urlparse

import aiohttp
from bs4 import BeautifulSoup, NavigableString, ResultSet, SoupStrainer, Tag

# from aiolimiter import AsyncLimiter
from fuzzywuzzy import fuzz
from sphobjinv import DataObjStr, Inventory

from redbot.core.utils.chat_formatting import humanize_list

from .types import Attribute, Attributes, Documentation, Examples, Parameters, SearchResults

if CogsUtils().is_dpy2:
    setattr(commands, "Literal", typing.Literal)  # To remove
    from .view import GetDocsView

# Credits:
# General repo credits.
# Thanks to amyrinbot on GitHub for a part of the code (https://github.com/amyrinbot/bot/blob/main/modules/util/scraping/documentation/discord_py.py)!
# Thanks to Lemon for the idea of this code (showed me @Lambda bot in the dpy server), for the documentations links, and for many ideas and suggestions!
# Thanks to Danny for fuzzy search function (https://github.com/Rapptz/RoboDanny/blob/rewrite/cogs/utils/fuzzy.py#L325-L350)!

_ = Translator("GetDocs", __file__)

if CogsUtils().is_dpy2:
    from functools import partial

    hybrid_command = partial(commands.hybrid_command, with_app_command=False)
    hybrid_group = partial(commands.hybrid_group, with_app_command=False)
else:
    hybrid_command = commands.command
    hybrid_group = commands.group

CT = typing.TypeVar("CT", bound=typing.Callable[..., typing.Any])  # defined CT as a type variable that is bound to a callable that can take any argument and return any value.


async def run_blocking_func(func: typing.Callable[..., typing.Any], *args: typing.Any, **kwargs: typing.Any) -> typing.Any:
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

BASE_URLS: typing.Dict[str, typing.Dict[str, typing.Any]] = {
    "discord.py": {
        "url": "https://discordpy.readthedocs.io/en/stable/",
        "icon_url": "https://cdn.discordapp.com/attachments/381963689470984203/1068553303908155442/sW87z7N.png",
        "aliases": ["dpy"],
    },
    "redbot": {
        "url": "https://docs.discord.red/en/stable/",
        "icon_url": "https://media.discordapp.net/attachments/133251234164375552/1074432427201663086/a_aab012f3206eb514cac0432182e9e9ec.png",
        "aliases": ["red"],
    },
    "python": {
        "url": "https://docs.python.org/3/",
        "icon_url": "https://assets.stickpng.com/images/5848152fcef1014c0b5e4967.png",
        "aliases": ["py"],
    },
    "aiohttp": {
        "url": "https://docs.aiohttp.org/en/stable/",
        "icon_url": "https://docs.aiohttp.org/en/v3.7.3/_static/aiohttp-icon-128x128.png",
    },
    "requests": {
        "url": "https://requests.readthedocs.io/en/latest/",
        "icon_url": "https://requests.readthedocs.io/en/latest/_static/requests-sidebar.png",
    },
    "slashtags": {
        "url": "https://phen-cogs.readthedocs.io/en/latest/",
        "icon_url": "https://i.imgur.com/dIOX12K.png",
    },
    "discordapi": {  # Special source.
        "url": "https://discord.com/developers/docs/",
        "icon_url": "https://c.clc2l.com/t/d/i/discord-4OXyS2.png",
        "aliases": ["apidiscord"],
    },
    "psutil": {"url": "https://psutil.readthedocs.io/en/latest/", "icon_url": None},
    "pillow": {
        "url": "https://pillow.readthedocs.io/en/stable/",
        "icon_url": "https://pillow.readthedocs.io/en/stable/_static/pillow-logo-dark-text.png",
    },
    "numpy": {
        "url": "https://numpy.org/doc/stable/",
        "icon_url": "https://www.google.com/url?sa=i&url=https%3A%2F%2Frphabet.github.io%2Fposts%2Fpython_numpy_loop%2F&psig=AOvVaw1WvAODE50upYEYKVF68d8s&ust=1676914473120000&source=images&cd=vfe&ved=0CBAQjRxqFwoTCLiMo66Pov0CFQAAAAAdAAAAABAJ",
    },
    "matplotlib": {
        "url": "https://matplotlib.org/stable/",
        "icon_url": "https://matplotlib.org/2.1.2/_static/logo2.png",
    },
    "asyncpg": {"url": "https://magicstack.github.io/asyncpg/current/", "icon_url": None},
    "sqlite": {"url": "https://pysqlite.readthedocs.io/en/latest/", "icon_url": None},
    "websockets": {
        "url": "https://websockets.readthedocs.io/en/latest/",
        "icon_url": "https://repository-images.githubusercontent.com/9113587/aa03b380-afdb-11eb-8e88-2c7542e1670f",
    },
    "mango": {"url": "https://pymongo.readthedocs.io/en/latest/", "icon_url": None},
    "redis": {
        "url": "https://redis-py.readthedocs.io/en/stable/",
        "icon_url": "https://blog.loginradius.com/static/4eda1ce5a0f541d97fdf27cd88bf2a49/03979/index.png",
    },
    "aiomysql": {"url": "https://aiomysql.readthedocs.io/en/stable/", "icon_url": None},
    "flask": {
        "url": "https://flask.palletsprojects.com/",
        "icon_url": "https://flask.palletsprojects.com/en/2.2.x/_images/flask-logo.png",
    },
    "motor": {
        "url": "https://motor.readthedocs.io/en/stable/",
        "icon_url": "https://motor.readthedocs.io/en/stable/_images/motor.png",
    },
    "sphinx": {
        "url": "https://www.sphinx-doc.org/en/master/",
        "icon_url": "https://www.sphinx-doc.org/en/master/_static/sphinxheader.png",
    },
    "starlite": {
        "url": "https://starliteproject.dev/",
        "icon_url": "https://preview.redd.it/2veaqsnz2uf81.png?width=1280&format=png&auto=webp&s=8d7c84d4ec435fc102c14f3f2534ee2c3e5c1cae",
    },
}


class SourceConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> str:
        if argument.lower() not in BASE_URLS:
            found = False
            for name, data in BASE_URLS.items():
                if argument.lower() in data.get("aliases", []):
                    argument = name
                    found = True
            if not found:
                raise commands.BadArgument(_("The source doesn't exist."))
        return argument.lower()


@cog_i18n(_)
class GetDocs(Cog):
    """A cog to get and display Sphinx docs! Use `[p]listsources` to get a list of all the available sources."""

    def __init__(self, bot: Red) -> None:
        self.bot: Red = bot

        self.config: Config = Config.get_conf(
            self,
            identifier=205192943327321000143939875896557571750,
            force_registration=True,
        )
        self.getdocs_global = {
            "disabled_sources": [],
        }
        self.config.register_global(**self.getdocs_global)

        self.documentations: typing.Dict[str, Source] = {}
        self._docs_stats: typing.Dict[str, int] = {"GLOBAL": {"manuals": 0, "documentations": 0}}
        self._load_time: float = None
        self._caching_time: typing.Dict[str, int] = {"GLOBAL": 0}

        # self._playwright = None
        # self._browser = None
        # self._bcontext = None
        self._session: aiohttp.ClientSession = None
        # self._rate_limit = AsyncLimiter(100, 30)

        self.__authors__: typing.List[str] = ["AAA3A", "amyrinbot"]
        self.cogsutils: CogsUtils = CogsUtils(cog=self)

    async def cog_load(self) -> None:
        # self._playwright = await async_playwright().start()
        # self._browser = await self._playwright.chromium.launch()
        # self._bcontext = await self._browser.new_context()
        self._load_time = time.monotonic()
        self._session = aiohttp.ClientSession()
        disabled_sources = await self.config.disabled_sources()
        for source in BASE_URLS:
            if source in disabled_sources:
                continue
            self.documentations[source] = Source(
                self,
                name=source,
                url=BASE_URLS[source]["url"],
                icon_url=BASE_URLS[source]["icon_url"],
            )
            asyncio.create_task(self.documentations[source].load())

    if CogsUtils().is_dpy2:

        async def cog_unload(self) -> None:
            self.cogsutils._end()
            if self._session is not None:
                await self._session.close()

    else:

        def cog_unload(self) -> None:
            self.cogsutils._end()
            if self._session is not None:
                asyncio.create_task(self._session.close())

    @hybrid_command(
        aliases=["getdoc", "docs", "documentations"],
    )
    async def getdocs(
        self,
        ctx: commands.Context,
        source: typing.Optional[SourceConverter] = "discord.py",
        *,
        query: typing.Optional[str] = None,
    ) -> None:
        """
        View rich documentation for a specific node/query.

        The name must be exact, or else rtfm is invoked instead.

        Arguments:
        - `source`: The name of the documentation to use. Defaults to `discord.py`.
        - `query`: The documentation node/query. (`random` to get a random documentation)
        """
        source: Source = self.documentations[source]
        if query is None:
            embed = discord.Embed(description=source.url)
            embed.set_author(
                name=f"{source.name} Documentation",
                icon_url=source.icon_url,
            )
            if self.cogsutils.is_dpy2:
                view = discord.ui.View()
                view.add_item(discord.ui.Button(label="Click to view", url=source.url))
                await ctx.send(embed=embed, view=view)
            else:
                await ctx.send(embed=embed)
            return
        if query == "random":
            if not source._docs_cache:
                raise commands.UserFeedbackCheckFailure(_("Documentations cache is not yet built, building now."))
            choice: Documentation = random.choice(source._docs_cache)
            await ctx.send(embed=choice.to_embed())
            return
        try:
            if self.cogsutils.is_dpy2:
                await GetDocsView(cog=self, query=query, source=source).start(ctx)
            else:
                results = await source.search(query, limit=25, exclude_std=True)
                if not results or not results.results:
                    raise RuntimeError("No results found.")
                doc = None
                i = 0
                doc = source.get_documentation(results.results[0][0])
                while doc is None and i < len(results.results):
                    doc = source.get_documentation(results.results[i][0])
                    if doc is not None:
                        break
                    i += 1
                if doc is None:
                    raise RuntimeError("No results found.")
                embed = doc.to_embed()
                content = None
                if (
                    source._docs_caching_task is not None
                    and source._docs_caching_task.currently_running
                ):
                    content = "⚠️ The documentation cache is not yet fully built, building now."
                await ctx.send(content=content, embed=embed)
        except RuntimeError as e:
            raise commands.UserFeedbackCheckFailure(str(e))

    @hybrid_command()
    async def rtfm(
        self,
        ctx: commands.Context,
        source: typing.Optional[SourceConverter] = "discord.py",
        limit: typing.Optional[int] = 10,
        with_std: typing.Optional[bool] = True,
        *,
        query: typing.Optional[str] = "",
    ) -> None:
        """
        Show all attributes matching your search.

        The name must be exact, or else rtfm is invoked instead.

        Arguments:
        - `source`: The name of the documentation to use. Defaults to `discord.py`.
        - `limit`: The limit of objects to be sent.
        - `with_std`: Also display links to non-API documentation.
        - `query`: Your search. (`events` to get all dpy events, for `discord.py` and `redbot` source only)
        """
        source: Source = self.documentations[source]
        if source.name == "discord.py" and query == "events":
            limit = len([item for item in source._raw_rtfm_cache_without_std if item.startswith("discord.on_")])
            with_std = False
        elif query == "":
            limit = len(source._rtfm_cache.objects)
        try:
            result = await source.search(query, limit=limit, exclude_std=not with_std)
        except RuntimeError as e:
            raise commands.UserFeedbackCheckFailure(str(e))
        if result is None or not result.results:
            raise commands.UserFeedbackCheckFailure(_("No results found."))
        embeds = result.to_embeds()
        if len(embeds) == 1:
            await ctx.send(embed=embeds[0])
        else:
            await Menu(pages=embeds).start(ctx)

    if CogsUtils().is_dpy2:

        async def _cogsutils_add_hybrid_commands(
            self, command: typing.Union[commands.HybridCommand, commands.HybridGroup]
        ) -> None:
            if command.app_command is None:
                return
            if not isinstance(command, commands.HybridCommand):
                return
            if "source" in command.app_command._params:
                command.app_command._params["source"].required = True
                command.app_command._params["source"].default = "discord.py"
                command.app_command._params["source"].choices = [
                    discord.app_commands.Choice(name=source, value=source)
                    for source in list(self.documentations.keys())
                ][:25]
            if "query" in command.app_command._params:
                command.app_command._params["query"].required = True
            _params1 = command.app_command._params.copy()
            _params2 = list(command.app_command._params.keys())
            _params2 = sorted(_params2, key=lambda x: _params1[x].required, reverse=True)
            _params3 = {key: _params1[key] for key in _params2}
            command.app_command._params = _params3

        async def query_autocomplete(
            self, interaction: discord.Interaction, current: str, exclude_std: bool
        ) -> typing.List[discord.app_commands.Choice[str]]:
            source = None
            if "source" in interaction.namespace and interaction.namespace.source:
                try:
                    _source = await SourceConverter().convert(interaction, interaction.namespace.source)
                except commands.BadArgument:
                    pass
                else:
                    source = _source
            source = source or "discord.py"
            source = self.documentations[source]
            if not current:
                return [
                    discord.app_commands.Choice(name=name, value=name)
                    for name in source._raw_rtfm_cache_with_std[:25]
                ]
            matches = await source.search(
                current, limit=25, exclude_std=exclude_std, with_raw_search=True
            )
            return source, [discord.app_commands.Choice(name=name, value=name) for name in matches]

        # @getdocs.autocomplete("query")
        async def getdocs_query_autocomplete(
            self, interaction: discord.Interaction, current: str
        ) -> typing.List[discord.app_commands.Choice[str]]:
            _, result = await self.query_autocomplete(interaction, current, exclude_std=True)
            if not current:
                result.insert(0, discord.app_commands.Choice(name="random", value="random"))
            return result[:25]

        # @rtfm.autocomplete("query")
        async def rtfm_query_autocomplete(
            self, interaction: discord.Interaction, current: str
        ) -> typing.List[discord.app_commands.Choice[str]]:
            exclude_std = False
            if "with_std" in interaction.namespace:
                exclude_std = not interaction.namespace.with_std
            source, result = await self.query_autocomplete(interaction, current, exclude_std=exclude_std)
            if not current and source.name in ["discord.py", "redbot"]:
                result.insert(0, discord.app_commands.Choice(name="events", value="events"))
            return result[:25]

    @hybrid_command(
        name="listsources",
        aliases=["listdocsources", "listrtfmsources", "listsource"]
    )
    async def _sources_list(self, ctx: commands.Context, status: typing.Optional[commands.Literal["available", "all", "disabled"]] = "available") -> None:
        """
        Shows a list of all sources, those that are available or those that are disabled.
        """
        if status == "available":
            keys: str = humanize_list([f"`{key}`" for key in self.documentations.keys()])
        elif status == "all":
            keys: str = humanize_list([f"`{key}`" for key in BASE_URLS.keys()])
        elif status == "disabled":
            keys: str = humanize_list([f"`{key}`" for key in BASE_URLS.keys() if key not in self.documentations.keys()])
        embed = discord.Embed(title="GetDocs Sources", color=discord.Color.green())
        embed.description = keys
        await ctx.send(embed=embed)

    @commands.is_owner()
    @hybrid_group()
    async def setgetdocs(self, ctx: commands.Context) -> None:
        """
        Commands to configure GetDocs.
        """
        pass

    @setgetdocs.command(name="enablesource",)
    async def _source_enable(self, ctx: commands.Context, source: SourceConverter) -> None:
        """
        Enable a documentations source.
        """
        disabled_sources: typing.List[str] = await self.config.disabled_sources()
        if source not in disabled_sources:
            raise commands.UserFeedbackCheckFailure(_("This source is already enabled."))
        disabled_sources.append(source)
        await self.config.disabled_sources.set(disabled_sources)
        self.documentations[source] = Source(
            self,
            name=source,
            url=BASE_URLS[source]["url"],
            icon_url=BASE_URLS[source]["icon_url"],
        )
        asyncio.create_task(self.documentations[source].load())

    @setgetdocs.command(name="disablesource",)
    async def _source_disable(self, ctx: commands.Context, source: SourceConverter) -> None:
        """
        Disable a documentations source.
        """
        disabled_sources: typing.List[str] = await self.config.disabled_sources()
        if source in disabled_sources:
            raise commands.UserFeedbackCheckFailure(_("This source is already disabled."))
        disabled_sources.remove(source)
        await self.config.disabled_sources.set(disabled_sources)


class Source:
    def __init__(self, cog: GetDocs, name: str, url: str, icon_url: typing.Optional[str] = None) -> None:
        self.cog: GetDocs = cog
        self.name: str = name
        self.url: str = url
        self.icon_url: typing.Optional[str] = icon_url

        self._rtfm_cache_url: str = urljoin(url, "objects.inv")
        # self._rtfs_commit: typing.Optional[str] = None

        self._rtfm_caching_task: Loop = None
        self._docs_caching_task: Loop = None
        self._docs_caching_progress: typing.Dict[
            str, typing.Optional[typing.Union[bool, Exception]]
        ] = {}
        # self._rtfs_caching_task = None

        self._rtfm_cache: Inventory = None
        self._raw_rtfm_cache_with_std: typing.List[str] = []
        self._raw_rtfm_cache_without_std: typing.List[str] = []
        self._docs_cache: typing.List[Documentation] = []
        self._result_docs_cache: typing.Dict[str, Documentation] = {}
        # self._rtfs_cache: typing.List = []

    ###################
    # Building caches #
    ###################

    async def load(self) -> None:
        if self.name != "discordapi":
            self._rtfm_caching_task = self.cog.cogsutils.create_loop(
                self._build_rtfm_cache, name=f"{self.name}: Build RTFM Cache", limit_count=1
            )
            while self._rtfm_cache is None or (
                self._rtfm_caching_task is not None and self._rtfm_caching_task.currently_running
            ):
                await asyncio.sleep(1)
        self._docs_caching_task = self.cog.cogsutils.create_loop(
            self._build_docs_cache,
            name=f"{self.name}: Build Documentations Cache",
            limit_count=1,
        )
        # if not self._rtfs_cache:
        #     self._rtfs_caching_task = self.cog.cogsutils.create_loop(self._build_rtfs_cache, name=f"{self.name}: Build RTFS Cache", limit_count=1)

    async def _build_rtfm_cache(self, recache: bool = False) -> Inventory:
        if self._rtfm_cache is not None and not recache:
            return self._rtfm_cache
        self.cog.log.debug(f"{self.name}: Starting RTFM caching...")
        partial = functools.partial(Inventory, url=self._rtfm_cache_url)
        loop = asyncio.get_running_loop()
        self._rtfm_cache = await loop.run_in_executor(None, partial)
        for item in self._rtfm_cache.objects:
            self._raw_rtfm_cache_with_std.append(item.name)
            if item.domain != "std":
                self._raw_rtfm_cache_without_std.append(item.name)
        self.cog.log.debug(f"{self.name}: RTFM cache built.")
        return self._rtfm_cache

    async def _build_docs_cache(
        self, recache: bool = False
    ) -> typing.Dict[str, typing.List[Documentation]]:
        if self._docs_cache and not recache:
            return self._docs_cache
        self._docs_cache = []
        self._result_docs_cache = {}
        self.cog.log.debug(f"{self.name}: Starting Documentations caching...")
        start = time.monotonic()
        self.cog._docs_stats[self.name] = {"manuals": 0, "documentations": 0}

        manuals = []
        if self.name != "discordapi":
            _manuals = {
                obj.uri.split("#")[0]
                for obj in self._rtfm_cache.objects
                if obj.domain != "std"
            }
            for manual in _manuals:
                if manual.endswith("#$"):
                    manual = manual[:-2]
                manuals.append((manual, self.url + manual))
            if self.name == "python":
                for i, manual in enumerate(["library/stdtypes.html", "library/functions.html"]):  # important documentations
                    manuals.remove((manual, self.url + manual))
                    manuals.insert(i, (manual, self.url + manual))
                manual = "tutorial/datastructures.html"  # not found by RTFM caching task
                manuals.insert(i + 1, (manual, self.url + manual))
            for name, manual in manuals:
                try:
                    documentations = await self._get_all_manual_documentations(manual)
                    for documentation in documentations:
                        self.cog._docs_stats[self.name]["documentations"] += 1
                        self.cog._docs_stats["GLOBAL"]["documentations"] += 1
                        self._docs_cache.append(documentation)
                    self.cog._docs_stats[self.name]["manuals"] += 1
                    self.cog._docs_stats["GLOBAL"]["manuals"] += 1
                    if self.cog.cogsutils.is_dpy2:
                        self.cog.log.trace(
                            f"{self.name}: `{name}` documentation added to documentation cache."
                        )
                except Exception as e:
                    self.cog.log.debug(
                        f"{self.name}: Error occured while trying to cache `{name}` documentation.",
                        exc_info=e,
                    )
                    self._docs_caching_progress[name] = e
        else:
            _rtfm_cache = Inventory()
            _rtfm_cache.project = self.name
            _rtfm_cache.version = "1.0"
            with tempfile.TemporaryDirectory() as directory:
                # Clone GitHub repo.
                repo_url = "https://github.com/discord/discord-api-docs.git"
                loop = asyncio.get_running_loop()
                partial = functools.partial(subprocess.run, ["git", "clone", repo_url, directory], capture_output=True)
                result = await loop.run_in_executor(None, partial)
                if result.returncode != 0:
                    self.cog.log.error(f"{self.name}: Error occured while trying to clone Discord API Docs's GitHub repo.")
                    return []
                # Iter files.
                for subdir, _, files in os.walk(f"{directory}\\docs"):
                    if subdir.endswith(("docs", "dispatch", "game_and_server_management", "game_sdk", "policies_and_agreements", "rich_presence", "tutorials")):
                        continue
                    for file in files:
                        if not file.endswith(".md"):
                            continue
                        try:
                            filepath = pathlib.Path(os.path.join(subdir, file))
                            _subdir = f"{filepath.parents[0].name}".replace(" ", "_")
                            _file = filepath.name[:-3].lower().replace("_", "-").replace(" ", "-")
                            name = f"{_subdir}/{file}"
                            with open(filepath, "rt") as f:
                                content: str = f.read()[2:]
                            manuals.append(name)
                            # Find documentations.
                            _documentations: typing.List[str] = []
                            _current = None
                            for line in content.split("\n"):
                                if (line.startswith("### ") or line.startswith("## ")) and not line.startswith(("### Guild Scheduled Event ", "### An ", "### Any ")):
                                    if _current is not None:
                                        _documentations.append(_current.strip("### ").strip("## "))
                                    _current = line
                                if _current is not None:
                                    _current += f"\n{line}"
                            documentations = []
                            # Iter documentations.
                            for _documentation in _documentations:
                                if not _documentation:
                                    continue
                                # Get name and full_name.
                                _name = _documentation.split("\n")[0]
                                _documentation = "\n".join(_documentation.split("\n")[1:])
                                if _documentation.startswith(f"## {_name}") or _documentation.startswith(f"### {_name}"):
                                    _documentation = "\n".join(_documentation.split("\n")[1:])
                                if len(_name.split(" % ")) == 2:
                                    full_name = _name.split(" % ")[1]
                                    _name = _name.split(" % ")[0]
                                    for _match in re.compile(r"{.*?#DOCS_(.*?)}").findall(full_name):
                                        full_name = full_name.replace(f"#DOCS_{_match}", "")
                                else:
                                    full_name = ""
                                description = _documentation.split("###### ")[0]
                                if not description:
                                    continue
                                # Get fields.
                                fields = {field.split("\n")[0]: "\n".join(field.split("\n")[1:]) for field in _documentation.split("###### ")[1:]}
                                examples = Examples()
                                for field in fields.copy():
                                    if "Example" in field:
                                        examples.append(fields[field])
                                        del fields[field]
                                    elif "-----" in fields[field]:  # Format tables.
                                        value = ""
                                        for row in fields[field].split("\n"):
                                            if not row or not row.startswith("|") or row == "|" or "-----" in row:  # not row.startswith("|")
                                                continue
                                            row = row.split("|")
                                            if value != "":
                                                value += f"\n{'• ' if value else ''}{' | '.join([_row for _row in row if _row != ''])}"
                                            else:
                                                value += f"**{' | '.join([_row for _row in row if _row != ''])}**"
                                        fields[field] = value
                                if full_name:  # Create a custom example for each endpoint.
                                    _method = full_name.split(" ")[0]
                                    _path = full_name.split(" ")[1]
                                    example = "from discord.http import Route"
                                    _kwargs = re.compile(r"{(.*?)}").findall(_path)
                                    if _kwargs:
                                        example += "\nkwargs = {"
                                        for _kwarg in _kwargs:
                                            _kwarg_raw = "\n    "
                                            _kwarg_raw += f'"{_kwarg.replace(".", "_")}": '
                                            _kwarg_raw += f'"{_kwarg.split(".")[0].upper()}_ID",  # snowflake' if _kwarg.split(".")[-1] == "id" and _kwarg.split(".")[-2] in ["user", "member", "guild", "channel", "role", "message", "application"] else '"",'
                                            example += _kwarg_raw
                                            _path = _path.replace("{" + _kwarg + "}", "{" + _kwarg.replace(".", "_") + "}")
                                        example += "\n}"
                                        example += f'\nroute = Route(method="{_method}", path="{_path}", **kwargs)'
                                    else:
                                        example += f'\nroute = Route(method="{_method}", path="{_path}")'
                                    _kwargs = ""
                                    for key, value in {"Query String Params": "params", "JSON Params": "json", "JSON/Form Params": "json"}.items():
                                        if key in fields:
                                            example += f"\n_{value}" + "= {"
                                            for _param in fields[key].split("\n"):
                                                if not _param.startswith("• "):
                                                    continue
                                                _param = _param.split(" | ")
                                                if not len(_param) > 2 or not len(_param[0]) > 3:
                                                    continue
                                                _param_raw = "\n    "
                                                if _param[0][2:].strip().endswith("?"):
                                                    _param_raw += f'# ? "{_param[0][2:].strip()[:-1]}": '
                                                elif _param[0][2:].strip().endswith("?\\*"):
                                                    _param_raw += f'# ?\\* "{_param[0][2:].strip()[:-3]}": '
                                                else:
                                                    _param_raw += f'"{_param[0][2:].strip()}": '
                                                _param_raw += "1" if _param[1].strip() in ["integer", "snowflake"] else ('"true"' if _param[1].strip() == "boolean" else ('""' if _param[1].strip() == "string" else "MISSING"))
                                                _param_raw += f",  # {_param[1].strip()[1:] if _param[1].strip().endswith('?') else _param[1].strip()}"
                                                example += _param_raw
                                            example += "\n}"
                                            _kwargs += f", {value}=_{value}"
                                    example += f"\nreturn await ctx.bot.http.request(route=route{_kwargs})"
                                    examples.insert(0, example)
                                # Add to RTFM cache.
                                _object = DataObjStr(
                                    name=_name,
                                    domain="py",
                                    role="endpoint" if full_name else _subdir,
                                    priority="1",
                                    uri=f"{self.url}{_subdir}/{_file}#{_name.lower().replace('_', '-').replace(' ', '-')}",
                                    dispname="-",
                                )
                                setattr(_object, "fake", True)
                                _rtfm_cache.objects.append(_object)
                                self._raw_rtfm_cache_with_std.append(_object.name)
                                if _object.domain != "std":
                                    self._raw_rtfm_cache_without_std.append(_object.name)
                                # Add to Documentations cache.
                                documentation = Documentation(
                                    self,
                                    name=_name,
                                    url=f"{self.url}{_subdir}/{_file}#{_name.lower().replace('_', '-').replace(' ', '-')}",
                                    full_name=full_name,
                                    description=description,
                                    parameters=None,
                                    examples=examples,
                                    fields=fields,
                                    attributes=Attributes(attributes={}, properties={}, methods={}),
                                )
                                self.cog._docs_stats[self.name]["documentations"] += 1
                                self.cog._docs_stats["GLOBAL"]["documentations"] += 1
                                self._docs_cache.append(documentation)
                            self.cog._docs_stats[self.name]["manuals"] += 1
                            self.cog._docs_stats["GLOBAL"]["manuals"] += 1
                            if self.cog.cogsutils.is_dpy2:
                                self.cog.log.trace(
                                    f"{self.name}: `{name}` documentation added to documentation cache."
                                )
                        except Exception as e:
                            self.cog.log.debug(
                                f"{self.name}: Error occured while trying to cache `{name}` documentation.",
                                exc_info=e,
                            )
                            self._docs_caching_progress[name] = e
            self._rtfm_cache = _rtfm_cache
        amount = len(self._docs_cache)
        end = time.monotonic()
        duration = int(end - start)
        self.cog._caching_time[self.name] = duration
        total_duration = end - self.cog._load_time
        if total_duration > self.cog._caching_time["GLOBAL"]:
            self.cog._caching_time["GLOBAL"] = total_duration
        self.cog.log.debug(
            f"{self.name}: Successfully cached {amount} Documentations/{len(manuals)} manuals."
        )
        return self._docs_cache

    async def _get_html(self, url: str, timeout: int = 0) -> str:
        # async with self.cog._rate_limit:
        async with self.cog._session.get(url, timeout=timeout) as r:
            content = await r.text(encoding="utf-8")
        return content

    def _get_text(self, element: Tag, parsed_url: ParseResult, template: str = "[`{}`]({})") -> str:
        if not hasattr(element, "contents"):
            element.contents = [element]

        def parse_element(elem: Tag, only: typing.Optional[str] = None):
            def is_valid(elem, name):
                if only is not None and elem.name == only and elem.name == name:
                    return True
                elif only is None and elem.name == name:
                    return True
                return False

            if is_valid(elem, "a"):
                tag_name = elem.text
                tag_href = elem["href"]
                if parsed_url:
                    parsed_href = urlparse(tag_href)
                    if not parsed_href.netloc:
                        raw_url = parsed_url._replace(params="", fragment="").geturl()
                        tag_href = urljoin(raw_url, tag_href)
                return template.format(tag_name, tag_href)
            if is_valid(elem, "strong"):
                return f"**{elem.text}**"
            if is_valid(elem, "code"):
                return f"`{elem.text}`"

        if isinstance(element, Tag):
            result = parse_element(element)
            if result is not None:
                return result
        text = []
        for element in element.contents:
            text.append(element.text)
        return " ".join(text)

    @executor()
    def _get_documentation(self, element: Tag, page_url: str) -> Documentation:
        full_name = element.text
        full_name = full_name.strip().replace("¶", "").replace("", "").replace("\n", "")
        if full_name.endswith("[source]"):
            full_name = full_name[:-8]
        elif full_name.endswith("[source]#"):
            full_name = full_name[:-9]
        if self.name == "python" and page_url == self.url + "tutorial/datastructures.html":
            name = full_name.strip("\n").split("(")[0]
            if discord.utils.get(self._rtfm_cache.objects, name=name) is None:
                _object = DataObjStr(
                    name=name,
                    domain="py",
                    role="method",
                    priority="1",
                    uri=page_url[len(self.url):] + "#$",
                    dispname="-",
                )
                setattr(_object, "fake", True)
                self._rtfm_cache.objects.append(_object)
                self._raw_rtfm_cache_with_std.append(_object.name)
                if _object.domain != "std":
                    self._raw_rtfm_cache_without_std.append(_object.name)
            _url = f"#{name}"
        else:
            name = element.attrs.get("id")
            try:
                _url = element.find("a", class_="headerlink").get("href", None)
            except AttributeError:
                return
        full_url = urljoin(page_url, _url)
        parsed_url = urlparse(full_url)
        url = parsed_url.geturl()
        parent = element.parent
        documentation = parent.find("dd")

        def parse_method_role(_name: str):
            if _name.startswith("async with "):
                _name = _name[11:]
                _role = "async with"
            elif _name.startswith("coroutine async-with "):  # aiohttp
                _name = _name[21:]
                _role = "async with"
            elif _name.startswith("async for ... in "):
                _name = _name[17:]
                _role = "async for ... in"
            elif _name.startswith("coroutine async-for "):  # aiohttp
                _name = _name[21:]
                _role = "async for ... in"
            elif _name.startswith("await "):
                _name = _name[6:]
                _role = "await"
            elif _name.startswith("coroutine "):  # aiohttp
                _name = _name[10:]
                _role = "await"
            elif name.startswith("classmethod "):
                _name = _name[12:]
                _role = "classmethod"
            else:
                _role = None
            return _role, _name
        _full_name = parse_method_role(full_name)
        full_name = (f"{_full_name[0]} " if _full_name[0] is not None else "") + _full_name[1]

        # Description
        description = []
        for child in documentation.children:
            child: Tag = child
            if child.name == "div":
                break
            if isinstance(child, NavigableString):
                continue
            if child.attrs.get("class") is not None and not (
                child.name == "ul" and child.attrs.get("class") == ["simple"]
            ):
                break
            if child.name == "p":
                elements = []
                for element in child.contents:
                    text = self._get_text(element, parsed_url)
                    elements.append(text)
                description.append("".join(elements))
            elif child.name == "ul" and child.attrs.get("class") == ["simple"]:
                _elements = []
                for _child in child.find_all("p"):
                    elements = []
                    for element in _child.contents:
                        text = self._get_text(element, parsed_url)
                        elements.append(text)
                    _elements.append("• " + "".join(elements))
                try:
                    x = description[-1]
                    del description[-1]
                except IndexError:
                    x = ""
                description.append(f"{x}\n" + "\n".join(_elements))
        description = "\n\n".join(description).replace("Example:", "").strip()

        # Examples
        examples = Examples()
        for child in documentation.find_all(
            "div", class_=["highlight-python3", "highlight-default", "highlight"], recursive=False
        ):
            examples.append(child.find("pre").text)

        # Fields
        fields = {}
        if supported_operations := documentation.find("div", class_="operations", recursive=False):
            items: typing.List[typing.Set] = []  # typing.List[set[str, str]]
            for supported_operation in supported_operations.findChildren("dl", class_="describe"):
                operation = supported_operation.find("span", class_="descname").text.strip()
                desc = (
                    self._get_text(supported_operation.find("dd", recursive=False), parsed_url)
                    .strip()
                    .split("\n")[0]
                )
                items.append((operation, desc))
            if items:
                fields["Supported Operations"] = "\n".join(
                    f"> {operation}\n{desc}" for operation, desc in items
                )
        field_list = documentation.find("dl", class_="field-list", recursive=False)
        if field_list:
            for field in field_list.findChildren("dt"):
                field: Tag = field
                if "class" not in field.attrs:
                    continue
                key = field.text
                values: typing.List[Tag] = [x for x in field.next_siblings if isinstance(x, Tag)][
                    0
                ].find_all("p")
                elements: typing.List[typing.List[str]] = []
                for value in values:
                    texts: typing.List[str] = []
                    for element in value.contents:
                        text = self._get_text(element, parsed_url)
                        texts.append(text.replace("\n", " "))
                    if key == "Raises" and not texts[0].startswith(("[", "**")):
                        elements[-1].extend(texts)
                        continue
                    elements.append(texts)
                fields[key] = "\n".join(
                    (
                        "• "
                        if (key == "Parameters" and element[0].startswith("**")) or key == "Raises"
                        else ""
                    )
                    + "".join(element)
                    for element in elements
                )

        # Parameters
        parameters = Parameters()
        if "Parameters" in fields:
            _parameters: str = fields.pop("Parameters")
            _parameters = _parameters.strip("• ").split("\n• ")
            for _parameter in _parameters:
                if len(_parameter.split(" – ")) > 1:
                    key = _parameter.split(" – ")[0]
                    value = "".join(_parameter.split(" – ")[1:]).strip()
                else:
                    key = _parameter.split(": ")[0]
                    value = "".join(_parameter.split(": ")[1:]).strip()
                parameters[key] = value

        # Versions changes
        versions_changes = []
        children = documentation.children
        for child in children:
            child: Tag = child
            if isinstance(child, NavigableString):
                continue
            if child.attrs.get("class") is not None and child.attrs.get("class") == [
                "sig",
                "sig-object",
            ]:
                break
            if child.name == "div" and (
                child.attrs.get("class") == ["versionchanged"]
                or child.attrs.get("class") == ["versionadded"]
            ):
                _child = child.find("p")
                elements = []
                for element in _child.contents:
                    text = self._get_text(element, parsed_url)
                    try:
                        if text[0] == "\n":
                            text = " " + text[1:]
                    except IndexError:
                        pass
                    if text == "":
                        continue
                    elements.append(text)
                text = "".join(elements)
                if text == "":
                    continue
                try:
                    if len(text.strip().split(": ")) == 1:
                        raise IndexError()
                    version = text.strip().split(": ")[0]
                    change = " ".join(text.strip().split(": ")[1:])
                except IndexError:
                    versions_changes.append(f"*{text}*")
                    continue
                versions_changes.append(f"• *{version}*: *{change}*".replace("\n", " "))
        if versions_changes:
            versions_changes = "\n".join(versions_changes)
            fields["Versions Changes"] = versions_changes

        # Attributes
        def format_attributes(items: Tag) -> typing.List[Attribute]:
            results: typing.Dict[str, typing.Dict[str, str]] = {}
            for item in items:
                infos = " ".join(x.text for x in item.contents).strip().split("\n")
                name = infos[0].replace("¶", "").strip().split("(")[0]
                if item.attrs.get("class") == ["py", "property"]:
                    name = name[8:]
                    role = None
                elif item.attrs.get("class") == ["py", "method"]:
                    role, name = parse_method_role(name)
                else:
                    role = None
                if (
                    item.attrs.get("class") == ["py", "attribute"]
                    or item.attrs.get("class") == ["py", "property"]
                ) and len(infos) > 1:
                    description = [x.strip() for x in infos][1]
                else:
                    description = None
                if item.find("a", class_="headerlink") is not None:
                    href = item.find("a", class_="headerlink").get("href")
                else:
                    href = ""
                url = urljoin(full_url, href)
                results[name] = Attribute(name=name, role=role, url=url, description=description)
            return results
        attributes: typing.Dict[str, typing.List[Attribute]] = {}
        attribute_list = documentation.find_all("dl", class_="py attribute")
        if attribute_list:
            attributes["attributes"] = format_attributes(attribute_list)
        else:
            attributes["attributes"] = {}
        property_list = documentation.find_all("dl", class_="py property")
        if property_list:
            attributes["properties"] = format_attributes(property_list)
        else:
            attributes["properties"] = {}
        methods_list = documentation.find_all("dl", class_="py method")
        if methods_list:
            attributes["methods"] = format_attributes(methods_list)
        else:
            attributes["methods"] = {}
        attributes = Attributes(**attributes)

        return Documentation(
            self,
            name=name,
            url=url,
            full_name=full_name,
            description=description,
            parameters=parameters,
            examples=examples,
            fields=fields,
            attributes=attributes,
        )

    async def _get_all_manual_documentations(self, page_url: str) -> typing.List[Documentation]:
        @executor()
        def bs4(content: str):
            strainer = SoupStrainer("dl")
            soup = BeautifulSoup(content, "lxml", parse_only=strainer)
            if self._rtfm_cache is not None and (
                self._rtfm_caching_task is None or not self._rtfm_caching_task.currently_running
            ):
                e1 = soup.find_all("dt", id=[x.name for x in self._rtfm_cache.objects])
            else:
                e1 = ResultSet(strainer)
            e2 = soup.find_all("dt", class_="sig sig-object py")
            return ResultSet(strainer, set(e1 + e2))

        elements = await bs4(await self._get_html(page_url))
        results: typing.List[Documentation] = []
        for element in elements:
            result = await self._get_documentation(element, page_url)
            if result is not None:
                results.append(result)
        # Add attributes for Python stdtypes.
        if self.name == "python" and page_url[len(self.url):] in ["library/stdtypes.html", "tutorial/datastructures.html"]:
            for documentation in results:
                if len(documentation.name.split(".")) > 1:
                    parent_name = ".".join(documentation.name.split(".")[:-1])
                    parent = discord.utils.get(results, name=parent_name) or discord.utils.get(self._docs_cache, name=parent_name)
                    if parent is not None:
                        parent.attributes.methods[documentation.name[len(parent_name) + 1:]] = Attribute(name=documentation.name[(len(parent_name) + 1) * 2:], role="", url=documentation.url, description=documentation.description.split("\n")[0])
        return results

    #######################
    # Get a documentation #
    #######################

    async def search(
        self,
        query: str,
        limit: typing.Optional[int] = None,
        exclude_std: bool = False,
        with_raw_search: bool = False,
    ) -> SearchResults:
        if self._rtfm_cache is None or (
            self._rtfm_caching_task is not None and self._rtfm_caching_task.currently_running
        ):
            raise RuntimeError(_("RTFM caching isn't finished."))
        start = time.monotonic()

        def fuzzy_search(text: str, collection: typing.Iterable[typing.Union[str, typing.Any]], key: typing.Optional[typing.Callable] = None) -> typing.List[typing.Union[str, typing.Any]]:
            if self.name != "python":
                matches = []
                pat = '.*?'.join(map(re.escape, text))
                regex = re.compile(pat, flags=re.IGNORECASE)
                def _key(item: typing.Union[str, typing.Any]) -> str:
                    item_name = key(item) if key is not None else item
                    if self.name == "discord.py" and item_name.startswith("discord.ext.commands."):
                        item_name = item_name[21:]
                    elif self.name == "discord.py" and item_name.startswith("discord."):
                        item_name = item_name[8:]
                    return item_name
                for item in collection:
                    item_name = key(item) if key is not None else item
                    if self.name == "discord.py" and item_name.startswith("discord.ext.commands."):
                        item_name = item_name[21:]
                    elif self.name == "discord.py" and item_name.startswith("discord."):
                        item_name = item_name[8:]
                    r = regex.search(item_name)
                    if r:
                        matches.append((len(r.group()), r.start(), item))
                def sort_key(tup: typing.Tuple[int, int, typing.Union[str, typing.Any]]) -> typing.Tuple[int, int, str]:
                    return tup[0], tup[1], _key(tup[2])
                matches = [item for _, _, item in sorted(matches, key=sort_key)]
            else:
                matches = sorted(
                    collection,
                    key=lambda x: fuzz.ratio(text, key(x)),
                    reverse=True,
                )
            return matches

        if len(query.split(".")) == 1:
            if self.name == "discord.py":
                for name in dir(discord.abc.Messageable):
                    if name.startswith("_"):
                        continue
                    if query.lower() == name:
                        query = f"discord.abc.Messageable.{name.lower()}"
                        break
                query = re.sub(r"^(?:discord\.(?:ext\.)?)?(?:commands\.)?(.+)", r"\1", query)
            elif self.name == "aiohttp":
                for name in dir(aiohttp.ClientSession):
                    if name.startswith("_"):
                        continue
                    if query.lower() == name:
                        query = f"aiohttp.ClientSession.{name.lower()}"
                        break
        if with_raw_search:
            if exclude_std:
                matches = fuzzy_search(text=query, collection=self._raw_rtfm_cache_without_std)
            else:
                matches = fuzzy_search(text=query, collection=self._raw_rtfm_cache_with_std)
            return matches[:limit]

        def get_name(obj: DataObjStr) -> str:
            name = obj.name or (obj.dispname if obj.dispname not in ["-", None] else None)
            original_name = name
            if obj.domain == "std" or self.name == "discordapi":
                name = f"{obj.role}: {name}"
            if self.name == "discord.py":
                if name.startswith("discord.ext.commands."):
                    name = name[21:]
                elif name.startswith("discord."):
                    name = name[8:]
            return name, original_name or name

        def build_uri(obj: DataObjStr) -> str:
            location = obj.uri
            if location.endswith("$"):
                location = location[:-1] + obj.name
            return urljoin(self.url, location)

        if self.name in ["discord.py", "redbot"] and query == "events":
            matches = [item for item in self._rtfm_cache.objects if item.name.split(".")[-1].startswith("on_")]
        else:
            matches = fuzzy_search(text=query, collection=self._rtfm_cache.objects, key=lambda item: item.name)
        results = [
            (*get_name(item), build_uri(item), item.domain == "std") for item in matches
        ]
        results = [result for result in results if not result[2].startswith("c-api/")]
        if exclude_std:
            results = [result for result in results if not result[3]]
        end = time.monotonic()
        return SearchResults(self, results=results[:limit], query_time=int(end - start))

    def get_documentation(self, name: str) -> Documentation:
        # if self._docs_caching_task is not None and self._docs_caching_task.currently_running:
        #     raise RuntimeError(_("Documentations cache is not yet built, building now."))
        if self.name == "discord.py" and not self.name.startswith("discord."):
            if f"discord.{name}" in self._raw_rtfm_cache_without_std:
                name = f"discord.{name}"
            else:
                name = f"discord.ext.commands.{name}"
        return discord.utils.get(self._docs_cache, name=name)

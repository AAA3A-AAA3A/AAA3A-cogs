from types import TracebackType
from .AAA3A_utils import CogsUtils, Menu  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
from redbot.core.bot import Red  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import asyncio
import functools
import random
import time

# from playwright._impl._api_types import TimeoutError as PlaywrightTimeoutError
# from playwright.async_api import async_playwright
from urllib.parse import ParseResult, urljoin, urlparse

import aiohttp
from bs4 import BeautifulSoup, NavigableString, ResultSet, SoupStrainer, Tag

# from aiolimiter import AsyncLimiter
from fuzzywuzzy import fuzz
from sphobjinv import DataObjStr, Inventory

from .types import Attribute, Attributes, Documentation, Examples, Parameters, SearchResults

if CogsUtils().is_dpy2:
    from .view import DocsView

# Credits:
# General repo credits.
# Thanks to amyrinbot on GitHub for a part of the code (https://github.com/amyrinbot/bot/blob/main/modules/util/scraping/documentation/discord_py.py)!
# Thanks to @Lemon for the idea of this code (showed me @Lambda bot in the dpy server, and gave me many ideas and documentations links)!

_ = Translator("GetDocs", __file__)

if CogsUtils().is_dpy2:
    from functools import partial

    hybrid_command = partial(commands.hybrid_command, with_app_command=False)
    hybrid_group = partial(commands.hybrid_group, with_app_command=False)
else:
    hybrid_command = commands.command
    hybrid_group = commands.group
    
CT = typing.TypeVar("CT", bound=typing.Callable[..., typing.Any]) # defined CT as a type variable that is bound to a callable that can take any argument and return any value.

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


class SourceConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> str:
        if argument.lower() not in BASE_URLS:
            found = False
            for name, data in BASE_URLS.items():
                if argument.lower() in data.get("aliases", []):
                    argument = name
                    found = True
            if not found:
                raise commands.UserFeedbackCheckFailure(_("The source doesn't exist."))
        return argument.lower()


@cog_i18n(_)
class GetDocs(commands.Cog):
    """A cog to get and display Sphinx docs! Use `[p]listsources` to get a list of all the available sources."""

    def __init__(self, bot: Red) -> None:
        self.bot: Red = bot

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
        for source in BASE_URLS:
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
        """View rich documentation for a specific node/query.

        The name must be exact, or else rtfm is invoked instead.

        Arguments:
        - `source`: The name of the documentation to use. Defaults to `discord.py`.
        - `query`: The documentation node/query. (`random` to get a random documentation)
        """
        source = self.documentations[source]
        if query is None:
            embed = discord.Embed(description=source.url)
            embed.set_author(
                name=f"{source.name} Documentation",
                icon_url=source.icon_url,
            )
            if self.cogsutils.is_dpy2:
                view = discord.ui.View()
                view.add_item(discord.ui.Button(label="Click to view", url=source.url))
                await ctx.send(embed=embed)
            else:
                await ctx.send(embed=embed)
            return
        if query == "random":
            choice: Documentation = random.choice(source._docs_cache)
            await ctx.send(embed=choice.to_embed())
            return
        try:
            if self.cogsutils.is_dpy2:
                await DocsView(ctx, query=query, source=source).start()
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
        query: typing.Optional[str] = None,
    ) -> None:
        """Show all attributes matching your search.

        The name must be exact, or else rtfm is invoked instead.

        Arguments:
        - `source`: The name of the documentation to use. Defaults to `discord.py`.
        - `limit`: The limit of objects to be sent.
        - `with_std`: Also display links to non-API documentation.
        - `query`: Your search.
        """
        source = self.documentations[source]
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
                ]
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
            if "source" in interaction.namespace:
                if interaction.namespace.source:
                    try:
                        await SourceConverter().convert(interaction, interaction.namespace.source)
                    except commands.BadArgument:
                        pass
                    else:
                        source = interaction.namespace.source
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
            return [discord.app_commands.Choice(name=name, value=name) for name in matches]

        # @getdocs.autocomplete("query")
        async def getdocs_query_autocomplete(
            self, interaction: discord.Interaction, current: str
        ) -> typing.List[discord.app_commands.Choice[str]]:
            return await self.query_autocomplete(interaction, current, exclude_std=True)

        # @rtfm.autocomplete("query")
        async def rtfm_query_autocomplete(
            self, interaction: discord.Interaction, current: str
        ) -> typing.List[discord.app_commands.Choice[str]]:
            exclude_std = False
            if "with_std" in interaction.namespace:
                exclude_std = not interaction.namespace.with_std
            return await self.query_autocomplete(interaction, current, exclude_std=exclude_std)
        
    @hybrid_command(
        name="listsources", 
        aliases=["listdocsources", "listrtfmsources", "listsource"]
    )
    async def _source_list(self, ctx: commands.Context) -> None:
        """
        Shows a list of all the possible sources.
        """
        keys: str = ", ".join(
            [f"`{key}`" for key in self.documentations.keys()]
        )
        embed = discord.Embed(color=await ctx.embed_color())
        embed.title = "Sources"
        embed.description = keys
        await ctx.send(embed=embed)


class Source:
    def __init__(self, cog: GetDocs, name: str, url: str, icon_url: typing.Optional[str] = None) -> None:
        self.cog: GetDocs = cog
        self.name: str = name
        self.url: str = url
        self.icon_url: typing.Optional[str] = icon_url

        self._rtfm_cache_url: str = urljoin(url, "objects.inv")
        # self._rtfs_commit: typing.Optional[str] = None

        self._rtfm_caching_task = None
        self._docs_caching_task = None
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
        
    async def __aenter__(self) -> "Source":
        return self
    
    async def __aexit__(
        self,
        exc_type: typing.Optional[type],
        exc: typing.Optional[Exception],
        traceback: typing.Optional[TracebackType],
    ) -> typing.Literal[False]:
        return False

    ###################
    # Building caches #
    ###################

    async def load(self) -> None:
        self._rtfm_caching_task = self.cog.cogsutils.create_loop(
            self._build_rtfm_cache, name=f"{self.name}: Build RTFM Cache", limit_count=1
        )
        while self._rtfm_cache is None or (
            self._rtfm_caching_task is not None and self._rtfm_caching_task.currently_running
        ):
            await asyncio.sleep(1)
        if not self._docs_cache:
            self._docs_caching_task = self.cog.cogsutils.create_loop(
                self._build_docs_cache,
                name=f"{self.name}: Build Documentations Cache",
                limit_count=1,
            )
        # if not self._rtfs_cache:
        # self._rtfs_caching_task = self.cog.cogsutils.create_loop(self._build_rtfs_cache, name=f"{self.name}: Build RTFS Cache", limit_count=1)

    async def _build_rtfm_cache(self, recache: bool = False) -> Inventory:
        if self._rtfm_cache is not None and not recache:
            return self._rtfm_cache
        self.cog.log.debug(f"{self.name}: Starting RTFM caching...")
        partial = functools.partial(Inventory, url=self._rtfm_cache_url)
        loop = asyncio.get_running_loop()
        self._rtfm_cache = await loop.run_in_executor(None, partial)
        for item in self._rtfm_cache.objects:
            self._raw_rtfm_cache_with_std.append(item.name)
        for item in self._rtfm_cache.objects:
            if not item.domain == "std":
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

        _manuals = set(
            [obj.uri.split("#")[0] for obj in self._rtfm_cache.objects if obj.domain != "std"]
        )
        manuals = []
        for manual in _manuals:
            if manual.endswith("#$"):
                manual = manual[:-2]
            manuals.append((manual, self.url + manual))
        if self.name == "python":
            manual = "tutorial/datastructures.html"
            manuals.insert(0, (manual, self.url + manual))

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
        full_name = full_name.replace("¶", "").strip()
        if full_name.endswith("[source]"):
            full_name = full_name[:-8]
        if self.name == "discord.py" and page_url == self.url + "tutorial/datastructures.html":
            name = full_name.strip("\n").split("(")[0]
            if discord.utils.get(self._rtfm_cache.objects, name=name) is None:
                _object = DataObjStr(
                    name=name,
                    domain="py",
                    role="method",
                    priority="1",
                    uri=page_url[len(self.url) :] + "#$",
                    dispname="-",
                )
                setattr(_object, "fake", True)
                self._rtfm_cache.objects.append(_object)
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
                    texts = []
                    for element in value.contents:
                        text = self._get_text(element, parsed_url)
                        texts.append(text.replace("\n", " "))
                    elements.append(texts)
                fields[key] = "\n".join(
                    (
                        "• "
                        if key in ["Parameters", "Raises"] and element[0].startswith("**")
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
                versions_changes.append(f"• *{version}*: *{change}*")
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
                    if name.startswith("async with "):
                        name = name[11:]
                        role = "async with"
                    elif name.startswith("async for ... in "):
                        name = name[17:]
                        role = "async for ... in"
                    elif name.startswith("await "):
                        name = name[6:]
                        role = "await"
                    elif name.startswith("coroutine "):  # aiohttp
                        name = name[10:]
                        role = "await"
                    elif name.startswith("classmethod "):  # aiohttp
                        name = name[12:]
                        role = "classmethod"
                    else:
                        role = None
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
            attributes["attributes"] = []
        property_list = documentation.find_all("dl", class_="py property")
        if property_list:
            attributes["properties"] = format_attributes(property_list)
        else:
            attributes["properties"] = []
        methods_list = documentation.find_all("dl", class_="py method")
        if methods_list:
            attributes["methods"] = format_attributes(methods_list)
        else:
            attributes["methods"] = []
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

    async def _get_all_manual_documentations(self, url: str) -> typing.List[Documentation]:
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

        elements = await bs4(await self._get_html(url))
        results = []
        for element in elements:
            result = await self._get_documentation(element, url)
            if result is not None:
                results.append(result)
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

        if with_raw_search:
            if exclude_std:
                matches = sorted(
                    self._raw_rtfm_cache_without_std,
                    key=lambda name: fuzz.ratio(query, name),
                    reverse=True,
                )
            else:
                matches = sorted(
                    self._raw_rtfm_cache_with_std,
                    key=lambda name: fuzz.ratio(query, name),
                    reverse=True,
                )
            return matches[:limit]

        def get_name(obj: DataObjStr) -> str:
            name = (
                obj.name if obj.name else obj.dispname if obj.dispname not in ["-", None] else None
            )
            original_name = name
            if obj.domain == "std":
                name = f"{obj.role}: {name}"
            if self._rtfm_cache.project == "discord.py":
                if name.startswith("discord."):
                    name = name[8:]  # .replace("discord.ext.commands.", "")
            return name, original_name or name

        def build_uri(obj: DataObjStr) -> str:
            location = obj.uri
            if location.endswith("$"):
                location = location[:-1] + obj.name
            return urljoin(self.url, location)

        matches = sorted(
            self._rtfm_cache.objects,
            key=lambda x: fuzz.ratio(query, x.name),
            reverse=True,
        )
        results = [
            (*get_name(item), build_uri(item), bool(item.domain == "std")) for item in matches
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
            name = f"discord.{name}"
        result = discord.utils.get(self._docs_cache, name=name)
        return result

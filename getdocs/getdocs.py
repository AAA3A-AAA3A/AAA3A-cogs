from .AAA3A_utils import CogsUtils  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
from redbot.core.bot import Red  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import aiohttp
import asyncio
import functools
import time
from fuzzywuzzy import fuzz
# from playwright._impl._api_types import TimeoutError as PlaywrightTimeoutError
# from playwright.async_api import async_playwright
from urllib.parse import ParseResult, urljoin, urlparse
from bs4 import BeautifulSoup, SoupStrainer, Tag, ResultSet
from sphobjinv import DataObjStr, Inventory

from .types import SearchResults, Documentation, Attribute

if CogsUtils().is_dpy2:
    from .view import DocsView

# Credits:
# Thanks to amyrinbot on GitHub for a part of the code (https://github.com/amyrinbot/bot/blob/main/modules/util/scraping/documentation/discord_py.py)!
# Thanks to @Lemon for the idea of this code (show me @Lambda bot in dpy server)!
# Thanks to @epic guy on Discord for the basic syntax (command groups, commands) and also commands (await ctx.send, await ctx.author.send, await ctx.message.delete())!
# Thanks to the developers of the cogs I added features to as it taught me how to make a cog! (Chessgame by WildStriker, Captcha by Kreusada, Speak by Epic guy and Rommer by Dav)
# Thanks to all the people who helped me with some commands in the #coding channel of the redbot support server!

_ = Translator("GetDocs", __file__)

if CogsUtils().is_dpy2:
    from functools import partial

    hybrid_command = partial(commands.hybrid_command, with_app_command=False)
    hybrid_group = partial(commands.hybrid_group, with_app_command=False)
else:
    hybrid_command = commands.command
    hybrid_group = commands.group

BASE_URLS = {
    "discord.py": {"url": "https://discordpy.readthedocs.io/en/stable/", "icon_url": "https://cdn.discordapp.com/attachments/381963689470984203/1068553303908155442/sW87z7N.png", "aliases": ["dpy"]},
    "redbot": {"url": "https://docs.discord.red/en/stable/", "icon_url": "https://media.discordapp.net/attachments/133251234164375552/1074432427201663086/a_aab012f3206eb514cac0432182e9e9ec.png", "aliases": ["red"]},
    "python": {"url": "https://docs.python.org/3/", "icon_url": "https://assets.stickpng.com/images/5848152fcef1014c0b5e4967.png", "aliases": ["py"]},
    "aiohttp": {"url": "https://docs.aiohttp.org/en/stable/", "icon_url": "https://docs.aiohttp.org/en/stable/_static/aiohttp-plain.svg"},
    "requests": {"url": "https://requests.readthedocs.io/en/latest/", "icon_url": "https://requests.readthedocs.io/en/latest/_static/requests-sidebar.png"},
    "pillow": {"url": "https://pillow.readthedocs.io/en/stable/", "icon_url": "https://pillow.readthedocs.io/en/stable/_static/pillow-logo-dark-text.png"},
    # "numpy": {"url": "https://numpy.org/doc/stable/", "icon_url": "https://numpy.org/doc/stable/_static/numpylogo.svg"},
    # "matplotlib": {"url": "https://matplotlib.org/stable/index.html", "icon_url": "https://matplotlib.org/stable/_static/images/logo2.svg"},
    "asyncpg": {"url": "https://magicstack.github.io/asyncpg/current/", "icon_url": None},
    # "pygame": {"url": "https://pygame.readthedocs.io/en/latest/", "icon_url": "https://camo.githubusercontent.com/1971c0a4f776fb5351c765c37e59630c83cabd52/68747470733a2f2f7777772e707967616d652e6f72672f696d616765732f6c6f676f2e706e67"},
    "psutil": {"url": "https://psutil.readthedocs.io/en/latest/", "icon_url": None},
}


class SourceConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str):
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
    """A cog to get and display Sphinx docs! Only `discord.py`, `redbot`, `python`, `aiohttp`, `request`, `asyncpg` and `pillow` for the moment."""

    def __init__(self, bot: Red):
        self.bot: Red = bot

        self.documentations: typing.Dict[str, Source] = {}

        # self._playwright = None
        # self._browser = None
        # self._bcontext = None
        self._session: aiohttp.ClientSession = None

        self.__authors__ = ["AAA3A", "amyrinbot"]
        self.cogsutils = CogsUtils(cog=self)

    async def cog_load(self):
        # self._playwright = await async_playwright().start()
        # self._browser = await self._playwright.chromium.launch()
        # self._bcontext = await self._browser.new_context()
        self._session = aiohttp.ClientSession()
        for source in BASE_URLS:
            self.documentations[source] = Source(self, name=source, url=BASE_URLS[source]["url"], icon_url=BASE_URLS[source]["icon_url"])
            asyncio.create_task(self.documentations[source].load())

    if CogsUtils().is_dpy2:
        async def cog_unload(self):
            self.cogsutils._end()
            if self._session is not None:
                await self._session.close()
    else:
        def cog_unload(self):
            self.cogsutils._end()
            if self._session is not None:
                asyncio.create_task(self._session.close())

    @hybrid_command(aliases=["getdoc", "docs", "documentations"])
    async def getdocs(self, ctx: commands.Context, source: typing.Optional[SourceConverter], *, query: str):
        """View rich documentation for a specific node/query.

           The name must be exact, or else rtfm is invoked instead.

           Arguments:
           - `source`: The name of the documentation to use. Defaults to `discord.py`.
           - `query`: The documentation node/query.
        """
        if source is None:
            source = "discord.py"
        source = self.documentations[source]
        try:
            if self.cogsutils.is_dpy2:
                await DocsView(ctx, query=query, source=source).start()
            else:
                results = await source.search(query, limit=25, exclude_std=True)
                if not results or not results.results:
                    raise RuntimeError("No results found.")
                doc = None
                i = 0
                doc = await source.get_documentation(results.results[0][0])
                while doc is None and i < len(results.results):
                    doc = await source.get_documentation(results.results[i][0])
                    if doc is not None:
                        break
                    i += 1
                if doc is None:
                    raise RuntimeError("No results found.")
                embed = doc.to_embed()
                content = None
                if source._docs_caching_task is not None and source._docs_caching_task.currently_running:
                    content = "⚠️ The documentation cache is not yet fully built, building now."
                await ctx.send(content=content, embed=embed)
        except RuntimeError as e:
            raise commands.UserFeedbackCheckFailure(str(e))

    @hybrid_command()
    async def rtfm(self, ctx: commands.Context, source: typing.Optional[SourceConverter], limit: typing.Optional[int], with_std: typing.Optional[bool], *, query: str):
        """Show all attributes matching your search.

           The name must be exact, or else rtfm is invoked instead.

           Arguments:
           - `source`: The name of the documentation to use. Defaults to `discord.py`.
           - `limit`: The limit of objects to be sent.
           - `with_std`: Also display links to non-API documentation.
           - `query`: Your search.
        """
        if source is None:
            source = "discord.py"
        source = self.documentations[source]
        try:
            result = await source.search(query, exclude_std=not with_std)
        except RuntimeError as e:
            raise commands.UserFeedbackCheckFailure(str(e))
        if result is None or not result.results:
            raise commands.UserFeedbackCheckFailure(_("No results found."))
        await ctx.send(embed=result.to_embed(limit=limit))


class Source:

    def __init__(self, cog: GetDocs, name: str, url: str, icon_url: typing.Optional[str] = None):
        self.cog = cog
        self.name: str = name
        self.url: str = url
        self.icon_url: typing.Optional[str] = icon_url

        self._rtfm_cache_url: str = urljoin(url, "objects.inv")
        self._rtfs_commit: typing.Optional[str] = None

        self._rtfm_caching_task = None
        self._docs_caching_task = None
        self._docs_caching_progress: typing.Dict[str, typing.Optional[typing.Union[bool, Exception]]] = {}
        # self._rtfs_caching_task = None

        self._rtfm_cache: typing.List = None
        self._docs_cache: typing.List[Documentation] = []
        self._result_docs_cache: typing.Dict[str, Documentation] = {}
        # self._rtfs_cache: typing.List = []

    async def load(self):
        self._rtfm_caching_task = self.cog.cogsutils.create_loop(self._build_rtfm_cache, name=f"{self.name}: Build RTFM Cache", limit_count=1)
        while self._rtfm_cache is None or (self._rtfm_caching_task is not None and self._rtfm_caching_task.currently_running):
            await asyncio.sleep(1)
        if not self._docs_cache:
            self._docs_caching_task = self.cog.cogsutils.create_loop(self._build_docs_cache, name=f"{self.name}: Build Documentations Cache", limit_count=1)
        # if not self._rtfs_cache:
            # self._rtfs_caching_task = self.cog.cogsutils.create_loop(self._build_rtfs_cache, name=f"{self.name}: Build RTFS Cache", limit_count=1)

    ###################
    # Building caches #
    ###################

    async def _build_rtfm_cache(self, recache: bool = False):
        if self._rtfm_cache is not None and not recache:
            return self._rtfm_cache
        self.cog.log.debug(f"{self.name}: Starting RTFM caching...")
        partial = functools.partial(Inventory, url=self._rtfm_cache_url)
        loop = asyncio.get_running_loop()
        self._rtfm_cache = await loop.run_in_executor(None, partial)
        self.cog.log.debug(f"{self.name}: RTFM cache built.")
        return self._rtfm_cache

    async def _build_docs_cache(self, recache: bool = False) -> typing.Dict[str, typing.List[Documentation]]:
        if self._docs_cache and not recache:
            return self._result_docs_cache
        if recache:
            self._docs_cache = []
            self._result_docs_cache = {}
        self.cog.log.debug(f"{self.name}: Starting Documentations caching...")

        # def bs4(content: str) -> typing.List[typing.Set]:  # typing.List[set[str, str]]
        #     soup = BeautifulSoup(content, "lxml")
        #     if self.name == "discord.py":
        #         manual_section = soup.find("section", id="manuals")
        #     else:
        #         manual_section = soup.find("section")
        #     if manual_section is None:
        #         raise RuntimeError()
        #     manual_lis = manual_section.find_all("li", class_="toctree-l1")
        #     manual_as = [manual_li.find("a") for manual_li in manual_lis]
        #     manuals = [
        #         (manual.text, self.url + (manual.get("href")))
        #         for manual in manual_as
        #     ]
        #     return manuals
        # if self.name == "discord.py":
        #     content = await self._get_html(self.url)
        #     try:
        #         manuals = bs4(content)
        #     except RuntimeError:
        #         return
        _manuals = set([obj.uri.split("#")[0] for obj in self._rtfm_cache.objects if obj.domain != "std"])
        manuals = []
        for manual in _manuals:
            if manual.endswith("#$"):
                manual = manual[:-2]
            manuals.append((manual, self.url + manual))

        for name, _ in manuals:
            self._docs_caching_progress[name] = None
        for name, manual in manuals:
            try:
                documentations = await self._get_all_manual_documentations(manual)
                if name not in self._result_docs_cache.keys():
                    self._result_docs_cache[name] = []
                self._result_docs_cache[name] = documentations
                for documentation in documentations:
                    self._docs_cache.append(documentation)
                self._docs_caching_progress[name] = True
                if self.cog.cogsutils.is_dpy2:
                    self.cog.log.trace(f"{self.name}: `{name}` documentation added to documentation cache.")
            except Exception as e:
                self.cog.log.debug(f"{self.name}: Error occured while trying to cache `{name}` documentation.", exc_info=e)
                self._docs_caching_progress[name] = e
        amount = sum(name in self._result_docs_cache.keys() for name, _ in manuals)
        self.cog.log.debug(f"{self.name}: Successfully cached {amount}/{len(manuals)} Documentations.")
        return self._result_docs_cache

    async def _get_html(self, url: str, timeout: int = 0, wait: bool = True) -> str:
        # page = await self.cog._bcontext.new_page()
        # await page.goto(url)
        # if wait:
        #     try:
        #         await page.wait_for_load_state("networkidle", timeout=timeout)
        #     except PlaywrightTimeoutError:
        #         pass
        # content = await page.content()
        async with self.cog._session.request("GET", url, timeout=timeout) as r:
            content = await r.text()
        return content

    def _get_text(self, element: Tag, parsed_url: ParseResult, template: str = "[`{}`]({})"):
        if isinstance(element, Tag) and element.name == "a":
            tag_name = element.text
            tag_href = element["href"]
            if parsed_url:
                parsed_href = urlparse(tag_href)
                if not parsed_href.netloc:
                    raw_url = parsed_url._replace(params="", fragment="").geturl()
                    tag_href = urljoin(raw_url, tag_href)
            text = template.format(tag_name, tag_href)
        elif isinstance(element, Tag) and element.name == "strong":
            text = f"**{element.text}**"
        else:
            text = element.text
        return text

    def _get_documentation(self, element: Tag, page_url: str) -> Documentation:
        try:
            url = element.find("a", class_="headerlink").get("href", None)
        except AttributeError:
            return
        full_url = urljoin(page_url, url)
        parsed_url = urlparse(full_url)
        parent = element.parent
        full_name = element.text
        name = element.attrs.get("id")
        documentation = parent.find("dd")
        description = []
        examples = []

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
                        name = name[10:]
                        role = "async with"
                    elif name.startswith("async for ... in "):
                        name = name[16:]
                        role = "async for ... in"
                    elif name.startswith("await "):
                        name = name[5:]
                        role = "await"
                    else:
                        role = None
                else:
                    role = None
                if (item.attrs.get("class") == ["py", "attribute"] or item.attrs.get("class") == ["py", "property"]) and len(infos) > 1:
                    description = [x.strip() for x in infos][1]
                else:
                    description = None
                href = item.find("span", class_="sig-name descname").get("href")
                url = urljoin(full_url, href)
                results[name] = {"role": role, "url": url, "description": description}
            return results
        attributes: typing.Dict[str, typing.List[Attribute]] = {}
        attribute_list = documentation.find_all("dl", class_="py attribute")
        if attribute_list:
            attributes["attributes"] = format_attributes(attribute_list)
        property_list = documentation.find_all("dl", class_="py property")
        if property_list:
            attributes["properties"] = format_attributes(property_list)
        methods_list = documentation.find_all("dl", class_="py method")
        if methods_list:
            attributes["methods"] = format_attributes(methods_list)

        fields = {}
        if supported_operations := documentation.find(
            "div", class_="operations", recursive=False
        ):
            items: typing.List[typing.Set] = []  # typing.List[set[str, str]]
            for supported_operation in supported_operations.findChildren(
                "dl", class_="describe"
            ):
                operation = supported_operation.find(
                    "span", class_="descname"
                ).text.strip()
                desc = self._get_text(
                    supported_operation.find("dd", recursive=False), parsed_url
                ).strip()
                items.append((operation, desc))
            if items:
                fields["Supported Operations"] = "\n".join(
                    f"> {operation}\n{desc}" for operation, desc in items
                )
        field_list = documentation.find("dl", class_="field-list", recursive=False)
        if field_list:
            for field in field_list.findChildren("dt"):
                field: Tag = field
                key = field.text
                values: typing.List[Tag] = [x for x in field.next_siblings if isinstance(x, Tag)][0].find_all("p")
                elements: typing.List[typing.List[str]] = []
                for value in values:
                    texts = []
                    for element in value.contents:
                        text = self._get_text(element, parsed_url)
                        texts.append(text.replace("\n", " "))
                    elements.append(texts)
                fields[key] = "\n".join("".join(element) for element in elements)
        for child in documentation.find_all("p", recursive=False):
            child: Tag = child
            if child.attrs.get("class"):
                break
            elements = []
            for element in child.contents:
                text = self._get_text(element, parsed_url)
                elements.append(text)
            description.append("".join(elements))
        for child in documentation.find_all("div", class_=["highlight-python3", "highlight-default", "highlight"], recursive=False):
            examples.append(child.find("pre").text)
        if version_modified := documentation.find("div", class_="versionchanged"):
            _version_modified = [f"*{x}*" for x in self._get_text(version_modified, parsed_url).split("\n") if not x == ""]
            version_modified = "\n".join(_version_modified)
            description.append(version_modified)
        description = "\n\n".join(description).replace("Example:", "").strip()
        full_name = full_name.replace("¶", "").strip()
        url = parsed_url.geturl()
        return Documentation(
            self,
            name=name,
            full_name=full_name,
            description=description,
            examples=examples,
            url=url,
            fields=fields,
            attributes=attributes,
        )

    async def _get_all_manual_documentations(self, url: str) -> typing.List[Documentation]:
        def bs4(content: str):
            strainer = SoupStrainer("dl")
            soup = BeautifulSoup(content, "lxml", parse_only=strainer)
            if self._rtfm_cache is not None and (self._rtfm_caching_task is None or not self._rtfm_caching_task.currently_running):
                e1 = soup.find_all("dt", id=[x.name for x in self._rtfm_cache.objects])
            else:
                e1 = ResultSet(strainer)
            e2 = soup.find_all("dt", class_="sig sig-object py")
            return ResultSet(strainer, set(e1 + e2))
        elements = bs4(await self._get_html(url))
        results = []
        for element in elements:
            result = self._get_documentation(element, url)
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
    ) -> SearchResults:
        if self._rtfm_cache is None or (self._rtfm_caching_task is not None and self._rtfm_caching_task.currently_running):
            raise RuntimeError(_("RTFM caching isn't finished."))
        start = time.monotonic()

        def get_name(obj: DataObjStr) -> str:
            name = (
                obj.name
                if obj.name
                else obj.dispname
                if obj.dispname not in ["-", None]
                else None
            )
            original_name = name
            if obj.domain == "std":
                name = f"{obj.role}: {name}"
            if self._rtfm_cache.project == "discord.py":
                name = name.replace("discord.", "")  # .replace("discord.ext.commands.", "")
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
            (*get_name(item), build_uri(item), bool(item.domain == "std"))
            for item in matches
        ]
        if exclude_std:
            results = [result for result in results if not result[3]]
        end = time.monotonic()
        return SearchResults(self, results=results[:limit], query_time=int(end - start))

    async def get_documentation(self, name: str) -> Documentation:
        # if self._docs_caching_task is not None and self._docs_caching_task.currently_running:
        #     raise RuntimeError(_("Documentations cache is not yet built, building now."))
        if self.name == "discord.py":
            name = f"discord.{name}"
        result = discord.utils.get(self._docs_cache, name=name)
        return result

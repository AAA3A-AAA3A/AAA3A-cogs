from AAA3A_utils import Cog, Loop, CogsUtils, Menu, Settings  # isort:skip
from redbot.core import commands, app_commands, Config  # isort:skip
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
import sys
import tempfile
import time
from dataclasses import is_dataclass
from urllib.parse import ParseResult, urljoin, urlparse

import aiohttp
from bs4 import BeautifulSoup, NavigableString, ResultSet, SoupStrainer, Tag
from fuzzywuzzy import fuzz
from prettytable import PrettyTable
from redbot.core.utils import AsyncIter
from redbot.core.utils.chat_formatting import humanize_list, inline
from sphobjinv import DataObjStr, Inventory

from .dashboard_integration import DashboardIntegration
from .types import Attribute, Attributes, Documentation, Examples, Parameters, SearchResults
from .view import GetDocsView

# from playwright._impl._api_types import TimeoutError as PlaywrightTimeoutError
# from playwright.async_api import async_playwright
# from aiolimiter import AsyncLimiter


# Credits:
# General repo credits.
# Thanks to amyrinbot on GitHub for a part of the code (https://github.com/amyrinbot/bot/blob/main/modules/util/scraping/documentation/discord_py.py)!
# Thanks to Lemon for the idea of this code (showed me @Lambda bot in the dpy server), for the documentations links, and for many ideas and suggestions!
# Thanks to Danny for fuzzy search function (https://github.com/Rapptz/RoboDanny/blob/rewrite/cogs/utils/fuzzy.py#L325-L350)!

_ = Translator("GetDocs", __file__)


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


def get_object_size(obj: typing.Any) -> int:
    size = sys.getsizeof(obj)
    try:
        if isinstance(obj, typing.List):
            size += sum(get_object_size(item) for item in obj)
        elif isinstance(obj, typing.Tuple):
            size += sum(get_object_size(item) for item in obj)
        elif isinstance(obj, typing.Dict):
            size += sum(
                get_object_size(key) + get_object_size(value)
                for key, value in obj.items()
                if isinstance(key, str) and not key.startswith("_")
            )
        elif is_dataclass(obj):
            size += sum(
                get_object_size(key) + get_object_size(getattr(obj, key))
                for key in obj.__dataclass_fields__
                if isinstance(key, str) and not key.startswith("_")
            )
    except RecursionError:
        pass
    return size


# https://stackoverflow.com/questions/1094841/get-human-readable-version-of-file-size
def sizeof_fmt(num, suffix: str = "B") -> str:
    for unit in ["", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"]:
        if abs(num) < 1024.0:
            return f"{num:3.1f} {unit}{suffix}"
        num /= 1024.0
    return f"{num:.1f} Yi{suffix}"


BASE_URLS: typing.Dict[str, typing.Dict[str, typing.Any]] = {
    "discord.py": {
        "url": "https://discordpy.readthedocs.io/en/stable/",
        "icon_url": "https://cdn.discordapp.com/attachments/381963689470984203/1068553303908155442/sW87z7N.png",
        "aliases": ["dpy", "discordpy", "discord-py"],
    },
    "redbot": {
        "url": "https://docs.discord.red/en/latest/",
        "icon_url": "https://media.discordapp.net/attachments/133251234164375552/1074432427201663086/a_aab012f3206eb514cac0432182e9e9ec.png",
        "aliases": ["red"],
    },
    "python": {
        "url": "https://docs.python.org/3/",
        "icon_url": "https://assets.stickpng.com/images/5848152fcef1014c0b5e4967.png",
        "aliases": ["py", "python3", "python-3", "py3"],
    },
    "aiohttp": {
        "url": "https://docs.aiohttp.org/en/stable/",
        "icon_url": "https://docs.aiohttp.org/en/v3.7.3/_static/aiohttp-icon-128x128.png",
        "aliases": ["ahttp"],
    },
    "requests": {
        "url": "https://requests.readthedocs.io/en/latest/",
        "icon_url": "https://requests.readthedocs.io/en/latest/_static/requests-sidebar.png",
    },
    "discordapi": {  # Special source.
        "url": "https://discord.com/developers/docs/",
        "icon_url": "https://c.clc2l.com/t/d/i/discord-4OXyS2.png",
        "aliases": ["apidiscord"],
    },
    "pylav": {
        "url": "https://pylav.readthedocs.io/en/latest/",
        "icon_url": "https://avatars.githubusercontent.com/u/125160897?s=88&v=4",
    },
    "phentags": {  # Cogs `Tags` and `SlashTags` by Phen.
        "url": "https://phen-cogs.readthedocs.io/en/latest/",
        "icon_url": "https://i.imgur.com/dIOX12K.png",
        "aliases": ["slashtags"],
    },
    "git": {  # Special source.
        "url": "https://git-scm.com/docs/",
        "icon_url": "https://git-scm.com/images/logos/downloads/Git-Icon-1788C.png",
        "aliases": ["pythongit"],
    },
    "aiomysql": {"url": "https://aiomysql.readthedocs.io/en/stable/", "icon_url": None},
    "asyncpg": {
        "url": "https://magicstack.github.io/asyncpg/current/",
        "icon_url": None,
        "aliases": ["apg"],
    },
    "flask": {
        "url": "https://flask.palletsprojects.com/",
        "icon_url": "https://flask.palletsprojects.com/en/2.2.x/_images/flask-logo.png",
    },
    "gitpython": {
        "url": "https://gitpython.readthedocs.io/en/stable/",
        "icon_url": "https://git-scm.com/images/logos/downloads/Git-Icon-1788C.png",
        "aliases": ["pythongit"],
    },
    "mango": {"url": "https://pymongo.readthedocs.io/en/latest/", "icon_url": None},
    "matplotlib": {
        "url": "https://matplotlib.org/stable/",
        "icon_url": "https://matplotlib.org/2.1.2/_static/logo2.png",
        "aliases": ["mpl"],
    },
    "motor": {
        "url": "https://motor.readthedocs.io/en/stable/",
        "icon_url": "https://motor.readthedocs.io/en/stable/_images/motor.png",
    },
    "numpy": {
        "url": "https://numpy.org/doc/stable/",
        "icon_url": "https://www.google.com/url?sa=i&url=https%3A%2F%2Frphabet.github.io%2Fposts%2Fpython_numpy_loop%2F&psig=AOvVaw1WvAODE50upYEYKVF68d8s&ust=1676914473120000&source=images&cd=vfe&ved=0CBAQjRxqFwoTCLiMo66Pov0CFQAAAAAdAAAAABAJ",
        "aliases": ["np"],
    },
    "piccolo": {"url": "https://piccolo-orm.readthedocs.io/en/latest/", "icon_url": None},
    "pillow": {
        "url": "https://pillow.readthedocs.io/en/stable/",
        "icon_url": "https://pillow.readthedocs.io/en/stable/_static/pillow-logo-dark-text.png",
        "aliases": ["pil"],
    },
    "psutil": {"url": "https://psutil.readthedocs.io/en/latest/", "icon_url": None},
    "redis": {
        "url": "https://redis-py.readthedocs.io/en/stable/",
        "icon_url": "https://blog.loginradius.com/static/4eda1ce5a0f541d97fdf27cd88bf2a49/03979/index.png",
    },
    "sphinx": {
        "url": "https://www.sphinx-doc.org/en/master/",
        "icon_url": "https://www.sphinx-doc.org/en/master/_static/sphinxheader.png",
    },
    "sqlite": {"url": "https://pysqlite.readthedocs.io/en/latest/", "icon_url": None},
    "starlite": {
        "url": "https://docs.litestar.dev/2/",
        "icon_url": "https://preview.redd.it/2veaqsnz2uf81.png?width=1280&format=png&auto=webp&s=8d7c84d4ec435fc102c14f3f2534ee2c3e5c1cae",
    },
    "websockets": {
        "url": "https://websockets.readthedocs.io/en/latest/",
        "icon_url": "https://repository-images.githubusercontent.com/9113587/aa03b380-afdb-11eb-8e88-2c7542e1670f",
    },
    "warcraftapi": {  # Special source.
        "url": "https://wowpedia.fandom.com/wiki/World_of_Warcraft_API",
        "icon_url": "https://static.wikia.nocookie.net/wowpedia/images/e/e6/Site-logo.png",
        "aliases": ["warcraft"],
    },
}


class SourceConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> str:
        cog: GetDocs = ctx.bot.get_cog("GetDocs")
        if argument.lower() not in cog.documentations:
            found = False
            for name, documentation in cog.documentations.items():
                if argument.lower() in documentation.aliases:
                    argument = name
                    found = True
            if not found:
                raise commands.BadArgument(_("Please provide a valid documentations source."))
        return argument.lower()


class StrConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> str:
        return argument


@cog_i18n(_)
class GetDocs(Cog, DashboardIntegration):
    """A cog to get and display some documentations in Discord! Use `[p]listsources` to get a list of all the available sources."""

    def __init__(self, bot: Red) -> None:
        super().__init__(bot=bot)
        self.__authors__: typing.List[str] = ["AAA3A", "amyrinbot"]

        self.config: Config = Config.get_conf(
            self,
            identifier=205192943327321000143939875896557571750,
            force_registration=True,
        )
        self.getdocs_global: typing.Dict[str, typing.Union[str, bool, typing.List[str]]] = {
            "default_source": "discord.py",
            "caching": True,
            "enabled_sources": ["discord.py", "redbot", "aiohttp", "discordapi"],
        }
        self.config.register_global(**self.getdocs_global)

        self.documentations: typing.Dict[str, Source] = {}
        self._docs_stats: typing.Dict[str, int] = {"GLOBAL": {"manuals": 0, "documentations": 0}}
        self._load_time: float = None
        self._caching_time: typing.Dict[str, int] = {"GLOBAL": 0}
        self._docs_sizes: typing.Dict[str, int] = {"GLOBAL": 0}

        # self._playwright = None
        # self._browser = None
        # self._bcontext = None
        self._session: aiohttp.ClientSession = None
        # self._rate_limit = AsyncLimiter(100, 30)

        _settings: typing.Dict[
            str, typing.Dict[str, typing.Union[typing.List[str], bool, str]]
        ] = {
            "default_source": {
                "converter": SourceConverter,
                "description": "Set the documentations source.",
            },
            "caching": {
                "converter": bool,
                "description": "Enable or disable Documentations caching when loading the cog.\n\nIf the option is disabled, a web request will be executed when the command `[p]getdocs` is run only for the searched item.",
            },
        }
        self.settings: Settings = Settings(
            bot=self.bot,
            cog=self,
            config=self.config,
            group=self.config.GLOBAL,
            settings=_settings,
            global_path=[],
            use_profiles_system=False,
            can_edit=True,
            commands_group=self.configuration,
        )

    async def cog_load(self) -> None:
        await super().cog_load()
        await self.settings.add_commands()
        # self._playwright = await async_playwright().start()
        # self._browser = await self._playwright.chromium.launch()
        # self._bcontext = await self._browser.new_context()
        self._load_time = int(time.monotonic())
        self._session: aiohttp.ClientSession = aiohttp.ClientSession()
        enabled_sources = await self.config.enabled_sources()
        for source in BASE_URLS:
            if source not in enabled_sources:
                continue
            self.documentations[source] = Source(
                self,
                name=source,
                url=BASE_URLS[source]["url"],
                icon_url=BASE_URLS[source]["icon_url"],
                aliases=BASE_URLS[source].get("aliases", []),
            )
            asyncio.create_task(self.documentations[source].load())

    async def cog_unload(self) -> None:
        await super().cog_unload()  # Close loops before session closing.
        if self._session is not None:
            await self._session.close()

    async def red_delete_data_for_user(self, *args, **kwargs) -> None:
        """Nothing to delete."""
        return

    async def red_get_data_for_user(self, *args, **kwargs) -> typing.Dict[str, typing.Any]:
        """Nothing to get."""
        return {}

    @commands.bot_has_permissions(embed_links=True)
    @commands.hybrid_command(
        aliases=["getdoc", "docs", "doc"],
    )
    @app_commands.describe(
        source="The name of the documentation to use.",
        query="The documentation node/query. (`random` to get a random documentation)",
    )
    async def getdocs(
        self,
        ctx: commands.Context,
        source: typing.Optional[SourceConverter] = None,
        *,
        query: typing.Optional[str] = None,
    ) -> None:
        """
        View rich documentation for a specific node/query.

        The name must be exact, or else rtfm is invoked instead.

        Arguments:
        - `source`: The name of the documentation to use. Defaults to the one configured with `[p]setgetdocs defaultsource`.
        - `query`: The documentation node/query. (`random` to get a random documentation)
        """
        try:
            if source is None:
                source = await self.config.default_source()
                if source not in self.documentations:
                    if "discord.py" not in self.documentations:
                        raise commands.UserFeedbackCheckFailure(
                            _("Please provide a valid documentations source.")
                        )
                    source = "discord.py"
            source: Source = self.documentations[source]
            if query is None:
                embed = discord.Embed(description=source.url)
                embed.set_author(
                    name=f"{source.name} Documentation",
                    icon_url=source.icon_url,
                )
                view = discord.ui.View()
                view.add_item(discord.ui.Button(label="Click to view", url=source.url))
                await ctx.send(embed=embed, view=view)
                return
            if query == "random":
                if not source._docs_cache:
                    raise commands.UserFeedbackCheckFailure(
                        _("Documentations cache is not yet built.")
                    )
                choice: Documentation = random.choice(source._docs_cache)
                if not any([choice.parameters, choice.examples, choice.attributes]):
                    await ctx.send(embed=choice.to_embed(embed_color=await ctx.embed_color()))
                    return
                query = choice.name
            try:
                await GetDocsView(cog=self, query=query.strip(), source=source).start(ctx)
            except RuntimeError as e:
                raise commands.UserFeedbackCheckFailure(str(e))
        except GeneratorExit as e:
            await self.cog_command_error(ctx, commands.CommandInvokeError(e))

    @commands.bot_has_permissions(embed_links=True)
    @commands.hybrid_command(aliases=["rtfd"])
    @app_commands.describe(
        source="The name of the documentation to use.",
        limit="The limit of items to be sent.",
        with_std="Also display links to non-API documentation.",
        query="Your search. (`events` to get all dpy events, for `discord.py`, `redbot` and `pylav` source only)",
    )
    async def rtfm(
        self,
        ctx: commands.Context,
        source: typing.Optional[SourceConverter] = None,
        limit: typing.Optional[int] = 10,
        with_std: typing.Optional[bool] = False,
        *,
        query: typing.Optional[str] = "",
    ) -> None:
        """
        Show all items matching your search.

        Arguments:
        - `source`: The name of the documentation to use. Defaults to the one configured with `[p]setgetdocs defaultsource`.
        - `limit`: The limit of objects to be sent.
        - `with_std`: Also display links to non-API documentation.
        - `query`: Your search. (`events` to get all dpy events, for `discord.py`, `redbot` and `pylav` source only)
        """
        if source is None:
            source = await self.config.default_source()
            if source not in self.documentations:
                if "discord.py" not in self.documentations:
                    raise commands.UserFeedbackCheckFailure(
                        _("Please provide a valid documentations source.")
                    )
                source = "discord.py"
        source: Source = self.documentations[source]
        if query in ["", "events"]:
            limit = None
        try:
            result = await source.search(query.strip(), limit=limit, exclude_std=not with_std)
        except RuntimeError as e:
            raise commands.UserFeedbackCheckFailure(str(e))
        if result is None or not result.results:
            raise commands.UserFeedbackCheckFailure(_("No results found."))
        embeds = result.to_embeds(embed_color=await ctx.embed_color())
        if len(embeds) == 1:
            await ctx.send(embed=embeds[0])
        else:
            await Menu(pages=embeds).start(ctx)

    # async def _cogsutils_add_hybrid_commands(
    #     self, command: typing.Union[commands.HybridCommand, commands.HybridGroup]
    # ) -> None:
    #     if command.app_command is None:
    #         return
    #     if not isinstance(command, commands.HybridCommand):
    #         return
    #     if "source" in command.app_command._params:
    #         command.app_command._params["source"].required = True
    #         command.app_command._params["source"].default = await self.config.default_source()
    #         command.app_command._params["source"].choices = [
    #             app_commands.Choice(name=source, value=source)
    #             for source in list(self.documentations.keys())
    #         ][:25]
    #     if "query" in command.app_command._params:
    #         command.app_command._params["query"].required = True
    #     _params1 = command.app_command._params.copy()
    #     _params2 = list(command.app_command._params.keys())
    #     _params2 = sorted(_params2, key=lambda x: _params1[x].required, reverse=True)
    #     _params3 = {key: _params1[key] for key in _params2}
    #     command.app_command._params = _params3

    @getdocs.autocomplete("source")
    async def getdocs_source_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> typing.List[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=source, value=source)
            for source in self.documentations
            if source.lower().startswith(current.lower())
        ][:25]

    @rtfm.autocomplete("source")
    async def rtfm_source_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> typing.List[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=source, value=source)
            for source in self.documentations
            if source.lower().startswith(current.lower())
        ][:25]

    async def query_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
        exclude_std: typing.Optional[bool] = True,
    ) -> typing.Tuple["Source", typing.List[app_commands.Choice[str]]]:
        if "source" in interaction.namespace and interaction.namespace.source:
            try:
                source = await SourceConverter().convert(
                    await commands.Context.from_interaction(interaction),
                    interaction.namespace.source,
                )
            except commands.BadArgument:
                source = await self.config.default_source()
        else:
            source = await self.config.default_source()
        if source not in self.documentations:
            return []
        source = self.documentations[source]
        if not current:
            return source, [
                app_commands.Choice(name=name, value=name)
                for name in source._raw_rtfm_cache_with_std[:25]
            ]
        matches = await source.search(
            current, limit=25, exclude_std=exclude_std, with_raw_search=True
        )
        return source, [app_commands.Choice(name=name, value=name) for name in matches]

    @getdocs.autocomplete("query")
    async def getdocs_query_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> typing.List[app_commands.Choice[str]]:
        _, result = await self.query_autocomplete(interaction, current, exclude_std=True)
        if not current:
            result.insert(0, app_commands.Choice(name="random", value="random"))
        return result[:25]

    @rtfm.autocomplete("query")
    async def rtfm_query_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> typing.List[app_commands.Choice[str]]:
        exclude_std = True
        if "with_std" in interaction.namespace:
            exclude_std = not interaction.namespace.with_std
        source, result = await self.query_autocomplete(
            interaction, current, exclude_std=exclude_std
        )
        if not current and source.name in ["discord.py", "redbot", "pylav"]:
            result.insert(0, app_commands.Choice(name="events", value="events"))
        return result[:25]

    @commands.bot_has_permissions(embed_links=True)
    @commands.hybrid_command(
        name="listsources", aliases=["listdocsources", "listrtfmsources", "listsource"]
    )
    @app_commands.describe(
        _sorted="Whether to sort the list of sources alphabetically.",
        status="Whether to show all sources, only available sources or only disabled sources.",
    )
    async def _sources_list(
        self,
        ctx: commands.Context,
        _sorted: typing.Optional[bool] = False,
        status: typing.Optional[typing.Literal["available", "all", "disabled"]] = "available",
    ) -> None:
        """
        Shows a list of all sources, those that are available or those that are disabled.
        """
        if status == "available":
            keys: typing.List[str] = [f"`{key}`" for key in self.documentations.keys()]
            if _sorted:
                keys = sorted(keys)
            keys: str = humanize_list(keys)
        elif status == "all":
            keys: typing.List[str] = [f"`{key}`" for key in BASE_URLS.keys()]
            if _sorted:
                keys = sorted(keys)
            keys: str = humanize_list(keys)
        elif status == "disabled":
            keys: typing.List[str] = [
                f"`{key}`" for key in BASE_URLS.keys() if key not in self.documentations.keys()
            ]
            if _sorted:
                keys = sorted(keys)
            keys: str = humanize_list(keys)
        embed = discord.Embed(title="GetDocs Sources", color=await ctx.embed_color())
        embed.description = keys
        await ctx.send(embed=embed)

    @commands.is_owner()
    @commands.hybrid_group(name="setgetdocs")
    async def configuration(self, ctx: commands.Context) -> None:
        """
        Commands to configure GetDocs.
        """
        pass

    @configuration.command(name="enablesources", aliases=["enablesource"])
    @app_commands.describe(sources="The source(s) to enable.")
    async def _sources_enable(
        self, ctx: commands.Context, sources: commands.Greedy[StrConverter]
    ) -> None:
        """
        Enable Documentations source(s).
        """
        enabled_sources: typing.List[str] = await self.config.enabled_sources()
        for source in sources:
            if source in enabled_sources and source in self.documentations:
                raise commands.UserFeedbackCheckFailure(
                    _("The source `{source}` is already enabled.").format(source=source)
                )
            elif source not in BASE_URLS:
                raise commands.UserFeedbackCheckFailure(
                    _("The source `{source}` doesn't exist.").format(source=source)
                )
            enabled_sources.append(source)
            self.documentations[source] = Source(
                self,
                name=source,
                url=BASE_URLS[source]["url"],
                icon_url=BASE_URLS[source]["icon_url"],
                aliases=BASE_URLS[source]["aliases"],
            )
            asyncio.create_task(self.documentations[source].load())
        await self.config.enabled_sources.set(enabled_sources)

    @configuration.command(name="disablesources", aliases=["disablesource"])
    @app_commands.describe(sources="The source(s) to disable.")
    async def _sources_disable(
        self, ctx: commands.Context, sources: commands.Greedy[SourceConverter]
    ) -> None:
        """
        Disable Documentations source(s).
        """
        enabled_sources: typing.List[str] = await self.config.enabled_sources()
        for source in sources:
            if source not in enabled_sources:
                raise commands.UserFeedbackCheckFailure(
                    _("The source `{source}` is already disabled.").format(source=source)
                )
            elif source not in self.documentations:
                raise commands.UserFeedbackCheckFailure(
                    _("The source `{source}` doesn't exist.").format(source=source)
                )
            enabled_sources.remove(source)
        await self.config.enabled_sources.set(enabled_sources)

    @configuration.command(name="stats")
    async def stats(self, ctx: commands.Context) -> None:
        """
        Show stats about all documentations sources.
        """
        table = PrettyTable()
        table.field_names = ["Name", "Manuals", "Docs", "Caching", "Size"]
        table.add_row(
            [
                "GLOBAL",
                self._docs_stats["GLOBAL"]["manuals"],
                self._docs_stats["GLOBAL"]["documentations"],
                str(self._caching_time["GLOBAL"]) + "s",
                sizeof_fmt(self._docs_sizes["GLOBAL"]),
            ]
        )
        for source in self.documentations:
            table.add_row(
                [
                    source,
                    self._docs_stats.get(source, {"manuals": None, "documentations": None})[
                        "manuals"
                    ],
                    self._docs_stats.get(source, {"manuals": None, "documentations": None})[
                        "documentations"
                    ],
                    f"{str(self._caching_time[source])}s"
                    if source in self._caching_time
                    else None,
                    sizeof_fmt(self._docs_sizes[source]) if source in self._docs_sizes else None,
                ]
            )
        await Menu(pages=str(table), lang="py").start(ctx)

    @configuration.command(hidden=True)
    async def getdebugloopsstatus(self, ctx: commands.Context) -> None:
        """Get an embed to check loops status."""
        embeds = [loop.get_debug_embed() for loop in self.loops]
        await Menu(pages=embeds).start(ctx)

    @commands.Cog.listener()
    async def on_assistant_cog_add(
        self, assistant_cog: typing.Optional[commands.Cog] = None
    ) -> None:  # Vert's Assistant integration/third party.
        if assistant_cog is None:
            return self.get_documentation_for_assistant
        schema = {
            "name": "get_documentation_for_assistant",
            "description": f"Get the documentation for an object/method from one of the following sources: {humanize_list([f'`{source}`' for source in self.documentations])}.",
            "parameters": {
                "type": "object",
                "properties": {
                    "source": {
                        "type": "string",
                        "description": "The name of the documentation source.",
                    },
                    "query": {
                        "type": "string",
                        "description": "The name of the object/method to search.",
                    },
                },
                "required": ["source", "query"],
            },
        }
        await assistant_cog.register_function(cog_name=self.qualified_name, schema=schema)

    async def get_documentation_for_assistant(self, source: str, query: str, *args, **kwargs):
        if source not in self.documentations.keys():
            return f"This source doesn't exist! Valid sources are: {humanize_list([f'`{source}`' for source in self.documentations])}."
        source = self.documentations[source]
        results = await source.search(query, limit=1, exclude_std=True)
        if not results.results:
            return "No documentation found for this query."
        documentation = await source.get_documentation(results.results[0][1])
        if documentation is None:
            return "No documentation found for this query."
        data = {
            "Name": documentation.name,
            "Signature": documentation.signature,
            "Description": documentation.description.replace("\n", " "),
            "Parameters": f"{humanize_list([inline(parameter.split(' ')[0].strip('**')) for parameter in documentation.parameters])}."
            if documentation.parameters
            else "No parameter(s)",
        }
        for _type in ["attributes", "properties", "methods"]:
            if getattr(documentation.attributes, _type):
                # result += f"{_type.capitalize()}:\n{BREAK_LINE.join([f'• {inline(attribute.name)}' for _type in ['attributes', 'properties', 'methods'] for attribute in getattr(documentation.attributes, _type).values()]) or 'No attribute(s)'}.\n"
                data[
                    _type.capitalize()
                ] = f"{humanize_list([inline(attribute.name) for _type in ['attributes', 'properties', 'methods'] for attribute in getattr(documentation.attributes, _type).values()])}."
        return [f"{key}: {value}\n" for key, value in data.items() if value is not None]


class Source:
    def __init__(
        self,
        cog: GetDocs,
        name: str,
        url: str,
        icon_url: typing.Optional[str] = None,
        aliases: typing.Optional[typing.List[str]] = None,
    ) -> None:
        if aliases is None:
            aliases = []
        self.cog: GetDocs = cog
        self.name: str = name
        self.url: str = url
        self.icon_url: typing.Optional[str] = icon_url
        self.aliases: typing.List[str] = aliases

        if self.url.startswith("http"):
            self._rtfm_cache_url: str = urljoin(url, "objects.inv")
        else:
            self._rtfm_cache_url: str = f"{self.url}/objects.inv"
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
        if not hasattr(self, f"_build_{self.name}_docs_cache"):
            self._rtfm_caching_task: Loop = Loop(
                cog=self.cog,
                name=f"`{self.name}`: Build RTFM Cache",
                function=self._build_rtfm_cache,
                limit_count=1,
            )
            self.cog.loops.append(self._rtfm_caching_task)
            while self._rtfm_cache is None or (
                self._rtfm_caching_task is not None and self._rtfm_caching_task.currently_running
            ):
                await asyncio.sleep(1)
        self._docs_caching_task: Loop = Loop(
            cog=self.cog,
            name=f"`{self.name}`: Build Documentations Cache",
            function=self._build_docs_cache,
            limit_count=1,
        )
        self.cog.loops.append(self._docs_caching_task)
        # if not self._rtfs_cache:
        #     self._rtfs_caching_task: Loop = Loop(
        #         cog=self.cog,
        #         name=f"`{self.name}`: Build RTFS Cache",
        #         function=self._build_rtfs_cache,
        #         limit_count=1,
        #     )
        #     self.cog.loops.append(self._rtfs_caching_task)

    async def _build_rtfm_cache(self, recache: bool = False) -> Inventory:
        if self._rtfm_cache is not None and not recache:
            return self._rtfm_cache
        self.cog.log.debug(f"`{self.name}`: Starting RTFM caching...")
        partial = (
            functools.partial(Inventory, url=self._rtfm_cache_url)
            if self.url.startswith("http")
            else functools.partial(Inventory, self._rtfm_cache_url)
        )
        loop = asyncio.get_running_loop()
        self._rtfm_cache = await loop.run_in_executor(None, partial)
        for item in self._rtfm_cache.objects:
            if (
                self.name == "redbot"
                and len(item.name.split("-")) > 2
                and item.name.split("-")[1] == "command"
            ):
                item.role = "command"
            self._raw_rtfm_cache_with_std.append(item.name)
            if item.domain != "std":
                self._raw_rtfm_cache_without_std.append(item.name)
        self.cog.log.debug(f"`{self.name}`: RTFM cache built.")
        return self._rtfm_cache

    async def _build_docs_cache(
        self, recache: bool = False
    ) -> typing.Dict[str, typing.List[Documentation]]:
        if self._docs_cache and not recache:
            return self._docs_cache
        self._docs_cache = []
        self._result_docs_cache = {}
        self.cog.log.debug(f"`{self.name}`: Starting Documentations caching...")
        start = time.monotonic()
        self.cog._docs_stats[self.name] = {"manuals": 0, "documentations": 0}

        if not (await self.cog.config.caching()) and not hasattr(
            self, f"_build_{self.name}_docs_cache"
        ):
            return self._docs_cache
        if hasattr(self, f"_build_{self.name}_docs_cache"):
            try:
                _, manuals, documentations = await (
                    await executor()(getattr(self, f"_build_{self.name}_docs_cache"))()
                )
            except TypeError:
                _, manuals, documentations = await getattr(
                    self, f"_build_{self.name}_docs_cache"
                )()
            self._docs_cache.extend(documentations)
            self.cog._docs_stats[self.name]["manuals"] += len(manuals)
            self.cog._docs_stats["GLOBAL"]["manuals"] += len(manuals)
            self.cog._docs_stats[self.name]["documentations"] += len(documentations)
            self.cog._docs_stats["GLOBAL"]["documentations"] += len(documentations)
        else:
            manuals = []
            _manuals = {
                obj.uri.split("#")[0] for obj in self._rtfm_cache.objects if obj.domain != "std"
            }
            for manual in _manuals:
                if manual.endswith("#$"):
                    manual = manual[:-2]
                manuals.append((manual, self.url + manual))
            if self.name == "python":
                for i, manual in enumerate(
                    ["library/stdtypes.html", "library/functions.html"]
                ):  # important documentations
                    manuals.remove((manual, self.url + manual))
                    manuals.insert(i, (manual, self.url + manual))
                manual = "tutorial/datastructures.html"  # not found by RTFM caching task
                manuals.insert(i + 1, (manual, self.url + manual))
            async for name, manual in AsyncIter(
                manuals, delay=1, steps=1
            ):  # for name, manual in manuals:
                try:
                    documentations = await self._get_all_manual_documentations(manual)
                    # self._docs_cache.extend(documentations)
                    self.cog._docs_stats[self.name]["manuals"] += 1
                    self.cog._docs_stats["GLOBAL"]["manuals"] += 1
                    self.cog._docs_stats[self.name]["documentations"] += len(documentations)
                    self.cog._docs_stats["GLOBAL"]["documentations"] += len(documentations)
                    self.cog.log.verbose(
                        f"`{self.name}`: `{name}` documentation added to documentation cache."
                    )
                except Exception as e:
                    self.cog.log.debug(
                        f"`{self.name}`: Error occured while trying to cache `{name}` documentation.",
                        exc_info=e,
                    )
                    self._docs_caching_progress[name] = e
        amount = len(self._docs_cache)
        end = int(time.monotonic())
        duration = int(end - start)
        self.cog._caching_time[self.name] = duration
        total_duration = end - self.cog._load_time
        if total_duration > self.cog._caching_time["GLOBAL"]:
            self.cog._caching_time["GLOBAL"] = total_duration
        size = get_object_size(self._docs_cache)
        self.cog._docs_sizes[self.name] = size
        self.cog._docs_sizes["GLOBAL"] += size
        self.cog.log.debug(
            f"`{self.name}`: Successfully cached {amount} Documentations/{len(manuals)} manuals."
        )
        return self._docs_cache

    async def _build_discordapi_docs_cache(
        self,
    ) -> typing.Tuple[Inventory, typing.List[str], typing.List[Documentation]]:
        self._rtfm_cache = Inventory()
        self._rtfm_cache.project = "Discord API"
        self._rtfm_cache.version = "1.0"
        manuals = []
        documentations = []
        with tempfile.TemporaryDirectory() as directory:
            # Clone GitHub repo.
            repo_url = "https://github.com/discord/discord-api-docs.git"
            loop = asyncio.get_running_loop()
            partial = functools.partial(
                subprocess.run, ["git", "clone", repo_url, directory], capture_output=True
            )
            result = await loop.run_in_executor(None, partial)
            if result.returncode != 0:
                self.cog.log.error(
                    f"`{self.name}`: Error occured while trying to clone Discord API Docs's GitHub repo."
                )
                return self._rtfm_cache, [], []
            # Iter files.
            for subdir, _, files in os.walk(f"{directory}\\docs"):
                if subdir.endswith(
                    (
                        "docs",
                        "dispatch",
                        "game_and_server_management",
                        "game_sdk",
                        "policies_and_agreements",
                        "rich_presence",
                        "tutorials",
                    )
                ):
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
                        manuals.append((file, f"{self.url}{_subdir}/{_file}"))
                        # Find documentations.
                        _documentations: typing.List[str] = []
                        _current = None
                        for line in content.split("\n"):
                            if (
                                line.startswith("### ") or line.startswith("## ")
                            ) and not line.startswith(
                                ("### Guild Scheduled Event ", "### An ", "### Any ")
                            ):
                                if _current is not None:
                                    _documentations.append(_current.strip("### ").strip("## "))
                                _current = line
                            if _current is not None:
                                _current += f"\n{line}"
                        # Iter documentations.
                        for _documentation in _documentations:
                            if not _documentation:
                                continue
                            # Get name and signature.
                            _name = _documentation.split("\n")[0]
                            _documentation = "\n".join(_documentation.split("\n")[1:])
                            if _documentation.startswith(
                                f"## {_name}"
                            ) or _documentation.startswith(f"### {_name}"):
                                _documentation = "\n".join(_documentation.split("\n")[1:])
                            if len(_name.split(" % ")) == 2:
                                signature = _name.split(" % ")[1]
                                _name = _name.split(" % ")[0]
                                for _match in re.compile(r"{.*?#DOCS_(.*?)}").findall(signature):
                                    signature = signature.replace(f"#DOCS_{_match}", "")
                            else:
                                signature = ""
                            description = _documentation.split("###### ")[0]
                            if not description:
                                continue
                            for _match in re.compile(r"]\(#DOCS_(.*?)\)").findall(description):
                                if len(_match.split("/")) == 2:
                                    description = description.replace(
                                        f"#DOCS_{_match}",
                                        f"{self.url}{_match.split('/')[0].split('_')[0].lower()}/{'_'.join(_match.split('/')[0].split('_')[1:]).lower().replace('_', '-')}#{_match.split('/')[1]}",
                                    )
                                else:
                                    description = description.replace(
                                        f"#DOCS_{_match}",
                                        f"{self.url}{_match.split('_')[0].lower()}/{'_'.join(_match.split('_')[1:]).lower().replace('_', '-')}",
                                    )
                            # Get fields.
                            fields = {
                                field.split("\n")[0]: "\n".join(field.split("\n")[1:])
                                for field in _documentation.split("###### ")[1:]
                            }
                            examples = Examples()
                            for field in fields.copy():
                                if "Example" in field:
                                    examples.append(fields[field].strip())
                                    del fields[field]
                                elif "-----" in fields[field]:  # Format tables.
                                    value = ""
                                    for row in fields[field].split("\n"):
                                        if (
                                            not row
                                            or not row.startswith("|")
                                            or row == "|"
                                            or "-----" in row
                                        ):  # not row.startswith("|")
                                            continue
                                        row = row.split("|")
                                        if value != "":
                                            value += f"\n{'• ' if value else ''}{' | '.join([_row for _row in row if _row != ''])}"
                                        else:
                                            value += f"**{' | '.join([_row for _row in row if _row != ''])}**"
                                    fields[field] = value
                            if signature:  # Create a custom example for each endpoint.
                                _method = signature.split(" ")[0]
                                _path = signature.split(" ")[1]
                                example = "from discord.http import Route"
                                _kwargs = re.compile(r"{(.*?)}").findall(_path)
                                if _kwargs:
                                    example += "\nkwargs = {"
                                    for _kwarg in _kwargs:
                                        _kwarg_raw = "\n    "
                                        _kwarg_raw += f'"{_kwarg.replace(".", "_")}": '
                                        _kwarg_raw += (
                                            f'"{_kwarg.split(".")[0].upper()}_ID",  # snowflake'
                                            if _kwarg.split(".")[-1] == "id"
                                            and _kwarg.split(".")[-2]
                                            in [
                                                "user",
                                                "member",
                                                "guild",
                                                "channel",
                                                "role",
                                                "message",
                                                "application",
                                            ]
                                            else "MISSING,"
                                        )
                                        example += _kwarg_raw
                                        _path = _path.replace(
                                            "{" + _kwarg + "}",
                                            "{" + _kwarg.replace(".", "_") + "}",
                                        )
                                    example += "\n}"
                                    example += f'\nroute: Route = Route(method="{_method}", path="{_path}", **kwargs)'
                                else:
                                    example += f'\nroute: Route = Route(method="{_method}", path="{_path}")'
                                _kwargs = ""
                                for key, value in {
                                    "Query String Params": "params",
                                    "JSON Params": "json",
                                    "JSON/Form Params": "json",
                                }.items():
                                    if key in fields:
                                        example += f"\n_{value}" + "= {"
                                        for _param in fields[key].split("\n"):
                                            if not _param.startswith("• "):
                                                continue
                                            _param = _param.split(" | ")
                                            if len(_param) <= 2 or len(_param[0]) <= 3:
                                                continue
                                            _param_raw = "\n    "
                                            if _param[0][2:].strip().endswith("?"):
                                                _param_raw += (
                                                    f'# ? "{_param[0][2:].strip()[:-1]}": '
                                                )
                                            elif _param[0][2:].strip().endswith("?\\*"):
                                                _param_raw += (
                                                    f'# ?\\* "{_param[0][2:].strip()[:-3]}": '
                                                )
                                            else:
                                                _param_raw += f'"{_param[0][2:].strip()}": '
                                            if (
                                                len(fields[key].split("\n")[0].split(" | ")) > 3
                                                and "default"
                                                in fields[key]
                                                .split("\n")[0]
                                                .split(" | ")[3]
                                                .lower()
                                                and _param[3].split("(")[0].strip()
                                            ):
                                                _param_raw += (
                                                    f'{_param[3].split("(")[0].strip()}'
                                                    if _param[1].strip() == "integer"
                                                    else f'"{_param[3].split("(")[0].strip()}"'
                                                )
                                            else:
                                                _param_raw += (
                                                    '"true"'
                                                    if _param[1].strip() == "boolean"
                                                    else "MISSING"
                                                )
                                            _param_raw += f",  # {_param[1].strip()[1:] if _param[1].strip().endswith('?') else _param[1].strip()}"
                                            example += _param_raw
                                        example += "\n}"
                                        _kwargs += f", {value}=_{value}"
                                example += (
                                    f"\nreturn await ctx.bot.http.request(route=route{_kwargs})"
                                )
                                examples.insert(0, example)
                            # Add to RTFM cache.
                            _object = DataObjStr(
                                name=_name,
                                domain="py",
                                role="endpoint" if signature else _subdir,
                                priority="1",
                                uri=f"{self.url}{_subdir}/{_file}#{_name.lower().replace('_', '-').replace(' ', '-')}",
                                dispname="-",
                            )
                            setattr(_object, "fake", True)
                            self._rtfm_cache.objects.append(_object)
                            self._raw_rtfm_cache_with_std.append(_object.name)
                            if _object.domain != "std":
                                self._raw_rtfm_cache_without_std.append(_object.name)
                            # Add to Documentations cache.
                            documentation = Documentation(
                                self,
                                name=_name,
                                url=f"{self.url}{_subdir}/{_file}#{_name.lower().replace('_', '-').replace(' ', '-')}",
                                signature=signature,
                                description=description,
                                parameters=None,
                                examples=examples,
                                fields=fields,
                                attributes=Attributes(attributes={}, properties={}, methods={}),
                            )
                            documentations.append(documentation)
                            self._docs_cache.append(documentation)
                        self.cog.log.verbose(
                            f"`{self.name}`: `{name}` documentation added to documentation cache."
                        )
                    except Exception as e:
                        self.cog.log.debug(
                            f"`{self.name}`: Error occured while trying to cache `{name}` documentation.",
                            exc_info=e,
                        )
                        self._docs_caching_progress[name] = e
        return self._rtfm_cache, manuals, documentations

    async def _build_git_docs_cache(
        self,
    ) -> typing.Tuple[Inventory, typing.List[str], typing.List[Documentation]]:
        self._rtfm_cache = Inventory()
        self._rtfm_cache.project = "Git"
        self._rtfm_cache.version = "1.0"
        manuals = []
        documentations = []
        # Find manuals.
        content = await self._get_html(self.url)
        soup = BeautifulSoup(content, "lxml")
        for manuals_category in soup.find_all("ul", class_="unstyled"):
            manuals.extend(
                (e.text, self.url + e.find("a").get("href", "").split("/")[-1])
                for e in manuals_category.find_all("li")
            )
        # Iter manuals.
        for manual in manuals:
            try:
                manual_content = await self._get_html(manual[1])
                soup = BeautifulSoup(manual_content, "lxml")
                # Find documentation.
                _documentation = soup.find("div", id="main")
                # Get informations.
                div = _documentation.find_all("div", class_="sectionbody")
                _name = self._get_text(div[0], parsed_url=manual[1]).strip()
                signature = self._get_text(div[1], parsed_url=manual[1]).strip()
                description = self._get_text(div[2], parsed_url=manual[1])
                parameters = self._get_text(div[3], parsed_url=manual[1])
                examples = Examples(
                    [
                        self._get_text(div[4], parsed_url=manual[1])
                        .strip()
                        .replace("\n\n\n\n", "\n")
                    ]
                )
                # Add to RTFM cache.
                _object = DataObjStr(
                    name=_name,
                    domain="py",
                    role="command",
                    priority="1",
                    uri=manual[1],
                    dispname="-",
                )
                setattr(_object, "fake", True)
                self._rtfm_cache.objects.append(_object)
                self._raw_rtfm_cache_with_std.append(_object.name)
                if _object.domain != "std":
                    self._raw_rtfm_cache_without_std.append(_object.name)
                # Add to Documentations cache.
                documentation = Documentation(
                    self,
                    name=_name,
                    url=manual[1],
                    signature=signature,
                    description=description,
                    parameters=parameters,
                    examples=examples,
                    fields={},
                    attributes=Attributes(attributes={}, properties={}, methods={}),
                )
                documentations.append(documentation)
                self._docs_cache.append(documentation)
                self.cog.log.verbose(
                    f"`{self.name}`: `{manual[0]}` documentation added to documentation cache."
                )
            except Exception as e:
                self.cog.log.debug(
                    f"`{self.name}`: Error occured while trying to cache `{manual[0]}` documentation.",
                    exc_info=e,
                )
                self._docs_caching_progress[manual[0]] = e
        return self._rtfm_cache, manuals, documentations

    async def _build_warcraftapi_docs_cache(
        self,
    ) -> typing.Tuple[Inventory, typing.List[str], typing.List[Documentation]]:
        self._rtfm_cache = Inventory()
        self._rtfm_cache.project = "Warcraft API"
        self._rtfm_cache.version = "1.0"
        manuals = []
        documentations = []
        # Find manuals.
        content = await self._get_html(self.url)
        soup = BeautifulSoup(content, "lxml")
        manuals.extend(
            (
                potential_manual.text.strip(),
                self.url.split("/wiki")[0] + potential_manual.attrs["href"],
            )
            for potential_manual in soup.find_all("a")
            if potential_manual.attrs.get("href") is not None
            and potential_manual.attrs["href"].startswith("/wiki/API_")
            and potential_manual.text.strip() not in ["API changes", "loadstring"]
        )
        # Iter manuals.
        for manual in manuals:
            try:
                _name = manual[0]
                manual_content = await self._get_html(manual[1])
                soup = BeautifulSoup(manual_content, "lxml")
                # Get "Main Section".
                # soup = BeautifulSoup(manual_content[:manual_content.index('<a href="/wiki/Wowpedia:Interface_customization" title="Wowpedia:Interface customization">Main Menu</a>')], "lxml")
                # soup = BeautifulSoup(manual_content[:manual_content.index(str(soup.find("a", title="Wowpedia:Interface customization")))], "lxml")
                # Get informations.
                try:
                    description = soup.find("p").text.strip()
                    signature = soup.find("pre").text.strip()
                except AttributeError:
                    continue
                fields = {}
                try:
                    fields_labels = soup.find_all("span", class_="mw-headline")
                    fields_values = soup.find_all(("dl", "ul"))
                    for field_value in fields_values.copy():
                        if field_value.name == "ul":
                            text = self._get_text(
                                field_value, parsed_url=self.url.split("/wiki")[0]
                            )
                            if (
                                len(text.split("\n\n")) > 1
                                or "WoW API" in text
                                or "Hyperlinks" in text
                                or "mainline" in text
                                or "Wowprogramming" in text
                                or "Townlong Yak" in text
                            ):
                                fields_values.remove(field_value)
                    used_fields_values = set()
                    for field_label in fields_labels:
                        if field_label.text.strip().lower() in ["patch changes"]:
                            continue
                        _field_value = self._get_text(
                            fields_values.pop(0), parsed_url=self.url.split("/wiki")[0]
                        )
                        while _field_value.replace(" ", "") in used_fields_values:
                            _field_value = self._get_text(
                                fields_values.pop(0), parsed_url=self.url.split("/wiki")[0]
                            )
                        used_fields_values.add(_field_value.replace(" ", ""))
                        lines = _field_value.split("\n")
                        field_value = (
                            "".join(
                                f"**{line.strip()}**\n"
                                if i % 2 == 0
                                else f"> {line.split(' - ')[0].strip()}{' - ' if line.split(' - ')[1:] else ''}{' - '.join(line.split(' - ')[1:]).strip()}\n"
                                for i, line in enumerate(lines)
                            )
                            if len(lines) % 2 == 0
                            else _field_value
                        )
                        fields[field_label.text.strip()] = field_value
                except IndexError:
                    pass
                # Add to RTFM cache.
                _object = DataObjStr(
                    name=_name,
                    domain="py",
                    role="endpoint",
                    priority="1",
                    uri=manual[1],
                    dispname="-",
                )
                setattr(_object, "fake", True)
                self._rtfm_cache.objects.append(_object)
                self._raw_rtfm_cache_with_std.append(_object.name)
                if _object.domain != "std":
                    self._raw_rtfm_cache_without_std.append(_object.name)
                # Add to Documentations cache.
                documentation = Documentation(
                    self,
                    name=_name,
                    url=manual[1],
                    signature=signature,
                    description=description,
                    parameters={},
                    examples=Examples(),
                    fields=fields,
                    attributes=Attributes(attributes={}, properties={}, methods={}),
                )
                documentations.append(documentation)
                self._docs_cache.append(documentation)
                self.cog.log.verbose(
                    f"`{self.name}`: `{manual[0]}` documentation added to documentation cache."
                )
            except Exception as e:
                self.cog.log.debug(
                    f"`{self.name}`: Error occured while trying to cache `{manual[0]}` documentation.",
                    exc_info=e,
                )
                self._docs_caching_progress[manual[0]] = e
        return self._rtfm_cache, manuals, documentations

    async def _get_html(self, url: str, timeout: int = 0) -> str:
        # async with self.cog._rate_limit:
        if not self.url.startswith("http"):
            url = f"{self.url}/{url[len(self.url):]}"
            with open(url, mode="rt", encoding="utf-8") as file:
                return file.read()
        async with self.cog._session.get(url, timeout=timeout) as r:
            content = await r.text(encoding="utf-8")
        return content

    def _get_text(
        self, element: Tag, parsed_url: ParseResult, template: str = "[**`{}`**]({})"
    ) -> str:
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
        signature = element.text
        signature = signature.strip().replace("¶", "").replace("", "").replace("\n", "")
        if signature.endswith("[source]"):
            signature = signature[:-8]
        elif signature.endswith("[source]#"):
            signature = signature[:-9]
        if self.name == "python" and page_url == self.url + "tutorial/datastructures.html":
            name = signature.strip("\n").split("(")[0]
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

        _signature = parse_method_role(signature)
        signature = (f"{_signature[0]} " if _signature[0] is not None else "") + _signature[1]

        # Description & Examples
        description: typing.List[str] = []
        examples = Examples()
        for child in documentation.children:
            child: Tag = child
            if isinstance(child, NavigableString):
                continue
            if child.name == "div":
                if child.attrs.get("class") is not None and child.attrs.get("class")[0].startswith(
                    "highlight"
                ):
                    example = child.find("pre").text.strip()
                    if example not in examples:
                        examples.append(example)
                    example_index = examples.index(example) + 1
                    if len(description) > 1 and description[-1].endswith(":"):
                        # del description[-1]
                        description[-1] = f"{description[-1]} [See Example **#{example_index}**]"
                    continue
                else:
                    break
            elif child.attrs.get("class") is not None and not (
                child.name == "ul" and child.attrs.get("class") == ["simple"]
            ):
                break
            if child.name == "p":
                elements = []
                for element in child.contents:
                    text = self._get_text(element, parsed_url)
                    elements.append(text)
                description.append("".join(elements))
            elif child.name == "ul":  # and child.attrs.get("class") == ["simple"]:
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
        description = "\n\n".join(description).strip()

        # Examples
        # examples = Examples()
        # for child in documentation.find_all(
        #     "div", class_=["highlight-python3", "highlight-default", "highlight", "highlight-pycon3"], recursive=True
        # ):
        #     example = child.find("pre").text.strip()
        #     if example in examples:
        #         continue
        #     examples.append(example)

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
                if key[-1] == ":":
                    key = key[:-1]
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
                        try:
                            elements[-1].extend(texts)
                        except IndexError:
                            pass
                        else:
                            continue
                    elements.append(texts)
                if key.startswith("Parameters") and "Parameters" not in fields:  # PyLav by Draper.
                    key = "Parameters"
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
            signature=signature,
            description=description,
            parameters=parameters,
            examples=examples,
            fields=fields,
            attributes=attributes,
        )

    async def _get_all_manual_documentations(
        self, page_url: str, item_name: typing.Optional[str] = None
    ) -> typing.List[Documentation]:
        @executor()
        def bs4(content: str):
            strainer = SoupStrainer("dl")
            soup = BeautifulSoup(content, "lxml", parse_only=strainer)
            if item_name is not None:
                r = soup.find(id=item_name)
                return [r] if r is not None else []
            if self._rtfm_cache is not None and (
                self._rtfm_caching_task is None or not self._rtfm_caching_task.currently_running
            ):
                e1 = soup.find_all("dt", id=list(self._raw_rtfm_cache_without_std))
            else:
                e1 = ResultSet(strainer)
            e2 = soup.find_all("dt", class_="sig sig-object py")
            return ResultSet(strainer, set(e1 + e2))

        elements = await bs4(await self._get_html(page_url))
        if item_name is not None and not elements:
            return None
        results: typing.List[Documentation] = []
        async for element in AsyncIter(elements, delay=0.1, steps=1):  # for element in elements:
            result = await self._get_documentation(element, page_url)
            if item_name is not None:
                return result
            if result is not None:
                results.append(result)
        # Add attributes for Python stdtypes.
        if self.name == "python" and page_url[len(self.url) :] in [
            "library/stdtypes.html",
            "tutorial/datastructures.html",
        ]:
            for documentation in results:
                if len(documentation.name.split(".")) > 1:
                    parent_name = ".".join(documentation.name.split(".")[:-1])
                    parent = discord.utils.get(results, name=parent_name) or discord.utils.get(
                        self._docs_cache, name=parent_name
                    )
                    if parent is not None:
                        parent.attributes.methods[
                            documentation.name[len(parent_name) + 1 :]
                        ] = Attribute(
                            name=documentation.name[(len(parent_name) + 1) * 2 :],
                            role="",
                            url=documentation.url,
                            description=documentation.description.split("\n")[0],
                        )
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

        def fuzzy_search(
            text: str,
            collection: typing.Iterable[typing.Union[str, typing.Any]],
            key: typing.Optional[typing.Callable] = None,
        ) -> typing.List[typing.Union[str, typing.Any]]:
            if self.name != None:  # "python":
                matches = []
                pat = ".*?".join(map(re.escape, text))
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

                def sort_key(
                    tup: typing.Tuple[int, int, typing.Union[str, typing.Any]]
                ) -> typing.Tuple[int, int, str]:
                    return tup[0], tup[1], _key(tup[2])

                matches = [item for __, __, item in sorted(matches, key=sort_key)]
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
            elif self.name == "aiohttp":
                for name in dir(aiohttp.ClientSession):
                    if name.startswith("_"):
                        continue
                    if query.lower() == name:
                        query = f"aiohttp.ClientSession.{name.lower()}"
                        break
        if self.name in ["discord.py", "redbot"]:
            if query.split(".")[0] == "ctx":
                query = f"commands.Context{query[4:]}"
            if self.name == "discord.py":
                query = re.sub(r"^(?:discord\.(?:ext\.)?)?(?:commands\.)?(.+)", r"\1", query)
        if with_raw_search:
            if exclude_std:
                matches = fuzzy_search(text=query, collection=self._raw_rtfm_cache_without_std)
            else:
                matches = fuzzy_search(text=query, collection=self._raw_rtfm_cache_with_std)
            return matches[:limit]

        def get_name(obj: DataObjStr) -> str:
            name = obj.name or (obj.dispname if obj.dispname not in ["-", None] else None)
            original_name = name
            if obj.domain == "std" or obj.role == "command" or self.name == "discordapi":
                name = f"{obj.role}: {name}"
            if self.name == "discord.py":
                if name.startswith("discord.ext.commands."):
                    name = name[21:]
                elif name.startswith("discord."):
                    name = name[8:]
            elif (
                self.name == "pylav"
                and query == "events"
                and name.startswith("pylav.events.")
                and name.split(".")[-1].endswith("Event")
                and name != "pylav.events.base.PyLavEvent"
            ):

                def to_snake_case(name: str) -> str:
                    return re.sub(
                        "([a-z0-9])([A-Z])",
                        r"\1_\2",
                        re.sub("__([A-Z])", r"_\1", re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)),
                    ).lower()

                name = f"on_pylav_{to_snake_case(name.split('.')[-1])} ({original_name})"
            return name, original_name

        def build_uri(obj: DataObjStr) -> str:
            location = obj.uri
            if location.endswith("$"):
                location = location[:-1] + obj.name
            if not self.url.startswith("http"):
                location = CogsUtils.replace_var_paths(location)
            return urljoin(self.url, location)

        if self.name in ["discord.py", "redbot", "pylav"] and query == "events":
            exclude_std = True
            matches = [
                item
                for item in self._rtfm_cache.objects
                if item.name.split(".")[-1].startswith("on_")
            ]
            if self.name == "pylav":
                matches = [
                    item
                    for item in self._rtfm_cache.objects
                    if item.name.startswith("pylav.events.")
                    and item.name.split(".")[-1].endswith("Event")
                ]
        else:
            matches = fuzzy_search(
                text=query, collection=self._rtfm_cache.objects, key=lambda item: item.name
            )
        results = [(*get_name(item), build_uri(item), item.domain == "std") for item in matches]
        results = [result for result in results if not result[2].startswith("c-api/")]
        if exclude_std:
            results = [result for result in results if not result[3]]
        end = time.monotonic()
        return SearchResults(
            self,
            results=results[:limit] if limit is not None else results,
            query_time=int(end - start),
        )

    async def get_documentation(self, name: str) -> Documentation:
        # if self._docs_caching_task is not None and self._docs_caching_task.currently_running:
        #     raise RuntimeError(_("Documentations cache is not yet built, building now."))
        # if self.name == "discord.py" and not self.name.startswith("discord."):
        #     if f"discord.{name}" in self._raw_rtfm_cache_without_std:
        #         name = f"discord.{name}"
        #     elif f"discord.ext.commands.{name}" in self._raw_rtfm_cache_without_std:
        #         name = f"discord.ext.commands.{name}"
        documentation = discord.utils.get(self._docs_cache, name=name)
        if self.name not in ["discordapi", "git", "warcraftapi"] and documentation is None:
            item = discord.utils.get(self._rtfm_cache.objects, name=name)
            location = item.uri
            if location.endswith("$"):
                location = location[:-1]
            if location.endswith("#"):
                location = location[:-1]
            page_url = urljoin(self.url, location)
            documentation = await self._get_all_manual_documentations(
                page_url=page_url, item_name=name
            )
            if documentation is None:
                return
            self._docs_cache.append(documentation)
            return documentation
        return documentation

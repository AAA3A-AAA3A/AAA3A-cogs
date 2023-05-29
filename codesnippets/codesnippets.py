from AAA3A_utils import Cog, CogsUtils, Menu, Settings  # isort:skip
from redbot.core import commands, Config  # isort:skip
from redbot.core.bot import Red  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import asyncio
import re
import textwrap
from collections import deque
from urllib.parse import quote_plus

import aiohttp
from redbot.core.utils.chat_formatting import pagify

from .dashboard_integration import DashboardIntegration

# Credits:
# General repo credits.
# Thanks to "Python Discord" for the code to find URls and get codes (https://github.com/python-discord/bot/blob/main/bot/exts/info/code_snippets.py)!

GITHUB_RE = re.compile(
    r"https://(?:www\.)?github\.com/(?P<repo>[a-zA-Z0-9-]+/[\w.-]+)/blob/(?P<path>[^#>]+)"
    r"((\?[^#>]+)?(#L?(?P<start_line>\d+)(([-~:]|(\.\.))L?(?P<end_line>\d+))?))?"
)
GITHUB_GIST_RE = re.compile(
    r"https://(?:www\.)?gist\.github\.com/([a-zA-Z0-9-]+)/(?P<gist_id>[a-zA-Z0-9]+)/*"
    r"(?P<revision>[a-zA-Z0-9]*)/*(#file-(?P<file_path>[^#>]+))?"
    r"((\?[^#->]+)?(-L?(?P<start_line>\d+)(([-~:]|(\.\.))L?(?P<end_line>\d+))?))?"
)
GITHUB_PR_DIFF_RE = re.compile(
    r"https://(?:www\.)?github\.com/(?P<repo>[a-zA-Z0-9-]+/[\w.-]+)/pull/(?P<pr_number>\d+)"
    r"((\?[^#>]+)?(#L?(?P<start_line>\d+)(([-~:]|(\.\.))L?(?P<end_line>\d+))?))?"
)
GITHUB_COMMIT_DIFF_RE = re.compile(
    r"https://(?:www\.)?github\.com/(?P<repo>[a-zA-Z0-9-]+/[\w.-]+)/commit/(?P<commit_hash>[a-zA-Z0-9]*)"
    r"((\?[^#>]+)?(#L?(?P<start_line>\d+)(([-~:]|(\.\.))L?(?P<end_line>\d+))?))?"
)
GITLAB_RE = re.compile(
    r"https://(?:www\.)?gitlab\.com/(?P<repo>[\w.-]+/[\w.-]+)/\-/blob/(?P<path>[^#>]+)"
    r"((\?[^#>]+)?(#L?(?P<start_line>\d+)(-(?P<end_line>\d+))?))?"
)
BITBUCKET_RE = re.compile(
    r"https://(?:www\.)?bitbucket\.org/(?P<repo>[a-zA-Z0-9-]+/[\w.-]+)/src/(?P<ref>[0-9a-zA-Z]+)/(?P<file_path>[^#>]+)"
    r"((\?[^#>]+)?(#lines-(?P<start_line>\d+)(:(?P<end_line>\d+))?))?"
)
PASTEBIN_RE = re.compile(
    r"https://(?:www\.)?pastebin\.com/(?P<paste_id>[a-zA-Z0-9]+)/*"
    r"((\?[^->]+)?(#L?(?P<start_line>\d+)(([-~:]|(\.\.))L?(?P<end_line>\d+))?))?"
)
HASTEBIN_RE = re.compile(
    r"https://(?:www\.)?hastebin\.com/(?P<paste_id>[a-zA-Z0-9]+)/*"
    r"((\?[^->]+)?(#L?(?P<start_line>\d+)(([-~:]|(\.\.))L?(?P<end_line>\d+))?))?"
)


GITHUB_HEADERS = {"Accept": "application/vnd.github.v3.raw"}

_ = Translator("CodeSnippets", __file__)


@cog_i18n(_)
class CodeSnippets(DashboardIntegration, Cog):
    """A cog to send code content from a GitHub/Gist/GitLab/BitBucket/Pastebin/Hastebin URL!"""

    def __init__(self, bot: Red) -> None:
        self.bot: Red = bot

        self.config: Config = Config.get_conf(
            self,
            identifier=205192943327321000143939875896557571750,
            force_registration=True,
        )
        self.codesnippets_guild: typing.Dict[str, typing.List] = {
            "channels": [],
        }
        self.config.register_guild(**self.codesnippets_guild)

        self.pattern_handlers = {
            GITHUB_RE: self.fetch_github_snippet,
            GITHUB_GIST_RE: self.fetch_github_gist_snippet,
            GITHUB_PR_DIFF_RE: self.fetch_github_pr_diff_snippet,
            GITHUB_COMMIT_DIFF_RE: self.fetch_github_commit_diff_snippet,
            GITLAB_RE: self.fetch_gitlab_snippet,
            BITBUCKET_RE: self.fetch_bitbucket_snippet,
            PASTEBIN_RE: self.fetch_pastebin_snippet,
            HASTEBIN_RE: self.fetch_hastebin_snippet,
        }
        self._session: aiohttp.ClientSession = None
        self.antispam_cache: typing.Dict[discord.abc.Messageable, deque[tuple, 5]] = {}

        self.cogsutils: CogsUtils = CogsUtils(cog=self)

        _settings: typing.Dict[
            str, typing.Dict[str, typing.Union[typing.List[str], bool, str]]
        ] = {
            "channels": {
                "path": ["channels"],
                "converter": typing.List[
                    typing.Union[discord.TextChannel, discord.VoiceChannel, discord.Thread]
                ],
                "description": "Channels where the cog have to send automatically code snippets from URLs.",
            },
        }
        self.settings: Settings = Settings(
            bot=self.bot,
            cog=self,
            config=self.config,
            group=self.config.GUILD,
            settings=_settings,
            global_path=[],
            use_profiles_system=False,
            can_edit=False,  # Just to show settings.
            commands_group=self.configuration,
        )

    async def cog_load(self) -> None:
        self._session: aiohttp.ClientSession = aiohttp.ClientSession()
        await self.settings.add_commands()

    async def cog_unload(self) -> None:
        if self._session is not None:
            await self._session.close()
        await super().cog_unload()

    async def _fetch_response(self, url: str, response_format: str, **kwargs) -> typing.Any:
        if "github.com" in url:
            api_tokens = await self.bot.get_shared_api_tokens(service_name="github")
            if (token := api_tokens.get("token")) is not None:
                if "headers" not in kwargs:
                    kwargs["headers"] = {}
                kwargs["headers"]["Authorization"] = f"Token {token}"
        async with self._session.get(url, raise_for_status=True, **kwargs) as response:
            if response_format == "text":
                return await response.text()
            return await response.json() if response_format == "json" else None

    def _find_ref(self, path: str, refs: tuple) -> tuple:
        ref, file_path = path.split("/", 1)
        for possible_ref in refs:
            if path.startswith(possible_ref["name"] + "/"):
                ref = possible_ref["name"]
                file_path = path[len(ref) + 1 :]
                break
        return ref, file_path

    async def fetch_github_snippet(
        self,
        repo: str,
        path: str,
        start_line: typing.Optional[str] = None,
        end_line: typing.Optional[str] = None,
    ) -> str:
        """Fetches a snippet from a GitHub repo."""
        branches = await self._fetch_response(
            f"https://api.github.com/repos/{repo}/branches",
            response_format="json",
            headers=GITHUB_HEADERS,
        )
        tags = await self._fetch_response(
            f"https://api.github.com/repos/{repo}/tags", response_format="json"
        )
        refs = branches + tags
        ref, file_path = self._find_ref(path, refs)

        file_contents = await self._fetch_response(
            f"https://api.github.com/repos/{repo}/contents/{file_path}?ref={ref}",
            response_format="text",
            headers=GITHUB_HEADERS,
        )
        return self._snippet_to_codeblock(source="GitHub", file_contents=file_contents, file_path=file_path, start_line=start_line, end_line=end_line)

    async def fetch_github_gist_snippet(
        self,
        gist_id: str,
        revision: str,
        file_path: typing.Optional[str] = None,
        start_line: typing.Optional[str] = None,
        end_line: typing.Optional[str] = None,
    ) -> str:
        """Fetches a snippet from a GitHub gist."""
        gist_json = await self._fetch_response(
            f"https://api.github.com/gists/{gist_id}{f'/{revision}' if revision != '' else ''}",
            response_format="json",
            headers=GITHUB_HEADERS,
        )
        if len(gist_json["files"]) == 1 and file_path is None:
            file_path = list(gist_json["files"])[0].lower().replace(".", "-")
        for gist_file in gist_json["files"]:
            if file_path == gist_file.lower().replace(".", "-"):
                file_contents = await self._fetch_response(
                    gist_json["files"][gist_file]["raw_url"],
                    "text",
                    headers=GITHUB_HEADERS,
                )
                return self._snippet_to_codeblock(source="GitHub Gist", file_contents=file_contents, file_path=gist_file, start_line=start_line, end_line=end_line)
        return "GitHub Gist", "", "", ""

    async def fetch_github_pr_diff_snippet(
        self,
        repo: str,
        pr_number: str,
        start_line: typing.Optional[str] = None,
        end_line: typing.Optional[str] = None,
    ) -> str:
        """Fetches a snippet from a GitHub PR diff."""
        file_contents = await self._fetch_response(
            f"https://api.github.com/repos/{repo}/pulls/{pr_number}",
            response_format="text",
            headers={"Accept": "application/vnd.github.v3.diff"},
        )
        source, ret, __, code = self._snippet_to_codeblock(
            source="GitHub", file_contents=file_contents, file_path=f"Diff Pull Request {pr_number} in {repo}", start_line=start_line, end_line=end_line
        )
        return source, ret, "diff", code

    async def fetch_github_commit_diff_snippet(
        self,
        repo: str,
        commit_hash: str,
        start_line: typing.Optional[str] = None,
        end_line: typing.Optional[str] = None,
    ) -> str:
        """Fetches a snippet from a GitHub Commit diff."""
        file_contents = await self._fetch_response(
            f"https://api.github.com/repos/{repo}/commits/{commit_hash}",
            response_format="text",
            headers={"Accept": "application/vnd.github.v3.diff"},
        )
        source, ret, __, code = self._snippet_to_codeblock(
            source="GitHub", file_contents=file_contents, file_path=f"Diff Commit `{commit_hash}` in {repo}", start_line=start_line, end_line=end_line
        )
        return source, ret, "diff", code

    async def fetch_gitlab_snippet(
        self,
        repo: str,
        path: str,
        start_line: typing.Optional[str] = None,
        end_line: typing.Optional[str] = None,
    ) -> str:
        """Fetches a snippet from a GitLab repo."""
        enc_repo = quote_plus(repo)
        branches = await self._fetch_response(
            f"https://gitlab.com/api/v4/projects/{enc_repo}/repository/branches",
            response_format="json",
        )
        tags = await self._fetch_response(
            f"https://gitlab.com/api/v4/projects/{enc_repo}/repository/tags",
            response_format="json",
        )
        refs = branches + tags
        ref, file_path = self._find_ref(path, refs)
        enc_ref = quote_plus(ref)
        enc_file_path = quote_plus(file_path)
        file_contents = await self._fetch_response(
            f"https://gitlab.com/api/v4/projects/{enc_repo}/repository/files/{enc_file_path}/raw?ref={enc_ref}",
            response_format="text",
        )
        return self._snippet_to_codeblock(source="GitLab", file_contents=file_contents, file_path=file_path, start_line=start_line, end_line=end_line)

    async def fetch_bitbucket_snippet(
        self,
        repo: str,
        ref: str,
        file_path: str,
        start_line: typing.Optional[str] = None,
        end_line: typing.Optional[str] = None,
    ) -> str:
        """Fetches a snippet from a BitBucket repo."""
        file_contents = await self._fetch_response(
            f"https://bitbucket.org/{quote_plus(repo)}/raw/{quote_plus(ref)}/{quote_plus(file_path)}",
            response_format="text",
        )
        return self._snippet_to_codeblock(source="BitBucket", file_contents=file_contents, file_path=file_path, start_line=start_line, end_line=end_line)

    async def fetch_pastebin_snippet(
        self,
        paste_id: str,
        start_line: typing.Optional[str] = None,
        end_line: typing.Optional[str] = None,
    ) -> str:
        """Fetches a snippet from a Pastebin paste."""
        file_contents = await self._fetch_response(
            f"https://pastebin.com/raw/{paste_id}", response_format="text"
        )
        source, ret, __, code = self._snippet_to_codeblock(
            source="PasteBin", file_contents=file_contents, file_path=f"Paste {paste_id}", start_line=start_line, end_line=end_line
        )
        return source, ret, "py", code

    async def fetch_hastebin_snippet(
        self,
        paste_id: str,
        start_line: typing.Optional[str] = None,
        end_line: typing.Optional[str] = None,
    ) -> str:
        """Fetches a snippet from a Hastebin paste."""
        api_tokens = await self.bot.get_shared_api_tokens(service_name="github")
        if (token := api_tokens.get("token")) is None:
            raise RuntimeError("No Hastebin token.")
        file_contents = await self._fetch_response(
            f"https://hastebin.com/raw/{paste_id}",
            response_format="text",
            headers={"Authentification": f"Bearer {token}"},
        )
        source, ret, __, code = self._snippet_to_codeblock(
            source="Hastebin", file_contents=file_contents, file_path=f"Paste {paste_id}", start_line=start_line, end_line=end_line
        )
        return source, ret, "py", code

    def _snippet_to_codeblock(
        self,
        source: str,
        file_contents: str,
        file_path: str,
        start_line: typing.Optional[str] = None,
        end_line: typing.Optional[str] = None,
    ) -> str:
        split_file_contents = file_contents.split("\n")
        if start_line is None and end_line is None:
            start_line = 1
            end_line = len(split_file_contents)
        elif end_line is None:
            start_line = end_line = int(start_line)
        else:
            start_line = int(start_line)
            end_line = int(end_line)

        if start_line > end_line:
            start_line, end_line = end_line, start_line
        if start_line > len(split_file_contents) or end_line < 1:
            return source, "", "", ""
        start_line = max(1, start_line)
        end_line = min(len(split_file_contents), end_line)

        code = "\n".join(split_file_contents[start_line - 1 : end_line])
        code = textwrap.dedent(code).rstrip().replace("`", "`\u200b")

        language = file_path.split("/")[-1].split(".")[-1]
        trimmed_language = language.replace("-", "").replace("+", "").replace("_", "")
        is_valid_language = trimmed_language.isalnum()
        if not is_valid_language:
            language = ""

        if start_line == end_line:
            ret = f"`{file_path}` line {start_line}."
        else:
            ret = f"`{file_path}` lines {start_line} to {end_line}."

        if len(code) > 0:
            return source, ret, language, code
        return source, "", "", ""

    async def parse_snippets(
        self,
        content: str,
        limit: typing.Optional[int] = None,
        is_listener: typing.Optional[bool] = False,
        channel: typing.Optional[discord.abc.Messageable] = None,
    ) -> typing.Dict[str, str]:
        all_snippets = {}
        i = 0
        for pattern, handler in self.pattern_handlers.items():
            for match in pattern.finditer(content):
                i += 1
                if limit is not None and i > limit:
                    return all_snippets
                if is_listener:
                    if (
                        channel in self.antispam_cache
                        and tuple(match.groupdict().items()) in self.antispam_cache[channel]
                    ):
                        continue
                    if channel not in self.antispam_cache:
                        self.antispam_cache[channel] = deque(maxlen=5)
                    self.antispam_cache[channel].append(tuple(match.groupdict().items()))
                try:
                    snippet = await handler(**match.groupdict())
                    if (snippet[1], snippet[2], snippet[3]) == ("", "", ""):
                        continue
                    snippet = snippet[0], f"{snippet[1]}\n> {match.group()}", snippet[2], snippet[3]
                    all_snippets[match.group()] = snippet
                except (RuntimeError, aiohttp.ClientResponseError) as e:
                    if e.status == 404:
                        continue
                    self.log.error(
                        f"Failed to fetch code snippet from {match[0]!r}: {e.status} for GET {e.request_info.real_url.human_repr()}.",
                        exc_info=e,
                    )
        return all_snippets

    async def send_snippets(
        self, ctx: commands.Context, snippets: typing.Dict[str, typing.Tuple[str, str, str]]
    ):
        for url, snippet in snippets.items():
            source, ret, language, code = snippet
            pages = pagify(
                code, shorten_by=len(f"```py\n{ret}\n```") + len(f"```{language}\n\n```")
            )
            pages = [f"```py\n{ret}\n```\n```{language}\n{page}\n```" for page in pages]
            menu = Menu(pages=pages)
            menu.extra_items.append(
                discord.ui.Button(style=discord.ButtonStyle.url, label=f"View on {source}", url=url)
            )
            asyncio.create_task(menu.start(ctx))

    @commands.hybrid_command(aliases=["codesnippet"])
    async def codesnippets(
        self,
        ctx: commands.Context,
        limit: typing.Optional[commands.Range[int, 1, 10]] = 3,
        *,
        urls: str,
    ) -> None:
        """Send code content from a GitHub/Gist/GitLab/BitBucket/Pastebin/Hastebin URL."""
        snippets = await self.parse_snippets(content=urls, limit=limit)
        if not snippets:
            raise commands.UserFeedbackCheckFailure(
                _("No GitHub/Gist/GitLab/BitBucket/Pastebin/Hastebin URL found.")
            )
        await self.send_snippets(ctx, snippets=snippets)

    @commands.Cog.listener()
    async def on_message_without_command(self, message: discord.Message) -> None:
        if message.webhook_id is not None or message.author.bot:
            return
        if message.guild is None:
            return
        if not await self.bot.allowed_by_whitelist_blacklist(message.author):
            return
        if message.channel.id not in await self.config.guild(message.guild).channels():
            return
        context = await self.bot.get_context(message)
        snippets = await self.parse_snippets(
            content=message.content, limit=3, is_listener=True, channel=message.channel
        )
        if not snippets:
            return
        await self.send_snippets(context, snippets=snippets)

    @commands.guild_only()
    @commands.admin_or_permissions(administrator=True)
    @commands.hybrid_group(name="setcodesnippets")
    async def configuration(self, ctx: commands.Context) -> None:
        """Configure CodeSnippets."""
        pass

    @configuration.command()
    async def addchannel(
        self,
        ctx: commands.Context,
        channel: typing.Union[discord.TextChannel, discord.VoiceChannel, discord.Thread],
    ) -> None:
        """Add a channel where the cog have to send automatically code snippets from URLs."""
        channels = await self.config.guild(ctx.guild).channels()
        if channel.id in channels:
            raise commands.UserFeedbackCheckFailure(
                _("The cog is already enabled in this channel")
            )
        channels.append(channel.id)
        await self.config.guild(ctx.guild).channels.set(channels)

    @configuration.command()
    async def removechannel(
        self,
        ctx: commands.Context,
        channel: typing.Union[discord.TextChannel, discord.VoiceChannel, discord.Thread],
    ) -> None:
        """Remove a channel where the cog have to send automatically code snippets from URLs."""
        channels = await self.config.guild(ctx.guild).channels()
        if channel.id not in channels:
            raise commands.UserFeedbackCheckFailure(
                _("The cog is already disabled in this channel")
            )
        channels.remove(channel.id)
        await self.config.guild(ctx.guild).channels.set(channels)

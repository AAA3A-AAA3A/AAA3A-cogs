from AAA3A_utils import Menu  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import io
import json
import re
import textwrap
import yaml

from redbot.core import dev_commands
from redbot.core.utils.chat_formatting import box

_ = Translator("EmbedUtils", __file__)

def cleanup_code(code: str) -> str:
    code = dev_commands.cleanup_code(textwrap.dedent(code)).strip()
    with io.StringIO(code) as codeio:
        for line in codeio:
            line = line.strip()
            if line and not line.startswith("#"):
                break
        else:
            return "pass"
    return code


class StringToEmbed(commands.Converter):
    def __init__(
        self, *, conversion_type: str = "json", validate: bool = False, content: bool = True
    ) -> None:
        self.CONVERSION_TYPES: typing.Dict[str, typing.Any] = {
            "json": self.load_from_json,
            "yaml": self.load_from_yaml,
        }

        self.validate: bool = validate
        self.conversion_type: typing.Literal["json", "yaml"] = conversion_type.lower()
        self.allow_content: bool = content
        try:
            self.converter = self.CONVERSION_TYPES[self.conversion_type]
        except KeyError as exc:
            raise ValueError(
                f"`{conversion_type}` is not a valid conversion type for Embed conversion."
            ) from exc

    async def convert(self, ctx: commands.Context, argument: str) -> typing.Dict[typing.Literal["embed", "content"], typing.Union[discord.Embed, str]]:
        argument = cleanup_code(argument)
        data = await self.converter(ctx, argument=argument)

        content = self.get_content(data)
        if "embed" in data:
            data = data["embed"]
        elif "embeds" in data:
            data = data.get("embeds")[0]
        if not data:
            raise commands.BadArgument(
                _(
                    "This doesn't seem to be properly formatted embed {conversion_type}. "
                    "Refer to the link on `{ctx.clean_prefix}help {ctx.command.qualified_name}`."
                ).format(conversion_type=self.conversion_type.upper(), ctx=ctx)
            )
        self.check_data_type(ctx, data=data)

        kwargs = await self.create_embed(ctx, data=data, content=content)
        if self.validate:
            await self.validate_embed(ctx, kwargs)
        return kwargs

    def check_data_type(self, ctx: commands.Context, data, *, data_type=dict) -> None:
        if not isinstance(data, data_type):
            raise commands.BadArgument(
                _(
                    "This doesn't seem to be properly formatted embed {conversion_type}. "
                    "Refer to the link on `{ctx.clean_prefix}help {ctx.command.qualified_name}`."
                ).format(conversion_type=self.conversion_type.upper(), ctx=ctx)
            )

    async def load_from_json(self, ctx: commands.Context, argument: str, **kwargs) -> typing.Dict[str, typing.Any]:
        try:
            data = json.loads(argument)
        except json.decoder.JSONDecodeError as error:
            await self.embed_convert_error(ctx, _("JSON Parse Error"), error)
            raise commands.BadArgument()
        self.check_data_type(ctx, data, **kwargs)
        return data

    async def load_from_yaml(self, ctx: commands.Context, argument: str, **kwargs) -> typing.Dict[str, typing.Any]:
        try:
            data = yaml.safe_load(argument)
        except Exception as error:
            await self.embed_convert_error(ctx, _("YAML Parse Error"), error)
            raise commands.BadArgument()
        self.check_data_type(ctx, data, **kwargs)
        return data

    def get_content(self, data: typing.Dict[str, typing.Any], *, content: str = None) -> typing.Optional[str]:
        content = data.pop("content", content)
        if content is not None and not self.allow_content:
            raise commands.BadArgument(_("The `content` field is not supported for this command."))
        return content

    async def create_embed(
        self, ctx: commands.Context, data: typing.Dict[str, typing.Any], *, content: str = None
    ) -> typing.Dict[typing.Literal["embed", "content"], typing.Union[discord.Embed, str]]:
        content = self.get_content(data, content=content)

        if timestamp := data.get("timestamp"):
            data["timestamp"] = timestamp.strip("Z")
        try:
            embed = discord.Embed.from_dict(data)
            length = len(embed)
        except Exception as error:
            await self.embed_convert_error(ctx, _("Embed Parse Error"), error)
            raise commands.BadArgument()

        if length > 6000:
            raise commands.BadArgument(
                _("Embed size exceeds Discord limit of 6000 characters ({length}).").format(length=length)
            )
        return {"embed": embed, "content": content}

    async def validate_embed(
        self, ctx: commands.Context, kwargs: typing.Dict[str, typing.Union[discord.Embed, str]]
    ) -> None:
        try:
            await ctx.channel.send(**kwargs)  # ignore tips/monkeypatch cogs
        except discord.errors.HTTPException as error:
            await self.embed_convert_error(ctx, _("Embed Send Error"), error)
            raise commands.BadArgument()

    @staticmethod
    async def embed_convert_error(ctx: commands.Context, error_type: str, error: Exception) -> None:
        embed: discord.Embed = discord.Embed(
            title=f"{error_type}: `{type(error).__name__}`",
            description=box(str(error), lang="py"),
            color=await ctx.embed_color(),
        )
        embed.set_footer(
            text=_("Use `{ctx.prefix}help {ctx.command.qualified_name}` to see an example.").format(ctx=ctx)
        )
        await Menu(pages=[embed]).start(ctx)


class ListStringToEmbed(StringToEmbed):
    def __init__(self, *, conversion_type: str = "json", limit: int = 10) -> None:
        super().__init__(conversion_type=conversion_type, content=False)
        self.limit: int = limit

    async def convert(self, ctx: commands.Context, argument: str) -> typing.Dict[typing.Literal["embeds", "content"], typing.Union[typing.List[discord.Embed], str]]:
        argument = cleanup_code(argument)
        data = await self.converter(ctx, argument=argument, data_type=(dict, list))

        content = data.get("content")
        if isinstance(data, typing.List):
            pass
        elif "embed" in data:
            data = [data["embed"]]
        elif "embeds" in data:
            data = data["embeds"]
            if isinstance(data, typing.Dict):
                data = list(data.values())
        else:
            data = [data]
        self.check_data_type(ctx, data=data, data_type=list)

        embeds = []
        for i, embed_data in enumerate(data, 1):
            kwargs = await self.create_embed(ctx, data=embed_data)
            embed = kwargs["embed"]
            embeds.append(embed)
            if i >= self.limit:
                raise commands.BadArgument(_("Embed limit reached ({limit}).").format(limit=self.limit))
        if embeds:
            return {"content": content, "embeds": embeds}
        else:
            raise commands.BadArgument(_("Failed to convert input into embeds."))


class MessageableConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> typing.Union[discord.TextChannel, discord.VoiceChannel, discord.Thread]:
        for converter in (commands.TextChannelConverter, commands.VoiceChannelConverter, commands.ThreadConverter):
            try:
                channel = await converter().convert(ctx, argument=argument)
            except commands.BadArgument:
                pass
            else:
                break
        else:
            raise commands.BadArgument(_("It's not a valid channel or thread."))
        bot_permissions = channel.permissions_for(ctx.me)
        if not (bot_permissions.send_messages and bot_permissions.embed_links):
            raise commands.BadArgument(
                _("I do not have permissions to send embeds in {channel.mention}.").format(channel=channel)
            )
        permissions = channel.permissions_for(ctx.author)
        if not (permissions.send_messages and permissions.embed_links):
            raise commands.BadArgument(
                _("You do not have permissions to send embeds in {channel.mention}.").format(channel=channel)
            )
        return channel


class MyMessageConverter(commands.MessageConverter):
    async def convert(self, ctx: commands.Context, argument: str) -> discord.Message:
        message = await super().convert(ctx, argument=argument)
        if message.author != ctx.me:
            raise commands.UserFeedbackCheckFailure(
                _("I have to be the author of the message. You can use the command without providing a message to send one.")
            )
        ctx.message.channel = message.channel
        fake_context = await ctx.bot.get_context(ctx.message)
        if not await discord.utils.async_all([check(fake_context) for check in ctx.bot.get_cog("EmbedUtils").embed_edit.checks]):
            raise commands.BadArgument(_("You are not allowed to edit embeds of an existing message (bot owner can set the permissions with the cog Permissions on the command `[p]embed edit`)."))
        return message


class MessageableOrMessageConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> typing.Union[discord.TextChannel, discord.VoiceChannel, discord.Thread, discord.Message]:
        try:
            return await MessageableConverter().convert(ctx, argument=argument)
        except commands.BadArgument as e:
            try:
                return await MyMessageConverter().convert(ctx, argument=argument)
            except commands.BadArgument:
                raise e


GITHUB_RE = re.compile(
    r"https://(?:www\.)?github\.com/(?P<repo>[a-zA-Z0-9-]+/[\w.-]+)/blob/(?P<path>[^#>]+)"
)
GITHUB_GIST_RE = re.compile(
    r"https://(?:www\.)?gist\.github\.com/([a-zA-Z0-9-]+)/(?P<gist_id>[a-zA-Z0-9]+)/*"
    r"(?P<revision>[a-zA-Z0-9]*)/*(#file-(?P<file_path>[^#>]+))?"
)
PASTEBIN_RE = re.compile(
    r"https://(?:www\.)?pastebin\.com/(?P<paste_id>[a-zA-Z0-9]+)/*"
)
HASTEBIN_RE = re.compile(
    r"https://(?:www\.)?hastebin\.com/(?P<paste_id>[a-zA-Z0-9]+)/*"
)

GITHUB_HEADERS = {"Accept": "application/vnd.github.v3.raw"}

class PastebinMixin:
    async def convert(self, ctx: commands.Context, argument: str) -> typing.Dict[typing.Literal["embed", "embeds", "content"], typing.Union[discord.Embed, typing.List[discord.Embed], str]]:
        async def _fetch_response(url: str, response_format: str, **kwargs) -> typing.Any:
            if "github.com" in url:
                api_tokens = await ctx.bot.get_shared_api_tokens(service_name="github")
                if (token := api_tokens.get("token")) is not None:
                    if "headers" not in kwargs:
                        kwargs["headers"] = {}
                    kwargs["headers"]["Authorization"] = f"Token {token}"
            async with ctx.bot.get_cog("EmbedUtils")._session.get(url, raise_for_status=True, **kwargs) as response:
                if response_format == "text":
                    return await response.text()
                return await response.json() if response_format == "json" else None

        def _find_ref(path: str, refs: typing.List[dict]) -> typing.Tuple[str, str]:
            ref, file_path = path.split("/", 1)
            for possible_ref in refs:
                if path.startswith(possible_ref["name"] + "/"):
                    ref = possible_ref["name"]
                    file_path = path[len(ref) + 1 :]
                    break
            return ref, file_path

        if (_match := list(GITHUB_RE.finditer(argument))):
            _match = _match[0].groupdict()
            branches = await _fetch_response(
                f"https://api.github.com/repos/{_match['repo']}/branches",
                response_format="json",
                headers=GITHUB_HEADERS,
            )
            tags = await _fetch_response(
                f"https://api.github.com/repos/{_match['repo']}/tags", response_format="json"
            )
            refs = branches + tags
            ref, file_path = _find_ref(_match['path'], refs)
            argument = await _fetch_response(
                f"https://api.github.com/repos/{_match['repo']}/contents/{file_path}?ref={ref}",
                response_format="text",
                headers=GITHUB_HEADERS,
            )
        elif (_match := list(GITHUB_GIST_RE.finditer(argument))):
            _match = _match[0].groupdict()
            revision = _match["revision"]
            gist_json = await _fetch_response(
                f"https://api.github.com/gists/{_match['gist_id']}{f'/{revision}' if revision != '' else ''}",
                response_format="json",
                headers=GITHUB_HEADERS,
            )
            if len(gist_json["files"]) == 1 and _match["file_path"] is None:
                file_path = list(gist_json["files"])[0].lower().replace(".", "-")
            for gist_file in gist_json["files"]:
                if file_path == gist_file.lower().replace(".", "-"):
                    argument = await _fetch_response(
                        gist_json["files"][gist_file]["raw_url"],
                        "text",
                        headers=GITHUB_HEADERS,
                    )
        elif (_match := list(PASTEBIN_RE.finditer(argument))):
            _match = _match[0].groupdict()
            argument = await _fetch_response(
                f"https://pastebin.com/raw/{_match['paste_id']}", response_format="text"
            )
        elif (_match := list(HASTEBIN_RE.finditer(argument))) and (token := (await ctx.bot.get_shared_api_tokens(service_name="hastebin")).get("token")) is not None:
            _match = _match[0].groupdict()
            argument = await _fetch_response(
                f"https://hastebin.com/raw/{_match['paste_id']}",
                response_format="text",
                headers={"Authentification": f"Bearer {token}"},
            )
        else:
            raise commands.BadArgument(f"`{argument}` is not a valid code GitHub/Gist/Pastebin/Hastebin link.")
        return await super().convert(ctx, argument=argument)


class PastebinConverter(PastebinMixin, StringToEmbed):
    pass


class PastebinListConverter(PastebinMixin, ListStringToEmbed):
    pass


class StrConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> str:
        return argument

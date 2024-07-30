from redbot.core import commands  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import sys
from dataclasses import dataclass

from redbot.core.utils.chat_formatting import box, pagify


@dataclass(frozen=True)
class RTFSItem:
    name: str
    url: str


class RTFSResults:
    def __init__(
        self, source, results: typing.List[typing.Tuple[str, str, str]]
    ) -> None:  # set[str, str, bool]
        self.source = source
        self.results: typing.List[RTFSItem] = results

    def __list__(self) -> typing.List[RTFSItem]:
        return self.results

    def to_embeds(
        self, embed_color: discord.Color = discord.Color.green()
    ) -> typing.List[discord.Embed]:
        description = "\n".join(
            f"**•** [**`{name}`**]({url})" for name, _, url, __ in self.results
        )
        pages = list(pagify(description, page_length=4000, delims="\n"))  # delims="\n• "
        embed = discord.Embed(color=embed_color)
        embed.set_author(
            name=f"{self.source.name} Documentation",
            icon_url=self.source.icon_url,
        )
        # query_time = format_timespan(self.query_time)
        # embed.set_footer(text=f"Fetched in {query_time}.")
        embeds = []
        for page in pages:
            e = embed.copy()
            e.description = page
            embeds.append(e)
        return embeds


class SearchResults:
    def __init__(
        self, source, results: typing.List[typing.Tuple[str, str, str]], query_time: int
    ) -> None:  # set[str, str, bool]
        self.source = source
        self.results: typing.List[typing.Tuple[str, str, str]] = results
        self.query_time = query_time

    def __list__(self) -> typing.Set:
        return self.results

    def to_embeds(
        self, embed_color: discord.Color = discord.Color.green()
    ) -> typing.List[discord.Embed]:
        description = "\n".join(
            f"**•** [**`{name}`**]({url})" for name, _, url, __ in self.results
        )
        pages = list(pagify(description, page_length=4000, delims="\n"))  # delims="\n• "
        embed = discord.Embed(color=embed_color)
        embed.set_author(
            name=f"{self.source.display_name} Documentation",
            icon_url=self.source.icon_url,
        )
        # query_time = format_timespan(self.query_time)
        # embed.set_footer(text=f"Fetched in {query_time}.")
        embeds = []
        for page in pages:
            e = embed.copy()
            e.description = page
            embeds.append(e)
        return embeds


class Parameters(typing.Dict):
    def to_text(self) -> str:
        def format_parameter(name: str, description: str):
            formatted_parameter = f"• {name} – {description}"
            return formatted_parameter

        return "\n".join(
            [format_parameter(name, description) for name, description in self.items()]
        )

    def to_embeds(
        self, embed_color: discord.Color = discord.Color.green()
    ) -> typing.List[discord.Embed]:
        description = self.to_text()
        embeds = []
        pages = list(pagify(description, page_length=4000, delims=["\n• "]))
        if len(pages) == 1:
            embed = discord.Embed(
                title="Parameters:",
                description=description,
                color=embed_color,
            )
            embeds.append(embed)
        else:
            embeds = []
            for i, page in enumerate(pages, start=1):
                embed = discord.Embed(
                    title=f"Parameters {i}:",
                    description=page,
                    color=embed_color,
                )
                embeds.append(embed)
        return embeds


class Examples(typing.List):
    def to_embeds(
        self,
        ctx: typing.Optional[commands.Context] = None,
        embed_color: discord.Color = discord.Color.green(),
    ) -> typing.List[discord.Embed]:
        embeds = []
        for i, example in enumerate(self, start=1):
            if ctx is not None:
                example = (
                    example.replace("USER_ID", str(ctx.author.id))
                    .replace("MEMBER_ID", str(ctx.author.id))
                    .replace(
                        "GUILD_ID", str(ctx.guild.id) if ctx.guild is not None else '"{GUILD_ID}"'
                    )
                    .replace("CHANNEL_ID", str(ctx.channel.id))
                    .replace(
                        "ROLE_ID",
                        str(ctx.author.top_role)
                        if getattr(ctx.author, "top_role", None) is not None
                        else '"{ROLE_ID}"',
                    )
                    .replace("MESSAGE_ID", str(ctx.message.id))
                    .replace("BOT_ID", str(ctx.bot.user.id))
                    .replace("APPLICATION_ID", str(ctx.bot.application_id))
                )
            embed = discord.Embed(
                title=f"Example {i}:"
                if len(self) > 1 or True
                else "Example:",  # Always include the example index...
                description=(box(example, lang="py") if "```" not in example else example)[:4096],
                color=embed_color,
            )
            embeds.append(embed)
        return embeds


@dataclass(frozen=True)
class Attribute:
    name: str
    role: typing.Optional[str]
    url: str
    type: typing.Optional[str]
    description: str


@dataclass(frozen=True)
class Attributes:
    attributes: typing.Dict[str, Attribute]
    properties: typing.Dict[str, Attribute]
    methods: typing.Dict[str, Attribute]

    def __bool__(self) -> bool:
        return any(bool(getattr(self, key)) for key in self.__dataclass_fields__.keys())

    def to_embeds(
        self, embed_color: discord.Color = discord.Color.green()
    ) -> typing.List[discord.Embed]:
        def format_attribute(
            name: str,
            role: typing.Optional[str],
            url: str,
            type: typing.Optional[str],
            description: typing.Optional[str],
            show_description: typing.Optional[bool] = True,
        ):
            formatted_attribute = "**•** "
            if role is not None:
                formatted_attribute += f"{role} "
            formatted_attribute += f"[**{name}**]({url})" + (f" ({type})" if type else "")
            if description is not None and show_description:
                formatted_attribute += f"\n> {description}"
            return formatted_attribute

        embeds = []
        for name in self.__dataclass_fields__.keys():
            attributes = getattr(self, name)
            if not attributes:
                continue
            formatted_attributes = []
            for attribute in attributes:
                formatted_attributes.append(
                    format_attribute(
                        name=attribute,
                        role=attributes[attribute].role,
                        url=attributes[attribute].url,
                        type=attributes[attribute].type,
                        description=attributes[attribute].description,
                    )
                )
            description = "\n".join(formatted_attributes)
            pages = list(pagify(description, page_length=4000, delims=["\n• "]))
            if len(pages) == 1:
                embed = discord.Embed(
                    title=f"{name.title()}:",
                    description=description,
                    color=embed_color,
                )
                embeds.append(embed)
            else:
                for i, page in enumerate(pages, start=1):
                    embed = discord.Embed(
                        title=f"{name.title()} {i}:",
                        description=page,
                        color=embed_color,
                    )
                    embeds.append(embed)
        return embeds


@dataclass(frozen=True)
class Documentation:
    source: typing.Any
    name: str
    signature: str
    description: str
    if sys.version_info >= (3, 11):
        parameters: typing.Union[Parameters[str, str], str]
        examples: Examples[str]
    else:
        parameters: typing.Any
        examples: Examples
    url: str
    fields: typing.Dict[str, str]
    attributes: Attributes

    def to_json(self) -> typing.Dict[str, typing.Any]:
        return {
            v: getattr(self, v)
            for v in dir(self)
            if not v.startswith("_") and v != "to_json" and v != "to_embed"
        }

    def to_embed(self, embed_color: discord.Color = discord.Color.green()) -> discord.Embed:
        description = (
            f"{box(self.signature, lang='py' if self.source.name != 'git' else 'ini')}\n"
            if self.signature
            else ""
        ) + f"{self.description}".strip()
        embed = discord.Embed(
            title=discord.utils.escape_markdown(self.name),
            url=self.url if self.url.startswith("http") else None,
            description=list(pagify(description, page_length=4000))[0]
            if description
            else "No description.",
            color=embed_color,
        )
        embed.set_author(
            name=f"{self.source.display_name} Documentation",
            icon_url=self.source.icon_url,
        )
        fields = {}
        if self.parameters:
            if isinstance(self.parameters, str):
                parameters = self.parameters
            else:
                parameters = self.parameters.to_text()
            fields["Parameters"] = parameters
        fields.update(**self.fields)
        field_limit = 1024
        for name, value in fields.items():
            if len(value) > field_limit:
                if "-----" not in value:
                    value = list(pagify(value, page_length=field_limit, shorten_by=6))[0] + "\n..."
                else:
                    value = (
                        box(
                            list(pagify(value, page_length=field_limit, shorten_by=16))[0],
                            lang="py",
                        )
                        + "\n..."
                    )
            embed.add_field(name=f"{name}:", value=value, inline=False)
        return embed

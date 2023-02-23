import discord  # isort:skip
import typing  # isort:skip

from dataclasses import dataclass

from humanfriendly import format_timespan
from redbot.core.utils.chat_formatting import box, pagify


@dataclass(frozen=True)
class RTFSItem:
    name: str
    url: str


class RTFSResults:
    def __init__(self, source, results: typing.Set) -> None:  # set[str, str, bool]
        self.source = source
        self.results: typing.List[RTFSItem] = results

    def __list__(self) -> typing.List[RTFSItem]:
        return self.results

    def to_embeds(self) -> typing.List[discord.Embed]:
        description = "\n".join(
            f"• [`{name}`]({url})" for name, _, url, _ in self.results
        )
        embeds = []
        pages = list(pagify(description, page_length=4000, delims="\n• "))
        if len(pages) == 1:
            embed = discord.Embed(description=description, color=discord.Color.green())
            embed.set_author(
                name=f"{self.source.name} Documentation",
                icon_url=self.source.icon_url,
            )
            embeds.append(embed)
        else:
            for i, page in enumerate(pages, start=1):
                embed = discord.Embed(description=page, color=discord.Color.green())
                embed.set_author(
                    name=f"{self.source.name} Documentation",
                    icon_url=self.source.icon_url,
                )
                embeds.append(embed)
        return embeds


class SearchResults:
    def __init__(self, source, results: typing.Set, query_time: int) -> None:  # set[str, str, bool]
        self.source = source
        self.results: typing.List[typing.Tuple[str, str, str]] = results
        self.query_time = query_time

    def __list__(self) -> typing.Set:
        return self.results

    def to_embeds(self) -> typing.List[discord.Embed]:
        description = "\n".join(
            f"• [`{name}`]({url})" for name, _, url, _ in self.results
        )
        embeds = []
        pages = list(pagify(description, page_length=4000, delims="\n• "))
        if len(pages) == 1:
            embed = discord.Embed(description=description, color=discord.Color.green())
            embed.set_author(
                name=f"{self.source.name} Documentation",
                icon_url=self.source.icon_url,
            )
            query_time = format_timespan(self.query_time)
            embed.set_footer(text=f"Fetched in {query_time}.")
            embeds.append(embed)
        else:
            for i, page in enumerate(pages, start=1):
                embed = discord.Embed(description=page, color=discord.Color.green())
                embed.set_author(
                    name=f"{self.source.name} Documentation",
                    icon_url=self.source.icon_url,
                )
                query_time = format_timespan(self.query_time)
                embed.set_footer(text=f"Fetched in {query_time}.")
                embeds.append(embed)
        return embeds


# @dataclass(frozen=True)
# class Parameter:
#     name: str
#     type: typing.Optional[str]
#     description: str


class Parameters(typing.Dict):

    def to_text(self) -> str:
        def format_parameter(name: str, description: str):
            formatted_parameter = f"• {name} – {description}"
            return formatted_parameter
        return "\n".join([format_parameter(name, description) for name, description in self.items()])

    def to_embeds(self) -> typing.List[discord.Embed]:
        description = self.to_text()
        embeds = []
        pages = list(pagify(description, page_length=4000, delims=["\n• "]))
        if len(pages) == 1:
            embed = discord.Embed(
                    title="Parameters:",
                    description=description,
                    color=discord.Color.green(),
            )
            embeds.append(embed)
        else:
            embeds = []
            for i, page in enumerate(pages, start=1):
                embed = discord.Embed(
                        title=f"Parameters {i}:",
                        description=page,
                        color=discord.Color.green(),
                )
                embeds.append(embed)
        return embeds


class Examples(typing.List):

    def to_embeds(self) -> typing.List[discord.Embed]:
        embeds = []
        for i, example in enumerate(self, start=1):
            embed = discord.Embed(
                title=f"Example {i}:" if len(self) > 1 else "Example:",
                description=box(example, lang="py"),
                color=discord.Color.green(),
            )
            embeds.append(embed)
        return embeds


@dataclass(frozen=True)
class Attribute:
    name: str
    role: str
    url: str
    description: str


@dataclass(frozen=True)
class Attributes:
    attributes: typing.Dict[str, Attribute]
    properties: typing.Dict[str, Attribute]
    methods: typing.Dict[str, Attribute]

    def __bool__(self) -> bool:
        return all(bool(attributes) for attributes in self.__dataclass_fields__.values())

    def to_embeds(self) -> typing.List[discord.Embed]:
        def format_attribute(name: str, role: str, url: str, description: str, show_description: typing.Optional[bool] = True):
            formatted_attribute = "• "
            if role is not None:
                formatted_attribute += f"{role} "
            formatted_attribute += f"[{name}]({url})"
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
                formatted_attributes.append(format_attribute(attribute, attributes[attribute].role, attributes[attribute].url, attributes[attribute].description))
            description = "\n".join(formatted_attributes)
            pages = list(pagify(description, page_length=4000, delims=["\n• "]))
            if len(pages) == 1:
                embed = discord.Embed(
                    title=name.title() + ":",
                    description=description,
                    color=discord.Color.green(),
                )
                embeds.append(embed)
            else:
                for i, page in enumerate(pages, start=1):
                    embed = discord.Embed(
                        title=name.title() + f" {i}:",
                        description=page,
                        color=discord.Color.green(),
                    )
                    embeds.append(embed)
        return embeds


@dataclass(frozen=True)
class Documentation:
    source: typing.Any
    name: str
    full_name: str
    description: str
    parameters: Parameters[str, str]
    examples: Examples[str]
    url: str
    fields: typing.Dict[str, str]
    attributes: Attributes

    def to_json(self) -> typing.Dict[str, typing.Any]:
        return {
            v: getattr(self, v)
            for v in dir(self)
            if not v.startswith("_") and v != "to_json" and v != "to_embed"
        }

    def to_embed(self) -> discord.Embed:
        description = f"```py\n{self.full_name}\n```\n{self.description}".strip()
        embed = discord.Embed(
            title=self.name, url=self.url, description=list(pagify(description, page_length=4000))[0], color=discord.Color.green()
        )
        embed.set_author(
            name=f"{self.source.name} Documentation",
            icon_url=self.source.icon_url,
        )
        fields = {}
        if self.parameters:
            parameters = self.parameters.to_text()
            fields["Parameters"] = parameters
        fields.update(**self.fields)
        field_limit = 1024
        for name, value in fields.items():
            if len(value) > field_limit:
                value = list(pagify(value, page_length=field_limit - 6))[0] + "\n..."
            embed.add_field(name=name, value=value, inline=False)
        return embed

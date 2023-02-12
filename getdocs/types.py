import discord  # isort:skip
import typing  # isort:skip

from dataclasses import dataclass
from humanfriendly import format_timespan


@dataclass(frozen=True)
class RTFSItem:
    name: str
    url: str


class RTFSResults:
    def __init__(self, source, results: set[str, str, bool]) -> None:
        self.source = source
        self.results: typing.List[RTFSItem] = results

    def __list__(self):
        return self.results

    def to_embed(self):
        description = "\n".join(f"[`{result.name}`]({result.url})" for result in self.results[:10])
        embed = discord.Embed(description=description[:5000 - 1], color=discord.Color.green())
        embed.set_author(
            name=f"{self.source.name} Documentation",
            icon_url=self.source.icon_url,
        )
        return embed


class SearchResults:
    def __init__(self, source, results: set[str, str, bool], query_time: int) -> None:
        self.source = source
        self.results = results
        self.query_time = query_time

    def __list__(self):
        return self.results

    def to_embed(self):
        description = "\n".join(
            f"[`{name}`]({url})" for name, _, url, _ in self.results[:10]
        )
        embed = discord.Embed(description=description[:5000 - 1], color=discord.Color.green())
        embed.set_author(
            name=f"{self.source.name} Documentation",
            icon_url=self.source.icon_url,
        )
        query_time = format_timespan(self.query_time)
        embed.set_footer(text=f"Fetched in {query_time}.")
        return embed


@dataclass(frozen=True)
class Attribute:
    name: str
    url: str


@dataclass(frozen=True)
class Documentation:
    source: typing.Any
    name: str
    full_name: str
    description: str
    examples: typing.List[str]
    url: str
    fields: typing.Dict[str, typing.List[str]]
    attributes: typing.List[Attribute]

    def to_json(self):
        return {
            v: getattr(self, v)
            for v in dir(self)
            if not v.startswith("_") and v != "to_json" and v != "to_embed"
        }

    def to_embed(self):
        description = f"```py\n{self.full_name}\n```\n{self.description}".strip()
        embed = discord.Embed(
            title=self.name, url=self.url, description=description[:5000 - 1], color=discord.Color.green()
        )
        embed.set_author(
            name=f"Documentation for {self.source.name}",
            icon_url=self.source.icon_url,
        )
        field_limit = 1024
        for name, field in self.fields.items():
            if len(field) > field_limit:
                field = field[: field_limit - 3] + "..."
            embed.add_field(name=name, value=field, inline=False)
        return embed

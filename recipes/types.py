import discord  # isort:skip
import typing  # isort:skip

from dataclasses import dataclass

from redbot.core.utils.chat_formatting import pagify


class SearchResults:
    def __init__(
        self, query: str, url: str, results: typing.Dict[str, str]
    ) -> None:  # set[str, str, bool]
        self.query: str = query
        self.url: str = url
        self.results: typing.Dict[str, str] = results

    def __list__(self) -> typing.Set:
        return self.results

    def to_embeds(
        self, embed_color: typing.Optional[discord.Color] = discord.Color.green()
    ) -> typing.List[discord.Embed]:
        description = "\n".join(
            f"**•** [**`{name}`**]({url})" for name, url in self.results.items()
        )
        embeds = []
        pages = list(pagify(description, page_length=4000, delims="\n"))  # delims="\n• "
        embed: discord.Embed = discord.Embed(
            title=f'Results for "{self.query}" query', url=self.url, color=embed_color
        )
        embed.set_footer(text="Fetched from Food52.")
        for page in pages:
            e = embed.copy()
            e.description = page
            embeds.append(e)
        return embeds


@dataclass(frozen=True)
class Recipe:
    url: str
    name: str
    category: str
    cuisine: str
    author: typing.Dict[str, str]
    description: str
    _yield: str
    preparation_time: str
    cook_time: str
    rating: typing.Optional[typing.Dict[str, typing.Union[float, int]]]
    images_urls: typing.List[str]
    ingredients: typing.List[str]
    instructions: typing.Dict[str, typing.List[str]]

    def to_json(self) -> typing.Dict[str, typing.Any]:
        return {
            v: getattr(self, v)
            for v in dir(self)
            if not v.startswith("_") and v != "to_json" and v != "to_embed"
        }

    def to_embeds(
        self, embed_color: typing.Optional[discord.Color] = discord.Color.green()
    ) -> typing.List[discord.Embed]:
        embed: discord.Embed = discord.Embed(title=self.name, url=self.url, color=embed_color)
        embed.set_author(
            name=self.author["name"],
            url=self.author["url"],
            icon_url="https://forum.mtasa.com/uploads/monthly_2016_10/Anonyme.png.4060431ce866962fa496657f752d5613.png",
        )
        embed.description = (
            f"{self.description[:1250]}\n..." if len(self.description) > 1250 else self.description
        )
        embed.add_field(name="Yield:", value=self._yield, inline=True)
        if self.rating:
            embed.add_field(
                name="Note:",
                value=f"{self.rating['value']}/5 with {self.rating['count']} votes",
                inline=True,
            )
        ingredients = "\n".join([f"**•** {ingredient}" for ingredient in self.ingredients])
        embed.add_field(
            name="Ingredients:",
            value=f"{ingredients[:1020]}\n..." if len(ingredients) > 1024 else ingredients,
            inline=False,
        )
        if self.preparation_time:
            embed.add_field(name="Preparation Time:", value=self.preparation_time, inline=True)
        if self.cook_time:
            embed.add_field(name="Cook Time:", value=self.cook_time, inline=True)
        if len(self.images_urls) == 0:
            embeds = [embed]
        else:
            embed.set_thumbnail(url=self.images_urls[0])
            embeds = []
            for image_url in self.images_urls:
                e = embed.copy()
                e.set_image(url=image_url)
                embeds.append(e)
        return embeds

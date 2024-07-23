from AAA3A_utils import Cog, Menu  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.bot import Red  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import json
import re
from html import unescape
from urllib.parse import quote_plus, unquote_plus

import aiohttp
from bs4 import BeautifulSoup
from redbot.core.utils.chat_formatting import box, humanize_list

from .types import Recipe, SearchResults
from .view import RecipesView

# Credits:
# General repo credits.
# Thanks to Max for the cog idea!

_: Translator = Translator("Recipes", __file__)


def unquote(string: str):
    return unescape(unquote_plus(string))


@cog_i18n(_)
class Recipes(Cog):
    """A cog to search and show a cooking recipe!"""

    def __init__(self, bot: Red) -> None:
        super().__init__(bot=bot)

        self._session: aiohttp.ClientSession = None
        self.cache: typing.Dict[str, Recipe] = {}

    async def cog_load(self) -> None:
        await super().cog_load()
        self._session: aiohttp.ClientSession = aiohttp.ClientSession()

    async def cog_unload(self) -> None:
        await self._session.close()
        await super().cog_unload()

    async def get_query_results(
        self, query: str, limit: int = 15
    ) -> typing.Tuple[str, SearchResults]:
        url = f"https://food52.com/recipes/search?q={quote_plus(query)}"
        async with self._session.get(url) as r:
            content = await r.text()
        bs4 = BeautifulSoup(content, "lxml")
        content = bs4.find("script", type="application/ld+json").text.strip()
        json_content = json.loads(content)
        return url, SearchResults(
            query=query,
            url=url,
            results={
                " ".join(recipe["url"].split("/")[-1].split("-")[1:]).capitalize(): recipe["url"]
                for recipe in sorted(json_content["itemListElement"], key=lambda x: x["position"])[
                    :limit
                ]
            },
        )

    async def get_recipe(self, url: str) -> Recipe:
        if url in self.cache:
            return self.cache[url]
        async with self._session.get(url) as r:
            content = await r.text()
        bs4 = BeautifulSoup(content, "lxml")
        content = (
            bs4.find("script", type="application/ld+json")
            .text.strip()
            .replace("\r", "")
            .replace("”", "`")
        )
        pattern = r'(?<="description": ")[^"]*?(?="\,)'
        if match := re.search(pattern, content):
            description = match[0].replace("\n", "BREAK_LINE")
            content = re.sub(pattern, description, content)
        json_content = json.loads(content)
        recipe = Recipe(
            url=url,
            name=unquote(json_content["name"]),
            category=unquote(json_content["recipeCategory"]),
            cuisine=unquote(json_content["recipeCuisine"]),
            author={
                "name": unquote(json_content["author"]["name"]),
                "url": json_content["author"]["url"],
            },
            description=unquote(json_content["description"].replace("BREAK_LINE", "\n")),
            _yield=unquote(json_content["recipeYield"].strip()),
            preparation_time=json_content["prepTime"][2:].lower(),
            cook_time=json_content["cookTime"][2:].lower(),
            rating=(
                {
                    "value": round(float(json_content["aggregateRating"]["ratingValue"]), 1),
                    "count": int(json_content["aggregateRating"]["ratingCount"]),
                }
            )
            if "aggregateRating" in json_content
            else None,
            images_urls=json_content["image"],
            ingredients=[
                unquote(ingredient).lstrip("<em>").rstrip("</em>")
                for ingredient in json_content["recipeIngredient"]
            ],
            instructions=(
                {
                    unquote(section["name"].title()): [
                        unquote(instruction["text"]) for instruction in section["itemListElement"]
                    ]
                    for section in json_content["recipeInstructions"]
                }
            )
            if not json_content["recipeInstructions"]
            or isinstance(json_content["recipeInstructions"][0], typing.Dict)
            else (
                {
                    "Main section": [
                        unquote(instruction["text"])
                        for instruction in json_content["recipeInstructions"][0]
                    ]
                }
            ),
        )
        self.cache[url] = recipe
        return recipe

    @commands.bot_has_permissions(embed_links=True)
    @commands.hybrid_command()
    async def recipe(self, ctx: commands.Context, *, query: str) -> None:
        """Show a recipe of Food52, from a query."""
        __, results = await self.get_query_results(query, limit=1)
        if not results.results:
            raise commands.UserFeedbackCheckFailure(_("No recipe found."))
        url = list(results.results.values())[0]
        try:
            recipe = await self.get_recipe(url)
        except json.JSONDecodeError as e:
            raise commands.UserFeedbackCheckFailure(
                _("Error in parsing the response.\n{error}").format(error=box(str(e), lang="py"))
            )
        await RecipesView(cog=self, recipe=recipe).start(ctx)

    @commands.bot_has_permissions(embed_links=True)
    @commands.hybrid_command(aliases=["searchrecipe"])
    async def searchrecipes(
        self, ctx: commands.Context, limit: typing.Optional[int] = 15, *, query: str
    ) -> None:
        """Search cooking recipes on Food52, from a query."""
        url, results = await self.get_query_results(query, limit=limit)
        if not results.results:
            raise commands.UserFeedbackCheckFailure(_("No recipe found."))
        embeds = results.to_embeds(embed_color=await ctx.embed_color())
        menu = Menu(pages=embeds)
        menu.extra_items.append(
            discord.ui.Button(
                label=_("View results on Food52"),
                url=url,
                style=discord.ButtonStyle.url,
            )
        )
        await menu.start(ctx)

    @commands.Cog.listener()
    async def on_assistant_cog_add(
        self, assistant_cog: typing.Optional[commands.Cog] = None
    ) -> None:  # Vert's Assistant integration/third party.
        if assistant_cog is None:
            return get_recipe_for_assistant
        schema = {
            "name": "get_recipe_for_assistant",
            "description": "Get a recipe from the website Food52, from a query.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The name of the recipe to search.",
                    },
                },
                "required": ["query"],
            },
        }
        await assistant_cog.register_function(cog_name=self.qualified_name, schema=schema)

    async def get_recipe_for_assistant(self, query: str, *args, **kwargs):
        __, results = await self.get_query_results(query, limit=1)
        if not results.results:
            return "No recipe found."
        url = list(results.results.values())[0]
        try:
            recipe = await self.get_recipe(url)
        except json.JSONDecodeError:
            return "Error in parsing the response."
        data = {
            "Name": recipe.name,
            "Category": recipe.category,
            "Cuisine": recipe.cuisine,
            "Description": recipe.description,
            "Yield": recipe._yield,
            "Preparation time": recipe.preparation_time,
            "Cook time": recipe.cook_time,
            "Ingredients": humanize_list(recipe.ingredients),
            "Instructions": "\n"
            + "\n\n".join(
                [
                    f"\n\n• {section}\n"
                    "\n".join(
                        [
                            f"    **{n}.** {instruction}"
                            for n, instruction in enumerate(recipe.instructions[section], start=1)
                        ]
                    )
                    for section in recipe.instructions
                ]
            ),
        }
        return [f"{key}: {value}\n" for key, value in data.items() if value is not None]

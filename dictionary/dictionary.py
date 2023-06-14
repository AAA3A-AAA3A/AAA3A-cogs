from AAA3A_utils import Cog, CogsUtils  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.bot import Red  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
import typing  # isort:skip

from urllib.parse import quote_plus

import aiohttp

from .types import Word
from .view import DictionaryView

# Credits:
# General repo credits.

_ = Translator("Dictionary", __file__)


@cog_i18n(_)
class Dictionary(Cog):
    """A cog to search an english term/word in the dictionary! Synonyms, antonyms, phonetics (with audio)..."""

    def __init__(self, bot: Red) -> None:
        self.bot: Red = bot

        self._session: aiohttp.ClientSession = None
        self.cache: typing.Dict[str, Word] = {}

        self.cogsutils: CogsUtils = CogsUtils(cog=self)

    async def cog_load(self) -> None:
        self._session: aiohttp.ClientSession = aiohttp.ClientSession()

    async def cog_unload(self) -> None:
        await self._session.close()
        await super().cog_unload()

    async def get_word(self, query: str) -> Word:
        if query in self.cache:
            return self.cache[query]
        url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{quote_plus(query)}"
        async with self._session.get(url) as r:
            json_content = await r.json()
        if "title" in json_content:
            if json_content["title"] == "No Definitions Found":
                return None
            else:
                raise commands.UserFeedbackCheckFailure(json_content["title"])
        json_content = json_content[0]
        word = Word(
            url=url,
            source_url=json_content["sourceUrls"][0] if json_content.get("sourceUrls") else None,
            word=json_content["word"],
            phonetics=[
                {
                    "text": phonetic.get("text"),
                    "audio_url": phonetic["audio"],
                    "audio_file": None,
                    "source_url": phonetic.get("sourceUrl"),
                }
                for phonetic in json_content["phonetics"]
            ],
            meanings={
                meaning["partOfSpeech"]: [
                    {
                        "definition": definition["definition"],
                        "synonyms": definition["synonyms"],
                        "antonyms": definition["antonyms"],
                        "example": definition.get("example"),
                    }
                    for definition in meaning["definitions"]
                ]
                for meaning in json_content["meanings"]
            },
        )
        self.cache[query] = word
        return word

    @commands.hybrid_command()
    @commands.bot_has_permissions(embed_links=True)
    async def dictionary(self, ctx: commands.Context, query: str) -> None:
        """Search a word in the english dictionnary."""
        word = await self.get_word(query)
        if word is None:
            raise commands.UserFeedbackCheckFailure(_("Word not found in English dictionary."))
        await DictionaryView(cog=self, word=word).start(ctx)

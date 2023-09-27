import discord  # isort:skip
import typing  # isort:skip

from dataclasses import dataclass

from redbot.core.utils.chat_formatting import humanize_list


@dataclass(frozen=True)
class Word:
    url: str
    source_url: str
    word: str
    phonetics: typing.List[typing.Dict[str, typing.Optional[str]]]
    meanings: typing.Dict[
        str,
        typing.Dict[
            str,
            typing.List[typing.Dict[str, typing.Optional[typing.Union[str, typing.List[str]]]]],
        ],
    ]

    def to_json(self) -> typing.Dict[str, typing.Any]:
        return {
            v: getattr(self, v)
            for v in dir(self)
            if not v.startswith("_") and v != "to_json" and v != "to_embed"
        }

    def to_embed(
        self, embed_color: discord.Color = discord.Color.green()
    ) -> discord.Embed:
        embed: discord.Embed = discord.Embed(
            title=f'Dictionary - "{self.word}"', url=self.source_url, color=embed_color
        )
        for meaning in self.meanings:
            if len(embed.fields) >= 10:
                break
            value = "\n\n".join(
                [
                    (f"**{n}.** " if len(self.meanings[meaning]) > 1 else "")
                    + f"{definition['definition']}"
                    + (
                        f"\n- Synonyms: {humanize_list(definition['synonyms'])}"
                        if definition["synonyms"]
                        else ""
                    )
                    + (
                        f"\n- Antonyms: {humanize_list(definition['antonyms'])}"
                        if definition["antonyms"]
                        else ""
                    )
                    + (f"\n> Example: {definition['example']}" if definition["example"] else "")
                    for n, definition in enumerate(self.meanings[meaning], start=1)
                ]
            )
            embed.add_field(
                name=meaning.capitalize(),
                value=value if len(value) <= 1024 else f"{value[:1020]}\n...",
                inline=False,
            )
        return embed

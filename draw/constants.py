import discord

from .color import Color


def base_colors_options() -> list[discord.SelectOption]:
    return [
        discord.SelectOption(label="Red", emoji="🟥", value="🟥"),
        discord.SelectOption(label="Orange", emoji="🟧", value="🟧"),
        discord.SelectOption(label="Yellow", emoji="🟨", value="🟨"),
        discord.SelectOption(label="Green", emoji="🟩", value="🟩"),
        discord.SelectOption(label="Blue", emoji="🟦", value="🟦"),
        discord.SelectOption(label="Purple", emoji="🟪", value="🟪"),
        discord.SelectOption(label="Brown", emoji="🟫", value="🟫"),
        discord.SelectOption(label="Black", emoji="⬛", value="⬛"),
        discord.SelectOption(label="White", emoji="⬜", value="⬜"),
        discord.SelectOption(label="Transparent", emoji=None, value="transparent"),
    ]


MAIN_COLORS_DICT: dict[str, Color] = {
    "🟥": Color((255, 0, 0, 255)),
    "🟧": Color((255, 130, 0, 255)),
    "🟨": Color((255, 255, 0, 255)),
    "🟩": Color((0, 255, 0, 255)),
    "🟦": Color((0, 190, 255, 255)),
    "🟪": Color((210, 110, 255, 255)),
    "🟫": Color((200, 100, 80, 255)),
    "⬛": Color((0, 0, 0, 255)),
    "⬜": Color((255, 255, 255, 255)),
}
MAIN_COLORS: list[str] = list(MAIN_COLORS_DICT.keys()) + ["transparent"]

MIN_HEIGHT_OR_WIDTH: int = 5
MAX_HEIGHT_OR_WIDTH: int = 17


def base_height_or_width_select_options(
    prefix: str | None = "",
) -> list[discord.SelectOption]:
    return [
        discord.SelectOption(label=f"{f'{prefix} = ' if prefix else prefix}{n}", value=n)
        for n in range(MIN_HEIGHT_OR_WIDTH, MAX_HEIGHT_OR_WIDTH + 1)
    ]


ROW_ICONS_DICT: dict[str, int] = {
    "🇦": 799628816846815233,
    "🇧": 799628882713509891,
    "🇨": 799620822716383242,
    "🇩": 799621070319255572,
    "🇪": 799621103030894632,
    "🇫": 799621133174571008,
    "🇬": 799621170450137098,
    "🇭": 799621201621811221,
    "🇮": 799621235226050561,
    "🇯": 799621266842583091,
    "🇰": 799621296408887357,
    "🇱": 799621320408301638,
    "🇲": 799621344740114473,
    "🇳": 799621367297343488,
    "🇴": 799628923260370945,
    "🇵": 799621387219369985,
    "🇶": 799621417049260042,
}
ROW_ICONS = list(ROW_ICONS_DICT.keys())
COLUMN_ICONS_DICT: dict[str | int, int] = {
    "0️⃣": 1000010892500537437,
    "1️⃣": 1000010893981143040,
    "2️⃣": 1000010895331692555,
    "3️⃣": 1000010896946499614,
    "4️⃣": 1000010898213195937,
    "5️⃣": 1000010899714740224,
    "6️⃣": 1000010901744791653,
    "7️⃣": 1000010902726262857,
    "8️⃣": 1000010904240402462,
    "9️⃣": 1000010905276403773,
    "🔟": 1000011148537626624,
    1032564324281098240: 1000011153226874930,
    1032564339946823681: 1000011154262851634,
    1032564356380098630: 1000011155391131708,
    1032564734609862696: 1000011156787834970,
    1032564783850983464: 1000011158348120125,
    1032564935412174868: 1000011159623192616,
}
COLUMN_ICONS = list(COLUMN_ICONS_DICT.keys())

LETTER_TO_NUMBER: dict[str, int] = {
    "A": 0,
    "B": 1,
    "C": 2,
    "D": 3,
    "E": 4,
    "F": 5,
    "G": 6,
    "H": 7,
    "I": 8,
    "J": 9,
    "K": 10,
    "L": 11,
    "M": 12,
    "N": 13,
    "O": 14,
    "P": 15,
    "Q": 16,
    "R": 17,
    "S": 18,
    "T": 19,
    "U": 20,
    "V": 21,
    "W": 22,
    "X": 23,
    "Y": 24,
    "Z": 25,
}
ALPHABETS: tuple[str] = tuple(LETTER_TO_NUMBER.keys())
NUMBERS: tuple[int] = tuple(LETTER_TO_NUMBER.values())

u200b: str = "\u200b"
PADDING: str = f" {u200b}" * 6
LB: str = "\n"

DEFAULT_CACHE: list[str | int] = (
    list(MAIN_COLORS_DICT.keys())
    + list(MAIN_COLORS_DICT.values())
    + ROW_ICONS
    + COLUMN_ICONS
    + list(ROW_ICONS_DICT.values())
    + list(COLUMN_ICONS_DICT.values())
)

IMAGE_EXTENSION = "PNG"

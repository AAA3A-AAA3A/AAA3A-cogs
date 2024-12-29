import copy
import datetime
from dataclasses import _is_dataclass_instance, dataclass, fields

import pycountry
from mimesis.enums import Gender
from mimesis.locales import Locale
from redbot.core.i18n import Translator
from redbot.core.utils.chat_formatting import humanize_list, inline

import discord  # isort:skip
import typing  # isort:skip


_: Translator = Translator("FakeIdentities", __file__)


LOCALES: typing.Dict[Locale, typing.Any] = dict(
    sorted(
        {
            locale: country
            for locale in Locale
            if (
                locale != Locale.DEFAULT
                and "-" not in locale.value
                and (country := pycountry.countries.get(alpha_2=locale.value.upper())) is not None
            )
        }.items(),
        key=lambda x: x[1].name,
    )
)


def get_pages() -> typing.Dict[str, typing.Dict[str, typing.Any]]:
    return {
        "main": {
            "emoji": "🏠",
            "title": _("Main"),
            "elements": {
                "surname": "📛",
                "birth": "🎂",
                "communication": "☎️",
            },
        },
        "medical": {
            "emoji": "🩺",
            "title": _("Medical"),
            "elements": {
                "medical": "🩸",
            },
        },
        "studies_profession": {
            "emoji": "🎓",
            "title": _("Studies & Profession"),
            "elements": {
                "studies": "📚",
                "profession": "💼",
            },
        },
        "address_transport": {
            "emoji": "🏠",
            "title": _("Address & Transport"),
            "elements": {
                "address": "🏠",
                "transport": "🚗",
            },
        },
        "payment": {
            "emoji": "💳",
            "title": _("Payment"),
            "elements": {
                "payment": "💰",
            },
        },
        "login_devices": {
            "emoji": "🔒",
            "title": _("Login & Devices"),
            "elements": {
                "login": "🔑",
                "devices": "🖥️",
            },
        },
        "favorite": {
            "emoji": "❤️",
            "title": _("Favorite"),
            "elements": {
                "favorite": "❤️",
            },
        },
        "partner_and_children": {
            "emoji": "👩‍👧‍👦",
            "title": _("Woman & Children"),
            "elements": {
                "partner": "👩",
                "children": "👦",
            },
        },
    }


def _asdict_inner(obj, dict_factory=dict):
    if _is_dataclass_instance(obj):
        result = []
        for f in fields(obj):
            value = _asdict_inner(getattr(obj, f.name), dict_factory)
            result.append((f.name, value))
        return dict_factory(result)
    elif isinstance(obj, tuple) and hasattr(obj, "_fields"):
        return type(obj)(*[_asdict_inner(v, dict_factory) for v in obj])
    elif isinstance(obj, (list, tuple)):
        return type(obj)(_asdict_inner(v, dict_factory) for v in obj)
    elif isinstance(obj, dict):
        return type(obj)(
            (_asdict_inner(k, dict_factory), _asdict_inner(v, dict_factory))
            for k, v in obj.items()
        )
    elif isinstance(obj, datetime.date):
        return obj.isoformat()
    elif hasattr(obj, "value"):
        return obj.value
    else:
        return copy.deepcopy(obj)


@dataclass(frozen=True)
class FakeIdentity:
    gender: Gender
    nationality: Locale
    location: Locale
    seed: int

    name: "Name"
    thumbnail_url: str

    birth: "Birth"
    communication: "Communication"

    medical: "Medical"

    studies: "Studies"
    profession: "Profession"

    address: "Address"
    transport: "Transport"

    payment: "Payment"

    login: "Login"
    devices: "Devices"

    favorite: "Favorite"

    partner: typing.Optional["SecondaryIdentity"] = None
    children: typing.List["SecondaryIdentity"] = None

    def to_dict(self) -> typing.Dict[str, typing.Any]:
        return _asdict_inner(self)

    def to_embed(self, page: str = "main") -> discord.Embed:
        embed: discord.Embed = discord.Embed(
            title=f"{LOCALES[self.nationality].flag} {self.name.title} {self.name.first} {self.name.last} (Location: {LOCALES[self.location].flag})",
            color=(discord.Color.green() if self.gender is Gender.MALE else discord.Color.pink()),
        )
        embed.set_thumbnail(url=self.thumbnail_url)
        embed.set_footer(
            text=_("Seed: {seed}").format(seed=self.seed),
        )

        elements = get_pages()[page]["elements"]
        for element, emoji in elements.items():
            v = getattr(self, element) if element != "surname" else self.name.surname
            if not v:
                value = "N/A"
            elif hasattr(v, "to_string"):
                value = v.to_string()
            elif _is_dataclass_instance(v):
                value = []
                for f in fields(v):
                    _v = getattr(v, f.name)
                    if not _v:
                        _v = "N/A"
                    elif hasattr(_v, "to_string"):
                        _v = _v.to_string()
                    if element == "login" or "address" in f.name:
                        _v = inline(_v)
                    value.append(f"**{f.name.replace('_', ' ').title()}**: {_v}")
                value = "\n".join(value)
            elif isinstance(v, typing.List):
                value = humanize_list([_v.to_string() for _v in v])
            else:
                value = str(v)
            embed.add_field(
                name=f"{emoji} **{element.title()}**:",
                value=value,
                inline=False,
            )

        return embed


@dataclass(frozen=True)
class Name:
    title: typing.Optional[str]
    first: str
    last: str
    surname: typing.Optional[str]


@dataclass(frozen=True)
class Birth:
    date: str
    age: int


@dataclass(frozen=True)
class Communication:
    email: str
    phone: str
    cell: typing.Optional[str]


@dataclass(frozen=True)
class Medical:
    blood_type: str
    weight: str
    height: str


@dataclass(frozen=True)
class Studies:
    university: str
    academic_degree: str


@dataclass(frozen=True)
class Profession:
    occupation: str
    company: str


@dataclass(frozen=True)
class Address:
    street: "Street"
    city: str
    postal_code: str
    state: str
    country: str
    coordinates: "Coordinates"


@dataclass(frozen=True)
class Street:
    number: str
    name: str

    def to_string(self) -> str:
        return f"{self.number} {self.name}"


@dataclass(frozen=True)
class Coordinates:
    latitude: str
    longitude: str

    def to_string(self) -> str:
        return f"{self.latitude}, {self.longitude}"


@dataclass(frozen=True)
class Transport:
    car: str
    manufacturer: str
    vehicle_registration_code: str


@dataclass(frozen=True)
class Payment:
    bank: str
    credit_card: "CreditCard"
    paypal_account: str
    bitcoin_address: str
    ethereum_address: str


@dataclass(frozen=True)
class CreditCard:
    network: str
    number: str
    expiration_date: str
    cvv: str

    def to_string(self) -> str:
        return f"{self.network} `{self.number}` (`{self.expiration_date}`) - CVV `{self.cvv}`"


@dataclass(frozen=True)
class Login:
    uuid: str
    pin_code: str

    username: str
    password: str
    md5: str
    sha1: str
    sha256: str


@dataclass(frozen=True)
class Devices:
    computer: "Computer"
    phone: "Phone"


@dataclass(frozen=True)
class Computer:
    os: str
    manufacturer: str

    cpu: str
    cpu_codename: str
    cpu_frequency: str
    generation: str

    graphics: str

    ram_size: str
    ram_type: str

    resolution: str
    screen_size: str

    ssd_or_hdd: str

    mac_address: str
    ip_v4: str
    ip_v6: str

    def to_string(self) -> str:
        return _(
            "\n- OS: {os}\n- Manufacturer: {manufacturer}\n- CPU: {cpu} ({cpu_codename}) {cpu_frequency} ({generation})\n- Graphics: {graphics}\n- RAM: {ram_size} {ram_type}\n- Resolution: {resolution}\n- Screen Size: {screen_size}\n- Storage: {ssd_or_hdd}\n- MAC Address: `{mac_address}`\n- IP v4: `{ip_v4}`\n- IP v6: `{ip_v6}`"
        ).format(
            os=self.os,
            manufacturer=self.manufacturer,
            cpu=self.cpu,
            cpu_codename=self.cpu_codename,
            cpu_frequency=self.cpu_frequency,
            generation=self.generation,
            graphics=self.graphics,
            ram_size=self.ram_size,
            ram_type=self.ram_type,
            resolution=self.resolution,
            screen_size=self.screen_size,
            ssd_or_hdd=self.ssd_or_hdd,
            mac_address=self.mac_address,
            ip_v4=self.ip_v4,
            ip_v6=self.ip_v6,
        )


@dataclass(frozen=True)
class Phone:
    model: str
    ram_size: str

    mac_address: str
    ip_v4: str
    ip_v6: str

    def to_string(self) -> str:
        return _(
            "\n- Model: {model}\n- RAM: {ram_size}\n- MAC Address: `{mac_address}`\n- IP v4: `{ip_v4}`\n- IP v6: `{ip_v6}`"
        ).format(
            model=self.model,
            ram_size=self.ram_size,
            mac_address=self.mac_address,
            ip_v4=self.ip_v4,
            ip_v6=self.ip_v6,
        )


@dataclass(frozen=True)
class Favorite:
    political_views: str
    color: str
    emoji: str
    quote: str
    word: str
    food: "Food"


@dataclass(frozen=True)
class Food:
    dish: str
    vegetable: str
    fruit: str
    drink: str
    spices: str

    def to_string(self) -> str:
        return _(
            "\n- Dish: {dish}\n- Vegetable: {vegetable}\n- Fruit: {fruit}\n- Drink: {drink}\n- Spices: {spices}"
        ).format(
            dish=self.dish,
            vegetable=self.vegetable,
            fruit=self.fruit,
            drink=self.drink,
            spices=self.spices,
        )


@dataclass(frozen=True)
class SecondaryIdentity:
    name: Name
    birth: Birth

    def to_string(self) -> str:
        return (
            (f"{self.name.title} " if self.name.title is not None else "")
            + f"{self.name.first} {self.name.last} ({self.birth.age} years old - {self.birth.date})"
        )

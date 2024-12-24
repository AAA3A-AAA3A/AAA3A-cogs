from AAA3A_utils import Cog  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.bot import Red  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import datetime
import hashlib
import mimesis
import random
import secrets
from mimesis.locales import Locale
from mimesis.enums import Gender, TitleType

from .types import LOCALES, FakeIdentity, Name, Birth, Communication, Medical, Studies, Profession, Address, Street, Coordinates, Transport, Payment, CreditCard, Login, Devices, Computer, Phone, Favorite, Food, SecondaryIdentity
from .view import FakeIdentityView

# Credits:
# General repo credits.

_: Translator = Translator("FakeIdentities", __file__)


@cog_i18n(_)
class FakeIdentities(Cog):
    """Generate random and fake identities, including names, addresses, emails, and phone numbers!"""

    def __init__(self, bot: Red) -> None:
        super().__init__(bot=bot)
        self.fake_identities: typing.List[FakeIdentity] = []

    def generate_fake_identity(
        self,
        gender: typing.Optional[Gender] = None,
        nationality: typing.Optional[Locale] = None,
        location: typing.Optional[Locale] = None,
        seed: typing.Optional[int] = None,
    ) -> FakeIdentity:
        seed = seed or secrets.randbelow(2 ** 32)
        random.seed(seed)
        nationality = nationality or random.choice(list(LOCALES))
        person_nationality: mimesis.Person = mimesis.Person(
            locale=nationality,
            seed=seed,
        )
        if location is None:
            if random.random() <= 0.8:
                location = nationality
            else:
                location = random.choice(list(LOCALES))
        person_location: mimesis.Person = mimesis.Person(
            locale=location,
            seed=seed,
        )
        gender = gender or random.choice([Gender.MALE, Gender.FEMALE])

        address: mimesis.Address = mimesis.Address(
            locale=location,
            seed=seed,
        )
        transport: mimesis.Transport = mimesis.Transport(seed=seed)
        finance: mimesis.Finance = mimesis.Finance(
            locale=location,
            seed=seed,
        )
        payment: mimesis.Payment = mimesis.Payment(seed=seed)
        code: mimesis.Code = mimesis.Code(seed=seed)
        development: mimesis.Development = mimesis.Development(seed=seed)
        hardware: mimesis.Hardware = mimesis.Hardware(seed=seed)
        internet: mimesis.Internet = mimesis.Internet(seed=seed)
        text: mimesis.Text = mimesis.Text(
            locale=nationality,
            seed=seed,
        )
        food: mimesis.Food = mimesis.Food(
            locale=nationality,
            seed=seed,
        )

        has_partner = random.random() <= 0.5
        has_children = random.random() <= 0.5 if has_partner else random.random() <= 0.1
        children_number = (random.randint(1, 2) if random.random() <= 0.3 else 3) if has_children else 0
        children_last_name = None

        # "picture": {
        #     "large": "https://randomuser.me/api/portraits/women/74.jpg",
        #     "medium": "https://randomuser.me/api/portraits/med/women/74.jpg",
        #     "thumbnail": "https://randomuser.me/api/portraits/thumb/women/74.jpg"
        # },
        fake_identity: FakeIdentity = FakeIdentity(
            gender=gender,
            nationality=nationality,
            location=location,
            seed=seed,

            name=Name(
                title=person_nationality.title(gender, TitleType.TYPICAL),
                first=person_nationality.first_name(gender),
                last=(last_name := person_nationality.last_name(gender)),
                surname=person_location.surname(gender) if random.random() <= 0.5 else None,
            ),
            thumbnail_url=f"https://randomuser.me/api/portraits/{'men' if gender is Gender.MALE else 'women'}/{random.randint(0, 99 if gender is Gender.MALE else 96)}.jpg",

            birth=Birth(
                date=(birthdate := person_nationality.birthdate()),
                age=int((datetime.date.today() - birthdate).days // 365.5),
            ),
            communication=Communication(
                email=person_location.email(),
                phone=person_location.telephone(),
                cell=person_location.telephone() if random.random() <= 0.5 else None,
            ),

            medical=Medical(
                blood_type=person_nationality.blood_type(),
                weight=person_nationality.weight(),
                height=person_nationality.height(),
            ),

            studies=Studies(
                university=person_location.university(),
                academic_degree=person_location.academic_degree(),
            ),
            profession=Profession(
                occupation=person_location.occupation(),
                company=finance.company(),
            ),

            address=Address(
                street=Street(
                    number=address.street_number(),
                    name=address.street_name(),
                ),
                city=address.city(),
                postal_code=address.postal_code(),
                state=address.state(),
                country=address.default_country(),
                coordinates=Coordinates(
                    latitude=address.latitude(),
                    longitude=address.longitude(),
                ),
            ),
            transport=Transport(
                car=transport.car(),
                manufacturer=transport.manufacturer(),
                vehicle_registration_code=transport.vehicle_registration_code(location),
            ),

            payment=Payment(
                bank=finance.bank(),
                credit_card=CreditCard(
                    network=payment.credit_card_network(),
                    number=payment.credit_card_number(),
                    expiration_date=payment.credit_card_expiration_date(),
                    cvv=payment.cvv(),
                ),
                paypal_account=payment.paypal(),
                bitcoin_address=payment.bitcoin_address(),
                ethereum_address=payment.ethereum_address(),
            ),

            login=Login(
                uuid=person_location.identifier("@@@@-@@@@-@@@@-@@@@"),
                pin_code=code.pin(),

                username=person_location.username(),
                password=(password := person_location.password()),
                md5=hashlib.md5(password.encode()).hexdigest(),
                sha1=hashlib.sha1(password.encode()).hexdigest(),
                sha256=hashlib.sha256(password.encode()).hexdigest(),
            ),
            devices=Devices(
                computer=Computer(
                    os=development.os(),
                    manufacturer=hardware.manufacturer(),

                    cpu=hardware.cpu(),
                    cpu_codename=hardware.cpu_codename(),
                    cpu_frequency=hardware.cpu_frequency(),
                    generation=hardware.generation(),

                    graphics=hardware.graphics(),

                    ram_size=hardware.ram_size(),
                    ram_type=hardware.ram_type(),

                    resolution=hardware.resolution(),
                    screen_size=hardware.screen_size(),

                    ssd_or_hdd=hardware.ssd_or_hdd(),

                    mac_address=internet.mac_address(),
                    ip_v4=internet.ip_v4(),
                    ip_v6=internet.ip_v6(),
                ),
                phone=Phone(
                    model=hardware.phone_model(),

                    ram_size=hardware.ram_size(),

                    mac_address=internet.mac_address(),
                    ip_v4=internet.ip_v4(),
                    ip_v6=internet.ip_v6(),
                ),
            ),

            favorite=Favorite(
                political_views=person_location.political_views(),
                color=text.color(),
                emoji=text.emoji(),
                quote=text.quote(),
                word=text.word(),
                food=Food(
                    dish=food.dish(),
                    vegetable=food.vegetable(),
                    fruit=food.fruit(),
                    drink=food.drink(),
                    spices=food.spices(),
                ),
            ),

            partner=(
                SecondaryIdentity(
                    name=Name(
                        title=person_location.title((other_gender := (Gender.FEMALE if gender is Gender.MALE else Gender.MALE))),
                        first=person_location.first_name(other_gender),
                        last=(partner_last_name := person_location.name(other_gender)),
                        surname=None,
                    ),
                    birth=Birth(
                        date=(birthdate := person_location.birthdate()),
                        age=int((datetime.date.today() - birthdate).days // 365.5),
                    ),
                )
                if has_partner else None
            ),
            children=[
                SecondaryIdentity(
                    name=Name(
                        title=None,
                        first=person_location.first_name(random.choice(list(Gender))),
                        last=children_last_name if children_last_name is not None else (children_last_name := random.choice([last_name, partner_last_name])),
                        surname=None,
                    ),
                    birth=Birth(
                        age=(child_age := random.randint(1, 18)),
                        date=datetime.date.today() - datetime.timedelta(days=365.25 * child_age),
                    ),
                )
                for __ in range(children_number)
            ],
        )
        self.fake_identities.append(fake_identity)
        return fake_identity

    @commands.bot_has_permissions(embed_links=True)
    @commands.hybrid_command(aliases=["fakeid"])
    async def fakeidentity(
        self,
        ctx: commands.Context,
        gender: typing.Optional[Gender] = None,
        nationality: typing.Optional[Locale] = None,
        location: typing.Optional[Locale] = None,
        seed: typing.Optional[int] = None,
    ) -> None:
        """Generate a fake identity."""
        view: FakeIdentityView = FakeIdentityView(
            self,
            gender=gender,
            nationality=nationality,
            location=location,
            seed=seed,
        )
        await view.start(ctx)

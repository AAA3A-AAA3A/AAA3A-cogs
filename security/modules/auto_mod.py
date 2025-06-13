from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import asyncio
import datetime
import re
import urllib
from collections import defaultdict

from fuzzywuzzy import StringMatcher
from redbot.core.data_manager import bundled_data_path
from redbot.core.utils.chat_formatting import humanize_list, text_to_file
from redbot.core.utils.common_filters import INVITE_URL_RE, URL_RE

try:
    from emoji import EMOJI_DATA  # emoji>=2.0.0
except ImportError:
    from emoji import UNICODE_EMOJI_ENGLISH as EMOJI_DATA  # emoji<2.0.0

from ..constants import POSSIBLE_ACTIONS, Emojis
from ..views import DurationConverter, ToggleModuleButton
from .module import Module

_: Translator = Translator("Security", __file__)

EMOJIS = set(EMOJI_DATA) | {
    "🇦",
    "🇧",
    "🇨",
    "🇩",
    "🇪",
    "🇫",
    "🇬",
    "🇭",
    "🇮",
    "🇯",
    "🇰",
    "🇱",
    "🇲",
    "🇳",
    "🇴",
    "🇵",
    "🇶",
    "🇷",
    "🇸",
    "🇹",
    "🇺",
    "🇻",
    "🇼",
    "🇽",
    "🇾",
    "🇿",
}


def similarity_ratio_check(last_content: str, content: str, similarity_ratio: float) -> bool:
    if not last_content or not content:
        return False
    return StringMatcher.ratio(last_content, content) >= similarity_ratio


def get_emoji_count(content: str) -> int:
    return sum(content.count(emoji) for emoji in EMOJIS) + len(
        re.findall(r"<a?:\w+:\d+>", content)
    )


async def check_invite_links(
    message: discord.Message, filter_config: typing.Dict[str, typing.Any]
) -> int:
    count = 0
    for invite_url in re.findall(INVITE_URL_RE, message.content):
        try:
            invite = await message._state._get_client().fetch_invite(invite_url[1])
            if invite.guild == message.guild:
                continue
        except discord.HTTPException:
            pass
        count += 1
    return filter_config["added_heat"] * count


NSFW_LINKS: typing.Set[str] = set()
BAD_WORDS: typing.Set[str] = set()
AUTO_MOD_FILTERS: typing.Dict[
    str,
    typing.Dict[
        typing.Literal["name", "emoji", "description", "filters"],
        typing.Union[
            str,
            typing.List[
                typing.Dict[
                    typing.Literal[
                        "name",
                        "emoji",
                        "value",
                        "default_added_heat",
                        "specific_heats",
                        "params",
                        "check",
                        "reason",
                    ],
                    typing.Union[
                        str,
                        float,
                        typing.Dict[str, float],
                        typing.List[typing.Tuple[str, typing.Any]],
                        typing.Callable,
                    ],
                ]
            ],
        ],
    ],
] = {
    "anti_spam": {
        "name": "Anti Spam",
        "emoji": Emojis.SPAM.value,
        "description": "Detect and prevent spam messages.",
        "filters": [
            {
                "name": "Regular Message",
                "emoji": Emojis.MESSAGE.value,
                "value": "regular_message",
                "default_added_heat": 15.0,
                "check": lambda message, filter_config: filter_config["added_heat"],
                "reason": lambda: _("**Auto Mod** - Spam of messages detected."),
            },
            {
                "name": "Similar Message (similarity ratio)",
                "emoji": "🔄",
                "value": "similar_message",
                "default_added_heat": 22.0,
                "params": [("similarity_ratio", 0.8)],
                "check": lambda message, filter_config, previous_message: (
                    filter_config["added_heat"]
                    if previous_message is not None
                    and similarity_ratio_check(
                        previous_message.content,
                        message.content,
                        filter_config["similarity_ratio"],
                    )
                    else 0
                ),
                "reason": lambda: _("**Auto Mod** - Spam of similar messages detected."),
            },
            {
                "name": "Emojis (each)",
                "emoji": Emojis.EMOJI.value,
                "value": "emojis",
                "default_added_heat": 9.0,
                "check": lambda message, filter_config: filter_config["added_heat"]
                * get_emoji_count(message.content),
                "reason": lambda: _("**Auto Mod** - Spam of emojis detected."),
            },
            {
                "name": "New Lines (each)",
                "emoji": Emojis.NEW_LINES.value,
                "value": "new_lines",
                "default_added_heat": 5.0,
                "check": lambda message, filter_config: filter_config["added_heat"]
                * message.content.count("\n"),
                "reason": lambda: _("**Auto Mod** - Spam of new lines detected."),
            },
            {
                "name": "Zalgo Characters (each)",
                "emoji": Emojis.ZALGO_CHARACTERS.value,
                "value": "zalgo_characters",
                "default_added_heat": 1.5,
                "check": lambda message, filter_config: (
                    filter_config["added_heat"]
                    * len(
                        re.findall(
                            r"[\u0300-\u036F\u0483-\u0487\u0488-\u0489\u048A-\u048B\u048C-\u048D\u048E-\u048F\u0490-\u0491\u0492-\u0493\u0494-\u0495\u0496-\u0497\u0498-\u0499\u049A-\u049B\u049C-\u049D\u049E-\u049F\u04A0-\u04A1\u04A2-\u04A3\u04A4-\u04A5\u04A6-\u04A7\u04A8-\u04A9\u04AA-\u04AB\u04AC-\u04AD\u04AE-\u04AF]",
                            message.content,
                        )
                    )
                ),
                "reason": lambda: _("**Auto Mod** - Spam of Zalgo characters detected."),
            },
            {
                "name": "Characters (each)",
                "emoji": Emojis.CHARACTERS.value,
                "value": "characters",
                "default_specific_heats": {
                    "lowercase": 0.08,
                    "uppercase": 0.12,
                },
                "check": lambda message, filter_config: (
                    filter_config["specific_heats"]["lowercase"]
                    * sum(1 for c in message.content if c.islower())
                    + filter_config["specific_heats"]["uppercase"]
                    * sum(1 for c in message.content if c.isupper())
                ),
                "reason": lambda: _("**Auto Mod** - Spam of messages detected."),
            },
            {
                "name": "Embed (at least one)",
                "emoji": "📎",
                "value": "embed",
                "default_added_heat": 20.0,
                "check": lambda message, filter_config: (
                    filter_config["added_heat"] if message.embeds else 0
                ),
                "reason": lambda: _("**Auto Mod** - Spam of embeds detected."),
            },
            {
                "name": "Image/Video (at least one)",
                "emoji": Emojis.IMAGE_VIDEO.value,
                "value": "image_video",
                "default_added_heat": 30.0,
                "check": lambda message, filter_config: (
                    filter_config["added_heat"]
                    if any(
                        attachment.content_type
                        and attachment.content_type.startswith(("image/", "video/"))
                        for attachment in message.attachments
                    )
                    else 0
                ),
                "reason": lambda: _("**Auto Mod** - Spam of images/videos detected."),
            },
            {
                "name": "File (at least one)",
                "emoji": Emojis.FILE.value,
                "value": "file",
                "default_added_heat": 20.0,
                "check": lambda message, filter_config: (
                    filter_config["added_heat"]
                    if any(
                        not attachment.content_type
                        or not attachment.content_type.startswith(("image/", "video/"))
                        for attachment in message.attachments
                    )
                    else 0
                ),
                "reason": lambda: _("**Auto Mod** - Spam of files detected."),
            },
            {
                "name": "Links (each)",
                "emoji": Emojis.LINK.value,
                "value": "links",
                "default_added_heat": 15.0,
                "check": lambda message, filter_config: (
                    filter_config["added_heat"] * len(re.findall(URL_RE, message.content))
                ),
                "reason": lambda: _("**Auto Mod** - Spam of links detected."),
            },
            {
                "name": "Stickers (each)",
                "emoji": Emojis.STICKER.value,
                "value": "stickers",
                "default_added_heat": 20.0,
                "check": lambda message, filter_config: (
                    filter_config["added_heat"] * len(message.stickers)
                ),
                "reason": lambda: _("**Auto Mod** - Spam of stickers detected."),
            },
        ],
    },
    "anti_advertising": {
        "name": "Anti Advertising",
        "emoji": Emojis.ADVERTISING.value,
        "description": "Detect and prevent advertising messages.",
        "filters": [
            {
                "name": "Invite Links (each)",
                "emoji": Emojis.LINK.value,
                "value": "invite_links",
                "default_added_heat": 100.0,
                "check": check_invite_links,
                "reason": lambda: _("**Auto Mod** - Advertising of Discord invites detected."),
            },
        ],
    },
    "anti_mention_spam": {
        "name": "Anti Mention Spam",
        "emoji": Emojis.PING.value,
        "description": "Detect and prevent spam of mentions.",
        "filters": [
            {
                "name": "@member Mentions (each)",
                "emoji": Emojis.PING.value,
                "value": "member_mentions",
                "default_added_heat": 20.0,
                "check": lambda message, filter_config: (
                    filter_config["added_heat"]
                    * len(
                        [
                            member
                            for member in message.mentions
                            if member != message.author and not member.bot
                        ]
                    )
                ),
                "reason": lambda: _("**Auto Mod** - Spam of member mentions detected."),
            },
            {
                "name": "@role Mentions (each)",
                "emoji": Emojis.PING.value,
                "value": "role_mentions",
                "default_added_heat": 30.0,
                "check": lambda message, filter_config: (
                    filter_config["added_heat"]
                    * len(
                        [
                            role
                            for role in message.role_mentions
                            if not role.is_default()
                            and len(role.members) < 0.1 * len(message.guild.members)
                        ]
                    )
                ),
                "reason": lambda: _("**Auto Mod** - Spam of role mentions detected."),
            },
            {
                "name": "@everyone, @here and main roles Mentions (each)",
                "emoji": Emojis.EVERYONE_HERE.value,
                "value": "everyone_here_mentions",
                "default_added_heat": 100.0,
                "check": lambda message, filter_config: (
                    filter_config["added_heat"]
                    * (
                        int(message.mention_everyone)
                        + len(
                            [
                                role
                                for role in message.role_mentions
                                if not role.is_default()
                                and len(role.members) >= 0.1 * len(message.guild.members)
                            ]
                        )
                    )
                ),
                "reason": lambda: _(
                    "**Auto Mod** - Spam of @everyone, @here or main roles mentions detected."
                ),
            },
        ],
    },
    "anti_bad_links": {
        "name": "Anti Bad Links",
        "emoji": Emojis.LINK.value,
        "description": "Detect and prevent links to known bad websites.",
        "filters": [
            {
                "name": "Discord/Steam Scam Links (each)",
                "emoji": Emojis.STEAM_SCAM_LINK.value,
                "value": "discord_steam_scam_links",
                "default_added_heat": 100.0,
                "check": lambda message, filter_config: (
                    filter_config["added_heat"]
                    * (
                        len(
                            re.findall(
                                re.compile(
                                    r"https?://(?!discord(?:\.com/gifts|\.gift))([a-zA-Z0-9-]+\.)*discord[a-zA-Z0-9-]*gift[a-zA-Z0-9-]*\.[a-z]{2,}(?:/\S*)?",
                                    re.IGNORECASE,
                                ),
                                message.content,
                            )
                        )
                        + len(
                            re.findall(
                                re.compile(
                                    r"https?://(?!www\.steamcommunity\.com/gift)(?:[a-zA-Z0-9-]+\.)*steam[a-zA-Z0-9-]*gift[a-zA-Z0-9-]*\.[a-z]{2,}(?:/\S*)?",
                                    re.IGNORECASE,
                                ),
                                message.content,
                            )
                        )
                    )
                ),
                "reason": lambda: _("**Auto Mod** - Steam scam links detected."),
            },
            {
                "name": "NSFW Links in SFW channels (each)",
                "emoji": Emojis.NSFW.value,
                "value": "nsfw_links",
                "default_added_heat": 100.0,
                "check": lambda message, filter_config: (
                    filter_config["added_heat"]
                    * len(
                        [
                            url
                            for url in re.findall(URL_RE, message.content)
                            if any(nsfw_link in f"{url[0]}://{url[1]}" for nsfw_link in NSFW_LINKS)
                        ]
                    )
                    if not message.channel.is_nsfw()
                    else 0
                ),
                "reason": lambda: _("**Auto Mod** - NSFW links detected."),
            },
            {
                "name": "Disguised Links (each)",
                "emoji": Emojis.DISGUISED_LINK.value,
                "value": "disguised_links",
                "default_added_heat": 100.0,
                "check": lambda message, filter_config: (
                    filter_config["added_heat"]
                    * len(
                        re.findall(
                            rf"\[{URL_RE.pattern}\]\({URL_RE.pattern}\)",
                            message.content,
                        )
                    )
                ),
                "reason": lambda: _("**Auto Mod** - Disguised links detected."),
            },
            {
                "name": "Blacklisted Domains (each)",
                "emoji": Emojis.BLACKLISTED_LINK.value,
                "value": "blacklisted_domains",
                "default_added_heat": 100.0,
                "params": [("blacklisted_domains", [])],
                "check": lambda message, filter_config: (
                    filter_config["added_heat"]
                    * len(
                        [
                            url
                            for url in re.findall(URL_RE, message.content)
                            if any(
                                urllib.parse.urlparse(f"{url[0]}://{url[1]}").netloc.endswith(
                                    domain
                                )
                                for domain in filter_config["blacklisted_domains"]
                            )
                        ]
                    )
                ),
                "reason": lambda: _("**Auto Mod** - Blacklisted links detected."),
            },
        ],
    },
    "word_blacklist": {
        "name": "Word Blacklist",
        "emoji": Emojis.WORD_BLACKLIST.value,
        "description": "Detect and prevent messages containing blacklisted words.",
        "filters": [
            {
                "name": "Premade Bad Word Lists",
                "emoji": Emojis.WORD_LISTS.value,
                "value": "premade_bad_word_lists",
                "default_added_heat": 100.0,
                "check": lambda message, filter_config: (
                    filter_config["added_heat"]
                    * sum(
                        [
                            len(
                                re.compile(rf"\b{bad_word}\b", re.IGNORECASE).findall(
                                    message.content
                                )
                            )
                            for bad_word in BAD_WORDS
                        ]
                    )
                ),
                "reason": lambda: _("**Auto Mod** - Bad words detected."),
            },
            {
                "name": "Blacklisted Words (each)",
                "emoji": Emojis.BLACKLISTED_WORD.value,
                "value": "blacklisted_words",
                "default_added_heat": 100.0,
                "params": [("strict", []), ("wildcard", [])],
                "check": lambda message, filter_config: (
                    filter_config["added_heat"]
                    * len(
                        [
                            word
                            for word in re.findall(r"\w+(?:\s\w+)*", message.content)
                            if (
                                word.lower() in filter_config["strict"]
                                or any(
                                    re.fullmatch(pattern, word.lower())
                                    for pattern in filter_config["wildcard"]
                                )
                            )
                        ]
                    )
                ),
                "reason": lambda: _("**Auto Mod** - Blacklisted word detected."),
            },
        ],
    },
}


def sum_dicts(*dicts: typing.Dict) -> typing.Dict:
    dict0 = dicts[0]
    for d in dicts[1:]:
        dict0.update(d)
    return dict0


class AutoModModule(Module):
    name = "Auto Mod"
    emoji = Emojis.AUTO_MOD.value
    description = (
        "Detect and prevent spam, advertising, and other unwanted behavior in your server."
    )
    default_config = {
        "enabled": False,
        "heats": {
            "max": 100,
            "degradation": 5,
            "reset_after_punishment": False,
        },
        "strike_durations": {
            "regular": "1m",
            "severe": "10m",  # After 3 strikes.
            "auto_multiplier": 2,  # After severe strike, the next strike will be multiplied by this factor.
            "individual_timeout_mute": "1h",  # Only used if a filter has a specific action set.
        },
        "filters": {
            category: {
                filter["value"]: sum_dicts(
                    {"enabled": True, "action": None},
                    (
                        {"added_heat": filter["default_added_heat"]}
                        if "default_added_heat" in filter
                        else {}
                    ),
                    (
                        {"specific_heats": filter["default_specific_heats"].copy()}
                        if "default_specific_heats" in filter
                        else {}
                    ),
                    {key: value for key, value in filter.get("params", [])},
                )
                for filter in data["filters"]
            }
            for category, data in AUTO_MOD_FILTERS.items()
        },
    }

    def __init__(self, cog: commands.Cog) -> None:
        super().__init__(cog)
        self.heats_cache: typing.Dict[
            discord.Guild,
            typing.Dict[
                discord.Member,
                typing.List[typing.Tuple[datetime.datetime, str, float, discord.Message]],
            ],
        ] = defaultdict(lambda: defaultdict(list))
        self.strikes_cache: typing.Dict[
            discord.Guild, typing.Dict[discord.Member, int]
        ] = defaultdict(lambda: defaultdict(lambda: 0))
        self.previous_messages_cache: typing.Dict[
            discord.Guild, typing.Dict[discord.Member, discord.Message]
        ] = defaultdict(lambda: defaultdict(lambda: None))
        self.strikes_locks: typing.Dict[
            discord.Guild, typing.Dict[discord.Member, asyncio.Lock]
        ] = defaultdict(lambda: defaultdict(asyncio.Lock))

    async def load(self) -> None:
        data_path = bundled_data_path(self.cog)
        for file in data_path.glob("bad_words/*.txt"):
            with open(file, mode="rt", encoding="utf-8") as f:
                BAD_WORDS.update(word.strip().lower() for word in f.readlines() if word.strip())
        with open(data_path / "nsfw_links.txt", mode="rt", encoding="utf-8") as f:
            NSFW_LINKS.update(line.strip().lower() for line in f if line.strip())
        self.cog.bot.add_listener(self.on_message)

    async def unload(self) -> None:
        self.cog.bot.remove_listener(self.on_message)

    async def get_status(
        self, guild: discord.Guild
    ) -> typing.Tuple[typing.Literal["✅", "⚠️", "❎", "❌"], str, str]:
        config = await self.config_value(guild)()
        if not config["enabled"]:
            return "❌", _("Disabled"), _("Auto Mod is currently disabled.")
        if all(
            not filter["enabled"]
            for filters in config["filters"].values()
            for filter in filters.values()
        ):
            return (
                "❎",
                _("No Enabled Filters"),
                _("There are no Auto Mod filter category enabled."),
            )
        missing_permissions = []
        if not guild.me.guild_permissions.manage_messages:
            missing_permissions.append("manage_messages")
        if (
            config["filters"]["anti_advertising"]["invite_links"]["enabled"]
            and not guild.me.guild_permissions.manage_guild
        ):
            missing_permissions.append("manage_guild")
        for action, permission in {
            "timeout": "moderate_members",
            "kick": "kick_members",
            "ban": "ban_members",
        }.items():
            if any(
                filter["enabled"] and filter["action"] == action
                for filters in config["filters"].values()
                for filter in filters.values()
            ) and not getattr(guild.me.guild_permissions, permission):
                missing_permissions.append(permission)
        if missing_permissions:
            return (
                "⚠️",
                _("Missing Permissions"),
                _("I need the {permissions} permission{s} to function properly.").format(
                    permissions=humanize_list(
                        [f"`{permission}`" for permission in missing_permissions]
                    ),
                    s="" if len(missing_permissions) == 1 else "s",
                ),
            )
        return "✅", _("Enabled"), _("Auto Mod is enabled and configured correctly.")

    async def get_settings(
        self, guild: discord.Guild, view: discord.ui.View
    ) -> typing.Tuple[str, str, typing.List[typing.Dict], typing.List[discord.ui.Item]]:
        title = _("Security — {emoji} {name} {status}").format(
            emoji=self.emoji, name=self.name, status=(await self.get_status(guild))[0]
        )
        description = _(
            "This module helps to detect and prevent spam, advertising, and other unwanted behavior in your server.\n"
        )
        status = await self.get_status(guild)
        if status[0] == "⚠️":
            description += f"{status[0]} **{status[1]}**: {status[2]}\n"

        config = await self.config_value(guild)()
        description += _(
            "\n**Heat:**\n"
            "- Maximum heat: **{max_heat}%**\n"
            "- Degradation: **{degradation}%** per second\n"
            "- Reset after punishment: {reset_after_punishment}\n"
            "**Strike timeout durations:**\n"
            "- Regular: `{regular}`\n"
            "- Severe: `{severe}`\n"
            "- Auto multiplier: `{auto_multiplier}x`\n"
            "- Individual timeout/mute duration: `{specific_duration}`\n"
            "*When the total heat reaches the maximum, the last trigger message will be deleted and the most triggered filter configuration will be used to punish the member.*"
        ).format(
            max_heat=config["heats"]["max"],
            degradation=config["heats"]["degradation"],
            reset_after_punishment="✅" if config["heats"]["reset_after_punishment"] else "❌",
            regular=config["strike_durations"]["regular"],
            severe=config["strike_durations"]["severe"],
            auto_multiplier=config["strike_durations"]["auto_multiplier"],
            specific_duration=config["strike_durations"]["individual_timeout_mute"],
        )
        fields = []
        for category, data in AUTO_MOD_FILTERS.items():
            category_config = config["filters"][category]
            fields.append(
                dict(
                    name=f"{data['emoji']} {data['name']}",
                    value=data["description"],
                    inline=True,
                )
            )
            first_state = list(category_config.values())[0]["enabled"]
            if all(filter["enabled"] == first_state for filter in category_config.values()):
                fields[-1]["value"] += _("\n**Enabled:** {state}").format(
                    state="✅" if first_state else "❌"
                )
            else:
                fields[-1]["value"] += _("\n**Enabled:** 🔀 (Different States)")

        components = [ToggleModuleButton(self, guild, view, config["enabled"])]
        heat_button: discord.ui.Button = discord.ui.Button(
            label=_("Heat"),
            style=discord.ButtonStyle.secondary,
        )

        async def heat_button_callback(interaction: discord.Interaction) -> None:
            await interaction.response.send_modal(
                ConfigureHeatModal(self, guild, view, config["heats"])
            )

        heat_button.callback = heat_button_callback
        components.append(heat_button)
        strike_durations_button: discord.ui.Button = discord.ui.Button(
            label=_("Strike Durations"),
            style=discord.ButtonStyle.secondary,
        )

        async def strike_durations_button_callback(interaction: discord.Interaction) -> None:
            await interaction.response.send_modal(
                ConfigureStrikeDurationsModal(self, guild, view, config["strike_durations"])
            )

        strike_durations_button.callback = strike_durations_button_callback
        components.append(strike_durations_button)

        configure_filter_category_select: discord.ui.Select = discord.ui.Select(
            placeholder=_("Configure Filter Category"),
            options=[
                discord.SelectOption(
                    emoji=data["emoji"],
                    label=data["name"],
                    value=category,
                    description=data["description"],
                )
                for category, data in AUTO_MOD_FILTERS.items()
            ],
        )

        async def configure_filter_category_callback(interaction: discord.Interaction) -> None:
            await interaction.response.defer(ephemeral=True, thinking=True)
            await ConfigureFilterCategoryView(
                self,
                guild,
                view,
                configure_filter_category_select.values[0],
            ).start(interaction)

        configure_filter_category_select.callback = configure_filter_category_callback
        components.append(configure_filter_category_select)

        return title, description, fields, components

    async def update_heats_cache(self, guild: discord.Guild, member: discord.Member) -> None:
        heats = self.heats_cache[guild][member]
        if heats:
            degradation = await self.config_value(guild).heats.degradation()
            to_remove = (
                degradation
                * (datetime.datetime.now(tz=datetime.timezone.utc) - heats[0][0]).total_seconds()
            )
            while to_remove > 0 and heats:
                if heats[0][2] <= to_remove:
                    to_remove -= heats[0][2]
                    heats.pop(0)
                else:
                    heats[0] = (heats[0][0], heats[0][1], heats[0][2] - to_remove, heats[0][3])
                    to_remove = 0
        if not heats:
            del self.heats_cache[guild][member]
        if not self.heats_cache[guild]:
            del self.heats_cache[guild]

    async def on_message(self, message: discord.Message) -> None:
        if message.guild is None:
            return
        config = await self.config_value(message.guild)()
        if not config["enabled"]:
            return
        if await self.cog.is_trusted_admin_or_higher(message.author):
            return
        heats = self.heats_cache[message.guild][message.author]
        previous_message = self.previous_messages_cache[message.guild].get(message.author)
        self.previous_messages_cache[message.guild][message.author] = message
        for category, data in AUTO_MOD_FILTERS.items():
            for filter in data["filters"]:
                filter_config = config["filters"][category][filter["value"]]
                if not filter_config["enabled"]:
                    continue
                if category == "anti_spam":
                    whitelist_type = "auto_mod_spam"
                elif category == "anti_advertising":
                    whitelist_type = "auto_mod_advertising"
                elif filter["value"] in ("member_mentions", "role_mentions"):
                    whitelist_type = "auto_mod_mentions"
                elif filter["value"] == "everyone_here_mentions":
                    whitelist_type = "auto_mod_everyone_here_mentions"
                else:
                    whitelist_type = None
                if whitelist_type is not None and await self.cog.is_message_whitelisted(
                    message, whitelist_type
                ):
                    continue
                try:
                    added_heat = await discord.utils.maybe_coroutine(
                        filter["check"], message, filter_config
                    )
                except TypeError:
                    added_heat = filter["check"](message, filter_config, previous_message)
                if added_heat > 0:
                    heats.append(
                        (
                            message.created_at,
                            filter["value"],
                            added_heat,
                            message,
                        )
                    )
        number = self.strikes_cache[message.guild][message.author]
        lock = self.strikes_locks[message.guild][message.author]
        await lock.acquire()
        if self.strikes_cache[message.guild][message.author] > number:
            lock.release()
            return
        await self.update_heats_cache(message.guild, message.author)
        total_heat = sum(heat[2] for heat in heats)
        if total_heat >= config["heats"]["max"]:
            trigger_messages = sorted(
                {heat[3] for heat in heats},
                key=lambda m: m.created_at,
            )
            file = text_to_file(
                "\n".join(
                    f"[{message.created_at.strftime('%Y-%m-%d %H:%M:%S')} (UTC)] #{message.channel.name}: {message.content}"
                    for message in trigger_messages
                ),
                filename="auto_mod_trigger_messages.txt",
            )
            if config["heats"]["reset_after_punishment"]:
                heats.clear()
            filter_value = sorted(
                {heat[1]: sum(h[2] for h in heats if h[1] == heat[1]) for heat in heats}.items(),
                key=lambda item: item[1],
            )[-1]
            category_value, filter = next(
                (
                    (category, f)
                    for category, data in AUTO_MOD_FILTERS.items()
                    for f in data["filters"]
                    if f["value"] == filter_value[0]
                ),
            )
            if config["filters"][category_value][filter["value"]].get("added_heat", 0) >= 50:
                try:
                    await message.delete()
                except discord.HTTPException:
                    pass
            self.strikes_cache[message.guild][message.author] += 1
            reason = filter["reason"]()
            audit_log_reason = f"Security's Auto Mod: {filter['name']}."
            filter_config = config["filters"][category_value][filter["value"]]
            if await self.cog.is_moderator_or_higher(
                message.author
            ):  # An administrator can't be timed out, and we don't want to get the staff kicked/banned.
                await self.cog.quarantine_member(
                    member=message.author,
                    reason=reason,
                    file=file,
                    context_message=message,
                )
            elif (action := filter_config["action"]) is None:
                if self.strikes_cache[message.guild][message.author] < 3:
                    duration = await DurationConverter.convert(
                        None, config["strike_durations"]["regular"]
                    )
                else:
                    duration = await DurationConverter.convert(
                        None, config["strike_durations"]["severe"]
                    )
                for __ in range(self.strikes_cache[message.guild][message.author] - 2):
                    duration *= config["strike_durations"]["auto_multiplier"]
                await self.cog.send_modlog(
                    action="timeout",
                    member=message.author,
                    reason=reason,
                    duration=duration,
                    file=file,
                    context_message=message,
                    current_ctx=message,
                )
                if message.guild.me.guild_permissions.moderate_members:
                    await message.author.timeout(duration, reason=audit_log_reason)
            else:
                if action in ("timeout", "mute"):
                    duration = await DurationConverter.convert(
                        None, config["timeout_mute_duration"]
                    )
                else:
                    duration = None
                if action != "quarantine":
                    await self.cog.send_modlog(
                        action=action,
                        member=message.author,
                        reason=reason,
                        duration=duration,
                        file=file,
                        context_message=message,
                        current_ctx=message,
                    )
                if action == "timeout" and message.guild.me.guild_permissions.moderate_members:
                    await message.author.timeout(duration, reason=audit_log_reason)
                elif (
                    action == "mute"
                    and message.guild.me.guild_permissions.manage_roles
                    and (Mutes := self.cog.bot.get_cog("Mutes")) is not None
                    and hasattr(Mutes, "mute_user")
                ):
                    await Mutes.mute_user(
                        guild=message.guild,
                        author=message.guild.me,
                        user=message.author,
                        until=datetime.datetime.now(tz=datetime.timezone.utc) + duration,
                        reason=audit_log_reason,
                    )
                elif action == "kick" and message.guild.me.guild_permissions.kick_members:
                    await message.author.kick(reason=audit_log_reason)
                elif action == "ban" and message.guild.me.guild_permissions.ban_members:
                    await message.author.ban(reason=audit_log_reason)
                elif (
                    action == "quarantine"
                    and message.author.guild.me.guild_permissions.manage_roles
                ):
                    await self.cog.quarantine_member(
                        member=message.author,
                        reason=reason,
                        file=file,
                        context_message=message,
                        current_ctx=message,
                    )
        lock.release()


class ConfigureHeatModal(discord.ui.Modal):
    def __init__(
        self,
        module: AutoModModule,
        guild: discord.Guild,
        view: discord.ui.View,
        heats_config: typing.Dict[str, typing.Union[int, bool]],
    ) -> None:
        self.module: AutoModModule = module
        self.guild: discord.Guild = guild
        self.view: discord.ui.View = view
        self.heats_config: typing.Dict[str, typing.Union[int, bool]] = heats_config
        super().__init__(title=_("Configure Heat Settings"))
        self.max_heat: discord.ui.TextInput = discord.ui.TextInput(
            label=_("Maximum Heat:"),
            style=discord.TextStyle.short,
            default=str(heats_config["max"]),
            required=True,
        )
        self.add_item(self.max_heat)
        self.degradation: discord.ui.TextInput = discord.ui.TextInput(
            label=_("Degradation per second:"),
            style=discord.TextStyle.short,
            default=str(heats_config["degradation"]),
            required=True,
        )
        self.add_item(self.degradation)
        self.reset_after_punishment: discord.ui.TextInput = discord.ui.TextInput(
            label=_("Reset After Punishment (True/False):"),
            style=discord.TextStyle.short,
            default=str(heats_config["reset_after_punishment"]),
            required=True,
        )
        self.add_item(self.reset_after_punishment)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        try:
            max_heat = int(self.max_heat.value)
            degradation = int(self.degradation.value)
            reset_after_punishment = self.reset_after_punishment.value.lower() in (
                "true",
                "yes",
                "1",
            )
        except ValueError as e:
            await interaction.followup.send(
                _("Invalid value: {error}").format(error=str(e)),
                ephemeral=True,
            )
            return
        self.heats_config["max"] = max_heat
        self.heats_config["degradation"] = degradation
        self.heats_config["reset_after_punishment"] = reset_after_punishment
        await self.module.config_value(self.guild).heats.set(self.heats_config)
        await self.view._message.edit(embed=await self.view.get_embed(), view=self.view)


class ConfigureStrikeDurationsModal(discord.ui.Modal):
    def __init__(
        self,
        module: AutoModModule,
        guild: discord.Guild,
        view: discord.ui.View,
        strike_durations_config: typing.Dict[str, typing.Union[str, int]],
    ) -> None:
        self.module: AutoModModule = module
        self.guild: discord.Guild = guild
        self.view: discord.ui.View = view
        self.strike_durations_config: typing.Dict[
            str, typing.Union[str, int]
        ] = strike_durations_config
        super().__init__(title=_("Configure Strike Durations"))
        self.regular: discord.ui.TextInput = discord.ui.TextInput(
            label=_("Regular Strike Duration:"),
            style=discord.TextStyle.short,
            default=str(strike_durations_config["regular"]),
            required=True,
        )
        self.add_item(self.regular)
        self.severe: discord.ui.TextInput = discord.ui.TextInput(
            label=_("Severe Strike Duration (3 strikes +):"),
            style=discord.TextStyle.short,
            default=str(strike_durations_config["severe"]),
            required=True,
        )
        self.add_item(self.severe)
        self.auto_multiplier: discord.ui.TextInput = discord.ui.TextInput(
            label=_("Auto Multiplier (1 severe strike +):"),
            style=discord.TextStyle.short,
            default=str(strike_durations_config["auto_multiplier"]),
            required=True,
        )
        self.add_item(self.auto_multiplier)
        self.individual_timeout_mute: discord.ui.TextInput = discord.ui.TextInput(
            label=_("Individual Timeout/Mute Duration (e.g., 1h):"),
            style=discord.TextStyle.short,
            default=str(strike_durations_config["individual_timeout_mute"]),
            required=True,
        )
        self.add_item(self.individual_timeout_mute)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        try:
            regular = self.regular.value
            severe = self.severe.value
            individual_timeout_mute = self.individual_timeout_mute.value
            await DurationConverter.convert(None, regular)
            await DurationConverter.convert(None, severe)
            await DurationConverter.convert(None, individual_timeout_mute)
        except commands.BadArgument as e:
            await interaction.followup.send(
                _("Invalid duration: {error}.").format(error=str(e)),
                ephemeral=True,
            )
            return
        try:
            auto_multiplier = int(self.auto_multiplier.value)
        except ValueError as e:
            await interaction.followup.send(
                _("Invalid auto multiplier: {error}.").format(error=str(e)),
                ephemeral=True,
            )
            return
        self.strike_durations_config["regular"] = regular
        self.strike_durations_config["severe"] = severe
        self.strike_durations_config["auto_multiplier"] = auto_multiplier
        self.strike_durations_config["individual_timeout_mute"] = individual_timeout_mute
        await self.module.config_value(self.guild).strike_durations.set(
            self.strike_durations_config
        )
        await self.view._message.edit(embed=await self.view.get_embed(), view=self.view)


class ConfigureFilterCategoryView(discord.ui.View):
    def __init__(
        self,
        module: AutoModModule,
        guild: discord.Guild,
        parent_view: discord.ui.View,
        category: str,
    ) -> None:
        super().__init__(timeout=None)
        self.module: AutoModModule = module
        self.guild: discord.Guild = guild
        self.category: str = category
        self.parent_view: discord.ui.View = parent_view
        self._message: discord.Message = None

        self.configure_filter_select.placeholder = _("Select a filter to configure...")
        self.configure_filter_select.options = [
            discord.SelectOption(
                emoji=filter["emoji"],
                label=filter["name"],
                value=filter["value"],
            )
            for filter in AUTO_MOD_FILTERS[self.category]["filters"]
        ]

    async def start(self, interaction: discord.Interaction) -> None:
        self._message: discord.Message = await interaction.followup.send(
            embed=await self.get_embed(),
            view=self,
            ephemeral=True,
            wait=True,
        )
        self.module.cog.views[self._message] = self

    async def get_embed(self) -> discord.Embed:
        config = await self.module.config_value(self.guild)()
        category = AUTO_MOD_FILTERS[self.category]
        embed: discord.Embed = discord.Embed(
            title=_("Configure {emoji} {category_name} Filters").format(
                emoji=category["emoji"],
                category_name=category["name"],
            ),
            description="\n".join(
                f"**{'✅' if (filter_config := config['filters'][self.category][filter['value']])['enabled'] else '❌'} {filter['emoji']} {filter['name']}**"
                + (
                    _("\n- Added Heat: **{added_heat}%**").format(
                        added_heat=filter_config["added_heat"]
                    )
                    if "added_heat" in filter_config
                    else ""
                )
                + (
                    (
                        "\n"
                        + "\n".join(
                            f"- {key.replace('_', ' ').title()}: **{value}%**"
                            for key, value in filter_config["specific_heats"].items()
                        )
                    )
                    if "specific_heats" in filter_config
                    else ""
                )
                + (
                    (
                        "\n"
                        + "\n".join(
                            f"- {key.replace('_', ' ').title()}: "
                            + (
                                ("✅" if filter_config[key] else "❌")
                                if isinstance(filter_config[key], bool)
                                else (
                                    str(filter_config[key])
                                    if not isinstance(filter_config[key], typing.List)
                                    else _("[{count} item{s}]").format(
                                        count=len(filter_config[key]),
                                        s="" if len(filter_config[key]) == 1 else "s",
                                    )
                                )
                            )
                            for key, __ in filter["params"]
                            if key in filter_config
                        )
                    )
                    if "params" in filter
                    else ""
                )
                + _("\n- Individual Action: {action}").format(
                    action=filter_config["action"].title()
                    if filter_config["action"]
                    else _("None")
                )
                for filter in AUTO_MOD_FILTERS[self.category]["filters"]
            ),
        )
        first_state = list(config["filters"][self.category].values())[0]["enabled"]
        if all(f["enabled"] == first_state for f in config["filters"][self.category].values()):
            self.toggle_filter_category.label = (
                _("Enable All") if not first_state else _("Disable All")
            )
            self.toggle_filter_category.style = (
                discord.ButtonStyle.success if not first_state else discord.ButtonStyle.danger
            )
        else:
            self.toggle_filter_category.label = _("Toggle All")
            self.toggle_filter_category.style = discord.ButtonStyle.secondary
        return embed

    async def on_timeout(self) -> None:
        try:
            await self._message.delete()
        except discord.HTTPException:
            pass

    @discord.ui.button(label="Toggle All")
    async def toggle_filter_category(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        config = await self.module.config_value(self.guild)()
        new_state = not list(config["filters"][self.category].values())[0]["enabled"]
        for filter in config["filters"][self.category].values():
            filter["enabled"] = new_state
        await self.module.config_value(self.guild).set(config)
        await interaction.response.send_message(
            _("✅ All {category_name} filters have been {state}.").format(
                category_name=AUTO_MOD_FILTERS[self.category]["name"],
                state=_("enabled") if new_state else _("disabled"),
            ),
            ephemeral=True,
        )
        await self._message.edit(
            embed=await self.get_embed(),
            view=self,
        )
        await self.parent_view._message.edit(
            embed=await self.parent_view.get_embed(),
            view=self.parent_view,
        )

    @discord.ui.select(placeholder="Select a filter to configure...")
    async def configure_filter_select(
        self, interaction: discord.Interaction, select: discord.ui.Select
    ) -> None:
        filter = next(
            (
                f
                for f in AUTO_MOD_FILTERS[self.category]["filters"]
                if f["value"] == select.values[0]
            ),
        )
        filter_config = (await self.module.config_value(self.guild)())["filters"][self.category][
            filter["value"]
        ]
        await interaction.response.send_modal(
            ConfigureFilterModal(
                self.module,
                self.guild,
                self.parent_view,
                self,
                self.category,
                filter,
                filter_config,
            )
        )


class ConfigureFilterModal(discord.ui.Modal):
    def __init__(
        self,
        module: AutoModModule,
        guild: discord.Guild,
        view: discord.ui.View,
        category_view: discord.ui.View,
        category: str,
        filter: dict,
        filter_config: dict,
    ) -> None:
        self.module: AutoModModule = module
        self.guild: discord.Guild = guild
        self.view: discord.ui.View = view
        self.category_view: discord.ui.View = category_view
        self.category: str = category
        self.filter = filter
        self.filter_config = filter_config
        super().__init__(
            title=f"{self.filter['emoji']} {self.filter['name']}"[:45],
        )
        self.enabled: discord.ui.TextInput = discord.ui.TextInput(
            label=_("Enabled:"),
            style=discord.TextStyle.short,
            default=str(filter_config["enabled"]),
            required=True,
        )
        self.add_item(self.enabled)
        if "added_heat" in filter_config:
            self.added_heat: discord.ui.TextInput = discord.ui.TextInput(
                label=_("Added Heat:"),
                style=discord.TextStyle.short,
                default=str(filter_config["added_heat"]),
                required=True,
            )
            self.add_item(self.added_heat)
        if "specific_heats" in filter_config:
            for key, value in filter_config["specific_heats"].items():
                setattr(
                    self,
                    f"specific_heat_{key}",
                    discord.ui.TextInput(
                        label=_("Specific Heat for {key}:").format(key=key),
                        style=discord.TextStyle.short,
                        default=str(value),
                        required=True,
                    ),
                )
                self.add_item(getattr(self, f"specific_heat_{key}"))
        if "params" in filter:
            for key, default_value in filter["params"]:
                if key not in filter_config:
                    continue
                setattr(
                    self,
                    f"param_{key}",
                    discord.ui.TextInput(
                        label=f"{key.replace('_', ' ').title()}{' (one per line)' if isinstance(default_value, typing.List) else ''}:",
                        style=discord.TextStyle.short
                        if not isinstance(default_value, typing.List)
                        else discord.TextStyle.paragraph,
                        default=str(filter_config[key])
                        if not isinstance(default_value, typing.List)
                        else "\n".join(str(v) for v in filter_config[key]),
                        required=not isinstance(default_value, typing.List),
                    ),
                )
                self.add_item(getattr(self, f"param_{key}"))
        self.action: discord.ui.TextInput = discord.ui.TextInput(
            label=_("Action ({actions}):").format(
                actions="/".join([action["value"] for action in POSSIBLE_ACTIONS])
            ),
            style=discord.TextStyle.short,
            default=str(filter_config["action"]) if filter_config["action"] is not None else None,
            required=False,
        )
        self.add_item(self.action)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        self.filter_config["enabled"] = self.enabled.value.lower() in ("true", "yes", "1")
        if "added_heat" in self.filter_config:
            try:
                self.filter_config["added_heat"] = float(self.added_heat.value)
            except ValueError as e:
                await interaction.followup.send(
                    _("Invalid added heat value: {error}").format(error=str(e)),
                    ephemeral=True,
                )
                return
        if "specific_heats" in self.filter_config:
            for key in self.filter_config["specific_heats"]:
                field = getattr(self, f"specific_heat_{key}")
                try:
                    self.filter_config["specific_heats"][key] = float(field.value)
                except ValueError as e:
                    await interaction.followup.send(
                        _("Invalid specific heat value for {key}: {error}").format(
                            key=key, error=str(e)
                        ),
                        ephemeral=True,
                    )
                    return
        for key, default_value in self.filter.get("params", []):
            field = getattr(self, f"param_{key}")
            if isinstance(default_value, typing.List):
                if field_value := field.value.strip():
                    try:
                        self.filter_config[key] = [
                            v.strip() for v in field_value.split("\n") if v.strip()
                        ]
                    except ValueError as e:
                        await interaction.followup.send(
                            _("Invalid value for {key}: {error}.").format(key=key, error=str(e)),
                            ephemeral=True,
                        )
                        return
                else:
                    self.filter_config[key] = []
            elif isinstance(default_value, bool):
                self.filter_config[key] = field.value.lower() in ("true", "yes", "1")
            else:
                try:
                    self.filter_config[key] = type(default_value)(field.value)
                except ValueError as e:
                    await interaction.followup.send(
                        _("Invalid value for {key}: {error}.").format(key=key, error=str(e)),
                        ephemeral=True,
                    )
                    return
        action_value = self.action.value.strip().lower()
        if action_value in ("", "none"):
            self.filter_config["action"] = None
        elif (action := self.action.value.lower()) not in [
            action["value"] for action in POSSIBLE_ACTIONS
        ]:
            await interaction.followup.send(
                _("Invalid action: `{action}`. Possible actions are: {actions}").format(
                    action=action,
                    actions="/".join([action["value"] for action in POSSIBLE_ACTIONS]),
                ),
                ephemeral=True,
            )
            return
        else:
            self.filter_config["action"] = action_value
        await self.module.config_value(self.guild).filters.set_raw(
            self.category, self.filter["value"], value=self.filter_config
        )
        try:
            await self.category_view._message.edit(
                embed=await self.category_view.get_embed(),
                view=self.category_view,
            )
        except discord.HTTPException:
            pass
        await self.view._message.edit(embed=await self.view.get_embed(), view=self.view)

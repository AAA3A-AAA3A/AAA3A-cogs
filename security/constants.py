from redbot.core import commands  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import datetime

from enum import Enum


class Levels(Enum):
    ME = 0
    OWNER = 1
    EXTRA_OWNER = 2
    TRUSTED_ADMIN = 3

    ADMIN = 4
    BOT = 5
    MODERATOR = 6

    MEMBER = 7
    NEW = 8


class Colors(Enum):
    QUARANTINE: discord.Color = discord.Color.dark_embed()
    UNQUARANTINE: discord.Color = discord.Color.green()
    TIMEOUT: discord.Color = discord.Color.orange()
    MUTE: discord.Color = discord.Color.orange()
    KICK: discord.Color = discord.Color.red()
    BAN: discord.Color = discord.Color.red()
    NOTIFY: discord.Color = discord.Color.gold()
    WHITELIST: discord.Color = discord.Color.light_embed()
    REPORTS: discord.Color = discord.Color.blue()
    DANK_POOL_PROTECTION: discord.Color = discord.Color.dark_gold()
    UNAUTHORIZED_TEXT_CHANNEL_DELETIONS: discord.Color = discord.Color.dark_red()


class MemberEmojis(Enum):
    ME = "🔥"
    OWNER = "👑"
    EXTRA_OWNER = "👑"
    TRUSTED_ADMIN = "🛡️"
    ADMIN = "👮"
    MODERATOR = "🛠️"
    BOT = "🤖"
    MEMBER = "👤"
    NEW = "🆕"


class Emojis(Enum):
    QUARANTINE = "🚨"
    UNQUARANTINE = "✅"
    TIMEOUT = "⏳"
    MUTE = "🔇"
    KICK = "👢"
    BAN = "🔨"
    NOTIFY = "🔍"
    ISSUED_BY = "🛡️"
    REASON = "📝"
    LOGS = "📂"
    WHITELIST = "📋"

    JOIN_GATE = "🚪"
    AUTO_MOD = "♨️"
    REPORTS = "📑"
    LOGGING = "📜"
    ANTI_NUKE = "💥"
    PROTECTED_ROLES = "☢️"
    DANK_POOL_PROTECTION = "💰"
    LOCKDOWN = "🔒"
    ANTI_IMPERSONATION = "👮"
    UNAUTHORIZED_TEXT_CHANNEL_DELETIONS = "🚫"
    SENTINEL_RELAY = "🛰️"

    MEMBER = "👤"
    ROLE = "🎭"
    CHANNEL = "#️⃣"
    THREAD = "🧵"
    WEBHOOK = "🪝"
    MESSAGE = "💬"
    EMOJI = "😀"
    STICKER = "🏷️"
    SCHEDULED_EVENT = "📅"

    SPAM = "🗯️"
    SIMILAR_MESSAGE = "🔁"
    NEW_LINES = "↩️"
    ZALGO_CHARACTERS = "🌀"
    CHARACTERS = "🔤"
    PING = "🔔"
    EVERYONE_HERE = "📣"
    LINK = "🔗"
    IMAGE_VIDEO = "🖼️"
    FILE = "📁"
    ADVERTISING = "📢"
    STEAM_SCAM_LINK = "🎮"
    NSFW = "🔞"
    DISGUISED_LINK = "🕵️"
    BLACKLISTED_LINK = "🚫"
    WORD_BLACKLIST = "🚷"
    WORD_LISTS = "📋"
    BLACKLISTED_WORD = "🚫"

    VANITY_URL = "🔗"
    ONBOARDING = "🚀"


WHITELIST_TYPES: typing.List[
    typing.Dict[
        typing.Literal[
            "name", "emoji", "description", "value", "channels", "categories", "staff_allowed"
        ],
        typing.Union[str, bool],
    ]
] = [
    {
        "name": "Auto Mod - Spam Whitelist",
        "emoji": Emojis.SPAM.value,
        "description": "Spam messages anywhere except for mention spam.",
        "value": "auto_mod_spam",
        "members_roles": True,
        "channels": True,
        "categories": True,
        "webhooks": True,
        "staff_allowed": True,
    },
    {
        "name": "Auto Mod - Advertising Whitelist",
        "emoji": Emojis.ADVERTISING.value,
        "description": "Post invites to other Discord servers.",
        "value": "auto_mod_advertising",
        "members_roles": True,
        "channels": True,
        "categories": True,
        "webhooks": True,
        "staff_allowed": True,
    },
    {
        "name": "Auto Mod - Mention Whitelist",
        "emoji": Emojis.PING.value,
        "description": "Spam mention members and roles anywhere.",
        "value": "auto_mod_mentions",
        "members_roles": True,
        "channels": True,
        "categories": True,
        "webhooks": True,
        "staff_allowed": False,
    },
    {
        "name": "Auto Mod - @everyone, @here and main roles Mention Whitelist",
        "emoji": Emojis.EVERYONE_HERE.value,
        "description": "Mention @everyone, @here and main roles anywhere, or spam mention them.",
        "value": "auto_mod_everyone_here_mentions",
        "members_roles": True,
        "channels": True,
        "categories": True,
        "webhooks": True,
        "staff_allowed": False,
    },
    {
        "name": "Logging - Edited/Deleted Message Log Whitelist",
        "emoji": Emojis.MESSAGE.value,
        "description": "Edit and delete messages without being logged in the message logs.",
        "value": "logging_message_log",
        "members_roles": True,
        "channels": True,
        "categories": True,
        "webhooks": True,
        "staff_allowed": False,
    },
    {
        "name": "Logging - Channel Update & Overwrites Log Whitelist",
        "emoji": Emojis.CHANNEL.value,
        "description": "Edit channels and their overwrites without being logged.",
        "value": "logging_channel_update_overwrites_log",
        "members_roles": False,
        "channels": True,
        "categories": True,
        "webhooks": False,
        "staff_allowed": False,
    },
    {
        "name": "Logging - Reaction Log Whitelist",
        "emoji": Emojis.EMOJI.value,
        "description": "Add and remove reactions without being logged.",
        "value": "logging_reaction_log",
        "members_roles": True,
        "channels": True,
        "categories": True,
        "webhooks": True,
        "staff_allowed": True,
    },
    {
        "name": "Reports Whitelist",
        "emoji": Emojis.REPORTS.value,
        "description": "Can't be reported on the reports system.",
        "value": "reports",
        "members_roles": True,
        "channels": True,
        "categories": True,
        "webhooks": False,
        "staff_allowed": True,
    },
    {
        "name": "Quarantine Whitelist",
        "emoji": Emojis.QUARANTINE.value,
        "description": "CAUTION Be able to edit roles of members in quarantine.",
        "value": "quarantine",
        "members_roles": True,
        "channels": False,
        "categories": False,
        "webhooks": False,
        "staff_allowed": False,
    },
    {
        "name": "Anti Nuke - Kick & Ban Whitelist",
        "emoji": Emojis.ANTI_NUKE.value,
        "description": "CAUTION Be able to kick and ban members without being limited.",
        "value": "anti_nuke_filter_kick_ban",
        "members_roles": True,
        "channels": False,
        "categories": False,
        "webhooks": False,
        "staff_allowed": False,
    },
    {
        "name": "Anti Nuke - Role Creation Whitelist",
        "emoji": Emojis.ANTI_NUKE.value,
        "description": "CAUTION Be able to create roles without being limited.",
        "value": "anti_nuke_filter_role_creation",
        "members_roles": True,
        "channels": False,
        "categories": False,
        "webhooks": False,
        "staff_allowed": False,
    },
    {
        "name": "Anti Nuke - Role Deletion Whitelist",
        "emoji": Emojis.ANTI_NUKE.value,
        "description": "CAUTION Be able to delete roles without being limited.",
        "value": "anti_nuke_filter_role_deletion",
        "members_roles": True,
        "channels": False,
        "categories": False,
        "webhooks": False,
        "staff_allowed": False,
    },
    {
        "name": "Anti Nuke - Channel Creation Whitelist",
        "emoji": Emojis.ANTI_NUKE.value,
        "description": "CAUTION Be able to create channels without being limited.",
        "value": "anti_nuke_filter_channel_creation",
        "members_roles": True,
        "channels": False,
        "categories": True,
        "webhooks": False,
        "staff_allowed": False,
    },
    {
        "name": "Anti Nuke - Channel Deletion Whitelist",
        "emoji": Emojis.ANTI_NUKE.value,
        "description": "CAUTION Be able to delete channels without being limited.",
        "value": "anti_nuke_filter_channel_deletion",
        "members_roles": True,
        "channels": True,
        "categories": False,  # A member could change the category of a channel...
        "webhooks": False,
        "staff_allowed": False,
    },
    {
        "name": "Anti Nuke - Webhook Creation Whitelist",
        "emoji": Emojis.ANTI_NUKE.value,
        "description": "CAUTION Be able to create webhooks without being limited.",
        "value": "anti_nuke_filter_webhook_creation",
        "members_roles": True,
        "channels": True,
        "categories": True,
        "webhooks": False,
        "staff_allowed": False,
    },
    {
        "name": "Anti Nuke - Webhook Deletion Whitelist",
        "emoji": Emojis.ANTI_NUKE.value,
        "description": "CAUTION Be able to delete webhooks without being limited.",
        "value": "anti_nuke_filter_webhook_deletion",
        "members_roles": True,
        "channels": False,
        "categories": False,
        "webhooks": True,
        "staff_allowed": False,
    },
    {
        "name": "Anti Nuke - Emoji Creation Whitelist",
        "emoji": Emojis.ANTI_NUKE.value,
        "description": "CAUTION Be able to create emojis without being limited.",
        "value": "anti_nuke_filter_emoji_creation",
        "members_roles": True,
        "channels": False,
        "categories": False,
        "webhooks": False,
        "staff_allowed": False,
    },
    {
        "name": "Anti Nuke - Emoji Deletion Whitelist",
        "emoji": Emojis.ANTI_NUKE.value,
        "description": "CAUTION Be able to delete emojis without being limited.",
        "value": "anti_nuke_filter_emoji_deletion",
        "members_roles": True,
        "channels": False,
        "categories": False,
        "webhooks": False,
        "staff_allowed": False,
    },
    {
        "name": "All Protected Roles Whitelist",
        "emoji": Emojis.PROTECTED_ROLES.value,
        "description": "CAUTION Be able to get and give any protected role.",
        "value": "protected_roles",
        "members_roles": True,
        "channels": False,
        "categories": False,
        "webhooks": False,
        "staff_allowed": False,
    },
    {
        "name": "Dank Pool Protection Whitelist",
        "emoji": Emojis.DANK_POOL_PROTECTION.value,
        "description": "CAUTION Bypass any option which prevents Dank Pool abuse.",
        "value": "dank_pool_protection",
        "members_roles": True,
        "channels": True,
        "categories": True,
        "webhooks": True,
        "staff_allowed": False,
    },
    {
        "name": "Lockdown Whitelist",
        "emoji": Emojis.LOCKDOWN.value,
        "description": "CAUTION Bypass any mode of lockdown when it is active.",
        "value": "lockdown",
        "members_roles": True,
        "channels": True,
        "categories": True,
        "webhooks": True,
        "staff_allowed": False,
    },
    {
        "name": "Anti Impersonation Whitelist",
        "emoji": Emojis.ANTI_IMPERSONATION.value,
        "description": "CAUTION Be able to bypass anti impersonation checks.",
        "value": "anti_impersonation",
        "members_roles": True,
        "channels": False,
        "categories": False,
        "webhooks": False,
        "staff_allowed": False,
    },
    {
        "name": "Unauthorized Text Channel Deletions Whitelist",
        "emoji": Emojis.UNAUTHORIZED_TEXT_CHANNEL_DELETIONS.value,
        "description": "CAUTION Be able to delete text channels without being logged.",
        "value": "unauthorized_text_channel_deletions",
        "members_roles": True,
        "channels": True,
        "categories": False,  # A member could change the category of a channel...
        "webhooks": False,
        "staff_allowed": False,
    },
]


class WhitelistTypeConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> str:
        cog = ctx.bot.get_cog("Security")
        for whitelist_type in WHITELIST_TYPES:
            value = whitelist_type["value"]
            if argument == value:
                return value
            if (
                (
                    module_key := next(
                        m
                        for m in cog.modules
                        if value.startswith(m)
                    )
                ) is not None
                and argument == value.removeprefix(f"{module_key}_")
            ):
                return value
        raise commands.BadArgument(f"Unknown whitelist type: {argument}")


POSSIBLE_ACTIONS: typing.List[
    typing.Dict[typing.Literal["name", "emoji", "value", "permission"], str]
] = [
    {
        "name": "Timeout",
        "emoji": Emojis.TIMEOUT.value,
        "value": "timeout",
        "permission": "moderate_members",
    },
    {
        "name": "Mute",
        "emoji": Emojis.MUTE.value,
        "value": "mute",
        "permission": "manage_roles",
    },
    {
        "name": "Kick",
        "emoji": Emojis.KICK.value,
        "value": "kick",
        "permission": "kick_members",
    },
    {
        "name": "Ban",
        "emoji": Emojis.BAN.value,
        "value": "ban",
        "permission": "ban_members",
    },
    {
        "name": "Quarantine",
        "emoji": Emojis.QUARANTINE.value,
        "value": "quarantine",
        "permission": "manage_roles",
    },
]


DANGEROUS_PERMISSIONS: typing.List[str] = [
    "administrator",
    "manage_guild",
    "manage_roles",
    "manage_channels",
    "manage_webhooks",
    "manage_emojis_and_stickers",
    "manage_messages",
    "manage_threads",
    "moderate_members",
]


def get_correct_timeout_duration(member: discord.Member, duration: datetime.timedelta) -> datetime.timedelta:
    if member.is_timed_out():
        duration += member.timed_out_until - datetime.datetime.now(datetime.timezone.utc)
    return min(duration, datetime.timedelta(days=28))


def get_non_animated_asset(asset: typing.Optional[discord.Asset] = None) -> typing.Optional[str]:
    if asset is None:
        return None
    if not asset.is_animated():
        return asset
    return discord.Asset(
        asset._state,
        url=asset.url.replace("/a_", "/").replace(".gif", ".png"),
        key=asset.key.removeprefix("a_"),
        animated=False,
    )


def clean_backticks(text: str) -> str:
    return text.replace("`", "\u02CB")

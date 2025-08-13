from redbot.core import commands  # isort:skip
from redbot.core.bot import Red  # isort:skip
from redbot.core.i18n import Translator  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

from redbot.core.utils.chat_formatting import box

import datetime
from dataclasses import dataclass, asdict

from ..constants import Emojis, Colors
from ..views import ToggleModuleButton
from .module import Module

_: Translator = Translator("Security", __file__)


def convert_amount(argument: str) -> int:
    argument = argument.replace(",", "")
    try:
        return int(argument)
    except ValueError:
        try:
            return int(float(argument[:-1]) * (1000 ** ("kmbt".index(argument[-1].lower()) + 1)))
        except (ValueError, IndexError):
            raise ValueError(
                _("Invalid amount format. Use a number or a shorthand like `1k`, `2m`, etc.")
            )


async def get_or_fetch_member_or_user(bot: Red, guild: discord.Guild, user_id: int) -> typing.Optional[typing.Union[discord.Member, discord.User]]:
    if (member := guild.get_member(user_id)) is not None:
        return member
    try:
        return await bot.get_or_fetch_user(user_id)
    except discord.HTTPException:
        return None


DANK_MEMER_BOT_ID: int = 270904126974590976

DANK_POOL_PROTECTION_OPTIONS: typing.List[
    typing.Dict[
        typing.Literal["name", "emoji", "description", "value", "check", "reason"],
        typing.Union[
            str,
            typing.Callable[
                [discord.Message, typing.Dict[str, typing.Any], typing.Dict[str, typing.Any]], bool
            ],
            typing.Callable[[], str],
        ],
    ]
] = [
    {
        "name": "Self Payment Protection",
        "emoji": "🙅",
        "description": "Prevent members from paying themselves.",
        "value": "self_payment",
        "check": lambda message, raw_message, config: (
            message._interaction.name == "serverevents payout"
            and "Pending Confirmation" in raw_message["components"][0]["components"][0]["content"]
            and int(
                raw_message["components"][0]["components"][2]["content"]
                .split("<@")[1]
                .split(">")[0]
            )
            == message.interaction_metadata.user.id
        ),
        "reason": lambda: _("**Dank Pool Protection** - Attempted to pay themselves."),
    },
    {
        "name": "High Amount Payment Protection",
        "emoji": "💸",
        "description": "Prevent members from making payments over a certain amount.",
        "value": "high_amount_payment",
        "check": lambda message, raw_message, config: (
            message._interaction.name == "serverevents payout"
            and "Pending Confirmation" in raw_message["components"][0]["components"][0]["content"]
            and convert_amount(
                raw_message["components"][0]["components"][2]["content"]
                .split("**\u23e3 ")[1]
                .split("**")[0]
            )
            > config["high_amount_limit"]
        ),
        "reason": lambda: _("**Dank Pool Protection** - Attempted to pay over the limit."),
    },
    {
        "name": "Rapid Payout Protection",
        "emoji": "⏱️",
        "description": "Prevent members from making too many payouts in a short period.",
        "value": "rapid_payout",
        "reason": lambda: _(
            "**Dank Pool Protection** - Attempted to make too many payouts in a short period."
        ),
    },
    {
        "name": "Payout Cooldown",
        "emoji": "⏳",
        "description": "Prevent members from making consecutive payouts too quickly.",
        "value": "payout_cooldown",
        "reason": lambda: _(
            "**Dank Pool Protection** - Attempted to make a payout too quickly after the last one."
        ),
    },
    {
        "name": "Unauthorized Payout",
        "emoji": "🚫",
        "description": "Detect members who try to execute payout command without permission.",
        "value": "unauthorized_payout",
        "check": lambda message, raw_message, config: (
            message._interaction.name == "serverevents payout"
            and "Only event managers can payout from the server's pool!"
            in raw_message["components"][0]["components"][0]["content"]
        ),
        "reason": lambda: _(
            "**Dank Pool Protection** - Attempted to execute payout command without permission."
        ),
    },
    {
        "name": "Unauthorized Event",
        "emoji": "🏦",
        "description": "Detect members who try to execute event command without permission.",
        "value": "unauthorized_event",
        "check": lambda message, raw_message, config: (
            message._interaction.name.startswith("serverevents run")
            and "Only event managers can run events!"
            in raw_message["components"][0]["components"][0]["content"]
        ),
        "reason": lambda: _(
            "**Dank Pool Protection** - Attempted to execute event command without permission."
        ),
    },
]


@dataclass
class Payout:
    issued_at_timestamp: int
    channel_id: int
    message_id: int
    quantity: int
    item: typing.Optional[str] = None
    recipient_id: typing.Optional[int] = None

    issued_by_id: typing.Optional[int] = None

    def to_dict(self) -> typing.Dict[str, typing.Union[int, str]]:
        d = asdict(self)
        del d["issued_by_id"]
        return d

    @classmethod
    def from_message(
        cls,
        message: discord.Message,
        quantity: int,
        item: typing.Optional[str] = None,
        recipient_id: typing.Optional[int] = None,
        issued_by_id: typing.Optional[int] = None,
    ) -> "Payout":
        return cls(
            issued_at_timestamp=int(message.created_at.timestamp()),
            channel_id=message.channel.id,
            message_id=message.id,
            quantity=quantity,
            item=item,
            recipient_id=recipient_id,
            issued_by_id=issued_by_id,
        )

    @property
    def issued_at(self) -> datetime.datetime:
        return datetime.datetime.fromtimestamp(
            self.issued_at_timestamp, tz=datetime.timezone.utc
        )

    @property
    def display_amount(self) -> str:
        return f"{'⏣ ' if self.item is None else ''}{format_amount(self.quantity)}{' ' + self.item if self.item is not None else ''}"

    def get_jump_url(self, guild: discord.Guild) -> str:
        return discord.PartialMessage(
            channel=discord.PartialMessageable(state=guild._state, id=self.channel_id, guild_id=guild.id),
            id=self.message_id,
        ).jump_url

    async def get_issued_by(self, bot: Red, guild: discord.Guild) -> typing.Optional[typing.Union[discord.Member, discord.User]]:
        if self.issued_by_id is None:
            return None
        return await get_or_fetch_member_or_user(bot, guild, self.issued_by_id)

    async def get_recipient(self, bot: Red, guild: discord.Guild) -> typing.Optional[typing.Union[discord.Member, discord.User]]:
        if self.recipient_id is None:
            return None
        return await get_or_fetch_member_or_user(bot, guild, self.recipient_id)

    async def get_embed(self, cog: commands.Cog, guild: discord.Guild) -> discord.Embed:
        embed: discord.Embed = discord.Embed(
            title=_("New Dank Memer Payout"),
            color=Colors.DANK_POOL_PROTECTION.value,
            timestamp=self.issued_at,
        )
        embed.description = _("**{emoji} Amount**: {amount}").format(emoji=Emojis.DANK_POOL_PROTECTION.value, amount=self.display_amount)
        if (issued_by := await self.get_issued_by(cog.bot, guild)) is not None:
            embed.description += (
                _("\n**{emoji} Issued By**: {issued_by.mention} (`{issued_by}`)").format(emoji=Emojis.ISSUED_BY.value, issued_by=issued_by)
                + (
                    f" {await cog.get_member_emoji(issued_by)}"
                    if isinstance(issued_by, discord.Member)
                    else ""
                )
            )
            embed.set_author(
                name=issued_by.display_name,
                icon_url=issued_by.display_avatar.url,
            )
        if (recipient := await self.get_recipient(cog.bot, guild)) is not None:
            embed.description += (
                _("\n**{emoji} Recipient**: {recipient.mention} (`{recipient}`)").format(emoji=Emojis.MEMBER.value, recipient=recipient)
                + (
                    f" {await cog.get_member_emoji(recipient)}"
                    if isinstance(recipient, discord.Member)
                    else ""
                )
            )
        if self.recipient_id is not None:
            embed.description += f"\n{box(await self.get_slash_name(cog.bot))}"
        embed.description += _("\n**{emoji} Message**: {message_jump_url}").format(
            emoji=Emojis.MESSAGE.value, message_jump_url=self.get_jump_url(guild)
        )
        embed.set_footer(text=guild.name, icon_url=guild.icon) 
        return embed

    async def get_slash_name(self, bot: Red) -> str:
        try:
            recipient = str(await bot.get_or_fetch_user(self.recipient_id))
        except discord.HTTPException:
            recipient = str(self.recipient_id)
        return f"/serverevents payout user: {recipient} quantity: {self.quantity:,}" + (f" item: {self.item}" if self.item else "")


class DankPoolProtectionModule(Module):
    name = "Dank Pool Protection"
    emoji = Emojis.DANK_POOL_PROTECTION.value
    description = "Protect your server's Dank Memer pool from abuse."
    default_config = {
        "enabled": False,
        "payout_logs_channel": None,
        "quarantine": True,
        "options": {option["value"]: True for option in DANK_POOL_PROTECTION_OPTIONS},
        "high_amount_limit": 1_000_000_000,
        "rapid_payout": {
            "minute_limit": 5,
            "hour_limit": 20,
        },
        "payout_cooldown": 10,
    }
    configurable_by_trusted_admins = False

    def __init__(self, cog: commands.Cog) -> None:
        super().__init__(cog)

    async def load(self) -> None:
        self.cog.bot.add_listener(self.on_payout_message, "on_message")
        self.cog.bot.add_listener(self.on_confirmation_message, "on_message")

    async def unload(self) -> None:
        self.cog.bot.remove_listener(self.on_payout_message, "on_message")
        self.cog.bot.remove_listener(self.on_confirmation_message, "on_message")

    async def get_status(
        self, guild: discord.Guild, check_enabled: bool = True
    ) -> typing.Tuple[typing.Literal["✅", "⚠️", "❌"], str, str]:
        config = await self.config_value(guild)()
        if not config["enabled"] and check_enabled:
            return "❌", _("Disabled"), _("Dank Pool Protection is currently disabled.")
        if (
            (payout_logs_channel_id := config["payout_logs_channel"]) is not None
            and (payout_logs_channel := guild.get_channel(payout_logs_channel_id)) is not None
        ) and (
            not (channel_permissions := payout_logs_channel.permissions_for(guild.me)).view_channel
            or not channel_permissions.send_messages
            or not channel_permissions.embed_links
        ):
            return (
                "⚠️",
                _("Missing Permission(s)"),
                _(
                    "I need the `View Channel`, `Send Messages`, and `Embed Links` permissions in the logs channel to function properly."
                ),
            )
        if any(config["options"].values()):
            if not guild.me.guild_permissions.manage_messages:
                return (
                    "⚠️",
                    _("Missing Permission"),
                    _("I need the `Manage Messages` permission to function properly."),
                )
            if config["quarantine"] and not guild.me.guild_permissions.manage_roles:
                return (
                    "⚠️",
                    _("Missing Permission"),
                    _("I need the `Manage Roles` permission to quarantine members."),
                )
        return "✅", _("Enabled"), _("Dank Pool Protection is enabled and configured correctly.")

    async def get_settings(self, guild: discord.Guild, view: discord.ui.View):
        status = await self.get_status(guild)
        title = _("Security — {emoji} {name} {status}").format(
            emoji=self.emoji, name=self.name, status=status[0]
        )
        description = _("Protect your server's Dank Memer pool from abuse.")
        if status[0] == "⚠️":
            description += f"\n{status[0]} **{status[1]}**: {status[2]}"
        config = await self.config_value(guild)()
        payout_logs_channel = (
            payout_logs_channel
            if (payout_logs_channel_id := config["payout_logs_channel"]) is not None
            and (payout_logs_channel := guild.get_channel(payout_logs_channel_id)) is not None
            else None
        )
        description += _("\n\n**Logs Channel**: {payout_logs_channel}").format(
            payout_logs_channel=f"{payout_logs_channel.mention} (`{payout_logs_channel}`)" if payout_logs_channel is not None else _("Not set")
        )
        fields = []
        for option in DANK_POOL_PROTECTION_OPTIONS:
            fields.append(
                dict(
                    name=f"{option['emoji']} {option['name']}",
                    value=option["description"]
                    + _("\n**Enabled**: {enabled}").format(
                        enabled="✅" if config["options"][option["value"]] else "❌"
                    )
                    + (
                        _("\n**Limit**: ⏣ {limit}").format(
                            limit=f"{config['high_amount_limit']:,}"
                        )
                        if option["value"] == "high_amount_payment"
                        else (
                            _(
                                "\n**Minute Limit**: {minute_limit}\n**Hour Limit**: {hour_limit}"
                            ).format(
                                minute_limit=config["rapid_payout"]["minute_limit"],
                                hour_limit=config["rapid_payout"]["hour_limit"],
                            )
                            if option["value"] == "rapid_payout"
                            else (
                                _("\n**Cooldown**: {cooldown} seconds").format(
                                    cooldown=config["payout_cooldown"]
                                )
                                if option["value"] == "payout_cooldown"
                                else ""
                            )
                        )
                    ),
                    inline=True,
                )
            )

        components = [ToggleModuleButton(self, guild, view, config["enabled"])]

        payout_logs_channel_select: discord.ui.ChannelSelect = discord.ui.ChannelSelect(
            placeholder=_("Payout Logs Channel"),
            min_values=0,
            max_values=1,
            channel_types=[discord.ChannelType.text],
            default_values=[payout_logs_channel] if payout_logs_channel is not None else [],
        )

        async def payout_logs_channel_select_callback(interaction: discord.Interaction) -> None:
            selected = payout_logs_channel_select.values[0] if payout_logs_channel_select.values else None
            if selected:
                await self.config_value(guild).payout_logs_channel.set(selected.id)
                await interaction.response.send_message(
                    _("✅ {selected} set as the payout logs channel.").format(
                        selected=selected.mention
                    ),
                    ephemeral=True,
                )
            else:
                await self.config_value(guild).payout_logs_channel.clear()
                await interaction.response.send_message(
                    _("✅ The logs channel has been unset."),
                    ephemeral=True,
                )
            await view._message.edit(embed=await view.get_embed(), view=view)

        payout_logs_channel_select.callback = payout_logs_channel_select_callback
        components.append(payout_logs_channel_select)

        create_a_payout_logs_channel_button: discord.ui.Button = discord.ui.Button(
            label=_("Create a Payout Logs Channel"),
            style=discord.ButtonStyle.primary,
            disabled=not guild.me.guild_permissions.manage_channels,
        )

        async def create_payout_logs_channel_callback(interaction: discord.Interaction) -> None:
            await interaction.response.defer(ephemeral=True, thinking=True)
            channel = await guild.create_text_channel(
                name=_("💸・payout-logs"),
                topic=_("This channel is used for logging Dank Memer pool payouts."),
                overwrites={
                    guild.default_role: discord.PermissionOverwrite(
                        view_channel=False, send_messages=False
                    ),
                    guild.me: discord.PermissionOverwrite(
                        view_channel=True, send_messages=True, embed_links=True
                    ),
                },
                reason=_("Created by Security's Dank Pool Protection Module."),
            )
            await self.config_value(guild).payout_logs_channel.set(channel.id)
            await interaction.followup.send(
                _("✅ A new payout logs channel has been created: {channel.mention}.").format(
                    channel=channel
                ),
                ephemeral=True,
            )
            await view._message.edit(embed=await view.get_embed(), view=view)

        create_a_payout_logs_channel_button.callback = create_payout_logs_channel_callback
        components.append(create_a_payout_logs_channel_button)

        quarantine_button: discord.ui.Button = discord.ui.Button(
            label=_("Quarantine Automatically"),
            style=discord.ButtonStyle.success
            if config["quarantine"]
            else discord.ButtonStyle.danger,
            emoji=Emojis.QUARANTINE.value,
            row=3,
        )

        async def quarantine_callback(interaction: discord.Interaction) -> None:
            await interaction.response.defer()
            config["quarantine"] = not config["quarantine"]
            await self.config_value(guild).quarantine.set(config["quarantine"])
            await interaction.followup.send(
                _("Automatic Quarantine is now {status}.").format(
                    status="enabled" if config["quarantine"] else "disabled"
                ),
                ephemeral=True,
            )
            await view._message.edit(embed=await view.get_embed(), view=view)

        quarantine_button.callback = quarantine_callback
        components.append(quarantine_button)

        options_select: discord.ui.Select = discord.ui.Select(
            placeholder=_("Select Dank Pool Protection Options"),
            options=[
                discord.SelectOption(
                    emoji=option["emoji"],
                    label=option["name"],
                    value=option["value"],
                    default=config["options"][option["value"]],
                )
                for option in DANK_POOL_PROTECTION_OPTIONS
            ],
            min_values=0,
            max_values=len(DANK_POOL_PROTECTION_OPTIONS),
            row=4,
        )

        async def options_select_callback(interaction: discord.Interaction) -> None:
            await interaction.response.defer()
            for option in DANK_POOL_PROTECTION_OPTIONS:
                config["options"][option["value"]] = option["value"] in options_select.values
            await self.config_value(guild).options.set(config["options"])
            await view._message.edit(embed=await view.get_embed(), view=view)

        options_select.callback = options_select_callback
        components.append(options_select)

        configure_values_button: discord.ui.Button = discord.ui.Button(
            label=_("Configure Values"),
            style=discord.ButtonStyle.secondary,
            row=3,
        )

        async def configure_values_button_callback(interaction: discord.Interaction) -> None:
            await interaction.response.send_modal(ConfigureValuesModal(self, guild, view, config))

        configure_values_button.callback = configure_values_button_callback
        components.append(configure_values_button)

        return title, description, fields, components

    async def on_payout_message(self, message: discord.Message) -> None:
        if message.guild is None:
            return
        if not message.author.bot or message.author.id != DANK_MEMER_BOT_ID:
            return
        if message.interaction_metadata is None:
            return
        if message.content or message.embeds:
            return
        config = await self.config_value(message.guild)()
        if not config["enabled"]:
            return
        try:
            raw_message = await self.cog.bot.http.get_message(message.channel.id, message.id)
        except discord.HTTPException:
            return
        if (
            not raw_message["components"]
            or not raw_message["components"][0]["type"] == 17
            or not raw_message["components"][0]["components"]
            or "content" not in raw_message["components"][0]["components"][0]
        ):
            return
        description = raw_message["components"][0]["components"][0]["content"]
        if (
            not description.startswith("Successfully paid ")
            or not description.endswith(" from the server's pool!")
        ):
            return
        member_id = message.interaction_metadata.user.id
        member_payouts = await self.cog.config.member_from_ids(message.guild.id, member_id).payouts()
        thing = description.split("**")[1].split("**")[0]
        quantity = convert_amount(thing.removeprefix("⏣ ").split(" ")[0])
        item = None if thing.startswith("⏣ ") else " ".join(thing.split(" ")[2:])
        payout: Payout = Payout.from_message(
            message,
            quantity=quantity,
            item=item,
            recipient_id=(
                int(raw_message["referenced_message"]["mentions"][0]["id"])
                if raw_message.get("referenced_message", {}).get("mentions", []) else None
            ),
            issued_by_id=member_id,
        )
        member_payouts.append(payout.to_dict())
        await self.cog.config.member_from_ids(
            message.guild.id, member_id
        ).payouts.set(member_payouts)
        if (
            (payout_logs_channel_id := config["payout_logs_channel"]) is not None
            and (payout_logs_channel := message.guild.get_channel(payout_logs_channel_id)) is not None
            and (channel_permissions := payout_logs_channel.permissions_for(message.guild.me)).view_channel
            and channel_permissions.send_messages
            and channel_permissions.embed_links
        ):
            await payout_logs_channel.send(embed=await payout.get_embed(self.cog, message.guild))

    async def on_confirmation_message(self, message: discord.Message) -> None:
        if message.guild is None:
            return
        if not message.author.bot or message.author.id != DANK_MEMER_BOT_ID:
            return
        if message.interaction_metadata is None or message._interaction is None:
            return
        if message.content or message.embeds:
            return
        config = await self.config_value(message.guild)()
        if not config["enabled"]:
            return
        try:
            raw_message = await self.cog.bot.http.get_message(message.channel.id, message.id)
        except discord.HTTPException:
            return
        if (
            not raw_message["components"]
            or not raw_message["components"][0]["type"] == 17
            or not raw_message["components"][0]["components"]
            or "content" not in raw_message["components"][0]["components"][0]
        ):
            return
        member_id = message.interaction_metadata.user.id
        if (member := message.guild.get_member(member_id)) is None:
            try:
                member = await message.guild.fetch_member(member_id)
            except discord.HTTPException:
                return
        if await self.cog.is_whitelisted(
            member, "dank_pool_protection"
        ) or await self.cog.is_whitelisted(message.channel, "dank_pool_protection"):
            return
        log = _(
            "{member.mention} (`{member}`) executed `{slash_name}` ({jump_url}) {timestamp}."
        ).format(
            member=member,
            slash_name=message._interaction.name,
            jump_url=message.jump_url,
            timestamp=f"<t:{int(message.created_at.timestamp())}:R>",
        )
        last_payouts = [
            (
                datetime.datetime.fromtimestamp(last_payout["issued_at_timestamp"], tz=datetime.timezone.utc),
                _("{member.mention} (`{member}`) executed `{slash_name}` ({jump_url}) {timestamp}.").format(
                    member=member,
                    slash_name=await (payout := Payout(**last_payout)).get_slash_name(self.cog.bot),
                    jump_url=payout.get_jump_url(message.guild),
                    timestamp=f"<t:{int(message.created_at.timestamp())}:R>",
                ),
            )
            for last_payout in await self.cog.config.member(member).payouts()
        ]
        hour_ago, minute_ago = message.created_at - datetime.timedelta(hours=1), message.created_at - datetime.timedelta(minutes=1)
        for option in DANK_POOL_PROTECTION_OPTIONS:
            if not config["options"][option["value"]]:
                continue
            if option["value"] == "rapid_payout":
                if (
                    sum(
                        [
                            last_payout[0] >= hour_ago
                            for last_payout in last_payouts
                        ]
                    )
                    > config["rapid_payout"]["hour_limit"]
                    or sum(
                        [
                            last_payout[0] >= minute_ago
                            for last_payout in last_payouts
                        ]
                    )
                    > config["rapid_payout"]["minute_limit"]
                ):
                    logs = [log for (__, log) in last_payouts]
                    break
            elif option["value"] == "payout_cooldown":
                if (
                    last_payouts
                    and message.created_at - last_payouts[-1][0] < datetime.timedelta(seconds=config["payout_cooldown"])
                ):
                    logs = [log for (__, log) in last_payouts]
                    break
            elif option["check"](message, raw_message, config):
                logs = [log]
                break
        else:
            return
        try:
            await message.delete()
        except discord.HTTPException:
            pass
        reason = option["reason"]()
        if config["quarantine"]:
            await self.cog.quarantine_member(
                member=member,
                reason=reason,
                logs=logs,
            )
        else:
            await self.cog.send_modlog(
                action="notify",
                member=member,
                reason=reason,
                logs=logs,
            )


def format_amount(amount: int) -> str:
    if amount < 1000:
        return str(amount)
    for i, suffix in enumerate(["", "k", "m", "b", "t"]):
        if amount < 1000 ** (i + 1) or i == 3:
            num = round(amount / (1000**i), 1)
            if num % 1 == 0:
                return f"{int(num)}{suffix}"
            else:
                return f"{num:.1f}{suffix}"


class ConfigureValuesModal(discord.ui.Modal):
    def __init__(
        self,
        module: DankPoolProtectionModule,
        guild: discord.Guild,
        view: discord.ui.View,
        config: dict,
    ) -> None:
        self.module: DankPoolProtectionModule = module
        self.guild: discord.Guild = guild
        self.view: discord.ui.View = view
        self.config: dict = config
        super().__init__(title=_("Dank Pool Protection - Configure Values"))

        self.high_amount_limit: discord.ui.TextInput = discord.ui.TextInput(
            label=_("High Amount Payment Limit:"),
            style=discord.TextStyle.short,
            default=format_amount(config["high_amount_limit"]),
            required=True,
        )
        self.add_item(self.high_amount_limit)
        self.minute_limit: discord.ui.TextInput = discord.ui.TextInput(
            label=_("Rapid Payout Minute Limit:"),
            style=discord.TextStyle.short,
            default=str(config["rapid_payout"]["minute_limit"]),
            required=True,
        )
        self.add_item(self.minute_limit)
        self.hour_limit: discord.ui.TextInput = discord.ui.TextInput(
            label=_("Rapid Payout Hour Limit:"),
            style=discord.TextStyle.short,
            default=str(config["rapid_payout"]["hour_limit"]),
            required=True,
        )
        self.add_item(self.hour_limit)
        self.payout_cooldown: discord.ui.TextInput = discord.ui.TextInput(
            label=_("Payout Cooldown:"),
            style=discord.TextStyle.short,
            default=str(config["payout_cooldown"]),
            required=True,
        )
        self.add_item(self.payout_cooldown)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        try:
            high_amount_limit = convert_amount(self.high_amount_limit.value)
            if high_amount_limit < 1_000_000:
                raise ValueError(_("High amount limit must be at least **⏣ 1,000,000**."))
            minute_limit = int(self.minute_limit.value)
            if minute_limit < 1:
                raise ValueError(_("Minute limit must be at least **1**."))
            hour_limit = int(self.hour_limit.value)
            if hour_limit < 1:
                raise ValueError(_("Hour limit must be at least **1**."))
            payout_cooldown = int(self.payout_cooldown.value)
            if payout_cooldown < 2:
                raise ValueError(_("Payout cooldown must be at least **2 seconds**."))
        except ValueError as e:
            await interaction.followup.send(
                _("Invalid value: {error}").format(error=str(e)),
                ephemeral=True,
            )
            return
        self.config["high_amount_limit"] = high_amount_limit
        self.config["rapid_payout"]["minute_limit"] = minute_limit
        self.config["rapid_payout"]["hour_limit"] = hour_limit
        self.config["payout_cooldown"] = payout_cooldown
        await self.module.config_value(self.guild).high_amount_limit.set(high_amount_limit)
        await self.module.config_value(self.guild).rapid_payout.set(
            {
                "minute_limit": minute_limit,
                "hour_limit": hour_limit,
            }
        )
        await self.view._message.edit(embed=await self.view.get_embed(), view=self.view)

from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import datetime
from collections import defaultdict

from ..constants import Emojis
from ..views import ToggleModuleButton
from .module import Module

_: Translator = Translator("Security", __file__)


DANK_MEMER_BOT_ID: int = 270904126974590976

DANK_POOL_PROTECTION_OPTIONS: typing.List[typing.Dict[typing.Literal["name", "emoji", "description", "value", "check", "reason"], typing.Union[str, typing.Callable[[discord.Message, typing.Dict[str, typing.Any], typing.Dict[str, typing.Any]], bool], typing.Callable[[], str]]]] = [
    {
        "name": "Self Payment Protection",
        "emoji": "🙅",
        "description": "Prevent members from paying themselves.",
        "value": "self_payment",
        "check": lambda message, raw_message, config: (
            message.interaction.name == "serverevents payout"
            and "Pending Confirmation" in raw_message["components"][0]["components"][0]["content"]
            and int(raw_message["components"][0]["components"][2]["content"].split("<@")[1].split(">")[0]) == message.interaction_metadata.user.id
        ),
        "reason": lambda: _("**Dank Pool Protection** - Attempted to pay themselves."),
    },
    {
        "name": "High Amount Payment Protection",
        "emoji": "💸",
        "description": "Prevent members from making payments over a certain amount.",
        "value": "high_amount_payment",
        "check": lambda message, raw_message, config: (
            message.interaction.name == "serverevents payout"
            and "Pending Confirmation" in raw_message["components"][0]["components"][0]["content"]
            and int(raw_message["components"][0]["components"][2]["content"].split("**\u23e3 ")[1].split("**")[0].replace(",", "")) > config["high_amount_limit"]
        ),
        "reason": lambda: _("**Dank Pool Protection** - Attempted to pay over the limit."),
    },
    {
        "name": "Rapid Payout Protection",
        "emoji": "⏱️",
        "description": "Prevent members from making too many payouts in a short period.",
        "value": "rapid_payout",
        "reason": lambda: _("**Dank Pool Protection** - Attempted to make too many payouts in a short period."),
    },
    {
        "name": "Payout Cooldown",
        "emoji": "⏳",
        "description": "Prevent members from making consecutive payouts too quickly.",
        "value": "payout_cooldown",
        "reason": lambda: _("**Dank Pool Protection** - Attempted to make a payout too quickly after the last one."),
    },
    {
        "name": "Unauthorized Payout",
        "emoji": "🚫",
        "description": "Detect members who try to execute payout command without permission.",
        "value": "unauthorized_payout",
        "check": lambda message, raw_message, config: (
            message.interaction.name == "serverevents payout"
            and "Only event managers can payout from the server's pool!" in raw_message["components"][0]["components"][0]["content"]
        ),
        "reason": lambda: _("**Dank Pool Protection** - Attempted to execute payout command without permission."),
    },
    {
        "name": "Unauthorized Event",
        "emoji": "🏦",
        "description": "Detect members who try to execute event command without permission.",
        "value": "unauthorized_event",
        "check": lambda message, raw_message, config: (
            message.interaction.name.startswith("serverevents run")
            and "Only event managers can run events!" in raw_message["components"][0]["components"][0]["content"]
        ),
        "reason": lambda: _("**Dank Pool Protection** - Attempted to execute event command without permission."),
    },
]


class DankPoolProtectionModule(Module):
    name = "Dank Pool Protection"
    emoji = Emojis.DANK_POOL_PROTECTION.value
    description = "Protect your server's Dank Memer pool from abuse."
    default_config = {
        "enabled": False,
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
        self.payouts_cache: typing.Dict[
            discord.Guild,
            typing.Dict[
                discord.Member, typing.List[typing.Tuple[datetime.datetime, str]]
            ],
        ] = defaultdict(lambda: defaultdict(list))

    async def load(self) -> None:
        self.cog.bot.add_listener(self.on_message_without_command)

    async def unload(self) -> None:
        self.cog.bot.remove_listener(self.on_message_without_command)

    async def get_status(self, guild: discord.Guild) -> typing.Tuple[typing.Literal["✅", "⚠️", "❌"], str, str]:
        config = await self.config_value(guild)()
        if not config["enabled"]:
            return "❌", "Disabled", "Dank Pool Protection is currently disabled."
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
        return "✅", "Enabled", "Dank Pool Protection is enabled and configured correctly."

    async def get_settings(self, guild: discord.Guild, view: discord.ui.View):
        title = f"{self.emoji} {self.name} {(await self.get_status(guild))[0]}"
        description = "Protect your server's Dank Memer pool from abuse.\n"
        config = await self.config_value(guild)()
        fields = []
        for option in DANK_POOL_PROTECTION_OPTIONS:
            fields.append(
                dict(
                    name=f"{option['emoji']} {option['name']}",
                    value=option["description"] + _("\n**Enabled**: {enabled}").format(
                        enabled="✅" if config["options"][option["value"]] else "❌"
                    ) + (
                        _("\n**Limit**: ⏣ {limit}").format(
                            limit=f"{config['high_amount_limit']:,}"
                        ) if option["value"] == "high_amount_payment" else (
                            _("\n**Minute Limit**: {minute_limit}\n**Hour Limit**: {hour_limit}").format(
                                minute_limit=config["rapid_payout"]["minute_limit"],
                                hour_limit=config["rapid_payout"]["hour_limit"]
                            ) if option["value"] == "rapid_payout" else (
                                _("\n**Cooldown**: {cooldown} seconds").format(
                                    cooldown=config["payout_cooldown"]
                                ) if option["value"] == "payout_cooldown" else ""
                            )
                        )
                    ),
                    inline=True,
                )
            )

        components = [ToggleModuleButton(self, guild, view, config["enabled"])]
        quarantine_button: discord.ui.Button = discord.ui.Button(
            label=_("Quarantine Automatically"),
            style=discord.ButtonStyle.success
            if config["quarantine"]
            else discord.ButtonStyle.danger,
            emoji=Emojis.QUARANTINE.value,
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
        )
        async def configure_values_button_callback(interaction: discord.Interaction) -> None:
            await interaction.response.send_modal(
            ConfigureValuesModal(self, guild, view, config)
            )
        configure_values_button.callback = configure_values_button_callback
        components.append(configure_values_button)

        return title, description, fields, components

    async def on_message_without_command(self, message: discord.Message) -> None:
        if message.guild is None:
            return
        if not message.author.bot or message.author.id != DANK_MEMER_BOT_ID:
            return
        if message.interaction_metadata is None:
            return
        config = await self.config_value(message.guild)()
        if not config["enabled"]:
            return
        if await self.cog.is_message_whitelisted(message, "dank_pool_protection"):
            return
        try:
            raw_message = await self.cog.bot.http.get_message(message.channel.id, message.id)
        except discord.HTTPException:
            return
        if not raw_message["components"] or not raw_message["components"][0]["type"] == 17 or not raw_message["components"][0]["components"]:
            return
        if (member := message.guild.get_member(message.interaction_metadata.user.id)) is None:
            try:
                member = await message.guild.fetch_member(message.interaction.user.id)
            except discord.HTTPException:
                return
        log = _(
            "{member.mention} (`{member}`) executed `/{slash_name}` ({jump_url}) {timestamp}."
        ).format(
            member=member,
            slash_name=message.interaction.name,
            jump_url=message.jump_url,
            timestamp=f"<t:{int(message.created_at.timestamp())}:R>",
        )
        if (
            message.interaction.name == "serverevents payout"
            and "Pending Confirmation" in raw_message["components"][0]["components"][0]["content"]
        ):
            self.payouts_cache[message.guild][member].append((message.created_at, log))
            self.payouts_cache[message.guild][member] = [
                (created_at, log)
                for (created_at, log) in self.payouts_cache[message.guild][member]
                if created_at >= message.created_at - datetime.timedelta(hours=1)
            ]
        for option in DANK_POOL_PROTECTION_OPTIONS:
            if not config["options"][option["value"]]:
                continue
            if option["value"] == "rapid_payout":
                if (
                    len(self.payouts_cache[message.guild][member]) > config["rapid_payout"]["hour_limit"]
                    or sum(
                        [
                            created_at >= message.created_at - datetime.timedelta(minutes=1)
                            for (created_at, __) in self.payouts_cache[message.guild][member]
                        ]
                    ) > config["rapid_payout"]["minute_limit"]
                ):
                    logs = [
                        log
                        for (__, log) in self.payouts_cache[message.guild][member]
                    ]
                    break
            elif option["value"] == "payout_cooldown":
                if (
                    len(self.payouts_cache[message.guild][member]) > 1
                    and message.created_at - self.payouts_cache[message.guild][member][-2][0] < datetime.timedelta(seconds=config["payout_cooldown"])
                ):
                    logs = [
                        log
                        for (__, log) in self.payouts_cache[message.guild][member]
                    ]
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

def convert_amount(argument: str) -> int:
    try:
        return int(argument)
    except ValueError:
        try:
            return int(float(argument[:-1]) * (1000 ** ("kmbt".index(argument[-1].lower()) + 1)))
        except (ValueError, IndexError):
            raise ValueError(_("Invalid amount format. Use a number or a shorthand like `1k`, `2m`, etc."))


def format_number(number: int) -> str:
    if number < 1000:
        return str(number)
    for i, suffix in enumerate(["", "k", "m", "b", "t"]):
        if number < 1000 ** (i + 1) or i == 3:
            num = number / (1000 ** i)
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
            default=format_number(config["high_amount_limit"]),
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
        await self.module.config_value(self.guild).rapid_payout.set({
            "minute_limit": minute_limit,
            "hour_limit": hour_limit,
        })
        await self.view._message.edit(embed=await self.view.get_embed(), view=self.view)

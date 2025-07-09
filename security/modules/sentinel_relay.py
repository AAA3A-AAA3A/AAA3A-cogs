from AAA3A_utils import Loop  # isort:skip
from redbot.core.i18n import Translator  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

from redbot.core.utils.chat_formatting import humanize_list

from ..constants import Emojis
from ..views import ToggleModuleButton
from .module import Module

_: Translator = Translator("Security", __file__)


class SentinelRelayModule(Module):
    name = "Sentinel Relay"
    emoji = Emojis.SENTINEL_RELAY.value
    description = "Maintain essential functionality and continuity when the main bot goes offline."
    default_config = {
        "enabled": False,
        "main_bot": None,
        "modules_to_enable": ["logging", "anti_nuke", "protected_roles", "dank_pool_protection"],
        "triggered": False,
    }
    configurable_by_trusted_admins = False

    async def load(self) -> None:
        self.cog.loops.append(
            Loop(
                cog=self.cog,
                name="Check Sentinel Relay",
                function=self.check_loop,
                minutes=1,
            )
        )

    async def unload(self) -> None:
        pass

    async def get_status(self, guild: discord.Guild, check_enabled: bool = True) -> typing.Tuple[typing.Literal["✅", "⚠️", "❎"], str, str]:
        config = await self.config_value(guild)()
        if not config["enabled"] and check_enabled:
            return "❎", _("Disabled"), _("Sentinel Relay is currently disabled.")
        if config["main_bot"] is None:
            return "⚠️", _("No Main Bot"), _("No main bot selected.")
        if not self.cog.bot.intents.presences:
            return "⚠️", _("No Presence Intent"), _("The bot's presence intent is required for this module to function correctly.")
        return "✅", _("Enabled"), _("Sentinel Relay is enabled and configured correctly.")

    async def get_settings(self, guild: discord.Guild, view: discord.ui.View):
        config = await self.config_value(guild)()
        title = f"{self.emoji} {self.name} {(await self.get_status(guild))[0]}"
        main_bot = (
            main_bot
            if (main_bot_id := config["main_bot"]) is not None
            and (main_bot := guild.get_member(main_bot_id)) is not None
            else None
        )
        description = _(
            "This module automatically enables specified modules when the main bot goes offline, ensuring essential functionality and continuity. This ensures that both bots won't conflict with each other.\n\n"
            "**Main Bot:** {main_bot}\n"
            "**Modules to Enable:** {modules_to_enable}"
        ).format(
            main_bot=f"{main_bot.mention} (`{main_bot}`) {await self.cog.get_member_emojis(main_bot)}" if main_bot is not None else _("Not Set"),
            modules_to_enable=humanize_list(
                [f"{module_name.replace('_', ' ').title()} {(await self.cog.modules[module_name].get_status(guild, check_enabled=False))[0]}" for module_name in config["modules_to_enable"]]
            ) if config["modules_to_enable"] else _("None"),
        )

        components = [ToggleModuleButton(self, guild, view, config["enabled"])]

        main_bot_select: discord.ui.UserSelect = discord.ui.UserSelect(
            placeholder=_("Select the main bot"),
            min_values=0,
            max_values=1,
            default_values=[main_bot] if main_bot is not None else [],
        )
        async def main_bot_select_callback(interaction: discord.Interaction) -> None:
            selected = main_bot_select.values[0] if main_bot_select.values else None
            if selected:
                if not selected.bot:
                    await interaction.response.send_message(
                        _("You can only select a bot as the main bot."), ephemeral=True
                    )
                    return
                if selected == guild.me:
                    await interaction.response.send_message(
                        _("You can't select me as the main bot."), ephemeral=True
                    )
                    return
                await self.config_value(guild).main_bot.set(selected.id)
                await interaction.response.send_message(
                    _("{selected} has been set as the main bot.").format(selected=selected.mention),
                    ephemeral=True,
                )
            else:
                await self.config_value(guild).main_bot.clear()
                await interaction.response.send_message(
                    _("The main bot has been unset."),
                    ephemeral=True,
                )
            await view._message.edit(embed=await view.get_embed(), view=view)
        main_bot_select.callback = main_bot_select_callback
        components.append(main_bot_select)

        modules = [
            module
            for module in self.cog.modules.values()
            if "enabled" in module.default_config and module != self
        ]
        modules_select: discord.ui.Select = discord.ui.Select(
            placeholder=_("Select modules to enable"),
            min_values=0,
            max_values=len(self.cog.modules) - 2,
            options=[
                discord.SelectOption(
                    emoji=module.emoji,
                    label=module.name,
                    description=module.description,
                    value=module.key_name(),
                    default=module.key_name() in config["modules_to_enable"],
                )
                for module in modules
            ],
        )
        async def modules_select_callback(interaction: discord.Interaction) -> None:
            await interaction.response.defer()
            selected_modules = modules_select.values
            await self.config_value(guild).modules_to_enable.set(selected_modules)
        modules_select.callback = modules_select_callback
        components.append(modules_select)

        return title, description, [], components

    async def check_loop(self) -> None:
        for guild_id in await self.cog.config.all_guilds():
            if (guild := self.cog.bot.get_guild(guild_id)) is None:
                continue
            config = await self.config_value(guild)()
            if (
                not config["enabled"]
                or (main_bot_id := config["main_bot"]) is None
            ):
                continue
            if (main_bot := guild.get_member(main_bot_id)) is None:
                try:
                    main_bot = await guild.fetch_member(main_bot_id)
                except discord.NotFound:
                    main_bot = None
                except discord.HTTPException:
                    continue
            if main_bot is None or main_bot.status.value == "offline":
                if not config["triggered"]:
                    await self.config_value(guild).triggered.set(True)
                    for module_name in config["modules_to_enable"]:
                        await self.cog.modules[module_name].config_value(guild).enabled.set(True)
                    embed: discord.Embed = discord.Embed(
                        title=_("Sentinel Relay Triggered!"),
                        description=_("The main bot is offline, triggering the relay."),
                        color=discord.Color.red()
                    )
                    if main_bot is not None:
                        embed.set_author(name=main_bot.display_name, icon_url=main_bot.display_avatar)
                    else:
                        user = await self.cog.bot.fetch_user(main_bot_id)
                        embed.set_author(name=user.display_name, icon_url=user.display_avatar)
                    embed.add_field(
                        name=_("Enabled Modules:"),
                        value="\n".join(
                            [
                                f"- {module.emoji} {module.name} {(await module.get_status(guild))[0]}"
                                for module in self.cog.modules.values()
                                if module.key_name() in config["modules_to_enable"]
                            ]
                        ),
                    )
                    embed.set_footer(text=guild.name, icon_url=guild.icon)
                    await self.cog.send_in_modlog_channel(guild, embed=embed)
            else:
                if config["triggered"]:
                    await self.config_value(guild).triggered.set(False)
                    for module_name in config["modules_to_enable"]:
                        if (module := self.cog.modules.get(module_name)) is not None:
                            await module.config_value(guild).enabled.set(False)
                    embed: discord.Embed = discord.Embed(
                        title=_("Sentinel Relay Untriggered!"),
                        description=_("The main bot is back online, untriggering the relay."),
                        color=discord.Color.green()
                    )
                    embed.set_author(name=main_bot.display_name, icon_url=main_bot.display_avatar)
                    embed.add_field(
                        name=_("Disabled Modules:"),
                        value="\n".join(
                            [
                                f"- {module.emoji} {module.name} {(await module.get_status(guild))[0]}"
                                for module in self.cog.modules.values()
                                if module.key_name() in config["modules_to_enable"]
                            ]
                        ),
                    )
                    embed.set_footer(text=guild.name, icon_url=guild.icon)
                    await self.cog.send_in_modlog_channel(guild, embed=embed)

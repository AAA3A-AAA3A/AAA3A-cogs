import asyncio
import typing
from collections import defaultdict
from pathlib import Path

import aiohttp
import discord
import torch
import transformers

from redbot.core import commands
from redbot.core.data_manager import cog_data_path
from redbot.core.i18n import Translator
from redbot.core.utils.chat_formatting import box, humanize_list
from security.constants import Emojis
from security.utils import get_correct_timeout_duration
from security.views import DurationConverter, SettingsView, ToggleModuleButton

from .module import Module

_: Translator = Translator("Security", __file__)


LEVELS: dict[str, float] = {
    # "toxicity": 0.75,
    "severe_toxicity": 0.15,
    # "obscene": 0.75,
    "identity_attack": 0.25,
    "insult": 0.90,
    "threat": 0.50,
    "sexual_explicit": 0.75,
}

MODEL_URL: str = "https://github.com/unitaryai/detoxify/releases/download/v0.4-alpha/multilingual_debiased-0b549669.ckpt"

CHANGE_NAMES = {
    "toxic": "toxicity",
    "identity_hate": "identity_attack",
    "severe_toxic": "severe_toxicity",
}


class MultilingualDetoxify:
    def __init__(self, ckpt_path: Path, hf_path: Path, device: str = "cpu") -> None:
        self.device = torch.device(device)
        ckpt = torch.load(
            ckpt_path,
            map_location=self.device,
            weights_only=False,
        )
        arch = ckpt["config"]["arch"]["args"]
        model_class = getattr(transformers, arch["model_name"])
        tokenizer_class = getattr(transformers, arch["tokenizer_name"])
        config = model_class.config_class.from_pretrained(
            hf_path,
            num_labels=arch["num_classes"],
            local_files_only=True,
        )
        self.model = model_class(config)
        self.model.load_state_dict(
            ckpt["state_dict"],
            strict=False,
        )
        self.model.to(self.device)
        self.model.eval()
        self.tokenizer = tokenizer_class.from_pretrained(
            hf_path,
            local_files_only=True,
        )
        class_names = ckpt["config"]["dataset"]["args"]["classes"]
        self.class_names = [CHANGE_NAMES.get(name, name) for name in class_names]

    @torch.inference_mode()
    def predict(self, text: str) -> dict[str, float]:
        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            padding=True,
        )
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        logits = self.model(**inputs).logits
        scores = torch.sigmoid(logits)[0].cpu().tolist()
        return dict(zip(self.class_names, scores))


class MessageAnalysisModule(Module):
    name = "Message Analysis"
    emoji = Emojis.MESSAGE_ANALYSIS.value
    description = "Analyze messages with a local model to detect potential issues and take action."
    default_config = {
        "enabled": False,
        "levels": LEVELS.copy(),
        "timeout": True,
        "duration": "15m",
        "increase_duration": True,
    }

    def __init__(self, cog: commands.Cog) -> None:
        super().__init__(cog)
        self.detoxify: MultilingualDetoxify | None = None
        self.detoxify_error: bool = False
        self.locks: dict[discord.Guild, dict[discord.Member, asyncio.Lock]] = defaultdict(
            lambda: defaultdict(asyncio.Lock),
        )
        self.strikes_cache: dict[discord.Guild, dict[discord.Member, int]] = defaultdict(
            lambda: defaultdict(lambda: 0),
        )

    async def load(self) -> None:
        asyncio.create_task(self._load_detoxify())
        self.cog.bot.add_listener(self.on_message)

    async def _load_detoxify(self, download: bool = False) -> None:
        if self.detoxify is not None:
            return
        data_path = cog_data_path(self.cog)
        ckpt_path = data_path / "multilingual.ckpt"
        hf_path = data_path / "xlm-roberta-base"
        try:
            if download:
                self.cog.logger.info("Downloading MultilingualDetoxify model...")
                if ckpt_path.exists():
                    ckpt_path.unlink()
                if hf_path.exists():
                    for file in hf_path.iterdir():
                        if file.is_file():
                            file.unlink()
                    hf_path.rmdir()
                async with (
                    aiohttp.ClientSession(raise_for_status=True) as session,
                    session.get(MODEL_URL) as r,
                ):
                    with ckpt_path.open("wb") as f:
                        f.write(await r.read())
                hf_path.mkdir(parents=True, exist_ok=True)
                await asyncio.to_thread(
                    transformers.AutoConfig.from_pretrained("xlm-roberta-base").save_pretrained,
                    hf_path,
                )

                await asyncio.to_thread(
                    transformers.XLMRobertaTokenizer.from_pretrained(
                        "xlm-roberta-base",
                    ).save_pretrained,
                    hf_path,
                )
                self.cog.logger.info("MultilingualDetoxify model downloaded successfully.")
            if ckpt_path.exists() and hf_path.exists():
                self.detoxify = await asyncio.to_thread(
                    MultilingualDetoxify,
                    ckpt_path,
                    hf_path,
                )
        except Exception as e:  # noqa: BLE001
            self.detoxify_error = True
            self.cog.logger.error(f"Failed to load MultilingualDetoxify: {e}", exc_info=e)

    async def unload(self) -> None:
        self.cog.bot.remove_listener(self.on_message)

    async def get_status(
        self,
        guild: discord.Guild,
        check_enabled: bool = True,
    ) -> tuple[typing.Literal["✅", "⚠️", "❌"], str, str]:
        config = await self.config_value(guild)()
        if not config["enabled"] and check_enabled:
            return "❌", _("Disabled"), _("Message Analysis is currently disabled.")
        data_path = cog_data_path(self.cog)
        ckpt_path = data_path / "multilingual.ckpt"
        hf_path = data_path / "xlm-roberta-base"
        if not ckpt_path.exists() or not hf_path.exists():
            return "⚠️", _("Not Downloaded"), _("The model files are not downloaded yet.")
        if self.detoxify_error:
            return (
                "⚠️",
                _("Error"),
                _(
                    "Failed to load the MultilingualDetoxify model (check the logs for more information).",
                ),
            )
        missing_permissions = []
        if not guild.me.guild_permissions.manage_messages:
            missing_permissions.append("manage_messages")
        if config["timeout"] and not guild.me.guild_permissions.moderate_members:
            missing_permissions.append("moderate_members")
        if missing_permissions:
            return (
                "⚠️",
                _("Missing Permissions"),
                _("I need the {permissions} permission{s} to function properly.").format(
                    permissions=humanize_list(
                        [f"`{permission}`" for permission in missing_permissions],
                    ),
                    s="" if len(missing_permissions) == 1 else "s",
                ),
            )
        return "✅", _("Enabled"), _("Message Analysis is enabled and configured correctly.")

    async def get_settings(
        self,
        guild: discord.Guild,
        view: SettingsView,
    ) -> tuple[str, str, list[dict], list[discord.ui.Item]]:
        title = _("Security — {emoji} {name} {status}").format(
            emoji=self.emoji,
            name=self.name,
            status=(await self.get_status(guild))[0],
        )
        description = _(
            "This module analyzes messages for potential issues using a **local model**. It can detect severe toxicity, obscene content, threats, insults and identity attacks. Several languages are supported: english, french, spanish, italian, portuguese, turkish and russian.\n",
        )
        status = await self.get_status(guild)
        if status[0] == "⚠️":
            description += f"{status[0]} **{status[1]}**: {status[2]}\n"

        config = await self.config_value(guild)()
        for key in LEVELS:
            description += f"\n⛰️ **{key.replace('_', ' ').title()}:** `{config['levels'][key]:.2f}`"

        fields = [
            {
                "name": _("Timeout:"),
                "value": "✅" if config["timeout"] else "❌",
                "inline": True,
            },
            {
                "name": _("Duration:"),
                "value": f"`{config['duration']}`",
                "inline": True,
            },
            {
                "name": _("Increase Duration (each time):"),
                "value": "✅" if config["increase_duration"] else "❌",
                "inline": True,
            },
        ]

        data_path = cog_data_path(self.cog)
        ckpt_path = data_path / "multilingual.ckpt"
        hf_path = data_path / "xlm-roberta-base"
        downloaded = ckpt_path.exists() and hf_path.exists()

        components = [ToggleModuleButton(self, guild, view, config["enabled"])]

        timeout_button: discord.ui.Button = discord.ui.Button(
            emoji=Emojis.TIMEOUT.value,
            label=_("Timeout"),
            style=discord.ButtonStyle.success if config["timeout"] else discord.ButtonStyle.danger,
        )

        async def timeout_button_callback(interaction: discord.Interaction) -> None:
            config["timeout"] = not config["timeout"]
            await self.config_value(guild).timeout.set(config["timeout"])
            await interaction.response.edit_message(
                embed=await view.get_embed(),
                view=view,
            )

        timeout_button.callback = timeout_button_callback
        components.append(timeout_button)

        duration_button: discord.ui.Button = discord.ui.Button(
            label=_("Timeout Duration"),
            style=discord.ButtonStyle.secondary,
        )

        async def duration_button_callback(interaction: discord.Interaction) -> None:
            await interaction.response.send_modal(
                ConfigureDurationModal(self, guild, view, config["duration"]),
            )

        duration_button.callback = duration_button_callback
        components.append(duration_button)

        increase_duration_button: discord.ui.Button = discord.ui.Button(
            label=_("Increase Duration"),
            style=discord.ButtonStyle.success
            if config["increase_duration"]
            else discord.ButtonStyle.danger,
        )

        async def increase_duration_button_callback(interaction: discord.Interaction) -> None:
            config["increase_duration"] = not config["increase_duration"]
            await self.config_value(guild).increase_duration.set(config["increase_duration"])
            await interaction.response.edit_message(
                embed=await view.get_embed(),
                view=view,
            )

        increase_duration_button.callback = increase_duration_button_callback
        components.append(increase_duration_button)

        download_model_button: discord.ui.Button = discord.ui.Button(
            label=(_("Download Model") if not downloaded else _("Redownload Model")),
            style=discord.ButtonStyle.secondary,
            disabled=downloaded and view.ctx.author.id not in self.cog.bot.owner_ids,
        )

        async def download_model_button_callback(interaction: discord.Interaction) -> None:
            asyncio.create_task(self._load_detoxify(download=True))
            await interaction.response.send_message(
                _("Downloading model in the background. This may take a while..."),
                ephemeral=True,
            )

        download_model_button.callback = download_model_button_callback
        components.append(download_model_button)

        for i, level in enumerate(LEVELS):
            level_button: discord.ui.Button = discord.ui.Button(
                emoji="⛰️",
                label=level.replace("_", " ").title(),
                style=discord.ButtonStyle.primary,
                row=2 + (i // 5),
            )

            async def level_button_callback(interaction: discord.Interaction) -> None:
                await interaction.response.send_modal(
                    ConfigureLevelModal(self, guild, view, level, config["levels"][level]),
                )

            level_button.callback = level_button_callback
            components.append(level_button)

        if view.ctx.author.id in self.cog.bot.owner_ids:
            hidden_modules = await self.cog.config.hidden_modules()
            hide_module_button: discord.ui.Button = discord.ui.Button(
                label=_("Hide Module")
                if self.key_name() not in hidden_modules
                else _("Unhide Module"),
                style=discord.ButtonStyle.secondary,
            )

            async def hide_module_button_callback(interaction: discord.Interaction) -> None:
                if self.key_name() not in hidden_modules:
                    hidden_modules.append(self.key_name())
                else:
                    hidden_modules.remove(self.key_name())
                await self.cog.config.hidden_modules.set(hidden_modules)
                await interaction.response.edit_message(
                    embed=await view.get_embed(),
                    view=view,
                )

            hide_module_button.callback = hide_module_button_callback
            components.append(hide_module_button)

        return title, description, fields, components

    async def predict(self, content: str) -> dict[str, float]:
        return self.detoxify.predict(content)

    async def on_message(self, message: discord.Message) -> None:
        if self.detoxify is None:
            return
        if message.guild is None:
            return
        config = await self.config_value(message.guild)()
        if not config["enabled"]:
            return
        number = self.strikes_cache[message.guild][message.author]
        if not isinstance(message.author, discord.Member):
            try:
                message.author = await message.guild.fetch_member(message.author.id)
            except discord.HTTPException:
                return
        if await self.cog.is_message_whitelisted(message, "message_analysis"):
            return
        if not message.content:
            return
        async with self.locks[message.guild][message.author]:
            if self.strikes_cache[message.guild][message.author] > number:
                try:
                    await message.delete()
                except discord.HTTPException:
                    pass
                return
            result = await self.predict(message.content)
            if not any(result[key] >= config["levels"][key] for key in LEVELS):
                return
            try:
                await message.delete()
            except discord.HTTPException:
                pass
            reason = _("**Message Analysis** - Message detected as potentially harmful.")
            reason += box(
                "\n{\n"
                + "\n".join(
                    f"  {key}: {value:.3f},{'  # ⚠️' if key in LEVELS and value >= config['levels'][key] else ''}"
                    for key, value in result.items()
                )
                + "\n}",
                lang="py",
            )
            if config["timeout"]:
                audit_log_reason = (
                    "Security's Message Analysis: message detected as potentially harmful."
                )
                duration = await DurationConverter.convert(
                    None,
                    config["duration"],
                )
                self.strikes_cache[message.guild][message.author] += 1
                if config["increase_duration"]:
                    duration *= self.strikes_cache[message.guild][message.author]
                duration = get_correct_timeout_duration(message.author, duration)
                if message.guild.me.guild_permissions.moderate_members:
                    await message.author.timeout(duration, reason=audit_log_reason)
                await self.cog.send_modlog(
                    action="timeout",
                    member=message.author,
                    reason=reason,
                    duration=duration,
                    trigger_messages=[message],
                    context_message=message,
                    current_ctx=message,
                )
            else:
                await self.cog.send_modlog(
                    action="notify",
                    member=message.author,
                    reason=reason,
                    trigger_messages=[message],
                    context_message=message,
                    current_ctx=message,
                )


class ConfigureDurationModal(discord.ui.Modal):
    def __init__(
        self,
        module: MessageAnalysisModule,
        guild: discord.Guild,
        view: SettingsView,
        duration: str,
    ) -> None:
        self.module: MessageAnalysisModule = module
        self.guild: discord.Guild = guild
        self.view: SettingsView = view
        self.duration: str = duration
        super().__init__(title=_("Configure Duration"))
        self.duration_input: discord.ui.TextInput = discord.ui.TextInput(
            label=_("Duration:"),
            style=discord.TextStyle.short,
            default=duration,
            required=True,
        )
        self.add_item(self.duration_input)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        try:
            duration = self.duration_input.value
            await DurationConverter.convert(None, duration)
        except ValueError as e:
            await interaction.followup.send(
                _("Invalid value: {error}").format(error=str(e)),
                ephemeral=True,
            )
            return
        self.duration = duration
        await self.module.config_value(self.guild).duration.set(duration)
        await self.view.edit_message()


class ConfigureLevelModal(discord.ui.Modal):
    def __init__(
        self,
        module: MessageAnalysisModule,
        guild: discord.Guild,
        view: SettingsView,
        level: str,
        value: float,
    ) -> None:
        self.module: MessageAnalysisModule = module
        self.guild: discord.Guild = guild
        self.view: SettingsView = view
        self.level: str = level
        self.value: float = value
        super().__init__(title=_("Configure Level"))
        self.value_input: discord.ui.TextInput = discord.ui.TextInput(
            label=_("Value:"),
            style=discord.TextStyle.short,
            default=f"{value:.2f}",
            required=True,
        )
        self.add_item(self.value_input)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        try:
            value = float(self.value_input.value)
            if not 0 <= value <= 1:
                raise ValueError(_("Value must be between 0 and 1."))
        except ValueError as e:
            await interaction.followup.send(
                _("Invalid value: {error}").format(error=str(e)),
                ephemeral=True,
            )
            return
        await self.module.config_value(self.guild).levels.set_raw(self.level, value=value)
        await self.view.edit_message()

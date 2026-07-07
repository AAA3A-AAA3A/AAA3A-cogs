import asyncio
import datetime
import typing
from collections import defaultdict
from io import BytesIO

import discord
import imagehash
from PIL import Image

from AAA3A_utils import Menu
from redbot.core import commands
from redbot.core.i18n import Translator
from redbot.core.utils.chat_formatting import humanize_list
from security.constants import POSSIBLE_ACTIONS, Emojis
from security.utils import get_correct_timeout_duration
from security.views import DurationConverter, SettingsView, ToggleModuleButton

from .module import Module

_: Translator = Translator("Security", __file__)


class ImageCheckingModule(Module):
    name = "Image Checking"
    emoji = Emojis.IMAGE_CHECKING.value
    description = "Detect and respond to matching images using perceptual hashes."
    default_config = {
        "enabled": False,
        "hashes": [
            "d0f0872f2f60f0c7",
            "c13a37c9c0b736c9",
            "f5de4800bcbd5a25",
            "c3e1e3c67c1c5c94",
            "c1e0e187981f0efe",
            "e1e0e187981f0ede",
            "c3e1e3c65c5e5c90",
            "c1b0c9a6d83e4a7e",
            "c5ba36c9caa4318f",
            "c1b0c9a7d83e0a7e",
            "946a6e964a49b6d9",
            "ff44106f337c3350",
            "9163e6946a3d364b",
            "dc8e91f16368ee82",
            "916e19c6c613b39b",
            "9adb7fc0a2804db6",
            "c3e1e3c65c1e5c94",
            "946a6e96cac9b689",
            "c3e1e3c65c5c5c94",
            "e5de4a00bcbd5a25",
            "946b6e964ac9b689",
            "c89136c999e639a7",
            "c0908f2f2f60f8cf",
            "946a6e94cac9b699",
            "f5de4a00bcb55a25",
            "c1e1e3c65c5e5c94",
            "931e6ae194d3486f",
            "946a6e964ac9b699",
            "b74a3bc4cc33321b",
            "9e6961d461969e96",
            "9bff7ca4a08149a6",
            "ce879ad819782727",
            "e07d97c44d974dc0",
            "9c86b1f16368ee16",
            "f766182519775a46",
            "956bf6946a151a6c",
            "c478374ac4313b3f",
            "956bf6956a151a4c",
            "f766182119775a66",
            "dc86b1f16368ec16",
            "c13b36c0c93f2ccd",
            "c1b0c1b7d83e8a3e",
            "c478334acc313b3f",
            "ff44106c0bb76c33",
            "dc87b17163688697",
            "954a68dacc97b1b1",
            "934a20b14e3f1f5b",
            "be49134d227d3e54",
            "98fc3f63661ec013",
        ],
        "action": "mute",
        "duration": "24h",
    }

    def __init__(self, cog: commands.Cog) -> None:
        super().__init__(cog)
        self.locks: dict[discord.Guild, dict[discord.Member, asyncio.Lock]] = defaultdict(
            lambda: defaultdict(asyncio.Lock),
        )
        self.strikes_cache: dict[discord.Guild, dict[discord.Member, int]] = defaultdict(
            lambda: defaultdict(int),
        )

    async def load(self) -> None:
        self.cog.bot.add_listener(self.on_message)

    async def unload(self) -> None:
        self.cog.bot.remove_listener(self.on_message)

    async def get_status(
        self,
        guild: discord.Guild,
        check_enabled: bool = True,
    ) -> tuple[typing.Literal["✅", "⚠️", "❌"], str, str]:
        config = await self.config_value(guild)()
        if not config["enabled"] and check_enabled:
            return "❌", _("Disabled"), _("Image Checking is currently disabled.")
        missing_permissions = []
        if not guild.me.guild_permissions.manage_messages:
            missing_permissions.append("manage_messages")
        action = next(a for a in POSSIBLE_ACTIONS if a["value"] == config["action"])
        if not getattr(guild.me.guild_permissions, action["permission"]):
            missing_permissions.append(action["permission"])
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
        return "✅", _("Enabled"), _("Image Checking is enabled and configured correctly.")

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
            "This module checks images against stored perceptual hashes. This can be used to detect and respond to scam images, among other things. Similar images will be detected even if they have been resized, cropped, or had their colors changed.\n"
            "*Some images are already preloaded (including several from Mr. Beast's scams), but you can add your own hashes as well and remove the default ones.*",
        )
        status = await self.get_status(guild)
        if status[0] == "⚠️":
            description += f"\n{status[0]} **{status[1]}**: {status[2]}"

        config = await self.config_value(guild)()
        action = next(a for a in POSSIBLE_ACTIONS if a["value"] == config["action"])
        fields = [
            {
                "name": _("Hashes:"),
                "value": _("{count} hash{plural} stored.").format(
                    count=len(config["hashes"]),
                    plural="" if len(config["hashes"]) == 1 else "es",
                ),
                "inline": True,
            },
            {
                "name": _("Action:"),
                "value": f"{action['emoji']} {action['name']}",
                "inline": True,
            },
            {
                "name": _("Duration:"),
                "value": f"`{config['duration']}`",
                "inline": True,
            },
        ]

        components = [ToggleModuleButton(self, guild, view, config["enabled"])]
        add_hash_button: discord.ui.Button = discord.ui.Button(
            emoji="➕",
            label=_("Add Hashes"),
            style=discord.ButtonStyle.success,
        )

        async def add_hash_button_callback(interaction: discord.Interaction) -> None:
            await interaction.response.send_message(
                _(
                    "To add hashes, please send a message with hashes in its content (one per line) and/or the images you want to hash. I will then compute the perceptual hashes and add them to the list.",
                ),
                ephemeral=True,
            )
            try:
                message: discord.Message = await self.cog.bot.wait_for(
                    "message_without_command",
                    check=lambda m: (
                        m.author == interaction.user
                        and m.channel == interaction.channel
                        and (
                            (m.content and all(len(line) == 16 for line in m.content.splitlines()))
                            or m.attachments
                        )
                    ),
                    timeout=180,
                )
            except asyncio.TimeoutError:
                await interaction.followup.send(
                    _("You took too long to send the hashes/images."),
                    ephemeral=True,
                )
                return
            new_hashes = []
            for line in message.content.splitlines():
                if len(line) == 16 and not await self.check_image(
                    config["hashes"] + new_hashes,
                    line,
                ):
                    new_hashes.append(line)
            for attachment in message.attachments:
                if (
                    hash_value := await self.hash_image(attachment)
                ) is not None and not await self.check_image(
                    config["hashes"] + new_hashes,
                    hash_value,
                ):
                    new_hashes.append(hash_value)
            if not new_hashes:
                await interaction.followup.send(
                    _("No new hashes were added. All hashes were already present."),
                    ephemeral=True,
                )
                return
            config["hashes"].extend(new_hashes)
            await self.config_value(guild).set(config)
            await interaction.followup.send(
                _("Added {count} new hash{plural}.").format(
                    count=len(new_hashes),
                    plural="" if len(new_hashes) == 1 else "es",
                ),
                ephemeral=True,
            )
            await view.edit_message()

        add_hash_button.callback = add_hash_button_callback
        components.append(add_hash_button)
        show_hashes_button: discord.ui.Button = discord.ui.Button(
            emoji="🔍",
            label=_("Show Hashes"),
            style=discord.ButtonStyle.primary,
        )

        async def show_hashes_button_callback(interaction: discord.Interaction) -> None:
            if not config["hashes"]:
                await interaction.response.send_message(
                    _("No hashes are currently stored."),
                    ephemeral=True,
                )
                return
            await interaction.response.defer(ephemeral=True)
            embed: discord.Embed = discord.Embed(
                title=_("Stored Hashes ({count})").format(count=len(config["hashes"])),
                color=discord.Color.blurple(),
            )
            embed.set_footer(
                text=guild.name,
                icon_url=guild.icon,
            )
            embeds = []
            for page in discord.utils.as_chunks(config["hashes"], 10):
                e = embed.copy()
                e.description = "\n".join(f"- `{h}`" for h in page)
                embeds.append(e)
            fake_context = type(
                "FakeContext",
                (),
                {
                    "interaction": interaction,
                    "bot": interaction.client,
                    "guild": interaction.guild,
                    "channel": interaction.channel,
                    "author": interaction.user,
                    "message": interaction.message,
                    "send": interaction.followup.send,
                },
            )()
            await Menu(pages=embeds, ephemeral=True).start(fake_context)

        show_hashes_button.callback = show_hashes_button_callback
        components.append(show_hashes_button)

        remove_hashes_button: discord.ui.Button = discord.ui.Button(
            emoji="➖",
            label=_("Remove Hashes"),
            style=discord.ButtonStyle.danger,
        )

        async def remove_hashes_button_callback(interaction: discord.Interaction) -> None:
            await interaction.response.send_message(
                _(
                    "To remove hashes, please send a message with hashes in its content (one per line). I will then remove them from the list.",
                ),
                ephemeral=True,
            )
            try:
                message: discord.Message = await self.cog.bot.wait_for(
                    "message_without_command",
                    check=lambda m: (
                        m.author == interaction.user
                        and m.channel == interaction.channel
                        and m.content
                        and all(len(line) == 16 for line in m.content.splitlines())
                    ),
                    timeout=180,
                )
            except asyncio.TimeoutError:
                await interaction.followup.send(
                    _("You took too long to send the hashes."),
                    ephemeral=True,
                )
                return
            removed_hashes = []
            for line in message.content.splitlines():
                if len(line) == 16 and line in config["hashes"]:
                    config["hashes"].remove(line)
                    removed_hashes.append(line)
            if not removed_hashes:
                await interaction.followup.send(
                    _("No hashes were removed. None of the provided hashes were found."),
                    ephemeral=True,
                )
                return
            await self.config_value(guild).set(config)
            await interaction.followup.send(
                _("Removed {count} hash{plural}.").format(
                    count=len(removed_hashes),
                    plural="" if len(removed_hashes) == 1 else "es",
                ),
                ephemeral=True,
            )
            await view.edit_message()

        remove_hashes_button.callback = remove_hashes_button_callback
        components.append(remove_hashes_button)

        action_select: discord.ui.Select = discord.ui.Select(
            placeholder=_("Select action"),
            options=[
                discord.SelectOption(
                    emoji=a["emoji"],
                    label=a["name"],
                    value=a["value"],
                    default=a["value"] == config["action"],
                )
                for a in POSSIBLE_ACTIONS
            ],
        )

        async def action_select_callback(interaction: discord.Interaction) -> None:
            action = next(a for a in POSSIBLE_ACTIONS if a["value"] == action_select.values[0])
            if not getattr(guild.me.guild_permissions, action["permission"]):
                await interaction.response.send_message(
                    _("I do not have the required permission to perform this action."),
                    ephemeral=True,
                )
                return
            await interaction.response.defer()
            config["action"] = action_select.values[0]
            await self.config_value(guild).set(config)
            await view.edit_message()

        action_select.callback = action_select_callback
        components.append(action_select)
        duration_button: discord.ui.Button = discord.ui.Button(
            label=_("Action Duration (for timeout/mute)"),
            style=discord.ButtonStyle.secondary,
            row=3,
        )

        async def duration_button_callback(interaction: discord.Interaction) -> None:
            await interaction.response.send_modal(
                ConfigureDurationModal(self, guild, view, config["duration"]),
            )

        duration_button.callback = duration_button_callback
        components.append(duration_button)

        return title, description, fields, components

    async def hash_image(self, attachment: discord.Attachment) -> str | None:
        if not attachment.content_type or not attachment.content_type.startswith("image/"):
            return None
        data = await attachment.read()
        return str(imagehash.phash(Image.open(BytesIO(data))))

    async def check_image(self, config_hashes: list[str], image_hash: str) -> bool:
        return any(
            imagehash.hex_to_hash(image_hash) - imagehash.hex_to_hash(h) <= 8 for h in config_hashes
        )

    async def on_message(self, message: discord.Message) -> None:
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
        if await self.cog.is_message_whitelisted(message, "image_checking"):
            return

        async with self.locks[message.guild][message.author]:
            if self.strikes_cache[message.guild][message.author] > number:
                try:
                    await message.delete()
                except discord.HTTPException:
                    pass
                return
            for attachment in message.attachments:
                if (
                    hash_value := await self.hash_image(attachment)
                ) is not None and await self.check_image(config["hashes"], hash_value):
                    break
            else:
                for embed in message.embeds:
                    if embed.type == "image" and embed.thumbnail and embed.thumbnail.url:
                        data = {
                            "id": 0,
                            "url": embed.thumbnail.url,
                            "proxy_url": embed.thumbnail.proxy_url,
                            "filename": embed.thumbnail.url.split("?")[0].split("/")[-1],
                            "content_type": embed._thumbnail.get("content_type", ""),
                            "height": embed.thumbnail.height,
                            "width": embed.thumbnail.width,
                            "flags": embed.thumbnail.flags,
                            "size": 1024,
                        }
                        attachment = discord.Attachment(
                            data=data,
                            state=message._state,
                        )
                        if (
                            hash_value := await self.hash_image(attachment)
                        ) is not None and await self.check_image(config["hashes"], hash_value):
                            break
                else:
                    return

            try:
                await message.delete()
            except discord.HTTPException:
                pass
            self.strikes_cache[message.guild][message.author] += 1

            action_value = config["action"]
            reason = _(
                "**Image Checking** - Matching image detected (hash `{hash_value}`)."
            ).format(
                hash_value=hash_value,
            )
            audit_log_reason = (
                f"Security's Image Checking: matching image detected (hash `{hash_value}`)."
            )
            file = await attachment.to_file()
            if action_value in ("timeout", "mute"):
                duration = await DurationConverter.convert(
                    None,
                    config["duration"],
                )
                if action_value == "timeout":
                    duration = get_correct_timeout_duration(message.author, duration)
            else:
                duration = None
            if action_value in ("kick", "ban"):
                await self.cog.send_modlog(
                    action=action_value,
                    member=message.author,
                    reason=reason,
                    trigger_messages=[message],
                    image_file=file,
                    context_message=message,
                    current_ctx=message,
                )
            if action_value == "timeout" and message.guild.me.guild_permissions.moderate_members:
                await message.author.timeout(duration, reason=audit_log_reason)
            elif (
                action_value == "mute"
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
            elif action_value == "kick" and message.guild.me.guild_permissions.kick_members:
                await message.author.kick(reason=audit_log_reason)
            elif action_value == "ban" and message.guild.me.guild_permissions.ban_members:
                await message.author.ban(reason=audit_log_reason)
            elif (
                action_value == "quarantine"
                and message.author.guild.me.guild_permissions.manage_roles
            ):
                try:
                    await self.cog.quarantine_member(
                        member=message.author,
                        reason=reason,
                        trigger_messages=[message],
                        image_file=file,
                        context_message=message,
                        current_ctx=message,
                    )
                except RuntimeError:
                    pass
            if action_value not in ("quarantine", "kick", "ban"):
                await self.cog.send_modlog(
                    action=action_value,
                    member=message.author,
                    reason=reason,
                    duration=duration,
                    trigger_messages=[message],
                    image_file=file,
                    context_message=message,
                    current_ctx=message,
                )


class ConfigureDurationModal(discord.ui.Modal):
    def __init__(
        self,
        module: ImageCheckingModule,
        guild: discord.Guild,
        view: SettingsView,
        duration: str,
    ) -> None:
        self.module: ImageCheckingModule = module
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

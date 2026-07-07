import asyncio
import datetime
import math
import random
import string
from collections import defaultdict
from io import BytesIO

import discord
from PIL import Image, ImageDraw, ImageFont

from redbot.core import commands
from redbot.core.i18n import Translator
from redbot.core.utils.chat_formatting import humanize_list
from security.constants import DANGEROUS_PERMISSIONS, Colors, Emojis
from security.modules.module import Module
from security.views import DurationConverter, SettingsView, ToggleModuleButton

_: Translator = Translator("Security", __file__)


class VerificationModule(Module):
    name = "Verification"
    emoji = Emojis.VERIFICATION.value
    description = "Verify new members using captcha before they can access the server."
    default_config = {
        "enabled": False,
        "channel": None,
        "max_attempts": 3,
        "kick_timeout": "180s",
        "roles_to_add": [],
    }

    def __init__(self, cog: commands.Cog) -> None:
        super().__init__(cog)
        self.pending: dict[discord.Guild, dict[discord.Member, dict]] = defaultdict(dict)

    async def load(self) -> None:
        self.cog.bot.add_listener(self.on_member_join)

    async def unload(self) -> None:
        self.cog.bot.remove_listener(self.on_member_join)

    async def get_status(
        self,
        guild: discord.Guild,
        check_enabled: bool = True,
    ) -> tuple[str, str, str]:
        config = await self.config_value(guild)()
        if not config["enabled"] and check_enabled:
            return "❌", _("Disabled"), _("Verification is currently disabled.")
        if (channel := config["channel"]) is None or (
            channel := guild.get_channel(channel)
        ) is None:
            return "⚠️", _("Channel not set"), _("Verification channel is not set or invalid.")
        missing_permissions = []
        if not channel.permissions_for(guild.me).view_channel:
            missing_permissions.append("view_channel")
        if not channel.permissions_for(guild.me).send_messages:
            missing_permissions.append("send_messages")
        if config["roles_to_add"]:
            if not guild.me.guild_permissions.manage_roles:
                missing_permissions.append("manage_roles")
            for role_id in config["roles_to_add"]:
                if (role := guild.get_role(role_id)) is None:
                    continue
                if not role.is_assignable():
                    return (
                        "⚠️",
                        _("Role not assignable"),
                        _(
                            "The role {role} is higher than my highest role and cannot be assigned.",
                        ).format(role=role.mention),
                    )
                if any(
                    getattr(role.permissions, permission) for permission in DANGEROUS_PERMISSIONS
                ):
                    return (
                        "⚠️",
                        _("Role not assignable"),
                        _(
                            "The role {role} is not assignable because it has dangerous permissions. Please remove those permissions or choose a different role.",
                        ).format(role=role.mention),
                    )
        if not guild.me.guild_permissions.kick_members:
            missing_permissions.append("kick_members")
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
        return "✅", _("Enabled"), _("Verification is enabled and configured correctly.")

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
            "This module verifies new members using captcha before they can access the server. "
            "Members will be required to solve a captcha and can be automatically assigned roles upon successful verification."
        )
        status = await self.get_status(guild)
        if status[0] == "⚠️":
            description += f"\n{status[0]} **{status[1]}**: {status[2]}"

        config = await self.config_value(guild)()

        fields = [
            {
                "name": _("Channel:"),
                "value": f"{channel.mention} (`{channel}`)"
                if (channel := config["channel"]) is not None
                and (channel := guild.get_channel(channel))
                else _("Not set"),
                "inline": True,
            },
            {
                "name": _("Max Attempts:"),
                "value": str(config["max_attempts"]),
                "inline": True,
            },
            {
                "name": _("Kick Timeout:"),
                "value": f"`{config['kick_timeout']}`",
                "inline": True,
            },
            {
                "name": _("Roles to Add:"),
                "value": "\n".join(
                    [
                        f"- {role.mention} (`{role}`)"
                        for role_id in config["roles_to_add"]
                        if (role := guild.get_role(role_id)) is not None
                    ],
                )
                or _("None"),
                "inline": False,
            },
        ]

        components = [ToggleModuleButton(self, guild, view, config["enabled"])]

        create_a_verification_channel_button: discord.ui.Button = discord.ui.Button(
            emoji=Emojis.CHANNEL.value,
            label=_("Create a Verification Channel"),
            style=discord.ButtonStyle.secondary,
            disabled=not guild.me.guild_permissions.manage_channels,
        )

        async def create_a_verification_channel_callback(interaction: discord.Interaction):
            await interaction.response.defer(ephemeral=True, thinking=True)
            channel = await guild.create_text_channel(
                name=_("{emoji}・verification").format(emoji=Emojis.VERIFICATION.value),
                topic=_("This channel is used for verification."),
                overwrites={
                    guild.default_role: discord.PermissionOverwrite(
                        view_channel=True,
                        send_messages=True,
                    ),
                    guild.me: discord.PermissionOverwrite(
                        view_channel=True,
                        send_messages=True,
                        embed_links=True,
                    ),
                },
                reason=_("Created by Security's Verification Module."),
            )
            config["channel"] = channel.id
            await self.config_value(guild).channel.set(channel.id)
            await interaction.followup.send(
                _("✅ A new verification channel has been created: {channel.mention}.").format(
                    channel=channel,
                ),
                ephemeral=True,
            )
            await view.edit_message()

        create_a_verification_channel_button.callback = create_a_verification_channel_callback
        components.append(create_a_verification_channel_button)

        max_attempts_button: discord.ui.Button = discord.ui.Button(
            emoji="🔢",
            label=_("Set Max Attempts"),
            style=discord.ButtonStyle.secondary,
        )

        async def max_attempts_callback(interaction: discord.Interaction):
            await interaction.response.send_modal(
                ConfigureMaxAttemptsModal(self, guild, view, config["max_attempts"]),
            )

        max_attempts_button.callback = max_attempts_callback
        components.append(max_attempts_button)

        kick_timeout_button: discord.ui.Button = discord.ui.Button(
            emoji=Emojis.KICK.value,
            label=_("Set Kick Timeout"),
            style=discord.ButtonStyle.secondary,
        )

        async def kick_timeout_callback(interaction: discord.Interaction):
            await interaction.response.send_modal(
                ConfigureKickTimeoutModal(self, guild, view, config["kick_timeout"]),
            )

        kick_timeout_button.callback = kick_timeout_callback
        components.append(kick_timeout_button)

        channel_select: discord.ui.ChannelSelect = discord.ui.ChannelSelect(
            channel_types=[discord.ChannelType.text],
            placeholder=_("Select verification channel"),
            min_values=0,
            max_values=1,
            default_values=[channel] if channel is not None else [],
        )

        async def channel_callback(interaction: discord.Interaction):
            await interaction.response.defer()
            selected = channel_select.values[0] if channel_select.values else None
            if selected is not None:
                config["channel"] = selected.id
                await self.config_value(guild).channel.set(selected.id)
            else:
                config["channel"] = None
                await self.config_value(guild).channel.clear()
            await view.edit_message()

        channel_select.callback = channel_callback
        components.append(channel_select)

        roles_to_add_select: discord.ui.RoleSelect = discord.ui.RoleSelect(
            placeholder=_("Select roles to add"),
            min_values=0,
            max_values=25,
            default_values=[
                role
                for role_id in config["roles_to_add"]
                if (role := guild.get_role(role_id)) is not None
            ],
        )

        async def roles_to_add_callback(interaction: discord.Interaction):
            await interaction.response.defer()
            selected_roles = roles_to_add_select.values
            config["roles_to_add"] = [role.id for role in selected_roles]
            await self.config_value(guild).roles_to_add.set(config["roles_to_add"])
            await view.edit_message()

        roles_to_add_select.callback = roles_to_add_callback
        components.append(roles_to_add_select)

        return title, description, fields, components

    def generate_captcha(
        self,
        width: int = 800,
        height: int = 400,
        text_length: int = 6,
    ) -> tuple[str, Image]:
        # 1. Background setup.
        img = Image.new("RGB", (width, height), "white")
        draw = ImageDraw.Draw(img)
        characters = string.ascii_uppercase + string.digits
        solution = "".join(random.choices(characters, k=text_length))

        # 2. Background noise (dots).
        for _ in range(8000):
            x = random.randint(0, width)
            y = random.randint(0, height)
            dot_color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
            draw.point((x, y), fill=dot_color)

        # 3. Load font pools for variety.
        font_names = [
            "arial.ttf",
            "times.ttf",
            "cour.ttf",
            "comic.ttf",
            "impact.ttf",
            "trebuc.ttf",
            "georgia.ttf",
            "verdana.ttf",
            "DejaVuSans.ttf",
        ]
        bg_fonts = []
        main_fonts = []
        for fn in font_names:
            try:
                bg_fonts.append(ImageFont.truetype(fn, 50))
                main_fonts.append(ImageFont.truetype(fn, 120))
            except OSError:
                # Skip fonts not installed on the system.
                continue
        if not bg_fonts:
            bg_fonts = [ImageFont.load_default()]
            main_fonts = [ImageFont.load_default()]

        # 4. Faded background letters (Noise).
        for _ in range(150):
            bg_char = random.choice(characters)
            x = random.randint(-20, width)
            y = random.randint(-20, height)
            bg_color = (
                random.randint(120, 190),
                random.randint(120, 190),
                random.randint(120, 190),
            )
            current_bg_font = random.choice(bg_fonts)
            bg_stroke = random.randint(1, 3)

            txt_img = Image.new("RGBA", (80, 80), (255, 255, 255, 0))
            txt_draw = ImageDraw.Draw(txt_img)
            txt_draw.text(
                (10, 10),
                bg_char,
                font=current_bg_font,
                fill=bg_color,
                stroke_width=bg_stroke,
                stroke_fill=bg_color,
            )
            txt_img = txt_img.rotate(random.randint(-60, 60), expand=1)
            img.paste(txt_img, (x, y), txt_img)

        # 5. Composite central curve parameters (unpredictable).
        y_base = height // 2
        amp1 = random.randint(20, 50)
        period1 = width / random.uniform(1.5, 2.5)
        phase1 = random.uniform(0, 2 * math.pi)
        amp2 = random.randint(10, 35)
        period2 = width / random.uniform(3.0, 5.0)
        phase2 = random.uniform(0, 2 * math.pi)

        def calculate_y_on_line(x_pos):
            wave1 = amp1 * math.sin(2 * math.pi * x_pos / period1 + phase1)
            wave2 = amp2 * math.cos(2 * math.pi * x_pos / period2 + phase2)
            return y_base + int(wave1 + wave2)

        # 6. Thin lines.
        for _ in range(4):
            y_start = random.randint(50, height - 50)
            fine_amp = random.randint(10, 40)
            fine_freq = random.uniform(0.005, 0.015)
            fine_points = [
                (x, y_start + int(math.sin(x * fine_freq) * fine_amp)) for x in range(width)
            ]
            draw.line(fine_points, fill=(150, 150, 150), width=1)

        # 7. Thick wavy line.
        main_line_points = [(x, calculate_y_on_line(x)) for x in range(width)]
        draw.line(main_line_points, fill=(100, 100, 100), width=8, joint="curve")

        # 8. Main text.
        segment_width = width // text_length

        for i, char in enumerate(solution):
            base_x = (segment_width * i) + (segment_width // 2)
            jitter = int(segment_width * random.uniform(-0.25, 0.25))
            x_center = base_x + jitter + 13
            y_center = calculate_y_on_line(x_center)

            char_color = (random.randint(40, 130), random.randint(40, 130), random.randint(40, 130))
            current_main_font = random.choice(main_fonts)
            main_stroke = random.randint(0, 2)

            canvas_size = 180
            txt_img = Image.new("RGBA", (canvas_size, canvas_size), (255, 255, 255, 0))
            txt_draw = ImageDraw.Draw(txt_img)
            txt_draw.text(
                (30, 20),
                char,
                font=current_main_font,
                fill=char_color,
                stroke_width=main_stroke,
                stroke_fill=char_color,
            )
            rotation = random.randint(-40, 40)
            txt_img = txt_img.rotate(rotation, expand=0)
            paste_x = x_center - (canvas_size // 2)
            paste_y = y_center - (canvas_size // 2)
            img.paste(txt_img, (paste_x, paste_y), txt_img)

        return solution, img

    async def on_member_join(self, member: discord.Member) -> None:
        config = await self.config_value(member.guild)()
        if not config["enabled"]:
            return
        if (channel_id := config["channel"]) is None or (
            channel := member.guild.get_channel(channel_id)
        ) is None:
            return
        bot_permissions = channel.permissions_for(member.guild.me)
        if (
            not bot_permissions.view_channel
            or not bot_permissions.send_messages
            or not bot_permissions.embed_links
            or not bot_permissions.attach_files
        ):
            return
        if await self.cog.is_trusted_admin_or_higher(member):
            return
        member_permissions = channel.permissions_for(member)
        if not member_permissions.view_channel or not member_permissions.send_messages:
            if bot_permissions.manage_channels:
                try:
                    await channel.set_permissions(member, view_channel=True, send_messages=True)
                except discord.HTTPException:
                    return
            changed = True
        else:
            changed = False

        for attempt in range(1, config["max_attempts"] + 1):
            embed: discord.Embed = discord.Embed(
                title=_("{emoji} Verification Required (Attempt {attempt}/{max_attempts})!").format(
                    emoji=self.emoji,
                    attempt=attempt,
                    max_attempts=config["max_attempts"],
                ),
                description=_(
                    "Welcome to **{guild}**! To gain access, please solve the captcha below. If you fail to solve it within {max_attempts} attempts or the timeout period (`{timeout}`), you will be kicked from the server.",
                ).format(
                    guild=member.guild.name,
                    max_attempts=config["max_attempts"],
                    timeout=config["kick_timeout"],
                ),
                color=Colors.VERIFICATION.value,
                timestamp=datetime.datetime.now(tz=datetime.timezone.utc),
            )
            embed.set_author(
                name=member.display_name,
                icon_url=member.display_avatar,
            )
            embed.set_footer(
                text=member.guild.name,
                icon_url=member.guild.icon,
            )
            solution, captcha_img = await asyncio.to_thread(self.generate_captcha)
            buffer = BytesIO()
            captcha_img.save(buffer, format="PNG")
            buffer.seek(0)
            file = discord.File(buffer, filename="captcha.png")
            embed.set_image(url=f"attachment://{file.filename}")
            message = await channel.send(member.mention, embed=embed, file=file)

            kick_timeout = await DurationConverter.convert(None, config["kick_timeout"])
            try:
                response: discord.Message = await self.cog.bot.wait_for(
                    "message_without_command",
                    check=lambda m: m.author == member and m.channel == channel,
                    timeout=kick_timeout.total_seconds(),
                )
            except asyncio.TimeoutError:
                await self.cog.send_modlog(
                    action="kick",
                    member=member,
                    reason=_("**Verification** - Failed to verify in time and was kicked."),
                    logs=[
                        _("{member.mention} (`{member}`) joined the server.").format(member=member),
                        _("They failed to verify in time and were kicked."),
                    ],
                )
                try:
                    await member.send(
                        _(
                            "You failed to verify in time and have been kicked from **{guild}**.",
                        ).format(
                            guild=member.guild.name,
                        ),
                    )
                except discord.HTTPException:
                    pass
                try:
                    await member.kick(reason="Security's Verification: Failed to verify in time.")
                except discord.HTTPException:
                    pass
                return
            try:
                await message.delete()
                await response.delete()
            except discord.HTTPException:
                pass
            if response.content.strip().upper() == solution:
                break
            if attempt < config["max_attempts"]:
                await channel.send(
                    _("{member.mention}, that was incorrect. Please try again.").format(
                        member=member,
                        attempt=attempt,
                        max_attempts=config["max_attempts"],
                    ),
                    delete_after=10,
                )
            else:
                await self.cog.send_modlog(
                    action="kick",
                    member=member,
                    reason=_(
                        "**Verification** - Failed to verify after {max_attempts} attempts."
                    ).format(
                        max_attempts=config["max_attempts"],
                    ),
                    logs=[
                        _("{member.mention} (`{member}`) joined the server.").format(member=member),
                        _(
                            "They failed to verify after {max_attempts} attempts and were kicked.",
                        ).format(
                            max_attempts=config["max_attempts"],
                        ),
                    ],
                )
                try:
                    await member.send(
                        _(
                            "You failed to verify after {max_attempts} attempts and have been kicked from **{guild}**."
                        ).format(
                            max_attempts=config["max_attempts"],
                            guild=member.guild.name,
                        ),
                    )
                except discord.HTTPException:
                    pass
                try:
                    await member.kick(reason="Security's Verification: Failed to verify.")
                except discord.HTTPException:
                    pass
                return

        await channel.send(
            _("{member.mention}, you have successfully verified!").format(member=member),
            delete_after=10,
        )
        roles_to_add = [
            role
            for role_id in config["roles_to_add"]
            if (role := member.guild.get_role(role_id)) is not None
            and role.is_assignable()
            and all(
                not getattr(role.permissions, permission) for permission in DANGEROUS_PERMISSIONS
            )
        ]
        if roles_to_add:
            try:
                await member.add_roles(
                    *roles_to_add,
                    reason="Security's Verification: Verified successfully.",
                )
            except discord.HTTPException:
                pass
        if changed:
            try:
                await channel.set_permissions(member, overwrite=None)
            except discord.HTTPException:
                pass


class ConfigureMaxAttemptsModal(discord.ui.Modal):
    def __init__(
        self,
        module: VerificationModule,
        guild: discord.Guild,
        view: SettingsView,
        max_attempts: int,
    ) -> None:
        self.module: VerificationModule = module
        self.guild: discord.Guild = guild
        self.view: SettingsView = view
        self.max_attempts: int = max_attempts
        super().__init__(title=_("Configure Max Attempts"))
        self.max_attempts_input: discord.ui.TextInput = discord.ui.TextInput(
            label=_("Max Attempts:"),
            style=discord.TextStyle.short,
            default=str(max_attempts),
            required=True,
        )
        self.add_item(self.max_attempts_input)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        try:
            max_attempts = int(self.max_attempts_input.value)
        except ValueError as e:
            await interaction.followup.send(
                _("Invalid value: {error}").format(error=str(e)),
                ephemeral=True,
            )
            return
        if max_attempts < 1:
            await interaction.followup.send(
                _("Max attempts must be at least 1."),
                ephemeral=True,
            )
            return
        if max_attempts > 10:
            await interaction.followup.send(
                _("Max attempts cannot exceed 10."),
                ephemeral=True,
            )
            return
        self.max_attempts = max_attempts
        await self.module.config_value(self.guild).max_attempts.set(max_attempts)
        await self.view.edit_message()


class ConfigureKickTimeoutModal(discord.ui.Modal):
    def __init__(
        self,
        module: VerificationModule,
        guild: discord.Guild,
        view: SettingsView,
        kick_timeout: str,
    ) -> None:
        self.module: VerificationModule = module
        self.guild: discord.Guild = guild
        self.view: SettingsView = view
        self.kick_timeout: str = kick_timeout
        super().__init__(title=_("Configure Kick Timeout"))
        self.kick_timeout_input: discord.ui.TextInput = discord.ui.TextInput(
            label=_("Kick Timeout:"),
            style=discord.TextStyle.short,
            default=str(kick_timeout),
            required=True,
        )
        self.add_item(self.kick_timeout_input)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        try:
            kick_timeout = self.kick_timeout_input.value
            await DurationConverter.convert(None, kick_timeout)
        except ValueError as e:
            await interaction.followup.send(
                _("Invalid value: {error}").format(error=str(e)),
                ephemeral=True,
            )
            return
        self.kick_timeout = kick_timeout
        await self.module.config_value(self.guild).kick_timeout.set(kick_timeout)
        await self.view.edit_message()

import datetime
import typing
from collections import defaultdict

import discord

from redbot.core import app_commands, commands
from redbot.core.i18n import Translator
from redbot.core.utils.chat_formatting import box
from security.constants import Colors, Emojis
from security.utils import get_non_animated_asset
from security.views import ActionsView, DurationConverter, SettingsView, ToggleModuleButton

from .module import Module

_: Translator = Translator("Security", __file__)


@app_commands.context_menu(name="Report Member")
async def report_member(interaction: discord.Interaction, member: discord.Member) -> None:
    cog = interaction.client.get_cog("Security")
    module = cog.modules["reports"]
    await module.report(interaction, member)


@app_commands.context_menu(name="Report Message")
async def report_message(interaction: discord.Interaction, message: discord.Message) -> None:
    cog = interaction.client.get_cog("Security")
    module = cog.modules["reports"]
    await module.report(interaction, message)


class ReportsModule(Module):
    name = "Reports"
    emoji = Emojis.REPORTS.value
    description = "Configure the reports system for your server."
    default_config = {
        "enabled": False,
        "anonymous": False,
        "allow_staff_actions": True,
        "channel": None,
        "ping_role": None,
        "cooldown": "5m",
    }

    def __init__(self, cog: commands.Cog) -> None:
        super().__init__(cog)
        self.last_report_at: dict[int, dict[int, datetime.datetime]] = defaultdict(dict)

    async def load(self) -> None:
        self.cog.bot.tree.add_command(report_member)
        self.cog.bot.tree.add_command(report_message)

    async def unload(self) -> None:
        self.cog.bot.tree.remove_command(report_member.name)
        self.cog.bot.tree.remove_command(report_message.name)

    async def get_status(
        self,
        guild: discord.Guild,
        check_enabled: bool = True,
    ) -> tuple[typing.Literal["✅", "⚠️", "❎"], str, str]:
        config = await self.config_value(guild)()
        if not config["enabled"] and check_enabled:
            return "❎", _("Disabled"), _("Reports are currently disabled.")
        if config["channel"] is None:
            return "⚠️", _("No Channel Set"), _("Please set a channel for reports.")
        return "✅", _("Enabled"), _("Reports are enabled and configured.")

    async def get_settings(
        self,
        guild: discord.Guild,
        view: SettingsView,
    ) -> tuple[str, str, list[dict], list[discord.ui.Item]]:
        config = await self.config_value(guild)()
        title = _("Security — {emoji} {name} {status}").format(
            emoji=self.emoji,
            name=self.name,
            status=(await self.get_status(guild))[0],
        )
        description = _("Configure how members can report other members and messages to staff.")
        status = await self.get_status(guild)
        if status[0] == "⚠️":
            description += f"\n{status[0]} **{status[1]}**: {status[2]}\n"

        channel = (
            channel
            if (channel_id := config["channel"]) is not None
            and (channel := guild.get_channel(channel_id)) is not None
            else None
        )
        ping_role = (
            role
            if (role_id := config["ping_role"]) is not None
            and (role := guild.get_role(role_id)) is not None
            else None
        )
        fields = [
            {
                "name": _("Anonymous Reporting:"),
                "value": "✅" if config["anonymous"] else "❌",
                "inline": True,
            },
            {
                "name": _("Staff Can Act on Reports:"),
                "value": "✅" if config["allow_staff_actions"] else "❌",
                "inline": True,
            },
            {
                "name": _("Channel:"),
                "value": f"{channel.mention} (`{channel}`)"
                if channel is not None
                else _("Not set"),
                "inline": True,
            },
            {
                "name": _("Ping Role:"),
                "value": f"{ping_role.mention} (`{ping_role}`)"
                if ping_role is not None
                else _("Not set"),
                "inline": True,
            },
            {
                "name": _("Report Cooldown:"),
                "value": f"`{config['cooldown']}`",
                "inline": True,
            },
        ]

        components = [ToggleModuleButton(self, guild, view, config["enabled"])]

        create_a_report_channel_button: discord.ui.Button = discord.ui.Button(
            emoji=Emojis.CHANNEL.value,
            label=_("Create a Report Channel"),
            style=discord.ButtonStyle.secondary,
            disabled=not guild.me.guild_permissions.manage_channels,
        )

        async def create_a_report_channel_callback(interaction: discord.Interaction):
            await interaction.response.defer(ephemeral=True, thinking=True)
            channel = await guild.create_text_channel(
                name=_("{emoji}・reports").format(emoji=Emojis.REPORTS.value),
                topic=_("This channel is used for reports."),
                overwrites={
                    guild.default_role: discord.PermissionOverwrite(
                        view_channel=False,
                        send_messages=False,
                    ),
                    guild.me: discord.PermissionOverwrite(
                        view_channel=True,
                        send_messages=True,
                        embed_links=True,
                    ),
                },
                reason=_("Created by Security's Reports Module."),
            )
            config["channel"] = channel.id
            await self.config_value(guild).channel.set(channel.id)
            await interaction.followup.send(
                _("✅ A new report channel has been created: {channel.mention}.").format(
                    channel=channel,
                ),
                ephemeral=True,
            )
            await view.edit_message()

        create_a_report_channel_button.callback = create_a_report_channel_callback
        components.append(create_a_report_channel_button)

        anonymous_button: discord.ui.Button = discord.ui.Button(
            emoji="🕵️",
            label=_("Anonymous Reporting"),
            style=discord.ButtonStyle.success
            if config["anonymous"]
            else discord.ButtonStyle.danger,
        )

        async def anonymous_callback(interaction: discord.Interaction):
            await interaction.response.defer()
            config["anonymous"] = not config["anonymous"]
            await self.config_value(guild).anonymous.set(config["anonymous"])
            await view.edit_message()

        anonymous_button.callback = anonymous_callback
        components.append(anonymous_button)

        staff_actions_button: discord.ui.Button = discord.ui.Button(
            emoji=Emojis.ISSUED_BY.value,
            label=_("Staff Actions"),
            style=discord.ButtonStyle.success
            if config["allow_staff_actions"]
            else discord.ButtonStyle.danger,
        )

        async def staff_actions_callback(interaction: discord.Interaction):
            await interaction.response.defer()
            config["allow_staff_actions"] = not config["allow_staff_actions"]
            await self.config_value(guild).allow_staff_actions.set(config["allow_staff_actions"])
            await view.edit_message()

        staff_actions_button.callback = staff_actions_callback
        components.append(staff_actions_button)

        channel_select: discord.ui.ChannelSelect = discord.ui.ChannelSelect(
            channel_types=[discord.ChannelType.text],
            placeholder=_("Select report channel"),
            min_values=0,
            max_values=1,
            default_values=[channel] if channel is not None else [],
        )

        async def channel_callback(interaction: discord.Interaction):
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

        role_select: discord.ui.RoleSelect = discord.ui.RoleSelect(
            placeholder=_("Select ping role"),
            min_values=0,
            max_values=1,
            default_values=[ping_role] if ping_role is not None else [],
        )

        async def role_callback(interaction: discord.Interaction):
            selected = role_select.values[0] if role_select.values else None
            if selected is not None:
                config["ping_role"] = selected.id
                await self.config_value(guild).ping_role.set(selected.id)
            else:
                config["ping_role"] = None
                await self.config_value(guild).ping_role.clear()
            await view.edit_message()

        role_select.callback = role_callback
        components.append(role_select)

        cooldown_button: discord.ui.Button = discord.ui.Button(
            label=_("Report Cooldown"),
            style=discord.ButtonStyle.secondary,
        )

        async def cooldown_button_callback(interaction: discord.Interaction) -> None:
            await interaction.response.send_modal(
                ConfigureReportCooldownModal(self, guild, view, config["cooldown"]),
            )

        cooldown_button.callback = cooldown_button_callback
        components.append(cooldown_button)

        return title, description, fields, components

    async def report(
        self,
        interaction: discord.Interaction,
        target: discord.Member | discord.Message,
    ) -> None:
        config = await self.config_value(interaction.guild)()
        if not config["enabled"]:
            await interaction.response.send_message(
                _("Reports are currently disabled."),
                ephemeral=True,
            )
            return
        if (channel_id := config["channel"]) is None or interaction.guild.get_channel(
            channel_id,
        ) is None:
            await interaction.response.send_message(_("Report channel is not set."), ephemeral=True)
            return
        member = target if isinstance(target, discord.Member) else target.author
        if member.bot:
            await interaction.response.send_message(_("You can't report a bot."), ephemeral=True)
            return
        if member == interaction.user:
            await interaction.response.send_message(_("You can't report yourself."), ephemeral=True)
            return
        if (
            await self.cog.is_whitelisted(member, "reports")
            if isinstance(target, discord.Member)
            else await self.cog.is_message_whitelisted(target, "reports")
        ):
            await interaction.response.send_message(
                _("You can't report this target."),
                ephemeral=True,
            )
            return
        if (
            last_report_at := self.last_report_at[interaction.guild.id].get(interaction.user.id)
        ) is not None:
            cooldown = await DurationConverter.convert(None, config["cooldown"])
            retry_at = last_report_at + cooldown
            if retry_at > datetime.datetime.now(tz=datetime.timezone.utc):
                await interaction.response.send_message(
                    _("⏳ You're reporting too often. You can report again {relative}.").format(
                        relative=discord.utils.format_dt(retry_at, style="R"),
                    ),
                    ephemeral=True,
                )
                return
        await interaction.response.send_modal(ReasonModal(self, interaction.guild, target))


class ConfigureReportCooldownModal(discord.ui.Modal):
    def __init__(
        self,
        module: ReportsModule,
        guild: discord.Guild,
        view: SettingsView,
        cooldown: str,
    ) -> None:
        self.module: ReportsModule = module
        self.guild: discord.Guild = guild
        self.view: SettingsView = view
        self.cooldown: str = cooldown
        super().__init__(title=_("Report Cooldown"))
        self.cooldown_input: discord.ui.TextInput = discord.ui.TextInput(
            label=_("Cooldown:"),
            style=discord.TextStyle.short,
            default=str(cooldown),
            required=True,
        )
        self.add_item(self.cooldown_input)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        try:
            cooldown = self.cooldown_input.value
            await DurationConverter.convert(None, cooldown)
        except commands.BadArgument as e:
            await interaction.followup.send(
                _("Invalid value: {error}").format(error=str(e)),
                ephemeral=True,
            )
            return
        self.cooldown = cooldown
        await self.module.config_value(self.guild).cooldown.set(cooldown)
        await self.view.edit_message()


class ReasonModal(discord.ui.Modal):
    def __init__(
        self,
        module: ReportsModule,
        guild: discord.Guild,
        target: discord.Member | discord.Message,
    ) -> None:
        super().__init__(
            title=_("Report")
            + " "
            + (_("Member") if isinstance(target, discord.Member) else _("Message")),
        )
        self.module: ReportsModule = module
        self.guild: discord.Guild = guild
        self.target: discord.Member | discord.Message = target
        self.reason = discord.ui.TextInput(
            label=_("Reason:"),
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=500,
        )
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)
        config = await self.module.config_value(self.guild)()
        member = self.target if isinstance(self.target, discord.Member) else self.target.author
        embed: discord.Embed = discord.Embed(
            title=_("{member.display_name} has been reported! {emoji}").format(
                member=member,
                emoji=self.module.emoji,
            ),
            color=Colors.REPORTS.value,
            timestamp=datetime.datetime.now(tz=datetime.timezone.utc),
        )
        embed.description = _("👤 **Member:** {member.mention} (`{member}`) {member_emoji}").format(
            member=member,
            member_emoji=await self.module.cog.get_member_emoji(member),
        )
        if not config["anonymous"]:
            embed.set_author(
                name=interaction.user.display_name,
                icon_url=get_non_animated_asset(interaction.user.display_avatar),
            )
            embed.description += _(
                "\n{emoji} **Reporter:** {reporter.mention} (`{reporter}`) {reporter_emojis}",
            ).format(
                emoji=Emojis.ISSUED_BY.value,
                reporter=interaction.user,
                reporter_emojis=await self.module.cog.get_member_emoji(interaction.user),
            )
        if isinstance(self.target, discord.Message):
            embed.description += _("\n{emoji} **Channel:** {channel.mention} (`{channel}`)").format(
                emoji=Emojis.CHANNEL.value,
                channel=self.target.channel,
            )
            embed.description += _("\n{emoji} **Message:** {jump_url}").format(
                emoji=Emojis.MESSAGE.value,
                jump_url=self.target.jump_url,
            )
            if self.target.content:
                embed.description += f"\n{box(self.target.content)}"
            if self.target.attachments:
                embed.description += _("\n{emoji} **Attachments:**").format(
                    emoji=Emojis.ATTACHMENTS.value,
                ) + "\n".join(
                    f" - [{attachment.filename}]({attachment.url})"
                    for attachment in self.target.attachments
                )
        embed.set_thumbnail(url=get_non_animated_asset(member.display_avatar))
        embed.add_field(
            name=_("Reason:"),
            value=f">>> {self.reason.value}",
        )
        embed.set_footer(
            text=self.guild.name,
            icon_url=get_non_animated_asset(self.guild.icon),
        )
        channel = self.guild.get_channel(config["channel"])
        ping_role = (
            ping_role
            if (ping_role_id := config["ping_role"]) is not None
            and (ping_role := self.guild.get_role(ping_role_id)) is not None
            else None
        )
        view: ActionsView = ActionsView(
            self.module.cog,
            member,
            staff_allowed=config["allow_staff_actions"],
        )
        await view.populate()
        view._message = await channel.send(
            content=ping_role.mention if ping_role is not None else None,
            embed=embed,
            view=view,
            allowed_mentions=discord.AllowedMentions(roles=True),
        )
        self.module.cog.views[view._message] = view
        await self.module.cog.record_weekly_stat(self.guild, "report")
        self.module.last_report_at[self.guild.id][interaction.user.id] = datetime.datetime.now(
            tz=datetime.timezone.utc,
        )
        await interaction.followup.send(
            _("Your report has been submitted successfully. Thank you!"),
            ephemeral=True,
        )

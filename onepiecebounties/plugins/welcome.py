from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import random

_: Translator = Translator("OnePieceBounties", __file__)


class WelcomePlugin:
    @commands.Cog.listener()
    async def on_member_join(
        self,
        member: discord.Member,
        welcome_channel: typing.Optional[typing.Union[discord.TextChannel, discord.VoiceChannel, discord.Thread]] = None,
    ) -> None:
        if welcome_channel is None:
            config = await self.config.guild(member.guild).plugins.Welcome()
            if (
                not config["enabled"]
                or (welcome_channel_id := config["channel"]) is None
                or (welcome_channel := member.guild.get_channel(welcome_channel_id)) is None
                or not welcome_channel.permissions_for(member.guild.me).send_messages
            ):
                return
        if member.bot:
            bot_messages = [
                "**{bot_member.name}** has joined the crew, ready to conquer the Grand Line!",
                "Ahoy, nakamas! **{bot_member.name}** has docked, bringing treasures from the New World!",
                "Yo-ho-ho! **{bot_member.name}** has anchored, ready to set sail for One Piece!",
                "Shiver me timbers! **{bot_member.name}** has joined the Straw Hat fleet!",
                "Blimey! **{bot_member.name}** just arrived, aiming to become the Pirate King of bots!",
                "Look out! **{bot_member.name}** just washed up on our shores!",
                "A mysterious mechanical nakama, **{bot_member.name}**, has joined our voyage!",
                "Franky would be proud! **{bot_member.name}** has joined our crew to help maintain the ship!",
                "Is it a bird? Is it a fish? No, it's **{bot_member.name}** joining our adventure!",
            ]
            await welcome_channel.send(random.choice(bot_messages).format(bot_member=member))
            return
        welcome_view: WelcomeView = WelcomeView(self, member)
        await welcome_view.update_buttons(member.guild)
        welcome_view._message = await welcome_channel.send(
            content=_(
                "## 🏴‍☠️ {member.mention} has joined **{guild.name}**!\n"
            ).format(member=member, guild=member.guild),
            **await self.get_kwargs(member),
            view=welcome_view,
        )
        self.views[welcome_view._message] = welcome_view


class WelcomeView(discord.ui.View):
    def __init__(self, cog: commands.Cog, member: discord.Member) -> None:
        self.cog: commands.Cog = cog
        self.member: discord.Member = member
        super().__init__(timeout=60**2)

        self._message: discord.Message = None
        self.toasters: typing.List[discord.Member] = []

        self.toast.label = _("Toast")
        self.log_pose.label = _("Log Pose")

    async def on_timeout(self) -> None:
        for child in self.children:
            child: discord.ui.Item
            if hasattr(child, "disabled") and not (
                isinstance(child, discord.ui.Button) and child.style == discord.ButtonStyle.url
            ):
                self.remove_item(child)
        try:
            await self._message.edit(view=self)
        except discord.HTTPException:
            pass

    @discord.ui.button(emoji="🍻", label="Toast", style=discord.ButtonStyle.success)
    async def toast(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        if interaction.guild.get_member(self.member.id) is None:
            await interaction.response.send_message(
                _("The member you are trying to toast is no longer in the server."),
                ephemeral=True,
            )
            return
        if interaction.user == self.member:
            await interaction.response.send_message(
                _("You can't toast yourself!"), ephemeral=True
            )
        if interaction.user in self.toasters:
            await interaction.response.send_message(
                _("You've already toasted this member!"), ephemeral=True
            )
        toasts = [
            _('{user.mention} grins widely: "To {new_member.mention} joining our grand voyage!"'),
            _('{user.mention} raises a flag: "Another brave soul for our pirate crew!"'),
            _('{user.mention}: "May your log pose always point to adventure, {new_member.mention}!"'),
            _('{user.mention} slams down a mug: "To finding nakama in the vast blue sea!"'),
            _('{user.mention} declares: "Even the Pirate King needs a reliable crew like {new_member.mention}!"'),
            _('{user.mention}: "To dreams as vast as the Grand Line!"'),
            _('{user.mention} toasts: "May your bounty rise with each adventure, {new_member.mention}!"'),
            _('{user.mention}: "The Will of D lives on in our new nakama!"'),
            _('{user.mention} raises a barrel of sake: "To the treasures we\'ll find together!"'),
            _('{user.mention}: "Even Gol D. Roger would welcome {new_member.mention} aboard!"'),
            _('{user.mention} cheers: "Your wanted poster just joined our wall of fame, {new_member.mention}!"'),
            _('{user.mention}: "To sailing beyond the Red Line with our new crewmate!"'),
            _('{user.mention} toasts: "Even the All Blue isn\'t as vast as the adventures ahead!"'),
            _('{user.mention}: "May your spirit be as unbreakable as Luffy\'s will, {new_member.mention}!"'),
            _('{user.mention} shares a toast: "To finding our own Laugh Tale together!"')
        ]
        await interaction.response.send_message(
            random.choice(toasts).format(user=interaction.user, new_member=self.member),
        )
        self.toasters.append(interaction.user)

    @discord.ui.button(emoji="🧭", label="Log Pose", style=discord.ButtonStyle.primary)
    async def log_pose(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        channels = [
            channel
            for channel_id in await self.cog.config.guild(interaction.guild).welcome_log_pose_channels()
            if (channel := interaction.guild.get_channel(channel_id)) is not None
        ]
        await interaction.response.send_message(
            _(
                "# Navigator's Guide\n\n"
                "Welcome aboard the {guild.name} ship! Here's your Log Pose to navigate our waters:\n"
            ).format(guild=interaction.guild)
            + "\n".join(
                f"🏴‍☠️ {channel.mention}"
                for channel in channels
            )
            + _("\n\n*It's not about the destination, it's about the journey!*"),
            ephemeral=True,
        )

    @discord.ui.button(emoji="💰", label="Bounty Info", style=discord.ButtonStyle.danger)
    async def bounty_info(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await interaction.response.send_message(
            _(
                "# Bounty System\n\n"
                "In our crew, everyone gets a bounty when they join!\n\n"
                "**Bounty Tiers:**\n{tiers}\n\n"
                "Be active and helpful to raise your bounty over time!\n"
                "*\"Your bounty doesn't determine your worth to the crew.\"*"
            ).format(
                tiers="\n".join(
                    f"💰 **{tier[0]}**: **+ {tier[1]:,}** berries"
                    for tier in self.cog.get_bounty_tiers()
                )
            ),
            ephemeral=True,
        )

    async def update_buttons(self, guild: discord.Guild) -> None:
        config = await self.cog.config.guild(guild).plugins.Welcome()
        if not config["log_pose_channels"]:
            self.remove_item(self.log_pose)
        for label_link in config["link_buttons"]:
            self.add_item(
                discord.ui.Button(
                    label=label_link[0],
                    url=label_link[1],
                    style=discord.ButtonStyle.link,
                )
            )

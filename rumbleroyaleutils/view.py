from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator  # isort:skip
import discord  # isort:skip

_ = Translator("RumbleRoyaleUtils", __file__)


class AmIAliveView(discord.ui.View):
    def __init__(self, cog: commands.Cog) -> None:
        self.cog: commands.Cog = cog
        super().__init__(timeout=10 * 60)
        self._message: discord.Message = None
        self.am_i_alive.label = _("Am I Alive?")

    async def on_timeout(self) -> None:
        for child in self.children:
            child: discord.ui.Item
            if hasattr(child, "disabled") and not (
                isinstance(child, discord.ui.Button) and child.style == discord.ButtonStyle.url
            ):
                child.disabled = True
        try:
            await self._message.edit(view=self)
        except discord.HTTPException:
            pass

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.channel not in self.cog.rumbles:
            await interaction.response.send_message(
                _("There is no active Rumble Royale in this channel."), ephemeral=True
            )
            return False
        if interaction.user not in self.cog.rumbles[interaction.channel].players:
            await interaction.response.send_message(
                _("You are not a participant in this Rumble Royale."), ephemeral=True
            )
            return False
        return True

    @discord.ui.button(emoji="😃", label="Am I Alive?", style=discord.ButtonStyle.success)
    async def am_i_alive(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        embed: discord.Embed = discord.Embed(timestamp=interaction.message.created_at)
        embed.set_author(
            name=interaction.user.display_name,
            icon_url=interaction.user.display_avatar,
        )
        alive = True
        description = []
        for event in self.cog.rumbles[interaction.channel].players[interaction.user]:
            alive = event.type != "death"
            if event.type == "kill":
                description.append(
                    _("- **🔪 Round {round_number}:** You killed {other}.").format(
                        round_number=event.round_number,
                        other=f"{event.other.mention} (`{event.other}`)",
                    )
                )
            elif event.type == "death":
                description.append(
                    _("- **💀 Round {round_number}:** You died{killed}.").format(
                        round_number=event.round_number,
                        killed=(
                            _(", killed by {other}").format(
                                other=f"{event.other.mention} (`{event.other}`)"
                            )
                            if event.other is not None
                            else ""
                        ),
                    )
                )
            elif event.type == "revive":
                description.append(
                    _("- **💖 Round {round_number}:** You were revived.").format(
                        round_number=event.round_number,
                    )
                )
            elif event.type == "apparition":
                description.append(
                    _("- **👻 Round {round_number}:** You appeared.").format(
                        round_number=event.round_number,
                    )
                )
            description[-1] += f"\n-# {event.message.jump_url} {event.cause}"
        if alive:
            embed.title = _("😃 You are alive!")
            embed.color = discord.Color.green()
        else:
            embed.title = _("💀 You are dead!")
            embed.color = discord.Color.red()
        embed.description = (
            "\n".join(description) if description else _("You have no events recorded.")
        )
        embed.set_footer(text=interaction.guild.name, icon_url=interaction.guild.icon)
        await interaction.response.send_message(embed=embed, ephemeral=True)

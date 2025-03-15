from AAA3A_utils import CogsUtils  # isort:skip
from redbot.core import commands, bank  # isort:skip
from redbot.core.i18n import Translator  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import datetime

_: Translator = Translator("AdventCalendar", __file__)


class SetRewardsView(discord.ui.View):
    def __init__(self, cog: commands.Cog) -> None:
        super().__init__(timeout=60 * 10)
        self.cog: commands.Cog = cog
        self.ctx: commands.Context = None

        self.current_day: typing.Optional[int] = 1

        self.role.label = _("Role")
        self.temp_role.label = _("Temp Role")
        self.bank_credits.label = _("Bank Credits")
        self.levelup_xp.label = _("LevelUp XP")
        self.custom_reward.label = _("Custom Reward")
        self.message.label = _("Message")
        self.nothing.label = _("Nothing")
        self.clear.label = _("Clear")
        self.clear_all.label = _("Clear All")

    async def start(self, ctx: commands.Context) -> discord.Message:
        self.ctx: commands.Context = ctx
        await self._update(edit_message=False)
        self._message: discord.Message = await ctx.send(
            embed=await self.get_embed(),
            view=self,
            file=discord.File(self.cog.christmas_tree_path, filename="christmas_tree.png"),
        )
        self.cog.views[self._message] = self
        return self._message

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id not in [self.ctx.author.id] + list(self.ctx.bot.owner_ids):
            await interaction.response.send_message(
                _("You are not allowed to use this interaction."), ephemeral=True
            )
            return False
        return True

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

    async def get_embed(self) -> discord.Embed:
        embed: discord.Embed = discord.Embed(
            title=(
                _("🎄 Final (24 boxes opened) 🎄")
                if self.current_day is None
                else _("🎄 Rewards for Day {day} 🎄").format(day=self.current_day)
            ),
            color=await self.ctx.embed_color(),
        )
        embed.set_thumbnail(url="attachment://christmas_tree.png")
        day_rewards = await self.cog.config.guild(self.ctx.guild).rewards.get_raw(
            str(self.current_day) if self.current_day is not None else "null"
        )
        for reward in sorted(
            day_rewards,
            key=lambda r: (
                r["priority"],
                (
                    "role",
                    "temp_role",
                    "bank_credits",
                    "levelup_xp",
                    "custom",
                    "message",
                    None,
                ).index(r["type"]),
            ),
        ):
            if reward["type"] == "role":
                role = self.ctx.guild.get_role(reward["role_id"])
                if role is None:
                    continue
                embed.add_field(
                    name=_(
                        "• Role Reward ({priority} ; {percent}{multiplied_priority_percent})"
                    ).format(
                        priority=reward["priority"],
                        percent=round(
                            reward["priority"] / sum([r["priority"] for r in day_rewards]) * 100, 2
                        ),
                        multiplied_priority_percent=(
                            f" ; x{reward['priority_multiplier'] or 1} {round(reward['priority'] * (reward['priority_multiplier'] or 1) / sum([r['priority'] * (r['priority_multiplier'] or 1) for r in day_rewards]) * 100, 2)}%"
                            if any(r["priority_multiplier"] is not None for r in day_rewards)
                            else ""
                        ),
                    ),
                    value=f"{role.mention} ({role.id})",
                    inline=False,
                )
            elif reward["type"] == "temp_role":
                role = self.ctx.guild.get_role(reward["role_id"])
                if role is None:
                    continue
                embed.add_field(
                    name=_(
                        "• Temp Role Reward ({priority} ; {percent}%{multiplied_priority_percent})"
                    ).format(
                        priority=reward["priority"],
                        percent=round(
                            reward["priority"] / sum([r["priority"] for r in day_rewards]) * 100, 2
                        ),
                        multiplied_priority_percent=(
                            f" ; x{reward['priority_multiplier'] or 1} {round(reward['priority'] * (reward['priority_multiplier'] or 1) / sum([r['priority'] * (r['priority_multiplier'] or 1) for r in day_rewards]) * 100, 2)}%"
                            if any(r["priority_multiplier"] is not None for r in day_rewards)
                            else ""
                        ),
                    ),
                    value=f"{role.mention} ({role.id}) for {CogsUtils.get_interval_string(datetime.timedelta(seconds=reward['duration']))}",
                    inline=False,
                )
            elif reward["type"] == "bank_credits":
                embed.add_field(
                    name=_(
                        "• Bank Credits Reward ({priority} ; {percent}%{multiplied_priority_percent})"
                    ).format(
                        priority=reward["priority"],
                        percent=round(
                            reward["priority"] / sum([r["priority"] for r in day_rewards]) * 100, 2
                        ),
                        multiplied_priority_percent=(
                            f" ; x{reward['priority_multiplier'] or 1} {round(reward['priority'] * (reward['priority_multiplier'] or 1) / sum([r['priority'] * (r['priority_multiplier'] or 1) for r in day_rewards]) * 100, 2)}%"
                            if any(r["priority_multiplier"] is not None for r in day_rewards)
                            else ""
                        ),
                    ),
                    value=f"+ {reward['amount']} credits",
                    inline=False,
                )
            elif reward["type"] == "levelup_xp":
                embed.add_field(
                    name=_(
                        "• LevelUp XP Reward ({priority} ; {percent}%{multiplied_priority_percent})"
                    ).format(
                        priority=reward["priority"],
                        percent=round(
                            reward["priority"] / sum([r["priority"] for r in day_rewards]) * 100, 2
                        ),
                        multiplied_priority_percent=(
                            f" ; x{reward['priority_multiplier'] or 1} {round(reward['priority'] * (reward['priority_multiplier'] or 1) / sum([r['priority'] * (r['priority_multiplier'] or 1) for r in day_rewards]) * 100, 2)}%"
                            if any(r["priority_multiplier"] is not None for r in day_rewards)
                            else ""
                        ),
                    ),
                    value=f"+ {reward['amount']} XP",
                    inline=False,
                )
            elif reward["type"] == "custom":
                embed.add_field(
                    name=_(
                        "• Custom Reward ({priority} ; {percent}%{multiplied_priority_percent})"
                    ).format(
                        priority=reward["priority"],
                        percent=round(
                            reward["priority"] / sum([r["priority"] for r in day_rewards]) * 100, 2
                        ),
                        multiplied_priority_percent=(
                            f" ; x{reward['priority_multiplier'] or 1} {round(reward['priority'] * (reward['priority_multiplier'] or 1) / sum([r['priority'] * (r['priority_multiplier'] or 1) for r in day_rewards]) * 100, 2)}%"
                            if any(r["priority_multiplier"] is not None for r in day_rewards)
                            else ""
                        ),
                    ),
                    value=f">>> {reward['label']}",
                    inline=False,
                )
            elif reward["type"] == "message":
                embed.add_field(
                    name=_(
                        "• Message ({priority} ; {percent}%{multiplied_priority_percent})"
                    ).format(
                        priority=reward["priority"],
                        percent=round(
                            reward["priority"] / sum([r["priority"] for r in day_rewards]) * 100, 2
                        ),
                        multiplied_priority_percent=(
                            f" ; x{reward['priority_multiplier'] or 1} {round(reward['priority'] * (reward['priority_multiplier'] or 1) / sum([r['priority'] * (r['priority_multiplier'] or 1) for r in day_rewards]) * 100, 2)}%"
                            if any(r["priority_multiplier"] is not None for r in day_rewards)
                            else ""
                        ),
                    ),
                    value=f">>> {reward['message']}",
                    inline=False,
                )
            elif reward["type"] is None:
                embed.add_field(
                    name=_(
                        "• Nothing ({priority} ; {percent}%{multiplied_priority_percent})"
                    ).format(
                        priority=reward["priority"],
                        percent=round(
                            reward["priority"] / sum([r["priority"] for r in day_rewards]) * 100, 2
                        ),
                        multiplied_priority_percent=(
                            f" ; x{reward['priority_multiplier'] or 1} {round(reward['priority'] * (reward['priority_multiplier'] or 1) / sum([r['priority'] * (r['priority_multiplier'] or 1) for r in day_rewards]) * 100, 2)}%"
                            if any(r["priority_multiplier"] is not None for r in day_rewards)
                            else ""
                        ),
                    ),
                    value="\u200b",
                    inline=False,
                )
        embed.set_footer(text=self.ctx.guild.name, icon_url=self.ctx.guild.icon)
        return embed

    async def _update(
        self,
        page: typing.Optional[int] = discord.utils.MISSING,
        edit_message: bool = True,
    ) -> None:
        if page is not discord.utils.MISSING:
            self.current_day = page
        for button in self.children:
            button: discord.ui.Button
            button.disabled = False
        if self.current_day == 1:
            self.first_page.disabled = True
            self.previous_page.disabled = True
        elif self.current_day is None:
            self.last_page.disabled = True
            self.next_page.disabled = True
        self.temp_role.disabled = self.cog.bot.get_cog("TempRoles") is None
        self.bank_credits.disabled = await bank.is_global()
        self.levelup_xp.disabled = self.cog.bot.get_cog("LevelUp") is None
        self.custom_reward.disabled = (
            custom_rewards_logs_channel_id := await self.cog.config.guild(
                self.ctx.guild
            ).custom_rewards_logs_channel()
        ) is None or self.ctx.guild.get_channel(custom_rewards_logs_channel_id) is None
        day_rewards = await self.cog.config.guild(self.ctx.guild).rewards.get_raw(
            str(self.current_day) if self.current_day is not None else "null"
        )
        if len(day_rewards) >= 5:
            for button in [
                self.role,
                self.temp_role,
                self.bank_credits,
                self.levelup_xp,
                self.custom_reward,
                self.message,
                self.nothing,
            ]:
                button.disabled = True
        self.clear.disabled = not day_rewards
        self.clear_all.disabled = not any(
            [reward for reward in (await self.cog.config.guild(self.ctx.guild).rewards()).values()]
        )
        if edit_message:
            await self._message.edit(
                embed=await self.get_embed(),
                view=self,
            )

    @discord.ui.button(emoji="⏮️", style=discord.ButtonStyle.secondary, row=0)
    async def first_page(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await interaction.response.defer()
        await self._update(page=1)

    @discord.ui.button(emoji="◀️", style=discord.ButtonStyle.secondary, row=0)
    async def previous_page(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await interaction.response.defer()
        if self.current_day == 1:
            page = None
        elif self.current_day is None:
            page = 24
        else:
            page = self.current_day - 1
        await self._update(page=page)

    @discord.ui.button(emoji="✖️", style=discord.ButtonStyle.danger, row=0)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer()
        try:
            await self._message.delete()
        except discord.HTTPException:
            pass

    @discord.ui.button(emoji="▶️", style=discord.ButtonStyle.secondary, row=0)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer()
        if self.current_day == 24:
            page = None
        elif self.current_day is None:
            page = 1
        else:
            page = self.current_day + 1
        await self._update(page=page)

    @discord.ui.button(emoji="⏭️", style=discord.ButtonStyle.secondary, row=0)
    async def last_page(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer()
        await self._update(page=None)

    @discord.ui.button(label="Role", style=discord.ButtonStyle.success, row=1)
    async def role(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.send_modal(RoleRewardModal(self.cog, self.current_day, self))

    @discord.ui.button(label="Temp Role", style=discord.ButtonStyle.success, row=1)
    async def temp_role(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.send_modal(
            TempRoleRewardModal(self.cog, self.current_day, self)
        )

    @discord.ui.button(label="Bank Credits", style=discord.ButtonStyle.success, row=1)
    async def bank_credits(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await interaction.response.send_modal(
            BankCreditsRewardModal(self.cog, self.current_day, self)
        )

    @discord.ui.button(label="LevelUp XP", style=discord.ButtonStyle.success, row=1)
    async def levelup_xp(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await interaction.response.send_modal(
            LevelUpXPRewardModal(self.cog, self.current_day, self)
        )

    @discord.ui.button(label="Custom Reward", style=discord.ButtonStyle.success, row=1)
    async def custom_reward(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await interaction.response.send_modal(CustomRewardModal(self.cog, self.current_day, self))

    @discord.ui.button(label="Message", style=discord.ButtonStyle.success, row=2)
    async def message(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.send_modal(MessageModal(self.cog, self.current_day, self))

    @discord.ui.button(label="Nothing", style=discord.ButtonStyle.success, row=2)
    async def nothing(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.send_modal(NothingModal(self.cog, self.current_day, self))

    @discord.ui.button(label="Clear", style=discord.ButtonStyle.danger, row=2)
    async def clear(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer()
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
        if not await CogsUtils.ConfirmationAsk(
            fake_context,
            (
                _("Are you sure you want to clear all rewards for day {day}?").format(
                    day=self.current_day
                )
                if self.current_day is not None
                else _("Are you sure you want to clear all final rewards?")
            ),
            ephemeral=True,
            timeout_message=None,
        ):
            return
        await self.cog.config.guild(self.ctx.guild).rewards.clear_raw(
            str(self.current_day) if self.current_day is not None else "null"
        )
        await self._update()

    @discord.ui.button(label="Clear All", style=discord.ButtonStyle.danger, row=2)
    async def clear_all(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer()
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
        if not await CogsUtils.ConfirmationAsk(
            fake_context,
            _("Are you sure you want to clear all rewards?"),
            ephemeral=True,
            timeout_message=None,
        ):
            return
        await self.cog.config.guild(self.ctx.guild).rewards.clear_raw()
        await self._update()


class PriorityModal(discord.ui.Modal):
    def __init__(
        self, cog: commands.Cog, day: typing.Optional[int], view: SetRewardsView, *, title: str
    ) -> None:
        super().__init__(title=title)
        self.cog: commands.Cog = cog
        self.day: typing.Optional[int] = day
        self.view: SetRewardsView = view

        self.priority: discord.ui.TextInput = discord.ui.TextInput(
            label=_("Priority:"),
            placeholder=_("Enter the priority of the reward..."),
            min_length=1,
            max_length=3,
            required=True,
            default="10",
        )
        self.add_item(self.priority)
        self.priority_multiplier: discord.ui.TextInput = discord.ui.TextInput(
            label=_("Priority Multiplier (for configured roles):"),
            placeholder=_("Keep empty if you don't want this feature..."),
            min_length=1,
            max_length=2,
            required=False,
        )
        self.add_item(self.priority_multiplier)


class RoleConverter(commands.RoleConverter):
    async def convert(self, ctx: commands.Context, argument: str) -> discord.Role:
        role: discord.Role = await super().convert(ctx, argument)
        if not role.is_assignable():
            raise commands.BadArgument(_("I can't assign this role."))
        if role >= ctx.author.top_role and ctx.author.id not in ctx.bot.owner_ids:
            raise commands.BadArgument(_("This role is higher than your top role."))
        return role


class RoleRewardModal(PriorityModal):
    def __init__(self, *args, **kwargs) -> None:
        kwargs["title"] = kwargs.get("title", _("Role Reward"))
        super().__init__(*args, **kwargs)

        self.role: discord.ui.TextInput = discord.ui.TextInput(
            label=_("Role:"),
            placeholder=_("Enter the role name/ID..."),
            min_length=1,
            max_length=20,
            required=True,
        )
        self.add_item(self.role)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        try:
            priority = int(self.priority.value)
        except ValueError:
            priority = 10
        try:
            priority_multiplier = int(self.priority_multiplier.value)
            if priority_multiplier <= 1:
                raise ValueError()
        except ValueError:
            priority_multiplier = None
        try:
            role = await RoleConverter().convert(self.view.ctx, self.role.value)
        except commands.BadArgument as e:
            await interaction.response.send_message(str(e), ephemeral=True)
            return
        await interaction.response.defer()
        day_rewards = await self.cog.config.guild(self.view.ctx.guild).rewards.get_raw(
            str(self.day) if self.day is not None else "null"
        )
        day_rewards.append(
            {
                "type": "role",
                "priority": priority,
                "priority_multiplier": priority_multiplier,
                "role_id": role.id,
            }
        )
        await self.cog.config.guild(self.view.ctx.guild).rewards.set_raw(
            str(self.day) if self.day is not None else "null", value=day_rewards
        )
        await self.view._update()


class TempRoleRewardModal(RoleRewardModal):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs, title=_("Temp Role Reward"))

        self.duration: discord.ui.TextInput = discord.ui.TextInput(
            label=_("Duration:"),
            placeholder=_("Enter the duration..."),
            min_length=1,
            max_length=20,
            required=True,
            default="4w",
        )
        self.add_item(self.duration)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        try:
            priority = int(self.priority.value)
        except ValueError:
            priority = 10
        try:
            priority_multiplier = int(self.priority_multiplier.value)
            if priority_multiplier <= 1:
                raise ValueError()
        except ValueError:
            priority_multiplier = None
        try:
            role = await RoleConverter().convert(self.view.ctx, self.role.value)
        except commands.BadArgument as e:
            await interaction.response.send_message(str(e), ephemeral=True)
            return
        # try:
        from temproles.temproles import DurationConverter

        # except ImportError:
        #     await interaction.response.send_message(
        #         _("You must install/load update the TempRoles cog by AAA3A to use this feature."),
        #         ephemeral=True,
        #     )
        #     return
        try:
            duration = await DurationConverter.convert(self.view.ctx, self.duration.value)
        except commands.BadArgument as e:
            await interaction.response.send_message(str(e), ephemeral=True)
            return
        await interaction.response.defer()
        day_rewards = await self.cog.config.guild(self.view.ctx.guild).rewards.get_raw(
            str(self.day) if self.day is not None else "null"
        )
        day_rewards.append(
            {
                "type": "temp_role",
                "priority": priority,
                "priority_multiplier": priority_multiplier,
                "role_id": role.id,
                "duration": duration.total_seconds(),
            }
        )
        await self.cog.config.guild(self.view.ctx.guild).rewards.set_raw(
            str(self.day) if self.day is not None else "null", value=day_rewards
        )
        await self.view._update()


class BankCreditsRewardModal(PriorityModal):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs, title=_("Bank Credits Reward"))

        self.amount: discord.ui.TextInput = discord.ui.TextInput(
            label=_("Bank Credits Amount:"),
            placeholder=_("Enter the bank credits amount to give..."),
            min_length=1,
            max_length=10,
            required=True,
        )
        self.add_item(self.amount)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        try:
            priority = int(self.priority.value)
        except ValueError:
            priority = 10
        try:
            priority_multiplier = int(self.priority_multiplier.value)
            if priority_multiplier <= 1:
                raise ValueError()
        except ValueError:
            priority_multiplier = None
        try:
            amount = int(self.amount.value)
            if amount < 1:
                raise ValueError()
        except ValueError:
            await interaction.response.send_message(
                _("The bank credits amount must be a positive number."), ephemeral=True
            )
            return
        await interaction.response.defer()
        day_rewards = await self.cog.config.guild(self.view.ctx.guild).rewards.get_raw(
            str(self.day) if self.day is not None else "null"
        )
        day_rewards.append(
            {
                "type": "bank_credits",
                "priority": priority,
                "priority_multiplier": priority_multiplier,
                "amount": amount,
            }
        )
        await self.cog.config.guild(self.view.ctx.guild).rewards.set_raw(
            str(self.day) if self.day is not None else "null", value=day_rewards
        )
        await self.view._update()


class LevelUpXPRewardModal(PriorityModal):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs, title=_("LevelUp XP Reward"))

        self.amount: discord.ui.TextInput = discord.ui.TextInput(
            label=_("LevelUp XP amount:"),
            placeholder=_("Enter the XP amount..."),
            min_length=1,
            max_length=10,
            required=True,
        )
        self.add_item(self.amount)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        try:
            priority = int(self.priority.value)
        except ValueError:
            priority = 10
        try:
            priority_multiplier = int(self.priority_multiplier.value)
            if priority_multiplier <= 1:
                raise ValueError()
        except ValueError:
            priority_multiplier = None
        try:
            amount = int(self.amount.value)
            if amount < 1:
                raise ValueError()
        except ValueError:
            await interaction.response.send_message(
                _("The XP amount must be a positive number."), ephemeral=True
            )
            return
        await interaction.response.defer()
        day_rewards = await self.cog.config.guild(self.view.ctx.guild).rewards.get_raw(
            str(self.day) if self.day is not None else "null"
        )
        day_rewards.append(
            {
                "type": "levelup_xp",
                "priority": priority,
                "priority_multiplier": priority_multiplier,
                "amount": amount,
            }
        )
        await self.cog.config.guild(self.view.ctx.guild).rewards.set_raw(
            str(self.day) if self.day is not None else "null", value=day_rewards
        )
        await self.view._update()


class CustomRewardModal(PriorityModal):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs, title=_("Custom Reward"))

        self.label: discord.ui.TextInput = discord.ui.TextInput(
            label=_("Label:"),
            placeholder=_("Enter the label..."),
            min_length=1,
            max_length=100,
            required=True,
        )
        self.add_item(self.label)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        try:
            priority = int(self.priority.value)
        except ValueError:
            priority = 10
        try:
            priority_multiplier = int(self.priority_multiplier.value)
            if priority_multiplier <= 1:
                raise ValueError()
        except ValueError:
            priority_multiplier = None
        await interaction.response.defer()
        day_rewards = await self.cog.config.guild(self.view.ctx.guild).rewards.get_raw(
            str(self.day) if self.day is not None else "null"
        )
        day_rewards.append(
            {
                "type": "custom",
                "priority": priority,
                "priority_multiplier": priority_multiplier,
                "label": self.label.value,
            }
        )
        await self.cog.config.guild(self.view.ctx.guild).rewards.set_raw(
            str(self.day) if self.day is not None else "null", value=day_rewards
        )
        await self.view._update()


class MessageModal(PriorityModal):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs, title=_("Message"))

        self.message: discord.ui.TextInput = discord.ui.TextInput(
            label=_("Message:"),
            placeholder=_("Enter the message..."),
            min_length=1,
            max_length=2000,
            required=True,
        )
        self.add_item(self.message)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        try:
            priority = int(self.priority.value)
        except ValueError:
            priority = 10
        try:
            priority_multiplier = int(self.priority_multiplier.value)
            if priority_multiplier <= 1:
                raise ValueError()
        except ValueError:
            priority_multiplier = None
        await interaction.response.defer()
        day_rewards = await self.cog.config.guild(self.view.ctx.guild).rewards.get_raw(
            str(self.day) if self.day is not None else "null"
        )
        day_rewards.append(
            {
                "type": "message",
                "priority": priority,
                "priority_multiplier": priority_multiplier,
                "message": self.message.value,
            }
        )
        await self.cog.config.guild(self.view.ctx.guild).rewards.set_raw(
            str(self.day) if self.day is not None else "null", value=day_rewards
        )
        await self.view._update()


class NothingModal(PriorityModal):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs, title=_("Nothing"))

    async def on_submit(self, interaction: discord.Interaction) -> None:
        try:
            priority = int(self.priority.value)
        except ValueError:
            priority = 10
        try:
            priority_multiplier = int(self.priority_multiplier.value)
            if priority_multiplier <= 1:
                raise ValueError()
        except ValueError:
            priority_multiplier = None
        await interaction.response.defer()
        day_rewards = await self.cog.config.guild(self.view.ctx.guild).rewards.get_raw(
            str(self.day) if self.day is not None else "null"
        )
        day_rewards.append(
            {
                "type": None,
                "priority": priority,
                "priority_multiplier": priority_multiplier,
            }
        )
        await self.cog.config.guild(self.view.ctx.guild).rewards.set_raw(
            str(self.day) if self.day is not None else "null", value=day_rewards
        )
        await self.view._update()

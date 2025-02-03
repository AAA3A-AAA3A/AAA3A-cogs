from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import asyncio
import datetime
import functools

from redbot.core.utils.chat_formatting import box

_: Translator = Translator("Tickets", __file__)


class TicketView(discord.ui.View):
    def __init__(self, cog: commands.Cog, ticket) -> None:
        super().__init__(timeout=None)
        self.cog: commands.Cog = cog
        self.ticket = ticket
        self._message: discord.Message = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        interaction.data["ticket"] = self.ticket
        if not await self.cog.is_support.__func__().predicate(interaction):
            await interaction.response.send_message(
                _("⛔ You aren't allowed to interact with this ticket!"),
                ephemeral=True,
            )
            return False
        if interaction.data["custom_id"].split("_")[
            -1
        ] == "claim" and not await self.cog.is_support.__func__(ignore_owner=True).predicate(
            interaction
        ):
            await interaction.response.send_message(
                _("⛔ You aren't allowed to claim or unclaim this ticket!"),
                ephemeral=True,
            )
            return False
        return True

    async def _update(self, edit_message: bool = False) -> None:
        config = await self.cog.config.guild(self.ticket.guild).profiles.get_raw(
            self.ticket.profile
        )
        self.members.custom_id = f"Tickets_#{self.ticket.id}_members"
        if not self.ticket.is_locked:
            try:
                int(config["emojis"]["lock"])
            except ValueError:
                e = config["emojis"]["lock"]
            else:
                e = (
                    str(e)
                    if (e := self.cog.bot.get_emoji(int(config["emojis"]["lock"]))) is not None
                    else None
                )
            self.lock.emoji = e
            self.lock.label = _("Lock")
            self.lock.style = discord.ButtonStyle.secondary
        else:
            try:
                int(config["emojis"]["unlock"])
            except ValueError:
                e = config["emojis"]["unlock"]
            else:
                e = (
                    str(e)
                    if (e := self.cog.bot.get_emoji(int(config["emojis"]["unlock"]))) is not None
                    else None
                )
            self.lock.emoji = e
            self.lock.label = _("Unlock")
            self.lock.style = discord.ButtonStyle.success
        self.lock.custom_id = f"Tickets_#{self.ticket.id}_lock"
        if not self.ticket.is_claimed:
            try:
                int(config["emojis"]["claim"])
            except ValueError:
                e = config["emojis"]["claim"]
            else:
                e = (
                    str(e)
                    if (e := self.cog.bot.get_emoji(int(config["emojis"]["claim"]))) is not None
                    else None
                )
            self.claim.emoji = e
            self.claim.label = _("Claim")
            self.claim.style = discord.ButtonStyle.success
        else:
            try:
                int(config["emojis"]["unclaim"])
            except ValueError:
                e = config["emojis"]["unclaim"]
            else:
                e = (
                    str(e)
                    if (e := self.cog.bot.get_emoji(int(config["emojis"]["claim"]))) is not None
                    else None
                )
            self.claim.emoji = e
            self.claim.label = _("Unclaim")
            self.claim.style = discord.ButtonStyle.secondary
        self.claim.custom_id = f"Tickets_#{self.ticket.id}_claim"
        if not self.ticket.is_closed:
            self.lock.disabled = False
            self.claim.disabled = False
            try:
                int(config["emojis"]["close"])
            except ValueError:
                e = config["emojis"]["close"]
            else:
                e = (
                    str(e)
                    if (e := self.cog.bot.get_emoji(int(config["emojis"]["close"]))) is not None
                    else None
                )
            self.close.emoji = e
            self.close.label = _("Close")
            self.close.style = discord.ButtonStyle.danger
        else:
            self.lock.disabled = True
            self.claim.disabled = True
            try:
                int(config["emojis"]["reopen"])
            except ValueError:
                e = config["emojis"]["reopen"]
            else:
                e = (
                    str(e)
                    if (e := self.cog.bot.get_emoji(int(config["emojis"]["reopen"]))) is not None
                    else None
                )
            self.close.emoji = e
            self.close.label = _("Reopen")
            self.close.style = discord.ButtonStyle.secondary
        self.close.custom_id = f"Tickets_#{self.ticket.id}_close"
        if edit_message:
            try:
                await self._message.edit(view=self)
            except discord.HTTPException:
                pass

    @discord.ui.button(label="Members", style=discord.ButtonStyle.secondary)
    async def members(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        members_view: MembersView = MembersView(self.cog, self.ticket)
        await interaction.response.send_message(
            embed=await members_view.get_members_embeds(),
            view=members_view,
            ephemeral=True,
        )
        members_view._message = await interaction.original_response()

    @discord.ui.button(label="Lock", style=discord.ButtonStyle.secondary)
    async def lock(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer()
        try:
            if not self.ticket.is_locked:
                await self.ticket.lock(interaction.user)
                await interaction.followup.send(
                    _("🔒 This ticket has been locked!"), ephemeral=True
                )
            else:
                await self.ticket.unlock(interaction.user)
                await interaction.followup.send(
                    _("🔓 This ticket has been unlocked!"), ephemeral=True
                )
        except RuntimeError as e:
            return await interaction.followup.send(
                f"⛔ {e}",
                ephemeral=True,
            )

    @discord.ui.button(label="Claim", style=discord.ButtonStyle.secondary)
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer()
        try:
            if not self.ticket.is_claimed:
                await self.ticket.claim(interaction.user)
                await interaction.followup.send(
                    _("👥 You have claimed this ticket!"), ephemeral=True
                )
            else:
                await self.ticket.unclaim()
                await interaction.followup.send(
                    _("👤 You have unclaimed this ticket!"), ephemeral=True
                )
        except RuntimeError as e:
            return await interaction.followup.send(
                f"⛔ {e}",
                ephemeral=True,
            )

    @discord.ui.button(label="Close", style=discord.ButtonStyle.danger)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        config = await self.cog.config.guild(self.ticket.guild).profiles.get_raw(
            self.ticket.profile
        )
        if not self.ticket.is_closed and not config["owner_can_close"]:
            fake_context = type(
                "FakeContext",
                (),
                {
                    "bot": self.ticket.bot,
                    "guild": self.ticket.guild,
                    "channel": self.ticket.channel,
                    "author": interaction.user,
                    "kwargs": {"profile": self.ticket.profile},
                },
            )()
            if not await self.cog.is_support.__func__(ignore_owner=True).predicate(fake_context):
                raise RuntimeError("⛔ You aren't allowed to close this ticket!")
        elif self.ticket.is_closed and not config["owner_can_reopen"]:
            fake_context = type(
                "FakeContext",
                (),
                {
                    "bot": self.ticket.bot,
                    "guild": self.ticket.guild,
                    "channel": self.ticket.channel,
                    "author": interaction.user,
                    "kwargs": {"profile": self.ticket.profile},
                },
            )()
            if not await self.cog.is_support.__func__(ignore_owner=True).predicate(fake_context):
                raise RuntimeError("⛔ You aren't allowed to reopen this ticket!")
        modal: ReasonModal = ReasonModal(self.cog, self.ticket)
        if config["close_reopen_reason_modal"]:
            await interaction.response.send_modal(modal)
        else:
            await modal.on_submit(interaction)


class MembersView(discord.ui.View):
    def __init__(self, cog: commands.Cog, ticket) -> None:
        super().__init__(timeout=180)
        self.cog: commands.Cog = cog
        self.ticket = ticket

        self._message: discord.Message = None

    async def on_timeout(self) -> None:
        if self._message is not None:
            try:
                await self._message.delete()
            except discord.HTTPException:
                pass

    async def get_members_embeds(self) -> typing.List[discord.Embed]:
        embed: discord.Embed = discord.Embed(
            title=_("{total} Member{s}").format(
                total=len(self.ticket.members_ids),
                s="s" if len(self.ticket.members_ids) > 1 else "",
            ),
            color=await self.cog.bot.get_embed_color(self.ticket.channel),
            timestamp=datetime.datetime.now(tz=datetime.timezone.utc),
        )
        embed.description = "\n".join(
            _("**{i}.** {member.mention} ({member.id})").format(i=i, member=member)
            for i, member in enumerate(self.ticket.members, start=1)
        )
        embed.set_footer(text=self.ticket.guild.name, icon_url=self.ticket.guild.icon)
        return embed

    async def _update(self, edit_message: bool = True) -> None:
        self.add.disabled = len(self.ticket.members) >= 10
        self.remove.disabled = not self.ticket.members
        self.add.placeholder = _("Select the member(s) to add to the ticket.")
        self.remove.placeholder = _("Select the member(s) to remove from the ticket.")
        if edit_message:
            try:
                await self._message.edit(
                    embed=await self.get_members_embeds(),
                    view=self,
                )
            except discord.HTTPException:
                pass

    @discord.ui.select(
        cls=discord.ui.UserSelect,
        min_values=0,
        max_values=10,
        placeholder="Select the member(s) to add to the ticket.",
    )
    async def add(self, interaction: discord.Interaction, select: discord.ui.UserSelect) -> None:
        if not select.values:
            await interaction.response.defer()
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            for member in select.values:
                await self.ticket.add_member(
                    member,
                    interaction.user,
                )
        except RuntimeError as e:
            return await interaction.followup.send(
                f"⛔ {e}",
                ephemeral=True,
            )
        await self._update()
        await interaction.followup.send(
            _("➕ Members have been added to the ticket!"), ephemeral=True
        )

    @discord.ui.select(
        cls=discord.ui.UserSelect,
        min_values=0,
        max_values=10,
        placeholder="Select the member(s) to remove from the ticket.",
    )
    async def remove(
        self, interaction: discord.Interaction, select: discord.ui.UserSelect
    ) -> None:
        if not select.values:
            await interaction.response.defer()
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            for member in select.values:
                await self.ticket.remove_member(
                    member,
                    interaction.user,
                )
        except RuntimeError as e:
            return await interaction.followup.send(
                f"⛔ {e}",
                ephemeral=True,
            )
        await self._update()
        await interaction.followup.send(
            _("➖ Members have been removed from the ticket!"), ephemeral=True
        )


class ReasonModal(discord.ui.Modal):
    def __init__(self, cog: commands.Cog, ticket) -> None:
        self.cog: commands.Cog = cog
        self.ticket = ticket
        super().__init__(
            title=_("Close Ticket") if not self.ticket.is_closed else _("Reopen Ticket")
        )

        self.reason: discord.ui.TextInput = discord.ui.TextInput(
            label=_("Reason:"),
            style=discord.TextStyle.paragraph,
            placeholder=_("Optional reason..."),
            required=False,
            max_length=2000,
        )
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        reason = self.reason.value.strip() or None
        try:
            if not self.ticket.is_closed:
                config = await self.cog.config.guild(self.ticket.guild).profiles.get_raw(
                    self.ticket.profile
                )
                if (
                    interaction.user != self.ticket.owner
                    and self.ticket.owner is not None
                    and config["owner_close_confirmation"]
                ):
                    view: OwnerCloseConfirmation = OwnerCloseConfirmation(self.cog)
                    await view.start(self.ticket, interaction, reason=reason)
                    return
                await self.ticket.close(interaction.user, reason=reason)
                await interaction.response.send_message(
                    _("❌ This ticket has been closed!"),
                    ephemeral=True,
                )
            else:
                await self.ticket.reopen(interaction.user, reason=reason)
                await interaction.response.send_message(
                    _("👐 This ticket has been reopened!"),
                    ephemeral=True,
                )
        except RuntimeError as e:
            await interaction.response.send_message(
                f"⛔ {e}",
                ephemeral=True,
            )


class OwnerCloseConfirmation(discord.ui.View):
    def __init__(self, cog: commands.Cog) -> None:
        super().__init__(timeout=None)
        self.cog: commands.Cog = cog

        self.cancel.label = _("Cancel")
        self.cancel.custom_id = "Tickets_owner_close_cancel"
        self.close.label = _("Close")
        self.close.custom_id = "Tickets_owner_close"

    async def start(
        self,
        ticket,
        interaction: typing.Optional[discord.Interaction] = None,
        reason: typing.Optional[str] = None,
    ) -> discord.Message:
        embed: discord.Embed = discord.Embed(
            title=_("Close Ticket"),
            description=_(
                "If you would like to close this ticket, then just press the `Close` button. If you would like to keep this ticket open to get further assistance, you can click on the `Cancel` button."
            ),
            color=await self.cog.bot.get_embed_color(ticket.channel),
        )
        if reason is not None:
            embed.add_field(
                name=_("Reason:"),
                value=f">>> {reason}",
                inline=False,
            )
        embed.set_footer(
            text=_("Note that if there is no response from you the ticket will be closed.")
        )
        config = await self.cog.config.guild(ticket.guild).profiles.get_raw(ticket.profile)
        try:
            int(config["emojis"]["close"])
        except ValueError:
            e = config["emojis"]["close"]
        else:
            e = (
                str(e)
                if (e := self.cog.bot.get_emoji(int(config["emojis"]["close"]))) is not None
                else None
            )
        self.close.emoji = e
        message = await (
            interaction.response.send_message if interaction is not None else ticket.channel.send
        )(
            _("{owner.mention}, is there anything else we can help you with?").format(
                owner=ticket.owner
            ),
            embed=embed,
            view=self,
        )
        if message is None:
            message = await interaction.original_response()
        self.cog.views[message] = self
        return message

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        ticket = discord.utils.get(
            self.cog.tickets.get(interaction.guild.id, {}).values(), channel=interaction.channel
        )
        if ticket is None:
            await interaction.response.send_message(
                _("⛔ This channel is not in the Config!"),
                ephemeral=True,
            )
            return False
        interaction.data["ticket"] = ticket
        if not await self.cog.is_support.__func__().predicate(interaction):
            await interaction.response.send_message(
                _("⛔ You aren't allowed to interact with this ticket!"),
                ephemeral=True,
            )
            return False
        return True

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        try:
            await interaction.message.delete()
        except discord.HTTPException:
            pass
        await interaction.response.send_message(
            _("👍 This ticket has not been closed!"),
            ephemeral=True,
        )

    @discord.ui.button(label="Close", style=discord.ButtonStyle.danger)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            await interaction.message.delete()
        except discord.HTTPException:
            pass
        ticket = discord.utils.get(
            self.cog.tickets.get(interaction.guild.id, {}).values(), channel=interaction.channel
        )
        try:
            reason = (
                interaction.message.embeds[0].fields[0].value[4:].strip()
                if interaction.message.embeds[0].fields
                else None
            )
            await ticket.close(interaction.user, reason=reason)
            await interaction.followup.send(_("❌ This ticket has been closed!"), ephemeral=True)
        except RuntimeError as e:
            return await interaction.followup.send(
                f"⛔ {e}",
                ephemeral=True,
            )


class ClosedTicketControls(discord.ui.View):
    def __init__(self, cog: commands.Cog) -> None:
        super().__init__(timeout=None)
        self.cog: commands.Cog = cog

        self.transcript.label = _("Transcript")
        self.transcript.custom_id = "Tickets_transcript"
        self.reopen.label = _("Reopen")
        self.reopen.custom_id = "Tickets_reopen"
        self.delete.label = _("Delete")
        self.delete.custom_id = "Tickets_delete"

    async def start(
        self, ticket, interaction: typing.Optional[discord.Interaction] = None
    ) -> discord.Message:
        config = await self.cog.config.guild(ticket.guild).profiles.get_raw(ticket.profile)
        try:
            int(config["emojis"]["transcript"])
        except ValueError:
            e = config["emojis"]["transcript"]
        else:
            e = (
                str(e)
                if (e := self.cog.bot.get_emoji(int(config["emojis"]["transcript"]))) is not None
                else None
            )
        self.transcript.emoji = e
        try:
            int(config["emojis"]["reopen"])
        except ValueError:
            e = config["emojis"]["reopen"]
        else:
            e = (
                str(e)
                if (e := self.cog.bot.get_emoji(int(config["emojis"]["reopen"]))) is not None
                else None
            )
        self.reopen.emoji = e
        try:
            int(config["emojis"]["delete"])
        except ValueError:
            e = config["emojis"]["delete"]
        else:
            e = (
                str(e)
                if (e := self.cog.bot.get_emoji(int(config["emojis"]["delete"]))) is not None
                else None
            )
        self.delete.emoji = e
        message = await (
            interaction.response.send_message if interaction is not None else ticket.channel.send
        )(
            embed=discord.Embed(
                description=box(_("Closed Ticket Controls")),
                color=await self.cog.bot.get_embed_color(ticket.channel),
            ),
            view=self,
        )
        if message is None:
            message = await interaction.original_response()
        self.cog.views[message] = self
        return message

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        ticket = discord.utils.get(
            self.cog.tickets.get(interaction.guild.id, {}).values(), channel=interaction.channel
        )
        if ticket is None:
            await interaction.response.send_message(
                _("⛔ This channel is not in the Config!"),
                ephemeral=True,
            )
            return False
        interaction.data["ticket"] = ticket
        if not await self.cog.is_support.__func__().predicate(interaction):
            await interaction.response.send_message(
                _("⛔ You aren't allowed to interact with this ticket!"),
                ephemeral=True,
            )
            return False
        return True

    @discord.ui.button(label="Transcript", style=discord.ButtonStyle.secondary)
    async def transcript(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await interaction.response.defer(thinking=True)
        ticket = discord.utils.get(
            self.cog.tickets.get(interaction.guild.id, {}).values(), channel=interaction.channel
        )
        transcript = await ticket.export()
        message = await interaction.followup.send(
            _("📜 Here is the transcript of this ticket!"),
            file=transcript,
            ephemeral=True,
            wait=True,
        )
        view: discord.ui.View = discord.ui.View()
        view.add_item(
            discord.ui.Button(
                label=_("View Transcript"),
                style=discord.ButtonStyle.link,
                url=f"https://mahto.id/chat-exporter?url={message.attachments[0].url}",
            )
        )
        await interaction.edit_original_response(view=view)

    @discord.ui.button(label="Reopen", style=discord.ButtonStyle.secondary)
    async def reopen(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)
        ticket = discord.utils.get(
            self.cog.tickets.get(interaction.guild.id, {}).values(), channel=interaction.channel
        )
        try:
            await ticket.reopen(interaction.user)
            await interaction.followup.send(_("👐 This ticket has been reopened!"), ephemeral=True)
        except RuntimeError as e:
            return await interaction.followup.send(
                f"⛔ {e}",
                ephemeral=True,
            )

    @discord.ui.button(label="Delete", style=discord.ButtonStyle.danger)
    async def delete(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        ticket = discord.utils.get(
            self.cog.tickets.get(interaction.guild.id, {}).values(), channel=interaction.channel
        )
        await interaction.response.send_message(
            embed=discord.Embed(
                title=_("🗑️ This ticket will be deleted in a few seconds..."),
                color=discord.Color.red(),
            ),
        )
        await asyncio.sleep(5)
        await ticket.delete_channel(interaction.user)


class CreateTicketView(discord.ui.View):
    def __init__(
        self,
        cog: commands.Cog,
        components: typing.Dict[
            typing.Literal["buttons", "dropdown_options"],
            typing.List[typing.Dict[str, typing.Any]],
        ],
    ) -> None:
        super().__init__(timeout=None)
        self.cog: commands.Cog = cog

        async def callback(
            interaction: discord.Interaction,
            item: typing.Union[discord.ui.Button, discord.ui.Select],
        ) -> None:
            if isinstance(item, discord.ui.Button):
                config_identifier = item.custom_id.split("_")[-1]
                category_label = "{emoji}{label}".format(
                    emoji=f"{item.emoji} " if item.emoji is not None else "",
                    label=item.label if item.label is not None else "",
                )
            else:
                value = item.values[0]
                config_identifier = value
                item = discord.utils.get(item.options, value=value)
                category_label = "{emoji}{label}".format(
                    emoji=f"{item.emoji} " if item.emoji is not None else "",
                    label=item.label if item.label is not None else "",
                )
            buttons_dropdowns = await self.cog.config.guild(interaction.guild).buttons_dropdowns()
            profile = buttons_dropdowns[
                f"{interaction.message.channel.id}-{interaction.message.id}"
            ]["buttons" if isinstance(item, discord.ui.Button) else "dropdown_options"][
                config_identifier
            ][
                "profile"
            ]
            try:
                await self.cog.create_ticket(
                    interaction, profile, interaction.user, category_label=category_label
                )
            except commands.UserFeedbackCheckFailure as e:
                return await interaction.followup.send(
                    f"⛔ {e}",
                    ephemeral=True,
                )

        for config_identifier, button in components["buttons"].items():
            if button["emoji"] is not None:
                try:
                    int(button["emoji"])
                except ValueError:
                    e = button["emoji"]
                else:
                    e = (
                        str(e)
                        if (e := self.cog.bot.get_emoji(int(button["emoji"]))) is not None
                        else None
                    )
            else:
                e = None
            button = discord.ui.Button(
                label=button["label"],
                emoji=e,
                style=discord.ButtonStyle(button["style"]),
                custom_id=f"Tickets_{config_identifier}",
                disabled=False,
            )
            button.callback = functools.partial(callback, item=button)
            self.add_item(button)
        if components["dropdown_options"]:
            dropdown = discord.ui.Select(
                custom_id="Tickets_dropdown",
                disabled=False,
            )
            for config_identifier, option in components["dropdown_options"].items():
                if option["emoji"] is not None:
                    try:
                        int(option["emoji"])
                    except ValueError:
                        e = option["emoji"]
                    else:
                        e = (
                            str(e)
                            if (e := self.cog.bot.get_emoji(int(option["emoji"]))) is not None
                            else None
                        )
                else:
                    e = None
                dropdown.options.append(
                    discord.SelectOption(
                        emoji=e,
                        label=option["label"],
                        description=option["description"],
                        value=config_identifier,
                    )
                )
            dropdown.callback = functools.partial(callback, item=dropdown)
            self.add_item(dropdown)

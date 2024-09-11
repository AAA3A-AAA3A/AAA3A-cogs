from AAA3A_utils import CogsUtils, Menu  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

_: Translator = Translator("CtrlZ", __file__)


class BaseView(discord.ui.View):
    def __init__(self, cog: commands.Cog) -> None:
        super().__init__(timeout=600)
        self.cog: commands.Cog = cog
        self.ctx: commands.Context = None
        self._message: discord.Message = None

        self.audit_logs: typing.List[discord.AuditLogEntry] = []
        self.displayed_actions: typing.List[discord.AuditLogAction] = []
        self.current_audit_log: discord.AuditLogEntry = None

        self.create_actions.placeholder = _("Create Actions")
        self.update_actions.placeholder = _("Update Actions")
        self.delete_actions.placeholder = _("Delete Actions")
        self.revert.label = _("Revert")

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

    async def start(
        self,
        ctx: commands.Context,
        audit_logs: typing.List[discord.AuditLogEntry],
        displayed_actions: typing.List[discord.AuditLogAction] = None,
    ) -> discord.Message:
        self.ctx: commands.Context = ctx
        self.audit_logs: typing.List[discord.AuditLogEntry] = audit_logs
        self.displayed_actions: typing.List[discord.AuditLogAction] = [action for action in displayed_actions or [] if any(audit_log.action == action for audit_log in self.audit_logs)]
        self.displayed_actions = self.displayed_actions or list(
            set(
                [
                    audit_log.action
                    for audit_log in self.audit_logs
                ]
            )
        )
        self.current_audit_log = self.audit_logs[-1]
        await self._update()
        self._message: discord.Message = await ctx.send(
            embed=await self.cog.get_audit_log_embed(self.current_audit_log),
            view=self,
        )
        self.cog.views[self._message] = self
        return self._message

    async def _update(self, page: int = 0) -> None:
        self.clear_items()
        audit_logs_actions = await self.cog.get_audit_logs_actions()
        if (create_actions := [
            discord.SelectOption(label=label, value=action.name, default=action in self.displayed_actions)
            for action, label in audit_logs_actions["create"].items()
            if any(audit_log.action == action for audit_log in self.audit_logs)
        ]):
            self.create_actions.options = create_actions
            self.create_actions.max_values = len(create_actions)
            self.add_item(self.create_actions)
        else:
            self.remove_item(self.create_actions)
        if (update_actions := [
            discord.SelectOption(label=label, value=action.name, default=action in self.displayed_actions)
            for action, label in audit_logs_actions["update"].items()
            if any(audit_log.action == action for audit_log in self.audit_logs)
        ]):
            self.update_actions.options = update_actions
            self.update_actions.max_values = len(update_actions)
            self.add_item(self.update_actions)
        if (delete_actions := [
            discord.SelectOption(label=label, value=action.name, default=action in self.displayed_actions)
            for action, label in audit_logs_actions["delete"].items()
            if any(audit_log.action == action for audit_log in self.audit_logs)
        ]):
            self.delete_actions.options = delete_actions
            self.delete_actions.max_values = len(delete_actions)
            self.add_item(self.delete_actions)
        for button in (self.first, self.previous, self.close, self.next, self.last, self.page):
            self.add_item(button)

        displayed_audit_logs = [audit_log for audit_log in self.audit_logs if audit_log.action in self.displayed_actions]
        try:
            if page == 1:
                self.current_audit_log = displayed_audit_logs[displayed_audit_logs.index(self.current_audit_log) + 1]
            elif page == -1:
                self.current_audit_log = displayed_audit_logs[max(displayed_audit_logs.index(self.current_audit_log) - 1, 0)]
            elif page == -2:
                self.current_audit_log = displayed_audit_logs[0]
            elif page == 2:
                self.current_audit_log = displayed_audit_logs[-1]
            elif self.current_audit_log not in displayed_audit_logs:
                self.current_audit_log = displayed_audit_logs[-1]
        except StopIteration:
            pass

        self.first.disabled = self.previous.disabled = displayed_audit_logs.index(self.current_audit_log) == 0
        self.last.disabled = self.next.disabled = displayed_audit_logs.index(self.current_audit_log) == len(displayed_audit_logs) - 1
        self.page.label = f"Page {displayed_audit_logs.index(self.current_audit_log) + 1}/{len(displayed_audit_logs)}"

    async def change_page(self, page: int = 0) -> None:
        await self._update(page=page)
        try:
            await self._message.edit(
                embed=await self.cog.get_audit_log_embed(self.current_audit_log),
                view=self,
            )
        except discord.HTTPException:
            pass

    @discord.ui.select(placeholder="Create Actions", min_values=0)
    async def create_actions(self, interaction: discord.Interaction, select: discord.ui.Select) -> None:
        await interaction.response.defer()
        _old = self.displayed_actions.copy()
        for value in select.values:
            if (action := discord.AuditLogAction[value]) not in self.displayed_actions:
                self.displayed_actions.append(action)
        for option in select.options:
            if option.value not in select.values:
                try:
                    self.displayed_actions.remove(discord.AuditLogAction[option.value])
                except ValueError:
                    pass
        if not self.displayed_actions:
            self.displayed_actions = _old
        await self.change_page()

    @discord.ui.select(placeholder="Update Actions", min_values=0)
    async def update_actions(self, interaction: discord.Interaction, select: discord.ui.Select) -> None:
        await interaction.response.defer()
        _old = self.displayed_actions.copy()
        for value in select.values:
            if (action := discord.AuditLogAction[value]) not in self.displayed_actions:
                self.displayed_actions.append(action)
        for option in select.options:
            if option.value not in select.values:
                try:
                    self.displayed_actions.remove(discord.AuditLogAction[option.value])
                except ValueError:
                    pass
        if not self.displayed_actions:
            self.displayed_actions = _old
        await self.change_page()

    @discord.ui.select(placeholder="Delete Actions", min_values=0)
    async def delete_actions(self, interaction: discord.Interaction, select: discord.ui.Select) -> None:
        await interaction.response.defer()
        _old = self.displayed_actions.copy()
        for value in select.values:
            if (action := discord.AuditLogAction[value]) not in self.displayed_actions:
                self.displayed_actions.append(action)
        for option in select.options:
            if option.value not in select.values:
                try:
                    self.displayed_actions.remove(discord.AuditLogAction[option.value])
                except ValueError:
                    pass
        if not self.displayed_actions:
            self.displayed_actions = _old
        await self.change_page()

    @discord.ui.button(emoji="⏮️")
    async def first(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer()
        await self.change_page(page=-2)

    @discord.ui.button(emoji="⬅️")
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer()
        await self.change_page(page=-1)

    @discord.ui.button(emoji="✖️", style=discord.ButtonStyle.danger)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer()
        try:
            await self._message.delete()
        except discord.HTTPException:
            pass

    @discord.ui.button(emoji="➡️")
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer()
        await self.change_page(page=1)

    @discord.ui.button(emoji="⏭️")
    async def last(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer()
        await self.change_page(page=2)

    @discord.ui.button(label="Page X/X", style=discord.ButtonStyle.grey, disabled=True)
    async def page(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        pass

    @discord.ui.button(emoji="↩️", label="Revert", style=discord.ButtonStyle.success)
    async def revert(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            await self.cog.revert_audit_log(self.current_audit_log)
        except RuntimeError as e:
            await interaction.followup.send(f"❌ {e}", ephemeral=True)
        else:
            await self.change_page()
            await interaction.followup.send(_("✅ This Audit Log has been reverted successfully."), ephemeral=True)


class CtrlZView(BaseView):
    async def _update(self, page: int = 0) -> None:
        await super()._update(page=page)
        self.add_item(self.revert)
        if self.current_audit_log.id not in await self.cog.config.guild(self.ctx.guild).reverted_audit_logs():
            self.revert.label = _("Revert")
            self.revert.style = discord.ButtonStyle.success
            audit_logs_actions = await self.cog.get_audit_logs_actions()
            async def can_fetch_invite(code: str) -> bool:
                try:
                    await self.cog.bot.fetch_invite(code)
                except discord.NotFound:
                    return False
                return True
            self.revert.disabled = (
                (self.current_audit_log.action in audit_logs_actions["create"] or self.current_audit_log.action in audit_logs_actions["update"])
                and (
                    isinstance(self.current_audit_log.target, discord.Object)
                    or (
                        isinstance(self.current_audit_log.target, discord.Invite)
                        and not await can_fetch_invite(self.current_audit_log.target.code)
                    )
                )
            )
        else:
            self.revert.label = _("Already Reverted")
            self.revert.style = discord.ButtonStyle.danger
            self.revert.disabled = True


class CtrlZMassView(BaseView):
    def __init__(self, cog: commands.Cog) -> None:
        super().__init__(cog=cog)
        self.ignored_audit_logs: typing.List[discord.AuditLogEntry] = []

    async def _update(self, page: int = 0) -> None:
        await super()._update(page=page)
        self.add_item(self.ignore)
        if self.current_audit_log not in self.ignored_audit_logs:
            self.ignore.label = _("Ignore")
            self.ignore.style = discord.ButtonStyle.success
        else:
            self.ignore.label = _("Unignore")
            self.ignore.style = discord.ButtonStyle.danger
        self.add_item(self.revert_all)

    @discord.ui.button(label="Ignore", style=discord.ButtonStyle.success)
    async def ignore(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer()
        if self.current_audit_log not in self.ignored_audit_logs:
            self.ignored_audit_logs.append(self.current_audit_log)
        else:
            self.ignored_audit_logs.remove(self.current_audit_log)
        await self.change_page()

    @discord.ui.button(emoji="↩️", label="Revert All", style=discord.ButtonStyle.red)
    async def revert_all(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer(ephemeral=True)
        await self.on_timeout()
        fake_context = type(
            "FakeContext",
            (),
            {"interaction": interaction, "bot": interaction.client, "guild": interaction.guild, "channel": interaction.channel, "author": interaction.user, "message": interaction.message, "send": interaction.followup.send},
        )()
        if not await CogsUtils.ConfirmationAsk(
            fake_context, _("Are you sure you want to revert all these audit logs?"), ephemeral=True
        ):
            return
        reverted_audit_logs = await self.cog.config.guild(self.ctx.guild).reverted_audit_logs()
        audit_logs = [
            audit_log for audit_log in self.audit_logs
            if (
                audit_log.action in self.displayed_actions
                and audit_log not in self.ignored_audit_logs
                and audit_log.id not in reverted_audit_logs
            )
        ]
        if not audit_logs:
            await interaction.followup.send(_("❌ There are no audit logs to revert."), ephemeral=True)
            return
        embed: discord.Embed = discord.Embed(
            title=_("Reverting Audit Logs..."),
            description=_("This may take a while."),
            color=discord.Color.red(),
        )
        embed.add_field(
            name=_("Progression:"),
            value=f"0/{len(audit_logs)}",
        )
        embed.add_field(
            name=_("Errors:"),
            value=_("No errors yet."),
        )
        progression_message = await self.ctx.send(embed=embed)
        audit_logs_actions = await self.cog.get_audit_logs_actions()
        errors = []
        for i, audit_log in enumerate(reversed(audit_logs), start=1):
            if audit_log.id in reverted_audit_logs:
                continue
            try:
                await self.cog.revert_audit_log(audit_log)
            except RuntimeError as e:
                action = next(
                    (
                        action
                        for action, action_actions in audit_logs_actions.items()
                        if audit_log.action in action_actions
                    ),
                    None,
                )
                errors.append(
                    (
                        f"**•** **{audit_logs_actions[action][audit_log.action]}** — {getattr(audit_log.target, 'mention', getattr(audit_log.target, 'name', repr(audit_log.target)))} ({audit_log.target.id})"
                        if not isinstance(audit_log.target, discord.Object)
                        else f"Unknown ({audit_log.target.id})" + (f" (`{audit_log.target.type.__name__}`)" if audit_log.target.type != discord.Object else "")
                    ) + f" — {e}"
                )
            try:
                embed.set_field_at(
                    0,
                    name=_("Progression:"),
                    value=f"{i}/{len(audit_logs)} ({round(i / len(audit_logs) * 100)}%)",
                )
                if errors:
                    embed.set_field_at(
                        1,
                        name=_("Errors:"),
                        value=f"{len(errors)}/{i}",
                    )
                await progression_message.edit(embed=embed)
            except discord.HTTPException:
                pass
        if errors:
            embeds = [
                discord.Embed(
                    title=_("❌ Errors..."),
                    description="\n\n".join(page),
                    color=discord.Color.red(),
                )
                for page in discord.utils.as_chunks(errors, 5)
            ]
            await Menu(pages=embeds).start(self.ctx, wait=False)
        await self.change_page()
        await self.ctx.send(_("✅ All Audit Logs have been reverted successfully."))
        
        
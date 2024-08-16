from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

from redbot.core.utils.chat_formatting import humanize_list

from .converter import Emoji

_: Translator = Translator("PersonalReact", __file__)


class PersonalReactView(discord.ui.View):
    def __init__(self, cog: commands.Cog) -> None:
        super().__init__(timeout=180)
        self.ctx: commands.Context = None
        self.cog: commands.Cog = cog
        self._message: discord.Message = None

        self.replies.label = _("Replies")
        self.user_id.label = _("User ID")
        self.custom_trigger.label = _("Custom Trigger")
        self.reactions.label = _("Reactions")
        self.ignore_myself.label = _("Ignore Myself")
        self.ignore_bots.label = _("Ignore Bots")

    async def start(self, ctx: commands.Context) -> None:
        self.ctx: commands.Context = ctx
        self._message: discord.Message = await self.ctx.send(
            embed=await self.get_embed(),
            view=self,
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
        data = await self.cog.config.member(self.ctx.author).all()
        if not data["enabled"]:
            self.toggle.label = _("Enable")
            self.toggle.style = discord.ButtonStyle.success
        else:
            self.toggle.label = _("Disable")
            self.toggle.style = discord.ButtonStyle.danger
        self.replies.style = discord.ButtonStyle.success if data["replies"] else discord.ButtonStyle.secondary
        self.user_id.style = discord.ButtonStyle.success if data["user_id"] else discord.ButtonStyle.secondary
        self.ignore_myself.style = discord.ButtonStyle.success if data["ignore_myself"] else discord.ButtonStyle.secondary
        self.ignore_bots.style = discord.ButtonStyle.success if data["ignore_bots"] else discord.ButtonStyle.secondary
        __, base_total_amount, __, base_is_staff, __, base_roles_requirements = await self.cog.get_reactions(
            self.ctx.author, "base"
        )
        __, custom_trigger_total_amount, __, custom_trigger_is_staff, always_allow_custom_trigger, custom_trigger_roles_requirements = await self.cog.get_reactions(
            self.ctx.author, "custom_trigger"
        )

        embed = discord.Embed(
            title=f"{'✅' if data['enabled'] and base_total_amount > 0 else '❌'} " + _("PersonalReact"),
            color=await self.ctx.embed_color(),
        )
        embed.set_author(name=self.ctx.author.display_name, icon_url=self.ctx.author.display_avatar)
        embed.set_thumbnail(url=self.ctx.author.display_avatar)
        embed.set_footer(text=self.ctx.guild.name, icon_url=self.ctx.guild.icon)

        embed.add_field(
            name=_("Base Roles Requirements:"),
            value=(
                (_("**+ ∞** Staff") if base_is_staff else "")
                + ("\n" if base_roles_requirements else "")
                + "\n".join(
                    f"**+ {amount}** — {role.mention}"
                    for role, amount in base_roles_requirements.items()
                )
                + "\n\n" + (_("✅ Elligible") + _(" ({amount} reactions)").format(amount=base_total_amount) if base_total_amount > 0 else _("❌ Not elligible"))
            ),
        )
        embed.add_field(
            name=_("Custom Trigger Roles Requirements:"),
            value=(
                (_("**+ ∞** Staff") if custom_trigger_is_staff else "")
                + (_("\n**+ {base_total_amount}** Always Allow").format(base_total_amount=base_total_amount) if always_allow_custom_trigger and base_total_amount > 0 else "")
                + ("\n" if custom_trigger_roles_requirements else "")
                + "\n".join(
                    f"**+ {amount}** — {role.mention}"
                    for role, amount in custom_trigger_roles_requirements.items()
                )
                + "\n\n" + (_("✅ Elligible") + _(" ({amount} reactions)").format(amount=custom_trigger_total_amount) if custom_trigger_total_amount > 0 else _("❌ Not elligible"))
            ),
        )

        embed.add_field(
            name=_("Triggers:"),
            value=(
                _("**•** Your mention")
                + (_("\n**•** Replies (with @)") if data["replies"] else "")
                + (_("\n**•** Your User ID") if data["user_id"] else "")
                + (_("\n**•** {emoji}Custom Trigger").format(emoji="❌ " if custom_trigger_total_amount == 0 else "") if data["custom_trigger"] is not None else "")
            ),
            inline=False,
        )
        embed.add_field(
            name=_("Custom Trigger:"),
            value=f"`{data['custom_trigger']}`" if data["custom_trigger"] is not None else _("Not set."),
        )

        embed.add_field(
            name=_("Reactions:"),
            value=humanize_list(
                [
                    reaction
                    for r in data["reactions"]
                    if (
                        reaction := (r if isinstance(r, str) else self.ctx.bot.get_emoji(r))
                    ) is not None
                ]
            ) or _("No reactions set."),
            inline=False,
        )

        embed.add_field(
            name=_("Ignore Myself:"),
            value="✅" if data["ignore_myself"] else "❌",
        )
        embed.add_field(
            name=_("Ignore Bots:"),
            value="✅" if data["ignore_bots"] else "❌",
        )

        return embed

    @discord.ui.button(label="Toggle")
    async def toggle(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        enabled = await self.cog.config.member(self.ctx.author).enabled()
        enabled = not enabled
        if enabled:
            if (await self.cog.get_reactions(self.ctx.author, "base"))[1] == 0 and (await self.cog.get_reactions(self.ctx.author, "custom_trigger"))[1] == 0:
                await interaction.response.send_message(
                    _("You aren't elligible for using PersonalReact."),
                    ephemeral=True,
                )
                return
            if not await self.cog.config.member(self.ctx.author).reactions():
                await interaction.response.send_message(
                    _("You don't have any reaction set."),
                    ephemeral=True,
                )
                return
        await self.cog.config.member(self.ctx.author).enabled.set(enabled)
        await interaction.response.edit_message(embed=await self.get_embed(), view=self)

    @discord.ui.button(label="Replies")
    async def replies(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        replies = await self.cog.config.member(self.ctx.author).replies()
        replies = not replies
        await self.cog.config.member(self.ctx.author).replies.set(replies)
        await interaction.response.edit_message(embed=await self.get_embed(), view=self)

    @discord.ui.button(label="User ID")
    async def user_id(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        user_id = await self.cog.config.member(self.ctx.author).user_id()
        user_id = not user_id
        await self.cog.config.member(self.ctx.author).user_id.set(user_id)
        await interaction.response.edit_message(embed=await self.get_embed(), view=self)

    @discord.ui.button(label="Custom Trigger", row=1)
    async def custom_trigger(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if (await self.cog.get_reactions(self.ctx.author, "custom_trigger"))[1] == 0:
            await interaction.response.send_message(
                _("You aren't elligible for using the custom trigger feature."),
                ephemeral=True,
            )
            return
        await interaction.response.send_modal(
            CustomTriggerModal(
                self.cog,
                self.ctx,
                self,
                default_custom_trigger=await self.cog.config.member(self.ctx.author).custom_trigger(),
                min_custom_trigger_length=await self.cog.config.guild(self.ctx.guild).min_custom_trigger_length(),
            )
        )

    @discord.ui.button(label="Reactions", row=1)
    async def reactions(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        view: ReactionsView = ReactionsView(self.cog, self.ctx, self)
        await view._update()
        await interaction.response.send_message(
            view=view,
            ephemeral=True,
        )
        view._message = await interaction.original_response()
        self.cog.views[view._message] = view

    @discord.ui.button(label="Ignore Myself", row=2)
    async def ignore_myself(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        ignore_myself = await self.cog.config.member(self.ctx.author).ignore_myself()
        ignore_myself = not ignore_myself
        await self.cog.config.member(self.ctx.author).ignore_myself.set(ignore_myself)
        await interaction.response.edit_message(embed=await self.get_embed(), view=self)

    @discord.ui.button(label="Ignore Bots", row=2)
    async def ignore_bots(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        ignore_bots = await self.cog.config.member(self.ctx.author).ignore_bots()
        ignore_bots = not ignore_bots
        await self.cog.config.member(self.ctx.author).ignore_bots.set(ignore_bots)
        await interaction.response.edit_message(embed=await self.get_embed(), view=self)

    @discord.ui.button(emoji="✖️", style=discord.ButtonStyle.danger)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer()
        try:
            await self._message.delete()
        except discord.HTTPException:
            pass


class CustomTriggerModal(discord.ui.Modal):
    def __init__(
        self,
        cog: commands.Cog,
        ctx: commands.Context,
        parent_view: discord.ui.View,
        *,
        default_custom_trigger: typing.Optional[str] = None,
        min_custom_trigger_length: int = 3,
    ) -> None:
        self.ctx: commands.Context = ctx
        self.cog: commands.Cog = cog
        self.parent_view: discord.ui.View = parent_view

        super().__init__(title=_("Custom Trigger"))
        self.custom_trigger: discord.ui.TextInput = discord.ui.TextInput(
            label=_("Custom Trigger"),
            placeholder=_("Type your custom trigger..."),
            default=default_custom_trigger,
            min_length=min_custom_trigger_length,
            max_length=100,
            required=False,
        )
        self.add_item(self.custom_trigger)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        custom_trigger = self.custom_trigger.value
        if custom_trigger:
            if " " in custom_trigger:
                await interaction.response.send_message(_("The custom trigger can't have spaces."), ephemeral=True)
                return
            await self.cog.config.member(self.ctx.author).custom_trigger.set(custom_trigger)
        else:
            await interaction.response.defer()
            await self.cog.config.member(self.ctx.author).custom_trigger.clear()
        try:
            await self.parent_view._message.edit(embed=await self.parent_view.get_embed())
        except discord.HTTPException:
            pass


class AddReactionsModal(discord.ui.Modal):
    def __init__(self, cog: commands.Cog, ctx: commands.Context, parent_view: discord.ui.View, view: discord.ui.View) -> None:
        self.ctx: commands.Context = ctx
        self.cog: commands.Cog = cog
        self.parent_view: discord.ui.View = parent_view
        self.view: discord.ui.View = view

        super().__init__(title=_("Add Reaction(s)"))
        self.reactions: discord.ui.TextInput = discord.ui.TextInput(
            label=_("Reaction(s)"),
            placeholder=_("Type the reaction(s)..."),
            min_length=1,
            max_length=50,
            required=True,
        )
        self.add_item(self.reactions)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        reactions = []
        try:
            for r in self.reactions.value.split(" "):
                reaction = await Emoji().convert(self.ctx, r)
                reactions.append(getattr(reaction, "id", reaction))
        except commands.BadArgument as e:
            await interaction.response.send_message(str(e), ephemeral=True)
        _reactions = await self.cog.config.member(self.ctx.author).reactions()
        _reactions.extend(reactions)
        if len(_reactions) > (max_reactions_per_member := (await self.cog.config.guild(self.ctx.guild).max_reactions_per_member())):
            await interaction.response.send_message(
                _("You can't have more than {max_reactions_per_member} reactions.").format(max_reactions_per_member=max_reactions_per_member),
                ephemeral=True,
            )
            return
        await self.cog.config.member(self.ctx.author).reactions.set(_reactions)
        try:
            await self.parent_view._message.edit(embed=await self.parent_view.get_embed())
        except discord.HTTPException:
            pass
        await self.view._update()
        try:
            await self.view._message.edit(view=self.view)
        except discord.HTTPException:
            pass
        await interaction.response.send_message(
            _("Reaction added successfully."),
            ephemeral=True,
        )


class ReactionsView(discord.ui.View):
    def __init__(self, cog: commands.Cog, ctx: commands.Context, parent_view: discord.ui.View) -> None:
        super().__init__(timeout=60)
        self.ctx: commands.Context = ctx
        self.cog: commands.Cog = cog
        self.parent_view: discord.ui.View = parent_view
        self._message: discord.Message = None

        self.add.label = _("Add Reaction(s)")
        self.remove.placeholder = _("Select reaction(s) to remove...")

    async def _update(self) -> None:
        reactions = await self.cog.config.member(self.ctx.author).reactions()
        self.clear_items()
        self.add_item(self.add)
        if len(reactions) == 25:
            self.add.disabled = True
        if reactions:
            self.remove.options = []
            for r in reactions:
                reaction = r if isinstance(r, str) else self.ctx.bot.get_emoji(r)
                self.remove.options.append(
                    discord.SelectOption(
                        emoji=reaction if reaction is not None else None,
                        label=getattr(reaction, "name", "\u200b") if reaction is not None else r,
                        value=r,
                    )
                )
            self.add_item(self.remove)

    async def on_timeout(self) -> None:
        if self._message is not None:
            try:
                await self._message.delete()
            except discord.HTTPException:
                pass

    @discord.ui.button(label="Add Reaction(s)")
    async def add(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.send_modal(
            AddReactionsModal(self.cog, self.ctx, self.parent_view, self),
        )

    @discord.ui.select(min_values=1, placeholder="Select reaction(s) to remove...")
    async def remove(self, interaction: discord.Interaction, select: discord.ui.Select) -> None:
        reactions = await self.cog.config.member(self.ctx.author).reactions()
        for reaction in select.values:
            reactions.remove(reaction)
        await self.cog.config.member(self.ctx.author).reactions.set(reactions)
        await interaction.response.send_message(
            _("Reactions removed successfully."),
            ephemeral=True,
        )
        try:
            await self.parent_view._message.edit(embed=await self.parent_view.get_embed())
        except discord.HTTPException:
            pass


class SettingsView(discord.ui.View):
    def __init__(self, cog: commands.Cog) -> None:
        super().__init__(timeout=180)
        self.ctx: commands.Context = None
        self.cog: commands.Cog = cog
        self._message: discord.Message = None

        self.base_roles.label = _("Base Roles")
        self.custom_trigger_roles.label = _("Custom Trigger Roles")

    async def start(self, ctx: commands.Context) -> None:
        self.ctx: commands.Context = ctx
        self._message: discord.Message = await ctx.send(
            embed=await self.get_embed(),
            view=self,
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
        base_roles_requirements = await self.cog.config.guild(self.ctx.guild).base_roles_requirements()
        custom_trigger_roles_requirements = await self.cog.config.guild(self.ctx.guild).custom_trigger_roles_requirements()
        embed = discord.Embed(
            title=_("PersonalReact - Roles Requirements"),
            color=await self.ctx.embed_color(),
        )
        embed.set_footer(text=self.ctx.guild.name, icon_url=self.ctx.guild.icon)
        embed.add_field(
            name=_("Base:"),
            value="\n".join(
                f"**•** **+ {amount}** — {role.mention}"
                for role_id, amount in base_roles_requirements.items()
                if (role := self.ctx.guild.get_role(int(role_id)))
            )
            or _("No base roles requirements."),
        )
        embed.add_field(
            name=_("Custom Trigger:"),
            value="\n".join(
                f"**•** **+ {amount}** — {role.mention}"
                for role_id, amount in custom_trigger_roles_requirements.items()
                if (role := self.ctx.guild.get_role(int(role_id)))
            )
            or _("No custom trigger roles requirements."),
            inline=False,
        )
        return embed

    @discord.ui.button(label="Base Roles")
    async def base_roles(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        view: RolesView = RolesView(self.cog, self.ctx, self, "base")
        await view._update()
        await interaction.response.send_message(
            embed=discord.Embed(
                title=_("Custom Trigger Roles"),
                color=await self.ctx.embed_color(),
            ),
            view=view,
            ephemeral=True,
        )
        view._message = await interaction.original_response()
        self.cog.views[view._message] = view

    @discord.ui.button(label="Custom Trigger Roles")
    async def custom_trigger_roles(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        view: RolesView = RolesView(self.cog, self.ctx, self, "custom_trigger")
        await view._update()
        await interaction.response.send_message(
            embed=discord.Embed(
                title=_("Custom Trigger Roles"),
                color=await self.ctx.embed_color(),
            ),
            view=view,
            ephemeral=True,
        )
        view._message = await interaction.original_response()
        self.cog.views[view._message] = view

    @discord.ui.button(emoji="✖️", style=discord.ButtonStyle.danger)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer()
        try:
            await self._message.delete()
        except discord.HTTPException:
            pass


class RolesView(discord.ui.View):
    def __init__(self, cog: commands.Cog, ctx: commands.Context, settings_view: SettingsView, _type: typing.Literal["base", "custom_trigger"]) -> None:
        super().__init__(timeout=60)
        self.ctx: commands.Context = ctx
        self.cog: commands.Cog = cog
        self.settings_view: SettingsView = settings_view
        self._type: typing.Literal["base", "custom_trigger"] = _type

        self.amount.placeholder = _("Select the allowed amount...")
        self.add.placeholder = _("Select role(s) to add...")
        self.remove.placeholder = _("Select role(s) to remove...")

    async def _update(self) -> None:
        if not self.amount.options:
            self.amount.options = [
                discord.SelectOption(
                    label=str(i),
                    value=str(i),
                    default=i == 1,
                )
                for i in range(1, await self.cog.config.guild(self.ctx.guild).max_reactions_per_member() + 1)
            ]
        roles_requirements = (
            await self.cog.config.guild(self.ctx.guild).base_roles_requirements()
            if self._type == "base"
            else await self.cog.config.guild(self.ctx.guild).custom_trigger_roles_requirements()
        )
        self.clear_items()
        self.add_item(self.amount)
        self.add_item(self.add)
        if len(roles_requirements) == 25:
            self.amount.disabled = True
            self.add.disabled = True
        if roles_requirements:
            self.remove.options = [
                discord.SelectOption(
                    label=role.name,
                    value=str(role.id),
                )
                for role_id in roles_requirements
                if (role := self.ctx.guild.get_role(int(role_id)))
            ]
            self.add_item(self.remove)

    async def on_timeout(self) -> None:
        if self._message is not None:
            try:
                await self._message.delete()
            except discord.HTTPException:
                pass

    @discord.ui.select(min_values=1, placeholder="Select the allowed amount...")
    async def amount(self, interaction: discord.Interaction, select: discord.ui.Select) -> None:
        await interaction.response.defer()

    @discord.ui.select(cls=discord.ui.RoleSelect, min_values=1, placeholder="Select role(s) to add...")
    async def add(self, interaction: discord.Interaction, select: discord.ui.Select) -> None:
        roles_requirements = (
            await self.cog.config.guild(self.ctx.guild).base_roles_requirements()
            if self._type == "base"
            else await self.cog.config.guild(self.ctx.guild).custom_trigger_roles_requirements()
        )
        for role in select.values:
            roles_requirements[role.id] = int((self.amount.values or [1])[0])
        if len(roles_requirements) == 25:
            raise commands.UserFeedbackCheckFailure(_("You can't have more than 25 {_type} roles requirements.").format(_type=self._type))
        if self._type == "base":
            await self.cog.config.guild(self.ctx.guild).base_roles_requirements.set(roles_requirements)
        else:
            await self.cog.config.guild(self.ctx.guild).custom_trigger_roles_requirements.set(roles_requirements)
        try:
            await self.settings_view._message.edit(embed=await self.settings_view.get_embed())
        except discord.HTTPException:
            pass
        await self._update()
        try:
            await self._message.edit(view=self)
        except discord.HTTPException:
            pass
        await interaction.response.send_message(
            _("Roles requirements added successfully."),
            ephemeral=True,
        )

    @discord.ui.select(min_values=1, placeholder="Select role(s) to remove...")
    async def remove(self, interaction: discord.Interaction, select: discord.ui.Select) -> None:
        roles_requirements = (
            await self.cog.config.guild(self.ctx.guild).base_roles_requirements()
            if self._type == "base"
            else await self.cog.config.guild(self.ctx.guild).custom_trigger_roles_requirements()
        )
        for role_id in select.values:
            roles_requirements.pop(int(role_id), None)
        await interaction.response.send_message(repr(roles_requirements))
        if self._type == "base":
            await self.cog.config.guild(self.ctx.guild).base_roles_requirements.set(roles_requirements)
        else:
            await self.cog.config.guild(self.ctx.guild).custom_trigger_roles_requirements.set(roles_requirements)
        try:
            await self.settings_view._message.edit(embed=await self.settings_view.get_embed())
        except discord.HTTPException:
            pass
        await self._update()
        try:
            await self._message.edit(view=self)
        except discord.HTTPException:
            pass
        await interaction.response.send_message(
            _("Roles requirements removed successfully."),
            ephemeral=True,
        )

from AAA3A_utils import Cog, CogsUtils, Menu  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
from redbot.core.bot import Red  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import asyncio
import json

from redbot.core.utils.chat_formatting import box, humanize_list, pagify


def _(untranslated: str) -> str:  # `redgettext` will found these strings.
    return untranslated


ERROR_MESSAGE = _(
    "I attempted to do something that Discord denied me permissions for. Your command failed to successfully complete.\n{error}"
)

_ = Translator("DiscordEdit", __file__)


class AutoModRuleConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> discord.AutoModRule:
        try:
            rule_id = int(argument)
        except ValueError:
            raise commands.BadArgument(_("Invalid rule ID."))
        try:
            rule = await ctx.guild.fetch_automod_rule(rule_id)
        except discord.NotFound:
            raise commands.BadArgument(_("Rule not found."))
        return rule


class AutoModTriggerConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> discord.AutoModTrigger:
        try:
            data = json.loads(argument)
        except json.JSONDecodeError:
            raise commands.BadArgument(_("Invalid JSON."))
        if (
            not isinstance(data, typing.Dict)
            or "trigger_type" not in data
            or "trigger_metadata" not in data
        ):
            raise commands.BadArgument(
                _("Invalid data. Must be a dict with `trigger_type` and `trigger_metadara` keys.")
            )
        try:
            trigger_type = int(data["trigger_type"])
        except ValueError:
            raise commands.BadArgument(_("Invalid trigger type."))
        try:
            automod_trigger = discord.AutoModTrigger.from_data(
                type=trigger_type, data=data["trigger_metadata"]
            )
        except (TypeError, ValueError, KeyError):
            raise commands.BadArgument(_("Invalid trigger metadata."))
        return automod_trigger


class AutoModRuleActionsConverter(commands.Converter):
    async def convert(
        self, ctx: commands.Context, argument: str
    ) -> typing.List[discord.AutoModAction]:
        try:
            data = json.loads(argument)
        except json.JSONDecodeError:
            raise commands.BadArgument(_("Invalid JSON."))
        if not isinstance(data, typing.List):
            raise commands.BadArgument(
                _("Invalid data. Must be a list of dicts with `type` and `data` keys.")
            )
        actions = []
        for action_dict in data:
            if (
                not isinstance(action_dict, typing.Dict)
                or "type" not in action_dict
                or "data" not in action_dict
            ):
                raise commands.BadArgument(
                    _("Invalid data. Must be a list of dicts with `type` and `data` keys.")
                )
            try:
                action_type = int(action_dict["type"])
            except ValueError:
                raise commands.BadArgument(_("Invalid action type."))
            try:
                discord.AutoModAction
                automod_action = discord.AutoModRuleAction.from_data(
                    type=action_type, data=action_dict["data"]
                )
            except (TypeError, ValueError, KeyError):
                raise commands.BadArgument(_("Invalid action metadata."))
            actions.append(automod_action)
        return actions


@cog_i18n(_)
class EditAutoMod(Cog):
    """A cog to edit AutoMod rules!"""

    def __init__(self, bot: Red) -> None:  # Never executed except manually.
        super().__init__(bot=bot)

    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    @commands.bot_has_permissions(manage_guild=True)
    @commands.hybrid_group()
    async def editautomod(self, ctx: commands.Context) -> None:
        """Commands for edit an AutoMod rule."""
        pass

    @editautomod.command(name="create", aliases=["new", "+"])
    async def editautomod_create(
        self,
        ctx: commands.Context,
        name: str,
        trigger: AutoModTriggerConverter,
        *,
        actions: AutoModRuleActionsConverter,
    ) -> None:
        """Create an AutoMod rule.

        event_type:
        - message_send = 1

        `trigger` and `actions` arguments must be JSON with specified keys. Warning, remove all spaces in the trigger dict.
        trigger:
        - `trigger_type`: https://discord.com/developers/docs/resources/auto-moderation#auto-moderation-rule-object-trigger-types
        - `trigger_metadata`: https://discord.com/developers/docs/resources/auto-moderation#auto-moderation-rule-object-trigger-metadata
        actions:
        - `action_type`: https://discord.com/developers/docs/resources/auto-moderation#auto-moderation-rule-object-action-types
        - `action_metadata`: https://discord.com/developers/docs/resources/auto-moderation#auto-moderation-rule-object-action-metadata
        """
        # One only `event_type` is possible.
        # event_type: discord.AutoModRuleEventType,
        # if event_type is None:
        #     event_type = discord.AutoModRuleEventType.message_send
        event_type = discord.AutoModRuleEventType.message_send
        try:
            rule = await ctx.guild.create_automod_rule(
                name=name, event_type=event_type, trigger=trigger, actions=actions
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )
        await ctx.send(_("AutoMod rule {rule.name} ({rule.id}) created.").format(rule=rule))

    @commands.bot_has_permissions(embed_links=True)
    @editautomod.command(name="list")
    async def editautomod_list(
        self,
        ctx: commands.Context,
    ) -> None:
        """List all AutoMod rules in the current guild."""
        description = "".join(
            f"\n**•** **{rule.name} ({rule.id})**: {rule.trigger.type}"
            for rule in await ctx.guild.fetch_automod_rules()
        )
        embed: discord.Embed = discord.Embed(color=await ctx.embed_color())
        embed.title = _("List of AutoMod rules in {guild.name} ({guild.id})").format(
            guild=ctx.guild
        )
        embeds = []
        pages = pagify(description, page_length=4096)
        for page in pages:
            e = embed.copy()
            e.description = page
            embeds.append(e)
        await Menu(pages=embeds).start(ctx)

    @editautomod.command(name="name")
    async def editautomod_name(
        self, ctx: commands.Context, rule: AutoModRuleConverter, *, name: str
    ) -> None:
        """Edit AutoMod rule name."""
        try:
            await rule.edit(
                name=name,
                reason=f"{ctx.author} ({ctx.author.id}) has edited the rule {rule.name} ({rule.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    # @editautomod.command(name="eventtype")
    # async def editautomod_event_type(self, ctx: commands.Context, rule: AutoModRuleConverter, event_type: discord.AutoModRuleEventType) -> None:
    #     """Edit AutoMod rule event type.

    #     event_type:
    #     - message_send = 1
    #     """
    #     try:
    #         await rule.edit(
    #             event_type=event_type,
    #             reason=f"{ctx.author} ({ctx.author.id}) has edited the rule {rule.name} ({rule.id}).",
    #         )
    #     except discord.HTTPException as e:
    #         raise commands.UserFeedbackCheckFailure(
    #             _(ERROR_MESSAGE).format(error=box(e, lang="py"))
    #         )

    @editautomod.command(name="trigger")
    async def editautomod_trigger(
        self,
        ctx: commands.Context,
        rule: AutoModRuleConverter,
        *,
        trigger: AutoModTriggerConverter,
    ) -> None:
        """Edit AutoMod rule trigger.

        trigger:
        - `trigger_type`: https://discord.com/developers/docs/resources/auto-moderation#auto-moderation-rule-object-trigger-types
        - `trigger_metadata`: https://discord.com/developers/docs/resources/auto-moderation#auto-moderation-rule-object-trigger-metadata
        """
        try:
            await rule.edit(
                trigger=trigger,
                reason=f"{ctx.author} ({ctx.author.id}) has edited the rule {rule.name} ({rule.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @editautomod.command(name="actions")
    async def editautomod_actions(
        self,
        ctx: commands.Context,
        rule: AutoModRuleConverter,
        *,
        actions: AutoModRuleActionsConverter,
    ) -> None:
        """Edit AutoMod rule actions.

        actions:
        - `action_type`: https://discord.com/developers/docs/resources/auto-moderation#auto-moderation-rule-object-action-types
        - `action_metadata`: https://discord.com/developers/docs/resources/auto-moderation#auto-moderation-rule-object-action-metadata
        """
        try:
            await rule.edit(
                actions=actions,
                reason=f"{ctx.author} ({ctx.author.id}) has edited the rule {rule.name} ({rule.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @editautomod.command(name="enabled")
    async def editautomod_enabled(
        self, ctx: commands.Context, rule: AutoModRuleConverter, enabled: bool
    ) -> None:
        """Edit AutoMod rule enabled."""
        try:
            await rule.edit(
                enabled=enabled,
                reason=f"{ctx.author} ({ctx.author.id}) has edited the rule {rule.name} ({rule.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @editautomod.command(name="exemptroles", aliases=["exempt_roles"])
    async def editautomod_exempt_roles(
        self,
        ctx: commands.Context,
        rule: AutoModRuleConverter,
        *,
        exempt_roles: commands.Greedy[discord.Role],
    ) -> None:
        """Edit AutoMod rule exempt roles."""
        try:
            await rule.edit(
                exempt_roles=exempt_roles,
                reason=f"{ctx.author} ({ctx.author.id}) has edited the rule {rule.name} ({rule.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @editautomod.command(name="exemptchannels", aliases=["exempt_channels"])
    async def editautomod_exempt_channels(
        self,
        ctx: commands.Context,
        rule: AutoModRuleConverter,
        *,
        exempt_channels: commands.Greedy[
            typing.Union[
                discord.TextChannel, discord.VoiceChannel, discord.Thread, discord.ForumChannel
            ]
        ],
    ) -> None:
        """Edit AutoMod rule exempt channels."""
        try:
            await rule.edit(
                exempt_channels=exempt_channels,
                reason=f"{ctx.author} ({ctx.author.id}) has edited the rule {rule.name} ({rule.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @editautomod.command(name="delete", aliases=["-"])
    async def editautomod_delete(
        self,
        ctx: commands.Context,
        rule: AutoModRuleConverter,
        confirmation: bool = False,
    ) -> None:
        """Delete automod rule."""
        if not confirmation and not ctx.assume_yes:
            if ctx.bot_permissions.embed_links:
                embed: discord.Embed = discord.Embed()
                embed.title = _("⚠️ - Delete AutoMod rule")
                embed.description = _(
                    "Do you really want to delete the AutoMod rule {rule.name} ({rule.id}) in {guild.name} ({guild.id})?"
                ).format(rule=rule, guild=ctx.guild)
                embed.color = 0xF00020
                content = ctx.author.mention
            else:
                embed = None
                content = f"{ctx.author.mention} " + _(
                    "Do you really want to delete the AutoMod rule {rule.name} ({rule.id}) in {guild.name} ({guild.id})?"
                ).format(rule=rule, guild=ctx.guild)
            if not await CogsUtils.ConfirmationAsk(ctx, content=content, embed=embed):
                await CogsUtils.delete_message(ctx.message)
                return
        try:
            await rule.delete(
                reason=f"{ctx.author} ({ctx.author.id}) has deleted the AutoMod rule {rule.name} ({rule.id})."
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @editautomod.command(name="view")
    async def editautomod_view(
        self,
        ctx: commands.Context,
        rule: AutoModRuleConverter = None,
    ) -> None:
        await EditAutoModRuleView(
            cog=self, rules=await ctx.guild.fetch_automod_rules(), rule=rule
        ).start(ctx)


class AutoModRulesSelect(discord.ui.Select):
    def __init__(
        self,
        parent: discord.ui.View,
        rules: typing.List[discord.AutoModRule],
        current_rule: typing.Optional[discord.AutoModRule] = None,
    ) -> None:
        self._parent: discord.ui.View = parent
        self._options = [
            discord.SelectOption(
                label=f"{rule.name} ({rule.id})", value=str(rule.id), default=rule == current_rule
            )
            for rule in rules[:25]
        ]
        super().__init__(
            placeholder="Select an AutoMod rule.",
            options=self._options,
            row=2,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        option = discord.utils.get(self._options, value=self.values[0])
        await self._parent._callback(interaction, option)


class ChannelsRolesSelectView(discord.ui.View):
    def __init__(self, parent: discord.ui.View, rule: discord.AutoModRule) -> None:
        super().__init__(timeout=180)
        self._parent: discord.ui.View = parent
        self.rule: discord.AutoModRule = rule

    @discord.ui.select(
        cls=discord.ui.ChannelSelect,
        min_values=0,
        max_values=25,
        placeholder="Select channels to replace existing ones.",
    )
    async def channels_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        exempt_channels = select.values
        try:
            self._parent.rule = self.rule = await self.rule.edit(
                exempt_channels=exempt_channels,
                reason=f"{self._parent.ctx.author} ({self._parent.ctx.author.id}) has edited the rule {self.rule.name} ({self.rule.id}).",
            )
        except discord.HTTPException as e:
            await interaction.response.send_message(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )
            return
        await interaction.response.send_message(
            _("Rule `{rule.name} ({rule.id})` edited.").format(rule=self.rule), ephemeral=True
        )
        await self._parent._update()

    @discord.ui.select(
        cls=discord.ui.RoleSelect,
        min_values=0,
        max_values=25,
        placeholder="Select roles to replace existing ones.",
    )
    async def roles_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        exempt_roles = select.values
        try:
            self._parent.rule = self.rule = await self.rule.edit(
                exempt_roles=exempt_roles,
                reason=f"{self._parent.ctx.author} ({self._parent.ctx.author.id}) has edited the rule {self.rule.name} ({self.rule.id}).",
            )
        except discord.HTTPException as e:
            await interaction.response.send_message(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )
            return
        await interaction.response.send_message(
            _("Rule `{rule.name} ({rule.id})` edited.").format(rule=self.rule), ephemeral=True
        )
        await self._parent._update()


class EditAutoModRuleView(discord.ui.View):
    def __init__(
        self,
        cog: commands.Cog,
        rules: typing.List[discord.AutoModRule],
        rule: typing.Optional[discord.AutoModRule] = None,
    ) -> None:
        super().__init__(timeout=180)
        self.cog: commands.Cog = cog
        self.ctx: commands.Context = None

        self.rules: typing.List[discord.AutoModRule] = rules
        self.rule: typing.Optional[discord.AutoModRule] = rule

        self._message: discord.Message = None
        self._embed: discord.Embed = None

        self._deleted: bool = False
        self._rules_select: AutoModRulesSelect = None
        self._ready: asyncio.Event = asyncio.Event()

    async def start(self, ctx: commands.Context) -> None:
        self.ctx: commands.Context = ctx
        await self._update()
        await self._ready.wait()
        return self._message

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id not in [self.ctx.author.id] + list(self.ctx.bot.owner_ids):
            await interaction.response.send_message(
                "You are not allowed to use this interaction.", ephemeral=True
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
        self._ready.set()

    async def _update(self) -> None:
        self._embed: discord.Embed = await self.get_embed(self.ctx, rule=self.rule)
        if self.rule is None:
            self.edit_rule.disabled = True
            self.edit_exempt_channels_roles.disabled = True
            self.delete_rule.disabled = True
            self.enable_or_disable_rule.disabled = True
            self.enable_or_disable_rule.label = "Enable/Disable"
            self.enable_or_disable_rule.style = discord.ButtonStyle.secondary
        else:
            self.edit_rule.disabled = False
            self.edit_exempt_channels_roles.disabled = False
            self.delete_rule.disabled = False
            if self.rule.enabled:
                self.enable_or_disable_rule.label = "Disable"
                self.enable_or_disable_rule.style = discord.ButtonStyle.danger
            else:
                self.enable_or_disable_rule.label = "Enable"
                self.enable_or_disable_rule.style = discord.ButtonStyle.success
            self.enable_or_disable_rule.disabled = False
        if self.rules:
            if self._rules_select is not None:
                self.remove_item(self._rules_select)
            self._rules_select: AutoModRulesSelect = AutoModRulesSelect(
                parent=self, rules=self.rules, current_rule=self.rule
            )
            self.add_item(self._rules_select)
        elif self._rules_select is not None:
            self.remove_item(self._rules_select)
            self._rules_select = None
        if self._message is None:
            self._message: discord.Message = await self.ctx.send(embed=self._embed, view=self)
            self.cog.views[self._message] = self
        else:
            self._message: discord.Message = await self._message.edit(embed=self._embed, view=self)

    async def get_embed(
        self, ctx: commands.Context, rule: typing.Optional[discord.AutoModRule] = None
    ) -> typing.List[discord.Embed]:
        embed: discord.Embed = discord.Embed(color=await ctx.embed_color())
        if rule is None:
            embed.title = "Rule not provided."
            embed.description = None
        else:
            rule.exempt_channels
            embed.title = (
                f"[DELETED] {rule.name} ({rule.id})"
                if self._deleted
                else f"{rule.name} ({rule.id})"
            )
            embed.set_author(
                name=f"{rule.creator} ({rule.creator.id})", icon_url=rule.creator.display_avatar
            )
            embed.add_field(name="Enabled State:", value=str(rule.enabled), inline=True)
            embed.add_field(name="Trigger:", value=repr(rule.trigger), inline=True)
            embed.add_field(
                name="Actions:",
                value="\n".join(
                    [
                        (
                            f"**• {action.type}: **"
                            + (
                                f" - Channel ID {action.channel_id}"
                                if action.channel_id is not None
                                else ""
                            )
                            + (
                                f" - Duration {action.duration}"
                                if action.duration is not None
                                else ""
                            )
                            + (
                                f' - Custom message "{action.custom_message}"'
                                if action.custom_message is not None
                                else ""
                            )
                        )
                        for action in rule.actions
                    ]
                )
                if rule.actions
                else "None.",
                inline=False,
            )
            embed.add_field(
                name="Exempt Channels:",
                value=humanize_list(
                    [f"{channel.mention} ({channel.id})" for channel in rule.exempt_channels]
                )
                if rule.exempt_channels
                else "None.",
                inline=True,
            )
            embed.add_field(
                name="Exempt Roles:",
                value=humanize_list([f"{role.mention} ({role.id})" for role in rule.exempt_roles])
                if rule.exempt_roles
                else "None.",
                inline=True,
            )
        return embed

    async def _callback(
        self, interaction: discord.Interaction, option: discord.SelectOption
    ) -> None:
        await interaction.response.defer()
        self.rule: discord.AutoModRule = discord.utils.get(self.rules, id=int(option.value))
        self._deleted: bool = False
        await self._update()

    @discord.ui.button(style=discord.ButtonStyle.danger, emoji="✖️", custom_id="close_page")
    async def close_page(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        try:
            await interaction.response.defer()
        except discord.errors.NotFound:
            pass
        self.stop()
        await CogsUtils.delete_message(self._message)
        self._ready.set()

    @discord.ui.button(label="Create new AutoMod Rule", style=discord.ButtonStyle.success)
    async def create_rule(self, interaction: discord.Interaction, button: discord.Button) -> None:
        modal = CreateAutoModRuleModal(self)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Edit AutoMod Rule", style=discord.ButtonStyle.primary)
    async def edit_rule(self, interaction: discord.Interaction, button: discord.Button) -> None:
        modal = EditAutoModRuleModal(self, rule=self.rule)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Edit Exempt Channels/Roles", style=discord.ButtonStyle.primary)
    async def edit_exempt_channels_roles(
        self, interaction: discord.Interaction, button: discord.Button
    ) -> None:
        view = ChannelsRolesSelectView(parent=self, rule=self.rule)
        await interaction.response.send_message(
            _(
                "Select channels/roles to exempt for the AutoMod rule `{rule.name} ({rule.id})`."
            ).format(rule=self.rule),
            view=view,
            ephemeral=True,
        )

    @discord.ui.button(label="Enable/Disable", style=discord.ButtonStyle.secondary)
    async def enable_or_disable_rule(
        self, interaction: discord.Interaction, button: discord.Button
    ) -> None:
        try:
            self.rule = await self.rule.edit(
                enabled=not self.rule.enabled,
                reason=f"{self.ctx.author} ({self.ctx.author.id}) has edited the rule {self.rule.name} ({self.rule.id}).",
            )
        except discord.HTTPException as e:
            await interaction.response.send_message(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )
            return
        await interaction.response.send_message(
            _("Rule `{rule.name} ({rule.id})` enabled.").format(rule=self.rule)
            if self.rule.enabled
            else _("Rule {rule.name} `{rule.id}` disabled.").format(rule=self.rule),
            ephemeral=True,
        )
        await self._update()

    @discord.ui.button(label="Delete AutoMod Rule", style=discord.ButtonStyle.danger)
    async def delete_rule(self, interaction: discord.Interaction, button: discord.Button) -> None:
        try:
            await self.rule.delete(
                reason=f"{self.ctx.author} ({self.ctx.author.id}) has deleted the rule {self.rule.name} ({self.rule.id})."
            )
        except discord.HTTPException as e:
            await interaction.response.send_message(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )
            return
        self._deleted: bool = True
        await interaction.response.send_message(
            _("Rule `{rule.name} ({rule.id})` deleted.").format(rule=self.rule), ephemeral=True
        )
        await self._update()

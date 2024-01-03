from AAA3A_utils import CogsUtils  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import asyncio
import functools
import inspect

from redbot.core.utils.chat_formatting import box


def _(untranslated: str) -> str:  # `redgettext` will found these strings.
    return untranslated


ERROR_MESSAGE = _(
    "I attempted to do something that Discord denied me permissions for. Your command failed to successfully complete.\n{error}"
)

_ = Translator("DiscordEdit", __file__)


class DiscordEditView(discord.ui.View):
    def __init__(
        self,
        cog: commands.Cog,
        _object: typing.Union[
            discord.Guild, discord.Role, discord.TextChannel, discord.Thread, discord.VoiceChannel
        ],
        parameters: typing.Dict[str, typing.Dict[str, typing.Any]],
        get_embed_function: typing.Any,
        audit_log_reason: str,
        _object_qualified_name: str,
    ) -> None:
        super().__init__(timeout=180)
        self.cog: commands.Cog = cog
        self.ctx: commands.Context = None

        self._object: typing.Union[
            discord.Guild, discord.Role, discord.TextChannel, discord.Thread, discord.VoiceChannel
        ] = _object
        self.parameters: typing.Dict[str, typing.Dict[str, typing.Any]] = parameters
        self.get_embed_function: typing.Any = get_embed_function
        self.audit_log_reason: str = audit_log_reason
        self._object_qualified_name: str = _object_qualified_name

        self._chunked_parameters: typing.List[typing.List[str]] = []
        self._message: discord.Message = None
        self._ready: asyncio.Event = asyncio.Event()

    async def start(self, ctx: commands.Context) -> None:
        self.ctx: commands.Context = ctx
        self.remove_item(self.delete_button)
        self.remove_item(self.close_page)

        self._chunked_parameters: typing.List[typing.List[str]] = list(discord.utils.as_chunks(list(self.parameters), max_size=5))
        for button_index in range(len(self._chunked_parameters)):
            button = discord.ui.Button(
                label=f"Edit {self._object_qualified_name} {button_index + 1}"
                if len(self._chunked_parameters) > 1
                else f"Edit {self._object_qualified_name}",
                style=discord.ButtonStyle.secondary,
            )
            button.callback = functools.partial(self.edit_object_button, button_index=button_index)
            self.add_item(button)

        if not isinstance(self._object, discord.Guild) or (
            self._object.owner != self._object.me
            and self.ctx.author.id not in self.ctx.bot.owner_ids
        ):
            self.delete_button.label = f"Delete {self._object_qualified_name}"
            self.add_item(self.delete_button)
        self.add_item(self.close_page)
        self._message: discord.Message = await self.ctx.send(
            embed=self.get_embed_function(), view=self
        )

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

    @discord.ui.button(label="Delete Object", style=discord.ButtonStyle.danger)
    async def delete_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await interaction.response.defer()
        ctx = await CogsUtils.invoke_command(
            bot=interaction.client,
            author=interaction.user,
            channel=interaction.channel,
            command=f"edit{self._object_qualified_name.replace(' ', '').lower()} delete{'' if isinstance(self._object, discord.Guild) else f' {self._object.id}'}",
            message=self.ctx.message,
        )
        if not await discord.utils.async_all([check(ctx) for check in ctx.command.checks]):
            await interaction.followup.send(
                _("You are not allowed to execute this command."), ephemeral=True
            )
            return

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

    async def edit_object_button(
        self, interaction: discord.Interaction, button_index: int
    ) -> None:
        modal: discord.ui.Modal = discord.ui.Modal(title=f"Edit {self._object_qualified_name}")
        modal.on_submit = lambda interaction: interaction.response.defer()
        text_inputs: typing.Dict[str, discord.ui.TextInput] = {}
        for parameter in self._chunked_parameters[button_index]:
            text_input = discord.ui.TextInput(
                label=parameter.replace("_", " ").title(),
                style=discord.TextStyle.short,
                placeholder=repr(self.parameters[parameter]["converter"]),
                default=str(attribute)
                if (
                    attribute := getattr(
                        self._object,
                        self.parameters[parameter].get("attribute_name", parameter),
                        None,
                    )
                )
                is not None
                else None,
                required=False,
            )
            text_inputs[parameter] = text_input
            modal.add_item(text_input)
        await interaction.response.send_modal(modal)
        if await modal.wait():
            return  # Timeout.
        kwargs = {}
        for parameter in text_inputs:
            if not text_inputs[parameter].value:
                if self.parameters[parameter]["converter"] is bool:
                    continue
                kwargs[parameter] = None
                continue
            if text_inputs[parameter].value == str(text_inputs[parameter].default):
                continue
            try:
                value = await discord.ext.commands.converter.run_converters(
                    self.ctx,
                    converter=self.parameters[parameter]["converter"],
                    argument=text_inputs[parameter].value,
                    param=discord.ext.commands.parameters.Parameter(
                        name=parameter,
                        kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                        annotation=self.parameters[parameter]["converter"],
                    ),
                )
            except discord.ext.commands.errors.CommandError as e:
                await interaction.followup.send(
                    f"An error occurred when using the `{parameter}`"
                    f" converter:\n{box(e, lang='py')}"
                )
                return None
            else:
                kwargs[parameter] = value
        try:
            await self._object.edit(
                **kwargs,
                reason=self.audit_log_reason,
            )
        except discord.HTTPException as e:
            await interaction.followup.send(_(ERROR_MESSAGE).format(error=box(e, lang="py")))
        else:
            try:
                await interaction.message.edit(embed=self.get_embed_function())
            except discord.HTTPException:
                pass

from redbot.core import commands  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

# import typing_extensions  # isort:skip

import asyncio
import inspect
import string
from functools import partial
from random import choice

__all__ = [
    "Buttons",
    "Dropdown",
    "Select",
    "ChannelSelect",
    "MentionableSelect",
    "RoleSelect",
    "UserSelect",
    "Modal",
]


def _(untranslated: str) -> str:
    return untranslated


def generate_key(
    number: typing.Optional[int] = 10,
    existing_keys: typing.Optional[typing.Union[typing.List, typing.Set]] = [],
    strings_used: typing.Optional[typing.List] = {
        "ascii_lowercase": True,
        "ascii_uppercase": False,
        "digits": True,
        "punctuation": False,
        "others": [],
    },
) -> str:  # same in CogsUtils
    """
    Generate a secret key, with the choice of characters, the number of characters and a list of existing keys.
    """
    strings = []
    if "ascii_lowercase" in strings_used:
        if strings_used["ascii_lowercase"]:
            strings += string.ascii_lowercase
    if "ascii_uppercase" in strings_used:
        if strings_used["ascii_uppercase"]:
            strings += string.ascii_uppercase
    if "digits" in strings_used:
        if strings_used["digits"]:
            strings += string.digits
    if "punctuation" in strings_used:
        if strings_used["punctuation"]:
            strings += string.punctuation
    if "others" in strings_used:
        if isinstance(strings_used["others"], typing.List):
            strings += strings_used["others"]
    while True:
        # This probably won't turn into an endless loop.
        key = "".join(choice(strings) for x in range(number))
        if key not in existing_keys:
            return key


class ConfirmationAskView(discord.ui.View):
    """Request a confirmation by the user!"""

    def __init__(
        self,
        ctx: commands.Context,
        timeout: typing.Optional[int] = 60,
        timeout_message: typing.Optional[str] = _("Timed out, please try again."),
        delete_message: typing.Optional[bool] = True,
        delete_after_timeout: typing.Optional[bool] = True,
        members: typing.Optional[typing.Iterable[typing.Union[discord.Member, int]]] = None
    ):
        super().__init__(timeout=timeout)
        self.ctx: commands.Context = ctx

        self.delete_message: bool = delete_message
        self.timeout_message: str = timeout_message
        self.delete_after_timeout: bool = delete_after_timeout
        self.members: typing.Optional[typing.List[int]] = (members if members is None else [getattr(member, "id", member) for member in members])

        self._message: discord.Message = None
        self._result: typing.Optional[bool] = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id not in [self.ctx.author.id] + self.members + list(self.ctx.bot.owner_ids):
            await interaction.response.send_message(
                "You are not allowed to use this interaction.", ephemeral=True
            )
            return False
        return True

    async def on_timeout(self) -> None:
        await self.ctx.send(self.timeout_message)
        if not self.delete_after_timeout:
            for child in self.children:
                child: discord.ui.Item
                if not getattr(child, "style", 0) == discord.ButtonStyle.url:
                    child.disabled = True
            try:
                await self._message.edit(view=self)
            except discord.HTTPException:
                pass
        else:
            try:
                await self._message.delete()
            except discord.HTTPException:
                pass
        self.stop()

    @discord.ui.button(label=_("Yes"), emoji="✅", style=discord.ButtonStyle.success, custom_id="true_button")
    async def true_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        if self.delete_message:
            try:
                await self._message.delete()
            except discord.HTTPException:
                pass
        self._result = True

    @discord.ui.button(label=_("No"), emoji="✖️", style=discord.ButtonStyle.danger, custom_id="false_button")
    async def false_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        if self.delete_message:
            try:
                await self._message.delete()
            except discord.HTTPException:
                pass
        self._result = False

    async def start(self, *args, **kwargs) -> bool:
        """
        Allow confirmation to be requested from the user, in the form of buttons/dropdown/reactions/message, with many additional options.
        """
        self._message = await self.ctx.send(*args, **kwargs, view=self)
        task_result = await self.wait()
        if task_result is True or self._result is None:  # timeout
            return None
        return self._result


class Buttons(discord.ui.View):
    """Create Buttons easily."""

    def __init__(
        self,
        timeout: typing.Optional[int] = 180,
        buttons: typing.Optional[typing.List] = [{}],
        members: typing.Optional[typing.Iterable[typing.Union[discord.Member, int]]] = None,
        check: typing.Optional[typing.Callable] = None,
        function: typing.Optional[typing.Callable] = None,
        function_kwargs: typing.Optional[typing.Dict[str, typing.Any]] = {},
        infinity: typing.Optional[bool] = False,
    ) -> None:
        """style: ButtonStyle, label: Optional[str], disabled: bool, custom_id: Optional[str], url: Optional[str], emoji: Optional[Union[str, Emoji, PartialEmoji]], row: Optional[int]"""
        for button_dict in buttons:
            if "url" in button_dict and button_dict["url"] is not None:
                button_dict["style"] = 5
                continue
            if "custom_id" not in button_dict:
                button_dict["custom_id"] = "CogsUtils" + "_" + generate_key(number=10)
        self.buttons_dict_instance: typing.Dict[str, typing.Any] = {
            "timeout": timeout,
            "buttons": [b.copy() for b in buttons],
            "members": members,
            "check": check,
            "function": function,
            "function_kwargs": function_kwargs,
            "infinity": infinity,
        }
        super().__init__(timeout=timeout)
        self.infinity: bool = infinity
        self.interaction_result: typing.Optional[discord.Interaction] = None
        self.function_result: typing.Optional[typing.Any] = None
        self.members: typing.Optional[typing.List[int]] = (
            members if members is None else [getattr(member, "id", member) for member in members]
        )
        self.check: typing.Optional[typing.Callable] = check
        self.function: typing.Optional[typing.Callable] = function
        self.function_kwargs: typing.Optional[typing.Dict[str, typing.Any]] = function_kwargs
        self.clear_items()
        self.buttons: typing.List[discord.ui.Button] = []
        self.buttons_dict: typing.List[typing.Dict[str, typing.Any]] = []
        for button_dict in buttons:
            if "style" not in button_dict:
                button_dict["style"] = discord.ButtonStyle(2)
            else:
                if isinstance(button_dict["style"], int):
                    button_dict["style"] = discord.ButtonStyle(button_dict["style"])
            if "disabled" not in button_dict:
                button_dict["disabled"] = False
            if "label" not in button_dict and "emoji" not in button_dict:
                button_dict["label"] = "Test"
            button = discord.ui.Button(**button_dict)
            self.add_item(button)
            self.buttons.append(button)
            self.buttons_dict.append(button_dict)
        self.done: asyncio.Event = asyncio.Event()

    def to_dict_cogsutils(
        self, for_Config: typing.Optional[bool] = False
    ) -> typing.Dict[str, typing.Any]:
        buttons_dict_instance = self.buttons_dict_instance
        if for_Config:
            buttons_dict_instance["check"] = None
            buttons_dict_instance["function"] = None
        return buttons_dict_instance

    @classmethod
    def from_dict_cogsutils(
        cls, buttons_dict_instance: typing.Dict
    ) -> typing.Any:  # typing_extensions.Self
        if "function_args" in buttons_dict_instance:
            buttons_dict_instance["function_kwargs"] = buttons_dict_instance["function_args"]
            del buttons_dict_instance["function_args"]
        return cls(**buttons_dict_instance)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if self.members is not None:
            if interaction.user.id not in self.members:
                await interaction.response.send_message(
                    "You are not allowed to use this interaction.", ephemeral=True
                )
                return False
        if self.check is not None:
            if not self.check(interaction):
                await interaction.response.send_message(
                    "You are not allowed to use this interaction.", ephemeral=True
                )
                return False
        self.interaction_result = interaction
        if self.function is not None:
            self.function_result = await self.function(self, interaction, **self.function_kwargs)
        self.done.set()
        if not self.infinity:
            self.stop()
        return True

    async def on_timeout(self) -> None:
        self.done.set()
        self.stop()

    async def on_error(self, interaction: discord.Interaction, error: Exception, item) -> None:
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=True)
        await interaction.followup.send("Sorry. An error has occurred.", ephemeral=True)
        discord.ui.view._log.error(
            "Ignoring exception in view %r for item %r.", self, item, exc_info=error
        )

    async def wait_result(self) -> typing.Tuple[discord.Interaction, typing.Optional[typing.Any]]:
        self.done = asyncio.Event()
        await self.done.wait()
        interaction, function_result = self.get_result()
        if interaction is None:
            raise TimeoutError()
        self.interaction_result, self.function_result = None, None
        return interaction, function_result

    def get_result(self) -> typing.Tuple[discord.Interaction, typing.Optional[typing.Any]]:
        return self.interaction_result, self.function_result


class Dropdown(discord.ui.View):
    """Create Dropdown easily."""

    def __init__(
        self,
        timeout: typing.Optional[int] = 180,
        placeholder: typing.Optional[str] = "Choose an option.",
        min_values: typing.Optional[int] = 1,
        max_values: typing.Optional[int] = 1,
        *,
        _type: typing.Optional[discord.ComponentType] = discord.ComponentType.select,
        options: typing.Optional[
            typing.Union[typing.List, discord.ComponentType, discord.ui.Select]
        ] = [{}],
        disabled: typing.Optional[bool] = False,
        members: typing.Optional[typing.Iterable[typing.Union[discord.Member, int]]] = None,
        check: typing.Optional[typing.Callable] = None,
        function: typing.Optional[typing.Callable] = None,
        function_kwargs: typing.Optional[typing.Dict[str, typing.Any]] = {},
        infinity: typing.Optional[bool] = False,
        custom_id: typing.Optional[str] = f"CogsUtils_{generate_key(number=10)}",
    ) -> None:
        """label: str, value: str, description: Optional[str], emoji: Optional[Union[str, Emoji, PartialEmoji]], default: bool"""
        self.dropdown_dict_instance: typing.Dict[str, typing.Any] = {
            "timeout": timeout,
            "placeholder": placeholder,
            "min_values": min_values,
            "max_values": max_values,
            "_type": _type,
            "options": ([(o.copy() if hasattr(o, "copy") else o) for o in options])
            if isinstance(options, typing.List)
            else options,
            "members": members,
            "check": check,
            "function": function,
            "function_kwargs": function_kwargs,
            "infinity": infinity,
            "custom_id": custom_id,
        }
        super().__init__(timeout=timeout)
        self._type: discord.ComponentType = _type
        self.infinity: bool = infinity
        self.interaction_result: typing.Optional[discord.Interaction] = None
        self.options_result: typing.Optional[typing.List[str]] = None
        self.function_result: typing.Optional[typing.Any] = None
        self.disabled: bool = disabled
        self.members: typing.Optional[typing.List[int]] = (
            members if members is None else [getattr(member, "id", member) for member in members]
        )
        self.check: typing.Optional[typing.Callable] = check
        self.function: typing.Optional[typing.Callable] = function
        self.function_kwargs: typing.Optional[typing.Dict[str, typing.Any]] = function_kwargs
        self.clear_items()
        self.options: typing.List[discord.SelectOption] = []
        self.options_dict: typing.List[typing.Dict[str, typing.Any]] = []
        if _type is discord.ComponentType.select or _type is Select:
            for option_dict in options:
                if "label" not in option_dict and "emoji" not in option_dict:
                    option_dict["label"] = "Test"
                option = discord.SelectOption(**option_dict)
                self.options.append(option)
                self.options_dict.append(option_dict)
            self.dropdown: discord.ui.Select = Select(
                placeholder=placeholder,
                min_values=min_values,
                max_values=max_values,
                options=self.options,
                disabled=disabled,
                custom_id=custom_id,
            )
        elif _type is discord.ComponentType.channel_select or _type is ChannelSelect:
            if options == [{}] or options == []:
                options = None
            self.dropdown: discord.ui.Select = ChannelSelect(
                placeholder=placeholder,
                min_values=min_values,
                max_values=max_values,
                channel_types=options,
                disabled=disabled,
                custom_id=custom_id,
            )
        elif _type is discord.ComponentType.mentionable_select or type is MentionableSelect:
            self.dropdown: discord.ui.Select = MentionableSelect(
                placeholder=placeholder,
                min_values=min_values,
                max_values=max_values,
                disabled=disabled,
                custom_id=custom_id,
            )
        elif _type is discord.ComponentType.role_select or type is RoleSelect:
            self.dropdown: discord.ui.Select = RoleSelect(
                placeholder=placeholder,
                min_values=min_values,
                max_values=max_values,
                disabled=disabled,
                custom_id=custom_id,
            )
        elif _type is discord.ComponentType.user_select or _type is UserSelect:
            self.dropdown: discord.ui.Select = UserSelect(
                placeholder=placeholder,
                min_values=min_values,
                max_values=max_values,
                disabled=disabled,
                custom_id=custom_id,
            )
        else:
            if inspect.isclass(_type):
                self.dropdown: discord.ui.Select = _type(
                    placeholder=placeholder,
                    min_values=min_values,
                    max_values=max_values,
                    disabled=disabled,
                    custom_id=custom_id,
                )
            else:
                self.dropdown = _type
            setattr(self.dropdown, "callback", partial(_Select.callback, self.dropdown))
        self.add_item(self.dropdown)
        self.done: asyncio.Event = asyncio.Event()

    def to_dict_cogsutils(
        self, for_Config: typing.Optional[bool] = False
    ) -> typing.Dict[str, typing.Any]:
        dropdown_dict_instance = self.dropdown_dict_instance
        if for_Config:
            dropdown_dict_instance["members"] = None
            dropdown_dict_instance["check"] = None
            dropdown_dict_instance["function"] = None
        return dropdown_dict_instance

    @classmethod
    def from_dict_cogsutils(
        cls, dropdown_dict_instance: typing.Dict
    ) -> typing.Any:  # typing_extensions.Self
        if "function_args" in dropdown_dict_instance:
            dropdown_dict_instance["function_kwargs"] = dropdown_dict_instance["function_args"]
            del dropdown_dict_instance["function_args"]
        return cls(**dropdown_dict_instance)

    async def on_timeout(self) -> None:
        self.done.set()
        self.stop()

    async def on_error(self, interaction: discord.Interaction, error: Exception, item) -> None:
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=True)
        await interaction.followup.send("Sorry. An error has occurred.", ephemeral=True)
        discord.ui.view._log.error(
            "Ignoring exception in view %r for item %r.", self, item, exc_info=error
        )

    async def wait_result(
        self,
    ) -> typing.Tuple[discord.Interaction, typing.List[str], typing.Optional[typing.Any]]:
        self.done = asyncio.Event()
        await self.done.wait()
        interaction, options, function_result = self.get_result()
        if interaction is None:
            raise TimeoutError()
        self.interaction_result, self.options_result, self.function_result = None, None, None
        return interaction, options, function_result

    def get_result(
        self,
    ) -> typing.Tuple[discord.Interaction, typing.List[str], typing.Optional[typing.Any]]:
        return self.interaction_result, self.options_result, self.function_result

    async def callback(self, interaction: discord.Interaction) -> None:
        if self.members is not None:
            if interaction.user.id not in self.members:
                await interaction.response.send_message(
                    "You are not allowed to use this interaction.", ephemeral=True
                )
                return False
        if self.check is not None:
            if not self.check(interaction):
                await interaction.response.send_message(
                    "You are not allowed to use this interaction.", ephemeral=True
                )
                return False
        self.interaction_result = interaction
        self.options_result = self.dropdown.values
        if self.function is not None:
            self.function_result = await self.function(
                self, interaction, self.dropdown.values, **self.function_kwargs
            )
        self.done.set()
        if not self.infinity:
            self.stop()


class _Select:
    async def callback(self, interaction: discord.Interaction) -> None:
        if hasattr(self.view, "callback"):
            await self.view.callback(interaction)
        else:
            super().callback(interaction)


class Select(_Select, discord.ui.Select):
    def __init__(
        self,
        placeholder: typing.Optional[str] = "Choose an option.",
        min_values: typing.Optional[int] = 1,
        max_values: typing.Optional[int] = 1,
        *,
        options: typing.Optional[typing.List] = [],
        disabled: typing.Optional[bool] = False,
        custom_id: typing.Optional[str] = f"CogsUtils_{generate_key(number=10)}",
        row: typing.Optional[int] = None,
    ) -> None:
        super().__init__(
            custom_id=custom_id,
            placeholder=placeholder,
            min_values=min_values,
            max_values=max_values,
            options=options,
            disabled=disabled,
            row=row,
        )


class ChannelSelect(_Select, discord.ui.ChannelSelect):
    def __init__(
        self,
        placeholder: typing.Optional[str] = "Choose a channel.",
        min_values: typing.Optional[int] = 1,
        max_values: typing.Optional[int] = 1,
        *,
        channel_types: typing.Optional[discord.ChannelType] = [],
        disabled: typing.Optional[bool] = False,
        custom_id: typing.Optional[str] = f"CogsUtils_{generate_key(number=10)}",
        row: typing.Optional[int] = None,
    ) -> None:
        super().__init__(
            custom_id=custom_id,
            placeholder=placeholder,
            min_values=min_values,
            max_values=max_values,
            channel_types=channel_types,
            disabled=disabled,
            row=row,
        )


class MentionableSelect(_Select, discord.ui.MentionableSelect):
    def __init__(
        self,
        placeholder: typing.Optional[str] = "Choose an option.",
        min_values: typing.Optional[int] = 1,
        max_values: typing.Optional[int] = 1,
        *,
        disabled: typing.Optional[bool] = False,
        custom_id: typing.Optional[str] = f"CogsUtils_{generate_key(number=10)}",
        row: typing.Optional[int] = None,
    ) -> None:
        super().__init__(
            custom_id=custom_id,
            placeholder=placeholder,
            min_values=min_values,
            max_values=max_values,
            disabled=disabled,
            row=row,
        )


class RoleSelect(_Select, discord.ui.RoleSelect):
    def __init__(
        self,
        placeholder: typing.Optional[str] = "Choose a role.",
        min_values: typing.Optional[int] = 1,
        max_values: typing.Optional[int] = 1,
        *,
        disabled: typing.Optional[bool] = False,
        custom_id: typing.Optional[str] = f"CogsUtils_{generate_key(number=10)}",
        row: typing.Optional[int] = None,
    ) -> None:
        super().__init__(
            custom_id=custom_id,
            placeholder=placeholder,
            min_values=min_values,
            max_values=max_values,
            disabled=disabled,
            row=row,
        )


class UserSelect(_Select, discord.ui.UserSelect):
    def __init__(
        self,
        placeholder: typing.Optional[str] = "Choose an user.",
        min_values: typing.Optional[int] = 1,
        max_values: typing.Optional[int] = 1,
        *,
        disabled: typing.Optional[bool] = False,
        custom_id: typing.Optional[str] = f"CogsUtils_{generate_key(number=10)}",
        row: typing.Optional[int] = None,
    ) -> None:
        super().__init__(
            custom_id=custom_id,
            placeholder=placeholder,
            min_values=min_values,
            max_values=max_values,
            disabled=disabled,
            row=row,
        )


class Modal(discord.ui.Modal):
    """Create Modal easily."""

    def __init__(
        self,
        title: typing.Optional[str] = "Form",
        timeout: typing.Optional[float] = None,
        inputs: typing.Optional[typing.List] = [{}],
        members: typing.Optional[typing.Iterable[typing.Union[discord.Member, int]]] = None,
        check: typing.Optional[typing.Callable] = None,
        function: typing.Optional[typing.Callable] = None,
        function_kwargs: typing.Optional[typing.Dict[str, typing.Any]] = {},
        custom_id: typing.Optional[str] = f"CogsUtils_{generate_key(number=10)}",
    ) -> None:
        """label: str, style: TextStyle, custom_id: str, placeholder: Optional[str], default: Optional[str], required: bool, min_length: Optional[int], max_length: Optional[int], row: Optional[int]"""
        for input_dict in inputs:
            if "custom_id" not in input_dict:
                input_dict["custom_id"] = f"CogsUtils_{generate_key(number=10)}"
        self.modal_dict_instance = {
            "title": title,
            "timeout": timeout,
            "inputs": [i.copy() for i in inputs],
            "members": members,
            "check": check,
            "function": function,
            "function_kwargs": function_kwargs,
            "custom_id": custom_id,
        }
        super().__init__(title=title, timeout=timeout, custom_id=custom_id)
        self.title: str = title
        self.interaction_result: typing.Optional[discord.Interaction] = None
        self.inputs_result: typing.Optional[typing.List[discord.ui.TextInput]] = None
        self.function_result: typing.Optional[typing.Any] = None
        self.members: typing.Optional[typing.List[int]] = (
            members if members is None else [getattr(member, "id", member) for member in members]
        )
        self.check: typing.Optional[typing.Callable] = check
        self.function: typing.Optional[typing.Callable] = function
        self.function_kwargs: typing.Optional[typing.Dict[str, typing.Any]] = function_kwargs
        self.inputs: typing.List[discord.ui.TextInput] = []
        self.inputs_dict: typing.List[typing.Dict[str, typing.Any]] = []
        for input_dict in inputs:
            if "label" not in input_dict:
                input_dict["label"] = "Test"
            if "style" in input_dict:
                if isinstance(input_dict["style"], int):
                    input_dict["style"] = discord.TextStyle(input_dict["style"])
            input = discord.ui.TextInput(**input_dict)
            self.add_item(input)
            self.inputs.append(input)
            self.inputs_dict.append(input_dict)
        self.done: asyncio.Event = asyncio.Event()

    def to_dict_cogsutils(
        self, for_Config: typing.Optional[bool] = False
    ) -> typing.Dict[str, typing.Any]:
        modal_dict_instance = self.modal_dict_instance
        if for_Config:
            modal_dict_instance["members"] = None
            modal_dict_instance["check"] = None
            modal_dict_instance["function"] = None
        return modal_dict_instance

    @classmethod
    def from_dict_cogsutils(
        cls, modal_dict_instance: typing.Dict
    ) -> typing.Any:  # typing_extensions.Self
        if "function_args" in modal_dict_instance:
            modal_dict_instance["function_kwargs"] = modal_dict_instance["function_args"]
            del modal_dict_instance["function_args"]
        return cls(**modal_dict_instance)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if self.members is not None:
            if interaction.user.id not in self.members:
                await interaction.response.send_message(
                    "You are not allowed to use this interaction.", ephemeral=True
                )
                return False
        if self.check is not None:
            if not self.check(interaction):
                await interaction.response.send_message(
                    "You are not allowed to use this interaction.", ephemeral=True
                )
                return False
        self.interaction_result = interaction
        self.inputs_result = self.inputs
        if self.function is not None:
            self.function_result = await self.function(
                self, self.interaction_result, self.inputs_result, **self.function_kwargs
            )
        self.done.set()
        self.stop()

    async def on_timeout(self) -> None:
        self.done.set()
        self.stop()

    async def wait_result(
        self,
    ) -> typing.Tuple[
        discord.Interaction, typing.List[discord.ui.TextInput], typing.Optional[typing.Any]
    ]:
        self.done = asyncio.Event()
        await self.done.wait()
        interaction, inputs_result, function_result = self.get_result()
        if interaction is None:
            raise TimeoutError()
        self.interaction_result, self.inputs_result, self.function_result = None, None, None
        return interaction, inputs_result, function_result

    def get_result(
        self,
    ) -> typing.Tuple[
        discord.Interaction, typing.List[discord.ui.TextInput], typing.Optional[typing.Any]
    ]:
        return self.interaction_result, self.inputs_result, self.function_result

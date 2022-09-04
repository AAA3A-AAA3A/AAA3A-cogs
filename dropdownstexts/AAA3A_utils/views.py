import discord  # isort:skip
import typing  # isort:skip

import asyncio
import string

from random import choice

__all__ = ["Buttons", "Dropdown", "Modal"]

def _(untranslated: str):
    return untranslated

def generate_key(number: typing.Optional[int]=10, existing_keys: typing.Optional[typing.Union[typing.List, typing.Set]]=[], strings_used: typing.Optional[typing.List]={"ascii_lowercase": True, "ascii_uppercase": False, "digits": True, "punctuation": False, "others": []}):  # same in CogsUtils
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

class Buttons(discord.ui.View):
    """Create Buttons easily."""

    def __init__(self, timeout: typing.Optional[float]=180, buttons: typing.Optional[typing.List]=[{}], members: typing.Optional[typing.List]=None, check: typing.Optional[typing.Any]=None, function: typing.Optional[typing.Any]=None, function_args: typing.Optional[typing.Dict]={}, infinity: typing.Optional[bool]=False):
        """style: ButtonStyle, label: Optional[str], disabled: bool, custom_id: Optional[str], url: Optional[str], emoji: Optional[Union[str, Emoji, PartialEmoji]], row: Optional[int]"""
        for button_dict in buttons:
            if "url" in button_dict and button_dict["url"] is not None:
                button_dict["style"] = 5
                continue
            if "custom_id" not in button_dict:
                button_dict["custom_id"] = "CogsUtils" + "_" + generate_key(number=10)
        self.buttons_dict_instance = {"timeout": timeout, "buttons": [b.copy() for b in buttons], "members": members, "check": check, "function": function, "function_args": function_args, "infinity": infinity}
        super().__init__(timeout=timeout)
        self.infinity = infinity
        self.interaction_result = None
        self.function_result = None
        self.members = members
        self.check = check
        self.function = function
        self.function_args = function_args
        self.clear_items()
        self.buttons = []
        self.buttons_dict = []
        self.done = asyncio.Event()
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

    def to_dict_cogsutils(self, for_Config: typing.Optional[bool]=False):
        buttons_dict_instance = self.buttons_dict_instance
        if for_Config:
            buttons_dict_instance["check"] = None
            buttons_dict_instance["function"] = None
        return buttons_dict_instance

    @classmethod
    def from_dict_cogsutils(cls, buttons_dict_instance: typing.Dict):
        return cls(**buttons_dict_instance)

    async def interaction_check(self, interaction: discord.Interaction):
        if self.check is not None:
            if not self.check(interaction):
                await interaction.response.send_message("You are not allowed to use this interaction.", ephemeral=True)
                return True
        if self.members is not None:
            if interaction.user.id not in self.members:
                await interaction.response.send_message("You are not allowed to use this interaction.", ephemeral=True)
                return True
        self.interaction_result = interaction
        if self.function is not None:
            self.function_result = await self.function(self, interaction, **self.function_args)
        self.done.set()
        if not self.infinity:
            self.stop()
        return True

    async def on_timeout(self):
        self.done.set()
        self.stop()

    async def wait_result(self):
        self.done = asyncio.Event()
        await self.done.wait()
        interaction, function_result = self.get_result()
        if interaction is None:
            raise TimeoutError()
        self.interaction_result, self.function_result = None, None
        return interaction, function_result

    def get_result(self):
        return self.interaction_result, self.function_result

class Dropdown(discord.ui.View):
    """Create Dropdown easily."""

    def __init__(self, timeout: typing.Optional[float]=180, placeholder: typing.Optional[str]="Choose a option.", min_values: typing.Optional[int]=1, max_values: typing.Optional[int]=1, *, options: typing.Optional[typing.List]=[{}], disabled: typing.Optional[bool]=False, members: typing.Optional[typing.List]=None, check: typing.Optional[typing.Any]=None, function: typing.Optional[typing.Any]=None, function_args: typing.Optional[typing.Dict]={}, infinity: typing.Optional[bool]=False, custom_id: typing.Optional[str]=f"CogsUtils_{generate_key(number=10)}"):
        """label: str, value: str, description: Optional[str], emoji: Optional[Union[str, Emoji, PartialEmoji]], default: bool"""
        self.dropdown_dict_instance = {"timeout": timeout, "placeholder": placeholder, "min_values": min_values, "max_values": max_values, "options": [o.copy() for o in options], "members": members, "check": check, "function": function, "function_args": function_args, "infinity": infinity, "custom_id": custom_id}
        super().__init__(timeout=timeout)
        self.infinity = infinity
        self.interaction_result = None
        self.options_result = None
        self.function_result = None
        self.disabled = disabled
        self.members = members
        self.check = check
        self.function = function
        self.function_args = function_args
        self.clear_items()
        self.dropdown = Select(placeholder=placeholder, min_values=min_values, max_values=max_values, options=options, disabled=disabled, custom_id=custom_id)
        self.options = self.dropdown._options
        self.options_dict = self.dropdown.options_dict
        self.done = asyncio.Event()
        self.add_item(self.dropdown)

    def to_dict_cogsutils(self, for_Config: typing.Optional[bool]=False):
        dropdown_dict_instance = self.dropdown_dict_instance
        if for_Config:
            dropdown_dict_instance["members"] = None
            dropdown_dict_instance["check"] = None
            dropdown_dict_instance["function"] = None
        return dropdown_dict_instance

    @classmethod
    def from_dict_cogsutils(cls, dropdown_dict_instance: typing.Dict):
        return cls(**dropdown_dict_instance)

    async def on_timeout(self):
        self.dropdown.done.set()
        self.stop()

    async def wait_result(self):
        self.done = asyncio.Event()
        await self.done.wait()
        interaction, options, function_result = self.get_result()
        if interaction is None:
            raise TimeoutError()
        self.interaction_result, self.options_result, self.function_result = None, None, None
        return interaction, options, function_result

    def get_result(self):
        return self.interaction_result, self.options_result, self.function_result

    async def callback(self, interaction: discord.Interaction):
        if self.check is not None:
            if not self.check(interaction):
                await interaction.response.send_message("You are not allowed to use this interaction.", ephemeral=True)
                return True
        if self.members is not None:
            if interaction.user.id not in self.members:
                await interaction.response.send_message("You are not allowed to use this interaction.", ephemeral=True)
                return True
        self.interaction_result = interaction
        self.options_result = self.dropdown.values
        if self.function is not None:
            self.function_result = await self.function(self, interaction, self.dropdown.values, **self.function_args)
        self.done.set()
        if not self.infinity:
            self.stop()

class Select(discord.ui.Select):

    def __init__(self, placeholder: typing.Optional[str]="Choose a option.", min_values: typing.Optional[int]=1, max_values: typing.Optional[int]=1, *, options: typing.Optional[typing.List]=[], disabled: typing.Optional[bool]=False, custom_id: typing.Optional[str]=f"CogsUtils_{generate_key(number=10)}"):
        self._options = []
        self.options_dict = []
        self.done = asyncio.Event()
        for option_dict in options:
            if "label" not in option_dict and "emoji" not in option_dict:
                option_dict["label"] = "Test"
            option = discord.SelectOption(**option_dict)
            self._options.append(option)
            self.options_dict.append(option_dict)
        super().__init__(custom_id=custom_id, placeholder=placeholder, min_values=min_values, max_values=max_values, options=self._options, disabled=disabled)

    async def callback(self, interaction: discord.Interaction):
        if hasattr(self.view, "callback"):
            await self.view.callback(interaction)

class Modal(discord.ui.Modal):
    """Create Modal easily."""

    def __init__(self, title: typing.Optional[str]="Form", timeout: typing.Optional[float]=None, inputs: typing.Optional[typing.List]=[{}], members: typing.Optional[typing.List]=None, check: typing.Optional[typing.Any]=None, function: typing.Optional[typing.Any]=None, function_args: typing.Optional[typing.Dict]={}, custom_id: typing.Optional[str]=f"CogsUtils_{generate_key(number=10)}"):
        """label: str, style: TextStyle, custom_id: str, placeholder: Optional[str], default: Optional[str], required: bool, min_length: Optional[int], max_length: Optional[int], row: Optional[int]"""
        for input_dict in inputs:
            if "custom_id" not in input_dict:
                input_dict["custom_id"] = f"CogsUtils_{generate_key(number=10)}"
        self.modal_dict_instance = {"title": title, "timeout": timeout, "inputs": [i.copy() for i in inputs], "members": members, "check": check, "function": function, "function_args": function_args, "custom_id": custom_id}
        super().__init__(title=title, timeout=timeout, custom_id=custom_id)
        self.title = title
        self.interaction_result = None
        self.inputs_result = None
        self.function_result = None
        self.members = members
        self.check = check
        self.function = function
        self.function_args = function_args
        self.inputs = []
        self.inputs_dict = []
        self.done = asyncio.Event()
        for input_dict in inputs:
            if "label" not in input_dict:
                input_dict["label"] = "Test"
            if "style" in input_dict:
                if isinstance(input_dict["style"], int):
                    input_dict["style"] = discord.ui.text_input.TextStyle(input_dict["style"])
            input = discord.ui.text_input.TextInput(**input_dict)
            self.add_item(input)
            self.inputs.append(input)
            self.inputs_dict.append(input_dict)

    def to_dict_cogsutils(self, for_Config: typing.Optional[bool]=False):
        modal_dict_instance = self.modal_dict_instance
        if for_Config:
            modal_dict_instance["members"] = None
            modal_dict_instance["check"] = None
            modal_dict_instance["function"] = None
        return modal_dict_instance

    @classmethod
    def from_dict_cogsutils(cls, modal_dict_instance: typing.Dict):
        return cls(**modal_dict_instance)

    async def on_submit(self, interaction: discord.Interaction):
        if self.check is not None:
            if not self.check(interaction):
                await interaction.response.send_message("You are not allowed to use this interaction.", ephemeral=True)
                return True
        if self.members is not None:
            if interaction.user.id not in self.members:
                await interaction.response.send_message("You are not allowed to use this interaction.", ephemeral=True)
                return True
        self.interaction_result = interaction
        self.inputs_result = self.inputs
        if self.function is not None:
            self.function_result = await self.function(self, self.interaction_result, self.inputs_result, **self.function_args)
        self.done.set()
        self.stop()

    async def on_timeout(self):
        self.done.set()
        self.stop()

    async def wait_result(self):
        self.done = asyncio.Event()
        await self.done.wait()
        interaction, inputs_result, function_result = self.get_result()
        if interaction is None:
            raise TimeoutError()
        self.interaction_result, self.inputs_result, self.function_result = None, None, None
        return interaction, inputs_result, function_result

    def get_result(self):
        return self.interaction_result, self.inputs_result, self.function_result
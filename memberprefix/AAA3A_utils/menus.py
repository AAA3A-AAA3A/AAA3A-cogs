from redbot.core import commands  # isort:skip
from redbot.core.bot import Red  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import asyncio
import re

from redbot.core.utils.chat_formatting import box, pagify, text_to_file
from redbot.core.utils.menus import start_adding_reactions
from redbot.core.utils.predicates import MessagePredicate, ReactionPredicate
from redbot.vendored.discord.ext import menus

if discord.version_info.major >= 2:
    from .views import Buttons, Dropdown, Modal

__all__ = ["Reactions", "Menu"]


def _(untranslated: str):
    return untranslated


class Reactions:
    """Create Reactions easily."""

    def __init__(
        self,
        bot: Red,
        message: discord.Message,
        remove_reaction: typing.Optional[bool] = True,
        timeout: typing.Optional[float] = 180,
        reactions: typing.Optional[typing.List] = ["✅", "❌"],
        members: typing.Optional[typing.Iterable[discord.Member]] = None,
        check: typing.Optional[typing.Any] = None,
        function: typing.Optional[typing.Any] = None,
        function_args: typing.Optional[typing.Dict] = {},
        infinity: typing.Optional[bool] = False,
    ):
        self.reactions_dict_instance = {
            "message": message,
            "timeout": timeout,
            "reactions": reactions,
            "members": members,
            "check": check,
            "function": function,
            "function_args": function_args,
            "infinity": infinity,
        }
        self.bot = bot
        self.message = message
        self.remove_reaction = remove_reaction
        self.timeout = timeout
        self.infinity = infinity
        self.reaction_result = None
        self.user_result = None
        self.function_result = None
        self.members = (
            members if members is None else [getattr(member, "id", member) for member in members]
        )
        self.check = check
        self.function = function
        self.function_args = function_args
        self.reactions = reactions
        self.done = asyncio.Event()
        self.r = False
        asyncio.create_task(self.wait())

    def to_dict_cogsutils(self, for_Config: typing.Optional[bool] = False):
        reactions_dict_instance = self.reactions_dict_instance
        if for_Config:
            reactions_dict_instance["bot"] = None
            reactions_dict_instance["message"] = None
            reactions_dict_instance["members"] = None
            reactions_dict_instance["check"] = None
            reactions_dict_instance["function"] = None
        return reactions_dict_instance

    @classmethod
    def from_dict_cogsutils(cls, reactions_dict_instance: typing.Dict):
        return cls(**reactions_dict_instance)

    async def wait(self):
        if not self.r:
            await start_adding_reactions(self.message, self.reactions)
            self.r = True
        predicates = ReactionPredicate.same_context(message=self.message)
        running = True
        try:
            while True:
                if not running:
                    break
                tasks = [asyncio.create_task(self.bot.wait_for("reaction_add", check=predicates))]
                done, pending = await asyncio.wait(
                    tasks, timeout=self.timeout, return_when=asyncio.FIRST_COMPLETED
                )
                for task in pending:
                    task.cancel()
                if len(done) == 0:
                    raise TimeoutError()
                reaction, user = done.pop().result()
                running = await self.reaction_check(reaction, user)
        except TimeoutError:
            await self.on_timeout()

    async def reaction_check(self, reaction: discord.Reaction, user: discord.User):
        async def remove_reaction(
            remove_reaction,
            message: discord.Message,
            reaction: discord.Reaction,
            user: discord.User,
        ):
            if remove_reaction:
                try:
                    await message.remove_reaction(emoji=reaction, member=user)
                except discord.HTTPException:
                    pass

        if not str(reaction.emoji) in self.reactions:
            await remove_reaction(self.remove_reaction, self.message, reaction, user)
            return False
        if self.members is not None:
            if user.id not in self.members:
                await remove_reaction(self.remove_reaction, self.message, reaction, user)
                return False
        if self.check is not None:
            if not self.check(reaction, user):
                await remove_reaction(self.remove_reaction, self.message, reaction, user)
                return False
        await remove_reaction(self.remove_reaction, self.message, reaction, user)
        self.reaction_result = reaction
        self.user_result = user
        if self.function is not None:
            self.function_result = await self.function(self, reaction, user, **self.function_args)
        self.done.set()
        if self.infinity:
            return True
        else:
            return False

    async def on_timeout(self):
        self.done.set()

    async def wait_result(self):
        self.done = asyncio.Event()
        await self.done.wait()
        reaction, user, function_result = self.get_result()
        if reaction is None:
            raise TimeoutError()
        self.reaction_result, self.user_result, self.function_result = None, None, None
        return reaction, user, function_result

    def get_result(self):
        return self.reaction_result, self.user_result, self.function_result


class Menu:
    """Create Menus easily."""

    def __init__(
        self,
        pages: typing.List[
            typing.Union[typing.Dict[str, typing.Union[str, typing.Any]], discord.Embed, str]
        ],
        timeout: typing.Optional[int] = 180,
        delete_after_timeout: typing.Optional[bool] = False,
        way: typing.Optional[typing.Literal["buttons", "reactions", "dropdown"]] = "buttons",
        controls: typing.Optional[typing.Dict] = None,
        page_start: typing.Optional[int] = 0,
        check_owner: typing.Optional[bool] = True,
        members: typing.Optional[typing.Iterable[discord.Member]] = [],
        box_language_py: typing.Optional[bool] = False,
    ):
        self.ctx: commands.Context = None
        self.pages: typing.List = pages
        self.timeout: int = timeout
        self.delete_after_timeout: bool = delete_after_timeout
        self.way: typing.Literal["buttons", "reactions", "dropdown"] = way
        if controls is None:
            controls = {
                "⏮️": "left_page",
                "◀️": "prev_page",
                "❌": "close_page",
                "▶️": "next_page",
                "⏭️": "right_page",
                "🔻": "send_all",
                "📩": "send_interactive",
                "💾": "send_as_file",
            }
        self.controls: typing.Dict = controls.copy()
        self.check_owner: bool = check_owner
        self.members: typing.List = members
        if (
            not discord.version_info.major >= 2
            and self.way == "buttons"
            or not discord.version_info.major >= 2
            and self.way == "dropdown"
        ):
            self.way = "reactions"
        if not pages:
            pages = ["Nothing to show."]
        if isinstance(self.pages, str):
            self.pages = list(pagify(self.pages, page_length=2000 - 10))
        if box_language_py and all([isinstance(page, str) for page in self.pages]):
            self.pages = [box(page, "py") for page in self.pages]
        if not isinstance(self.pages[0], (typing.Dict, discord.Embed, str)):
            raise RuntimeError("Pages must be of type typing.Dict, discord.Embed or str.")

        self.source = self._SimplePageSource(items=self.pages)
        if not self.source.is_paginating():
            for emoji, name in controls.items():
                if name in ["left_page", "prev_page", "next_page", "right_page"]:
                    del self.controls[emoji]
        if (
            not self.source.is_paginating()
            or len(self.pages) > 3
        ):
            for emoji, name in controls.items():
                if name in ["send_all"]:
                    del self.controls[emoji]
        if not self.source.is_paginating() or len(self.pages) <= 3:
            for emoji, name in controls.items():
                if name in ["send_interactive"]:
                    del self.controls[emoji]
        if not all([isinstance(page, str) for page in self.pages]):
            for emoji, name in controls.items():
                if name in ["send_as_file"]:
                    del self.controls[emoji]

        self.message: discord.Message = None
        self.view: typing.Union[Buttons, Dropdown] = None
        self.current_page: int = page_start
        self.is_done = asyncio.Event()

    async def start(self, ctx: commands.Context):
        """
        Used to start the menu displaying the first page requested.
        Parameters
        ----------
            ctx: `commands.Context`
                The context to start the menu in.
        """
        self.ctx = ctx
        if self.way == "buttons":
            if self.members is None:
                self.view = Buttons(
                    timeout=self.timeout,
                    buttons=[
                        {"emoji": str(e), "custom_id": str(n), "disabled": False}
                        for e, n in self.controls.items()
                    ],
                    members=None,
                    infinity=True,
                )
            else:
                self.view = Buttons(
                    timeout=self.timeout,
                    buttons=[
                        {"emoji": str(e), "custom_id": str(n), "disabled": False}
                        for e, n in self.controls.items()
                    ],
                    members=[self.ctx.author.id] + list(self.ctx.bot.owner_ids)
                    if self.check_owner
                    else [] + [x.id for x in self.members],
                    infinity=True,
                )
            self.view.add_item(
                discord.ui.Button(
                    label=f"Page {self.current_page + 1}/{len(self.pages)}",
                    custom_id="choose_page",
                    disabled=False,
                )
            )
            await self.send_initial_message(self.ctx)
        elif self.way == "reactions":
            await self.send_initial_message(self.ctx)
            if self.members is None:
                self.view = Reactions(
                    bot=self.ctx.bot,
                    message=self.message,
                    remove_reaction=True,
                    timeout=self.timeout,
                    reactions=[str(e) for e in self.controls.keys()],
                    members=None,
                    infinity=True,
                )
            else:
                self.view = Reactions(
                    bot=self.ctx.bot,
                    message=self.message,
                    remove_reaction=True,
                    timeout=self.timeout,
                    reactions=[str(e) for e in self.controls.keys()],
                    members=[self.ctx.author.id] + list(self.ctx.bot.owner_ids)
                    if self.check_owner
                    else [] + [x.id for x in self.members],
                    infinity=True,
                )
        elif self.way == "dropdown":
            if self.members is None:
                self.view = Dropdown(
                    timeout=self.timeout,
                    options=[
                        {"emoji": str(e), "label": str(n).replace("_", " ").capitalize()}
                        for e, n in self.controls.items()
                    ],
                    disabled=False,
                    members=None,
                    infinity=True,
                )
            else:
                self.view = Dropdown(
                    timeout=self.timeout,
                    options=[
                        {"emoji": str(e), "label": str(n).replace("_", " ").capitalize()}
                        for e, n in self.controls.items()
                    ],
                    disabled=False,
                    members=[self.ctx.author.id] + list(self.ctx.bot.owner_ids)
                    if self.check_owner
                    else [] + [x.id for x in self.members],
                    infinity=True,
                )
            await self.send_initial_message(self.ctx)
        try:
            while True:
                if self.way == "buttons":
                    interaction, function_result = await self.view.wait_result()
                    response = interaction.data["custom_id"]
                elif self.way == "reactions":
                    reaction, user, function_result = await self.view.wait_result()
                    response = self.controls[str(reaction.emoji)]
                elif self.way == "dropdown":
                    interaction, values, function_result = await self.view.wait_result()
                    response = str(values[0]).lower().replace(" ", "_")
                if response == "left_page":
                    self.current_page = 0
                elif response == "prev_page":
                    self.current_page += -1
                elif response == "close_page":
                    if self.way == "buttons" or self.way == "dropdown":
                        self.view.stop()
                    await self.message.delete()
                    break
                elif response == "next_page":
                    self.current_page += 1
                elif response == "right_page":
                    self.current_page = self.source.get_max_pages() - 1
                elif response == "send_all":
                    for x in range(0, len(self.pages)):
                        current, kwargs = await self.get_page(x)
                        await ctx.send(**kwargs)
                    if self.way in ["buttons", "dropdown"]:
                        try:
                            await interaction.response.defer()
                        except discord.errors.NotFound:
                            pass
                    continue
                elif response == "send_interactive":

                    async def send_interactive(
                        timeout: typing.Optional[int] = 15,
                    ) -> typing.List[discord.Message]:
                        ret = []
                        for x in range(0, len(self.pages)):
                            current, kwargs = await self.get_page(x)
                            msg = await self.ctx.send(**kwargs)
                            ret.append(msg)
                            n_remaining = len(self.pages) - current
                            if n_remaining > 0:
                                if n_remaining == 1:
                                    plural = ""
                                    is_are = "is"
                                else:
                                    plural = "s"
                                    is_are = "are"
                                query = await self.ctx.send(
                                    f"There {is_are} still {n_remaining} message{plural} remaining. Type `more` to continue."
                                )
                                try:
                                    resp = await self.ctx.bot.wait_for(
                                        "message",
                                        check=MessagePredicate.lower_equal_to("more", self.ctx),
                                        timeout=timeout,
                                    )
                                except asyncio.TimeoutError:
                                    try:
                                        await query.delete()
                                    except discord.HTTPException:
                                        pass
                                    break
                                else:
                                    try:
                                        await self.ctx.channel.delete_messages((query, resp))
                                    except (discord.HTTPException, AttributeError):
                                        try:
                                            await query.delete()
                                        except discord.HTTPException:
                                            pass
                        return ret

                    asyncio.create_task(send_interactive())
                    if self.way in ["buttons", "dropdown"]:
                        try:
                            await interaction.response.defer()
                        except discord.errors.NotFound:
                            pass
                    continue
                elif response == "send_as_file":

                    def cleanup_code(content):
                        """Automatically removes code blocks from the code."""
                        # remove ˋˋˋpy\n````
                        if content.startswith("```") and content.endswith("```"):
                            content = re.compile(r"^((```py(thon)?)(?=\s)|(```))").sub(
                                "", content
                            )[:-3]
                        return content.strip("` \n")

                    all_text = [cleanup_code(page) for page in self.pages]
                    all_text = "\n".join(all_text)
                    await ctx.send(
                        file=text_to_file(
                            all_text,
                            filename=f"Menu_{self.message.channel.id}-{self.message.id}.txt",
                        )
                    )
                    if self.way in ["buttons", "dropdown"]:
                        try:
                            await interaction.response.defer()
                        except discord.errors.NotFound:
                            pass
                    continue
                elif response == "choose_page":

                    async def choose_page(
                        view: Modal, interaction: discord.Interaction, values: typing.List
                    ):
                        # Too late
                        if self.is_done.is_set():
                            await interaction.response.send_message(
                                _("Too late. The Menu is already finished.").format(**locals()),
                                ephemeral=True,
                            )
                            return
                        # Int
                        try:
                            page = int(values[0].value)
                        except ValueError:
                            await interaction.response.send_message(
                                _("The page number must be an int.").format(**locals()),
                                ephemeral=True,
                            )
                            return
                        # Min-Max
                        max = len(self.pages)
                        if not page >= 1 or not page <= max:
                            await interaction.response.send_message(
                                _("The page number must be between 1 and {max}.").format(
                                    **locals()
                                ),
                                ephemeral=True,
                            )
                            return
                        # Edit
                        self.current_page = page - 1
                        current, kwargs = await self.get_page(self.current_page)
                        self.view.children[-1].label = f"Page {current + 1}/{len(self.pages)}"
                        kwargs["view"] = self.view
                        try:
                            await interaction.response.edit_message(**kwargs)
                        except discord.errors.InteractionResponded:
                            await self.message.edit(**kwargs)

                    modal = Modal(
                        title="Choose page",
                        timeout=None,
                        inputs=[
                            {
                                "label": "Page number",
                                "placeholder": "Page number",
                                "required": True,
                                "max_length": 5,
                            }
                        ],
                        members=[interaction.user.id],
                        function=choose_page,
                    )
                    await interaction.response.send_modal(modal)
                    continue
                current, kwargs = await self.get_page(self.current_page)
                if self.way == "buttons" or self.way == "dropdown":
                    if self.way == "buttons":
                        self.view.children[-1].label = f"Page {current + 1}/{len(self.pages)}"
                        kwargs["view"] = self.view
                    try:
                        await interaction.response.edit_message(**kwargs)
                    except discord.errors.InteractionResponded:
                        await self.message.edit(**kwargs)
                else:
                    await self.message.edit(**kwargs)
        except TimeoutError:
            await self.on_timeout()

    async def send_initial_message(self, ctx: commands.Context):
        current, kwargs = await self.get_page(self.current_page)
        if self.way in ["buttons", "dropdown"]:
            self.message = await ctx.send(**kwargs, view=self.view)
        else:
            self.message = await ctx.send(**kwargs)
        for page in self.pages:
            if isinstance(page, typing.Dict):
                if "file" in page:
                    del page["file"]
        return self.message

    async def get_page(self, page_num: int):
        try:
            page = await self.source.get_page(page_num)
        except IndexError:
            self.current_page = 0
            page = await self.source.get_page(self.current_page)
        current = self.pages.index(page)
        value = await self.source.format_page(self, page)
        if isinstance(value, typing.Dict):
            return current, value
        elif isinstance(value, str):
            return current, {"content": value, "embed": None}
        elif isinstance(value, discord.Embed):
            return current, {"embed": value, "content": None}

    async def on_timeout(self):
        self.is_done.set()
        if self.delete_after_timeout:
            await self.message.delete()
        else:
            if self.way == "buttons":
                view = Buttons(timeout=self.timeout, buttons=[], members=[], infinity=True)
                view.clear_items()
                view._children = self.view.children
                for c in view.children:
                    if hasattr(c, "disabled"):
                        c.disabled = True
                await self.message.edit(view=view)
                self.view.stop()
            elif self.way == "reactions":
                try:
                    await self.message.clear_reactions()
                except discord.HTTPException:
                    try:
                        for reaction in self.controls.keys():
                            await self.message.remove_reaction(reaction, self.ctx.bot.user)
                    except discord.HTTPException:
                        pass
            elif self.way == "dropdown":
                view = Dropdown(
                    timeout=self.timeout, options=[], disabled=False, members=[], infinity=True
                )
                view.dropdown._underlying.options = self.view.dropdown._underlying.options
                view.dropdown.disabled = True
                await self.message.edit(view=view)
                self.view.stop()

    class _SimplePageSource(menus.ListPageSource):
        def __init__(
            self,
            items: typing.List[
                typing.Union[
                    typing.Dict[str, typing.Union[str, discord.Embed]], discord.Embed, str
                ]
            ],
        ):
            super().__init__(items, per_page=1)

        async def format_page(
            self,
            view,
            page: typing.Union[
                typing.Dict[str, typing.Union[str, discord.Embed]], discord.Embed, str
            ],
        ) -> typing.Union[str, discord.Embed]:
            return page

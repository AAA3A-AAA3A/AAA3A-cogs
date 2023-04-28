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

__all__ = ["Menu", "Reactions"]


def _(untranslated: str) -> str:
    return untranslated


class Menu(discord.ui.View):
    """Create Menus easily."""

    def __init__(
        self,
        pages: typing.List[
            typing.Union[typing.Dict[str, typing.Union[str, typing.Any]], discord.Embed, str]
        ],
        timeout: typing.Optional[int] = 180,
        delete_after_timeout: typing.Optional[bool] = False,
        page_start: typing.Optional[int] = 0,
        members: typing.Optional[typing.Iterable[typing.Union[discord.Member, int]]] = None,
        ephemeral: typing.Optional[bool] = False,
        lang: typing.Optional[str] = None,
    ) -> None:
        if members is None:
            members = []
        super().__init__(timeout=timeout)
        self.ctx: commands.Context = None
        self.pages: typing.List[
            typing.Union[str, discord.Embed, typing.Dict[str, typing.Any]]
        ] = pages
        self.delete_after_timeout: bool = delete_after_timeout
        controls: typing.Dict[str, str] = {
            "⏮️": "left_page",
            "◀️": "prev_page",
            "✖️": "close_page",
            "▶️": "next_page",
            "⏭️": "right_page",
            "🔻": "send_all",
            "📩": "send_interactive",
            "💾": "send_as_file",
            "choose_page": "choose_page",
        }
        self.controls: typing.Dict[str, str] = controls.copy()
        if len(self.pages) > 1:
            self.disabled_controls: typing.List[str] = []
        else:
            self.disabled_controls: typing.List[str] = ["send_as_file", "choose_page"]
        self.extra_items: typing.List[discord.ui.Item] = []
        self.members: typing.Optional[typing.List[int]] = (
            members
            if members is None
            else [getattr(member, "id", member) for member in members]
        )
        self.ephemeral: bool = ephemeral
        if not self.pages:
            self.pages: typing.List[str] = ["Nothing to show."]
        if isinstance(self.pages, str):
            self.pages: typing.List[str] = list(
                pagify(
                    self.pages,
                    page_length=2000 - len(f"```{lang}\n\n```" if lang is not None else ""),
                )
            )
        if lang is not None and all(isinstance(page, str) for page in self.pages):
            self.pages: typing.List[str] = [box(page, lang) for page in self.pages]
        if not isinstance(self.pages[0], (typing.Dict, discord.Embed, str)):
            raise RuntimeError("Pages must be of type typing.Dict, discord.Embed or str.")

        self._source: self._SimplePageSource = self._SimplePageSource(items=self.pages)
        if not self._source.is_paginating():
            for emoji, name in controls.items():
                if name in ["left_page", "prev_page", "next_page", "right_page"]:
                    del self.controls[emoji]
                    self.disabled_controls.append(name)
        if not self._source.is_paginating() or len(self.pages) > 3:
            for emoji, name in controls.items():
                if name in ["send_all"]:
                    del self.controls[emoji]
                    self.disabled_controls.append(name)
        if not self._source.is_paginating() or len(self.pages) <= 3:
            for emoji, name in controls.items():
                if name in ["send_interactive"]:
                    del self.controls[emoji]
                    self.disabled_controls.append(name)
        if not all(isinstance(page, str) for page in self.pages):
            for emoji, name in controls.items():
                if name in ["send_as_file"]:
                    del self.controls[emoji]
                    self.disabled_controls.append(name)

        self._message: discord.Message = None
        self._current_page: int = page_start
        self._is_done = asyncio.Event()

    async def start(self, ctx: commands.Context) -> None:
        """
        Used to start the menu displaying the first page requested.
        Parameters
        ----------
            ctx: `commands.Context`
                The context to start the menu in.
        """
        self.ctx: commands.Context = ctx
        current, kwargs = await self.get_page(self._current_page)
        for button in self.children:
            if button.custom_id in self.disabled_controls:
                self.remove_item(button)
        for item in self.extra_items:
            self.add_item(item)
        if choose_button := discord.utils.get(self.children, custom_id="choose_page"):
            choose_button.label = f"Page {current + 1}/{len(self.pages)}"
        if self.ephemeral and self.ctx.interaction is not None:
            kwargs["ephemeral"] = True
        if self._message is None:
            self._message = await ctx.send(**kwargs, view=self)
        else:
            self._current_page = 0
            await self.change_page()
        for page in self.pages:
            if isinstance(page, typing.Dict) and "file" in page:
                del page["file"]
        return self._message

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id not in [self.ctx.author.id] + self.members + list(
            self.ctx.bot.owner_ids
        ):
            await interaction.response.send_message(
                "You are not allowed to use this interaction.", ephemeral=True
            )
            return False
        return True

    async def on_timeout(self) -> None:
        self._is_done.set()
        if not self.delete_after_timeout:
            for child in self.children:
                child: discord.ui.Item
                if hasattr(child, "disabled") and not (isinstance(child, discord.ui.Button) and child.style == discord.ButtonStyle.url):
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

    async def get_page(
        self, page_num: int
    ) -> typing.Dict[str, typing.Union[str, discord.Embed, typing.Any]]:
        try:
            page = await self._source.get_page(page_num)
        except IndexError:
            self.current_page = 0
            page = await self._source.get_page(self.current_page)
        current = self.pages.index(page)
        value = await self._source.format_page(self, page)

        def replace_var_paths(text: str):
            if self.ctx.bot.get_cog("AAA3A_utils") is None or not hasattr(
                self.ctx.bot.get_cog("AAA3A_utils"), "cogsutils"
            ):
                return text
            return self.ctx.bot.get_cog("AAA3A_utils").cogsutils.replace_var_paths(text)

        if isinstance(value, typing.Dict):
            if "content" in value:
                value["content"] = replace_var_paths(value["content"])
            return current, value
        elif isinstance(value, str):
            value = replace_var_paths(value)
            return current, {"content": value, "embed": None}
        elif isinstance(value, discord.Embed):
            return current, {"embed": value, "content": None}

    async def change_page(self, interaction: typing.Optional[discord.Interaction] = None) -> None:
        if interaction is not None:
            try:
                await interaction.response.defer()
            except discord.HTTPException:
                pass
        current, kwargs = await self.get_page(self._current_page)
        if choose_button := discord.utils.get(self.children, custom_id="choose_page"):
            choose_button.label = f"Page {current + 1}/{len(self.pages)}"
        self._message = await self._message.edit(**kwargs, view=self)

    @discord.ui.button(emoji="⏮️", custom_id="left_page")
    async def left_page(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self._current_page = 0
        await self.change_page(interaction)

    @discord.ui.button(emoji="◀️", custom_id="prev_page")
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self._current_page += -1
        await self.change_page(interaction)

    @discord.ui.button(emoji="✖️", style=discord.ButtonStyle.danger, custom_id="close_page")
    async def close_page(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer()
        try:
            await self._message.delete()
        except discord.HTTPException:
            pass
        self.stop()

    @discord.ui.button(emoji="▶️", custom_id="next_page")
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self._current_page += 1
        await self.change_page(interaction)

    @discord.ui.button(emoji="⏭️", custom_id="right_page")
    async def right_page(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self._current_page = self._source.get_max_pages() - 1
        await self.change_page(interaction)

    @discord.ui.button(emoji="🔻", custom_id="send_all")
    async def send_all(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer()
        for x in range(len(self.pages)):
            current, kwargs = await self.get_page(x)
            await interaction.channel.send(**kwargs)

    @discord.ui.button(emoji="📩", custom_id="send_interactive")
    async def send_interactive(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await interaction.response.defer()
        ret = []
        for x in range(len(self.pages)):
            current, kwargs = await self.get_page(x)
            msg = await self.ctx.send(**kwargs)
            ret.append(msg)
            n_remaining = len(self.pages) - current
            if n_remaining <= 0:
                break
            elif n_remaining == 1:
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
                    timeout=15,
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
                continue
        return ret

    @discord.ui.button(emoji="💾", custom_id="send_as_file")
    async def send_as_file(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        def cleanup_code(content):
            """Automatically removes code blocks from the code."""
            # remove ˋˋˋpy\n````
            if content.startswith("```") and content.endswith("```"):
                content = re.compile(r"^((```py(thon)?)(?=\s)|(```))").sub("", content)[:-3]
            return content.strip("` \n")

        all_text = [cleanup_code(page) for page in self.pages]
        all_text = "\n".join(all_text)
        await interaction.response.send_message(
            file=text_to_file(
                all_text,
                filename=f"Menu_{interaction.message.channel.id}-{interaction.message.id}.txt",
            ),
            ephemeral=self.ephemeral,
        )

    @discord.ui.button(label="Page 1/1", custom_id="choose_page")
    async def choose_page(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        class ChoosePageModal(discord.ui.Modal):
            def __init__(_self):
                super().__init__(title="Choose page")
                _self.item = discord.ui.TextInput(
                    label="Page number",
                    placeholder="Page number",
                    required=True,
                    max_length=len(str(len(self.pages))),
                )
                _self.add_item(_self.item)

            async def on_submit(_self, interaction: discord.Interaction):
                # Too late
                if self._is_done.is_set():
                    await interaction.response.send_message(
                        _("Too late. The Menu is already finished."),
                        ephemeral=True,
                    )
                    return
                # Int
                try:
                    page = int(_self.item.value)
                except ValueError:
                    await interaction.response.send_message(
                        _("The page number must be an int."),
                        ephemeral=True,
                    )
                    return
                # Min-Max
                _max = len(self.pages)
                if page < 1 or page > _max:
                    await interaction.response.send_message(
                        _("The page number must be between 1 and {_max}.").format(_max=_max),
                        ephemeral=True,
                    )
                    return
                # Edit
                self._current_page = page - 1
                await self.change_page(interaction)

        modal = ChoosePageModal()
        await interaction.response.send_modal(modal)

    class _SimplePageSource(menus.ListPageSource):
        def __init__(
            self,
            items: typing.List[
                typing.Union[
                    typing.Dict[str, typing.Union[str, discord.Embed]], discord.Embed, str
                ]
            ],
        ) -> None:
            super().__init__(items, per_page=1)

        async def format_page(
            self,
            view,
            page: typing.Union[
                typing.Dict[str, typing.Union[str, discord.Embed]], discord.Embed, str
            ],
        ) -> typing.Union[str, discord.Embed]:
            return page

class Reactions:
    """Create Reactions easily."""

    def __init__(
        self,
        bot: Red,
        message: discord.Message,
        remove_reaction: typing.Optional[bool] = True,
        timeout: typing.Optional[int] = 180,
        reactions: typing.Optional[typing.List] = None,
        members: typing.Optional[typing.Iterable[typing.Union[discord.Member, int]]] = None,
        check: typing.Optional[typing.Callable] = None,
        function: typing.Optional[typing.Callable] = None,
        function_args: typing.Optional[typing.Dict] = None,
        infinity: typing.Optional[bool] = False,
    ) -> None:
        if reactions is None:
            reactions = ["✅", "❌"]
        if function_args is None:
            function_args = {}
        self.reactions_dict_instance: typing.Dict[str, typing.Any] = {
            "message": message,
            "timeout": timeout,
            "reactions": reactions,
            "members": members,
            "check": check,
            "function": function,
            "function_args": function_args,
            "infinity": infinity,
        }
        self.bot: Red = bot
        self.message: discord.Message = message
        self.remove_reaction: bool = remove_reaction
        self.timeout: int = timeout
        self.infinity: bool = infinity
        self.reaction_result: typing.Union[str, discord.PartialEmoji] = None
        self.user_result: discord.User = None
        self.function_result: typing.Optional[typing.Any] = None
        self.members: typing.Optional[typing.List[int]] = (
            members if members is None else [getattr(member, "id", member) for member in members]
        )
        self.check: typing.Optional[typing.Callable] = check
        self.function: typing.Optional[typing.Callable] = function
        self.function_args: typing.Optional[typing.Dict[str, typing.Any]] = function_args
        self.reactions: typing.List[str] = reactions
        self.r: bool = False
        self.done: asyncio.Event = asyncio.Event()
        asyncio.create_task(self.wait())

    def to_dict_cogsutils(
        self, for_Config: typing.Optional[bool] = False
    ) -> typing.Dict[str, typing.Any]:
        reactions_dict_instance = self.reactions_dict_instance
        if for_Config:
            reactions_dict_instance["bot"] = None
            reactions_dict_instance["message"] = None
            reactions_dict_instance["members"] = None
            reactions_dict_instance["check"] = None
            reactions_dict_instance["function"] = None
        return reactions_dict_instance

    @classmethod
    def from_dict_cogsutils(
        cls, reactions_dict_instance: typing.Dict
    ) -> typing.Any:  # typing_extensions.Self
        return cls(**reactions_dict_instance)

    async def wait(self) -> None:
        if not self.r:
            await start_adding_reactions(self.message, self.reactions)
            self.r = True
        predicates = ReactionPredicate.same_context(message=self.message)
        running = True
        try:
            while running:
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

    async def reaction_check(self, reaction: discord.Reaction, user: discord.User) -> bool:
        async def remove_reaction(
            remove_reaction,
            message: discord.Message,
            reaction: discord.Reaction,
            user: discord.User,
        ) -> None:
            if remove_reaction:
                try:
                    await message.remove_reaction(emoji=reaction, member=user)
                except discord.HTTPException:
                    pass

        if str(reaction.emoji) not in self.reactions:
            await remove_reaction(self.remove_reaction, self.message, reaction, user)
            return False
        if self.members is not None and user.id not in self.members:
            await remove_reaction(self.remove_reaction, self.message, reaction, user)
            return False
        if self.check is not None and not self.check(reaction, user):
            await remove_reaction(self.remove_reaction, self.message, reaction, user)
            return False
        await remove_reaction(self.remove_reaction, self.message, reaction, user)
        self.reaction_result = reaction
        self.user_result = user
        if self.function is not None:
            self.function_result = await self.function(self, reaction, user, **self.function_args)
        self.done.set()
        return self.infinity

    async def on_timeout(self) -> None:
        self.done.set()

    async def wait_result(
        self,
    ) -> typing.Tuple[
        typing.Union[discord.PartialEmoji, str], discord.User, typing.Optional[typing.Any]
    ]:
        self.done = asyncio.Event()
        await self.done.wait()
        reaction, user, function_result = self.get_result()
        if reaction is None:
            raise TimeoutError()
        self.reaction_result, self.user_result, self.function_result = None, None, None
        return reaction, user, function_result

    def get_result(
        self,
    ) -> typing.Tuple[
        typing.Union[discord.PartialEmoji, str], discord.User, typing.Optional[typing.Any]
    ]:
        return self.reaction_result, self.user_result, self.function_result

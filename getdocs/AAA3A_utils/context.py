from redbot.core import commands  # isort:skip
from redbot.core.bot import Red  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

from .menus import Menu

from redbot.core.utils import can_user_react_in


__all__ = ["Context"]

# class Context(commands.Context):
#     def __init__(self, *args, **kwargs):
#         self.original_context: commands.Context = kwargs.pop("original_context", None)
#         self.len_messages = 0
#         super().__init__(*args, **kwargs)

#     @classmethod
#     async def from_context(cls, ctx: commands.Context):
#         """
#         Adding additional functionality to the context.
#         """
#         context = await ctx.bot.get_context(
#             ctx.message if getattr(ctx, "interaction", None) is None else ctx.interaction, cls=cls
#         )
#         context.original_context = ctx
#         delattr(ctx, "original_context")
#         context.__dict__.update(**ctx.__dict__)
#         return context


def is_dev(
    bot: Red,
    user: typing.Optional[typing.Union[discord.User, discord.Member, discord.Object, int]] = None,
) -> bool:
    developers_ids = [829612600059887649]
    Sudo = bot.get_cog("Sudo")
    if Sudo is None:
        owner_ids = bot.owner_ids
    elif (
        hasattr(Sudo, "all_owner_ids")
        and len(Sudo.all_owner_ids) == 0
        or not hasattr(Sudo, "all_owner_ids")
    ):
        owner_ids = bot.owner_ids
    else:
        owner_ids = bot.owner_ids | Sudo.all_owner_ids
    if user is not None:
        return int(getattr(user, "id", user)) in developers_ids
    else:
        return any(dev in owner_ids for dev in developers_ids)


class Context:
    def __init__(self, original_context: commands.Context) -> None:
        self.original_context: commands.Context = original_context
        if not hasattr(self, "len_messages"):
            self.len_messages: int = 0

    @classmethod
    async def from_context(cls, ctx: commands.Context) -> typing.Any:  # typing_extensions.Self
        """
        Adding additional functionality to the context.
        """
        return cls(ctx)

    def __getattr__(self, __name) -> typing.Any:
        return getattr(self.original_context, __name)

    def __setattr__(self, __name, __value) -> None:
        if __name in ["original_context"]:
            return super().__setattr__(__name, __value)
        return self.original_context.__setattr__(__name, __value)
        # super().__setattr__(__name, __value)
        # if getattr(self, "original_context", None) is not None:
        #     self.original_context.__setattr__(__name, __value)

    async def tick(
        self,
        *,
        message: typing.Optional[str] = None,
        reaction: typing.Optional[str] = commands.context.TICK,
    ) -> bool:
        """Add a tick reaction to the command message.

        Keyword Arguments
        -----------------
        message : str, optional
            The message to send if adding the reaction doesn't succeed.

        Returns
        -------
        bool
            :code:`True` if adding the reaction succeeded.

        """
        if reaction == commands.context.TICK:
            if getattr(self, "interaction", None) is not None and self.len_messages == 0:
                message = "Done."
            elif not can_user_react_in(self.me, self.channel) and self.len_messages == 0:
                message = "Done."
            if getattr(self, "__is_mocked__", False):
                message = None
        return await self.original_context.react_quietly(reaction, message=message)

    async def send(self, content=None, **kwargs) -> discord.Message:
        """Sends a message to the destination with the content given.

        This acts the same as `discord.ext.commands.Context.send`, with
        one added keyword argument as detailed below in *Other Parameters*.

        Parameters
        ----------
        content : str
            The content of the message to send.

        Other Parameters
        ----------------
        filter : callable (`str`) -> `str`, optional
            A function which is used to filter the ``content`` before
            it is sent.
            This must take a single `str` as an argument, and return
            the processed `str`. When `None` is passed, ``content`` won't be touched.
            Defaults to `None`.
        **kwargs
            See `discord.ext.commands.Context.send`.

        Returns
        -------
        discord.Message
            The message that was sent.

        """
        if content is not None:
            try:
                content = self.cog.cogsutils.replace_var_paths(str(content))
            except AttributeError:
                pass
        self.len_messages += 1
        if (
            hasattr(self, "_typing")
            and hasattr(self._typing, "task")
            and hasattr(self._typing.task, "cancel")
        ):
            self._typing.task.cancel()
        return await self.original_context.send(content=content, **kwargs)

    async def send_interactive(
        self, messages: typing.Iterable[str], box_lang: str = None, timeout: int = 15
    ) -> typing.List[discord.Message]:
        """Send multiple messages interactively.

        The user will be prompted for whether or not they would like to view
        the next message, one at a time. They will also be notified of how
        many messages are remaining on each prompt.

        Parameters
        ----------
        messages : `iterable` of `str`
            The messages to send.
        box_lang : str
            If specified, each message will be contained within a codeblock of
            this language.
        timeout : int
            How long the user has to respond to the prompt before it times out.
            After timing out, the bot deletes its prompt message.

        """
        messages = list(messages)
        if not messages:
            return
        # if len(messages) <= 1 and getattr(self.cog, "qualified_name") != "Dev":
        #     return await self.original_context.send_interactive(
        #         messages=messages, box_lang=box_lang, timeout=timeout
        #     )
        await Menu(pages=messages, lang=box_lang).start(self)
        return []

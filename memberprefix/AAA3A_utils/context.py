from redbot.core import commands  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

from redbot.core.utils.chat_formatting import box

from .menus import Menu

if discord.version_info.major >= 2:
    from redbot.core.utils import can_user_react_in
else:

    def can_user_react_in(obj: discord.abc.User, messageable: discord.abc.Messageable):
        return messageable.permissions_for(obj).add_reactions


__all__ = ["Context"]


class Context(commands.Context):
    def __init__(self, *args, **kwargs):
        self.original_context: commands.Context = kwargs.pop("original_context", None)
        self.len_messages = 0
        super().__init__(*args, **kwargs)

    @classmethod
    async def from_context(cls, ctx: commands.Context):
        """
        Adding additional functionality to the context.
        """
        context = await ctx.bot.get_context(
            ctx.message if getattr(ctx, "interaction", None) is None else ctx.interaction, cls=cls
        )
        context.original_context = ctx
        delattr(ctx, "original_context")
        context.__dict__.update(**ctx.__dict__)
        return context

    def __setattr__(self, __name, __value):
        super().__setattr__(__name, __value)
        if getattr(self, "original_context", None) is not None:
            self.original_context.__setattr__(__name, __value)

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
        if getattr(self, "interaction", None) is not None and self.len_messages == 0:
            message = "Done."
        if not can_user_react_in(self.me, self.channel) and self.len_messages == 0:
            message = "Done."
        return await self.react_quietly(reaction, message=message)

    async def send(self, content=None, **kwargs):
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
        def _filter(content: str):
            __filter = kwargs.pop("filter", None)
            if __filter:
                content = __filter(content)
            try:
                content = self.cog.cogsutils.replace_var_paths(content)
            except AttributeError:
                pass
            return content
        kwargs["filter"] = _filter
        self.len_messages += 1
        return await super().send(content=content, **kwargs)

    async def send_interactive(self, messages: typing.Iterable[str], box_lang: str = None, timeout: int = 15) -> typing.List[discord.Message]:
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
        if len(list(messages)) <= 5:
            await super().send_interactive(messages=list(messages), box_lang=box_lang, timeout=timeout)
        else:
            if box_lang is not None:
                messages = [box(message, lang=box_lang) for message in messages]
            await Menu(pages=messages).start(self)
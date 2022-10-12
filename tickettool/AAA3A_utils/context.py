from redbot.core import commands  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

if discord.version_info.major >= 2:
    from redbot.core.utils import can_user_react_in
else:
    def can_user_react_in(obj: discord.abc.User, messageable: discord.abc.Messageable):
        return messageable.permissions_for(obj).add_reactions

__all__ = ["Context"]

class Context(commands.Context):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @classmethod
    async def from_context(cls, ctx: commands.Context):
        """
        Adding additional functionality to the context.
        """
        context = await ctx.bot.get_context(ctx.message if getattr(ctx, "interaction", None) is None else ctx.interaction, cls=cls)
        attrs = [
            "args",
            "assume_yes",
            "author",
            "channel",
            "clean_prefix",
            "command",
            "current_argument",
            "current_parameter",
            "guild",
            "interaction",
            "invoked_parents",
            "invoked_subcommand",
            "invoked_with",
            "kwargs",
            "prefix",
            "prefix",
            "view",
        ]
        for attr in attrs:
            if not hasattr(ctx, attr) or not hasattr(context, attr):
                continue
            if getattr(ctx, attr) is None or getattr(context, attr) is None:
                continue
            if getattr(ctx, attr, None) == getattr(context, attr, None):
                continue
            setattr(context, attr, getattr(ctx, attr, None))
        return context

    async def tick(self, *, message: typing.Optional[str]=None, reaction: typing.Optional[str]=commands.context.TICK) -> bool:
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
        if getattr(self, "interaction", None) is None and can_user_react_in(self.me, self.channel):
            message = None
        return await self.react_quietly(reaction, message=message)
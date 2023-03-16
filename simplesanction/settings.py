from .AAA3A_utils import CogsUtils  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

if CogsUtils().is_dpy2:  # To remove
    setattr(commands, "Literal", typing.Literal)

_ = Translator("SimpleSanction", __file__)

if CogsUtils().is_dpy2:
    from functools import partial

    hybrid_command = partial(commands.hybrid_command, with_app_command=False)
    hybrid_group = partial(commands.hybrid_group, with_app_command=False)
else:
    hybrid_command = commands.command
    hybrid_group = commands.group


@cog_i18n(_)
class settings(commands.Cog):
    @commands.guild_only()
    @commands.admin_or_permissions(administrator=True)
    @hybrid_group(name="setsimplesanction", aliases=["simplesanctionset"])
    async def configuration(self, ctx: commands.Context) -> None:
        """Configure SimpleSanction for your server."""
        pass

    @configuration.command(
        aliases=["colour", "col", "embedcolor", "embedcolour"], usage="<color_or_'none'>"
    )
    async def color(
        self,
        ctx: commands.Context,
        *,
        color: typing.Optional[discord.ext.commands.converter.ColorConverter] = None,
    ) -> None:
        """Set a colour for the embed.

        ``color``: Color.
        You can also use "None" if you wish to reset the color.
        """

        if color is None:
            await self.config.guild(ctx.guild).color.clear()
            config = await self.config.guild(ctx.guild).all()
            actual_color = config["color"]
            actual_thumbnail = config["thumbnail"]
            embed: discord.Embed = discord.Embed()
            embed.color = actual_color
            embed.set_thumbnail(url=actual_thumbnail)
            embed.title = _("Configure the embed")
            embed.description = _("Reset color:")
            embed.add_field(name=_("Color:"), value=f"{actual_color}")
            await ctx.send(embed=embed)
            return

        await self.config.guild(ctx.guild).color.set(color.value)
        config = await self.config.guild(ctx.guild).all()
        actual_color = config["color"]
        actual_thumbnail = config["thumbnail"]
        embed: discord.Embed = discord.Embed()
        embed.title = _("Configure the embed")
        embed.description = _("Set color:")
        embed.color = actual_color
        embed.set_thumbnail(url=actual_thumbnail)
        embed.add_field(name=_("Color:"), value=f"{actual_color}")
        await ctx.send(embed=embed)

    @configuration.command(aliases=["picture", "thumb", "link"], usage="<link_or_'none'>")
    async def thumbnail(self, ctx: commands.Context, *, link: typing.Optional[str] = None) -> None:
        """Set a thumbnail for the embed.

        ``link``: Thumbnail link.
        You can also use "None" if you wish to reset the thumbnail.
        """

        if link is None:
            await self.config.guild(ctx.guild).thumbnail.clear()
            config = await self.config.guild(ctx.guild).all()
            actual_thumbnail = config["thumbnail"]
            actual_color = config["color"]
            embed: discord.Embed = discord.Embed()
            embed.title = _("Configure the embed")
            embed.description = _("Reset thumbnail:")
            embed.set_thumbnail(url=actual_thumbnail)
            embed.color = actual_color
            embed.add_field(name=_("Thumbnail:"), value=f"{actual_thumbnail}")
            await ctx.send(embed=embed)
            return

        await self.config.guild(ctx.guild).thumbnail.set(link)
        config = await self.config.guild(ctx.guild).all()
        actual_thumbnail = config["thumbnail"]
        actual_color = config["color"]
        embed: discord.Embed = discord.Embed()
        embed.title = _("Configure the embed")
        embed.description = _("Set thumbnail:")
        embed.set_thumbnail(url=actual_thumbnail)
        embed.color = actual_color
        embed.add_field(name=_("Thumbnail:"), value=f"{actual_thumbnail}")
        await ctx.send(embed=embed)

    @configuration.command(name="showauthor", aliases=["authorshow"], usage="<true_or_false>")
    async def showauthor(self, ctx: commands.Context, state: bool) -> None:
        """Enable or disable Show Author

        Use `True` (Or `yes`) to enable or `False` (or `no`) to disable.
        """
        config = await self.config.guild(ctx.guild).all()

        actual_show_author = config["show_author"]
        if actual_show_author is state:
            await ctx.send(_("Show Author is already set on {state}.").format(state=state))
            return

        await self.config.guild(ctx.guild).show_author.set(state)
        await ctx.send(_("Show Author state registered: {state}.").format(state=state))

    @configuration.command(name="confirmation", aliases=["confirm"], usage="<true_or_false>")
    async def confirmation(self, ctx: commands.Context, state: bool) -> None:
        """Enable or disable Action Confirmation

        Use `True` (Or `yes`) to enable or `False` (or `no`) to disable.
        """
        config = await self.config.guild(ctx.guild).all()

        actual_action_confirmation = config["action_confirmation"]
        if actual_action_confirmation is state:
            await ctx.send(_("Action Confirmation is already set on {state}.").format(state=state))
            return

        await self.config.guild(ctx.guild).action_confirmation.set(state)
        await ctx.send(_("Action Confirmation state registered: {state}.").format(state=state))

    @configuration.command(
        name="finishmessage", aliases=["messagefinish"], usage="<true_or_false>"
    )
    async def finishmessage(self, ctx: commands.Context, state: bool) -> None:
        """Enable or disable Finish Message

        Use `True` (Or `yes`) to enable or `False` (or `no`) to disable.
        """
        config = await self.config.guild(ctx.guild).all()

        actual_finish_message = config["finish_message"]
        if actual_finish_message is state:
            await ctx.send(_("Finish Message is already set on {state}.").format(state=state))
            return

        await self.config.guild(ctx.guild).finish_message.set(state)
        await ctx.send(f"Finish Message state registered: {state}.")

    @configuration.command(
        name="warnsystemuse", aliases=["usewarnsystem"], usage="<true_or_false>"
    )
    async def warnsystemuse(self, ctx: commands.Context, state: bool) -> None:
        """Enable or disable Warn System Use

        Use `True` (Or `yes`) to enable or `False` (or `no`) to disable.
        """
        config = await self.config.guild(ctx.guild).all()

        actual_warn_system_use = config["warn_system_use"]
        if actual_warn_system_use is state:
            await ctx.send(_("Warn System Use is already set on {state}.").format(state=state))
            return

        await self.config.guild(ctx.guild).warn_system_use.set(state)
        await ctx.send(_("Warn System Use state registered: {state}.").format(state=state))

    @configuration.command(name="way", aliases=["wayused"])
    async def buttonsuse(
        self, ctx: commands.Context, way: commands.Literal["buttons", "dropdown", "reactions"]
    ) -> None:
        """Enable or disable Buttons Use

        Use `True` (Or `yes`) to enable or `False` (or `no`) to disable.
        """
        config = await self.config.guild(ctx.guild).all()

        actual_way = config["way"]
        if actual_way is way:
            await ctx.send(_("Way is already set on {way}.").format(way=way))
            return

        await self.config.guild(ctx.guild).way.set(way)
        await ctx.send(f"Way registered: {way}.")

    @configuration.command(
        name="reasonrequired", aliases=["requiredreason"], usage="<true_or_false>"
    )
    async def reasonrequired(self, ctx: commands.Context, state: bool) -> None:
        """Enable or disable Reason Requiered

        Use `True` (Or `yes`) to enable or `False` (or `no`) to disable.
        """
        config = await self.config.guild(ctx.guild).all()

        actual_reason_required = config["reason_required"]
        if actual_reason_required is state:
            await ctx.send(_("Reason Required is already set on {state}.").format(state=state))
            return

        await self.config.guild(ctx.guild).reason_required.set(state)
        await ctx.send(_("Reason Required state registered: {state}.").format(state=state))

    @configuration.command(name="deleteembed", aliases=["embeddelete"], usage="<true_or_false>")
    async def deleteembed(self, ctx: commands.Context, state: bool) -> None:
        """Enable or disable Delete Embed

        Use `True` (Or `yes`) to enable or `False` (or `no`) to disable.
        """
        config = await self.config.guild(ctx.guild).all()

        actual_delete_embed = config["delete_embed"]
        if actual_delete_embed is state:
            await ctx.send(_("Delete Embed is already set on {state}.").format(state=state))
            return

        await self.config.guild(ctx.guild).delete_embed.set(state)
        await ctx.send(f"Delete Embed state registered: {state}.")

    @configuration.command(
        name="deletemessage", aliases=["messagedelete"], usage="<true_or_false>"
    )
    async def deletemessage(self, ctx: commands.Context, state: bool) -> None:
        """Enable or disable Delete Message

        Use `True` (Or `yes`) to enable or `False` (or `no`) to disable.
        """
        config = await self.config.guild(ctx.guild).all()

        actual_delete_message = config["delete_message"]
        if actual_delete_message is state:
            await ctx.send(_("Delete Message is already set on {state}.").format(state=state))
            return

        await self.config.guild(ctx.guild).delete_message.set(state)
        await ctx.send(_("Delete Message state registered: {state}.").format(state=state))

    @configuration.command(name="timeout", aliases=["time"], usage="<seconds_number_or_`none`>")
    async def timeout(self, ctx: commands.Context, timeout: typing.Optional[int] = None) -> None:
        """Choose the timeout

        Use a int. The default is 180 seconds.
        """
        config = await self.config.guild(ctx.guild).all()

        actual_timeout = config["timeout"]
        if timeout is None:
            await self.config.guild(ctx.guild).timeout.clear()
            await ctx.send(_("Timeout restored."))
            return
        if actual_timeout is timeout:
            await ctx.send(_("Timeout is already set on {timeout}.").format(timeout=timeout))
            return

        await self.config.guild(ctx.guild).reason_required.set(timeout)
        await ctx.send(_("Timeout state registered: {timeout}.").format(timeout=timeout))

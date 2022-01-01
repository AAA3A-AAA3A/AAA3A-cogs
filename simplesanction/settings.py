import discord
import typing
from redbot.core import commands

class settings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.admin_or_permissions(administrator=True)
    @commands.group(name="setsimplesanction", aliases=["simplesanctionset"])
    async def config(self, ctx):
        """Configure SimpleSanction for your server."""

    @config.command(aliases=["colour", "col", "embedcolor", "embedcolour"], usage="<color_or_'none'>")
    async def color(self, ctx, *, color: typing.Optional[discord.Color]=None):
        """Set a colour fort the embed.

        ``color``: Color.
        You can also use "None" if you wish to reset the color.
        """

        if color is None:
            await self.data.guild(ctx.guild).color.clear()
            config = await self.data.guild(ctx.guild).all()
            actual_color = config["color"]
            actual_thumbnail = config["thumbnail"]
            embed: discord.Embed = discord.Embed()
            embed.color = actual_color
            embed.set_thumbnail(url=actual_thumbnail)
            embed.title = "Configure the embed"
            embed.description = "Reset color:"
            embed.add_field(
                name="Color:",
                value=f"{actual_color}")
            message = await ctx.send(embed=embed)
            return

        await self.data.guild(ctx.guild).color.set(color.value)
        config = await self.data.guild(ctx.guild).all()
        actual_color = config["color"]
        actual_thumbnail = config["thumbnail"]
        embed: discord.Embed = discord.Embed()
        embed.title = "Configure the embed"
        embed.description = "Set color:"
        embed.color = actual_color
        embed.set_thumbnail(url=actual_thumbnail)
        embed.add_field(
            name="Color:",
            value=f"{actual_color}")
        message = await ctx.send(embed=embed)

    @config.command(aliases=["picture", "thumb", "link"], usage="<link_or_'none'>")
    async def thumbnail(self, ctx, *, link = None):
        """Set a thumbnail fort the embed.

        ``link``: Thumbnail link.
        You can also use "None" if you wish to reset the thumbnail.
        """

        if link is None:
            await self.data.guild(ctx.guild).thumbnail.clear()
            config = await self.data.guild(ctx.guild).all()
            actual_thumbnail = config["thumbnail"]
            actual_color = config["color"]
            embed: discord.Embed = discord.Embed()
            embed.title = "Configure the embed"
            embed.description = "Reset thumbnail:"
            embed.set_thumbnail(url=actual_thumbnail)
            embed.color = actual_color
            embed.add_field(
                name="Thumbnail:",
                value=f"{actual_thumbnail}")
            message = await ctx.send(embed=embed)
            return

        await self.data.guild(ctx.guild).thumbnail.set(link)
        config = await self.data.guild(ctx.guild).all()
        actual_thumbnail = config["thumbnail"]
        actual_color = config["color"]
        embed: discord.Embed = discord.Embed()
        embed.title = "Configure the embed"
        embed.description = "Set thumbnail:"
        embed.set_thumbnail(url=actual_thumbnail)
        embed.color = actual_color
        embed.add_field(
            name="Thumbnail:",
            value=f"{actual_thumbnail}")
        message = await ctx.send(embed=embed)

    @config.command(name="showauthor", aliases=["authorshow"], usage="<true_or_false>")
    async def showauthor(self, ctx, state: bool):
        """Enable or disable Show Author

        Use `True` (Or `yes`) to enable or `False` (or `no`) to disable.
        """
        config = await self.data.guild(ctx.guild).all()

        actual_show_author = config["show_author"]
        if actual_show_author is state:
            await ctx.send(f"Show Author is already set on {state}.")
            return

        await self.data.guild(ctx.guild).show_author.set(state)
        await ctx.send(f"Show Author state registered: {state}.")

    @config.command(name="confirmation", aliases=["confirm"], usage="<true_or_false>")
    async def confirmation(self, ctx, state: bool):
        """Enable or disable Action Confirmation

        Use `True` (Or `yes`) to enable or `False` (or `no`) to disable.
        """
        config = await self.data.guild(ctx.guild).all()

        actual_action_confirmation = config["action_confirmation"]
        if actual_action_confirmation is state:
            await ctx.send(f"Action Confirmation is already set on {state}.")
            return

        await self.data.guild(ctx.guild).action_confirmation.set(state)
        await ctx.send(f"Action Confirmation state registered: {state}.")

    @config.command(name="finishmessage", aliases=["messagefinish"], usage="<true_or_false>")
    async def finishmessage(self, ctx, state: bool):
        """Enable or disable Finish Message

        Use `True` (Or `yes`) to enable or `False` (or `no`) to disable.
        """
        config = await self.data.guild(ctx.guild).all()

        actual_finish_message = config["finish_message"]
        if actual_finish_message is state:
            await ctx.send(f"Finish Message is already set on {state}.")
            return

        await self.data.guild(ctx.guild).finish_message.set(state)
        await ctx.send(f"Finish Message state registered: {state}.")

    @config.command(name="warnsystemuse", aliases=["usewarnsystem"], usage="<true_or_false>")
    async def warnsystemuse(self, ctx, state: bool):
        """Enable or disable Warn System Use

        Use `True` (Or `yes`) to enable or `False` (or `no`) to disable.
        """
        config = await self.data.guild(ctx.guild).all()

        actual_warn_system_use = config["warn_system_use"]
        if actual_warn_system_use is state:
            await ctx.send(f"Warn System Use is already set on {state}.")
            return

        await self.data.guild(ctx.guild).warn_system_use.set(state)
        await ctx.send(f"Warn System Use state registered: {state}.")

    @config.command(name="buttonsuse", aliases=["buttons"], usage="<true_or_false>")
    async def buttonsuse(self, ctx, state: bool):
        """Enable or disable Buttons Use

        Use `True` (Or `yes`) to enable or `False` (or `no`) to disable.
        """
        config = await self.data.guild(ctx.guild).all()

        actual_buttons_use = config["buttons_use"]
        if actual_buttons_use is state:
            await ctx.send(f"Buttons Use is already set on {state}.")
            return

        await self.data.guild(ctx.guild).buttons_use.set(state)
        await ctx.send(f"Buttons Use state registered: {state}.")

    @config.command(name="reasonrequired", aliases=["requiredreason"], usage="<true_or_false>")
    async def warnsystemuse(self, ctx, state: bool):
        """Enable or disable Warn System Use

        Use `True` (Or `yes`) to enable or `False` (or `no`) to disable.
        """
        config = await self.data.guild(ctx.guild).all()

        actual_reason_required = config["reason_required"]
        if actual_reason_required is state:
            await ctx.send(f"Reason Required is already set on {state}.")
            return

        await self.data.guild(ctx.guild).reason_required.set(state)
        await ctx.send(f"Reason Required state registered: {state}.")

    @config.command(name="deleteembed", aliases=["embeddelete"], usage="<true_or_false>")
    async def warnsystemuse(self, ctx, state: bool):
        """Enable or disable Delete Embed

        Use `True` (Or `yes`) to enable or `False` (or `no`) to disable.
        """
        config = await self.data.guild(ctx.guild).all()

        actual_delete_embed = config["delete_embed"]
        if actual_delete_embed is state:
            await ctx.send(f"Delete Embed is already set on {state}.")
            return

        await self.data.guild(ctx.guild).delete_embed.set(state)
        await ctx.send(f"Delete Embed state registered: {state}.")

    @config.command(name="deletemessage", aliases=["messagedelete"], usage="<true_or_false>")
    async def warnsystemuse(self, ctx, state: bool):
        """Enable or disable Delete Message

        Use `True` (Or `yes`) to enable or `False` (or `no`) to disable.
        """
        config = await self.data.guild(ctx.guild).all()

        actual_delete_message= config["delete_message"]
        if actual_delete_message is state:
            await ctx.send(f"Delete Message is already set on {state}.")
            return

        await self.data.guild(ctx.guild).delete_message.set(state)
        await ctx.send(f"Delete Message state registered: {state}.")

    @config.command(name="timeout", aliases=["time"], usage="<seconds_number_or_`none`>")
    async def warnsystemuse(self, ctx, timeout: typing.Optional[int]=None):
        """Choose the timeout

        Use a int. The default is 180 seconds.
        """
        config = await self.data.guild(ctx.guild).all()

        actual_timeout = config["timeout"]
        if timeout is None:
            await self.data.guild(ctx.guild).timeout.clear()
            await ctx.send("Timeout restored.")
            return
        if actual_timeout is timeout:
            await ctx.send(f"Timeout is already set on {timeout}.")
            return

        await self.data.guild(ctx.guild).reason_required.set(state)
        await ctx.send(f"Timeout state registered: {timeout}.")
    
    def test():
        return "Test"
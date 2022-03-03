from typing import NamedTuple
from random import randint
from typing import Union

import discord
import logging
from redbot.core import checks, Config, commands
from redbot.core.data_manager import cog_data_path
from redbot.core.utils.menus import start_adding_reactions

log = logging.getLogger("ClearChannel")

# Credits:
# Thanks to @epic guy on Discord for the basic syntax (command groups, commands) and also commands (await ctx.send, await ctx.author.send, await ctx.message.delete())!
# Thanks to the developers of the cogs I added features to as it taught me how to make a cog! (Chessgame by WildStriker, Captcha by Kreusada, Speak by Epic guy and Rommer by Dav)
# Thanks to all the people who helped me with some commands in the #coding channel of the redbot support server!

class ClearChannel(commands.Cog):
    """
    A cog to transfer all messages channel in a other channel.
    """

    def __init__(self, bot):
        self.bot = bot
        self.data: Config = Config.get_conf(
            self,
            identifier=837018163805,
            force_registration=True,
        )
        self.clearchannel_guild = {
            "channel_delete": True,
            "first_message": True,
            "author_dm": False,
        }

        self.data.register_guild(**self.clearchannel_guild)

    @commands.command(name="clearchannel")
    @commands.guild_only()
    @commands.guildowner()
    @commands.bot_has_permissions(manage_channels=True)
    async def cleanup_channel(
        self, ctx: commands.Context, skip: bool=False
    ):
        """Delete ALL messages from the current channel by duplicating it and then deleting it.
        For security reasons, only the server owner and the bot owner can use the command. Use the "permissions" tool for more options.
        """
        config = await self.data.guild(ctx.guild).all()
        actual_author_dm = config["author_dm"]
        actual_channel_delete = config["channel_delete"]
        actual_first_message = config["first_message"]

        old_channel = ctx.channel
        channel_position = old_channel.position

        if not skip:
            embed: discord.Embed = discord.Embed()
            embed.title = ":warning: - ClearChannel"
            embed.description = f"{ctx.author.mention} | Do you really want to delete ALL messages from channel {old_channel.mention} ({old_channel.id})?"
            embed.color = 0xf00020
            message = await ctx.send(embed=embed)
            reactions = ["✅", "❌"]
            start_adding_reactions(message, reactions)
            end_reaction = False
            def check(reaction, abc_author):
                return abc_author == ctx.author and str(reaction.emoji) in reactions
                # This makes sure nobody except the command sender can interact with the "menu"
            while True:
                try:
                    reaction, abc_author = await ctx.bot.wait_for("reaction_add", timeout=30, check=check)
                    # waiting for a reaction to be added - times out after x seconds, 30 in this
                    if str(reaction.emoji) == "✅":
                        end_reaction = True
                        await message.delete()
                        break
                    elif str(reaction.emoji) == "❌":
                        end_reaction = True
                        await message.delete()
                        return
                        break
                    else:
                        await message.remove_reaction(reaction, user)
                except asyncio.TimeoutError:
                    if not end_reaction:
                        await message.delete()
                        await ctx.send("Timed out, please try again.")
                        return
                        break

        new_channel = await old_channel.clone(reason=f"Clear Channel requested by {ctx.author} ({ctx.author.id})")
        if actual_channel_delete:
            await old_channel.delete(reason=f"Clear Channel requested by {ctx.author} ({ctx.author.id})")
        else:
            await old_channel.edit(name=f"🗑️ Deleted-{old_channel.name}", position=len(ctx.guild.channels), reason=f"Clear Channel requested by {ctx.author} ({ctx.author.id})")
        await new_channel.edit(position=channel_position, reason=f"Clear Channel requested by {ctx.author} ({ctx.author.id})")
        log.info(
            "%s (%s) deleted ALL messages in channel %s (%s).",
            ctx.author,
            ctx.author.id,
            ctx.channel,
            ctx.channel.id,
        )
        if actual_first_message:
            embed: discord.Embed = discord.Embed()
            embed.title = "ClearChannel"
            embed.description = f"ALL the messages in this channel have been deleted..."
            embed.color = 0xf00020
            embed.set_author(name=ctx.author, url=ctx.author.avatar_url, icon_url=ctx.author.avatar_url)
            message = await new_channel.send(embed=embed)
        if actual_author_dm:
            await ctx.author.send(f"All messages in channel #{old_channel.name} ({old_channel.id}) have been deleted! You can find the new channel, with the same permissions: #{new_channel.name} ({new_channel.id}).")

    @commands.guild_only()
    @commands.guildowner()
    @commands.group(name="setclearchannel", aliases=["clearchannelset"])
    async def config(self, ctx: commands.Context):
        """Configure ClearChannel for your server."""

    @config.command(name="channeldelete", aliases=["delete"], usage="<true_or_false>")
    async def channeldelete(self, ctx: commands.Context, state: bool):
        """Enable or disable Channel Delete
        If this option is enabled, the bot will not delete the original channel: it will duplicate it as normal, but move it to the end of the server's channel list.
        Use `True` (Or `yes`) to enable or `False` (or `no`) to disable.
        """
        if not ctx.author.id == ctx.guild.owner.id:
            await ctx.send("Only the owner of this server can access these commands!")
            return

        config = await self.data.guild(ctx.guild).all()

        actual_channel_delete = config["channel_delete"]
        if actual_channel_delete is state:
            await ctx.send(f"Channel Delete is already set on {state}.")
            return

        await self.data.guild(ctx.guild).channel_delete.set(state)
        await ctx.send(f"Channel Delete state registered: {state}.")

    @config.command(name="firstmessage", aliases=["message"], usage="<true_or_false>")
    async def firstmessage(self, ctx: commands.Context, state: bool):
        """Enable or disable First Message
        If this option is enabled, the bot will send a message to the emptied channel to warn that it has been emptied.
        Use `True` (Or `yes`) to enable or `False` (or `no`) to disable.
        """
        if not ctx.author.id == ctx.guild.owner.id:
            await ctx.send("Only the owner of this server can access these commands!")
            return

        config = await self.data.guild(ctx.guild).all()

        actual_first_message = config["first_message"]
        if actual_first_message is state:
            await ctx.send(f"First Message is already set on {state}.")
            return

        await self.data.guild(ctx.guild).first_message.set(state)
        await ctx.send(f"First Message state registered: {state}.")

    @config.command(name="authordm", aliases=["dmauthor"], usage="<true_or_false>")
    async def authordm(self, ctx: commands.Context, state: bool):
        """Enable or disable Author dm
        If this option is enabled, the bot will try to send a dm to the author of the order to confirm that everything went well.
        Use `True` (Or `yes`) to enable or `False` (or `no`) to disable.
        """
        if not ctx.author.id == ctx.guild.owner.id:
            await ctx.send("Only the owner of this server can access these commands!")
            return

        config = await self.data.guild(ctx.guild).all()

        actual_author_dm = config["author_dm"]
        if actual_author_dm is state:
            await ctx.send(f"Author dm is already set on {state}.")
            return

        await self.data.guild(ctx.guild).author_dm.set(state)
        await ctx.send(f"Author dm state registered: {state}.")

    async def red_get_data_for_user(self, *, user_id: int):
        # this cog does not store any data
        return {}

    async def red_delete_data_for_user(self, *, requester, user_id: int) -> None:
        # this cog does not store any data
        pass

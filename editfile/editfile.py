import typing
from redbot.core import commands
from pathlib import Path

# Credits:
# I made this cog to be able to update files on my bot's host machine easily and quickly, without having to update cogs from GitHub for all my tests.
# Thanks to @epic guy on Discord for the basic syntax (command groups, commands) and also commands (await ctx.send, await ctx.author.send, await ctx.message.delete())!
# Thanks to the developers of the cogs I added features to as it taught me how to make a cog! (Chessgame by WildStriker, Captcha by Kreusada, Speak by Epic guy and Rommer by Dav)
# Thanks to all the people who helped me with some commands in the #coding channel of the redbot support server!

class EditFile(commands.Cog):
    """A cog to get a file and replace it from its path from Discord!"""

    def __init__(self, bot):
        self.bot = bot

    @commands.is_owner()
    @commands.group(aliases=["fileedit"])
    async def editfile(self, ctx):
        """Commands group to get a file and replace it from its path.
        """
        pass

    @editfile.command()
    async def get(self, ctx, path: Path):
        """Get a file on the bot's host machine from its path.
        """
        try:
            file = discord.File(f"{path}")
        except FileNotFoundError:
            await ctx.send("This file cannot be found on the host machine.")
        except IsADirectoryError:
            await ctx.send("The path you specified refers to a directory, not a file.")
        else:
            await ctx.send(f"This is the file available at path `{path}`.", file=file)

    @editfile.command()
    async def replace(self, ctx, path: Path):
        """Replace a file on the bot's host machine from its path.
        """
        try:
            old_file = discord.File(f"{path}")
        except FileNotFoundError:
            await ctx.send("This original file cannot be found on the host machine.")
        except IsADirectoryError:
            await ctx.send("The path you specified refers to a directory, not a file.")
        else:
            if ctx.message.attachments == []:
                await ctx.send("You must send the command with an attachment that will be used to replace the original file.")
                return
            new_file = ctx.message.attachments[0]
            await new_file.save(fp=f"{path}")
            await ctx.send(f"This is the original/old file available at path `{path}`. Normally, this file has been replaced correctly.", file=old_file)
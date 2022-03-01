import discord
import typing
from redbot.core import commands
from pathlib import Path
from redbot.core.data_manager import cog_data_path
from redbot.core.utils.chat_formatting import pagify
from os import listdir

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
    async def get(self, ctx, *, path: Path):
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
    async def replace(self, ctx, *, path: Path):
        """Replace a file on the bot's host machine from its path.
        """
        try:
            if not path.exists():
                raise FileNotFoundError
            if not path.is_dir():
                raise IsADirectoryError
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
 
    @editfile.command()
    async def findcog(self, ctx, cog: str):
        """Get a cog directory on the bot's host machine from its name.
        """
        downloader = ctx.bot.get_cog("Downloader")
        try:
            if downloader is not None:
                path = Path((await downloader.cog_install_path()) / cog)
            else:
                path = cog_data_path(raw_name=cog)
            if not path.exists() or not path.is_dir():
                raise
        except Exception:
            await ctx.send("This cog cannot be found. Are you sure of its name?")
        else:
            await ctx.send(f"```{path}```")

    @editfile.command()
    async def listdir(self, ctx, *, path: Path):
        """List all files/directories of a directory from its path.
        """
        if not path.exists():
            await ctx.send("This directory cannot be found on the host machine.")
            return
        if not path.is_dir():
            await ctx.send("The path you specified refers to a file, not a directory.")
            return
        files = listdir(str(path))
        message = ""
        for file in files:
            path_file = path / file
            if path_file.is_file():
                message += "\n" + f"- [FILE] {file}"
            elif path_file.is_dir():
                message += "\n" + f"- [DIR] {file}"
        message = "```" + message + "```"
        for m in pagify(message):
            await ctx.send(m)

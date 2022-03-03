from .AAA3A_utils.cogsutils import CogsUtils
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

def _(untranslated: str):
    return untranslated

class EditFile(commands.Cog):
    """A cog to get a file and replace it from its path from Discord!"""

    def __init__(self, bot):
        self.bot = bot

        self.cogsutils = CogsUtils(cog=self)
        self.cogsutils._setup()

    @commands.is_owner()
    @commands.group(aliases=["fileedit"])
    async def editfile(self, ctx: commands.Context):
        """Commands group to get a file and replace it from its path.
        """
        pass

    @editfile.command()
    async def get(self, ctx: commands.Context, *, path: Path):
        """Get a file on the bot's host machine from its path.
        """
        try:
            file = discord.File(f"{path}")
        except FileNotFoundError:
            await ctx.send(_("This file cannot be found on the host machine.").format(**locals()))
        except IsADirectoryError:
            await ctx.send(_("The path you specified refers to a directory, not a file.").format(**locals()))
        else:
            await ctx.send(_("This is the file available at path `{path}`.").format(**locals()), file=file)

    @editfile.command()
    async def replace(self, ctx: commands.Context, *, path: Path):
        """Replace a file on the bot's host machine from its path.
        """
        try:
            # if not path.exists():
                # raise FileNotFoundError
            # if not path.is_dir():
                # raise IsADirectoryError
            old_file = discord.File(f"{path}")
        except FileNotFoundError:
            await ctx.send(_("This original file cannot be found on the host machine.").format(**locals()))
        except IsADirectoryError:
            await ctx.send(_("The path you specified refers to a directory, not a file.").format(**locals()))
        else:
            if ctx.message.attachments == []:
                await ctx.send(_("You must send the command with an attachment that will be used to replace the original file.").format(**locals()))
                return
            new_file = ctx.message.attachments[0]
            await new_file.save(fp=f"{path}")
            await ctx.send(_("This is the original/old file available at path `{path}`. Normally, this file has been replaced correctly.").format(**locals()), file=old_file)
 
    @editfile.command()
    async def findcog(self, ctx: commands.Context, cog: str):
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
            await ctx.send(_("This cog cannot be found. Are you sure of its name?").format(**locals()))
        else:
            await ctx.send(f"```{path}```")

    @editfile.command()
    async def listdir(self, ctx: commands.Context, *, path: Path):
        """List all files/directories of a directory from its path.
        """
        if not path.exists():
            await ctx.send(_("This directory cannot be found on the host machine.").format(**locals()))
            return
        if not path.is_dir():
            await ctx.send(_("The path you specified refers to a file, not a directory.").format(**locals()))
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

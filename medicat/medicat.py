from .AAA3A_utils.cogsutils import CogsUtils, Menu  # isort:skip
from redbot.core import commands  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
from redbot.core.bot import Red  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import aiohttp
import asyncio
import os
import re
import textwrap
import traceback

from copy import copy
from redbot import VersionInfo
from redbot.core import Config
from redbot.core.utils.chat_formatting import box, pagify

# Credits:
# Thanks to @epic guy on Discord for the basic syntax (command groups, commands) and also commands (await ctx.send, await ctx.author.send, await ctx.message.delete())!
# Thanks to the developers of the cogs I added features to as it taught me how to make a cog! (Chessgame by WildStriker, Captcha by Kreusada, Speak by Epic guy and Rommer by Dav)
# Thanks to all the people who helped me with some commands in the #coding channel of the redbot support server!

MEDICAT_GUILD = 829469886681972816
VENTOY_UPDATES_CHANNEL = 831224763162165278
BOOTABLES_TOOLS_UPDATES_CHANNEL = 970043597481185301
PORTABLEAPPS_SOFTWARES_UPDATES_CHANNEL = None

# MODERATORS_ROLE = 829472084454670346
# DEVELOPER_ROLE = 883612487881195520
# MEMBERS_ROLE = 829538904720932884

TEST_GUILD = 886147551890399253
TEST_CHANNEL = 905737223348047914

CUSTOM_COMMANDS = {
    "customtools": {"title": "How to add your own bootable tools (iso, wim, vhd) to Medicat USB?", "description": "To add your own bootable tools to Medicat USB, simply put the files in any sub-folder (except those with a `.ventoyignore` file at their root) of your USB stick. As if by magic, the new tools will appear on the Ventoy menu.\nThen you can add a custom name, icon, description, by editing the `USB\\ventoy\\ventoy.json` file following the template."},
    "kofi": {"title": "How to make a donation?", "description": "Jayro (Creator of Medicat): https://ko-fi.com/jayrojones\nMON5TERMATT (Medicat Developer): https://ko-fi.com/mon5termatt\nAAA3A (Medicat Developer): None"},
    "medicatversion": {"title": "What is the latest version of Medicat USB?", "description": "The latest version of Medicat USB is 21.12!\n||https://gbatemp.net/threads/medicat-usb-a-multiboot-linux-usb-for-pc-repair.361577/||"},
    "menus": {"title": "How to download one of the menus?", "description": "Here are the latest links to download the latest versions of the menus:\n- Jayro's Lockîck: \n<https://mega.nz/file/ZtpwEDhR#4bCjUDri2hhUlCgv8Y1EmZVyUnGyhqZjCo0fazXLzqY>\n- AAA3A's Backup: \n<https://mega.nz/file/s8hATRbZ#C28qA8HWKi_xikC6AUG46DiXKIG2Qjl__-4MOl6SI7w>\n- AAA3A's Partition: \n<https://mega.nz/file/w8oFkKYQ#5BbIf7K6pyxYDlE6L4efPqtHUWtCMmx_kta_QHejhpk>\nHere is also a link that should never change to access the same folder containing all the menus: \n<https://mega.nz/folder/FtRCgLQL#KTq897WQiXCJT8OQ3cT9Tg>"},
    "usbvhd": {"title": "What is the difference between Medicat USB and Medicat VHD?", "description": "Medicat USB is a bootable menu that runs on Ventoy and contains all the necessary tools for computer troubleshooting. It contains for example Malwarebytes bootable for virus scans, Mini Windows 10 for a winPE utility and Jayro's Lockpick for all things password related.\n<https://gbatemp.net/threads/medicat-usb-a-multiboot-linux-usb-for-pc-repair.361577/>\nMedicat VHD is a full-featured windows, using the real performance of the computer. It is therefore much more powerful than Mini Windows 10. Moreover, all data is saved and you can find it again at each reboot. (Not intended to be used as an operating system).\n<https://gbatemp.net/threads/official-medicat-vhd-a-usb-bootable-windows-10-virtual-harddisk-for-pc-repair.581637/>\nJayro's Lockpick is a winPE with a menu containing all the necessary tools to remove/bypass/retrieve a Windows password or even for a server.\n<https://gbatemp.net/threads/release-jayros-lockpick-a-bootable-password-removal-suite-winpe.579278/>\nMalwarebytes bootable is a very powerful antivirus. Since it is launched from a winPE, a potential virus cannot prevent it from running properly.\n<https://gbatemp.net/threads/unofficial-malwarebytes-bootable.481046/>"},
    "virus": {"title": "Why does my antivirus software blame Medicat?", "description": "Medicat USB does not contain any viruses! If an antivirus software detects one of its files as such, it is a false positive. As you know, Medicat USB contains tools that can reset a partition, find a password, and modify the system. Portable applications can be falsely flagged because of how they are cracked and packaged. For these reasons all antivirus software's 'real-time scanning' should be disabled when installing, and sometimes even when using, Medicat USB."},
    "whatmedicat": {"title": "What is Medicat USB?", "description": "Medicat USB contains tools to backup/restore data, to manage disks/partitions, to reset/bypass/find a Windows password, to use software with admin rights from a winPE, to do virus scans. In addition, it uses Ventoy, which allows you to add your own bootable tools with a simple copy and paste."}
}

BOOTABLES_TOOLS = {
    "Acronis Cyber Backup": {"url": "https://www.fcportables.com/acronis-cyber-backup-boot/", "category": "USB\\Backup_and_Recovery\\", "regex": r"Acronis Cyber Backup (\d*(\.|-)\d*(\.|-)\d*(\.|-)\d*|\d*(\.|-)\d*(\.|-)\d*|\d*(\.|-)\d*|\d*) Build (\d*) Multilingual BootCD"},
    "Acronis True Image": {"url": "https://www.fcportables.com/acronis-true-image-boot/", "category": "USB\\Backup_and_Recovery\\", "regex": r"Acronis True Image (\d*(\.|-)\d*(\.|-)\d*(\.|-)\d*|\d*(\.|-)\d*(\.|-)\d*|\d*(\.|-)\d*|\d*) Build (\d*) Multilingual Boot ISO"},
    "AOMEI Backupper Technician Plus": {"url": "https://www.fcportables.com/aomei-backupper-boot/", "category": "USB\\Backup_and_Recovery\\", "regex": r"Portable AOMEI Backupper Technician Plus (\d*(\.|-)\d*(\.|-)\d*(\.|-)\d*|\d*(\.|-)\d*(\.|-)\d*|\d*(\.|-)\d*|\d*) \+ Boot WinPE"},
    "EaseUS Data Recovery Wizard": {"url": "https://www.fcportables.com/easeus-recovery-wizard-winpe/", "category": "USB\\Backup_and_Recovery\\", "regex": r"EaseUS Data Recovery Wizard (\d*(\.|-)\d*(\.|-)\d*(\.|-)\d*|\d*(\.|-)\d*(\.|-)\d*|\d*(\.|-)\d*|\d*) WinPE"},
    "EaseUS Todo Backup": {"url": "https://www.fcportables.com/easeus-todo-backup-winpe/", "category": "USB\\Backup_and_Recovery\\", "regex": r"EaseUS Todo Backup (\d*(\.|-)\d*(\.|-)\d*(\.|-)\d*|\d*(\.|-)\d*(\.|-)\d*|\d*(\.|-)\d*|\d*) Build (\d*) Enterprise Technician WinPE"},
    "Macrium Reflect": {"url": "https://www.fcportables.com/macrium-reflect-rescue-winpe/", "category": "USB\\Backup_and_Recovery\\", "regex": r"Macrium Reflect (\d*(\.|-)\d*(\.|-)\d*(\.|-)\d*|\d*(\.|-)\d*(\.|-)\d*|\d*(\.|-)\d*|\d*) Server Plus WinPE \(x64\)"},
    "MiniTool ShadowMaker Pro Ultimate": {"url": "https://www.fcportables.com/shadowmaker-pro/", "category": "USB\\Backup_and_Recovery\\", "regex": r"Portable MiniTool ShadowMaker Pro Ultimate (\d*(\.|-)\d*(\.|-)\d*(\.|-)\d*|\d*(\.|-)\d*(\.|-)\d*|\d*(\.|-)\d*|\d*) \(x64\) \+ WinPE"},
    "MiniTool Power Data Recovery": {"url": "https://www.fcportables.com/minitool-data-recovery-winpe/", "category": "USB\\Backup_and_Recovery\\", "regex": r"Portable MiniTool Power Data Recovery (\d*(\.|-)\d*(\.|-)\d*(\.|-)\d*|\d*(\.|-)\d*(\.|-)\d*|\d*(\.|-)\d*|\d*) Business Technician \+ WinPE"},
    "Boot Repair Disk": {"url": "https://www.fcportables.com/boot-repair-disk/", "category": "USB\\Boot_Repair\\", "regex": r"Boot-Repair-Disk (\d*(\.|-)\d*(\.|-)\d*(\.|-)\d*|\d*(\.|-)\d*(\.|-)\d*|\d*(\.|-)\d*|\d*)"},
    "EasyUEFI Technician": {"url": "https://www.fcportables.com/easyuefi-portable-winpe/", "category": "USB\\Boot_Repair\\", "regex": r"Portable EasyUEFI Technician (\d*(\.|-)\d*(\.|-)\d*(\.|-)\d*|\d*(\.|-)\d*(\.|-)\d*|\d*(\.|-)\d*|\d*) \+ WinPE \(x64\)"},
    "SystemRescue": {"url": "https://www.fcportables.com/systemrescuecd/", "category": "USB\\Boot_Repair\\", "regex": r"SystemRescue (\d*(\.|-)\d*(\.|-)\d*(\.|-)\d*|\d*(\.|-)\d*(\.|-)\d*|\d*(\.|-)\d*|\d*) Boot ISO \(x64\)"},
    "Ultimate Boot": {"url": "https://www.fcportables.com/ultimate-boot-cd/", "category": "USB\\Boot_Repair\\", "regex": r"Ultimate Boot CD (\d*(\.|-)\d*(\.|-)\d*(\.|-)\d*|\d*(\.|-)\d*(\.|-)\d*|\d*(\.|-)\d*|\d*) Final"},
    "HDAT2": {"url": "https://www.fcportables.com/hdat-boot/", "category": "USB\\Boot_Repair\\", "regex": r"HDAT2 (\d*(\.|-)\d*(\.|-)\d*(\.|-)\d*|\d*(\.|-)\d*(\.|-)\d*|\d*(\.|-)\d*|\d*) \(ALL-IN-ONE BOOT Version\)"},
    "Memtest86 Pro": {"url": "https://www.fcportables.com/memtest86-pro/", "category": "USB\\Boot_Repair\\", "regex": r"Memtest86 Pro (\d*(\.|-)\d*(\.|-)\d*(\.|-)\d*|\d*(\.|-)\d*(\.|-)\d*|\d*(\.|-)\d*|\d*) Retail \(ISO/USB\)"},
    "Active@ Boot Disk": {"url": "https://www.fcportables.com/active-boot-disk/", "category": "USB\\Live_Operating_Systems\\", "regex": r"Active@ Boot Disk (\d*(\.|-)\d*(\.|-)\d*(\.|-)\d*|\d*(\.|-)\d*(\.|-)\d*|\d*(\.|-)\d*|\d*) WinPE \(x64\)"},
    "Acronis Disk Director": {"url": "https://www.fcportables.com/acronis-disk-director-boot/", "category": "USB\\Partition_Tools\\", "regex": r"Acronis Disk Director (\d*(\.|-)\d*(\.|-)\d*(\.|-)\d*|\d*(\.|-)\d*(\.|-)\d*|\d*(\.|-)\d*|\d*) WinPE"},
    "AOMEI Partition Assistant Technician Edition": {"url": "https://www.fcportables.com/aomei-partition-assistant-technician-winpe/", "category": "USB\\Partition_Tools\\", "regex": r"Portable AOMEI Partition Assistant Technician Edition (\d*(\.|-)\d*(\.|-)\d*(\.|-)\d*|\d*(\.|-)\d*(\.|-)\d*|\d*(\.|-)\d*|\d*) \+ WinPE"},
    "EaseUS Partition Master": {"url": "https://www.fcportables.com/easeus-partition-master-winpe/", "category": "USB\\Partition_Tools\\", "regex": r"EaseUS Partition Master (\d*(\.|-)\d*(\.|-)\d*(\.|-)\d*|\d*(\.|-)\d*(\.|-)\d*|\d*(\.|-)\d*|\d*) WinPE"},
    "MiniTool Partition Wizard Technician": {"url": "https://www.fcportables.com/minitool-partition-wizard-portable/", "category": "USB\\Partition_Tools\\", "regex": r"Portable MiniTool Partition Wizard Technician v(\d*(\.|-)\d*(\.|-)\d*(\.|-)\d*|\d*(\.|-)\d*(\.|-)\d*|\d*(\.|-)\d*|\d*) \(x64\) \+ WinPE"},
    "NIUBI Partition Editor Technician Edition": {"url": "https://www.fcportables.com/niubi-partition-editor-portable/", "category": "USB\\Partition_Tools\\", "regex": r"Portable NIUBI Partition Editor Technician Edition (\d*(\.|-)\d*(\.|-)\d*(\.|-)\d*|\d*(\.|-)\d*(\.|-)\d*|\d*(\.|-)\d*|\d*) \(x64\) \+ Boot ISO"},
    "Paragon Hard Disk Manager Advanced": {"url": "https://www.fcportables.com/paragon-hard-disk-manager-portable/", "category": "USB\\Partition_Tools\\", "regex": r"Portable Paragon Hard Disk Manager Advanced v(\d*(\.|-)\d*(\.|-)\d*(\.|-)\d*|\d*(\.|-)\d*(\.|-)\d*|\d*(\.|-)\d*|\d*) \(x64\) \+WinPE"},
    "Parted Magic": {"url": "https://www.fcportables.com/parted-magic/", "category": "USB\\Partition_Tools\\", "regex": r"Parted Magic (\d*(\.|-)\d*(\.|-)\d*(\.|-)\d*|\d*(\.|-)\d*(\.|-)\d*|\d*(\.|-)\d*|\d*) Boot ISO \(x64\)"}
}

_ = Translator("Medicat", __file__)

@cog_i18n(_)
class Medicat(commands.Cog):
    """This cog will only work on x server and therefore cannot be used by the general public!"""

    def __init__(self, bot):
        self.bot: Red = bot

        self.config: Config = Config.get_conf(
            self,
            identifier=953864285308,
            force_registration=True,
        )
        self.CONFIG_SCHEMA = 2
        self.medicat_global = {
            "CONFIG_SCHEMA": None,
            "last_ventoy_version": "1.0.74",
            "last_bootables_tools_versions": {
                "Acronis Cyber Backup": "12.5",
                "Acronis True Image": "2021.6",
                "AOMEI Backupper Technician Plus": "6.9.1",
                "EaseUS Data Recovery Wizard": "15.1.0.0",
                "EaseUS Todo Backup": "13.5.0",
                "Macrium Reflect": "8.0.6635",
                "MiniTool ShadowMaker Pro Ultimate": "3.6.1",
                "MiniTool Power Data Recovery": "10.2",
                "Boot Repair Disk": "2021-12-16",
                "EasyUEFI Technician": "4.9.1",
                "SystemRescue": "9.02",
                "Ultimate Boot": "5.3.8",
                "HDAT2": "7.4",
                "Memtest86 Pro": "9.4.1000",
                "Active@ Boot Disk": "19.0.0",
                "Acronis Disk Director": "12.5.163",
                "AOMEI Partition Assistant Technician Edition": "9.7.0",
                "EaseUS Partition Master": "16.8",
                "MiniTool Partition Wizard Technician": "12.6",
                "NIUBI Partition Editor Technician Edition": "7.8.7",
                "Paragon Hard Disk Manager Advanced": "17.20.11",
                "Parted Magic": "2022.01.18",
            },
        }
        self.config.register_global(**self.medicat_global)

        self.__func_red__ = ["cog_unload"]
        self.cogsutils = CogsUtils(cog=self)
        self.cogsutils._setup()

        asyncio.create_task(self.edit_config_schema())
        self.cogsutils.create_loop(function=self.ventoy_updates, name="Ventoy Updates", hours=1)
        self.cogsutils.create_loop(function=self.bootables_tools_updates, name="Bootables Tools Updates", hours=1)
        try:
            self.add_custom_commands()
        except Exception as e:
            self.log.error(f"An error occurred while adding the custom_commands.", exc_info=e)

    async def edit_config_schema(self):
        ALL_CONFIG = await self.config.all()
        CONFIG_SCHEMA = await self.config.CONFIG_SCHEMA()
        if ALL_CONFIG == self.medicat_global:
            CONFIG_SCHEMA = self.CONFIG_SCHEMA
            await self.config.CONFIG_SCHEMA.set(CONFIG_SCHEMA)
            return
        if CONFIG_SCHEMA is None:
            CONFIG_SCHEMA = 1
            await self.config.CONFIG_SCHEMA(CONFIG_SCHEMA)
        if CONFIG_SCHEMA == 1 and not CONFIG_SCHEMA == self.CONFIG_SCHEMA:
            await self.config.last_bootables_tools_versions.clear()
            self.log.info(f"The Config scheme has been successfully modified to {self.CONFIG_SCHEMA} for the {self.__class__.__name__} cog.")
            CONFIG_SCHEMA = 2
            await self.config.CONFIG_SCHEMA.set(CONFIG_SCHEMA)
        if CONFIG_SCHEMA < self.CONFIG_SCHEMA and not CONFIG_SCHEMA == self.CONFIG_SCHEMA:
            self.log.info(f"The Config scheme has been successfully modified to {self.CONFIG_SCHEMA} for the {self.__class__.__name__} cog.")
            CONFIG_SCHEMA = self.CONFIG_SCHEMA
            await self.config.CONFIG_SCHEMA.set(CONFIG_SCHEMA)

    def cog_unload(self):
        try:
            self.remove_custom_commands()
        except Exception as e:
            self.log.error(f"An error occurred while removing the custom_commands.", exc_info=e)
        self.cogsutils._end()

    async def ventoy_updates(self, channel: typing.Optional[discord.TextChannel]=None):
        if channel is None:
            guild = self.bot.get_guild(MEDICAT_GUILD)
            if guild is None:
                return
            channel = guild.get_channel(VENTOY_UPDATES_CHANNEL)
            if channel is None:
                return
        else:
            guild = channel.guild
            channel = channel
        last_ventoy_version_str = str(await self.config.last_ventoy_version())
        last_ventoy_version = VersionInfo.from_str(last_ventoy_version_str)

        async with aiohttp.ClientSession() as session:
            async with session.get("https://api.github.com/repos/ventoy/Ventoy/git/refs/tags", timeout=3) as r:
                ventoy_tags = await r.json()
        versions = sorted(ventoy_tags, key=lambda ventoy_version: VersionInfo.from_str(str(ventoy_version["ref"]).replace("refs/tags/v", "").replace("1.0.0", "1.0.").replace("beta", ".dev")))

        if last_ventoy_version >= VersionInfo.from_str(str(ventoy_tags[len(ventoy_tags) - 1]["ref"]).replace("refs/tags/v", "").replace("1.0.0", "1.0.").replace("beta", ".dev")):
            return
        await self.config.last_ventoy_version.set(str(ventoy_tags[len(ventoy_tags) - 1]["ref"]).replace("refs/tags/v", "").replace("1.0.0", "1.0.").replace("beta", ".dev"))

        for version in versions:
            ventoy_tag_name = str(version["ref"]).replace("refs/tags/", "")
            ventoy_version_str = ventoy_tag_name.replace("v", "").replace("1.0.0", "1.0.").replace("beta", ".dev")
            ventoy_version = VersionInfo.from_str(ventoy_version_str)
            if last_ventoy_version >= ventoy_version:
                continue

            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"https://api.github.com/repos/ventoy/Ventoy/releases/tags/{ventoy_tag_name}", timeout=3) as r:
                        ventoy_tag_body = str((await r.json())["body"])
            except Exception:
                ventoy_tag_body = None

            message: str = f"Ventoy v{ventoy_version_str} has been released!\nhttps://ventoy.net/en/index.html"
            if ventoy_tag_body is not None:
                ventoy_tag_body = ventoy_tag_body.split("\n")
                result = []
                for x in ventoy_tag_body:
                    if x == "See [https://www.ventoy.net/en/doc_news.html](https://www.ventoy.net/en/doc_news.html) for more details.\r":
                        break
                    result += x
                ventoy_tag_body = "".join(result)
                message += "\n" + box(ventoy_tag_body[:1999 - len(message + "\n") - len("``````")])

            hook: discord.Webhook = await CogsUtils(bot=self.bot).get_hook(channel)
            message: discord.Message = await hook.send(content=message, username="Ventoy Updates", avatar_url="https://ventoy.net/static/img/ventoy.png?v=1")
            if message is not None:
                try:
                    await message.publish()
                except discord.HTTPException:
                    pass

    async def bootables_tools_updates(self, channel: typing.Optional[discord.TextChannel]=None):
        if channel is None:
            guild = self.bot.get_guild(MEDICAT_GUILD)
            if guild is None:
                return
            channel = guild.get_channel(BOOTABLES_TOOLS_UPDATES_CHANNEL)
            if channel is None:
                return
        else:
            guild = channel.guild
            channel = channel
        last_bootables_tools_versions_str: typing.Dict = await self.config.last_bootables_tools_versions()

        tools_versions_str = {}
        for tool in BOOTABLES_TOOLS:
            if tool not in last_bootables_tools_versions_str:
                continue
            url = BOOTABLES_TOOLS[tool]["url"]
            last_tool_version_str = last_bootables_tools_versions_str[tool]
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=3) as r:
                    r = await r.text()
            for x in r.split("\n"):
                if '"headline":' in x and '<html lang="en-US">' not in x:
                    break
            x = x.replace('    "headline": "', '').replace('",', '')
            regex = re.compile(BOOTABLES_TOOLS[tool]["regex"], re.I).findall(x)
            if regex == []:
                continue
            regex = regex[0]
            regex = regex[0] if isinstance(regex, typing.Tuple) and len(regex) > 0 else regex
            tool_version_str: str = regex
            tools_versions_str[tool] = tool_version_str

            if last_tool_version_str == tool_version_str:
                continue

            embed: discord.Embed = discord.Embed()
            embed.set_thumbnail(url="https://www.fcportables.com/wp-content/uploads/fcportables-logo.jpg")
            embed.set_footer(text="From FCportables.", icon_url="https://www.fcportables.com/wp-content/uploads/fcportables-logo.jpg")
            embed.url = url
            embed.title = f"{tool} now has a new version!"
            embed.description = f"[View on FCportables!]({url})"
            embed.add_field(name="Old version:", value=last_tool_version_str, inline=True)
            embed.add_field(name="New version:", value=tool_version_str, inline=True)

            hook: discord.Webhook = await CogsUtils(bot=self.bot).get_hook(channel)
            message: discord.Message = await hook.send(embed=embed, username="Bootables Tools Updates", avatar_url="https://www.fcportables.com/wp-content/uploads/fcportables-logo.jpg")
            if message is not None:
                try:
                    await message.publish()
                except discord.HTTPException:
                    pass
        await self.config.last_bootables_tools_versions.set(tools_versions_str)

    def in_medicat_guild():
        async def pred(ctx):
            if ctx.guild.id == MEDICAT_GUILD or ctx.guild.id == TEST_GUILD:
                return True
            else:
                return False
        return commands.check(pred)

    def add_custom_commands(self):

        def get_function_from_str(bot, command, name=None):
            to_compile = "def func():\n%s" % textwrap.indent(command, "  ")
            env = {
                "bot": bot,
                "discord": discord,
                "commands": commands,
                "CUSTOM_COMMANDS": CUSTOM_COMMANDS,
            }
            exec(to_compile, env)
            result = env["func"]()
            return result

        for name, text in CUSTOM_COMMANDS.items():
            try:
                self.bot.remove_command(name)
                command_str = """
    def in_medicat_guild():
        async def pred(ctx):
            if ctx.guild.id == {MEDICAT_GUILD} or ctx.guild.id == {TEST_GUILD}:
                return True
            else:
                return False
        return commands.check(pred)

    @in_medicat_guild()
    @commands.command()
    async def {name}(ctx):
        embed: discord.Embed = discord.Embed()
        embed.set_thumbnail(url="https://cdn.discordapp.com/avatars/882914619847479296/22ec88463059ae49099ba1aaea790bc4.webp?size=100")
        embed.set_footer(text="Medicat USB Official", icon_url="https://cdn.discordapp.com/avatars/882914619847479296/22ec88463059ae49099ba1aaea790bc4.webp?size=100")
        embed.title = CUSTOM_COMMANDS[ctx.command.name]["title"]
        embed.description = CUSTOM_COMMANDS[ctx.command.name]["description"]
        await ctx.send(embed=embed)
    return {name}
    """.format(MEDICAT_GUILD=MEDICAT_GUILD, TEST_GUILD=TEST_GUILD, name=name)
                command: commands.command = get_function_from_str(self.bot, command_str)
                command.name = name
                command.description = text["title"]
                command.cog = self
                self.bot.add_command(command)
            except Exception:
                self.bot.remove_command(name)
            else:
                self.__cog_commands__.__add__(tuple([command]))

    def remove_custom_commands(self):
        for name in CUSTOM_COMMANDS:
            self.remove_command(name)

    @commands.guild_only()
    @in_medicat_guild()
    @commands.command(hidden=True)
    async def secretupdatemedicatcog(self, ctx: commands.Context):
        try:
            message = copy(ctx.message)
            message.author = ctx.guild.get_member(list(ctx.bot.owner_ids)[0]) or ctx.guild.get_member(list(ctx.bot.owner_ids)[1])
            message.content = f"{ctx.prefix}cog update medicat"
            context = await ctx.bot.get_context(message)
            context.assume_yes = True
            await ctx.bot.invoke(context)
        except Exception as error:
            traceback_error = "".join(traceback.format_exception(type(error), error, error.__traceback__))
            if "USERPROFILE" in os.environ:
                traceback_error = traceback_error.replace(os.environ["USERPROFILE"], "{USERPROFILE}")
            if "HOME" in os.environ:
                traceback_error = traceback_error.replace(os.environ["HOME"], "{HOME}")
            pages = []
            for page in pagify(traceback_error, shorten_by=15, page_length=1985):
                pages.append(box(page, lang="py"))
            try:
                await Menu(pages=pages, timeout=30, delete_after_timeout=True).start(ctx)
            except discord.HTTPException:
                return
        else:
            await ctx.tick()
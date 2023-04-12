from .AAA3A_utils import Cog, CogsUtils, Menu, Loop  # isort:skip
from redbot.core import commands, Config  # isort:skip
from redbot.core.bot import Red  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import asyncio
import json
import re
import traceback
from copy import copy

import aiohttp
from bs4 import BeautifulSoup
from redbot import VersionInfo
from redbot.core.utils.chat_formatting import bold, box, pagify

# Credits:
# General repo credits.
# Thanks to Jayro for Medicat!
# Thanks to Matt because this cog is for him bot.

_ = Translator("Medicat", __file__)

if CogsUtils().is_dpy2:
    hybrid_command = commands.hybrid_command
    hybrid_group = commands.hybrid_group
else:
    hybrid_command = commands.command
    hybrid_group = commands.group

MEDICAT_ICON_URL = None

MEDICAT_GUILD = 829469886681972816
VENTOY_UPDATES_CHANNEL = 831224763162165278
BOOTABLES_TOOLS_UPDATES_CHANNEL = 970043597481185301
PORTABLEAPPS_SOFTWARES_UPDATES_CHANNEL = None

VENTOY_UPDATES_ROLE = 985288671009837066
BOOTABLES_TOOLS_UPDATE_ROLE = None

# MODERATORS_ROLE = 829472084454670346
# DEVELOPER_ROLE = 883612487881195520
# MEMBERS_ROLE = 829538904720932884

TEST_GUILD = 886147551890399253
TEST_CHANNEL = 905737223348047914

CUSTOM_COMMANDS = {
    "customtools": {
        "title": (
            "Can I add my own bootable tools (iso, wim, vhd) or PortableApps softwares to Medicat USB?"
        ),
        "description": (
            "Please feel free to modify MediCat to YOUR individual needs! 😄\nTo add your own bootable tools to Medicat USB, simply put the files in any sub-folder (except those with a `.ventoyignore` file at their root) of your USB stick. As if by magic, the new tools will appear on the Ventoy menu.\nThen you can add a custom name, icon, description, by editing the `USB\\ventoy\\ventoy.json` file following the template.\nAbsolutely, I encourage it!"
        ),
    },
    "free": {
        "title": ("Is Medicat free?"),
        "description": (
            "Absolutely. I will never charge money for MediCat, or accept donations. However, feel free to share your ideas, questions, and concerns in this thread. That's how you can give back. 🙂"
        ),
    },
    "howinstall": {
        "title": ("How do I install Medicat USB?"),
        "description": (
            "1) Install the latest version of Ventoy on your USB stick (<https://github.com/ventoy/Ventoy/releases> & <https://ventoy.net/en/doc_start.html>).\n2) Download the last version of Medicat USB with Torrent, Mega or Google Drive (<https://medicatusb.com/>).\n3) Extract the downloaded zips to the root of the USB stick.\nFull tutorial: <https://medicatusb.com/docs/installation/installing-medicat/>\nYou can also use the automatic installer of MON5TERMATT (<https://medicatusb.com/installer/>).\nWarning: do not forget to disable your antivirus software (see the `virus` command for more information)."
        ),
    },
    "kofi": {
        "title": ("How to make a donation?"),
        "description": (
            "@Jayro (Creator of Medicat): <https://ko-fi.com/jayrojones>\n@MON5TERMATT (Medicat Developer): <https://ko-fi.com/mon5termatt>\n@AAA3A (Medicat Developer): Nothing"
        ),
    },
    "medicatversion": {
        "title": ("What is the latest version of Medicat USB?"),
        "description": (
            "The latest version of Medicat USB is 21.12!\n||<https://gbatemp.net/threads/medicat-usb-a-multiboot-linux-usb-for-pc-repair.361577/>||"
        ),
    },
    "menus": {
        "title": ("How to download one of the menus?"),
        "description": (
            "Here are the latest links to download the latest versions of the menus:\n- Jayro's Lockîck: \n<https://mega.nz/file/ZtpwEDhR#4bCjUDri2hhUlCgv8Y1EmZVyUnGyhqZjCo0fazXLzqY>\n- AAA3A's Backup: \n<https://mega.nz/file/s8hATRbZ#C28qA8HWKi_xikC6AUG46DiXKIG2Qjl__-4MOl6SI7w>\n- AAA3A's Partition: \n<https://mega.nz/file/w8oFkKYQ#5BbIf7K6pyxYDlE6L4efPqtHUWtCMmx_kta_QHejhpk>\nHere is also a link that should never change to access the same folder containing all the menus: \n<https://mega.nz/folder/FtRCgLQL#KTq897WQiXCJT8OQ3cT9Tg>"
        ),
    },
    "minios": {
        "title": ("Can I install Mini Windows 10 as my main OS?"),
        "description": (
            "No, it doesn't work like that. It's a WinPE image (Windows Pre-install Environment) that runs in memory. It's primary use is to troubleshoot a troublesome PC."
        ),
    },
    "noiso": {
        "title": ("How do I download the Medicat USB iso file?"),
        "description": (
            "Medicat USB is not available as an iso file.\nPreviously, Medicat USB was available as an iso file. Now it uses Ventoy to run. It is currently impossible to put Ventoy and therefore Medicat USB in an iso file, or at least not without difficulties."
        ),
    },
    "portableapps": {
        "title": ("Can I run the PortableApps on my current PC without booting up MediCat?"),
        "description": (
            "Yes, just mount the MediCat USB, and open Start.exe to launch the platform. These are the same exact apps that get loaded within Mini Windows 10. So if you update them, they will show up updated in Mini Windows 10 as well."
        ),
    },
    "updateonly": {
        "title": ("How can I update Medicat USB without having to install all the files again?"),
        "description": (
            "For the time being, you are in any case obliged to download all Medicat USB files again to update it. However, if you only want to keep your previous personal changes, you can save them somewhere and reproduce them on the new instance of the bootable USB stick.\nFor Medicat USB 22.06, @AAA3A is currently coding an update only script for Medicat USB, in batch. It will be downloaded with only the necessary files and will however only work from one version to another, after being prepared in advance."
        ),
    },
    "usbvhd": {
        "title": ("What is the difference between Medicat USB and Medicat VHD?"),
        "description": (
            "**Medicat USB** is a bootable menu that runs on Ventoy and contains all the necessary tools for computer troubleshooting. It contains for example Malwarebytes bootable for virus scans, Mini Windows 10 for a winPE utility and Jayro's Lockpick for all things password related.\n<https://gbatemp.net/threads/medicat-usb-a-multiboot-linux-usb-for-pc-repair.361577/>\n**Medicat VHD** is a full-featured windows, using the real performance of the computer. It is therefore much more powerful than Mini Windows 10. Moreover, all data is saved and you can find it again at each reboot. (Not intended to be used as an operating system).\n<https://gbatemp.net/threads/official-medicat-vhd-a-usb-bootable-windows-10-virtual-harddisk-for-pc-repair.581637/>\n**Jayro's Lockpick** is a winPE with a menu containing all the necessary tools to remove/bypass/retrieve a Windows password or even for a server.\n<https://gbatemp.net/threads/release-jayros-lockpick-a-bootable-password-removal-suite-winpe.579278/>\n**Malwarebytes bootable** is a very powerful antivirus. Since it is launched from a winPE, a potential virus cannot prevent it from running properly.\n<https://gbatemp.net/threads/unofficial-malwarebytes-bootable.481046/>\n**Medicat Second Opinion** is a set of 11 bootable antiviruses to clean viruses in a computer. But most of them only work on legacy BIOS and not UEFI.\n<https://gbatemp.net/threads/medicat-second-opinion-a-collection-of-bootable-antivirus-boot-disks-on-a-single-usb-device.577842/>"
        ),
    },
    "virus": {
        "title": ("Why does my antivirus software blame Medicat?"),
        "description": (
            "Medicat USB does not contain any viruses! If an antivirus software detects one of its files as such, it is a false positive.\nAs you know, Medicat USB contains tools that can reset a partition, find a password, and modify the system. Portable applications can be falsely flagged because of how they are cracked and packaged.\nFor these reasons all antivirus software's 'real-time scanning' should be disabled when installing, and sometimes even when using, Medicat USB.\nAll the scripts associated with the project (published by one of the 3 developers) and Ventoy do not have one either."
        ),
    },
    "whatmedicat": {
        "title": ("What is Medicat USB?"),
        "description": (
            "Medicat USB contains tools to backup/restore data, to manage disks/partitions, to reset/bypass/find a Windows password, to use software with admin rights from a winPE, to do virus scans. In addition, it uses Ventoy, which allows you to add your own bootable tools with a simple copy and paste."
        ),
    },
    "whenupdate": {
        "title": ("How often will Medicat be updated?"),
        "description": (
            "MediCat USB is now a rolling release, so will be regularly updated with major releases, and minor updates as needed (Typically monthly or bi-monthly). The links here will always be the latest version. The PortableApps are easily updatable by the user, once they have been 'burned' to USB."
        ),
    },
    "wimvhd": {
        "title": ("Why doesn't Ventoy display Wim and VHD files?"),
        "description": (
            "You must download an additional plugin/file and place it in the `USB\\ventoy\\` folder (create it if necessary).\n\n**WimBoot Plugin (https://ventoy.net/en/plugin_wimboot.html):**\n- Download `ventoy_wimboot.img` file from <https://github.com/ventoy/wimiso/releases>.\n- Put the file under `ventoy` directory in the `ventoy partition` of the USB stick, that is `/ventoy/ventoy_wimboot.img` and that's all.\n\n**VhdBoot Plugin (<https://ventoy.net/en/plugin_vhdboot.html>):**\n- Download `ventoy_vhdboot.img` file from <https://github.com/ventoy/vhdiso/releases>.\n- Put the file under `ventoy` directory in the `ventoy` partition of the USB stick, that is `/ventoy/ventoy_vhdboot.img` and that's all."
        ),
    },
    "xy": {
        "title": ("X & Y"),
        "description": (
            "What is the context?\nIf you have any problems or would like to ask for help, please give information about what you are not able to do. Don't just say you don't understand how to make x software work, say where you are, what is wrong with it and what is the potential error. \nThank you for your understanding."
        ),
    },
    "test": {"title": ("Test!"), "description": ("Test.")},
}

BOOTABLES_TOOLS = {
    "Acronis Cyber Backup": {
        "url": "https://www.fcportables.com/acronis-cyber-backup-boot/",
        "category": "USB\\Backup_and_Recovery\\",
        "regex": r"Acronis Cyber Backup (\d*(\.|-)\d*(\.|-)\d*(\.|-)\d*|\d*(\.|-)\d*(\.|-)\d*|\d*(\.|-)\d*|\d*) Build (\d*) Multilingual BootCD",
    },
    "Acronis True Image": {
        "url": "https://www.fcportables.com/acronis-true-image-boot/",
        "category": "USB\\Backup_and_Recovery\\",
        "regex": r"Acronis True Image (\d*(\.|-)\d*(\.|-)\d*(\.|-)\d*|\d*(\.|-)\d*(\.|-)\d*|\d*(\.|-)\d*|\d*) Build (\d*) Multilingual Boot ISO",
    },
    "AOMEI Backupper Technician Plus": {
        "url": "https://www.fcportables.com/aomei-backupper-boot/",
        "category": "USB\\Backup_and_Recovery\\",
        "regex": r"Portable AOMEI Backupper Technician Plus (\d*(\.|-)\d*(\.|-)\d*(\.|-)\d*|\d*(\.|-)\d*(\.|-)\d*|\d*(\.|-)\d*|\d*) \+ Boot WinPE",
    },
    "EaseUS Data Recovery Wizard": {
        "url": "https://www.fcportables.com/easeus-recovery-wizard-winpe/",
        "category": "USB\\Backup_and_Recovery\\",
        "regex": r"EaseUS Data Recovery Wizard (\d*(\.|-)\d*(\.|-)\d*(\.|-)\d*|\d*(\.|-)\d*(\.|-)\d*|\d*(\.|-)\d*|\d*) Build (\d*) WinPE \(x64\)",
    },
    "EaseUS Todo Backup": {
        "url": "https://www.fcportables.com/easeus-todo-backup-winpe/",
        "category": "USB\\Backup_and_Recovery\\",
        "regex": r"EaseUS Todo Backup (\d*(\.|-)\d*(\.|-)\d*(\.|-)\d*|\d*(\.|-)\d*(\.|-)\d*|\d*(\.|-)\d*|\d*) Build (\d*) WinPE \(x64\)",
    },
    "Macrium Reflect": {
        "url": "https://www.fcportables.com/macrium-reflect-rescue-winpe/",
        "category": "USB\\Backup_and_Recovery\\",
        "regex": r"Macrium Reflect (\d*(\.|-)\d*(\.|-)\d*(\.|-)\d*|\d*(\.|-)\d*(\.|-)\d*|\d*(\.|-)\d*|\d*) Server Plus WinPE \(x64\)",
    },
    "MiniTool ShadowMaker Business Deluxe": {
        "url": "https://www.fcportables.com/shadowmaker-pro/",
        "category": "USB\\Backup_and_Recovery\\",
        "regex": r"Portable MiniTool ShadowMaker Business Deluxe (\d*(\.|-)\d*(\.|-)\d*(\.|-)\d*|\d*(\.|-)\d*(\.|-)\d*|\d*(\.|-)\d*|\d*) \(x64\)",
    },
    "MiniTool Power Data Recovery": {
        "url": "https://www.fcportables.com/minitool-data-recovery-winpe/",
        "category": "USB\\Backup_and_Recovery\\",
        "regex": r"Portable MiniTool Power Data Recovery (\d*(\.|-)\d*(\.|-)\d*(\.|-)\d*|\d*(\.|-)\d*(\.|-)\d*|\d*(\.|-)\d*|\d*) Business Technician \+ WinPE",
    },
    "Boot Repair Disk": {
        "url": "https://www.fcportables.com/boot-repair-disk/",
        "category": "USB\\Boot_Repair\\",
        "regex": r"Boot-Repair-Disk (\d*(\.|-)\d*(\.|-)\d*(\.|-)\d*|\d*(\.|-)\d*(\.|-)\d*|\d*(\.|-)\d*|\d*)",
    },
    "EasyUEFI Technician": {
        "url": "https://www.fcportables.com/easyuefi-portable-winpe/",
        "category": "USB\\Boot_Repair\\",
        "regex": r"Portable EasyUEFI Technician (\d*(\.|-)\d*(\.|-)\d*(\.|-)\d*|\d*(\.|-)\d*(\.|-)\d*|\d*(\.|-)\d*|\d*) \+ WinPE \(x64\)",
    },
    "SystemRescue": {
        "url": "https://www.fcportables.com/systemrescuecd/",
        "category": "USB\\Boot_Repair\\",
        "regex": r"SystemRescue (\d*(\.|-)\d*(\.|-)\d*(\.|-)\d*|\d*(\.|-)\d*(\.|-)\d*|\d*(\.|-)\d*|\d*) Boot ISO \(x64\)",
    },
    "Ultimate Boot": {
        "url": "https://www.fcportables.com/ultimate-boot-cd/",
        "category": "USB\\Boot_Repair\\",
        "regex": r"Ultimate Boot CD (\d*(\.|-)\d*(\.|-)\d*(\.|-)\d*|\d*(\.|-)\d*(\.|-)\d*|\d*(\.|-)\d*|\d*) Final",
    },
    "HDAT2": {
        "url": "https://www.fcportables.com/hdat-boot/",
        "category": "USB\\Boot_Repair\\",
        "regex": r"HDAT2 (\d*(\.|-)\d*(\.|-)\d*(\.|-)\d*|\d*(\.|-)\d*(\.|-)\d*|\d*(\.|-)\d*|\d*) \(ALL-IN-ONE BOOT Version\)",
    },
    "Memtest86 Pro": {
        "url": "https://www.fcportables.com/memtest86-pro/",
        "category": "USB\\Boot_Repair\\",
        "regex": r"Memtest86 Pro v(\d*(\.|-)\d*(\.|-)\d*(\.|-)\d*|\d*(\.|-)\d*(\.|-)\d*|\d*(\.|-)\d*|\d*) ISO-USB Multilingual \(Fixed\)",
    },
    "Active@ Boot Disk": {
        "url": "https://www.fcportables.com/active-boot-disk/",
        "category": "USB\\Live_Operating_Systems\\",
        "regex": r"Active@ Boot Disk (\d*(\.|-)\d*(\.|-)\d*(\.|-)\d*|\d*(\.|-)\d*(\.|-)\d*|\d*(\.|-)\d*|\d*) WinPE \(x64\)",
    },
    "Acronis Disk Director": {
        "url": "https://www.fcportables.com/acronis-disk-director-boot/",
        "category": "USB\\Partition_Tools\\",
        "regex": r"Acronis Disk Director (\d*(\.|-)\d*(\.|-)\d*(\.|-)\d*|\d*(\.|-)\d*(\.|-)\d*|\d*(\.|-)\d*|\d*) WinPE",
    },
    "AOMEI Partition Assistant Technician Edition": {
        "url": "https://www.fcportables.com/aomei-partition-assistant-technician-winpe/",
        "category": "USB\\Partition_Tools\\",
        "regex": r"Portable AOMEI Partition Assistant Technician Edition (\d*(\.|-)\d*(\.|-)\d*(\.|-)\d*|\d*(\.|-)\d*(\.|-)\d*|\d*(\.|-)\d*|\d*) \+ WinPE",
    },
    "EaseUS Partition Master": {
        "url": "https://www.fcportables.com/easeus-partition-master-winpe/",
        "category": "USB\\Partition_Tools\\",
        "regex": r"EaseUS Partition Master (\d*(\.|-)\d*(\.|-)\d*(\.|-)\d*|\d*(\.|-)\d*(\.|-)\d*|\d*(\.|-)\d*|\d*) Build (\d*) \(x64\) WinPE",
    },
    "MiniTool Partition Wizard Technician": {
        "url": "https://www.fcportables.com/minitool-partition-wizard-portable/",
        "category": "USB\\Partition_Tools\\",
        "regex": r"Portable MiniTool Partition Wizard Technician v(\d*(\.|-)\d*(\.|-)\d*(\.|-)\d*|\d*(\.|-)\d*(\.|-)\d*|\d*(\.|-)\d*|\d*) \(x64\) \+ WinPE",
    },
    "NIUBI Partition Editor Technician Edition": {
        "url": "https://www.fcportables.com/niubi-partition-editor-portable/",
        "category": "USB\\Partition_Tools\\",
        "regex": r"Portable NIUBI Partition Editor Technician Edition (\d*(\.|-)\d*(\.|-)\d*(\.|-)\d*|\d*(\.|-)\d*(\.|-)\d*|\d*(\.|-)\d*|\d*)",
    },
    "Paragon Hard Disk Manager Advanced": {
        "url": "https://www.fcportables.com/paragon-hard-disk-manager-portable/",
        "category": "USB\\Partition_Tools\\",
        "regex": r"Portable Paragon Hard Disk Manager Advanced v(\d*(\.|-)\d*(\.|-)\d*(\.|-)\d*|\d*(\.|-)\d*(\.|-)\d*|\d*(\.|-)\d*|\d*) \(x64\) \+WinPE",
    },
    "Parted Magic": {
        "url": "https://www.fcportables.com/parted-magic/",
        "category": "USB\\Partition_Tools\\",
        "regex": r"Parted Magic (\d*(\.|-)\d*(\.|-)\d*(\.|-)\d*|\d*(\.|-)\d*(\.|-)\d*|\d*(\.|-)\d*|\d*) Boot ISO \(x64\)",
    },
}


@cog_i18n(_)
class Medicat(Cog):
    """This cog will only work on x server and therefore cannot be used by the general public!"""

    def __init__(self, bot: Red) -> None:
        self.bot: Red = bot

        self.config: Config = Config.get_conf(
            self,
            identifier=205192943327321000143939875896557571750,  # 953864285308
            force_registration=True,
        )
        self.CONFIG_SCHEMA: int = 2
        self.medicat_global: typing.Dict[
            str, typing.Union[typing.Optional[int], str, typing.Dict[str, str]]
        ] = {
            "CONFIG_SCHEMA": None,
            "last_ventoy_version": "1.0.74",
            "last_bootables_tools_versions": {
                "Acronis Cyber Backup": "12.5",
                "Acronis True Image": "2021.6",
                "AOMEI Backupper Technician Plus": "6.9.1",
                "EaseUS Data Recovery Wizard": "15.2.0.0",
                "EaseUS Todo Backup": "13.5.0",
                "Macrium Reflect": "8.0.6758",
                "MiniTool ShadowMaker Business Deluxe": "3.6.1",
                "MiniTool Power Data Recovery": "10.2",
                "Boot Repair Disk": "2021-12-16",
                "EasyUEFI Technician": "4.9.2",
                "SystemRescue": "9.02",
                "Ultimate Boot": "5.3.8",
                "HDAT2": "7.4",
                "Memtest86 Pro": "9.4.1000",
                "Active@ Boot Disk": "22.0",
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

        self._session: aiohttp.ClientSession = None

        self.cogsutils: CogsUtils = CogsUtils(cog=self)

    @property
    def loops(self) -> typing.List[Loop]:
        return list(self.cogsutils.loops.values())

    async def cog_load(self) -> None:
        global MEDICAT_ICON_URL
        MEDICAT_ICON_URL = (
            (await self.bot.fetch_invite("medicat")).guild.icon.url
            if self.cogsutils.is_dpy2
            else (await self.bot.fetch_invite("medicat")).guild.icon_url
        )
        await self.edit_config_schema()
        self._session = aiohttp.ClientSession()
        self.cogsutils.create_loop(function=self.ventoy_updates, name="Ventoy Updates", hours=1)
        self.cogsutils.create_loop(
            function=self.bootables_tools_updates, name="Bootables Tools Updates", hours=1
        )
        self.CC_added: asyncio.Event = asyncio.Event()
        await self.add_custom_commands()

    async def edit_config_schema(self) -> None:
        CONFIG_SCHEMA = await self.config.CONFIG_SCHEMA()
        ALL_CONFIG_GLOBAL = await self.config.all()
        if ALL_CONFIG_GLOBAL == self.config._defaults[self.config.GLOBAL]:
            CONFIG_SCHEMA = self.CONFIG_SCHEMA
            await self.config.CONFIG_SCHEMA.set(CONFIG_SCHEMA)
            return
        if CONFIG_SCHEMA is None:
            CONFIG_SCHEMA = 1
            await self.config.CONFIG_SCHEMA(CONFIG_SCHEMA)
        if CONFIG_SCHEMA == self.CONFIG_SCHEMA:
            return
        if CONFIG_SCHEMA == 1:
            await self.config.last_bootables_tools_versions.clear()
            CONFIG_SCHEMA = 2
            await self.config.CONFIG_SCHEMA.set(CONFIG_SCHEMA)
        if CONFIG_SCHEMA < self.CONFIG_SCHEMA:
            CONFIG_SCHEMA = self.CONFIG_SCHEMA
            await self.config.CONFIG_SCHEMA.set(CONFIG_SCHEMA)
        self.log.info(
            f"The Config schema has been successfully modified to {self.CONFIG_SCHEMA} for the {self.qualified_name} cog."
        )

    if CogsUtils().is_dpy2:

        async def cog_unload(self) -> None:
            self.CC_added.set()
            try:
                self.remove_custom_commands()
            except Exception as e:
                self.log.error(
                    "An error occurred while removing the custom_commands.", exc_info=e
                )
            self.cogsutils._end()
            if self._session is not None:
                await self._session.close()

    else:

        def cog_unload(self) -> None:
            try:
                self.remove_custom_commands()
            except Exception as e:
                self.log.error(
                    "An error occurred while removing the custom_commands.", exc_info=e
                )
            self.cogsutils._end()
            if self._session is not None:
                asyncio.create_task(self._session.close())

    async def ventoy_updates(
        self,
        channel: typing.Optional[discord.TextChannel] = None,
        ping_role: typing.Optional[bool] = True,
        force: typing.Optional[bool] = False,
        version: str = None,
    ) -> typing.List[typing.Dict]:
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

        async with self._session.get(
            "https://api.github.com/repos/ventoy/ventoy/releases", timeout=3
        ) as r:
            ventoy_tags = await r.json()
        versions = sorted(
            ventoy_tags,
            key=lambda ventoy_version: VersionInfo.from_str(
                str(ventoy_version["tag_name"])
                .replace("v", "")
                .replace("1.0.0", "1.0.")
                .replace("beta", ".dev")
            ),
        )
        if versions == []:
            return

        if not force:
            if last_ventoy_version >= VersionInfo.from_str(
                str(versions[-1]["tag_name"])
                .replace("v", "")
                .replace("1.0.0", "1.0.")
                .replace("beta", ".dev")
            ):
                return
            await self.config.last_ventoy_version.set(
                str(versions[-1]["tag_name"])
                .replace("v", "")
                .replace("1.0.0", "1.0.")
                .replace("beta", ".dev")
            )
        elif version is not None:
            for v in versions:
                if (
                    str(v["tag_name"])
                    .replace("v", "")
                    .replace("1.0.0", "1.0.")
                    .replace("beta", ".dev")
                    == version
                ):
                    versions = [v]
                    break
            else:
                await channel.send(_("This Ventoy version doesn't exists."))
                return
        else:
            versions = [versions[-1]]

        for version in versions:
            ventoy_tag_name = str(version["tag_name"])
            ventoy_version_str = (
                ventoy_tag_name.replace("v", "").replace("1.0.0", "1.0.").replace("beta", ".dev")
            )
            ventoy_version = VersionInfo.from_str(ventoy_version_str)
            if not force and last_ventoy_version >= ventoy_version:
                continue

            ventoy_tag_body = str(version["body"])

            ventoy_tag_body = ventoy_tag_body.split("\n")
            result = []
            for x in ventoy_tag_body:
                if (
                    x
                    == "See [https://www.ventoy.net/en/doc_news.html](https://www.ventoy.net/en/doc_news.html) for more details.\r"
                ):
                    break
                if x != "\r":
                    result.append(x)
            ventoy_tag_body = "\n".join(result)
            changelog = box(ventoy_tag_body)

            embed: discord.Embed = discord.Embed()
            embed.set_thumbnail(url="https://ventoy.net/static/img/ventoy.png?v=1")
            embed.set_footer(
                text="From official Ventoy.",
                icon_url="https://ventoy.net/static/img/ventoy.png?v=1",
            )
            embed.url = "https://www.ventoy.net/en/doc_news.html"
            embed.title = _("Ventoy v{ventoy_version_str} has been released!").format(
                ventoy_version_str=ventoy_version_str
            )
            embed.description = _("New features:") + "\n" + changelog
            embed.add_field(
                name="More details:", value="https://www.ventoy.net/en/doc_news.html", inline=True
            )
            embed.add_field(
                name=_("Download this version:"),
                value=f"https://github.com/ventoy/Ventoy/releases/tag/{ventoy_tag_name}",
                inline=True,
            )
            role = guild.get_role(VENTOY_UPDATES_ROLE) if ping_role else None
            try:
                hook: discord.Webhook = await self.cogsutils.get_hook(channel)
                if self.cogsutils.is_dpy2:
                    view = discord.ui.View()
                    view.add_item(
                        discord.ui.Button(
                            label=_("View on Ventoy Official Website"),
                            url="https://www.ventoy.net/en/doc_news.html",
                            style=discord.ButtonStyle(5),
                        )
                    )
                    message: discord.Message = await hook.send(
                        content=role.mention if role is not None else None,
                        embed=embed,
                        username="Ventoy Updates",
                        avatar_url="https://ventoy.net/static/img/ventoy.png?v=1",
                        view=view,
                        allowed_mentions=discord.AllowedMentions(everyone=True, roles=True),
                        wait=True,
                    )
                else:
                    message: discord.Message = await hook.send(
                        content=role.mention if role is not None else None,
                        embed=embed,
                        username="Ventoy Updates",
                        avatar_url="https://ventoy.net/static/img/ventoy.png?v=1",
                        allowed_mentions=discord.AllowedMentions(everyone=True, roles=True),
                        wait=True,
                    )
            except (AttributeError, discord.errors.Forbidden):
                if self.cogsutils.is_dpy2:
                    view = discord.ui.View()
                    view.add_item(
                        discord.ui.Button(
                            label=_("View on Ventoy Official Website"),
                            url="https://www.ventoy.net/en/doc_news.html",
                            style=discord.ButtonStyle(5),
                        )
                    )
                    message: discord.Message = await channel.send(
                        content=role.mention if role is not None else None,
                        embed=embed,
                        view=view,
                        allowed_mentions=discord.AllowedMentions(everyone=True, roles=True),
                    )
                else:
                    message: discord.Message = await channel.send(
                        content=role.mention if role is not None else None,
                        embed=embed,
                        allowed_mentions=discord.AllowedMentions(everyone=True, roles=True),
                    )
            if message is not None:
                try:
                    await message.publish()
                except discord.HTTPException:
                    pass
        return versions

    async def bootables_tools_updates(
        self,
        channel: typing.Optional[discord.TextChannel] = None,
        ping_role: typing.Optional[bool] = True,
    ) -> None:
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
        last_bootables_tools_versions_str: typing.Dict = (
            await self.config.last_bootables_tools_versions()
        )

        tools_versions_str = {}
        for tool in BOOTABLES_TOOLS:
            if tool not in last_bootables_tools_versions_str:
                continue
            url = BOOTABLES_TOOLS[tool]["url"]
            last_tool_version_str = last_bootables_tools_versions_str[tool]
            async with self._session.get(url, timeout=3) as r:
                content = await r.text()
            # for x in r.split("\n"):
            #     if '"headline":' in x and '<html lang="en-US">' not in x:
            #         break
            # x = x.replace('    "headline": "', "").replace('",', "")
            soup = BeautifulSoup(content, "lxml")
            _json = json.loads(soup.find("script", class_="yoast-schema-graph").text)
            x = _json["@graph"][0]["headline"]
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
            embed.set_thumbnail(
                url="https://www.fcportables.com/wp-content/uploads/fcportables-logo.jpg"
            )
            embed.set_footer(
                text="From FCportables.",
                icon_url="https://www.fcportables.com/wp-content/uploads/fcportables-logo.jpg",
            )
            embed.url = url
            embed.title = _("{tool} now has a new version!").format(tool=tool)
            embed.description = f"[View on FCportables!]({url})"
            embed.add_field(name="Old version:", value=last_tool_version_str, inline=True)
            embed.add_field(name="New version:", value=tool_version_str, inline=True)
            embed.add_field(
                name="Category in Medicat USB:",
                value=BOOTABLES_TOOLS[tool]["category"],
                inline=False,
            )

            role = guild.get_role(BOOTABLES_TOOLS_UPDATE_ROLE) if ping_role else None
            try:
                hook: discord.Webhook = await self.cogsutils.get_hook(channel)
                if self.cogsutils.is_dpy2:
                    view = discord.ui.View()
                    view.add_item(
                        discord.ui.Button(
                            label=_("View on FCportables Official Website"),
                            url=url,
                            style=discord.ButtonStyle(5),
                        )
                    )
                    message: discord.Message = await hook.send(
                        content=role.mention if role is not None else None,
                        embed=embed,
                        username="Bootables Tools Updates",
                        avatar_url="https://www.fcportables.com/wp-content/uploads/fcportables-logo.jpg",
                        view=view,
                        allowed_mentions=discord.AllowedMentions(everyone=True, roles=True),
                        wait=True,
                    )
                else:
                    message: discord.Message = await hook.send(
                        content=role.mention if role is not None else None,
                        embed=embed,
                        username="Bootables Tools Updates",
                        avatar_url="https://www.fcportables.com/wp-content/uploads/fcportables-logo.jpg",
                        allowed_mentions=discord.AllowedMentions(everyone=True, roles=True),
                        wait=True,
                    )
            except (AttributeError, discord.errors.Forbidden):
                if self.cogsutils.is_dpy2:
                    view = discord.ui.View()
                    view.add_item(
                        discord.ui.Button(
                            label=_("View on FCportables Official Website"),
                            url=url,
                            style=discord.ButtonStyle(5),
                        )
                    )
                    message: discord.Message = await channel.send(
                        content=role.mention if role is not None else None,
                        embed=embed,
                        view=view,
                        allowed_mentions=discord.AllowedMentions(everyone=True, roles=True),
                    )
                else:
                    message: discord.Message = await channel.send(
                        content=role.mention if role is not None else None,
                        embed=embed,
                        allowed_mentions=discord.AllowedMentions(everyone=True, roles=True),
                    )
            if message is not None:
                try:
                    await message.publish()
                except discord.HTTPException:
                    pass
        await self.config.last_bootables_tools_versions.set(tools_versions_str)

    def in_medicat_guild():
        async def pred(ctx) -> bool:
            if ctx.author.id in ctx.bot.owner_ids:
                return True
            if ctx.guild is None:
                return False
            return ctx.guild.id in [MEDICAT_GUILD, TEST_GUILD]

        return commands.check(pred)

    def is_owner_or_AAA3A():
        async def pred(ctx) -> bool:
            return (
                ctx.author.id in ctx.bot.owner_ids
                or (ctx.author.id == 829612600059887649 and ctx.guild.id == MEDICAT_GUILD)
            )

        return commands.check(pred)

    @in_medicat_guild()
    @hybrid_group()
    async def medicat(self, ctx: commands.Context) -> None:
        """Commands of Medicat cog."""
        pass

    async def add_custom_commands(self) -> None:
        # def get_function_from_str(bot: Red, command: str):
        #     to_compile = "def func():\n%s" % textwrap.indent(command, "  ")
        #     env = {
        #         "bot": bot,
        #         "discord": discord,
        #         "commands": commands,
        #         "CUSTOM_COMMANDS": CUSTOM_COMMANDS,
        #         "medicat": self.medicat,
        #     }
        #     exec(to_compile, env)
        #     result = env["func"]()
        #     return result

        for name, text in CUSTOM_COMMANDS.items():
            try:
                self.medicat.remove_command(name)

                async def CC(self, ctx: commands.Context):
                    embed: discord.Embed = discord.Embed()
                    embed.set_thumbnail(url=MEDICAT_ICON_URL)
                    embed.set_footer(text="Medicat USB Official", icon_url=MEDICAT_ICON_URL)
                    embed.title = _(CUSTOM_COMMANDS[ctx.command.name]["title"])
                    embed.description = _(CUSTOM_COMMANDS[ctx.command.name]["description"])
                    await ctx.send(embed=embed)

                CC.__qualname__ = f"{self.qualified_name}.CC_{name}"
                setattr(CC, "__doc__", text["title"])  # Description, but translated with i18n.
                command: commands.Command = self.medicat.command(name=name, i18n=_)(CC)
                command.name = name
                # command.brief = text["title"]
                # command.description = text["title"]
                command.callback.__doc__ = text["title"]
                command.cog = self
                self.bot.dispatch("command_add", command)
                if self.bot.get_cog("permissions") is None:
                    command.requires.ready_event.set()
                if self.cogsutils.is_dpy2 and "ctx" in command.params:
                    del command.params["ctx"]
                setattr(self, f"CC_{name}", command)
            except Exception as e:
                self.log.error(
                    f"An error occurred while adding the `medicat {name}` custom command.",
                    exc_info=e,
                )
            else:
                cog_commands = list(self.__cog_commands__)
                cog_commands.append(command)
                self.__cog_commands__ = tuple(cog_commands)

        self.CC_added.set()

    def remove_custom_commands(self) -> None:
        for name in CUSTOM_COMMANDS:
            self.medicat.remove_command(name)

    @commands.Cog.listener()
    async def on_message_without_command(self, message: discord.Message) -> None:
        if message.webhook_id is not None or message.author.bot:
            return
        context = await self.bot.get_context(message)
        if context.prefix is None:
            return
        command = context.message.content[len(str(context.prefix)):]
        if len(command.split(" ")) == 0:
            return
        command_name = command.split(" ")[0]
        if command_name not in CUSTOM_COMMANDS:
            return
        await self.cogsutils.invoke_command(
            author=context.author,
            channel=context.channel,
            command=f"medicat {command}",
            prefix=context.prefix,
            message=context.message,
        )

    @commands.cooldown(rate=1, per=3600, type=commands.BucketType.member)
    @medicat.command()
    async def getlastventoyversion(self, ctx: commands.Context) -> None:
        """Get the latest version of Ventoy."""
        try:
            await self.ventoy_updates(channel=ctx.channel, ping_role=False, force=True)
        except Exception:
            raise commands.UserFeedbackCheckFailure(_("An error has occurred. Please try again."))

    @commands.cooldown(rate=1, per=3600, type=commands.BucketType.member)
    @medicat.command()
    async def getventoyversion(self, ctx: commands.Context, version: str) -> None:
        """Get a version of Ventoy."""
        try:
            await self.ventoy_updates(
                channel=ctx.channel, ping_role=False, force=True, version=version
            )
        except Exception:
            raise commands.UserFeedbackCheckFailure(_("An error has occurred. Please try again."))

    @commands.cooldown(rate=1, per=3600, type=commands.BucketType.member)
    @medicat.command()
    async def getlastbootablestoolsversions(self, ctx: commands.Context) -> None:
        """Get the latest versions of each Medicat USB bootable tool."""
        result = {}
        for tool in BOOTABLES_TOOLS:
            try:
                async with self._session.get(BOOTABLES_TOOLS[tool]["url"], timeout=3) as r:
                    content = await r.text()
                # for x in r.split("\n"):
                #     if '"headline":' in x and '<html lang="en-US">' not in x:
                #         break
                # x = x.replace('    "headline": "', "").replace('",', "")
                soup = BeautifulSoup(content, "lxml")
                _json = json.loads(soup.find("script", class_="yoast-schema-graph").text)
                x = _json["@graph"][0]["headline"]
                regex = re.compile(BOOTABLES_TOOLS[tool]["regex"], re.I).findall(x)
                regex = regex[0] if len(regex) > 0 else None
                regex = regex[0] if isinstance(regex, typing.Tuple) and len(regex) > 0 else regex
                result[tool] = regex
            except asyncio.TimeoutError:
                result[tool] = None
        embed: discord.Embed = discord.Embed()
        embed.set_thumbnail(
            url="https://www.fcportables.com/wp-content/uploads/fcportables-logo.jpg"
        )
        embed.set_footer(
            text="From FCportables.",
            icon_url="https://www.fcportables.com/wp-content/uploads/fcportables-logo.jpg",
        )
        embed.title = "Last bootables tools versions"
        embed.url = "https://www.fcportables.com/"
        embed.description = "\n".join(
            [f"{bold(name)} ➜ {value}" for name, value in result.items()]
        )
        try:
            hook: discord.Webhook = await self.cogsutils.get_hook(ctx.channel)
            if self.cogsutils.is_dpy2:
                view = discord.ui.View()
                view.add_item(
                    discord.ui.Button(
                        style=discord.ButtonStyle(5),
                        label=_("View FCportables Official Website"),
                        url="https://www.fcportables.com/"
                    )
                )
                await hook.send(
                    embed=embed,
                    username="Bootables Tools Updates",
                    avatar_url="https://www.fcportables.com/wp-content/uploads/fcportables-logo.jpg",
                    view=view,
                )
            else:
                await hook.send(
                    embed=embed,
                    username="Bootables Tools Updates",
                    avatar_url="https://www.fcportables.com/wp-content/uploads/fcportables-logo.jpg",
                )
        except (AttributeError, discord.errors.Forbidden):
            if self.cogsutils.is_dpy2:
                view = discord.ui.View()
                view.add_item(
                    discord.ui.Button(
                        style=discord.ButtonStyle(5),
                        label=_("View FCportables Official Website"),
                        url="https://www.fcportables.com/"
                    )
                )
                await ctx.send(embed=embed, view=view)
            else:
                await ctx.send(embed=embed)

    @is_owner_or_AAA3A()
    @medicat.command(hidden=True)
    async def debuglastbootablestoolsversions(self, ctx: commands.Context, *, url: str) -> None:
        """Get the debug for a FCportables's tool."""
        try:
            result = {
                "Settings": {
                    "Found": False,
                    "Name": None,
                    "Url": None,
                    "Category": None,
                    "Regex": None,
                },
                "Web request": {
                    "Web request url": None,
                    "Web request status": None,
                    "Web request result": None,
                },
                "Search for the tool name": {"Tool name line": None, "Tool name full": None},
                "Find version": {
                    "Regex used": None,
                    "Result 1": None,
                    "Result 2": None,
                    "Result 3": None,
                },
            }
            tool = None
            if url in BOOTABLES_TOOLS:
                tool = url
                url = BOOTABLES_TOOLS[tool]["url"]
            else:
                if not url.startswith("https://www.fcportables.com/"):
                    url = f"https://www.fcportables.com/{url}"
                if not url.endswith("/"):
                    url += "/"
                for t in BOOTABLES_TOOLS:
                    if BOOTABLES_TOOLS[t]["url"] == url:
                        tool = t
                        break
            if tool is not None:
                result["Settings"]["Found"] = True
                result["Settings"]["Name"] = tool
                result["Settings"]["Url"] = BOOTABLES_TOOLS[tool]["url"]
                result["Settings"]["Category"] = BOOTABLES_TOOLS[tool]["category"]
                result["Settings"]["Regex"] = BOOTABLES_TOOLS[tool]["regex"]
            async with self._session.get(url, timeout=3) as r:
                result["Web request"]["Web request url"] = r.url
                result["Web request"]["Web request status"] = r.status
                content = await r.text()
            result["Web request"]["Web request result"] = list(content.split("\n"))[20:29]
            # for x in r.split("\n"):
            #     if '"headline":' in x and '<html lang="en-US">' not in x:
            #         break
            # result["Search for the tool name"]["Tool name line"] = x
            # x = x.replace('    "headline": "', "").replace('",', "")
            # result["Search for the tool name"]["Tool name full"] = x
            soup = BeautifulSoup(content, "lxml")
            found = soup.find("script", class_="yoast-schema-graph")
            _json = json.loads(found.text)
            x = _json["@graph"][0]["headline"]
            result["Search for the tool name"]["Tool name line"] = str(found)[:301] + "\n..."
            result["Search for the tool name"]["Tool name full"] = x
            if tool is not None:
                result["Find version"]["Regex used"] = BOOTABLES_TOOLS[tool]["regex"]
                regex = re.compile(BOOTABLES_TOOLS[tool]["regex"], re.I).findall(x)
                result["Find version"]["Result 1"] = regex
                regex = regex[0] if len(regex) > 0 else None
                result["Find version"]["Result 2"] = regex
                regex = regex[0] if isinstance(regex, typing.Tuple) and len(regex) > 0 else regex
                result["Find version"]["Result 3"] = regex
        except Exception:
            pass
        message = ""
        for x in result:
            message += f"\n\n--------------- {x} ---------------"
            for y, z in result[x].items():
                message += f"\n{y}: {z}"
        await Menu(pages=message, box_language_py=True).start(ctx)

    @is_owner_or_AAA3A()
    @medicat.command(hidden=True)
    async def getdebugloopsstatus(self, ctx: commands.Context) -> None:
        """Get an embed for check loops status."""
        embeds = [loop.get_debug_embed() for loop in self.cogsutils.loops.values()]
        await Menu(pages=embeds).start(ctx)

    @is_owner_or_AAA3A()
    @medicat.command(hidden=True)
    async def update(self, ctx: commands.Context) -> None:
        """Update Medicat cog directly."""
        try:
            message = copy(ctx.message)
            if ctx.guild is not None:
                message.author = ctx.guild.get_member(
                    list(ctx.bot.owner_ids)[0]
                ) or ctx.bot.get_user(list(ctx.bot.owner_ids)[0])
            else:
                message.author = ctx.bot.get_user(list(ctx.bot.owner_ids)[0])
            message.content = f"{ctx.prefix}cog update medicat"
            context = await ctx.bot.get_context(message)
            context.assume_yes = True
            await ctx.bot.invoke(context)
        except Exception as e:
            traceback_error = "".join(traceback.format_exception(type(e), e, e.__traceback__))
            traceback_error = self.cogsutils.replace_var_paths(traceback_error)
            pages = [
                box(page, lang="py")
                for page in pagify(
                    traceback_error, shorten_by=15, page_length=1985
                )
            ]
            try:
                await Menu(pages=pages, timeout=30, delete_after_timeout=True).start(ctx)
            except discord.HTTPException:
                return

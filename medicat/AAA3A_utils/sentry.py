from redbot.core import commands  # isort:skip
from redbot.core.bot import Red  # isort:skip
from redbot.core import Config  # isort:skip
import typing  # isort:skip
import discord  # isort:skip

import asyncio
import re
from uuid import uuid4

import sentry_sdk
from redbot.core import __version__ as red_version
from redbot.core.utils.common_filters import INVITE_URL_RE

SNOWFLAKE_REGEX = r"\b\d{17,20}\b"
IP_V4_REGEX = (
    r"(\b25[0-5]|\b2[0-4][0-9]|\b[01]?[0-9][0-9]?)(\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)){3}"
)
IP_V6_REGEX = r"(([0-9a-fA-F]{1,4}:){7,7}[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,7}:|([0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,5}(:[0-9a-fA-F]{1,4}){1,2}|([0-9a-fA-F]{1,4}:){1,4}(:[0-9a-fA-F]{1,4}){1,3}|([0-9a-fA-F]{1,4}:){1,3}(:[0-9a-fA-F]{1,4}){1,4}|([0-9a-fA-F]{1,4}:){1,2}(:[0-9a-fA-F]{1,4}){1,5}|[0-9a-fA-F]{1,4}:((:[0-9a-fA-F]{1,4}){1,6})|:((:[0-9a-fA-F]{1,4}){1,7}|:)|fe80:(:[0-9a-fA-F]{0,4}){0,4}%[0-9a-zA-Z]{1,}|::(ffff(:0{1,4}){0,1}:){0,1}((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])|([0-9a-fA-F]{1,4}:){1,4}:((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9]))"

SENTRY_DSN = (
    "https://d67f82abaf0a4b4eb95016f4aa414e5d@o4504401396695040.ingest.sentry.io/4504401415897088"
)

# Thanks to Vexed for all this file (https://github.com/Vexed01/vex-cog-utils/blob/ba8adb3d270c968bc7ff3e3b977ac90ff752dca3/vexcogutils/sentry.py)!

# This is copied from the source code, but maybe true soon.
""" # SENTRY IS OPT-IN
#
# When a bot owner installes their first cog of mine, they will recieve a DM asking if they would
# like to start sending basic session data and error reporting, which applies to all of my cogs.
# They will then recieve a DM reminding then of their choice whenever they install one of my cogs.
#
# There are two types of messages sent to owners: "master" and "reminder":
# - The "master" message is the first message to the owner when they first load one of my cogs.
# - A "reminder" message will be sent whenever one of my cogs is loaded for the first time AND a
#   master message was sent previously. If Sentry is enabled, these will be sent every time a new
#   cog of mine is loaded. If Sentry is disabled, these will only be sent once per loading of a new
#   cog of mine IF it is the first cog loaded since last bot restart.
#   This has the added bonus of meaning that when this will be rolled out to all my cogs it will
#   only send 1 DM (or at least that's the plan...)
#
# I recommend anyone looking at this also takes a look at the Technical Details section of
# https://aaa3a-cogs.readthedocs.io/en/latest/repo_telemetry.html
#
# """


def _(untranslated: str) -> str:
    return untranslated


SENTRY_MASTER_MSG = _(
    "Hey there! This looks like the first time you're using AAA3A's cogs (or you just updated to "
    "a version which supports this). To help make this cog, and all my others, as good "
    "and bug-free as possible, I have **opt-in** telemetry and error reporting __which affects "
    "all of my (github.com/AAA3A-AAA3A's) cogs__ on the AAA3A-cogs repository, using Sentry. The "
    "telemetry consists of data on the cog release and performance data of backgroup tasks and "
    "loops (if applicable), and error reporting means that if something goes wrong the error and "
    "some associated data will be automatically sent to me so I can fix it quickly.\n\nA best "
    "effort is made to ensure no sensitive data is transmitted. For more information, including "
    "some technical details, visit <https://aaa3a-cogs.readthedocs.io/en/latest/repo_telemetry.html>\n\n"
    "**If you would like to opt-in to telemetry and error reporting, and help me develop my cogs, "
    "run the command `[p]AAA3A_utils telemetrywithsentry True`. `[p]` is your prefix.**\nNo data is collected "
    "relating to command usage."
)
SENTRY_REMINDER_ON = _(
    "Hey there! You just installed AAA3A's {} cog. This is a reminder that you previously enabled telemetry and error reporting, which applies to all of my cogs, and this one is no different.\n\nI would like to emphasise again that a best effort it made to remove sensitive data. You can see <https://aaa3a-cogs.readthedocs.io/en/latest/repo_telemetry.html> for more details and change your choice at any time with the `[p]AAA3A_utils telemetrywithsentry False` command, applying to all my cogs."
)
SENTRY_REMINDER_OFF = _(
    "Hey there! You just installed AAA3A's {} cog. This is a reminder that you previously chose not to enable telemetry and error reporting, which is also available in this cog. I hope you don't mind this reminder.\n\nI would like to emphasise again that a best effort it made to remove sensitive data. You can see <https://aaa3a-cogs.readthedocs.io/en/latest/repo_telemetry.html> for more details and change your choice at any time with the `[p]AAA3A_utils telemetrywithsentry True` command, applying to all my cogs."
)

__all__ = ["SentryHelper"]


class SentryHelper:
    def __init__(self, cog: commands.Cog) -> None:
        if cog.qualified_name != "AAA3A_utils":
            raise ValueError(cog.qualified_name)
        self.cog: commands.Cog = cog
        self.cogsutils = cog.cogsutils
        self.bot: Red = cog.cogsutils.bot
        self.last_errors: typing.Dict[str, typing.Dict[str, typing.Union[commands.Context, Exception]]] = {}

        self.sentry_enabled: typing.Optional[bool] = None
        self.send_reminders: bool = True
        self.uuid: typing.Optional[str] = None
        self.hubs: typing.Dict[str, sentry_sdk.Hub] = {}

        self.config: Config = cog.config
        self.sentry_global: typing.Dict[str, typing.Dict[str, typing.Union[int, bool, typing.Optional[str], typing.List[str]]]] = {
            "sentry": {
                "version": 1,
                "sentry_enabled": False,
                "master_msg_sent": False,
                "uuid": None,
                "cogs_notified": [],
            }
        }
        self.config.register_global(**self.sentry_global)

        asyncio.create_task(self._async_init())
        self.cogsutils.create_loop(
            function=self.periodic_session_restart, name="Sentry Helper", hours=1
        )

        self.dont_send_reminders: bool = False
        self.ready: asyncio.Event = asyncio.Event()

    async def _async_init(self) -> None:
        sentry_enabled = await self.config.sentry.sentry_enabled()
        self.sentry_enabled = sentry_enabled
        # always set it, really doesn't do much
        uuid = await self.config.sentry.uuid()
        if uuid is None:
            uuid = str(uuid4())
            await self.config.sentry.uuid.set(uuid)
        self.uuid = uuid
        self.ready.set()

    async def periodic_session_restart(self) -> None:
        if not self.sentry_enabled:
            return
        for hub in self.hubs.values():
            hub.end_session()
            hub.start_session()

    async def send_command_error(
        self,
        ctx: commands.Context,
        error: commands.CommandError,
        manually: typing.Optional[bool] = False,
    ) -> typing.Optional[typing.Union[str, bool]]:
        try:
            if ctx.cog is None:
                return
            if not manually:
                if not self.sentry_enabled:
                    return False
            hub = await self.get_sentry_hub(ctx.cog)
            if hub is None:
                return
            if isinstance(error, commands.CommandInvokeError):
                if self.cogsutils.is_dpy2 and isinstance(
                    ctx.command, discord.ext.commands.HybridCommand
                ):
                    _type = "[hybrid|text]"
                else:
                    _type = "[text]"
            elif self.cogsutils.is_dpy2 and isinstance(error, commands.HybridCommandError):
                _type = "[hybrid|slash]"
            else:
                return False
            message = f"Error in {_type} command '{ctx.command.qualified_name}'."
            with hub:
                hub.add_breadcrumb(category="command", message=message)
                try:
                    e = error.original  # type:ignore
                except AttributeError:
                    e = error
                event_id = hub.capture_exception(e)
            return event_id
        except Exception as e:
            if manually:
                raise e
            self.cog.log.error("Sending an error to Sentry failed.", exc_info=e)
            return False

    def remove_sensitive_data(self, event: dict, hint: dict) -> typing.Dict:
        """Remove sensitive data from the event. This should only be used by the Sentry SDK.
        This has two main parts:
        1) Remove any mentions of the bot's token
        2) Replace all IDs with a 4 digit number which originates from the timestamp of the ID
        3) Remove discord invites
        4) Replace var paths (userprofile, home, computer name, user name)
        Parameters
        ----------
        event : dict
            Event data
        hint : dict
            Event hint
        Returns
        -------
        dict
            The event dict with above stated sensitive data removed.
        """

        def regex_stuff(s: str) -> str:
            """Shorten any Discord IDs/snowflakes (basically any number 17-20 characters) to 4 digits
            by locating the timestamp and getting the last 4 digits - the milliseconds and the last
            digit of the second countsecond.
            Parameters
            ----------
            s : str
                String to shorten IDs in
            Returns
            -------
            str
                String with IDs shortened
            """
            s = re.sub(
                SNOWFLAKE_REGEX,
                lambda m: "[SHORTENED-ID-" + str(int(m.group()) >> 22)[-4:] + "]",
                s,
            )
            s = re.sub(IP_V4_REGEX, "IP_V4", s)
            s = re.sub(IP_V6_REGEX, "IP_V6", s)
            return re.sub(INVITE_URL_RE, "[DISCORD-INVITE-LINK]", s)

        def recursive_replace(
            d: typing.Union[typing.Dict[str, typing.Any], typing.List, str], token: str
        ) -> typing.Union[dict, str]:
            """Recursively replace text in keys and values of a dictionary.
            Parameters
            ----------
            d : Union[Dict[str, Any], str]
                Dict or item to replace text in
            token : str
                Token to remove
            Returns
            -------
            dict
                Safe dict
            """
            if isinstance(d, dict):
                return {
                    self.cogsutils.replace_var_paths(regex_stuff(k.replace(token, "[BOT-TOKEN]")))
                    if isinstance(k, str)
                    else k: recursive_replace(v, token)
                    for k, v in d.items()
                }
            if isinstance(d, list):
                return [
                    self.cogsutils.replace_var_paths(
                        regex_stuff(recursive_replace(i, token))
                    )  # type:ignore
                    if isinstance(i, str)
                    else recursive_replace(i, token)
                    for i in d
                ]
            return (
                self.cogsutils.replace_var_paths(regex_stuff(d.replace(token, "[BOT_TOKEN]")))
                if isinstance(d, str)
                else d
            )

        token = self.bot.http.token

        return recursive_replace(event, token)  # type:ignore

    async def enable_sentry(self) -> None:
        """Enable Sentry telemetry and error reporting."""
        await self.config.sentry.sentry_enabled.set(True)
        self.sentry_enabled = True
        self.dont_send_reminders = False
        for hub in self.hubs.values():
            hub.start_session()

    async def disable_sentry(self) -> None:
        """Enable Sentry telemetry and error reporting."""
        await self.config.sentry.sentry_enabled.set(False)
        self.sentry_enabled = False
        self.dont_send_reminders = True

        for hub in self.hubs.values():
            hub.end_session()

    async def get_sentry_hub(
        self, cog: commands.Cog, force: typing.Optional[bool] = False
    ) -> sentry_sdk.Hub:
        """Get a Sentry Hub and Client for a DSN. Each cog should have it's own hub.
        Returns
        -------
        Hub
            A Sentry Hub with a Client
        """
        if not self.ready.is_set():
            await self.ready.wait()
        if cog.qualified_name in self.hubs and not force:
            hub = self.hubs[cog.qualified_name]
            return hub
        if getattr(cog, "__version__", None) is None and getattr(cog, "__commit__", None) is None:
            try:
                nb_commits, version, commit = await self.cogsutils.get_cog_version(cog)
                cog.__version__ = version
                cog.__commit__ = commit
            except Exception:
                pass
        # not using sentry_sdk.init so other don't interfear with other CCs/cogs/packages
        # from https://github.com/getsentry/sentry-python/issues/610
        client = sentry_sdk.Client(
            dsn=SENTRY_DSN,
            traces_sample_rate=0.005,
            before_send=self.remove_sensitive_data,
            before_breadcrumb=self.remove_sensitive_data,
            release=f"AAA3A-cogs|{cog.qualified_name}@{getattr(cog, '__version__', 1.0)}|{getattr(cog, '__commit__', '')}",
            debug=False,
            max_breadcrumbs=25,
            server_name="[EXPUNGED]",
        )

        scope = sentry_sdk.Scope()
        scope.set_tag("cog_version", getattr(cog, "__version__", 1.0))
        scope.set_tag("cog_commit", getattr(cog, "__commit__", ""))
        scope.set_tag("red_release", red_version)
        scope.set_tag("dpy_release", discord.__version__)
        scope.set_user({"id": self.uuid})

        hub = sentry_sdk.Hub(client, scope)
        self.hubs[cog.qualified_name] = hub

        hub.start_session()
        return hub

    async def cog_unload(self, cog: commands.Cog) -> sentry_sdk.Hub:
        """Close the linked Sentry Hub.
        Returns
        -------
        Hub
            A Sentry Hub closed
        """
        hub = self.hubs.get(cog.qualified_name, None)
        if hub is None:
            return None
        hub.end_session()
        hub.client.close()
        del self.hubs[cog.qualified_name]
        return hub

    async def maybe_send_owners(self, cog: commands.Cog) -> None:
        if not self.ready.is_set():
            await self.ready.wait()
        if (
            self.cog is None
            or not hasattr(self.cog, "telemetrywithsentry")
            or getattr(self.cog.telemetrywithsentry, "__is_dev__", False)
        ):
            return  # Not send automatically errors tp Sentry for the moment.
        if not await self.config.sentry.master_msg_sent():
            self.dont_send_reminders = True
            await self.config.sentry.master_msg_sent.set(True)
            try:
                await self.bot.send_to_owners(SENTRY_MASTER_MSG.format(cog.qualified_name))
            except Exception:
                pass
            async with self.config.sentry.cogs_notified() as c_n:
                c_n.append(cog.qualified_name)
            return

        if cog.qualified_name in await self.config.sentry.cogs_notified():
            return
        if self.dont_send_reminders:
            async with self.config.sentry.cogs_notified() as c_n:
                c_n.append(cog.qualified_name)
            return
        try:
            if self.sentry_enabled:
                await self.bot.send_to_owners(SENTRY_REMINDER_ON.format(cog.qualified_name))
            else:
                self.dont_send_reminders = True
                await self.bot.send_to_owners(SENTRY_REMINDER_OFF.format(cog.qualified_name))
        except Exception:
            pass
        async with self.config.sentry.cogs_notified() as c_n:
            c_n.append(cog.qualified_name)

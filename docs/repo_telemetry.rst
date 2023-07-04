.. _telemetry:

Thanks to Vexed for this documentation and a part of the code to use Telemetry with Sentry!

Opt-in Telemetry and Error Reporting
====================================

I have **opt-in** telemetry and error reporting built into all of my (`github.com/AAA3A-AAA3A/AAA3A-cogs <https://github.com/AAA3A-AAA3A/AAA3A-cogs>`_) cogs.

Enabling or disabling it affects all of my cogs. If this command `[p]AAA3A_utils telemetrywithsentry` doesn't exist, then no data is being sent.
This is likely because you haven't updated yet.

I use a platform called Sentry (`sentry.io <https://sentry.io>`_) to collect this.

**No data is collected relating to command usage.**


Why collect this?
-----------------

Error reporting allows me to fix bugs better - with more context to
fix them faster and easier. Sentry has a variety of tools to help pinpoint
when a bug was introduced.

Performance data is collected mainly because I can't be everywhere: I want
to know if something is quite slow on some machines so I can try and
optimise it.

What's sent?
------------

**Where possible, only data associated with my cogs is sent.**

Everything that is sent is associated with a temporary session and permanent
user UUID. This UUID is random and can't be linked directly to you or your bot.
Anything that is sent includes some context/tags. This is basic information on
the setup of the system to help me identify how to reproduce a bug.

For **telemetry**, the performance of background tasks and loops (for example
config migration or time taken to check for updates in my Status cog) is
sometimes reported. As stated in the opening of this page, no performance of
commands is collected or sent. At the moment, only errors in commands are sent to Sentry.

For **error reporting**, whenever something goes wrong with my cogs (this could
be a command breaking or something in a background loop) the traceback is sent
along with some logs leading up to the error to try and help me work out why it
happened. Sentry also sends some variables for debugging.
In the future, some related config data (if applicable) might be
sent. The IDs in this will be shortened to unidentifiable timestamps, as
described below in :ref:`telemetry_sens_data`

No usage information is shared with Sentry and no errors from another cog are sent.


.. _telemetry_sens_data:

Sensitive data
--------------

A best effort is made to ensure that no sensitive data is sent. Client-side,
all data sent is scrubbed of Discord invite links and IP adress, and Discord IDs are
shortened to 4 digits (based on the timestamp of the ID - seconds and
milliseconds) - so they can't be used to
identify anything. In the very unlikely event your bot token makes it into the
data, this will also be removed. For technical details, see
:ref:`sentry_technical_details_scrubbing` below. Sentry also has some data scrubbing
on their side which should scrub most other sensitive fields. You can see
more info on this in `their docs <https://docs.sentry.io/product/data-management-settings/scrubbing/server-side-scrubbing/>`_.

Data collected is sent to Sentry directly
and as such I cannot see your IP address or your server/computer name. I will never share any data
from Sentry that could be used to identify anyone or stuff that gets past the filters for
removing sensitive data.

Technical details of Sentry
===========================

.. _sentry_technical_details_scrubbing:

Data scrubbing
--------------

Data scrubbing has three parts: removal of bot token, removal of Discord invites,
removal of IP adress and shortening of Discord IDs.

A simple `str.replace()` is used to replace the bot token with ``BOT-TOKEN``,
if it appears for any reason.

For invites, the regex provided in `Red's utils <https://github.com/Cog-Creators/Red-DiscordBot/blob/76bb65912ededdb58f72b9ed0dbb77071d22d4d5/redbot/core/utils/common_filters.py#L21>`_
is used and invites replaced with ``DISCORD-INVITE-LINK``

For IP adress, a regex found in internet is used for IPv4 and IPv6.

The shortening of Discord IDs is a little more complicated. Docs on these from
Discord are `here <https://discord.com/developers/docs/reference#snowflakes>`_
and will help explain this better.
In short, the timestamp of the ID is in the ID from bytes 63 to 22. To shorten IDs,
this is extracted and the seconds and milliseconds replace the ID. So, if an ID
had the timestamp of ``2021-08-18 19:23:45.114`` the extracted data will be
``5114``. This part is used because, for all intents and purposes it is random,
and that it couldn't be used (on it's own) to find the full ID. This means that
in the data I see on Sentry, IDs are quite likely to be unique but always the same
if they occur in different places. It's sort of like hashing but worse but easier
to implement with regex. This 4
digit ID is prefixed with ``SHORTENED-ID-``

The exact functions can be seen at https://github.com/AAA3A-AAA3A/AAA3A_utils/blob/main/AAA3A_utils/sentry.py

SentryHelper
~~~~~~~~~~~~

In AAA3A_utils, as part of the client-side Sentry set up, the SentryHelper class is used by the utils and initialize with
the cog `AAA3A_utils` (cog automatically loaded with all my cogs).

This utils has various things to reduce boilerplate in each cog.

.. _telemetry_config:

Config
~~~~~~

Setup data is stored in Red's config under the fictional cog name ``AAA3A_utils`` (cog added by all cog to add slash commands and other functionnalities)

Owner notifications
~~~~~~~~~~~~~~~~~~~
There are two types of messages sent to owners: "master" and "reminder":

- The "master" message is the first message to the owner when they first load one of my cogs.
- A "reminder" message will be sent whenever one of my cogs is loaded for the first time AND a
  master message was sent previously. If Sentry is enabled, these will be sent every time a new
  cog of mine is loaded. If Sentry is disabled, these will only be sent once per loading of a new
  cog of mine IF it is the first cog loaded since last bot restart.
  This has the added bonus of meaning that when this will be rolled out to all my cogs it will
  only send 1 DM (or at least that's the plan...)


To prevent repeated messages, a record of which cogs have been notified is stored in Config
(see above)

For the time being, you will not receive any messages, as the automatic sending of Sentry errors is still under development (although it works).
The manual way will be offered for each error directly and you can execute the displayed command.


Only catching errors for *my* cogs
----------------------------------

I override a function called ``cog_command_error`` in my cog classes. This means that
all *command* errors are sent through this if they are part of this cog. To also
ensure they are handled normally by Red/dpy, they are sent back to the bot's error
handler with ``unhandled_by_cog=True``.

.. code-block:: python

    # In the cog class
    async def cog_command_error(self, ctx: "commands.Context", error: "CommandError", unhandled_by_cog: bool = False):
        await self.bot.on_command_error(ctx, error, unhandled_by_cog=True)  # type:ignore  # Ensure main bot error handler still handles it as normal
        # Sentry logging here

For background loops and tasks, I generally already had full error catching and
handling. I just had to send the exception to Sentry as well as log it with Python's
logging module.

UUIDs
-----

I choose to use UUIDs as a way to separate users and allow for features like
Release Health to work. This are generated using the standard lib uuid package:

.. code-block:: python

    import uuid

    uuid.uuid4()  # a completely random UUID
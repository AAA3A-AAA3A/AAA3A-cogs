.. _reminders:
=========
Reminders
=========

This is the cog guide for the 'Reminders' cog. This guide contains the collection of commands which you can use in the cog.
Through this guide, ``[p]`` will always represent your prefix. Replace ``[p]`` with your own prefix when you use these commands in Discord.

.. note::

    Ensure that you are up to date by running ``[p]cog update reminders``.
    If there is something missing, or something that needs improving in this documentation, feel free to create an issue `here <https://github.com/AAA3A-AAA3A/AAA3A-cogs/issues>`_.
    This documentation is auto-generated everytime this cog receives an update.

--------------
About this cog
--------------

Don't forget anything anymore! Reminders in DMs, channels, FIFO commands scheduler, say scheduler... With 'Me Too', snooze and buttons.

--------
Commands
--------

Here are all the commands included in this cog (30):

* ``[p]remind [destination] [targets]... <time> [message_or_text]``
 Create a reminder with optional reminder text or message, in a channel with an user/role ping.

* ``[p]reminder``
 List, edit and delete existing reminders, or create FIFO/commands or Say reminders.

* ``[p]reminder clear [confirmation=False]``
 Clear all your existing reminders.

* ``[p]reminder edit <reminder>``
 Edit an existing Reminder from its ID.

* ``[p]reminder expires <reminder> <time>``
 Edit the expires time of an existing Reminder from its ID.

* ``[p]reminder fifo [destination] <time> <command>``
 Create a FIFO/command reminder. The chosen command will be executed with you as invoker. Don't provide the prefix.

* ``[p]reminder list [card=False] ["text"|"command"|"say"] ["expire"|"created"|"id"=expire]``
 List your existing reminders.

* ``[p]reminder remove [reminders]...``
 Remove existing Reminder(s) from their IDs.

* ``[p]reminder repeat <reminder> <repeat>``
 Edit the repeat of an existing Reminder from its ID.

* ``[p]reminder say [destination] <time> <text>``
 Create a reminder who will say/send text.

* ``[p]reminder text <reminder> <text>``
 Edit the text of an existing Reminder from its ID.

* ``[p]reminder timetips``
 Show time parsing tips.

* ``[p]reminder timezone <timezone>``
 Set your timezone for the time converter.

* ``[p]remindme <time> [message_or_text]``
 Create a reminder with optional reminder text or message.

* ``[p]setreminders``
 Configure Reminders.

* ``[p]setreminders clearuserreminders <user> [confirmation=False]``
 Clear all existing reminders for a user.

* ``[p]setreminders creationview <creation_view>``
 Send Creation view/buttons when reminders creation.

* ``[p]setreminders fifoallowed <fifo_allowed>``
 Allow or deny commands reminders for users (except bot owners).

* ``[p]setreminders getdebugloopsstatus``
 Get an embed to check loops status.

* ``[p]setreminders maximumuserreminders <maximum_user_reminders>``
 Change the reminders limit for each user (except bot owners).

* ``[p]setreminders metoo <me_too>``
 Show a `Me too` button in reminders.

* ``[p]setreminders migratefromfifo``
 Migrate Reminders from FIFO by Fox.

* ``[p]setreminders migratefromremindme``
 Migrate Reminders from RemindMe by PhasecoreX.

* ``[p]setreminders minimumrepeat <minimum_repeat>``
 Change the minimum minutes number for a repeat time.

* ``[p]setreminders modalconfig [confirmation=False]``
 Set all settings for the cog with a Discord Modal.

* ``[p]setreminders repeatallowed <repeat_allowed>``
 Enable or disabled repeat option for users (except bot owners).

* ``[p]setreminders resetsetting <setting>``
 Reset a setting.

* ``[p]setreminders secondsallowed <seconds_allowed>``
 Check reminders every 30 seconds instead of every 1 minute, to allow reminders with precise duration.

* ``[p]setreminders showsettings [with_dev=False]``
 Show all settings for the cog with defaults and values.

* ``[p]setreminders snoozeview <snooze_view>``
 Send Snooze view/buttons when reminders sending.

------------
Installation
------------

If you haven't added my repo before, lets add it first. We'll call it
"AAA3A-cogs" here.

.. code-block:: ini

    [p]repo add AAA3A-cogs https://github.com/AAA3A-AAA3A/AAA3A-cogs

Now, we can install Reminders.

.. code-block:: ini

    [p]cog install AAA3A-cogs reminders

Once it's installed, it is not loaded by default. Load it by running the following command:

.. code-block:: ini

    [p]load reminders

---------------
Further Support
---------------

Check out my docs `here <https://aaa3a-cogs.readthedocs.io/en/latest/>`_.
Mention me in the #support_other-cogs in the `cog support server <https://discord.gg/GET4DVk>`_ if you need any help.
Additionally, feel free to open an issue or pull request to this repo.

------
Credit
------

Thanks to Kreusada for the Python code to automatically generate this documentation!

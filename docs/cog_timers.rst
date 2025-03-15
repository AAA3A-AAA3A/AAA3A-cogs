.. _timers:
======
Timers
======

This is the cog guide for the ``Timers`` cog. This guide contains the collection of commands which you can use in the cog.
Through this guide, ``[p]`` will always represent your prefix. Replace ``[p]`` with your own prefix when you use these commands in Discord.

.. note::

    Ensure that you are up to date by running ``[p]cog update timers``.
    If there is something missing, or something that needs improving in this documentation, feel free to create an issue `here <https://github.com/AAA3A-AAA3A/AAA3A-cogs/issues>`_.
    This documentation is generated everytime this cog receives an update.

---------------
About this cog:
---------------

Make incredible timers, with a unique user experience!

---------
Commands:
---------

Here are all the commands included in this cog (37):

* ``[p]settimers``
 Commands to configure Timers.

* ``[p]settimers creatorroles <profile> <creator_roles>``
 Roles that can create timers.

* ``[p]settimers dmhost <profile> <dm_host>``
 DM the host when the timer ends.

* ``[p]settimers embedcolor <profile> <colour>``
 Embed color for the timers messages.

* ``[p]settimers emoji <profile> <emoji>``
 Emoji to use for the timers.

* ``[p]settimers emojicontent <profile> <emoji_content>``
 Emoji to use in the timers messages content.

* ``[p]settimers getdebugloopsstatus``
 Get an embed for check loop status.

* ``[p]settimers hostautomaticjoin <profile> <host_automatic_join>``
 Automatically join the host to the timer.

* ``[p]settimers imageurl <profile> <image_url>``
 Image URL for the timers messages.

* ``[p]settimers logschannel <profile> <logs_channel>``
 Channel where to log timers.

* ``[p]settimers managerroles <profile> <manager_roles>``
 Roles that can manage timers.

* ``[p]settimers modalconfig <profile> [confirmation=False]``
 Set all settings for the cog with a Discord Modal.

* ``[p]settimers ping <profile> <ping>``
 Ping the ping role when the timer starts.

* ``[p]settimers pingroles <profile> <ping_roles>``
 Roles to ping when the timer starts.

* ``[p]settimers profileadd <profile>``
 Create a new profile with defaults settings.

* ``[p]settimers profileclone <old_profile> <profile>``
 Clone an existing profile with his settings.

* ``[p]settimers profileremove <profile> [confirmation=False]``
 Remove an existing profile.

* ``[p]settimers profilerename <old_profile> <profile>``
 Rename an existing profile.

* ``[p]settimers profileslist``
 List the existing profiles.

* ``[p]settimers resetsetting <profile> <setting>``
 Reset a setting.

* ``[p]settimers showsettings <profile> [with_dev=False]``
 Show all settings for the cog with defaults and values.

* ``[p]settimers thankdonor <profile> <thank_donor>``
 Thank the donor when the timer starts.

* ``[p]settimers thumbnailurl <profile> <thumbnail_url>``
 Thumbnail URL for the timers messages.

* ``[p]timer``
 Make incredible timers, with a unique user experience.

* ``[p]timer cancel <timer>``
 Cancel a timer.

* ``[p]timer create [channel] [duration] <title> [kwargs_requirements_flags]``
 Create a timer.

* ``[p]timer end <timer>``
 End a timer.

* ``[p]timer explain``
 Explain how to use the timers creation commands.

* ``[p]timer invalidate <timer> <member>``
 Forcefully invalidate a member for a timer.

* ``[p]timer join <timer>``
 Join a timer.

* ``[p]timer leaderboard``
 Get the leaderboard of timers hosts.

* ``[p]timer leave <timer>``
 Leave a timer.

* ``[p]timer list ["all"|"active"|"scheduled"|"ended"=all]``
 List all active or 3-days ended timers.

* ``[p]timer participants <timer>``
 Get the participants of a timer.

* ``[p]timer settings [profile]``
 Show Timers settings.

* ``[p]timer show <timer>``
 Show a timer.

* ``[p]timer validate <timer> <member>``
 Forcefully validate a member for a timer.

------------
Installation
------------

If you haven't added my repo before, lets add it first. We'll call it "AAA3A-cogs" here.

.. code-block:: ini

    [p]repo add AAA3A-cogs https://github.com/AAA3A-AAA3A/AAA3A-cogs

Now, we can install Timers.

.. code-block:: ini

    [p]cog install AAA3A-cogs timers

Once it's installed, it is not loaded by default. Load it by running the following command:

.. code-block:: ini

    [p]load timers

----------------
Further Support:
----------------

Check out my docs `here <https://aaa3a-cogs.readthedocs.io/en/latest/>`_.
Mention me in the #support_other-cogs in the `cog support server <https://discord.gg/GET4DVk>`_ if you need any help.
Additionally, feel free to open an issue or pull request to this repo.

--------
Credits:
--------

Thanks to Kreusada for the Python code to automatically generate this documentation!
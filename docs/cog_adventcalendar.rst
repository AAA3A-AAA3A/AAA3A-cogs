.. _adventcalendar:
==============
AdventCalendar
==============

This is the cog guide for the ``AdventCalendar`` cog. This guide contains the collection of commands which you can use in the cog.
Through this guide, ``[p]`` will always represent your prefix. Replace ``[p]`` with your own prefix when you use these commands in Discord.

.. note::

    Ensure that you are up to date by running ``[p]cog update adventcalendar``.
    If there is something missing, or something that needs improving in this documentation, feel free to create an issue `here <https://github.com/AAA3A-AAA3A/AAA3A-cogs/issues>`_.
    This documentation is generated everytime this cog receives an update.

---------------
About this cog:
---------------

Set up an Advent Calendar for your members, with custom rewards or messages each day! Work in december only...

---------
Commands:
---------

Here are all the commands included in this cog (17):

* ``[p]adventcalendar``
 Open your Advent Calendar box for the day!

* ``[p]setadventcalendar``
 Set up the Advent Calendar for your server.

* ``[p]setadventcalendar blacklistroles <blacklist_roles>``
 Roles that cannot access the Advent Calendar.

* ``[p]setadventcalendar customrewardslogschannel <custom_rewards_logs_channel>``
 The channel where custom rewards logs will be sent.

* ``[p]setadventcalendar customrewardspingrole <role>``
 The role that will be pinged when custom rewards are given.

* ``[p]setadventcalendar enabled <enabled>``
 Whether the Advent Calendar is enabled in this server.

* ``[p]setadventcalendar includeopenermention <include_opener_mention>``
 Whether to include the opener's mention in all messages.

* ``[p]setadventcalendar madvent [member=<you>]``
 Get the Advent Calendar for a member.

* ``[p]setadventcalendar modalconfig [confirmation=False]``
 Set all settings for the cog with a Discord Modal.

* ``[p]setadventcalendar mstats [member=<you>]``
 Get the stats of the Advent Calendar for a member.

* ``[p]setadventcalendar pingalldaysmembersuntilyesterday``
 Ping all members who have opened all boxes until yesterday and have not opened today's box.

* ``[p]setadventcalendar prioritymultiplierroles <priority_multiplier_roles>``
 Roles that will have their rewards priority multiplied (set individually for each reward).

* ``[p]setadventcalendar resetsetting <setting>``
 Reset a setting.

* ``[p]setadventcalendar rewards``
 Set up the rewards for each day of the Advent Calendar.

* ``[p]setadventcalendar showsettings [with_dev=False]``
 Show all settings for the cog with defaults and values.

* ``[p]setadventcalendar stats``
 Get the stats of the Advent Calendar for the server.

* ``[p]setadventcalendar whitelistroles <whitelist_roles>``
 Roles that can access the Advent Calendar.

------------
Installation
------------

If you haven't added my repo before, lets add it first. We'll call it "AAA3A-cogs" here.

.. code-block:: ini

    [p]repo add AAA3A-cogs https://github.com/AAA3A-AAA3A/AAA3A-cogs

Now, we can install AdventCalendar.

.. code-block:: ini

    [p]cog install AAA3A-cogs adventcalendar

Once it's installed, it is not loaded by default. Load it by running the following command:

.. code-block:: ini

    [p]load adventcalendar

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
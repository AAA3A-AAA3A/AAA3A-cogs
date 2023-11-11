.. _guildstats:
==========
GuildStats
==========

This is the cog guide for the 'GuildStats' cog. This guide contains the collection of commands which you can use in the cog.
Through this guide, ``[p]`` will always represent your prefix. Replace ``[p]`` with your own prefix when you use these commands in Discord.

.. note::

    Ensure that you are up to date by running ``[p]cog update guildstats``.
    If there is something missing, or something that needs improving in this documentation, feel free to create an issue `here <https://github.com/AAA3A-AAA3A/AAA3A-cogs/issues>`_.
    This documentation is auto-generated everytime this cog receives an update.

--------------
About this cog
--------------

A cog to generate images with messages and voice stats, for members, roles, guilds, categories, text channels, voice channels and activities!

--------
Commands
--------

Here are all the commands included in this cog (23):

* ``[p]guildstats ["humans"|"bots"|"both"=humans] [show_graphic=False] <_object>``
 Generate images with messages and voice stats, for members, roles, guilds, categories, text channels, voice channels and activities.

* ``[p]guildstats activities ["humans"|"bots"|"both"=humans]``
 Display stats for activities in this guild.

* ``[p]guildstats activity ["humans"|"bots"|"both"=humans] <activity_name>``
 Display stats for a specific activity in this guild.

* ``[p]guildstats category ["humans"|"bots"|"both"=humans] [show_graphic=False] [category]``
 Display stats for a specified category.

* ``[p]guildstats channel ["humans"|"bots"|"both"=humans] [show_graphic=False] [channel]``
 Display stats for a specified channel.

* ``[p]guildstats disable``
 Disable the cog in this guild/server.

* ``[p]guildstats enable``
 Enable the cog in this guild/server.

* ``[p]guildstats getdebugloopsstatus``
 Get an embed for check loop status.

* ``[p]guildstats graphic ["humans"|"bots"|"both"=humans] [_object]``
 Display graphic for members, roles guilds, text channels, voice channels and activities.

* ``[p]guildstats guild ["humans"|"bots"|"both"=humans] [show_graphic=False]``
 Display stats for this guild.

* ``[p]guildstats ignoreactivity <activity_name>``
 Ignore or unignore a specific activity.

* ``[p]guildstats ignorecategory <category>``
 Ignore or unignore a specific category.

* ``[p]guildstats ignorechannel <channel>``
 Ignore or unignore a specific channel.

* ``[p]guildstats ignoreme``
 Asking GuildStats to ignore your actions.

* ``[p]guildstats ignoreuser <user>``
 Ignore or unignore a specific user.

* ``[p]guildstats member [show_graphic=False] [member]``
 Display stats for a specified member.

* ``[p]guildstats messages ["humans"|"bots"|"both"=humans] [show_graphic=False]``
 Display stats for the messages in this guild.

* ``[p]guildstats purge <"all"|"messages"|"voice"|"activities">``
 Purge Config for the current guild.

* ``[p]guildstats role [show_graphic=False] [role]``
 Display stats for a specified role.

* ``[p]guildstats setdefaultstate <state>``
 Enable or disable by default the cog in the bot guilds.

* ``[p]guildstats toggleactivitiesstats <state>``
 Enable or disable activities stats.

* ``[p]guildstats top ["humans"|"bots"|"both"] <"messages"|"voice"> <"members"|"channels">``
 Display top stats for voice/messages members/channels.

* ``[p]guildstats voice ["humans"|"bots"|"both"=humans] [show_graphic=False]``
 Display stats for the voice in this guild.

------------
Installation
------------

If you haven't added my repo before, lets add it first. We'll call it
"AAA3A-cogs" here.

.. code-block:: ini

    [p]repo add AAA3A-cogs https://github.com/AAA3A-AAA3A/AAA3A-cogs

Now, we can install GuildStats.

.. code-block:: ini

    [p]cog install AAA3A-cogs guildstats

Once it's installed, it is not loaded by default. Load it by running the following command:

.. code-block:: ini

    [p]load guildstats

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

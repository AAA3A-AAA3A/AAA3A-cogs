.. _discordedit:
===========
DiscordEdit
===========

This is the cog guide for the 'DiscordEdit' cog. This guide contains the collection of commands which you can use in the cog.
Through this guide, ``[p]`` will always represent your prefix. Replace ``[p]`` with your own prefix when you use these commands in Discord.

.. note::

    Ensure that you are up to date by running ``[p]cog update discordedit``.
    If there is something missing, or something that needs improving in this documentation, feel free to create an issue `here <https://github.com/AAA3A-AAA3A/AAA3A-cogs/issues>`_.
    This documentation is auto-generated everytime this cog receives an update.

--------------
About this cog
--------------

A cog to edit Discord default objects!

--------
Commands
--------

Here are all the commands included in this cog (33):

* ``[p]editrole``
 Commands for edit a role.

* ``[p]editrole colour <role> <colour>``
 Edit role colour.

* ``[p]editrole create [colour=None] <name>``
 Create a role.

* ``[p]editrole delete <role> [confirmation=False]``
 Delete role.

* ``[p]editrole mentionable <role> <mentionable>``
 Edit role mentionable.

* ``[p]editrole name <role> <name>``
 Edit role name.

* ``[p]editrole permissions <role> <permissions>``
 Edit role permissions.

* ``[p]editrole position <role> <position>``
 Edit role position.

* ``[p]edittextchannel``
 Commands for edit a text channel.

* ``[p]edittextchannel category [channel] <category>``
 Edit text channel category.

* ``[p]edittextchannel clone [channel] <name>``
 Clone a text channel.

* ``[p]edittextchannel create [category=None] <name>``
 Create a text channel.

* ``[p]edittextchannel defaultautoarchiveduration [channel] <"60"|"1440"|"4320"|"10080">``
 Edit text channel default auto archive duration.

* ``[p]edittextchannel delete [channel] [confirmation=False]``
 Delete text channel.

* ``[p]edittextchannel name [channel] <name>``
 Edit text channel name.

* ``[p]edittextchannel nsfw [channel] <nsfw>``
 Edit text channel nsfw.

* ``[p]edittextchannel position [channel] <position>``
 Edit text channel position.

* ``[p]edittextchannel slowmodedelay [channel] <slowmode_delay>``
 Edit text channel slowmode delay.

* ``[p]edittextchannel syncpermissions [channel] <sync_permissions>``
 Edit text channel syncpermissions with category.

* ``[p]edittextchannel topic [channel] <topic>``
 Edit text channel topic.

* ``[p]edittextchannel type [channel] <"0"|"5">``
 Edit text channel type.

* ``[p]editvoicechannel``
 Commands for edit a voice channel.

* ``[p]editvoicechannel bitrate <channel> <bitrate>``
 Edit voice channel bitrate.

* ``[p]editvoicechannel category <channel> <category>``
 Edit voice channel category.

* ``[p]editvoicechannel clone <channel> <name>``
 Clone a voice channel.

* ``[p]editvoicechannel create [category=None] <name>``
 Create a voice channel.

* ``[p]editvoicechannel delete <channel> [confirmation=False]``
 Delete voice channel.

* ``[p]editvoicechannel name <channel> <name>``
 Edit voice channel name.

* ``[p]editvoicechannel nsfw <channel> <nsfw>``
 Edit voice channel nsfw.

* ``[p]editvoicechannel position <channel> <position>``
 Edit voice channel position.

* ``[p]editvoicechannel syncpermissions <channel> <sync_permissions>``
 Edit voice channel sync permissions.

* ``[p]editvoicechannel userlimit <channel> <user_limit>``
 Edit voice channel user limit.

* ``[p]editvoicechannel videoqualitymode <channel> <"1"|"2">``
 Edit voice channel video quality mode.

------------
Installation
------------

If you haven't added my repo before, lets add it first. We'll call it
"AAA3A-cogs" here.

.. code-block:: ini

    [p]repo add AAA3A-cogs https://github.com/AAA3A-AAA3A/AAA3A-cogs

Now, we can install DiscordEdit.

.. code-block:: ini

    [p]cog install AAA3A-cogs discordedit

Once it's installed, it is not loaded by default. Load it by running the following command:

.. code-block:: ini

    [p]load discordedit

---------------
Further Support
---------------

Check out my docs `here <https://aaa3a-cogs.readthedocs.io/en/latest/>`_.
Mention me in the #support_other-cogs in the `cog support server <https://discord.gg/GET4DVk>`_ if you need any help.
Additionally, feel free to open an issue or pull request to this repo.

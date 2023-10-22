.. _snipe:
=====
Snipe
=====

This is the cog guide for the 'Snipe' cog. This guide contains the collection of commands which you can use in the cog.
Through this guide, ``[p]`` will always represent your prefix. Replace ``[p]`` with your own prefix when you use these commands in Discord.

.. note::

    Ensure that you are up to date by running ``[p]cog update snipe``.
    If there is something missing, or something that needs improving in this documentation, feel free to create an issue `here <https://github.com/AAA3A-AAA3A/AAA3A-cogs/issues>`_.
    This documentation is auto-generated everytime this cog receives an update.

--------------
About this cog
--------------

Bulk sniping deleted and edited messages, for moderation purpose!

--------
Commands
--------

Here are all the commands included in this cog (24):

* ``[p]esnipe [channel] [index=0]``
 Bulk snipe edited messages.

* ``[p]esnipe bulk [channel]``
 Bulk snipe edited messages.

* ``[p]esnipe embeds [channel]``
 Bulk snipe edited messages with embeds.

* ``[p]esnipe index [channel] [index=0]``
 Snipe an edited message.

* ``[p]esnipe list [channel] [member]``
 List edited messages.

* ``[p]esnipe member [channel] <member>``
 Bulk snipe edited messages for the specified member.

* ``[p]esnipe membersmentions [channel]``
 Bulk snipe edited messages with members mentions.

* ``[p]esnipe mentions [channel]``
 Bulk snipe edited messages with roles/users mentions.

* ``[p]esnipe rolesmentions [channel]``
 Bulk snipe edited messages with roles mentions.

* ``[p]setsnipe``
 Commands to configure Snipe.

* ``[p]setsnipe ignored <ignored>``
 Set if the deleted and edited messages in this guild will be ignored.

* ``[p]setsnipe ignoredchannels <ignored_channels>``
 Set the channels in which deleted and edited messages will be ignored.

* ``[p]setsnipe modalconfig [confirmation=False]``
 Set all settings for the cog with a Discord Modal.

* ``[p]setsnipe resetsetting <setting>``
 Reset a setting.

* ``[p]setsnipe showsettings [with_dev=False]``
 Show all settings for the cog with defaults and values.

* ``[p]snipe [channel] [index=0]``
 Bulk snipe deleted messages.

* ``[p]snipe bulk [channel]``
 Bulk snipe deleted messages.

* ``[p]snipe embeds [channel]``
 Bulk snipe deleted messages with embeds.

* ``[p]snipe index [channel] [index=0]``
 Snipe a deleted message.

* ``[p]snipe list [channel] [member]``
 List deleted messages.

* ``[p]snipe member [channel] <member>``
 Bulk snipe deleted messages for the specified member.

* ``[p]snipe membersmentions [channel]``
 Bulk snipe deleted messages with members mentions.

* ``[p]snipe mentions [channel]``
 Bulk snipe deleted messages with roles/users mentions.

* ``[p]snipe rolesmentions [channel]``
 Bulk snipe deleted messages with roles mentions.

------------
Installation
------------

If you haven't added my repo before, lets add it first. We'll call it
"AAA3A-cogs" here.

.. code-block:: ini

    [p]repo add AAA3A-cogs https://github.com/AAA3A-AAA3A/AAA3A-cogs

Now, we can install Snipe.

.. code-block:: ini

    [p]cog install AAA3A-cogs snipe

Once it's installed, it is not loaded by default. Load it by running the following command:

.. code-block:: ini

    [p]load snipe

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

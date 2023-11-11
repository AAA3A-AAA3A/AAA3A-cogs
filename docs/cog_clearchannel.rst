.. _clearchannel:
============
ClearChannel
============

This is the cog guide for the 'ClearChannel' cog. This guide contains the collection of commands which you can use in the cog.
Through this guide, ``[p]`` will always represent your prefix. Replace ``[p]`` with your own prefix when you use these commands in Discord.

.. note::

    Ensure that you are up to date by running ``[p]cog update clearchannel``.
    If there is something missing, or something that needs improving in this documentation, feel free to create an issue `here <https://github.com/AAA3A-AAA3A/AAA3A-cogs/issues>`_.
    This documentation is auto-generated everytime this cog receives an update.

--------------
About this cog
--------------

A cog to delete ALL messages of a channel!

⚠ The channel will be cloned, and then **deleted**.

--------
Commands
--------

Here are all the commands included in this cog (9):

* ``[p]clearchannel [confirmation=False]``
 Delete ALL messages from the current channel by duplicating it and then deleting it.

* ``[p]setclearchannel``
 Configure ClearChannel for your server.

* ``[p]setclearchannel channeldelete <channel_delete>``
 If this option is disabled, the bot will not delete the original channel: it will duplicate it as normal, but move it to the end of the server's channel list.

* ``[p]setclearchannel custommessage <custom_message>``
 Specify a custom message to be sent from the link of another message or a json (https://discohook.org/ for example).

* ``[p]setclearchannel dmauthor <dm_author>``
 If this option is enabled, the bot will try to send a dm to the author of the order to confirm that everything went well.

* ``[p]setclearchannel firstmessage <first_message>``
 If this option is enabled, the bot will send a message to the emptied channel to inform that it has been emptied.

* ``[p]setclearchannel modalconfig [confirmation=False]``
 Set all settings for the cog with a Discord Modal.

* ``[p]setclearchannel resetsetting <setting>``
 Reset a setting.

* ``[p]setclearchannel showsettings [with_dev=False]``
 Show all settings for the cog with defaults and values.

------------
Installation
------------

If you haven't added my repo before, lets add it first. We'll call it
"AAA3A-cogs" here.

.. code-block:: ini

    [p]repo add AAA3A-cogs https://github.com/AAA3A-AAA3A/AAA3A-cogs

Now, we can install ClearChannel.

.. code-block:: ini

    [p]cog install AAA3A-cogs clearchannel

Once it's installed, it is not loaded by default. Load it by running the following command:

.. code-block:: ini

    [p]load clearchannel

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

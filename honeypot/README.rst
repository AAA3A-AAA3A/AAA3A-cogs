.. _honeypot:
========
Honeypot
========

This is the cog guide for the ``Honeypot`` cog. This guide contains the collection of commands which you can use in the cog.
Through this guide, ``[p]`` will always represent your prefix. Replace ``[p]`` with your own prefix when you use these commands in Discord.

.. note::

    Ensure that you are up to date by running ``[p]cog update honeypot``.
    If there is something missing, or something that needs improving in this documentation, feel free to create an issue `here <https://github.com/AAA3A-AAA3A/AAA3A-cogs/issues>`_.
    This documentation is generated everytime this cog receives an update.

---------------
About this cog:
---------------

Create a channel at the top of the server to attract self bots/scammers and notify/mute/kick/ban them immediately!

---------
Commands:
---------

Here are all the commands included in this cog (11):

* ``[p]sethoneypot``
 Set the honeypot settings. Only the server owner can use this command for security reasons.

* ``[p]sethoneypot action <action>``
 The action to take when a self bot/scammer is detected.

* ``[p]sethoneypot bandeletemessagedays <ban_delete_message_days>``
 The number of days of messages to delete when banning a self bot/scammer.

* ``[p]sethoneypot createchannel``
 Create the honeypot channel.

* ``[p]sethoneypot enabled <enabled>``
 Toggle the cog.

* ``[p]sethoneypot logschannel <logs_channel>``
 The channel to send the logs to.

* ``[p]sethoneypot modalconfig [confirmation=False]``
 Set all settings for the cog with a Discord Modal.

* ``[p]sethoneypot muterole <role>``
 The mute role to assign to the self bots/scammers, if the action is `mute`.

* ``[p]sethoneypot pingrole <role>``
 The role to ping when a self bot/scammer is detected.

* ``[p]sethoneypot resetsetting <setting>``
 Reset a setting.

* ``[p]sethoneypot showsettings [with_dev=False]``
 Show all settings for the cog with defaults and values.

------------
Installation
------------

If you haven't added my repo before, lets add it first. We'll call it "AAA3A-cogs" here.

.. code-block:: ini

    [p]repo add AAA3A-cogs https://github.com/AAA3A-AAA3A/AAA3A-cogs

Now, we can install Honeypot.

.. code-block:: ini

    [p]cog install AAA3A-cogs honeypot

Once it's installed, it is not loaded by default. Load it by running the following command:

.. code-block:: ini

    [p]load honeypot

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
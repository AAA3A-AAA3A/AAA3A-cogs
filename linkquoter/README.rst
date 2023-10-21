.. _linkquoter:
==========
LinkQuoter
==========

This is the cog guide for the 'LinkQuoter' cog. This guide contains the collection of commands which you can use in the cog.
Through this guide, ``[p]`` will always represent your prefix. Replace ``[p]`` with your own prefix when you use these commands in Discord.

.. note::

    Ensure that you are up to date by running ``[p]cog update linkquoter``.
    If there is something missing, or something that needs improving in this documentation, feel free to create an issue `here <https://github.com/AAA3A-AAA3A/AAA3A-cogs/issues>`_.
    This documentation is auto-generated everytime this cog receives an update.

--------------
About this cog
--------------

Quote any Discord message from its link!

--------
Commands
--------

Here are all the commands included in this cog (12):

* ``[p]linkquote [message]``
 

* ``[p]setlinkquoter``
 Commands to configure LinkQuoter.

* ``[p]setlinkquoter blacklistchannels <blacklist_channels>``
 Set the channels in which auto-quoting will be disabled.

* ``[p]setlinkquoter crossserver <cross_server>``
 Toggle cross-server quoting.

* ``[p]setlinkquoter deletemessage <delete_message>``
 Toggle deleting of messages for automatic quoting.

* ``[p]setlinkquoter enabled <enabled>``
 Toggle automatic link-quoting.

* ``[p]setlinkquoter migratefromlinkquoter``
 Migrate config from LinkQuoter by Phen.

* ``[p]setlinkquoter modalconfig [confirmation=False]``
 Set all settings for the cog with a Discord Modal.

* ``[p]setlinkquoter resetsetting <setting>``
 Reset a setting.

* ``[p]setlinkquoter showsettings [with_dev=False]``
 Show all settings for the cog with defaults and values.

* ``[p]setlinkquoter webhooks <webhooks>``
 Toggle deleting of messages for automatic quoting.

* ``[p]setlinkquoter whitelistchannels <whitelist_channels>``
 Set the channels in which auto-quoting will be enabled.

------------
Installation
------------

If you haven't added my repo before, lets add it first. We'll call it
"AAA3A-cogs" here.

.. code-block:: ini

    [p]repo add AAA3A-cogs https://github.com/AAA3A-AAA3A/AAA3A-cogs

Now, we can install LinkQuoter.

.. code-block:: ini

    [p]cog install AAA3A-cogs linkquoter

Once it's installed, it is not loaded by default. Load it by running the following command:

.. code-block:: ini

    [p]load linkquoter

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

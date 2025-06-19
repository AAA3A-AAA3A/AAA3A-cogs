.. _serversupporters:
================
ServerSupporters
================

This is the cog guide for the ``ServerSupporters`` cog. This guide contains the collection of commands which you can use in the cog.
Through this guide, ``[p]`` will always represent your prefix. Replace ``[p]`` with your own prefix when you use these commands in Discord.

.. note::

    Ensure that you are up to date by running ``[p]cog update serversupporters``.
    If there is something missing, or something that needs improving in this documentation, feel free to create an issue `here <https://github.com/AAA3A-AAA3A/AAA3A-cogs/issues>`_.
    This documentation is generated everytime this cog receives an update.

---------------
About this cog:
---------------

Track and give roles to supporters, members using the server tag or having a server invite link in their status!

---------
Commands:
---------

Here are all the commands included in this cog (10):

* ``[p]setserversupporters``
 Settings for the Server Supporters system.

* ``[p]setserversupporters enabled <enabled>``
 Whether the server supporters system is enabled.

* ``[p]setserversupporters forceupdate``
 Force update the roles of all members in the guild.

* ``[p]setserversupporters logschannel <logs_channel>``
 The channel where logs will be sent.

* ``[p]setserversupporters modalconfig [confirmation=False]``
 Set all settings for the cog with a Discord Modal.

* ``[p]setserversupporters resetsetting <setting>``
 Reset a setting.

* ``[p]setserversupporters showsettings [with_dev=False]``
 Show all settings for the cog with defaults and values.

* ``[p]setserversupporters statussupporterrole <status_supporter_role>``
 The role given to users who have the server invite link in their status.

* ``[p]setserversupporters tagabandonchannel <text channel>``
 The channel where users can abandon the server tag.

* ``[p]setserversupporters tagsupporterrole <tag_supporter_role>``
 The role given to users who use the server tag.

------------
Installation
------------

If you haven't added my repo before, lets add it first. We'll call it "AAA3A-cogs" here.

.. code-block:: ini

    [p]repo add AAA3A-cogs https://github.com/AAA3A-AAA3A/AAA3A-cogs

Now, we can install ServerSupporters.

.. code-block:: ini

    [p]cog install AAA3A-cogs serversupporters

Once it's installed, it is not loaded by default. Load it by running the following command:

.. code-block:: ini

    [p]load serversupporters

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
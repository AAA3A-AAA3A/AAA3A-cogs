.. _antinuke:
========
AntiNuke
========

This is the cog guide for the 'AntiNuke' cog. This guide contains the collection of commands which you can use in the cog.
Through this guide, ``[p]`` will always represent your prefix. Replace ``[p]`` with your own prefix when you use these commands in Discord.

.. note::

    Ensure that you are up to date by running ``[p]cog update antinuke``.
    If there is something missing, or something that needs improving in this documentation, feel free to create an issue `here <https://github.com/AAA3A-AAA3A/AAA3A-cogs/issues>`_.
    This documentation is auto-generated everytime this cog receives an update.

--------------
About this cog
--------------

A cog to remove all permissions from a person who deletes a channel!

--------
Commands
--------

Here are all the commands included in this cog (10):

* ``[p]setantinuke``
 Configure AntiNuke for your server.

* ``[p]setantinuke enabled <enabled>``
 Enable of disable AntiNuke system.

* ``[p]setantinuke logschannel <text channel>``
 Set a channel where events will be sent.

* ``[p]setantinuke modalconfig [confirmation=False]``
 Set all settings for the cog with a Discord Modal.

* ``[p]setantinuke nbbot <nbbot>``
 Before action, how many deleted channels should be detected for a bot? `0` to disable this protection.

* ``[p]setantinuke nbmember <nbmember>``
 Before action, how many deleted channels should be detected for a member? `0` to disable this protection.

* ``[p]setantinuke resetsetting <setting>``
 Reset a setting.

* ``[p]setantinuke resetuser <int>``
 Reset number detected for a user.

* ``[p]setantinuke showsettings [with_dev=False]``
 Show all settings for the cog with defaults and values.

* ``[p]setantinuke userdm <user_dm>``
 If enabled, the detected user will receive a DM.

------------
Installation
------------

If you haven't added my repo before, lets add it first. We'll call it
"AAA3A-cogs" here.

.. code-block:: ini

    [p]repo add AAA3A-cogs https://github.com/AAA3A-AAA3A/AAA3A-cogs

Now, we can install AntiNuke.

.. code-block:: ini

    [p]cog install AAA3A-cogs antinuke

Once it's installed, it is not loaded by default. Load it by running the following command:

.. code-block:: ini

    [p]load antinuke

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

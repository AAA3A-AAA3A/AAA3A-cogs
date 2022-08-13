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

Here are all the commands included in this cog (7):

* ``[p]setantinuke``
 Configure AntiNuke for your server.

* ``[p]setantinuke enable <true_or_false>``
 Enable or disable AntiNuke.

* ``[p]setantinuke logschannel <text_channel_or_'none'>``
 Set a channel where events are registered.

* ``[p]setantinuke nbbot <int>``
 Number Detected - Bot

* ``[p]setantinuke nbmember <int>``
 Number Detected - Member

* ``[p]setantinuke resetuser <int>``
 Reset number detected for a user

* ``[p]setantinuke userdm <true_or_false>``
 Enable or disable User DM.

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

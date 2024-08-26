.. _aaa3a_utils:
===========
AAA3A_utils
===========

This is the cog guide for the ``AAA3A_utils`` cog. This guide contains the collection of commands which you can use in the cog.
Through this guide, ``[p]`` will always represent your prefix. Replace ``[p]`` with your own prefix when you use these commands in Discord.

.. note::

    Ensure that you are up to date by running ``[p]cog update aaa3a_utils``.
    If there is something missing, or something that needs improving in this documentation, feel free to create an issue `here <https://github.com/AAA3A-AAA3A/AAA3A-cogs/issues>`_.
    This documentation is generated everytime this cog receives an update.

---------------
About this cog:
---------------

Commands to manage all the cogs in AAA3A-cogs repo!

---------
Commands:
---------

Here are all the commands included in this cog (10):

* ``[p]aaa3a_utils``
 All commands to manage all the cogs from AAA3A-cogs repo.

* ``[p]aaa3a_utils displaysentrymanualcommand <state>``
 Enable or disable displaying the command `[p]AAA3A_utils senderrorwithsentry` in commands errors.

* ``[p]aaa3a_utils flags <content>``
 Use any command with flags.

* ``[p]aaa3a_utils getallfor ["all"|"ALL"] [page] [repo] [check_updates=False] [cog] [command]``
 Get all the necessary information to get support on a bot/repo/cog/command.

* ``[p]aaa3a_utils getdebugloopsstatus <cog>``
 Get debug loops status for a cog from AAA3A-cogs.

* ``[p]aaa3a_utils getlogs <cog> [level=all]``
 Get logs for a cog from AAA3A-cogs

* ``[p]aaa3a_utils replacementvarpaths <state>``
 Replace various var paths in texts sent by cog from AAA3A-cogs.

* ``[p]aaa3a_utils resetconfig <cog> [confirmation=False]``
 Reset Config for a cog from AAA3A-cogs.

* ``[p]aaa3a_utils senderrorwithsentry <error>``
 Send a recent error to the developer of AAA3A's cogs with Sentry (use the code given when the error has been triggered).

* ``[p]aaa3a_utils telemetrywithsentry <state>``
 Enable or disable Telemetry with Sentry for all cogs from AAA3A-cogs.

------------
Installation
------------

If you haven't added my repo before, lets add it first. We'll call it "AAA3A-cogs" here.

.. code-block:: ini

    [p]repo add AAA3A-cogs https://github.com/AAA3A-AAA3A/AAA3A-cogs

Now, we can install AAA3A_utils.

.. code-block:: ini

    [p]cog install AAA3A-cogs aaa3a_utils

Once it's installed, it is not loaded by default. Load it by running the following command:

.. code-block:: ini

    [p]load aaa3a_utils

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
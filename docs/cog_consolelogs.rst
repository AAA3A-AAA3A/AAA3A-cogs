.. _consolelogs:
===========
ConsoleLogs
===========

This is the cog guide for the 'ConsoleLogs' cog. This guide contains the collection of commands which you can use in the cog.
Through this guide, ``[p]`` will always represent your prefix. Replace ``[p]`` with your own prefix when you use these commands in Discord.

.. note::

    Ensure that you are up to date by running ``[p]cog update consolelogs``.
    If there is something missing, or something that needs improving in this documentation, feel free to create an issue `here <https://github.com/AAA3A-AAA3A/AAA3A-cogs/issues>`_.
    This documentation is auto-generated everytime this cog receives an update.

--------------
About this cog
--------------

A cog to display the console logs, with buttons and filter options, and to send commands errors in configured channels!

--------
Commands
--------

Here are all the commands included in this cog (7):

* ``[p]consolelogs [lines_break=2] ["critical"|"error"|"warning"|"info"|"debug"|"trace"|"node"|"criticals"|"errors"|"warnings"|"infos"|"debugs"|"traces"|"nodes"] [ids] [logger_name]``
 View a console log, for a provided level/logger name.

* ``[p]consolelogs addchannel <channel> [global_errors=True] [prefixed_commands_errors=True] [slash_commands_errors=True] [dpy_ignored_exceptions=False] [full_console=False] [guild_invite=True] [ignored_cogs]``
 Enable errors logging in a channel.

* ``[p]consolelogs getdebugloopsstatus``
 Get an embed to check loops status.

* ``[p]consolelogs removechannel <channel>``
 Disable errors logging in a channel.

* ``[p]consolelogs scroll [lines_break=2] ["critical"|"error"|"warning"|"info"|"debug"|"trace"|"node"|"criticals"|"errors"|"warnings"|"infos"|"debugs"|"traces"|"nodes"] [ids] [logger_name]``
 Scroll the console logs, for all levels/loggers or provided level/logger name.

* ``[p]consolelogs stats``
 Display the stats for the bot logs since the bot start.

* ``[p]consolelogs view [index=-1] ["critical"|"error"|"warning"|"info"|"debug"|"trace"|"node"|"criticals"|"errors"|"warnings"|"infos"|"debugs"|"traces"|"nodes"] [ids] [logger_name]``
 View the console logs one by one, for all levels/loggers or provided level/logger name.

------------
Installation
------------

If you haven't added my repo before, lets add it first. We'll call it
"AAA3A-cogs" here.

.. code-block:: ini

    [p]repo add AAA3A-cogs https://github.com/AAA3A-AAA3A/AAA3A-cogs

Now, we can install ConsoleLogs.

.. code-block:: ini

    [p]cog install AAA3A-cogs consolelogs

Once it's installed, it is not loaded by default. Load it by running the following command:

.. code-block:: ini

    [p]load consolelogs

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

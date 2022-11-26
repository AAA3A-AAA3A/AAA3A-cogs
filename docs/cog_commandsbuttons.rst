.. _commandsbuttons:
===============
CommandsButtons
===============

This is the cog guide for the 'CommandsButtons' cog. This guide contains the collection of commands which you can use in the cog.
Through this guide, ``[p]`` will always represent your prefix. Replace ``[p]`` with your own prefix when you use these commands in Discord.

.. note::

    Ensure that you are up to date by running ``[p]cog update commandsbuttons``.
    If there is something missing, or something that needs improving in this documentation, feel free to create an issue `here <https://github.com/AAA3A-AAA3A/AAA3A-cogs/issues>`_.
    This documentation is auto-generated everytime this cog receives an update.

--------------
About this cog
--------------

A cog to allow a user to execute a command by clicking on a button!

--------
Commands
--------

Here are all the commands included in this cog (6):

* ``[p]commandsbuttons``
 Group of commands for use CommandsButtons.

* ``[p]commandsbuttons add <message> <emoji> <command> ["1"|"2"|"3"|"4"=2] [text_button=None]``
 Add a command-button to a message.

* ``[p]commandsbuttons bulk <message> [commands_buttons]...``
 Add commands-buttons to a message.

* ``[p]commandsbuttons clear <message>``
 Clear all commands-buttons to a message.

* ``[p]commandsbuttons purge``
 Clear all commands-buttons to a **guild**.

* ``[p]commandsbuttons remove <message> <emoji>``
 Remove a command-button to a message.

------------
Installation
------------

If you haven't added my repo before, lets add it first. We'll call it
"AAA3A-cogs" here.

.. code-block:: ini

    [p]repo add AAA3A-cogs https://github.com/AAA3A-AAA3A/AAA3A-cogs

Now, we can install CommandsButtons.

.. code-block:: ini

    [p]cog install AAA3A-cogs commandsbuttons

Once it's installed, it is not loaded by default. Load it by running the following command:

.. code-block:: ini

    [p]load commandsbuttons

---------------
Further Support
---------------

Check out my docs `here <https://aaa3a-cogs.readthedocs.io/en/latest/>`_.
Mention me in the #support_other-cogs in the `cog support server <https://discord.gg/GET4DVk>`_ if you need any help.
Additionally, feel free to open an issue or pull request to this repo.

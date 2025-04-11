.. _instantcommands:
===============
InstantCommands
===============

This is the cog guide for the ``InstantCommands`` cog. This guide contains the collection of commands which you can use in the cog.
Through this guide, ``[p]`` will always represent your prefix. Replace ``[p]`` with your own prefix when you use these commands in Discord.

.. note::

    Ensure that you are up to date by running ``[p]cog update instantcommands``.
    If there is something missing, or something that needs improving in this documentation, feel free to create an issue `here <https://github.com/AAA3A-AAA3A/AAA3A-cogs/issues>`_.
    This documentation is generated everytime this cog receives an update.

---------------
About this cog:
---------------

Create commands, listeners, dev values and dpy views from a code snippet!

---------
Commands:
---------

Here are all the commands included in this cog (6):

* ``[p]instantcommands``
 Create commands, listeners, dev values and dpy views from a code snippet.

* ``[p]instantcommands assignview <message> <name>``
 Assign a View code snippet to an existing message.

* ``[p]instantcommands create [code]``
 Instantly generate a new object from a code snippet.

* ``[p]instantcommands delete <"commands"|"hybrid_commands"|"slash_commands"|"dev_env_values"|"views"> <name>``
 Delete a code snippet from its type and its name.

* ``[p]instantcommands disable <"commands"|"hybrid_commands"|"slash_commands"|"dev_env_values"|"views"> <name>``
 Disable a code snippet from its type and its name.

* ``[p]instantcommands enable <"commands"|"hybrid_commands"|"slash_commands"|"dev_env_values"|"views"> <name>``
 Enable a code snippet from its type and its name.

------------
Installation
------------

If you haven't added my repo before, lets add it first. We'll call it "AAA3A-cogs" here.

.. code-block:: ini

    [p]repo add AAA3A-cogs https://github.com/AAA3A-AAA3A/AAA3A-cogs

Now, we can install InstantCommands.

.. code-block:: ini

    [p]cog install AAA3A-cogs instantcommands

Once it's installed, it is not loaded by default. Load it by running the following command:

.. code-block:: ini

    [p]load instantcommands

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
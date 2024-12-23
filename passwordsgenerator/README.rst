.. _onlyallow:
=========
OnlyAllow
=========

This is the cog guide for the ``OnlyAllow`` cog. This guide contains the collection of commands which you can use in the cog.
Through this guide, ``[p]`` will always represent your prefix. Replace ``[p]`` with your own prefix when you use these commands in Discord.

.. note::

    Ensure that you are up to date by running ``[p]cog update onlyallow``.
    If there is something missing, or something that needs improving in this documentation, feel free to create an issue `here <https://github.com/AAA3A-AAA3A/AAA3A-cogs/issues>`_.
    This documentation is generated everytime this cog receives an update.

---------------
About this cog:
---------------

Only allow users to execute specific commands or commands from specific cogs, on specific servers! If nothing is set in a server, all cogs/commands are permitted.

---------
Commands:
---------

Here are all the commands included in this cog (7):

* ``[p]onlyallow``
 Only allow users to execute specific commands or commands from specific cogs, on specific servers!

* ``[p]onlyallow addcog [guild] <cog>``
 Add a cog to the allowed cogs list in a server or the current one.

* ``[p]onlyallow addcommand [guild] <command>``
 Add a command to the allowed commands list in a server or the current one.

* ``[p]onlyallow clear [guild]``
 Clear the allowed cogs and commands list in a server or the current one.

* ``[p]onlyallow list``
 List the allowed cogs and commands in the server.

* ``[p]onlyallow removecog [guild] <cog>``
 Remove a cog from the allowed cogs list in a server or the current one.

* ``[p]onlyallow removecommand [guild] <command>``
 Remove a command from the allowed commands list in a server or the current one.

------------
Installation
------------

If you haven't added my repo before, lets add it first. We'll call it "AAA3A-cogs" here.

.. code-block:: ini

    [p]repo add AAA3A-cogs https://github.com/AAA3A-AAA3A/AAA3A-cogs

Now, we can install OnlyAllow.

.. code-block:: ini

    [p]cog install AAA3A-cogs onlyallow

Once it's installed, it is not loaded by default. Load it by running the following command:

.. code-block:: ini

    [p]load onlyallow

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
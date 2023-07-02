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

A cog to display the console logs, with buttons and filter options!

--------
Commands
--------

Here are all the commands included in this cog (5):

* ``[p]consolelogs [index=-1] ["critical"|"error"|"warning"|"info"|"debug"|"trace"|"node"=None] [logger_name=None]``
 View a console log, for a provided level/logger name.

* ``[p]consolelogs errors [index=-1] [logger_name=None]``
 View the `ERROR` console logs one by one, for all loggers or a provided logger name.

* ``[p]consolelogs scroll [lines_break=2] ["critical"|"error"|"warning"|"info"|"debug"|"trace"|"node"=None] [logger_name=None]``
 Scroll the console logs, for all levels/loggers or provided level/logger name.

* ``[p]consolelogs stats``
 Scroll the console logs, for all levels/loggers or provided level/logger name.

* ``[p]consolelogs view [index=-1] ["critical"|"error"|"warning"|"info"|"debug"|"trace"|"node"=None] [logger_name=None]``
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

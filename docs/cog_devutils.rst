.. _devutils:
========
DevUtils
========

This is the cog guide for the ``DevUtils`` cog. This guide contains the collection of commands which you can use in the cog.
Through this guide, ``[p]`` will always represent your prefix. Replace ``[p]`` with your own prefix when you use these commands in Discord.

.. note::

    Ensure that you are up to date by running ``[p]cog update devutils``.
    If there is something missing, or something that needs improving in this documentation, feel free to create an issue `here <https://github.com/AAA3A-AAA3A/AAA3A-cogs/issues>`_.
    This documentation is generated everytime this cog receives an update.

---------------
About this cog:
---------------

Various development utilities!

---------
Commands:
---------

Here are all the commands included in this cog (10):

* ``[p]devutils``
 Various development utilities.

* ``[p]devutils bypass <command>``
 Bypass a command's checks and cooldowns.

* ``[p]devutils do <times> [sequential=True] <command>``
 Repeats a command a specified number of times.

* ``[p]devutils execute [sequential=True] <commands_list>``
 Execute multiple commands at once. Split them using |.

* ``[p]devutils loglevel <level> [logger_name=red]``
 Change the logging level for a logger. If no name is provided, the root logger (`red`) is used.

* ``[p]devutils rawrequest <thing>``
 Display the JSON of a Discord object with a raw request.

* ``[p]devutils reinvoke [message]``
 Reinvoke a command message.

* ``[p]devutils reloadmodule [modules]...``
 Force reload a module (to use code changes without restarting your bot).

* ``[p]devutils stoptyping``
 Stop all bot typing tasks.

* ``[p]devutils timing <command>``
 Run a command timing execution and catching exceptions.

------------
Installation
------------

If you haven't added my repo before, lets add it first. We'll call it "AAA3A-cogs" here.

.. code-block:: ini

    [p]repo add AAA3A-cogs https://github.com/AAA3A-AAA3A/AAA3A-cogs

Now, we can install DevUtils.

.. code-block:: ini

    [p]cog install AAA3A-cogs devutils

Once it's installed, it is not loaded by default. Load it by running the following command:

.. code-block:: ini

    [p]load devutils

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
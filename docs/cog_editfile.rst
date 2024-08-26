.. _editfile:
========
EditFile
========

This is the cog guide for the ``EditFile`` cog. This guide contains the collection of commands which you can use in the cog.
Through this guide, ``[p]`` will always represent your prefix. Replace ``[p]`` with your own prefix when you use these commands in Discord.

.. note::

    Ensure that you are up to date by running ``[p]cog update editfile``.
    If there is something missing, or something that needs improving in this documentation, feel free to create an issue `here <https://github.com/AAA3A-AAA3A/AAA3A-cogs/issues>`_.
    This documentation is generated everytime this cog receives an update.

---------------
About this cog:
---------------

A cog to get a file and replace it from its path from Discord!

⚠️ This cog can be very dangerous, since it allows direct read/write/delete of files on the bot’s machine, considering the fact that reading the wrong file can expose sensitive information like tokens and deleting the wrong file can corrupt the bot or the system entirely.

---------
Commands:
---------

Here are all the commands included in this cog (8):

* ``[p]editfile``
 Commands group to get a file and replace it from its path.

* ``[p]editfile delete <path>``
 Delete a file.

* ``[p]editfile findcog <cog>``
 Get a cog directory on the bot's host machine from its name.

* ``[p]editfile get [menu=False] [show_line=False] <path>``
 Get a file on the bot's host machine from its path.

* ``[p]editfile listdir <path>``
 List all files/directories of a directory from its path.

* ``[p]editfile rename <new_name> <path>``
 Rename a file.

* ``[p]editfile replace <path> [content]``
 Replace a file on the bot's host machine from its path.

* ``[p]editfile treedir <path>``
 Make a tree with all files/directories of a directory from its path.

------------
Installation
------------

If you haven't added my repo before, lets add it first. We'll call it "AAA3A-cogs" here.

.. code-block:: ini

    [p]repo add AAA3A-cogs https://github.com/AAA3A-AAA3A/AAA3A-cogs

Now, we can install EditFile.

.. code-block:: ini

    [p]cog install AAA3A-cogs editfile

Once it's installed, it is not loaded by default. Load it by running the following command:

.. code-block:: ini

    [p]load editfile

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
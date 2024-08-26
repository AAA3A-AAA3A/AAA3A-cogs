.. _exportchannel:
=============
ExportChannel
=============

This is the cog guide for the ``ExportChannel`` cog. This guide contains the collection of commands which you can use in the cog.
Through this guide, ``[p]`` will always represent your prefix. Replace ``[p]`` with your own prefix when you use these commands in Discord.

.. note::

    Ensure that you are up to date by running ``[p]cog update exportchannel``.
    If there is something missing, or something that needs improving in this documentation, feel free to create an issue `here <https://github.com/AAA3A-AAA3A/AAA3A-cogs/issues>`_.
    This documentation is generated everytime this cog receives an update.

---------------
About this cog:
---------------

A cog to export all or a part of the messages of a channel in an html file!

---------
Commands:
---------

Here are all the commands included in this cog (9):

* ``[p]exportchannel``
 Export all or a part of the messages of a channel in an html file.

* ``[p]exportchannel after [channel] <after> ["html"|"txt"=html] [exclude_users_and_roles=[]]...``
 Export a part of the messages of a channel in an html file.

* ``[p]exportchannel all [channel] ["html"|"txt"=html] [exclude_users_and_roles=[]]...``
 Export all of a channel's messages to an html file.

* ``[p]exportchannel before [channel] <before> ["html"|"txt"=html] [exclude_users_and_roles=[]]...``
 Export a part of the messages of a channel in an html file.

* ``[p]exportchannel between [channel] <before> <after> ["html"|"txt"=html] [exclude_users_and_roles=[]]...``
 Export a part of the messages of a channel in an html file.

* ``[p]exportchannel bot [channel] [bot=True] [limit] ["html"|"txt"=html] [exclude_users_and_roles=[]]...``
 Export a part of the messages of a channel in an html file.

* ``[p]exportchannel message <message> ["html"|"txt"=html]``
 Export a specific message in an html file.

* ``[p]exportchannel messages [channel] <limit> ["html"|"txt"=html] [exclude_users_and_roles=[]]...``
 Export a part of the messages of a channel in an html file.

* ``[p]exportchannel user [channel] <user> [limit] ["html"|"txt"=html]``
 Export a part of the messages of a channel in an html file.

------------
Installation
------------

If you haven't added my repo before, lets add it first. We'll call it "AAA3A-cogs" here.

.. code-block:: ini

    [p]repo add AAA3A-cogs https://github.com/AAA3A-AAA3A/AAA3A-cogs

Now, we can install ExportChannel.

.. code-block:: ini

    [p]cog install AAA3A-cogs exportchannel

Once it's installed, it is not loaded by default. Load it by running the following command:

.. code-block:: ini

    [p]load exportchannel

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
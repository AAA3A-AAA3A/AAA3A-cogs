.. _transferchannel:
===============
TransferChannel
===============

This is the cog guide for the ``TransferChannel`` cog. This guide contains the collection of commands which you can use in the cog.
Through this guide, ``[p]`` will always represent your prefix. Replace ``[p]`` with your own prefix when you use these commands in Discord.

.. note::

    Ensure that you are up to date by running ``[p]cog update transferchannel``.
    If there is something missing, or something that needs improving in this documentation, feel free to create an issue `here <https://github.com/AAA3A-AAA3A/AAA3A-cogs/issues>`_.
    This documentation is generated everytime this cog receives an update.

---------------
About this cog:
---------------

A cog to transfer messages from a channel to another channel, with many options!

---------
Commands:
---------

Here are all the commands included in this cog (9):

* ``[p]transferchannel``
 Transfer messages from a channel to another channel, with many options. This might take a long time.

* ``[p]transferchannel after <source> <destination> <after> ["webhooks"|"embeds"|"messages"=webhooks] [exclude_users_and_roles=[]]...``
 Transfer a part of the messages from a channel to another channel. This might take a long time.

* ``[p]transferchannel all <source> <destination> ["webhooks"|"embeds"|"messages"=webhooks] [exclude_users_and_roles=[]]...``
 Transfer all messages from a channel to another channel. This might take a long time.

* ``[p]transferchannel before <source> <destination> <before> ["webhooks"|"embeds"|"messages"=webhooks] [exclude_users_and_roles=[]]...``
 Transfer a part of the messages from a channel to another channel. This might take a long time.

* ``[p]transferchannel between <source> <destination> <before> <after> ["webhooks"|"embeds"|"messages"=webhooks] [exclude_users_and_roles=[]]...``
 Transfer a part of the messages from a channel to another channel. This might take a long time.

* ``[p]transferchannel bot <source> <destination> [bot=True] [limit] ["webhooks"|"embeds"|"messages"=webhooks] [exclude_users_and_roles=[]]...``
 Transfer a part of the messages from a channel to another channel. This might take a long time.

* ``[p]transferchannel message <message> <destination> ["webhooks"|"embeds"|"messages"=webhooks]``
 Transfer a specific message to another channel. This might take a long time.

* ``[p]transferchannel messages <source> <destination> <limit> ["webhooks"|"embeds"|"messages"=webhooks] [exclude_users_and_roles=[]]...``
 Transfer a part of the messages from a channel to another channel. This might take a long time.

* ``[p]transferchannel user <source> <destination> <user> [limit] ["webhooks"|"embeds"|"messages"=webhooks]``
 Transfer a part of the messages from a channel to another channel. This might take a long time.

------------
Installation
------------

If you haven't added my repo before, lets add it first. We'll call it "AAA3A-cogs" here.

.. code-block:: ini

    [p]repo add AAA3A-cogs https://github.com/AAA3A-AAA3A/AAA3A-cogs

Now, we can install TransferChannel.

.. code-block:: ini

    [p]cog install AAA3A-cogs transferchannel

Once it's installed, it is not loaded by default. Load it by running the following command:

.. code-block:: ini

    [p]load transferchannel

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
.. _cmdchannel:
==========
CmdChannel
==========
This is the cog guide for the 'CmdChannel' cog. This guide contains the collection of commands which you can use in the cog.
Through this guide, ``[p]`` will always represent your prefix. Replace ``[p]`` with your own prefix when you use these commands in Discord.

.. note::

    Ensure that you are up to date by running ``[p]cog update cmdchannel``.
    If there is something missing, or something that needs improving in this documentation, feel free to create an issue `here <https://github.com/AAA3A-AAA3A/AAA3A-cogs/issues>`_.
    This documentation is auto-generated everytime this cog receives an update.

--------------
About this cog
--------------

A cog to send the result of a command to another channel!

--------
Commands
--------

Here are all the commands included in this cog (21):

* ``[p]cmdchannel [guild=None] [channel=None] [command]``
 Act as if the command had been typed in the channel of your choice.
* ``[p]cmdset``
 Configure Command for your server.
* ``[p]cmdset cmdchannel``
 Configure CmdChannel for your server.
* ``[p]cmdset cmdchannel confirmation <true_or_false>``
 Enable or disable confirmation.
* ``[p]cmdset cmdchannel delete <true_or_false>``
 Enable or disable message delete.
* ``[p]cmdset cmdchannel enable <true_or_false>``
 Enable or disable CommandChannel.
* ``[p]cmdset cmdchannel information <true_or_false>``
 Enable or disable information message.
* ``[p]cmdset cmduser``
 Configure CmdUser for your server.
* ``[p]cmdset cmduser confirmation <true_or_false>``
 Enable or disable confirmation.
* ``[p]cmdset cmduser delete <true_or_false>``
 Enable or disable message delete.
* ``[p]cmdset cmduser enable <true_or_false>``
 Enable or disable CommandUser.
* ``[p]cmdset cmduser information <true_or_false>``
 Enable or disable information message.
* ``[p]cmdset cmduserchannel``
 Configure CmdUserChannel for your server.
* ``[p]cmdset cmduserchannel confirmation <true_or_false>``
 Enable or disable confirmation.
* ``[p]cmdset cmduserchannel delete <true_or_false>``
 Enable or disable message delete.
* ``[p]cmdset cmduserchannel enable <true_or_false>``
 Enable or disable CommandUserChannel.
* ``[p]cmdset cmduserchannel information <true_or_false>``
 Enable or disable information message.
* ``[p]cmdset logschannel <text_channel_or_'none'>``
 Set a channel where events are registered.
* ``[p]cmduser [user=None] [command]``
 Act as if the command had been typed by imitating the specified user.
* ``[p]cmduserchannel [user=None] [channel=None] [command]``
 Act as if the command had been typed in the channel of your choice by imitating the specified user.
* ``[p]testvar``
 Test variables.

------------
Installation
------------

If you haven't added my repo before, lets add it first. We'll call it
"AAA3A-cogs" here.

.. code-block:: ini

    [p]repo add AAA3A-cogs https://github.com/AAA3A-AAA3A/AAA3A-cogs

Now, we can install CmdChannel.

.. code-block:: ini

    [p]cog install AAA3A-cogs cmdchannel

Once it's installed, it is not loaded by default. Load it by running the following command:

.. code-block:: ini

    [p]load cmdchannel

---------------
Further Support
---------------

For more support, head over to the `cog support server <https://discord.gg/GET4DVk>`_,
You can ask in #support_othercogs by pinging me.
You can also contact me by private message.

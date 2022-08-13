.. _simplesanction:
==============
SimpleSanction
==============

This is the cog guide for the 'SimpleSanction' cog. This guide contains the collection of commands which you can use in the cog.
Through this guide, ``[p]`` will always represent your prefix. Replace ``[p]`` with your own prefix when you use these commands in Discord.

.. note::

    Ensure that you are up to date by running ``[p]cog update simplesanction``.
    If there is something missing, or something that needs improving in this documentation, feel free to create an issue `here <https://github.com/AAA3A-AAA3A/AAA3A-cogs/issues>`_.
    This documentation is auto-generated everytime this cog receives an update.

--------------
About this cog
--------------

A cog to sanction a user!

--------
Commands
--------

Here are all the commands included in this cog (23):

* ``[p]sanction [user] [confirmation] [show_author] [finish_message] [fake_action] [duration_for_mute_or_ban] [reason_or_`not`]``
 Sanction a user quickly and easily.

* ``[p]sanction 01 [user] [confirmation] [show_author] [finish_message] [fake_action] [duration_for_mute_or_ban] [reason_or_`not`]``
 - :information_source: Show info on a user.

* ``[p]sanction 02 [user] [confirmation] [show_author] [finish_message] [fake_action] [duration_for_mute_or_ban] [reason_or_`not`]``
 - :warning: Set a simple warning on a user.

* ``[p]sanction 03 [user] [confirmation] [show_author] [finish_message] [fake_action] [duration_for_mute_or_ban] [reason_or_`not`]``
 - :hammer: Ban the member from the server.

* ``[p]sanction 04 [user] [confirmation] [show_author] [finish_message] [fake_action] [duration_for_mute_or_ban] [reason_or_`not`]``
 - :repeat_one: Softban the member from the server.

* ``[p]sanction 05 [user] [confirmation] [show_author] [finish_message] [fake_action] [duration_for_mute_or_ban] [reason_or_`not`]``
 - :dash: Tempban the member from the server.

* ``[p]sanction 06 [user] [confirmation] [show_author] [finish_message] [fake_action] [duration_for_mute_or_ban] [reason_or_`not`]``
 - :boot: Kick the member from the server.

* ``[p]sanction 07 [user] [confirmation] [show_author] [finish_message] [fake_action] [duration_for_mute_or_ban] [reason_or_`not`]``
 - :mute: Mute the user in all channels, including voice channels.

* ``[p]sanction 08 [user] [confirmation] [show_author] [finish_message] [fake_action] [duration_for_mute_or_ban] [reason_or_`not`]``
 - :punch: Mute the user in this channel.

* ``[p]sanction 09 [user] [confirmation] [show_author] [finish_message] [fake_action] [duration_for_mute_or_ban] [reason_or_`not`]``
 - :hourglass_flowing_sand: TempMute the user in all channels, including voice channels.

* ``[p]sanction 10 [user] [confirmation] [show_author] [finish_message] [fake_action] [duration_for_mute_or_ban] [reason_or_`not`]``
 - :hourglass: TempMute the user in this channel.

* ``[p]setsimplesanction``
 Configure SimpleSanction for your server.

* ``[p]setsimplesanction color <color_or_'none'>``
 Set a colour fort the embed.

* ``[p]setsimplesanction confirmation <true_or_false>``
 Enable or disable Action Confirmation

* ``[p]setsimplesanction deleteembed <true_or_false>``
 Enable or disable Delete Embed

* ``[p]setsimplesanction deletemessage <true_or_false>``
 Enable or disable Delete Message

* ``[p]setsimplesanction finishmessage <true_or_false>``
 Enable or disable Finish Message

* ``[p]setsimplesanction reasonrequired <true_or_false>``
 Enable or disable Reason Requiered

* ``[p]setsimplesanction showauthor <true_or_false>``
 Enable or disable Show Author

* ``[p]setsimplesanction thumbnail <link_or_'none'>``
 Set a thumbnail fort the embed.

* ``[p]setsimplesanction timeout <seconds_number_or_`none`>``
 Choose the timeout

* ``[p]setsimplesanction warnsystemuse <true_or_false>``
 Enable or disable Warn System Use

* ``[p]setsimplesanction way <"buttons"|"dropdown"|"reactions">``
 Enable or disable Buttons Use

------------
Installation
------------

If you haven't added my repo before, lets add it first. We'll call it
"AAA3A-cogs" here.

.. code-block:: ini

    [p]repo add AAA3A-cogs https://github.com/AAA3A-AAA3A/AAA3A-cogs

Now, we can install SimpleSanction.

.. code-block:: ini

    [p]cog install AAA3A-cogs simplesanction

Once it's installed, it is not loaded by default. Load it by running the following command:

.. code-block:: ini

    [p]load simplesanction

---------------
Further Support
---------------

Check out my docs `here <https://aaa3a-cogs.readthedocs.io/en/latest/>`_.
Mention me in the #support_other-cogs in the `cog support server <https://discord.gg/GET4DVk>`_ if you need any help.
Additionally, feel free to open an issue or pull request to this repo.

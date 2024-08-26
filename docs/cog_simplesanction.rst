.. _simplesanction:
==============
SimpleSanction
==============

This is the cog guide for the ``SimpleSanction`` cog. This guide contains the collection of commands which you can use in the cog.
Through this guide, ``[p]`` will always represent your prefix. Replace ``[p]`` with your own prefix when you use these commands in Discord.

.. note::

    Ensure that you are up to date by running ``[p]cog update simplesanction``.
    If there is something missing, or something that needs improving in this documentation, feel free to create an issue `here <https://github.com/AAA3A-AAA3A/AAA3A-cogs/issues>`_.
    This documentation is generated everytime this cog receives an update.

---------------
About this cog:
---------------

A cog to sanction members, with buttons!

---------
Commands:
---------

Here are all the commands included in this cog (22):

* ``[p]sanction [member] [confirmation] [show_author] [finish_message] [fake_action=False] [duration_for_mute_or_ban] [reason]``
 Sanction a member quickly and easily.

* ``[p]sanction 00 [member] [confirmation] [show_author] [finish_message] [fake_action=False] [duration_for_mute_or_ban] [reason]``
 - Sanction a member quickly and easily.

* ``[p]sanction 01 [member] [confirmation] [show_author] [finish_message] [fake_action=False] [reason]``
 - ℹ️ Show informations about a member.

* ``[p]sanction 02 [member] [confirmation] [show_author] [finish_message] [fake_action=False] [duration_for_mute_or_ban] [reason]``
 - ⚠️ Add a simple warning on a member.

* ``[p]sanction 03 [member] [confirmation] [show_author] [finish_message] [fake_action=False] [reason]``
 - 🔨 Ban a member from this server.

* ``[p]sanction 04 [member] [confirmation] [show_author] [finish_message] [fake_action=False] [reason]``
 - 🔂 SoftBan a member from this server.

* ``[p]sanction 05 [member] [confirmation] [show_author] [finish_message] [fake_action=False] [duration_for_mute_or_ban] [reason]``
 - 💨 TempBan a member from this server.

* ``[p]sanction 06 [member] [confirmation] [show_author] [finish_message] [fake_action=False] [reason]``
 - 👢 Kick a member from this server.

* ``[p]sanction 07 [member] [confirmation] [show_author] [finish_message] [fake_action=False] [reason]``
 - 🔇 Mute a member in all channels, including voice channels.

* ``[p]sanction 08 [member] [confirmation] [show_author] [finish_message] [fake_action=False] [reason]``
 - 👊 Mute a member in this channel.

* ``[p]sanction 09 [member] [confirmation] [show_author] [finish_message] [fake_action=False] [duration_for_mute_or_ban] [reason]``
 - ⏳ TempMute a member in all channels, including voice channels.

* ``[p]sanction 10 [member] [confirmation] [show_author] [finish_message] [fake_action=False] [duration_for_mute_or_ban] [reason]``
 - ⌛ TempMute a member in this channel.

* ``[p]setsimplesanction``
 Configure SimpleSanction for your server.

* ``[p]setsimplesanction actionconfirmation <action_confirmation>``
 Require a confirmation for each sanction (except userinfo).

* ``[p]setsimplesanction finishmessage <finish_message>``
 Send an embed after a sanction command execution.

* ``[p]setsimplesanction modalconfig [confirmation=False]``
 Set all settings for the cog with a Discord Modal.

* ``[p]setsimplesanction reasonrequired <reason_required>``
 Require a reason for each sanction (except userinfo).

* ``[p]setsimplesanction resetsetting <setting>``
 Reset a setting.

* ``[p]setsimplesanction showauthor <show_author>``
 Show the command author in embeds.

* ``[p]setsimplesanction showsettings [with_dev=False]``
 Show all settings for the cog with defaults and values.

* ``[p]setsimplesanction thumbnail <thumbnail>``
 Set the embed thumbnail.

* ``[p]setsimplesanction usewarnsystem <use_warn_system>``
 Use WarnSystem by Laggron for the sanctions.

------------
Installation
------------

If you haven't added my repo before, lets add it first. We'll call it "AAA3A-cogs" here.

.. code-block:: ini

    [p]repo add AAA3A-cogs https://github.com/AAA3A-AAA3A/AAA3A-cogs

Now, we can install SimpleSanction.

.. code-block:: ini

    [p]cog install AAA3A-cogs simplesanction

Once it's installed, it is not loaded by default. Load it by running the following command:

.. code-block:: ini

    [p]load simplesanction

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
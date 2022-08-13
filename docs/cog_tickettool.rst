.. _tickettool:
==========
TicketTool
==========

This is the cog guide for the 'TicketTool' cog. This guide contains the collection of commands which you can use in the cog.
Through this guide, ``[p]`` will always represent your prefix. Replace ``[p]`` with your own prefix when you use these commands in Discord.

.. note::

    Ensure that you are up to date by running ``[p]cog update tickettool``.
    If there is something missing, or something that needs improving in this documentation, feel free to create an issue `here <https://github.com/AAA3A-AAA3A/AAA3A-cogs/issues>`_.
    This documentation is auto-generated everytime this cog receives an update.

--------------
About this cog
--------------

A cog to manage a ticket system!

--------
Commands
--------

Here are all the commands included in this cog (37):

* ``[p]setticket``
 Configure TicketTool for your server.

* ``[p]setticket adminrole <role_or_'none'>``
 Set a role for administrators of the ticket system.

* ``[p]setticket auditlogs <true_or_false>``
 Make the author of each action concerning a ticket appear in the server logs.

* ``[p]setticket categoryclose <category_or_'none'>``
 Set a category where close tickets are created.

* ``[p]setticket categoryopen <category_or_'none'>``
 Set a category where open tickets are created.

* ``[p]setticket closeconfirmation <true_or_false>``
 Enable or disable Close Confirmation.

* ``[p]setticket closeonleave <true_or_false>``
 Enable or disable Close on Leave.

* ``[p]setticket color <color_or_'none'>``
 Set a colour for the embeds.

* ``[p]setticket createonreact <true_or_false>``
 Enable or disable Create on React.

* ``[p]setticket custommessage [custom_message=None]``
 Set the Custom Message.

* ``[p]setticket dynamicchannelname [dynamic_channel_name=None]``
 Set the Dinamic Ticket Channel Name.

* ``[p]setticket embedbutton <"title"|"description"|"image"|"placeholderdropdown"> [text=None]``
 Set the settings for the button embed.

* ``[p]setticket enable <true_or_false>``
 Enable or disable Ticket System

* ``[p]setticket logschannel <text_channel_or_'none'>``
 Set a channel where events are registered.

* ``[p]setticket message [channel=None] [message=None] [reason_options...]``
 Send a message with a button to open a ticket or dropdown with possible reasons.

* ``[p]setticket modlog <true_or_false>``
 Enable or disable Modlog.

* ``[p]setticket nbmax <int>``
 Max Number of tickets for a member.

* ``[p]setticket pingrole <role_or_'none'>``
 Set a role for pings on ticket creation.

* ``[p]setticket purge [confirmation=False]``
 Purge all existing tickets in the config. Does not delete any channels. All commands associated with the tickets will no longer work.

* ``[p]setticket renamechanneldropdown <true_or_false>``
 Enable or disable Rename Channel Dropdown.

* ``[p]setticket supportrole <role_or_'none'>``
 Set a role for helpers of the ticket system.

* ``[p]setticket thumbnail <link_or_'none'>``
 Set a thumbnail for the embeds.

* ``[p]setticket ticketrole <role_or_'none'>``
 Set a role for creaters of a ticket.

* ``[p]setticket usercanclose <true_or_false>``
 Enable or disable User Can Close.

* ``[p]setticket viewrole <role_or_'none'>``
 Set a role for viewers of tickets.

* ``[p]ticket``
 Commands for using the ticket system.

* ``[p]ticket add [members...] [reason=No reason provided.]``
 Add a member to an existing ticket.

* ``[p]ticket claim [member=None] [reason=No reason provided.]``
 Claim an existing ticket.

* ``[p]ticket close [confirmation=None] [reason=No reason provided.]``
 Close an existing ticket.

* ``[p]ticket create [reason=No reason provided.]``
 Create a ticket.

* ``[p]ticket delete [confirmation=False] [reason=No reason provided.]``
 Delete an existing ticket.

* ``[p]ticket export``
 Export all the messages of an existing ticket in html format.

* ``[p]ticket open [reason=No reason provided.]``
 Open an existing ticket.

* ``[p]ticket owner <new_owner> [reason=No reason provided.]``
 Change the owner of an existing ticket.

* ``[p]ticket remove [members...] [reason=No reason provided.]``
 Remove a member to an existing ticket.

* ``[p]ticket rename <new_name> [reason=No reason provided.]``
 Rename an existing ticket.

* ``[p]ticket unclaim [reason=No reason provided.]``
 Unclaim an existing ticket.

------------
Installation
------------

If you haven't added my repo before, lets add it first. We'll call it
"AAA3A-cogs" here.

.. code-block:: ini

    [p]repo add AAA3A-cogs https://github.com/AAA3A-AAA3A/AAA3A-cogs

Now, we can install TicketTool.

.. code-block:: ini

    [p]cog install AAA3A-cogs tickettool

Once it's installed, it is not loaded by default. Load it by running the following command:

.. code-block:: ini

    [p]load tickettool

---------------
Further Support
---------------

Check out my docs `here <https://aaa3a-cogs.readthedocs.io/en/latest/>`_.
Mention me in the #support_other-cogs in the `cog support server <https://discord.gg/GET4DVk>`_ if you need any help.
Additionally, feel free to open an issue or pull request to this repo.

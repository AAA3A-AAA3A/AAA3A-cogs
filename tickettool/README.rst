.. _tickettool:
==========
TicketTool
==========

This is the cog guide for the ``TicketTool`` cog. This guide contains the collection of commands which you can use in the cog.
Through this guide, ``[p]`` will always represent your prefix. Replace ``[p]`` with your own prefix when you use these commands in Discord.

.. note::

    Ensure that you are up to date by running ``[p]cog update tickettool``.
    If there is something missing, or something that needs improving in this documentation, feel free to create an issue `here <https://github.com/AAA3A-AAA3A/AAA3A-cogs/issues>`_.
    This documentation is generated everytime this cog receives an update.

---------------
About this cog:
---------------

A cog to manage a Tickets system!

---------
Commands:
---------

Here are all the commands included in this cog (48):

* ``[p]settickettool``
 Configure TicketTool for your server.

* ``[p]settickettool adminroles <profile> <admin_roles>``
 Users with this role will have full permissions for tickets, but will not be able to set up the cog.

* ``[p]settickettool auditlogs <profile> <audit_logs>``
 On all requests to the Discord api regarding the ticket (channel modification), does the bot send the name and id of the user who requested the action as the reason?

* ``[p]settickettool categoryclose <profile> <category channel>``
 Set the category where the closed tickets will be.

* ``[p]settickettool categoryopen <profile> <category channel>``
 Set the category where the opened tickets will be.

* ``[p]settickettool closeconfirmation <profile> <close_confirmation>``
 Should the bot ask for confirmation before closing the ticket (deletion will necessarily have a confirmation)?

* ``[p]settickettool closeonleave <profile> <close_on_leave>``
 If a user leaves the server, will all their open tickets be closed?

* ``[p]settickettool createonreact <profile> <create_on_react>``
 Create a ticket when the reaction 🎟️ is set on any message on the server.

* ``[p]settickettool custommessage <profile> <custom_message>``
 This message will be sent in the ticket channel when the ticket is opened.

* ``[p]settickettool custommodal <profile> <custom_modal>``
 Ask a maximum of 5 questions to the user who opens a ticket, with a Discord Modal.

* ``[p]settickettool deleteonclose <profile> <delete_on_close>``
 Does closing the ticket directly delete it (with confirmation)?

* ``[p]settickettool dynamicchannelname <profile> <dynamic_channel_name>``
 Set the template that will be used to name the channel when creating a ticket.

* ``[p]settickettool enable <profile> <enable>``
 Enable the system.

* ``[p]settickettool forumchannel <profile> <forum_channel>``
 Set the forum channel where the opened tickets will be, or a text channel to use private threads. If it's set, `category_open` and `category_close` will be ignored (except for existing tickets).

* ``[p]settickettool logschannel <profile> <logschannel>``
 Set the channel where the logs will be sent/saved.

* ``[p]settickettool message <profile> [channel] [message] [reason_options]... [emoji=🎟️] [label]``
 Send a message with a button to open a ticket or dropdown with possible reasons.

* ``[p]settickettool modalconfig <profile> [confirmation=False]``
 Set all settings for the cog with a Discord Modal.

* ``[p]settickettool modlog <profile> <modlog>``
 Does the bot create an action in the bot modlog when a ticket is created?

* ``[p]settickettool nbmax <profile> <nb_max>``
 Sets the maximum number of open tickets a user can have on the system at any one time (for a profile only).

* ``[p]settickettool pingroles <profile> <ping_roles>``
 This role will be pinged automatically when the ticket is created, but does not give any additional permissions.

* ``[p]settickettool profileadd <profile>``
 Create a new profile with defaults settings.

* ``[p]settickettool profileclone <old_profile> <profile>``
 Clone an existing profile with his settings.

* ``[p]settickettool profileremove <profile> [confirmation=False]``
 Remove an existing profile.

* ``[p]settickettool profilerename <old_profile> <profile>``
 Rename an existing profile.

* ``[p]settickettool profileslist``
 List the existing profiles.

* ``[p]settickettool renamechanneldropdown <profile> <rename_channel_dropdown>``
 With Dropdowns feature, rename the ticket channel with chosen reason.

* ``[p]settickettool resetsetting <profile> <setting>``
 Reset a setting.

* ``[p]settickettool showsettings <profile> [with_dev=False]``
 Show all settings for the cog with defaults and values.

* ``[p]settickettool supportroles <profile> <support_roles>``
 Users with this role will be able to participate and claim the ticket.

* ``[p]settickettool ticketrole <profile> <role>``
 This role will be added automatically to open tickets owners.

* ``[p]settickettool usercanclose <profile> <user_can_close>``
 Can the author of the ticket, if he/she does not have a role set up for the system, close the ticket himself?

* ``[p]settickettool viewroles <profile> <view_roles>``
 Users with this role will only be able to read messages from the ticket, but not send them.

* ``[p]ticket``
 Commands for using the Tickets system.

* ``[p]ticket addmember [members]...``
 Add a member to an existing Ticket.

* ``[p]ticket claim [member] [reason=No reason provided.]``
 Claim an existing Ticket.

* ``[p]ticket close [confirmation] [reason=No reason provided.]``
 Close an existing Ticket.

* ``[p]ticket create [profile] [reason=No reason provided.]``
 Create a Ticket.

* ``[p]ticket createfor [profile] <member> [reason=No reason provided.]``
 Create a Ticket for a member.

* ``[p]ticket delete [confirmation=False] [reason=No reason provided.]``
 Delete an existing Ticket.

* ``[p]ticket export``
 Export all the messages of an existing Ticket in html format.

* ``[p]ticket list <profile> ["open"|"close"|"all"] [owner]``
 List the existing Tickets for a profile. You can provide a status and/or a ticket owner.

* ``[p]ticket lock [confirmation] [reason=No reason provided.]``
 Lock an existing Ticket.

* ``[p]ticket open [reason=No reason provided.]``
 Open an existing Ticket.

* ``[p]ticket owner <new_owner> [reason=No reason provided.]``
 Change the owner of an existing Ticket.

* ``[p]ticket removemember [members]...``
 Remove a member to an existing Ticket.

* ``[p]ticket rename <new_name> [reason=No reason provided.]``
 Rename an existing Ticket.

* ``[p]ticket unclaim [reason=No reason provided.]``
 Unclaim an existing Ticket.

* ``[p]ticket unlock [reason=No reason provided.]``
 Unlock an existing locked Ticket.

------------
Installation
------------

If you haven't added my repo before, lets add it first. We'll call it "AAA3A-cogs" here.

.. code-block:: ini

    [p]repo add AAA3A-cogs https://github.com/AAA3A-AAA3A/AAA3A-cogs

Now, we can install TicketTool.

.. code-block:: ini

    [p]cog install AAA3A-cogs tickettool

Once it's installed, it is not loaded by default. Load it by running the following command:

.. code-block:: ini

    [p]load tickettool

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
.. _tickets:
=======
Tickets
=======

This is the cog guide for the ``Tickets`` cog. This guide contains the collection of commands which you can use in the cog.
Through this guide, ``[p]`` will always represent your prefix. Replace ``[p]`` with your own prefix when you use these commands in Discord.

.. note::

    Ensure that you are up to date by running ``[p]cog update tickets``.
    If there is something missing, or something that needs improving in this documentation, feel free to create an issue `here <https://github.com/AAA3A-AAA3A/AAA3A-cogs/issues>`_.
    This documentation is generated everytime this cog receives an update.

---------------
About this cog:
---------------

Configure and manage a tickets system for your server!

---------
Commands:
---------

Here are all the commands included in this cog (64):

* ``[p]settickets``
 Commands to configure Tickets.

* ``[p]settickets addbutton <message> [profile] [emoji] ["1"|"2"|"3"|"4"=2] [label]``
 Add a button to a message.

* ``[p]settickets adddropdownoption <message> [profile] [emoji] <label> [description]``
 Add an option to the dropdown of a message.

* ``[p]settickets alwaysincludeitemlabel <profile> <always_include_item_label>``
 Whether the item label will always be included in the embeds.

* ``[p]settickets autodeleteonclose <profile> <auto_delete_on_close>``
 Time in hours before the ticket is deleted after being closed. Set to 0 for an immediate deletion.

* ``[p]settickets blacklistroles <profile> <blacklist_roles>``
 Roles that can't create tickets.

* ``[p]settickets categoryclosed <profile> <category channel>``
 Category where the closed tickets will be created.

* ``[p]settickets categoryopen <profile> <category channel>``
 Category where the open tickets will be created.

* ``[p]settickets channelname <profile> <channel_name>``
 Name of the channel where the tickets will be created, reduced to 100 characters. You can use the following placeholders: `{emoji}`, `{owner_display_name}`, `{owner_name}`, `{owner_mention}`, `{owner_id}`, `{guild_name}` and `{guild_id}`.

* ``[p]settickets clearmessage <message>``
 Clear the components of a message.

* ``[p]settickets closeonleave <profile> <close_on_leave>``
 Whether the ticket will be closed when the owner leaves the server.

* ``[p]settickets closereopenreasonmodal <profile> <close_reopen_reason_modal>``
 Whether a modal will be sent to the ticket owner when they close or reopen a ticket for asking a reason.

* ``[p]settickets createmodlogcase <profile> <create_modlog_case>``
 Whether a modlog's case will be created when a ticket is created.

* ``[p]settickets creatingmodal <profile> <creating_modal>``
 Whether a modal will be sent to the ticket owner when they create a ticket.

* ``[p]settickets custommessage <profile> <custom_message>``
 Custom message that will be sent when a ticket is created. You can use the following placeholders: `{owner_display_name}`, `{owner_name}`, `{owner_mention}`, `{owner_id}`, `{guild_name}` and `{guild_id}`.

* ``[p]settickets emojiclaim <profile> <emoji_claim>``
 Emoji of the `Claim` button.

* ``[p]settickets emojiclose <profile> <emoji_close>``
 Emoji of the `Close` buttons.

* ``[p]settickets emojidelete <profile> <emoji_delete>``
 Emoji of the `Delete` button.

* ``[p]settickets emojilock <profile> <emoji_lock>``
 Emoji of the `Lock` button.

* ``[p]settickets emojireopen <profile> <emoji_reopen>``
 Emoji of the `Reopen` buttons.

* ``[p]settickets emojitranscript <profile> <emoji_transcript>``
 Emoji of the `Transcript` button.

* ``[p]settickets emojiunclaim <profile> <emoji_unclaim>``
 Emoji of the `Unclaim` button.

* ``[p]settickets emojiunlock <profile> <emoji_unlock>``
 Emoji of the `Unlock` button.

* ``[p]settickets enabled <profile> <enabled>``
 Whether the profile is enabled or not.

* ``[p]settickets forumchannel <profile> <forum_channel>``
 Forum/text channel where the tickets will be created as threads.

* ``[p]settickets forumtags <profile> <forum_tags>``
 Tags that will be added to the threads in the forum channel.

* ``[p]settickets getdebugloopsstatus``
 Get an embed for check loop status.

* ``[p]settickets logschannel <profile> <logs_channel>``
 Channel where the logs will be sent.

* ``[p]settickets maxopenticketsbymember <profile> <max_open_tickets_by_member>``
 Maximum number of open tickets a member can have.

* ``[p]settickets modalconfig <profile> [confirmation=False]``
 Set all settings for the cog with a Discord Modal.

* ``[p]settickets ownercanaddmembers <profile> <owner_can_add_members>``
 Whether the ticket owner can add members to the ticket.

* ``[p]settickets ownercanclose <profile> <owner_can_close>``
 Whether the ticket owner can close the ticket.

* ``[p]settickets ownercanremovemembers <profile> <owner_can_remove_members>``
 Whether the ticket owner can remove members from the ticket.

* ``[p]settickets ownercanreopen <profile> <owner_can_reopen>``
 Whether the ticket owner can reopen the ticket.

* ``[p]settickets ownercloseconfirmation <profile> <owner_close_confirmation>``
 Whether the ticket owner get a message to confirm the closing of the ticket.

* ``[p]settickets pingroles <profile> <ping_roles>``
 Roles that will be pinged when a ticket is created.

* ``[p]settickets profileadd <profile>``
 Create a new profile with defaults settings.

* ``[p]settickets profileclone <old_profile> <profile>``
 Clone an existing profile with his settings.

* ``[p]settickets profileremove <profile> [confirmation=False]``
 Remove an existing profile.

* ``[p]settickets profilerename <old_profile> <profile>``
 Rename an existing profile.

* ``[p]settickets profileslist``
 List the existing profiles.

* ``[p]settickets resetsetting <profile> <setting>``
 Reset a setting.

* ``[p]settickets setup``
 Help to setup Tickets.

* ``[p]settickets showsettings <profile> [with_dev=False]``
 Show all settings for the cog with defaults and values.

* ``[p]settickets supportroles <profile> <support_roles>``
 Roles that can support tickets.

* ``[p]settickets ticketrole <profile> <role>``
 Role that will be added to the ticket owner for the duration of the ticket.

* ``[p]settickets transcripts <profile> <transcripts>``
 Whether a transcript will be created when a ticket is deleted.

* ``[p]settickets viewroles <profile> <view_roles>``
 Roles that can view tickets.

* ``[p]settickets welcomemessage <profile> <welcome_message>``
 Welcome message that will be sent when a ticket is created. You can use the following placeholders: `{owner_display_name}`, `{owner_name}`, `{owner_mention}`, `{owner_id}`, `{guild_name}` and `{guild_id}`.

* ``[p]settickets whitelistroles <profile> <whitelist_roles>``
 Roles that can create tickets.

* ``[p]ticket``
 Create, manage and list tickets.

* ``[p]ticket addmember [ticket] <member>``
 Add a member to a ticket.

* ``[p]ticket claim [ticket]``
 Claim a ticket.

* ``[p]ticket close [ticket]``
 Close a ticket.

* ``[p]ticket create [profile=main] [reason]``
 Create a ticket.

* ``[p]ticket createfor <owner> [profile=main] [reason]``
 Create a ticket for a member.

* ``[p]ticket export [ticket]``
 Export a ticket.

* ``[p]ticket list [short=False] [claimed=False] ["all"|"open"|"claimed"|"unclaimed"|"closed"=open] [owner]``
 List tickets.

* ``[p]ticket removemember [ticket] <member>``
 Remove a member from a ticket.

* ``[p]ticket reopen [ticket]``
 Reopen a ticket.

* ``[p]ticket settings [profile]``
 Show Tickets settings.

* ``[p]ticket show [ticket]``
 Show a ticket.

* ``[p]ticket unclaim [ticket]``
 Unclaim a ticket.

* ``[p]ticket unlock [ticket]``
 Unlock a ticket.

------------
Installation
------------

If you haven't added my repo before, lets add it first. We'll call it "AAA3A-cogs" here.

.. code-block:: ini

    [p]repo add AAA3A-cogs https://github.com/AAA3A-AAA3A/AAA3A-cogs

Now, we can install Tickets.

.. code-block:: ini

    [p]cog install AAA3A-cogs tickets

Once it's installed, it is not loaded by default. Load it by running the following command:

.. code-block:: ini

    [p]load tickets

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
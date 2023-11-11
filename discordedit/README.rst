.. _discordedit:
===========
DiscordEdit
===========

This is the cog guide for the 'DiscordEdit' cog. This guide contains the collection of commands which you can use in the cog.
Through this guide, ``[p]`` will always represent your prefix. Replace ``[p]`` with your own prefix when you use these commands in Discord.

.. note::

    Ensure that you are up to date by running ``[p]cog update discordedit``.
    If there is something missing, or something that needs improving in this documentation, feel free to create an issue `here <https://github.com/AAA3A-AAA3A/AAA3A-cogs/issues>`_.
    This documentation is auto-generated everytime this cog receives an update.

--------------
About this cog
--------------

A cog to edit Discord default objects, like guilds, roles, text channels, voice channels, threads and AutoMod!

--------
Commands
--------

Here are all the commands included in this cog (93):

* ``[p]editguild``
 Commands for edit a guild.

* ``[p]editguild afkchannel [afk_channel]``
 Edit guild afkchannel.

* ``[p]editguild afktimeout <afk_timeout>``
 Edit guild afk timeout.

* ``[p]editguild banner [banner]``
 Edit guild banner.

* ``[p]editguild clone <name>``
 Clone a guild.

* ``[p]editguild community <community>``
 Edit guild community state.

* ``[p]editguild create <name> [template_code]``
 Create a guild with the bot as owner.

* ``[p]editguild defaultnotifications <default_notifications>``
 Edit guild notification level.

* ``[p]editguild delete [confirmation=False]``
 Delete guild (if the bot is owner).

* ``[p]editguild description [description]``
 Edit guild description.

* ``[p]editguild discoverable <discoverable>``
 Edit guild discoverable state.

* ``[p]editguild discoverysplash [discovery_splash]``
 Edit guild discovery splash.

* ``[p]editguild explicitcontentfilter <explicit_content_filter>``
 Edit guild explicit content filter.

* ``[p]editguild icon [icon]``
 Edit guild icon.

* ``[p]editguild invitesdisabled <invites_disabled>``
 Edit guild invites disabled state.

* ``[p]editguild name <name>``
 Edit guild name.

* ``[p]editguild owner <owner> [confirmation=False]``
 Edit guild owner (if the bot is bot owner).

* ``[p]editguild preferredlocale <preferred_locale>``
 Edit guild preferred locale.

* ``[p]editguild premiumprogressbarenabled [premium_progress_bar_enabled]``
 Edit guild premium progress bar enabled.

* ``[p]editguild publicupdateschannel [public_updates_channel]``
 Edit guild public updates channel.

* ``[p]editguild raidalertsdisabled <raid_alerts_disabled>``
 Edit guild invites raid alerts disabled state.

* ``[p]editguild ruleschannel [rules_channel]``
 Edit guild rules channel.

* ``[p]editguild safetyalertschannel [safety_alerts_channel]``
 Edit guild invites safety alerts channel.

* ``[p]editguild splash [splash]``
 Edit guild splash.

* ``[p]editguild systemchannel [system_channel]``
 Edit guild system channel.

* ``[p]editguild systemchannelflags <system_channel_flags>``
 Edit guild system channel flags.

* ``[p]editguild vanitycode <vanity_code>``
 Edit guild vanity code.

* ``[p]editguild verificationlevel <verification_level>``
 Edit guild verification level.

* ``[p]editguild view``
 View and edit guild.

* ``[p]editguild widgetchannel [widget_channel]``
 Edit guild invites widget channel.

* ``[p]editguild widgetenabled <widget_enabled>``
 Edit guild invites widget enabled state.

* ``[p]editrole``
 Commands for edit a role.

* ``[p]editrole color <role> <color>``
 Edit role color.

* ``[p]editrole create [color] <name>``
 Create a role.

* ``[p]editrole delete <role> [confirmation=False]``
 Delete a role.

* ``[p]editrole displayicon <role> [display_icon]``
 Edit role display icon.

* ``[p]editrole hoist <role> [hoist]``
 Edit role hoist.

* ``[p]editrole list``
 List all roles in the current guild.

* ``[p]editrole mentionable <role> [mentionable]``
 Edit role mentionable.

* ``[p]editrole name <role> <name>``
 Edit role name.

* ``[p]editrole permissions <role> <true_or_false> [permissions]...``
 Edit role permissions.

* ``[p]editrole position <role> <position>``
 Edit role position.

* ``[p]editrole view <role>``
 View and edit role.

* ``[p]edittextchannel``
 Commands for edit a text channel.

* ``[p]edittextchannel category [channel] <category>``
 Edit text channel category.

* ``[p]edittextchannel clone [channel] <name>``
 Clone a text channel.

* ``[p]edittextchannel create [category] <name>``
 Create a text channel.

* ``[p]edittextchannel defaultautoarchiveduration [channel] <60|1440|4320|10080>``
 Edit text channel default auto archive duration.

* ``[p]edittextchannel defaultthreadslowmodedelay [channel] <default_thread_slowmode_delay>``
 Edit text channel default thread slowmode delay.

* ``[p]edittextchannel delete [channel] [confirmation=False]``
 Delete a text channel.

* ``[p]edittextchannel invite [channel] [max_age] [max_uses] [temporary=False] [unique=True]``
 Create an invite for a text channel.

* ``[p]edittextchannel list``
 List all text channels in the current guild.

* ``[p]edittextchannel name [channel] <name>``
 Edit text channel name.

* ``[p]edittextchannel nsfw [channel] [nsfw]``
 Edit text channel nsfw.

* ``[p]edittextchannel overwrites [channel] [roles_or_users]... [true_or_false] [permissions]...``
 Edit text channel overwrites/permissions.

* ``[p]edittextchannel position [channel] <position>``
 Edit text channel position.

* ``[p]edittextchannel slowmodedelay [channel] <slowmode_delay>``
 Edit text channel slowmode delay.

* ``[p]edittextchannel syncpermissions [channel] [sync_permissions]``
 Edit text channel syncpermissions with category.

* ``[p]edittextchannel topic [channel] <topic>``
 Edit text channel topic.

* ``[p]edittextchannel type [channel] <_type>``
 Edit text channel type.

* ``[p]edittextchannel view [channel]``
 View and edit text channel.

* ``[p]editthread``
 Commands for edit a text channel.

* ``[p]editthread adduser [thread] <member>``
 Add member to thread.

* ``[p]editthread appliedtags [thread] [applied_tags]...``
 Edit thread applied tags.

* ``[p]editthread archived [thread] [archived]``
 Edit thread archived.

* ``[p]editthread autoarchiveduration [thread] <60|1440|4320|10080>``
 Edit thread auto archive duration.

* ``[p]editthread create [channel] [message] <name>``
 Create a thread.

* ``[p]editthread delete [thread] [confirmation=False]``
 Delete a thread.

* ``[p]editthread invitable [thread] [invitable]``
 Edit thread invitable.

* ``[p]editthread list``
 List all threads in the current guild.

* ``[p]editthread locked [thread] [locked]``
 Edit thread locked.

* ``[p]editthread name [thread] <name>``
 Edit thread name.

* ``[p]editthread pinned [thread] <pinned>``
 Edit thread pinned.

* ``[p]editthread removeuser [thread] <member>``
 Remove member from thread.

* ``[p]editthread slowmodedelay [thread] <slowmode_delay>``
 Edit thread slowmode delay.

* ``[p]editthread view [thread]``
 View and edit thread.

* ``[p]editvoicechannel``
 Commands for edit a voice channel.

* ``[p]editvoicechannel bitrate <channel> <bitrate>``
 Edit voice channel bitrate.

* ``[p]editvoicechannel category <channel> <category>``
 Edit voice channel category.

* ``[p]editvoicechannel clone <channel> <name>``
 Clone a voice channel.

* ``[p]editvoicechannel create [category] <name>``
 Create a voice channel.

* ``[p]editvoicechannel delete <channel> [confirmation=False]``
 Delete voice channel.

* ``[p]editvoicechannel invite <channel> [max_age] [max_uses] [temporary=False] [unique=True]``
 Create an invite for a voice channel.

* ``[p]editvoicechannel list``
 List all voice channels in the current guild.

* ``[p]editvoicechannel name <channel> <name>``
 Edit voice channel name.

* ``[p]editvoicechannel nsfw <channel> [nsfw]``
 Edit voice channel nsfw.

* ``[p]editvoicechannel overwrites <channel> [roles_or_users]... [true_or_false] [permissions]...``
 Edit voice channel overwrites/permissions.

* ``[p]editvoicechannel position <channel> <position>``
 Edit voice channel position.

* ``[p]editvoicechannel slowmodedelay <channel> <slowmode_delay>``
 Edit voice channel slowmode delay.

* ``[p]editvoicechannel syncpermissions <channel> [sync_permissions]``
 Edit voice channel sync permissions.

* ``[p]editvoicechannel userlimit <channel> <user_limit>``
 Edit voice channel user limit.

* ``[p]editvoicechannel videoqualitymode <channel> <video_quality_mode>``
 Edit voice channel video quality mode.

* ``[p]editvoicechannel view <channel>``
 View and edit voice channel.

------------
Installation
------------

If you haven't added my repo before, lets add it first. We'll call it
"AAA3A-cogs" here.

.. code-block:: ini

    [p]repo add AAA3A-cogs https://github.com/AAA3A-AAA3A/AAA3A-cogs

Now, we can install DiscordEdit.

.. code-block:: ini

    [p]cog install AAA3A-cogs discordedit

Once it's installed, it is not loaded by default. Load it by running the following command:

.. code-block:: ini

    [p]load discordedit

---------------
Further Support
---------------

Check out my docs `here <https://aaa3a-cogs.readthedocs.io/en/latest/>`_.
Mention me in the #support_other-cogs in the `cog support server <https://discord.gg/GET4DVk>`_ if you need any help.
Additionally, feel free to open an issue or pull request to this repo.

------
Credit
------

Thanks to Kreusada for the Python code to automatically generate this documentation!

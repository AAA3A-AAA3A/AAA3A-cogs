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

A cog to edit Discord default objects!

--------
Commands
--------

Here are all the commands included in this cog (70):

* ``[p]editguild``
 Commands for edit a guild.

* ``[p]editguild afkchannel [afk_channel=None]``
 Edit guild afkchannel.

* ``[p]editguild afktimeout <afk_timeout>``
 Edit guild afktimeout.

* ``[p]editguild clone <name>``
 Clone a guild.

* ``[p]editguild community <community>``
 Edit guild community state.

* ``[p]editguild create <name> [template_code=None]``
 Create a guild with the bot as owner.

* ``[p]editguild defaultnotifications <"0"|"1">``
 Edit guild notification level.

* ``[p]editguild delete [confirmation=False]``
 Delete guild (if the bot is owner).

* ``[p]editguild description [description=None]``
 Edit guild description.

* ``[p]editguild discoverable <discoverable>``
 Edit guild discoverable state.

* ``[p]editguild explicitcontentfilter <explicit_content_filter>``
 Edit guild explicit content filter.

* ``[p]editguild invitesdisabled <invites_disabled>``
 Edit guild invites disabled state.

* ``[p]editguild name <name>``
 Edit guild name.

* ``[p]editguild owner <owner> [confirmation=False]``
 Edit guild owner (if the bot is bot owner).

* ``[p]editguild preferredlocale <preferred_locale>``
 Edit guild preferred locale.

* ``[p]editguild premiumprogressbarenabled <premium_progress_bar_enabled>``
 Edit guild premium progress bar enabled.

* ``[p]editguild publicupdateschannel [public_updates_channel=None]``
 Edit guild public updates channel.

* ``[p]editguild ruleschannel [rules_channel=None]``
 Edit guild rules channel.

* ``[p]editguild systemchannel [system_channel=None]``
 Edit guild system channel.

* ``[p]editguild systemchannelflags <system_channel_flags>``
 Edit guild system channel flags.

* ``[p]editguild vanitycode <vanity_code>``
 Edit guild vanity code.

* ``[p]editguild verificationlevel <verification_level>``
 Edit guild verification level.

* ``[p]editrole``
 Commands for edit a role.

* ``[p]editrole color <role> <color>``
 Edit role color.

* ``[p]editrole create [color=None] <name>``
 Create a role.

* ``[p]editrole delete <role> [confirmation=False]``
 Delete a role.

* ``[p]editrole mentionable <role> <mentionable>``
 Edit role mentionable.

* ``[p]editrole name <role> <name>``
 Edit role name.

* ``[p]editrole permissions <role> <permissions>``
 Edit role permissions.

* ``[p]editrole position <role> <position>``
 Edit role position.

* ``[p]edittextchannel``
 Commands for edit a text channel.

* ``[p]edittextchannel category [channel] <category>``
 Edit text channel category.

* ``[p]edittextchannel clone [channel] <name>``
 Clone a text channel.

* ``[p]edittextchannel create [category=None] <name>``
 Create a text channel.

* ``[p]edittextchannel defaultautoarchiveduration [channel] <"60"|"1440"|"4320"|"10080">``
 Edit text channel default auto archive duration.

* ``[p]edittextchannel delete [channel] [confirmation=False]``
 Delete a text channel.

* ``[p]edittextchannel invite [channel] [max_age=None] [max_uses=None] [temporary=False] [unique=True]``
 Create an invite for a text channel.

* ``[p]edittextchannel name [channel] <name>``
 Edit text channel name.

* ``[p]edittextchannel nsfw [channel] <nsfw>``
 Edit text channel nsfw.

* ``[p]edittextchannel permissions [channel] <permission> [true_or_false] [roles_or_users]...``
 Edit text channel permissions/overwrites.

* ``[p]edittextchannel position [channel] <position>``
 Edit text channel position.

* ``[p]edittextchannel slowmodedelay [channel] <slowmode_delay>``
 Edit text channel slowmode delay.

* ``[p]edittextchannel syncpermissions [channel] <sync_permissions>``
 Edit text channel syncpermissions with category.

* ``[p]edittextchannel topic [channel] <topic>``
 Edit text channel topic.

* ``[p]edittextchannel type [channel] <"0"|"5">``
 Edit text channel type.

* ``[p]editthread``
 Commands for edit a text channel.

* ``[p]editthread appliedtags <thread> [applied_tags]...``
 Edit thread applied tags.

* ``[p]editthread archived <thread> <archived>``
 Edit thread archived.

* ``[p]editthread autoarchiveduration <thread> <"60"|"1440"|"4320"|"10080">``
 Edit thread auto archive duration.

* ``[p]editthread create [channel=None] [message=None] <name>``
 Create a thread.

* ``[p]editthread delete <thread> [confirmation=False]``
 Delete a thread.

* ``[p]editthread invitable <thread> <invitable>``
 Edit thread invitable.

* ``[p]editthread locked <thread> <locked>``
 Edit thread locked.

* ``[p]editthread name <thread> <name>``
 Edit thread name.

* ``[p]editthread pinned <thread> <pinned>``
 Edit thread pinned.

* ``[p]editthread slowmodedelay <thread> <slowmode_delay>``
 Edit thread slowmode delay.

* ``[p]editvoicechannel``
 Commands for edit a voice channel.

* ``[p]editvoicechannel bitrate <channel> <bitrate>``
 Edit voice channel bitrate.

* ``[p]editvoicechannel category <channel> <category>``
 Edit voice channel category.

* ``[p]editvoicechannel clone <channel> <name>``
 Clone a voice channel.

* ``[p]editvoicechannel create [category=None] <name>``
 Create a voice channel.

* ``[p]editvoicechannel delete <channel> [confirmation=False]``
 Delete voice channel.

* ``[p]editvoicechannel invite <channel> [max_age=None] [max_uses=None] [temporary=False] [unique=True]``
 Create an invite for a voice channel.

* ``[p]editvoicechannel name <channel> <name>``
 Edit voice channel name.

* ``[p]editvoicechannel nsfw <channel> <nsfw>``
 Edit voice channel nsfw.

* ``[p]editvoicechannel permissions <channel> <permission> [true_or_false] [roles_or_users]...``
 Edit voice channel permissions/overwrites.

* ``[p]editvoicechannel position <channel> <position>``
 Edit voice channel position.

* ``[p]editvoicechannel syncpermissions <channel> <sync_permissions>``
 Edit voice channel sync permissions.

* ``[p]editvoicechannel userlimit <channel> <user_limit>``
 Edit voice channel user limit.

* ``[p]editvoicechannel videoqualitymode <channel> <"1"|"2">``
 Edit voice channel video quality mode.

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

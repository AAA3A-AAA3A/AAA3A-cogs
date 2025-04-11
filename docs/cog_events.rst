.. _events:
======
Events
======

This is the cog guide for the ``Events`` cog. This guide contains the collection of commands which you can use in the cog.
Through this guide, ``[p]`` will always represent your prefix. Replace ``[p]`` with your own prefix when you use these commands in Discord.

.. note::

    Ensure that you are up to date by running ``[p]cog update events``.
    If there is something missing, or something that needs improving in this documentation, feel free to create an issue `here <https://github.com/AAA3A-AAA3A/AAA3A-cogs/issues>`_.
    This documentation is generated everytime this cog receives an update.

---------------
About this cog:
---------------

Make incredible events, with a unique user experience to claim prizes!

---------
Commands:
---------

Here are all the commands included in this cog (38):

* ``[p]event``
 Make incredible events, with a unique user experience to claim prizes!

* ``[p]event cancel <event>``
 Cancel an event.

* ``[p]event create [channel] <prize> [description] [kwargs_flags]``
 Create an event.

* ``[p]event end [event] [channel] [winners]... [prize] [description] [kwargs_flags]``
 End an event.

* ``[p]event explain``
 Explain how to use the events creation and ending commands.

* ``[p]event leaderboard``
 Get the leaderboard of events hosts.

* ``[p]event list ["all"|"active"|"scheduled"|"ended"=all]``
 List all active or 3-days ended events.

* ``[p]event settings [profile]``
 Show Events settings.

* ``[p]event show <event>``
 Show an event.

* ``[p]event winners <event>``
 Get the winners of an event.

* ``[p]event winsleaderboard``
 Get the leaderboard of events wins.

* ``[p]setevents``
 Commands to configure Events.

* ``[p]setevents claimprizeforumchannel <profile> <forum channel>``
 Forum channel where to create the claim prize threads.

* ``[p]setevents claimprizeforumtags <profile> <claim_prize_forum_tags>``
 Forum tags to use for the claim prize threads. Provide `0` to get the available tags ids.

* ``[p]setevents claimprizepingrole <profile> <role>``
 Role to ping when a claim prize thread is created.

* ``[p]setevents creatorroles <profile> <creator_roles>``
 Roles that can create events.

* ``[p]setevents defaultdescription <profile> <default_description>``
 Default description for the events.

* ``[p]setevents dmhost <profile> <dm_host>``
 DM the host when the event starts.

* ``[p]setevents dmwinners <profile> <dm_winners>``
 DM the winners when the event ends.

* ``[p]setevents embedcolor <profile> <colour>``
 Embed color for the events messages.

* ``[p]setevents emojicontent <profile> <emoji_content>``
 Emoji to use in the events messages content.

* ``[p]setevents getdebugloopstatus``
 Get an embed for check loop status.

* ``[p]setevents imageurl <profile> <image_url>``
 Image URL for the giveaways messages.

* ``[p]setevents logschannel <profile> <logs_channel>``
 Channel where to log events.

* ``[p]setevents managerroles <profile> <manager_roles>``
 Roles that can manage events.

* ``[p]setevents modalconfig <profile> [confirmation=False]``
 Set all settings for the cog with a Discord Modal.

* ``[p]setevents ping <profile> <ping>``
 Ping the ping role when the event starts.

* ``[p]setevents pingroles <profile> <ping_roles>``
 Roles to ping when the event starts.

* ``[p]setevents profileadd <profile>``
 Create a new profile with defaults settings.

* ``[p]setevents profileclone <old_profile> <profile>``
 Clone an existing profile with his settings.

* ``[p]setevents profileremove <profile> [confirmation=False]``
 Remove an existing profile.

* ``[p]setevents profilerename <old_profile> <profile>``
 Rename an existing profile.

* ``[p]setevents profileslist``
 List the existing profiles.

* ``[p]setevents resetsetting <profile> <setting>``
 Reset a setting.

* ``[p]setevents showsettings <profile> [with_dev=False]``
 Show all settings for the cog with defaults and values.

* ``[p]setevents thankdonor <profile> <thank_donor>``
 Thank the donor when the event starts.

* ``[p]setevents thumbnailurl <profile> <thumbnail_url>``
 Thumbnail URL for the events messages.

* ``[p]setevents winnersrole <profile> <role>``
 Role to give to winners.

------------
Installation
------------

If you haven't added my repo before, lets add it first. We'll call it "AAA3A-cogs" here.

.. code-block:: ini

    [p]repo add AAA3A-cogs https://github.com/AAA3A-AAA3A/AAA3A-cogs

Now, we can install Events.

.. code-block:: ini

    [p]cog install AAA3A-cogs events

Once it's installed, it is not loaded by default. Load it by running the following command:

.. code-block:: ini

    [p]load events

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
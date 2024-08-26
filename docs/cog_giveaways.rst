.. _giveaways:
=========
Giveaways
=========

This is the cog guide for the ``Giveaways`` cog. This guide contains the collection of commands which you can use in the cog.
Through this guide, ``[p]`` will always represent your prefix. Replace ``[p]`` with your own prefix when you use these commands in Discord.

.. note::

    Ensure that you are up to date by running ``[p]cog update giveaways``.
    If there is something missing, or something that needs improving in this documentation, feel free to create an issue `here <https://github.com/AAA3A-AAA3A/AAA3A-cogs/issues>`_.
    This documentation is generated everytime this cog receives an update.

---------------
About this cog:
---------------

Make incredible giveaways, moving from requirements checks to a unique user experience!

---------
Commands:
---------

Here are all the commands included in this cog (65):

* ``[p]giveaway``
 Make incredible giveaways, moving from requirements checks to a unique user experience.

* ``[p]giveaway cancel <giveaway>``
 Cancel a giveaway.

* ``[p]giveaway checkrequirements <giveaway> [member=<you>]``
 Check the requirements of a giveaway.

* ``[p]giveaway create [channel] [duration] [winners_amount] <prize> [kwargs_requirements_flags]``
 Create a giveaway.

* ``[p]giveaway drop [channel] [duration] [winners_amount] <prize> [kwargs_requirements_flags]``
 Create a drop giveaway, where the first participants to click win.

* ``[p]giveaway end <giveaway>``
 End a giveaway.

* ``[p]giveaway explain``
 Explain how to use the giveaways creation commands.

* ``[p]giveaway invalidate <giveaway> <member>``
 Forcefully invalidate a member for a giveaway.

* ``[p]giveaway join <giveaway>``
 Join a giveaway.

* ``[p]giveaway leaderboard``
 Get the leaderboard of giveaways hosts.

* ``[p]giveaway leave <giveaway>``
 Leave a giveaway.

* ``[p]giveaway list ["all"|"active"|"scheduled"|"ended"=all]``
 List all active or 3-days ended giveaways.

* ``[p]giveaway multi [channel] [duration] [winners_amount] [prizes]... [kwargs_requirements_flags]``
 Create multiple giveaways at once, with the same requirements and flags, but different prizes.

* ``[p]giveaway participants <giveaway>``
 Get the participants of a giveaway.

* ``[p]giveaway reroll <giveaway>``
 Reroll a giveaway.

* ``[p]giveaway settings [profile]``
 Show Giveaways settings.

* ``[p]giveaway show <giveaway>``
 Show a giveaway.

* ``[p]giveaway validate <giveaway> <member>``
 Forcefully validate a member for a giveaway.

* ``[p]giveaway winners <giveaway>``
 Get the winners of a giveaway.

* ``[p]giveaway winsleaderboard``
 Get the leaderboard of giveaways wins.

* ``[p]setgiveaways``
 Commands to configure Giveaways.

* ``[p]setgiveaways bonusentries <profile> <bonus_entries>``
 Roles that give bonus entries in the giveaways. Use `ROLE_ID|AMOUNT ROLE_ID|AMOUNT ...`.

* ``[p]setgiveaways checkrequirementsonend <profile> <check_requirements_on_end>``
 Re-check the requirements for the participants of the giveaway when it ends.

* ``[p]setgiveaways claimprizeforumchannel <profile> <forum channel>``
 Forum channel where to create the claim prize threads.

* ``[p]setgiveaways claimprizeforumtags <profile> <claim_prize_forum_tags>``
 Forum tags to use for the claim prize threads. Provide `0` to get the available tags ids.

* ``[p]setgiveaways claimprizepingrole <profile> <role>``
 Role to ping when a claim prize thread is created.

* ``[p]setgiveaways creatorroles <profile> <creator_roles>``
 Roles that can create giveaways.

* ``[p]setgiveaways dmhost <profile> <dm_host>``
 DM the host when the giveaway ends.

* ``[p]setgiveaways dmwinners <profile> <dm_winners>``
 DM the winners when the giveaway ends.

* ``[p]setgiveaways embedcolor <profile> <colour>``
 Embed color for the giveaways messages.

* ``[p]setgiveaways emoji <profile> <emoji>``
 Emoji to use for the giveaways.

* ``[p]setgiveaways emojicontent <profile> <emoji_content>``
 Emoji to use in the giveaways messages content.

* ``[p]setgiveaways getdebugloopsstatus``
 Get an embed for check loop status.

* ``[p]setgiveaways logschannel <profile> <logs_channel>``
 Channel where to log giveaways.

* ``[p]setgiveaways managerroles <profile> <manager_roles>``
 Roles that can manage giveaways.

* ``[p]setgiveaways modalconfig <profile> [confirmation=False]``
 Set all settings for the cog with a Discord Modal.

* ``[p]setgiveaways nodonor <profile> <no_donor>``
 Don't allow the donor to join the giveaway.

* ``[p]setgiveaways ping <profile> <ping>``
 Ping the ping role when the giveaway starts.

* ``[p]setgiveaways pingrole <profile> <role>``
 Role to ping when the giveaway starts.

* ``[p]setgiveaways profileadd <profile>``
 Create a new profile with defaults settings.

* ``[p]setgiveaways profileclone <old_profile> <profile>``
 Clone an existing profile with his settings.

* ``[p]setgiveaways profileremove <profile> [confirmation=False]``
 Remove an existing profile.

* ``[p]setgiveaways profilerename <old_profile> <profile>``
 Rename an existing profile.

* ``[p]setgiveaways profileslist``
 List the existing profiles.

* ``[p]setgiveaways resetsetting <profile> <setting>``
 Reset a setting.

* ``[p]setgiveaways rqamariexp <profile> <rq_amari_exp>``
 Amari's Exp of the user required to join the giveaways.

* ``[p]setgiveaways rqamarilevel <profile> <rq_amari_level>``
 Amari's Level of the user required to join the giveaways.

* ``[p]setgiveaways rqamariweeklyexp <profile> <rq_amari_weekly_exp>``
 Amari's weekly Exp of the user required to join the giveaways.

* ``[p]setgiveaways rqblacklistedroles <profile> <rq_blacklisted_roles>``
 Roles that can't join the giveaways.

* ``[p]setgiveaways rqbypassroles <profile> <rq_bypass_roles>``
 Roles that bypass the requirements of the giveaways.

* ``[p]setgiveaways rqdiscordjoineddays <profile> <rq_discord_joined_days>``
 Days since the user joined Discord required to join the giveaways.

* ``[p]setgiveaways rqguildjoineddays <profile> <rq_guild_joined_days>``
 Days since the user joined the guild required to join the giveaways.

* ``[p]setgiveaways rqlevelupexp <profile> <rq_levelup_exp>``
 LevelUp's Exp of the user required to join the giveaways.

* ``[p]setgiveaways rqleveluplevel <profile> <rq_levelup_level>``
 LevelUp's Level of the user required to join the giveaways.

* ``[p]setgiveaways rqlevelupmessages <profile> <rq_levelup_messages>``
 LevelUp's messages of the user required to join the giveaways.

* ``[p]setgiveaways rqmessagesallowedchannels <profile> <rq_messages_allowed_channels>``
 Channels where the messages count is counted.

* ``[p]setgiveaways rqmessagescooldown <profile> <rq_messages_cooldown>``
 Cooldown in seconds between messages.

* ``[p]setgiveaways rqmessagescount <profile> <rq_messages_count>``
 Messages count of the user required to join the giveaways.

* ``[p]setgiveaways rqregexallowedchannels <profile> <rq_regex_allowed_channels>``
 Channels where the regex pattern is checked.

* ``[p]setgiveaways rqregexpatternmessagecontent <profile> <rq_regex_pattern_message_content>``
 Regex pattern for the message content required to join the giveaways.

* ``[p]setgiveaways rqrequiredroles <profile> <rq_required_roles>``
 Roles required to join the giveaways.

* ``[p]setgiveaways showsettings <profile> [with_dev=False]``
 Show all settings for the cog with defaults and values.

* ``[p]setgiveaways thankdonor <profile> <thank_donor>``
 Thank the donor when the giveaway starts.

* ``[p]setgiveaways thumbnailurl <profile> <thumbnail_url>``
 Thumbnail URL for the giveaways messages.

* ``[p]setgiveaways winnersrole <profile> <role>``
 Role to give to winners.

------------
Installation
------------

If you haven't added my repo before, lets add it first. We'll call it "AAA3A-cogs" here.

.. code-block:: ini

    [p]repo add AAA3A-cogs https://github.com/AAA3A-AAA3A/AAA3A-cogs

Now, we can install Giveaways.

.. code-block:: ini

    [p]cog install AAA3A-cogs giveaways

Once it's installed, it is not loaded by default. Load it by running the following command:

.. code-block:: ini

    [p]load giveaways

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
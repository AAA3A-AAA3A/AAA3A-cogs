.. _disurlvotestracker:
==================
DisurlVotesTracker
==================

This is the cog guide for the ``DisurlVotesTracker`` cog. This guide contains the collection of commands which you can use in the cog.
Through this guide, ``[p]`` will always represent your prefix. Replace ``[p]`` with your own prefix when you use these commands in Discord.

.. note::

    Ensure that you are up to date by running ``[p]cog update disurlvotestracker``.
    If there is something missing, or something that needs improving in this documentation, feel free to create an issue `here <https://github.com/AAA3A-AAA3A/AAA3A-cogs/issues>`_.
    This documentation is generated everytime this cog receives an update.

---------------
About this cog:
---------------

Track votes on Disurl, assign roles to voters and remind them to vote!

---------
Commands:
---------

Here are all the commands included in this cog (17):

* ``[p]disurlvotestracker``
 Commands to interact with DisurlVotesTracker.

* ``[p]disurlvotestracker leaderboard``
 Show the lifetime leaderboard of voters.

* ``[p]disurlvotestracker monthlyleaderboard``
 Show the monthly leaderboard of voters.

* ``[p]setdisurlvotestracker``
 Commands to configure DisurlVotesTracker.

* ``[p]setdisurlvotestracker customvotemessage <custom_vote_message>``
 Custom vote message. You can specify the ID or the link of an existing message, or provide an embed payload. Use the variables `{member_name}`, `{member_avatar_url}`, `{member_mention}`, `{member_id}`, `{guild_name}`, `{guild_icon_url}`, `{guild_id}`, `{votes_channel_name}`, `{votes_channel_mention}`, `{votes_channel_id}`, `{voters_role_name}`, `{voters_role_mention}`, `{voters_role_id}`, `{number_member_votes}`, `{number_member_monthly_votes}`, `{s_1}` (`number_member_votes` plural) and `{s_2}` (`number_member_monthly_votes` plural).

* ``[p]setdisurlvotestracker customvoteremindermessage <custom_vote_reminder_message>``
 Custom vote reminder message. You can specify the ID or the link of an existing message, or provide an embed payload. Use the variables `{member_name}`, `{member_avatar_url}`, `{member_mention}`, `{member_id}`, `{guild_name}`, `{guild_icon_url}`, `{guild_id}`, `{votes_channel_name}`, `{votes_channel_mention}`, `{votes_channel_id}`, `{voters_role_name}`, `{voters_role_mention}`, `{voters_role_id}`, `{number_member_votes}`, `{number_member_monthly_votes}`, `{s_1}` (`number_member_votes` plural) and `{s_2}` (`number_member_monthly_votes` plural).

* ``[p]setdisurlvotestracker disurlauthaurizationkey <disurl_authaurization_key>``
 Your Disurl authorization key, used to secure the Dashboard webhook. That's the key which you set on https://disurl.me/dashboard/server/GUILD_ID/webhooks.

* ``[p]setdisurlvotestracker enabled <enabled>``
 Toggle the cog. WARNING: Red-Web-Dashboard has to be installed and started for this to work.

* ``[p]setdisurlvotestracker getdebugloopsstatus``
 Get an embed for check loop status.

* ``[p]setdisurlvotestracker instructions``
 Instructions on how to set up DisurlVotesTracker.

* ``[p]setdisurlvotestracker modalconfig [confirmation=False]``
 Set all settings for the cog with a Discord Modal.

* ``[p]setdisurlvotestracker resetleaderboards [confirmation=False]``
 Reset the leaderboards.

* ``[p]setdisurlvotestracker resetsetting <setting>``
 Reset a setting.

* ``[p]setdisurlvotestracker showsettings [with_dev=False]``
 Show all settings for the cog with defaults and values.

* ``[p]setdisurlvotestracker votereminder <vote_reminder>``
 Toggle vote reminders. A reminder will be sent to voters 12 hours after their vote.

* ``[p]setdisurlvotestracker votersrole <voters_role>``
 The role that will be assigned to voters.

* ``[p]setdisurlvotestracker voteschannel <votes_channel>``
 The channel where votes notifications will be sent.

------------
Installation
------------

If you haven't added my repo before, lets add it first. We'll call it "AAA3A-cogs" here.

.. code-block:: ini

    [p]repo add AAA3A-cogs https://github.com/AAA3A-AAA3A/AAA3A-cogs

Now, we can install DisurlVotesTracker.

.. code-block:: ini

    [p]cog install AAA3A-cogs disurlvotestracker

Once it's installed, it is not loaded by default. Load it by running the following command:

.. code-block:: ini

    [p]load disurlvotestracker

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
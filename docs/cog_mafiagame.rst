.. _mafiagame:
=========
MafiaGame
=========

This is the cog guide for the ``MafiaGame`` cog. This guide contains the collection of commands which you can use in the cog.
Through this guide, ``[p]`` will always represent your prefix. Replace ``[p]`` with your own prefix when you use these commands in Discord.

.. note::

    Ensure that you are up to date by running ``[p]cog update mafiagame``.
    If there is something missing, or something that needs improving in this documentation, feel free to create an issue `here <https://github.com/AAA3A-AAA3A/AAA3A-cogs/issues>`_.
    This documentation is generated everytime this cog receives an update.

---------------
About this cog:
---------------

Play the Mafia game, with many roles (Mafia/Villagers/Neutral), modes (including Random and Custom), anomalies...!

---------
Commands:
---------

Here are all the commands included in this cog (53):

* ``[p]mafia``
 Play the Mafia game, with many roles (Mafia/Villagers/Neutral), modes (including Random and Custom), anomalies...

* ``[p]mafia achievements [role] [user=<you>]``
 Show your achievements or the achievements of a specific member.

* ``[p]mafia afkkill <member>``
 Kill a member for AFK from the Mafia game in this server.

* ``[p]mafia anomalies``
 Show the different anomalies of the Mafia game.

* ``[p]mafia anomaly <anomaly>``
 Show the information about a specific anomaly.

* ``[p]mafia defaultdyingmessage [default_dying_message]``
 Set your default custom dying message.

* ``[p]mafia explain [page=main]``
 Explain how to play the Mafia game.

* ``[p]mafia mode <mode>``
 Show the informations about a specific mode.

* ``[p]mafia modes``
 Show the different modes of the Mafia game.

* ``[p]mafia role <role>``
 Show the informations about a specific role.

* ``[p]mafia roles``
 Show the different roles of the Mafia game

* ``[p]mafia start [mode]``
 Start a game of Mafia!

* ``[p]mafia tempban <member> <duration>``
 Ban a member temporary from the Mafia game in this server.

* ``[p]mafia unban <member>``
 Unban a member from the Mafia game in this server.

* ``[p]setmafia``
 Settings for MafiaGame.

* ``[p]setmafia addreactions <add_reactions>``
 If this option is enabled, the alive players will be able to react to the messages.

* ``[p]setmafia afkdaysbeforekick <afk_days_before_kick>``
 The number of days before a player is kicked for being AFK.

* ``[p]setmafia afktempbanduration <afk_temp_ban_duration>``
 The duration in hours of the temp ban for being AFK.

* ``[p]setmafia alchemistlethalpotionnight1 <alchemist_lethal_potion_night_1>``
 If this option is enabled, the Alchemist will be able to use the lethal potion on Night 1.

* ``[p]setmafia allowspectators <allow_spectators>``
 If this option is enabled, the cog will allow spectators to watch the game.

* ``[p]setmafia anomalies <anomalies>``
 If this option is enabled, the anomalies will be enabled.

* ``[p]setmafia anonymousjudgement <anonymous_judgement>``
 If this option is enabled, the judgement will be anonymous.

* ``[p]setmafia anonymousvoting <anonymous_voting>``
 If this option is enabled, the voting will be anonymous.

* ``[p]setmafia category <category channel>``
 The category where the channel will be created.

* ``[p]setmafia channelautodelete <channel_auto_delete>``
 If this option is enabled, the channel will be automatically deleted after the game.

* ``[p]setmafia costtoplay <cost_to_play>``
 The cost to play the game.

* ``[p]setmafia customroles <custom_roles>``
 The roles that will be assigned at the beginning of the game, if the mode is `Custom`.

* ``[p]setmafia defaultmode <default_mode>``
 The default mode that will be used.

* ``[p]setmafia defendjudgement <defend_judgement>``
 If this option is enabled, the player who has been voted will be able to defend.

* ``[p]setmafia defendtimeout <defend_timeout>``
 The time in seconds to defend.

* ``[p]setmafia disabledanomalies <disabled_anomalies>``
 The anomalies that will be disabled.

* ``[p]setmafia disabledroles <disabled_roles>``
 The roles that will be disabled.

* ``[p]setmafia displayroleswhenstarting <display_roles_when_starting>``
 If this option is enabled, the cog will display the roles in game and their abilities when starting.

* ``[p]setmafia dyingmessage <dying_message>``
 If this option is enabled, the players will be able to set a custom death message.

* ``[p]setmafia gamelogs <game_logs>``
 If this option is enabled, the cog will log the game in an HTML file.

* ``[p]setmafia hoarderhoardsameplayeriffailed <hoarder_hoard_same_player_if_failed>``
 If this option is enabled, the Hoarder can hoard the same player again if they failed previously.

* ``[p]setmafia judgementtimeout <judgement_timeout>``
 The time in seconds to judge.

* ``[p]setmafia judgeprosecuteday1 <judge_prosecute_day_1>``
 If this option is enabled, the Judge will be able to prosecute on Day 1.

* ``[p]setmafia mafiacommunication <mafia_communication>``
 If this option is enabled, the Mafia members will be able to communicate.

* ``[p]setmafia modalconfig [confirmation=False]``
 Set all settings for the cog with a Discord Modal.

* ``[p]setmafia moreroles <more_roles>``
 If this option is enabled, the cog will add more roles to the game.

* ``[p]setmafia performactiontimeout <perform_action_timeout>``
 The time in seconds to perform an action.

* ``[p]setmafia redeconomy <red_economy>``
 If this option is enabled, the cog will integrate with the Red economy.

* ``[p]setmafia resetsetting <setting>``
 Reset a setting.

* ``[p]setmafia rewardforwinning <reward_for_winning>``
 The reward for winning the game.

* ``[p]setmafia rewardforwinningbasedoncosts <reward_for_winning_based_on_costs>``
 If this option is enabled, the reward for winning will be based on the costs and shared between the winners.

* ``[p]setmafia showdeadrole <show_dead_role>``
 If this option is enabled, the cog will show the dead role to the players.

* ``[p]setmafia showsettings [with_dev=False]``
 Show all settings for the cog with defaults and values.

* ``[p]setmafia talktimeout <talk_timeout>``
 The time in seconds to talk.

* ``[p]setmafia towntraitor <town_traitor>``
 If this option is enabled, the town will have a Traitor. The Traitor has to be killed within 3 days of last mafia death.

* ``[p]setmafia townvip <town_vip>``
 If this option is enabled, the town will have a VIP who have to be killed by Mafia before win.

* ``[p]setmafia vigilanteshootnight1 <vigilante_shoot_night_1>``
 If this option is enabled, the Vigilante will be able to shoot on Night 1.

* ``[p]setmafia votingtimeout <voting_timeout>``
 The time in seconds to vote.

------------
Installation
------------

If you haven't added my repo before, lets add it first. We'll call it "AAA3A-cogs" here.

.. code-block:: ini

    [p]repo add AAA3A-cogs https://github.com/AAA3A-AAA3A/AAA3A-cogs

Now, we can install MafiaGame.

.. code-block:: ini

    [p]cog install AAA3A-cogs mafiagame

Once it's installed, it is not loaded by default. Load it by running the following command:

.. code-block:: ini

    [p]load mafiagame

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
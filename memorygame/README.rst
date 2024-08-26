.. _memorygame:
==========
MemoryGame
==========

This is the cog guide for the ``MemoryGame`` cog. This guide contains the collection of commands which you can use in the cog.
Through this guide, ``[p]`` will always represent your prefix. Replace ``[p]`` with your own prefix when you use these commands in Discord.

.. note::

    Ensure that you are up to date by running ``[p]cog update memorygame``.
    If there is something missing, or something that needs improving in this documentation, feel free to create an issue `here <https://github.com/AAA3A-AAA3A/AAA3A-cogs/issues>`_.
    This documentation is generated everytime this cog receives an update.

---------------
About this cog:
---------------

Play to Memory game, with buttons, leaderboard and Red bank!

---------
Commands:
---------

Here are all the commands included in this cog (12):

* ``[p]memorygame ["3x3"|"4x4"|"5x5"=5x5]``
 Play to Memory game. Choose between `3x3`, `4x4` and `5x5` versions.

* ``[p]memorygameleaderboard``
 Show MemoryGame leaderboard.

* ``[p]setmemorygame``
 Group of commands to set MemoryGame.

* ``[p]setmemorygame maxprize <max_prize>``
 Set the max prize for Red bank system and cog leaderboard. Default is 5000.

* ``[p]setmemorygame maxwrongmatches <max_wrong_matches>``
 Set the maximum tries for each game. Use `0` for no limit.

* ``[p]setmemorygame modalconfig [confirmation=False]``
 Set all settings for the cog with a Discord Modal.

* ``[p]setmemorygame redeconomy <red_economy>``
 If this option is enabled, the cog will give credits to the user each time the game is won.

* ``[p]setmemorygame reductionpersecond <reduction_per_second>``
 Set the reduction per second of prize for Red bank system and cog leaderboard. Default is 5.

* ``[p]setmemorygame reductionperwrongmatch <reduction_per_wrong_match>``
 Set the reduction per wrong match of prize for Red bank system and cog leaderboard. Default is 15.

* ``[p]setmemorygame resetleaderboard``
 Reset leaderboard in the guild.

* ``[p]setmemorygame resetsetting <setting>``
 Reset a setting.

* ``[p]setmemorygame showsettings [with_dev=False]``
 Show all settings for the cog with defaults and values.

------------
Installation
------------

If you haven't added my repo before, lets add it first. We'll call it "AAA3A-cogs" here.

.. code-block:: ini

    [p]repo add AAA3A-cogs https://github.com/AAA3A-AAA3A/AAA3A-cogs

Now, we can install MemoryGame.

.. code-block:: ini

    [p]cog install AAA3A-cogs memorygame

Once it's installed, it is not loaded by default. Load it by running the following command:

.. code-block:: ini

    [p]load memorygame

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
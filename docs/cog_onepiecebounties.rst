.. _onepiecebounties:
================
OnePieceBounties
================

This is the cog guide for the ``OnePieceBounties`` cog. This guide contains the collection of commands which you can use in the cog.
Through this guide, ``[p]`` will always represent your prefix. Replace ``[p]`` with your own prefix when you use these commands in Discord.

.. note::

    Ensure that you are up to date by running ``[p]cog update onepiecebounties``.
    If there is something missing, or something that needs improving in this documentation, feel free to create an issue `here <https://github.com/AAA3A-AAA3A/AAA3A-cogs/issues>`_.
    This documentation is generated everytime this cog receives an update.

---------------
About this cog:
---------------

Give One Piece's bounties to your members, based on their time in the server, their level and their roles, then generate their wanted posters, and also welcome them when they join!

---------
Commands:
---------

Here are all the commands included in this cog (25):

* ``[p]bounty [member=<you>]``
 🏴‍☠️ Get the bounty of a member.

* ``[p]bountylb``
 🏴‍☠️ Get the bounty leaderboard.

* ``[p]setonepiecebounties``
 Configure One Piece Bounties.

* ``[p]setonepiecebounties addbonus [member] <bonus>``
 Add a bonus to a member's bounty.

* ``[p]setonepiecebounties addbonusrole <role> <min_bounty> <max_bounty>``
 Add a bonus role to the bounty calculation.

* ``[p]setonepiecebounties addonlyrole <role> <"alive"|"dead">``
 Add a role to the only roles list.

* ``[p]setonepiecebounties basebounty <base_bounty>``
 Set the base bounty for all members.

* ``[p]setonepiecebounties clearbonus [member]``
 Clear a member's bonus.

* ``[p]setonepiecebounties includeleveluplevels <include_levelup_levels>``
 Include LevelUp levels in bounty calculation.

* ``[p]setonepiecebounties includemonthssincejoining <include_months_since_joining>``
 Include months since joining in bounty calculation.

* ``[p]setonepiecebounties listbonuses``
 List all bonuses.

* ``[p]setonepiecebounties listbonusroles``
 List all bonus roles.

* ``[p]setonepiecebounties listonlyroles``
 List all only roles.

* ``[p]setonepiecebounties modalconfig [confirmation=False]``
 Set all settings for the cog with a Discord Modal.

* ``[p]setonepiecebounties randombasebounty <random_base_bounty>``
 Enable or disable randomization of the base bounty.

* ``[p]setonepiecebounties removebonus [member] <bonus>``
 Remove a bonus from a member's bounty.

* ``[p]setonepiecebounties removebonusrole <role>``
 Remove a bonus role from the bounty calculation.

* ``[p]setonepiecebounties removeonlyrole <role>``
 Remove a role from the only roles list.

* ``[p]setonepiecebounties resetsetting <setting>``
 Reset a setting.

* ``[p]setonepiecebounties setaccuratejoinedat [member=<you>] [date]``
 Set the accurate joined at date of a member in the format `YYYY-MM-DD`.

* ``[p]setonepiecebounties showsettings [with_dev=False]``
 Show all settings for the cog with defaults and values.

* ``[p]setonepiecebounties welcomechannel <welcome_channel>``
 Set the welcome channel.

* ``[p]setonepiecebounties welcomeenabled <welcome_enabled>``
 Enable or disable the welcome message.

* ``[p]setonepiecebounties welcomelinkbuttons <welcome_link_buttons>``
 Set the link buttons for the welcome message.

* ``[p]setonepiecebounties welcomelogposechannels <welcome_log_pose_channels>``
 Set the log pose channels for the welcome message.

------------
Installation
------------

If you haven't added my repo before, lets add it first. We'll call it "AAA3A-cogs" here.

.. code-block:: ini

    [p]repo add AAA3A-cogs https://github.com/AAA3A-AAA3A/AAA3A-cogs

Now, we can install OnePieceBounties.

.. code-block:: ini

    [p]cog install AAA3A-cogs onepiecebounties

Once it's installed, it is not loaded by default. Load it by running the following command:

.. code-block:: ini

    [p]load onepiecebounties

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
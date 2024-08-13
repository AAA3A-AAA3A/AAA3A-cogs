.. _personalreact:
=============
PersonalReact
=============

This is the cog guide for the 'PersonalReact' cog. This guide contains the collection of commands which you can use in the cog.
Through this guide, ``[p]`` will always represent your prefix. Replace ``[p]`` with your own prefix when you use these commands in Discord.

.. note::

    Ensure that you are up to date by running ``[p]cog update personalreact``.
    If there is something missing, or something that needs improving in this documentation, feel free to create an issue `here <https://github.com/AAA3A-AAA3A/AAA3A-cogs/issues>`_.
    This documentation is auto-generated everytime this cog receives an update.

--------------
About this cog
--------------

Make the bot react to messages with your mention, reply or your custom trigger, based on roles perks!

--------
Commands
--------

Here are all the commands included in this cog (24):

* ``[p]personalreact``
 Make the bot react to messages with your mention, reply or your custom trigger!

* ``[p]personalreact addreaction <reaction>``
 Add a reaction.

* ``[p]personalreact customtrigger <custom_trigger>``
 Set a custom trigger.

* ``[p]personalreact disable``
 Disable PersonalReact for you.

* ``[p]personalreact enable``
 Enable PersonalReact for you.

* ``[p]personalreact ignorebots <toggle>``
 Ignore bots.

* ``[p]personalreact ignoremyself <toggle>``
 Ignore yourself.

* ``[p]personalreact reactions [reactions]...``
 Set your reactions.

* ``[p]personalreact removereaction <reaction>``
 Remove a reaction.

* ``[p]personalreact replies <toggle>``
 Allow the bot to react on the messages which ping you in replies.

* ``[p]personalreact view``
 View your PersonalReact settings.

* ``[p]setpersonalreact``
 Set PersonalReact settings.

* ``[p]setpersonalreact addbaserolerequirement <role> <amount>``
 Add a base role requirement.

* ``[p]setpersonalreact addcustomtriggerrolerequirement <role> <amount>``
 Add a custom trigger role requirement.

* ``[p]setpersonalreact blacklistedchannels <blacklisted_channels>``
 The channels where the bot won't react.

* ``[p]setpersonalreact cooldown <cooldown>``
 The cooldown in seconds between each message from the same person to react.

* ``[p]setpersonalreact maxreactionspermember <max_reactions_per_member>``
 The maximum number of reactions a member can set for them.

* ``[p]setpersonalreact mincustomtriggerlength <min_custom_trigger_length>``
 The minimum length of a custom trigger.

* ``[p]setpersonalreact modalconfig [confirmation=False]``
 Set all settings for the cog with a Discord Modal.

* ``[p]setpersonalreact removebaserolerequirement <role>``
 Remove a base role requirement.

* ``[p]setpersonalreact removectrolerequirement <role>``
 Remove a custom trigger role requirement.

* ``[p]setpersonalreact resetsetting <setting>``
 Reset a setting.

* ``[p]setpersonalreact roles``
 Set the roles requirements.

* ``[p]setpersonalreact showsettings [with_dev=False]``
 Show all settings for the cog with defaults and values.

------------
Installation
------------

If you haven't added my repo before, lets add it first. We'll call it
"AAA3A-cogs" here.

.. code-block:: ini

    [p]repo add AAA3A-cogs https://github.com/AAA3A-AAA3A/AAA3A-cogs

Now, we can install PersonalReact.

.. code-block:: ini

    [p]cog install AAA3A-cogs personalreact

Once it's installed, it is not loaded by default. Load it by running the following command:

.. code-block:: ini

    [p]load personalreact

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

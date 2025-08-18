.. _lastmentions:
============
LastMentions
============

This is the cog guide for the ``LastMentions`` cog. This guide contains the collection of commands which you can use in the cog.
Through this guide, ``[p]`` will always represent your prefix. Replace ``[p]`` with your own prefix when you use these commands in Discord.

.. note::

    Ensure that you are up to date by running ``[p]cog update lastmentions``.
    If there is something missing, or something that needs improving in this documentation, feel free to create an issue `here <https://github.com/AAA3A-AAA3A/AAA3A-cogs/issues>`_.
    This documentation is generated everytime this cog receives an update.

---------------
About this cog:
---------------

Check the last mentions you received easily and get your or server statistics!

---------
Commands:
---------

Here are all the commands included in this cog (17):

* ``[p]lastmentions``
 Check the last mentions you received easily and get your or server statistics.

* ``[p]lastmentions ignore <member_or_channel>``
 Ignore a member or channel for Last Mentions.

* ``[p]lastmentions ignoreme``
 Mark yourself as ignored for Last Mentions and clear your data.

* ``[p]lastmentions serverstats``
 Show the server statistics for Last Mentions.

* ``[p]lastmentions show``
 Show the last mentions you received.

* ``[p]lastmentions stats``
 Show your statistics for Last Mentions.

* ``[p]lastmentions unignore <member_or_channel>``
 Unignore a member or channel for Last Mentions.

* ``[p]setlastmentions``
 Configure the Last Mentions settings.

* ``[p]setlastmentions enabled <enabled>``
 Toggle the cog in the server.

* ``[p]setlastmentions ignorebots <ignore_bots>``
 Ignore mentions from bots.

* ``[p]setlastmentions maxmentionsper5minutes <max_mentions_per_5_minutes>``
 Maximum number of mentions allowed per member in a 5-minute window before ignoring further mentions in that period.

* ``[p]setlastmentions maxmentionspermember <max_mentions_per_member>``
 Maximum number of mentions to store per member.

* ``[p]setlastmentions modalconfig [confirmation=False]``
 Set all settings for the cog with a Discord Modal.

* ``[p]setlastmentions resetsetting <setting>``
 Reset a setting.

* ``[p]setlastmentions retentiondays <retention_days>``
 Number of days to keep the mentions.

* ``[p]setlastmentions showsettings [with_dev=False]``
 Show all settings for the cog with defaults and values.

* ``[p]setlastmentions trackreplies <track_replies>``
 Track replies to mentions.

------------
Installation
------------

If you haven't added my repo before, lets add it first. We'll call it "AAA3A-cogs" here.

.. code-block:: ini

    [p]repo add AAA3A-cogs https://github.com/AAA3A-AAA3A/AAA3A-cogs

Now, we can install LastMentions.

.. code-block:: ini

    [p]cog install AAA3A-cogs lastmentions

Once it's installed, it is not loaded by default. Load it by running the following command:

.. code-block:: ini

    [p]load lastmentions

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
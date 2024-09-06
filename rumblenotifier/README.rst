.. _rumblenotifier:
==============
RumbleNotifier
==============

This is the cog guide for the ``RumbleNotifier`` cog. This guide contains the collection of commands which you can use in the cog.
Through this guide, ``[p]`` will always represent your prefix. Replace ``[p]`` with your own prefix when you use these commands in Discord.

.. note::

    Ensure that you are up to date by running ``[p]cog update rumblenotifier``.
    If there is something missing, or something that needs improving in this documentation, feel free to create an issue `here <https://github.com/AAA3A-AAA3A/AAA3A-cogs/issues>`_.
    This documentation is generated everytime this cog receives an update.

---------------
About this cog:
---------------

Ping a role when a rumble starts, and let members suscribe or unsuscribe from the notifications!

---------
Commands:
---------

Here are all the commands included in this cog (8):

* ``[p]setrumblenotifier``
 Settings for the RumbleNotifier cog.

* ``[p]setrumblenotifier channels <channels>``
 The channels/categories where the cog will detect rumbles.

* ``[p]setrumblenotifier enabled <enabled>``
 Enable or disable the cog.

* ``[p]setrumblenotifier modalconfig [confirmation=False]``
 Set all settings for the cog with a Discord Modal.

* ``[p]setrumblenotifier resetsetting <setting>``
 Reset a setting.

* ``[p]setrumblenotifier role <role>``
 The role that will be pinged when a rumble starts.

* ``[p]setrumblenotifier showsettings [with_dev=False]``
 Show all settings for the cog with defaults and values.

* ``[p]setrumblenotifier suscribing <suscribing>``
 Enable or disable the suscribing system.

------------
Installation
------------

If you haven't added my repo before, lets add it first. We'll call it "AAA3A-cogs" here.

.. code-block:: ini

    [p]repo add AAA3A-cogs https://github.com/AAA3A-AAA3A/AAA3A-cogs

Now, we can install RumbleNotifier.

.. code-block:: ini

    [p]cog install AAA3A-cogs rumblenotifier

Once it's installed, it is not loaded by default. Load it by running the following command:

.. code-block:: ini

    [p]load rumblenotifier

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
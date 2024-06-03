.. _dashboard:
=========
Dashboard
=========

This is the cog guide for the 'Dashboard' cog. This guide contains the collection of commands which you can use in the cog.
Through this guide, ``[p]`` will always represent your prefix. Replace ``[p]`` with your own prefix when you use these commands in Discord.

.. note::

    Ensure that you are up to date by running ``[p]cog update dashboard``.
    If there is something missing, or something that needs improving in this documentation, feel free to create an issue `here <https://github.com/AAA3A-AAA3A/AAA3A-cogs/issues>`_.
    This documentation is auto-generated everytime this cog receives an update.

--------------
About this cog
--------------

Interact with your bot through a web dashboard!

⚠️ This package is a fork of Neuro Assassin's work, and isn't endorsed by the Org at all.

--------
Commands
--------

Here are all the commands included in this cog (17):

* ``[p]setdashboard``
 Configure Dashboard.

* ``[p]setdashboard allinone <all_in_one>``
 Run the Dashboard in the bot process, without having to open another window. You have to install Red-Dashboard in your bot venv with Pip and reload the cog.

* ``[p]setdashboard defaultbackgroundtheme <default_background_theme>``
 Set the default background theme of the dashboard.

* ``[p]setdashboard defaultcolor <default_color>``
 Set the default color of the dashboard.

* ``[p]setdashboard defaultsidebartheme <default_sidebar_theme>``
 Set the default sidebar theme of the dashboard.

* ``[p]setdashboard disabledthirdparties <disabled_third_parties>``
 The third parties to disable.

* ``[p]setdashboard flaskflags <flask_flags>``
 The flags used to setting the webserver if `all_in_one` is enabled. They are the cli flags of `reddash` without `--rpc-port`.

* ``[p]setdashboard metadescription <meta_description>``
 The website description to use.

* ``[p]setdashboard metaicon <meta_icon>``
 The website description to use.

* ``[p]setdashboard metatitle <meta_title>``
 The website title to use.

* ``[p]setdashboard metawebsitedescription <meta_website_description>``
 The website description to use.

* ``[p]setdashboard modalconfig [confirmation=False]``
 Set all settings for the cog with a Discord Modal.

* ``[p]setdashboard redirecturi <redirect_uri>``
 The redirect uri to use for the Discord OAuth.

* ``[p]setdashboard resetsetting <setting>``
 Reset a setting.

* ``[p]setdashboard secret [secret]``
 Set the client secret needed for Discord OAuth.

* ``[p]setdashboard showsettings [with_dev=False]``
 Show all settings for the cog with defaults and values.

* ``[p]setdashboard supportserver <support_server>``
 Set the support server url of your bot.

------------
Installation
------------

If you haven't added my repo before, lets add it first. We'll call it
"AAA3A-cogs" here.

.. code-block:: ini

    [p]repo add AAA3A-cogs https://github.com/AAA3A-AAA3A/AAA3A-cogs

Now, we can install Dashboard.

.. code-block:: ini

    [p]cog install AAA3A-cogs dashboard

Once it's installed, it is not loaded by default. Load it by running the following command:

.. code-block:: ini

    [p]load dashboard

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

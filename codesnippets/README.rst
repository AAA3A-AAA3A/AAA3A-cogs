.. _codesnippets:
============
CodeSnippets
============

This is the cog guide for the 'CodeSnippets' cog. This guide contains the collection of commands which you can use in the cog.
Through this guide, ``[p]`` will always represent your prefix. Replace ``[p]`` with your own prefix when you use these commands in Discord.

.. note::

    Ensure that you are up to date by running ``[p]cog update codesnippets``.
    If there is something missing, or something that needs improving in this documentation, feel free to create an issue `here <https://github.com/AAA3A-AAA3A/AAA3A-cogs/issues>`_.
    This documentation is auto-generated everytime this cog receives an update.

--------------
About this cog
--------------

A cog to send code content from a GitHub/Gist/GitLab/BitBucket/Pastebin/Hastebin URL!

--------
Commands
--------

Here are all the commands included in this cog (5):

* ``[p]codesnippets [limit=3] <urls>``
 Send code content from a GitHub/Gist/GitLab/BitBucket/Pastebin/Hastebin URL.

* ``[p]setcodesnippets``
 Configure CodeSnippets.

* ``[p]setcodesnippets addchannel <channel>``
 Add a channel where the cog have to send automatically code snippets from URLs.

* ``[p]setcodesnippets removechannel <channel>``
 Remove a channel where the cog have to send automatically code snippets from URLs.

* ``[p]setcodesnippets showsettings [with_dev=False]``
 Show all settings for the cog with defaults and values.

------------
Installation
------------

If you haven't added my repo before, lets add it first. We'll call it
"AAA3A-cogs" here.

.. code-block:: ini

    [p]repo add AAA3A-cogs https://github.com/AAA3A-AAA3A/AAA3A-cogs

Now, we can install CodeSnippets.

.. code-block:: ini

    [p]cog install AAA3A-cogs codesnippets

Once it's installed, it is not loaded by default. Load it by running the following command:

.. code-block:: ini

    [p]load codesnippets

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

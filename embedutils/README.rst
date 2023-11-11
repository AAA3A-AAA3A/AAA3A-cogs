.. _embedutils:
==========
EmbedUtils
==========

This is the cog guide for the 'EmbedUtils' cog. This guide contains the collection of commands which you can use in the cog.
Through this guide, ``[p]`` will always represent your prefix. Replace ``[p]`` with your own prefix when you use these commands in Discord.

.. note::

    Ensure that you are up to date by running ``[p]cog update embedutils``.
    If there is something missing, or something that needs improving in this documentation, feel free to create an issue `here <https://github.com/AAA3A-AAA3A/AAA3A-cogs/issues>`_.
    This documentation is auto-generated everytime this cog receives an update.

--------------
About this cog
--------------

Create, send, and store embeds!

--------
Commands
--------

Here are all the commands included in this cog (17):

* ``[p]embed [channel_or_message] [color] <title> <description>``
 Post a simple embed with a color, a title and a description.

* ``[p]embed download <message> [index] [include_content=False]``
 Download a JSON file for a message's embed(s).

* ``[p]embed downloadstored [global_level=False] <name>``
 Download a JSON file for a stored embed.

* ``[p]embed edit <message> <json|yaml|jsonfile|yamlfile|pastebin|message> [data]``
 Edit a message sent by [botname].

* ``[p]embed fromfile [channel_or_message]``
 Post an embed from a valid JSON file (upload it).

* ``[p]embed info [global_level=False] <name>``
 Get info about a stored embed.

* ``[p]embed json [channel_or_message] [data]``
 Post embeds from valid JSON.

* ``[p]embed list [global_level=False]``
 Get info about a stored embed.

* ``[p]embed message [channel_or_message] <message> [index] [include_content=False]``
 Post embed(s) from an existing message.

* ``[p]embed migratefromphen``
 Migrate stored embeds from EmbedUtils by Phen.

* ``[p]embed pastebin [channel_or_message] <data>``
 Post embeds from a GitHub/Gist/Pastebin/Hastebin link containing valid JSON.

* ``[p]embed poststored [channel_or_message=<CurrentChannel>] [global_level=False] <names>``
 Post stored embeds.

* ``[p]embed postwebhook [channel_or_message=<CurrentChannel>] <username> <avatar_url> [global_level=False] <names>``
 Post stored embeds with a webhook.

* ``[p]embed store [global_level=False] [locked=False] <name> <json|yaml|jsonfile|yamlfile|pastebin|message> [data]``
 Store an embed.

* ``[p]embed unstore [global_level=False] <name>``
 Remove a stored embed.

* ``[p]embed yaml [channel_or_message] [data]``
 Post embeds from valid YAML.

* ``[p]embed yamlfile [channel_or_message]``
 Post an embed from a valid YAML file (upload it).

------------
Installation
------------

If you haven't added my repo before, lets add it first. We'll call it
"AAA3A-cogs" here.

.. code-block:: ini

    [p]repo add AAA3A-cogs https://github.com/AAA3A-AAA3A/AAA3A-cogs

Now, we can install EmbedUtils.

.. code-block:: ini

    [p]cog install AAA3A-cogs embedutils

Once it's installed, it is not loaded by default. Load it by running the following command:

.. code-block:: ini

    [p]load embedutils

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

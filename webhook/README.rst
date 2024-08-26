.. _webhook:
=======
Webhook
=======

This is the cog guide for the ``Webhook`` cog. This guide contains the collection of commands which you can use in the cog.
Through this guide, ``[p]`` will always represent your prefix. Replace ``[p]`` with your own prefix when you use these commands in Discord.

.. note::

    Ensure that you are up to date by running ``[p]cog update webhook``.
    If there is something missing, or something that needs improving in this documentation, feel free to create an issue `here <https://github.com/AAA3A-AAA3A/AAA3A-cogs/issues>`_.
    This documentation is generated everytime this cog receives an update.

---------------
About this cog:
---------------

Various webhook commands to create and send messages along webhooks!

---------
Commands:
---------

Here are all the commands included in this cog (14):

* ``[p]webhook``
 Various webhook commands to create and send messages along webhooks.

* ``[p]webhook clear [confirmation=False]``
 Delete all webhooks in this server.

* ``[p]webhook closesession [channel]``
 Close an ongoing webhook session in a channel.

* ``[p]webhook clyde [channel] [content]``
 Sends a message a channel as a webhook using Clyde's display name and avatar.

* ``[p]webhook create [channel] [webhook_name]``
 Creates a webhook in the channel specified with the name specified.

* ``[p]webhook custom [channel] <username> <avatar_url> [content]``
 Sends a message a channel as a webhook using a specified display name and a specified avatar url.

* ``[p]webhook edit <message> [content]``
 Edit a message sent by a webhook.

* ``[p]webhook permissions``
 Show all members in the server that have the permission `manage_webhooks`.

* ``[p]webhook reverse [channel] <member> [content]``
 

* ``[p]webhook reversed [channel] <message>``
 

* ``[p]webhook say [channel] [content]``
 Sends a message in a channel as a webhook using your display name and your avatar.

* ``[p]webhook send <webhook_link> <content>``
 Sends a message to the specified webhook using your display name and you avatar.

* ``[p]webhook session <webhook_link>``
 Initiate a session within this channel sending messages to a specified webhook link.

* ``[p]webhook sudo [channel] <member> [content]``
 Sends a message in a channel as a webhook using the display name and the avatar of a specified member.

------------
Installation
------------

If you haven't added my repo before, lets add it first. We'll call it "AAA3A-cogs" here.

.. code-block:: ini

    [p]repo add AAA3A-cogs https://github.com/AAA3A-AAA3A/AAA3A-cogs

Now, we can install Webhook.

.. code-block:: ini

    [p]cog install AAA3A-cogs webhook

Once it's installed, it is not loaded by default. Load it by running the following command:

.. code-block:: ini

    [p]load webhook

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
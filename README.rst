================================================
Redbot cogs for Red-DiscordBot authored by AAA3A
================================================

This is my cog repo for the redbot, a multifunctional Discord bot!

------------
Installation
------------

Primarily, make sure you have `downloader` loaded.

.. code-block:: ini

    [p]load downloader

Next, let's add my repository to your system.

.. code-block:: ini

    [p]repo add AAA3A https://github.com/AAA3A-AAA3A/AAA3A-cogs

To install a cog, use this command, replacing <cog> with the name of the cog you wish to install:

.. code-block:: ini

    [p]cog install AAA3A <cog>

-------------------
Available cogs list
-------------------

This list of cogs is not up to date. At the time of writing there are 22. You can look at the folder names on this repo or see a more complete description on Red's Index or in the README for each cog.

**SimpleSanction:**

A cog to gather all sanction/moderation actions (userinfo, warn, ban, sofban, tempban, kick, mute, mutechannel, tempmute, tempmutechannel) in one menu with buttons/reactions.  Many options like a Fake mode, show the author of the command in the embeds or not, show an embed at the end describing the action or not, a confirmation or not, a reason required or not... All options can be included in the command, but are also all optional: whatever is needed will be requested later.

Short version: [p]sanction

Long version: [p]sanction 10 @user true true true true true true true 3d Spam.

There is also a slash command, a context menu for the user and another for the messages (note that this doesn't work all the time because the bot sends a message in the same channel, gets the context of this message, changes the author and invokes the real command).

**TicketTool:**

A cog to set up a ticket system on your server, with many options. It has many commands in a ticket channel to export all messages in the ticket, close it, reopen it, delete the channel, log, change the owner of the ticket, claim the ticket, add/remove a member to the ticket, etc. Many roles: a ping role, an admin role, a support role, a view role, a ticket role...

**CmdChannel:**

Allow bot moderators to type commands in a command channel with a result in the specified channel.
There are settings for server administrators (logs, delete message, information with command in specified channel, disable commands).
There is a possibility to imitate a user and also the user and the channel at the same time.

**Calculator:**

A cog to use a calculator directly in Discord, with buttons. You can also enter the calculation directly as an argument to the command. Buttons allow parentheses, square roots (with parentheses required), moving around the expression, deleting the last character...

**AntiNuke:**

This cog allows you to prevent raids on your servers. If you give a person too many permissions, they can destroy everything by deleting each channel one by one. With this cog, the bot will delete all the roles (and therefore permissions) of the person if they delete a channel (unless they are the server owner).

**ClearChannel:**

This cog will remove ALL messages from the channel in which the command is made. It clones it and deletes the old one. By default, only the server owner (and the bot owner) can use it for security reasons. There are several options: an embed at the beginning of the new channel to say that the channel has been renitialized, a dm to the author of the command, and an additional security feature allowing the old channel to be simply renamed instead of deleted (to keep the messages).

**TransferChannel:**

A cog to transfer messages from one channel to another with embeds or single messages or single messages with webhooks (name and avatar of the original author). Warning: this cog uses the Discord api many times during transfers.

**Ip:**

A cog to display the external ip address of the bot and a command for the web address with support for ip and a custom port.

------------
Contributing
------------

If you have ideas, you can open a problem. If you have coded new features, make a PR. I'm happy to make changes to these cogs!

-----------------
Translate my cogs
-----------------

The associated crowdin project is available at this address: https://crowdin.com/project/aaa3a-cogs

If you would like to see languages added to this project, please let me know.

-------
Support
-------

Check out my docs `here <https://aaa3a-cogs.readthedocs.io/en/latest/>`_.
Mention me in the #support_othercogs in the `cog support server <https://discord.gg/GET4DVk>`_ if you need any help.
Please ping me or contact me in DM.
Additionally, feel free to open an issue or pull request to this repo.

-------
Credits
-------

* Thanks to Matt from the Medicat community for letting me discover Red!

* Thanks to @epic guy on Discord for the basic syntax (command groups, commands) and also commands (await ctx.send, await ctx.author.send, await ctx.message.delete())!

* Thanks to the developers of the cogs I saw as it taught me how to make a cog! (Chessgame by WildStriker, Captcha by Kreusada, Speak by Epic guy and Rommer by Dav, for example)

* Thanks to all the people who helped me with some commands in the #coding channel of the redbot support server!

* Individual credits in each cog.

* Thanks to 26, Aika, Yami, Jack, Flame, Draper, Zeph and others for the discussions that helped me develop my cogs!

* Thanks to Kreusada because his repo served as a model for mine! Everything in the documentation uses the layout of his.

* Thanks to Nado on Discord and Flame for giving me the solution to fix my repo, which Downloader could not update anymore!

* Thanks to Yami for the technique in the init file of some cogs to load the interaction client only if it is not already loaded! Before this fix, when a user clicked a button, the actions would be run about 10 times, causing a huge spam and loop in the channel.

* Thanks to Lemon for his help and many cogs ideas!

* Thanks to WitherredAway for the Draw cog!

* Thanks to amyrinbot on GitHub for a part of the GetDocs cog's code!

-------
LICENSE
-------

This repository and its cogs are protected under the MIT License.

For further information, please click `here <https://github.com/AAA3A-AAA3A/AAA3A-cogs/blob/main/LICENSE>`_

Copyright (c) 2022 AAA3A
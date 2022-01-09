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

Here is the list of cogs in my repo. There are (so far) only 2.

**SimpleSanction:**

A cog to gather all sanction/moderation actions (userinfo, warn, ban, sofban, tempban, kick, mute, mutechannel, tempmute, tempmutechannel) in one menu with buttons/reactions.  Many options like a Fake mode, show the author of the command in the embeds or not, show an embed at the end describing the action or not, a confirmation or not, a reason required or not... All options can be included in the command, but are also all optional: whatever is needed will be requested later.

Short version: [p]sanction

Long version: [p]sanction 10 @user true true true true true true true 3d Spam.

There is also a slash command, a context menu for the user and another for the messages (note that this doesn't work all the time because the bot sends a message in the same channel, gets the context of this message, changes the author and invokes the real command).

**CmdChannel:**

Allow bot moderators to type commands in a command channel with a result in the specified channel.
There are settings for server administrators (logs, delete message, information with command in specified channel, disable commands).
There is a possibility to imitate a user and also the user and the channel at the same time.

**AntiRaid:**

This cog allows you to prevent raids on your servers. If you give a person too many permissions, they can destroy everything by deleting each channel one by one. With this cog, the bot will delete all the roles (and therefore permissions) of the person if he deletes a channel (unless he is the server owner).

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

-------
Support
-------

Mention me in the #support_othercogs in the `cog support server <https://discord.gg/GET4DVk>`_ if you need any help.
Please ping me or contact me in DM.
Additionally, feel free to open an issue or pull request to this repo.

-------
Credits
-------

**Credits for the cog SimpleSanction:**

* Thanks to @epic guy on Discord for the basic syntax (command groups, commands) and also commands (await ctx.send, await ctx.author.send, await ctx.message.delete())!

* Thanks to Laggrons-dumb's WarnSystem cog (https://github.com/laggron42/Laggrons-Dumb-Cogs/tree/v3/warnsystem) for giving me some ideas and code for subcommands for a main command!

* Thanks to @YamiKaitou on Discord for the technique in the init file to load the interaction client only if it is not loaded! Before this fix, when a user clicked on a button, the actions would be launched about 10 times, which caused huge spam and a loop in the channel.

* Thanks to @Aikaterna on the Redbot support server for help on displaying the main command help menu and other commands!

* Thanks to the developers of the cogs I added features to as it taught me how to make a cog! (Chessgame by WildStriker, Captcha by Kreusada, Speak by Epic guy and Rommer by Dav)

* Thanks to all the people who helped me with some commands in the #coding channel of the redbot support server!

**Credits for the cog CmdChannel:**

* Thanks to @epic guy on Discord for the basic syntax (command groups, commands) and also commands (await ctx.send, await ctx.author.send, await ctx.message.delete())!

* Thanks to TrustyJAID for the code (a bit modified to work here and to improve as needed) for the log messages sent! (https://github.com/TrustyJAID/Trusty-cogs/tree/master/extendedmodlog)

* Thanks to Kreusada for the code (with modifications to make it work and match the syntax of the rest) to add a log channel or remove it if no channel is specified! (https://github.com/Kreusada/Kreusada-Cogs/tree/master/captcha)

* Thanks to the developers of the cogs I added features to as it taught me how to make a cog! (Chessgame by WildStriker, Captcha by Kreusada, Speak by Epic guy and Rommer by Dav)

* Thanks to all the people who helped me with some commands in the #coding channel of the redbot support server!

**Credits for the cog AntiRaid:**

* Thanks to @epic guy on Discord for the basic syntax (command groups, commands) and also commands (await ctx.send, await ctx.author.send, await ctx.message.delete())!

* Thanks to TrustyJAID for the code (a bit modified to work here and to improve as needed) for the log messages sent! (https://github.com/TrustyJAID/Trusty-cogs/tree/master/extendedmodlog)

* Thanks to the developers of the cogs I added features to as it taught me how to make a cog! (Chessgame by WildStriker, Captcha by Kreusada, Speak by Epic guy and Rommer by Dav)

* Thanks to all the people who helped me with some commands in the #coding channel of the redbot support server!

**Credits for the cog ClearChannel:**

* Thanks to @epic guy on Discord for the basic syntax (command groups, commands) and also commands (await ctx.send, await ctx.author.send, await ctx.message.delete())!

* Thanks to the developers of the cogs I added features to as it taught me how to make a cog! (Chessgame by WildStriker, Captcha by Kreusada, Speak by Epic guy and Rommer by Dav)

* Thanks to all the people who helped me with some commands in the #coding channel of the redbot support server!

**Credits for the cog TransferChannel:**

* Thanks to @epic guy on Discord for the basic syntax (command groups, commands) and also commands (await ctx.send, await ctx.author.send, await ctx.message.delete())!

* Thanks to TrustyJAID's Backup for starting the command to list the latest source channel messages! (https://github.com/TrustyJAID/Trusty-cogs/tree/master/backup)

* Thanks to QuoteTools from SimBad for the embed!

* Thanks to Speak from @epic guy for the webhooks! (https://github.com/npc203/npc-cogs/tree/main/speak)

* Thanks to Say from LaggronsDumb for the attachments in the single messages and webhooks! (https://github.com/laggron42/Laggrons-Dumb-Cogs/tree/v3/say)

* Thanks to the developers of the cogs I added features to as it taught me how to make a cog! (Chessgame by WildStriker, Captcha by Kreusada, Speak by Epic guy and Rommer by Dav)

* Thanks to all the people who helped me with some commands in the #coding channel of the redbot support server!
  
**Credits for the cog Ip:**

* Thanks to @AverageGamer on Discord for the cog idea and the code to find the external ip!

* Thanks to @epic guy on Discord for the basic syntax (command groups, commands) and also commands (await ctx.send, await ctx.author.send, await ctx.message.delete())!

-------
LICENSE
-------

This repository and its cogs are protected under the MIT License.

For further information, please click `here <https://github.com/AAA3A-AAA3A/AAA3A-cogs/blob/master/LICENSE>`_

Copyright (c) 2021 AAA3A-AAA3A

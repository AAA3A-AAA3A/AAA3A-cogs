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

**CmdChannel:**

Allow bot moderators to type commands in a command channel with a result in the specified channel.
There are settings for server administrators (logs, delete message, information with command in specified channel, disable commands).
There is a possibility to imitate a user and also the user and the channel at the same time.

**AntiRaid:**

This cog allows you to prevent raids on your servers. If you give a person too many permissions, they can destroy everything by deleting each channel one by one. With this cog, the bot will delete all the roles (and therefore permissions) of the person if he deletes a channel (unless he is the server owner).

**Ip:**

A cog to display the external ip address of the bot and a command for the web address with support for ip and a custom port.
In order for cog to calculate the ip address for both commands, please install "requests" with this command.

    python -m pip install requests

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

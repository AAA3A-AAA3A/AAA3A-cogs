.. _rolesbuttons:
============
RolesButtons
============

This is the cog guide for the 'RolesButtons' cog. This guide contains the collection of commands which you can use in the cog.
Through this guide, ``[p]`` will always represent your prefix. Replace ``[p]`` with your own prefix when you use these commands in Discord.

.. note::

    Ensure that you are up to date by running ``[p]cog update rolesbuttons``.
    If there is something missing, or something that needs improving in this documentation, feel free to create an issue `here <https://github.com/AAA3A-AAA3A/AAA3A-cogs/issues>`_.
    This documentation is auto-generated everytime this cog receives an update.

--------------
About this cog
--------------

A cog to have roles-buttons!

--------
Commands
--------

Here are all the commands included in this cog (7):

* ``[p]rolesbuttons``
 Group of commands to use RolesButtons.

* ``[p]rolesbuttons add <message> <emoji> <role> ["1"|"2"|"3"|"4"=2] [text_button=None]``
 Add a role-button for a message.

* ``[p]rolesbuttons bulk <message> [roles_buttons]...``
 Add roles-buttons for a message.

* ``[p]rolesbuttons clear <message>``
 Clear all roles-buttons for a message.

* ``[p]rolesbuttons mode <message> <"add_or_remove"|"add_only"|"remove_only"|"replace">``
 Choose a mode for a roles-buttons message.

* ``[p]rolesbuttons purge``
 Clear all roles-buttons for a guild.

* ``[p]rolesbuttons remove <message> <emoji>``
 Remove a role-button for a message.

------------
Installation
------------

If you haven't added my repo before, lets add it first. We'll call it
"AAA3A-cogs" here.

.. code-block:: ini

    [p]repo add AAA3A-cogs https://github.com/AAA3A-AAA3A/AAA3A-cogs

Now, we can install RolesButtons.

.. code-block:: ini

    [p]cog install AAA3A-cogs rolesbuttons

Once it's installed, it is not loaded by default. Load it by running the following command:

.. code-block:: ini

    [p]load rolesbuttons

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

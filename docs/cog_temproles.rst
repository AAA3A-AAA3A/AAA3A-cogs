.. _temproles:
=========
TempRoles
=========

This is the cog guide for the 'TempRoles' cog. This guide contains the collection of commands which you can use in the cog.
Through this guide, ``[p]`` will always represent your prefix. Replace ``[p]`` with your own prefix when you use these commands in Discord.

.. note::

    Ensure that you are up to date by running ``[p]cog update temproles``.
    If there is something missing, or something that needs improving in this documentation, feel free to create an issue `here <https://github.com/AAA3A-AAA3A/AAA3A-cogs/issues>`_.
    This documentation is auto-generated everytime this cog receives an update.

--------------
About this cog
--------------

A cog to assign temporary roles to users, expiring after a set time!

--------
Commands
--------

Here are all the commands included in this cog (11):

* ``[p]temproles``
 Assign TempRoles roles to users, expiring after a set time.

* ``[p]temproles addallowedselftemprole <role> [min_time=1 day, 0:00:00] [max_time=365 days, 0:00:00]``
 Add an allowed self Temp Role.

* ``[p]temproles assign <member> <role> <time>``
 Assign/Add a TempRole to a member, for a specified duration.

* ``[p]temproles edit <member> <role> <time>``
 Edit a TempRole for a member, for a specified duration.

* ``[p]temproles list [member] [role]``
 List active Temp Roles on this server, for optional specified member and/or role.

* ``[p]temproles logschannel [logs_channel]``
 Set the logs channel for Temp Roles.

* ``[p]temproles removeallowedselftemprole <role>``
 Remove an allowed self Temp Role.

* ``[p]temproles selfassign <role> <time>``
 Assign/Add an allowed self Temp Role to yourself, for a specified duration.

* ``[p]temproles selflist``
 Unassign/Remove an allowed self Temp Role from yourself.

* ``[p]temproles selfunassign <role>``
 Unassign/Remove an allowed self Temp Role from yourself.

* ``[p]temproles unassign <member> <role>``
 Unassign/Remove a TempRole from a member.

------------
Installation
------------

If you haven't added my repo before, lets add it first. We'll call it
"AAA3A-cogs" here.

.. code-block:: ini

    [p]repo add AAA3A-cogs https://github.com/AAA3A-AAA3A/AAA3A-cogs

Now, we can install TempRoles.

.. code-block:: ini

    [p]cog install AAA3A-cogs temproles

Once it's installed, it is not loaded by default. Load it by running the following command:

.. code-block:: ini

    [p]load temproles

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

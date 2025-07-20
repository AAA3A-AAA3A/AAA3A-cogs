.. _reach:
=====
Reach
=====

This is the cog guide for the ``Reach`` cog. This guide contains the collection of commands which you can use in the cog.
Through this guide, ``[p]`` will always represent your prefix. Replace ``[p]`` with your own prefix when you use these commands in Discord.

.. note::

    Ensure that you are up to date by running ``[p]cog update reach``.
    If there is something missing, or something that needs improving in this documentation, feel free to create an issue `here <https://github.com/AAA3A-AAA3A/AAA3A-cogs/issues>`_.
    This documentation is generated everytime this cog receives an update.

---------------
About this cog:
---------------

Check the reach of ping roles in specific channels and find the closest ping roles for the number of members you want to ping!

---------
Commands:
---------

Here are all the commands included in this cog (8):

* ``[p]reach``
 Check the reach of ping roles in specific channels and find the closest ping roles for the number of members you want to ping!

* ``[p]reach addroleforsearch <role>``
 Add a role to the list of roles to search for.

* ``[p]reach check [channel] [roles]... [include_statuses=False]``
 Check the reach of specific ping roles in a specific channel.

* ``[p]reach clearrolesforsearch``
 Clear the list of roles to search for.

* ``[p]reach listrolesforsearch``
 List the roles that are in the list of roles to search for.

* ``[p]reach removeroleforsearch <role>``
 Remove a role from the list of roles to search for.

* ``[p]reach search [channel] <amount> [possible_combinations=1] [possible_roles=[]]... [include_statuses=False]``
 Find the closest ping roles for the amount of members you want to ping in a specific channel.

* ``[p]reach setrolesforsearch [roles]...``
 Set the roles to search for. This will replace the current list of roles to search for.

------------
Installation
------------

If you haven't added my repo before, lets add it first. We'll call it "AAA3A-cogs" here.

.. code-block:: ini

    [p]repo add AAA3A-cogs https://github.com/AAA3A-AAA3A/AAA3A-cogs

Now, we can install Reach.

.. code-block:: ini

    [p]cog install AAA3A-cogs reach

Once it's installed, it is not loaded by default. Load it by running the following command:

.. code-block:: ini

    [p]load reach

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
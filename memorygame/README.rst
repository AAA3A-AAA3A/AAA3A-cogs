.. _getdocs:
=======
GetDocs
=======

This is the cog guide for the 'GetDocs' cog. This guide contains the collection of commands which you can use in the cog.
Through this guide, ``[p]`` will always represent your prefix. Replace ``[p]`` with your own prefix when you use these commands in Discord.

.. note::

    Ensure that you are up to date by running ``[p]cog update getdocs``.
    If there is something missing, or something that needs improving in this documentation, feel free to create an issue `here <https://github.com/AAA3A-AAA3A/AAA3A-cogs/issues>`_.
    This documentation is auto-generated everytime this cog receives an update.

--------------
About this cog
--------------

A cog to get and display Sphinx docs! Use `[p]listsources` to get a list of all the available sources.

--------
Commands
--------

Here are all the commands included in this cog (6):

* ``[p]getdocs [source=discord.py] [query=None]``
 View rich documentation for a specific node/query.

* ``[p]listsources ["available"|"all"|"disabled"=available]``
 Shows a list of all sources, those that are available or those that are disabled.

* ``[p]rtfm [source=discord.py] [limit=10] [with_std=True] [query=None]``
 Show all attributes matching your search.

* ``[p]setgetdocs``
 Commands to configure GetDocs.

* ``[p]setgetdocs disablesource <source>``
 Disable a documentations source.

* ``[p]setgetdocs enablesource <source>``
 Enable a documentations source.

------------
Installation
------------

If you haven't added my repo before, lets add it first. We'll call it
"AAA3A-cogs" here.

.. code-block:: ini

    [p]repo add AAA3A-cogs https://github.com/AAA3A-AAA3A/AAA3A-cogs

Now, we can install GetDocs.

.. code-block:: ini

    [p]cog install AAA3A-cogs getdocs

Once it's installed, it is not loaded by default. Load it by running the following command:

.. code-block:: ini

    [p]load getdocs

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

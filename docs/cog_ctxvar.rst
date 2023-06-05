.. _ctxvar:
======
CtxVar
======

This is the cog guide for the 'CtxVar' cog. This guide contains the collection of commands which you can use in the cog.
Through this guide, ``[p]`` will always represent your prefix. Replace ``[p]`` with your own prefix when you use these commands in Discord.

.. note::

    Ensure that you are up to date by running ``[p]cog update ctxvar``.
    If there is something missing, or something that needs improving in this documentation, feel free to create an issue `here <https://github.com/AAA3A-AAA3A/AAA3A-cogs/issues>`_.
    This documentation is auto-generated everytime this cog receives an update.

--------------
About this cog
--------------

A cog to list and display the contents of all sub-functions of `ctx`!

--------
Commands
--------

Here are all the commands included in this cog (6):

* ``[p]ctxvar``
 Commands for CtxVar.

* ``[p]ctxvar astdump [include_attributes=False] <thing>``
 Execute `ast.dump(ast.parse(<code content>))` on the provided object (debug not async).

* ``[p]ctxvar ctx [message=None] [args=None]``
 Display a list of all attributes and their values of the 'ctx' class instance or its sub-attributes.

* ``[p]ctxvar dir <thing> [search=None]``
 Display a list of all attributes of the provided object (debug not async).

* ``[p]ctxvar inspect [show_all] <thing>``
 Execute `rich.help(obj=object, ...)` on the provided object (debug not async).

* ``[p]ctxvar whatis <thing>``
 List attributes of the provided object like dpy objects (debug not async).

------------
Installation
------------

If you haven't added my repo before, lets add it first. We'll call it
"AAA3A-cogs" here.

.. code-block:: ini

    [p]repo add AAA3A-cogs https://github.com/AAA3A-AAA3A/AAA3A-cogs

Now, we can install CtxVar.

.. code-block:: ini

    [p]cog install AAA3A-cogs ctxvar

Once it's installed, it is not loaded by default. Load it by running the following command:

.. code-block:: ini

    [p]load ctxvar

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

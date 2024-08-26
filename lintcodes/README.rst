.. _lintcodes:
=========
LintCodes
=========

This is the cog guide for the ``LintCodes`` cog. This guide contains the collection of commands which you can use in the cog.
Through this guide, ``[p]`` will always represent your prefix. Replace ``[p]`` with your own prefix when you use these commands in Discord.

.. note::

    Ensure that you are up to date by running ``[p]cog update lintcodes``.
    If there is something missing, or something that needs improving in this documentation, feel free to create an issue `here <https://github.com/AAA3A-AAA3A/AAA3A-cogs/issues>`_.
    This documentation is generated everytime this cog receives an update.

---------------
About this cog:
---------------

A cog to lint a code from Discord, with Flake8, PyLint, MyPy, Bandit, Black, Isort, Yapf, AutoFlake8, PyRight and Ruff!

---------
Commands:
---------

Here are all the commands included in this cog (17):

* ``[p]lintcode``
 

* ``[p]lintcode abandit <flags>``
 Format code with Bandit, with flags.

* ``[p]lintcode aflake8 <flags>``
 Format code with Flake8, with flags.

* ``[p]lintcode amypy <flags>``
 Format code with MyPy, with flags.

* ``[p]lintcode apylint <flags>``
 Format code with PyLint, with flags.

* ``[p]lintcode apyright <flags>``
 Format code with PyRight, with flags.

* ``[p]lintcode aruff <flags>``
 Format code with Ruff, with flags.

* ``[p]lintcode autopep8 [code]``
 Format code with AutoPep8, without flags, just the code.

* ``[p]lintcode bandit [code]``
 Format code with Bandit, without flags, just the code.

* ``[p]lintcode black [code]``
 Format code with Black, without flags, just the code.

* ``[p]lintcode flake8 [code]``
 Format code with Flake8, without flags, just the code.

* ``[p]lintcode isort [code]``
 Format code with Isort, without flags, just the code.

* ``[p]lintcode mypy [code]``
 Format code with MyPy, without flags, just the code.

* ``[p]lintcode pylint [code]``
 Format code with PyLint, without flags, just the code.

* ``[p]lintcode pyright [code]``
 Format code with PyRight, without flags, just the code.

* ``[p]lintcode ruff [code]``
 Format code with Ruff, without flags, just the code.

* ``[p]lintcode yapf [code]``
 Format code with Yapf, without flags, just the code.

------------
Installation
------------

If you haven't added my repo before, lets add it first. We'll call it "AAA3A-cogs" here.

.. code-block:: ini

    [p]repo add AAA3A-cogs https://github.com/AAA3A-AAA3A/AAA3A-cogs

Now, we can install LintCodes.

.. code-block:: ini

    [p]cog install AAA3A-cogs lintcodes

Once it's installed, it is not loaded by default. Load it by running the following command:

.. code-block:: ini

    [p]load lintcodes

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
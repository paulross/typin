.. highlight:: shell

============
Installation
============

First make a virtual environment in your :file:`{<PYTHONVENVS>}`, say :file:`{~/pyvenvs}`:

.. code-block:: console

    $ python3 -m venv <PYTHONVENVS>/typin
    $ . <PYTHONVENVS>/typin/bin/activate
    (typin) $


Stable release
--------------

To install typin, run this command in your terminal:

.. code-block:: console

    $ pip install typin

This is the preferred method to install typin, as it will always install the most recent stable release. 

If you don't have `pip`_ installed, this `Python installation guide`_ can guide
you through the process.

.. _pip: https://pip.pypa.io
.. _Python installation guide: http://docs.python-guide.org/en/latest/starting/installation/


From sources
------------

The sources for typin can be downloaded from the `Github repo`_.

You can either clone the public repository:

.. code-block:: console

    $ git clone git://github.com/paulross/typin

Or download the `tarball`_:

.. code-block:: console

    $ curl  -OL https://github.com/paulross/typin/tarball/master

Once you have a copy of the source, you can install it with:

.. code-block:: console

    $ python setup.py install

Install the test dependencies and run typin's tests:

.. code-block:: console

    (typin) $ pip install pytest
    (typin) $ pip install pytest-runner
    (typin) $ python setup.py test

Developing with typin
----------------------------

If you are developing with typin you need test coverage and documentation tools.

Test Coverage
^^^^^^^^^^^^^^^^

Install ``pytest-cov``:

.. code-block:: console

    (typin) $ pip install pytest-cov

The most meaningful invocation that elimates the top level tools is:

.. code-block:: console

    (typin) $ pytest --cov=typin --cov-report html tests/

Documentation
^^^^^^^^^^^^^^^^

If you want to build the documentation you need to:

.. code-block:: console

    (typin) $ pip install Sphinx
    (typin) $ cd docs
    (typin) $ make html

The landing page is *docs/_build/html/index.html*.

.. _Github repo: https://github.com/paulross/typin
.. _tarball: https://github.com/paulross/typin/tarball/master

.. moduleauthor:: Paul Ross <apaulross@gmail.com>
.. sectionauthor:: Paul Ross <apaulross@gmail.com>

Example
======================

There is a CLI interface ``typin/src/typin/typin_cli.py`` to execute arbitrary
python code using ``compile()`` and ``exec()`` like this::
    
    python typin_cli.py --stubs=stubs -- example.py 'foo bar baz'

This will ``compile()/exec()`` ``example.py`` with the arguments ``foo bar baz``
and dump out the results. These include the docstrings for the functions in ``example.py`` which
have been inserted in that source code to produce this:

.. _typin.ref.example:

example.py
----------------------

.. automodule:: typin.example
    :members:


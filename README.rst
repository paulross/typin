typin README
============

``typin`` is a *Type Inferencer* for understanding what types of objects
are flowing through your Python code. It observes your code dynamically and can
record all the types that each function sees, returns or raises.
``typin`` can then use this information to create Python's type annotations or
``__doc__`` strings to insert into your code.

``typin`` is currently proof-of-concept and a very early prototype.
It is Python 3 only at the moment.
There is a forthcoming project https://github.com/paulross/pytest-typin which
turns ``typin`` into a pytest plugin so that your unit tests can generate type
annotations and documentation strings.

Example
--------

Lets say you have a function that creates a repeated string, like this:

.. code-block:: python

    def function(s, num):
        if num < 1:
            raise ValueError('Value must be > 0, not {:d}'.format(num))
        lst = []
        while num:
            lst.append(s)
            num -= 1
        return ' '.join(lst)

You can exercise this under the watchful gaze of ``typin``:

.. code-block:: python

    from typin import type_inferencer

    with type_inferencer.TypeInferencer() as ti:
        assert function('Hi', 2) == 'Hi Hi'

You can then get the types that ``typin`` has observed as a string suitable for
a stub file:

.. code-block:: python

    ti.stub_file_str(__file__, '', 'function')
    # returns: 'def function(s: str, num: int) -> str: ...'

Then adding code that provokes the exception we can track that as well:

.. code-block:: python

    from typin import type_inferencer

    with type_inferencer.TypeInferencer() as ti:
        assert function('Hi', 2) == 'Hi Hi' # As before
        try:
            function('Hi', 0)
        except ValueError:
            pass

Exception specifications are not part of Python's type annotation but they are
part of of the Sphinx documentation string standard and ``typin`` can provide that, and
the line number where it should be inserted:

.. code-block:: python

    line_number, docstring = ti.docstring(__file__, '', 'function', style='sphinx')
    docstring
    """
    <insert documentation for function>

    :param s: <insert documentation for argument>
    :type s: ``str``

    :param num: <insert documentation for argument>
    :type num: ``int``

    :returns: ``str`` -- <insert documentation for return values>

    :raises: ``ValueError``
    """
    # Insert template docstrings into the source code.
    new_src = ti.insert_docstrings(__file__, style='sphinx')
    with open(__file__, 'w') as f:
        for line in new_src:
            f.write(line)

Sadly ``typin`` is not smart enough to write the documentation text for you :-)

There is a CLI interface ``typin_cli`` that is an entry point to ``typin/src/typin/typin_cli.py``.
This  executes arbitrary python code using ``compile()`` and ``exec()`` like the following example.
Note use of ``--`` followed by Python script then the arguments for that script surrounded by quotes:

.. code-block:: console

    $ python typin_cli.py --stubs=stubs/ --write-docstrings=docstrings/ -- example.py 'foo bar baz'

This will ``compile()/exec()`` ``example.py`` with the arguments ``foo bar baz``
write the stub files (``'.pyi'`` files) to ``stubs/`` and the source code with the docstrings
inserted to ``docstrings/``.

``typin_cli.py`` help:

.. code-block:: console

    $ python typin_cli.py --help
    usage: typin_cli.py [-h] [-l LOGLEVEL] [-d] [-t] [-e EVENTS_TO_TRACE]
                        [-s STUBS] [-w WRITE_DOCSTRINGS]
                        [--docstring-style DOCSTRING_STYLE] [-r ROOT]
                        program argstring

    typin_cli - Infer types of Python functions.
      Created by Paul Ross on 2017-10-25. Copyright 2017. All rights reserved.
      Version: v0.1.0 Licensed under MIT License
    USAGE

    positional arguments:
      program               Python target file to be compiled and executed.
      argstring             Argument as a string to give to the target. Prefix
                            this with '--' to avoid them getting consumed by
                            typin_cli.py

    optional arguments:
      -h, --help            show this help message and exit
      -l LOGLEVEL, --loglevel LOGLEVEL
                            Log Level (debug=10, info=20, warning=30, error=40,
                            critical=50) [default: 30]
      -d, --dump            Dump results on stdout after processing. [default:
                            False]
      -t, --trace-frame-events
                            Very verbose trace output, one line per frame event.
                            [default: False]
      -e EVENTS_TO_TRACE, --events-to-trace EVENTS_TO_TRACE
                            Events to trace (additive). [default: []] i.e. every
                            event.
      -s STUBS, --stubs STUBS
                            Directory to write stubs files. [default: ]
      -w WRITE_DOCSTRINGS, --write-docstrings WRITE_DOCSTRINGS
                            Directory to write source code with docstrings.
                            [default: ]
      --docstring-style DOCSTRING_STYLE
                            Style of docstrings, can be: 'google', 'sphinx'.
                            [default: sphinx]
      -r ROOT, --root ROOT  Root path of the Python packages to generate stub
                            files for. [default: .]


.. image:: https://img.shields.io/pypi/v/typin.svg
        :target: https://pypi.python.org/pypi/typin

.. image:: https://img.shields.io/travis/paulross/typin.svg
        :target: https://travis-ci.org/paulross/typin

.. image:: https://readthedocs.org/projects/typin/badge/?version=latest
        :target: https://typin.readthedocs.io/en/latest/?badge=latest
        :alt: Documentation Status

.. image:: https://pyup.io/repos/github/paulross/typin/shield.svg
     :target: https://pyup.io/repos/github/paulross/typin/
     :alt: Updates


Python type inferencing.

* Free software: MIT license
* Documentation: https://typin.readthedocs.io.

Features
--------

* TODO

Credits
---------

This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage

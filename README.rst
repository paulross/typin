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

Lets say you have a function that creates a repeated string, like this::

    def function(s, num):
        if num < 1:
            raise ValueError('Value must be > 0, not {:d}'.format(num))
        lst = []
        while num:
            lst.append(s)
            num -= 1
        return ' '.join(lst)

You can exercise this under the watchful gaze of ``typin``::

    from typin import type_inferencer

    with type_inferencer.TypeInferencer() as ti:
        assert function('Hi', 2) == 'Hi Hi'
        try:
            function('Hi', 0)
        except ValueError:
            pass

You can then get the types that ``typin`` has observed as a string suitable for
a stub file::

    ti.stub_file_str(__file__, '', 'function')
    # returns: 'def function(s: str, num: int) -> str: ...'

Then adding code that provokes the exception we can track that as well:

.. code-block:: python
    :emphasize-lines: 5-8

    from typin import type_inferencer

    with type_inferencer.TypeInferencer() as ti:
        assert function('Hi', 2) == 'Hi Hi' # As before
        try:
            function('Hi', 0)
        except ValueError:
            pass

Exception specification are not part of Python's type annotation but they are
part of of the Sphinx documentation string standard and ``typin`` can provide that, and
the line number where it should be inserted::

    line, docstring = ti.docstring(__file__, '', 'function', style='sphinx')
    docstring
    """<insert documentation for function>
    :param s: <insert documentation for argument>
    :type s: str
    :param num: <insert documentation for argument>
    :type num: int
    :returns: str -- <insert documentation for return values>
    :raises: ValueError"""
    # 'line' is the line before which the documentation string should be inserted.
    # If 'src' is the source code as a list of strings then inserting the
    # documentation string is done by:
    # src[:line_number] + docstring + src[line_number:]



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

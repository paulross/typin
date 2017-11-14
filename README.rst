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

You can then get the types that ``typin`` has observed as a string suitable for
a stub file::

    ti.stub_file_str(__file__, '', 'function')
    # returns: 'def function(s: str, num: int) -> str: ...'

Then adding code that provokes the exception we can track that as well::

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

    line_number, docstring = ti.docstring(__file__, '', 'function', style='sphinx')
    '"""{:s}"""'.format(docstring)
    """<insert documentation for function>
    
    :param s: <insert documentation for argument>
    :type s: str
    
    :param num: <insert documentation for argument>
    :type num: int
    
    :returns: str -- <insert documentation for return values>
    
    :raises: ValueError"""
    # 'line_number' is the line of the function definition where the documentation string
    # should be inserted. These can be inserted thus:
    with open(__file__) as f:
        src = f.readlines()
    new_src = src[:line_number] + docstring.split('\n') + src[line_number:]
    with open(__file__, 'w') as f:
        for line in new_src:
            f.write(line)
    # Obviously you want to insert the docstrings in reverse line order with multiple functions.
    # ti.docstring_map(file_path) will return a dict of:
    # {line_number : (namespace, function_name, docstring), ...}
    # for the file.

Sadly ``typin`` is not smart enough to write the documentation text for you :-)

There is a CLI interface ``typin/src/typin/typin_cli.py`` to execute arbitrary
python code using ``compile()`` and ``exec()`` like this::
    
    python typin_cli.py --stubs=stubs -- example.py 'foo bar baz'

This will ``compile()/exec()`` ``example.py`` with the arguments ``foo bar baz``
and dump out the results.

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

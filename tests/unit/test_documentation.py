import pytest

from typin import type_inferencer

def function(s, num):
    if num < 1:
        raise ValueError('Value must be > 0, not {:d}'.format(num))
    lst = []
    while num:
        lst.append(s)
        num -= 1
    return ' '.join(lst)

def test_function_raises_ValueError():
    with pytest.raises(ValueError):
        function('Hi', 0)

def test_function():
    assert function('Hi', 2) == 'Hi Hi'


def function_checks_type(s, num):
    if not isinstance(s, str):
        raise TypeError('s must be an string, not {:s}'.format(type(num)))
    if not isinstance(num, int):
        raise TypeError('num must be an integer, not {:s}'.format(type(num)))
    if num < 1:
        raise ValueError('Value must be > 0, not {:d}'.format(num))
    return ' '.join([s for _i in range(num)])
#     return 'Hi ' * num

def test_function_checks_type_raises_TypeError():
    with pytest.raises(TypeError):
        function_checks_type('Hi', 'bad argument')
    with pytest.raises(TypeError):
        function_checks_type(2, 'bad argument')

def test_function_checks_type_raises_ValueError():
    with pytest.raises(ValueError):
        function_checks_type('Hi', 0)


def test_function_annotation():
    with type_inferencer.TypeInferencer() as ti:
        assert function('Hi', 2) == 'Hi Hi'
        try:
            function('Hi', 0)
        except ValueError:
            pass
    expected = [
        'def function(s: str, num: int) -> str: ...',
    ]
#     print()
#     print(ti.pretty_format(__file__))
    assert ti.pretty_format(__file__) == '\n'.join(expected)
    assert ti.stub_file_str(__file__, '', 'function') \
        == 'def function(s: str, num: int) -> str: ...'
    _line, docstring = ti.docstring(__file__, '', 'function', style='sphinx')
#     print()
#     print(docstring)
    expected_docstring = """<insert documentation for function>
:param s: <insert documentation for argument>
:type s: str
:param num: <insert documentation for argument>
:type num: int
:returns: str -- <insert documentation for return values>
:raises: ValueError"""
    assert docstring == expected_docstring
    
def test_function_raises():
    with type_inferencer.TypeInferencer() as ti:
        try:
            function_checks_type('Hi', 'str')
        except TypeError:
            pass
        try:
            function_checks_type(2, 'str')
        except TypeError:
            pass
        try:
            function_checks_type('Hi', 0)
        except ValueError:
            pass
    _line, docstring = ti.docstring(__file__, '', 'function_checks_type', style='sphinx')
#     print()
#     print(docstring)
    expected_docstring = """<insert documentation for function>
:param s: <insert documentation for argument>
:type s: int, str
:param num: <insert documentation for argument>
:type num: int, str
:returns:  -- <insert documentation for return values>
:raises: TypeError, ValueError"""
    assert docstring == expected_docstring
    

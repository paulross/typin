'''
Created on 22 Jun 2017

@author: paulross
'''
import collections # To test problematic named tuple
import base64 # Just used as an example of stdlib usage
import inspect
import io
import os
import pprint
# import sys

import pytest

from typin import type_inferencer

def test_creation():
    t = type_inferencer.TypeInferencer()
    assert t is not None

def test_RE_TEMPORARY_FILE():
    ti = type_inferencer.TypeInferencer()
    assert ti.is_temporary_file('<string>')
    assert ti.is_temporary_file('/Users/USER/Documents/workspace/typin/src/typin/<frozen importlib._bootstrap>')
    assert not ti.is_temporary_file('/Users/USER/Documents/workspace/typin/src/typin/typin_cli.py')

@pytest.mark.parametrize('string', [
    '@property',
    ' @property',
    '  @property',
    '@property ',
    '@property  ',
    ' @property ',
    '  @property  ',
])
def test_RE_DECORATOR(string):
    regex = type_inferencer.RE_DECORATOR
    assert regex.match(string) is not None
    assert regex.match(string).group(1) == 'property'

@pytest.mark.parametrize('string, result', [
    ('def foo():', ('foo', '):')),
    ('def foo():   ', ('foo', '):   ')),
    (' def foo():', ('foo', '):')),
    ('    def foo():', ('foo', '):')),
    ('    def foo():   ', ('foo', '):   ')),
    ('def foo(a, b, c):', ('foo', 'a, b, c):')),
    ('    def foo(\n', ('foo', '')),
])
def test_RE_FUNCTION(string, result):
    regex = type_inferencer.RE_FUNCTION
    assert regex.match(string) is not None
    assert regex.match(string).group(1) == result[0]
    assert regex.match(string).group(2) == result[1]

@pytest.mark.parametrize('string, result', [
    ('def foo(self):', ('foo', '):')),
    ('def foo(self):   ', ('foo', '):   ')),
    (' def foo(self):', ('foo', '):')),
    ('    def foo(self):', ('foo', '):')),
    ('    def foo(self):   ', ('foo', '):   ')),
    ('def foo(self, a, b, c):', ('foo', ', a, b, c):')),
    ('def foo(self,a, b, c):', ('foo', ',a, b, c):')),
    ('    def foo(self,\n', ('foo', ',')),
])
def test_RE_METHOD(string, result):
    regex = type_inferencer.RE_METHOD
    assert regex.match(string) is not None
    assert regex.match(string).group(1) == result[0]
    assert regex.match(string).group(2) == result[1]

# def _pretty_print(ti):
#     print(ti.pretty_format())

# def _pretty_format(ti, file=None):
#     str_list = []
#     if file is not None:
#         for function_name in sorted(ti.function_map[file]):
#             str_list.append('def {:s}{:s}'.format(
#                 function_name,
#                 ti.function_map[file][function_name].stub_file_str()
#                 )
#             )
#     else:
#         # {file_path : { function_name : FunctionTypes, ...}
#         for file_path in sorted(ti.function_map):
#             str_list.append('File: {:s}'.format(file_path))
#             for function_name in sorted(ti.function_map[file_path]):
#                 str_list.append('def {:s}{:s}'.format(
#                     function_name,
#                     ti.function_map[file_path][function_name].stub_file_str()
#                     )
#                 )
#     return '\n'.join(str_list)

def test_a_couple_of_functions():
    def func_single_arg_no_return(arg):
        pass

    def func_single_arg_return_arg(arg):
        return arg
    with type_inferencer.TypeInferencer() as ti:
        func_single_arg_no_return('string')
        func_single_arg_return_arg('string')
#     print()
#     print('test_single_function()')
#     _pretty_print(ti)
#     pprint.pprint(ti.function_map)
    expected = [
        'def func_single_arg_no_return(arg: str) -> None: ...',
        'def func_single_arg_return_arg(arg: str) -> str: ...',
    ]
    assert ti.pretty_format(__file__) == '\n'.join(expected)

def test_a_couple_of_functions_with_line_numbers():
    line_fn_1 = inspect.currentframe().f_lineno + 1
    def func_single_arg_no_return(arg):
        pass

    line_fn_2 = inspect.currentframe().f_lineno + 1
    def func_single_arg_return_arg(arg):
        return arg

    with type_inferencer.TypeInferencer() as ti:
        func_single_arg_no_return('string')
        func_single_arg_return_arg('string')
    expected = [
        'def func_single_arg_no_return(arg: str) -> None: ...#{:d}'.format(line_fn_1),
        'def func_single_arg_return_arg(arg: str) -> str: ...#{:d}'.format(line_fn_2),
    ]
    assert ti.pretty_format(__file__, add_line_number_as_comment=True) == '\n'.join(expected)

def test_single_function_that_raises():
    line_raises = inspect.currentframe().f_lineno + 2
    def func_that_raises():
        raise ValueError('Error message')

    with type_inferencer.TypeInferencer() as ti:
        try:
            func_that_raises()
        except ValueError:
            pass
#     print()
#     print('test_single_function_that_raises()')
#     _pretty_print(ti)
#     pprint.pprint(ti.function_map)
    expected = [
        'def func_that_raises() -> None: ...',
    ]
    assert ti.pretty_format(__file__) == '\n'.join(expected)
    fts = ti.function_types(__file__, '', 'func_that_raises')
    assert fts.exception_type_strings == {line_raises : {'ValueError'}}

def test_single_function_that_raises_and_catches():
    line_raises = inspect.currentframe().f_lineno + 3
    def func_that_raises_and_catches():
        try:
            raise ValueError('Error message')
        except ValueError as _err:
            pass
        return 'OK'

    with type_inferencer.TypeInferencer() as ti:
        func_that_raises_and_catches()
#     print()
#     pprint.pprint(ti.function_map)
#     print(ti.pretty_format(__file__))
    expected = [
        'def func_that_raises_and_catches() -> str: ...',
    ]
    assert ti.pretty_format(__file__) == '\n'.join(expected)
    fts = ti.function_types(__file__, '', 'func_that_raises_and_catches')
    # No exception recorded.
    assert fts.exception_type_strings == {}

def test_nested_function_that_raises():
    func_no_catch_line = inspect.currentframe().f_lineno + 2
    def func_no_catch():
        func_that_raises()

    func_that_raises_line = inspect.currentframe().f_lineno + 2
    def func_that_raises():
        raise ValueError('Error message')

    with type_inferencer.TypeInferencer() as ti:
        try:
            func_no_catch()
        except ValueError:
            pass
#     print()
#     pprint.pprint(ti.function_map)
#     print(ti.pretty_format(__file__))
    expected = [
        'def func_no_catch() -> None: ...',
        'def func_that_raises() -> None: ...',
    ]
    assert ti.pretty_format(__file__) == '\n'.join(expected)
    fts = ti.function_types(__file__, '', 'func_that_raises')
    assert fts.exception_type_strings == {func_that_raises_line : {'ValueError'}}
    fts = ti.function_types(__file__, '', 'func_no_catch')
    assert fts.exception_type_strings == {func_no_catch_line : {'ValueError'}}

def test_nested_functions_some_that_raises():
#     line_func_that_catches = inspect.currentframe().f_lineno + 1
    def func_that_catches():
        try:
            func_no_catch()
        except ValueError:
            pass

    line_func_no_catch = inspect.currentframe().f_lineno + 2
    def func_no_catch():
        func_that_raises()

    line_func_that_raises = inspect.currentframe().f_lineno + 2
    def func_that_raises():
        raise ValueError('Error message')

    with type_inferencer.TypeInferencer() as ti:
        func_that_catches()
#     print()
#     pprint.pprint(ti.function_map)
#     print(ti.pretty_format(__file__))
    expected = [
        'def func_no_catch() -> None: ...',
        'def func_that_catches() -> None: ...',
        'def func_that_raises() -> None: ...',
    ]
    assert ti.pretty_format(__file__) == '\n'.join(expected)
    fts = ti.function_types(__file__, '', 'func_that_catches')
    assert fts.exception_type_strings == {}
    fts = ti.function_types(__file__, '', 'func_no_catch')
    assert fts.exception_type_strings == {line_func_no_catch : {'ValueError'}}
    fts = ti.function_types(__file__, '', 'func_that_raises')
    assert fts.exception_type_strings == {line_func_that_raises : {'ValueError'}}

def test_function_within_function_that_raises():
    func_no_catch_line = inspect.currentframe().f_lineno + 2
    func_that_raises_line = inspect.currentframe().f_lineno + 2
    def func_no_catch():
        def func_that_raises():
            raise ValueError('Error message')
        func_that_raises()

    with type_inferencer.TypeInferencer() as ti:
        try:
            func_no_catch()
        except ValueError:
            pass
    print()
    print(' test_function_within_function_that_raises() '.center(75, '-'))
    pprint.pprint(ti.function_map)
    print(ti.pretty_format(__file__))

    expected = [
        'def func_no_catch() -> None: ...',
        'def func_that_raises() -> None: ...',
    ]
    assert ti.pretty_format(__file__) == '\n'.join(expected)
    fts = ti.function_types(__file__, '', 'func_that_raises')
    assert fts.exception_type_strings == {func_that_raises_line : {'ValueError'}}
    fts = ti.function_types(__file__, '', 'func_no_catch')
    assert fts.exception_type_strings == {func_no_catch_line : {'ValueError'}}


def test_single_function_that_might_raises_does_not_return_none():
    """Functions that raise will also be seen to return None from the same
    line even if they never return None."""
    def may_raise(v):
        if v == 0:
            raise ValueError('Value can not be zero')
        return 1.0 / v

    with type_inferencer.TypeInferencer() as ti:
        may_raise(1)
        try:
            may_raise(0)
        except ValueError:
            pass
    expected = [
        'def may_raise(v: int) -> float: ...',
    ]
#     print()
#     print(ti.pretty_format(__file__))
    assert ti.pretty_format(__file__) == '\n'.join(expected)

def test_single_function_that_might_raises_does_return_none():
    """Functions that raise will also be seen to return None from the same
    line. This function could also specifically return None."""
    def may_raise(v):
        if v == 0:
            raise ValueError('Value can not be zero')
        if v > 0:
            return 1.0 / v
        return None

    with type_inferencer.TypeInferencer() as ti:
        may_raise(1)
        may_raise(-1)
        try:
            may_raise(0)
        except ValueError:
            pass
    expected = [
        'def may_raise(v: int) -> Union[None, float]: ...',
    ]
#     print()
#     print(ti.pretty_format(__file__))
    assert ti.pretty_format(__file__) == '\n'.join(expected)

def test_context_manager_external():
    def function(v): pass
    ti = type_inferencer.TypeInferencer()
    with ti:
        function('string')
#     print()
#     pprint.pprint(ti.function_map)
#     print(ti.pretty_format(__file__))
    expected = [
        'def function(v: str) -> None: ...',
    ]
    assert ti.pretty_format(__file__) == '\n'.join(expected)

def test_context_manager_nested():
    def outer(v):
        pass
    def inner(v):
        pass
    def other(v):
        pass
    with type_inferencer.TypeInferencer() as ti_outer:
        outer('string')
        with type_inferencer.TypeInferencer() as ti_inner:
            inner(42)
        other(4.2)
#     print()
#     print(ti_outer.pretty_format(__file__))
#     print(ti_inner.pretty_format(__file__))
    expected_outer = [
        'def other(v: float) -> None: ...',
        'def outer(v: str) -> None: ...',
    ]
    assert ti_outer.pretty_format(__file__) == '\n'.join(expected_outer)
    expected_inner = [
        'def inner(v: int) -> None: ...',
    ]
    assert ti_inner.pretty_format(__file__) == '\n'.join(expected_inner)

def test_context_manager_nested_external():
    def outer(v):
        pass
    def inner(v):
        pass
    def other(v):
        pass
    ti = type_inferencer.TypeInferencer()
    with ti:
        outer('string')
        with ti:
            inner(42)
        other(4.2)
#     print()
#     print(ti_outer.pretty_format(__file__))
#     print(ti_inner.pretty_format(__file__))
    expected_outer = [
        'def inner(v: int) -> None: ...',
        'def other(v: float) -> None: ...',
        'def outer(v: str) -> None: ...',
    ]
    assert ti.pretty_format(__file__) == '\n'.join(expected_outer)

# ==== Test some functions that take basic builtins ====

# ---- Test numbers ---
def test_typeshed_integers():
    """Tests functions that take and return integers."""
    def one(i): return i
    def one_None(i): return None
    def many(i, j, k): return i * j * j
    with type_inferencer.TypeInferencer() as ti:
        one(4)
        one_None(4)
        many(1, 2, 3)
    expected = [
        'def many(i: int, j: int, k: int) -> int: ...',
        'def one(i: int) -> int: ...',
        'def one_None(i: int) -> None: ...',
    ]
    assert ti.pretty_format(__file__) == '\n'.join(expected)

def test_typeshed_float():
    """Tests functions that take and return floats."""
    def one(i): return i
    def one_None(i): return None
    def many(i, j, k): return i * j * j
    with type_inferencer.TypeInferencer() as ti:
        one(4.)
        one_None(4.)
        many(1., 2., 3.)
    expected = [
        'def many(i: float, j: float, k: float) -> float: ...',
        'def one(i: float) -> float: ...',
        'def one_None(i: float) -> None: ...',
    ]
    assert ti.pretty_format(__file__) == '\n'.join(expected)

def test_typeshed_complex():
    """Tests functions that take and return complex."""
    def one(i): return i
    def one_None(i): return None
    def many(i, j, k): return i * j * j
    with type_inferencer.TypeInferencer() as ti:
        one((4. + 0j))
        one_None((4. + 0j))
        many((1. + 0j), (2. + 0j), (3. + 0j))
    expected = [
        'def many(i: complex, j: complex, k: complex) -> complex: ...',
        'def one(i: complex) -> complex: ...',
        'def one_None(i: complex) -> None: ...',
    ]
    assert ti.pretty_format(__file__) == '\n'.join(expected)

def test_typeshed_mixed_union():
    """Tests functions that take and return complex."""
    def one(i): return i
    with type_inferencer.TypeInferencer() as ti:
        one(4)
        one(4.)
        one((4. + 0j))
    expected = [
        'def one(i: complex, float, int) -> Union[complex, float, int]: ...',
    ]
    assert ti.pretty_format(__file__) == '\n'.join(expected)

# ---- END:Test numbers ---

# ==== END: Test some functions that take basic builtins ====

# def test_typeshed_base64():
#     """From the typeshed: https://github.com/python/typeshed/blob/master/stdlib/2and3/base64.pyi
#
#     def b64decode(s: _decodable, altchars: bytes = ...,
#                   validate: bool = ...) -> bytes: ...
#     def b64encode(s: _encodable, altchars: bytes = ...) -> bytes: ...
#
#     def decode(input: IO[bytes], output: IO[bytes]) -> None: ...
#     def decodebytes(s: bytes) -> bytes: ...
#     def decodestring(s: bytes) -> bytes: ...
#     def encode(input: IO[bytes], output: IO[bytes]) -> None: ...
#     def encodebytes(s: bytes) -> bytes: ...
#     def encodestring(s: bytes) -> bytes: ...
#     """
#     with type_inferencer.TypeInferencer() as ti:
#         base64.b64encode(b'')
#         base64.b64decode(b'')
# #         stream_in = io.StringIO()
# #         stream_out = io.StringIO()
# #         base64.encode(stream_in, stream_out)
# #         base64.decode(stream_in, stream_out)
# #         base64.encodebytes(b'')
# #         base64.decodebytes(b'')
# #         base64.decode(stream_in, stream_out)
# #         encoded = base64.encodestring(b'')
# #         decoded = base64.encodestring(encoded)
#     print()
#     print('test_typeshed_base64()')
#     _pretty_print(ti)
#     # def _input_type_check(s: 'bytes') -> NoneType: ...
#     # def decode(input: '_io.StringIO', output: '_io.StringIO') -> NoneType: ...
#     # def decodebytes(s: 'bytes') -> bytes: ...
#     # def encode(input: '_io.StringIO', output: '_io.StringIO') -> NoneType: ...
#     # def encodebytes(s: 'bytes') -> bytes: ...
#     # def encodestring(s: 'bytes') -> bytes: ...
#
# #     pprint.pprint(ti.function_map)

def test_typeshed_io_StringIO():
    """Based on base64 from the typeshed:
    https://github.com/python/typeshed/blob/master/stdlib/2and3/base64.pyi

    Should see stub file of:
    def decode(input: IO[bytes], output: IO[bytes]) -> None: ...
    def encode(input: IO[bytes], output: IO[bytes]) -> None: ...
    """
    def decode(input, output):
        pass
    def encode(input, output):
        pass
    with type_inferencer.TypeInferencer() as ti:
        stream_in = io.StringIO()
        stream_out = io.StringIO()
        encode(stream_in, stream_out)
        decode(stream_in, stream_out)
    expected = [
        'def decode(input: IO[bytes], output: IO[bytes]) -> None: ...',
        'def encode(input: IO[bytes], output: IO[bytes]) -> None: ...',
    ]
    assert ti.pretty_format(__file__) == '\n'.join(expected)

def test_typeshed_encode_bytes():
    """Based on base64 from the typeshed:
    https://github.com/python/typeshed/blob/master/stdlib/2and3/base64.pyi

    Should see stub file of:
    def decodebytes(s: 'bytes') -> bytes: ...
    def encodebytes(s: 'bytes') -> bytes: ...
    """
    def decodebytes(s):
        return s
    def encodebytes(s):
        return s
    with type_inferencer.TypeInferencer() as ti:
        encodebytes(b'')
        decodebytes(b'')
    expected = [
        'def decodebytes(s: bytes) -> bytes: ...',
        'def encodebytes(s: bytes) -> bytes: ...',
    ]
    assert ti.pretty_format(__file__) == '\n'.join(expected)

def test_simple_class():
    """A simple class with a constructor and a single method."""
    class Simple:
        def __init__(self, first_name, last_name):
            self.first_name = first_name
            self.last_name = last_name
        def name(self):
            return '{:s}, {:s}'.format(self.last_name, self.first_name)

    with type_inferencer.TypeInferencer() as ti:
        s = Simple('First', 'Last')
        s.name()
    expected = [
        'class Simple:',
        '    def __init__(self, first_name: str, last_name: str) -> None: ...',
        '    def name(self) -> str: ...',
    ]
#     pprint.pprint(ti.function_map)
#     print(ti.pretty_format(__file__))
    assert ti.pretty_format(__file__) == '\n'.join(expected)

def test_class_in_class():
    """A class in a class and a single method."""
    class Outer:
        class Inner:
            def __init__(self, first_name, last_name):
                self.first_name = first_name
                self.last_name = last_name
            def name(self):
                return '{:s}, {:s}'.format(self.last_name, self.first_name)

    with type_inferencer.TypeInferencer() as ti:
        s = Outer.Inner('First', 'Last')
        s.name()
    expected = [
        'class Outer:',
        '    class Inner:',
        '        def __init__(self, first_name: str, last_name: str) -> None: ...',
        '        def name(self) -> str: ...',
    ]
#     pprint.pprint(ti.function_map)
#     print()
#     print(ti.pretty_format(__file__))
    assert ti.pretty_format(__file__) == '\n'.join(expected)

def test_class_in_class_both_have_methods():
    """A simple class with a constructor and a single method."""
    class Outer:
        def z_function(self, s):
            return s
        class Inner:
            def __init__(self, first_name, last_name):
                self.first_name = first_name
                self.last_name = last_name
            def name(self):
                return '{:s}, {:s}'.format(self.last_name, self.first_name)

    with type_inferencer.TypeInferencer() as ti:
        o = Outer()
        o.z_function(b'')
        s = Outer.Inner('First', 'Last')
        s.name()
    expected = [
        'class Outer:',
        '    def z_function(self, s: bytes) -> bytes: ...',
        '    class Inner:',
        '        def __init__(self, first_name: str, last_name: str) -> None: ...',
        '        def name(self) -> str: ...',
    ]
#     pprint.pprint(ti.function_map)
#     print()
#     print(ti.pretty_format(__file__))
#     print('\n'.join(expected))
    assert ti.pretty_format(__file__) == '\n'.join(expected)

def test_three_nested_classes_only_inner_has_methods():
    """Three nested classes and a single method."""
    class A:
        class B:
            class C:
                def __init__(self, first_name, last_name):
                    self.first_name = first_name
                    self.last_name = last_name
                def name(self):
                    return '{:s}, {:s}'.format(self.last_name, self.first_name)

    with type_inferencer.TypeInferencer() as ti:
        s = A.B.C('First', 'Last')
        s.name()
    expected = [
        'class A:',
        '    class B:',
        '        class C:',
        '            def __init__(self, first_name: str, last_name: str) -> None: ...',
        '            def name(self) -> str: ...',
    ]
#     pprint.pprint(ti.function_map)
#     print()
#     print(ti.pretty_format(__file__))
    assert ti.pretty_format(__file__) == '\n'.join(expected)

def test_three_nested_classes_only_inner_has_methods_rev_names():
    """Three nested classes and a single method, names reversed."""
    class C:
        class B:
            class A:
                def __init__(self, first_name, last_name):
                    self.first_name = first_name
                    self.last_name = last_name
                def name(self):
                    return '{:s}, {:s}'.format(self.last_name, self.first_name)

    with type_inferencer.TypeInferencer() as ti:
        s = C.B.A('First', 'Last')
        s.name()
    expected = [
        'class C:',
        '    class B:',
        '        class A:',
        '            def __init__(self, first_name: str, last_name: str) -> None: ...',
        '            def name(self) -> str: ...',
    ]
#     pprint.pprint(ti.function_map)
#     print()
#     print(ti.pretty_format(__file__))
    assert ti.pretty_format(__file__) == '\n'.join(expected)

def test_three_nested_classes_middle_and_inner_has_methods():
    """Three nested classes and a single method."""
    class A:
        class B:
            class C:
                def __init__(self, first_name, last_name):
                    self.first_name = first_name
                    self.last_name = last_name
                def name(self):
                    return '{:s}, {:s}'.format(self.last_name, self.first_name)
            def some_function(self, byt): return byt

    with type_inferencer.TypeInferencer() as ti:
        c = A.B.C('First', 'Last')
        c.name()
        b = A.B()
        b.some_function(b'')
    expected = [
        'class A:',
        '    class B:',
        '        def some_function(self, byt: bytes) -> bytes: ...',
        '        class C:',
        '            def __init__(self, first_name: str, last_name: str) -> None: ...',
        '            def name(self) -> str: ...',
    ]
#     pprint.pprint(ti.function_map)
#     print()
#     print(ti.pretty_format(__file__))
    assert ti.pretty_format(__file__) == '\n'.join(expected)

def test_four_nested_classes_A_and_inner_has_methods():
    class A:
        def some_function(self, byt): return byt
        class B:
            class C:
                class D:
                    def __init__(self, first_name, last_name):
                        self.first_name = first_name
                        self.last_name = last_name
                    def name(self):
                        return '{:s}, {:s}'.format(self.last_name, self.first_name)

    with type_inferencer.TypeInferencer() as ti:
        d = A.B.C.D('First', 'Last')
        d.name()
        a = A()
        a.some_function(b'')
    expected = [
        'class A:',
        '    def some_function(self, byt: bytes) -> bytes: ...',
        '    class B:',
        '        class C:',
        '            class D:',
        '                def __init__(self, first_name: str, last_name: str) -> None: ...',
        '                def name(self) -> str: ...',
    ]
#     pprint.pprint(ti.function_map)
#     print()
#     print(ti.pretty_format(__file__))
    assert ti.pretty_format(__file__) == '\n'.join(expected)

def test_four_nested_classes_B_and_inner_has_methods():
    class A:
        class B:
            def some_function(self, byt): return byt
            class C:
                class D:
                    def __init__(self, first_name, last_name):
                        self.first_name = first_name
                        self.last_name = last_name
                    def name(self):
                        return '{:s}, {:s}'.format(self.last_name, self.first_name)

    with type_inferencer.TypeInferencer() as ti:
        d = A.B.C.D('First', 'Last')
        d.name()
        b = A.B()
        b.some_function(b'')
    expected = [
        'class A:',
        '    class B:',
        '        def some_function(self, byt: bytes) -> bytes: ...',
        '        class C:',
        '            class D:',
        '                def __init__(self, first_name: str, last_name: str) -> None: ...',
        '                def name(self) -> str: ...',
    ]
#     print()
#     pprint.pprint(ti.function_map[__file__])
#     print(ti.pretty_format(__file__))
    assert ti.pretty_format(__file__) == '\n'.join(expected)

def test_four_nested_classes_C_and_inner_has_methods():
    class A:
        class B:
            class C:
                def some_function(self, byt): return byt
                class D:
                    def __init__(self, first_name, last_name):
                        self.first_name = first_name
                        self.last_name = last_name
                    def name(self):
                        return '{:s}, {:s}'.format(self.last_name, self.first_name)

    with type_inferencer.TypeInferencer() as ti:
        d = A.B.C.D('First', 'Last')
        d.name()
        c = A.B.C()
        c.some_function(b'')
    expected = [
        'class A:',
        '    class B:',
        '        class C:',
        '            def some_function(self, byt: bytes) -> bytes: ...',
        '            class D:',
        '                def __init__(self, first_name: str, last_name: str) -> None: ...',
        '                def name(self) -> str: ...',
    ]
#     print()
#     pprint.pprint(ti.function_map[__file__])
#     print(ti.pretty_format(__file__))
    assert ti.pretty_format(__file__) == '\n'.join(expected)

def test_four_nested_classes_all_have_methods():
    class A:
        def some_function(self, byt): return byt
        class B:
            def some_function(self, byt): return byt
            class C:
                def some_function(self, byt): return byt
                class D:
                    def __init__(self, first_name, last_name):
                        self.first_name = first_name
                        self.last_name = last_name
                    def name(self):
                        return '{:s}, {:s}'.format(self.last_name, self.first_name)

    with type_inferencer.TypeInferencer() as ti:
        d = A.B.C.D('First', 'Last')
        d.name()
        c = A.B.C()
        c.some_function(b'')
        b = A.B()
        b.some_function(b'')
        a = A()
        a.some_function(b'')
    expected = [
        'class A:',
        '    def some_function(self, byt: bytes) -> bytes: ...',
        '    class B:',
        '        def some_function(self, byt: bytes) -> bytes: ...',
        '        class C:',
        '            def some_function(self, byt: bytes) -> bytes: ...',
        '            class D:',
        '                def __init__(self, first_name: str, last_name: str) -> None: ...',
        '                def name(self) -> str: ...',
    ]
#     print()
#     pprint.pprint(ti.function_map[__file__])
#     print(ti.pretty_format(__file__))
    assert ti.pretty_format(__file__) == '\n'.join(expected)

def test_class_inheritance():
    """From the calendar module stubs file:
class IllegalMonthError(ValueError):
    def __init__(self, month: int) -> None: ...
    def __str__(self) -> str: ...
    """
    class IllegalMonthError(ValueError):
        def __init__(self, month): pass
        def __str__(self):
            return ''

    with type_inferencer.TypeInferencer() as ti:
        obj = IllegalMonthError(4)
        str(obj)
    expected = [
        'class IllegalMonthError(ValueError):',
        '    def __init__(self, month: int) -> None: ...',
        '    def __str__(self) -> str: ...',
    ]
#     print()
#     print(ti.pretty_format(__file__))
    assert ti.pretty_format(__file__) == '\n'.join(expected)

def test_class_multiple_inheritance_unsorted():
    """Tests that the base names do not get sorted."""
    class X: pass
    class Y: pass
    class Z: pass
    class A(Z, X, Y):
#         def __init__(self, month):
#             super().__init__()
        def __str__(self):
            return ''

    with type_inferencer.TypeInferencer() as ti:
        obj = A()
        str(obj)
    expected = [
        'class A(Z, X, Y):',
        '    def __init__(self, month: int) -> None: ...',
        '    def __str__(self) -> str: ...',
    ]
    print()
    print(ti.pretty_format(__file__))
    assert ti.pretty_format(__file__) == '\n'.join(expected)

# Used for line number and ranges
line_first = inspect.currentframe().f_lineno + 1
def function_lineno(v):
    if v == 0:
        return inspect.currentframe().f_lineno
    elif v == 1:
        raise ValueError()
    elif v == 2:
        return inspect.currentframe().f_lineno
    return inspect.currentframe().f_lineno
line_last = inspect.currentframe().f_lineno - 1

@pytest.mark.parametrize('value, expected_increment', [
    (0, 2), # Partial, return
    (1, 4), # Partial, raises
    (2, 6), # Partial, return
    (3, 7), # Full, return
])
def test_single_function_line_range(value, expected_increment):
    with type_inferencer.TypeInferencer() as ti:
        try:
            function_lineno(value)
        except ValueError:
            pass
    fts = ti.function_types(__file__, '', 'function_lineno')
    assert fts.line_range == (line_first, line_first + expected_increment)
    assert fts.call_line_numbers == [line_first,]

# Generators and line numbers.
# Used for line number and ranges
line_first_gen = inspect.currentframe().f_lineno + 1
def function_gen_lineno():
    for _i in range(3):
        yield inspect.currentframe().f_lineno
    for _i in range(3):
        yield inspect.currentframe().f_lineno
line_last_gen = inspect.currentframe().f_lineno - 1

def test_generator_line_number_range():
    """Tests the line numbers of """
    lines_yielded = []
    with type_inferencer.TypeInferencer() as ti:
        for line_no in function_gen_lineno():
            lines_yielded.append(line_no - line_first_gen)
    assert lines_yielded == [2, 2, 2, 4, 4, 4,]
    fts = ti.function_types(__file__, '', 'function_gen_lineno')
    assert fts.line_range == (line_first_gen, line_last_gen)
    assert fts.call_line_numbers == [
                                     line_first_gen,
                                     line_first_gen + 2,
                                     line_first_gen + 4,
                                     ]

def test_file_filtering():
    """This exercises code in the stdlib, 3rd party libraries and local
    functions and extracts just the local data."""
    def function(v):
        """Local function."""
        pass
    with type_inferencer.TypeInferencer() as ti:
        function('string') # Local function
        # Stdlib
        base64.b64encode(b'')
        base64.b64decode(b'')
        stream_in = io.StringIO()
        stream_out = io.StringIO()
        base64.encode(stream_in, stream_out)
        base64.decode(stream_in, stream_out)
        base64.encodebytes(b'')
        base64.decodebytes(b'')
        base64.decode(stream_in, stream_out)
        encoded = base64.encodestring(b'')
        _decoded = base64.encodestring(encoded)
        # 3rd Party
        with pytest.raises(ValueError):
            raise ValueError
#     print()
#     pprint.pprint(ti.function_map)
#     print(os.getcwd())
#     pprint.pprint(sorted(ti.function_map.keys()))
#     for file_path in sorted(ti.function_map.keys()):
#         print(file_path)
#         pprint.pprint(ti.function_map[file_path])
#     print(ti.pretty_format(__file__))
    expected = [
        'def function(v: str) -> None: ...',
    ]
    assert ti.pretty_format(__file__) == '\n'.join(expected)
    assert ti.file_paths_filtered(
        file_path_prefix=os.path.dirname(__file__),
        relative=True) == [(__file__, os.path.basename(__file__))]
#     assert ti.file_paths_cwd(relative=True) == [(__file__, 'tests/unit/test_type_inferencer.py')]

def test_class_semie_private_methods():
    class A:
        pass
    class B(A):
        def public(self, value):
            return self._semie_private(value)

        def _semie_private(self, value):
            return '{!r:s}'.format(value)

    with type_inferencer.TypeInferencer() as ti:
        b = B()
        b.public(14)

    expected = [
        'class B(A):',
        '    def _semie_private(self, value: int) -> str: ...',
        '    def public(self, value: int) -> str: ...',
    ]
#     print()
#     pprint.pprint(ti.function_map)
#     print(ti.pretty_format(__file__))
    assert ti.pretty_format(__file__) == '\n'.join(expected)

def test_class_private_methods():
    class A:
        pass
    class B(A):
        def public(self, value):
            return self._semie_private(value)

        def _semie_private(self, value):
            return self.__private(value)

        def __private(self, value):
            return '{!r:s}'.format(value)

    with type_inferencer.TypeInferencer() as ti:
        b = B()
        b.public(14)

    expected = [
        'class B(A):',
        '    def __private(self, value: int) -> str: ...',
        '    def _semie_private(self, value: int) -> str: ...',
        '    def public(self, value: int) -> str: ...',
    ]
#     print()
#     pprint.pprint(ti.function_map)
#     print(ti.pretty_format(__file__))
    assert ti.pretty_format(__file__) == '\n'.join(expected)

def test_class_private_methods_trailing_underscore():
    class A:
        pass
    class B(A):
        def public(self, value):
            return self._semie_private(value)

        def _semie_private(self, value):
            return self.__private_(value)

        def __private_(self, value):
            # One trailing underscore allowed.
            return '{!r:s}'.format(value)

    with type_inferencer.TypeInferencer() as ti:
        b = B()
        b.public(14)

    expected = [
        'class B(A):',
        '    def __private_(self, value: int) -> str: ...',
        '    def _semie_private(self, value: int) -> str: ...',
        '    def public(self, value: int) -> str: ...',
    ]
#     print()
#     pprint.pprint(ti.function_map)
#     print(ti.pretty_format(__file__))
    assert ti.pretty_format(__file__) == '\n'.join(expected)

def test_class_private_methods_nested_class():
    class A:
        pass
    class B(A):
        class C:
            def public(self, value):
                return self._semie_private(value)

            def _semie_private(self, value):
                return self.__private(value)

            def __private(self, value):
                return '{!r:s}'.format(value)

    with type_inferencer.TypeInferencer() as ti:
        b = B.C()
        b.public(14)

    expected = [
        # NOTE: No inheritance of A by B
        'class B:',
        '    class C:',
        '        def __private(self, value: int) -> str: ...',
        '        def _semie_private(self, value: int) -> str: ...',
        '        def public(self, value: int) -> str: ...',
    ]
#     print()
#     pprint.pprint(ti.function_map)
#     print(ti.pretty_format(__file__))
    assert ti.pretty_format(__file__) == '\n'.join(expected)

def test_class_private_methods_nested_class_inherits():
    class A:
        def __init__(self):
            pass
    class B(A):
        def __init__(self):
            super().__init__()
        class C:
            def public(self, value):
                return self._semie_private(value)

            def _semie_private(self, value):
                return self.__private(value)

            def __private(self, value):
                return '{!r:s}'.format(value)

    with type_inferencer.TypeInferencer() as ti:
        b = B()
        c = b.C()
        c.public(14)

    expected = [
        # NOTE: Inheritance of A by B
        'class A:',
        '    def __init__(self) -> None: ...',
        'class B(A):',
        '    def __init__(self) -> None: ...',
        '    class C:',
        '        def __private(self, value: int) -> str: ...',
        '        def _semie_private(self, value: int) -> str: ...',
        '        def public(self, value: int) -> str: ...',
    ]
#     print()
#     pprint.pprint(ti.function_map)
#     print(ti.pretty_format(__file__))
    assert ti.pretty_format(__file__) == '\n'.join(expected)

def test_class_properties():
    class A:
        @property
        def get(self):
            return id(self)

    with type_inferencer.TypeInferencer() as ti:
        b = A()
        b.get

    expected = [
        'class A:',
        '    def get(self) -> int: ...',
    ]
#     print()
#     pprint.pprint(ti.function_map)
#     print(ti.pretty_format(__file__))
    assert ti.pretty_format(__file__) == '\n'.join(expected)

def test_class_properties():
    class A:
        @property
        def get(self):
            return id(self)

    with type_inferencer.TypeInferencer() as ti:
        b = A()
        b.get

    expected = [
        'class A:',
        '    def get(self) -> int: ...',
    ]
#     print()
#     pprint.pprint(ti.function_map)
#     print(ti.pretty_format(__file__))
    assert ti.pretty_format(__file__) == '\n'.join(expected)

def test_class_properties_get_set():
    class A:
        def __init__(self, value):
            self._value = value

        @property
        def value(self):
            return self._value

        @value.setter
        def value(self, value):
            self._value = value

    with type_inferencer.TypeInferencer() as ti:
        b = A(21)
        assert b.value == 21
        b.value = 42
        assert b.value == 42

    expected = [
        'class A:',
        '    def __init__(self, value: int) -> None: ...',
        '    def value(self, value: int) -> Union[None, int]: ...',
    ]
#     print()
#     pprint.pprint(ti.function_map)
#     print(ti.pretty_format(__file__))
    assert ti.pretty_format(__file__) == '\n'.join(expected)

def test_class_properties_get_set_calls_reversed():
    class A:
        def __init__(self, value):
            self._value = value

        @property
        def value(self):
            return self._value

        @value.setter
        def value(self, value):
            self._value = value

    with type_inferencer.TypeInferencer() as ti:
        b = A(21)
        b.value = 42
        assert b.value == 42

    expected = [
        'class A:',
        '    def __init__(self, value: int) -> None: ...',
        '    def value(self, value: int) -> Union[None, int]: ...',
    ]
#     print()
#     pprint.pprint(ti.function_map)
#     print(ti.pretty_format(__file__))
    assert ti.pretty_format(__file__) == '\n'.join(expected)

def test_named_tuple():
    """Named tuples are weird."""
    MyNT = collections.namedtuple('MyNT', 'a b c')
    with type_inferencer.TypeInferencer() as ti:
        nt = MyNT(1, 'B', b'C')
        nt.a
        nt.b
        nt.c
        nt.count(1)
        print()
        print(dir(MyNT))
        print(MyNT.__module__)
        print(dir(MyNT.__new__))
        print(locals())
        print(nt._fields)

    expected = [
        'class A:',
        '    def get(self) -> int: ...',
    ]
    print()
#     pprint.pprint(ti.function_map)
    for filename in ti.function_map.keys():
        print(filename)
        print(ti.pretty_format(filename))
    assert ti.pretty_format(filename) == '\n'.join(expected)

def _test_named_tuple_subclass():
    """Named tuples are a bit awkward as they are equivelent to mere tuples."""
    class Dim(collections.namedtuple('Dim', 'value units',)):
        """Represents a dimension as an engineering value i.e. a number and units."""
        __slots__ = ()

        def scale(self, factor):
            """Returns a new Dim() scaled by a factor, units are unchanged."""
            return self._replace(value=self.value*factor)

    with type_inferencer.TypeInferencer() as ti:
        d = Dim(12, 'kilometers')
        d.scale(10) # 120 kilometers
        print()
#         print(type(d))
#         print(d._fields)
        e = type(d)(*d)
        print(e)
        print(e._fields)
        print(e.value)
        print(e.units)
        e.scale(.1)

    expected = [
        'class Dim(tests.unit.test_type_inferencer.Dim):',
        '    def scale(self, factor: int) -> tuple([int, str]): ...',
    ]
#     print()
#     pprint.pprint(ti.function_map)
#     print(ti.pretty_format(__file__))
    assert ti.pretty_format(__file__) == '\n'.join(expected)

def test_list_comprehension_ignored():
    with type_inferencer.TypeInferencer() as ti:
        [i for i in range(8)]
#     print()
#     pprint.pprint(ti.function_map)
    assert __file__ not in ti.function_map

def test_dict_comprehension_ignored():
    with type_inferencer.TypeInferencer() as ti:
        {i : i for i in range(8)}
#     print()
#     pprint.pprint(ti.function_map)
    assert __file__ not in ti.function_map

def test_set_comprehension_ignored():
    with type_inferencer.TypeInferencer() as ti:
        {i for i in range(8)}
    print()
    pprint.pprint(ti.function_map)
    assert __file__ not in ti.function_map

def test_generator():
    # Generator events should not be recorded as exceptions
    line_raises = inspect.currentframe().f_lineno + 2
    def gen():
        for i in range(3):
            yield i

    with type_inferencer.TypeInferencer() as ti:
        result = []
        for i in gen():
            result.append(i)
        assert result == [0, 1, 2]
    print()
    pprint.pprint(ti.function_map)
    expected = [
        'def gen() -> Union[None, int]: ...',
    ]
    assert ti.pretty_format(__file__) == '\n'.join(expected)
    fts = ti.function_types(__file__, '', 'gen')
    assert fts.exception_type_strings == {}

def test_generator_in_generator():
    # Generator events should not be recorded as exceptions
    line_raises = inspect.currentframe().f_lineno + 2
    def gen_outer():
        for i in gen_inner(3):
            yield i

    def gen_inner(num):
        for i in range(num):
            yield i

    with type_inferencer.TypeInferencer() as ti:
        result = []
        for i in gen_outer():
            result.append(i)
        assert result == [0, 1, 2]
#     print()
#     pprint.pprint(ti.function_map)
#     print(ti.pretty_format(__file__))
    expected = [
        'def gen_inner(num: int) -> Union[None, int]: ...',
        'def gen_outer() -> Union[None, int]: ...',
    ]
    assert ti.pretty_format(__file__) == '\n'.join(expected)
    fts = ti.function_types(__file__, '', 'gen_inner')
    assert fts.exception_type_strings == {}
    fts = ti.function_types(__file__, '', 'gen_outer')
    assert fts.exception_type_strings == {}

def test_generator_in_generator_that_raises():
    # Generator events should not be recorded as exceptions
    def gen_outer():
        try:
            for i in gen_inner(3):
                yield i
        except RuntimeError:
            pass

    line_raises = inspect.currentframe().f_lineno + 4
    def gen_inner(num):
        for i in range(num):
            if i % 2 == 1:
                raise RuntimeError()
            yield i

    with type_inferencer.TypeInferencer() as ti:
        result = []
        for i in gen_outer():
            result.append(i)
        assert result == [0,]
#     print()
#     pprint.pprint(ti.function_map)
#     print(ti.pretty_format(__file__))
    expected = [
        'def gen_inner(num: int) -> int: ...',
        'def gen_outer() -> Union[None, int]: ...',
    ]
    assert ti.pretty_format(__file__) == '\n'.join(expected)
    fts = ti.function_types(__file__, '', 'gen_inner')
    assert fts.exception_type_strings == {line_raises: {'RuntimeError'}}
    fts = ti.function_types(__file__, '', 'gen_outer')
    assert fts.exception_type_strings == {}

def test_insert_docstrings_simple_function():
    start_lineno = inspect.currentframe().f_lineno + 1
    def func_single_arg_return_arg(arg):
        return arg

    with type_inferencer.TypeInferencer() as ti:
        func_single_arg_return_arg('string')

    src_lines = ['\n'] * (start_lineno - 1)
    src_lines += [
        'def func_single_arg_return_arg(arg):\n',
        '    return arg\n',
    ]
    exp_lines = ['\n'] * (start_lineno - 1)
    exp_lines += [
        'def func_single_arg_return_arg(arg):\n',
        '    """\n',
        '    <insert documentation for function>\n',
        '    \n',
        '    :param arg: <insert documentation for argument>\n',
        '    :type arg: ``str``\n',
        '    \n',
        '    :returns: ``str`` -- <insert documentation for return values>\n',
        '    """\n',
        '    return arg\n',
    ]
    new_src_lines = ti.insert_docstrings(__file__, src_lines, style='sphinx')
    # print()
    # print(ti.docstring_map(__file__, style='sphinx'))
    # src_start = list(ti.docstring_map(__file__, style='sphinx').keys())[0]
    # print(src_lines[src_start-1:])
    # print(new_src_lines[src_start-1:])
    assert new_src_lines == exp_lines

def test_insert_docstrings_two_functions():
    start_lineno = inspect.currentframe().f_lineno + 1
    def func_single_arg_return_arg(arg):
        return arg

    def another_func_single_arg_return_arg(arg):
        return arg

    with type_inferencer.TypeInferencer() as ti:
        # NOTE: Reverse calling order
        another_func_single_arg_return_arg(b'bytes')
        func_single_arg_return_arg('string')

    src_lines = ['\n'] * (start_lineno - 1)
    src_lines += [
        'def func_single_arg_return_arg(arg):\n',
        '    return arg\n',
        '\n',
        'def another_func_single_arg_return_arg(arg):\n',
        '    return arg\n',
    ]
    exp_lines = ['\n'] * (start_lineno - 1)
    exp_lines += [
        'def func_single_arg_return_arg(arg):\n',
        '    """\n',
        '    <insert documentation for function>\n',
        '    \n',
        '    :param arg: <insert documentation for argument>\n',
        '    :type arg: ``str``\n',
        '    \n',
        '    :returns: ``str`` -- <insert documentation for return values>\n',
        '    """\n',
        '    return arg\n',
        '\n',
        'def another_func_single_arg_return_arg(arg):\n',
        '    """\n',
        '    <insert documentation for function>\n',
        '    \n',
        '    :param arg: <insert documentation for argument>\n',
        '    :type arg: ``bytes``\n',
        '    \n',
        '    :returns: ``bytes`` -- <insert documentation for return values>\n',
        '    """\n',
        '    return arg\n',
    ]
    new_src_lines = ti.insert_docstrings(__file__, src_lines, style='sphinx')
    # print()
    # print(ti.docstring_map(__file__, style='sphinx'))
    # src_start = list(ti.docstring_map(__file__, style='sphinx').keys())[0]
    # print(src_lines[src_start-1:])
    # print(new_src_lines[src_start-1:])
    assert new_src_lines == exp_lines

def test_insert_docstrings_simple_class():
    start_lineno = inspect.currentframe().f_lineno + 1
    class Simple:
        def __init__(self, first_name, last_name):
            self.first_name = first_name
            self.last_name = last_name

        def name(self):
            return '{:s}, {:s}'.format(self.last_name, self.first_name)

    with type_inferencer.TypeInferencer() as ti:
        s = Simple('First', 'Last')
        s.name()

    src_lines = ['\n'] * (start_lineno - 1)
    src_lines += [
        'class Simple:\n',
        '    def __init__(self, first_name, last_name):\n',
        '        self.first_name = first_name\n',
        '        self.last_name = last_name\n',
        '    \n',
        '    def name(self):\n',
        '        return \'{:s}, {:s}\'.format(self.last_name, self.first_name)\n',
    ]
    exp_lines = ['\n'] * (start_lineno - 1)
    exp_lines += [
        'class Simple:\n',
        '    def __init__(self, first_name, last_name):\n',
        '        """\n',
        '        <insert documentation for function>\n',
        '        \n',
        '        :param first_name: <insert documentation for argument>\n',
        '        :type first_name: ``str``\n',
        '        \n',
        '        :param last_name: <insert documentation for argument>\n',
        '        :type last_name: ``str``\n',
        '        """\n',
        '        self.first_name = first_name\n',
        '        self.last_name = last_name\n',
        '    \n',
        '    def name(self):\n',
        '        """\n',
        '        <insert documentation for function>\n',
        '        \n',
        '        :returns: ``str`` -- <insert documentation for return values>\n',
        '        """\n',
        "        return '{:s}, {:s}'.format(self.last_name, self.first_name)\n"
    ]
    new_src_lines = ti.insert_docstrings(__file__, src_lines, style='sphinx')
    # print()
    # print(ti.docstring_map(__file__, style='sphinx'))
    # src_start = list(ti.docstring_map(__file__, style='sphinx').keys())[0]
    # print(src_lines[src_start-1:])
    # pprint.pprint(new_src_lines[src_start-2:])
    assert new_src_lines == exp_lines

def test_insert_docstrings_simple_class_with_property():
    start_lineno = inspect.currentframe().f_lineno + 1
    class Simple:
        def __init__(self, first_name, last_name):
            self.first_name = first_name
            self.last_name = last_name

        def name(self):
            return '{:s}, {:s}'.format(self.last_name, self.first_name)

    with type_inferencer.TypeInferencer() as ti:
        s = Simple('First', 'Last')
        s.name()

    src_lines = ['\n'] * (start_lineno - 1)
    src_lines += [
        'class Simple:\n',
        '    def __init__(self, first_name, last_name):\n',
        '        self.first_name = first_name\n',
        '        self.last_name = last_name\n',
        '    \n',
        '    @property\n',
        '    def name(self):\n',
        '        return \'{:s}, {:s}\'.format(self.last_name, self.first_name)\n',
    ]
    exp_lines = ['\n'] * (start_lineno - 1)
    exp_lines += [
        'class Simple:\n',
        '    def __init__(self, first_name, last_name):\n',
        '        """\n',
        '        <insert documentation for function>\n',
        '        \n',
        '        :param first_name: <insert documentation for argument>\n',
        '        :type first_name: ``str``\n',
        '        \n',
        '        :param last_name: <insert documentation for argument>\n',
        '        :type last_name: ``str``\n',
        '        """\n',
        '        self.first_name = first_name\n',
        '        self.last_name = last_name\n',
        '    \n',
        '    @property\n',
        '    def name(self):\n',
        '        """\n',
        '        <insert documentation for function>\n',
        '        \n',
        '        :returns: ``str`` -- <insert documentation for return values>\n',
        '        """\n',
        "        return '{:s}, {:s}'.format(self.last_name, self.first_name)\n"
    ]
    new_src_lines = ti.insert_docstrings(__file__, src_lines, style='sphinx')
    # print()
    # print(ti.docstring_map(__file__, style='sphinx'))
    # src_start = list(ti.docstring_map(__file__, style='sphinx').keys())[0]
    # print(src_lines[src_start-1:])
    # pprint.pprint(new_src_lines[src_start-2:])
    assert new_src_lines == exp_lines

def test_insert_docstrings_simple_class_multiline_arguments():
    start_lineno = inspect.currentframe().f_lineno + 1
    class Simple:
        def __init__(self,
                     first_name,
                     last_name):
            self.first_name = first_name
            self.last_name = last_name

        def name(self):
            return '{:s}, {:s}'.format(self.last_name, self.first_name)

    with type_inferencer.TypeInferencer() as ti:
        s = Simple('First', 'Last')
        s.name()

    src_lines = ['\n'] * (start_lineno - 1)
    src_lines += [
        'class Simple:\n',
        '    def __init__(self,\n',
        '                 first_name,\n',
        '                 last_name):',
        '        self.first_name = first_name\n',
        '        self.last_name = last_name\n',
        '    \n',
        '    def name(self):\n',
        '        return \'{:s}, {:s}\'.format(self.last_name, self.first_name)\n',
    ]
    exp_lines = ['\n'] * (start_lineno - 1)
    exp_lines += [
        'class Simple:\n',
        '    def __init__(self,\n',
        '                 first_name,\n',
        '                 last_name):',
        '        """\n',
        '        <insert documentation for function>\n',
        '        \n',
        '        :param first_name: <insert documentation for argument>\n',
        '        :type first_name: ``str``\n',
        '        \n',
        '        :param last_name: <insert documentation for argument>\n',
        '        :type last_name: ``str``\n',
        '        """\n',
        '        self.first_name = first_name\n',
        '        self.last_name = last_name\n',
        '    \n',
        '    def name(self):\n',
        '        """\n',
        '        <insert documentation for function>\n',
        '        \n',
        '        :returns: ``str`` -- <insert documentation for return values>\n',
        '        """\n',
        "        return '{:s}, {:s}'.format(self.last_name, self.first_name)\n"
    ]
    new_src_lines = ti.insert_docstrings(__file__, src_lines, style='sphinx')
    # print()
    # print(ti.docstring_map(__file__, style='sphinx'))
    # src_start = list(ti.docstring_map(__file__, style='sphinx').keys())[0]
    # print(src_lines[src_start-1:])
    # pprint.pprint(new_src_lines[src_start-2:])
    assert new_src_lines == exp_lines


def test_event_count_on_a_couple_of_functions():
    def func_single_arg_no_return(arg):
        pass

    def func_single_arg_return_arg(arg):
        return arg
    with type_inferencer.TypeInferencer() as ti:
        func_single_arg_no_return('string')
        func_single_arg_return_arg('string')
    assert ti.eventno == 8

def test_event_counter_on_a_couple_of_functions():
    def func_single_arg_no_return(arg):
        pass

    def func_single_arg_return_arg(arg):
        return arg
    with type_inferencer.TypeInferencer() as ti:
        func_single_arg_no_return('string')
        func_single_arg_return_arg('string')
    # print()
    # print(ti.event_counter)
    # Counter({'call': 3, 'line': 3, 'return': 2})
    assert sorted(ti.event_counter.keys()) == ['call', 'line', 'return']
    assert ti.event_counter['call'] == 3
    assert ti.event_counter['line'] == 3
    assert ti.event_counter['return'] == 2


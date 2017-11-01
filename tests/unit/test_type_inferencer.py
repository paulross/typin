'''
Created on 22 Jun 2017

@author: paulross
'''
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


def func_single_arg_no_return(arg):
    pass

def func_single_arg_return_arg(arg):
    return arg

def _pretty_print(ti):
    print(ti.pretty_format())

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

def test_single_function():
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

def func_that_raises():
    raise ValueError('Error message')

def test_single_function_that_raises():
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
        def __init__(self, month): pass
        def __str__(self):
            return ''
        
    with type_inferencer.TypeInferencer() as ti:
        obj = A(4)
        str(obj)
    expected = [
        'class A(Z, X, Y):',
        '    def __init__(self, month: int) -> None: ...',
        '    def __str__(self) -> str: ...',
    ]
#     print()
#     print(ti.pretty_format(__file__))
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
        relative=True) == [os.path.basename(__file__)]
    assert ti.file_paths_cwd(relative=True) == ['tests/unit/test_type_inferencer.py']



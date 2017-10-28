'''
Created on 22 Jun 2017

@author: paulross
'''
import io
import base64
import pprint
import sys

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
    # {file_path : { function_name : FunctionTypes, ...}
    # Example of stub file:
    # def encodebytes(s: bytes) -> bytes: ...
    for file_path in sorted(ti.function_map):
        print('File: {:s}'.format(file_path))
        for function_name in sorted(ti.function_map[file_path]):
            print('def {:s}{:s}'.format(
                function_name,
                ti.function_map[file_path][function_name].stub_file_str()
                )
            )

def test_single_function():
    with type_inferencer.TypeInferencer() as ti:
        func_single_arg_no_return('string')
        func_single_arg_return_arg('string')
    print()
    print('test_single_function()')
    _pretty_print(ti)
#     pprint.pprint(ti.self.function_map)

def func_that_raises():
    raise ValueError('Error message')

def test_single_function_that_raises():
    with type_inferencer.TypeInferencer() as ti:
        try:
            func_that_raises()
        except ValueError:
            pass
    print()
    print('test_single_function_that_raises()')
    _pretty_print(ti)
#     pprint.pprint(ti.self.function_map)

def test_typeshed_base64():
    """From the typeshed: https://github.com/python/typeshed/blob/master/stdlib/2and3/base64.pyi
    
    def decode(input: IO[bytes], output: IO[bytes]) -> None: ...
    def decodebytes(s: bytes) -> bytes: ...
    def decodestring(s: bytes) -> bytes: ...
    def encode(input: IO[bytes], output: IO[bytes]) -> None: ...
    def encodebytes(s: bytes) -> bytes: ...
    def encodestring(s: bytes) -> bytes: ...
    """
    with type_inferencer.TypeInferencer() as ti:
        stream_in = io.StringIO()
        stream_out = io.StringIO()
        base64.encode(stream_in, stream_out)
        base64.decode(stream_in, stream_out)
        base64.encodebytes(b'')
        base64.decodebytes(b'')
        base64.decode(stream_in, stream_out)
        encoded = base64.encodestring(b'')
        decoded = base64.encodestring(encoded)
    print()
    print('test_typeshed_base64()')
    _pretty_print(ti)
    # def _input_type_check(s: 'bytes') -> NoneType: ...
    # def decode(input: '_io.StringIO', output: '_io.StringIO') -> NoneType: ...
    # def decodebytes(s: 'bytes') -> bytes: ...
    # def encode(input: '_io.StringIO', output: '_io.StringIO') -> NoneType: ...
    # def encodebytes(s: 'bytes') -> bytes: ...
    # def encodestring(s: 'bytes') -> bytes: ...

#     pprint.pprint(ti.function_map)

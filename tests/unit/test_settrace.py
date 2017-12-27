"""Test the behaviour of sys.setrace() to understand the sequence and type of
events produced by various function and generator calls.

Created on 6 Dec 2017

@author: paulross
"""
import inspect
import collections
import pprint
import sys

import pytest

# RecordTraceEvents accumulates a list of these
TraceRecord = collections.namedtuple(
    'TraceRecord', 'filename, function, lineno, lineno_code, event, arg'
)
TraceRecord.__doc__ += ': Data from an event seen by sys.setprofile() or sys.settrace()'
TraceRecord.filename.__doc__ = 'Absolute file path as a string.' 
TraceRecord.lineno.__doc__ = 'Line number of the event as an int.'
TraceRecord.lineno_code.__doc__ = 'Line number of the start of the function' \
    ' or generator where the event is as an int. This is constant per function' \
    ' regardless of where the return or yield statements is.'
TraceRecord.event.__doc__ = "Event type: ('call', 'line', 'return', 'exception', 'c_call', 'c_return', or 'c_exception')."
TraceRecord.arg.__doc__ = "Argument: 'call': always None, 'line': always None," \
    " 'return' return value. 'exception': (exception, value, traceback)" \
    "'c_call', 'c_return', 'c_exception': the C function object."


class RecordTraceEvents:
    """
    Class to record events generated by sys.settrace().
    """
    def __init__(self, events_to_trace=None, ignore_self_exit=True):
        self.events_to_trace = events_to_trace
        self.records = []
        self._trace_fn_stack = []
        self._profile_fn_stack = []
        if ignore_self_exit:
            self._call__exit__ = (__file__, self.__exit__lineno, '__exit__')
        else:
            self._call__exit__ = None
        
    def __str__(self):
#         return '\n'.join(
#             ['{:30} {:4d} {:4d} {:10s} {:s}'.format(
#                 r.function, r.lineno, r.lineno_code, r.event, '{!r:s}'.format(r.arg) if r.event != 'call' else '')
#                     for r in self.records
#              ]
#         )
        result = []
        for r in self.records:
            if r.event == 'call':
                # Always None
                arg = ''
            else:
                arg = '{!r:s}'.format(r.arg)
            result.append(
                '{:30} {:4d} {:4d} {:10s} {:s}'.format(
                    r.function, r.lineno, r.lineno_code, r.event, arg
                )
            )
        return '\n'.join(result)
            
    def __call__(self, frame, event, arg):
        if self.events_to_trace is None or event in self.events_to_trace:
            # Traceback(filename, lineno, function, code_context, index)
            frame_info = inspect.getframeinfo(frame)
            tr = TraceRecord(
                frame_info.filename,
                frame_info.function,
                frame_info.lineno,
                frame.f_code.co_firstlineno,
                event,
                arg,
            )
            if self._call__exit__ is None \
            or (tr.filename, tr.lineno, tr.function) != self._call__exit__:
                self.records.append(tr)
        return self

    def __enter__(self):
        """
        Context manager sets the profiling function. This saves the existing
        tracing function.
        """
        self._trace_fn_stack.append(sys.gettrace())
        sys.settrace(self)
#         self._profile_fn_stack.append(sys.getprofile())
#         sys.setprofile(self)
        return self
    
    __exit__lineno = inspect.currentframe().f_lineno + 1 
    def __exit__(self, exc_type, exc_value, traceback):
        """
        Exit the context manager. This restores the tracing function to that
        prior to ``__enter__``.
        """
        sys.settrace(self._trace_fn_stack.pop())
#         sys.setprofile(self._profile_fn_stack.pop())

def test_simple_function():
    def simple_function_double(n):
        return n * 2

    with RecordTraceEvents(('call', 'return')) as rte:
        assert simple_function_double(14) == 28
    print()
#     pprint.pprint(rte.records)
    print(rte)
    print('Code line numbers:', sorted(set([r.lineno_code for r in rte.records])))
    assert len(rte.records) == 2

def test_simple_function_multiple_returns():
    def function_multiple_returns(n):
        if n > 0:
            return 1
        elif n < 0:
            return -1
        return 0

    with RecordTraceEvents(('call', 'return')) as rte:
        assert function_multiple_returns(14) == 1
        assert function_multiple_returns(-14) == -1
        assert function_multiple_returns(0) == 0
    print()
#     pprint.pprint(rte.records)
    print(rte)
    print('Code line numbers:', sorted(set([r.lineno_code for r in rte.records])))
    assert len(rte.records) == 6

def test_function_stack_two():
    def simple_function_child(n):
        return n * 2

    def simple_function_parent(n):
        return simple_function_child(2 * n)

    with RecordTraceEvents(('call', 'return')) as rte:
        assert simple_function_parent(1) == 4
    print()
#     pprint.pprint(rte.records)
    print(rte)
    print('Code line numbers:', sorted(set([r.lineno_code for r in rte.records])))
    assert len(rte.records) == 4

def test_function_stack_two_decl_swap():
    def simple_function_parent(n):
        return simple_function_child(2 * n)

    def simple_function_child(n):
        return n * 2

    with RecordTraceEvents(('call', 'return')) as rte:
        assert simple_function_parent(1) == 4
    print()
#     pprint.pprint(rte.records)
    print(rte)
    print('Code line numbers:', sorted(set([r.lineno_code for r in rte.records])))
    assert len(rte.records) == 4

def test_function_stack_three():
    def simple_function_child(n):
        return n * 2

    def simple_function_parent(n):
        return simple_function_child(2 * n)

    def simple_function_grandparent(n):
        return simple_function_parent(2 * n)

    with RecordTraceEvents(('call', 'return')) as rte:
        assert simple_function_grandparent(1) == 8
    print()
#     pprint.pprint(rte.records)
    print(rte)
    print('Code line numbers:', sorted(set([r.lineno_code for r in rte.records])))
    assert len(rte.records) == 6

def test_function_recursive():
    def simple_recursive_function(n):
        assert n >= 0
        if n == 0:
            return 1
        return 2 * simple_recursive_function(n - 1)

    with RecordTraceEvents(('call', 'return')) as rte:
        assert simple_recursive_function(3) == 8
    print()
#     pprint.pprint(rte.records)
    print(rte)
    print('Code line numbers:', sorted(set([r.lineno_code for r in rte.records])))
    assert len(rte.records) == 8
    
def test_same_named_functions():
    """Two classes that have the same named function called independently."""
    class NamedFunctionOne:
        def same_function(self, n):
            return n * 2

    class NamedFunctionTwo:
        def same_function(self, n):
            return n * 4

    with RecordTraceEvents(('call', 'return')) as rte:
        one = NamedFunctionOne()
        assert one.same_function(2) == 4
        two = NamedFunctionTwo()
        assert two.same_function(2) == 8
    print()
#     pprint.pprint(rte.records)
    print(rte)
    print('Code line numbers:', sorted(set([r.lineno_code for r in rte.records])))
    assert len(rte.records) == 4

def test_same_named_functions_interleave():
    """Two classes that have the same named function called one after the other."""
    class NamedFunctionOne:
        def same_function(self, n):
            return n * 2

    class NamedFunctionTwo:
        def same_function(self, n):
            one = NamedFunctionOne()
            return one.same_function(n) * 4

    with RecordTraceEvents(('call', 'return')) as rte:
        two = NamedFunctionTwo()
        assert two.same_function(2) == 16
    print()
#     pprint.pprint(rte.records)
    print(rte)
    print('Code line numbers:', sorted(set([r.lineno_code for r in rte.records])))
    assert len(rte.records) == 4

def test_generator():
    def simple_generator(n):
        for i in range(n):
            yield i

    with RecordTraceEvents(('call', 'exception', 'return')) as rte:
        # Avoid <listcomp> for the moment
#         results = [v for v in simple_generator(3)]
        results = []
        for v in simple_generator(3):
            results.append(v)
        assert results == [0, 1, 2]
    print()
#     pprint.pprint(rte.records)
    print(rte)
    print('Code line numbers:', sorted(set([r.lineno_code for r in rte.records])))
    assert len(rte.records) == 8

def test_generator_unfinished():
    def simple_generator(n):
        for i in range(n):
            yield i

    with RecordTraceEvents(('call', 'exception', 'return')) as rte:
        # Avoid <listcomp> for the moment
#         results = [v for v in simple_generator(3)]
        results = []
        gen = simple_generator(3)
        for i in range(2):
            results.append(next(gen))
        assert results == [0, 1]
    print()
#     pprint.pprint(rte.records)
    print(rte)
    print('Code line numbers:', sorted(set([r.lineno_code for r in rte.records])))
    assert len(rte.records) == 4

def test_generator_parent_child():
    def child_generator(n):
        for i in range(n):
            yield i

    def parent_generator(n):
        for value in child_generator(n):
            yield 2 * value

    with RecordTraceEvents(('call', 'exception', 'return')) as rte:
        # Avoid <listcomp> for the moment
#         results = [v for v in simple_generator(3)]
        results = []
        for v in parent_generator(3):
            results.append(v)
        assert results == [0, 2, 4]
    print()
#     pprint.pprint(rte.records)
    print(rte)
    print('Code line numbers:', sorted(set([r.lineno_code for r in rte.records])))
    assert len(rte.records) == 17

def test_generator_grandparent_parent_child():
    def child_generator(n):
        for i in range(n):
            yield i

    def parent_generator(n):
        for value in child_generator(n):
            yield 2 * value

    def grandparent_generator(n):
        for value in parent_generator(n):
            yield 2 * value

    with RecordTraceEvents(('call', 'exception', 'return')) as rte:
        # Avoid <listcomp> for the moment
        results = []
        for v in grandparent_generator(3):
            results.append(v)
        assert results == [0, 4, 8]
    print()
#     pprint.pprint(rte.records)
    print(rte)
    print('Code line numbers:', sorted(set([r.lineno_code for r in rte.records])))
    assert len(rte.records) == 26

def test_generator_class_different_named_methods():
    class ChildGenerator:
        def child_generate(self, n):
            yield n
            yield n * 2
            yield n * 4
    
    class ParentGenerator:
        def parent_generate(self, n):
            child = ChildGenerator()
            for value in child.child_generate(n):
                yield 3 * value
            
    with RecordTraceEvents(('call', 'exception', 'return')) as rte:
        # Avoid <listcomp> for the moment
        results = []
        gen_class = ParentGenerator()
        for v in gen_class.parent_generate(3):
            results.append(v)
        assert results == [9, 18, 36]
    print()
#     pprint.pprint(rte.records)
    print(rte)
    print('Code line numbers:', sorted(set([r.lineno_code for r in rte.records])))
    assert len(rte.records) == 17

def test_generator_class_same_named_methods():
    class ChildGenerator:
        def generate(self, n):
            yield n
            yield n * 2
            yield n * 4
    
    class ParentGenerator:
        def generate(self, n):
            child = ChildGenerator()
            for value in child.generate(n):
                yield 3 * value
            
    with RecordTraceEvents(('call', 'exception', 'return')) as rte:
        # Avoid <listcomp> for the moment
        results = []
        gen_class = ParentGenerator()
        for v in gen_class.generate(3):
            results.append(v)
        assert results == [9, 18, 36]
    print()
#     pprint.pprint(rte.records)
    print(rte)
    print('Code line numbers:', sorted(set([r.lineno_code for r in rte.records])))
    assert len(rte.records) == 17

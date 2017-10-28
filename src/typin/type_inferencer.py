"""
Created on 22 Jun 2017

@author: paulross
"""
from collections import OrderedDict
import inspect
import logging
import pprint
import sys

from typin import str_id_cache
from typin import types

# TODO: How to create the taxonomy? collections.abc [Python3]?
    
class FunctionTypes(object):
    TYPE_NAME_TRANSLATION = {
        '_io.StringIO' : 'IO[bytes]',
        'NoneType' : 'None',
    }
    def __init__(self):
        # TODO: Track a range of line numbers.
        # 'call' must be always the same line number
        # Since functions can not overlap the 'return' shows function bounds
        #
        # OrderedDict of {argument_name : set(types.Type), ...}
        self.arguments = OrderedDict()
        # dict of {line_number : set(types.Type), ...}
        self.return_types = {}
        # dict of {line_number : set(types.Type), ...}
        self.exception_types = {}
        # Should be unique
        self.call_line_number = 0
        # TODO: Track call/return type pairs so we can use the @overload
        # decorator in the .pyi files.
        
    def add_call(self, frame, line_number):
        """Adds a function call from the frame."""
        # arg_info is an ArgInfo object that has the following attributes:
        # args - list of names as strings.
        # varargs - name entry in the locals for *args or None.
        # keywords - name entry in the locals for *kwargs or None.
        # locals - dict of {name : value, ...} of arguments.
        arg_info = inspect.getargvalues(frame)
        for arg in arg_info.args:
            try:
                self.arguments[arg].add(types.Type(arg_info.locals[arg]))
            except KeyError:
                self.arguments[arg] = set([types.Type(arg_info.locals[arg])])
        if self.call_line_number == 0:
            self.call_line_number = line_number
        elif self.call_line_number != line_number:
            raise ValueError('Call site was {:d} now {:d}'.format(
                self.call_line_number, line_number)
            )
    
    def add_return(self, return_value, line_number):
        t = types.Type(return_value)
        try:
            self.return_types[line_number].add(t)
        except KeyError:
            self.return_types[line_number] = set([t])
        
    def add_exception(self, exception, line_number):
        t = types.Type(exception)
        try:
            self.exception_types[line_number].add(t)
        except KeyError:
            self.exception_types[line_number] = set([t])
    
    def __str__(self):
        """Returns something like the annotation string."""
        sl = ['type:']
        for arg in self.arguments:
            arguments = sorted(self.arguments[arg])
            if len(arguments) == 1:
                sl.append('({:s} {:s})'.format(arg, str(arguments[0])))
            else:
                sl.append(
                    '({:s} {!r:s})'.format(
                        arg,
                        ', '.join([str(v) for v in arguments])
                    )
                )                
        # self.return_types is a dict of {line_number : set(types.Type), ...}
        return_types = set()
        for v in self.return_types.values():
            return_types |= v
        if len(return_types) == 0:
            sl.append('-> None')
        elif len(return_types) == 1:
            sl.append('-> {:s}'.format(str(return_types.pop())))
        else:
            sl.append('-> Union[{:s}]'.format(', '.join((t for t in return_types))))
        return ' '.join(sl)
    
    __repr__ = __str__
    
    def _type(self, name):
        """Translates a type name if necessary."""
        return self.TYPE_NAME_TRANSLATION.get(name, name)
        
    def stub_file_str(self):
        """Example: def encodebytes(s: bytes) -> bytes: ..."""
        sl = ['(']
        arg_str_list = []
        for arg_name in self.arguments:
            arguments = sorted(self.arguments[arg_name])
            if len(arguments) == 1:
                arg_str_list.append('{:s}: {:s}'.format(
                    arg_name,
                    self._type(str(arguments[0]))))
            else:
                arg_str_list.append(
                    '{:s}: {:s}'.format(
                        arg_name,
                        ', '.join([self._type(str(v)) for v in arguments])
                    )
                )
        sl.append(', '.join(arg_str_list)) 
        # self.return_types is a dict of {line_number : set(types.Type), ...}
        sl.append(') ->')
        return_types = set()
        for v in self.return_types.values():
            return_types |= v
        if len(return_types) == 0:
            sl.append(' None')
        elif len(return_types) == 1:
            sl.append(' {:s}'.format(self._type(str(return_types.pop()))))
        else:
            sl.append(' Union[{:s}]'.format(', '.join((self._type(t) for t in return_types))))
        sl.append(': ...')
        return ''.join(sl)
        

class TypeInferencer(object):
    """Infers types of function arguments and return values at runtime."""
    
    def __init__(self):
        """Constructor."""
        # dict of {file_path : { function_name : FunctionTypes, ...}, ...} 
        self.function_map = {}
        # Allow re-entrancy with sys.settrace(function)
        self._trace_fn_stack = []
                
    def _get_func_data(self, file_path, function_name):
        """Return a FunctionTypes() object for the function."""
        if file_path not in self.function_map:
            self.function_map[file_path] = {}
        if function_name not in self.function_map[file_path]:
            self.function_map[file_path][function_name] = FunctionTypes()
        r = self.function_map[file_path][function_name]
        return r
    
    def __call__(self, frame, event, arg):
        logging.debug('TypeInferencer.__call__', event, arg)
        if event in ('call', 'return', 'exception'):
            frame_info = inspect.getframeinfo(frame)
            file_path = frame_info.filename
            # TODO: For methods use __qualname__
            function_name = frame_info.function
            lineno = frame_info.lineno
            
#             print()
#             print(function_name)
#             print(inspect.getframeinfo(frame))
#             print(frame)

#             print(dir(frame))
#             print(' Frame '.center(75, '-'))
#             for attr in dir(frame):
#                 if attr.startswith('_') or attr in ('f_builtins', ):#'f_globals'):
#                     continue
#                 if attr == 'f_globals':
#                     pprint.pprint(getattr(frame, attr))
#                 else:
#                     print(attr, ':', type(getattr(frame, attr)), getattr(frame, attr))
#             print(' END: Frame '.center(75, '-'))

#             print(' GC Frame '.center(75, '-'))
#             import gc
#             for o in gc.get_objects():
#                 if inspect.isfunction(o):
# #                     print(dir(o))
# #                     print(o.__qualname__)
#                     # See: https://stackoverflow.com/questions/1132543/getting-callable-object-from-the-frame
#                     # Py2: if o.func_code is frame.f_code:
#                     if o.__code__ is frame.f_code:
#                         print(type(o), o, o.__qualname__) 
#             print(' END: GC Frame '.center(75, '-'))
# #             print(frame.f_code.co_name)
# #             print(frame.f_globals[frame.f_code.co_name], frame.f_globals[frame.f_code.co_name].__qualname__)
# 
#             print(frame.f_code)
#             print(dir(frame.f_code))

#             print(self.__exit__.__qualname__)
            
#             print(' Code '.center(75, '-'))
#             for attr in dir(frame.f_code):
#                 if not attr.startswith('_'):
#                     print(attr, ':', type(getattr(frame.f_code, attr)), getattr(frame.f_code, attr))
#             print(' END Code '.center(75, '-'))
            
#             print(frame.function.__qualname__)
            func_types = self._get_func_data(file_path, function_name)
            if event == 'call':
                # arg is None
                func_types.add_call(frame, lineno)
            elif event == 'return':
                # arg is return value
                func_types.add_return(arg, lineno)
            else:
                assert event == 'exception'
                # arg is a tuple (exception_type, exception_value, traceback)
                func_types.add_exception(arg[1], lineno)
        return self
    
    def __enter__(self):
        self._trace_fn_stack.append(sys.gettrace())
        sys.settrace(self)
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        sys.settrace(self._trace_fn_stack.pop())

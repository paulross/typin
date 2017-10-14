"""
Created on 22 Jun 2017

@author: paulross
"""
from collections import OrderedDict
import inspect
import re
import sys

from typin import str_id_cache

# TODO: How to create the taxonomy? collections.abc [Python3]?

    
class FunctionTypes(object):
    def __init__(self):
        # TODO: Track a range of line numbers.
        # 'call' must be always the same line number
        # Since functions can not overlap the 'return' shows function bounds
        #
        # dict of {name : set(types), ...}
        self.arguments = OrderedDict()
        self.return_types = set()
        self.exception_types = set()
        # TODO: Track call/return type pairs so we can use the @overload
        # decorator in th e.pyi files.
        
    def add_call(self, frame):
        """Adds a function call from the frame"""
        # arg_info is an ArgInfo object that has the following attributes:
        # args - list of names as strings.
        # varargs - name entry in the locals for *args or None.
        # keywords - name entry in the locals for *kwargs or None.
        # locals - dict of {name : value, ...} of arguments.
        arg_info = inspect.getargvalues(frame)
        for arg in arg_info.args:
            self.arguments[arg] = type(arg_info.locals[arg])
    
    def add_return(self, return_type):
        self.return_types.add(return_type)

    def add_exception(self, exception_type):
        self.exception_types.add(exception_type)
        
    def __str__(self):
        """Returns something like the annotation string."""
        sl = ['type:']
        for k in self.arguments:
            sl.append('({:s})'.format(str(self.arguments[k])))
        if len(self.return_types) == 0:
            sl.append('-> None')
        elif len(self.return_types) == 1:
            t = self.return_types.pop()
            sl.append('-> {:s}'.format(str(t)))
            # Preserve set
            self.return_types.add(t)
        else:
            sl.append('-> Union[{:s}]'.format(', '.join((t for t in self.return_types))))
        return ' '.join(sl)
    
    __repr__ = __str__

class TypeInferencer(object):
    """Infers types of function arguments and return values at runtime."""
    
    def __init__(self):
        """Constructor."""
        # dict of {file_path : { function_name : FunctionTypes, ...}, ...} 
        self._fn_map = {}
        # Allow re-entrancy with sys.setprofile(profilefunc)
        self._trace_fn_stack = []
                
    def _get_func_data(self, file_path, function_name):
        if file_path not in self._fn_map:
            self._fn_map[file_path] = {}
        if function_name not in self._fn_map[file_path]:
            self._fn_map[file_path][function_name] = FunctionTypes()
        r = self._fn_map[file_path][function_name]
        return r
    
    def __call__(self, frame, event, arg):
        if event in ('call', 'return', 'exception'):
            frame_info = inspect.getframeinfo(frame)
            file_path = frame_info.filename
            lineno = frame_info.lineno
            
#             print(frame)
#             print(dir(frame))
#             print(frame.f_code)
#             print(dir(frame.f_code))
#             print(frame.function.__qualname__)
            
            # TODO: use __qualname__
            func_info = self._get_func_data(file_path,
                                            frame_info.function)
            if event == 'call':
                # arg is None
                func_info.add_call(frame)
            elif event == 'return':
                # arg is return value
                func_info.add_return(type(arg))
            else:
                assert event == 'exception'
                # arg is a tuple (exception, value, traceback)
                pass
        return self
    
    def __enter__(self):
        self._trace_fn_stack.append(sys.gettrace())
        sys.settrace(self)
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        sys.settrace(self._trace_fn_stack.pop())

"""
Created on 22 Jun 2017

@author: paulross
"""
from collections import OrderedDict
import inspect
import sys

from typin import str_id_cache

class FunctionTypes(object):
    def __init__(self, function_name):
        # TODO: Function scope???
        self.name = function_name
        # dict of {name : set(types), ...}
        self.arguments = OrderedDict()
        self.return_types = set()
        self.exception_types = set()
        
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
    EVENTS = set(('call', 'return', 'exception'))
    def __init__(self):
        """Constructor."""
        # dict of {file_path : { line_number : FunctionTypes, ...}, ...} 
        self._fn_map = {}
        # Allow re-entrancy with sys.setprofile(profilefunc)
        self._fn_stack = []
                
    def _get_func_data(self, file_path, lineno, function_name):
        if file_path not in self._fn_map:
            self._fn_map[file_path] = {}
        if lineno not in self._fn_map[file_path]:
            self._fn_map[file_path][lineno] = FunctionTypes(function_name)
        r = self._fn_map[file_path][lineno]
        assert r.name == function_name
        return r
    
    def __call__(self, frame, event, arg):
        # For sys.setprofile(self)
        if event in self.EVENTS:
            frame_info = inspect.getframeinfo(frame)
            file_path = frame_info.filename
            lineno = frame_info.lineno
            func_info = self._get_func_data(file_path,
                                            lineno,
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
        self._fn_stack.append(sys.getprofile())
        sys.setprofile(self)
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        sys.setprofile(self._fn_stack.pop())

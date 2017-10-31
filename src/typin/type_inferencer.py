"""
Created on 22 Jun 2017

@author: paulross
"""
from collections import OrderedDict
import gc
import inspect
import logging
import pprint
import sys

from typin import str_id_cache
from typin import types

# TODO: How to create the taxonomy? collections.abc [Python3]?

class TypesBase(object):
    TYPE_NAME_TRANSLATION = {
        '_io.StringIO' : 'IO[bytes]',
        'NoneType' : 'None',
    }

class ClassBaseTypes(TypesBase):
    """Holds the __bases__ of a class."""
    def __init__(self, obj):
        super().__init__()
        assert inspect.isclass(obj)
        self.bases = tuple(types.Type(o) for o in obj.__class__.__bases__)
        
    def __str__(self):
        return str(tuple([str(t) for t in self.bases]))
    
#     __repr__ = __str__

class FunctionTypes(TypesBase):
    def __init__(self):
        super().__init__()
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
        # Largest seen line number
        self.max_line_number = 0
        # TODO: Track call/return type pairs so we can use the @overload
        # decorator in the .pyi files.

    @property
    def line_range(self):
        return self.call_line_number, self.max_line_number
        
    def add_call(self, frame, line_number):
        """Adds a function call from the frame."""
        # arg_info is an ArgInfo object that has the following attributes:
        # args - list of names as strings.
        # varargs - name entry in the locals for *args or None.
        # keywords - name entry in the locals for *kwargs or None.
        # locals - dict of {name : value, ...} of arguments.
        self.max_line_number = max(self.max_line_number, line_number)
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
        """Records a return value at a particular line number.
        If the return_value is None and we have previously seen an exception at
        this line then this is a phantom return value and must be ignored.
        See ``TypeInferencer.__enter__`` for a description of this.
        """
        self.max_line_number = max(self.max_line_number, line_number)
        if return_value is None and line_number in self.exception_types:
            # Ignore phantom return value
            return
        t = types.Type(return_value)
        try:
            self.return_types[line_number].add(t)
        except KeyError:
            self.return_types[line_number] = set([t])
        
    def add_exception(self, exception, line_number):
        self.max_line_number = max(self.max_line_number, line_number)
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
            sl.append('-> Union[{:s}]'.format(
                ', '.join((self._type(str(t)) for t in return_types)))
            )
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
            if arg_name.startswith('self'):
                arg_str_list.append('self')
            else:
                argument_types = sorted(self.arguments[arg_name])
                if len(argument_types) == 1:
                    arg_str_list.append('{:s}: {:s}'.format(
                        arg_name,
                        self._type(str(argument_types[0]))))
                else:
                    arg_str_list.append(
                        '{:s}: {:s}'.format(
                            arg_name,
                            ', '.join([self._type(str(v)) for v in argument_types])
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
            sl.append(
                ' Union[{:s}]'.format(
                    ', '.join(
                        sorted(self._type(str(t)) for t in return_types)
                    )
                )
            )
        sl.append(': ...')
        return ''.join(sl)

class TypeInferencer(object):
    """Infers types of function arguments and return values at runtime."""
    INDENT = '    '
    def __init__(self):
        """Constructor."""
        # dict of {file_path : { namespace : { function_name : FunctionTypes, ...}, ...} 
        self.function_map = {}
        # Bases classes of a class from __bases__
        # dict of {file_path : { namespace : (__bases__, ...), ...}
        self.class_bases = {} 
        # Allow re-entrancy with sys.settrace(function)
        self._trace_fn_stack = []
        
    def function_types(self, file_path, namespace, function_name):
        """Returns the FunctionTypes object for the file_path, namespace and
        function_name. namespace will be '' for global functions.
        May raise a KeyError."""
        return self.function_map[file_path][namespace][function_name]
    
    def _pformat_class_line(self, file_path, prefix, class_name_stack):
        assert len(class_name_stack) > 0, \
            'Class name stack {!r:s} must have one item.'.format(class_name_stack)
        scoped_name = '.'.join(class_name_stack)
        
#         print('TRACE self.class_bases:', '.'.join(scoped_name))
#         pprint.pprint(self.class_bases)
        
        try:
            bases_types = self.class_bases[file_path][scoped_name]
        except KeyError:
            # This is a bit hacky. Suppose we have class B within class A and
            # only B has methods that we exercise. Then we never get to see
            # A's inheritance, only B's. In this case we assume A has no base
            # classes
            bases_types = tuple()
        bases_str = [types.Type.str_of_type(t) for t in bases_types]
        bases_str = [self._strip_locals_from_qualified_name(_v) for _v in bases_str]
        if 'object' in bases_str:
            # Python2.7 - we might want to revise this
            bases_str.remove('object')
        if len(bases_str) > 0:
            base_str = '({:s})'.format(', '.join(bases_str))
        else:
            base_str = ''
        return '{:s}class {:s}{:s}:'.format(prefix, class_name_stack[-1], base_str)
    
    def _pformat_file(self, file_path):
        # file_map is { namespace : { function_name : FunctionTypes, ...}
        file_map = self.function_map[file_path]
#         pprint.pprint(file_map)
        str_list = []
        for namespace in sorted(file_map.keys()):
            prefix = ''
            if namespace:
                namespace_stack = namespace.split('.')
                # If enclosing namespace(s) not in the map then we have an
                # enclosing class with no methods of its own so just write out
                # the enclosing class declaration
                # Walk down the namespace and find any classes that are empty.
                # break as soon as we find one that is non-empty as enclosing
                # empty classes will have already been written out.
                i = len(namespace_stack) - 1 # [:i] is enclosing scope
                while i > 0:
                    if '.'.join(namespace_stack[:i]) in file_map:
                        break
                    i -= 1
                # Now write out all the enclosing empty classes
                while i < len(namespace_stack) - 1:
                    prefix = self.INDENT * i
#                     str_list.append('{:s}class {:s}:'.format(prefix, namespace_stack[i]))
                    str_list.append(self._pformat_class_line(file_path, prefix,
                                                             namespace_stack[:i+1],
                                                             ))
                    i += 1
                # Continue with this base class
                prefix = self.INDENT * (len(namespace_stack) - 1)
#                 str_list.append('{:s}class {:s}:'.format(prefix, namespace_stack[-1]))
                str_list.append(self._pformat_class_line(file_path, prefix,
                                                         namespace_stack))
                prefix += self.INDENT
            for function_name in sorted(file_map[namespace]):
                str_list.append('{:s}def {:s}{:s}'.format(
                    prefix,
                    function_name,
                    file_map[namespace][function_name].stub_file_str()
                    )
                )
        return str_list

    def pretty_format(self, file=None):
        str_list = []
        # {file_path : { namespace : { function_name : FunctionTypes, ...}, ...}
        if file is None:
            for file_path in sorted(self.function_map.keys()):
                str_list.append('File: {:s}'.format(file_path))
                str_list.extend(self._pformat_file(file_path))
        else:
            str_list.extend(self._pformat_file(file))
        return '\n'.join(str_list)
                
    def _get_func_data(self, file_path, qualified_name):
        """Return a FunctionTypes() object for the function, created if necessary."""
        if file_path not in self.function_map:
            self.function_map[file_path] = {}
        # Compute namespace hierarchy
        hierarchy = qualified_name.split('.')
        assert len(hierarchy) > 0
        if len(hierarchy) == 1:
            namespace = ''
            function_name = hierarchy[0]
        else:
            namespace = '.'.join(hierarchy[:-1])
            function_name = hierarchy[-1]
        if namespace not in self.function_map[file_path]:
            self.function_map[file_path][namespace] = {}
        if function_name not in self.function_map[file_path][namespace]:
            self.function_map[file_path][namespace][function_name] = FunctionTypes()
        r = self.function_map[file_path][namespace][function_name]
        return r
    
    def _set_bases(self, file_path, q_name, bases):
        """classname including dotted scope."""
        parent_scope = '.'.join(q_name.split('.')[:-1])
        if file_path not in self.function_map:
            self.class_bases[file_path] = {}
        if parent_scope not in self.class_bases[file_path]:
            self.class_bases[file_path][parent_scope] = bases
        elif self.class_bases[file_path][parent_scope] != bases:
#             print('TRACE:', str(bases))
            raise ValueError('Bases changed for {:s} from {!r:s} to {!r:s}'.format(
                    parent_scope,
                    self.class_bases[file_path][parent_scope],
                    bases,
                )
            )
    
    def _strip_locals_from_qualified_name(self, qualified_name):
        idx = qualified_name.find('<locals>')
        if idx == -1:
            return qualified_name
        # Strip prefix
        return qualified_name[idx + len('<locals>') + 1:]
        
    def _qualified_name(self, frame):
        # The qualified name of the function 
        q_name = ''
        bases = tuple()
        fn_obj = None
        for fn_obj in gc.get_objects():
            # See:
            # https://stackoverflow.com/questions/1132543/getting-callable-object-from-the-frame
            # Py2: if o.func_code is frame.f_code:
            if inspect.isfunction(fn_obj) and fn_obj.__code__ is frame.f_code:
#                 idx = fn_obj.__qualname__.find('<locals>')
#                 if idx == -1:
#                     q_name = fn_obj.__qualname__
#                 else:
#                     # Strip prefix
#                     q_name = fn_obj.__qualname__[idx + len('<locals>') + 1:]
                q_name = self._strip_locals_from_qualified_name(fn_obj.__qualname__)
                break
        if fn_obj is not None:
            for class_obj in gc.get_objects():
                # Something like:
                # function_object.__name__ in class_obj.__dict__
                # and class_obj.__dict__[function_object.__name__] == function_object
                if inspect.isclass(class_obj) \
                and fn_obj.__name__ in class_obj.__dict__ \
                and class_obj.__dict__[fn_obj.__name__] == fn_obj:
#                     bases = ClassBaseTypes(class_obj)
#                     bases = class_obj.__class__.__bases__
                    bases = class_obj.__bases__
#                     print('TRACE finding bases:', class_obj, class_obj.__class__, bases)
#         print('TRACE:', q_name, bases)
        return q_name, bases

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
# #             import gc
#             for o in gc.get_objects():
#                 if inspect.isfunction(o):
# #                     print(dir(o))
# #                     print(o.__qualname__)
#                     # See: https://stackoverflow.com/questions/1132543/getting-callable-object-from-the-frame
#                     # Py2: if o.func_code is frame.f_code:
#                     if o.__code__ is frame.f_code:
#                         idx = o.__qualname__.find('<locals>')
#                         if idx != -1:
#                             name = o.__qualname__[idx + len('<locals>') + 1:]
#                         else:
#                             name = o.__qualname__
#                         print(type(o), o, name) 
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

#             print('Qualified name:', self._qualified_name(frame))
            
#             func_types = self._get_func_data(file_path, function_name)
            q_name, bases = self._qualified_name(frame)
            self._set_bases(file_path, q_name, bases)
            func_types = self._get_func_data(file_path, q_name)
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
        """Context manager sets the profiling function.
        We need to use ``sys.settrace()`` not ``sys.setprofile()`` as the
        latter does not see the exception.
        Suppose ``typin/src/typin/research.py`` raises an exception on line 41
        in function c() we will see the event::
            
            typin/src/typin/research.py 41 c return None
        
        With ``sys.settrace()`` we get::
        
            # c() raises. We can see this as an exception event is followed by
            # a return None with the same lineno.
            # Return None on its own is not enough as that might happen in the
            # normal course of events.
            typin/src/typin/research.py 41 c exception (<class 'ValueError'>, ValueError(), <traceback object at 0x102365c08>)
            typin/src/typin/research.py 41 c return None

        So returning None on the same line as a previously seen exception must
        be ignored as it is a phantom return value.
        """
        self._trace_fn_stack.append(sys.gettrace())
        sys.settrace(self)
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        sys.settrace(self._trace_fn_stack.pop())

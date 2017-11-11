"""
Created on 22 Jun 2017

@author: paulross
"""
import gc
import inspect
import logging
import os
import pprint
import re
import sys
import traceback

# from typin import str_id_cache
from typin import types

# TODO: How to create the taxonomy? collections.abc [Python3]?

class TypeInferencer(object):
    """Infers types of function arguments and return values at runtime.
    This is used as a context manager thus::
    
        with type_inferencer.TypeInferencer() as ti:
            # Execute your code here...
            
        # Look at the data that ti has captured.
    """
    INDENT = '    '
    # Match a temporary file such as '<string>' or '<frozen importlib._bootstrap>'
    # This is matched on os.path.basename 
    RE_TEMPORARY_FILE = re.compile(r'<(.+)>')
    GLOBAL_NAMESPACE = ''
    def __init__(self):
        """Constructor, takes no arguments, merely initialises internal state."""
        # dict of {file_path : { namespace : { function_name : FunctionTypes, ...}, ...} 
        self.function_map = {}
        # Bases classes of a class from __bases__
        # dict of {file_path : { namespace : (__bases__, ...), ...}
        self.class_bases = {} 
        # Allow re-entrancy with sys.settrace(function)
        self._trace_fn_stack = []
        
    def dump(self, stream=sys.stdout):
        """Dump the internal representation to a stream."""
        stream.write(' TypeInferencer.dump() '.center(75, '='))
        stream.write('\n')
        stream.write(' self.function_map '.center(75, '-'))
        stream.write('\n')
        # dict of {file_path : { namespace : { function_name : FunctionTypes, ...}, ...} 
        for file_path in sorted(self.function_map.keys()):
            stream.write('File: {:s}\n'.format(file_path))
            for namespace in sorted(self.function_map[file_path].keys()):
                stream.write('  Namespace: "{:s}"\n'.format(namespace))
                for function in sorted(self.function_map[file_path][namespace].keys()):
                    stream.write(
                        '    Function: "{:s}" {!r:s}\n'.format(
                            function, self.function_map[file_path][namespace][function]
                        )
                    )
        stream.write(' END: self.function_map '.center(75, '-'))
        stream.write('\n')
        stream.write(' self.class_basses '.center(75, '-'))
        stream.write('\n')
        # dict of {file_path : { namespace : (__bases__, ...), ...}
        for file_path in sorted(self.class_bases.keys()):
            non_global_ns = [ns for ns in self.class_bases[file_path].keys()
                             if ns != self.GLOBAL_NAMESPACE]
            if len(non_global_ns):
                stream.write(file_path)
                stream.write('\n')
                for ns in sorted(non_global_ns):
                    if ns != self.GLOBAL_NAMESPACE:
                        stream.write('{:s}{:s}: {!r:s}'.format(
                           self.INDENT,
                           ns,
                           self.class_bases[file_path][ns]),
                        )
                        stream.write('\n')
        stream.write(' END: self.class_basses '.center(75, '-'))
        stream.write('\n')
        stream.write(' END: TypeInferencer.dump() '.center(75, '='))
        stream.write('\n')
        
    def file_paths(self):
        """Returns the file paths seen as a dict keys object."""
        return self.function_map.keys()
    
    def namespaces(self, file_path):
        """Returns the namespaces seen the file as a dict keys object."""
        return self.function_map[file_path].keys()
    
    def function_names(self, file_path, namespace):
        """Returns the function names seen the file and namespace as a dict
        keys object."""
        return self.function_map[file_path][namespace].keys()
    
    def function_types(self, file_path, namespace, function_name):
        """Returns the FunctionTypes object for the file_path, namespace and
        function_name. namespace will be '' for global functions.
        May raise a KeyError."""
        return self.function_map[file_path][namespace][function_name]
    
    def file_paths_filtered(self, file_path_prefix=os.sep, relative=False):
        """Returns a list of file paths seen that have the prefix when that is
        converted to an absolute path e.g. os.getcwd().
        If relative then a list of tuples is returned [(key, suffix), ...]
        The default arguments mean that all paths are returned."""
        abs_path = os.path.abspath(os.path.normpath(file_path_prefix))
        ret_val = [k for k in self.function_map.keys() if k.startswith(abs_path)]
        if relative:
            ret_val = [(v, v[len(abs_path)+1:]) for v in ret_val]
        return ret_val
    
#     def file_paths_cwd(self, relative=False):
#         """Returns a list of file paths seen that are below the current
#         working directory."""
#         return self.file_paths_filtered(os.getcwd(), relative=relative)
    
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
            # For Python2.7 we might want to revise this
            bases_str.remove('object')
        if len(bases_str) > 0:
            base_str = '({:s})'.format(', '.join(bases_str))
        else:
            base_str = ''
        return '{:s}class {:s}{:s}:'.format(prefix, class_name_stack[-1], base_str)
    
    def _pformat_file(self, file_path, add_line_number_as_comment):
        # file_map is { namespace : { function_name : FunctionTypes, ...}
        file_map = self.function_map[file_path]
#         pprint.pprint(file_map)
        str_list = []
        for namespace in sorted(file_map.keys()):
            prefix = ''
            if namespace != self.GLOBAL_NAMESPACE:
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
                    str_list.append(self._pformat_class_line(file_path, prefix,
                                                             namespace_stack[:i+1],
                                                             ))
                    i += 1
                # Continue with this base class
                prefix = self.INDENT * (len(namespace_stack) - 1)
                str_list.append(self._pformat_class_line(file_path, prefix,
                                                         namespace_stack))
                prefix += self.INDENT
            for function_name in sorted(file_map[namespace]):
                fts = file_map[namespace][function_name]
                str_list.append('{:s}def {:s}{:s}'.format(
                    prefix,
                    function_name,
                    fts.stub_file_str()
                    )
                )
                if add_line_number_as_comment:
                    str_list[-1] = str_list[-1] + '#{:d}'.format(fts.line_range[0])
        return str_list

    def pretty_format(self, file=None, add_line_number_as_comment=False):
        """Returns a pretty formatted string."""
        str_list = []
        # {file_path : { namespace : { function_name : FunctionTypes, ...}, ...}
        if file is None:
            for file_path in sorted(self.function_map.keys()):
                str_list.append('File: {:s}'.format(file_path))
                str_list.extend(self._pformat_file(file_path, add_line_number_as_comment))
        else:
            str_list.extend(self._pformat_file(file, add_line_number_as_comment))
        return '\n'.join(str_list)
    
    def stub_file_str(self, file_path, namespace, function_name):
        fts = self.function_types(file_path, namespace, function_name)
        return 'def {:s}{:s}'.format(function_name, fts.stub_file_str())
    
    def docstring(self, file_path, namespace, function_name, style='sphinx'):
        fts = self.function_types(file_path, namespace, function_name)
        return fts.docstring(style)
    
    def _get_func_data(self, file_path, qualified_name):
        """Return a FunctionTypes() object for the function, created if necessary."""
        if file_path not in self.function_map:
            self.function_map[file_path] = {}
        # Compute namespace hierarchy
        hierarchy = qualified_name.split('.')
        assert len(hierarchy) > 0
        if len(hierarchy) == 1:
            namespace = self.GLOBAL_NAMESPACE
            function_name = hierarchy[0]
        else:
            namespace = '.'.join(hierarchy[:-1])
            function_name = hierarchy[-1]
        if namespace not in self.function_map[file_path]:
            self.function_map[file_path][namespace] = {}
        if function_name not in self.function_map[file_path][namespace]:
            self.function_map[file_path][namespace][function_name] = types.FunctionTypes()
        r = self.function_map[file_path][namespace][function_name]
        return r
    
    def is_temporary_file(self, file_path):
        """Returns True if the file_path is to a temporary file such as '<string>'
        or:
        /Users/USER/Documents/workspace/typin/src/typin/<frozen importlib._bootstrap>
        """
        m = self.RE_TEMPORARY_FILE.match(os.path.basename(file_path))
        return m is not None
    
    def _set_bases(self, file_path, lineno, q_name, bases):
        """classname including dotted scope."""
#         print('_set_bases:', file_path, lineno, q_name, bases)
        parent_scope = '.'.join(q_name.split('.')[:-1])
        if file_path not in self.function_map:
            self.class_bases[file_path] = {}
        if parent_scope not in self.class_bases[file_path]:
            self.class_bases[file_path][parent_scope] = bases
        elif self.class_bases[file_path][parent_scope] != bases:
#             if not self.is_temporary_file(file_path):
#                 # Temporary files such as '<frozen importlib._bootstrap>'
#                 raise ValueError('In {:s}#{:d} bases changed for {:s} from {!r:s} to {!r:s}'.format(
#                         file_path,
#                         lineno,
#                         parent_scope,
#                         self.class_bases[file_path][parent_scope],
#                         bases,
#                     )
#                 )
            if not self.is_temporary_file(file_path):
                logging.warning(
                    'In {:s}#{:d} bases changed for {:s} from {!r:s} to {!r:s}'.format(
                        file_path,
                        lineno,
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
        """This takes a frame and discovers which function is being executed.
        It then returns the qualified name of the function as a string and the
        base classes (as a tuple of types) of the enclosing object (if any).
        
        This pretty flakey for a number of reasons:
        
        * It searches the whole garbage collector for live functions that match.
          This is really expensive, surely there is a better way?
        * It frequently fails to discover base class types for reasons not yet
          well understood.

        If this can be made more reliable then cacheing could help to make the
        performance problem go away. 
        """
        # The qualified name of the function 
        q_name = ''
        bases = None
        fn_obj = None
        function_name = ''
        for _fn_obj in gc.get_objects():
            # See:
            # https://stackoverflow.com/questions/1132543/getting-callable-object-from-the-frame
            # Py2: if o.func_code is frame.f_code:
            if inspect.isfunction(_fn_obj) and _fn_obj.__code__ is frame.f_code:
#                 print('TRACE: _fn_obj', _fn_obj, _fn_obj.__qualname__, _fn_obj.__name__)
                q_name = self._strip_locals_from_qualified_name(_fn_obj.__qualname__)
                fn_obj = _fn_obj
                break
        # Find the immediate namespace
        q_list = q_name.split('.')
        if len(q_list) > 1:
            cls_name = '.'.join(q_list[:-1])
            cls_name_leaf = q_list[-2]
        else:
            # Global
            cls_name = ''
            cls_name_leaf = ''
        if fn_obj is not None:
            if fn_obj.__name__.startswith('__') and not fn_obj.__name__.endswith('__'):
                # Name mangling: class A that has def __private the key is _A__private
                function_name = '_{:s}{:s}'.format(cls_name_leaf, fn_obj.__name__)
            else:
                function_name = fn_obj.__name__
#             print('function_name', function_name)
            for class_obj in gc.get_objects():
                # Something like:
                # function_object.__name__ in class_obj.__dict__
                # and class_obj.__dict__[function_name] == function_object
#                 if inspect.isclass(class_obj):
#                     print('class_obj.__dict__', class_obj.__name__, class_obj.__dict__.keys(), class_obj.__bases__)
                if inspect.isclass(class_obj) \
                and function_name in class_obj.__dict__ \
                and class_obj.__dict__[function_name] == fn_obj:
                    bases = class_obj.__bases__
                    break
        else:
            logging.warning('Can not find function in frame')
#         print('TRACE: _qualified_name():', q_name, bases)
        if bases is None:
            if cls_name != '':
                logging.warning('Can not find bases for class "{:s}" method "{:s}"'.format(cls_name, function_name))
            bases = tuple()
        return q_name, bases

    def __call__(self, frame, event, arg):
        frame_info = inspect.getframeinfo(frame)
        try:
            logging.debug(
                'TypeInferencer.__call__({!r:s}, {!r:s}): function: {:s} file: {:s}#{:d}'.format(
                    event, arg, frame_info.function, frame_info.filename, frame_info.lineno
                )
            )
        except Exception:
            # This can happen when calling __repr__ on partially constructed objects
            # For example with argparse:
            # AttributeError: 'ArgumentParser' object has no attribute 'prog'
            logging.warning(
                'TypeInferencer.__call__(): failed, function: {:s} file: {:s}#{:d}'.format(
                    frame_info.function, frame_info.filename, frame_info.lineno
                )
            )
            pass
        if event in ('call', 'return', 'exception'):# and frame_info.filename != '<module>':
            file_path = os.path.abspath(frame_info.filename)
            # TODO: For methods use __qualname__
#             function_name = frame_info.function
            lineno = frame_info.lineno
            q_name, bases = self._qualified_name(frame)
            logging.debug(
                'TypeInferencer.__call__(): q_name="{:s}", bases={!r:s})'.format(
                    q_name, bases
            ))
            if q_name != '':
                try:
                    self._set_bases(file_path, lineno, q_name, bases)
                    func_types = self._get_func_data(file_path, q_name)
                    if event == 'call':
                        # arg is None
                        func_types.add_call(inspect.getargvalues(frame), file_path, lineno)
                    elif event == 'return':
                        # arg is return value
                        func_types.add_return(arg, lineno)
                    else:
                        assert event == 'exception'
                        # arg is a tuple (exception_type, exception_value, traceback)
                        func_types.add_exception(arg[1], lineno)
                except Exception as err:
                    logging.error(str(err))
                    logging.error(''.join(traceback.format_stack()))
        return self
    
    def _cleanup(self):
        """This does any spring cleaning once tracing has stopped.
        The only thing this currently does is to remove spurious function calls
        that appear when using exec() at the point of class declaration.
        I don't understand why this is so but a function call event is generated
        which ends up with the entry point the class declaration and the return
        line the declaration of the last method.
        """
        # self.function_map is a dict of:
        # {file_path : { namespace : { function_name : FunctionTypes, ...}, ...}
        for file_path in self.function_map:
            class_names = []
            for ns in self.function_map[file_path]:
                if ns != self.GLOBAL_NAMESPACE:
                    class_names.append(ns.split('.')[-1])
            names_to_remove = []
            if self.GLOBAL_NAMESPACE in self.function_map[file_path]:
                for function_name in  self.function_map[file_path][self.GLOBAL_NAMESPACE]:
                    if function_name in class_names:
                        names_to_remove.append(function_name)
            if len(names_to_remove):
                logging.debug('TypeInferencer._cleanup(): file: {:s}'.format(file_path))
            for function_name in names_to_remove:
                logging.debug('TypeInferencer._cleanup(): removing {:s}'.format(function_name))
                del self.function_map[file_path][self.GLOBAL_NAMESPACE][function_name]
    
    def __enter__(self):
        """Context manager sets the profiling function. This saves the existing
        tracing function.
        We need to use ``sys.settrace()`` not ``sys.setprofile()`` as the
        latter does not see any exception raised.
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
        """Exit the context manager. This performs some cleanup and then
        restores the tracing function to that prior to ``__enter__``."""
        # TODO: Check what is sys.gettrace(), if it is not self then someone has
        # monkeyed with the tracing.
        sys.settrace(self._trace_fn_stack.pop())
        self._cleanup()

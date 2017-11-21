"""
Created on 22 Jun 2017

@author: paulross
"""
import collections
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

class TypeInferencerExceptionBase(Exception):
    """Base class for exceptions thrown by this module."""
    pass

class TypeInferencerExceptionConflictingLines(TypeInferencerExceptionBase):
    """Exception thrown when multiple functions appear on same line."""
    pass

RE_DECORATOR = re.compile(r'\s*@(\S+)\s*')
RE_FUNCTION = re.compile(r'\s*def\s+(\S+)\((.*)')
RE_METHOD = re.compile(r'\s*def\s+(\S+)\(self(.*)')

#: This is to hold exception data while we decide whether the exception is
#: caught within a function (then we don't record the function as raising or
#: propagating the exception) or not. See research.rst 2017-11-16 and 18.
#: eventno is an event counter and check that event after exception is
#: is the next immediate event.
ExceptionInProgress = collections.namedtuple(
    'ExceptionInProgress', 'filename function lineno exception_value eventno'
)

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
    FALSE_FUNCTION_NAMES = ('<dictcomp>', '<genexpr>', '<listcomp>', '<module>', '<setcomp>')
    DOCSTRING_STYLE_DEFAULT = 'sphinx'
    DOCSTRING_STYLES_AVAILABLE = ('sphinx',)
    def __init__(self, verbose=0):
        """Constructor, takes no arguments, merely initialises internal state."""
        # dict of {file_path : { namespace : { function_name : FunctionTypes, ...}, ...}
        self.function_map = {}
        # TODO: Record if the function is a generator/co-routine by observing StopIteration?
        # Bases classes of a class from __bases__
        # dict of {file_path : { namespace : (__bases__, ...), ...}
        self.class_bases = {}
        # Allow re-entrancy with sys.settrace(function)
        self._trace_fn_stack = []
        # Verbose output, unused.
        self.verbose = verbose
        # Deferred evaluation of exceptions to exclude spurious
        # return None events
        # This is a ExceptionInProgress object or None
        self.exception_in_progress = None
        # Event number for checking exceptions
        self.eventno = 0
        # Event counters for different events, for the curious
        self.event_counter = collections.Counter()
        # Used for trace/debug
        self._trace_flag = False

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
                if len(str_list):
                    str_list.append('')
                str_list.append('File: {:s}'.format(file_path))
                str_list.extend(self._pformat_file(file_path, add_line_number_as_comment))
        else:
            str_list.extend(self._pformat_file(file, add_line_number_as_comment))
        return '\n'.join(str_list)

    def stub_file_str(self, file_path, namespace, function_name):
        fts = self.function_types(file_path, namespace, function_name)
        return 'def {:s}{:s}'.format(function_name, fts.stub_file_str())

    def docstring(self, file_path, namespace, function_name, style=DOCSTRING_STYLE_DEFAULT):
        """Returns a pair (line_number, docstring) for the function."""
        fts = self.function_types(file_path, namespace, function_name)
        include_returns = function_name != '__init__'
        return fts.docstring(include_returns, style)

    def docstring_map(self, file_path, style=DOCSTRING_STYLE_DEFAULT):
        """Returns a dict of {line_number : (namespace, function_name, docstring), ...} for the file."""
        line_docs = {}
        for namespace in self.function_map[file_path]:
            for function_name in self.function_map[file_path][namespace]:
                fts = self.function_map[file_path][namespace][function_name]
                include_returns = function_name != '__init__'
                lineno, docstring = fts.docstring(include_returns, style)
                if lineno in line_docs:
                    raise TypeInferencerExceptionConflictingLines('Line {:d} appears twice'.format(lineno))
                line_docs[lineno] = (namespace, function_name, docstring)
        return line_docs

    def _get_func_data(self, file_path, qualified_name, signature):
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
            self.function_map[file_path][namespace][function_name] = types.FunctionTypes(signature)
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

    def _qualified_name_bases_signature(self, frame, bases_cache={}):
        """This takes a frame and discovers which function is being executed.
        It then returns the qualified name of the function as a string and the
        base classes (as a tuple of types) of the enclosing object (if any).

        This pretty flakey for a number of reasons:

        * It searches the whole garbage collector for live functions that match.
          This is really expensive, surely there is a better way?
        * It frequently fails to discover base class types for reasons not yet
          well understood.
        * Functions declared within functions fail.

        If this can be made more reliable then cacheing could help to make the
        performance problem go away.
        """
        # The qualified name of the function
        q_name = ''
        bases = None
        fn_obj = None
        signature = None
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
        if fn_obj is None:
            logging.warning('Can not find function in frame {:s}'.format(repr(inspect.getframeinfo(frame))))
        else:
            # Try the cache
            frame_info = inspect.getframeinfo(frame)
            if frame_info.filename in bases_cache and cls_name in bases_cache[frame_info.filename]:
                bases = bases_cache[frame_info.filename][cls_name]
            else:
                # Look up the bases
                if fn_obj.__name__.startswith('__') and not fn_obj.__name__.endswith('__'):
                    # Name mangling: class A that has def __private the key is _A__private
                    function_name = '_{:s}{:s}'.format(cls_name_leaf, fn_obj.__name__)
                else:
                    function_name = fn_obj.__name__
                # print('function_name', function_name)
                for class_obj in gc.get_objects():
                    # Something like:
                    # function_object.__name__ in class_obj.__dict__
                    # and class_obj.__dict__[function_name] == function_object
                    # if inspect.isclass(class_obj):
                    #     print('class_obj.__dict__', class_obj.__name__, class_obj.__dict__.keys(), class_obj.__bases__)
                    if inspect.isclass(class_obj) \
                    and function_name in class_obj.__dict__ \
                    and class_obj.__dict__[function_name] == fn_obj:
                        bases = class_obj.__bases__
                        # Cache the bases
                        if frame_info.filename not in bases_cache:
                            bases_cache[frame_info.filename] = {}
                        bases_cache[frame_info.filename][cls_name] = bases
                        break
            signature = inspect.signature(fn_obj)
        # print('TRACE: _qualified_name_bases_signature():', q_name, bases, signature)
        if bases is None:
            if cls_name != '':
                logging.warning(
                    'Can not find bases for class "{:s}" method "{:s}" frame: {!r:s}'.format(
                        cls_name, function_name, inspect.getframeinfo(frame)
                    )
                )
            bases = tuple()
        return q_name, bases, signature

    def _trace(self, *args):
        if self._trace_flag:
            print(*args)

    def _debug(self, *args):
        if self._trace_flag:
            print(*args)
        logging.debug(*args)

    def _warn(self, *args):
        if self._trace_flag:
            print(*args)
        logging.warning(*args)

    def _error(self, *args):
        if self._trace_flag:
            print(*args)
        logging.error(*args)

    def _assert_exception_propagates(self, event, arg, frame_info):
        """Does some asserts when an exception is propagates from a function."""
        assert event == 'return', 'Event is "{!r:s}"'.format(event)
        assert arg is None, 'arg is {!r:s} instead of None'.format(arg)
        assert self.exception_in_progress is not None, \
            'self.exception_in_progress: {!r:s}'.format(self.exception_in_progress)
        assert frame_info.filename == self.exception_in_progress.filename, \
            '"return": File name was {:s} now {:s}'.format(
                self.exception_in_progress.filename, frame_info.filename
            )
        assert frame_info.function == self.exception_in_progress.function, \
            '"return": Function was "{:s}" now "{:s}"'.format(
                self.exception_in_progress.function, frame_info.function
            )
        assert frame_info.lineno == self.exception_in_progress.lineno, \
            '"return": Line number was {:d} now {:d}'.format(
                self.exception_in_progress.lineno, frame_info.lineno
            )
        assert self.exception_in_progress.eventno == self.eventno - 1, \
            '"return": Event number was {:d}, expected {:d}'.format(
                self.exception_in_progress.eventno, self.eventno - 1
            )

    def _assert_exception_caught(self, event, arg, frame_info):
        """Does some asserts when an exception is caught within a function."""
        assert event == 'line', 'Event is "{!r:s}"'.format(event)
        assert self.exception_in_progress is not None, \
            'self.exception_in_progress: {!r:s}'.format(self.exception_in_progress)
        assert arg is None, 'arg is {!r:s} instead of None'.format(arg)
        assert frame_info.filename == self.exception_in_progress.filename, \
            '"line": File name was {:s} now {:s}'.format(
                self.exception_in_progress.filename, frame_info.filename
            )
        assert frame_info.function == self.exception_in_progress.function, \
            '"line": Function was "{:s}" now "{:s}"'.format(
                self.exception_in_progress.function, frame_info.function
            )
        # We have jumped forward in the function to the catch point so line
        # number must be > than where originally raised.
        assert frame_info.lineno > self.exception_in_progress.lineno, \
            '"line": Line number was {:d} now {:d}'.format(
                self.exception_in_progress.lineno, frame_info.lineno
            )
        assert self.exception_in_progress.eventno == self.eventno - 1, \
            '"line": Event number was {:d}, expected {:d}'.format(
                self.exception_in_progress.eventno, self.eventno - 1
            )

    def _process_call_return_exception(self, frame, event, arg, frame_info, func_types):
        assert event in ('call', 'return', 'exception')
        if event == 'call':
            # arg is None
            func_types.add_call(inspect.getargvalues(frame),
                                frame_info.filename,
                                frame_info.lineno)
        elif event == 'return':
            if self.exception_in_progress is not None:
                self._assert_exception_propagates(event, arg, frame_info)
                # Ignore spurious return after exception instead add
                # a propagated exception.
                self._trace('TRACE: "return": adding exception:', self.exception_in_progress)
                func_types.add_exception(
                    self.exception_in_progress.exception_value,
                    self.exception_in_progress.lineno
                )
                self.exception_in_progress = None
            else:
                self._trace('TRACE: "return": adding return value:', arg,
                            frame_info.lineno)
                # arg is a valid return value
                func_types.add_return(arg, frame_info.lineno)
        else:
            assert event == 'exception'
            # arg is a tuple (exception_type, exception_value, traceback)
            # For a stop iteration these values are: (<class 'StopIteration'>, StopIteration(), None)
            exception_type, exception_value, exception_traceback = arg
            self._trace('TRACE:', frame_info.filename, frame_info.function,
                        frame_info.lineno, exception_type, repr(exception_value),
                        repr(exception_traceback))
            # Ignore exceptions caused by co-routines as that is just for flow of control.
            if exception_type not in (StopIteration, GeneratorExit):
                # func_types.add_exception(arg[1], lineno)
                # Fields: filename function lineno exception_value eventno
                assert self.exception_in_progress is None, \
                    'File: {:s}, function: {:s}, exception {:s} type {!r:s} in flight from line {:d}, now see exception event {:s} at {:d}'.format(
                        frame_info.filename,
                        frame_info.function,
                        repr(self.exception_in_progress.exception_value),
                        type(self.exception_in_progress.exception_value),
                        self.exception_in_progress.lineno,
                        repr(exception_value),
                        frame_info.lineno
                    )
                # Fields: filename, function, lineno, exception_value, eventno
                self.exception_in_progress = ExceptionInProgress(
                    frame_info.filename,
                    frame_info.function,
                    frame_info.lineno,
                    exception_value,
                    self.eventno,
                )

    def __call__(self, frame, event, arg):
        """Handle a trace event."""
        self.event_counter.update({event : 1})
        frame_info = inspect.getframeinfo(frame)
        try:
            self._debug(
                'TypeInferencer.__call__(): file: {:s}#{:d} function: {:s} event:{:s} arg: {:s}'.format(
                    frame_info.filename,
                    frame_info.lineno, frame_info.function,
                    repr(event), repr(arg)
                )
            )
        except Exception:
            # This can happen when calling __repr__ on partially constructed objects
            # For example with argparse:
            # AttributeError: 'ArgumentParser' object has no attribute 'prog'
            self._warn(
                'TypeInferencer.__call__(): failed, function: {:s} file: {:s}#{:d}'.format(
                    frame_info.function, frame_info.filename, frame_info.lineno
                )
            )
        self._trace('TRACE: self.exception_in_progress', self.exception_in_progress)
        if self.RE_TEMPORARY_FILE.match(frame_info.filename) \
        or frame_info.function in self.FALSE_FUNCTION_NAMES:
            # Ignore these.
            pass
        else:
            # Only look at 'real' files and functions
            lineno = frame_info.lineno
            if event in ('call', 'return', 'exception'):# and frame_info.filename != '<module>':
                file_path = os.path.abspath(frame_info.filename)
                # TODO: For methods use __qualname__
                #             function_name = frame_info.function
                q_name, bases, signature = self._qualified_name_bases_signature(frame)
                self._debug(
                    'TypeInferencer.__call__(): q_name="{:s}", bases={!r:s})'.format(
                        q_name, bases
                ))
                if q_name != '':
                    try:
                        self._set_bases(file_path, lineno, q_name, bases)
                        func_types = self._get_func_data(file_path, q_name, signature)
                        self._process_call_return_exception(frame, event, arg,
                                                            frame_info, func_types)

                    except Exception as err:
                        self._error(
                            'ERROR: Could not add event "{:s}" Function: {:s} File: {:s}#{:d}'.format(
                                event,
                                frame_info.function,
                                frame_info.filename,
                                frame_info.lineno,
                            )
                        )
                        self._error('ERROR: Type error: {!r:s}, message: {:s}'.format(type(err), str(err)))
                        self._error(''.join(traceback.format_exception(*sys.exc_info())))
                else:
                    self._error('Could not find qualified name in frame: {!r:s}'.format(frame_info))
            elif event == 'line':
                # Deferred decision about the exception reveals that
                # this exception is caught within the function.
                if self.exception_in_progress is not None:
                    self._trace('TRACE: Exception in flight followed by line event', frame_info.filename, frame_info.function, lineno)
                    # The exception has been caught within the function
                    self._assert_exception_caught(event, arg, frame_info)
                    self.exception_in_progress = None
        self.eventno += 1
        self._trace()
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
            # TODO: Remove functions by reading the source and checking
            # RE_FUNCTION matches? Need to take care of decorators.
            if self.GLOBAL_NAMESPACE in self.function_map[file_path]:
                for function_name in self.function_map[file_path][self.GLOBAL_NAMESPACE]:
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

    def insert_docstrings(self, file_path, src_lines=None, style=DOCSTRING_STYLE_DEFAULT):
        """Injects the documentation strings into lines of source code.

        :param file_path: Path to the source file.
        :type file_path: ``str``

        :param src_lines: List of source lines, if None (default) then file_path will be read.
        :type src_lines: ``list([str]),NoneType``

        :param style: Docstring style.
        :type style: ``str``

        :return: ``list([str])`` -- List of source lines with docstrings inserted.
        """
        if src_lines is None:
            with open(file_path) as f:
                src_lines = f.readlines()
        docstring_map = self.docstring_map(file_path, style=style)
        for lineno in reversed(sorted(docstring_map.keys())):
            # print('TRACE:', lineno, src_lines[lineno - 1])
            namespace, _function_name, docstring = docstring_map[lineno]
            prefix = '    '
            if namespace != '':
                prefix *= 1 + len(namespace.split('.'))
            # docstring = '"""{:s}"""'.format(docstring)
            docstring_lines = ['{:s}{:s}\n'.format(prefix, aline) for aline in docstring.split('\n')]
            # With decorators the lineno is the line of the decorator, not the function.
            while RE_DECORATOR.match(src_lines[lineno - 1]):
                lineno += 1
            if RE_FUNCTION.match(src_lines[lineno - 1]) is None:
                # Example: members.sort(key=lambda t: (t[1], t[0]))
                # lambda seen as function
                logging.warning(
                    'insert_docstrings(): file {:s}{:d} source line "{:s}" is not a function'.format(
                        file_path, lineno, src_lines[lineno - 1].rstrip()
                ))
            else:
                while '):' not in src_lines[lineno - 1]:
                    # Arguments written over multiple lines
                    lineno += 1
                src_lines = src_lines[:lineno] + docstring_lines + src_lines[lineno:]
        return src_lines


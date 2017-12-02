'''
Created on 17 Jul 2017

@author: paulross
'''
import collections
import functools
# import inspect
import sys

import re

class TypesExceptionBase(Exception):
    """Base class for exceptions thrown by the types module."""
    pass

class FunctionTypesExceptionNoData(TypesExceptionBase):
    """Exception thrown when no call date has been added to a FunctionTypes object."""
    pass

@functools.total_ordering
class Type(object):
    """This class holds type information extracted from a single object.
    For sequences and so on this will contain a sequence of types.
    """
    # Matches "<class 'int'>" to extract "int"
    # re.ASCII is "<enum RegexFlag>"
    RE_TYPE_STR_MATCH = re.compile(r'<(?:class|enum) \'(.+)\'>')

    def __init__(self, obj, __ids=None):
        """Constructor with an object. __ids is used internally to prevent
        infinite recursion when, for example, a list contains itself.
        This constructor decomposes the object into its types."""
#         print('TRACE: Type.__init__:', type(obj))
        self._type = None
        # __ids is a set of ID values from id(object)
        if __ids is None:
            __ids = set()
        else:
            assert isinstance(__ids, set)
            assert len(__ids) > 0
        if id(obj) in __ids:
            self._type = type(obj)
        else:
            __ids.add(id(obj))
            if isinstance(obj, list):
                # List: insert unique types only, this is ordered by encounter
                # but that is not regarded as significant.
                self._type = []
                for o in obj:
                    t = Type(o, __ids)
                    if t not in self._type:
                        self._type.append(t)
            elif isinstance(obj, tuple):
                # Tuple: make an tuple of all types, we specify tuple as this block also
                # deals with namedtuples and using type(obj) will cause __new__ to fail.
                if hasattr(obj, '_fields'):
                    # Presume a named tuple
#                     print('TRACE: namedtuple detected:', type(obj))
                    self._type = type(obj)(*[self._get_type(o, __ids) for o in obj])
                else:
#                     print('TRACE: tuple detected:', type(obj))
                    self._type = tuple([self._get_type(o, __ids) for o in obj])
            elif isinstance(obj, set):
                # Set: insert unique types only by virtue of type(obj).
                self._type = type(obj)([self._get_type(o, __ids) for o in obj])
            elif isinstance(obj, dict):
                # Dict: make a dict {key_type : set(value_types), ...}
                self._type = {}
                for k, v in obj.items():
                    key = self._get_type(k, __ids)
                    val = self._get_type(v, __ids)
                    try:
                        self._type[key].add(val)
                    except KeyError:
                        self._type[key] = set([val,])
            else:
                # Non-container, just the type() of the object.
                self._type = type(obj)

    def _get_type(self, obj, __ids):
        """Returns the type of the object as a type or Type object."""
        if id(obj) in __ids:
            return type(obj)
        r = Type(obj, __ids)
        __ids.add(id(obj))
        return r

    def __eq__(self, other):
        # other could be a type object not just a Type object
        if hasattr(other, '_type'):
            return self._type == other._type
        return False

    def __lt__(self, other):
        return str(self._type) < str(other._type)

    def __hash__(self):
        return hash(str(self))

    def __str__(self):
        if isinstance(self._type, (list, set, tuple)):
            sl = [Type.str_of_object_type(self._type), '([']
            if isinstance(self._type, (list, set)):
                # List, set, unordered types
                str_list = sorted([str(t) for t in self._type])
            else:
                # Tuple, maintain order of types
                str_list = [str(t) for t in self._type]
            sl.append(', '.join(str_list))
            sl.append('])')
            s = ''.join(sl)
            return s
        elif isinstance(self._type, dict):
            sl = [Type.str_of_object_type(self._type), '({']
            sep = ''
            for k, v in self._type.items():
                sl.append(sep)
                v_str = '[' + ', '.join(sorted([str(_v) for _v in v])) + ']'
                sl.append('{!s:s} : {:s}'.format(k, v_str))
                sep = ', '
            sl.append('})')
            s = ''.join(sl)
            return s
        else:
            return '{!s:s}'.format(self.str_of_type(self._type))

    @classmethod
    def str_of_type(cls, typ):
        m = Type.RE_TYPE_STR_MATCH.match(str(typ))
        if m is not None:
            return m.group(1)
        raise ValueError('Can not parse type: "{:s}"'.format(str(typ)))

    @classmethod
    def str_of_object_type(cls, obj):
        m = Type.RE_TYPE_STR_MATCH.match(str(type(obj)))
        if m is not None:
            return m.group(1)
        raise ValueError('Can not parse object: "{:s}", type {:s}'.format(str(obj), str(type(obj))))

class FunctionTypes:
    """Class that accumulate function call data such as call arguments,
    return values and exceptions raised."""
    # Translate type names into typing parlance
    TYPE_NAME_TRANSLATION = {
        '_io.StringIO' : 'IO[bytes]',
        'NoneType' : 'None',
    }
    SELF = 'self'
    # Alphabetical order
    DOCSTRING_STYLES_AVAILABLE = tuple(sorted(('sphinx', 'google')))
    def __init__(self, signature=None):
        """Constructor, takes no arguments, merely initialises internal state."""
        super().__init__()
        # An inspect.Signature object.
        self.signature = signature
        # TODO: Track a range of line numbers.
        # 'call' must be always the same line number
        # Since functions can not overlap the 'return' shows function bounds
        #
        # OrderedDict of {argument_name : set(types.Type), ...}
        self.arguments = collections.OrderedDict()
        # dict of {line_number : set(types.Type), ...}
        self.return_types = {}
        # TODO: Store the id() of the exception so that we can track how
        # its arc through the stack.
        # Something like {line : (types.Type, set(id...)), ...}
        # On reflection, probably not as id() values might get reused.
        #
        # dict of {line_number : set(types.Type), ...}
        self._exception_types = {}
        # There should be at least one of these, possibly others for generators
        # where yield is a re-entry point.
        # The [0] element will be the lowest value, the others are unordered.
        self.call_line_numbers = []
        # Line numbers:
        # No general sanity check is possible on the ordering of line numbers
        # since property setters and getters can be called in any order.
        # Generators have a call site at declaration and each yield statement
        # Smallest seen line number
        self.min_line_number = sys.maxsize
        # Largest seen line number
        self.max_line_number = 0
        # TODO: Track call/return type pairs so we can use the @overload
        # decorator in the .pyi files.
        self.DOCSTRING_STYLE_FUNCTIONS = {
                'sphinx' : self._docstring_sphinx,
                'google' : self._docstring_google,
        }
        keys = tuple(sorted(self.DOCSTRING_STYLE_FUNCTIONS.keys()))
        assert keys == self.DOCSTRING_STYLES_AVAILABLE

    def __repr__(self):
        """Dump of the internal representation."""
        def _str_list_add_dict(title, d, l):
            sub_l = ['{:s}:'.format(title)]
            if len(d):
                for k, v in d.items():
                    sub_l.append('{!r:s} -> {!r:s}'.format(k, v))
            else:
                sub_l.append('N/A'.format(title))
            l.append(' '.join(sub_l))

        str_l = []
        _str_list_add_dict('Argument types', self.argument_type_strings, str_l)
        _str_list_add_dict('Return types', self.return_type_strings, str_l)
        _str_list_add_dict('Exceptions', self.exception_type_strings, str_l)
        str_l.append('Entry points: {!r:s}'.format(self.call_line_numbers))
        str_l.append('Signature: {!s:s}'.format(self.signature))
        return ', '.join(str_l)

    def _stringify_dict_of_set(self, dofs):
        ret = type(dofs)()
        for k, v in dofs.items():
            ret[k] = set([str(t) for t in v])
        return ret

    @property
    def argument_type_strings(self):
        """A ``collections.OrderedDict`` of
        ``{argument_name : set(types, ...), ...}`` where the types are strings."""
        return self._stringify_dict_of_set(self.arguments)

    @property
    def return_type_strings(self):
        """A dict of ``{line_number : set(types, ...), ...}`` for the return
        values where the return types are strings.
        There should only be one type in the set."""
        return self._stringify_dict_of_set(self.return_types)

    @property
    def exception_type_strings(self):
        """A dict of ``{line_number : set(types, ...), ...}`` for any exceptions
        raised where the return types are strings.
        There should only be one type in the set."""
        return self._stringify_dict_of_set(self._exception_types)

    @property
    def num_entry_points(self):
        """The number of entry points, 1 for normal functions >1 for generators. 0 Something wrong."""
        return len(self.call_line_numbers)

    @property
    def line_decl(self):
        """Line number of the function declaration as an integer."""
        if len(self.call_line_numbers) == 0:
            raise FunctionTypesExceptionNoData()
        return self.call_line_numbers[0]

    @property
    def line_range(self):
        """A pair of line numbers of the span of the function as integers.
        The first is the declaration of the function, the last is the extreme
        return point or exception."""
        if len(self.call_line_numbers) == 0:
            raise FunctionTypesExceptionNoData()
        return self.min_line_number, self.max_line_number

#---- Data acquisition. ----

    def add_call(self, arg_info, file_path, line_number):
        """Adds a function call from the frame."""
        # arg_info is an ArgInfo object which is a named tuple from
        # inspect.getargvalues(frame):
        # ArgInfo(args, varargs, keywords, locals):
        #     args - list of names as strings.
        #     varargs - name entry in the locals for *args or None.
        #     keywords - name entry in the locals for *kwargs or None.
        #     locals - dict of {name : value, ...} of arguments.
        for arg in arg_info.args:
            t = Type(arg_info.locals[arg])
            try:
                self.arguments[arg].add(t)
            except KeyError:
                self.arguments[arg] = set([t])
        if len(self.call_line_numbers) == 0:
            # First call
            self.call_line_numbers.append(line_number)
        else:
            # Add a new entry point for yield statements
            if line_number not in self.call_line_numbers:
                self.call_line_numbers.append(line_number)
            # No general sanity check is possible on the ordering of line numbers
            # since property setters and getters appear as the same
            # function and can be called in any order.
            # Generators have a call site at declaration and each yield
            # statement
        self.min_line_number = min(self.min_line_number, line_number)
        self.max_line_number = max(self.max_line_number, line_number)

    def add_return(self, return_value, line_number):
        """Records a return value at a particular line number.
        If the return_value is None and we have previously seen an exception at
        this line then this is a phantom return value and must be ignored.
        See ``TypeInferencer.__enter__`` for a description of this.
        """
        if return_value is None and line_number in self._exception_types:
            # Ignore phantom return value of None immediately after an exception
            return
        t = Type(return_value)
        try:
            self.return_types[line_number].add(t)
        except KeyError:
            self.return_types[line_number] = set([t])
        # No general sanity check is possible on the ordering of line numbers
        # since property setters and getters can be called in any order.
        # Generators have a call site at declaration and each yield statement
        self.min_line_number = min(self.min_line_number, line_number)
        self.max_line_number = max(self.max_line_number, line_number)

    def add_exception(self, exception, line_number):
        """Add an exception."""
        t = Type(exception)
        try:
            self._exception_types[line_number].add(t)
        except KeyError:
            self._exception_types[line_number] = set([t])
        # No general sanity check is possible on the ordering of line numbers
        # since property setters and getters can be called in any order.
        # Generators have a call site at declaration and each yield statement
        self.min_line_number = min(self.min_line_number, line_number)
        self.max_line_number = max(self.max_line_number, line_number)

#---- END: Data acquisition. ----

    def has_self_first_arg(self):
        """Returns True if 'self' is the first argument i.e. I am a method."""
        arg_types = self.argument_type_strings
        return len(arg_types.keys()) > 0 and list(arg_types.keys())[0] == self.SELF
    
    def types_of_self(self):
        """Returns the set of types (as strings) as seen for the type of 'self'.
        Returns None if 'self' is not the first argument i.e. I am not a method.
        """
        arg_types = self.argument_type_strings
        if len(arg_types.keys()) > 0 and list(arg_types.keys())[0] == self.SELF:
            return arg_types[self.SELF]

    def filtered_arguments(self):
        """A ``collections.OrderedDict`` of
        ``{argument_name : set(types, ...), ...}`` where the types are strings.
        This removes the 'self' argument if it is the first argument."""
        arg_types = self.argument_type_strings
        if len(arg_types.keys()) > 0 and list(arg_types.keys())[0] == self.SELF:
            del arg_types[self.SELF]
        return arg_types

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

    def _type(self, name):
        """Translates a type name if necessary."""
        return self.TYPE_NAME_TRANSLATION.get(name, name)

    def stub_file_str(self):
        """A string suitable for writing to a stub file.
        Example::

            def encodebytes(s: bytes) -> bytes: ...
        """
        sl = ['(']
        arg_str_list = []
        for arg_name in self.arguments:
            if arg_name.startswith(self.SELF):
                arg_str_list.append(self.SELF)
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

    def _insert_doc_marker(self, suffix):
        return '<insert documentation for {:s}>'.format(suffix).replace(' ', '_')

    def _docstring_sphinx(self, include_returns):
        """Returns as string that is the function documentation in the Sphinx
        style. If include_returns is True then the return value documentation
        is included. If false it is excluded, this is used for functions that
        have no return value, __init__() for example.
        
        Example: https://pythonhosted.org/an_example_pypi_project/sphinx.html
        "def public_fn_with_sphinxy_docstring(name, state=None):"
        
        :param include_returns: Whether to include documentation of the return
            value.
        :type include_returns: ``bool``
        """
        str_l = ['"""']
        str_l.append(self._insert_doc_marker('function'))
        for arg, types in self.filtered_arguments().items():
            str_l.append('')
            str_l.append(':param {:s}: {:s}'.format(
                arg,
                self._insert_doc_marker('argument'))
            )
            str_l.append(':type {:s}: ``{:s}``'.format(arg, ', '.join(sorted(types))))
        if include_returns:
            str_l.append('')
            # Returns
            return_types = set()
            for set_returns in self.return_type_strings.values():
                return_types |= set_returns
            # :returns:  int -- the return code.
            str_return_types = ','.join(sorted(return_types))
            if str_return_types == 'NoneType':
                str_l.append(':returns: ``{:s}``'.format(str_return_types))
            else:
                str_l.append(
                    ':returns: ``{:s}`` -- {:s}'.format(
                        str_return_types,
                        self._insert_doc_marker('return values'),
                    )
                )
        # Exceptions, optional
        if len(self._exception_types) > 0:
            str_l.append('')
            excepts = set()
            for e in self.exception_type_strings.values():
                excepts |= e
            str_l.append(':raises: ``{:s}``'.format(', '.join(sorted(excepts))))
        str_l.append('"""')
        return '\n'.join(str_l)
    
    def _docstring_google(self, include_returns):
        """Returns as string that is the function documentation in the Google
        style. If include_returns is True then the return value documentation
        is included. If false it is excluded, this is used for functions that
        have no return value, __init__() for example.
        
        Example: https://pythonhosted.org/an_example_pypi_project/sphinx.html
        "def public_fn_with_googley_docstring(name, state=None):"
        
        :param include_returns: Whether to include documentation of the return
            value.
        :type include_returns: ``bool``
        """
        str_l = ['"""']
        str_l.append(self._insert_doc_marker('function'))
        args_types = self.filtered_arguments()
        if len(args_types) > 0:
            str_l.append('')
            str_l.append('Args:')
            for arg, types in args_types.items():
                str_l.append('    {:s} ({:s}): {:s}'.format(
                    arg,
                    ', '.join(sorted(types)),
                    self._insert_doc_marker('argument'))
                )
        if include_returns:
            str_l.append('')
            str_l.append('Returns:')
            # Returns
            return_types = set()
            for set_returns in self.return_type_strings.values():
                return_types |= set_returns
            # :returns:  int -- the return code.
            str_return_types = ','.join(sorted(return_types))
            if str_return_types == 'NoneType':
                str_l.append('    {:s}'.format(str_return_types))
            else:
                str_l.append(
                    '    {:s}. {:s}'.format(
                        str_return_types,
                        self._insert_doc_marker('return values'),
                    )
                )
        # Exceptions, optional
        if len(self._exception_types) > 0:
            str_l.append('')
            str_l.append('Raises:')
            excepts = set()
            for e in self.exception_type_strings.values():
                excepts |= e
            str_l.append('    {:s}'.format(', '.join(sorted(excepts))))
        str_l.append('"""')
        return '\n'.join(str_l)

    def docstring(self, include_returns, style='sphinx'):
        """Returns a pair (line_number, docstring) for this function. The
        docstring is the __doc__ for the function and the line_number is the
        docstring position (function declaration + 1).
        So to insert into a list of lines called ``src``::

            src[:line_number] + docstring.split('\\n') + src[line_number:]

        style can be: 'sphinx', 'google'."""
#         despatch = {
#             'sphinx' : self._docstring_sphinx,
#             'google' : self._docstring_google,
#         }
#         if style not in despatch:
#             raise ValueError(
#                 'Style {:s} not supported, must be one of {!r:s}'.format(
#                     style,
#                     list(despatch.keys())
#                 )
#             )
#         return self.line_decl, despatch[style](include_returns)
        if style not in self.DOCSTRING_STYLE_FUNCTIONS:
            raise ValueError(
                'Style {:s} not supported, must be one of {!r:s}'.format(
                    style,
                    list(self.DOCSTRING_STYLE_FUNCTIONS.keys())
                )
            )
        return self.line_decl, self.DOCSTRING_STYLE_FUNCTIONS[style](include_returns)

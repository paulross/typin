'''
Created on 17 Jul 2017

@author: paulross
'''
import collections
import functools
import inspect

import re

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
            elif isinstance(obj, (set, tuple)):
                # Set: insert unique types only by virtue of type(obj).
                # Tuple: make an tuple of all types.
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
        return self._type == other._type
    
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
    
# class TypesBase(object):
#     TYPE_NAME_TRANSLATION = {
#         '_io.StringIO' : 'IO[bytes]',
#         'NoneType' : 'None',
#     }
# 
# class ClassBaseTypes(TypesBase):
#     """Holds the __bases__ of a class."""
#     def __init__(self, obj):
#         super().__init__()
#         assert inspect.isclass(obj)
#         self.bases = tuple(Type(o) for o in obj.__class__.__bases__)
#         
#     def __str__(self):
#         return str(tuple([str(t) for t in self.bases]))
#     
#     __repr__ = __str__

class FunctionTypesExceptionBase(Exception):
    pass

class FunctionTypesExceptionNoData(FunctionTypesExceptionBase):
    pass

class FunctionTypes:
    # Translate type names into typing parlance
    TYPE_NAME_TRANSLATION = {
        '_io.StringIO' : 'IO[bytes]',
        'NoneType' : 'None',
    }
    def __init__(self):
        super().__init__()
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
        # where yield is a re-entry point 
        self.call_line_numbers = []
        # Largest seen line number
        self.max_line_number = 0
        # TODO: Track call/return type pairs so we can use the @overload
        # decorator in the .pyi files.
        
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
        return ', '.join(str_l)
    
    def _stringify_dict_of_set(self, dofs):
        ret = type(dofs)()
        for k, v in dofs.items():
            ret[k] = set([str(t) for t in v])
        return ret
        
    @property
    def argument_type_strings(self):
        return self._stringify_dict_of_set(self.arguments)

    @property
    def return_type_strings(self):
        return self._stringify_dict_of_set(self.return_types)

    @property
    def exception_type_strings(self):
        return self._stringify_dict_of_set(self._exception_types)

    @property
    def line_decl(self):
        if len(self.call_line_numbers) == 0:
            raise FunctionTypesExceptionNoData()
        return self.call_line_numbers[0]
        
    @property
    def line_range(self):
        if len(self.call_line_numbers) == 0:
            raise FunctionTypesExceptionNoData()
        return self.call_line_numbers[0], self.max_line_number
    
    def _check_line_number(self, line_number, file_path=''):
        assert len(self.call_line_numbers) > 0
        # Sanity check: Call sites, can increase when using yield statements
        # but never can decrease. Similarly return line numbers and exception
        # line numbers must be greater than the original call site.
        if self.call_line_numbers[0] > line_number:
            raise ValueError('Call site in "{:s}" goes backwards, was {:d} now {:d}'.format(
                file_path, self.call_line_numbers[0], line_number)
            )
        
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
            try:
                self.arguments[arg].add(Type(arg_info.locals[arg]))
            except KeyError:
                self.arguments[arg] = set([Type(arg_info.locals[arg])])
        if len(self.call_line_numbers) == 0:
            # First call
            self.call_line_numbers.append(line_number)
        else:
            # Add a new entry point for yield statements
            if line_number not in self.call_line_numbers:
                self.call_line_numbers.append(line_number)
            # Sanity check: Call sites can increase when using yield statements
            # but never can decrease
            self._check_line_number(line_number, file_path)
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
        self._check_line_number(line_number)
        self.max_line_number = max(self.max_line_number, line_number)
        
    def add_exception(self, exception, line_number):
        t = Type(exception)
        try:
            self._exception_types[line_number].add(t)
        except KeyError:
            self._exception_types[line_number] = set([t])
        self._check_line_number(line_number)
        self.max_line_number = max(self.max_line_number, line_number)
    
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
        """Example::
            def encodebytes(s: bytes) -> bytes: ...
        """
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
    
    def _insert_doc_marker(self, suffix):
        return '<insert documentation for {:s}>'.format(suffix)

    def _docstring_sphinx(self):
        str_l = []
        str_l.append(self._insert_doc_marker('function'))
        arg_types = self.argument_type_strings
        # Arguments, optional
        for arg, types in arg_types.items():
            assert len(types) == 1
            str_l.append(':param {:s}: {:s}'.format(
                arg,
                self._insert_doc_marker('argument'))
            )
            str_l.append(':type {:s}: {:s}'.format(arg, types.pop()))
        # Returns
        return_types = set()
        for set_returns in self.return_type_strings.values():
            return_types |= set_returns
        # :returns:  int -- the return code.
        str_l.append(
            ':returns: {:s} -- {:s}'.format(
                ','.join(sorted(return_types)),
                self._insert_doc_marker('return values'),
            )
        )
        # Exceptions, optional
        if len(self._exception_types) > 0:
            str_l.append(':raises: {:s}'.format(self.exception_type_strings()))
        return '\n'.join(str_l)
    
#     def _docstring_google(self):
#         str_l = []
#         return '\n'.join(str_l)
    
    def docstring(self, style='sphinx'):
        """Returns a pair (line_number, docstring) for this function. The
        docstring is the __doc__ for the function and the line_number is the
        docstring position (function declaration + 1).
        So to insert into ``src``::
            src[:line_number] + docstring + src[line_number:]
            
        style can be 'sphinx' or 'google'."""
        despatch = {
            'sphinx' : self._docstring_sphinx,
#             'google' : self._docstring_google,
        }
        return self.line_decl + 1, despatch[style]()

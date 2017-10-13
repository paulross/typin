'''
Created on 17 Jul 2017

@author: paulross
'''
import collections
import re

class Type(object):
    """This class holds type information extracted from a single object.
    For sequences and so on this will contain a sequence of types.
    """
    # Matches "<class 'int'>" to extract "int"
    RE_TYPE_STR_MATCH = re.compile(r'<class \'(.+)\'>')
    
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
                    t = Type(o)
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
    

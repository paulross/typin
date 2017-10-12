'''
Created on 17 Jul 2017

@author: paulross
'''
import re

class Type(object):
    """This class holds type information extracted from a single object.
    For sequences and so on this will contain a sequence of types.
    """
    # Matches "<class 'int'>" to extract "int"
    RE_TYPE_STR_MATCH = re.compile(r'<class \'(.+)\'>')
    
    def __init__(self, obj, ids=None):
        if ids is None:
            ids = set()
        if id(obj) in ids:
            self.type = type(obj)
        else:
            ids.add(id(obj))
            if isinstance(obj, list):
                self.type = []
                for o in obj:
                    t = Type(o)
                    if t not in self.type:
                        self.type.append(t)
            elif isinstance(obj, (set, tuple)):
                self.type = type(obj)([self._type(o, ids) for o in obj])
            elif isinstance(obj, dict):
                self.type = {self._type(k, ids) : self._type(v, ids) for k, v in obj.items()}
            else:
                self.type = type(obj)

    def _type(self, obj, ids):
        if id(obj) in ids:
            return type(obj)
        r = Type(obj, ids)
        ids.add(id(obj))
        return r

    def __eq__(self, other):
        return self.type == other.type
    
    def __hash__(self):
        return hash(str(self))
    
    def __str__(self):
        if isinstance(self.type, (list, set, tuple)):
            return '{!s:s}([{:s}])'.format(self.type,
                                           ', '.join([str(t) for t in self.type]))
        elif isinstance(self.type, dict):
            s = ', '.join(['{!s:s} : {!s:s}'.format(self.str_of_type(k),
                                                    self.str_of_type(v))
                           for k, v in self.type.items()])
            return '{!s:s}(\{{:s}\})'.format(self.str_of_type(type(self.type)), s)
        else:
            return '{!s:s}'.format(self.str_of_type(self.type))
    
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
    

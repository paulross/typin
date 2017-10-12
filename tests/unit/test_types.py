'''
Created on 17 Jul 2017

@author: paulross
'''

from typin import types

def test_Type_RE_TYPE_STR_MATCH():
    m = types.Type.RE_TYPE_STR_MATCH.match("<class 'str'>")
    assert m is not None
    assert len(m.groups()) == 1
    assert m.group(1) == 'str'

def test_Type_str():
    t = types.Type('')
    assert str(t) == 'str'

def test_Type_int():
    t = types.Type(12)
    assert str(t) == 'int'

def test_Type_float():
    t = types.Type(12.0)
    assert str(t) == 'float'

def test_Type_tuple_uniform():
    t = types.Type((1, 2, 3))
    assert str(t) == 'tuple([int, int, int])'

def test_Type_tuple_mixed():
    t = types.Type(('', 12, 12.0))
    assert str(t) == 'tuple([str, int, float])'

def test_Type_list_uniform():
    t = types.Type([1, 2, 3])
    assert str(t) == 'list([int])'

def test_Type_list_mixed():
    t = types.Type(['', 12, 12.0])
    assert str(t) == 'list([str, int, float])'

def test_Type_list_mixed_repeated():
    t = types.Type(['', 12, 12.0, '', 12, 12.0])
    assert str(t) == 'list([str, int, float])'

def test_Type_set_uniform():
    t = types.Type(set([1, 2, 3]))
    assert str(t) == "<class 'set'>([<class 'int'>])"

def test_Type_set_mixed():
    t = types.Type(set(['', 12]))
    assert str(t) == "<class 'set'>([<class 'str'>, <class 'int'>])" or \
        "<class 'set'>([<class 'int'>, <class 'str'>])"

def test_Type_set_mixed_dupe_numbers():
    t = types.Type(set(['', 12, 12.0]))
    assert str(t) == "<class 'set'>([<class 'str'>, <class 'int'>])" or \
        "<class 'set'>([<class 'int'>, <class 'str'>])"

class Outer:
    class Inner:
        pass

def test_Type_str_of_object_type():
    o = Outer()
    assert types.Type.str_of_object_type(o) \
        == 'tests.unit.test_type.Outer'
    i = Outer.Inner()
    assert types.Type.str_of_object_type(i) \
        == 'tests.unit.test_type.Outer.Inner'

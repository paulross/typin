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

def test_Type_str_equal():
    assert types.Type('') == types.Type('Hi there')

def test_Type_bytes():
    t = types.Type(b'')
    assert str(t) == 'bytes'

def test_Type_bytes_equal():
    assert types.Type(b'') == types.Type(b'Hi there')

def test_Type_int():
    t = types.Type(12)
    assert str(t) == 'int'

def test_Type_int_equal():
    assert types.Type(1) == types.Type(2)

def test_Type_float():
    t = types.Type(12.0)
    assert str(t) == 'float'

def test_Type_float_equal():
    assert types.Type(1.0) == types.Type(2.0)

def test_Type_tuple_uniform():
    t = types.Type((1, 2, 3))
    assert str(t) == 'tuple([int, int, int])'

def test_Type_tuple_mixed():
    t = types.Type(('', 12, 12.0))
    assert str(t) == 'tuple([str, int, float])'

def test_Type_tuple_equal():
    t0 = types.Type(('', 12, 12.0))
    t1 = types.Type(('Hi there', 1, 4.0))
    assert t1 == t0

def test_Type_list_empty():
    t = types.Type([])
    assert str(t) == 'list([])'

def test_Type_list_uniform():
    t = types.Type([1, 2, 3])
    assert str(t) == 'list([int])'

def test_Type_list_mixed():
    t = types.Type(['', 12, 12.0])
    assert str(t) == 'list([float, int, str])'

def test_Type_list_mixed_repeated():
    t = types.Type(['', 12, 12.0, '', 12, 12.0])
    assert str(t) == 'list([float, int, str])'

def test_Type_list_recursive():
    l = []
    l.append(l)
#     print(l)
    t = types.Type(l)
    assert str(t) == 'list([list])'

def test_Type_list_recursive_mixed():
    l = ['']
    l.append(l)
#     print(l)
    t = types.Type(l)
    assert str(t) == 'list([list, str])'

def test_Type_set_uniform():
    t = types.Type(set([1, 2, 3]))
    assert str(t) == 'set([int])'

def test_Type_set_mixed():
    t = types.Type(set(['', 12]))
    assert str(t) == 'set([int, str])'

def test_Type_set_mixed_numbers_diff_values():
    t = types.Type(set([12.0, 14]))
    assert str(t) == 'set([float, int])'

def test_Type_set_mixed_numbers_same_values():
    t = types.Type(set([12.0, 12]))
    assert str(t) in ('set([float])', 'set([int])')

def test_Type_set_mixed_dupe_numbers():
    t = types.Type(set(['', 12, 12.0]))
    assert str(t) in (
        'set([int, str])',
        'set([float, str])',
    )

def test_Type_set_mixed_dupe_numbers_diff_values():
    t = types.Type(set(['', 12, 14.0]))
    assert str(t) == 'set([float, int, str])'

def test_Type_tuple_of_tuple_uniform():
    t = types.Type(
        (
            (1, 2,),
            (3, 4,)
        )
    )
    assert str(t) == 'tuple([tuple([int, int]), tuple([int, int])])'

def test_Type_dict_str_int():
    t = types.Type(
        {
            'A' : 1,
         }
    )
    assert str(t) == 'dict({str : [int]})'

def test_Type_dict_str_int_multiple():
    t = types.Type(
        {
            'A' : 1,
            'B' : 2,
         }
    )
    assert str(t) == 'dict({str : [int]})'
  
def test_Type_dict_str_number():
    t = types.Type(
        {
            'A' : 1,
            'B' : 1.0,
         }
    )
    assert str(t) == 'dict({str : [float, int]})'

class Outer:
    class Inner:
        pass

def test_Type_str_of_object_type_Outer():
    o = Outer()
    assert types.Type.str_of_object_type(o) == 'tests.unit.test_types.Outer'

def test_Type_str_Outer():
    o = Outer()
    t = types.Type(o)
    assert str(t) == 'tests.unit.test_types.Outer'

def test_Type_str_of_object_type_Inner():
    i = Outer.Inner()
    assert types.Type.str_of_object_type(i) == 'tests.unit.test_types.Outer.Inner'

def test_Type_str_Inner():
    i = Outer.Inner()
    t = types.Type(i)
    assert str(t) == 'tests.unit.test_types.Outer.Inner'

def test_types__package__():
    assert types.__package__ == 'typin'

def test_Type__module__():
    assert types.Type.__module__ == 'typin.types'

def test_Type__package__():
    assert not hasattr(types.Type, '__package__')

def test_Type_Outer__module__():
    assert Outer.__module__ == 'tests.unit.test_types'

def test_Type_Outer__package__():
    assert not hasattr(Outer, '__package__')

def test_Type_Inner__module__():
    assert Outer.Inner.__module__ == 'tests.unit.test_types'

def test_Type_Inner__package__():
    assert not hasattr(Outer.Inner, '__package__')

'''
Created on 13 Oct 2017

@author: paulross
'''
import pytest

from typin import str_id_cache

def test_str_id_cache_id():
    id_cache = str_id_cache.StringIdCache()
    assert id_cache.id('Zero') == 0
    assert id_cache.id('One') == 1
    assert id_cache.id('Two') == 2

def test_str_id_cache_id_present():
    id_cache = str_id_cache.StringIdCache()
    id_cache.id('Zero')
    id_cache.id('One')
    id_cache.id('Two')
    assert id_cache.id('Zero') == 0
    assert id_cache.id('One') == 1
    assert id_cache.id('Two') == 2

def test_str_id_cache_name():
    id_cache = str_id_cache.StringIdCache()
    id_cache.id('Zero')
    id_cache.id('One')
    id_cache.id('Two')
    assert id_cache.name(0) == 'Zero'
    assert id_cache.name(1) == 'One'
    assert id_cache.name(2) == 'Two'

def test_str_id_cache_name_raises():
    id_cache = str_id_cache.StringIdCache()
    with pytest.raises(KeyError): 
        id_cache.name(0)

def test_str_id_cache_sorted_ids():
    id_cache = str_id_cache.StringIdCache()
    id_cache.id('Zero')
    id_cache.id('One')
    id_cache.id('Two')
    assert id_cache.sorted_ids() == [1, 2, 0]

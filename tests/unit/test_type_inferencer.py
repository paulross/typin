'''
Created on 22 Jun 2017

@author: paulross
'''
import pprint
import sys

import pytest

from typin import type_inferencer

def test_creation():
    t = type_inferencer.TypeInferencer()
    assert t is not None


def func_single_arg(arg):
    # Do some stuff
    pass


def test_single_function():
    with type_inferencer.TypeInferencer() as ti:
        func_single_arg('string')
#     print()
#     pprint.pprint(ti._fn_map)


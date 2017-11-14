#!/usr/local/bin/python
# -*- coding: utf-8 -*-
import collections
import os
import pprint
import sys
 
import argparse

import example_import

class BaseClass:
    """Example base class to explore inheritance."""
    def __init__(self):
        """Constructor."""
        pass

class ExampleClass(BaseClass):
    """An example class with a couple of methods that we exercise."""
    def __init__(self, first_name, last_name):
        """Constructor.
        
        :param first_name: Given name.
        :type first_name: ``str``
        
        :param last_name: Family name.
        :type last_name: ``str``
        """
        super(ExampleClass, self).__init__()
        self.first_name = first_name
        self.last_name = last_name

    def name(self):
        """Returns the last name, first name.
        
        :returns: ``str`` -- Formatted name.
        """
        ret = '{:s}, {:s}'.format(self.last_name, self.first_name)
        return ret

class OuterClass:
    """Example outer class to explore inner/outer issues."""
    class InnerClass:
        """Example inner class to explore inner/outer issues."""
        def __init__(self, value):
            """Constructor.
            
            :param value: The given value.
            :type value: ``str``
            """
            self._value = value
            
        def value(self):
            """Returns the value.
            
            :returns: ``str`` -- The value.
            """
            return self._value
            
    def __init__(self, value):
        """Constructor.
        
        :param value: The given value.
        :type value: ``str``
        """
        self.outer_inner = OuterClass.InnerClass(value)

    def value(self):
        """Returns the value.
        
        :returns: ``str`` -- The value.
        """
        return self.outer_inner.value()

class InnerClass:
    """Same named inner class to explore inner/outer namespaces."""

    def __init__(self, value):
        """Constructor.
        
        :param value: The given value.
        :type value: ``bytes``
        """
        self._value = value
        
    def value(self):
        """Returns the value.
        
        :returns: ``bytes`` -- The value.
        """
        return self._value
    
def example_function(x):
    """Example function.
    
    :param x: Example argument.
    :type x: ``int``
    
    :returns: ``int`` -- Doubles the argument.
    """
    return 2 * x

MyNT = collections.namedtuple('MyNT', 'a b c')

def main():
    """Main entry point.
    
    :returns: ``int`` -- status code, 0 is success.
    """
#     print('example.py: sys.argv:', sys.argv)
    parser = argparse.ArgumentParser(description='Example CLI',
                            formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(dest="args", nargs='+', help="Arguments to execute.")
    cli_args = parser.parse_args()
#     print('example.py: cli_args:', cli_args)
    _val = example_function(12)
    jane_doe = ExampleClass('Jane', 'Doe')
    jane_doe.name()
    outer = OuterClass('Hi there')
    outer.value()
    inner = InnerClass(b'Hi there')
    inner.value()
    nt = MyNT(1, 'B', b'C')
    nt.a
    # example_import
    _val = example_import.example_function(12)
    jane_doe = example_import.ExampleClass('Jane', 'Doe')
    jane_doe.name()
    outer = example_import.OuterClass('Hi there')
    outer.value()
    inner = example_import.InnerClass(b'Hi there')
    inner.value()
    
    return 0
 
if __name__ == "__main__":
#     trace_fn = sys.gettrace()
#     sys.settrace(None)
#     print(' globals() '.center(75, '-'))
#     pprint.pprint(globals())
#     print(' locals() '.center(75, '-'))
#     pprint.pprint(locals())
#     sys.settrace(trace_fn)

#     main()
    exit(main())

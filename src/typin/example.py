#!/usr/local/bin/python
# -*- coding: utf-8 -*-
import os
import pprint
import sys
 
import argparse

class BaseClass:
    def __init__(self):
        pass

class ExampleClass(BaseClass):
    """An example class with a couple of methods that we exercise."""
    def __init__(self, first_name, last_name):
        super(ExampleClass, self).__init__()
        self.first_name = first_name
        self.last_name = last_name

    def name(self):
        ret = '{:s}, {:s}'.format(self.last_name, self.first_name)
        return ret

def example_function(x):
    return 2 * x

def main():
#     print('example.py: sys.argv:', sys.argv)
    parser = argparse.ArgumentParser(description='Example CLI',
                            formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(dest="args", nargs='+', help="Arguments to execute.")
    cli_args = parser.parse_args()
#     print('example.py: cli_args:', cli_args)
    _val = example_function(12)
    jane_doe = ExampleClass('Jane', 'Doe')
    jane_doe.name()
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

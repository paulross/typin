#!/usr/local/bin/python
# -*- coding: utf-8 -*-
import os
import pprint
import sys
 
import argparse
 
def example_function(x):
    return 2*x

def main():
    print('example.py: sys.argv:', sys.argv)
    parser = argparse.ArgumentParser(description='Example CLI',
                            formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(dest="args", nargs='+', help="Arguments to execute.")
    cli_args = parser.parse_args()
    print('example.py: cli_args:', cli_args)
    val = example_function(12)
    print(val)
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

import sys

src = """#!/usr/local/bin/python
# -*- coding: utf-8 -*-

class BaseClass:
    def __init__(self):
        pass

class ExampleClass(BaseClass):
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
    _val = example_function(12)
    jane_doe = ExampleClass('Jane', 'Doe')
    jane_doe.name()
    return 0
 
if __name__ == "__main__":
    main()
"""
def main():
    filename = sys.argv[1]
    with open(filename) as f:
        src = f.read()
        print('exec_cli.compile_and_exec() read {:d} lines'.format(src.count('\n')))
        code = compile(src, filename, 'exec')
        exec(code, globals())#, locals())
    return 0
    
if __name__ == '__main__':
    sys.exit(main())

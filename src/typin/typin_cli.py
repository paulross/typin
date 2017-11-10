# -*- coding: utf-8 -*-
"""Main module."""
import argparse
import logging
import os
import sys

from typin import type_inferencer

def compile_and_exec(root_path, stubs_dir, filename, *args, **kwargs):
    sys.argv = [filename] + list(args)
    logging.debug('typein_cli.compile_and_exec({:s})'.format(filename))
    with open(filename) as f_obj:
        src = f_obj.read()
        logging.debug('typein_cli.compile_and_exec() read {:d} lines'.format(src.count('\n')))
        code = compile(src, filename, 'exec')
        with type_inferencer.TypeInferencer() as ti:
#             exec(code, globals())
            try:
                exec(code, globals())#, locals())
            except SystemExit:
                # Trap CLI code that calls exit() or sys.exit()
                pass
#         print('ti.pretty_format()')
#         print(ti.pretty_format())
        print(' ti.pretty_format() '.center(75, '-'))
        file_paths = ti.file_paths_filtered(root_path, relative=True)
        for key, file_path in file_paths:
            print(os.path.join(stubs_dir, file_path))
            print(ti.pretty_format(key))
        print(' ti.dump() '.center(75, '-'))
        ti.dump()

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

def test():
    with type_inferencer.TypeInferencer() as ti:
        _val = example_function(12)
        jane_doe = ExampleClass('Jane', 'Doe')
        jane_doe.name()
    file_paths = ti.file_paths_filtered()
    print(' typin_cli.test() ti.pretty_format() '.center(75, '-'))
    for file_path in file_paths:
        print(file_path)
        print(ti.pretty_format(file_path))
    print(' typin_cli.test() ti.dump() '.center(75, '-'))
    ti.dump()

def main():
    """Command line version of typin which executes arbitrary Python code and
    for each function records all the types called, returned and raised.
    For example::

        python typin_cli.py --stubs=stubs example.py foo bar baz

    This will execute ``example.py`` with the options ``foo bar baz`` under the
    control of typin and write all the type annotations to the stubs/ directory.
    """
    program_version = "v%s" % '0.1.0'
    program_shortdesc = 'typin_cli - Infer types of Python functions.'
    program_license = """%s
  Created by Paul Ross on 2017-10-25. Copyright 2017. All rights reserved.
  Version: %s Licensed under MIT License
USAGE
""" % (program_shortdesc, program_version)
    parser = argparse.ArgumentParser(description=program_license,
                            formatter_class=argparse.RawDescriptionHelpFormatter)
#     parser.add_argument("-c", action="store_true", dest="plot_conditional", default=False,
#                       help="Add conditionally included files to the plots. [default: %(default)s]")
#     parser.add_argument("-d", "--dump", action="append", dest="dump", default=[],
#                       help="""Dump output, additive. Can be:
# C - Conditional compilation graph.
# F - File names encountered and their count.
# I - Include graph.
# M - Macro environment.
# T - Token count.
# R - Macro dependencies as an input to DOT.
# [default: %(default)s]""")
#     parser.add_argument("-g", "--glob", action='append', default=[],
#             help="Pattern match to use when processing directories. [default: %(default)s] i.e. every file.")
#     parser.add_argument("--heap", action="store_true", dest="heap", default=False,
#                       help="Profile memory usage. [default: %(default)s]")
#     parser.add_argument("-k", "--keep-going", action="store_true",
#                          dest="keep_going", default=False,
#                          help="Keep going. [default: %(default)s]")
    parser.add_argument(
            "-l", "--loglevel",
            type=int,
            dest="loglevel",
            default=30,
            help="Log Level (debug=10, info=20, warning=30, error=40, critical=50)" \
            " [default: %(default)s]"
        )
#     parser.add_argument("-o", "--output",
#                          type=str,
#                          dest="output",
#                          default="out",
#                          help="Output directory. [default: %(default)s]")
#     parser.add_argument("-p", action="store_true", dest="ignore_pragma", default=False,
#                       help="Ignore pragma statements. [default: %(default)s]")
#     parser.add_argument("-r", "--recursive", action="store_true", dest="recursive",
#                          default=False,
#                       help="Recursively process directories. [default: %(default)s]")
#     parser.add_argument("-t", "--dot", action="store_true", dest="include_dot",
#                          default=False,
#                       help="""Write an DOT include dependency table and execute DOT
# on it to create a SVG file. [default: %(default)s]""")
#     parser.add_argument("-G", action="store_true", dest="gcc_extensions",
#                          default=False,
#                       help="""Support GCC extensions. Currently only #include_next. [default: %(default)s]""")
    parser.add_argument("-s", "--stubs",
                         type=str,
                         dest="stubs",
                         default="stubs",
                         help="Directory to write stubs files. [default: %(default)s]")
    parser.add_argument("-r", "--root",
                         type=str,
                         dest="root",
                         default=".",
                         help="Root path of the Python packages to generate stub files for. [default: %(default)s]")
    parser.add_argument(dest="args", nargs='+',
                        help="Arguments to execute, the first argument is the Python script to"
                        " call. The rest of the arguments are passed to that script.")
    cli_args = parser.parse_args()
    logFormat = '%(asctime)s %(levelname)-8s %(message)s'
    logging.basicConfig(level=cli_args.loglevel,
                        format=logFormat,
                        # datefmt='%y-%m-%d % %H:%M:%S',
                        stream=sys.stdout)
#     print('sys.argv:', sys.argv)
#     sys.argv = cli_args.args[1:]
#     print('sys.argv:', sys.argv)
#     print('cli_args', cli_args)
    filename = cli_args.args[0]
    root_path = os.path.abspath(os.path.normpath(cli_args.root))
    test()
    compile_and_exec(root_path, cli_args.stubs, filename, *cli_args.args[1:])
    return 0

if __name__ == '__main__':
    sys.exit(main())

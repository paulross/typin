# -*- coding: utf-8 -*-
"""Main module."""
import argparse
import logging
import sys

from typin import type_inferencer
    
def main():
    program_version = "v%s" % '0.1.1'
    program_shortdesc = 'typin.py - Infer types.'
    program_license = """%s
  Created by Paul Ross on 2017-10-25.
  Copyright 2017. All rights reserved.
  Version: %s
  Licensed under MIT
USAGE
""" % (program_shortdesc, program_version)
    parser = argparse.ArgumentParser(description=program_license,
                            formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-c", action="store_true", dest="plot_conditional", default=False,
                      help="Add conditionally included files to the plots. [default: %(default)s]")
    parser.add_argument("-d", "--dump", action="append", dest="dump", default=[],
                      help="""Dump output, additive. Can be:
C - Conditional compilation graph.
F - File names encountered and their count.
I - Include graph.
M - Macro environment.
T - Token count.
R - Macro dependencies as an input to DOT.
[default: %(default)s]""")
    parser.add_argument("-g", "--glob", action='append', default=[],
            help="Pattern match to use when processing directories. [default: %(default)s] i.e. every file.")
    parser.add_argument("--heap", action="store_true", dest="heap", default=False,
                      help="Profile memory usage. [default: %(default)s]")
    parser.add_argument("-k", "--keep-going", action="store_true",
                         dest="keep_going", default=False,
                         help="Keep going. [default: %(default)s]")
    parser.add_argument(
            "-l", "--loglevel",
            type=int,
            dest="loglevel",
            default=30,
            help="Log Level (debug=10, info=20, warning=30, error=40, critical=50)" \
            " [default: %(default)s]"
        )
    parser.add_argument("-o", "--output",
                         type=str,
                         dest="output",
                         default="out",
                         help="Output directory. [default: %(default)s]")
    parser.add_argument("-p", action="store_true", dest="ignore_pragma", default=False,
                      help="Ignore pragma statements. [default: %(default)s]")
    parser.add_argument("-r", "--recursive", action="store_true", dest="recursive",
                         default=False,
                      help="Recursively process directories. [default: %(default)s]")
    parser.add_argument("-t", "--dot", action="store_true", dest="include_dot",
                         default=False,
                      help="""Write an DOT include dependency table and execute DOT
on it to create a SVG file. [default: %(default)s]""")
    parser.add_argument("-G", action="store_true", dest="gcc_extensions",
                         default=False,
                      help="""Support GCC extensions. Currently only #include_next. [default: %(default)s]""")
    parser.add_argument(dest="stubs", nargs=1, help="Path to write typeshed stubs.")
    args = parser.parse_args()
    logFormat = '%(asctime)s %(levelname)-8s %(message)s'
    logging.basicConfig(level=args.loglevel,
                        format=logFormat,
                        # datefmt='%y-%m-%d % %H:%M:%S',
                        stream=sys.stdout)
    with type_inferencer.TypeInferencer() as ti:
        pass
    return 0

if __name__ == '__main__':
    exit(main())

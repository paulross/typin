"""
Created on 3 Jul 2017

@author: paulross
"""
import inspect
import sys

import research_import

def profile(frame, event, arg):
    frame_info = inspect.getframeinfo(frame)
#     f = frame
#     while f:
# #         print(f)
#         frame_depth += 1
#         # Hmm docs say f_back should be None when exhausted
#         if frame.f_back == f:
#             break
#         f = frame.f_back

#     frame_depth = len(inspect.getouterframes(frame))
#     print('    ' * frame_depth, frame_info, event, arg, inspect.getargvalues(frame))

#     print(frame_info, event, arg)
#     if event != 'line':
#         print('non-line', frame_info.filename, frame_info.lineno, frame_info.function, event, repr(arg))
    print('Event:', frame_info.filename, frame_info.lineno, frame_info.function, event, repr(arg))
#     print(frame, event, arg)
    return profile

def func_a(arg):
    func_b('calling b()')
    return 'A'

def func_b(arg):
    try:
        func_c('calling c()')
    except ValueError:
        pass
    return 'B'

def func_c(arg):
    raise ValueError()
    return 'C'

def exception_calls_exception_propogates():
    exception_propogates()

def exception_propogates():
    raise ValueError('Error message')
    return 'OK'

def exception_caught():
    try:
        raise ValueError('Bad value')
        # Code here
        # More code here
    except ValueError as _err:
        pass
    try:
        raise KeyError('Bad key.')
        # Code here
        # More code here
    except KeyError as _err:
        pass
    return 'OK'

def func_that_catches():
    try:
        func_no_catch()
    except ValueError:
        pass

def func_no_catch():
    func_that_raises()

def func_that_raises():
    raise ValueError('Error message')

def func_that_catches_import():
    try:
        research_import.func_no_catch()
    except ValueError:
        pass

def main():
    try:
        sys.settrace(profile)
#         sys.setprofile(profile)

#         print(' exception_propogates() '.center(75, '-'))
#         try:
#             exception_propogates()
#         except ValueError:
#             pass
#         a = 1 + 2
#         b = a + 4
#         print(' exception_caught() '.center(75, '-'))
#         exception_caught()
#         print(' exception_calls_exception_propogates() '.center(75, '-'))
#         try:
#             exception_calls_exception_propogates()
#         except ValueError:
#             pass
    
        func_that_catches()
#         func_that_catches_import()
    finally:
        sys.settrace(None)
#         sys.setprofile(None)

if __name__ == '__main__':
#     print('HI')
    main()

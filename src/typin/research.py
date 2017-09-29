"""
Created on 3 Jul 2017

@author: paulross
"""
import inspect
import sys

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
    if event != 'line':
        print(frame_info.filename, frame_info.lineno, frame_info.function, event, repr(arg))
#     print(frame, event, arg)
    return profile

def a(arg):
    b('calling b()')
    return 'A'

def b(arg):
    try:
        c('calling c()')
    except ValueError:
        pass
    return 'B'

def c(arg):
    raise ValueError()
    return 'C'



def main():
    try:
#         sys.settrace(profile)
        sys.setprofile(profile)
        a('calling a')
    finally:
#         sys.settrace(None)
        sys.setprofile(None)

if __name__ == '__main__':
    print('HI')
    main()

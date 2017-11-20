Various Research notes
======================================

Tracing functions
--------------------

This applies to both 2.7 and 3.6.

`sys.setprofile()` only sees call and return. If an exception is raised the function appears to return None.
`sys.setprofile()` can return None as the return value is ignored.

`sys.settrace()` is more fine grained and gets exception and line events as well.
`sys.settrace()` can return itself, None or some other function and this will be respected.

Both are thread specific so it doesn't make much sense to use these in a multithreaded environment.

Tracing Exceptions
^^^^^^^^^^^^^^^^^^

If we have this code::

    def a(arg):             # Line 29
        b('calling b()')    # Line 30
        return 'A'          # Line 31

    def b(arg):                 # Line 33
        try:
            c('calling c()')    # Line 35
        except ValueError:
            pass
        return 'B'              # Line 38

    def c(arg):                 # Line 40
        raise ValueError()      # Line 41
        return 'C'


`sys.settrace()` sees the exception::

    /Users/paulross/Documents/workspace/typin/src/typin/research.py 29 a call None
    /Users/paulross/Documents/workspace/typin/src/typin/research.py 33 b call None
    /Users/paulross/Documents/workspace/typin/src/typin/research.py 40 c call None
    # c() raises. We can see this as an exception event is followed by a return None with the same lineno.
    # Return None on its own is not enough as that might happen in the normal course of events.
    /Users/paulross/Documents/workspace/typin/src/typin/research.py 41 c exception (<class 'ValueError'>, ValueError(), <traceback object at 0x102365c08>)
    /Users/paulross/Documents/workspace/typin/src/typin/research.py 41 c return None
    # b() reports the exception at the point that the call to c() is made.
    # b() handles the exception, this can be detected by the exception and return events being on different lines.
    /Users/paulross/Documents/workspace/typin/src/typin/research.py 35 b exception (<class 'ValueError'>, ValueError(), <traceback object at 0x102365c48>)
    /Users/paulross/Documents/workspace/typin/src/typin/research.py 38 b return 'B'
    /Users/paulross/Documents/workspace/typin/src/typin/research.py 31 a return 'A'

`sys.setprofile()` does not see the exception::

    /Users/paulross/Documents/workspace/typin/src/typin/research.py 29 a call None
    /Users/paulross/Documents/workspace/typin/src/typin/research.py 33 b call None
    /Users/paulross/Documents/workspace/typin/src/typin/research.py 40 c call None
    /Users/paulross/Documents/workspace/typin/src/typin/research.py 41 c return None
    /Users/paulross/Documents/workspace/typin/src/typin/research.py 38 b return 'B'
    /Users/paulross/Documents/workspace/typin/src/typin/research.py 31 a return 'A'
    /Users/paulross/Documents/workspace/typin/src/typin/research.py 53 main c_call <built-in function setprofile>


I think at this stage that we should ignore exception specifications as static typing does not accomodate them
interesting though they are.
So we use `sys.setprofile()` for now.

2017-07-22
----------

We neeed to use `sys.settrace()` because if the function ever raises then `sys.setprofile()` will
only see it returning None which it might never actually do (implicitly or explicitly).
So we would then record any function that raises as possibly returning None.
With `sys.settrace` we can eliminate the false returns None by identifying, and ignoring, it as above.

2017-11-16 and 18
-----------------

Raising and catching exceptions.

Given this code:

# This function is defined on line 45 
def exception_propogates(): # Line 45
    raise ValueError('Error message') # Line 46
    return 'OK'

# This function is defined on line 50 
def exception_caught(): # line 50
    try:
        raise ValueError('Bad value') # line 52
    except ValueError as _err: # line 53
        pass
    try:
        raise KeyError('Bad key.') # line 56
    except KeyError as _err: # line 57
        pass
    return 'OK' # line 59

try:
    exception_propogates()
except ValueError:
    pass
exception_caught()

We get:

Event: research.py 45 exception_propogates call None
Event: research.py 46 exception_propogates line None
Event: research.py 46 exception_propogates exception (<class 'ValueError'>, ValueError('Error message',), <traceback object at 0x101031108>)
Event: research.py 46 exception_propogates return None

And:

Event: research.py 49 exception_caught call None
Event: research.py 50 exception_caught line None
Event: research.py 51 exception_caught line None
Event: research.py 51 exception_caught exception (<class 'ValueError'>, ValueError('Bad value',), <traceback object at 0x101a31188>)
Event: research.py 54 exception_caught line None
Event: research.py 55 exception_caught line None
Event: research.py 56 exception_caught line None
Event: research.py 57 exception_caught line None
Event: research.py 57 exception_caught exception (<class 'KeyError'>, KeyError('Bad key.',), <traceback object at 0x101a310c8>)
Event: research.py 60 exception_caught line None
Event: research.py 61 exception_caught line None
Event: research.py 62 exception_caught line None
Event: research.py 62 exception_caught return 'OK'

So exception propagation can be detected by the appearance of a return None at
the same line number as the exception. 

Caught exceptions have a line event following the exception where the line
number is greater than that of the exception.

So when we see an exception event we need to defer judgement and wait until the
next event to decide if it is propagated or not.

Exception propagates out of function:

Event: research.py 46 exception_propogates exception (<class 'ValueError'>, ValueError('Error message',), <traceback object at 0x101031108>)
Event: research.py 46 exception_propogates return None

Exception does not propagate out of function:

Event: research.py 51 exception_caught exception (<class 'ValueError'>, ValueError('Bad value',), <traceback object at 0x101a31188>)
Event: research.py 54 exception_caught line None

So if the event following the exception is the same line number,
event == 'return' and arg (return value) is None then ignore the return
value and record the exception.

If the next event is event == line event at a line greater than the Exception
event then the exception has been caught internally.

In both cases the event following the exception must have the same file and
function and the arg must be None.

2017-11-17
----------

sys.settrace() and sys.setprofile():

sys.settrace() creates 'call', 'line', 'return', 'exception' events.
sys.setprofile() creates 'call', 'c_call', 'return', 'c_return', 'exception' events.

Both sys.settrace() and sys.setprofile() can be set to the same function but
then you get duplicates:

Event: research.py 30 func_a call None
Event: research.py 30 func_a call None
Event: research.py 31 func_a line None
Event: research.py 34 func_b call None
Event: research.py 34 func_b call None
Event: research.py 35 func_b line None
Event: research.py 36 func_b line None
Event: research.py 41 func_c call None
Event: research.py 41 func_c call None
Event: research.py 42 func_c line None
Event: research.py 42 func_c exception (<class 'ValueError'>, ValueError(), <traceback object at 0x1022150c8>)
Event: research.py 42 func_c return None
Event: research.py 42 func_c return None


2017-11-20
----------

Revisiting order of events with exceptions:

(typin_00) Pauls-MacBook-Pro-2:typin paulross$ python research.py 
Event: research.py 81 func_that_catches_import call None
Event: research.py 82 func_that_catches_import line None
Event: research.py 83 func_that_catches_import line None
Event: /Users/paulross/Documents/workspace/typin/src/typin/research_import.py 5 func_no_catch call None
Event: /Users/paulross/Documents/workspace/typin/src/typin/research_import.py 6 func_no_catch line None
Event: /Users/paulross/Documents/workspace/typin/src/typin/research_import.py 2 func_that_raises call None
Event: /Users/paulross/Documents/workspace/typin/src/typin/research_import.py 3 func_that_raises line None
Event: /Users/paulross/Documents/workspace/typin/src/typin/research_import.py 3 func_that_raises exception (<class 'ValueError'>, ValueError('Error message',), <traceback object at 0x102333348>)
Event: /Users/paulross/Documents/workspace/typin/src/typin/research_import.py 3 func_that_raises return None
Event: /Users/paulross/Documents/workspace/typin/src/typin/research_import.py 6 func_no_catch exception (<class 'ValueError'>, ValueError('Error message',), <traceback object at 0x1023332c8>)
Event: /Users/paulross/Documents/workspace/typin/src/typin/research_import.py 6 func_no_catch return None
Event: research.py 83 func_that_catches_import exception (<class 'ValueError'>, ValueError('Error message',), <traceback object at 0x1023333c8>)
Event: research.py 84 func_that_catches_import line None
Event: research.py 85 func_that_catches_import line None
Event: research.py 85 func_that_catches_import return None
(typin_00) Pauls-MacBook-Pro-2:typin paulross$ 

Simplifying file names:

(typin_00) Pauls-MacBook-Pro-2:typin paulross$ python research.py 
Event: research.py 81 func_that_catches_import call None
Event: research.py 82 func_that_catches_import line None
Event: research.py 83 func_that_catches_import line None
Event: research_import.py 5 func_no_catch call None
Event: research_import.py 6 func_no_catch line None
Event: research_import.py 2 func_that_raises call None
Event: research_import.py 3 func_that_raises line None
Event: research_import.py 3 func_that_raises exception (<class 'ValueError'>, ValueError('Error message',), <traceback object at 0x102333348>)
Event: research_import.py 3 func_that_raises return None
Event: research_import.py 6 func_no_catch exception (<class 'ValueError'>, ValueError('Error message',), <traceback object at 0x1023332c8>)
Event: research_import.py 6 func_no_catch return None
Event: research.py 83 func_that_catches_import exception (<class 'ValueError'>, ValueError('Error message',), <traceback object at 0x1023333c8>)
Event: research.py 84 func_that_catches_import line None
Event: research.py 85 func_that_catches_import line None
Event: research.py 85 func_that_catches_import return None
(typin_00) Pauls-MacBook-Pro-2:typin paulross$ 

Exception raised, not caught:

Event: research_import.py 3 func_that_raises exception (<class 'ValueError'>, ValueError('Error message',), <traceback object at 0x102333348>)
Event: research_import.py 3 func_that_raises return None

self.exception_in_progress is created with:

filename:           research_import.py
function:           func_that_raises
lineno:             3
exception_value:    ValueError('Error message',)
eventno:            X

Next event has same filename, function, lineno, returning None with event X+1
and this means the exception is propogated. So add the exception to the
func_types.add_exception and set self.exception_in_progress to None. 

Exception propogated:
Event: research_import.py 6 func_no_catch exception (<class 'ValueError'>, ValueError('Error message',), <traceback object at 0x1023332c8>)
Event: research_import.py 6 func_no_catch return None

self.exception_in_progress is created with:

filename:           research_import.py
function:           func_no_catch
lineno:             6
exception_value:    ValueError('Error message',)
eventno:            X

This is as above. Next event has same filename, function, lineno, returning
None with event X+1 and this means the exception is propogated.
So add the exception to the func_types.add_exception and set
self.exception_in_progress to None. 

Event: research.py 83 func_that_catches_import exception (<class 'ValueError'>, ValueError('Error message',), <traceback object at 0x1023333c8>)
Event: research.py 84 func_that_catches_import line None

self.exception_in_progress is created with:

filename:           research.py
function:           func_that_catches_import
lineno:             83
exception_value:    ValueError('Error message',)
eventno:            X

Next event is 'line' event has same filename, function with event X+1
and line > 83.
This means the exception is caught. So do not add the exception to the
func_types.add_exception but set self.exception_in_progress to None. 

So the original analysis (above) is correct even when the exception is thrown
across modules.


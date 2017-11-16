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

2017-11-16
----------

Raising and catching exceptions.

Given this code:

# The next line is 45 
def exception_propogates():
    raise ValueError('Error message')
    return 'OK'

# The next line is 50 
def exception_caught():
    try:
        raise ValueError('Bad value')
    except ValueError as _err:
        pass
    try:
        raise KeyError('Bad key.')
    except KeyError as _err:
        pass
    return 'OK'

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

Event: research.py 46 exception_propogates exception (<class 'ValueError'>, ValueError('Error message',), <traceback object at 0x101031108>)

If the next event is:
    Event: research.py 46 exception_propogates return None
then record propagation of the exception.

If the next event is a line event at a line greater than the Exception:
    Event: research.py 54 exception_caught line None
The exception has been caught internally.


def func_that_raises():
    raise ValueError('Error message')

def func_no_catch():
    func_that_raises()


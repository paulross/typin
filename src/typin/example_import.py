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

class OuterClass:
    class InnerClass:
        def __init__(self, value):
            self._value = value
            
        def value(self):
            return self._value
            
    def __init__(self, value):
        self.outer_inner = OuterClass.InnerClass(value)

    def value(self):
        return self.outer_inner.value()

class InnerClass:
    def __init__(self, value):
        self._value = value
        
    def value(self):
        return self._value
    
def example_function(x):
    return 2 * x

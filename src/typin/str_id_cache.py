'''
Created on 22 Jun 2017

@author: paulross
'''

class StringIdCache:
    """Creates a cache of string to integer ID.
    Used for file paths and function names."""
    def __init__(self):
        self._name_to_id = {}
        # Reverse lookup
        self._id_to_name = {}
        
    def _lengths_match(self):
        if len(self._name_to_id) != len(self._id_to_name):
            raise RuntimeError('Length mismatch')
        return True
        
    def id(self, name):
        """Returns an integer ID corresponding to the name."""
        assert self._lengths_match()
        try:
            return self._name_to_id[name]
        except KeyError:
            _id = len(self._name_to_id)
            self._name_to_id[name] = _id
            assert _id not in self._id_to_name
            self._id_to_name[_id] = name
            return _id
    
    def name(self, the_id):
        """Returns the name for a given integer ID.
        Will raise a KeyError is the ID does not exist."""
        assert self._lengths_match()
        return self._id_to_name[the_id]

    def sorted_ids(self):
        """Returns a list of IDs sorted in order of the names."""
        assert self._lengths_match()
        lst = self._name_to_id.items()
        return [v[1] for v in sorted(lst)]

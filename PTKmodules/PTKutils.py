"""
Utilities for Reaper functions that provide user input.

Author: Michael Ellis
Copyright 2015 Ellis & Grant, Inc.
License: Open Source (MIT License)

"""
from reaper_python import *
def dbg(obj):
    """ Convenience wrapper for console logging """
    RPR_ShowConsoleMsg("{}\n".format(obj))

def userInputs(title, **items):
    """
    Simplifies the interface to RPR_GetUserInputs().
    See http://extremraym.com/cloud/reascript/x-raym_reascripthelp.html#GetUserInputs

    Usage example:
    inputs = UserInputs("A Title", foo=1, bar='yes')
    Returns:
        - None if user cancelled.
        - False if at least one input could not be converted to its proper type.
        - A Map object with the inputs names accessible with dotted notation and/or
          bracket notation, e.g. inputs.foo or inputs['foo']

    """
    inputs = Map(**items)
    names = inputs.keys()
    types = [type(inputs[n]) for n in names]
    captions = ["{} {}".format(n,t) for n, t in zip(names, types)]
    defaults = ["{}".format(inputs[n]) for n in names]
    num_inputs = len(inputs)
    csv_sz = num_inputs * 256 # arbitrary but more than long enough.
    result =  RPR_GetUserInputs(title, 
                                num_inputs, 
                                ",".join(captions), 
                                ",".join(defaults), 
                                csv_sz)
    if result[0] == False:
        return None # User cancelled
    else:
        retvals_csv = result[4]
        retval_strings = retvals_csv.split(',')
        for n, t, s in zip(names, types, retval_strings):
            try:
                inputs[n] = t(s)
            except ValueError:
                dbg("Bad input for {}. Can't convert {} to {}".format(n,s,t))
                return False  # User supplied bad input

        return inputs
                              
class Map(dict):
    """
    Creates a dict-like object with dot notation access.
    See http://stackoverflow.com/questions/2352181/how-to-use-a-dot-to-access-members-of-dictionary

    Example:
    m = Map({'first_name': 'Eduardo'}, last_name='Pool', age=24, sports=['Soccer'])
    """
    def __init__(self, *args, **kwargs):
        super(Map, self).__init__(*args, **kwargs)
        for arg in args:
            if isinstance(arg, dict):
                for k, v in arg.iteritems():
                    self[k] = v

        if kwargs:
            for k, v in kwargs.iteritems():
                self[k] = v

    def __getattr__(self, attr):
        return self.get(attr)

    def __setattr__(self, key, value):
        self.__setitem__(key, value)

    def __setitem__(self, key, value):
        super(Map, self).__setitem__(key, value)
        self.__dict__.update({key: value})

    def __delattr__(self, item):
        self.__delitem__(item)

    def __delitem__(self, key):
        super(Map, self).__delitem__(key)
        del self.__dict__[key]



# dbg(userInputs("My Test", foo=1, bar=3.2))


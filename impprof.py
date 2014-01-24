#####################################################################
#                                                                   #
# impprof.py                                                        #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of the labscript suite (see                     #
# http://labscriptsuite.org) and is licensed under the Simplified   #
# BSD License. See the license.txt file in the root of the project  #
# for the full license.                                             #
#                                                                   #
#####################################################################

import time

class _ProfilingImporter(object):
    def __init__(self):
        self.normal_import = __import__
        self.depth = 0
        self.threshold = 0
        try:
            self.builtins_dict = __builtins__.__dict__
        except AttributeError:
            self.builtins_dict = __builtins__

    def profiling_import(self, name, *args,**kwargs):
        self.depth += 1
        start_time = time.time()
        try:
            result = self.normal_import(name, *args, **kwargs)
        finally:
            self.depth -= 1
        time_taken = time.time() - start_time
        if time_taken > self.threshold:
            print ' '*self.depth + '[%.2f] import %s'%(time_taken, name)
        return result


    def enable(self, threshold=0.1):
        self.threshold = threshold
        self.builtins_dict['__import__'] = self.profiling_import

    def disable(self):
        self.builtins_dict['__import__'] = self.normal_import
    

_profiling_importer = _ProfilingImporter()                   
enable = _profiling_importer.enable
disable = _profiling_importer.disable

if __name__ == '__main__':
    enable(threshold=0.05)
    import IPython

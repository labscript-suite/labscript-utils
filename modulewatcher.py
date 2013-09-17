import sys
import threading
import time
import os
import imp
import gc

class ModuleWatcher(object):
    def __init__(self):
        # Disable garbage collection, due to a bug that causes a crash
        # if our check_and_unload function runs at the same time as a
        # garbage collection cycle. We will manually trigger garbage collection.
        gc.disable()
           
        # A lock to hold whenever you don't want modules unloaded:
        self.unloader_lock = threading.Lock()
            
        # The whitelist is the list of names of currently loaded modules:
        self.whitelist = set(sys.modules)
        self.modified_times = {}
        self.main = threading.Thread(target=self.mainloop)
        self.main.daemon = True
        self.main.start()
        
         
    def mainloop(self):
        while True:
            time.sleep(1)
            self.check_and_unload()
            self.check_garbage_collection()
            
    def check_and_unload(self):
        # Look through currently loaded modules:
        for name, module in sys.modules.items():
            # Look only at the modules not in the the whitelist:
            if name not in self.whitelist and hasattr(module,'__file__'):
                # Only consider modules which are .py files, no C extensions:
                module_file = module.__file__.replace('.pyc', '.py')
                if not module_file.endswith('.py') or not os.path.exists(module_file):
                    continue
                # Check and store the modified time of the .py file:
                modified_time = os.path.getmtime(module_file)
                previous_modified_time = self.modified_times.setdefault(name, modified_time)
                self.modified_times[name] = modified_time
                if modified_time != previous_modified_time:
                    # A module has been modified! Unload all modules
                    # not in the whitelist:
                    message = '%s modified: all modules will be reloaded next run.\n'%module_file
                    sys.stderr.write(message)
                    with self.unloader_lock:
                        # Acquire the import lock so that we don't unload
                        # modules whilst an import is in progess:
                        imp.acquire_lock()
                        try:
                            for name in sys.modules.copy():
                                if name not in self.whitelist:
                                    # This unloads a module. This is slightly
                                    # more general than reload(module), but
                                    # has the same caveats regarding existing
                                    # references. This also means that any
                                    # exception in the import will occur later,
                                    # once the module is (re)imported, rather
                                    # than now where catching the exception
                                    # would have to be handled differently.
                                    del sys.modules[name]
                                    if name in self.modified_times:
                                        del self.modified_times[name]
                        finally:
                            # We're done mucking around with the cached
                            # modules, normal imports in other threads
                            # may resume:
                            imp.release_lock()
                        
    def check_garbage_collection(self):
        counts, thresholds = gc.get_count(), gc.get_threshold()
        for generation, (count, threshold) in enumerate(zip(counts, thresholds)): 
            if count > threshold:
                gc.collect(generation)
                
if __name__ == '__main__':
    module_watcher = ModuleWatcher()
    import foo
    time.sleep(10)

import os
import sys
import cPickle as pickle
import imp
import __main__

check_stale = False

def get_path_to_cache_file():
    if os.name == 'nt':
        cachedir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cache')
    else:
        cachedir = os.path.join(os.environ['HOME'],'.cache','modulebooster')
    if not os.path.exists(cachedir):
        os.makedirs(cachedir)
    basename = os.path.abspath(getattr(__main__,'__file__','_interactive'))
    basename = '-'.join(s for s in basename.split(os.path.sep) if s) + '.pickle'
    basename = basename.replace(':','')
    cache_filepath = os.path.join(cachedir, basename)
    return cache_filepath
    
class _CachingImporter(object):
    def __init__(self):
        self.normal_import = __import__
        self.depth = 0
        self.attempted_module_searches = set()
        self.cache_filepath = get_path_to_cache_file()
        if not os.path.exists(self.cache_filepath):
            with open(self.cache_filepath,'w') as f:
                pickle.dump({},f)
        try:
            with open(self.cache_filepath) as f:
                self.cache = pickle.load(f)
        except Exception as e:
            sys.stderr.write("Warning: modulebooster: failed to open cache file, making a new one. Error was: %s\n"%str(e))
            self.cache = {}
            self.save()
        self.dirty = False
        try:
            self.builtins_dict = __builtins__.__dict__
        except AttributeError:
            self.builtins_dict = __builtins__
    
    def save(self):
        with open(self.cache_filepath,'w') as f:
            pickle.dump((self.cache), f)
        self.dirty = False
        
    def clear(self):
        self.cache = {}
        self.save()
    
    def bytecode_is_stale(self, fullname):
        attrs, _ = self.cache[fullname]
        if '__file__' in attrs:
            filepath = attrs['__file__']
            if filepath.endswith('.pyc'):
                dot_py = filepath[:-1]
                if os.path.exists(dot_py):
                    if os.path.getmtime(filepath) != os.path.getmtime(dot_py):
                        return True
        return False
        
    def find_module(self, fullname, path=None):
        try:
            if self.cache[fullname] is None:
                raise ImportError
            if check_stale and not self.bytecode_is_stale(fullname):
                return self
        except KeyError:
            self.attempted_module_searches.add(fullname)
                    
    def load_module(self, fullname):
        if imp.is_builtin(fullname):
            return imp.init_builtin(fullname)
        attrs, description = self.cache[fullname]
        module = sys.modules.setdefault(fullname, imp.new_module(fullname))
        for name, value in attrs.items():
            setattr(module, name, value)
        module.__loader__ = self
        _, mode, _ = description
        with open(module.__file__, mode) as module_file:
            module = imp.load_module(fullname, module_file, module.__file__, description)
            return module
                
    def __import__(self, name, globals={}, locals={}, fromlist=None, level=-1):
        try:
            self.depth += 1
            return self.normal_import(name, globals, locals, fromlist, level)
        except Exception as e:
            if self.depth == 1:
                sys.stderr.write('modulebooster: Uncaught exception during import. Invalidating import cache.\n')
                self.clear()
            raise
        finally:
            if self.depth == 1:
                self.inspect_modules()
            self.depth -= 1
     
    def inspect_modules(self):
        import inspect
        for fullname in self.attempted_module_searches:
            # Some entries in sys.modules are None. Other import attempts
            # failed and are not in sys.modules. We treat these the same.
            module = sys.modules.get(fullname, None)
            if module is None:
                data_to_cache = None
            else:
                names = ['__name__', '__file__', '__path__', '__package__']
                attrs = {name: getattr(module, name) for name in names if hasattr(module, name)}
                if imp.is_builtin(fullname):
                    description = None
                else:
                    (_, suffix, mode, module_type) = inspect.getmoduleinfo(module.__file__)
                    description = (suffix, mode, module_type)
                data_to_cache = attrs, description
            self.cache[fullname] = data_to_cache
            self.dirty = True
        self.attempted_module_searches = set()
        if self.dirty:
            self.save()
            
    def enable(self):
        self.builtins_dict['__import__'] = self.__import__
        if not self in sys.meta_path:
            sys.meta_path.append(self)

    def disable(self):
        self.builtins_dict['__import__'] = self.normal_import
        while self in sys.meta_path:
            sys.meta_path.remove(self)
     
_caching_importer = _CachingImporter()   
enable= _caching_importer.enable
disable = _caching_importer.disable
clear = _caching_importer.clear
enable()

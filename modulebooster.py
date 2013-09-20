import os
import sys
import cPickle as pickle
import inspect
import imp

if os.name == 'nt':
    cachedir = os.path.dirname(os.path.abspath(__file__))
else:
    cachedir = os.path.join(os.environ['HOME'],'.cache','modulebooster')
if not os.path.exists(cachedir):
    os.makedirs(cachedir)
    
cache_filepath = os.path.join(cachedir, 'import_cache.pickle')

class _CachingImporter(object):
    def __init__(self):
        self.normal_import = __import__
        try:
            self.builtins_dict = __builtins__.__dict__
        except AttributeError:
            self.builtins_dict = __builtins__
        self.depth = 0
        self.attempted_module_searches = set()
        try:
            with open(cache_filepath) as f:
                self.cache = pickle.load(f)
        except IOError:
            self.cache = {}
        self.dirty = False
        
    def find_module(self, fullname, path=None):
        try:
            if self.cache[fullname] is not None:
                return self
            else:
                raise ImportError
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
            self.depth -= 1
            if not self.depth:
                self.inspect_modules()
     
    def inspect_modules(self):
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
            
    def save(self):
        with open(cache_filepath,'w') as f:
            pickle.dump((self.cache), f)
        self.dirty = False
        
    def clear(self):
        self.cache = {}
        self.save()
                                
    def enable(self):
        self.builtins_dict['__import__'] = self.__import__
        sys.meta_path.append(self)

    def disable(self):
        self.builtins_dict['__import__'] = self.normal_import
        sys.meta_path.remove(self)
     
_caching_importer = _CachingImporter()   
enable= _caching_importer.enable
disable = _caching_importer.disable
clear = _caching_importer.clear
enable()

import os
import sys
import cPickle as pickle
import inspect
import imp

_cache_filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)),'cache.pickle')

DEBUG = False

class _Cache(object):
    def __init__(self):
        try:
            with open(_cache_filepath) as f:
                self.module_details = pickle.load(f)
        except IOError:
            self.module_details = {}
        self.dirty = False
    
    def __getitem__(self, name):
        return self.module_details[name] 
        
    def __setitem__(self, name, value):
        if name not in self.module_details or self.module_details.get(name, None) != value:
            if DEBUG: print 'saving deets for', name
            self.dirty = True
            self.module_details[name] = value
    
    def __contains__(self, name):
        return name in self.module_details
                       
    def save(self):
        print 'saving'
        with open(_cache_filepath,'w') as f:
            pickle.dump((self.module_details), f)
        self.dirty = False
        
    def clear(self):
        self.module_details = {}
        self.save()
        
        
class _CachingImporter(object):
    def __init__(self):
        self.normal_import = __import__
        self.cache = _Cache()
        try:
            self.builtins_dict = __builtins__.__dict__
        except AttributeError:
            self.builtins_dict = __builtins__
        self.depth = 0
        self.attempted_module_searches = set()
        
    def print_(self, *args, **kwargs):
        if DEBUG:
            msg = '   '*(self.depth-1) + ' '.join(str(arg) for arg in args) + '\n'
            if kwargs.get('stderr',False):
               sys.stderr.write(msg)
            else:
                sys.stdout.write(msg)

    def find_module(self, fullname, path=None):
        self.attempted_module_searches.add(fullname)
        if fullname in self.cache:
            if self.cache[fullname] is not None:
                self.print_('[cached as %s]'%fullname)
                if imp.is_builtin(fullname):
                    return self
                return self
            else:
                self.print_('[cached as failure - %s does not exist]'%fullname)
                raise ImportError
        else:
            self.print_('[normal import]')
            print 'normal:', fullname
        
    def load_module(self, fullname):
        self.print_('loading', fullname)
        if imp.is_builtin(fullname):
            return imp.init_builtin(fullname)
        details = self.cache[fullname]
        module = sys.modules.setdefault(fullname, imp.new_module(fullname))
        for name, value in details.items():
            setattr(module, name, value)
        module.__loader__ = self
        
        (_, suffix, mode, module_type) = inspect.getmoduleinfo(module.__file__)
        description = (suffix, mode, module_type)
        with open(module.__file__, mode) as module_file:
            module = imp.load_module(fullname, module_file, module.__file__, description)
            self.print_('success!')
            return module
                
    def __import__(self, name, globals={}, locals={}, fromlist=None, level=-1):
        try:
            self.depth += 1
            if not fromlist:
                self.print_('import', name)
            else:
               self.print_('from %s import'%name, ', '.join(fromlist))
            module = None
            module = self.normal_import(name, globals, locals, fromlist, level)
        except Exception as e:
            self.print_(e,stderr=True)
            if self.depth == 1:
                self.print_('Uncaught exception during import. Invalidating import cache...',stderr=True)
                self.cache.clear()
            raise
        finally:
            self.depth -= 1
        if self.depth == 0:
            self.print_('pop pop!')
            self.inspect_modules()
        return module
     
    def inspect_modules(self):
        for name in self.attempted_module_searches:
            # Some entries in sys.modules are None. Other import attempts
            # failed and are not in sys.modules. We treat these the same.
            module = sys.modules.get(name, None)
            if module is None:
                details = None
            else:
                names = ['__name__', '__file__', '__path__', '__package__']
                details = {name: getattr(module, name) for name in names if hasattr(module, name)}
            self.cache[name] = details
        self.attempted_module_searches = set()
        
        if self.cache.dirty:
            self.cache.save()
                            
    def enable(self):
        self.builtins_dict['__import__'] = self.__import__
        sys.meta_path.append(self)

    def disable(self):
        self.builtins_dict['__import__'] = self.normal_import
        sys.meta_path.remove(self)
     
_caching_importer = _CachingImporter()   
enable= _caching_importer.enable
disable = _caching_importer.disable


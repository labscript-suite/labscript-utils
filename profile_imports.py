def profile_imports(threshold = 0.1):
    import time
    _old_import = __import__
    class depth:
        depth = -1
        
    def profiling_import(name, *args,**kwargs):
        start_time = time.time()
        depth.depth += 1
        try:
            result = _old_import(name, *args, **kwargs)
            time_taken = time.time() - start_time
            if time_taken > threshold:
                print ' '*depth.depth + '[%.2f] import %s'%(time_taken, name)
            return result
        finally:
            depth.depth -= 1
    try:
        builtins_dict = __builtins__.__dict__
    except AttributeError:
        # We must be the __main__ module. __builtins__ is already a dict here.
         builtins_dict = __builtins__
          
    builtins_dict['__import__'] = profiling_import

if __name__ == '__main__':
    profile_imports()

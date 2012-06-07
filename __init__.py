import threading
import os
import time

class FileWatcher(object):
    def __init__(self,callback, files=None, folders=None):
        self.callback = callback
        if files is None:
            self.files = set()
        elif isinstance(files,str):
            self.files = set([files])
        else:
            self.files = set(files)
        if folders is None:
            self.folders = set()
        elif isinstance(folders,str):
            self.folders = set([folders])
        else:
            self.folders = set(folders)
            
        self.modified_times = {}
        self.main = threading.Thread(target = self.mainloop)
        self.main.daemon = True
        self.running = True
        self.lock = threading.Lock()
        self.update_files(trigger_callback=False)
        self.main.start()
        
    def mainloop(self):
        while self.running:
            time.sleep(1)
            with self.lock:
                self.update_files()
                self.check()
    
    
    def update_files(self,folders=None,trigger_callback=True):
        if folders is None:
            folders = self.folders
        for folder in folders:
            try:
                for name in os.listdir(folder):
                    path = os.path.join(folder,name)
                    if os.path.isdir(path):
                        self.update_files([path],trigger_callback)
                    else:
                        if not path in self.files:
                            self.files.add(path)
                            if trigger_callback:
                                self.callback(path,os.path.getmtime(path))
            except OSError:
                # Folder has been deleted. File deletion will still be
                # detected, so we can ignore this.
                continue
    
    def check(self):
        for name in self.files:
            try:
                modified_time = os.path.getmtime(name)
            except OSError:
                if not os.path.exists(name):
                    modified_time = None
            previous_modified_time = self.modified_times.setdefault(name, modified_time)
            self.modified_times[name] = modified_time
            if modified_time != previous_modified_time:
                if name in self.modified_times:
                    del self.modified_times[name]
                    self.callback(name,modified_time)
                                    
    def stop(self):
        self.running = False
    
    def add_file(self, path):
        self.add_files(path)
        
    def add_folder(self, folder):
        self.add_folders(folder)
        
    def add_files(self,files):
        with self.lock:
            if isinstance(files,str):
                self.files.add(files)
            else:
               self.files.union(set(files))
    
    def add_folders(self,folders):
        with self.lock:
            if isinstance(folders,str):
                self.folders.add(folders)
            else:
               self.files.union(set(folders))
            self.update_files(trigger_callback=False)
            
   
if __name__ == '__main__':
    # Example usage
    
    def callback(name,modified):
        if modified is None:
            print name,'has been deleted'
        else:
            print name, 'was modified at',modified
        
    f = FileWatcher(callback, files='test.txt',folders='foobar')  
    time.sleep(60)
    

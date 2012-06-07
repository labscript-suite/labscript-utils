import threading
import os
import time

class FileWatcher(object):
    def __init__(self,callback, files):
        self.callback = callback
        self.files = files
        self.modified_times = {}
        self.main = threading.Thread(target = self.mainloop)
        self.main.daemon = True
        self.running = True
        self.main.start()
        
    def mainloop(self):
        while self.running:
            time.sleep(1)
            self.check()
    
    def stop(self):
        self.running = False
        
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

   
if __name__ == '__main__':
    # Example usage
    
    def callback(name,modified):
        if modified is None:
            print name,'has been deleted'
        else:
            print name, 'was modified at',modified
        
    f = FileWatcher(callback, ['test.txt'])  
    time.sleep(60)
    

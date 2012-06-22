import ConfigParser
import os
from filewatcher import FileWatcher

class LabConfig(ConfigParser.SafeConfigParser):    
    def __init__(self,config_path = r'C:\lab_config.ini'):
        self.config_path = config_path
        
        # If the file doesn't exist, create it
        if not os.path.exists(config_path):
            with open(config_path,'a+') as f:
                pass
        
        # Watch the File for changes
        self.filewatcher = FileWatcher(self.reload,self.config_path)
        
        # Load the config file
        ConfigParser.SafeConfigParser.__init__(self)
        self.read(config_path)
        

    # Overwrite the add_section method to only attempt to add a section if it doesn't
    # exist. We don't ever care whether a section exists or not, only that it does exist
    # when we try and save an attribute into it.
    def add_section(self,section):
        # Create the group if it doesn't exist
        if not self.has_section(section):
            ConfigParser.SafeConfigParser.add_section(self,section)
    
    # Overwrite the set method so that it adds the section if it doesn't exist,
    # and immediately saves the data to the file (to avoid data loss on program crash)
    def set(self, section, option, value):
        self.add_section(section)            
        ConfigParser.SafeConfigParser.set(self,section,option,value)
        self.save()
        
    # Overwrite the remove section function so that it immediately saves the change to disk
    def remove_section(self,section):
        ConfigParser.SafeConfigParser.remove_section(self,section)
        self.save()
    
    # Overwrite the remove option function so that it immediately saves the change to disk    
    def remove_option(self,section,option):
        ConfigParser.SafeConfigParser.remove_option(self,section,option)
        self.save()
    
    # Provide a convenience method to save the contents of the ConfigParser to disk
    def save(self):
        with open(self.config_path, 'w+') as f:
            self.write(f)
    
    def reload(self,*args,**kwargs):
        self.filewatcher.stop()
        self.__init__(self.config_path)
        
    

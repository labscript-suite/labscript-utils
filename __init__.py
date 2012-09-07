import ConfigParser
import os

if os.name == 'nt':
    config_prefix = r'C:\labconfig\\'
else:
    config_prefix = os.path.join(os.getenv('HOME'),'labconfig')
    
class LabConfig(ConfigParser.SafeConfigParser):    
    def __init__(self,config_path,required_params={}):
        self.config_path = config_path
        
        self.file_format = ""
        for section, options in required_params.items():
            self.file_format += "[%s]\n"%section
            for option in options:
                self.file_format += "%s = <value>\n"%option
        
        # If the folder doesn't exist, create it
        if not os.path.exists(os.path.dirname(config_path)):
            os.mkdir(os.path.dirname(config_path))
        
        # If the file doesn't exist, create it
        if not os.path.exists(config_path):
            with open(config_path,'a+') as f:
                f.write(self.file_format)
        
        # Load the config file
        ConfigParser.SafeConfigParser.__init__(self)
        self.read(config_path)
        
        try:
            for section, options in required_params.items():
                for option in options:
                    self.get(section,option)
                
        except ConfigParser.NoOptionError as e:               
            raise Exception('The experiment configuration file located at %s does not have the required keys. Make sure the config file containes the following structure:\n%s'%(config_path, self.file_format))
        

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

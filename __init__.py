import os
import gtk
import h5py

# Create a generic interface for displaying pages of settings

class Settings(object):
    
    def __init__(self,storage='hdf5',file=None,parent = None,page_classes = []):
        self.pages = {}
        self.instantiated_pages = {}
        self.dialog_open = False
        self.parent = parent
        self.storage = storage
        self.file = file
        self.callback_list = []
        
        if not self.file:
            raise Exception('You must specify a file to load/save preferences from')
        
        for c in page_classes:
            self.add_settings_interface(c)
            
    # This function can be called to add a interface
    # Each one of these will display as a seperate page in the settings window
    # You can not add a class more than once!
    # Classes must have unique Class.name attributes! (This might change later...)
    def add_settings_interface(self,setting_class):
        if setting_class.name in self.pages:
            return False
                   
        self.pages[setting_class.name] = setting_class(self.load(setting_class.__name__))   
        return True
        
    def load(self,name):
        if self.storage == 'hdf5':
            with h5py.File(self.file,'r+') as h5file: 
                # does the settings group exist?
                if 'preferences' not in h5file:
                    h5file['/'].create_group('preferences')
                    
                # is there an entry for this preference type?
                group = h5file['/preferences']
                if name not in group.attrs:
                    group.attrs[name] = repr({})
                data = eval(group.attrs[name])                    
            return data    
        else:
            raise Exception("the Settings module cannot handle the storage type: %s"%str(self.storage))
        
    # A simple interface for accessing values in the settings interface
    def get_value(self,settings_class,value_name):
        return self.pages[settings_class.name].get_value(value_name)
        
    # goto_page should be the CLASS which you wish to go to!
    def create_dialog(self,goto_page=None):
        if not self.dialog_open:
            self.instantiated_pages = {}
            
            builder = gtk.Builder()
            builder.add_from_file(os.path.join(os.path.dirname(os.path.realpath(__file__)),'settings_interface.glade'))
            builder.connect_signals(self)
            
            self.notebook = builder.get_object('notebook')
            self.window = builder.get_object('window')
            
            #sorted(a.items(),key=lambda x: x[1])
            set_page = None
            for name, c in sorted(self.pages.items()):
                page,icon = c.create_dialog(self.notebook)
                
                # save page
                self.instantiated_pages[c.__class__] = page
                
                # Create label
                if isinstance(icon,gtk.Image):
                    # use their icon
                    pass
                else:
                    # use default icon
                    pass
                    
                tab_label = gtk.Label(c.name)
                self.notebook.append_page(page,tab_label)
                
                if goto_page and isinstance(c,goto_page):
                    # this is the page we want to go to!
                    set_page = page
        
            # We do this here in case one of the settings pages specifically inserts itself in an out of order place (eg first)
            # We hope that everything will be in alphabetical order, but maybe not!
            if set_page:
                self.notebook.set_current_page(self.notebook.page_num(set_page))
            
            if self.parent:
                self.window.set_transient_for(self.parent)
            
            self.window.show()
            self.dialog_open = True
        else:
            if goto_page and goto_page in self.instantiated_pages:
                
                self.notebook.set_current_page(self.notebook.page_num(self.instantiated_pages[goto_page]))
                
            self.window.present()
    
    def register_callback(self,callback):
        self.callback_list.append(callback)
        
    def remove_callback(self,callback):
        self.callback_list.remove(callback)
    
    def on_save(self,widget):
        # Save the settings
        if self.storage == 'hdf5':
            with h5py.File(self.file,'r+') as h5file:
                group = h5file['/preferences']
                for page in self.pages.values():
                    group.attrs[page.__class__.__name__] = repr(page.save()) 
        else:
            # this should never happen as the exception will have been raised on load!
            pass
            
        # run callback functions!
        # Notifies other areas of the program that settings have changed
        for callback in self.callback_list:
            callback()
        
        self.close()
            
    def on_cancel(self,widget):
        self.close()
    
    def close(self,*args,**kwargs):
        if self.dialog_open:
            # Close the setting classes
            for page in self.pages.values():
                page.close()   
            self.window.destroy()
            self.dialog_open = False
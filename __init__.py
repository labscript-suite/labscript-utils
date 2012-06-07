import gtk


# Create a generic interface for displaying pages of settings

class Settings(object):
    
    def __init__(self,page_classes):
        self.pages = {}
        for c in page_classes:
            self.add_settings_interface(c)
        
    # This function can be called to add a interface
    # Each one of these will display as a seperate page in the settings window
    # You can not add a class more than once!
    # Classes must have unique names! (This might change later...)
    def add_settings_interface(self,setting_class):
        if setting_class.name in self.pages:
            return False
        self.pages[setting_class.name] = setting_class()   
        return True
        
    # A simple interface for accessing values in the settings interface
    def get_value(self,settings_class,value_name)
        return self.pages[settings_class.name].get_value(value_name)
        
    # goto_page should be the CLASS which you wish to go to!
    def create_dialog(self,goto_page=None):        
        builder = gtk.Builder()
        builder.add_from_file('settings_interface.glade')
        builder.connect_signals(self)
        
        self.notebook = builder.get_object('notebook')
        
        #sorted(a.items(),key=lambda x: x[1])
        set_page = None
        for name, c in sorted(self.pages.items()):
            page = c.create_dialog(self.notebook)
            
            if goto_page and isinstance(c,goto_page):
                # this is the page we want to go to!
                set_page = page
    
        # We do this here in case one of the settings pages specifically inserts itself in an out of order place (eg first)
        # We hope that everything will be in alphabetical order, but maybe not!
        if set_page:
            self.notebook.set_current_page(self.notebook.page_num(set_page))
        
        self.window.show()
        
        
    def on_save(self,widget):
        # Save the settings
        for page in self.pages:
            page.save()    
            
    def on_cancel(self,widget):
        self.close()
    
    def close(self):
        # Close the setting classes
        for page in self.pages:
            page.close()   
        self.window.destroy()
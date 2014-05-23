#####################################################################
#                                                                   #
# tk_exception.py                                                   #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of the labscript suite (see                     #
# http://labscriptsuite.org) and is licensed under the Simplified   #
# BSD License. See the license.txt file in the root of the project  #
# for the full license.                                             #
#                                                                   #
#####################################################################

import sys, os

if sys.version < '3':
    import Tkinter as tkinter
    import Tkconstants as constants
else:
    import tkinter
    import tkinter.constants as constants

error_im_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'error.gif')

class ErrorWindow(tkinter.Text):
    """Class to display the error in a textbox. Parts copied from Tkinter's ScrolledText widget""" 
    def __init__(self, master=None, **kw):
        self.frame = tkinter.Frame(master, padx=10, pady=10)
        
        self.upperframe = tkinter.Frame(self.frame)
        self.upperframe.pack(side=constants.TOP, fill=constants.X) 
        
        self.lowerframe = tkinter.Frame(self.frame, pady=10)
        self.lowerframe.pack(side=constants.TOP, fill=constants.BOTH, expand=True)  
        
        self.error_im = tkinter.PhotoImage(file=error_im_path)
        self.imlabel = tkinter.Label(self.upperframe, borderwidth = 10, image=self.error_im)
        self.imlabel.pack(side=constants.LEFT)
        self.textlabel = tkinter.Label(self.upperframe, text='It looks like an error has occured:\n%s'%sys.argv[2], 
                                       borderwidth = 10, wraplength=400, justify='left')
        self.textlabel.pack(side=constants.LEFT)

        self.vbar = tkinter.Scrollbar(self.lowerframe)
        self.vbar.pack(side=constants.RIGHT, fill=constants.Y)
        
        self.button = tkinter.Button(self.frame, text='Ok', command=self.ok_clicked, padx=20, pady=5)
        self.button.pack(side=constants.BOTTOM)
        
        kw.update({'yscrollcommand': self.vbar.set})
        tkinter.Text.__init__(self, self.lowerframe, **kw)
        
        self.pack(side=constants.LEFT, fill=constants.BOTH, expand=True)
        self.vbar['command'] = self.yview

        # Copy geometry methods of self.frame without overriding Text
        # methods -- hack!
        text_meths = vars(tkinter.Text).keys()
        methods = list(vars(tkinter.Pack).keys()) + list(vars(tkinter.Grid).keys()) + list(vars(tkinter.Place).keys())
        methods = set(methods).difference(text_meths)

        for m in methods:
            if m[0] != '_' and m != 'config' and m != 'configure':
                setattr(self, m, getattr(self.frame, m))

    def ok_clicked(self):
        win.quit()
            

if __name__ == "__main__":
    win = tkinter.Tk()
    win.title('Unhandled exception in %s'%sys.argv[1])
    win.geometry('500x500')
    stext = ErrorWindow(master=win, bg='black', height=10, fg='red', font=("monospace", 10, "bold"))
    stext.insert(constants.END, sys.argv[3])
    stext.pack(fill=constants.BOTH, side=constants.LEFT, expand=True)
    stext.config(state=constants.DISABLED)
    stext.focus_set()
    stext.mainloop()

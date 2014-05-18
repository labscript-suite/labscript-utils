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

from Tkinter import Frame, Text, Scrollbar, Button, Pack, Grid, Place, Label, PhotoImage, Tk
from Tkconstants import RIGHT, LEFT, X, Y, BOTH, TOP, BOTTOM, W, END, DISABLED

error_im_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'error.gif')

class ErrorWindow(Text):
    """Class to display the error in a textbox. Parts copied from Tkinter's ScrolledText widget""" 
    def __init__(self, master=None, **kw):
        self.frame = Frame(master, padx=10, pady=10)
        
        self.upperframe = Frame(self.frame)
        self.upperframe.pack(side=TOP, fill=X) 
        
        self.lowerframe = Frame(self.frame, pady=10)
        self.lowerframe.pack(side=TOP, fill=BOTH, expand=True)  
        
        self.error_im = PhotoImage(file=error_im_path)
        self.imlabel = Label(self.upperframe, borderwidth = 10, image=self.error_im)
        self.imlabel.pack(side=LEFT)
        self.textlabel = Label(self.upperframe, text='It looks like an error has occured:\n%s'%sys.argv[2], 
                           borderwidth = 10, wraplength=400, justify='left')
        self.textlabel.pack(side=LEFT)

        self.vbar = Scrollbar(self.lowerframe)
        self.vbar.pack(side=RIGHT, fill=Y)
        
        self.button = Button(self.frame, text='Ok', command=self.ok_clicked, padx=20, pady=5)
        self.button.pack(side=BOTTOM)
        
        kw.update({'yscrollcommand': self.vbar.set})
        Text.__init__(self, self.lowerframe, **kw)
        
        self.pack(side=LEFT, fill=BOTH, expand=True)
        self.vbar['command'] = self.yview

        # Copy geometry methods of self.frame without overriding Text
        # methods -- hack!
        text_meths = vars(Text).keys()
        methods = vars(Pack).keys() + vars(Grid).keys() + vars(Place).keys()
        methods = set(methods).difference(text_meths)

        for m in methods:
            if m[0] != '_' and m != 'config' and m != 'configure':
                setattr(self, m, getattr(self.frame, m))

    def ok_clicked(self):
        win.quit()
            

if __name__ == "__main__":
    win = Tk()
    win.title('Unhandled exception in %s'%sys.argv[1])
    win.geometry('500x500')
    stext = ErrorWindow(master=win, bg='black', height=10, fg='red', font=("monospace", 10, "bold"))
    stext.insert(END, sys.argv[3])
    stext.pack(fill=BOTH, side=LEFT, expand=True)
    stext.config(state=DISABLED)
    stext.focus_set()
    stext.mainloop()

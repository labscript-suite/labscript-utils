#####################################################################
#                                                                   #
# gtk_exception.py                                                  #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of the labscript suite (see                     #
# http://labscriptsuite.org) and is licensed under the Simplified   #
# BSD License. See the license.txt file in the root of the project  #
# for the full license.                                             #
#                                                                   #
#####################################################################

import gtk, pango, sys

dialog = gtk.Dialog('Unhandled exception in %s'%sys.argv[1])
# title Label
label = gtk.Label()
label.set_markup("<b>" + "It looks like an error has occurred." + "</b>")
label.set_alignment(0, 0.5)
dialog.get_content_area().pack_start(label, False)

text_label = gtk.Label(sys.argv[2])
text_label.set_alignment(0, 0.5)
text_label.set_line_wrap(True)

def text_label_size_allocate(widget, rect):
        """Lets label resize correctly while wrapping text."""
        widget.set_size_request(rect.width, -1)
        
text_label.connect("size-allocate", text_label_size_allocate)
dialog.get_content_area().pack_start(text_label, False)

# TextView with error_string
buffer = gtk.TextBuffer()
buffer.set_text(sys.argv[3])
textview = gtk.TextView()
textview.set_buffer(buffer)
textview.set_editable(False)
textview.set_wrap_mode(gtk.WRAP_WORD)
try:
    textview.modify_font(pango.FontDescription("monospace 10"))
except Exception:
    print >> sys.stderr, "gtkcrashhandler: modify_font raised an exception"

# allow scrolling of textview
scrolled = gtk.ScrolledWindow()
scrolled.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
scrolled.add_with_viewport(textview)

# hide the textview in an Expander widget
expander = gtk.expander_new_with_mnemonic(("_Details"))
expander.set_expanded(True)
expander.add(scrolled)
dialog.get_content_area().pack_start(expander)

# add buttons
dialog.add_button(("_Ok"), 2)
dialog.set_default_response(2)

# set dialog aesthetic preferences
dialog.set_border_width(12)
dialog.get_content_area().set_spacing(4)
dialog.set_default_size(500,400)

# show the dialog and act on it
dialog.show_all()
res = dialog.run()
dialog.destroy()

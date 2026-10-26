#####################################################################
#                                                                   #
# application.py                                                    #
#                                                                   #
# Copyright 2026, Monash University                                 #
#                                                                   #
# This file is part of the labscript suite (see                     #
# http://labscriptsuite.org) and is licensed under the Simplified   #
# BSD License. See the license.txt file in the root of the project  #
# for the full license.                                             #
#                                                                   #
#####################################################################
"""The fonts and the style of the labscript suite applications"""

from qtutils.qt import QtGui
from qtutils.fonts import load_fonts

FONT_FAMILY = 'Ubuntu'
MONOSPACE_FONT_FAMILY = 'Ubuntu Mono'
# Font sizes in device-independent pixels, which are the same on every platform:
FONT_PIXEL_SIZE = 12
MONOSPACE_FONT_PIXEL_SIZE = 15


def setup_application(qapplication):
    """Set the style of the application to Fusion and its font to the bundled Ubuntu
    font at FONT_PIXEL_SIZE. Call this after making the QApplication and after setting
    any application style sheet, and before making any widget: setting a style or a
    style sheet gives the widget classes the fonts of the platform theme again."""
    load_fonts()
    qapplication.setStyle('Fusion')
    font = QtGui.QFont(FONT_FAMILY)
    font.setPixelSize(FONT_PIXEL_SIZE)
    qapplication.setFont(font)


def monospace_font(pixel_size=MONOSPACE_FONT_PIXEL_SIZE):
    """The bundled Ubuntu Mono font at the given size in device-independent pixels"""
    load_fonts()
    font = QtGui.QFont(MONOSPACE_FONT_FAMILY)
    font.setPixelSize(pixel_size)
    return font

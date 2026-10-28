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

from qtutils.qt import QtCore, QtGui
from qtutils.fonts import load_fonts

FONT_FAMILY = 'Ubuntu'
MONOSPACE_FONT_FAMILY = 'Ubuntu Mono'
# Font sizes in device-independent pixels, which are the same on every platform:
FONT_PIXEL_SIZE = 12
MONOSPACE_FONT_PIXEL_SIZE = 15
# Fraction by which the alternate row colour of item views is mixed from the base colour
# towards the text colour:
ALTERNATE_BASE_MIX = 0.07


def _mix(color, other, fraction):
    return QtGui.QColor.fromRgbF(
        *((1 - fraction) * a + fraction * b
          for a, b in zip(color.getRgbF(), other.getRgbF()))
    )


def _item_view_palette(qapplication):
    """The application palette with an alternate row colour that is the base colour
    mixed towards the text colour by ALTERNATE_BASE_MIX. In dark mode, the Windows
    platform theme gives every widget a shade of the accent colour as the alternate row
    colour."""
    palette = QtGui.QPalette(qapplication.palette())
    text = palette.color(QtGui.QPalette.ColorGroup.Active, QtGui.QPalette.ColorRole.Text)
    for group in [
        QtGui.QPalette.ColorGroup.Active,
        QtGui.QPalette.ColorGroup.Inactive,
        QtGui.QPalette.ColorGroup.Disabled,
    ]:
        base = palette.color(group, QtGui.QPalette.ColorRole.Base)
        palette.setColor(
            group,
            QtGui.QPalette.ColorRole.AlternateBase,
            _mix(base, text, ALTERNATE_BASE_MIX),
        )
    return palette


def _set_item_view_palette(qapplication):
    palette = _item_view_palette(qapplication)
    if qapplication.palette('QAbstractItemView') != palette:
        qapplication.setPalette(palette, 'QAbstractItemView')


def setup_application(qapplication):
    """Set the style of the application to Fusion and its font to the bundled Ubuntu
    font at FONT_PIXEL_SIZE, and give item views the palette of _item_view_palette().
    Call this after making the QApplication and after setting any application style
    sheet, and before making any widget: setting a style or a style sheet gives the
    widget classes the fonts of the platform theme again."""
    load_fonts()
    qapplication.setStyle('Fusion')
    _set_item_view_palette(qapplication)
    # When the application palette changes, Qt sets the palettes of the platform theme
    # for each widget class after emitting paletteChanged:
    qapplication.paletteChanged.connect(
        lambda: QtCore.QTimer.singleShot(0, lambda: _set_item_view_palette(qapplication))
    )
    font = QtGui.QFont(FONT_FAMILY)
    font.setPixelSize(FONT_PIXEL_SIZE)
    qapplication.setFont(font)


def monospace_font(pixel_size=MONOSPACE_FONT_PIXEL_SIZE):
    """The bundled Ubuntu Mono font at the given size in device-independent pixels"""
    load_fonts()
    font = QtGui.QFont(MONOSPACE_FONT_FAMILY)
    font.setPixelSize(pixel_size)
    return font

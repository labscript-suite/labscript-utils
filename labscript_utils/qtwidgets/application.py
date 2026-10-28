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

import sys

from qtutils.qt import QtCore, QtGui, QtWidgets
from qtutils.fonts import load_fonts
from qtutils.icons import ICON_SIZE

FONT_FAMILY = 'Ubuntu'
MONOSPACE_FONT_FAMILY = 'Ubuntu Mono'
# Font sizes in device-independent pixels, which are the same on every platform:
FONT_PIXEL_SIZE = 12
MONOSPACE_FONT_PIXEL_SIZE = 15
# Fraction by which the alternate row colour of item views is mixed from the base colour
# towards the text colour:
ALTERNATE_BASE_MIX = 0.07
# Relative luminance of the accent colour above which the check mark is black instead of
# white:
CHECK_MARK_LUMINANCE = 0.4
COLOR_GROUPS = [
    QtGui.QPalette.ColorGroup.Active,
    QtGui.QPalette.ColorGroup.Inactive,
    QtGui.QPalette.ColorGroup.Disabled,
]


class FusionStyle(QtWidgets.QProxyStyle):
    """The Fusion style, with the indicators of checked check boxes and radio buttons
    filled with the accent colour of the application palette, and icons in list views
    and toolbars drawn at ICON_SIZE. The check mark is black on a light accent colour and
    white on a dark one."""

    CHECKED_FILL_ELEMENTS = [
        QtWidgets.QStyle.PrimitiveElement.PE_IndicatorCheckBox,
        QtWidgets.QStyle.PrimitiveElement.PE_IndicatorRadioButton,
    ]
    # The fill is the accent colour that the user chose for the desktop. On Linux, the
    # accent colour role does not have this colour: Qt's GTK platform theme leaves it at
    # Qt's default and sets the highlight colour from the desktop theme, so we use the
    # application's highlight colour. Qt 5 has no accent colour role.
    if sys.platform.startswith('linux') or not hasattr(QtGui.QPalette.ColorRole, 'Accent'):
        ACCENT = QtGui.QPalette.ColorRole.Highlight
    else:
        ACCENT = QtGui.QPalette.ColorRole.Accent

    ICON_SIZE_METRICS = [
        QtWidgets.QStyle.PixelMetric.PM_ListViewIconSize,
        QtWidgets.QStyle.PixelMetric.PM_ToolBarIconSize,
    ]

    def __init__(self):
        super().__init__(QtWidgets.QStyleFactory.create('Fusion'))

    def pixelMetric(self, metric, option=None, widget=None):
        if metric in self.ICON_SIZE_METRICS:
            return ICON_SIZE
        return super().pixelMetric(metric, option, widget)

    def drawPrimitive(self, element, option, painter, widget=None):
        State = QtWidgets.QStyle.StateFlag
        if (
            element in self.CHECKED_FILL_ELEMENTS
            and option.state & State.State_On
            and option.state & State.State_Enabled
        ):
            # We take the accent colour from the application palette, since a widget may
            # change the highlight colour in its own palette. The Windows platform theme
            # gives the inactive colour group the window colour as the accent colour, so
            # we use the colour of the active group:
            if widget is None:
                application_palette = QtWidgets.QApplication.palette()
            else:
                application_palette = QtWidgets.QApplication.palette(widget)
            Active = QtGui.QPalette.ColorGroup.Active
            accent = application_palette.color(Active, self.ACCENT)
            palette = option.palette
            light = _relative_luminance(accent) > CHECK_MARK_LUMINANCE
            check_mark = QtGui.QColor('black' if light else 'white')
            filled = QtGui.QPalette(palette)
            filled.setColor(QtGui.QPalette.ColorRole.Base, accent)
            filled.setColor(QtGui.QPalette.ColorRole.Text, check_mark)
            option.palette = filled
            super().drawPrimitive(element, option, painter, widget)
            option.palette = palette
        else:
            super().drawPrimitive(element, option, painter, widget)


def _relative_luminance(color):
    """The relative luminance of the colour, as defined in WCAG 2"""

    def linear(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (linear(c) for c in (color.redF(), color.greenF(), color.blueF()))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _mix(color, other, fraction):
    return QtGui.QColor.fromRgbF(
        *((1 - fraction) * a + fraction * b
          for a, b in zip(color.getRgbF(), other.getRgbF()))
    )


def _class_palettes(qapplication):
    """Palettes of widget classes for which we replace the palette of the platform
    theme. In dark mode, the Windows platform theme gives QCheckBox and QRadioButton a
    palette with the accent colour as the base colour, which Fusion fills the indicator
    with, and gives every widget a shade of the accent colour as the alternate row
    colour. Item views get the application palette with an alternate row colour that is
    the base colour mixed towards the text colour by ALTERNATE_BASE_MIX."""
    palette = qapplication.palette()
    item_view_palette = QtGui.QPalette(palette)
    text = palette.color(QtGui.QPalette.ColorGroup.Active, QtGui.QPalette.ColorRole.Text)
    for group in COLOR_GROUPS:
        base = palette.color(group, QtGui.QPalette.ColorRole.Base)
        item_view_palette.setColor(
            group,
            QtGui.QPalette.ColorRole.AlternateBase,
            _mix(base, text, ALTERNATE_BASE_MIX),
        )
    return {
        'QCheckBox': palette,
        'QRadioButton': palette,
        'QAbstractItemView': item_view_palette,
    }


def _set_class_palettes(qapplication):
    for class_name, palette in _class_palettes(qapplication).items():
        if qapplication.palette(class_name) != palette:
            qapplication.setPalette(palette, class_name)


def setup_application(qapplication):
    """Set the style of the application to FusionStyle and its font to the bundled Ubuntu
    font at FONT_PIXEL_SIZE, and set the palettes of some widget classes (see
    _class_palettes()). Call this after making the QApplication and after setting any
    application style sheet, and before making any widget: setting a style or a style
    sheet gives the widget classes the fonts of the platform theme again."""
    load_fonts()
    qapplication.setStyle(FusionStyle())
    _set_class_palettes(qapplication)
    # When the application palette changes, Qt sets the palettes of the platform theme
    # for each widget class after emitting paletteChanged:
    qapplication.paletteChanged.connect(
        lambda: QtCore.QTimer.singleShot(0, lambda: _set_class_palettes(qapplication))
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

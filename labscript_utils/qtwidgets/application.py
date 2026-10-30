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
import warnings

from qtutils.qt import QtCore, QtGui, QtWidgets
from qtutils.fonts import load_fonts
from qtutils.icons import ICON_SIZE

from labscript_utils.labconfig import LabConfig

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
# Delay in milliseconds before a tooltip is shown. If a tooltip is visible, or was hidden
# less than this time ago, the next tooltip is shown immediately:
TOOLTIP_DELAY_MS = 300
# Interval in milliseconds of the timer that Qt starts on a tooltip label to hide it:
QT_TOOLTIP_HIDE_DELAY_MS = 300
TOOLTIP_FONT_PIXEL_SIZE = 12
TOOLTIP_TEXT = QtGui.QColor(255, 255, 255)
TOOLTIP_BACKGROUND = QtGui.QColor(0, 0, 0, 217)
TOOLTIP_BORDER = QtGui.QColor(255, 255, 255, 51)
TOOLTIP_CORNER_RADIUS = 4
# Horizontal and vertical distance in pixels between the border of a tooltip and its
# text:
TOOLTIP_PADDING_X = 6
TOOLTIP_PADDING_Y = 4
# Events that make the next tooltip wait for TOOLTIP_DELAY_MS even if it follows another
# tooltip immediately:
TOOLTIP_INHIBIT_EVENTS = [
    QtCore.QEvent.Type.MouseButtonPress,
    QtCore.QEvent.Type.MouseButtonDblClick,
    QtCore.QEvent.Type.Wheel,
    QtCore.QEvent.Type.KeyPress,
]
# Events after which Qt may start its timer to hide the tooltip:
TOOLTIP_HIDE_EVENTS = [
    QtCore.QEvent.Type.MouseMove,
    QtCore.QEvent.Type.Leave,
    QtCore.QEvent.Type.ToolTip,
]
COLOR_GROUPS = [
    QtGui.QPalette.ColorGroup.Active,
    QtGui.QPalette.ColorGroup.Inactive,
    QtGui.QPalette.ColorGroup.Disabled,
]
# Values of the labconfig key [gui] color_scheme, and the names of the corresponding
# members of Qt.ColorScheme:
COLOR_SCHEMES = {'system': 'Unknown', 'light': 'Light', 'dark': 'Dark'}


class FusionStyle(QtWidgets.QProxyStyle):
    """The Fusion style, with the indicators of checked check boxes and radio buttons
    filled with the accent colour of the application palette, and icons in list views
    and toolbars drawn at ICON_SIZE. The check mark is black on a light accent colour and
    white on a dark one.

    Tooltips are drawn as white text on a translucent black rounded rectangle, and are
    shown after TOOLTIP_DELAY_MS. Qt hides a tooltip 300 ms after the mouse leaves the
    widget or item that it belongs to; we hide it immediately instead. While a tooltip is
    visible, the style is an event filter of the application, and after each event that
    may start Qt's timer to hide the tooltip, we look for that timer on the tooltip label
    and close the label if the timer is running."""

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
        self._filtering_application_events = False
        self._tooltip_hide_check_pending = False
        self._tooltip_inhibited = False
        # Time since the last tooltip was hidden, invalid if it was hidden by an event in
        # TOOLTIP_INHIBIT_EVENTS:
        self._tooltip_hidden = QtCore.QElapsedTimer()

    def styleHint(self, hint, option=None, widget=None, returnData=None):
        if hint == QtWidgets.QStyle.StyleHint.SH_ToolTip_WakeUpDelay:
            recently_hidden = (
                self._tooltip_hidden.isValid()
                and not self._tooltip_hidden.hasExpired(TOOLTIP_DELAY_MS)
            )
            if QtWidgets.QToolTip.isVisible() or recently_hidden:
                return 0
            return TOOLTIP_DELAY_MS
        if hint == QtWidgets.QStyle.StyleHint.SH_ToolTip_FallAsleepDelay:
            return 0
        return super().styleHint(hint, option, widget, returnData)

    def polish(self, target):
        result = super().polish(target)
        if isinstance(target, QtWidgets.QWidget) and target.inherits('QTipLabel'):
            target.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
            palette = target.palette()
            palette.setColor(QtGui.QPalette.ColorRole.ToolTipText, TOOLTIP_TEXT)
            target.setPalette(palette)
            font = target.font()
            font.setPixelSize(TOOLTIP_FONT_PIXEL_SIZE)
            target.setFont(font)
            # Qt sets the margin of the label to the frame width plus one on every side:
            extra = TOOLTIP_PADDING_X - TOOLTIP_PADDING_Y
            target.setContentsMargins(extra, 0, extra, 0)
            target.installEventFilter(self)
        return result

    def pixelMetric(self, metric, option=None, widget=None):
        if metric in self.ICON_SIZE_METRICS:
            return ICON_SIZE
        if metric == QtWidgets.QStyle.PixelMetric.PM_ToolTipLabelFrameWidth:
            return TOOLTIP_PADDING_Y - 1
        return super().pixelMetric(metric, option, widget)

    def drawPrimitive(self, element, option, painter, widget=None):
        State = QtWidgets.QStyle.StateFlag
        if element == QtWidgets.QStyle.PrimitiveElement.PE_PanelTipLabel:
            painter.save()
            painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
            painter.setPen(QtGui.QPen(TOOLTIP_BORDER, 1))
            painter.setBrush(TOOLTIP_BACKGROUND)
            # The border is drawn centred on the edge of the rectangle:
            rect = QtCore.QRectF(option.rect).adjusted(0.5, 0.5, -0.5, -0.5)
            painter.drawRoundedRect(rect, TOOLTIP_CORNER_RADIUS, TOOLTIP_CORNER_RADIUS)
            painter.restore()
        elif (
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

    def eventFilter(self, watched, event):
        event_type = event.type()
        if event_type == QtCore.QEvent.Type.Show and watched.inherits('QTipLabel'):
            if not self._filtering_application_events:
                QtWidgets.QApplication.instance().installEventFilter(self)
                self._filtering_application_events = True
        elif event_type == QtCore.QEvent.Type.Hide and watched.inherits('QTipLabel'):
            if self._filtering_application_events:
                QtWidgets.QApplication.instance().removeEventFilter(self)
                self._filtering_application_events = False
                if self._tooltip_inhibited:
                    self._tooltip_hidden.invalidate()
                else:
                    self._tooltip_hidden.start()
                self._tooltip_inhibited = False
        elif event_type in TOOLTIP_INHIBIT_EVENTS:
            self._tooltip_inhibited = True
        elif event_type in TOOLTIP_HIDE_EVENTS and not self._tooltip_hide_check_pending:
            # Qt's own event filter and event handlers run after this one:
            self._tooltip_hide_check_pending = True
            QtCore.QTimer.singleShot(0, self._close_hiding_tooltip)
        return False

    def _close_hiding_tooltip(self):
        self._tooltip_hide_check_pending = False
        if not QtWidgets.QToolTip.isVisible():
            # The tooltip label was deleted without being hidden first:
            if self._filtering_application_events:
                QtWidgets.QApplication.instance().removeEventFilter(self)
                self._filtering_application_events = False
            return
        dispatcher = QtCore.QAbstractEventDispatcher.instance()
        for widget in QtWidgets.QApplication.topLevelWidgets():
            if widget.inherits('QTipLabel') and widget.isVisible():
                timers = dispatcher.registeredTimers(widget)
                if any(t.interval == QT_TOOLTIP_HIDE_DELAY_MS for t in timers):
                    widget.close()
                    widget.deleteLater()


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


def _set_color_scheme(qapplication):
    """Set the colour scheme of the application to the value of the labconfig key [gui]
    color_scheme, which is system, light or dark. Setting the colour scheme requires Qt
    6.8 or later, and with Qt 5 or an earlier Qt 6 the key is ignored."""
    style_hints = qapplication.styleHints()
    if not hasattr(style_hints, 'setColorScheme'):
        return
    color_scheme = LabConfig().get('gui', 'color_scheme', fallback='system')
    try:
        name = COLOR_SCHEMES[color_scheme.lower()]
    except KeyError:
        msg = "Invalid color_scheme in labconfig: %s. Must be system, light or dark"
        warnings.warn(msg % color_scheme)
        return
    style_hints.setColorScheme(getattr(QtCore.Qt.ColorScheme, name))


def setup_application(qapplication):
    """Set the colour scheme of the application from the labconfig (see
    _set_color_scheme()), its style to FusionStyle and its font to the bundled Ubuntu
    font at FONT_PIXEL_SIZE, and set the palettes of some widget classes (see
    _class_palettes()). Call this after making the QApplication and after setting any
    application style sheet, and before making any widget: setting a style or a style
    sheet gives the widget classes the fonts of the platform theme again."""
    load_fonts()
    _set_color_scheme(qapplication)
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

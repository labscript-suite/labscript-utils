#####################################################################
#                                                                   #
# /splash.py                                                        #
#                                                                   #
# Copyright 2018, Christopher Billington                            #
#                                                                   #
# This file is part of labscript_utils, in the labscript suite      #
# (see http://labscriptsuite.org), and is licensed under the        #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################

import sys
from labscript_utils import dedent

try:
    from qtutils.qt import QtWidgets, QtCore, QtGui, QT_ENV
except ImportError as e:
    if 'DLL load failed' in str(e):
        msg = """Failed to load Qt DLL. This can be caused by application shortcuts
            not being configured to activate conda environments. Try running the
            following from within the activated conda environment to fix the shortcuts:

                desktop-app install blacs lyse runmanager runviewer"""
        raise ImportError(dedent(msg))
    raise
    
Qt = QtCore.Qt

# These are default in Qt6 and print a warning if set
if QT_ENV == 'PyQt5':
    # Set auto high-DPI scaling - this ensures pixel metrics are scaled
    # appropriately so that we don't get a weird mix of large fonts and small
    # everything else on High DPI displays:
    QtWidgets.QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    # Use high res pixmaps if available, instead of rendering at low resolution and
    # upscaling:
    QtWidgets.QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)


class Splash(QtWidgets.QFrame):
    w = 250
    h = 230
    imwidth = 150
    imheight = 150
    alpha = 0.875
    icon_frac = 0.65
    BG = '#ffffff'
    FG = '#000000'

    def __init__(self, imagepath):
        self.qapplication = QtWidgets.QApplication.instance()
        if self.qapplication is None:
            self.qapplication = QtWidgets.QApplication(sys.argv)
        super().__init__()
        self.icon = QtGui.QPixmap()
        self.icon.load(imagepath)
        if self.icon.isNull():
            raise ValueError("Invalid image file: {}.\n".format(imagepath))
        self.icon = self.icon.scaled(
            self.imwidth, self.imheight, Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.text = 'Loading'
        self.setWindowFlags(Qt.SplashScreen)
        self.setWindowOpacity(self.alpha)
        self.label = QtWidgets.QLabel(self.text)
        self.setStyleSheet(f"color: {self.FG}; background-color: {self.BG}; font-size: 10pt")
        # Frame not necessary on macos, and looks ugly.
        if sys.platform != 'darwin':
            self.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.label.setWordWrap(True)
        self.label.setAlignment(Qt.AlignCenter)
        self.resize(self.w, self.h)

        image_label = QtWidgets.QLabel()
        image_label.setPixmap(self.icon)
        image_label.setAlignment(Qt.AlignCenter)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(image_label)
        layout.addWidget(self.label)

        self._paint_pending = False

    def paintEvent(self, event):
        self._paint_pending = False
        return super().paintEvent(event)

    def update_text(self, text):
        self.text = text
        self.label.setText(text)
        self._paint_pending = True
        while self._paint_pending:
            QtCore.QCoreApplication.processEvents(QtCore.QEventLoop.AllEvents)
            QtCore.QCoreApplication.sendPostedEvents()


if __name__ == '__main__':
    import time
    icon = '../../runmanager/runmanager/runmanager.svg'
    splash = Splash(icon)
    splash.show()
    time.sleep(1)
    splash.update_text('frombulating the dooberwhackies')
    time.sleep(1)
    splash.update_text(
        'The quick brown fox jumped over the lazy dog to get to the other side'
    )
    time.sleep(1)
    splash.hide()

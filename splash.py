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
    from qtutils.qt import QtWidgets, QtCore, QtGui
except ImportError as e:
    if 'DLL load failed' in str(e):
        msg = """Failed to load Qt DLL. This can be caused by application shortcuts
            not being configured to activate conda environments. Try running the
            following from within the activated conda environment to fix the shortcuts:

                python -m labscript_utils.winshell --fix-shortcuts.

            You may then need to unpin and re-pin any shortcuts pinned to the
            taskbar."""
        raise ImportError(dedent(msg))
    raise
    
Qt = QtCore.Qt


class Splash(QtWidgets.QFrame):
    w = 250
    h = 230
    imwidth = 150
    imheight = 150
    alpha = 0.875
    icon_frac = 0.65
    BG = '#ffffff'

    def __init__(self, imagepath):
        self.qapplication = QtWidgets.QApplication.instance()
        if self.qapplication is None:
            self.qapplication = QtWidgets.QApplication(sys.argv)
        QtWidgets.QFrame.__init__(self)
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
        self.setStyleSheet("background-color: %s; font-size: 10pt" % self.BG)
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

        center_point = QtWidgets.QDesktopWidget().availableGeometry().center()
        x0, y0 = center_point.x(), center_point.y()
        self.move(x0 - self.w / 2, y0 - self.h / 2)
        self._first_paint_complete = False

    def paintEvent(self, event):
        result = QtWidgets.QFrame.paintEvent(self, event)
        if not self._first_paint_complete:
            self._first_paint_complete = True
            self.qapplication.quit()
        return result

    def show(self):
        QtWidgets.QFrame.show(self)
        self.update_text(self.text)

    def update_text(self, text):
        self.text = text
        self.label.setText(text)
        # If we are not visible yet, exec until we are painted.
        if not self._first_paint_complete:
            self.qapplication.exec_()
        else:
            self.repaint()


if __name__ == '__main__':
    import time

    MACOS = sys.platform == 'darwin'
    WINDOWS = sys.platform == 'win32'
    LINUX = sys.platform.startswith('linux')

    if MACOS:
        icon = '/Users/bilbo/tmp/runmanager/runmanager.svg'
    elif LINUX:
        icon = '/home/bilbo/labscript_suite/runmanager/runmanager.svg'
    elif WINDOWS:
        icon = R'C:\labscript_suite\runmanager\runmanager.svg'

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

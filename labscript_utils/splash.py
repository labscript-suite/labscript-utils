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

                desktop-app install blacs lyse runmanager runviewer"""
        raise ImportError(dedent(msg))
    raise
    
Qt = QtCore.Qt


def configure_qapplication(qapplication):
    """Apply labscript-wide QApplication configuration."""
    qapplication.setAttribute(Qt.AA_DontShowIconsInMenus, False)
    if sys.platform == 'darwin':
        icon_path = qapplication.property('_labscript_icon_path')
        if icon_path:
            icon = QtGui.QIcon(icon_path)
            if not icon.isNull():
                qapplication.setWindowIcon(icon)
        if qapplication.property('_labscript_qapplication_configured'):
            return qapplication
        # Native macOS widget styling makes many Qt controls look inconsistent
        # with the rest of the suite. Use Qt's own style, but preserve the
        # current palette so dark/light appearance still follows the active
        # theme.
        palette = QtGui.QPalette(qapplication.palette())
        style = QtWidgets.QStyleFactory.create('Fusion')
        if style is not None:
            qapplication.setStyle(style)
            qapplication.setPalette(palette)
    elif qapplication.property('_labscript_qapplication_configured'):
        return qapplication
    qapplication.setProperty('_labscript_qapplication_configured', True)
    return qapplication

def get_qapplication(argv=None, application_name=None, icon_path=None):
    qapplication = QtWidgets.QApplication.instance()

    if qapplication is None:
        argv = sys.argv if argv is None else argv
        if application_name is not None:
            # Create a new argv so QApplication can alter it without mutating sys.argv.
            argv = [application_name] + argv[1:]

        qapplication = QtWidgets.QApplication(argv)

    if icon_path is not None:
        qapplication.setProperty('_labscript_icon_path', icon_path)
    return configure_qapplication(qapplication)


class Splash(QtWidgets.QFrame):
    w = 250
    h = 230
    imwidth = 150
    imheight = 150
    alpha = 0.875
    icon_frac = 0.65
    BG = '#ffffff'
    FG = '#000000'

    def __init__(self, icon_path, application_name=None):
        self.qapplication = get_qapplication(
            application_name=application_name, icon_path=icon_path
        )
        super().__init__()
        self.icon = QtGui.QPixmap()
        self.icon.load(icon_path)
        if self.icon.isNull():
            raise ValueError("Invalid image file: {}.\n".format(icon_path))
        self.icon = self.icon.scaled(
            self.imwidth, self.imheight, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        )
        self.text = 'Loading'
        self.setWindowFlags(Qt.WindowType.SplashScreen)
        self.setWindowOpacity(self.alpha)
        self.label = QtWidgets.QLabel(self.text)
        self.setStyleSheet(f"color: {self.FG}; background-color: {self.BG}; font-size: 10pt")
        # Frame not necessary on macos, and looks ugly.
        if sys.platform != 'darwin':
            self.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.label.setWordWrap(True)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.resize(self.w, self.h)

        image_label = QtWidgets.QLabel()
        image_label.setPixmap(self.icon)
        image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

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
            QtCore.QCoreApplication.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents)
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

import sys
if 'PySide' in sys.modules:
    from PySide.QtCore import *
    from PySide.QtGui import *
else:
    from PyQt4.QtCore import *
    from PyQt4.QtGui import *

from qtutils import *

class ElideQLabel(QLabel):
    """A QLabel that supports eliding text"""
    def __init__(self, *args, **kwargs):
        QLabel.__init__(self, *args, **kwargs)
        self.setElideMode(Qt.ElideNone)

    def elideMode(self):
        return self._elideMode

    def setElideMode(self, elideMode):
        if not isinstance(elideMode, Qt.TextElideMode):
            raise TypeError("Argument must be of type Qt.TextElideMode")
        if elideMode == Qt.ElideMiddle:
            raise NotImplementedError("The hack being used to elidetext does not work for ElideMiddle")
        self._elideMode = elideMode

    def paintEvent(self, event):

        ELLIPSIS = u'\u2026'

        text_width = QLabel.minimumSizeHint(self)
        label_width = self.width()
        if label_width > text_width:
            # Render normally:
            return QLabel.paintEvent(self, event)

        # Save the alignment, so that we can temporarily change it and change it back:
        alignment = self.alignment()
        if self.elideMode() == Qt.ElideRight:
            self.setAlignment(Qt.AlignLeft)
        elif self.elideMode() == Qt.ElideLeft:
            self.setAlignment(Qt.AlignRight)

        print('here')
        result = QLabel.paintEvent(self, event)

        # restore original alignment:
        self.setAlignment(alignment)



        # Otherwise, set alignment according to 
        # painter = QPainter(self)
        # metrics = QFontMetrics(self.font())
        # elided = metrics.elidedText(self.text(), self._elideMode, self.width())
        # painter.drawText(self.rect(), Qt.AlignRight, self.text())

    def minimumSizeHint(self):
        actual_minimum_size = QLabel.minimumSizeHint(self)
        if self._elideMode == Qt.ElideNone:
            return actual_minimum_size
        else:
            # No minimum width:
            return QSize(0, actual_minimum_size.height())


if __name__ == '__main__':
    # test:
    
    test_text = "The <b>quick</b> brown fox <b>jumped over the lazy dog</b>"
    app = QApplication(sys.argv)
    window = QWidget()
    layout = QVBoxLayout(window)
    # regular = QLabel("regular label: " + test_text)
    elide_none = ElideQLabel("ElideNone: " + test_text)
    elide_left = ElideQLabel("ElideLeft: " + test_text)
    elide_right = ElideQLabel("ElideRight: " + test_text)

    # elide_none.setElideMode(Qt.ElideNone)
    elide_left.setElideMode(Qt.ElideLeft)
    elide_right.setElideMode(Qt.ElideRight)

    # layout.addWidget(regular)
    # layout.addWidget(elide_none)
    layout.addWidget(elide_left)
    layout.addWidget(elide_right)

    window.show()
    window.resize(50, 50)
    app.exec_()

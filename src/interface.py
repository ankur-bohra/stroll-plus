import sys
import ctypes

from PyQt5.QtGui import (QIcon)
from PyQt5.QtWidgets import (QApplication, QMainWindow, QSystemTrayIcon)


class StrollWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # WINDOW CONFIGURATION        
        self.setWindowTitle(" Stroll")
        appIcon = QIcon("icons/stroll.png")
        # setWindowIcon() should but doesn't apply the icon to the windows taskbar.
        # Windows needs to be told python is hosting another application and python's icon should be not be used.
        # This can be done by changing the Application User Model Id to an arbitary string.
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Stroll")
        # setWindowIcon() will now affect window and taskbar icons.
        self.setWindowIcon(appIcon)
        # Ideal size is fairly subjective, but too small and the application looks too lazy.
        self.resize(900, 450)
        self.setMinimumSize(900, 450)

        # WINDOW FILLING
        self._createStatusBar()
        self._createMenuBar()
        self._createSideBar()
        self._showHome()
    
    def _createMenuBar(): pass
    def _createSideBar(): pass
    def _createStatusBar(): pass
    def _showHome(): pass


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = StrollWindow()
    window.show()

    sys.exit(app.exec_())
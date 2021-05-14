import sys
import ctypes

from threading import Timer
from PyQt5.QtGui import (QIcon)
from PyQt5.QtWidgets import (QApplication, QMainWindow, QSystemTrayIcon)


class StrollWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # WINDOW ATTRIBUTES
        self._statusBarMessage = "Starting up Stroll..." # Used to switch from empty message after tooltips to previous message 

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
    
    def _createStatusBar(self):
        statusBar = self.statusBar()
        statusBar.setSizeGripEnabled(False) # No use of non-functional size grip
        # Status bar is set to an empty string if any element's status tip is displayed, hiding the actual status.
        statusBar.messageChanged.connect(lambda text: text == "" and self._showStatusBarMessage(self._statusBarMessage))
        self._showStatusBarMessage(self._statusBarMessage)

    def _showStatusBarMessage(self, message, duration=-1):
        oldMessage = self._statusBarMessage
        self._statusBarMessage = message
        self.statusBar().showMessage(message)
        
        if duration > 0: # Timer could be called with -1 duration but that would be bad for memory.
            Timer(duration, lambda: self._showStatusBarMessage(oldMessage)).start()

    def _createMenuBar(self): pass
    def _createSideBar(self): pass
    def _showHome(self): pass


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = StrollWindow()
    window.show()

    sys.exit(app.exec_())
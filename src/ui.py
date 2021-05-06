# TODO:
# Check if calendar is linked in sync menu
# Check if meeting is left in meetings menu

import datetime as dt
import sys
from threading import Timer

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QKeySequence, QFontDatabase, QWindow
from PyQt5.QtWidgets import QApplication, QDoubleSpinBox, QLabel, QLineEdit, QMainWindow, QMenu, QAction, QActionGroup, QPushButton, QScrollArea, QStatusBar, QFrame, QMenuBar, QWidgetAction

import linker

class w():
    '''Wrapper class that makes an object's functions chainable
    '''
    def __init__(self,  object):
        '''
        Wraps object.

        Args:
            object(object): The object to wrap
        '''
        self.object = object

    def do(self, func, *args):
        if hasattr(self.object, func):
            try:
                getattr(self.object, func)(*args)
                return self
            except BaseException as e:
                raise e
        else:
            raise AttributeError(func, "is not a member of", self.object)
    
    def get(self):
        return self.object

class Window(QMainWindow):
    """
    Main Window.
    """
    def __init__(self, app):
        super().__init__()
        self.setWindowTitle("Stroll")
        self.setFixedSize(900, 450)
        self.setWindowIcon(QIcon("icons/logo.png"))

        self.meetings = []
        self.application = app
        self.statusBarMessage = "No meetings (0/0)."

        self._createMenuBar()
        self._createBody()
        self._createStatusBar()

    def _createMenuBar(self):
        menuBar = self.menuBar()
        # MEETING MENU
        meetingMenu = QMenu("&Meeting", self, objectName="Meeting")
        meetingMenu.menuAction().setStatusTip("Create or join meetings.")

        # Add meeting actions        
        newMeeting = w(QAction("&New Meeting", self))\
                        .do("setStatusTip", "Create a new meeting.")\
                        .do("setShortcut", QKeySequence("Ctrl+N"))\
                        .do("setShortcutVisibleInContextMenu", True)\
                        .get()
        
        syncMeetings = w(QAction("&Sync Meetings", self))\
                        .do("setEnabled", False)\
                        .get()

        # Join meeting actions
        joinNextMeeting = w(QAction("&Join Next Meeting", self))\
                            .do("setShortcut", QKeySequence("Ctrl+J"))\
                            .do("setShortcutVisibleInContextMenu", True)\
                            .do("setEnabled", False)\
                            .get()

        w(meetingMenu)\
            .do("addActions", (newMeeting, syncMeetings))\
            .do("addSeparator")\
            .do("addAction", joinNextMeeting)

        # JOINING MENU
        joiningMenu = QMenu("&Joining", self, objectName="Joining")
        joiningMenu.menuAction().setStatusTip("Pause automatic joining.")

        paused = w(QAction("&Paused", self, objectName="PauseIndicator"))\
                    .do("setShortcut", QKeySequence("Ctrl+P"))\
                    .do("setShortcutVisibleInContextMenu", True)\
                    .do("setCheckable", True)\
                    .get()
        paused.triggered.connect(lambda: self._changeSchedulerActivity("Pause" if paused.isChecked() else "Resume")) # NOTE: Ran after toggle
        self.findChild(QAction, "PauseIndicator").setStatusTip("Yup")

        shortPauseSubMenu = QMenu("&Briefly Pause", self, objectName="PauseOptions")
        pauseGroup = QActionGroup(self, objectName="PauseGroup")
        pauseGroup.setExclusive(True)
        for pauseTime in (1,5,10):
            suffix = '' if pauseTime == 1  else 's'
            pause = w(QAction(f"Pause for &{pauseTime} minute{suffix}", self))\
                        .do("setCheckable", True)\
                        .do("setActionGroup", pauseGroup)\
                        .get()
            shortPauseSubMenu.addAction(pause)
            pause.triggered.connect(lambda: self._changeSchedulerActivity("Pause", pauseTime))

        customPause = w(QAction("&Set Custom Pause", self))\
                        .do("setCheckable", True)\
                        .do("setActionGroup", pauseGroup)\
                        .get()

        customPauseAcceptor = w(QWidgetAction(self))\
                                .get()
        pauseValue = w(QDoubleSpinBox(self))\
                        .do("setRange", 0, 180)\
                        .do("setSuffix", " minutes")\
                        .do("setDecimals", 2)\
                        .do("setAlignment", Qt.AlignmentFlag.AlignRight)\
                        .do("setValue", 3)\
                        .get()
        customPauseAcceptor.setDefaultWidget(pauseValue)

        customPause.triggered.connect(lambda: self._changeSchedulerActivity("Pause", pauseValue.value()))
        w(shortPauseSubMenu)\
            .do("addSeparator")\
            .do("addActions", (customPause, customPauseAcceptor))

        w(joiningMenu)\
            .do("addAction", paused)\
            .do("addMenu", shortPauseSubMenu)

        # EDIT MENU
        editMenu = QMenu("&Edit", self, objectName="Edit")
        editMenu.menuAction().setStatusTip("Edit preferences and syncing.")

        preferencesSubMenu = QMenu("&Preferences", self, objectName="Preferences")
        settings = w(QAction("&Settings", self))\
                    .do("setShortcut", QKeySequence("Ctrl+,"))\
                    .do("setShortcutVisibleInContextMenu", True)\
                    .get()
        theme = QAction("Color &Theme", self)
        preferencesSubMenu.addActions((settings, theme))

        syncingSubMenu = QMenu("&Syncing", self, objectName="Syncing")

        enableSyncing = w(QAction("&Enable Syncing", self))\
                            .do("setCheckable", True)\
                            .do("setChecked", False)\
                            .do("setEnabled", False)\
                            .get()

        autoSyncSubSubMenu = QMenu("&Automatically Sync", self, objectName="Automatically Sync")
        autoSyncSubSubMenu.setEnabled(False)
        autoSyncGroup = QActionGroup(self)
        autoSyncGroup.setExclusive(True)
        for syncTime in (5,10,30):
            suffix = '' if syncTime == 1  else 's'
            autoSync = w(QAction(f"Sync every &{syncTime} minute{suffix}", self))\
                        .do("setCheckable", True)\
                        .do("setActionGroup", autoSyncGroup)\
                        .get()
            autoSync.triggered.connect(lambda: self._changeSyncDelay(syncTime))
            if syncTime == 10:
                autoSync.setChecked(True)
            autoSyncSubSubMenu.addAction(autoSync)

        customSync = w(QAction("&Set Custom Delay", self))\
                        .do("setCheckable", True)\
                        .do("setActionGroup", autoSyncGroup)\
                        .get()
        customSyncAcceptor = w(QWidgetAction(self))\
                                .get()
        syncValue = w(QDoubleSpinBox(self))\
                        .do("setRange", 5, 60)\
                        .do("setSuffix", " minutes")\
                        .do("setDecimals", 2)\
                        .do("setAlignment", Qt.AlignmentFlag.AlignRight)\
                        .do("setValue", 15)\
                        .get()
        customSyncAcceptor.setDefaultWidget(syncValue)
        customSync.triggered.connect(lambda: self._changeSyncDelay(syncValue.value()))
    
        w(autoSyncSubSubMenu)\
            .do("addSeparator")\
            .do("addActions", (customSync, customSyncAcceptor))

        linkGoogleAccount = QAction("&Link Google Account", self)
        removeAccount = QAction("&Remove Account", self)
        removeAccount.setEnabled(False)

        w(syncingSubMenu)\
            .do("addAction", enableSyncing)\
            .do("addMenu", autoSyncSubSubMenu)\
            .do("addSeparator")\
            .do("addActions", (linkGoogleAccount, removeAccount))

        editMenu.addMenu(preferencesSubMenu)
        editMenu.addMenu(syncingSubMenu)


        # HELP MENU
        helpMenu = QMenu("&Help", self, objectName="Help")
        helpMenu.menuAction().setStatusTip("Learn how to use Stroll.")

        about = QAction("&About", self)
        usage = QAction("&How to Use", self)
        reportBug = QAction("&Report Issue", self)
        credit = QAction(QIcon("icons/GitHub.png"), "@ankur-bohra", self)
        credit.setEnabled(False)

        w(helpMenu)\
            .do("addActions", (about, usage, reportBug))\
            .do("addSeparator")\
            .do("addAction", credit)

        # ADD ALL MENUS
        w(menuBar)\
            .do("addMenu", meetingMenu)\
            .do("addMenu", joiningMenu)\
            .do("addMenu", editMenu)\
            .do("addMenu", helpMenu)\
            .do("setStyleSheet", "background-color: #f0f0f0")

    def _createStatusBar(self):
        statusBar = self.statusBar()
        w(statusBar)\
            .do("setSizeGripEnabled", False)\
            .do("showMessage", self.statusBarMessage)\
            .get()
        statusBar.messageChanged.connect(lambda text: text == "" and statusBar.showMessage(self.statusBarMessage))

    def _showStatusMessage(self, text, time=None):
        oldMessage = self.statusBarMessage
        self.statusBarMessage = text
        self.findChild(QStatusBar).showMessage(text)
        if time:
            Timer(time, lambda: self._showStatusMessage(oldMessage)).start()

    def _createBody(self):
        # Meetings header
        body = QFrame(self)
        body.setFixedSize(900, 450 - self.findChild(QMenuBar).sizeHint().height() - self.statusBar().sizeHint().height())
        body.move(0, self.findChild(QMenuBar).sizeHint().height())

        header = w(QFrame(body))\
            .do("setFixedSize", 900, 50)\
            .do("setStyleSheet","background-color: #fafafa")\
            .get()

        heading = w(QLabel("Meetings", header))\
                    .do("setStyleSheet", '''
                            font-family: Segoe UI Semibold;
                            font-size: 18px;
                            color: #2e2e2e;
                        ''')\
                    .do("setAlignment", Qt.AlignCenter)\
                    .get()
        heading.move(
            round((900 - heading.width())/2),
            round((50 - heading.height())/2)
        )

        separator = self._createHLine("Major", body)
        separator.move(0, 51)

        meetingsScrollable = w(QScrollArea(body))\
                                .do("setFixedSize", 900, body.height()-50)\
                                .do("move", 0, 54)\
                                .do("setWidgetResizable", True)\
                                .do("setStyleSheet", "background-color: #f4f4f4; border-style: none none dotted; border-width:1px")\
                                .do("setVerticalScrollBarPolicy", Qt.ScrollBarPolicy.ScrollBarAlwaysOn)\
                                .do("setHorizontalScrollBarPolicy", Qt.ScrollBarPolicy.ScrollBarAlwaysOff)\
                                .get()

        meetingsContainer = w(QFrame(meetingsScrollable, objectName="MeetingsContainer"))\
                                .do("setStyleSheet", "background-color: black; border-style: none")\
                                .do("setFixedWidth", 900)\
                                .get()

        meetingsScrollable.setWidget(meetingsContainer)

        self._createMeetingCard("Chemistry", dt.datetime.now(), "https://xperientiallearning-org.zoom.us/j/98394275206?pwd=Yi9BQU1VZEpXMnA3UldNZ1h3YUtkQT09")
        self._createMeetingCard("Physics", dt.datetime.now() + dt.timedelta(minutes=67), "https://xperientiallearning-org.zoom.us/j/98394275206?pwd=Yi9BQU1VZEpXMnA3UldNZ1h3YUtkQT09")
        self._createMeetingCard("Maths", dt.datetime.now() + dt.timedelta(minutes=127), "https://xperientiallearning-org.zoom.us/j/98394275206?pwd=Yi9BQU1VZEpXMnA3UldNZ1h3YUtkQT09")
        self._createMeetingCard("English", dt.datetime.now() + dt.timedelta(minutes=184), "https://xperientiallearning-org.zoom.us/j/98394275206?pwd=Yi9BQU1VZEpXMnA3UldNZ1h3YUtkQT09")
        self._createMeetingCard("Computer Science", dt.datetime.now() + dt.timedelta(minutes=207), "https://xperientiallearning-org.zoom.us/j/98394275206?pwd=Yi9BQU1VZEpXMnA3UldNZ1h3YUtkQT09")

    def _createMeetingCard(self, name, time, meetingLink):
        self.meetings.append((name, time, meetingLink))
        meetingsContainer = w(self.findChild(QFrame, "MeetingsContainer"))\
                                .do("setFixedHeight", len(self.meetings) * 107)\
                                .get()
        card = w(QFrame(meetingsContainer))\
                .do("setFixedSize", 880, 107)\
                .do("move", 0, (len(self.meetings)-1) * 107)\
                .do("setStyleSheet", "background-color: white")\
                .get()

        name = w(QLabel(name, card))\
                .do("setStyleSheet", '''
                        font-family: Segoe UI Semibold;
                        font-size: 26px;
                        color: #454545;
                    ''')\
                .do("move", 18, 26)\
                .get()

        time = w(QLabel("⏱  " + time.strftime("%I:%M %p").lstrip("0"), card))\
                .do("setStyleSheet", '''
                    font-family: Segoe UI Semibold;
                    font-size: 15px;
                    color: gray;
                ''')\
                .do("move", 17, 65)\
                .get()

        link = w(QLabel(card))\
                .do("setText", f"🔗 <a href='{meetingLink}'> {meetingLink}</a>")\
                .do("setStyleSheet",'''
                    font-family: Segoe UI;
                    font-size: 15px;
                    color: gray;
                ''')\
                .do("setOpenExternalLinks", True)\
                .do("move", 115, 65)\
                .get()

        copyLink = w(QPushButton("📋", card))\
                    .do("setStyleSheet", "font-size: 13px;")\
                    .do("setStatusTip", "Copy meeting link.")\
                    .do("move", 825, 65)\
                    .get()
        copyLink.clicked.connect(lambda: self._copyLink(meetingLink))

        edit = w(QPushButton("Edit", card))\
                .do("setStyleSheet", "font-size: 14px; font-family: Segoe UI")\
                .do("move", 18, 7)\
                .get()
        edit.clicked.connect(lambda: print("Trying to edit"))

        delete = w(QPushButton("Delete", card))\
                    .do("setStyleSheet", "font-size: 14px; font-family: Segoe UI")\
                    .do("move", 54, 7)\
                    .get()
        delete.clicked.connect(lambda: print("Trying to delete"))

        separator = self._createHLine("Minor", card)
        separator.move(0, 105)

    def _createHLine(self, type="Major", parent=None):
        line = w(QFrame(parent or self))\
                .do("setFrameShape", QFrame.HLine)\
                .do("setFrameShadow", QFrame.Shadow.Sunken)\
                .do("setFixedSize", 900, 2)\
                .do("setStyleSheet", f"background-color: {'#dedede' if type == 'Major' else '#dedede'}")\
                .get()
        return line

    def _action_preferences(self):
        return True

    def _copyLink(self, link):
        self.application.clipboard().setText(link)
        self._showStatusMessage("Copied.", 1)

    def _changeSchedulerActivity(self, action, time=-1):
        indicator = self.findChild(QAction, "PauseIndicator")
        if action == "Pause":
            indicator.setChecked(True)
        elif action == "Resume":
            indicator.setChecked(False)
            pauseGroup = self.findChild(QActionGroup, "PauseGroup")
            checkedAction = pauseGroup.checkedAction()
            if checkedAction:
                checkedAction.setChecked(False)
        linker.changeSchedulerActivity(action, time, lambda: indicator.setChecked(not indicator.isChecked()))

    def _changeSyncDelay(self, delay):
        pass

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = Window(app)
    win.show()
    sys.exit(app.exec_() and linker.scheduler.terminate())

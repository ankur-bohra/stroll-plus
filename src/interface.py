import sys
import ctypes

from threading import Timer
from PyQt5.QtGui import (QIcon)
from PyQt5.QtWidgets import (QApplication, QDoubleSpinBox, QMainWindow, QSystemTrayIcon, QMenu, QAction, QActionGroup, QWidgetAction)

def mnemonicTextToPascal(text):
    name = text.replace("&", "") # Strip the ampersand used for mnemonic
    name = name.title() # Capitalize first character of all words
    name = name[0].lower() + name[1:] # Decapitalize first character of string
    name = name.replace(" ", "") # Remove all spaces
    return name

def createMenu(parent, text, statusTip=None, children=[], container=None):
    '''Create a QMenu object with common properties.

    Args:
        parent(QWidget): The parent for the menu.
        text(str): The mnemonic-containing text for the menu. Used to construct the menu objectName in pascal case.
        statusTip(optional, str): The status tip shown on hovering over the menu.
        children(optional, List[QAction | QMenu | str]): A list of actions, menus and "|" (for separators), to add to the menu in the given order.
        container(optional, QWidget): The container for the menu. Must have an addMenu() method.
    '''
    name = mnemonicTextToPascal(text)

    menu = QMenu(text, parent, objectName=name)
    if statusTip:
        menu.setStatusTip(statusTip)
    
    for child in children:
        if child == "|":
            menu.addSeparator()
        elif type(child) == QMenu:
            menu.addMenu(child)
        else:
            menu.addAction(child)

    if container:
        container.addMenu(menu)
    return menu

def createAction(parent, text, trigger=None, checkable=False, checked=False, icon=None):
    '''Create an action with common properties.

    Args:
        parent(QWidget): The parent for the action.
        text(string): The mnemonic-containing action text.
        checkable(optional, bool): Control whether the action is checkable. Defaults to False.
        checked(optional, bool): Conrol whether the action is checked if it is checkable. Defaults to False.
    '''
    action = QAction(text, parent, objectName=mnemonicTextToPascal(text))
    action.setCheckable(checkable)
    if checkable:
        action.setChecked(checked)
    if icon:
        action.setIcon(icon)
    if trigger:
        action.triggered.connect(trigger)
    return action

def createChoiceActionGroup(parent, groupName, choices, default):
    '''Create an action group with checkable actions.

    Args:
        parent(QWidget): The parent for the actions in the action group.
        groupName(str): Name of the action group.
        choices(Dict[str: lambda | function]): Dictionary of choice-onChosen pairs, optionally with an acceptor.
        default(str): The default choice.

    Returns:
        A tuple of all actions in the action group.

    To add a choice that accepts a float, a single pair of the following
    format may be added:
        "ACCEPTOR": {
            "Hint": "Acceptor Hint"         
                    (str): The hint showed above the input field.
            "Range": (minValue, maxValue)   
                    (tuple): The range of the input field.
            "Default": defaultValue,        
                    (optional, float): The default value of the field. Defaults to minValue 
            "Suffix": suffix,               
                    (optional, str): The suffix added to the field.
            "Triggered":  onChosen          
                    (function | lambda): The callback for when the field is chosen.
        }
    The field-accepting choice is always at the end and separated from
    other choices by a separator.
    '''
    actionGroup = QActionGroup(parent, objectName=groupName)
    actionGroup.setExclusive(True)

    actions = ()
    for actionText in choices:
        if actionText != "ACCEPTOR":
            isDefault = actionText.replace("&", "")==default.replace("&", "") # Mnemonic can be omitted while calling
            action = createAction(parent, actionText, choices[actionText], checkable=True, checked=isDefault)
            actionGroup.addAction(action)
            actions += (action,)
    
    # Always add acceptor at end
    if "ACCEPTOR" in choices:
        info = choices["ACCEPTOR"]
        hint, suffix, onChosen = info["Hint"], info["Suffix"], info["Triggered"],
        minValue, maxValue, defaultValue = info["Range"][0], info["Range"][1], info["Default"]
        # Acceptor choice comes before field
        # While WidgetActions do provide a checkable property right out of the box,
        # it looks congested. Hence a separate action using the hint is made.
        action = createAction(parent, hint, onChosen, checkable=True, checked=default=="ACCEPTOR")
        actionGroup.addAction(action)

        # Create input field
        field = QDoubleSpinBox(parent, objectName=action.objectName()+"Field") # Append to given hint e.g. setCustomDurationAcceptor
        field.setRange(minValue, maxValue)
        field.setSuffix(" "+suffix) # Suffix looks better with a space before
        field.setValue(defaultValue)
        fieldWidget = QWidgetAction(parent) # Widgets can only be added using WidgetActions
        fieldWidget.setDefaultWidget(field)

        actions += ("|", action, fieldWidget) # Separator goes before acceptor
    
    return actions

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
        '''Creates the status bar at the bottom of the window.
        
        The status bar is used to display the next meeting and its time if one is pending.
        '''
        statusBar = self.statusBar()
        statusBar.setSizeGripEnabled(False) # No use of non-functional size grip
        # Status bar is set to an empty string if any element's status tip is displayed, hiding the actual status.
        statusBar.messageChanged.connect(lambda text: text == "" and self._showStatusBarMessage(self._statusBarMessage))
        self._showStatusBarMessage(self._statusBarMessage)

    def _showStatusBarMessage(self, message, duration=-1):
        '''Shows a message on the status bar.

        Args:
            message(str): The message to display.
            duration(optional, float): The number of seconds to display the message for, -1 for non-disappearing. Defaults to -1.
        '''
        oldMessage = self._statusBarMessage
        self._statusBarMessage = message
        self.statusBar().showMessage(message)
        
        if duration > 0: # Timer could be called with -1 duration but that would be bad for memory.
            Timer(duration, lambda: self._showStatusBarMessage(oldMessage)).start()

    def _createMenuBar(self):
        '''Creates the menu bar at the top of the window.

        The menu bar provides a native interface for finer control of the application.
        '''
        menubar = self.menuBar()

        # MEETING MENU
        newMeeting = createAction(self, "&New Meeting", self._showMeetingPrompt)
        joinMeeting = createAction(self, "&Join Next Meeting", self._joinMeeting)
        syncMeetings = createAction(self, "&Sync Meetings", self._syncMeetings)
        syncMeetings.setEnabled(False)

        children = [newMeeting, joinMeeting, "|", syncMeetings]
        meetingMenu = createMenu(self, "&Meeting", "Create or join meetings", children=children, container=menubar)

        # JOINING MENU
        pausedButton = createAction(self, "&Paused", lambda: self._changeStatus("Pause"))
        brieflyPause = createMenu(self, "&Briefly Pause", children=createChoiceActionGroup(self, "pauseValues", {
            "Pause for &1 minute": lambda: self._changeStatus("Pause", 1),
            "Pause for &5 minutes": lambda: self._changeStatus("Pause", 5),
            "Pause for &10 minutes": lambda: self._changeStatus("Pause", 10),
            "ACCEPTOR": {
                "Hint": "&Set Custom Pause",
                "Range": (0, 120),
                "Default": 30,
                "Suffix": "mins",
                "Triggered": lambda: self._changeStatus("Pause", self.findChild(QDoubleSpinBox, "setCustomPauseField").value())
            }
        }, default="Pause for 5 minutes"))

        children = [pausedButton, brieflyPause]
        createMenu(self, "&Joining", "Pause automatic joining.", children=children, container=menubar)
        
        # EDIT MENU
        preferences = createMenu(self, "&Preferences", children=[
            createAction(self, "Change Color &Theme", self._changeTheme),
            createAction(self, "Open &Settings", self._showSettings),
        ])

        enableSyncing = createAction(self, "&Enable Syncing", self._toggleSyncing, checkable=True, checked=False)
        enableSyncing.setEnabled(False)
        autoSyncMenu = createMenu(self, "&Automatically Sync", children=createChoiceActionGroup(self, "syncDelay", choices={
            "Sync every 5 minutes": lambda: self._setSyncDelay(5),
            "Sync every 10 minutes": lambda: self._setSyncDelay(10),
            "Sync every 30 minutes": lambda: self._setSyncDelay(30),
            "ACCEPTOR": {
                "Hint": "Set Custom Delay",
                "Range": (1,90),
                "Default": 45,
                "Suffix": "mins",
                "Triggered": lambda: self._setSyncDelay(self.findChild(QDoubleSpinBox, "setCustomDelayField").value())
            }
        }, default="Sync every 10 minutes"))

        linkAccount = createAction(self, "&Link Google Account", self._linkAccount)
        removeAccount = createAction(self, "&Remove Account", self._removeAccount)
        removeAccount.setEnabled(False)

        children = [enableSyncing, autoSyncMenu, "|", linkAccount, removeAccount]
        syncing = createMenu(self, "&Syncing", children=children)

        children = [preferences, syncing]
        createMenu(self, "&Edit", "Edit preferences and syncing.", children, container=menubar)
        # HELP MENU
        about = createAction(self, "&About")
        usage = createAction(self, "&How To Use")
        report = createAction(self, "&Report Issue")
        credit = createAction(self, "@ankur-bohra", icon=QIcon("icons/GitHub.png"))
        credit.setEnabled(False)
        
        children = [about, usage, report, "|", credit]
        createMenu(self, "&Help", children=children, container=menubar)

    def _createSideBar(self): pass
    def _showHome(self): pass
    def _showSettings(self): pass
    def _showMeetingPrompt(self): pass
    def _joinMeeting(self): pass
    def _syncMeetings(self): pass
    def _changeStatus(self, action, duration=-1): pass
    def _showPreferences(self): pass
    def _changeTheme(self): pass
    def _setSyncDelay(self, delay): pass
    def _toggleSyncing(self): pass
    def _linkAccount(self): pass
    def _removeAccount(self): pass


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = StrollWindow()
    window.show()

    sys.exit(app.exec_())
import ctypes
import glob
import sys
from threading import Timer

from PyQt5.QtCore import QRect, QRegExp, QSize, QTime, Qt, pyqtProperty
from PyQt5.QtGui import QIcon, QPixmap, QColor, QRegExpValidator, QValidator
from PyQt5.QtWidgets import (QAction, QActionGroup, QApplication, QDialog, QDialogButtonBox,
                             QDoubleSpinBox, QFormLayout, QFrame, QGridLayout, QHBoxLayout, QInputDialog, QLabel, QLayout, QLineEdit,
                             QMainWindow, QMenu, QMessageBox, QPushButton, QSizePolicy, QSpacerItem, QSystemTrayIcon, QTimeEdit,
                             QVBoxLayout, QWidget, QWidgetAction)


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

def forceAspectRatio(widget, ratio):
    '''Forces a widget to resize with an aspect ratio.

    Args:
        widget(QWidget): The widget that will be resized.
        ratio(float): The ratio of the widget's height to its width.
    '''
    sidebar = widget.parent().findChild(QFrame, "sidebar")
    scale = QSize(100, ratio*100)
    def resizeEvent(event):
        size = QSize(scale)
        size.scale(event.size(), Qt.AspectRatioMode.KeepAspectRatio)
        widget.resize(size)
    # widget.sizeHint = sizeHint
    widget.resizeEvent = resizeEvent

def makeButtonIconDynamic(pushButton, size, ratio):
    '''Allows a QPushButton to resize its icon with the button itself.

    Args:
        pushButton(QPushButton): The button that will resize its icon.
        size(QSize): The size of the icon at any scale. Used to maintain aspect ratio.
        ratio(float): The ratio of the icon size to the button size. This allows "padding" around the icon.
    '''
    oldEvent = pushButton.resizeEvent
    def wrapped(event):
        oldEvent(event)
        iconSize = QSize(size) # Use original pixmap size for scaling.
        iconSize.scale(pushButton.size() * ratio, Qt.KeepAspectRatio) # Icon must be scaled to provide padding
        pushButton.setIconSize(iconSize)
    pushButton.resizeEvent = wrapped

def alphaAwareFill(pixmap, color):
    '''Fills an pixmap with the specified color alpha adjusted.

    Args:
        pixmap(QPixmap): The pixmap to fill with color.
        color(QColor): The color to fill the object with.
    
    Returns:
        The filled pixmap.
    '''
    # Pixmaps are meant for displaying and don't support modification
    # to pixels, while images do.
    image = pixmap.toImage()
    
    for y in range(image.height()):
        for x in range(image.width()):
            color.setAlpha(image.pixelColor(x, y).alpha())
            image.setPixelColor(x, y, color)
    
    pixmap = QPixmap.fromImage(image)
    return pixmap

def createMultiInputDialog(title, parent, standardButtons = None):
    dialog = QDialog(parent)
    dialog.setWindowTitle(" " + title) # Too close by default

    grid = QGridLayout(dialog)
    grid.setContentsMargins(0, 0, 0, 0)
    grid.setSizeConstraint(QGridLayout.SizeConstraint.SetNoConstraint)

    formContainer = QWidget(dialog, objectName="formContainer")
    formContainer.setFixedSize(600, 270) # Window resizes to this size due to grid layout
    formContainer.setContentsMargins(16, 16, 16, 16)
    form = QFormLayout(formContainer)
    form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
    dialog.form = form

    feedback = QLabel(formContainer, objectName="feedback")
    dialog.feedback = feedback

    buttonBox = QDialogButtonBox()
    buttonBox.setContentsMargins(16, 8, 16, 8)
    buttonBox.setAttribute(Qt.WA_StyledBackground, True) # Can't be styled by default
    dialog.buttonBox = buttonBox
    if standardButtons:
        buttonBox.setStandardButtons(standardButtons)

    grid.addWidget(formContainer, 0, 0)
    grid.addWidget(feedback, 1, 0, Qt.AlignmentFlag.AlignHCenter)
    grid.addWidget(buttonBox, 2, 0)

    return dialog

class StrollWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # WINDOW ATTRIBUTES
        self._statusBarMessage = "Starting up Stroll..." # Used to switch from empty message after tooltips to previous message 
        self._activeBoard = None # e.g. calendar, home, ...
        self._meetings = []

        # WINDOW CONFIGURATION        
        self.setWindowTitle(" Stroll")
        appIcon = QIcon("icons/stroll.png")
        # setWindowIcon() should but doesn't apply the icon to the windows taskbar.
        # Windows needs to be told python is hosting another application and python's icon should be not be used.
        # This can be done by changing the Application User Model Id to an arbitary string.
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Stroll")
        # setWindowIcon() will now affect window and taskbar icons.
        self.setWindowIcon(appIcon)
        self.setFixedSize(900, 450)

        # WINDOW FILLING
        self._createStatusBar()
        self._createMenuBar()
        self._createBody()
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
        newMeeting = createAction(self, "&New Meeting", self._showCreationPrompt)
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

    def _createBody(self):
        '''Creates the sidebar and board.
        '''
        sidebar = QFrame(self, objectName="sidebar")

        board = QFrame(self, objectName="board")
        self._board = board

        container = QFrame(self)
        self.setCentralWidget(container)
        # A ratio must be maintained between the sidebar and the board. This
        # can be done using a horizontal layout or a grid. WHile a horizontal 
        # layout seems more intuitive, implementing the ratio is significantly
        # simpler using grids and columnspans.
        grid = QGridLayout(container)
        grid.setSpacing(0) # Grid shouldn't have any gaps inside
        grid.setContentsMargins(0, 0, 0, 0) # or outside
        grid.addWidget(sidebar, 0, 0, 1, 1)
        # Board should have a width ~10x that of the sidebar
        # So it must occupy 10 columns if the sidebar occupies one
        grid.addWidget(board, 0, 1, 1, 10)
        
        self._fillSidebar(sidebar)

    def _fillSidebar(self, sidebar):
        '''Fills the sidebar with functional buttons
        '''
        grid = QGridLayout(sidebar)
        buttons = glob.glob("icons/sidebar/*.png")
        for i in range(len(buttons)):
            buttons[i] = buttons[i].split("\\")[-1][0:-4] # icons/sidebar\\Settings.png -> Settings.png -> Settings

        # All icons are given the same target size, and each icon adjusts according
        # to its own aspect ratio.
        iconToButtonRatio = 0.7
        for button_no in range(len(buttons)):
            name = buttons[button_no]
            # The button holder has the rounded corners and holds the actual push
            # button. It is responsible for handling the resizing.
            button = QPushButton(self, objectName=f"sidebarButton{name}")
            button.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
            button.setProperty("active", False)
            button.setProperty("type", "sidebarButton")
            forceAspectRatio(button, 1)

            # The button switches between premade copies of active and inactive icons.
            pixmap = QPixmap(f"icons/sidebar/{name}.png")
            INACTIVE_BTN_ICON_COLOR = "#707169"
            ACTIVE_BTN_ICON_COLOR = "#3B3C37"
            # Make icons accessible directly from button.
            button.inactiveIcon = QIcon(alphaAwareFill(pixmap, QColor(INACTIVE_BTN_ICON_COLOR)))
            button.activeIcon = QIcon(alphaAwareFill(pixmap, QColor(ACTIVE_BTN_ICON_COLOR)))
            makeButtonIconDynamic(button, pixmap.size(), iconToButtonRatio)
            button.setIcon(button.inactiveIcon) # Default is set separately.
            button.clicked.connect(getattr(self, f"_show{name}"))
            grid.addWidget(button, button_no*2 + 1, 0) # Every odd row is occupied by a button.

        # Grid is made with uniform rows everywhere to maintain even margins.
        for row_no in range(0, len(buttons)*2+1):
            grid.setRowStretch(row_no, 1)

    def _activateSidebarButton(self, name):
        '''Activates the specified button and deactivaties the active button.

        NOTE: This method must be called BEFORE changing the board.
        
        Args:
            name(str): The name of the button to be activated.
        '''
        if name == self._activeBoard:
            # No change required
            return

        button = self.findChild(QPushButton, f"sidebarButton{name}")
        button.setProperty("active", True)
        # Activate new button
        button.setIcon(button.activeIcon)
        button.resize(button.size()) # The changed icon must be scaled to fit the current size
        # Deactivate old button
        if self._activeBoard and self._activeBoard != name:
            oldButton = self.findChild(QPushButton, f"sidebarButton{self._activeBoard}")
            oldButton.setProperty("active", False)
            if oldButton:
                oldButton.setIcon(oldButton.inactiveIcon)
                oldButton.resize(oldButton.size())

        #with open("themes/light_stroll.qss", "r") as stylesheet:
        styleSheet = self.styleSheet()
        self.setStyleSheet("")
        self.setStyleSheet(styleSheet)

    def _clearBoard(self):
        for child in self._board.findChildren(QWidget, options=Qt.FindChildOption.FindDirectChildrenOnly):
            child.deleteLater()

    def _showHome(self):
        self._activateSidebarButton("Home")
        self._clearBoard()
        self._activeBoard = "Home"

        if len(self._meetings) == 0:
            # Show blank new meeting page
            newMeeting = QPushButton(self._board)
            newMeeting.setProperty("type", "boardButton")
            newMeeting.setIcon(QIcon(alphaAwareFill(QPixmap("icons/home/add.png"), QColor("#000000"))))
            newMeeting.setStatusTip("Create a new meeting.")
            newMeeting.setFixedSize(50, 50)
            newMeeting.setIconSize(QSize(50, 50))
            newMeeting.move(375, 160)
            newMeeting.clicked.connect(self._showCreationPrompt)

            label = QLabel("New Meeting", self._board)
            label.setFixedSize(202, 45)
            label.setProperty("type", "boardButtonLabel")
            label.move(300, 220)
            # Segoe UI Semibold 21

    def _showSettings(self):
        self._activateSidebarButton("Settings")
        self._clearBoard()
        self._activeBoard = "Settings"

    def _showCalendar(self):
        self._activateSidebarButton("Calendar")
        self._clearBoard()
        self._activeBoard = "Calendar"

    def _showCreationPrompt(self):
        dialog = createMultiInputDialog("New Meeting", self)
        dialog.setFixedSize(600, 220)
        dialog.buttonBox.setStandardButtons(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)

        linkRegEx = QRegExp(r"(?:https?://)?(?:\w+\.)?zoom\.us/j/(\d{9,11})\?pwd=(\w+)(?:.+)?")
        # (?:https?://)? : optionally allow https:// or http://
        # (?:\w+\.)? : optionally allow subdomain e.g. subdomain.zoom.us => subdomain.
        # zoom\.us/j/ : raw match
        # (\d{9,11}) : meeting id, can be 9-11 digits
        # \?pwd= : raw match NOTE: May be enforced to 32 characters if found to be always true.
        # (\w+): match all alphanumeric characters
        # (?:.+)?: optionally allow instances of #success after link e.g. ?pwd=xxxxxxxxxxxxxxxxxx#success

        title = QLineEdit(placeholderText="(Defaults to meeting id)")
        # Meeting title defaults to meeting id
        title.textChanged.connect(
            lambda text: title.setText(
                # Change to meeting id if 1) Title is empty and 2) Meeting id is found
                # itemAt is a dirty method to get the `link` QLineEdit defined later
                # NOTE: labels are stored as items before corresponding QLineEdits, hence itemAt(3) 
                linkRegEx.cap(1) if (linkRegEx.exactMatch(dialog.form.itemAt(3).widget().text()) and text == "") else text
            )
        )
        dialog.form.addRow("Title:", title)

        link = QLineEdit(placeholderText="(...)zoom.us/j/xxxxxxxxx(x(x))?pwd=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx(...)")
        linkValidator = QRegExpValidator(linkRegEx)
        link.setValidator(linkValidator)
        # Meeting title defaults to meeting id
        link.textChanged.connect(
            lambda text: title.setText(
                # Change to meeting id if 1) Title is empty and 2) Meeting id is found
                linkRegEx.cap(1) if (linkRegEx.exactMatch(text) and title.text() == "") else title.text()
            )
        )
        dialog.form.addRow("Meeting Link:", link)

        time = QTimeEdit(displayFormat="hh:mm:ss AP")
        dialog.form.addRow("Join Time:", time)

        dialog.buttonBox.accepted.connect(
            # Add meeting, destroy dialogue, show home if a valid link is found, all other data will then also be valid.
            # Chaining ors with non-returning functions allows multiple calls in a single statement.
            lambda: self._addMeeting(title.text(), link.text(), time.time()) or dialog.destroy() or self._showHome() if linkRegEx.exactMatch(link.text()) else dialog.feedback.setText("Invalid link. Try again or send a report!")
        )
        dialog.buttonBox.rejected.connect(dialog.destroy)
        dialog.setStyleSheet(self.styleSheet())
        dialog.show()

    def _addMeeting(self, title, link, time):
        pass
    
    def _joinMeeting(self): pass
    def _syncMeetings(self): pass
    def _changeStatus(self, action, duration=-1): pass
    def _changeTheme(self): pass
    def _setSyncDelay(self, delay): pass
    def _toggleSyncing(self): pass
    def _linkAccount(self): pass
    def _removeAccount(self): pass


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = StrollWindow()
    with open("themes/light_stroll.qss", "r") as stylesheet:
        window.setStyleSheet(stylesheet.read())
    window.show()
    sys.exit(app.exec_())
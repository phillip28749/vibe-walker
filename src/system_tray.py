from PyQt5.QtWidgets import QSystemTrayIcon, QMenu, QAction
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QObject, pyqtSignal
from activity_bridge import ActivityBridge


class SystemTray(QObject):
    """System tray icon with reactive mode toggle"""

    reactive_mode_changed = pyqtSignal(bool)
    exit_requested = pyqtSignal()

    def __init__(self, config):
        super().__init__()
        self.config = config

        # Load icons
        self.icon_active = QIcon("icons/minion_active.png")
        self.icon_inactive = QIcon("icons/minion_inactive.png")

        # Create system tray icon
        self.tray_icon = QSystemTrayIcon()

        # Create menu
        self._create_menu()

        # Set initial icon
        self.update_icon()

        # Show tray icon
        self.tray_icon.show()

    def _create_menu(self):
        """Create system tray context menu"""
        menu = QMenu()

        # Reactive mode toggle
        self.reactive_action = QAction("Reactive Mode", menu)
        self.reactive_action.setCheckable(True)
        self.reactive_action.setChecked(self.config.reactive_mode_enabled)
        self.reactive_action.triggered.connect(self.on_reactive_mode_toggled)
        menu.addAction(self.reactive_action)

        menu.addSeparator()

        # Exit action
        exit_action = QAction("Exit", menu)
        exit_action.triggered.connect(self.on_exit)
        menu.addAction(exit_action)

        self.tray_icon.setContextMenu(menu)

    def on_reactive_mode_toggled(self, enabled):
        """Handle reactive mode toggle"""
        self.config.reactive_mode_enabled = enabled
        self.config.save()
        self.update_icon()

        # Post Pygame events
        if enabled:
            ActivityBridge.post_show_minion()
        else:
            ActivityBridge.post_hide_minion()

        self.reactive_mode_changed.emit(enabled)

    def on_exit(self):
        """Handle exit request"""
        self.exit_requested.emit()

    def update_icon(self):
        """Update icon based on reactive mode state"""
        if self.config.reactive_mode_enabled:
            self.tray_icon.setIcon(self.icon_active)
        else:
            self.tray_icon.setIcon(self.icon_inactive)

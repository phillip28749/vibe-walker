import pygame
from PyQt5.QtCore import QObject, pyqtSlot

# Define custom Pygame event types
CLAUDE_STARTED = pygame.USEREVENT + 1
CLAUDE_STOPPED = pygame.USEREVENT + 2
SHOW_MINION = pygame.USEREVENT + 3
HIDE_MINION = pygame.USEREVENT + 4
ACTION_NEEDED = pygame.USEREVENT + 5
ACTION_HANDLED = pygame.USEREVENT + 6


class ActivityBridge(QObject):
    """Bridges Qt signals to Pygame events (thread-safe)"""

    def __init__(self, activity_monitor):
        super().__init__()
        self.monitor = activity_monitor

        # Connect Qt signals to event posters
        self.monitor.activity_started.connect(self.on_activity_started)
        self.monitor.activity_stopped.connect(self.on_activity_stopped)
        self.monitor.action_needed_started.connect(self.on_action_needed)
        self.monitor.action_needed_stopped.connect(self.on_action_handled)

    @pyqtSlot()
    def on_activity_started(self):
        """Claude Code query started"""
        pygame.event.post(pygame.event.Event(CLAUDE_STARTED))

    @pyqtSlot()
    def on_activity_stopped(self):
        """Claude Code query finished"""
        pygame.event.post(pygame.event.Event(CLAUDE_STOPPED))

    @pyqtSlot()
    def on_action_needed(self):
        """User action needed (permission, approval, etc.)"""
        pygame.event.post(pygame.event.Event(ACTION_NEEDED))

    @pyqtSlot()
    def on_action_handled(self):
        """User action completed"""
        pygame.event.post(pygame.event.Event(ACTION_HANDLED))

    @staticmethod
    def post_show_minion():
        """Post event to show minion"""
        pygame.event.post(pygame.event.Event(SHOW_MINION))

    @staticmethod
    def post_hide_minion():
        """Post event to hide minion"""
        pygame.event.post(pygame.event.Event(HIDE_MINION))

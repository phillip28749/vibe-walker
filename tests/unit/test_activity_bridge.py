import pytest
import pygame
from PyQt5.QtCore import QObject, pyqtSignal
from src.activity_bridge import (
    ActivityBridge,
    CLAUDE_STARTED,
    CLAUDE_STOPPED,
    SHOW_MINION,
    HIDE_MINION,
    ACTION_NEEDED,
    ACTION_HANDLED,
)


class MockActivityMonitor(QObject):
    """Mock activity monitor for testing"""
    activity_started = pyqtSignal()
    activity_stopped = pyqtSignal()
    action_needed_started = pyqtSignal()
    action_needed_stopped = pyqtSignal()


@pytest.fixture(scope="module")
def pygame_init():
    pygame.init()
    yield
    pygame.quit()


def test_activity_started_posts_pygame_event(qtbot, pygame_init):
    """Activity started signal posts CLAUDE_STARTED event"""
    monitor = MockActivityMonitor()
    bridge = ActivityBridge(monitor)

    # Clear event queue
    pygame.event.clear()

    # Emit signal
    monitor.activity_started.emit()

    # Process Qt events
    qtbot.wait(10)

    # Check Pygame event queue
    events = pygame.event.get(CLAUDE_STARTED)
    assert len(events) == 1


def test_activity_stopped_posts_pygame_event(qtbot, pygame_init):
    """Activity stopped signal posts CLAUDE_STOPPED event"""
    monitor = MockActivityMonitor()
    bridge = ActivityBridge(monitor)

    pygame.event.clear()
    monitor.activity_stopped.emit()
    qtbot.wait(10)

    events = pygame.event.get(CLAUDE_STOPPED)
    assert len(events) == 1


def test_post_show_minion_static_method(pygame_init):
    """Static method posts SHOW_MINION event"""
    pygame.event.clear()
    ActivityBridge.post_show_minion()
    events = pygame.event.get(SHOW_MINION)
    assert len(events) == 1


def test_post_hide_minion_static_method(pygame_init):
    """Static method posts HIDE_MINION event"""
    pygame.event.clear()
    ActivityBridge.post_hide_minion()
    events = pygame.event.get(HIDE_MINION)
    assert len(events) == 1


def test_action_needed_posts_pygame_event(qtbot, pygame_init):
    """Action-needed signal posts ACTION_NEEDED event"""
    monitor = MockActivityMonitor()
    bridge = ActivityBridge(monitor)

    pygame.event.clear()
    monitor.action_needed_started.emit()
    qtbot.wait(10)

    events = pygame.event.get(ACTION_NEEDED)
    assert len(events) == 1


def test_action_handled_posts_pygame_event(qtbot, pygame_init):
    """Action-handled signal posts ACTION_HANDLED event"""
    monitor = MockActivityMonitor()
    bridge = ActivityBridge(monitor)

    pygame.event.clear()
    monitor.action_needed_stopped.emit()
    qtbot.wait(10)

    events = pygame.event.get(ACTION_HANDLED)
    assert len(events) == 1

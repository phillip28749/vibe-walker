from unittest.mock import Mock, patch

from src.mob_manager import MobManager


class DummyMonitor:
    def __init__(self):
        self.active_instance_count_changed = Mock()


class DummySignal:
    def __init__(self):
        self.callback = None

    def connect(self, callback):
        self.callback = callback


class DummyActivityMonitor:
    def __init__(self):
        self.active_instance_count_changed = DummySignal()


class DummyConfig:
    reactive_mode_enabled = True
    behavior_mode = "vibe"
    sprite_size = 64
    pygame_fps = 60
    animation_fps = 7
    movement_speed_px = 2
    dragged_animation_enabled = False
    random_spawn_enabled = False


def test_target_companion_count_tracks_extra_instances(qtbot):
    config = DummyConfig()
    monitor = DummyActivityMonitor()
    manager = MobManager(config, monitor)
    manager.reconcile_timer.stop()

    manager.active_instance_count = 1
    assert manager._target_companion_count() == 0

    manager.active_instance_count = 3
    assert manager._target_companion_count() == 2


def test_reconcile_companions_creates_and_removes_windows(qtbot):
    config = DummyConfig()
    monitor = DummyActivityMonitor()
    manager = MobManager(config, monitor)
    manager.reconcile_timer.stop()

    fake_window_1 = Mock()
    fake_window_2 = Mock()
    fake_window_1.is_fading.return_value = False
    fake_window_2.is_fading.return_value = False
    fake_window_1.window_closed = Mock()
    fake_window_2.window_closed = Mock()

    with patch("src.mob_manager.CompanionWindow", side_effect=[fake_window_1, fake_window_2]):
        manager.active_instance_count = 3
        manager._reconcile_companions()

    assert manager.companion_windows == [fake_window_1, fake_window_2]
    fake_window_1.show.assert_called_once()
    fake_window_2.show.assert_called_once()

    manager.active_instance_count = 1
    manager._reconcile_companions()

    fake_window_2.begin_fade_out.assert_called_once()
    fake_window_1.begin_fade_out.assert_called_once()
    assert manager.companion_windows == [fake_window_1, fake_window_2]

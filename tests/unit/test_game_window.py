import pytest
from unittest.mock import Mock, patch, MagicMock
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from src.game_window import GameWindow
from src.state_machine import State, StateMachine
from src.config import Config


@pytest.fixture
def mock_config():
    """Mock configuration object"""
    config = Mock(spec=Config)
    config.sprite_size = 64
    config.pygame_fps = 60
    config.animation_fps = 7
    config.drag_transition_fps = 14
    config.idle_to_walking_fps = 14
    config.movement_speed_px = 2
    config.drop_duration_ms = 500
    config.random_spawn_enabled = False
    config.baseline_y_offset = 50
    config.walk_on_windows_enabled = True
    config.walk_freely = True
    return config


@pytest.fixture
def qapp():
    """Ensure QApplication exists for tests"""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def mock_pygame():
    """Mock Pygame module"""
    with patch('src.game_window.pygame') as mock_pg:
        # Mock pygame.display
        mock_pg.display.init = Mock()
        mock_pg.display.set_mode = Mock(return_value=Mock())
        mock_pg.display.flip = Mock()
        mock_pg.NOFRAME = 0

        # Mock pygame.time
        mock_pg.time.Clock = Mock(return_value=Mock())
        mock_pg.time.get_ticks = Mock(return_value=0)

        # Mock pygame.event
        mock_pg.event.get = Mock(return_value=[])

        # Mock pygame.sprite
        mock_pg.sprite.Group = Mock(return_value=Mock())

        # Mock pygame.quit
        mock_pg.quit = Mock()

        yield mock_pg


def test_window_initialization(qapp, mock_config, mock_pygame):
    """GameWindow initializes without errors"""
    state_machine = StateMachine()
    with patch('src.game_window.CharacterSprite'), \
         patch('src.game_window.DragHandler'), \
         patch('src.game_window.random.randint', return_value=100):
        window = GameWindow(mock_config, state_machine)
        assert window is not None
        assert window.config == mock_config
        assert window.state_machine == state_machine


def test_window_flags_set_correctly(qapp, mock_config, mock_pygame):
    """Window has correct flags (frameless, always-on-top, tool)"""
    state_machine = StateMachine()
    with patch('src.game_window.CharacterSprite'), \
         patch('src.game_window.DragHandler'), \
         patch('src.game_window.random.randint', return_value=100):
        window = GameWindow(mock_config, state_machine)
        flags = window.windowFlags()
        assert flags & Qt.FramelessWindowHint
        assert flags & Qt.WindowStaysOnTopHint
        assert flags & Qt.Tool


def test_window_size_matches_config(qapp, mock_config, mock_pygame):
    """Window size matches config sprite_size"""
    state_machine = StateMachine()
    with patch('src.game_window.CharacterSprite'), \
         patch('src.game_window.DragHandler'), \
         patch('src.game_window.random.randint', return_value=100):
        window = GameWindow(mock_config, state_machine)
        assert window.width() == 64
        assert window.height() == 64


def test_state_change_to_hidden_hides_window(qapp, mock_config, mock_pygame):
    """Transitioning to HIDDEN state hides window"""
    state_machine = StateMachine()
    with patch('src.game_window.CharacterSprite'), \
         patch('src.game_window.DragHandler'), \
         patch('src.game_window.random.randint', return_value=100):
        window = GameWindow(mock_config, state_machine)

        # Initially show window
        window.show()
        assert window.isVisible()

        # Transition to HIDDEN
        window.on_state_changed(State.HIDDEN)
        assert not window.isVisible()


def test_state_change_to_idle_shows_window(qapp, mock_config, mock_pygame):
    """Transitioning to IDLE state shows window"""
    state_machine = StateMachine()
    with patch('src.game_window.CharacterSprite'), \
         patch('src.game_window.DragHandler'), \
         patch('src.game_window.random.randint', return_value=100):
        window = GameWindow(mock_config, state_machine)

        # Hide window initially
        window.hide()
        assert not window.isVisible()

        # Transition to IDLE
        window.on_state_changed(State.IDLE)
        assert window.isVisible()


def test_close_event_stops_timer_and_quits_pygame(qapp, mock_config, mock_pygame):
    """closeEvent properly cleans up resources"""
    state_machine = StateMachine()
    with patch('src.game_window.CharacterSprite'), \
         patch('src.game_window.DragHandler'), \
         patch('src.game_window.random.randint', return_value=100):
        window = GameWindow(mock_config, state_machine)

        # Mock the timer
        window.timer = Mock()

        # Create mock close event
        mock_event = Mock()

        # Trigger close event
        window.closeEvent(mock_event)

        # Verify cleanup
        window.timer.stop.assert_called_once()
        mock_pygame.quit.assert_called_once()
        mock_event.accept.assert_called_once()


def test_timer_starts_on_initialization(qapp, mock_config, mock_pygame):
    """QTimer starts automatically on initialization"""
    state_machine = StateMachine()
    with patch('src.game_window.CharacterSprite'), \
         patch('src.game_window.DragHandler'), \
         patch('src.game_window.random.randint', return_value=100):
        window = GameWindow(mock_config, state_machine)

        assert window.timer is not None
        assert window.timer.isActive()


def test_baseline_y_calculated_correctly(qapp, mock_config, mock_pygame):
    """Baseline Y position aligns to the monitor work-area bottom (taskbar top)."""
    state_machine = StateMachine()
    with patch('src.game_window.CharacterSprite'), \
         patch('src.game_window.DragHandler'), \
         patch('src.game_window.random.randint', return_value=100), \
         patch('src.game_window.QApplication.primaryScreen') as mock_screen:

        # Mock screen dimensions
        mock_geom = Mock()
        mock_geom.width = Mock(return_value=1920)
        mock_geom.height = Mock(return_value=1080)
        mock_screen.return_value.geometry.return_value = mock_geom

        window = GameWindow(mock_config, state_machine)

        # baseline_y = work_area_bottom - sprite_size
        # baseline_y = 1080 - 64 = 1016
        assert window.baseline_y == 1016


def test_landing_baseline_prefers_window_top_when_below(qapp, mock_config, mock_pygame):
    """Drop landing chooses nearest window top below current position."""
    state_machine = StateMachine()
    with patch('src.game_window.CharacterSprite'), \
         patch('src.game_window.DragHandler'), \
         patch('src.game_window.random.randint', return_value=100):
        window = GameWindow(mock_config, state_machine)

        window.window_size = 64
        window.window_platforms = [
            {"bounds": (100, 500, 500, 900), "hwnd": 1, "z_index": 0}
        ]
        window._get_taskbar_baseline_for_point = Mock(return_value=1000)

        # Window-top landing baseline = 500 - 64 = 436.
        baseline = window._get_landing_baseline(x=220, current_y=200)
        assert baseline == 436


def test_landing_baseline_falls_back_when_window_is_above_mob(qapp, mock_config, mock_pygame):
    """Drop landing ignores window top if it is above current position."""
    state_machine = StateMachine()
    with patch('src.game_window.CharacterSprite'), \
         patch('src.game_window.DragHandler'), \
         patch('src.game_window.random.randint', return_value=100):
        window = GameWindow(mock_config, state_machine)

        window.window_size = 64
        window.window_platforms = [
            {"bounds": (100, 500, 500, 900), "hwnd": 1, "z_index": 0}
        ]
        window._get_taskbar_baseline_for_point = Mock(return_value=1000)

        # Current y is already below window top baseline (436), so land on taskbar baseline.
        baseline = window._get_landing_baseline(x=220, current_y=700)
        assert baseline == 1000


def test_landing_baseline_keeps_surface_at_same_height_inside_inner_lane(qapp, mock_config, mock_pygame):
    """Bouncing at window-top height should keep support while x stays in inner lane."""
    state_machine = StateMachine()
    with patch('src.game_window.CharacterSprite'), \
         patch('src.game_window.DragHandler'), \
         patch('src.game_window.random.randint', return_value=100):
        window = GameWindow(mock_config, state_machine)

        window.window_size = 64
        window.window_platforms = [
            {"bounds": (100, 500, 500, 900), "hwnd": 1, "z_index": 0}
        ]
        window._get_taskbar_baseline_for_point = Mock(return_value=1000)

        # Window-top baseline is 436. At the same Y and within inner lane, keep window support.
        baseline = window._get_landing_baseline(x=220, current_y=436)
        assert baseline == 436


def test_landing_baseline_falls_through_same_height_outside_inner_lane(qapp, mock_config, mock_pygame):
    """At same-height window top, support should drop only after leaving inner x bounds."""
    state_machine = StateMachine()
    with patch('src.game_window.CharacterSprite'), \
         patch('src.game_window.DragHandler'), \
         patch('src.game_window.random.randint', return_value=100):
        window = GameWindow(mock_config, state_machine)

        window.window_size = 64
        window.window_platforms = [
            {"bounds": (100, 500, 500, 900), "hwnd": 1, "z_index": 0}
        ]
        window._get_taskbar_baseline_for_point = Mock(return_value=1000)

        # Inner lane max_x = 500 - 64 = 436, so x=470 is outside inner lane.
        # Even with overlap, same-height support should fall through.
        baseline = window._get_landing_baseline(x=470, current_y=436)
        assert baseline == 1000


def test_get_walk_lane_uses_window_surface(qapp, mock_config, mock_pygame):
    """Walking lane stays on window top after landing there."""
    state_machine = StateMachine()
    with patch('src.game_window.CharacterSprite'), \
         patch('src.game_window.DragHandler'), \
         patch('src.game_window.random.randint', return_value=100):
        window = GameWindow(mock_config, state_machine)

        window.window_size = 64
        window.window_platforms = [
            {"bounds": (100, 500, 500, 900), "hwnd": 7, "z_index": 0}
        ]

        baseline, min_x, max_x = window._get_walk_lane(x=220, current_baseline=436)

        assert baseline == 436
        assert min_x == 100
        assert max_x == 436
        assert window.walking_on_window is True
        assert window.walking_on_window_hwnd == 7


def test_get_walk_lane_falls_back_to_taskbar_when_no_surface(qapp, mock_config, mock_pygame):
    """Walking lane falls back to taskbar when no matching window surface exists."""
    state_machine = StateMachine()
    with patch('src.game_window.CharacterSprite'), \
         patch('src.game_window.DragHandler'), \
         patch('src.game_window.random.randint', return_value=100):
        window = GameWindow(mock_config, state_machine)

        window.walking_on_window = True
        window.walking_on_window_hwnd = 42
        window.window_platforms = []
        window._get_taskbar_baseline_for_point = Mock(return_value=1000)
        window._get_virtual_screen_bounds = Mock(return_value=(0, 0, 1920, 1080))

        baseline, min_x, max_x = window._get_walk_lane(x=220, current_baseline=436)

        assert baseline == 1000
        assert min_x == 0
        assert max_x == 1856
        assert window.walking_on_window is False
        assert window.walking_on_window_hwnd is None


def test_should_drop_from_window_edge_only_on_crossing(qapp, mock_config, mock_pygame):
    """Drop triggers only when moving from inside lane to outside lane."""
    state_machine = StateMachine()
    with patch('src.game_window.CharacterSprite'), \
         patch('src.game_window.DragHandler'), \
         patch('src.game_window.random.randint', return_value=100):
        window = GameWindow(mock_config, state_machine)

        assert window._should_drop_from_window_edge(120, 98, 100, 300) is True
        assert window._should_drop_from_window_edge(280, 302, 100, 300) is True


def test_should_not_drop_when_not_crossing_edge(qapp, mock_config, mock_pygame):
    """No drop when staying inside lane or already outside lane."""
    state_machine = StateMachine()
    with patch('src.game_window.CharacterSprite'), \
         patch('src.game_window.DragHandler'), \
         patch('src.game_window.random.randint', return_value=100):
        window = GameWindow(mock_config, state_machine)

        assert window._should_drop_from_window_edge(150, 170, 100, 300) is False
        assert window._should_drop_from_window_edge(90, 80, 100, 300) is False
        assert window._should_drop_from_window_edge(320, 340, 100, 300) is False


def test_should_drop_when_tracked_window_edge_is_crossed(qapp, mock_config, mock_pygame):
    """Drop should trigger when tracked window walking crosses the lane edge."""
    state_machine = StateMachine()
    with patch('src.game_window.CharacterSprite'), \
         patch('src.game_window.DragHandler'), \
         patch('src.game_window.random.randint', return_value=100):
        window = GameWindow(mock_config, state_machine)

        window.window_size = 64
        window.window_platforms = [
            {"bounds": (100, 500, 500, 900), "hwnd": 99, "z_index": 0}
        ]
        window.walking_on_window = True
        window.walking_on_window_hwnd = 99

        # current_x=434 is still on the window lane; next_x=438 crosses the edge.
        assert window._should_drop_from_window_edge(434, 438, 100, 436) is True


def test_should_not_drop_when_tracked_window_bounces_inside_lane(qapp, mock_config, mock_pygame):
    """A bounce that stays within the window lane should not trigger a fall."""
    state_machine = StateMachine()
    with patch('src.game_window.CharacterSprite'), \
         patch('src.game_window.DragHandler'), \
         patch('src.game_window.random.randint', return_value=100):
        window = GameWindow(mock_config, state_machine)

        window.window_size = 64
        window.window_platforms = [
            {"bounds": (100, 500, 500, 900), "hwnd": 99, "z_index": 0}
        ]
        window.walking_on_window = True
        window.walking_on_window_hwnd = 99

        assert window._should_drop_from_window_edge(430, 432, 100, 436) is False


def test_landing_baseline_accepts_off_center_overlap(qapp, mock_config, mock_pygame):
    """Landing still uses window top when thrown off-center but overlapping."""
    state_machine = StateMachine()
    with patch('src.game_window.CharacterSprite'), \
         patch('src.game_window.DragHandler'), \
         patch('src.game_window.random.randint', return_value=100):
        window = GameWindow(mock_config, state_machine)

        window.window_size = 64
        window.window_platforms = [
            {"bounds": (100, 500, 500, 900), "hwnd": 1, "z_index": 0}
        ]
        window._get_taskbar_baseline_for_point = Mock(return_value=1000)

        # x=470 gives a 30px overlap with the window, enough for support.
        baseline = window._get_landing_baseline(x=470, current_y=200)
        assert baseline == 436


def test_get_current_window_surface_accepts_off_center_overlap(qapp, mock_config, mock_pygame):
    """Walking surface detection should keep support with off-center overlap."""
    state_machine = StateMachine()
    with patch('src.game_window.CharacterSprite'), \
         patch('src.game_window.DragHandler'), \
         patch('src.game_window.random.randint', return_value=100):
        window = GameWindow(mock_config, state_machine)

        window.window_size = 64
        window.window_platforms = [
            {"bounds": (100, 500, 500, 900), "hwnd": 12, "z_index": 0}
        ]

        surface = window._get_current_window_surface(x=470, current_baseline=436)
        assert surface is not None
        assert surface["hwnd"] == 12


def test_get_current_window_surface_accepts_tiny_edge_overlap(qapp, mock_config, mock_pygame):
    """Landing at the very edge should still keep the window surface."""
    state_machine = StateMachine()
    with patch('src.game_window.CharacterSprite'), \
         patch('src.game_window.DragHandler'), \
         patch('src.game_window.random.randint', return_value=100):
        window = GameWindow(mock_config, state_machine)

        window.window_size = 64
        window.window_platforms = [
            {"bounds": (100, 500, 500, 900), "hwnd": 13, "z_index": 0}
        ]

        surface = window._get_current_window_surface(x=497, current_baseline=436)
        assert surface is not None
        assert surface["hwnd"] == 13


def test_get_current_window_surface_rejects_tracked_window_after_vertical_move(qapp, mock_config, mock_pygame):
    """Tracked support should be lost once the window moves away from the mob."""
    state_machine = StateMachine()
    with patch('src.game_window.CharacterSprite'), \
         patch('src.game_window.DragHandler'), \
         patch('src.game_window.random.randint', return_value=100):
        window = GameWindow(mock_config, state_machine)

        window.window_size = 64
        window.walking_on_window = True
        window.walking_on_window_hwnd = 21
        window.window_platforms = [
            {"bounds": (100, 620, 500, 920), "hwnd": 21, "z_index": 0}
        ]

        surface = window._get_current_window_surface(x=220, current_baseline=436)
        assert surface is None


def test_update_sprite_starts_drop_when_window_support_is_lost(qapp, mock_config, mock_pygame):
    """Walking should switch into a drop when the tracked window is no longer under the mob."""
    state_machine = StateMachine()
    with patch('src.game_window.CharacterSprite'), \
         patch('src.game_window.DragHandler'), \
         patch('src.game_window.random.randint', return_value=100):
        window = GameWindow(mock_config, state_machine)

        state_machine.transition_to(State.WALKING)
        window.walking_on_window = True
        window.walking_on_window_hwnd = 21
        window.window_x = 220
        window.baseline_y = 436
        window.walk_direction = 1
        window.walk_frame_counter = 0
        window.walk_frame_update_rate = 999
        window.sprite.playing_drag_to_idle = False
        window.sprite.playing_idle_to_walking = False
        window.sprite.playing_walk_to_idle = False
        window.sprite.playing_idle_to_drag = False
        window._get_current_window_surface = Mock(return_value=None)
        window._start_dropping_from = Mock()
        window.move(220, 436)
        window.timer.stop()

        window._update_sprite()

        window._start_dropping_from.assert_called_once()


def test_is_window_fully_occluded_detects_hidden_window(qapp, mock_config, mock_pygame):
    """A window whose sampled points all land on another window is treated as covered."""
    state_machine = StateMachine()
    with patch('src.game_window.CharacterSprite'), \
         patch('src.game_window.DragHandler'), \
         patch('src.game_window.random.randint', return_value=100):
        window = GameWindow(mock_config, state_machine)

        fake_win32gui = MagicMock()
        fake_win32gui.WindowFromPoint.side_effect = lambda point: 2
        fake_win32gui.GetAncestor.side_effect = lambda hwnd, flag: hwnd

        assert window._is_window_fully_occluded(1, (100, 100, 300, 300), fake_win32gui) is True
        assert window._is_window_fully_occluded(2, (100, 100, 300, 300), fake_win32gui) is False


def test_refresh_active_window_bounds_skips_fully_covered_windows(qapp, mock_config, mock_pygame):
    """Covered windows should not enter the physics platform list."""
    state_machine = StateMachine()
    with patch('src.game_window.CharacterSprite'), \
         patch('src.game_window.DragHandler'), \
         patch('src.game_window.random.randint', return_value=100):
        window = GameWindow(mock_config, state_machine)

        window.window_size = 64
        window.winId = Mock(return_value=99)
        window._get_window_bounds_win32 = Mock(side_effect=lambda hwnd, _: {
            1: (100, 100, 300, 300),
            2: (100, 100, 300, 300),
        }[hwnd])
        window._get_window_z_order_index = Mock(side_effect=lambda hwnd: {2: 0, 1: 1}[hwnd])

        fake_win32gui = MagicMock()
        fake_win32gui.IsWindowVisible.side_effect = lambda hwnd: hwnd in {1, 2}
        fake_win32gui.IsIconic.return_value = False
        fake_win32gui.GetClassName.return_value = "application"
        fake_win32gui.WindowFromPoint.side_effect = lambda point: 2
        fake_win32gui.GetAncestor.side_effect = lambda hwnd, flag: hwnd

        def enum_windows(callback, _):
            callback(1, None)
            callback(2, None)

        fake_win32gui.EnumWindows.side_effect = enum_windows

        mock_windll = MagicMock()
        mock_windll.user32.GetWindowLongW.return_value = 0
        mock_windll.user32.GetWindow.return_value = 0
        mock_windll.dwmapi.DwmGetWindowAttribute.return_value = 1

        with patch.dict('sys.modules', {'win32gui': fake_win32gui}), \
             patch('src.game_window.ctypes.windll', mock_windll):
            window._refresh_active_window_bounds(force=True)

        assert [platform["hwnd"] for platform in window.window_platforms] == [2]

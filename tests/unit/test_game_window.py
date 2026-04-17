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
    config.movement_speed_px = 2
    config.drop_duration_ms = 500
    config.random_spawn_enabled = False
    config.baseline_y_offset = 50
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
    """Baseline Y position calculated from screen height and offset"""
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

        # baseline_y = screen_height - baseline_y_offset - sprite_size
        # baseline_y = 1080 - 50 - 64 = 966
        assert window.baseline_y == 966

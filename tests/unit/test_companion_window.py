from unittest.mock import Mock, patch

from src.companion_window import CompanionWindow
from src.state_machine import State


class DummyConfig:
    sprite_size = 64
    pygame_fps = 60
    animation_fps = 7
    movement_speed_px = 2
    dragged_animation_enabled = False
    random_spawn_enabled = False


def test_companion_switches_to_walking_after_appearing(qtbot):
    config = DummyConfig()

    fake_sprite = Mock()
    fake_sprite._get_sprite_for_state.side_effect = ["appearing-frame", "walking-frame"]
    fake_sprite.update_appearing_frame.return_value = True

    with patch("src.companion_window.CharacterSprite", return_value=fake_sprite), \
         patch("src.companion_window.QApplication.primaryScreen") as mock_screen, \
         patch.object(CompanionWindow, "_render_current_frame"):
        mock_geometry = Mock()
        mock_geometry.left.return_value = 0
        mock_geometry.right.return_value = 500
        mock_geometry.bottom.return_value = 400
        mock_geometry.width.return_value = 500
        mock_screen.return_value.availableGeometry.return_value = mock_geometry

        window = CompanionWindow(config, slot_index=1)
        qtbot.addWidget(window)
        window.timer.stop()
        window.walk_frame_counter = window.animation_frame_update_rate - 1
        window._update_frame()

    assert fake_sprite.set_walk_direction.called
    assert window.lifecycle_state == "walking"
    assert fake_sprite.current_state == State.WALKING
    assert fake_sprite.image == "walking-frame"
    fake_sprite._get_sprite_for_state.assert_called_with(State.WALKING)


def test_companion_starts_with_appearing_animation(qtbot):
    config = DummyConfig()

    fake_sprite = Mock()
    fake_sprite._get_sprite_for_state.return_value = Mock()

    with patch("src.companion_window.CharacterSprite", return_value=fake_sprite), \
         patch("src.companion_window.QApplication.primaryScreen") as mock_screen, \
         patch.object(CompanionWindow, "_render_current_frame"):
        mock_geometry = Mock()
        mock_geometry.left.return_value = 0
        mock_geometry.right.return_value = 500
        mock_geometry.bottom.return_value = 400
        mock_geometry.width.return_value = 500
        mock_screen.return_value.availableGeometry.return_value = mock_geometry

        window = CompanionWindow(config, slot_index=1)
        qtbot.addWidget(window)
        window.timer.stop()

    fake_sprite.reset_appearing_animation.assert_called_once()
    assert window.lifecycle_state == "appearing"
    assert fake_sprite.current_state == State.APPEARING
    fake_sprite._get_sprite_for_state.assert_called_with(State.APPEARING)


def test_companion_begin_fade_out_resets_fade_animation(qtbot):
    config = DummyConfig()

    fake_sprite = Mock()
    fake_sprite._get_sprite_for_state.return_value = Mock()
    fake_sprite.images = {"FADE": ["fade-0"]}

    with patch("src.companion_window.CharacterSprite", return_value=fake_sprite), \
         patch("src.companion_window.QApplication.primaryScreen") as mock_screen, \
         patch.object(CompanionWindow, "_render_current_frame"):
        mock_geometry = Mock()
        mock_geometry.left.return_value = 0
        mock_geometry.right.return_value = 500
        mock_geometry.bottom.return_value = 400
        mock_geometry.width.return_value = 500
        mock_screen.return_value.availableGeometry.return_value = mock_geometry

        window = CompanionWindow(config, slot_index=1)
        qtbot.addWidget(window)
        window.timer.stop()
        window.begin_fade_out()

    fake_sprite.reset_fade_animation.assert_called_once()
    assert window.lifecycle_state == "fading"
    assert fake_sprite.image == "fade-0"

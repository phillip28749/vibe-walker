import pytest
import pygame
from src.drag_handler import DragHandler
from src.state_machine import State


@pytest.fixture(scope="module")
def pygame_init():
    pygame.init()
    yield
    pygame.quit()


def test_drag_starts_on_sprite_click(pygame_init):
    """Clicking sprite starts drag"""
    handler = DragHandler(sprite_size=64, baseline_y=500)

    # Simulate sprite at (100, 500)
    sprite_rect = pygame.Rect(100, 500, 64, 64)

    # Click inside sprite
    result = handler.handle_mouse_down((120, 520), sprite_rect)
    assert result == State.DRAGGED
    assert handler.is_dragging is True


def test_drop_animation_completes(pygame_init):
    """Drop animation returns to baseline"""
    handler = DragHandler(sprite_size=64, baseline_y=500, drop_duration_ms=100)

    # Simulate drag start
    handler.is_dragging = True

    # Simulate drop from y=200
    state = handler.handle_mouse_up(sprite_x=100, sprite_y=200)
    assert state == State.DROPPING

    # Simulate enough frames for bouncing physics to settle.
    x = y = None
    is_complete = False
    current_time = pygame.time.get_ticks()
    for frame in range(240):
        x, y, is_complete = handler.update_drop(current_time + (frame * 16), screen_width=1920, window_size=64)
        if is_complete:
            break

    assert is_complete is True
    assert y == 500


def test_drag_offset_preserved(pygame_init):
    """Drag preserves click offset on sprite"""
    handler = DragHandler(sprite_size=64, baseline_y=500)
    sprite_rect = pygame.Rect(100, 500, 64, 64)

    # Click at specific point on sprite (not center)
    handler.handle_mouse_down((110, 510), sprite_rect)

    # Move mouse
    delta = handler.handle_mouse_motion((150, 550), current_window_pos=(100, 500))

    assert delta is not None
    assert delta == (40, 40)

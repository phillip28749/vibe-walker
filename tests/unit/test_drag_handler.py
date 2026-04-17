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


def test_drag_ignores_click_outside_sprite(pygame_init):
    """Clicking outside sprite doesn't start drag"""
    handler = DragHandler(sprite_size=64, baseline_y=500)
    sprite_rect = pygame.Rect(100, 500, 64, 64)

    # Click outside sprite
    result = handler.handle_mouse_down((50, 50), sprite_rect)
    assert result is None
    assert handler.is_dragging is False


def test_drop_animation_completes(pygame_init):
    """Drop animation returns to baseline"""
    handler = DragHandler(sprite_size=64, baseline_y=500, drop_duration_ms=100)

    # Simulate drag start
    handler.is_dragging = True

    # Simulate drop from y=200
    state = handler.handle_mouse_up(sprite_y=200)
    assert state == State.DROPPING

    # Simulate time passing (beyond drop duration)
    future_time = pygame.time.get_ticks() + 200
    y, is_complete = handler.update_drop(future_time)

    assert is_complete is True
    assert y == 500


def test_drag_offset_preserved(pygame_init):
    """Drag preserves click offset on sprite"""
    handler = DragHandler(sprite_size=64, baseline_y=500)
    sprite_rect = pygame.Rect(100, 500, 64, 64)

    # Click at specific point on sprite (not center)
    handler.handle_mouse_down((110, 510), sprite_rect)

    # Move mouse
    new_pos = handler.handle_mouse_motion((150, 550))

    assert new_pos is not None
    # Offset should be preserved (clicked 10 pixels right, 10 down from sprite origin)
    assert new_pos == (140, 540)

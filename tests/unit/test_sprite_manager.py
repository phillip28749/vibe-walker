import pytest
import pygame
from src.sprite_manager import CharacterSprite
from src.state_machine import State


@pytest.fixture(scope="module")
def pygame_init():
    """Initialize pygame for tests"""
    pygame.init()
    yield
    pygame.quit()


def test_sprite_loads_images(pygame_init):
    """Sprite loads all required images"""
    sprite = CharacterSprite(sprite_size=64)
    assert sprite.images[State.IDLE] is not None
    assert sprite.images[State.WALKING] is not None
    assert sprite.images[State.DRAGGED] is not None


def test_sprite_has_rect(pygame_init):
    """Sprite has bounding rect for collision"""
    sprite = CharacterSprite(sprite_size=64)
    assert sprite.rect is not None
    assert sprite.rect.width == 64
    assert sprite.rect.height == 64


def test_update_state_changes_image(pygame_init):
    """Updating state changes current image"""
    sprite = CharacterSprite(sprite_size=64)

    # Test that WALKING state is set correctly
    sprite.update_state(State.WALKING)
    assert sprite.current_state == State.WALKING
    assert sprite.image is not None

    # Test DRAGGED state
    sprite.update_state(State.DRAGGED)
    assert sprite.current_state == State.DRAGGED
    assert sprite.image is not None


def test_walk_frame_advances(pygame_init):
    """Walk animation frame increments"""
    sprite = CharacterSprite(sprite_size=64)
    sprite.update_state(State.WALKING)

    # Test frame cycles: 0 -> 1 -> 0
    assert sprite.walk_frame == 0
    sprite.update_walk_frame()
    assert sprite.walk_frame == 1
    sprite.update_walk_frame()
    assert sprite.walk_frame == 0


def test_all_states_handled(pygame_init):
    """All State enum values can be set without errors"""
    sprite = CharacterSprite(sprite_size=64)

    # Test all states except HIDDEN
    for state in [State.IDLE, State.WALKING, State.DRAGGED, State.DROPPING]:
        sprite.update_state(state)
        assert sprite.current_state == state
        assert sprite.image is not None, f"State {state} should have an image"

    # Test HIDDEN state
    sprite.update_state(State.HIDDEN)
    assert sprite.current_state == State.HIDDEN

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


def test_animations_use_standard_frame_count(pygame_init):
    """Movement and transition animations render as 16-frame cycles."""
    sprite = CharacterSprite(sprite_size=64)

    assert len(sprite.images[State.WALKING]["right"]) == CharacterSprite.STANDARD_FRAME_COUNT
    assert len(sprite.images[State.WALKING]["left"]) == CharacterSprite.STANDARD_FRAME_COUNT
    assert len(sprite.images[State.WAVING]) == CharacterSprite.STANDARD_FRAME_COUNT
    assert len(sprite.images[State.APPEARING]) == CharacterSprite.STANDARD_FRAME_COUNT
    assert len(sprite.images[State.DRAGGED]) == CharacterSprite.STANDARD_FRAME_COUNT
    assert len(sprite.images["IDLE_TO_WALKING"]) == CharacterSprite.STANDARD_FRAME_COUNT
    assert len(sprite.images["WALK_TO_IDLE"]) == CharacterSprite.STANDARD_FRAME_COUNT
    assert len(sprite.images["DRAG_TO_IDLE"]) == CharacterSprite.STANDARD_FRAME_COUNT
    assert len(sprite.images["IDLE_TO_DRAG"]) == CharacterSprite.STANDARD_FRAME_COUNT


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

    # Test frame cycles through the walking sheet frames.
    assert sprite.walk_frame == 0
    sprite.update_walk_frame()
    assert sprite.walk_frame == 1
    for _ in range(len(sprite.images[State.WALKING]["right"]) - 1):
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


def test_sprite_reuses_cached_images(pygame_init):
    """Sprites with the same config reuse loaded frame data."""
    CharacterSprite._image_cache.clear()

    first = CharacterSprite(sprite_size=64, use_dragged_animation=False)
    second = CharacterSprite(sprite_size=64, use_dragged_animation=False)

    assert first.images is second.images

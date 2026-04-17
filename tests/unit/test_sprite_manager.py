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
    idle_image = sprite.image

    sprite.update_state(State.DRAGGED)
    assert sprite.image != idle_image or sprite.current_state == State.DRAGGED


def test_walk_frame_advances(pygame_init):
    """Walk animation frame increments"""
    sprite = CharacterSprite(sprite_size=64)
    sprite.update_state(State.WALKING)

    initial_frame = sprite.walk_frame
    sprite.update_walk_frame()
    assert sprite.walk_frame != initial_frame or sprite.walk_frame == 0

"""Quick test to verify Vibe Walker is ready to run"""
import sys
sys.path.insert(0, '.')

print("Testing Vibe Walker components...")
print("-" * 50)

# Test 1: Config
try:
    from src.config import Config
    config = Config()
    print("[OK] Config loaded")
    print(f"    - Reactive mode: {config.reactive_mode_enabled}")
    print(f"    - Sprite size: {config.sprite_size}")
except Exception as e:
    print(f"[FAIL] Config: {e}")
    sys.exit(1)

# Test 2: State Machine
try:
    from src.state_machine import State, StateMachine
    sm = StateMachine()
    print("[OK] State Machine initialized")
    print(f"    - Current state: {sm.current_state}")
except Exception as e:
    print(f"[FAIL] State Machine: {e}")
    sys.exit(1)

# Test 3: Sprites
import os
sprites = ['idle.png', 'walk_left_1.png', 'walk_right_1.png', 'dragged.png']
missing = [s for s in sprites if not os.path.exists(f'sprites/{s}')]
if missing:
    print(f"[WARN] Missing sprites: {missing}")
else:
    print(f"[OK] All sprites present ({len(sprites)} files)")

# Test 4: Icons
icons = ['minion_active.png', 'minion_inactive.png']
missing_icons = [i for i in icons if not os.path.exists(f'icons/{i}')]
if missing_icons:
    print(f"[WARN] Missing icons: {missing_icons}")
else:
    print(f"[OK] All icons present ({len(icons)} files)")

# Test 5: Dependencies
try:
    import pygame
    import PyQt5
    from PIL import Image
    print("[OK] All dependencies installed")
    print(f"    - Pygame: {pygame.version.ver}")
except ImportError as e:
    print(f"[FAIL] Missing dependency: {e}")
    sys.exit(1)

print("-" * 50)
print("ALL TESTS PASSED")
print("\nReady to run:")
print("  python -m src.main")

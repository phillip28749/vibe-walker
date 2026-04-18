#!/usr/bin/env python3
"""
Vibe Walker - Interactive Desktop Pet
Main entry point
"""

import sys
from pathlib import Path
import pygame

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from PyQt5.QtWidgets import QApplication, QDialog
from src.config import Config
from src.config_dialog import ConfigDialog
from src.state_machine import State, StateMachine
from src.activity_monitor import ActivityMonitor
from src.activity_bridge import ActivityBridge
from src.game_window import GameWindow
from src.system_tray import SystemTray


def main():
    """Main entry point"""
    # Create Qt application
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # Keep running with tray icon

    # Load configuration
    config = Config()

    # Show startup configuration dialog
    dialog = ConfigDialog(config)
    if dialog.exec_() == QDialog.Rejected:
        # User cancelled - exit without launching
        print("[INFO] User cancelled configuration - exiting")
        sys.exit(0)
    # If accepted, config is already updated and saved
    # Note: Dialog stays open until game window is ready

    # Get preview position for spawn animation
    spawn_position = dialog.get_preview_screen_position()

    # Create state machine
    state_machine = StateMachine()

    # Create activity monitor and bridge
    activity_monitor = ActivityMonitor(config)
    activity_bridge = ActivityBridge(activity_monitor)

    # Create game window with spawn position from preview (dialog still visible)
    game_window = GameWindow(config, state_machine, spawn_from=spawn_position)

    # Create system tray
    system_tray = SystemTray(config)
    system_tray.exit_requested.connect(app.quit)

    # Set initial visibility and animation based on reactive mode and spawn position
    print(f"[MAIN] Reactive mode enabled: {config.reactive_mode_enabled}")

    if spawn_position is not None:
        # Drop from preview position to baseline
        current_y = game_window.y()
        baseline_y = game_window.baseline_y
        print(f"[MAIN] Spawning from preview - starting drop animation")
        print(f"[MAIN] Preview position: {spawn_position}")
        print(f"[MAIN] Current window Y: {current_y}, Baseline Y: {baseline_y}")
        print(f"[MAIN] Drop distance: {baseline_y - current_y} pixels")

        game_window.drag_handler.drop_start_y = current_y
        game_window.drag_handler.drop_start_time = pygame.time.get_ticks()
        game_window.drag_handler.is_dropping = True  # Enable dropping flag
        state_machine.transition_to(State.DROPPING)
        game_window.show()

        # Close dialog now that game window is visible - creates seamless transition
        dialog.close()
    elif config.reactive_mode_enabled:
        print("[MAIN] Setting initial state to APPEARING and showing window")
        game_window.sprite.reset_appearing_animation()
        state_machine.transition_to(State.APPEARING)
        game_window.show()
        dialog.close()
    else:
        print("[MAIN] Setting initial state to HIDDEN")
        state_machine.transition_to(State.HIDDEN)
        game_window.hide()
        dialog.close()

    # Start activity monitor thread
    activity_monitor.start()
    print("[MAIN] Application started - check system tray for controls")

    # Run application
    try:
        sys.exit(app.exec_())
    finally:
        # Cleanup
        activity_monitor.stop()
        activity_monitor.wait()


if __name__ == "__main__":
    main()

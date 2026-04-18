#!/usr/bin/env python3
"""
Vibe Walker - Interactive Desktop Pet
Main entry point
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from PyQt5.QtWidgets import QApplication
from src.config import Config
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

    # Create state machine
    state_machine = StateMachine()

    # Create activity monitor and bridge
    activity_monitor = ActivityMonitor(config)
    activity_bridge = ActivityBridge(activity_monitor)

    # Create game window
    game_window = GameWindow(config, state_machine)

    # Create system tray
    system_tray = SystemTray(config)
    system_tray.exit_requested.connect(app.quit)

    # Set initial visibility based on reactive mode
    print(f"[MAIN] Reactive mode enabled: {config.reactive_mode_enabled}")
    if config.reactive_mode_enabled:
        print("[MAIN] Setting initial state to IDLE and showing window")
        state_machine.transition_to(State.IDLE)
        game_window.show()
    else:
        print("[MAIN] Setting initial state to HIDDEN")
        state_machine.transition_to(State.HIDDEN)
        game_window.hide()

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

"""Main application entry point for vibe-walker."""
import sys
import os
import psutil
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

from config import Config
from state_manager import StateManager
from activity_monitor import ActivityMonitor
from animator import Animator
from character_window import CharacterWindow

def check_already_running():
    """Check if another instance of vibe-walker is already running."""
    current_pid = os.getpid()
    current_dir = os.path.dirname(os.path.abspath(__file__))

    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            # Skip the current process
            if proc.info['pid'] == current_pid:
                continue

            # Check if it's a Python process running main.py from this directory
            if proc.info['name'] and 'python' in proc.info['name'].lower():
                cmdline = proc.info.get('cmdline', [])
                if cmdline:
                    cmdline_str = ' '.join(str(arg) for arg in cmdline)
                    # Check if it's running main.py from vibe-walker directory
                    if 'main.py' in cmdline_str and 'vibe-walker' in cmdline_str:
                        return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    return False

def main():
    """Main application entry point."""
    print("=" * 50)
    print("VIBE WALKER - Taskbar Pixel Character")
    print("=" * 50)

    # Check for existing instances (disabled for testing)
    # if check_already_running():
    #     print("\n[ERROR] Another instance of Vibe Walker is already running!")
    #     print("Please close the existing instance before starting a new one.")
    #     print("Use 'stop_vibewalker.bat' or 'taskkill /F /IM python.exe'\n")
    #     print("=" * 50)
    #     sys.exit(1)

    # Create Qt application
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # Don't quit when window is hidden

    # Load configuration
    config = Config("config.json")

    # Get screen dimensions
    screen = app.primaryScreen()
    screen_geometry = screen.availableGeometry()
    screen_width = screen_geometry.width()
    screen_height = screen_geometry.height()
    print(f"[MAIN] Screen size: {screen_width}x{screen_height}")

    # Initialize state manager
    state_manager = StateManager(config)
    print("[MAIN] State manager initialized")

    # Initialize animator
    animator = Animator(config, screen_width, screen_height)
    print("[MAIN] Animator initialized")

    # Initialize character window
    window = CharacterWindow(config)
    print("[MAIN] Character window initialized")

    # Initialize activity monitor
    activity_monitor = ActivityMonitor(config)
    print("[MAIN] Activity monitor initialized")

    # Connect signals and slots
    print("[MAIN] Connecting signals...")

    # Activity monitor -> State manager
    activity_monitor.activity_started.connect(state_manager.on_claude_started)
    activity_monitor.activity_stopped.connect(state_manager.on_claude_stopped)

    # State manager -> Animator and Window
    state_manager.state_changed.connect(animator.on_state_changed)
    state_manager.state_changed.connect(window.on_state_changed)

    # Animator -> Window
    animator.sprite_changed.connect(window.update_sprite)
    animator.position_changed.connect(window.update_position)

    # Animator -> State manager (edge reached)
    animator.edge_reached.connect(state_manager.reverse_direction)

    print("[MAIN] All signals connected")

    # Start activity monitor thread
    activity_monitor.start()
    print("[MAIN] Activity monitor started")

    print("=" * 50)
    print("Application running! Press Ctrl+C to exit")
    print("Monitoring Claude Code activity in: ~/.claude/sessions/")
    print("Character appears during active tasks and disappears after", config.idle_timeout_sec, "seconds")
    print("=" * 50)

    # Run application
    try:
        exit_code = app.exec_()
    except KeyboardInterrupt:
        print("\n[MAIN] Keyboard interrupt received")
        exit_code = 0

    # Cleanup
    print("[MAIN] Shutting down...")
    activity_monitor.stop()
    activity_monitor.wait(2000)  # Wait up to 2 seconds for thread to finish

    print("[MAIN] Goodbye!")
    sys.exit(exit_code)

if __name__ == '__main__':
    main()

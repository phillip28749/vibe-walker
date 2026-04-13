"""Activity monitoring for Claude Code task execution."""
import os
import time
from pathlib import Path
from PyQt5.QtCore import QThread, pyqtSignal, QTimer

class ActivityMonitor(QThread):
    """Background thread that monitors Claude Code activity."""

    # Signals
    activity_started = pyqtSignal()  # Emitted when Claude Code starts activity
    activity_stopped = pyqtSignal()  # Emitted when Claude Code stops activity

    def __init__(self, config):
        """Initialize activity monitor.

        Args:
            config: Configuration object
        """
        super().__init__()
        self.config = config
        self.is_running = False
        self.was_active = False
        self._stop_requested = False

        # Claude session directory
        self.claude_dir = Path.home() / ".claude"
        self.sessions_dir = self.claude_dir / "sessions"

        # Track last activity time
        self.last_activity_time = 0
        self.activity_threshold = 2  # seconds of inactivity before considering stopped

    def run(self):
        """Run the monitoring loop (executed in background thread)."""
        self.is_running = True
        print("[MONITOR] Starting activity monitor")
        print(f"[MONITOR] Watching: {self.sessions_dir}")

        # Check that Claude directory exists
        if not self.sessions_dir.exists():
            print(f"[ERROR] Claude sessions directory not found: {self.sessions_dir}")
            print("[ERROR] Make sure Claude Code is installed and has run at least once")
            return

        # Use QTimer for polling
        self.timer = QTimer()
        self.timer.timeout.connect(self._check_activity)
        self.timer.start(self.config.poll_interval_ms)

        # Start Qt event loop for this thread
        self.exec_()

    def _check_activity(self):
        """Check for Claude Code activity."""
        if self._stop_requested:
            self.timer.stop()
            self.quit()
            return

        try:
            is_active = self._is_claude_active()
            current_time = time.time()

            # Detect state changes
            if is_active:
                self.last_activity_time = current_time

                if not self.was_active:
                    # Activity just started
                    print("[MONITOR] Claude Code activity detected")
                    self.activity_started.emit()
                    self.was_active = True

            else:
                # Check if we've been inactive long enough
                time_since_activity = current_time - self.last_activity_time

                if self.was_active and time_since_activity >= self.activity_threshold:
                    # Activity stopped
                    print(f"[MONITOR] Claude Code activity stopped ({time_since_activity:.1f}s idle)")
                    self.activity_stopped.emit()
                    self.was_active = False

        except Exception as e:
            print(f"[MONITOR] Error checking activity: {e}")

    def _is_claude_active(self):
        """Check if Claude Code is actively working.

        Returns:
            True if Claude Code is active, False otherwise
        """
        try:
            # Check for active session files
            if not self.sessions_dir.exists():
                return False

            # Get all session files
            session_files = list(self.sessions_dir.glob("*.json"))

            if not session_files:
                return False

            # Check modification times of session files
            # If any file was modified recently, Claude is active
            current_time = time.time()
            activity_window = 3  # Consider active if modified within 3 seconds

            for session_file in session_files:
                try:
                    mtime = session_file.stat().st_mtime
                    age = current_time - mtime

                    if age < activity_window:
                        # File was recently modified - Claude is active
                        return True

                except (OSError, FileNotFoundError):
                    continue

            # Also check file-history directory (shows file edits)
            file_history_dir = self.claude_dir / "file-history"
            if file_history_dir.exists():
                # Get most recent file in file-history
                try:
                    recent_files = sorted(
                        file_history_dir.rglob("*"),
                        key=lambda p: p.stat().st_mtime,
                        reverse=True
                    )[:3]  # Check 3 most recent

                    for recent_file in recent_files:
                        if recent_file.is_file():
                            mtime = recent_file.stat().st_mtime
                            age = current_time - mtime

                            if age < activity_window:
                                return True

                except Exception:
                    pass

            return False

        except Exception as e:
            print(f"[MONITOR] Error checking Claude activity: {e}")
            return False

    def stop(self):
        """Stop the monitoring thread."""
        print("[MONITOR] Stopping activity monitor")
        self._stop_requested = True

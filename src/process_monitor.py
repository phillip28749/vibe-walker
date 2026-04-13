"""Process monitoring for Claude Code detection."""
import psutil
from PyQt5.QtCore import QThread, pyqtSignal, QTimer

class ProcessMonitor(QThread):
    """Background thread that monitors for Claude Code processes."""

    # Signals
    claude_started = pyqtSignal()  # Emitted when Claude Code starts
    claude_stopped = pyqtSignal()  # Emitted when Claude Code stops

    def __init__(self, config):
        """Initialize process monitor.

        Args:
            config: Configuration object
        """
        super().__init__()
        self.config = config
        self.is_running = False
        self.claude_was_running = False
        self._stop_requested = False

    def run(self):
        """Run the monitoring loop (executed in background thread)."""
        self.is_running = True
        print("[MONITOR] Starting process monitor")

        # Use QTimer for polling instead of blocking sleep
        self.timer = QTimer()
        self.timer.timeout.connect(self._check_processes)
        self.timer.start(self.config.poll_interval_ms)

        # Start Qt event loop for this thread
        self.exec_()

    def _check_processes(self):
        """Check if Claude Code is running."""
        if self._stop_requested:
            self.timer.stop()
            self.quit()
            return

        try:
            claude_running = self._is_claude_running()

            # Detect state changes (with debouncing)
            if claude_running and not self.claude_was_running:
                # Claude just started
                print("[MONITOR] Detected Claude Code started")
                self.claude_started.emit()
                self.claude_was_running = True

            elif not claude_running and self.claude_was_running:
                # Claude just stopped
                print("[MONITOR] Detected Claude Code stopped")
                self.claude_stopped.emit()
                self.claude_was_running = False

        except Exception as e:
            print(f"[MONITOR] Error checking processes: {e}")

    def _is_claude_running(self):
        """Check if any Claude Code process is running.

        Returns:
            True if Claude Code is running, False otherwise
        """
        process_names_lower = [name.lower() for name in self.config.process_names]

        try:
            for proc in psutil.process_iter(['name']):
                try:
                    proc_name = proc.info['name']
                    if proc_name and proc_name.lower() in process_names_lower:
                        return True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    # Process ended or we don't have permission - skip it
                    continue
        except Exception as e:
            print(f"[MONITOR] Error iterating processes: {e}")

        return False

    def stop(self):
        """Stop the monitoring thread."""
        print("[MONITOR] Stopping process monitor")
        self._stop_requested = True

"""Activity monitoring from SDK hook-generated trace events."""
import json
from pathlib import Path
from PyQt5.QtCore import QThread, pyqtSignal, QTimer

class ActivityMonitor(QThread):
    """Background thread that monitors query lifecycle traces."""

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
        self.trace_path = Path(self.config.trace_file_path)
        self.last_processed_line = 0
        self.open_queries = set()

    def run(self):
        """Run the monitoring loop (executed in background thread)."""
        self.is_running = True
        print("[MONITOR] Starting trace activity monitor")
        print(f"[MONITOR] Watching trace file: {self.trace_path}")

        # Use QTimer for polling
        self.timer = QTimer()
        self.timer.timeout.connect(self._check_activity)
        self.timer.start(self.config.trace_poll_interval_ms)

        # Start Qt event loop for this thread
        self.exec_()

    def _check_activity(self):
        """Check activity by consuming lifecycle events from trace file."""
        if self._stop_requested:
            self.timer.stop()
            self.quit()
            return

        try:
            self._consume_new_events()
            is_active = bool(self.open_queries)

            if is_active and not self.was_active:
                print("[MONITOR] Query activity detected")
                self.activity_started.emit()
                self.was_active = True

            if not is_active and self.was_active:
                print("[MONITOR] Query activity stopped")
                self.activity_stopped.emit()
                self.was_active = False

        except Exception as e:
            print(f"[MONITOR] Error checking activity: {e}")

    def _consume_new_events(self):
        """Consume newly appended trace events and update open query set."""
        if not self.trace_path.exists():
            return

        with self.trace_path.open("r", encoding="utf-8") as handle:
            lines = handle.readlines()

        if self.last_processed_line >= len(lines):
            return

        for line in lines[self.last_processed_line:]:
            line = line.strip()
            if not line:
                continue

            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue

            query_id = event.get("query_id")
            if not query_id:
                continue

            event_type = event.get("event_type")
            if event_type == "query_started":
                self.open_queries.add(query_id)
            elif event_type in {"query_finished", "query_error"}:
                self.open_queries.discard(query_id)

        self.last_processed_line = len(lines)

    def stop(self):
        """Stop the monitoring thread."""
        print("[MONITOR] Stopping activity monitor")
        self._stop_requested = True

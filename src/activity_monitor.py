"""Activity monitoring from SDK hook-generated trace events."""
import json
from pathlib import Path
from PyQt5.QtCore import QThread, pyqtSignal, QTimer

class ActivityMonitor(QThread):
    """Background thread that monitors query lifecycle traces."""

    # Signals
    activity_started = pyqtSignal()  # Emitted when Claude Code starts activity
    activity_stopped = pyqtSignal()  # Emitted when Claude Code stops activity
    action_needed_started = pyqtSignal()  # Emitted when waiting for user action
    action_needed_stopped = pyqtSignal()  # Emitted when user handles action

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
        self.open_queries = set()  # Track active query IDs
        self._trace_file_warning_shown = False  # Track if warning was shown
        self.current_activity_status = "none"  # Track current activity status for console output
        self.pending_actions = {}  # Track action_needed events: {query_id: {'timestamp': float, 'tool_name': str, 'event': dict}}
        self.rejection_timeout_sec = 30  # If no action_handled after 30s, assume rejection

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
            self._check_action_timeouts()  # Check for rejected tools (timeout)
            is_active = bool(self.open_queries)

            # Determine new status (unless in action_needed, which is set by events)
            if self.current_activity_status != "action_needed":
                if is_active:
                    new_status = "thinking"
                else:
                    new_status = "none"

                # Print status change if different
                if new_status != self.current_activity_status:
                    old_status = self.current_activity_status
                    self.current_activity_status = new_status

                    # Console logging with emoji
                    if new_status == "thinking":
                        print("[MONITOR] 🟡 Claude is thinking")
                    elif new_status == "none" and old_status == "thinking":
                        print("[MONITOR] 🟢 Claude done")

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
            if not self._trace_file_warning_shown:
                print(f"[INFO] Waiting for Claude Code activity...")
                print(f"[INFO] Trace file will be created at: {self.trace_path}")
                self._trace_file_warning_shown = True
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
                # Clean up any pending actions for this query
                self._cleanup_pending_action(query_id, reason="query_ended")

            elif event_type == "action_needed":
                # Store pending action
                trigger = event.get('payload', {}).get('trigger')
                tool_name = event.get('payload', {}).get('tool_name', 'unknown')

                self.pending_actions[query_id] = {
                    'event': event,
                    'timestamp': event['timestamp'],
                    'tool_name': tool_name,
                    'trigger': trigger
                }

                # Only trigger animation for permission_request (dialog shown)
                if trigger == "permission_request":
                    if self.current_activity_status != "action_needed":
                        self.current_activity_status = "action_needed"
                        print(f"[MONITOR] 🔴 Permission requested - {tool_name} needs approval")
                        self.action_needed_started.emit()
                elif self.config.get('debug_action_detection', False):
                    print(f"[DEBUG] Action needed: {tool_name} (trigger: {trigger})")

            elif event_type == "action_denied":
                # User rejected the permission
                pending = self.pending_actions.get(query_id)
                if pending:
                    tool_name = pending['tool_name']
                    print(f"[MONITOR] 🚫 Permission denied - {tool_name} rejected by user")

                    # Stop animation if active
                    if self.current_activity_status == "action_needed":
                        self.current_activity_status = "thinking"
                        self.action_needed_stopped.emit()

                    # Clean up
                    self.pending_actions.pop(query_id, None)

            elif event_type == "action_handled":
                # Tool executed (success or failure)
                pending = self.pending_actions.get(query_id)
                success = event.get('payload', {}).get('success', True)
                tool_name = event.get('payload', {}).get('tool_name', 'unknown')

                if pending:
                    time_gap = event['timestamp'] - pending['timestamp']

                    # Stop animation if active
                    if self.current_activity_status == "action_needed":
                        self.current_activity_status = "thinking"
                        status = "✅" if success else "❌"
                        result = "completed" if success else "failed"
                        print(f"[MONITOR] {status} {tool_name} {result} ({time_gap:.2f}s)")
                        self.action_needed_stopped.emit()
                    elif self.config.get('debug_action_detection', False):
                        result = "completed" if success else "failed"
                        print(f"[DEBUG] {tool_name} {result} ({time_gap:.2f}s)")

                    # Clean up
                    self.pending_actions.pop(query_id, None)
                else:
                    # No pending action - might be auto-approved tool
                    if self.config.get('debug_action_detection', False):
                        result = "completed" if success else "failed"
                        print(f"[DEBUG] {tool_name} {result} (auto-approved, no dialog)")

        self.last_processed_line = len(lines)

    def _check_action_timeouts(self):
        """Check if any pending actions have timed out (user rejected tool)."""
        import time
        current_time = time.time()
        timed_out_queries = []

        for query_id, pending in self.pending_actions.items():
            time_elapsed = current_time - pending['timestamp']
            if time_elapsed > self.rejection_timeout_sec:
                timed_out_queries.append(query_id)

        # Clean up timed out actions
        for query_id in timed_out_queries:
            self._cleanup_pending_action(query_id, reason="timeout (user likely rejected or ignored)")

    def _cleanup_pending_action(self, query_id, reason="unknown"):
        """Clean up a pending action and stop animation if needed.

        Args:
            query_id: Query ID to clean up
            reason: Reason for cleanup (for logging)
        """
        pending = self.pending_actions.pop(query_id, None)
        if pending:
            tool_name = pending['tool_name']
            print(f"[MONITOR] ⏱️ Cleaning up {tool_name} - {reason}")

            # Stop animation if active
            if self.current_activity_status == "action_needed":
                self.current_activity_status = "none"
                self.action_needed_stopped.emit()

    def stop(self):
        """Stop the monitoring thread."""
        print("[MONITOR] Stopping activity monitor")
        self._stop_requested = True

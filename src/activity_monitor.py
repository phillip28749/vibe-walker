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
                # Reset action_needed when query finishes (e.g., user rejected tool)
                if self.current_activity_status == "action_needed":
                    self.current_activity_status = "none"
                    print("[MONITOR] 🔵 Query ended while waiting for action - stopping animation")
                    self.action_needed_stopped.emit()  # Stop waving animation
                # Clean up pending actions for this query
                self.pending_actions.pop(query_id, None)
            elif event_type == "action_needed":
                # Store pending action for potential timing analysis
                self.pending_actions[query_id] = {
                    'event': event,
                    'timestamp': event['timestamp'],
                    'tool_name': event.get('payload', {}).get('tool_name', 'unknown')
                }

                # Primary detection: Check if matcher confirmed manual-approval tool
                should_trigger, reason = self._should_trigger_animation(event, None)

                if should_trigger:
                    # Confirmed manual-approval tool - trigger animation immediately
                    if self.current_activity_status != "action_needed":
                        self.current_activity_status = "action_needed"
                        tool_name = self.pending_actions[query_id]['tool_name']
                        print(f"[MONITOR] 🔴 Action needed - {tool_name} requires approval ({reason})")
                        self.action_needed_started.emit()
                else:
                    # Not a known manual-approval tool - will check timing when action_handled arrives
                    if self.config.get('debug_action_detection', False):
                        print(f"[DEBUG] Deferred: {self.pending_actions[query_id]['tool_name']} - waiting for timing ({reason})")
            elif event_type == "action_handled":
                # Retrieve corresponding action_needed event
                pending = self.pending_actions.get(query_id)

                if pending:
                    time_gap = event['timestamp'] - pending['timestamp']

                    # If we already triggered (matcher-based), stop animation
                    if self.current_activity_status == "action_needed":
                        self.current_activity_status = "thinking"
                        print(f"[MONITOR] ✅ Action handled - {pending['tool_name']} completed ({time_gap:.2f}s)")
                        self.action_needed_stopped.emit()

                    # If we haven't triggered yet, perform retroactive timing check
                    else:
                        should_trigger, reason = self._should_trigger_animation(pending['event'], event)

                        if should_trigger and time_gap > 2.0:
                            # Retroactive detection: user was prompted but tool wasn't in matcher
                            print(f"[MONITOR] ⚠️ Retroactive: {pending['tool_name']} took {time_gap:.2f}s (likely manual, consider adding to matcher)")
                        elif self.config.get('debug_action_detection', False):
                            print(f"[DEBUG] Completed: {pending['tool_name']} in {time_gap:.3f}s ({reason})")

                    # Clean up
                    self.pending_actions.pop(query_id, None)

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
            pending = self.pending_actions.pop(query_id)
            tool_name = pending['tool_name']
            print(f"[MONITOR] ⏱️ Action timeout - {tool_name} (user likely rejected or ignored)")

            # If we're in action_needed status, stop the animation
            if self.current_activity_status == "action_needed":
                self.current_activity_status = "none"
                self.action_needed_stopped.emit()

    def _should_trigger_animation(self, action_needed_event, action_handled_event=None):
        """Determine if action_needed should trigger animation using hybrid detection.

        Method 1 (Primary): Trust the hook matcher - if action_needed fired, it's manual-approval
        Method 2 (Backup): Timing analysis - checks if gap indicates user prompt

        Args:
            action_needed_event: The pre-tool event dict
            action_handled_event: The post-tool event dict (or None if still pending)

        Returns:
            tuple: (should_trigger: bool, reason: str)
        """
        # Primary: Trust the hook matcher
        # If this event exists, it means PreToolUse hook fired, which means
        # the matcher (Bash|Write|Edit|Agent|Skill|Config) already confirmed
        # this is a manual-approval tool. So we should ALWAYS trigger.
        tool_name = action_needed_event.get('payload', {}).get('tool_name', 'matched_by_hook')

        # If the hook fired, trust that it matched a manual-approval tool
        if action_needed_event.get('payload', {}).get('trigger') == 'pre_tool_use':
            return (True, f"matcher:{tool_name}")

        # Backup: Timing analysis for other action_needed sources (e.g., notification hook)
        if action_handled_event is None:
            return (False, "pending")

        time_gap = action_handled_event['timestamp'] - action_needed_event['timestamp']

        # Gap > 2s = user was prompted for approval
        if time_gap > 2.0:
            return (True, f"timing:{time_gap:.2f}s")

        # Gap < 0.5s = definitely auto-approved
        if time_gap < 0.5:
            return (False, f"auto:{time_gap:.2f}s")

        # Gray area (0.5-2s): default to NOT triggering to avoid false positives
        return (False, f"gray:{time_gap:.2f}s")

    def stop(self):
        """Stop the monitoring thread."""
        print("[MONITOR] Stopping activity monitor")
        self._stop_requested = True

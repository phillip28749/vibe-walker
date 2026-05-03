"""Activity monitoring from SDK hook-generated trace events."""

import json
import time
from pathlib import Path

from PyQt5.QtCore import QThread, QTimer, pyqtSignal


class ActivityMonitor(QThread):
    """Background thread that monitors query lifecycle traces."""

    activity_started = pyqtSignal()
    activity_stopped = pyqtSignal()
    action_needed_started = pyqtSignal()
    action_needed_stopped = pyqtSignal()

    def __init__(self, config):
        """Initialize activity monitor."""
        super().__init__()
        self.config = config
        self.was_active = False
        self._stop_requested = False
        self.trace_path = Path(self.config.trace_file_path)
        self.trace_read_offset = 0
        self.trace_last_mtime_ns = None
        self.open_queries = set()
        self.codex_sessions_dir = Path(self.config.codex_sessions_dir)
        self.codex_active_turns = set()
        self.codex_file_offsets = {}
        self.codex_file_mtimes = {}
        self.codex_pending_approvals = {}
        self._trace_file_warning_shown = False
        self._codex_warning_shown = False
        self.current_activity_status = "none"
        self.pending_actions = {}
        self.rejection_timeout_sec = 30

    def run(self):
        """Run the monitoring loop in the background thread."""
        print("[MONITOR] Starting trace activity monitor")
        print(f"[MONITOR] Watching trace file: {self.trace_path}")
        if self.config.codex_activity_enabled:
            print(f"[MONITOR] Watching Codex sessions: {self.codex_sessions_dir}")

        self.timer = QTimer()
        self.timer.timeout.connect(self._check_activity)
        self.timer.start(self.config.trace_poll_interval_ms)
        self.exec_()

    def _check_activity(self):
        """Check activity by consuming lifecycle events from the trace file."""
        if self._stop_requested:
            self.timer.stop()
            self.quit()
            return

        try:
            self._consume_new_events()
            self._consume_codex_events()
            self._check_action_timeouts()
            is_active = bool(self.open_queries or self.codex_active_turns)

            if self.current_activity_status != "action_needed":
                new_status = "thinking" if is_active else "none"
                if new_status != self.current_activity_status:
                    old_status = self.current_activity_status
                    self.current_activity_status = new_status
                    if new_status == "thinking":
                        print("[MONITOR] Vibe mode active")
                    elif new_status == "none" and old_status == "thinking":
                        print("[MONITOR] Vibe mode idle")

            if is_active and not self.was_active:
                print("[MONITOR] Query activity detected")
                self.activity_started.emit()
                self.was_active = True

            if not is_active and self.was_active:
                print("[MONITOR] Query activity stopped")
                self.activity_stopped.emit()
                self.was_active = False
        except Exception as exc:
            print(f"[MONITOR] Error checking activity: {exc}")

    def _consume_new_events(self):
        """Consume newly appended trace events and update open query state."""
        if not self.trace_path.exists():
            if not self._trace_file_warning_shown:
                print("[INFO] Waiting for Claude Code activity...")
                print(f"[INFO] Trace file will be created at: {self.trace_path}")
                self._trace_file_warning_shown = True
            return

        stat_result = self.trace_path.stat()
        file_size = stat_result.st_size
        file_changed = self.trace_last_mtime_ns != stat_result.st_mtime_ns
        if file_size < self.trace_read_offset or (file_changed and file_size <= self.trace_read_offset):
            self.trace_read_offset = 0

        with self.trace_path.open("r", encoding="utf-8") as handle:
            handle.seek(self.trace_read_offset)
            for line in handle:
                self._process_event_line(line)
            self.trace_read_offset = handle.tell()
        self.trace_last_mtime_ns = stat_result.st_mtime_ns

    def _consume_codex_events(self):
        """Consume Codex session events from recent session JSONL files."""
        if not self.config.codex_activity_enabled:
            return

        if not self.codex_sessions_dir.exists():
            if not self._codex_warning_shown:
                print(f"[INFO] Codex sessions directory not found: {self.codex_sessions_dir}")
                self._codex_warning_shown = True
            return

        session_files = sorted(
            self.codex_sessions_dir.rglob("*.jsonl"),
            key=lambda path: path.stat().st_mtime_ns,
            reverse=True,
        )[:5]

        for session_file in session_files:
            stat_result = session_file.stat()
            file_key = str(session_file)
            read_offset = self.codex_file_offsets.get(file_key, 0)
            last_mtime_ns = self.codex_file_mtimes.get(file_key)
            file_changed = last_mtime_ns != stat_result.st_mtime_ns

            if stat_result.st_size < read_offset or (file_changed and stat_result.st_size <= read_offset):
                read_offset = 0

            with session_file.open("r", encoding="utf-8") as handle:
                handle.seek(read_offset)
                for line in handle:
                    self._process_codex_event_line(line)
                self.codex_file_offsets[file_key] = handle.tell()

            self.codex_file_mtimes[file_key] = stat_result.st_mtime_ns

    def _process_codex_event_line(self, line):
        """Process a single Codex session JSONL event line."""
        line = line.strip()
        if not line:
            return

        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            return

        payload = event.get("payload", {})

        if event.get("type") == "response_item":
            self._process_codex_response_item(payload)
            return

        if event.get("type") != "event_msg":
            return

        event_type = payload.get("type")
        turn_id = payload.get("turn_id")

        if event_type == "task_started" and turn_id:
            self.codex_active_turns.add(turn_id)
        elif event_type == "task_complete" and turn_id:
            self.codex_active_turns.discard(turn_id)

        call_id = payload.get("call_id")
        if call_id and payload.get("type") == "exec_command_end":
            self._complete_codex_approval(call_id)

    def _process_codex_response_item(self, payload):
        """Process Codex response-item events relevant to approvals."""
        payload_type = payload.get("type")
        if payload_type == "function_call":
            call_id = payload.get("call_id")
            arguments = payload.get("arguments", "")
            if not call_id or "require_escalated" not in arguments:
                return

            try:
                parsed_arguments = json.loads(arguments)
            except json.JSONDecodeError:
                return

            if parsed_arguments.get("sandbox_permissions") != "require_escalated":
                return

            tool_name = payload.get("name", "codex_tool")
            self.codex_pending_approvals[call_id] = {
                "timestamp": time.time(),
                "tool_name": tool_name,
                "trigger": "codex_permission_request",
            }

            if self.current_activity_status != "action_needed":
                self.current_activity_status = "action_needed"
                print(f"[MONITOR] Permission requested - {tool_name} needs approval")
                self.action_needed_started.emit()

        elif payload_type == "function_call_output":
            call_id = payload.get("call_id")
            if call_id:
                self._complete_codex_approval(call_id)

    def _complete_codex_approval(self, call_id):
        """Mark a Codex approval request as handled."""
        pending = self.codex_pending_approvals.pop(call_id, None)
        if not pending:
            return

        tool_name = pending["tool_name"]
        if not self.codex_pending_approvals and self.current_activity_status == "action_needed":
            self.current_activity_status = "thinking"
            print(f"[MONITOR] {tool_name} approval handled")
            self.action_needed_stopped.emit()

    def _process_event_line(self, line):
        """Process a single JSONL trace event line."""
        line = line.strip()
        if not line:
            return

        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            return

        query_id = event.get("query_id")
        if not query_id:
            return

        event_type = event.get("event_type")
        if event_type == "query_started":
            self.open_queries.add(query_id)
            return

        if event_type in {"query_finished", "query_error"}:
            self.open_queries.discard(query_id)
            self._cleanup_pending_action(query_id, reason="query_ended")
            return

        if event_type == "action_needed":
            payload = event.get("payload", {})
            trigger = payload.get("trigger")
            tool_name = payload.get("tool_name", "unknown")
            self.pending_actions[query_id] = {
                "timestamp": event["timestamp"],
                "tool_name": tool_name,
                "trigger": trigger,
            }

            if trigger == "permission_request":
                if self.current_activity_status != "action_needed":
                    self.current_activity_status = "action_needed"
                    print(f"[MONITOR] Permission requested - {tool_name} needs approval")
                    self.action_needed_started.emit()
            elif self.config.get("debug_action_detection", False):
                print(f"[DEBUG] Action needed: {tool_name} (trigger: {trigger})")
            return

        if event_type == "action_denied":
            pending = self.pending_actions.get(query_id)
            if pending:
                tool_name = pending["tool_name"]
                print(f"[MONITOR] Permission denied - {tool_name} rejected by user")
                if self.current_activity_status == "action_needed":
                    self.current_activity_status = "thinking"
                    self.action_needed_stopped.emit()
                self.pending_actions.pop(query_id, None)
            return

        if event_type == "action_handled":
            pending = self.pending_actions.get(query_id)
            payload = event.get("payload", {})
            success = payload.get("success", True)
            tool_name = payload.get("tool_name", "unknown")

            if pending:
                time_gap = event["timestamp"] - pending["timestamp"]
                result = "completed" if success else "failed"

                if self.current_activity_status == "action_needed":
                    self.current_activity_status = "thinking"
                    print(f"[MONITOR] {tool_name} {result} ({time_gap:.2f}s)")
                    self.action_needed_stopped.emit()
                elif self.config.get("debug_action_detection", False):
                    print(f"[DEBUG] {tool_name} {result} ({time_gap:.2f}s)")

                self.pending_actions.pop(query_id, None)
            elif self.config.get("debug_action_detection", False):
                result = "completed" if success else "failed"
                print(f"[DEBUG] {tool_name} {result} (auto-approved, no dialog)")

    def _check_action_timeouts(self):
        """Check whether any pending actions have timed out."""
        current_time = time.time()
        timed_out_queries = []

        for query_id, pending in self.pending_actions.items():
            if current_time - pending["timestamp"] > self.rejection_timeout_sec:
                timed_out_queries.append(query_id)

        for query_id in timed_out_queries:
            self._cleanup_pending_action(query_id, reason="timeout (user likely rejected or ignored)")

    def _cleanup_pending_action(self, query_id, reason="unknown"):
        """Clean up a pending action and stop animation if needed."""
        pending = self.pending_actions.pop(query_id, None)
        if pending:
            tool_name = pending["tool_name"]
            print(f"[MONITOR] Cleaning up {tool_name} - {reason}")
            if self.current_activity_status == "action_needed":
                self.current_activity_status = "none"
                self.action_needed_stopped.emit()

    def stop(self):
        """Stop the monitoring thread."""
        print("[MONITOR] Stopping activity monitor")
        self._stop_requested = True

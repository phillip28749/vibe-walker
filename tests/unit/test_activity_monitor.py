import json

from src.activity_monitor import ActivityMonitor
from src.config import Config


class DummyConfig:
    def __init__(self, trace_file_path):
        self.trace_file_path = str(trace_file_path)
        self.trace_poll_interval_ms = 500
        self.codex_sessions_dir = str(trace_file_path.parent / "codex-sessions")
        self.codex_activity_enabled = True

    def get(self, key, default=None):
        return default


def write_events(path, events):
    with path.open("w", encoding="utf-8") as handle:
        for event in events:
            handle.write(json.dumps(event) + "\n")


def append_events(path, events):
    with path.open("a", encoding="utf-8") as handle:
        for event in events:
            handle.write(json.dumps(event) + "\n")


def test_consume_new_events_only_reads_appended_lines(tmp_path):
    trace_path = tmp_path / "query_events.jsonl"
    monitor = ActivityMonitor(DummyConfig(trace_path))

    started = {"query_id": "q1", "event_type": "query_started", "timestamp": 1.0}
    finished = {"query_id": "q1", "event_type": "query_finished", "timestamp": 2.0}

    write_events(trace_path, [started])
    monitor._consume_new_events()
    assert "q1" in monitor.open_queries
    assert isinstance(monitor.open_queries["q1"], tuple)  # Should be (start_time, last_event_time)
    first_offset = monitor.trace_read_offset

    monitor._consume_new_events()
    assert monitor.trace_read_offset == first_offset
    assert "q1" in monitor.open_queries

    append_events(trace_path, [finished])
    monitor._consume_new_events()
    assert len(monitor.open_queries) == 0
    assert monitor.trace_read_offset > first_offset


def test_consume_new_events_recovers_after_trace_file_truncation(tmp_path):
    trace_path = tmp_path / "query_events.jsonl"
    monitor = ActivityMonitor(DummyConfig(trace_path))

    write_events(
        trace_path,
        [{"query_id": "old", "event_type": "query_started", "timestamp": 1.0}],
    )
    monitor._consume_new_events()
    assert "old" in monitor.open_queries
    assert isinstance(monitor.open_queries["old"], tuple)
    assert monitor.trace_read_offset > 0

    write_events(
        trace_path,
        [{"query_id": "new", "event_type": "query_started", "timestamp": 2.0}],
    )
    monitor.open_queries.clear()
    monitor._consume_new_events()

    assert "new" in monitor.open_queries
    assert isinstance(monitor.open_queries["new"], tuple)
    assert monitor.trace_read_offset == trace_path.stat().st_size


def test_consume_codex_events_tracks_task_started_and_complete(tmp_path):
    trace_path = tmp_path / "query_events.jsonl"
    monitor = ActivityMonitor(DummyConfig(trace_path))
    sessions_dir = tmp_path / "codex-sessions"
    sessions_dir.mkdir()
    session_file = sessions_dir / "session.jsonl"

    write_events(
        session_file,
        [
            {
                "timestamp": "2026-05-04T00:00:00Z",
                "type": "event_msg",
                "payload": {"type": "task_started", "turn_id": "turn-1"},
            }
        ],
    )

    monitor._consume_codex_events()
    assert "turn-1" in monitor.codex_active_turns
    assert isinstance(monitor.codex_active_turns["turn-1"], tuple)

    append_events(
        session_file,
        [
            {
                "timestamp": "2026-05-04T00:00:10Z",
                "type": "event_msg",
                "payload": {"type": "task_complete", "turn_id": "turn-1"},
            }
        ],
    )

    monitor._consume_codex_events()
    assert len(monitor.codex_active_turns) == 0


def test_codex_permission_request_emits_action_needed_signals(tmp_path, qtbot):
    trace_path = tmp_path / "query_events.jsonl"
    monitor = ActivityMonitor(DummyConfig(trace_path))

    with qtbot.waitSignal(monitor.action_needed_started):
        monitor._process_codex_event_line(
            json.dumps(
                {
                    "type": "response_item",
                    "payload": {
                        "type": "function_call",
                        "name": "shell_command",
                        "call_id": "call-1",
                        "arguments": json.dumps(
                            {
                                "command": "curl.exe https://example.com",
                                "sandbox_permissions": "require_escalated",
                                "justification": "Need approval",
                            }
                        ),
                    },
                }
            )
        )

    assert "call-1" in monitor.codex_pending_approvals
    assert monitor.current_activity_status == "action_needed"

    with qtbot.waitSignal(monitor.action_needed_stopped):
        monitor._process_codex_event_line(
            json.dumps(
                {
                    "type": "event_msg",
                    "payload": {
                        "type": "exec_command_end",
                        "call_id": "call-1",
                        "turn_id": "turn-1",
                        "status": "completed",
                    },
                }
            )
        )

    assert monitor.codex_pending_approvals == {}
    assert monitor.current_activity_status == "thinking"


def test_active_instance_count_signal_includes_claude_and_codex(tmp_path, qtbot):
    trace_path = tmp_path / "query_events.jsonl"
    monitor = ActivityMonitor(DummyConfig(trace_path))
    sessions_dir = tmp_path / "codex-sessions"
    sessions_dir.mkdir()
    session_file = sessions_dir / "session.jsonl"

    write_events(
        trace_path,
        [{"query_id": "claude-1", "event_type": "query_started", "timestamp": 1.0}],
    )
    write_events(
        session_file,
        [
            {
                "timestamp": "2026-05-04T00:00:00Z",
                "type": "event_msg",
                "payload": {"type": "task_started", "turn_id": "codex-1"},
            }
        ],
    )

    with qtbot.waitSignal(monitor.active_instance_count_changed) as blocker:
        monitor._check_activity()

    assert blocker.args == [2]
    assert monitor._get_active_instance_count() == 2


def test_behavior_mode_maps_legacy_claude_to_vibe(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text('{"behavior_mode": "claude"}', encoding="utf-8")

    config = Config(str(config_path))
    assert config.behavior_mode == "vibe"

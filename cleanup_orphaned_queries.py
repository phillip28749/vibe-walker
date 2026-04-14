"""Manual cleanup script for orphaned queries in trace file."""
import json
import time
from pathlib import Path

def cleanup_orphaned_queries(trace_file_path):
    """Find and close orphaned queries in the trace file.

    Args:
        trace_file_path: Path to the query_events.jsonl file
    """
    trace_path = Path(trace_file_path).expanduser()

    if not trace_path.exists():
        print(f"[ERROR] Trace file not found: {trace_path}")
        return

    # Read all events
    with trace_path.open("r", encoding="utf-8") as f:
        lines = f.readlines()

    # Track query states
    open_queries = {}
    closed_queries = set()

    for line in lines:
        line = line.strip()
        if not line:
            continue

        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue

        query_id = event.get("query_id")
        event_type = event.get("event_type")

        if not query_id or not event_type:
            continue

        if event_type == "query_started":
            open_queries[query_id] = event.get("timestamp")
        elif event_type in {"query_finished", "query_error"}:
            closed_queries.add(query_id)
            open_queries.pop(query_id, None)

    # Find orphaned queries (started but not finished)
    orphaned = {qid: ts for qid, ts in open_queries.items() if qid not in closed_queries}

    if not orphaned:
        print("[OK] No orphaned queries found! Trace file is clean.")
        return

    print(f"[FOUND] {len(orphaned)} orphaned query(ies):")
    for query_id, timestamp in orphaned.items():
        print(f"   - {query_id} (started at {timestamp})")

    # Write cleanup events
    timestamp = time.time()
    with trace_path.open("a", encoding="utf-8") as f:
        for query_id in orphaned:
            cleanup_event = {
                "query_id": query_id,
                "event_type": "query_finished",
                "timestamp": timestamp,
                "payload": {"reason": "manual_cleanup"}
            }
            f.write(json.dumps(cleanup_event) + "\n")
            print(f"[CLOSED] {query_id}")

    print(f"\n[SUCCESS] Cleanup complete! Closed {len(orphaned)} orphaned query(ies).")
    print("The character should stop and disappear within 7 seconds.")

if __name__ == "__main__":
    # Default trace file path (relative to script location)
    trace_file = "trace/query_events.jsonl"

    print("=" * 50)
    print("VIBE WALKER - Orphaned Query Cleanup")
    print("=" * 50)
    print(f"Trace file: {trace_file}")
    print()

    cleanup_orphaned_queries(trace_file)

    print()
    print("=" * 50)

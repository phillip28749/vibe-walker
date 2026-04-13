"""Claude Agent SDK query runner with lifecycle tracing hooks."""
import argparse
import asyncio
import json
import time
import uuid
from pathlib import Path

from config import Config

try:
    from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient, HookMatcher
except ImportError as exc:  # pragma: no cover
    ClaudeAgentOptions = None
    ClaudeSDKClient = None
    HookMatcher = None
    IMPORT_ERROR = exc
else:
    IMPORT_ERROR = None


class TraceCollector:
    """Collects query lifecycle events and persists them as JSONL."""

    def __init__(self, trace_path):
        self.trace_path = Path(trace_path)
        self.trace_path.parent.mkdir(parents=True, exist_ok=True)
        self.query_id = str(uuid.uuid4())
        self.start_time = time.time()

    def append(self, event_type, payload=None):
        """Append a structured event to the trace file."""
        payload = payload or {}
        now = time.time()
        event = {
            "query_id": self.query_id,
            "event_type": event_type,
            "timestamp": now,
            "elapsed_sec": round(now - self.start_time, 3),
            "payload": payload,
        }
        with self.trace_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=True) + "\n")


async def run_query_with_trace(query_text, config):
    """Run a Claude SDK query and capture lifecycle events."""
    if IMPORT_ERROR is not None:
        raise RuntimeError(
            "claude_agent_sdk is not installed. Run `pip install -r requirements.txt`."
        ) from IMPORT_ERROR

    collector = TraceCollector(config.trace_file_path)
    collector.append("query_started", {"query": query_text})

    async def on_pre_tool(input_data, tool_use_id, context):
        collector.append(
            "pre_tool",
            {
                "tool_use_id": tool_use_id,
                "tool_name": input_data.get("tool_name"),
                "tool_input": input_data.get("tool_input"),
            },
        )
        return {}

    async def on_post_tool(input_data, tool_use_id, context):
        collector.append(
            "post_tool",
            {
                "tool_use_id": tool_use_id,
                "tool_name": input_data.get("tool_name"),
                "tool_output": input_data.get("tool_output"),
            },
        )
        return {}

    async def on_stop(input_data, tool_use_id, context):
        collector.append("query_finished", {"stop_input": input_data})
        return {}

    options = ClaudeAgentOptions(
        hooks={
            "PreToolUse": [HookMatcher(matcher="*", hooks=[on_pre_tool])],
            "PostToolUse": [HookMatcher(matcher="*", hooks=[on_post_tool])],
            "Stop": [HookMatcher(matcher="*", hooks=[on_stop])],
        }
    )

    try:
        async with ClaudeSDKClient(options=options) as client:
            await client.query(query_text)
            async for _msg in client.receive_response():
                # Streaming is consumed to ensure hooks execute through completion.
                pass
    except Exception as exc:
        collector.append("query_error", {"error": str(exc)})
        collector.append("query_finished", {"reason": "error"})
        raise


def parse_args():
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Run one Claude query with lifecycle tracing hooks"
    )
    parser.add_argument("query", help="Prompt/query text to send")
    return parser.parse_args()


def main():
    """CLI entry point."""
    args = parse_args()
    config = Config("config.json")
    print("[TRACE] Running traced query")
    print(f"[TRACE] Writing events to: {config.trace_file_path}")
    asyncio.run(run_query_with_trace(args.query, config))
    print("[TRACE] Query completed")


if __name__ == "__main__":
    main()

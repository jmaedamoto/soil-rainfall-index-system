"""Append timing events for rainfall preview and recalculation requests."""

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any, Dict, Optional

from flask import Flask, g, request

logger = logging.getLogger(__name__)

_TIMED_ROUTE_SUFFIXES = (
    "/session/<session_id>/recalculate",
    "/session/<session_id>/rainfall-preview",
)


def _timing_file_path() -> Path:
    configured_path = os.environ.get("SOIL_RAINFALL_TIMING_FILE")
    if configured_path:
        return Path(configured_path).expanduser().resolve()
    server_dir = Path(__file__).resolve().parents[2]
    return server_dir / "performance_timings.jsonl"


def _append_event(event: Dict[str, Any]) -> None:
    """Append one complete JSON line; avoid a shared in-memory buffer across workers."""
    path = _timing_file_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        line = (json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o640)
        try:
            os.write(fd, line)
        finally:
            os.close(fd)
    except Exception:
        # Timing collection must never make the rainfall API fail.
        logger.exception("Could not append performance timing to %s", path)


def record_stage(stage: str, duration_ms: float, **metadata: Any) -> None:
    """Persist a stage measurement for the current timed request, if any."""
    try:
        record: Optional[Dict[str, Any]] = getattr(g, "performance_timing_record", None)
    except RuntimeError:
        return
    if record is None:
        return

    event = {
        "event": "stage",
        "request_id": record["request_id"],
        "stage": stage,
        "duration_ms": round(float(duration_ms), 3),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }
    if metadata:
        event["metadata"] = metadata
    _append_event(event)


def register_performance_timing_hooks(app: Flask) -> None:
    """Record start, stages, and completion for rainfall preview/recalculation APIs."""

    @app.before_request
    def _start_performance_timing() -> None:
        rule = request.url_rule.rule if request.url_rule is not None else ""
        if not any(rule.endswith(suffix) for suffix in _TIMED_ROUTE_SUFFIXES):
            return

        record = {
            "request_id": uuid.uuid4().hex,
            "route": rule,
            "method": request.method,
            "started_at_utc": datetime.now(timezone.utc).isoformat(),
            "started_at_perf": perf_counter(),
        }
        g.performance_timing_record = record
        _append_event({
            "event": "request_started",
            "request_id": record["request_id"],
            "route": rule,
            "method": request.method,
            "request_bytes": request.content_length,
            "process_id": os.getpid(),
            "timestamp_utc": record["started_at_utc"],
        })

    @app.after_request
    def _finish_performance_timing(response):
        record: Optional[Dict[str, Any]] = getattr(g, "performance_timing_record", None)
        if record is None:
            return response

        _append_event({
            "event": "request_completed",
            "request_id": record["request_id"],
            "route": record["route"],
            "method": record["method"],
            "status_code": response.status_code,
            "request_bytes": request.content_length,
            "total_duration_ms": round((perf_counter() - record["started_at_perf"]) * 1000, 3),
            "response_bytes": response.calculate_content_length(),
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        })
        return response

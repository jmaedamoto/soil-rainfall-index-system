"""Append timing events for the rainfall adjustment workflow."""

import hashlib
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
    "/production-soil-rainfall-index-with-urls",
    "/session/<session_id>/rainfall-data",
    "/session/<session_id>/recalculate",
    "/session/<session_id>/rainfall-preview",
)


def session_reference(session_id: Optional[str]) -> Optional[str]:
    """Return a stable, non-reversible reference for correlating one session's requests."""
    if not session_id:
        return None
    return hashlib.sha256(session_id.encode("utf-8")).hexdigest()[:16]


def _timing_file_path() -> Path:
    configured_path = os.environ.get("SOIL_RAINFALL_TIMING_FILE")
    if configured_path:
        return Path(configured_path).expanduser().resolve()

    server_dir = Path(__file__).resolve().parents[2]
    cache_dir = os.environ.get("CACHE_DIR")
    if cache_dir:
        return Path(cache_dir).expanduser().resolve() / "performance_timings.jsonl"
    return server_dir / "cache" / "performance_timings.jsonl"


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
    logger.info("Rainfall performance timing file: %s", _timing_file_path())

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
        session_id = (request.view_args or {}).get("session_id")
        session_ref = session_reference(session_id)
        if session_ref:
            record["session_ref"] = session_ref
        g.performance_timing_record = record
        event = {
            "event": "request_started",
            "request_id": record["request_id"],
            "route": rule,
            "method": request.method,
            "request_bytes": request.content_length,
            "process_id": os.getpid(),
            "timestamp_utc": record["started_at_utc"],
        }
        if session_ref:
            event["session_ref"] = session_ref
        _append_event(event)

    @app.after_request
    def _finish_performance_timing(response):
        record: Optional[Dict[str, Any]] = getattr(g, "performance_timing_record", None)
        if record is None:
            return response

        _append_event({
            "event": "request_completed",
            "request_id": record["request_id"],
            **({"session_ref": record["session_ref"]} if record.get("session_ref") else {}),
            "route": record["route"],
            "method": record["method"],
            "status_code": response.status_code,
            "request_bytes": request.content_length,
            "total_duration_ms": round((perf_counter() - record["started_at_perf"]) * 1000, 3),
            "response_bytes": response.calculate_content_length(),
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        })
        return response

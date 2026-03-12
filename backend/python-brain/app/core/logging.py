from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.core.request_context import get_request_id

SUMMARY_LOGGER = "interviewsim.summary"


def setup_logging() -> None:
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()

    formatter = logging.Formatter("%(message)s")
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    root.addHandler(stream_handler)

    log_dir = Path(settings.log_dir)
    if not log_dir.is_absolute():
        log_dir = Path(__file__).resolve().parents[2] / log_dir
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / settings.log_file

    file_handler = TimedRotatingFileHandler(
        filename=str(log_path),
        when="midnight",
        backupCount=14,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    summary_path = log_dir / settings.summary_log_file
    summary_logger = logging.getLogger(SUMMARY_LOGGER)
    summary_logger.handlers.clear()
    summary_logger.setLevel(logging.INFO)
    summary_logger.propagate = False
    summary_handler = TimedRotatingFileHandler(
        filename=str(summary_path),
        when="midnight",
        backupCount=14,
        encoding="utf-8",
    )
    summary_handler.setFormatter(logging.Formatter("%(message)s"))
    summary_logger.addHandler(summary_handler)

    log_event("logging.initialized", log_file=str(log_path))
    log_summary("logging.initialized", summary_log_file=str(summary_path))


def log_event(event: str, **fields: Any) -> None:
    payload = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "level": "INFO",
        "event": event,
        "request_id": get_request_id(),
    }
    payload.update(fields)
    logging.getLogger("interviewsim").info(json.dumps(payload, ensure_ascii=False, default=str))


def log_summary(event: str, **fields: Any) -> None:
    payload = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "request_id": get_request_id(),
    }
    payload.update(fields)
    logging.getLogger(SUMMARY_LOGGER).info(json.dumps(payload, ensure_ascii=False, default=str))


def log_workflow_diff(workflow: str, diff: dict[str, Any], **fields: Any) -> None:
    if not diff:
        return
    log_event(f"workflow.{workflow}.shadow.diff", diff=diff, **fields)

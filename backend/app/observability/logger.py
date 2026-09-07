"""
Structured logging module for FactLens.
Provides structured JSON and colored text formatting, context variable propagation
(e.g., request_id), and automatic sensitive credential redaction.
"""

import json
import logging
import re
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any

# Context variable for correlating logs with incoming HTTP requests
request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)

# Patterns for sensitive credentials that must never be exposed in logs
SENSITIVE_PATTERNS = [
    # API keys and bearer tokens
    (re.compile(r"(bearer\s+)[a-zA-Z0-9_\-\.]{15,}", re.IGNORECASE), r"\1[REDACTED_TOKEN]"),
    (re.compile(r"(api[_-]?key[\"'\s:=]+)[a-zA-Z0-9_\-\.]{12,}", re.IGNORECASE), r"\1[REDACTED_KEY]"),
    (re.compile(r"(groq_api_key[\"'\s:=]+)[a-zA-Z0-9_\-\.]{12,}", re.IGNORECASE), r"\1[REDACTED_GROQ_KEY]"),
    (re.compile(r"(jina_api_key[\"'\s:=]+)[a-zA-Z0-9_\-\.]{12,}", re.IGNORECASE), r"\1[REDACTED_JINA_KEY]"),
    (re.compile(r"(logfire_token[\"'\s:=]+)[a-zA-Z0-9_\-\.]{12,}", re.IGNORECASE), r"\1[REDACTED_LOGFIRE_TOKEN]"),
    # Database connection strings with passwords: postgresql://user:password@host
    (re.compile(r"(postgresql(?:ql|\+asyncpg)?://[^:]+:)[^@]+(@)", re.IGNORECASE), r"\1[REDACTED_PASSWORD]\2"),
    # Supabase service role keys / anon keys in headers or strings
    (re.compile(r"(supabase[_-]?(?:service[_-]role[_-]?key|anon[_-]?key)[\"'\s:=]+)[a-zA-Z0-9_\-\.]{20,}", re.IGNORECASE), r"\1[REDACTED_SUPABASE_KEY]"),
]


def mask_sensitive_data(text: str) -> str:
    """Mask known sensitive credentials, tokens, and passwords in log text."""
    if not isinstance(text, str):
        return text
    sanitized = text
    for pattern, replacement in SENSITIVE_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)
    return sanitized


class StructuredJsonFormatter(logging.Formatter):
    """Formats log records as single-line JSON objects with ISO timestamps."""

    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat()
        req_id = request_id_ctx.get()

        log_data: dict[str, Any] = {
            "timestamp": timestamp,
            "level": record.levelname,
            "logger": record.name,
            "message": mask_sensitive_data(record.getMessage()),
        }

        if req_id:
            log_data["request_id"] = req_id

        # Include custom extra fields
        for key, value in record.__dict__.items():
            if key not in (
                "args", "asctime", "created", "exc_info", "exc_text", "filename",
                "funcName", "id", "levelname", "levelno", "lineno", "module",
                "msecs", "message", "msg", "name", "pathname", "process",
                "processName", "relativeCreated", "stack_info", "thread",
                "threadName"
            ):
                log_data[key] = mask_sensitive_data(str(value)) if isinstance(value, str) else value

        if record.exc_info:
            log_data["exception"] = mask_sensitive_data(self.formatException(record.exc_info))

        return json.dumps(log_data)


class TextLogFormatter(logging.Formatter):
    """Readable human-friendly formatter for local development with secret masking."""

    def format(self, record: logging.LogRecord) -> str:
        req_id = request_id_ctx.get()
        req_part = f" [{req_id[:8]}]" if req_id else ""
        raw_msg = super().format(record)
        return mask_sensitive_data(f"{raw_msg}{req_part}")


def configure_logging(log_format: str = "text", level: int = logging.INFO) -> None:
    """Configure the root and FactLens logger with appropriate formatting."""
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers to prevent duplicate lines
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    stream_handler = logging.StreamHandler()
    if log_format.lower() == "json":
        stream_handler.setFormatter(StructuredJsonFormatter())
    else:
        stream_handler.setFormatter(
            TextLogFormatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )

    root_logger.addHandler(stream_handler)


def get_logger(name: str) -> logging.Logger:
    """Get a named logger instance."""
    return logging.getLogger(name)

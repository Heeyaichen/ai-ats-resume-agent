"""Structured logging configuration using structlog.

All backend and worker code must use structlog loggers — never print().
Log output is JSON with the fields required by design spec Section 10.1.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog


def _add_log_level(
    logger: Any, method_name: str, event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Ensure `level` is present in the event dict."""
    if "level" not in event_dict:
        event_dict["level"] = method_name
    return event_dict


def configure_logging(
    *,
    service: str = "ats-agent",
    environment: str = "dev",
    log_level: str = "INFO",
) -> None:
    """Configure structlog for JSON output.

    Call once at application startup. The bound fields `service` and
    `environment` appear in every log line. Call-sites bind additional
    context (job_id, iteration, tool_name, etc.) as needed.
    """
    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    structlog.configure(
        processors=[
            *_get_default_processors(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # stdlib handler so that uvicorn / Azure SDK log lines also go through structlog.
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            processors=[
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                structlog.processors.JSONRenderer(),
            ],
            foreign_pre_chain=shared_processors,
        ),
    )

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Bind static context so every log line includes these fields.
    structlog.contextvars.bind_contextvars(
        service=service,
        environment=environment,
    )


def _get_default_processors() -> list[Any]:
    return [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]


def get_logger(name: str | None = None) -> Any:
    """Return a structlog logger, optionally named for module filtering."""
    return structlog.get_logger(name)

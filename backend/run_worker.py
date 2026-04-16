"""Worker entrypoint for container deployment.

Usage: python -m backend.run_worker

Initializes production settings and starts the Service Bus worker loop.
"""

from __future__ import annotations

import asyncio
import logging
import sys

from backend.app.config import Settings
from backend.app.logging_config import configure_logging
from backend.app.worker import run_worker

logger = logging.getLogger(__name__)


def main() -> None:
    try:
        settings = Settings()
    except Exception as exc:
        print(f"FATAL: cannot load settings: {exc}", file=sys.stderr)
        sys.exit(1)

    configure_logging(
        service=settings.app_name,
        environment=settings.environment.value,
        log_level=settings.log_level,
    )

    logger.info(
        "Worker starting (environment=%s, queue=%s)",
        settings.environment.value,
        settings.servicebus_queue_name,
    )

    asyncio.run(
        run_worker(
            settings,
            job_store={},
            score_store={},
            trace_store={},
            review_store={},
            sse_registry=None,
        )
    )


if __name__ == "__main__":
    main()

from __future__ import annotations

import logging
import os


def configure_logging() -> None:
    level = getattr(logging, os.getenv("AUDIT_LOG_LEVEL", "INFO").upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

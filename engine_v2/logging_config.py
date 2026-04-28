"""Central loguru configuration for the engine."""

from __future__ import annotations

import logging
import os
import sys

from loguru import logger

_CONFIGURED = False


class _InterceptHandler(logging.Handler):
    """Route standard logging records through loguru."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level: str | int = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame = logging.currentframe()
        depth = 0
        while frame:
            if frame.f_code.co_filename == record.pathname:
                break
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level,
            record.getMessage(),
        )


def configure_logging(level: str | None = None) -> None:
    """Configure loguru once and bridge stdlib logging into it."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    log_level = (level or os.getenv("LOG_LEVEL") or "DEBUG").upper()

    logger.remove()
    logger.add(
        sys.stderr,
        level=log_level,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level:<8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        ),
        backtrace=True,
        diagnose=False,
    )

    logging.basicConfig(handlers=[_InterceptHandler()], level=0, force=True)

    for name in logging.root.manager.loggerDict:
        logging.getLogger(name).handlers = []
        logging.getLogger(name).propagate = True

    # Keep the engine chatty by default, while avoiding extreme third-party noise.
    logging.getLogger("uvicorn").setLevel(log_level)
    logging.getLogger("engine_v2").setLevel(log_level)

    _CONFIGURED = True
    logger.debug("Logging configured with level={}", log_level)

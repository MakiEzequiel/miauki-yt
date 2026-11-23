# -*- coding: utf-8 -*-
"""Logs con rotación en la carpeta de datos del usuario."""
import logging
from logging.handlers import RotatingFileHandler

from miauki import paths

_LOGGER = None


def obtener_logger() -> logging.Logger:
    """Logger único de la app (miauki.log, 1 MB, 3 copias viejas)."""
    global _LOGGER
    if _LOGGER is not None:
        return _LOGGER
    log = logging.getLogger("miauki")
    if not log.handlers:
        log.setLevel(logging.INFO)
        h = RotatingFileHandler(
            paths.dir_logs() / "miauki.log",
            maxBytes=1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        log.addHandler(h)
    _LOGGER = log
    return log

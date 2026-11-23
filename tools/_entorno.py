# -*- coding: utf-8 -*-
"""Carpeta de datos temporal para herramientas y pruebas (Fase 7, 0.1).

Importá esto ARRIBA de todo en cualquier herramienta de `tools/` que use
`miauki` (aunque solo lea links: el logger escribe en la carpeta de datos):

    import _entorno  # noqa: F401  (carpeta de datos temporal)

Al importarse apunta `MIAUKI_DATOS` a `%TEMP%\\miauki-herramientas\\<script>`
(si no vino ya definida). Nunca se toca `%LOCALAPPDATA%\\Miauki YT`, la
carpeta real de Maki.
"""
import os
import sys
import tempfile
from pathlib import Path


def datos_temporales(nombre: str, ruta: str | Path | None = None) -> Path:
    """Apunta MIAUKI_DATOS a una carpeta temporal (o a la que ya venga puesta)."""
    if ruta is None and os.environ.get("MIAUKI_DATOS"):
        return Path(os.environ["MIAUKI_DATOS"])
    carpeta = Path(ruta) if ruta else Path(tempfile.gettempdir()) / "miauki-herramientas" / nombre
    carpeta.mkdir(parents=True, exist_ok=True)
    os.environ["MIAUKI_DATOS"] = str(carpeta)
    return carpeta


if "MIAUKI_DATOS" not in os.environ:
    datos_temporales(Path(sys.argv[0] or "herramienta").stem or "herramienta")

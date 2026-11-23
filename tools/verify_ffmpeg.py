# -*- coding: utf-8 -*-
"""Verifica que miauki/bin/ffmpeg.exe exista y coincida con el SHA-256 del proyecto.

El hash canónico vive en miauki/core/ffmpeg_tools.py (lo comparten el
selftest, este script y el build). Uso: python tools/verify_ffmpeg.py
"""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
import _entorno  # noqa: E402  (carpeta de datos temporal, nunca la real)

from miauki.core.ffmpeg_tools import verificar_ffmpeg  # noqa: E402

if __name__ == "__main__":
    ok, msg = verificar_ffmpeg(RAIZ / "miauki" / "bin" / "ffmpeg.exe")
    print(msg)
    if not ok:
        print("BUILD DETENIDO: corrija el ffmpeg antes de empaquetar.", file=sys.stderr)
    sys.exit(0 if ok else 1)

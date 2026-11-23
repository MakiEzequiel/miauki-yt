# -*- coding: utf-8 -*-
"""ffmpeg embebido: hash canónico y verificación.

SHA256_ESPERADO es la única constante del hash en el proyecto:
lo usan el selftest, el build (tools/build_exe.py) y tools/verify_ffmpeg.py.
El origen y la versión están documentados en docs/DEPENDENCIAS.md.
"""
import hashlib
from pathlib import Path

SHA256_ESPERADO = "3256173F3F8BFFD7DF12227C68ADF68025EDB1832273A9530688A7BB1ED8EDEC"


def sha256_de(ruta: Path) -> str:
    h = hashlib.sha256()
    with ruta.open("rb") as f:
        for bloque in iter(lambda: f.read(1024 * 1024), b""):
            h.update(bloque)
    return h.hexdigest().upper()


def verificar_ffmpeg(ruta: Path) -> tuple[bool, str]:
    """Comprueba que el archivo exista y que su SHA-256 coincida."""
    if not ruta.exists():
        return False, f"Falta el archivo: {ruta}"
    real = sha256_de(ruta)
    if real != SHA256_ESPERADO:
        return False, (
            "El SHA-256 de ffmpeg.exe no coincide con el documentado.\n"
            f"  esperado: {SHA256_ESPERADO}\n"
            f"  real:     {real}"
        )
    return True, f"ffmpeg.exe verificado (SHA-256 coincide): {ruta}"

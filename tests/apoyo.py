# -*- coding: utf-8 -*-
"""Aísla los tests de la carpeta de datos real de Maki (Fase 7, 0.1).

Cada `test_*.py` importa este módulo ANTES de tocar `miauki.*`: acá se apunta
`MIAUKI_DATOS` a una carpeta temporal propia de esta corrida y se guarda una
huella de los archivos reales (historial, cola, ajustes) para que
`test_zz_datos_reales` falle si algo los escribió.

Importá así (una línea, arriba de los imports del proyecto):

    import apoyo  # noqa: F401  (aísla la carpeta de datos)
"""
import hashlib
import os
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

if "MIAUKI_DATOS" not in os.environ:
    _CARPETA = Path(tempfile.mkdtemp(prefix="miauki_tests_"))
    os.environ["MIAUKI_DATOS"] = str(_CARPETA)
else:
    _CARPETA = Path(os.environ["MIAUKI_DATOS"])

# Nunca, bajo ningún concepto, se deja que los tests usen la carpeta real.
_REAL = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "Miauki YT"


def huella(archivo: Path) -> str | None:
    """sha256 + tamaño del archivo, o None si no existe."""
    try:
        datos = archivo.read_bytes()
    except OSError:
        return None
    return f"{len(datos)}:{hashlib.sha256(datos).hexdigest()}"


HUELLA_REAL = {
    nombre: huella(_REAL / nombre)
    for nombre in ("historial.json", "cola.json", "ajustes.json")
}

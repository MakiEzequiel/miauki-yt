# -*- coding: utf-8 -*-
"""Prueba REAL del actualizador de yt-dlp (Fase 7, A2). Necesita internet.

Uso (desde la raíz del proyecto):

    python tools/probar_actualizador.py              # comprueba de verdad
    python tools/probar_actualizador.py --forzar     # ignora el límite de 10 min

Muestra la versión en uso, la que hay en PyPI, qué hizo y con qué motor queda.
No descarga videos. La carpeta de datos es temporal (nunca la real).
"""
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
import _entorno  # noqa: E402  (carpeta de datos temporal, nunca la real)
_entorno.datos_temporales("probar_actualizador")

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from miauki.core import actualizador, motor  # noqa: E402


def main() -> int:
    print("Motor en uso antes:", motor.version_en_uso(), "(%s)" % motor.origen_en_uso())
    print("Incluida en el .exe:", motor.version_en_uso(), "| estado:", motor.estado())
    inicio = time.monotonic()
    resultado = actualizador.comprobar(forzar="--forzar" in sys.argv)
    print("Comprobación: %.1f s" % (time.monotonic() - inicio))
    print("Resultado:", resultado)
    print("Motor en uso después:", motor.version_en_uso(), "(%s)" % motor.origen_en_uso())
    print("Estado:", motor.estado())
    if resultado.get("accion") == "actualizada":
        print("\nSe usa al reiniciar (o ya, si nada importó yt-dlp todavía).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

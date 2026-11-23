# -*- coding: utf-8 -*-
"""Genera `miauki/LICENCIAS.txt` (Fase 5C, A5).

Todo el texto sale de acá + los textos oficiales de `docs/legal/*.txt` +
`miauki/app_info.py`. El archivo generado viaja junto al `.exe` y embebido
en el `.exe` (ver `tools/build_exe.py`).

Uso:
  python tools/generar_licencias.py            escribe miauki/LICENCIAS.txt
  python tools/generar_licencias.py <destino>  escribe en otra ruta (tests)
"""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
import _entorno  # noqa: E402  (carpeta de datos temporal, nunca la real)

from miauki import app_info  # noqa: E402

LEGAL = RAIZ / "docs" / "legal"

# (componente, versión, licencia, qué es, obligación al distribuir)
COMPONENTES = [
    ("FFmpeg", "9.0.2 essentials (gyan.dev)", "GPLv3",
     "binario que corta y une audio y video",
     "incluir el texto GPLv3 completo y ofrecer el código fuente correspondiente"),
    ("yt-dlp", "2026.8.19", "Unlicense (dominio público)",
     "extrae los links de los sitios",
     "ninguna"),
    ("pywebview", "6.2.1", "BSD 3-Clause",
     "ventana con WebView2",
     "aviso de copyright y texto de la licencia"),
    ("pythonnet", "3.2.1", "MIT",
     "puente entre Python y .NET (lo usa pywebview)",
     "aviso de copyright y texto de la licencia"),
    ("clr-loader", "0.3.1", "MIT",
     "carga el runtime .NET",
     "aviso de copyright y texto de la licencia"),
    ("Bottle", "0.13.4", "MIT",
     "servidor local que sirve la interfaz a WebView2",
     "aviso de copyright y texto de la licencia"),
    ("Python", "3.12", "PSF License 2.0",
     "intérprete embebido en el .exe",
     "incluir el texto de la licencia PSF"),
    ("PyInstaller", "6.22.3", "GPLv2 con excepción del bootloader",
     "arma el .exe",
     "ninguna sobre el código de Miauki (ver aclaración más abajo); "
     "se incluye su aviso"),
    ("Fredoka", "Google Fonts", "SIL Open Font License 1.1",
     "tipografía de la interfaz",
     "incluir el texto OFL y no vender la fuente por separado"),
    ("Caveat", "Google Fonts", "SIL Open Font License 1.1",
     "tipografía de los títulos",
     "incluir el texto OFL y no vender la fuente por separado"),
    ("Simple Icons (instagram.svg)", "CC0 1.0", "CC0 1.0",
     "ícono de Instagram",
     "ninguna (las marcas siguen siendo de sus dueños)"),
    ("Microsoft Edge WebView2", "runtime del sistema", "términos de Microsoft",
     "muestra la interfaz",
     "no se redistribuye: lo instala Microsoft"),
]

OFERTA = """\
OFERTA DE CÓDIGO FUENTE (GPLv3, FFmpeg 9.0.2)
--------------------------------------------
Miauki YT incluye un binario de FFmpeg 9.0.2 (build essentials de gyan.dev),
que está bajo GNU GPL versión 3. Por eso:

1. El texto completo de la GPLv3 está más abajo, en este mismo archivo.
2. El código fuente exacto de esa versión está publicado por el proyecto
   FFmpeg en: https://ffmpeg.org/releases/ffmpeg-9.0.2.tar.xz
   (página de descargas: https://ffmpeg.org/download.html)
3. Oferta escrita válida por 3 años desde la entrega: si necesitás el código
   fuente correspondiente en otro formato, pedilo por Instagram a
   @tusrecursosdigitaless (https://www.instagram.com/tusrecursosdigitaless/)
   y se te entrega sin costo, junto con las instrucciones de compilación usadas.

LICENCIA DE MIAUKI YT
--------------------
Miauki YT (la interfaz y el código Python propio) está bajo GNU GPL versión 3
o posterior: podés usarlo, estudiarlo, modificarlo y redistribuirlo bajo la
misma licencia. El texto completo de la GPLv3 está más abajo, en este archivo.

Oferta escrita de código fuente (GPLv3, Miauki YT), válida por 3 años desde la
entrega: si querés el código fuente completo de Miauki YT, pedilo por Instagram
a @tusrecursosdigitaless (https://www.instagram.com/tusrecursosdigitaless/) y
se te entrega sin costo.

ACLARACIÓN SOBRE PYINSTALLER
----------------------------
El bootloader de PyInstaller es GPLv2 con una excepción especial que permite
empaquetar programas que no son libres (propietarios) sin obligarlos a abrir
su código. Por eso el .exe de Miauki YT puede ser propietario aunque haya sido
armado con PyInstaller.
"""


def leer(nombre: str) -> str:
    return (LEGAL / nombre).read_text(encoding="utf-8").rstrip() + "\n"


def texto() -> str:
    partes = [
        f"{app_info.NOMBRE} v{app_info.VERSION} — Licencias de terceros",
        "=" * 60,
        "",
        f"© {app_info.ANIO} {app_info.AUTOR}. {app_info.NOMBRE} se distribuye "
        f"bajo {app_info.LICENCIA}",
        "(ver \"LICENCIA DE MIAUKI YT\" más abajo; el texto completo de la GPLv3 "
        "está incluido).",
        "Este archivo acompaña al programa y enumera todo lo de terceros que "
        "viaja dentro del .exe,",
        "con el texto completo de cada licencia.",
        "",
        "QUÉ VIAJA EN EL .EXE",
        "---------------------",
        "El .exe es un paquete de PyInstaller: adentro van el intérprete de "
        "Python, las librerías de",
        "Python, la interfaz completa (HTML, CSS, JS, fuentes, íconos, "
        "imágenes) y ffmpeg.exe.",
        "El runtime de WebView2 no viaja: lo instala Microsoft en el equipo.",
        "",
        "COMPONENTES",
        "-----------",
    ]
    for nombre, version, licencia, que_es, obligacion in COMPONENTES:
        partes += [
            f"* {nombre} {version} — {licencia}",
            f"  Qué es: {que_es}.",
            f"  Obligación: {obligacion}.",
            "",
        ]
    partes += [
        OFERTA,
        "",
        "TEXTO COMPLETO — GNU GENERAL PUBLIC LICENSE v3",
        "=" * 60,
        "",
        leer("GPL-3.0.txt"),
        "",
        "TEXTO COMPLETO — SIL OPEN FONT LICENSE 1.1 (Fredoka y Caveat)",
        "=" * 60,
        "",
        "Copyright de las fuentes: The Fredoka Project Authors (Fredoka) y "
        "The Caveat Project Authors (Caveat),",
        "distribuidas por Google Fonts bajo SIL Open Font License 1.1.",
        "",
        leer("OFL-1.1.txt"),
        "",
        "TEXTO COMPLETO — BSD 3-CLAUSE (pywebview)",
        "=" * 60,
        "",
        leer("BSD-3-Clause.txt"),
        "",
        "TEXTO COMPLETO — MIT (pythonnet, clr-loader, Bottle)",
        "=" * 60,
        "",
        leer("MIT.txt"),
        "",
        "TEXTO COMPLETO — PYTHON SOFTWARE FOUNDATION LICENSE 2.0 (Python)",
        "=" * 60,
        "",
        leer("PSF-2.0.txt"),
        "",
        "TEXTO COMPLETO — THE UNLICENSE (yt-dlp)",
        "=" * 60,
        "",
        leer("Unlicense.txt"),
        "",
        "CC0 1.0 — SIMPLE ICONS",
        "----------------------",
        "El ícono de Instagram sale de Simple Icons (https://simpleicons.org), "
        "publicado bajo CC0 1.0",
        "(https://creativecommons.org/publicdomain/zero/1.0/). Las marcas y los "
        "logos son propiedad de",
        "sus dueños; se usan solo para identificar el servicio.",
        "",
        f"Contacto: {app_info.AUTOR} — "
        f"{app_info.ENLACES['instagram']}",
        "",
    ]
    return "\n".join(partes)


def main(destino: Path | None = None) -> Path:
    destino = destino or (RAIZ / "miauki" / "LICENCIAS.txt")
    destino.write_text(texto(), encoding="utf-8", newline="\r\n")
    return destino


if __name__ == "__main__":
    ruta = main(Path(sys.argv[1]) if len(sys.argv) > 1 else None)
    print(f"Escrito: {ruta} ({ruta.stat().st_size} bytes)")

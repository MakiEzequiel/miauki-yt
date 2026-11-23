# -*- coding: utf-8 -*-
"""Todas las rutas de la app en un solo lugar.

Datos del usuario en %LOCALAPPDATA%\\Miauki YT\\ (o reg-miau portable con
portable.flag junto al .exe). Recursos embebidos en _MEIPASS cuando está
congelado con PyInstaller. Fuente de interfaz: carpeta 'ui' externa junto al
.exe si tiene index.html válido; si no, la embebida.
"""
import os
import sys
from pathlib import Path

NOMBRE_DATOS = "Miauki YT"


def congelado() -> bool:
    """True cuando corre dentro del .exe de PyInstaller."""
    return bool(getattr(sys, "frozen", False))


def dir_del_programa() -> Path:
    """Carpeta del .exe (o del proyecto al correr desde el código)."""
    if congelado():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def recursos() -> Path:
    """Carpeta base de los recursos: _MEIPASS si está congelado."""
    if congelado():
        return Path(sys._MEIPASS)
    return dir_del_programa()


def es_portable() -> bool:
    return (dir_del_programa() / "portable.flag").exists()


def dir_datos() -> Path:
    """Carpeta de datos del usuario; la crea si no existe.

    Orden: `MIAUKI_DATOS` (pruebas y herramientas; ruta absoluta) → portable
    (`portable.flag` junto al .exe) → `%LOCALAPPDATA%\\Miauki YT`.
    """
    forzada = os.environ.get("MIAUKI_DATOS")
    if forzada:
        d = Path(forzada).expanduser().resolve()
    elif es_portable():
        d = dir_del_programa() / "reg-miau"
    else:
        d = Path(os.environ.get("LOCALAPPDATA") or str(Path.home())) / NOMBRE_DATOS
    d.mkdir(parents=True, exist_ok=True)
    return d


def dir_logs() -> Path:
    d = dir_datos() / "logs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def dir_perfil_webview() -> Path:
    """Perfil de WebView2 propio y estable (antes: %TEMP%\\tmpXXXX\\EBWebView).

    pywebview, en modo privado, usa `tempfile.TemporaryDirectory().name`: un
    nombre anónimo que nadie limpia si el proceso muere. Con una ruta fija
    dentro de la carpeta de datos, cualquier resto es demostrablemente nuestro.
    """
    d = dir_datos() / "webview2"
    d.mkdir(parents=True, exist_ok=True)
    return d


def ruta_ffmpeg() -> Path:
    return recursos() / "miauki" / "bin" / "ffmpeg.exe"


def fuente_interfaz() -> tuple[Path, str]:
    """Devolve (ruta del index.html, 'externa'|'embebida')."""
    externa = dir_del_programa() / "ui" / "index.html"
    if externa.is_file():
        return externa, "externa"
    return recursos() / "miauki" / "ui" / "index.html", "embebida"

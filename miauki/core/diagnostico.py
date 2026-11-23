# -*- coding: utf-8 -*-
"""Texto de diagnóstico para "Acerca de..." (Fase 5C, A4).

Regla de privacidad: NO sale ninguna ruta personal, ni cookies, ni links, ni
títulos. Solo versiones. El texto se copia al portapapeles a pedido del
usuario; nunca se envía a ningún lado.
"""
import os
import subprocess
import sys

from miauki import app_info, paths
from miauki.core import motor, webview2


def _windows() -> str:
    v = sys.getwindowsversion()
    nombre = {10: "Windows 10/11", 11: "Windows 11"}.get(v.major, f"Windows {v.major}")
    return f"{nombre} (build {v.build})"


def _ytdlp(idioma: str = "es") -> str:
    """Versión del motor en uso y de dónde salió (sin rutas)."""
    try:
        origen = motor.origen_en_uso()
        if idioma == "en":
            origen = {"incluida": "bundled", "actualizada": "updated"}.get(origen, origen)
        return f"{motor.version_en_uso()} ({origen})"
    except Exception:
        return "unavailable" if idioma == "en" else "no disponible"


def _ffmpeg(idioma: str = "es") -> str:
    """Primera línea de `ffmpeg -version`, sin la ruta del archivo."""
    try:
        r = subprocess.run(
            [str(paths.ruta_ffmpeg()), "-version"],
            capture_output=True, text=True, timeout=15,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        linea = (r.stdout or "").splitlines()[0] if r.stdout else ""
        # "ffmpeg version 8.0-full_build-www.gyan.dev Copyright (c) ..."
        partes = linea.split()
        if len(partes) >= 3 and partes[0] == "ffmpeg":
            return " ".join(partes[:3])
    except Exception:
        pass
    return "unavailable" if idioma == "en" else "no disponible"


def lineas(idioma: str = "es") -> list[str]:
    """Líneas de diagnóstico, con etiquetas según idioma (es/en)."""
    ok, msg = webview2.instalado()
    en = idioma == "en"
    if en:
        etiquetas = {"sistema": "System", "webview": "WebView2",
                      "motor": "yt-dlp", "ffmpeg": "ffmpeg"}
        no_webview = "not found"
    else:
        etiquetas = {"sistema": "Sistema", "webview": "WebView2",
                      "motor": "yt-dlp", "ffmpeg": "ffmpeg"}
        no_webview = "no encontrado"
    return [
        f"Miauki YT {app_info.VERSION}",
        f"{etiquetas['sistema']}: {_windows()}",
        f"{etiquetas['webview']}: {msg if ok else no_webview}",
        f"{etiquetas['motor']}: {_ytdlp(idioma)}",
        f"{etiquetas['ffmpeg']}: {_ffmpeg(idioma)}",
    ]


def texto(idioma: str = "es") -> str:
    return os.linesep.join(lineas(idioma))

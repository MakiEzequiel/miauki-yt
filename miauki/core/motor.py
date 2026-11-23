# -*- coding: utf-8 -*-
"""Única puerta a yt-dlp: versión activa, import diferido y reversa.

Nadie más hace `import yt_dlp`: todos piden el módulo por `motor.ytdlp()`.
Así la versión que se usa sale de un solo lugar y se puede cambiar entre
versiones descargadas (Fase 7, Parte A).

Estado en `%LOCALAPPDATA%\\Miauki YT\\motor.json`:

    {"activa": "2026.08.19" | null, "anterior": null, "malas": [],
     "ultima_comprobacion": "2026-10-20T19:30:00", "origen": "incluida"}

`activa` es una versión descargada en `motor/yt-dlp-<versión>/`; si es null se
usa la incluida en el .exe. Nunca se baja de versión por una fuente remota:
volver atrás es solo la reversa propia (import que falla → versión mala).
"""
import json
import shutil
import sys
import threading
from datetime import datetime
from pathlib import Path

from miauki import app_info, paths
from miauki.core.logger import obtener_logger

NOMBRE_ESTADO = "motor.json"
CARPETA_MOTOR = "motor"

_MODULO = None
_TRABA = threading.RLock()


# ---------- estado ----------

def ruta_estado() -> Path:
    return paths.dir_datos() / NOMBRE_ESTADO


def carpeta_motor() -> Path:
    """Carpeta donde viven las versiones descargadas."""
    return paths.dir_datos() / CARPETA_MOTOR


def carpeta_version(version: str) -> Path:
    return carpeta_motor() / ("yt-dlp-%s" % version)


def estado() -> dict:
    """Estado actual (tolera archivo ausente o roto)."""
    base = {"activa": None, "anterior": None, "malas": [],
            "ultima_comprobacion": None, "origen": "incluida"}
    try:
        datos = json.loads(ruta_estado().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return base
    if not isinstance(datos, dict):
        return base
    base.update({k: datos[k] for k in base if k in datos})
    if not isinstance(base["malas"], list):
        base["malas"] = []
    return base


def guardar_estado(**cambios) -> dict:
    """Actualiza el estado de forma atómica (temporal + reemplazo)."""
    with _TRABA:
        datos = estado()
        datos.update(cambios)
        ruta = ruta_estado()
        ruta.parent.mkdir(parents=True, exist_ok=True)
        temporal = ruta.with_suffix(".tmp")
        temporal.write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
        temporal.replace(ruta)
        return datos


def ahora() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


# ---------- versiones ----------

def tupla(version: str) -> tuple:
    """'2026.08.19' -> (2026, 8, 19); lo que no sea número vale 0."""
    partes = []
    for trozo in str(version or "").split("."):
        numero = ""
        for letra in trozo:
            if letra.isdigit():
                numero += letra
            else:
                break
        partes.append(int(numero) if numero else 0)
    return tuple(partes)


def version_en_uso() -> str:
    """Versión del yt-dlp que se está usando (o que se va a usar)."""
    if _MODULO is not None:
        return _MODULO.version.__version__
    activa = estado().get("activa")
    return activa or app_info.MOTOR_INCLUIDO


def origen_en_uso() -> str:
    return "actualizada" if estado().get("activa") else "incluida"


def esta_importado() -> bool:
    """True si la sesión ya cargó yt_dlp (entonces el cambio va al reiniciar)."""
    return _MODULO is not None


# ---------- importación ----------

def _limpiar_modulos() -> None:
    for nombre in [n for n in sys.modules if n == "yt_dlp" or n.startswith("yt_dlp.")]:
        del sys.modules[nombre]


def _importar(carpeta: Path | None):
    """Importa yt_dlp desde `carpeta` (o el incluido si es None)."""
    _limpiar_modulos()
    agregado = False
    if carpeta is not None:
        sys.path.insert(0, str(carpeta))
        agregado = True
    try:
        import yt_dlp
        if carpeta is not None:
            ubicacion = str(Path(yt_dlp.__file__).resolve())
            if not ubicacion.startswith(str(Path(carpeta).resolve())):
                raise ImportError("yt_dlp no salió de la carpeta pedida")
        return yt_dlp
    finally:
        if agregado:
            try:
                sys.path.remove(str(carpeta))
            except ValueError:
                pass


def ytdlp():
    """Módulo yt_dlp en uso. Import diferido: no toca nada hasta la primera vez."""
    global _MODULO
    with _TRABA:
        if _MODULO is not None:
            return _MODULO
        datos = estado()
        activa = datos.get("activa")
        if activa and activa not in datos.get("malas", []):
            carpeta = carpeta_version(activa)
            if carpeta.is_dir():
                try:
                    _MODULO = _importar(carpeta)
                    return _MODULO
                except Exception:  # noqa: BLE001  (reversa: cualquier falla)
                    obtener_logger().warning(
                        "Motor descargado %s no se pudo importar: se vuelve al anterior",
                        activa, exc_info=True)
                    _revertir(activa)
        try:
            _MODULO = _importar(None)
        except Exception:  # noqa: BLE001
            obtener_logger().error("No se pudo importar el yt-dlp incluido",
                                   exc_info=True)
            raise
        return _MODULO


def _revertir(version: str) -> None:
    """Marca la versión como mala y vuelve a la anterior (o a la incluida)."""
    datos = estado()
    malas = [m for m in datos.get("malas", []) if m != version]
    malas.append(version)
    anterior = datos.get("anterior")
    if anterior == version:
        anterior = None
    guardar_estado(activa=anterior, anterior=None, malas=malas,
                   origen="actualizada" if anterior else "incluida")


def activar(version: str | None) -> None:
    """Deja `version` como activa (None = incluida). Solo para reversa/UI."""
    datos = estado()
    guardar_estado(activa=version,
                   anterior=datos.get("activa"),
                   origen="actualizada" if version else "incluida")


def descartar_carpetas_viejas() -> None:
    """Borra las versiones descargadas que no sean la activa ni la anterior."""
    datos = estado()
    conservar = {datos.get("activa"), datos.get("anterior")} - {None}
    carpeta = carpeta_motor()
    if not carpeta.is_dir():
        return
    for ruta in carpeta.glob("yt-dlp-*"):
        if ruta.name.replace("yt-dlp-", "") not in conservar:
            shutil.rmtree(ruta, ignore_errors=True)


# ---------- prueba de humo ----------

# Respuesta de ejemplo guardada (recortada de un análisis real de YouTube, sin
# datos personales): sirve para probar el motor de formatos sin internet.
_EJEMPLO = {
    "id": "ejemplo", "title": "Ejemplo", "duration": 60,
    "webpage_url": "https://www.youtube.com/watch?v=ejemplo",
    "extractor": "youtube", "extractor_key": "Youtube",
    "_type": "video",
    "formats": [
        {"format_id": "137", "ext": "mp4", "height": 1080, "width": 1920,
         "vcodec": "avc1.640028", "acodec": "none", "tbr": 4000,
         "filesize": 30000000, "url": "https://ejemplo.invalid/137"},
        {"format_id": "140", "ext": "m4a", "vcodec": "none",
         "acodec": "mp4a.40.2", "abr": 128, "tbr": 128,
         "filesize": 960000, "url": "https://ejemplo.invalid/140"},
        {"format_id": "18", "ext": "mp4", "height": 360, "width": 640,
         "vcodec": "avc1.42001E", "acodec": "mp4a.40.2", "tbr": 500,
         "filesize": 3750000, "url": "https://ejemplo.invalid/18"},
    ],
}


def probar_motor(carpeta: str | Path, esperada: str = "") -> int:
    """Prueba de humo de UNA versión descargada, sin internet (--probar-motor).

    Importa solo esa carpeta, crea el extractor y corre el motor de selección
    de formatos con la respuesta de ejemplo. Devuelve 0 (sirve) o 1 (no).
    `esperada` es la versión del paquete (si no viene, se toma del nombre).
    """
    global _MODULO
    ruta = Path(carpeta)
    esperada = esperada or ruta.name.replace("yt-dlp-", "")
    try:
        _MODULO = _importar(ruta)
        if tupla(_MODULO.version.__version__) != tupla(esperada):
            print("FALLO versión: %s != %s" % (_MODULO.version.__version__, esperada))
            return 1
        opciones = {"quiet": True, "no_warnings": True}
        with _MODULO.YoutubeDL(opciones):
            pass
        from miauki.core import analyzer
        resultado = analyzer._resultado_de(dict(_EJEMPLO), "youtube", _EJEMPLO["webpage_url"])
        calidades = resultado.get("calidades") or []
        if not calidades or not calidades[0].get("selector"):
            print("FALLO formatos: %r" % (resultado,))
            return 1
        print("OK motor %s (%s)" % (_MODULO.version.__version__, _MODULO.__file__))
        return 0
    except Exception as e:  # noqa: BLE001
        print("FALLO %s: %s" % (type(e).__name__, e))
        return 1
    finally:
        _limpiar_modulos()
        _MODULO = None

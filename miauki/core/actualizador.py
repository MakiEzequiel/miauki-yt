# -*- coding: utf-8 -*-
"""Actualizador del motor yt-dlp (Fase 7, Parte A).

Diseño completo en docs/ACTUALIZADOR.md. Resumen:

- Fuente: PyPI (`/pypi/yt-dlp/json` + el wheel `py3-none-any`), con el sha256
  que publica el mismo JSON, y cruce con el lanzamiento oficial de GitHub.
- Nunca se baja ni se ejecuta un .exe. Tope de tamaño y de tiempo en todo.
- Antes de activar se prueba en un proceso aparte con `--probar-motor`.
- Cualquier falla se ignora en silencio (solo log) y se sigue con el motor
  actual. Una versión mala no se reintenta.

La interfaz llama a `api.comprobar_motor()`; el inicio automático llama a
`comprobar_en_segundo_plano()`.
"""
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

from miauki import app_info, paths
from miauki.core import motor
from miauki.core.logger import obtener_logger

URL_JSON = "https://pypi.org/pypi/yt-dlp/json"
URL_GITHUB = "https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest"
HOSTS = {"pypi.org", "files.pythonhosted.org", "api.github.com"}
TOPE_JSON = 2 * 1024 * 1024
TOPE_PAQUETE = 20 * 1024 * 1024
TOPE_PRUEBA = 60
MINUTOS_ENTRE_COMPROBACIONES = 10        # constante pedida por la fase
TIEMPO_HTTP = 10                         # segundos (JSON y GitHub)
TIEMPO_DESCARGA = 60
UA = "Miauki-YT/%s" % app_info.VERSION

_en_curso = threading.Lock()
_ya_comprobo = False


class Falla(Exception):
    """Falla interna del actualizador: se ignora y se sigue con el actual."""


# ---------- red ----------

def _abrir(url: str, tope: int, tiempo: int) -> bytes:
    """Descarga con lista blanca de hosts y tope de tamaño."""
    pedido = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "application/octet-stream, application/json",
    })
    with urllib.request.urlopen(pedido, timeout=tiempo) as respuesta:
        host = (respuesta.geturl().split("/")[2].split(":")[0]).lower()
        if host not in HOSTS:
            raise Falla("host no permitido tras redirección: %s" % host)
        largo = respuesta.headers.get("Content-Length")
        if largo and int(largo) > tope:
            raise Falla("respuesta demasiado grande (%s bytes)" % largo)
        trozos, total = [], 0
        while True:
            trozo = respuesta.read(65536)
            if not trozo:
                break
            total += len(trozo)
            if total > tope:
                raise Falla("respuesta más grande que el tope")
            trozos.append(trozo)
    return b"".join(trozos)


def _host_permitido(host: str) -> bool:
    return host in HOSTS


# ---------- selección de la versión ----------

def _elegir(datos: dict) -> dict:
    """Del JSON de PyPI saca el wheel puro y su sha256."""
    info = datos.get("info") or {}
    version = info.get("version") or ""
    if not version:
        raise Falla("PyPI no informó la versión")
    for archivo in datos.get("urls") or []:
        nombre = archivo.get("filename") or ""
        if archivo.get("packagetype") != "bdist_wheel":
            continue
        if not nombre.startswith("yt_dlp-") or not nombre.endswith("-py3-none-any.whl"):
            continue
        if archivo.get("yanked"):
            continue
        sha = ((archivo.get("digests") or {}).get("sha256") or "").lower()
        if len(sha) != 64:
            raise Falla("el wheel no trae sha256")
        tamano = int(archivo.get("size") or 0)
        if tamano <= 0 or tamano > TOPE_PAQUETE:
            raise Falla("tamaño del wheel fuera de rango: %s" % tamano)
        return {"version": version, "url": archivo.get("url"), "sha256": sha,
                "tamano": tamano, "archivo": nombre}
    raise Falla("PyPI no tiene el wheel py3-none-any")


def _existe_en_github(version: str, abrir=None) -> bool:
    """El lanzamiento oficial existe (segunda cuenta que habría que vulnerar).

    Se compara por números: PyPI dice "2026.8.19" y la etiqueta de GitHub
    "2026.08.19" (misma versión, distinto relleno).
    """
    abrir = abrir or _abrir
    try:
        datos = json.loads(abrir(URL_GITHUB, TOPE_JSON, TIEMPO_HTTP))
    except Exception:  # noqa: BLE001
        return False
    etiqueta = str(datos.get("tag_name") or "")
    return bool(etiqueta) and motor.tupla(etiqueta) == motor.tupla(version)


# ---------- extracción segura ----------

def _ruta_segura(nombre: str) -> PurePosixPath | None:
    """Normaliza una entrada del wheel; None si intenta salir de la carpeta."""
    if not nombre or "\\" in nombre or nombre.startswith("/"):
        return None
    partes = PurePosixPath(nombre)
    if any(p in ("..", "") or ":" in p for p in partes.parts):
        return None
    if partes.parts[0] != "yt_dlp":
        return None
    return partes


def _extraer(paquete: bytes, destino: Path) -> None:
    """Extrae solo el paquete yt_dlp, rechazando rutas maliciosas."""
    with zipfile.ZipFile(io.BytesIO(paquete)) as z:
        for entrada in z.infolist():
            if entrada.is_dir():
                continue
            relativa = _ruta_segura(entrada.filename)
            if relativa is None:
                continue           # arriba, absoluta, otra raíz: se ignora
            salida = destino.joinpath(*relativa.parts)
            salida.parent.mkdir(parents=True, exist_ok=True)
            salida.write_bytes(z.read(entrada))
    if not (destino / "yt_dlp" / "__init__.py").is_file():
        raise Falla("el paquete no trae yt_dlp/__init__.py")


# ---------- prueba de humo ----------

def _probar(carpeta: Path, version: str) -> bool:
    """Corre el propio .exe (o python app.py) con --probar-motor."""
    if paths.congelado():
        orden = [sys.executable, "--probar-motor", str(carpeta), version]
    else:
        raiz = Path(__file__).resolve().parent.parent.parent
        orden = [sys.executable, str(raiz / "app.py"), "--probar-motor", str(carpeta), version]
    try:
        hecho = subprocess.run(orden, capture_output=True, text=True,
                               timeout=TOPE_PRUEBA, encoding="utf-8", errors="replace")
    except (OSError, subprocess.SubprocessError):
        return False
    obtener_logger().info("Prueba del motor %s: código %s %s",
                          carpeta.name, hecho.returncode,
                          (hecho.stdout or "").strip()[:200])
    return hecho.returncode == 0


# ---------- comprobación ----------

def _reciente(estado: dict) -> bool:
    from datetime import datetime, timedelta
    ultima = estado.get("ultima_comprobacion")
    if not ultima:
        return False
    try:
        cuando = datetime.fromisoformat(ultima)
    except ValueError:
        return False
    return datetime.now() - cuando < timedelta(minutes=MINUTOS_ENTRE_COMPROBACIONES)


def comprobar(abrir=None, probar=None, forzar: bool = False) -> dict:
    """Comprueba, descarga, prueba y activa. Devuelve qué pasó (nunca lanza).

    {"accion": "al_dia"|"actualizada"|"omitida"|"fallo",
     "version": <en uso después>, "origen": "incluida"|"actualizada"}
    """
    abrir = abrir or _abrir
    probar = probar or _probar
    log = obtener_logger()
    datos = motor.estado()
    respuesta = {"accion": "al_dia", "version": motor.version_en_uso(),
                 "origen": motor.origen_en_uso()}
    try:
        if not forzar and _reciente(datos):
            respuesta["accion"] = "omitida"
            return respuesta
        motor.guardar_estado(ultima_comprobacion=motor.ahora())

        crudo = abrir(URL_JSON, TOPE_JSON, TIEMPO_HTTP)
        eleccion = _elegir(json.loads(crudo))
        actual = motor.version_en_uso()
        if motor.tupla(eleccion["version"]) <= motor.tupla(actual):
            return respuesta
        if eleccion["version"] in datos.get("malas", []):
            log.info("Motor %s está marcado como malo: no se reintenta", eleccion["version"])
            return respuesta
        if not _existe_en_github(eleccion["version"], abrir=abrir):
            raise Falla("la versión no existe como lanzamiento oficial")

        paquete = abrir(eleccion["url"], TOPE_PAQUETE, TIEMPO_DESCARGA)
        if len(paquete) > TOPE_PAQUETE:
            raise Falla("paquete más grande que el tope")
        if hashlib.sha256(paquete).hexdigest() != eleccion["sha256"]:
            raise Falla("hash incorrecto")

        motor.carpeta_motor().mkdir(parents=True, exist_ok=True)
        temporal = Path(tempfile.mkdtemp(prefix="tmp-", dir=str(motor.carpeta_motor())))
        try:
            _extraer(paquete, temporal)
            if not probar(temporal, eleccion["version"]):
                shutil.rmtree(temporal, ignore_errors=True)
                malas = list(datos.get("malas", [])) + [eleccion["version"]]
                motor.guardar_estado(malas=malas)
                log.warning("Motor %s no pasó la prueba: se descarta", eleccion["version"])
                return respuesta
            final = motor.carpeta_version(eleccion["version"])
            if final.exists():
                shutil.rmtree(final, ignore_errors=True)
            temporal.replace(final)
        except Exception:
            shutil.rmtree(temporal, ignore_errors=True)
            raise

        motor.guardar_estado(activa=eleccion["version"],
                             anterior=datos.get("activa"),
                             origen="actualizada")
        motor.descartar_carpetas_viejas()
        log.info("Motor actualizado a %s (se usa al reiniciar)", eleccion["version"])
        respuesta.update(accion="actualizada", version=eleccion["version"],
                         origen="actualizada")
        return respuesta
    except Exception as e:  # noqa: BLE001  (nunca rompe el inicio)
        log.info("Actualizador: se sigue con el motor actual (%s: %s)",
                 type(e).__name__, e)
        respuesta["accion"] = "fallo"
        return respuesta


def comprobar_en_segundo_plano() -> threading.Thread | None:
    """Comprobación automática del inicio: una por proceso, en un hilo."""
    global _ya_comprobo
    with _en_curso:
        if _ya_comprobo:
            return None
        _ya_comprobo = True
    from miauki.core import settings
    try:
        if settings.cargar().get("actualizar_motor_auto") is False:
            return None
        if _reciente(motor.estado()):
            return None
    except Exception:  # noqa: BLE001
        pass

    def _tarea():
        resultado = comprobar()
        if resultado.get("accion") == "actualizada":
            from miauki import events
            events.emitir("motor", {"actualizado": True,
                                    "version": resultado.get("version")})

    hilo = threading.Thread(target=_tarea, name="motor-actualizador", daemon=True)
    hilo.start()
    return hilo

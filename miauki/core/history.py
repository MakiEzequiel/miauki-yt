# -*- coding: utf-8 -*-
"""Historial de descargas (Fase 6, B1).

Archivo `historial.json` en la carpeta de datos del usuario:

- escritura ATÓMICA (temporal + `os.replace`) para no corromperlo si se corta
  la luz, y con un candado (`RLock`) porque la cola escribe desde su hilo;
- tope de 500 entradas: al pasarse se descartan las más viejas;
- tolerante a corrupción: si el JSON está roto se guarda una copia con otro
  nombre, se empieza vacío y se avisa en el log SIN contenido del archivo;
- solo se registra una descarga TERMINADA (la cola decide cuándo llamar);
- quitar una entrada la borra del archivo, miniatura incluida; el archivo
  descargado del disco NO se toca.

La fecha se guarda en UTC (ISO 8601) y la interfaz la muestra en hora de
Argentina. La miniatura solo se acepta si es un data URI de imagen válido
(≤ 300 KB reales); si se descarta, la interfaz muestra el gatito de respaldo.
"""
import base64
import json
import os
import re
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

from miauki import paths
from miauki.core.logger import obtener_logger

NOMBRE_ARCHIVO = "historial.json"
VERSION_ARCHIVO = 1
MAX_ENTRADAS = 500
# Tope de miniatura guardada (ajustes 21/11): antes 8 KB descartaba las
# vistas previas reales y el historial quedaba sin portadas. 300 KB alcanzan
# para las miniaturas típicas; las que excedan se descartan y la interfaz
# muestra el gatito de respaldo.
MAX_MINI_BYTES = 300 * 1024
MAX_TITULO = 500
MAX_TEXTO = 200
MAX_URL = 2048
TIPOS = ("video", "musica", "imagen")
_SITIOS = ("youtube", "tiktok", "instagram", "facebook", "x", "otro")
_MINI = re.compile(r"^data:image/(png|jpeg|jpg|webp|gif);base64,([A-Za-z0-9+/=]+)$")


def ruta_historial() -> Path:
    return paths.dir_datos() / NOMBRE_ARCHIVO


def _texto(valor, largo=MAX_TEXTO) -> str:
    return valor if isinstance(valor, str) and len(valor) <= largo else ""


def _fecha_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _miniatura_valida(uri) -> str:
    """Data URI de imagen con payload ≤ 8 KB reales, o ""."""
    if not isinstance(uri, str):
        return ""
    m = _MINI.match(uri)
    if not m:
        return ""
    try:
        if len(base64.b64decode(m.group(2), validate=True)) > MAX_MINI_BYTES:
            return ""
    except (ValueError, TypeError):
        return ""
    return uri


def _entrada_limpia(datos: dict) -> dict | None:
    if not isinstance(datos, dict):
        return None
    url = _texto(datos.get("url_canonica"), MAX_URL)
    if not url.lower().startswith(("http://", "https://")):
        return None
    tipo = datos.get("tipo")
    if tipo not in TIPOS:
        return None
    sitio = datos.get("sitio")
    peso = datos.get("peso")
    return {
        "id": uuid.uuid4().hex,
        "titulo": _texto(datos.get("titulo"), MAX_TITULO) or "Sin título",
        "sitio": sitio if sitio in _SITIOS else "otro",
        "tipo": tipo,
        "calidad": _texto(datos.get("calidad"), 40),
        "contenedor": _texto(datos.get("contenedor"), 10).lower(),
        "fecha": _fecha_utc(),
        "ruta": _texto(datos.get("ruta"), 32767),
        "peso": peso if isinstance(peso, int) and not isinstance(peso, bool) and peso >= 0 else 0,
        "url_canonica": url,
        "miniatura": _miniatura_valida(datos.get("miniatura")),
        # Datos para "Volver a bajar" (no se muestran en la lista).
        "selector": _texto(datos.get("selector"), 300),
        "resolucion": datos.get("resolucion") if isinstance(datos.get("resolucion"), int) else None,
        "kbps": datos.get("kbps") if isinstance(datos.get("kbps"), int) else None,
        "con_subs": datos.get("con_subs") is True,
    }


class Historial:
    """Lista de descargas terminadas, persistida en JSON."""

    def __init__(self, ruta: Path | None = None):
        self._ruta = Path(ruta) if ruta else ruta_historial()
        self._traba = threading.RLock()
        self._entradas: list[dict] | None = None   # carga perezosa

    # ---------- lectura / escritura ----------

    def _leer(self) -> list[dict]:
        if not self._ruta.is_file():
            return []
        try:
            datos = json.loads(self._ruta.read_text(encoding="utf-8"))
            entradas = datos.get("entradas") if isinstance(datos, dict) else None
            if not isinstance(entradas, list):
                raise ValueError("formato desconocido")
            return [e for e in entradas
                    if isinstance(e, dict) and isinstance(e.get("id"), str)]
        except (OSError, ValueError):
            self._respaldar_roto()
            return []

    def _respaldar_roto(self) -> None:
        """Copia el archivo ilegible a otro nombre y avisa sin mostrar contenido."""
        destino = self._ruta.with_name(
            f"{self._ruta.stem}.roto-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json")
        try:
            os.replace(self._ruta, destino)
        except OSError:
            obtener_logger().warning("Historial ilegible y no se pudo respaldar")
            return
        # Sin títulos ni links: solo el hecho y el nombre del respaldo.
        obtener_logger().warning("Historial ilegible: copia en %s, se empieza vacío",
                                 destino.name)

    def _guardar(self) -> None:
        temporal = self._ruta.with_name(self._ruta.name + ".tmp")
        temporal.write_text(
            json.dumps({"version": VERSION_ARCHIVO, "entradas": self._entradas},
                       ensure_ascii=False, indent=1),
            encoding="utf-8",
        )
        os.replace(temporal, self._ruta)

    def _listos(self) -> list[dict]:
        if self._entradas is None:
            self._entradas = self._leer()
        return self._entradas

    # ---------- contrato ----------

    def listar(self) -> list[dict]:
        """Todas las entradas, de la más nueva a la más vieja."""
        with self._traba:
            return [dict(e) for e in self._listos()]

    def obtener(self, ident) -> dict | None:
        if not isinstance(ident, str) or not ident:
            return None
        with self._traba:
            for entrada in self._listos():
                if entrada["id"] == ident:
                    return dict(entrada)
        return None

    def agregar(self, datos: dict) -> dict | None:
        entrada = _entrada_limpia(datos)
        if entrada is None:
            obtener_logger().warning("Historial: entrada descartada por inválida")
            return None
        with self._traba:
            entradas = self._listos()
            entradas.insert(0, entrada)
            del entradas[MAX_ENTRADAS:]
            self._guardar()
        obtener_logger().info("Historial: descarga registrada (%s)", entrada["tipo"])
        return dict(entrada)

    def quitar(self, ident) -> bool:
        """Borra UNA entrada del archivo (miniatura incluida). El archivo
        descargado NO se toca."""
        if not isinstance(ident, str) or not ident:
            return False
        with self._traba:
            entradas = self._listos()
            for i, entrada in enumerate(entradas):
                if entrada["id"] == ident:
                    del entradas[i]
                    self._guardar()
                    obtener_logger().info("Historial: entrada quitada")
                    return True
        return False

    def borrar(self) -> int:
        """Vacía el historial. Devuelve cuántas entradas había."""
        with self._traba:
            n = len(self._listos())
            self._entradas = []
            self._guardar()
        if n:
            obtener_logger().info("Historial: borrado completo (%s entradas)", n)
        return n


_historial = None


def obtener() -> Historial:
    global _historial
    if _historial is None:
        _historial = Historial()
    return _historial

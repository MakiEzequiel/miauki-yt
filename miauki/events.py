# -*- coding: utf-8 -*-
"""Avisos de Python hacia la interfaz (progreso, cola, errores).

Seguros entre hilos: pywebview encola las llamadas a run_js. Los datos se
serializan SIEMPRE con json.dumps (nunca se concatena texto del usuario
dentro de JavaScript). Se usa run_js y no evaluate_js porque la app corre
con CSP estricta (sin unsafe-eval).
"""
import json

from miauki.core.logger import obtener_logger

_ventana = None
_suscriptores = []


def conectar(ventana) -> None:
    """Guarda la ventana de pywebview para poder avisarle."""
    global _ventana
    _ventana = ventana


def suscribir(fn) -> None:
    """Registra fn(evento, datos) para lo que pase dentro de Python (Fase 7 B3).

    Se usa para avisar en la barra de tareas cuando termina una descarga.
    """
    if fn not in _suscriptores:
        _suscriptores.append(fn)


def emitir(evento: str, datos=None) -> None:
    """Llama a window.miaukiEventos({evento, datos}) en la interfaz."""
    for fn in list(_suscriptores):
        try:
            fn(evento, datos)
        except Exception:  # noqa: BLE001  (un aviso no rompe la descarga)
            obtener_logger().exception("Fallo un suscriptor del evento %s", evento)
    if _ventana is None:
        return
    carga = json.dumps({"evento": evento, "datos": datos}, ensure_ascii=False)
    try:
        _ventana.run_js(f"window.miaukiEventos && window.miaukiEventos({carga})")
    except Exception:
        obtener_logger().exception("No se pudo emitir el evento %s", evento)

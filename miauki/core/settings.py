# -*- coding: utf-8 -*-
"""Configuración de la app: única fuente de verdad.

Archivo ajustes.json en la carpeta de datos (paths.dir_datos()).
Escritura atómica (archivo temporal + reemplazo) para no corromperse si se
corta la luz. La interfaz solo pasa por el puente (api.obtener_ajustes /
api.cambiar_ajuste); la Fase 6 la conectará de verdad.
"""
import ctypes
import json
import os
from pathlib import Path

from miauki import paths
from miauki.core.logger import obtener_logger

NOMBRE_ARCHIVO = "ajustes.json"


class AjusteInvalido(ValueError):
    """Ajuste inexistente o con valor inválido: mensaje amable, va al puente."""


def ruta_ajustes() -> Path:
    return paths.dir_datos() / NOMBRE_ARCHIVO


# {374DE290-123F-4565-9164-39C4925E467B} = FOLDERID_Downloads (doc Microsoft)
class _GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", ctypes.c_uint32),
        ("Data2", ctypes.c_uint16),
        ("Data3", ctypes.c_uint16),
        ("Data4", ctypes.c_ubyte * 8),
    ]


_FOLDERID_DESCARGAS = _GUID(
    0x374DE290, 0x123F, 0x4565,
    (0x91, 0x64, 0x39, 0xC4, 0x92, 0x5E, 0x46, 0x7B),
)


def carpeta_descargas_por_defecto() -> str:
    """Carpeta Descargas del sistema vía SHGetKnownFolderPath.

    API de Windows, no "C:\\Users\\...": la carpeta puede estar redirigida
    (OneDrive, disco aparte). Si falla, respaldo en ~/Downloads.
    """
    salida = ctypes.c_wchar_p()
    try:
        hr = ctypes.windll.shell32.SHGetKnownFolderPath(
            ctypes.byref(_FOLDERID_DESCARGAS), 0, None, ctypes.byref(salida)
        )
        if hr == 0 and salida.value:
            texto = salida.value
            ctypes.windll.ole32.CoTaskMemFree(salida)
            if os.path.isdir(texto):
                return texto
    except Exception:
        pass
    return str(Path.home() / "Downloads")


def predeterminados() -> dict:
    return {
        "carpeta_descargas": carpeta_descargas_por_defecto(),
        "idioma_subs": "es",
        "incluir_subs": True,
        "navegador_cookies": "ninguno",
        # Fase 9, B2b: ruta a un cookies.txt Netscape (solo la ruta, no el archivo).
        "archivo_cookies": "",
        "fxtwitter": True,
        "idioma_interfaz": "es",
        "guardar_historial": True,
        # Fase 7, B1: H.264 + AAC hasta 1080p (se abre en cualquier reproductor).
        "maxima_compatibilidad": True,
        # Fase 7, A3: comprobar y bajar una versión nueva de yt-dlp al abrir.
        "actualizar_motor_auto": True,
        # Fase 7, C: el recorrido guiado se muestra una sola vez.
        "recorrido_visto": False,
        # Plan archivos y cola, paso 3: tamaño de la letra de toda la app.
        "tamano_fuente": "normal",
    }


_VALORES_PERMITIDOS = {
    "idioma_subs": {"es", "en"},
    "idioma_interfaz": {"es", "en"},
    "navegador_cookies": {"ninguno", "edge", "chrome", "firefox",
                          "brave", "chromium", "opera", "vivaldi"},
    "tamano_fuente": {"normal", "grande"},
}


def cargar(ruta: Path | None = None) -> dict:
    """Ajustes actuales (predeterminados + archivo). No crea el archivo."""
    ruta = ruta or ruta_ajustes()
    base = predeterminados()
    if not ruta.is_file():
        return base
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        obtener_logger().warning("Ajustes ilegibles, uso predeterminados: %s", ruta)
        return base
    if not isinstance(datos, dict):
        return base
    return {**base, **{k: datos[k] for k in base if k in datos and type(datos[k]) is type(base[k])}}


def guardar(ajustes: dict, ruta: Path | None = None) -> None:
    """Escribe los ajustes de forma atómica (temporal + reemplazo)."""
    ruta = ruta or ruta_ajustes()
    base = predeterminados()
    limpios = {k: ajustes[k] for k in base if k in ajustes}
    temporal = ruta.with_suffix(".json.tmp")
    temporal.write_text(
        json.dumps(limpios, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    os.replace(temporal, ruta)


def cambiar(clave: str, valor, ruta: Path | None = None) -> dict:
    """Cambia un ajuste, lo valida y lo guarda. Devuelve los ajustes completos."""
    base = predeterminados()
    if clave not in base:
        raise AjusteInvalido(f"No existe el ajuste «{clave}».")
    if clave == "carpeta_descargas":
        if not isinstance(valor, str) or not valor.strip():
            raise AjusteInvalido("La carpeta de descargas no puede quedar vacía.")
    elif type(base[clave]) is bool:
        if not isinstance(valor, bool):
            raise AjusteInvalido(f"«{clave}» espera sí o no.")
    elif not isinstance(valor, str):
        raise AjusteInvalido(f"«{clave}» espera una palabra.")
    permitidos = _VALORES_PERMITIDOS.get(clave)
    if permitidos and valor not in permitidos:
        opciones = ", ".join(sorted(permitidos))
        raise AjusteInvalido(f"«{valor}» no es válido para {clave} (usa: {opciones}).")
    actuales = cargar(ruta)
    actuales[clave] = valor
    guardar(actuales, ruta)
    return actuales

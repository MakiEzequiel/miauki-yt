# -*- coding: utf-8 -*-
"""Detección e instalación del WebView2 Runtime (flujo B de la especificación).

Fuente: doc oficial de Microsoft (learn.microsoft.com/microsoft-edge/webview2/
concepts/distribution, verificada el 12/10/2026):
- Detección: clave pv en HKLM (WOW6432Node) y HKCU, {F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}.
- Instalación: Evergreen Bootstrapper descargado por el fwlink oficial ("Get the Link")
  y ejecutado con /silent /install.
Seguridad: solo HTTPS y hostes de Microsoft; firma Authenticode verificada con
WinVerifyTrust antes de ejecutar; shell=False con tiempo límite; el archivo
descargado se borra siempre. Windows mínimo del conjunto: 10 versión 1709.
"""
import os
import shutil
import subprocess
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path

from miauki import app_info
from miauki.core.logger import obtener_logger

CLAVE = "{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"
URL_OFICIAL = "https://go.microsoft.com/fwlink/?linkid=2124703"  # Get the Link (bootstrapper)
VAR_TEST = "MIAUKI_TEST_WEBVIEW2"  # fuerza escenarios de prueba; nunca en uso normal

MENSAJE_SIN_RED = (
    "No se pudo descargar el componente necesario (WebView2) porque no hay "
    "internet o Microsoft no respondió. Conectate a internet y volvé a abrir "
    "Miauki YT, o instalá WebView2 desde la página oficial de Microsoft: "
    "https://developer.microsoft.com/microsoft-edge/webview2/consumer/"
)
MENSAJE_FIRMA = (
    "El instalador de WebView2 no tiene la firma digital de Microsoft, así que "
    "no se ejecuta por seguridad. Descargalo vos mismo desde la página oficial: "
    "https://developer.microsoft.com/microsoft-edge/webview2/consumer/"
)


def instalado() -> tuple[bool, str]:
    """(True, versión) si el Runtime está; MIAUKI_TEST_WEBVIEW2 fuerza 'no instalado'."""
    sim = os.environ.get(VAR_TEST)
    if sim:
        return False, f"simulado: no instalado (escenario {sim})"
    import winreg

    rutas = (
        "SOFTWARE\\WOW6432Node\\Microsoft\\EdgeUpdate\\Clients\\" + CLAVE,
        "SOFTWARE\\Microsoft\\EdgeUpdate\\Clients\\" + CLAVE,
    )
    for raiz_reg in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        for sub in rutas:
            try:
                with winreg.OpenKey(raiz_reg, sub) as k:
                    pv, _ = winreg.QueryValueEx(k, "pv")
                if pv and pv != "0.0.0.0":
                    return True, f"WebView2 Runtime {pv}"
            except OSError:
                continue
    return False, "WebView2 Runtime no encontrado"


def _url_permitida(url: str) -> bool:
    """Solo HTTPS en hostes de Microsoft (fwlink o CDN de Microsoft)."""
    if not url.lower().startswith("https://"):
        return False
    host = (urllib.parse.urlparse(url).hostname or "").lower()
    return (
        host == "go.microsoft.com"
        or host.endswith(".microsoft.com")
        or host.endswith(".dl.delivery.mp.microsoft.com")
    )


def descargar(url: str, destino: Path) -> None:
    """Descarga por urllib validando el host de la URL final (redirecciones incluidas)."""
    if not _url_permitida(url):
        raise ValueError(f"URL no permitida: {url}")
    req = urllib.request.Request(url, headers={"User-Agent": f"MiaukiYT/{app_info.VERSION}"})
    with urllib.request.urlopen(req, timeout=120) as respuesta:
        if not _url_permitida(respuesta.geturl()):
            raise ValueError(f"La descarga redirigió a un sitio no permitido: {respuesta.geturl()}")
        with destino.open("wb") as f:
            shutil.copyfileobj(respuesta, f)


def firma_valida(ruta: Path) -> bool:
    """Verifica la firma Authenticode con WinVerifyTrust (API nativa, sin shell)."""
    import ctypes
    from ctypes import wintypes

    class WINTRUST_FILE_INFO(ctypes.Structure):
        _fields_ = [
            ("cbStruct", wintypes.DWORD),
            ("pcwszFilePath", wintypes.LPCWSTR),
            ("hFile", ctypes.c_void_p),
            ("pgKnownSubject", ctypes.c_void_p),
        ]

    class WINTRUST_DATA(ctypes.Structure):
        _fields_ = [
            ("cbStruct", wintypes.DWORD),
            ("pPolicyCallbackData", ctypes.c_void_p),
            ("pSIPClientData", ctypes.c_void_p),
            ("dwUIChoice", wintypes.DWORD),
            ("fdwRevocationChecks", wintypes.DWORD),
            ("dwUnionChoice", wintypes.DWORD),
            ("pFile", ctypes.POINTER(WINTRUST_FILE_INFO)),
            ("dwStateAction", wintypes.DWORD),
            ("hWVTStateData", ctypes.c_void_p),
            ("pwszURLReference", wintypes.LPCWSTR),
            ("dwProvFlags", wintypes.DWORD),
            ("dwUIContext", wintypes.DWORD),
            ("pSignatureSettings", ctypes.c_void_p),
        ]

    # WINTRUST_ACTION_GENERIC_VERIFY_V2 = {00AAC56B-CD44-11d0-8CC2-00C04FC295EE}
    accion = (ctypes.c_byte * 16)(
        0x6B, 0xC5, 0xAA, 0x00, 0x44, 0xCD, 0xD0, 0x11,
        0x8C, 0xC2, 0x00, 0xC0, 0x4F, 0xC2, 0x95, 0xEE,
    )
    info = WINTRUST_FILE_INFO(ctypes.sizeof(WINTRUST_FILE_INFO), str(ruta), None, None)
    datos = WINTRUST_DATA()
    datos.cbStruct = ctypes.sizeof(WINTRUST_DATA)
    datos.dwUIChoice = 2               # WTD_UI_NONE: sin ventana
    datos.fdwRevocationChecks = 0      # WTD_REVOKE_NONE
    datos.dwUnionChoice = 1            # WTD_CHOICE_FILE
    datos.pFile = ctypes.pointer(info)
    datos.dwStateAction = 1            # WTD_STATEACTION_VERIFY
    datos.dwProvFlags = 0x10           # WTD_CACHE_ONLY_URL_RETRIEVAL: sin red

    wintrust = ctypes.WinDLL("wintrust")
    wintrust.WinVerifyTrust.argtypes = [wintypes.HWND, ctypes.c_void_p, ctypes.c_void_p]
    wintrust.WinVerifyTrust.restype = wintypes.LONG
    resultado = wintrust.WinVerifyTrust(0, ctypes.byref(accion), ctypes.byref(datos))
    datos.dwStateAction = 2            # WTD_STATEACTION_CLOSE
    wintrust.WinVerifyTrust(0, ctypes.byref(accion), ctypes.byref(datos))
    return resultado == 0


def garantizar() -> tuple[bool, str]:
    """Flujo completo: detectar; si falta, descargar, firmar, instalar y re-detectar."""
    ok, msg = instalado()
    if ok:
        return True, msg

    sim = os.environ.get(VAR_TEST, "")
    if sim == "exito":
        return True, "simulado: instalación correcta (escenario de prueba)"
    if sim == "sin-internet":
        return False, MENSAJE_SIN_RED
    if sim == "firma-mala":
        return False, MENSAJE_FIRMA
    if sim:
        # Cualquier escenario simulado (incluido "falta") NO toca la red ni instala
        return False, f"simulado: WebView2 ausente, no se intenta instalar (escenario {sim})"

    log = obtener_logger()
    destino = Path(tempfile.gettempdir()) / "miauki_webview2_setup.exe"
    try:
        try:
            descargar(URL_OFICIAL, destino)
        except Exception:
            log.exception("Falla al descargar el bootstrapper de WebView2")
            return False, MENSAJE_SIN_RED
        if not firma_valida(destino):
            log.error("Bootstrapper de WebView2 sin firma válida: %s", destino)
            return False, MENSAJE_FIRMA
        try:
            # shell=False + /silent /install: doc oficial "Online-only deployment"
            r = subprocess.run(
                [str(destino), "/silent", "/install"],
                shell=False, timeout=600,
            )
        except subprocess.TimeoutExpired:
            log.error("El instalador de WebView2 superó el tiempo máximo")
            return False, "La instalación de WebView2 tardó demasiado. Probá de nuevo más tarde."
        ok2, msg2 = instalado()
        if ok2:
            log.info("WebView2 instalado correctamente (%s, código %s)", msg2, r.returncode)
            return True, msg2
        log.error("El instalador terminó (%s) pero WebView2 sigue sin estar", r.returncode)
        return False, (
            "El instalador de WebView2 terminó pero el componente sigue sin estar "
            "disponible. Reiniciá el PC y volvé a abrir Miauki YT, o instalalo desde "
            "https://developer.microsoft.com/microsoft-edge/webview2/consumer/"
        )
    finally:
        destino.unlink(missing_ok=True)

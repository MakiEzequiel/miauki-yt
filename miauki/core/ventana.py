# -*- coding: utf-8 -*-
"""Aviso en la barra de tareas al terminar una descarga (Fase 7, B3).

Cuando una descarga TERMINA bien y la ventana no está en primer plano, se
hace parpadear el botón de la barra de tareas (y el borde) hasta que la
persona vuelve. Si la ventana ya está al frente no se hace nada, y nunca hay
sonido.

`FlashWindowEx` (user32) con `FLASHW_ALL | FLASHW_TIMERNOFG`: "sigue
parpadeando hasta que la ventana pase a primer plano" (documentación de
Microsoft, `FLASHWINFO`). Sin dependencias: ctypes.
"""
import ctypes
import os
from ctypes import wintypes

FLASHW_ALL = 0x00000003          # borde + botón de la barra de tareas
FLASHW_TIMERNOFG = 0x0000000C    # seguir hasta que pase a primer plano
GA_ROOT = 2


class _FLASHWINFO(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.UINT),
                ("hwnd", wintypes.HWND),
                ("dwFlags", wintypes.DWORD),
                ("uCount", wintypes.UINT),
                ("dwTimeout", wintypes.DWORD)]


def _user32():
    return ctypes.windll.user32


def hwnd_propio(titulo: str) -> int | None:
    """Ventana de ESTE proceso con ese título (o None).

    Se busca por proceso y título: el título lo fija la app, y así no se
    confunde con otra ventana igual de otro programa. No se exige que esté
    visible: pywebview la muestra un instante después de crearla.
    """
    user32 = _user32()
    encontradas = []
    pid = os.getpid()

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def _mirar(hwnd, _param):
        dueño = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(dueño))
        if dueño.value != pid:
            return True
        buf = ctypes.create_unicode_buffer(256)
        user32.GetWindowTextW(hwnd, buf, 256)
        if buf.value == titulo:
            encontradas.append(hwnd)
        return True

    user32.EnumWindows(_mirar, 0)
    return encontradas[0] if encontradas else None


def esta_al_frente(hwnd: int) -> bool:
    """True si esa ventana tiene el foco del sistema (y no está minimizada)."""
    if not hwnd:
        return False
    user32 = _user32()
    if user32.IsIconic(hwnd):
        # Minimizada: aunque Windows la deje como "ventana activa", no se ve.
        return False
    al_frente = user32.GetForegroundWindow()
    if not al_frente:
        return False
    return user32.GetAncestor(al_frente, GA_ROOT) == hwnd


def destellar(hwnd: int) -> bool:
    """Hace parpadear la ventana hasta que pase al frente. True si Windows quiso."""
    if not hwnd:
        return False
    try:
        info = _FLASHWINFO(ctypes.sizeof(_FLASHWINFO), hwnd,
                           FLASHW_ALL | FLASHW_TIMERNOFG, 0, 0)
        return bool(_user32().FlashWindowEx(ctypes.byref(info)))
    except Exception:  # noqa: BLE001  (nunca rompe una descarga por esto)
        return False


class AvisosDeFin:
    """Decide CUÁNDO avisar: una descarga nueva que terminó bien.

    Lógica pura y aparte de Windows (`destello` y `al_frente` se inyectan) para
    poder probarla sin ventana.
    """

    def __init__(self, buscar_hwnd, destello=destellar, al_frente=esta_al_frente):
        self._buscar_hwnd = buscar_hwnd
        self._destello = destello
        self._al_frente = al_frente
        self._vistos: set[str] = set()
        self._primera = True

    def revisar(self, items) -> bool:
        """Mira la lista de la Cola y destella si hay un final nuevo. Devuelve True si destelló."""
        terminados = {i.get("id") for i in (items or [])
                      if isinstance(i, dict) and i.get("estado") == "terminada"}
        terminados.discard(None)
        nuevos = terminados - self._vistos
        self._vistos = terminados
        if self._primera:
            # La primera lista es la que ya estaba: no se avisa de lo viejo.
            self._primera = False
            return False
        if not nuevos:
            return False
        hwnd = self._buscar_hwnd()
        if not hwnd or self._al_frente(hwnd):
            return False
        return bool(self._destello(hwnd))

    def al_evento(self, evento: str, datos) -> None:
        """Atajo para `events.suscribir`."""
        if evento == "cola":
            self.revisar(datos)

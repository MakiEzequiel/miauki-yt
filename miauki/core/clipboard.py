# -*- coding: utf-8 -*-
"""Link del portapapeles de Windows (Fase 5 Parte B, B1).

Sin dependencias: `user32`/`kernel32` con ctypes. Dos reglas fijas:

- **nunca se loguea el contenido** del portapapeles (privacidad): solo sale
  de acá un link ya validado, o `None`;
- cualquier falla (portapapeles tomado por otro programa, formato raro, texto
  enorme) devuelve `None`: el aviso simplemente no aparece.
"""
import ctypes
from ctypes import wintypes

from miauki.core import sites

CF_UNICODETEXT = 13
_LARGO_MAX = 2048            # el mismo tope que valida el puente para un link
_LEER_MAX = 64 * 1024        # no se escanea un texto más grande
_ABRE = "([<\"'«“"
_CIERRA = ".,;:!?)]}>\"'»”’"


def _texto_windows() -> str | None:
    """Texto plano del portapapeles, o None si no hay o no se puede leer."""
    try:
        u = ctypes.windll.user32
        k = ctypes.windll.kernel32
        u.GetClipboardData.argtypes = [wintypes.UINT]
        u.GetClipboardData.restype = wintypes.HANDLE
        k.GlobalLock.argtypes = [wintypes.HGLOBAL]
        k.GlobalLock.restype = wintypes.LPVOID
        k.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
        k.GlobalUnlock.restype = wintypes.BOOL
        k.GlobalSize.argtypes = [wintypes.HGLOBAL]
        k.GlobalSize.restype = ctypes.c_size_t

        if not u.OpenClipboard(None):
            return None
        try:
            if not u.IsClipboardFormatAvailable(CF_UNICODETEXT):
                return None
            manejador = u.GetClipboardData(CF_UNICODETEXT)
            if not manejador:
                return None
            puntero = k.GlobalLock(manejador)
            if not puntero:
                return None
            try:
                # wstring_at(puntero, n) lee EXACTAMENTE n caracteres y NO se
                # detiene en el NUL: pedir 64 K sobre un bloque de 40 bytes es
                # una violación de acceso (se vio 9 veces en el soak del
                # 20/10/2026). Se lee solo lo que entra en el bloque real.
                tam = int(k.GlobalSize(manejador))
                if tam < 2:
                    return None
                crudo = ctypes.wstring_at(puntero, min(tam // 2, _LEER_MAX))
            finally:
                k.GlobalUnlock(manejador)
        finally:
            u.CloseClipboard()
    except Exception:
        return None
    return crudo.split("\x00", 1)[0]


def link_en_texto(texto) -> str | None:
    """Primer link del texto, sin la puntuación pegada al final.

    Acepta `http://`, `https://`, `www.` y un dominio con ruta
    (`minombre.io/video`), suelto o dentro de una frase ("mirá esto: <link>."),
    con paréntesis o comillas alrededor. A un link sin esquema se le agrega
    `https://`. Un dominio SIN ruta no cuenta: en una frase ("visita
    minombre.io") sería un falso positivo. Devuelve None si no hay ninguno.
    """
    if not isinstance(texto, str) or not texto:
        return None
    for trozo in texto[:_LEER_MAX].split():
        # La normalización vive en sites (plan `plan.md`, paso 3.5): acá solo
        # se recorta la puntuación pegada y se aplica el tope de largo.
        url = sites.normalizar_url(trozo.lstrip(_ABRE).rstrip(_CIERRA))
        if url and 10 <= len(url) <= _LARGO_MAX:
            return url
    return None


def link_del_portapapeles() -> str | None:
    """Atajo para el puente: lee el portapapeles y devuelve el link o None."""
    return link_en_texto(_texto_windows() or "")


def texto_del_portapapeles() -> str | None:
    """Texto plano del portapapeles (Ctrl+V y arrastrar, Fase 7 B2).

    Igual que todo lo demás acá: no se registra en ningún lado; quien llama
    lo valida y lo descarta.
    """
    return _texto_windows()


GMEM_MOVEABLE = 0x0002


def copiar_texto(texto: str) -> bool:
    """Pone texto plano en el portapapeles. True si Windows lo aceptó.

    Se usa para "Copiar información de diagnóstico" (A4). No lee nada.
    """
    if not isinstance(texto, str) or not texto:
        return False
    bloque = None
    try:
        u = ctypes.windll.user32
        k = ctypes.windll.kernel32
        k.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
        k.GlobalAlloc.restype = wintypes.HGLOBAL
        k.GlobalLock.argtypes = [wintypes.HGLOBAL]
        k.GlobalLock.restype = wintypes.LPVOID
        k.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
        k.GlobalUnlock.restype = wintypes.BOOL
        u.OpenClipboard.argtypes = [wintypes.HWND]
        u.OpenClipboard.restype = wintypes.BOOL
        u.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
        u.SetClipboardData.restype = wintypes.HANDLE
        datos = ctypes.create_unicode_buffer(texto)
        tam = ctypes.sizeof(datos)
        bloque = k.GlobalAlloc(GMEM_MOVEABLE, tam)
        if not bloque:
            return False
        puntero = k.GlobalLock(bloque)
        if not puntero:
            return False
        ctypes.memmove(puntero, datos, tam)
        k.GlobalUnlock(bloque)
        if not u.OpenClipboard(None):
            return False
        try:
            u.EmptyClipboard()
            if not u.SetClipboardData(CF_UNICODETEXT, bloque):
                return False
            bloque = None  # ahora es del portapapeles: no se libera
            return True
        finally:
            u.CloseClipboard()
    except Exception:
        return False
    finally:
        if bloque:
            ctypes.windll.kernel32.GlobalFree(bloque)

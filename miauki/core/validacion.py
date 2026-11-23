# -*- coding: utf-8 -*-
"""Validación de seguridad del borde (Fase 4 Parte 0, P0.7).

Todo lo que llega de la interfaz se trata como hostil: el snapshot del
encolado, las rutas que se abren y la carpeta de descargas que se elige.
Acá viven las reglas, con sus tests, para que el puente y el descargador
solo usen datos ya limpios.

Reglas:
- El snapshot solo puede traer las claves permitidas, con tipos y largos
  acotados; nada de `outtmpl`, rutas de salida ni opciones de yt-dlp.
- El selector solo puede tener caracteres de id de formato (`+` para el
  combo); el contenedor y el kbps van contra listas cerradas.
- La miniatura solo puede ser `data:image/` y con tope de tamaño.
- Ninguna ruta puede salir de la carpeta elegida (ni con `..`).
- "Cambiar carpeta" rechaza raíces del sistema y carpetas de Windows o de
  Archivos de programa, y verifica que se pueda escribir.
"""
import os
import re

from miauki.core import sites
from miauki.core.errors import ErrorMiauki

# ---------- snapshot del encolado ----------

CLAVES_PERMITIDAS = {
    "url_canonica", "tipo", "selector", "contenedor", "kbps",
    "titulo", "miniatura", "con_subs", "resolucion", "sitio",
    "url_directa",  # opción "Original" (p.ej. Snapchat): se baja sin yt-dlp
    "entradas",     # playlist: lista de snapshots de video (Paso 3)
}
TIPOS = ("video", "musica", "imagen")
CONTENEDORES = (None, "mp4", "mkv")
KBPS = (None, 128, 256, 320)
MAX_PLAYLIST = 600                  # protección de memoria (decisión de Maki)
TAM_BLOQUE = 200                    # playlists por bloques de 200 (plan ajustes UI)

# Normalización de links compartida (plan `plan.md`, paso 3.5): una sola
# implementación (la de sites) para que el borde, el portapapeles y la
# interfaz no acepten cosas distintas.
normalizar_url = sites.normalizar_url

_LARGO_URL = 2048
_LARGO_TITULO = 500
_LARGO_MINiatura = 3_000_000          # ~3 MB de data-URI
# El selector ahora es una expresión de yt-dlp por altura/códec con
# respaldos (P0.5): permite letras, números, . , + - [ ] = < > ^ / ().
_SELECTOR = re.compile(r"^[A-Za-z0-9_.,+\-\[\]=<>^/()]{1,300}$")


def _texto(valor, largo) -> bool:
    return isinstance(valor, str) and 0 < len(valor) <= largo


def snapshot_limpio(snapshot) -> dict:
    """Devuelve solo las claves permitidas, validadas. Lanza ErrorMiauki."""
    if not isinstance(snapshot, dict):
        raise ErrorMiauki("entrada_invalida")

    url = snapshot.get("url_canonica")
    if not _texto(url, _LARGO_URL):
        raise ErrorMiauki("link_invalido")
    if not url.lower().startswith(("http://", "https://")):
        raise ErrorMiauki("link_invalido")

    tipo = snapshot.get("tipo")
    if tipo not in TIPOS:
        raise ErrorMiauki("entrada_invalida")

    selector = snapshot.get("selector")
    if tipo in ("video", "musica"):
        if not isinstance(selector, str) or not _SELECTOR.match(selector):
            raise ErrorMiauki("entrada_invalida")
    else:                              # imagen: sin selector
        if selector not in (None, ""):
            raise ErrorMiauki("entrada_invalida")

    contenedor = snapshot.get("contenedor")
    if contenedor not in CONTENEDORES:
        raise ErrorMiauki("entrada_invalida")

    kbps = snapshot.get("kbps")
    if kbps not in KBPS:
        raise ErrorMiauki("entrada_invalida")

    titulo = snapshot.get("titulo")
    if titulo is not None and not _texto(titulo, _LARGO_TITULO):
        raise ErrorMiauki("entrada_invalida")

    mini = snapshot.get("miniatura")
    if mini not in (None, ""):
        if not (isinstance(mini, str)
                and mini.startswith("data:image/")
                and len(mini) <= _LARGO_MINiatura):
            raise ErrorMiauki("entrada_invalida")

    con_subs = snapshot.get("con_subs", False)
    if not isinstance(con_subs, bool):
        raise ErrorMiauki("entrada_invalida")

    resolucion = snapshot.get("resolucion")
    if resolucion is not None and not (
            isinstance(resolucion, int) and not isinstance(resolucion, bool)
            and 1 <= resolucion <= 100_000):
        raise ErrorMiauki("entrada_invalida")

    url_directa = snapshot.get("url_directa")
    if url_directa not in (None, ""):
        if not (isinstance(url_directa, str)
                and len(url_directa) <= _LARGO_URL
                and url_directa.lower().startswith(("http://", "https://"))):
            raise ErrorMiauki("entrada_invalida")

    # Playlist (Paso 3): cada entrada se valida INDEPENDIENTE con las mismas
    # reglas. Si hay una más de MAX_PLAYLIST, se rechaza entera.
    entradas = None
    if "entradas" in snapshot:
        brutas = snapshot["entradas"]
        if not isinstance(brutas, list) or not brutas:
            raise ErrorMiauki("entrada_invalida")
        if len(brutas) > MAX_PLAYLIST:
            raise ErrorMiauki("playlist_muy_larga")
        entradas = []
        for e in brutas:
            if not isinstance(e, dict):
                raise ErrorMiauki("entrada_invalida")
            entradas.append(snapshot_limpio(e))

    # El sitio sale del link (no de lo que diga la interfaz): antes las
    # descargas nuevas quedaban como "otro" (Fase 7, 0.2).
    limpio = {
        "url_canonica": url,
        "tipo": tipo,
        "selector": selector if tipo in ("video", "musica") else None,
        "contenedor": contenedor,
        "kbps": kbps,
        "titulo": titulo or "",
        "miniatura": mini or "",
        "con_subs": con_subs,
        "resolucion": resolucion,
        "sitio": sites.sitio_de_url(url),
        "url_directa": url_directa or None,
    }
    if entradas is not None:
        limpio["entradas"] = entradas
    return limpio


# ---------- rutas ----------

def dentro_de(ruta, carpeta) -> bool:
    """True si `ruta` (normalizada, sin symlinks) está dentro de `carpeta`."""
    try:
        r = os.path.realpath(os.path.abspath(ruta))
        c = os.path.realpath(os.path.abspath(carpeta))
        return os.path.commonpath([r, c]) == c
    except (ValueError, OSError):
        return False                   # distinta unidad, etc.


_RESERVADOS = {
    "con", "prn", "aux", "nul",
    *(f"com{i}" for i in range(1, 10)),
    *(f"lpt{i}" for i in range(1, 10)),
}
_ILEGALES = set('\\/:*?"<>|')

# Tope de la ruta completa (carpeta + nombre + extensión). Windows falla
# pasado 260 caracteres; dejamos margen para " (NN)" y la peor extensión
# (".webm", ".<idioma>.srt").
MAX_RUTA = 240
_MARGEN = 12


def sanear_nombre(texto) -> str:
    """Convierte un título en un nombre de archivo válido para Windows.

    Quita los caracteres ilegales y de control (no los reemplaza por otros:
    eso evita que el archivo quede con basura de ancho completo), saca el
    punto/espacio final (Windows lo recorta solo y rompe la referencia) y,
    si el nombre cae en un reservado (`CON`, `NUL`, `COM1`), lo despega con
    un guion bajo. Devuelve "" si no queda nada usable.
    """
    bruto = "".join(c for c in (texto or "")
                    if c not in _ILEGALES and ord(c) >= 32)
    nombre = bruto.strip().rstrip(". ")
    if not nombre:
        return ""
    partes = nombre.split(".", 1)
    if partes[0].strip().lower() in _RESERVADOS:
        partes[0] += "_"
        nombre = ".".join(partes)
    return nombre


# Temporales de yt-dlp: NO cuentan como "ocupado" al buscar nombre libre (un
# .part es el mismo archivo a medio bajar, para reanudar; los .fNNN son
# fragmentos mientras se mergean). Sin esto, al reanudar se elegía "X (2)"
# y la descarga reiniciaba de 0 dejando el .part viejo ocupando espacio.
_TEMPORALES_SUFIJOS = (".part", ".ytdl", ".temp")
_FRAGMENTO = re.compile(r"\.f\d+\.")


def _es_temporal(nombre: str) -> bool:
    n = nombre.lower()
    if n.endswith(_TEMPORALES_SUFIJOS):
        return True
    return bool(_FRAGMENTO.search(n))


def nombre_base_libre(carpeta, titulo, tope_ruta: int = MAX_RUTA) -> str:
    """Nombre base (sin extensión) que no pisa ningún archivo de la carpeta.

    Prueba "titulo", "titulo (2)", "titulo (3)"… y considera TODAS las
    extensiones: cualquier archivo que empiece con "base." (video, música,
    imagen o un subtítulo ".es.srt") cuenta como ocupado. Los temporales de
    yt-dlp (.part, .ytdl, .temp y fragmentos .fNNN) NO cuentan: son el mismo
    archivo a medio bajar y se reutilizan al reanudar. Recorta el nombre
    para que la ruta completa no pase de `tope_ruta`.
    """
    base = sanear_nombre(titulo) or "descarga"
    try:
        existentes = {n.lower() for n in os.listdir(carpeta)}
    except OSError:
        existentes = set()
    limite = tope_ruta - len(os.path.abspath(carpeta)) - 1 - _MARGEN
    limite = max(1, limite)
    for i in range(1, 10000):
        sufijo = "" if i == 1 else " (%d)" % i
        candidato = base[:max(1, limite - len(sufijo))] + sufijo
        clave = candidato.lower()
        if not any((n == clave or n.startswith(clave + "."))
                   and not _es_temporal(n)
                   for n in existentes):
            return candidato
    return base[:limite]               # ponytail: 99999 duplicados no pasa


def carpeta_peligrosa(ruta) -> bool:
    """True si la carpeta es la raíz de una unidad o una carpeta de sistema."""
    if not isinstance(ruta, str) or not ruta.strip():
        return True
    r = os.path.realpath(ruta)
    if os.path.normpath(r) == os.path.normpath(os.path.splitdrive(r)[0] + os.sep):
        return True                    # raíz de la unidad (ej. "C:\")
    partes = [p.lower() for p in os.path.normpath(r).replace("/", "\\").split("\\")]
    sistema = {"windows", "program files", "program files (x86)", "programdata",
               "system32", "syswow64"}
    return any(parte in sistema for parte in partes)


def puede_escribir(ruta) -> bool:
    """Intenta crear y borrar un archivo temporal en la carpeta."""
    try:
        prueba = os.path.join(ruta, ".miauki_prueba_escritura.tmp")
        with open(prueba, "w", encoding="utf-8"):
            pass
        os.remove(prueba)
        return True
    except OSError:
        return False

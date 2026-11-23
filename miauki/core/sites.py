# -*- coding: utf-8 -*-
"""Detección de sitios y normalización de links (spec §3).

Reglas: solo http/https; YouTube v=+list= manda UN video y la lista sola
da error amable; portadas de los sitios conocidos dicen "no es un video";
Facebook pierde parámetros de tracking y conserva los IDs (fbid, story_fbid).
Lo demás pasa como "otro" y lo decide yt-dlp en el análisis.
"""
import re
from urllib.parse import parse_qs, parse_qsl, urlencode, urlsplit, urlunsplit

from miauki.core.errors import ErrorMiauki

TRACKING_FACEBOOK = {"fbclid", "fbc", "__cft__", "__tn__", "__tn", "mibextid",
                     "ref", "ref_src"}
_IDIOMAS = {"es", "en", "fr", "de", "it", "pt", "ja", "ko", "zh", "ar", "hi",
            "ru", "tr", "pl", "nl", "sv", "da", "no", "fi", "cs", "hu", "ro",
            "el", "he", "th", "vi", "id", "ms", "tl"}
_RAICES = {"youtube", "tiktok", "instagram", "facebook", "x"}
_DOMINIO = re.compile(r"^[a-z0-9\-]+(?:\.[a-z0-9\-]+)*\.[a-z]{2,}(?:[/?#]\S*)?$",
                      re.I)

# Sitios con vía de imagen/JSON propia (Paso 4-5): si yt-dlp no los cubre,
# la app los atiende por otro camino en vez de "otro".
SITIOS_IMAGEN = {"pinterest", "reddit", "snapchat"}


def termina_en(host: str, dominio: str) -> bool:
    """Host igual al dominio o subdominio (helper único: lo usa images.py)."""
    return host == dominio or host.endswith("." + dominio)


def _es_raiz(camino: str) -> bool:
    """Portada del sitio o solo el código de idioma (ej. /es/).

    Un story (`/stories/usuario/123/`) tiene más de un segmento, así que no es
    raíz y pasa de largo: yt-dlp lo resuelve con InstagramStoryIE.

    Un solo segmento que NO sea idioma es un perfil público
    (`/maki/`, plan `plan.md` paso 2.1): se deja pasar y el analizador lo
    trata como lista de sus posts. La lista de idiomas es explícita para que
    un usuario de dos letras (`/mk/`) no quede bloqueado como portada.
    """
    partes = [p for p in camino.split("/") if p]
    if not partes:
        return True
    return len(partes) == 1 and partes[0].lower() in _IDIOMAS


def _sitio_de(host: str) -> str:
    if termina_en(host, "youtube.com") or termina_en(host, "youtu.be"):
        return "youtube"
    if termina_en(host, "tiktok.com"):
        return "tiktok"
    if termina_en(host, "instagram.com"):
        return "instagram"
    if termina_en(host, "facebook.com") or termina_en(host, "fb.watch"):
        return "facebook"
    if termina_en(host, "x.com") or termina_en(host, "twitter.com"):
        return "x"
    if termina_en(host, "pinterest.com") or termina_en(host, "pinterest."):
        return "pinterest"
    if termina_en(host, "reddit.com"):
        return "reddit"
    if termina_en(host, "snapchat.com"):
        return "snapchat"
    if host == "pbs.twimg.com":  # imagen suelta de X (Fase 9, B1)
        return "x"
    return "otro"


def sitio_de_url(url: str) -> str:
    """Sitio de un link ya validado ("otro" si el host no es conocido).

    Se usa en el borde (validacion) para no creerle el sitio a la interfaz.
    """
    try:
        host = (urlsplit(url or "").hostname or "").lower()
    except ValueError:
        return "otro"
    return _sitio_de(host) if host else "otro"


def es_perfil_instagram(url: str) -> bool:
    """`instagram.com/<usuario>`: la página del perfil, no un post ni un story.

    Con un solo segmento que no sea idioma ya se sabe que es un perfil
    (plan `plan.md`, paso 2.2): el analizador lo trata como lista de posts.
    """
    try:
        p = urlsplit(url or "")
    except ValueError:
        return False
    if _sitio_de((p.hostname or "").lower()) != "instagram":
        return False
    partes = [x for x in p.path.split("/") if x]
    return len(partes) == 1 and partes[0].lower() not in _IDIOMAS


def normalizar_url(url: str) -> str | None:
    """Link con esquema completo, o None si no es una dirección reconocible.

    Un `http://`/`https://` pasa tal cual (se respeta http). A `www.` y a un
    dominio con ruta (`minombre.io/video`) se les agrega `https://`. Un
    dominio SIN ruta se rechaza: sin ruta no se distingue de una frase
    (plan `plan.md`, paso 3.2).
    """
    texto = (url or "").strip()
    bajo = texto.lower()
    if bajo.startswith(("http://", "https://")):
        return texto
    if bajo.startswith("www.") and _DOMINIO.match(texto[4:]):
        return "https://" + texto
    if "/" in texto and _DOMINIO.match(texto):
        return "https://" + texto
    return None


def detectar(url: str) -> tuple[str, str]:
    """(sitio, url_canonica). Lanza ErrorMiauki si el link no sirve."""
    normal = normalizar_url(url)
    if normal is None:
        raise ErrorMiauki("link_invalido")
    try:
        p = urlsplit(normal)
    except ValueError:
        raise ErrorMiauki("link_invalido") from None
    if p.scheme.lower() not in ("http", "https") or not p.netloc:
        raise ErrorMiauki("link_invalido")
    host = (p.hostname or "").lower()
    if not host:
        raise ErrorMiauki("link_invalido")
    sitio = _sitio_de(host)
    camino = p.path

    if sitio in _RAICES and _es_raiz(camino):
        raise ErrorMiauki("no_es_video")

    if sitio == "youtube":
        return _youtube(p, host)
    if sitio == "facebook":
        return "facebook", _limpiar_facebook(p, host)

    limpio = urlunsplit((p.scheme.lower(), p.netloc.lower(), camino, p.query, ""))
    return sitio, limpio


def _youtube(p, host: str) -> tuple[str, str]:
    partes = [x for x in p.path.split("/") if x]
    if host == "youtu.be":
        if not partes:
            raise ErrorMiauki("no_es_video")
        return "youtube", f"https://www.youtube.com/watch?v={partes[0]}"
    if partes and (partes[0].startswith("@") or partes[0] in {"channel", "user", "c"}):
        raise ErrorMiauki("no_es_video")
    consulta = parse_qs(p.query)
    video = (consulta.get("v") or [""])[0].strip()
    if video:
        # v= manda: se ignora list= (un solo video, spec §3)
        return "youtube", f"https://www.youtube.com/watch?v={video}"
    if "list" in consulta:
        # Playlist (Paso 1): devolver URL canónica, no error.
        # Se conserva el host original (www/music) para que yt-dlp los trate bien.
        lista = (consulta.get("list") or [""])[0].strip()
        if lista:
            return "youtube", urlunsplit(("https", host, "playlist", "list=" + lista, ""))
    if partes and partes[0] == "playlist":
        # Link de lista sin código (caso real 20/11/2026: youtube.com/playlist
        # solo): yt-dlp no devolvía nada y salía "el motor no devolvió datos".
        raise ErrorMiauki("playlist_sin_id")
    if partes and partes[0] == "watch":
        raise ErrorMiauki("link_invalido")
    return "youtube", urlunsplit(("https", "www.youtube.com", p.path, p.query, ""))


def _limpiar_facebook(p, host: str) -> str:
    q = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True)
         if k not in TRACKING_FACEBOOK]
    return urlunsplit(("https", host, p.path, urlencode(q), ""))

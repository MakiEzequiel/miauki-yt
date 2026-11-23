# -*- coding: utf-8 -*-
"""Descarga de imágenes segura + vías de X/Facebook (spec §5, A5 y A6).

Seguridad (A6): solo https, dominios de una lista blanca, timeout por
pedido, content-type image/* y tope de tamaño. Las redirecciones NO se
siguen a ciegas: cada salto vuelve a pasar las mismas comprobaciones y la
IP resuelta se verifica (rechaza privadas/locales/link-local).

Vías de imágenes (A5): funciones con LA MISMA interfaz
`f(id_o_url, ajustes) -> {"imagenes", "titulo", "autor"}` que al fallar
lanzan `_Falla(codigo, mensaje_amable, detalle)`. En X se prueban en el
orden del tupla VIAS_X (ahí se reconfigura), se loguea la vía usada y
cada fallida con su por qué. Para AGREGAR o REEMPLAZAR una vía: crear la
función con esa interfaz, registrarla en _VIAS_X y sumar su nombre a
VIAS_X. Facebook no tiene código propio: usa el extractor FacebookIE de
yt-dlp (INVENTARIO §4); si no devuelve fotos, se reporta la causa real.
"""
import base64
import ipaddress
import json
import math
import re
import socket
import threading
import urllib.error
import urllib.parse
import urllib.request

from miauki.core import cookies, errors, motor
from miauki.core.errors import ErrorMiauki
from miauki.core.logger import obtener_logger
from miauki.core.sites import termina_en

LIMITE_BYTES = 5 * 1024 * 1024
LIMITE_SALTOS = 5
TIEMPO = 10
TIEMPO_API = 15
REDIRECCIONES = {301, 302, 303, 307, 308}

# Lista blanca de dominios de imágenes (por sufijo de host): YouTube (B4),
# X y Facebook/Instagram (B5); B8 puede ampliarla con lo visto en las corridas.
ANFITRIONES = {"i.ytimg.com", "img.youtube.com", "pbs.twimg.com",
               "video.twimg.com", "abs.twimg.com", "fbcdn.net",
               "cdninstagram.com", "i.pinimg.com", "i.redd.it",
               "preview.redd.it", "v.redd.it", "tiktokcdn.com",
               "bolt-gcdn.sc-cdn.net", "sc-cdn.net",
               # Auditoría 23/11: CDN de imágenes de Google (gstatic) y de
               # la prensa (arcpublishing), que llegan por share.google/imgres.
               "gstatic.com", "arcpublishing.com"}

EXTENSIONES_IMAGEN = {"jpg", "jpeg", "png", "webp", "gif", "avif", "heic", "jfif"}

# --- Vías de imágenes (B5) ---------------------------------------------------
# Hosts que reconocen un link de X (INVENTARIO §4), además de x.com/twitter.com.
HOSTS_X = ("x.com", "twitter.com", "vxtwitter.com", "fixvx.com",
           "fxtwitter.com", "twittpr.com")
HOSTS_FACEBOOK = ("facebook.com",)
# Google Imágenes: share.google (link corto) y google.com/imgres?imgurl=...
# (auditoría 23/11: antes caían en "otro" y yt-dlp los rechazaba).
HOSTS_GOOGLE_IMAGEN = ("share.google", "google.com")
# Imagen directa de X (la URL del CDN, sin post): se analiza como imagen sola.
HOST_IMAGEN_X = "pbs.twimg.com"

GRAPHQL_URL = "https://x.com/i/api/graphql/2ICDjqPd81tulZcYrtpTuQ/TweetResultByRestId"
TOKEN_URL = "https://api.x.com/1.1/guest/activate.json"
SYNDICATION_URL = "https://cdn.syndication.twimg.com/tweet-result"
FX_URL = "https://api.fxtwitter.com/status/"
BEARER = ("AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs"
          "%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA")
UA_X = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36")
UA_SINDICACION = "Googlebot"
# El orden de las vías de X se reconfigura acá (A5).
VIAS_X = ("graphql", "syndication", "fxtwitter")

_UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Miauki/1.0"}

_token_invitado: str | None = None
_token_traba = threading.Lock()


class _Falla(Exception):
    """Falla de una vía: código + mensaje amable (UI) + detalle (log)."""

    def __init__(self, codigo: str, mensaje: str, detalle: str | None = None):
        self.codigo = codigo
        self.mensaje = mensaje
        self.detalle = detalle or mensaje
        super().__init__(mensaje)


class _SinSeguir(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # no seguir: lo decide _leer con sus propias reglas


_OPENER = urllib.request.build_opener(_SinSeguir)


def _ip_ok(direccion: str) -> bool:
    """False para privadas, locales, link-local, loopback, multicast..."""
    try:
        ip = ipaddress.ip_address(direccion.split("%")[0])
    except ValueError:
        return False
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
        ip = ip.ipv4_mapped
    return not (ip.is_private or ip.is_loopback or ip.is_link_local
                or ip.is_multicast or ip.is_reserved or ip.is_unspecified)


def _ips_ok(host: str) -> bool:
    """Resuelve el host y exige que TODAS las IPs sean públicas."""
    try:
        respuestas = socket.getaddrinfo(host, None)
    except OSError:
        return False
    if not respuestas:
        return False
    return all(_ip_ok(r[4][0]) for r in respuestas)


def _permitido(url: str) -> bool:
    p = urllib.parse.urlsplit(url)
    if (p.scheme or "").lower() != "https" or not p.hostname:
        return False
    host = p.hostname.lower()
    return any(termina_en(host, d) for d in ANFITRIONES)


def _leer(url: str, headers: dict | None = None) -> tuple[bytes, str]:
    """(bytes, mime) o ValueError si algo no está a la altura.

    `headers` extra (p.ej. cookies para CDN de Instagram/Facebook).
    """
    actual = url
    cabeceras = dict(_UA)
    if headers:
        cabeceras.update(headers)
    for _ in range(LIMITE_SALTOS + 1):
        if not _permitido(actual):
            raise ValueError("dominio fuera de la lista")
        host = urllib.parse.urlsplit(actual).hostname.lower()
        if not _ips_ok(host):
            raise ValueError("ip no pública")
        respuesta = None
        try:
            respuesta = _OPENER.open(
                urllib.request.Request(actual, headers=cabeceras), timeout=TIEMPO)
        except urllib.error.HTTPError as e:
            if e.code in REDIRECCIONES:
                destino = e.headers.get("Location") or ""
                e.close()
                if not destino:
                    raise ValueError("redirección sin destino") from None
                actual = urllib.parse.urljoin(actual, destino)
                continue
            raise ValueError("respuesta %s" % e.code) from None
        try:
            mime = (respuesta.headers.get("Content-Type") or "").split(";")[0].strip().lower()
            if not mime.startswith("image/"):
                raise ValueError("no es imagen")
            datos = respuesta.read(LIMITE_BYTES + 1)
        finally:
            respuesta.close()
        if len(datos) > LIMITE_BYTES:
            raise ValueError("imagen demasiado grande")
        return datos, mime
    raise ValueError("demasiadas redirecciones")


def data_uri_de(url: str, headers: dict | None = None) -> str | None:
    """data:image/...;base64,... o None si no es segura/cumple (no revienta)."""
    if not url:
        return None
    try:
        datos, mime = _leer(url, headers=headers)
    except Exception as exc:
        obtener_logger().info("Miniatura descartada (%s): %s",
                              exc, errors.sin_query(url))
        return None
    return "data:%s;base64,%s" % (mime, base64.b64encode(datos).decode("ascii"))


def peso_de_video(url: str):
    """Tamaño exacto del mp4 (Content-Length) sin descargarlo, o None.

    El `bitrate` que publica X no coincide con el peso real del archivo, así
    que la interfaz muestra este dato y deja la estimación como respaldo.
    """
    if not url or not _permitido(url):
        return None
    host = urllib.parse.urlsplit(url).hostname.lower()
    if not _ips_ok(host):
        return None
    try:
        respuesta = _OPENER.open(
            urllib.request.Request(url, method="HEAD", headers=_UA), timeout=TIEMPO)
    except Exception:
        return None
    try:
        largo = respuesta.headers.get("Content-Length")
    finally:
        respuesta.close()
    try:
        return int(largo) if largo else None
    except (TypeError, ValueError):
        return None


def es_extension_imagen(url: str) -> bool:
    camino = (url or "").split("?")[0].lower()
    return camino.rsplit(".", 1)[-1] in EXTENSIONES_IMAGEN if "." in camino else False


# --- Vías de X/Facebook (B5, A5) --------------------------------------------

def _es_host_x(host: str) -> bool:
    return any(termina_en(host, d) for d in HOSTS_X)


def es_imagen_google(url: str) -> bool:
    """¿Es un link de Google Imágenes (share.google o imgres con imgurl)?"""
    p = urllib.parse.urlsplit(url or "")
    if (p.scheme or "").lower() not in ("http", "https") or not p.hostname:
        return False
    host = p.hostname.lower()
    if host == "share.google":
        return True
    return termina_en(host, "google.com") and bool(
        urllib.parse.parse_qs(p.query).get("imgurl"))


def imgurl_de_google(url: str) -> str | None:
    """La URL de la imagen dentro de un imgres de Google, o None."""
    p = urllib.parse.urlsplit(url or "")
    return (urllib.parse.parse_qs(p.query).get("imgurl") or [None])[0]


def es_imagen_directa(url: str) -> bool:
    """Hosts que sirven imágenes solas aunque la URL no termine en .jpg.

    Auditoría 23/11: encrypted-tbn0.gstatic.com/...?q=tbn=... es una imagen
    de Google sin extensión en la ruta; yt-dlp no la entiende.
    """
    p = urllib.parse.urlsplit(url or "")
    if (p.scheme or "").lower() not in ("http", "https") or not p.hostname:
        return False
    return termina_en(p.hostname.lower(), "gstatic.com")


def _destino_final(url: str) -> str | None:
    """URL final tras las redirecciones de un link corto (share.google)."""
    try:
        req = urllib.request.Request(url, headers=_UA)
        with urllib.request.urlopen(req, timeout=TIEMPO) as r:
            return r.geturl()
    except Exception:
        return None


def es_imagen_x_directa(url: str) -> bool:
    """¿Es la URL de una foto de X (pbs.twimg.com/media/...), sin post?

    Maki pegó esos links en la Fase 9: antes caían en "otro" y yt-dlp no los
    entendía. Se reconocen como imagen sola.
    """
    p = urllib.parse.urlsplit(url or "")
    return ((p.scheme or "").lower() in ("http", "https")
            and (p.hostname or "").lower() == HOST_IMAGEN_X
            and p.path.startswith("/media/"))


def id_tweet(url: str) -> str:
    """Id del tweet en un link de X (cualquier host de la lista, con o sin /photo/N)."""
    p = urllib.parse.urlsplit(url)
    if (p.scheme or "").lower() not in ("http", "https") or not p.hostname:
        raise ErrorMiauki("link_invalido")
    if not _es_host_x(p.hostname.lower()):
        raise ErrorMiauki("link_invalido", "Ese link no parece de X.")
    m = re.search(r"/(?:status|statuses|mediaviewer)/(\d{5,25})", p.path)
    if not m:
        m = re.search(r"(?:^|[?&])(?:post_id|status_id)=(\d{5,25})", p.query or "")
    if not m:
        m = re.search(r"(?<!\d)(\d{15,25})(?!\d)", p.path)
    if not m:
        raise ErrorMiauki("link_invalido", "No encontré el id del tweet en ese link.")
    return m.group(1)


def _pedir(url: str, headers: dict | None = None, data: bytes | None = None,
           timeout: int = TIEMPO_API) -> tuple[int, bytes]:
    """(status, cuerpo) sin seguir redirecciones; IP pública verificada (A6)."""
    host = urllib.parse.urlsplit(url).hostname or ""
    if not host or not _ips_ok(host):
        raise _Falla("sin_internet", "No pude conectar con el sitio. Revisá tu red.",
                     "ip no pública: " + host)
    req = urllib.request.Request(url, data=data, headers=headers or _UA)
    try:
        with _OPENER.open(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        try:
            cuerpo = e.read()
        except Exception:
            cuerpo = b""
        codigo = e.code
        e.close()
        return codigo, cuerpo
    except Exception as exc:
        raise _Falla("sin_internet",
                     "No pude conectar con el sitio. Revisá tu red y probá de nuevo.",
                     str(exc)) from None


def _json(cuerpo: bytes):
    try:
        return json.loads(cuerpo.decode("utf-8", "replace") or "null")
    except ValueError:
        return None


def _token_invitado_get(recargar: bool = False) -> str:
    global _token_invitado
    with _token_traba:
        if _token_invitado and not recargar:
            return _token_invitado
        status, cuerpo = _pedir(TOKEN_URL, {
            "User-Agent": UA_X, "Authorization": "Bearer " + BEARER}, data=b"")
        if status != 200:
            raise _Falla("error_desconocido",
                         "X no respondió bien (HTTP %d)." % status,
                         "guest token HTTP %d" % status)
        token = str((_json(cuerpo) or {}).get("guest_token") or "")
        if not token:
            raise _Falla("error_desconocido", "X no entregó el token de invitado.",
                         "guest token vacío")
        _token_invitado = token
        return token


def _cookies_x(ajustes: dict) -> tuple[str | None, str | None, str | None]:
    """(cookie, csrf, error) de x.com/twitter.com (archivo o navegador elegido).

    La lectura vive en `core.cookies` para que sea la misma en todas las vías.
    """
    return cookies.para_x(ajustes)


def _foto_url(base: str) -> str:
    """Pide la foto al tamaño más grande disponible (name=4096x4096)."""
    if "name=" in base:
        return re.sub(r"name=[^&]*", "name=4096x4096", base)
    return base + ("&" if "?" in base else "?") + "name=4096x4096"


def _fotos(media) -> list[str]:
    """URLs de las fotos de una lista de medios (formato graphql/syndication)."""
    salida = []
    for item in media or []:
        if not isinstance(item, dict) or str(item.get("type") or "").lower() != "photo":
            continue
        base = item.get("media_url_https") or item.get("media_url")
        if base:
            salida.append(_foto_url(base))
    return salida


_ALTO_EN_URL = re.compile(r"/vid/[^/]+/(\d+)x(\d+)/")


def _alto_de(url: str):
    """Altura en píxeles que viene en la ruta del mp4 (…/avc1/1280x720/…)."""
    m = _ALTO_EN_URL.search(url or "")
    return int(m.group(2)) if m else None


def _video_datos(media) -> dict | None:
    """Video de un tweet: mp4 por calidad, duración y miniatura.

    Las tres vías de X traen la misma información con nombres distintos
    (video_info en graphql/syndication, formats en fxtwitter). Sin esto un
    tweet con video se descartaba como «sin fotos» y la interfaz no tenía
    calidades, peso, formato ni miniatura que mostrar.
    """
    variantes, duracion, miniatura = {}, None, ""
    for item in media or []:
        if not isinstance(item, dict):
            continue
        if str(item.get("type") or "").lower() not in ("video", "animated_gif", "gif"):
            continue
        info = item.get("video_info") or {}
        if duracion is None:
            ms = info.get("duration_millis") or item.get("duration_millis")
            if ms:
                duracion = float(ms) / 1000
            elif item.get("duration"):
                try:
                    duracion = float(item["duration"])
                except (TypeError, ValueError):
                    duracion = None
        if not miniatura:
            miniatura = (item.get("thumbnail_url")
                         or item.get("media_url_https") or "")
        lista = (info.get("variants") or item.get("formats")
                 or item.get("variants") or [])
        if not lista and str(item.get("format") or "").endswith("mp4"):
            lista = [{"url": item.get("url")}]
        for variante in lista:
            if not isinstance(variante, dict):
                continue
            url = variante.get("url") or ""
            tipo = str(variante.get("content_type") or "").lower()
            if not url or "mpegurl" in tipo or ".m3u8" in url:
                continue
            try:
                bitrate = int(variante.get("bitrate") or 0)
            except (TypeError, ValueError):
                bitrate = 0
            alto = _alto_de(url)
            if not alto and isinstance(item.get("height"), int):
                alto = item["height"]
            variantes.setdefault(url, {"url": url, "bitrate": bitrate,
                                       "alto": alto})
    if not variantes:
        return None
    ordenadas = sorted(variantes.values(),
                       key=lambda v: (v["bitrate"], v["alto"] or 0), reverse=True)
    return {"url": ordenadas[0]["url"], "variantes": ordenadas,
            "duracion": duracion, "miniatura": miniatura}


def _titulo(texto, autor: str) -> str:
    t = re.sub(r"\s+", " ", str(texto or "")).strip()
    t = re.sub(r"\s+https?://\S+", "", t).strip()
    if not t:
        t = "tweet"
    if autor:
        t = "%s - %s" % (autor, t)
    return t[:120]


def _via_graphql(tweet_id: str, ajustes: dict) -> dict:
    variables = json.dumps({"tweetId": tweet_id, "withCommunity": True,
                            "includePromotedContent": True,
                            "withSafetyModeUserFields": True, "withVoice": True},
                           separators=(",", ":"))
    url = GRAPHQL_URL + "?" + urllib.parse.urlencode({
        "variables": variables,
        "features": ('{"rweb_video_screen_enabled":false,"payments_enabled":false,'
                     '"profile_label_improvements_pcf_label_in_post_enabled":true,'
                     '"verified_phone_label_enabled":false,'
                     '"responsive_web_graphql_timeline_navigation_enabled":true,'
                     '"responsive_web_graphql_skip_user_profile_image_extensions_enabled":false,'
                     '"creator_subscriptions_tweet_preview_api_enabled":true,'
                     '"communities_web_enable_tweet_community_results_fetch":true,'
                     '"c9s_tweet_anatomy_moderator_badge_enabled":true,'
                     '"responsive_web_edit_tweet_api_enabled":true,'
                     '"graphql_is_translatable_rweb_tweet_is_translatable_enabled":true,'
                     '"view_counts_everywhere_api_enabled":true,'
                     '"longform_notetweets_consumption_enabled":true,'
                     '"tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled":true,'
                     '"longform_notetweets_rich_text_read_enabled":true,'
                     '"longform_notetweets_inline_media_enabled":true,'
                     '"responsive_web_enhance_cards_enabled":false}'),
        "fieldToggles": ('{"withArticleRichContentState":true,"withArticlePlainText":false,'
                         '"withGrokAnalyze":false,"withDisallowedReplyControls":false}'),
    })
    cookie, csrf, cookie_error = _cookies_x(ajustes)
    ultimo_status = 0
    for recargar in (False, True):
        token = _token_invitado_get(recargar)
        encabezados = {
            "User-Agent": UA_X,
            "Authorization": "Bearer " + BEARER,
            "x-twitter-client-language": "en",
            "x-twitter-active-user": "yes",
            "Accept-Language": "en",
            "x-guest-token": token,
        }
        if cookie:
            encabezados["Cookie"] = cookie
            encabezados["X-Twitter-Auth-Type"] = "OAuth2Session"
            if csrf:
                encabezados["x-csrf-token"] = csrf
        else:
            encabezados["Cookie"] = "guest_id=v1%3A" + urllib.parse.quote(token)
        ultimo_status, cuerpo = _pedir(url, encabezados)
        payload = _json(cuerpo) if ultimo_status == 200 else None
        if isinstance(payload, dict) and payload.get("data"):
            break
    else:
        raise _Falla("error_desconocido",
                     "X no respondió bien (HTTP %d)." % ultimo_status,
                     "graphql HTTP %d" % ultimo_status)
    try:
        return _extraer_graphql(payload, tweet_id, cookie_error)
    except _Falla as exc:
        if cookie_error and exc.codigo in ("requiere_sesion", "restriccion_edad"):
            raise _Falla(exc.codigo, exc.mensaje + " · " + cookie_error) from None
        raise


def _extraer_graphql(payload: dict, tweet_id: str, cookie_error) -> dict:
    result = ((payload.get("data") or {}).get("tweetResult") or {}).get("result")
    if not isinstance(result, dict):
        raise _Falla("error_desconocido", "No pude leer ese tweet.", "sin resultado")
    tipo = result.get("__typename")
    if tipo in ("TweetUnavailable", "TweetTombstone"):
        razon = result.get("reason") or ""
        if razon == "Protected":
            raise _Falla("requiere_sesion",
                         "El tweet es de una cuenta protegida: activá las cookies "
                         "del navegador en Ajustes.", "reason=Protected")
        if razon == "NsfwLoggedOut":
            raise _Falla("restriccion_edad",
                         "El tweet es para mayores: activá las cookies del "
                         "navegador en Ajustes.", "reason=NsfwLoggedOut")
        if tipo == "TweetTombstone" and not razon:
            # X devuelve una lápida vacía cuando el post necesita sesión
            # (contenido sensible). Sin sesión no hay forma de distinguirlo
            # de un borrado, así que se pide la sesión sin afirmar cuál es.
            raise _Falla("requiere_sesion",
                         "Ese post no se puede ver sin iniciar sesión (puede ser "
                         "para mayores o de una cuenta protegida). Activá «Usar el "
                         "inicio de sesión de tu navegador» en Ajustes.",
                         "tombstone vacío: pide sesión")
        raise _Falla("video_eliminado", "Ese tweet ya no existe o fue borrado.",
                     "__typename=" + str(tipo))
    if tipo not in ("Tweet", "TweetWithVisibilityResults"):
        raise _Falla("error_desconocido", "No pude leer ese tweet.",
                     "__typename=" + str(tipo))
    base = result.get("legacy") or {}
    if tipo == "TweetWithVisibilityResults":
        base = ((result.get("tweet") or {}).get("legacy")) or base
    media = (base.get("extended_entities") or {}).get("media")
    if not media:
        retuiteado = ((base.get("retweeted_status_result") or {}).get("result")
                      or {}).get("legacy") or {}
        media = (retuiteado.get("extended_entities") or {}).get("media")
    fotos = _fotos(media)
    video = _video_datos(media)
    if not fotos and not video:
        raise _Falla("no_es_video", "Ese tweet no tiene fotos ni videos.",
                     "sin medios en graphql")
    autor = _autor_graphql(result)
    titulo = _titulo(base.get("full_text"), autor)
    if fotos:
        return {"imagenes": fotos, "titulo": titulo, "autor": autor}
    return {"imagenes": [video["url"]], "video": video, "titulo": titulo,
            "autor": autor, "es_video": True}


def _autor_graphql(result: dict) -> str:
    for camino in (("core", "user_results", "result", "legacy"),
                   ("user", "result", "legacy"), ("user", "legacy")):
        nodo = result
        for clave in camino:
            nodo = nodo.get(clave) if isinstance(nodo, dict) else None
        if isinstance(nodo, dict) and (nodo.get("screen_name") or nodo.get("name")):
            return str(nodo.get("name") or nodo.get("screen_name"))
    return ""


def _via_syndication(tweet_id: str, ajustes: dict) -> dict:
    motor.ytdlp()  # asegura que el paquete activo esté importado
    from yt_dlp.jsinterp import js_number_to_string
    token = js_number_to_string((int(tweet_id) / 1e15) * math.pi, 36)
    token = token.translate(str.maketrans("", "", "0."))
    url = SYNDICATION_URL + "?" + urllib.parse.urlencode(
        {"id": tweet_id, "token": token})
    status, cuerpo = _pedir(url, {"User-Agent": UA_SINDICACION})
    if status >= 400:
        raise _Falla("video_eliminado" if status == 404 else "error_desconocido",
                     "El tweet no está disponible (HTTP %d)." % status,
                     "syndication HTTP %d" % status)
    payload = _json(cuerpo)
    if not isinstance(payload, dict):
        raise _Falla("error_desconocido", "X devolvió algo que no pude leer.",
                     "syndication sin json")
    media = payload.get("mediaDetails")
    if media is None:
        media = payload.get("media")
    fotos = _fotos(media)
    video = _video_datos(media)
    if not fotos and not video:
        raise _Falla("no_es_video", "Ese tweet no tiene fotos ni videos.",
                     "sin mediaDetails")
    user = payload.get("user") or {}
    autor = str(user.get("name") or user.get("screen_name") or "")
    titulo = _titulo(payload.get("text"), autor)
    if fotos:
        return {"imagenes": fotos, "titulo": titulo, "autor": autor}
    return {"imagenes": [video["url"]], "video": video, "titulo": titulo,
            "autor": autor, "es_video": True}


def _via_fxtwitter(tweet_id: str, ajustes: dict) -> dict:
    status, cuerpo = _pedir(FX_URL + tweet_id, {"User-Agent": UA_X})
    if status in (401, 403):
        raise _Falla("requiere_sesion",
                     "El tweet es de una cuenta protegida: activá las cookies "
                     "del navegador en Ajustes.", "fx HTTP %d" % status)
    if status >= 400:
        raise _Falla("video_eliminado" if status == 404 else "error_desconocido",
                     "FxTwitter no pudo leer el tweet (HTTP %d)." % status,
                     "fx HTTP %d" % status)
    payload = _json(cuerpo)
    if not isinstance(payload, dict) or payload.get("code") not in (None, 200):
        raise _Falla("error_desconocido", "FxTwitter no pudo leer ese tweet.",
                     "fx sin json")
    tweet = payload.get("tweet") or {}
    items = (tweet.get("media") or {}).get("all") or []
    fotos = [_foto_url(i["url"]) for i in items if isinstance(i, dict)
             and str(i.get("type") or "").lower() == "photo" and i.get("url")]
    video = _video_datos(items)
    if not fotos and not video:
        raise _Falla("no_es_video", "Ese tweet no tiene fotos ni videos.",
                     "sin medios en fx")
    autor = str((tweet.get("author") or {}).get("screen_name") or "")
    titulo = _titulo(tweet.get("text"), autor)
    if fotos:
        return {"imagenes": fotos, "titulo": titulo, "autor": autor}
    return {"imagenes": [video["url"]], "video": video, "titulo": titulo,
            "autor": autor, "es_video": True}


_VIAS_X = {"graphql": _via_graphql, "syndication": _via_syndication,
           "fxtwitter": _via_fxtwitter}


def _imagenes_x(tweet_id: str, ajustes: dict) -> dict:
    """Prueba las vías en orden (A5); loguea usada + fallidas + por qué."""
    fallos = []
    primero: _Falla | None = None
    for nombre in VIAS_X:
        if nombre == "fxtwitter" and not ajustes.get("fxtwitter", True):
            continue
        try:
            datos = _VIAS_X[nombre](tweet_id, ajustes)
        except _Falla as exc:
            if primero is None:
                primero = exc
            fallos.append(nombre)
            obtener_logger().info("Vías de imágenes X: %s falló [%s]: %s",
                                  nombre, exc.codigo, errors.sin_query(exc.detalle))
            continue
        except Exception as exc:
            codigo = errors.codigo_de(str(exc))
            if primero is None:
                primero = _Falla(codigo, errors.MENSAJES[codigo], str(exc))
            fallos.append(nombre)
            obtener_logger().info("Vías de imágenes X: %s falló [%s]: %s",
                                  nombre, codigo, errors.sin_query(str(exc)))
            continue
        obtener_logger().info("Imágenes X: vía %s usada (fallidas: %s)",
                              nombre, ", ".join(fallos) if fallos else "ninguna")
        return dict(datos, via=nombre)
    if primero is None:
        raise ErrorMiauki("sitio_no_soportado", "No hay vías configuradas para X.")
    raise ErrorMiauki(primero.codigo, primero.mensaje)


def _og_image_de(url: str, headers: dict | None = None) -> str:
    """Extrae la URL de `og:image` de una página (Paso 4-5)."""
    status, cuerpo = _pedir(url, headers=headers)
    if status != 200:
        raise _Falla("error_desconocido",
                     "El sitio no respondió bien (HTTP %d)." % status,
                     "og:image HTTP %d" % status)
    html = cuerpo.decode("utf-8", "replace")
    m = re.search(
        r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)',
        html)
    if not m:
        m = re.search(
            r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
            html)
    if not m:
        raise _Falla("no_es_video", "No encontré la imagen en esa página.",
                     "sin og:image")
    return m.group(1)


def _imagen_legible(url: str, headers: dict | None = None) -> bool:
    """¿La imagen se puede bajar y es imagen? (usa la red segura)."""
    try:
        _leer(url, headers=headers)
    except Exception:
        return False
    return True


def _via_pinterest(url: str, ajustes: dict) -> dict:
    """La imagen de un pin de Pinterest (og:image). Sin cookies."""
    try:
        img = _og_image_de(url, headers=_UA)
    except _Falla as exc:
        raise ErrorMiauki(exc.codigo, exc.mensaje) from None
    return {"imagenes": [img], "titulo": "Imagen de Pinterest",
            "autor": "", "via": "og"}


def _via_reddit(url: str, ajustes: dict) -> dict:
    """Reddit: lee el JSON público del post (sin cookies si es público).

    Devuelve la imagen o el video (mp4) que expone el post. Reddit hoy
    exige cookies para el extractor de yt-dlp; este camino usa el JSON
    público (reddit.com/.../.json) que expone `preview`/`media`.
    """
    base = (url or "").split("#")[0].rstrip("/")
    if not base.lower().startswith(("http://", "https://")):
        raise ErrorMiauki("link_invalido")
    headers = dict(_UA)
    pares, _ = cookies.para_dominio(ajustes, ("reddit.com",))
    if pares:
        headers["Cookie"] = "; ".join("%s=%s" % p for p in pares)
    status, cuerpo = _pedir(base + ".json", headers=headers)
    if status != 200:
        raise ErrorMiauki(
            "requiere_sesion",
            "Reddit pide iniciar sesión para ver ese post. Activá las cookies "
            "del navegador en Ajustes.")
    datos = _json(cuerpo)
    try:
        post = datos[0]["data"]["children"][0]["data"]
    except (TypeError, KeyError, IndexError):
        raise ErrorMiauki("error_desconocido",
                          "No pude leer ese post de Reddit.") from None
    # Video directo (mp4) si el post tiene media.
    media = post.get("secure_media") or post.get("media") or {}
    video = media.get("reddit_video") or {}
    fallback = video.get("fallback_url") or ""
    if fallback:
        return {"imagenes": [fallback], "titulo": post.get("title") or "",
                "autor": "", "via": "json", "es_video": True}
    # Imagen del post (preview o url directa).
    url_post = post.get("url_overridden_by_dest") or ""
    preview = (post.get("preview") or {}).get("images") or []
    if preview and isinstance(preview[0], dict):
        src = preview[0].get("source") or {}
        url_img = (src or {}).get("url") or ""
        if url_img:
            # Las URLs de preview vienen escapadas (\u0026).
            return {"imagenes": [url_img.replace("\\u0026", "&")],
                    "titulo": post.get("title") or "",
                    "autor": "", "via": "json"}
    if url_post and es_extension_imagen(url_post):
        return {"imagenes": [url_post], "titulo": post.get("title") or "",
                "autor": "", "via": "json"}
    raise ErrorMiauki("no_es_video",
                      "Ese post de Reddit no tiene imagen ni video accesibles.")


def _via_instagram_imagen(url: str, ajustes: dict) -> dict:
    """Instagram: foto de un post (og:image), con cookies si hace falta."""
    headers = dict(_UA)
    pares, _ = cookies.para_dominio(ajustes, ("instagram.com", "cdninstagram.com"))
    if pares:
        headers["Cookie"] = "; ".join("%s=%s" % p for p in pares)
    try:
        img = _og_image_de(url, headers=headers)
    except _Falla as exc:
        if exc.codigo == "error_desconocido" and not pares:
            raise ErrorMiauki(
                "requiere_sesion",
                "Ese post de Instagram necesita iniciar sesión. Activá las "
                "cookies del navegador en Ajustes.") from None
        raise ErrorMiauki(exc.codigo, exc.mensaje) from None
    if not _imagen_legible(img, headers=headers):
        if not pares:
            raise ErrorMiauki(
                "requiere_sesion",
                "Ese post de Instagram necesita iniciar sesión. Activá las "
                "cookies del navegador en Ajustes.")
        raise ErrorMiauki("error_desconocido",
                          "No pude bajar la imagen de Instagram.")
    return {"imagenes": [img], "titulo": "Imagen de Instagram",
            "autor": "", "via": "og"}


def _via_tiktok_photo(url: str, ajustes: dict) -> dict:
    """TikTok: post de fotos (pack). og:image como respaldo inicial.

    El pack completo requiere API propia (bloqueada sin sesión, verificado
    23/11/2026); se intenta og:image —con cookies si hay— y si no, un
    mensaje claro que apunta a la sesión del navegador.
    """
    headers = dict(_UA)
    pares, _ = cookies.para_dominio(ajustes, ("tiktok.com", "tiktokcdn.com"))
    if pares:
        headers["Cookie"] = "; ".join("%s=%s" % p for p in pares)
    try:
        img = _og_image_de(url, headers=headers)
    except _Falla as exc:
        if not pares:
            raise ErrorMiauki(
                "requiere_sesion",
                "TikTok no nos deja ver las fotos de ese post sin una sesión "
                "iniciada. Activá «Usar el inicio de sesión de tu navegador» "
                "en Ajustes.") from None
        if exc.codigo != "requiere_sesion":
            raise ErrorMiauki(
                "error_desconocido",
                "No pudimos acceder a las fotos de ese post de TikTok. Probá de "
                "nuevo más tarde.") from None
        raise ErrorMiauki(exc.codigo, exc.mensaje) from None
    if not _imagen_legible(img, headers=headers):
        raise ErrorMiauki(
            "error_desconocido",
            "No pudimos acceder a las fotos de ese post de TikTok. Probá de "
            "nuevo más tarde.")
    return {"imagenes": [img], "titulo": "Fotos de TikTok",
            "autor": "", "via": "og"}


def _via_facebook(url: str, ajustes: dict) -> dict:
    """Foto de Facebook: primero og:image (público); respaldo yt-dlp."""
    headers = dict(_UA)
    pares, _ = cookies.para_dominio(ajustes, ("facebook.com", "fbcdn.net"))
    if pares:
        headers["Cookie"] = "; ".join("%s=%s" % p for p in pares)
    try:
        img = _og_image_de(url, headers=headers)
    except _Falla:
        pass
    else:
        if not _imagen_legible(img, headers=headers):
            if not pares:
                raise ErrorMiauki(
                    "requiere_sesion",
                    "Las fotos de Facebook necesitan iniciar sesión. Activá las "
                    "cookies del navegador en Ajustes.")
            raise ErrorMiauki("error_desconocido",
                              "No pude bajar la imagen de Facebook.")
        return {"imagenes": [img], "titulo": "Foto de Facebook",
                "autor": "", "via": "og"}
    es_foto = ("photo" in url.lower() or "fbid=" in url.lower()
               or "photos" in url.lower())
    # Respaldo: yt-dlp (videos de Facebook; fotos que yt-dlp sí entienda).
    from miauki.core import analyzer  # import acá: analyzer importa a images (ciclo)
    try:
        info = analyzer._extraer(url, ajustes)
    except Exception as exc:
        codigo = errors.codigo_de(str(exc))
        obtener_logger().info("Facebook: yt-dlp falló [%s]: %s",
                              codigo, errors.sin_query(str(exc)))
        if es_foto and codigo == "sitio_no_soportado":
            raise _Falla(
                "requiere_sesion",
                "Las fotos de Facebook necesitan iniciar sesión. Activá las "
                "cookies del navegador en Ajustes.",
                "ytdlp: " + str(exc)) from None
        raise _Falla(codigo, errors.MENSAJES[codigo],
                     "ytdlp: " + str(exc)) from None
    fotos, vistas = [], set()
    for fuente in [info.get("url") or ""] + [
            e.get("url") or "" for e in (info.get("entries") or [])
            if isinstance(e, dict)]:
        if fuente and es_extension_imagen(fuente) and fuente not in vistas:
            vistas.add(fuente)
            fotos.append(fuente)
    if not fotos:
        raise _Falla("no_es_video",
                     "Ese link no devolvió fotos: el extractor de yt-dlp no "
                     "confirmó imágenes (probá con el link directo de la foto; "
                     "la causa quedó en el registro).",
                     "ytdlp sin fotos: " + errors.sin_query(str(info.get("url") or "")))
    return {"imagenes": fotos,
            "titulo": info.get("title") or "(sin título)",
            "autor": info.get("uploader") or info.get("channel") or ""}


def imagenes_de(url: str, ajustes: dict) -> dict:
    """Imágenes de un link de X o Facebook (vías intercambiables, A5).

    Devuelve {"sitio", "imagenes", "titulo", "autor", "via"} o lanza
    ErrorMiauki con código + mensaje amable.
    """
    p = urllib.parse.urlsplit(url)
    if (p.scheme or "").lower() not in ("http", "https") or not p.hostname:
        raise ErrorMiauki("link_invalido")
    host = p.hostname.lower()
    if es_imagen_x_directa(url):
        return {"sitio": "x", "imagenes": [_foto_url(url)], "titulo": "Imagen de X",
                "autor": "", "via": "directa"}
    if es_imagen_google(url):
        destino = url
        if (urllib.parse.urlsplit(url).hostname or "").lower() == "share.google":
            final = _destino_final(url)
            destino = final if es_imagen_google(final or "") else ""
        img = imgurl_de_google(destino)
        if not img:
            raise ErrorMiauki("no_es_video",
                              "No encontré la imagen en ese enlace de Google.")
        if not _imagen_legible(img):
            raise ErrorMiauki("no_es_video",
                              "No pude bajar esa imagen de Google.")
        return {"sitio": "google", "imagenes": [img],
                "titulo": "Imagen de Google", "autor": "", "via": "google"}
    if es_imagen_directa(url):
        if not _imagen_legible(url):
            raise ErrorMiauki("no_es_video", "No pude bajar esa imagen.")
        return {"sitio": "google", "imagenes": [url],
                "titulo": "Imagen", "autor": "", "via": "directa"}
    if _es_host_x(host):
        datos = _imagenes_x(id_tweet(url), ajustes)
        return dict(datos, sitio="x")
    if any(termina_en(host, d) for d in HOSTS_FACEBOOK):
        try:
            datos = _via_facebook(url, ajustes)
        except _Falla as exc:
            raise ErrorMiauki(exc.codigo, exc.mensaje) from None
        return dict(datos, sitio="facebook", via="ytdlp")
    if termina_en(host, "pinterest.com") or termina_en(host, "pinterest."):
        datos = _via_pinterest(url, ajustes)
        return dict(datos, sitio="pinterest")
    if termina_en(host, "reddit.com"):
        datos = _via_reddit(url, ajustes)
        return dict(datos, sitio="reddit")
    if termina_en(host, "instagram.com"):
        datos = _via_instagram_imagen(url, ajustes)
        return dict(datos, sitio="instagram")
    if termina_en(host, "tiktok.com") and "/photo/" in url.lower():
        datos = _via_tiktok_photo(url, ajustes)
        return dict(datos, sitio="tiktok")
    raise ErrorMiauki("sitio_no_soportado",
                      "Las imágenes de ese sitio todavía no están disponibles.")

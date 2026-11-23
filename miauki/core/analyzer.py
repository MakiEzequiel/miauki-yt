# -*- coding: utf-8 -*-
"""Motor de análisis: yt-dlp como librería, sin descargar nada (spec §4).

Fuentes (versión fijada yt-dlp==2026.8.19):
- README oficial: extract_info(url, download=False) + sanitize_info para
  JSON (https://github.com/yt-dlp/yt-dlp/blob/2026.08.19/README.md#extracting-information)
- YoutubeDL.py local: quiet (L241), noplaylist (L336), cookiesfrombrowser
  como tupla (L355), socket_timeout (L373).

Reglas: un análisis a la vez con tope de ~30 s y hilo daemon (A3), caché
de 5 min / 20 entradas sin errores (A7), errores mapeados a los códigos
amables (A4) y log sin cookies ni query (sin_query).
"""
import threading
import time
import uuid
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor, as_completed

from miauki.core import (cookies, errors, formats, images, motor, settings, sites,
                         validacion)
from miauki.core.errors import ErrorMiauki
from miauki.core.logger import obtener_logger

TIEMPO_MAX = 30.0
# Esperas del segundo nivel anti-bot (paso 3). El análisis se corta a los 30 s,
# así que acá entra solo la primera (5 s); el descargador usa las tres.
ESPERAS_ANALISIS = errors.ESPERAS_PACIENTES[:1]
SOCKET_TIMEOUT = 15
CACHE_TTL = 300  # 5 minutos (A7)
CACHE_MAX = 20
_cache: OrderedDict = OrderedDict()
_cache_traba = threading.Lock()
_traba = threading.Lock()
_hilo = None


# TikTok devuelve "Unexpected response from webpage request" al User-Agent de
# yt-dlp y funciona con uno de navegador real (medido 20/10/2026). yt-dlp
# recomienda impersonación (curl_cffi), que sería una dependencia nueva con
# binarios; el UA alcanza para el análisis y la descarga.
UA_NAVEGADOR = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36")


# Rotación de clientes de YouTube (tanda 22/11/2026, paso 2): cuando YouTube
# bloquea la conexión por anti-bot, cada reintento imita otra app (android,
# tv, ios, web). "default" es el cliente que yt-dlp ya usa por su cuenta.
CLIENTES_YT = ("default", "android", "tv", "ios", "web")


def cliente_youtube(opciones: dict, fallos: int) -> None:
    """Deja las opciones listas para el reintento número `fallos`."""
    cliente = CLIENTES_YT[fallos % len(CLIENTES_YT)]
    if cliente == "default":
        opciones.pop("extractor_args", None)
    else:
        opciones["extractor_args"] = {"youtube": {"player_client": [cliente]}}


def _opciones_ajustes(ajustes: dict, url: str = "") -> dict:
    """Opciones de YoutubeDL según los ajustes del usuario."""
    opciones = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "socket_timeout": SOCKET_TIMEOUT,
    }
    if "/playlist" in url or sites.es_perfil_instagram(url):
        # Playlist (plan de playlists) y perfil de Instagram (plan `plan.md`,
        # paso 2.2). Listado PLANO y rápido (título/url/duración por entrada,
        # sin extraer cada video). Cada video se vuelve a extraer por separado
        # recién al descargarlo; ignoreerrors saltea las entradas privadas/
        # eliminadas en el listado (decisión de Maki).
        opciones["extract_flat"] = "in_playlist"
        opciones["ignoreerrors"] = True
        # Un perfil puede tener miles de posts: se pide uno más que el tope
        # para detectar el exceso sin traerlos todos (protección de memoria).
        opciones["playlistend"] = validacion.MAX_PLAYLIST + 1
    opciones.update(cookies.opciones(ajustes))
    if url and sites.sitio_de_url(url) == "tiktok":
        opciones["http_headers"] = {"User-Agent": UA_NAVEGADOR}
    return opciones


def _extraer(url: str, ajustes: dict) -> dict:
    """Extrae la info del link. La verificación anti-bot de YouTube se
    reintenta rotando el cliente de yt-dlp (tanda 22/11/2026, paso 2) y, si
    sigue, esperando cada vez más (paso 3); el resto sale derecho."""
    yt_dlp = motor.ytdlp()
    intentos = 0
    paciente = 0
    while True:
        recolector = _RecolectorErrores()
        try:
            opciones = _opciones_ajustes(ajustes, url)
            opciones["logger"] = recolector
            cliente_youtube(opciones, intentos + paciente)
            with yt_dlp.YoutubeDL(opciones) as ydl:
                info = ydl.sanitize_info(ydl.extract_info(url, download=False)) or {}
            if not info and recolector.errores:
                # ignoreerrors se come el error real y devuelve None: se
                # recupera para mapearlo (así el bloqueo de YouTube no queda
                # como "el motor no devolvió datos").
                raise RuntimeError(recolector.errores[-1])
        except Exception as exc:
            codigo = errors.codigo_de(str(exc))
            if codigo == "youtube_verificacion_bot":
                if intentos < 2:
                    intentos += 1
                    time.sleep(errors.ESPERA_BOT)
                    continue
                if paciente < len(ESPERAS_ANALISIS):
                    time.sleep(ESPERAS_ANALISIS[paciente])
                    paciente += 1
                    continue
            # Ajustes 21/11: un "eliminado" pasajero en YouTube se reintenta una
            # vez de inmediato (página de verificación mal clasificada, etc.).
            if (codigo == "video_eliminado" and intentos == 0
                    and "youtube.com" in url):
                intentos = 1
                continue
            raise
        return info


class _RecolectorErrores:
    """Logger mínimo para yt-dlp: guarda los errores que ignora."""

    def __init__(self):
        self.errores = []

    def debug(self, mensaje):
        pass

    def info(self, mensaje):
        pass

    def warning(self, mensaje):
        pass

    def error(self, mensaje):
        self.errores.append(str(mensaje))


def _version_ytdlp() -> str:
    try:
        return motor.version_en_uso()
    except Exception:
        return "?"


def _altura(f: dict):
    """Altura para agrupar/etiquetar: el lado corto en videos verticales.

    Decisión de Maki (15/10/2026): un reel de 1080×1920 es "1080p",
    en las etiquetas y para aplicar las reglas de calidad §5b.
    """
    h = f.get("height")
    if not isinstance(h, (int, float)) or not h:
        return None
    w = f.get("width")
    if isinstance(w, (int, float)) and w and w < h:
        h = w
    return int(h)


def _es_video(f: dict) -> bool:
    return _altura(f) is not None and (f.get("vcodec") or "none") != "none"


def _es_original(f: dict) -> bool:
    """Un formato con URL directa y sin height/vcodec/tbr/acodec: no manda
    metadatos de calidad (ej. videos de Snapchat)."""
    return bool(f.get("url")) and not (f.get("height") or f.get("vcodec")
                                     or f.get("tbr") or f.get("acodec"))


def _con_audio(f: dict) -> bool:
    return (f.get("acodec") or "none") != "none"


def _tbr(f: dict):
    t = f.get("tbr")
    return float(t) if isinstance(t, (int, float)) and t else None


def _mejor(candidatos: list, preferible=None) -> dict:
    """El de mayor bitrate; si hay, entre los que cumplen `preferible`."""
    if preferible is not None:
        viables = [f for f in candidatos if preferible(f)]
        if viables:
            candidatos = viables
    return max(candidatos, key=lambda f: _tbr(f) or 0)


def _peso(combo: list, duracion):
    """Peso en bytes: filesize, si no filesize_approx (marcado), si no
    bitrate × duración (marcado). None si no hay con qué estimar (nunca 0)."""
    tamanios, aprox = [], False
    for f in combo:
        if f.get("filesize"):
            tamanios.append(int(f["filesize"]))
        elif f.get("filesize_approx"):
            tamanios.append(int(f["filesize_approx"]))
            aprox = True
        else:
            tamanios = []
            break
    if tamanios:
        return sum(tamanios), aprox
    tasas = [_tbr(f) for f in combo]
    if all(t is not None for t in tasas) and duracion:
        return int(sum(tasas) * 1000 * duracion / 8), True
    return None, False


def _da_mp4_video(f: dict) -> bool:
    """El video por sí solo entra en mp4 (H.264 o sin video)."""
    return formats.contenedor_de(f.get("vcodec"), "none") == "mp4"


def _da_mp4_audio(f: dict) -> bool:
    return formats.contenedor_de("none", f.get("acodec")) == "mp4"


def _da_mp4_completo(f: dict) -> bool:
    return formats.contenedor_de(f.get("vcodec"), f.get("acodec")) == "mp4"


def _codec(vcodec) -> str:
    """Códec corto para la interfaz ("h264", "hevc", "av1", "vp9")."""
    texto = str(vcodec or "")
    if texto.startswith("avc1"):
        return "h264"
    if texto.startswith(("hev1", "hvc1", "hvc2")):
        return "hevc"
    if texto.startswith("av01"):
        return "av1"
    if texto.startswith(("vp9", "vp09")):
        return "vp9"
    return texto


def _selector_video(altura: int, mp4: bool) -> str:
    """Selector de yt-dlp por ALTURA y CÓDEC, con respaldos (P0.5).

    No guarda IDs de formato (que cambian entre análisis en sitios como
    Facebook): pide "el mejor video hasta esa altura" y, separado por "/",
    deja respaldos por si el preferido no existe. El filtro por ANCHO va
    PRIMERO: en videos verticales el alto real es el lado largo, y filtrar
    solo por alto bajaba 576p cuando se pedía 1080p (medido en TikTok,
    20/10/2026). Termina en "best". Para la vía mp4 exige H.264 + AAC
    (sin re-codificar).
    """
    h = "height<=%d" % altura
    w = "width<=%d" % altura
    vh, vw = "bestvideo[%s]" % h, "bestvideo[%s]" % w
    if mp4:
        vh += "[vcodec^=avc1]"
        vw += "[vcodec^=avc1]"
        candidatos = [
            vw + "+bestaudio[acodec^=mp4a]",
            vh + "+bestaudio[acodec^=mp4a]",
            vw + "+bestaudio",
            vh + "+bestaudio",
            "best[%s][ext=mp4]" % w,
            "best[%s][ext=mp4]" % h,
        ]
    else:
        candidatos = [
            vw + "+bestaudio",
            vh + "+bestaudio",
            "best[%s]" % w,
            "best[%s]" % h,
        ]
    candidatos.append("best")
    return "/".join(candidatos)


def _contenedor_de_formato(f: dict) -> str:
    """Contenedor real de un formato: la extensión si es mp4/mkv, si no el de los códecs."""
    ext = (f.get("ext") or "").lower()
    if ext in ("mp4", "mkv"):
        return ext
    return formats.contenedor_de(f.get("vcodec"), f.get("acodec"))


def _opciones_de_altura(videos: list, audios: list, altura: int,
                       recomendada, duracion) -> list:
    """Una o dos opciones para una altura: mp4 (H.264+AAC) y/o mkv (AV1/VP9/..).

    El Paso 2 de Maki: si a una misma altura hay más de un contenedor viable,
    se ofrecen como opciones separadas (una por contenedor), cada una con su
    peso y su formato real. Si solo hay un contenedor, es una sola opción.
    """
    candidatos = [f for f in videos if _altura(f) == altura]
    progresivos = [f for f in candidatos if _con_audio(f)]
    combinaciones: list = []
    if progresivos:
        grupos: dict = {}
        for f in progresivos:
            grupos.setdefault(_contenedor_de_formato(f), []).append(f)
        for contenedor in sorted(grupos, key=lambda c: (c != "mp4", c)):
            combinaciones.append(
                ([_mejor(grupos[contenedor],
                         _da_mp4_completo if contenedor == "mp4" else None)],
                 contenedor))
    elif candidatos:
        mejor_video = _mejor(candidatos, _da_mp4_video) if candidatos else None
        mejor_audio = _mejor(audios, _da_mp4_audio) if audios else None
        mejor_combo = [mejor_video] + ([mejor_audio] if mejor_audio is not None else [])
        mejor_contenedor = formats.contenedor_de(
            mejor_video.get("vcodec"), mejor_audio.get("acodec") if mejor_audio else "none")
        combinaciones.append((mejor_combo, mejor_contenedor))
        v_mp4 = _mejor([f for f in candidatos if _da_mp4_video(f)],
                       _da_mp4_video) if any(_da_mp4_video(f) for f in candidatos) else None
        a_mp4 = _mejor([f for f in audios if _da_mp4_audio(f)],
                       _da_mp4_audio) if any(_da_mp4_audio(f) for f in audios) else None
        if v_mp4 is not None and (a_mp4 is not None or not audios):
            combinaciones.append(([v_mp4] + ([a_mp4] if a_mp4 is not None else []),
                                   formats.contenedor_de(
                                       v_mp4.get("vcodec"),
                                       a_mp4.get("acodec") if a_mp4 else "none")))
    opciones = []
    vistas_contenedores = set()
    for i, (combo, contenedor) in enumerate(combinaciones):
        if contenedor in vistas_contenedores:
            continue
        vistas_contenedores.add(contenedor)
        peso, aprox = _peso(combo, duracion)
        opciones.append({
            "resolucion": altura,
            "etiqueta": "%dp" % altura,
            "recomendada": recomendada if i == 0 else None,
            "selector": _selector_video(altura, contenedor == "mp4"),
            "contenedor": contenedor,
            "codec": _codec(combo[0].get("vcodec")),
            "peso_bytes": peso,
            "peso_aprox": aprox,
        })
    return opciones


def _calidades(formatos: list, duracion) -> list:
    videos = [f for f in formatos if _es_video(f)]
    if not videos:
        original = next((f for f in formatos if _es_original(f)), None)
        if original is None:
            return []
        # Snapchat manda un único formato sin metadatos: la única opción es
        # "Original" (calidad desconocida, se baja con el selector "best").
        # Se guarda la URL directa: yt-dlp rechaza el formato por su extensión
        # rara (IRZXSOY), así que el downloader baja esa URL sin yt-dlp.
        # Peso real via HEAD (images.peso_de_video), sin inventar.
        peso = images.peso_de_video(original.get("url"))
        return [{
            "resolucion": None,
            "etiqueta": "Original",
            "recomendada": None,
            "selector": "best",
            "contenedor": _contenedor_de_formato(original),
            "codec": _codec(original.get("vcodec")),
            "peso_bytes": peso,
            "peso_aprox": False if peso is not None else False,
            "url_directa": original.get("url"),
        }]
    audios = [f for f in formatos if _con_audio(f) and not _es_video(f)]
    alturas = sorted({_altura(f) for f in videos}, reverse=True)
    max_res = min(max(alturas), formats.TOPE_8K)
    recomendadas = [int(e[:-1]) for e in formats.calidades_recomendadas(max_res)]
    extendidas = alturas
    nombres = ["La mejor", "Equilibrada", "Liviana"]
    salida, vistas = [], set()
    for i, objetivo in enumerate(recomendadas):
        real = max((h for h in alturas if h <= objetivo), default=None)
        if real is None or real in vistas:
            continue
        vistas.add(real)
        salida.append((real, nombres[i] if i < len(nombres) else None))
    for h in extendidas:
        if h not in vistas:
            vistas.add(h)
            salida.append((h, None))
    return [opcion
            for h, nom in salida
            for opcion in _opciones_de_altura(videos, audios, h, nom, duracion)]


def _musica(hay_audio: bool, duracion):
    if not hay_audio:
        return []
    return [{
        "kbps": k,
        "selector": "bestaudio",
        "postproceso": "mp3",
        "peso_bytes": int(duracion * k * 1000 / 8) if duracion else None,
        "peso_aprox": True,
        "advertencia": "El MP3 se genera del audio original: no mejora la calidad que ya trae.",
    } for k in (320,)]


def _orden_idiomas(claves) -> list:
    """es y en primero (los únicos que usa la app), después el resto."""
    ids = sorted(claves)
    preferidos = [i for i in ("es", "en") if i in ids]
    resto = [i for i in ids if i not in ("es", "en")]
    return (preferidos + resto)[:15]


def _subtitulos(info: dict) -> tuple[dict, list]:
    manuales = info.get("subtitles") or {}
    automaticas = info.get("automatic_captions") or {}
    if manuales:
        return {"disponible": True, "idiomas": _orden_idiomas(manuales)}, []
    if automaticas:
        return ({"disponible": True, "idiomas": _orden_idiomas(automaticas)},
                ["Los subtítulos son automáticos: pueden tener errores."])
    return {"disponible": False, "idiomas": []}, []


def _mayor_miniatura(info: dict):
    """URL de la miniatura más grande (Instagram manda varias medidas)."""
    candidatas = [t for t in (info.get("thumbnails") or [])
                  if isinstance(t, dict) and t.get("url")]
    if not candidatas:
        return None
    mayor = max(candidatas,
                key=lambda t: (t.get("width") or 0) * (t.get("height") or 0))
    return mayor.get("url")


def _resultado_de(info: dict, sitio: str, url: str) -> dict:
    """El contrato completo que recibe la interfaz (spec §4)."""
    info = info or {}
    formatos = info.get("formats") or []
    entradas = [e for e in (info.get("entries") or []) if isinstance(e, dict)]
    duracion = info.get("duration")
    if isinstance(duracion, (int, float)) and duracion:
        duracion = int(duracion)
    else:
        duracion = None
    hay_video = any(_es_video(f) for f in formatos)
    hay_audio = any(_con_audio(f) for f in formatos)
    url_directa = info.get("url") or ""
    imagenes = []
    foto_story = None
    if entradas:
        imagenes = [e.get("url") or e.get("thumbnail") or "" for e in entradas]
        imagenes = [u for u in imagenes if u]
        tipo = "imagen" if imagenes and all(images.es_extension_imagen(u)
                                            for u in imagenes) else "video"
    elif (info.get("ext") or "").lower() in images.EXTENSIONES_IMAGEN or (
            url_directa and images.es_extension_imagen(url_directa) and not hay_video):
        tipo = "imagen"
        imagenes = [url_directa] if url_directa else []
    elif sitio == "instagram" and not formatos and _mayor_miniatura(info):
        # Story solo-imagen (plan `plan.md`, paso 1.2): llega sin formatos y
        # sin `url`; la foto es la miniatura de mayor tamaño.
        foto_story = _mayor_miniatura(info)
        tipo = "imagen"
        imagenes = [foto_story]
    elif hay_video:
        tipo = "video"
    elif hay_audio:
        tipo = "audio"
    else:
        tipo = "video"
    if tipo == "imagen":
        tipos = ["imagen"]
    elif hay_video and hay_audio:
        tipos = ["video", "audio"]
    elif hay_video:
        tipos = ["video"]
    else:
        tipos = ["audio"]
    subtitulos, advertencias = _subtitulos(info)
    calidades = _calidades(formatos, duracion)
    advertencias = list(advertencias)
    if tipo == "video" and calidades and calidades[0].get("resolucion") is None:
        # Opción "Original": el formato no trajo metadatos de calidad.
        advertencias.append("No se detectó la resolución del video")
    miniatura = images.data_uri_de(info.get("thumbnail"))
    if tipo == "imagen":
        tipos = ["imagen"]
        imagenes_urls = list(imagenes)
        if foto_story:
            # La grilla solo pinta data:image/ (CSP): la foto se convierte una
            # vez y la URL real queda en imagenes_urls para descargarla (3d.13).
            uri = images.data_uri_de(foto_story)
            if uri:
                imagenes = [uri]
    else:
        # Decisión de Maki (15/10/2026): un video ofrece video, música e
        # imagen (la imagen es la miniatura en la mayor calidad disponible).
        # Si el link es video pero no se detectaron formatos (ej. Snapchat), el
        # video igual es una opción válida: no se puede ofrecer música sin él.
        tipos = ["video", "musica", "imagen"] if (hay_video or tipo == "video") \
            else ["musica", "imagen"]
        imagenes_urls = list(imagenes)
        if miniatura and not imagenes:
            imagenes = [miniatura]
            imagenes_urls = ([info["thumbnail"]] if info.get("thumbnail")
                             else [])
    return {
        "id_solicitud": uuid.uuid4().hex,
        "tipo": tipo,
        "sitio": sitio,
        "titulo": info.get("title") or "(sin título)",
        "autor": info.get("uploader") or info.get("channel") or info.get("creator") or "",
        "duracion": duracion,
        "miniatura": miniatura,
        "url_canonica": info.get("webpage_url") or url,
        "tipos": tipos,
        "subtitulos": subtitulos,
        "calidades": calidades,
        "musica": _musica(tipo != "imagen" and hay_audio, duracion),
        "imagenes": imagenes,
        "imagenes_urls": imagenes_urls,
        "advertencias": advertencias,
    }


_ESCALAS_PLAYLIST = [4320, 2160, 1440, 1080, 720, 480, 360, 240]


def _altura_max_video(url: str, ajustes: dict):
    """Altura máxima real de un video desde sus formatos (None si falla)."""
    try:
        info = _extraer(url, ajustes)
    except Exception:
        return None
    formatos = info.get("formats") or []
    alturas = [_altura(f) for f in formatos if _es_video(f)]
    return max(alturas) if alturas else None


def _sondear_calidades_playlist(entradas: list, ajustes: dict,
                                presupuesto_s: float | None = None) -> dict:
    """Sondea la calidad máxima real de cada video de una playlist (híbrido).

    Extrae formatos en paralelo (hasta 8 workers) con un presupuesto total de
    tiempo que crece con el tamaño de la lista. Devuelve
    {"alturas": {url: altura}, "incompleto": bool, "duracion_sondeo": float}.
    Si se agota el presupuesto, devuelve lo que haya y `incompleto=True`
    (el llamador cae al comportamiento actual). Si aparecen alturas distintas
    se corta temprano: ya se sabe que la lista es mixta y no hace falta
    seguir sondeando.
    """
    urls = [e.get("webpage_url") or e.get("url") or ""
            for e in entradas if isinstance(e, dict)]
    urls = [u for u in urls if u.startswith(("http://", "https://"))]
    resultado = {"alturas": {}, "incompleto": False, "duracion_sondeo": 0.0}
    if not urls:
        return resultado
    if presupuesto_s is None:
        # Dinámico según tamaño: listas grandes necesitan más tiempo para
        # completar el sondeo y poder mostrar la calidad uniforme real.
        presupuesto_s = min(150.0, 30.0 + 0.20 * len(urls))
    inicio = time.monotonic()
    workers = min(8, len(urls))
    executor = ThreadPoolExecutor(max_workers=workers)
    futuros = {executor.submit(_altura_max_video, u, ajustes): u for u in urls}
    try:
        for futuro in as_completed(futuros, timeout=presupuesto_s):
            altura = futuro.result()
            if altura:
                resultado["alturas"][futuros[futuro]] = altura
            if len(set(resultado["alturas"].values())) > 1:
                # Ya hay mezcla: no hace falta sondear el resto.
                break
    except TimeoutError:
        resultado["incompleto"] = True
    finally:
        executor.shutdown(wait=False, cancel_futures=True)
    resultado["duracion_sondeo"] = time.monotonic() - inicio
    return resultado


def _calidades_playlist(modo: str, maxima) -> list:
    """Opciones del menú de calidad de una playlist (valores para la UI).

    - Uniforme: toda la lista tiene la misma máxima → se ofrece esa máxima
      real y las inferiores (más música).
    - Mixta: hay calidades distintas → "Calidad Máxima" (baja cada video en
      su mayor calidad real) + opciones fijas inferiores + música. Es la
      decisión de Maki (20/11 #2): siempre se puede descargar todo.
    - Fallback (sondeo incompleto): comportamiento clásico.
    """
    opciones = []
    if modo == "uniforme":
        if maxima:
            opciones.append({"valor": str(maxima), "resolucion": maxima})
        for h in _ESCALAS_PLAYLIST:
            if maxima and h < maxima:
                opciones.append({"valor": str(h), "resolucion": h})
    else:  # mixta o fallback: "Calidad Máxima" + opciones fijas inferiores.
        opciones.append({"valor": "mejor", "resolucion": None})
        for h in (1080, 720, 480):
            opciones.append({"valor": str(h), "resolucion": h})
    opciones.append({"valor": "musica", "resolucion": None})
    return opciones


def _calidad_defecto_playlist(modo: str, maxima) -> str:
    if modo == "uniforme" and maxima:
        return str(maxima)
    return "mejor"  # mixta y fallback: "Calidad Máxima".


def _playlist(info: dict, sitio: str, url: str, ajustes: dict) -> dict:
    """Contrato para una playlist (Paso 2): lista de entradas, cada una con
    el mismo contrato que un video individual. Si una entry falla en el
    análisis, se saltea pero la lista continúa (decisión de Maki)."""
    crudas = list(info.get("entries") or [])
    if len(crudas) > validacion.MAX_PLAYLIST:
        # Mismo tope que el borde (validacion): una lista enorme se rechaza
        # al analizar, no después de encolarla (protección de memoria).
        raise ErrorMiauki("playlist_muy_larga")
    # Calidad máxima real por video (híbrido, plan 20/11 #2): si el sondeo
    # termina y todas las máximas son iguales, esa es la calidad máxima que se
    # ofrece; si son distintas, todo pasa a 1080p y los videos de menor
    # calidad se saltean; si no termina en el presupuesto, comportamiento
    # actual ("Mejor calidad", sin tope ni salteados).
    sondeo = _sondear_calidades_playlist(crudas, ajustes)
    alturas = sondeo.get("alturas") or {}
    distintas = set(alturas.values())
    completa = bool(alturas) and not sondeo.get("incompleto")
    advertencias = []
    if completa and len(distintas) == 1:
        modo, maxima = "uniforme", next(iter(distintas))
    elif completa or len(distintas) > 1:
        # Mixta (o corte temprano porque ya se vio mezcla): se ofrece la
        # máxima real de la lista y cada video baja en su mejor calidad
        # disponible; NO se saltea nada por calidad (decisión de Maki,
        # corrección 20/11 #2).
        modo, maxima = "mixta", max(alturas.values()) if alturas else None
    elif alturas and len(distintas) == 1 and len(alturas) >= len(crudas) * 0.5:
        # Sondeo incompleto pero la muestra cubrió al menos la mitad y TODAS
        # coinciden: se muestra la calidad uniforme con advertencia honesta
        # (estimada por muestra, no verificada al 100%).
        modo, maxima = "uniforme", next(iter(distintas))
        advertencias.append(
            "Sondeo de calidad incompleto (muestra %d de %d videos): "
            "la calidad mostrada se estimó sobre esa muestra."
            % (len(alturas), len(crudas)))
    else:
        modo, maxima = "fallback", None
    entradas, salteados = [], []
    for entry in crudas:
        if not isinstance(entry, dict):
            # Entrada que yt-dlp no pudo listar (ignoreerrors la saltea).
            salteados.append({"entry": "", "motivo": "playlist_error_analisis"})
            continue
        # Entrada PLANA (extract_flat): la URL del video está en "url" y la
        # miniatura puede venir solo en la lista "thumbnails". Sin id de
        # YouTube no hay miniatura: no se inventa.
        url_entry = entry.get("webpage_url") or entry.get("url") or url
        mini = entry.get("thumbnail")
        if not mini and isinstance(entry.get("thumbnails"), list) \
                and entry["thumbnails"]:
            mini = (entry["thumbnails"][-1] or {}).get("url")
        try:
            entradas.append(_resultado_de(
                dict(entry, webpage_url=url_entry, thumbnail=mini),
                sitio, url_entry))
        except Exception as exc:  # video salteado: se registra y se sigue
            # El motivo queda como CODIGO de causa (decision de Maki, Paso 6):
            # la interfaz lo agrupa con el catalogo de causas.
            motivo = exc.codigo if isinstance(exc, ErrorMiauki) \
                else "error_desconocido"
            salteados.append({"entry": entry.get("id") or entry.get("title") or "",
                              "motivo": motivo})
    duracion = info.get("_playlist_duration") or info.get("duration")
    if isinstance(duracion, (int, float)) and duracion:
        duracion = int(duracion)
    else:
        duracion = None
    return {
        "id_solicitud": uuid.uuid4().hex,
        "es_playlist": True,
        "tipo": "playlist",
        "sitio": sitio,
        "titulo": info.get("title") or "(sin título)",
        "autor": info.get("uploader") or info.get("channel") or "",
        "duracion": duracion,
        "miniatura": images.data_uri_de(info.get("thumbnail")),
        "url_canonica": info.get("webpage_url") or url,
        "entradas": entradas,
        "salteados": salteados,
        "advertencias": advertencias,
        "calidades": _calidades_playlist(modo, maxima),
        "calidad_defecto": _calidad_defecto_playlist(modo, maxima),
        "sondeo_completo": completa,
        "sondeo_incompleto": bool(alturas) and not completa,
        "modo_calidad": modo,
    }


def _resultado_imagenes(datos: dict, sitio: str, url: str) -> dict:
    """Resultado con el MISMO contrato de _resultado_de desde las vías de imágenes (§5).

    Si la vía devuelve `es_video` (p.ej. video de Reddit por JSON), se arma
    un resultado tipo video con la opción "Original" y URL directa (el mismo
    caso que Snapchat, Paso 3).
    """
    if datos.get("es_video"):
        video = datos.get("video") or {}
        duracion = video.get("duracion")
        if isinstance(duracion, float):
            duracion = round(duracion, 1)
        miniatura = images.data_uri_de(video.get("miniatura") or "")
        calidades = []
        for variante in video.get("variantes") or []:
            alto = variante.get("alto")
            bitrate = variante.get("bitrate") or 0
            # Peso exacto por HEAD; si falla, bitrate × duración (aproximado).
            peso = images.peso_de_video(variante.get("url") or "")
            aprox = False
            if not peso:
                peso = int(bitrate * duracion / 8) if bitrate and duracion else None
                aprox = bool(peso)
            calidades.append({
                "resolucion": alto,
                "etiqueta": ("%dp" % alto) if alto else "Original",
                "recomendada": None,
                "selector": "best",
                "contenedor": "mp4",
                "codec": "",
                "peso_bytes": peso,
                "peso_aprox": aprox,
                "url_directa": variante.get("url"),
            })
        if calidades:
            # Mismos tres nombres que yt-dlp (Mejor/Equilibrada/Liviana): la
            # pantalla muestra hasta tres calidades sin abrir "Más opciones".
            for i, nombre in enumerate(("La mejor", "Equilibrada", "Liviana")):
                if i < len(calidades):
                    calidades[i]["recomendada"] = nombre
        else:
            # Vías sin variantes (p.ej. Reddit): una sola opción "Original".
            directa = (datos.get("imagenes") or [None])[0]
            if directa:
                calidades = [{
                    "resolucion": None, "etiqueta": "Original",
                    "recomendada": None, "selector": "best",
                    "contenedor": "mp4", "codec": "", "peso_bytes": None,
                    "peso_aprox": False, "url_directa": directa,
                }]
        advertencias = []
        if calidades and calidades[0].get("resolucion") is None:
            advertencias.append("No se detectó la resolución del video")
        return {
            "id_solicitud": uuid.uuid4().hex,
            "tipo": "video",
            "sitio": sitio,
            "titulo": datos.get("titulo") or "(sin título)",
            "autor": datos.get("autor") or "",
            "duracion": duracion,
            "miniatura": miniatura,
            "url_canonica": url,
            "tipos": ["video", "imagen"],
            "subtitulos": {"disponible": False, "idiomas": []},
            "calidades": calidades,
            "musica": [],
            "imagenes": [miniatura] if miniatura else [],
            "imagenes_urls": ([video.get("miniatura")] if miniatura else []),
            "advertencias": advertencias,
        }
    fotos = datos.get("imagenes") or []
    # La UI solo puede mostrar data:image/ (CSP img-src 'self' data:): las
    # vías devuelven URLs y acá se convierten; las que no se pueden bajar
    # se descartan (la interfaz igual nunca confía en la URL, §7). La URL
    # real viaja en `imagenes_urls` para poder encolar la descarga (3d.13).
    convertidas = [(u, images.data_uri_de(u)) for u in fotos]
    convertidas = [(u, d) for u, d in convertidas if d]
    uris = [d for _, d in convertidas]
    urls = [u for u, _ in convertidas]
    return {
        "id_solicitud": uuid.uuid4().hex,
        "tipo": "imagen",
        "sitio": sitio,
        "titulo": datos.get("titulo") or "(sin título)",
        "autor": datos.get("autor") or "",
        "duracion": None,
        "miniatura": uris[0] if uris else None,
        "url_canonica": url,
        "tipos": ["imagen"],
        "subtitulos": {"disponible": False, "idiomas": []},
        "calidades": [],
        "musica": [],
        "imagenes": uris,
        "imagenes_urls": urls,
        "advertencias": [],
    }


def _tomar_cache(clave: tuple):
    with _cache_traba:
        item = _cache.get(clave)
        if item is None:
            return None
        if time.monotonic() - item[0] > CACHE_TTL:
            del _cache[clave]
            return None
        _cache.move_to_end(clave)
        return item[1]


def _poner_cache(clave: tuple, resultado: dict) -> None:
    with _cache_traba:
        _cache[clave] = (time.monotonic(), resultado)
        _cache.move_to_end(clave)
        while len(_cache) > CACHE_MAX:
            _cache.popitem(last=False)


def _es_foto_facebook(url: str) -> bool:
    """¿El link de Facebook es una foto (o álbum)? Decisión de Maki 15/10/2026:
    el mensaje de "sitio no soportado" es más específico en esos casos."""
    u = (url or "").lower()
    return ("facebook.com/photo" in u or "facebook.com/photos" in u
            or "photo.php" in u or "fbid=" in u)


def analizar(url: str, forzar: bool = False, tiempo_max: float | None = None) -> dict:
    """Analiza un link y devuelve el resultado (spec §4 y §7).

    - Si hay otro análisis en curso: ErrorMiauki("analisis_en_curso") (A3).
    - Si no termina en ~30 s: ErrorMiauki("tiempo_agotado") y su resultado
      tardío se descarta (cada llamada solo lee su propia caja de resultado).
    - forzar=True salta la caché (A7).
    """
    inicio = time.monotonic()
    global _hilo
    sitio, canonica = sites.detectar(url)
    ajustes = settings.cargar()
    clave = (canonica, ajustes.get("navegador_cookies"), ajustes.get("idioma_subs"))
    if not forzar:
        guardado = _tomar_cache(clave)
        if guardado is not None:
            return dict(guardado, id_solicitud=uuid.uuid4().hex)
    if images.es_imagen_x_directa(canonica) or images.es_imagen_google(canonica) \
            or images.es_imagen_directa(canonica):
        # Fase 9, B1 + auditoría 23/11: imagen suelta de X (pbs.twimg.com),
        # Google Imágenes (share.google / imgres) y gstatic. No van a yt-dlp.
        datos = images.imagenes_de(canonica, ajustes)
        imagen_sitio = "x" if images.es_imagen_x_directa(canonica) else "google"
        resultado = _resultado_imagenes(datos, imagen_sitio, canonica)
        _poner_cache(clave, resultado)
        obtener_logger().info(
            "Análisis ok por vía de imágenes sitio=%s via=%s tiempo=%.1fs",
            sitio, datos.get("via", "?"), time.monotonic() - inicio)
        return resultado
    with _traba:
        if _hilo is not None and _hilo.is_alive():
            raise ErrorMiauki("analisis_en_curso")
        caja: dict = {}

        def trabajador():
            try:
                caja["info"] = _extraer(canonica, ajustes)
            except Exception as exc:  # el error se mapea en el hilo principal
                caja["error"] = exc

        _hilo = threading.Thread(target=trabajador, daemon=True, name="analizar")
        _hilo.start()
        hilo = _hilo
    hilo.join(TIEMPO_MAX if tiempo_max is None else tiempo_max)
    if hilo.is_alive():
        obtener_logger().info("Análisis sin respuesta en el tope (%.0f s): %s",
                              TIEMPO_MAX, errors.sin_query(canonica))
        raise ErrorMiauki("tiempo_agotado")
    if "error" in caja:
        codigo = errors.codigo_de(str(caja["error"]))
        obtener_logger().warning("yt-dlp (%s): %s",
                                 codigo, errors.sin_query(str(caja["error"])))
        # Sitios que caen a vías propias de imagen (o el público de Reddit)
        # cuando yt-dlp no los cubre: foto de Facebook, Pinterest, Reddit,
        # TikTok photo e Instagram imagen.
        texto_error = str(caja["error"]).lower()
        es_imagen_con_via = (
            sitio == "facebook" and _es_foto_facebook(canonica)
            or sitio in ("pinterest", "reddit")
            or (sitio == "tiktok" and "/photo/" in canonica.lower())
            or (sitio == "instagram" and "no video" in texto_error)
        )
        if sitio == "x" or es_imagen_con_via:
            # yt-dlp no cubre fotos de X → vías propias (§5, A5). Si tampoco
            # dan resultado, se informa el error original de yt-dlp. Si la vía
            # dice que falta sesión (contenido sensible), ese mensaje es el
            # útil para Maki (Fase 9, B2) y lleva a Ajustes.
            try:
                datos = images.imagenes_de(canonica, ajustes)
            except Exception as exc:
                obtener_logger().info("Vías de imágenes %s sin éxito: %s",
                                      sitio, errors.sin_query(str(exc)))
                if getattr(exc, "codigo", None) in ("requiere_sesion",
                                                    "restriccion_edad"):
                    raise ErrorMiauki(exc.codigo, exc.mensaje) from None
                if es_imagen_con_via and getattr(exc, "codigo", None):
                    raise ErrorMiauki(exc.codigo, exc.mensaje) from None
            else:
                resultado = _resultado_imagenes(datos, sitio, canonica)
                _poner_cache(clave, resultado)
                obtener_logger().info(
                    "Análisis ok por vía de imágenes sitio=%s via=%s tiempo=%.1fs",
                    sitio, datos.get("via", "?"), time.monotonic() - inicio)
                return resultado
        if (sitio == "facebook" and codigo == "sitio_no_soportado"
                and _es_foto_facebook(canonica)):
            # yt-dlp no tiene extractor de fotos de Facebook (verificado
            # 15/10/2026, ambas variantes de URL): mensaje específico.
            raise ErrorMiauki(
                "sitio_no_soportado",
                "Las fotos de Facebook todavía no se pueden analizar.")
        raise ErrorMiauki(codigo)
    info = caja.get("info") or {}
    if not info:
        # ignoreerrors deja None cuando el extractor falló entero (un perfil de
        # Instagram que yt-dlp ya no sabe leer, por ejemplo): sin esto la
        # interfaz mostraría una tarjeta vacía como si fuera un video.
        obtener_logger().warning("El motor no devolvió datos: %s",
                                 errors.sin_query(canonica))
        raise ErrorMiauki("error_desconocido")
    if info.get("_type") == "playlist":
        resultado = _playlist(info, sitio, canonica, ajustes)
    else:
        resultado = _resultado_de(info, sitio, canonica)
    _poner_cache(clave, resultado)
    obtener_logger().info("Análisis ok sitio=%s tiempo=%.1fs yt-dlp=%s url=%s",
                          sitio, time.monotonic() - inicio, _version_ytdlp(),
                          errors.sin_query(canonica))
    return resultado

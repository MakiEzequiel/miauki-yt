# -*- coding: utf-8 -*-
"""Ejecuta una descarga y reporta progreso (Fase 4, B2).

Receta probada de la v2.6 (engine.download_opts + jobs._run), adaptada al
contrato de esta app: el snapshot que encoló la interfaz + los ajustes →
yt-dlp; la ruta final sale de `requested_downloads[0].filepath` (ya con el
postproceso aplicado: merge y MP3) con fallback a `prepare_filename`.

Decisiones (DECISIONES.md §3d):
- selector y contenedor tal cual los mandó el análisis: sin re-codificar video;
- progreso monótono, máximo ~4 eventos por segundo (clase _Tope);
- subtítulos en una segunda pasada best-effort que nunca rompe la descarga;
- cancelar corta el hilo de verdad (Cancelada desde el hook) y limpia
  temporales (.part, .ytdl, .f*); pausar corta igual pero conserva .part
  para resumir (Pausada entrega los vistos a la cola); el archivo final no
  se toca.
El error de yt-dlp se vuelve ErrorMiauki con código amable (errors.codigo_de).
"""
import gc
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

from miauki import paths
from miauki.core import analyzer, errors, motor, validacion
from miauki.core.errors import ErrorMiauki
from miauki.core.logger import obtener_logger

# Tope de descarga directa (opción "Original", p.ej. Snapchat): 4 GB.
_LIMITE_DIRECTA = 4 * 1024 * 1024 * 1024
_TIEMPO_DIRECTA = 30
_UA_DIRECTA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
               "AppleWebKit/537.36 (KHTML, like Gecko) "
               "Chrome/140.0.0.0 Safari/537.36")


class Cancelada(Exception):
    """El usuario canceló: no es un error para mostrar, es un estado de cola."""


class Pausada(Exception):
    """El usuario pausó: corta el hilo conservando .part para resumir.

    `vistos` son los nombres que pasó yt-dlp: la cola los guarda y si el
    usuario cancela desde la pausa, limpia con `limpiar(vistos)` (decisión
    3d.8).
    """

    def __init__(self, vistos):
        self.vistos = list(vistos)
        super().__init__("pausada")


class _Tope:
    """Progreso monótono a ~4 ev/s (decisión 3d.5).

    El porcentaje nunca baja: si yt-dlp reporta menos que lo ya visto
    (descarga en partes, reintentos), se mantiene el máximo alcanzado.
    """

    def __init__(self, callback, reloj=time.monotonic, espera=0.25):
        self._cb = callback
        self._reloj = reloj
        self._espera = espera
        self._ultimo = 0.0
        self._pct = -1.0

    def avisar(self, datos: dict, forzar: bool = False) -> bool:
        pct = datos.get("porcentaje")
        if pct is not None:
            if pct < self._pct:
                datos["porcentaje"] = self._pct
            else:
                self._pct = pct
        ahora = self._reloj()
        if not forzar and (ahora - self._ultimo) < self._espera:
            return False
        self._ultimo = ahora
        self._cb(datos)
        return True


def construir_opciones(solicitud, ajustes, carpeta, nombre=None,
                       hook=None, pp_hook=None):
    """Opciones de yt-dlp para un ítem de la cola (todo offline, testeable).

    `solicitud` es el snapshot del encolado (decisión 3d.4): tipo, selector,
    contenedor, kbps, url_canonica, titulo. `con_subs` (si viene en el
    snapshot) manda sobre el ajuste global incluir_subs.
    `nombre` es el nombre base libre elegido (P0.6): el archivo final queda
    exactamente como "nombre.ext", sin depender del título que traiga yt-dlp.
    """
    outtmpl = os.path.join(carpeta,
                           (nombre + ".%(ext)s") if nombre
                           else "%(title).100s.%(ext)s")
    opciones = dict(analyzer._opciones_ajustes(ajustes, solicitud.get("url_canonica")))
    opciones.update({
        "noprogress": True,
        "outtmpl": outtmpl,
        "format": solicitud.get("selector") or "best",
        "retries": 3,
        "fragment_retries": 3,
        "ffmpeg_location": str(paths.ruta_ffmpeg()),
    })
    if solicitud.get("tipo") == "musica":
        opciones["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": str(solicitud.get("kbps") or 0),
        }]
    elif solicitud.get("contenedor"):
        opciones["merge_output_format"] = solicitud["contenedor"]
    if hook:
        opciones["progress_hooks"] = [hook]
    if pp_hook:
        opciones["postprocessor_hooks"] = [pp_hook]
    return opciones


def _elegir_subs(info, preferido):
    """Elige UN idioma de subtítulos: el de los ajustes y, si no está, el
    otro (es/en). Devuelve (idioma, automatico) o (None, False) si no hay
    ninguno de los dos. Los manuales tienen prioridad sobre los automáticos.
    """
    manuales = set((info or {}).get("subtitles") or {})
    automaticos = set((info or {}).get("automatic_captions") or {})
    orden = []
    for code in (preferido or "es", "es", "en"):
        if code and code not in orden:
            orden.append(code)
    for code in orden:
        if code in manuales:
            return code, False
    for code in orden:
        if code in automaticos:
            return code, True
    return None, False


def opciones_subs(carpeta, ajustes, idioma, automatico=False, nombre=None):
    """Segunda pasada de UN solo subtítulo: best-effort, nunca rompe la descarga.

    Receta de la v2.6 (engine.subtitle_opts): skip_download + ignoreerrors.
    Se pide un único idioma (decisión: un solo .srt); si es automático se
    usa writeautomaticsub, si no writesubtitles.
    """
    opciones = dict(analyzer._opciones_ajustes(ajustes))
    opciones.update({
        "noprogress": True,
        "outtmpl": os.path.join(
            carpeta, ((nombre + ".%(ext)s") if nombre
                      else "%(title).100s.%(ext)s")),
        "skip_download": True,
        "ignoreerrors": True,
        "writesubtitles": not automatico,
        "writeautomaticsub": automatico,
        "subtitleslangs": [idioma],
        "subtitlesformat": "srt/best",
    })
    return opciones


def _ruta_final(info, ydl) -> str:
    """La ruta real del archivo ya postprocesado (mp4/mkv/mp3)."""
    pedidos = (info or {}).get("requested_downloads") or []
    if pedidos and pedidos[0].get("filepath"):
        return pedidos[0]["filepath"]
    if info:
        try:
            ruta = ydl.prepare_filename(info)
            if ruta:
                return ruta
        except Exception:
            pass
    raise ErrorMiauki("error_desconocido")


def limpiar(vistos) -> None:
    """Borra parciales (.part, .ytdl, .f*) de los nombres que pasó yt-dlp.

    El archivo final NO entra acá: solo los temporales. Reintenta poco porque
    los hilos de yt-dlp a veces dejan el archivo abierto (receta v2.6).
    """
    for nombre in vistos:
        base = Path(nombre)
        stem = base.with_suffix("")
        candidatos = {base, Path(str(base) + ".part"),
                      Path(str(base) + ".ytdl")}
        directorio = base.parent
        candidatos.update(directorio.glob(stem.name + ".f*"))
        candidatos.update(directorio.glob(stem.name + "*.part"))
        for ruta in candidatos:
            try:
                ruta.unlink()
            except OSError:
                pass


def limpiar_parciales(vistos) -> None:
    """Borra SOLO temporales exactos de los nombres que pasó yt-dlp (F6 B3).

    A diferencia de `limpiar`, nunca toca el nombre base: si el archivo llegó
    a completarse antes del cierre brusco, se conserva. Se usa al arrancar
    para los ítems interrumpidos, con nombres que el propio yt-dlp reportó.
    """
    for nombre in vistos:
        base = Path(nombre)
        for sufijo in (".part", ".ytdl", ".temp"):
            try:
                Path(str(base) + sufijo).unlink()
            except OSError:
                pass


def limpiar_restos_del_final(ruta) -> None:
    """Borra parciales hermanos del archivo final ya terminado (defensa).

    Si alguna vez quedó un .part/.ytdl/.temp o un fragmento (.fNNN) del
    mismo nombre base (p.ej. de un intento anterior con otro nombre), se
    elimina para que no ocupe espacio ni confunda al usuario. Nunca toca el
    archivo final ni los subtítulos.
    """
    try:
        final = Path(ruta)
        for candidato in final.parent.iterdir():
            if candidato == final:
                continue
            nombre = candidato.name.lower()
            if not nombre.startswith(final.stem.lower() + "."):
                continue
            if (candidato.suffix.lower() in (".part", ".ytdl", ".temp")
                    or re.search(r"\.f\d+\.", nombre)):
                try:
                    candidato.unlink()
                except OSError:
                    pass
    except OSError:
        pass


def _selector_reanalizado(solicitud, ajustes):
    """Reanaliza el link y devuelve un selector nuevo por altura (P0.5).

    Silencioso (solo log): sirve de red de seguridad cuando el formato pedido
    ya no existe (IDs efímeros de Facebook). Devuelve None si no hay con qué.
    """
    try:
        res = analyzer.analizar(solicitud.get("url_canonica") or "",
                                forzar=True)
    except Exception:
        obtener_logger().info("Reanálisis silencioso sin éxito", exc_info=True)
        return None
    tipo = solicitud.get("tipo")
    if tipo == "musica":
        return "bestaudio"
    if tipo != "video":
        return None
    calidades = res.get("calidades") or []
    if not calidades:
        return None
    altura = solicitud.get("resolucion")
    elegida = None
    if isinstance(altura, int):
        iguales = [c for c in calidades if c.get("resolucion") == altura]
        if iguales:
            elegida = iguales[0]
        else:
            menores = [c for c in calidades
                       if (c.get("resolucion") or 0) <= altura]
            if menores:
                elegida = max(menores, key=lambda c: c.get("resolucion") or 0)
    if elegida is None:
        elegida = next((c for c in calidades if c.get("recomendada")),
                       calidades[0])
    return elegida.get("selector")


def _extraer_con_respaldo(solicitud, ajustes, opciones, url, ydl_ctor,
                          cancelar=None):
    """Extrae+descarga. Si yt-dlp dice que la calidad ya no existe (IDs
    efímeros, típico de Facebook), reanaliza en silencio y reintenta UNA vez
    con un selector nuevo por altura (P0.5). Si YouTube pide confirmar que no
    sos un robot, reintenta 2 veces (tanda 20/11/2026, paso 5).
    Devuelve (info, ydl)."""
    intentos = 0
    intentos_bot = 0
    paciente = 0
    while True:
        try:
            analyzer.cliente_youtube(opciones, intentos_bot + paciente)
            ydl = ydl_ctor(opciones)
            with ydl:
                info = ydl.extract_info(url, download=True)
            return info, ydl
        except (Cancelada, Pausada):
            raise
        except Exception as exc:
            codigo = errors.codigo_de(str(exc))
            if codigo == "youtube_verificacion_bot":
                if intentos_bot < 2:
                    intentos_bot += 1
                    time.sleep(errors.ESPERA_BOT)
                    if cancelar is not None and cancelar.is_set():
                        raise Cancelada()
                    continue
                # Segundo nivel (paso 3): espera creciente antes de rendirse.
                if paciente < len(errors.ESPERAS_PACIENTES):
                    time.sleep(errors.ESPERAS_PACIENTES[paciente])
                    paciente += 1
                    if cancelar is not None and cancelar.is_set():
                        raise Cancelada()
                    continue
            if (intentos == 0
                    and codigo == "calidad_no_disponible"):
                selector = _selector_reanalizado(solicitud, ajustes)
                if selector and selector != opciones.get("format"):
                    opciones["format"] = selector
                    intentos = 1
                    continue
            # Ajustes 21/11: en YouTube un "eliminado" puede ser pasajero
            # (página de verificación o error transitorio mal clasificado):
            # se reintenta UNA vez de inmediato antes de declararlo eliminado.
            if (codigo == "video_eliminado" and intentos == 0
                    and "youtube.com" in (solicitud.get("url_canonica") or "")):
                intentos = 1
                continue
            raise


def _descargar_directa(url, carpeta, nombre, progreso=None, cancelar=None):
    """Baja una URL directa a disco (opción "Original" de Snapchat).

    yt-dlp rechaza el formato de Snapchat por su extensión rara (IRZXSOY),
    pero la URL responde video/mp4. Esta vía descarga con urllib, con límite
    de tamaño, timeout y sin seguir redirecciones a otros hosts.
    Devuelve la ruta del archivo final (.mp4).
    """
    if not url.lower().startswith(("http://", "https://")):
        raise ErrorMiauki("link_invalido")
    ruta = os.path.join(carpeta, nombre + ".mp4")
    parcial = ruta + ".part"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": _UA_DIRECTA})
        with urllib.request.urlopen(req, timeout=_TIEMPO_DIRECTA) as resp, \
                open(parcial, "wb") as f:
            bajado = 0
            while True:
                if cancelar is not None and cancelar.is_set():
                    raise Cancelada()
                trozo = resp.read(1024 * 256)
                if not trozo:
                    break
                f.write(trozo)
                bajado += len(trozo)
                if bajado > _LIMITE_DIRECTA:
                    raise ErrorMiauki("error_desconocido")
                if progreso:
                    progreso({"fase": "descarga", "porcentaje": None,
                             "descargado": bajado, "total": None,
                             "velocidad": None, "restante": None})
        os.replace(parcial, ruta)
    except Cancelada:
        try:
            os.remove(parcial)
        except OSError:
            pass
        raise
    except urllib.error.URLError:
        try:
            os.remove(parcial)
        except OSError:
            pass
        raise ErrorMiauki("error_desconocido") from None
    except OSError:
        try:
            os.remove(parcial)
        except OSError:
            pass
        raise ErrorMiauki("error_desconocido") from None
    return {"ruta": ruta}


def descargar(solicitud, ajustes, progreso=None, cancelar=None, pausar=None,
              ydl_ctor=None):
    """Descarga un ítem del snapshot. Devuelve {"ruta": <archivo final>}.

    - `progreso(datos)`: llama como máximo ~4 veces por segundo con
      {fase: "descarga"|"proceso", porcentaje (monótono), descargado,
      total, velocidad, restante}.
    - `cancelar`: threading.Event; al estar encendida el hook lanza Cancelada,
      yt-dlp corta y se limpian los temporales.
    - `pausar`: threading.Event; corta igual que cancelar pero lanza Pausada
      SIN limpiar (.part queda para resumir con continuedl); cancelar tiene
      prioridad si las dos están encendidas.
    - Lanza ErrorMiauki (mensaje amable), Cancelada o Pausada. Sin red en
      los tests: ydl_ctor inyecta el YoutubeDL falso.
    """
    if ydl_ctor is None:
        ydl_ctor = motor.ytdlp().YoutubeDL

    carpeta = ajustes.get("carpeta_descargas") or str(Path.home() / "Downloads")
    # Playlists: el archivo usa el título real, sin el prefijo [Bloque X/Y].
    base = validacion.nombre_base_libre(
        carpeta, solicitud.get("_titulo_real") or solicitud.get("titulo"))
    tope = _Tope(progreso) if progreso else None
    vistos: list[str] = []

    # Paso 3: opción "Original" (p.ej. Snapchat) — yt-dlp rechaza el formato
    # por extensión rara; se baja la URL directa sin pasar por él.
    if solicitud.get("url_directa"):
        return _descargar_directa(
            solicitud["url_directa"], carpeta, base,
            progreso=(tope.avisar if tope else None), cancelar=cancelar)

    def _cortar():
        if cancelar is not None and cancelar.is_set():
            raise Cancelada()
        if pausar is not None and pausar.is_set():
            raise Pausada(vistos)

    def hook(datos):
        nombre = datos.get("filename")
        if nombre and nombre not in vistos:
            vistos.append(nombre)
        _cortar()
        if tope is None:
            return
        estado = datos.get("status")
        descargado = datos.get("downloaded_bytes")
        total = datos.get("total_bytes") or datos.get("total_bytes_estimate")
        if estado == "finished":
            tope.avisar({"fase": "descarga", "porcentaje": 100.0,
                         "descargado": descargado, "total": total,
                         "velocidad": None, "restante": None,
                         "parcial": nombre}, forzar=True)
        elif estado == "downloading":
            pct = None
            if descargado and total:
                pct = descargado * 100.0 / total
            tope.avisar({"fase": "descarga", "porcentaje": pct,
                         "descargado": descargado or 0, "total": total,
                         "velocidad": datos.get("speed"),
                         "restante": datos.get("eta"),
                         "parcial": nombre})

    def pp_hook(datos):
        _cortar()
        if datos.get("status") == "started" and tope is not None:
            tope.avisar({"fase": "proceso", "porcentaje": None,
                         "descargado": None, "total": None,
                         "velocidad": None, "restante": None}, forzar=True)

    opciones = construir_opciones(solicitud, ajustes, carpeta, nombre=base,
                                  hook=hook, pp_hook=pp_hook)
    url = solicitud.get("url_canonica") or ""
    try:
        info, ydl = _extraer_con_respaldo(solicitud, ajustes, opciones, url,
                                          ydl_ctor, cancelar=cancelar)
        ruta = _ruta_final(info, ydl)
        if not validacion.dentro_de(ruta, carpeta):
            # defensa en profundidad: yt-dlp ya sanitiza el título, pero el
            # archivo final nunca debe salir de la carpeta elegida (P0.7).
            raise ErrorMiauki("entrada_invalida")
        if not os.path.basename(ruta).lower().startswith(base.lower()):
            # el posproceso puede cambiar la extensión; si además cambió el
            # nombre, avisamos (P0.6): puede pisar algo que no previmos.
            obtener_logger().warning("yt-dlp cambió el nombre final: %s", ruta)
        # La cancelación puede llegar durante el postproceso (ffmpeg merge /
        # mp3), donde yt-dlp no vuelve a llamar hooks: se verifica acá, ya
        # con la ruta final, para que cancelar funcione de verdad (tera de
        # Maki, 20/11 #2).
        if cancelar is not None and cancelar.is_set():
            try:
                os.remove(ruta)
            except OSError:
                pass
            raise Cancelada()
        con_subs = (solicitud.get("tipo") == "video"
                    and solicitud.get("con_subs",
                                      ajustes.get("incluir_subs")))
        if con_subs and (cancelar is None or not cancelar.is_set()):
            idioma, automatico = _elegir_subs(info, ajustes.get("idioma_subs"))
            if idioma:
                try:
                    opciones_s = opciones_subs(carpeta, ajustes, idioma,
                                               automatico=automatico,
                                               nombre=base)
                    with ydl_ctor(opciones_s) as ydl2:
                        ydl2.extract_info(url, download=True)
                except (Cancelada, Pausada):
                    raise
                except Exception:
                    obtener_logger().warning(
                        "No se pudieron bajar los subtítulos de %s",
                        errors.sin_query(url), exc_info=True)
        # Limpieza defensiva: si quedó algún parcial/fragmento del mismo nombre
        # base (de un intento anterior), se borra (ajustes 21/11).
        limpiar_restos_del_final(ruta)
        return {"ruta": ruta}
    except Cancelada as exc:
        # el traceback de la excepción mantiene vivos los frames de yt-dlp
        # (y el .part abierto): sin cortarlo Windows no deja borrar nada
        # (WinError 32, visto en vivo en B6)
        exc.__traceback__ = None
        gc.collect()
        limpiar(vistos)
        raise
    except Pausada as exc:
        exc.__traceback__ = None
        gc.collect()
        raise
    except ErrorMiauki:
        raise
    except Exception as exc:
        limpiar(vistos)
        codigo = errors.codigo_de(str(exc))
        obtener_logger().exception("Descarga fallida (%s): %s", codigo,
                                   errors.sin_query(url))
        raise ErrorMiauki(codigo) from None

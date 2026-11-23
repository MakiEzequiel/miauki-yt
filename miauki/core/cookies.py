# -*- coding: utf-8 -*-
"""Cookies: archivo Netscape propio o las del navegador (Fase 9, B2 y B2b).

Un solo lugar decide qué cookies se le pasan a yt-dlp (análisis y descarga) y
cuáles se leen para las vías de imágenes de X. Reglas:

- si hay archivo elegido, gana el archivo; si no, el navegador; si no, ninguno;
- del archivo se guarda **solo la ruta** en los ajustes, nunca una copia;
- los valores de las cookies no se escriben en logs, diagnóstico ni tests.

El formato Netscape (el que exporta cualquier extensión) se valida con
`http.cookiejar` de la biblioteca estándar. Además se aceptan exportaciones
en JSON (muchas extensiones y gestores las entregan así): sin dependencias
nuevas.
"""
import http.cookiejar
import json
import os

from miauki.core.errors import ErrorMiauki

# Un cookies.txt real pesa pocos KB; el tope evita leer un archivo enorme por error.
ARCHIVO_MAX = 5 * 1024 * 1024
ARCHIVO_MIN = 16  # una cabecera sola no sirve como archivo de cookies

_DOMINIOS_X = ("x.com", "twitter.com")

_EXTENSIONES_JSON = (".json", ".jsonz")


def archivo_valido(ruta) -> str:
    """Ruta absoluta de un archivo de cookies usable (Netscape .txt/.cookies
    o JSON exportado), o `ErrorMiauki`."""
    if not isinstance(ruta, str) or not ruta.strip():
        raise ErrorMiauki("cookies_archivo_faltante")
    ruta = os.path.abspath(ruta)
    if not os.path.isfile(ruta):
        raise ErrorMiauki("cookies_archivo_faltante")
    try:
        tamano = os.path.getsize(ruta)
    except OSError:
        raise ErrorMiauki("cookies_archivo_faltante") from None
    if tamano < ARCHIVO_MIN or tamano > ARCHIVO_MAX:
        raise ErrorMiauki("cookies_archivo_invalido")
    if ruta.lower().endswith(_EXTENSIONES_JSON):
        if not _es_json_cookies(ruta):
            raise ErrorMiauki("cookies_archivo_invalido")
    elif not _es_netscape(ruta):
        raise ErrorMiauki("cookies_archivo_invalido")
    return ruta


def _es_netscape(ruta: str) -> bool:
    """¿Tiene cookies en formato Netscape? La cabecera es obligatoria.

    yt-dlp exige que la primera línea sea `# HTTP Cookie File` o
    `# Netscape HTTP Cookie File` (FAQ oficial, "How do I pass cookies to
    yt-dlp"), así que se valida con el mismo criterio: si el archivo no sirve
    acá, tampoco serviría en el motor.
    """
    try:
        jarra = http.cookiejar.MozillaCookieJar(ruta)
        jarra.load(ignore_discard=True, ignore_expires=True)
        return len(jarra) > 0
    except (http.cookiejar.LoadError, OSError):
        return False


def _es_json_cookies(ruta: str) -> bool:
    """¿Es un JSON con al menos una cookie aprovechable?"""
    try:
        return len(_leer_jarra_json(ruta)) > 0
    except Exception:
        return False


def _leer_jarra_json(ruta: str) -> http.cookiejar.MozillaCookieJar:
    """Construye una jarra a partir de un JSON exportado (varios formatos)."""
    with open(ruta, encoding="utf-8") as f:
        datos = json.load(f)
    filas = datos
    if isinstance(datos, dict):
        # Formatos comunes: {"cookies": [...]} o similar.
        for clave in ("cookies", "cookie", "items", "data"):
            if isinstance(datos.get(clave), list):
                filas = datos[clave]
                break
    if not isinstance(filas, list):
        raise ValueError("JSON de cookies sin lista")
    jarra = http.cookiejar.MozillaCookieJar()
    for fila in filas:
        if not isinstance(fila, dict):
            continue
        nombre = fila.get("name") or fila.get("nombre")
        valor = fila.get("value") or fila.get("valor")
        dominio = fila.get("domain") or fila.get("dominio")
        if not nombre or valor is None or not dominio:
            continue
        camino = fila.get("path") or "/"
        expira = fila.get("expires") or fila.get("expirationDate") or fila.get("expiry")
        try:
            expira = int(expira) if expira else None
        except (TypeError, ValueError):
            expira = None
        if expira is not None and expira <= 0:
            continue  # cookie expirada
        segura = bool(fila.get("secure"))
        dominio_sin_punto = str(dominio).lstrip(".")
        jarra.set_cookie(http.cookiejar.Cookie(
            version=0, name=str(nombre), value=str(valor),
            port=None, port_specified=False,
            domain=dominio_sin_punto, domain_specified=True,
            domain_initial_dot=str(dominio).startswith("."),
            path=str(camino), path_specified=True,
            secure=segura, expires=expira, discard=True,
            comment=None, comment_url=None, rest={}, rfc2109=False,
        ))
    return jarra


def _leer_jarra(ruta: str) -> http.cookiejar.MozillaCookieJar:
    """Jarra con las cookies del archivo (Netscape o JSON)."""
    if ruta.lower().endswith(_EXTENSIONES_JSON):
        return _leer_jarra_json(ruta)
    jarra = http.cookiejar.MozillaCookieJar(ruta)
    jarra.load(ignore_discard=True, ignore_expires=True)
    return jarra


def _a_netscape_temporal(jarra: http.cookiejar.MozillaCookieJar) -> str:
    """Convierte la jarra a un archivo Netscape temporal (para yt-dlp)."""
    import tempfile
    fd, ruta = tempfile.mkstemp(prefix="miauki-cookies-", suffix=".txt")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write("# Netscape HTTP Cookie File\n")
        for c in jarra:
            expira = int(c.expires) if c.expires else 0
            dominio = c.domain or ""
            if c.domain_initial_dot and not dominio.startswith("."):
                dominio = "." + dominio
            f.write("\t".join([
                dominio, "TRUE", c.path or "/",
                "TRUE" if c.secure else "FALSE",
                str(expira), c.name, c.value,
            ]) + "\n")
    return ruta


def opciones(ajustes: dict) -> dict:
    """Opciones de yt-dlp con las cookies elegidas (archivo o navegador)."""
    ajustes = ajustes or {}
    if ajustes.get("archivo_cookies"):
        # Se valida en el momento: una ruta vieja (archivo borrado o cambiado)
        # da un error amable en vez de un "pide iniciar sesión" sin explicación.
        ruta = archivo_valido(ajustes["archivo_cookies"])
        if ruta.lower().endswith(_EXTENSIONES_JSON):
            # yt-dlp no lee JSON: se convierte a Netscape temporal.
            return {"cookiefile": _a_netscape_temporal(_leer_jarra(ruta))}
        return {"cookiefile": ruta}
    navegador = ajustes.get("navegador_cookies") or "ninguno"
    if navegador != "ninguno":
        return {"cookiesfrombrowser": (navegador,)}
    return {}


def para_x(ajustes: dict) -> tuple[str | None, str | None, str | None]:
    """(cookie, csrf, error amable) con **solo** las cookies de x.com/twitter.com.

    Se leen en memoria y no se guardan en ningún lado.
    """
    partes, error = para_dominio(ajustes, _DOMINIOS_X)
    if error:
        return None, None, error
    if not partes:
        return None, None, None
    csrf = None
    for galleta in partes:
        if galleta[0] == "ct0":
            csrf = galleta[1]
    return "; ".join("%s=%s" % g for g in partes), csrf, None


def para_dominio(ajustes: dict, dominios: tuple) -> tuple[list, str | None]:
    """(pares (nombre, valor) de cookies, error amable) para los dominios dados.

    Reutilizable para vías de imagen de Instagram/Facebook: lee las cookies
    elegidas (archivo o navegador) y filtra por dominio. Se leen en memoria
    y no se guardan en ningún lado.
    """
    try:
        elegidas = opciones(ajustes)
    except ErrorMiauki as exc:
        return [], exc.mensaje
    if not elegidas:
        return [], None
    if "cookiefile" in elegidas or "cookiejar" in elegidas:
        origen = "el archivo de cookies"
    else:
        origen = "el navegador %s" % elegidas["cookiesfrombrowser"][0].capitalize()
    try:
        from miauki.core import motor

        class _Silencioso:
            def debug(self, *a): pass
            def info(self, *a): pass
            def warning(self, *a): pass
            def error(self, *a): pass

        with motor.ytdlp().YoutubeDL({"quiet": True, "no_warnings": True,
                                      "logger": _Silencioso(),
                                      **elegidas}) as ydl:
            partes = []
            for galleta in ydl.cookiejar:
                dominio = (galleta.domain or "").lstrip(".").lower()
                if not any(dominio == d or dominio.endswith("." + d)
                           for d in dominios):
                    continue
                partes.append((galleta.name, galleta.value))
    except Exception:
        return [], ("no pude leer las cookies en %s: probá con Firefox "
                    "o con un archivo de cookies" % origen)
    return partes, None

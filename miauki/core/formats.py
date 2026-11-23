# -*- coding: utf-8 -*-
"""Lógica de calidades y formatos (chips video/audio/imagen)."""
ESCALA = [2160, 1440, 1080, 720, 480, 360, 240]
TOPE_8K = 8192


def calidades_recomendadas(max_res):
    """Las 3 tarjetas del selector, según decisión Maki 08/11/2026.

    - La mejor: la resolución más alta del video, con tope 8K (8192).
    - Equilibrada: 1080p (siempre se intenta).
    - Liviana: 480p (siempre se intenta).
    Si dos recomendaciones caen en la misma resolución se muestra una sola.
    El fallback a la altura real más cercana inferior lo resuelve analyzer._calidades().
    """
    if not max_res or max_res <= 0:
        return []
    opciones = [min(max_res, TOPE_8K), 1080, 480]
    vistas = set()
    salida = []
    for r in opciones:
        if r not in vistas:
            vistas.add(r)
            salida.append("%dp" % r)
    return salida


def contenedor_de(vcodec: str, acodec: str) -> str:
    """Contenedor para una opción de video (spec §4).

    mp4 si los códecs son compatibles: H.264 (avc1...) con AAC (mp4a...)
    o sin audio. Cualquier otro caso (VP9, AV1, Opus...) va a mkv, que los
    acepta todos sin re-codificar.
    """
    vc = (vcodec or "none").split(".")[0]
    ac = (acodec or "none").split(".")[0]
    video_ok = vc in {"avc1", "none"}
    audio_ok = ac in {"mp4a", "aac", "none"}
    return "mp4" if video_ok and audio_ok else "mkv"

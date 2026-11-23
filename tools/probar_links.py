# -*- coding: utf-8 -*-
"""Prueba manual con links reales: analiza y arma una tabla (spec §8, A2).

Usa la MISMA vía que usaría la interfaz (Api.analizar) para los 6 links de
Maki. Por cada uno mide el tiempo y guarda en una carpeta TEMPORAL fuera
del repo (A2):

    linkNN_crudo.json      respuesta cruda de yt-dlp (info dict o el error)
    linkNN_resultado.json  nuestro contrato {ok, data|error}
    tabla.txt              la tabla resumen

De esos archivos salen las fixtures de B8, revisadas y limpiadas a mano
(sin cookies/tokens/IDs de usuario/IPs/URLs firmadas) antes del commit.

Uso (desde la raíz del proyecto):
    python tools/probar_links.py           # los 6 links
    python tools/probar_links.py 2 5       # solo esos
"""
import json
import sys
import tempfile
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
import _entorno  # noqa: E402  (carpeta de datos temporal, nunca la real)

from miauki.api import Api  # noqa: E402
from miauki.core import analyzer  # noqa: E402

SALIDA = Path(tempfile.gettempdir()) / "miauki_probar_links"

# Los 6 de la spec §8. Esperado = lo que dijo Maki en la spec.
LINKS = [
    (1, "https://www.tiktok.com/es/",
     "portada, NO video → error 'ese link no es de un video'"),
    (2, "https://www.youtube.com/watch?v=pCPYb7KPoUc&list=RDpCPYb7KPoUc&index=1",
     "UN solo video (ignorar la lista)"),
    (3, "https://www.instagram.com/reel/Def341BAmx8/",
     "reel → análisis OK (la query ?obrf=... venía truncada en la spec)"),
    (4, "https://www.facebook.com/share/r/1PonqKC4oQ/",
     "link corto compartido → resolver y analizar"),
    (5, "https://x.com/StereoHodler/status/2110183275461513256/photo/1",
     "post de X con foto → imagen (o video+foto según la vía)"),
    (6, "https://www.facebook.com/photo/?fbid=1111696508036243",
     "foto con fbid → imagen"),
]

_CRUDO: list = []


def _instalar_guardador():
    """Guarda la respuesta cruda de yt-dlp mientras Api.analizar trabaja."""
    original = analyzer._extraer

    def guardando(url, ajustes):
        try:
            info = original(url, ajustes)
        except Exception as exc:
            _CRUDO.append({"url": url, "error": str(exc)})
            raise
        _CRUDO.append({"url": url, "info": info})
        return info

    analyzer._extraer = guardando
    return original


def _jsonable(obj):
    return json.loads(json.dumps(obj, ensure_ascii=False, default=str))


def _guardar(nombre: str, datos) -> Path:
    ruta = SALIDA / nombre
    ruta.write_text(json.dumps(_jsonable(datos), ensure_ascii=False,
                               indent=1, default=str),
                    encoding="utf-8")
    return ruta


def _fila(n: int, r: dict, crudo: dict | None, segundos: float) -> str:
    if r["ok"]:
        d = r["data"]
        cal = d.get("calidades") or []
        recomendadas = " ".join(
            "%s(%s)" % (c["etiqueta"], c["recomendada"])
            for c in cal if c.get("recomendada")) or "-"
        n_formatos = (len((crudo or {}).get("info", {}).get("formats") or [])
                      if crudo and crudo.get("info") else "-")
        subs = d.get("subtitulos") or {}
        if subs.get("disponible"):
            texto_subs = "si (%s)" % ",".join((subs.get("idiomas") or [])[:4])
            if any("autom" in a for a in (d.get("advertencias") or [])):
                texto_subs += " autom."
        else:
            texto_subs = "no"
        return ("%-2s %-11s %-6s %-4s %-34s %-8s %-30s %-16s %-4s %5.1fs"
                % (n, d.get("sitio", "-"), d.get("tipo", "-"), "OK",
                   (d.get("titulo") or "")[:34], str(n_formatos),
                   recomendadas, texto_subs, len(d.get("imagenes") or []),
                   segundos))
    e = r.get("error") or {}
    return ("%-2s %-11s %-6s %-4s %-34s %-8s %-30s %-16s %-4s %5.1fs"
            % (n, "-", "-", "ERR", (e.get("codigo") or "?")[:34],
               "-", "-", "-", "-", segundos))


def main(seleccion=None):
    SALIDA.mkdir(parents=True, exist_ok=True)
    original = _instalar_guardador()
    try:
        filas, notas = [], []
        for n, url, esperado in LINKS:
            if seleccion and n not in seleccion:
                continue
            _CRUDO.clear()
            api = Api()
            inicio = time.monotonic()
            r = api.analizar(url)
            segundos = time.monotonic() - inicio
            crudo = _CRUDO[0] if _CRUDO else None
            _guardar("link%02d_crudo.json" % n, crudo or {"sin_respuesta": True})
            _guardar("link%02d_resultado.json" % n, r)
            filas.append(_fila(n, r, crudo, segundos))
            notas.append("link %d — esperado: %s" % (n, esperado))
            if r["ok"]:
                d = r["data"]
                notas.append("         obtenido: %s / %s — %s | vias: %s"
                             % (d["sitio"], d["tipo"], d["titulo"],
                                len(d.get("imagenes") or [])))
                for a in d.get("advertencias") or []:
                    notas.append("         advertencia: %s" % a)
            else:
                e = r["error"]
                notas.append("         ERROR real: [%s] %s"
                             % (e["codigo"], e["mensaje"]))
                if crudo and crudo.get("error"):
                    notas.append("         crudo yt-dlp: %s"
                                 % crudo["error"][:300])
    finally:
        analyzer._extraer = original

    encabezado = ("#  sitio      tipo   est  titulo                          "
                  "formatos recomendadas                  subs             "
                  " imgs  tiempo")
    tabla = [encabezado, "-" * len(encabezado)] + filas + [""] + notas
    texto = "\n".join(tabla)
    (SALIDA / "tabla.txt").write_text(texto + "\n", encoding="utf-8")
    print(texto)
    print("\nRespuestas crudas (temporal, fuera del repo): %s" % SALIDA)


if __name__ == "__main__":
    args = [int(a) for a in sys.argv[1:] if a.isdigit()]
    main(args or None)

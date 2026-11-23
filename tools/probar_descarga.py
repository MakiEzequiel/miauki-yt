# -*- coding: utf-8 -*-
"""Prueba REAL de descarga (Fase 4): link → análisis → archivo en disco.

Uso (necesita red; los tests unitarios NO usan esto):
    python tools/probar_descarga.py <url> [--tipo video|musica|imagen]
                                     [--etiqueta 720p] [--kbps 320]

Imprime una tabla: link (sin query) -> resultado -> archivo + bytes + tiempo.
Código de salida 0 = OK, 1 = error amable.
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _entorno  # noqa: E402  (carpeta de datos temporal, nunca la real)

from miauki.core import analyzer, downloader, errors, settings  # noqa: E402
from miauki.core.errors import ErrorMiauki  # noqa: E402


def _progreso(datos):
    if datos.get("fase") == "proceso":
        print("\r  procesando con ffmpeg...          ", end="", flush=True)
        return
    pct = datos.get("porcentaje")
    if pct is None:
        return
    velocidad = datos.get("velocidad")
    texto = "\r  %5.1f%%" % pct
    if velocidad:
        texto += "  %.1f MB/s" % (velocidad / 1e6)
    print(texto, end="", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Descarga real de prueba")
    parser.add_argument("url")
    parser.add_argument("--tipo", choices=("video", "musica", "imagen"))
    parser.add_argument("--etiqueta", help="etiqueta de calidad, ej: 720p")
    parser.add_argument("--kbps", type=int, default=320)
    parser.add_argument("--carpeta", help="carpeta destino (por defecto, "
                        "la de los ajustes)")
    args = parser.parse_args()

    ajustes = settings.cargar()
    if args.carpeta:
        ajustes["carpeta_descargas"] = args.carpeta
    try:
        info = analyzer.analizar(args.url)
    except ErrorMiauki as exc:
        print("%s\tANALISIS\tERROR\t%s\t%s"
              % (errors.sin_query(args.url), exc.codigo, exc.mensaje))
        return 1

    tipo = args.tipo or info["tipo"]
    solicitud = {"url_canonica": info["url_canonica"], "tipo": tipo,
                 "titulo": info["titulo"], "con_subs": ajustes["incluir_subs"]}
    detalle = tipo
    if tipo == "video":
        calidades = info["calidades"]
        if not calidades:
            print("%s\tVIDEO\tSIN_CALIDADES" % errors.sin_query(args.url))
            return 1
        elegida = None
        if args.etiqueta:
            elegida = next((c for c in calidades
                            if c["etiqueta"] == args.etiqueta), None)
            if elegida is None:
                print("%s\tCALIDAD_NO_DISPONIBLE\t%s"
                      % (errors.sin_query(args.url), args.etiqueta))
                return 1
        else:
            elegida = next((c for c in calidades if c.get("recomendada")),
                           calidades[0])
        solicitud.update({"selector": elegida["selector"],
                          "contenedor": elegida["contenedor"]})
        # Paso 3: opción "Original" (p.ej. Snapchat) — URL directa.
        if elegida.get("url_directa"):
            solicitud["url_directa"] = elegida["url_directa"]
        detalle = "%s %s %s" % (tipo, elegida["etiqueta"],
                                elegida["contenedor"])
    elif tipo == "imagen":
        urls_img = info.get("imagenes_urls") or []
        if not urls_img:
            print("%s\tIMAGEN\tSIN_IMAGEN" % errors.sin_query(args.url))
            return 1
        solicitud["url_canonica"] = urls_img[0]
        detalle = "imagen"
    elif tipo == "musica":
        solicitud.update({"selector": "bestaudio", "kbps": args.kbps})
        detalle = "%s %d kbps mp3" % (tipo, args.kbps)

    inicio = time.time()
    try:
        resultado = downloader.descargar(solicitud, ajustes,
                                         progreso=_progreso)
    except ErrorMiauki as exc:
        print()
        print("%s\tDESCARGA\tERROR\t%s\t%s"
              % (errors.sin_query(args.url), exc.codigo, exc.mensaje))
        return 1

    ruta = Path(resultado["ruta"])
    tiempo = time.time() - inicio
    tamano = ruta.stat().st_size if ruta.is_file() else -1
    print()
    print("%s\tOK\t%s\t%s\t%d bytes\t%.1f s"
          % (errors.sin_query(args.url), detalle, ruta, tamano, tiempo))
    return 0


if __name__ == "__main__":
    sys.exit(main())

# -*- coding: utf-8 -*-
"""Deriva el banner recortado al contenido visible (Fase 2D.1).

El PNG original (este OK 2, 2048x690) tiene margen transparente casi invisible
(alfa <= 10): al escalar para caber en el encabezado, el arte visible quedaría
mucho más chico que su caja. Este script recorta el original al bbox de alfa
> 10 con un margen de seguridad de 20 px (conserva el halo del neón) y guarda
el derivado junto al original. El original NO se toca.

Uso: python tools/crop_banner.py
Idempotente: regenera el derivado desde el original en cada corrida.
"""
from pathlib import Path

from PIL import Image

RAIZ = Path(__file__).resolve().parent.parent
CARPETA = RAIZ / "miauki" / "ui" / "assets" / "img" / "Icos"
ORIGINAL = CARPETA / "Banner neón de Miauki este OK 2.png"
DERIVADO = CARPETA / "Banner neón de Miauki este OK 2 recortado.png"
UMBRAL = 10    # alfa mínima para considerar "contenido visible"
SEGURIDAD = 20  # px de halo alrededor del bbox (el neón se desvanece)


def main() -> None:
    im = Image.open(ORIGINAL).convert("RGBA")
    ancho, alto = im.size
    bbox = im.getchannel("A").point(lambda a: 255 if a > UMBRAL else 0).getbbox()
    if bbox is None:
        raise SystemExit("el banner no tiene contenido visible (alfa > %d)" % UMBRAL)
    izq, arr, der, aba = bbox
    caja = (
        max(0, izq - SEGURIDAD),
        max(0, arr - SEGURIDAD),
        min(ancho, der + SEGURIDAD),
        min(alto, aba + SEGURIDAD),
    )
    recorte = im.crop(caja)
    recorte.save(DERIVADO, optimize=True)
    print("original: %dx%d" % (ancho, alto))
    print("bbox alfa>%d: %s" % (UMBRAL, bbox))
    print("recorte (con %d px de seguridad): %s -> %dx%d"
          % (SEGURIDAD, caja, recorte.width, recorte.height))
    print("guardado:", DERIVADO)


if __name__ == "__main__":
    main()

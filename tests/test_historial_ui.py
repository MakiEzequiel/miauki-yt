# -*- coding: utf-8 -*-
"""Historial: ícono por tipo, sitio amigable con ícono de marca y "otro" nunca.

Fase 7, Parte D3. El resto (filas, acciones, borrar) ya tiene sus tests; acá
queda el contrato de lo que se ve en cada fila.
"""
import apoyo  # noqa: F401  (aísla la carpeta de datos)
import re
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

JS = RAIZ / "miauki" / "ui" / "js" / "app.js"
CSS = RAIZ / "miauki" / "ui" / "css" / "layout.css"
STRINGS = RAIZ / "miauki" / "ui" / "js" / "strings.es.js"
MANIFIESTO = RAIZ / "tools" / "assets_manifest.txt"


class IconoPorTipo(unittest.TestCase):
    def setUp(self):
        self.js = JS.read_text(encoding="utf-8")
        self.css = CSS.read_text(encoding="utf-8")

    def test_hay_un_icono_por_tipo_y_esta_en_el_manifiesto(self):
        manifiesto = MANIFIESTO.read_text(encoding="utf-8")
        for nombre in ("video", "musica", "imagen"):
            self.assertTrue((RAIZ / "miauki" / "ui" / "assets" / "icons"
                             / (nombre + ".svg")).is_file(), nombre)
            self.assertIn("icons/%s.svg" % nombre, manifiesto)
        self.assertIn('if (tipo === "musica") return "musica";', self.js)
        self.assertIn('if (tipo === "imagen") return "imagen";', self.js)
        self.assertIn('return "video";', self.js)

    def test_el_tipo_se_muestra_con_icono_y_texto(self):
        self.assertIn("datoConIcono(tipoIcono(e.tipo)", self.js)
        self.assertIn("function datoConIcono(", self.js)
        self.assertIn(".hist-ico", self.css)


class SitioAmigable(unittest.TestCase):
    def setUp(self):
        self.js = JS.read_text(encoding="utf-8")
        self.strings = STRINGS.read_text(encoding="utf-8")

    def test_otro_nunca_se_muestra(self):
        self.assertIn('sitio && sitio !== "otro"', self.js)
        self.assertIn('e.sitio !== "otro"', self.js)
        self.assertIn('"historial.sitioWeb": "Sitio web"', self.strings)

    def test_sitio_lleva_icono_de_marca(self):
        self.assertIn("datoConIcono(sitio.icono, sitio.texto)", self.js)
        for sitio in ("youtube", "tiktok", "instagram", "facebook", "x", "globo"):
            manifiesto = MANIFIESTO.read_text(encoding="utf-8")
            self.assertIn("icons/%s.svg" % sitio, manifiesto, sitio)

    def test_otro_usa_el_dominio_del_link(self):
        self.assertIn("function dominioDe(url)", self.js)
        self.assertIn("new URL(url).hostname", self.js)


class ScrollbarFina(unittest.TestCase):
    def test_la_lista_tiene_barra_fina_en_chromium(self):
        css = CSS.read_text(encoding="utf-8")
        self.assertIn(".hist-lista::-webkit-scrollbar", css)
        self.assertRegex(css, r"\.hist-lista::-webkit-scrollbar \{\s*width: 8px;")
        self.assertIn("scrollbar-width: thin", css)


if __name__ == "__main__":
    unittest.main()

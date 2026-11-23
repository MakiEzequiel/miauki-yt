# -*- coding: utf-8 -*-
"""Ajustes (D5) y vacío del paso 2 (D5b).

D5: "Guardado." aparece en la tarjeta que se tocó, no al pie de la pantalla.
D5b: el vacío de la tarjeta VIDEO va centrado con el ícono del manifiesto.
"""
import apoyo  # noqa: F401  (aísla la carpeta de datos)
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

JS = RAIZ / "miauki" / "ui" / "js" / "app.js"
CSS = RAIZ / "miauki" / "ui" / "css" / "layout.css"
HTML = RAIZ / "miauki" / "ui" / "index.html"
MANIFIESTO = RAIZ / "tools" / "assets_manifest.txt"


class GuardadoJuntoALaTarjeta(unittest.TestCase):
    def setUp(self):
        self.js = JS.read_text(encoding="utf-8")
        self.css = CSS.read_text(encoding="utf-8")

    def test_el_aviso_se_mueve_a_la_tarjeta_que_se_toco(self):
        self.assertIn("function tarjetaDe(el)", self.js)
        self.assertIn('el.closest(".ajuste")', self.js)
        self.assertIn("tarjeta.appendChild(estado)", self.js)
        # El guardado de cada control y el de la carpeta pasan la tarjeta.
        self.assertIn("tarjetaDe(el));", self.js)
        self.assertIn("tarjetaDe(boton)", self.js)

    def test_sigue_habiendo_una_sola_region_viva(self):
        html = HTML.read_text(encoding="utf-8")
        self.assertEqual(html.count('data-ajuste-estado role="status"'), 1)

    def test_el_aviso_no_mueve_el_layout_y_el_error_va_en_rojo(self):
        self.assertIn(".ajuste > .ajuste-estado {", self.css)
        self.assertIn("position: absolute;", self.css)
        self.assertIn('.ajuste > .ajuste-estado[data-error="si"]', self.css)


class VacioDelPaso2(unittest.TestCase):
    def setUp(self):
        self.html = HTML.read_text(encoding="utf-8")
        self.css = CSS.read_text(encoding="utf-8")

    def test_el_vacio_lleva_icono_del_manifiesto(self):
        self.assertIn('class="video-vacio-ico"', self.html)
        self.assertIn('assets/icons/video.svg#ico-video', self.html)
        self.assertIn("icons/video.svg", MANIFIESTO.read_text(encoding="utf-8"))

    def test_el_vacio_va_centrado(self):
        self.assertIn(".video-vacio-ico {", self.css)
        self.assertIn("flex-direction: column;", self.css)
        self.assertIn("justify-content: center;", self.css)
        self.assertIn("text-align: center;", self.css)
        self.assertIn('.video-zona[data-estado-video="vacio"] .video-vacio {\n  display: flex;',
                      self.css)


if __name__ == "__main__":
    unittest.main()

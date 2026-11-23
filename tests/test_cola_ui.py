# -*- coding: utf-8 -*-
"""Cola (Parte D4): ícono y color por estado, barra indeterminada, "Guardar en".

El resto de la Cola (acciones, conteo, foco) ya tiene sus tests; acá queda el
contrato de lo visual que la spec pide en la Fase 7.
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
HTML = RAIZ / "miauki" / "ui" / "index.html"
TOKENS = RAIZ / "miauki" / "ui" / "css" / "tokens.css"
STRINGS = RAIZ / "miauki" / "ui" / "js" / "strings.es.js"
MANIFIESTO = RAIZ / "tools" / "assets_manifest.txt"


class IconoYColorPorEstado(unittest.TestCase):
    def setUp(self):
        self.js = JS.read_text(encoding="utf-8")
        self.css = CSS.read_text(encoding="utf-8")
        self.manifiesto = MANIFIESTO.read_text(encoding="utf-8")

    def test_cada_estado_tiene_su_icono_y_el_archivo_existe(self):
        bloque = re.search(r"var ESTADO_ICONO = \{(.*?)\};", self.js, re.S)
        self.assertIsNotNone(bloque)
        pares = re.findall(r'(\w+): "(\w+)"', bloque.group(1))
        self.assertGreaterEqual(len(pares), 7)
        for estado, nombre in pares:
            with self.subTest(estado=estado):
                self.assertTrue((RAIZ / "miauki" / "ui" / "assets" / "icons"
                                 / (nombre + ".svg")).is_file(), nombre)
                self.assertIn("icons/%s.svg" % nombre, self.manifiesto)

    def test_el_estado_muestra_icono_y_texto(self):
        self.assertIn("cuerpo.appendChild(filaEstado(item));", self.js)
        self.assertIn('estado.appendChild(icono(ESTADO_ICONO[item.estado]', self.js)
        self.assertIn('texto.textContent = etiquetaEstado(item.estado);', self.js)

    def test_terminada_usa_el_verde_neon_y_error_el_rojo_de_texto(self):
        self.assertIn(
            '.cola-item[data-estado="terminada"] .cola-estado {\n  color: var(--exito);',
            self.css)
        self.assertIn(
            '.cola-item[data-estado="error"] .cola-estado,\n'
            '.cola-item[data-estado="interrumpida"] .cola-estado {\n'
            '  color: var(--error-texto);', self.css)
        tokens = TOKENS.read_text(encoding="utf-8")
        self.assertIn("--exito: #39ff14;", tokens)
        self.assertIn("--error-texto: #ff6b6b;", tokens)

    def test_el_verde_y_el_rojo_llegan_a_aa_sobre_la_tarjeta(self):
        """4,5:1 mínimo (AA) contra el pixel más claro de la fila: rgb(32,14,86)."""
        def canal(v):
            v = v / 255
            return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4

        def luz(rgb):
            return (0.2126 * canal(rgb[0]) + 0.7152 * canal(rgb[1])
                    + 0.0722 * canal(rgb[2]))

        def contraste(a, b):
            la, lb = luz(a), luz(b)
            return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)

        fondo = (32, 14, 86)
        for nombre, rgb in (("exito", (0x39, 0xFF, 0x14)),
                            ("error-texto", (0xFF, 0x6B, 0x6B))):
            with self.subTest(color=nombre):
                self.assertGreaterEqual(contraste(rgb, fondo), 4.5)


class BarraIndeterminada(unittest.TestCase):
    def setUp(self):
        self.js = JS.read_text(encoding="utf-8")
        self.css = CSS.read_text(encoding="utf-8")

    def test_sin_porcentaje_la_barra_es_indeterminada(self):
        self.assertIn("function esIndeterminada(p)", self.js)
        self.assertIn('p.fase !== "proceso" && typeof p.porcentaje !== "number"',
                      self.js)
        self.assertIn('barra.setAttribute("data-indeterminada", "si")', self.js)
        self.assertIn("barra.removeAttribute(\"data-indeterminada\")", self.js)

    def test_el_css_anima_la_indeterminada_y_respeta_reducir_efectos(self):
        self.assertIn('.cola-barra[data-indeterminada="si"] .cola-barra-fill', self.css)
        self.assertIn("@keyframes cola-indeterminada", self.css)
        self.assertIn("animation: none;", self.css)
        self.assertIn("prefers-reduced-motion: reduce", self.css)


class GuardarEn(unittest.TestCase):
    def test_el_rotulo_y_el_globo_con_la_ruta_completa(self):
        html = HTML.read_text(encoding="utf-8")
        self.assertIn('class="col-rotulo" data-str="col.guardarEn"', html)
        self.assertIn('class="col-ruta" data-tooltip tabindex="0"', html)
        self.assertIn('"col.guardarEn": "Guardar en"',
                      STRINGS.read_text(encoding="utf-8"))
        self.assertIn('el.setAttribute("data-tooltip", ruta);', JS.read_text(encoding="utf-8"))

    def test_el_lema_no_se_corta_a_1200(self):
        css = CSS.read_text(encoding="utf-8")
        bloque = css[css.find("@media (max-width: 1279px)"):]
        bloque = bloque[:bloque.find("}\n\n")]
        self.assertIn("--fs-col-frase: 1.125rem;", bloque)


if __name__ == "__main__":
    unittest.main()

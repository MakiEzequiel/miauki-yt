# -*- coding: utf-8 -*-
"""Recorrido guiado "Así de fácil se usa" (Fase 7, C).

Los 8 pasos, sus textos y que cada cosa que señalan exista de verdad en la
interfaz. El comportamiento en vivo (primera vez, saltar, repetir, foco) se
probó en ventana real; acá queda el contrato que no queremos romper sin darnos
cuenta.
"""
import apoyo  # noqa: F401  (aísla la carpeta de datos)
import re
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from miauki.core import settings  # noqa: E402

HTML = RAIZ / "miauki" / "ui" / "index.html"
APP = RAIZ / "miauki" / "ui" / "js" / "app.js"
STRINGS = RAIZ / "miauki" / "ui" / "js" / "strings.es.js"


class Contrato(unittest.TestCase):
    def setUp(self):
        self.html = HTML.read_text(encoding="utf-8")
        self.app = APP.read_text(encoding="utf-8")
        self.strings = STRINGS.read_text(encoding="utf-8")

    def test_el_ajuste_arranca_apagado(self):
        """Primera vez: recorrido_visto en False (se muestra una vez)."""
        self.assertIs(settings.predeterminados()["recorrido_visto"], False)

    def test_es_un_dialogo_modal(self):
        self.assertIn('data-recorrido hidden role="dialog" aria-modal="true"',
                      self.html)
        self.assertIn('aria-labelledby="recorrido-titulo"', self.html)
        self.assertIn('aria-describedby="recorrido-texto"', self.html)

    def test_ocho_pasos_con_titulo_y_texto(self):
        pasos = sorted(set(re.findall(r'"(recorrido\.p\d+\.(?:titulo|texto))"',
                                     self.app)))
        self.assertEqual(len(pasos), 16)
        for clave in pasos:
            self.assertRegex(self.strings, r'"%s":\s*"[^"]+"' % clave)

    def test_textos_de_los_botones(self):
        for clave in ("recorrido.siguiente", "recorrido.anterior",
                      "recorrido.saltar", "recorrido.entendido",
                      "recorrido.indicador", "acerca.recorrido"):
            self.assertRegex(self.strings, r'"%s":\s*"[^"]+"' % clave)
        self.assertIn('"recorrido.indicador": "{n} de {total}"', self.strings)

    def test_cada_paso_senala_algo_que_existe(self):
        # selector en app.js -> marca en index.html
        esperado = {
            "#campo-link": 'id="campo-link"',
            'section[aria-labelledby="t-paso2"]': 'aria-labelledby="t-paso2"',
            'section[aria-labelledby="t-paso3"]': 'aria-labelledby="t-paso3"',
            ".columna-derecha": 'columna-derecha',
            '.nav-item[data-pantalla="cola"]': 'data-pantalla="cola"',
            '.nav-item[data-pantalla="historial"]': 'data-pantalla="historial"',
            '.nav-item[data-pantalla="ajustes"]': 'data-pantalla="ajustes"',
            "[data-refresh]": "data-refresh",
        }
        objetivos = re.findall(r"objetivo: ['\"](.+?)['\"],\n", self.app)
        self.assertEqual(len(objetivos), 8)
        for selector in objetivos:
            self.assertIn(selector, esperado, selector)
            self.assertTrue(esperado[selector] in self.html, selector)

    def test_cada_paso_apunta_a_una_pantalla_que_existe(self):
        pantallas = re.findall(r'pantalla: "([a-z]+)"', self.app)
        self.assertEqual(len(pantallas), 8)
        for pantalla in pantallas:
            self.assertTrue('data-pantalla="%s"' % pantalla in self.html,
                            pantalla)

    def test_se_puede_repetir_desde_acerca(self):
        self.assertTrue("data-acerca-recorrido" in self.html)
        self.assertTrue("verRecorrido: function" in self.app)

    def test_el_recorrido_bloquea_ctrl_v_mientras_esta_abierto(self):
        self.assertIn("if (recorrido.abierto) return;", self.app)

    def test_escape_y_foco_atrapado_solo_con_el_dialogo_abierto(self):
        self.assertIn('if (evento.key === "Escape")', self.app)
        self.assertIn('if (evento.key !== "Tab") return;', self.app)


if __name__ == "__main__":
    unittest.main()

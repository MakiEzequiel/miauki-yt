# -*- coding: utf-8 -*-
"""Tests del aviso al terminar una descarga (Fase 7, B3).

Sin ventana: `destello` y `al_frente` se inyectan. Solo se prueba la DECISIÓN
(cuándo parpadear); Windows se prueba en la ventana real.
"""
import apoyo  # noqa: F401  (aísla la carpeta de datos)
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from miauki.core import ventana  # noqa: E402


class AvisoDeFin(unittest.TestCase):
    def setUp(self):
        self.destellos = []
        self.al_frente = False
        self.avisos = ventana.AvisosDeFin(
            buscar_hwnd=lambda: 123,
            destello=lambda h: self.destellos.append(h) or True,
            al_frente=lambda h: self.al_frente)
        self.avisos.revisar([])          # primera lista: la de arranque

    def item(self, ident, estado):
        return {"id": ident, "estado": estado}

    def test_termina_y_no_estoy_mirando_destella(self):
        self.assertTrue(self.avisos.revisar(
            [self.item("a", "descargando"), self.item("b", "terminada")]))
        self.assertEqual(self.destellos, [123])

    def test_termina_con_la_ventana_al_frente_no_hace_nada(self):
        self.al_frente = True
        self.assertFalse(self.avisos.revisar([self.item("b", "terminada")]))
        self.assertEqual(self.destellos, [])

    def test_error_y_cancelada_no_avisan(self):
        self.assertFalse(self.avisos.revisar(
            [self.item("a", "error"), self.item("b", "cancelada")]))
        self.assertEqual(self.destellos, [])

    def test_no_avisa_dos_veces_por_el_mismo_item(self):
        items = [self.item("b", "terminada")]
        self.assertTrue(self.avisos.revisar(items))
        self.assertFalse(self.avisos.revisar(items))
        self.assertEqual(self.destellos, [123])

    def test_lo_que_ya_estaba_terminado_al_abrir_no_avisa(self):
        avisos = ventana.AvisosDeFin(
            buscar_hwnd=lambda: 123,
            destello=lambda h: self.destellos.append(h) or True,
            al_frente=lambda h: False)
        self.assertFalse(avisos.revisar([self.item("viejo", "terminada")]))
        self.assertFalse(avisos.revisar([self.item("viejo", "terminada")]))
        self.assertEqual(self.destellos, [])

    def test_dos_que_terminan_juntos_un_solo_destello(self):
        self.assertTrue(self.avisos.revisar(
            [self.item("a", "terminada"), self.item("b", "terminada")]))
        self.assertEqual(self.destellos, [123])

    def test_sin_ventana_no_destella_ni_rompe(self):
        avisos = ventana.AvisosDeFin(
            buscar_hwnd=lambda: None,
            destello=lambda h: self.destellos.append(h) or True,
            al_frente=lambda h: False)
        avisos.revisar([])
        self.assertFalse(avisos.revisar([self.item("b", "terminada")]))
        self.assertEqual(self.destellos, [])

    def test_al_evento_solo_mira_la_cola(self):
        self.avisos.al_evento("progreso", {"id": "b"})
        self.assertEqual(self.destellos, [])
        self.avisos.al_evento("cola", [self.item("b", "terminada")])
        self.assertEqual(self.destellos, [123])


class WindowsReal(unittest.TestCase):
    def test_hwnd_propio_encuentra_una_ventana_inexistente_como_none(self):
        self.assertIsNone(ventana.hwnd_propio("Ventana que no existe 12345"))

    def test_esta_al_frente_sin_hwnd(self):
        self.assertFalse(ventana.esta_al_frente(0))

    def test_destellar_sin_hwnd(self):
        self.assertFalse(ventana.destellar(0))


if __name__ == "__main__":
    unittest.main()

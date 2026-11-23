# -*- coding: utf-8 -*-
"""Tests del flujo de WebView2: detección simulada y garantías de seguridad."""
import apoyo  # noqa: F401  (aísla la carpeta de datos)
import os
import unittest
from pathlib import Path
from unittest import mock

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from miauki.core import webview2


class Deteccion(unittest.TestCase):
    def test_deteccion_real_devuelve_tupla(self):
        ok, msg = webview2.instalado()
        self.assertIsInstance(ok, bool)
        self.assertIsInstance(msg, str)

    def test_simulacion_falta(self):
        with mock.patch.dict(os.environ, {webview2.VAR_TEST: "falta"}):
            ok, msg = webview2.instalado()
        self.assertFalse(ok)
        self.assertIn("simulado", msg)


class Garantizar(unittest.TestCase):
    def test_simulado_exito(self):
        with mock.patch.dict(os.environ, {webview2.VAR_TEST: "exito"}):
            ok, msg = webview2.garantizar()
        self.assertTrue(ok)
        self.assertIn("simulado", msg)

    def test_simulado_sin_internet_da_error_en_espanol(self):
        with mock.patch.dict(os.environ, {webview2.VAR_TEST: "sin-internet"}):
            ok, msg = webview2.garantizar()
        self.assertFalse(ok)
        self.assertIn("internet", msg.lower())
        self.assertIn("instal", msg.lower())

    def test_simulado_firma_mala(self):
        with mock.patch.dict(os.environ, {webview2.VAR_TEST: "firma-mala"}):
            ok, msg = webview2.garantizar()
        self.assertFalse(ok)
        self.assertIn("firma", msg.lower())


class Seguridad(unittest.TestCase):
    def test_rechaza_url_no_microsoft(self):
        self.assertFalse(webview2._url_permitida("https://ejemplo.com/a.exe"))
        self.assertFalse(webview2._url_permitida("http://go.microsoft.com/a.exe"))
        self.assertTrue(webview2._url_permitida(webview2.URL_OFICIAL))

    def test_firma_archivo_no_firmado_es_falsa(self):
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".exe", delete=False) as f:
            f.write(b"no soy un ejecutable firmado")
            ruta = Path(f.name)
        try:
            self.assertFalse(webview2.firma_valida(ruta))
        finally:
            ruta.unlink()


if __name__ == "__main__":
    unittest.main()

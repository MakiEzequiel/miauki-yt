# -*- coding: utf-8 -*-
"""Tests de settings.py: única fuente de verdad de la configuración."""
import apoyo  # noqa: F401  (aísla la carpeta de datos)
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from miauki.api import Api  # noqa: E402
from miauki.core import settings  # noqa: E402


class Ajustes(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.ruta = Path(self._tmp.name) / "ajustes.json"
        self.addCleanup(self._tmp.cleanup)

    def test_sin_archivo_devuelve_predeterminados(self):
        a = settings.cargar(self.ruta)
        self.assertEqual(a["idioma_subs"], "es")
        self.assertEqual(a["idioma_interfaz"], "es")
        self.assertEqual(a["navegador_cookies"], "ninguno")
        self.assertTrue(a["incluir_subs"])
        self.assertTrue(a["fxtwitter"])
        self.assertNotEqual(a["carpeta_descargas"], "")
        self.assertFalse(self.ruta.exists())

    def test_carpeta_descargas_por_defecto_es_real(self):
        d = settings.carpeta_descargas_por_defecto()
        self.assertTrue(os.path.isdir(d), f"no existe: {d}")
        self.assertTrue(Path(d).is_absolute())

    def test_guardar_y_cargar_ronda_completa(self):
        a = settings.cargar(self.ruta)
        a["idioma_subs"] = "en"
        settings.guardar(a, self.ruta)
        b = settings.cargar(self.ruta)
        self.assertEqual(b["idioma_subs"], "en")
        self.assertEqual(b["carpeta_descargas"], a["carpeta_descargas"])

    def test_escritura_atomica_sin_temporales(self):
        settings.guardar(settings.cargar(self.ruta), self.ruta)
        sobras = [n for n in os.listdir(self._tmp.name) if n != "ajustes.json"]
        self.assertEqual(sobras, [])
        json.loads(self.ruta.read_text(encoding="utf-8"))

    def test_cambiar_guarda_el_valor(self):
        settings.cambiar("idioma_subs", "en", self.ruta)
        self.assertEqual(settings.cargar(self.ruta)["idioma_subs"], "en")

    def test_cambiar_clave_desconocida_da_error_amable(self):
        with self.assertRaises(settings.AjusteInvalido) as ctx:
            settings.cambiar("clave_rara", 1, self.ruta)
        self.assertIn("clave_rara", str(ctx.exception))

    def test_cambiar_tipo_invalido_da_error(self):
        with self.assertRaises(settings.AjusteInvalido):
            settings.cambiar("incluir_subs", "si", self.ruta)
        with self.assertRaises(settings.AjusteInvalido):
            settings.cambiar("idioma_subs", True, self.ruta)

    def test_cambiar_valor_fuera_de_opciones_da_error(self):
        with self.assertRaises(settings.AjusteInvalido):
            settings.cambiar("idioma_subs", "fr", self.ruta)
        with self.assertRaises(settings.AjusteInvalido):
            settings.cambiar("navegador_cookies", "netscape", self.ruta)
        with self.assertRaises(settings.AjusteInvalido):
            settings.cambiar("tamano_fuente", "enorme", self.ruta)

    def test_tamano_fuente_normal_y_grande(self):
        # Plan archivos y cola, paso 3: opción de tamaño de letra; por
        # defecto normal, admite grande.
        self.assertEqual(settings.cargar(self.ruta)["tamano_fuente"], "normal")
        settings.cambiar("tamano_fuente", "grande", self.ruta)
        self.assertEqual(settings.cargar(self.ruta)["tamano_fuente"], "grande")

    def test_carpeta_vacia_da_error(self):
        with self.assertRaises(settings.AjusteInvalido):
            settings.cambiar("carpeta_descargas", "   ", self.ruta)

    def test_archivo_con_claves_desconocidas_se_ignoran(self):
        self.ruta.write_text(
            json.dumps({"idioma_subs": "en", "clave_vieja": "x"}),
            encoding="utf-8",
        )
        a = settings.cargar(self.ruta)
        self.assertEqual(a["idioma_subs"], "en")
        self.assertNotIn("clave_vieja", a)

    def test_archivo_corrupto_vuelve_a_predeterminados(self):
        self.ruta.write_text("{no es json", encoding="utf-8")
        a = settings.cargar(self.ruta)
        self.assertEqual(a["idioma_subs"], "es")


class PuenteAjustes(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        ruta = Path(self._tmp.name) / "ajustes.json"
        parche = mock.patch.object(settings, "ruta_ajustes", return_value=ruta)
        parche.start()
        self.addCleanup(parche.stop)
        self.addCleanup(self._tmp.cleanup)

    def test_obtener_ajustes_ok(self):
        r = Api().obtener_ajustes()
        self.assertTrue(r["ok"])
        self.assertEqual(r["data"]["idioma_interfaz"], "es")

    def test_cambiar_ajuste_ok(self):
        r = Api().cambiar_ajuste("incluir_subs", False)
        self.assertTrue(r["ok"])
        self.assertFalse(r["data"]["incluir_subs"])

    def test_cambiar_ajuste_invalido_devuelve_ok_false(self):
        r = Api().cambiar_ajuste("no_existe", 1)
        self.assertFalse(r["ok"])
        self.assertEqual(r["error"]["codigo"], "ajuste_invalido")
        self.assertIsInstance(r["error"]["mensaje"], str)


if __name__ == "__main__":
    unittest.main()

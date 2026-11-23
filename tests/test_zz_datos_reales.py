# -*- coding: utf-8 -*-
"""Guardia de la carpeta de datos (Fase 7, 0.1).

Se llama `test_zz_...` a propósito: corre último y comprueba que NINGÚN test
escribió en la carpeta real de Maki (`%LOCALAPPDATA%\\Miauki YT`).
"""
import re
from pathlib import Path

import apoyo  # noqa: F401  (aísla la carpeta de datos)
import unittest

RAIZ = Path(__file__).resolve().parent.parent


class DatosAislados(unittest.TestCase):
    def test_los_tests_usan_una_carpeta_temporal(self):
        from miauki import paths
        real = Path(apoyo.os.environ.get("LOCALAPPDATA", "")) / "Miauki YT"
        datos = paths.dir_datos().resolve()
        self.assertNotEqual(datos, real.resolve())
        self.assertTrue(str(datos).startswith(str(Path(apoyo._CARPETA).resolve())))

    def test_nadie_toco_la_carpeta_real(self):
        real = Path(apoyo.os.environ.get("LOCALAPPDATA", "")) / "Miauki YT"
        cambiados = {}
        for nombre, antes in apoyo.HUELLA_REAL.items():
            ahora = apoyo.huella(real / nombre)
            if ahora != antes:
                cambiados[nombre] = (antes, ahora)
        self.assertEqual(cambiados, {}, "algún test escribió en la carpeta real")

    def test_solo_paths_usa_localappdata(self):
        """Nadie arma la carpeta de datos a mano: se pregunta a paths."""
        for carpeta in ("miauki", "tools"):
            for archivo in (RAIZ / carpeta).rglob("*.py"):
                if archivo.name in ("paths.py", "apoyo.py", "_entorno.py") or \
                        "__pycache__" in archivo.parts:
                    continue
                texto = archivo.read_text(encoding="utf-8", errors="replace")
                self.assertNotIn('os.environ["LOCALAPPDATA"]', texto,
                                 f"{archivo} arma la carpeta de datos a mano")
                self.assertNotIn("os.environ.get('LOCALAPPDATA'", texto,
                                 f"{archivo} arma la carpeta de datos a mano")

    def test_las_herramientas_aislan_los_datos(self):
        for archivo in (RAIZ / "tools").glob("*.py"):
            if archivo.name in ("_entorno.py",):
                continue
            texto = archivo.read_text(encoding="utf-8", errors="replace")
            if "from miauki" not in texto and "import miauki" not in texto:
                continue
            self.assertIn("_entorno", texto,
                          f"{archivo.name} usa miauki sin aislar la carpeta de datos")

    def test_la_variable_de_entorno_se_respeta(self):
        import os
        from miauki import paths
        anterior = os.environ.get("MIAUKI_DATOS")
        try:
            os.environ["MIAUKI_DATOS"] = str(Path(apoyo._CARPETA) / "otra")
            self.assertEqual(paths.dir_datos().name, "otra")
        finally:
            if anterior is None:
                os.environ.pop("MIAUKI_DATOS", None)
            else:
                os.environ["MIAUKI_DATOS"] = anterior


if __name__ == "__main__":
    unittest.main()

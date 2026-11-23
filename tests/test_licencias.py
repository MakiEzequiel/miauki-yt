# -*- coding: utf-8 -*-
"""A5: LICENCIAS.txt completo, reproducible y conectado al build."""
import apoyo  # noqa: F401  (aísla la carpeta de datos)
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "tools"))

import generar_licencias  # noqa: E402
from miauki import api, app_info  # noqa: E402


class LicenciasGeneradas(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ruta = RAIZ / "miauki" / "LICENCIAS.txt"
        cls.texto = cls.ruta.read_text(encoding="utf-8") if cls.ruta.is_file() else ""

    def test_el_archivo_existe_y_no_esta_vacio(self):
        self.assertTrue(self.ruta.is_file(), "falta miauki/LICENCIAS.txt")
        self.assertGreater(self.ruta.stat().st_size, 60000)  # GPL + PSF pesan

    def test_coincide_con_el_generador(self):
        """Si alguien edita el .txt a mano, el build lo pisa: el test lo avisa."""
        with tempfile.TemporaryDirectory() as tmp:
            destino = generar_licencias.main(Path(tmp) / "LICENCIAS.txt")
            self.assertEqual(destino.read_text(encoding="utf-8"), self.texto)

    def test_tiene_las_licencias_completas(self):
        for marca in (
            "GNU GENERAL PUBLIC LICENSE",
            "Version 3, 29 June 2007",
            "SIL OPEN FONT LICENSE",
            "BSD 3-Clause License",
            "MIT License",
            "PYTHON SOFTWARE FOUNDATION LICENSE",
            "This is free and unencumbered software",
            "CC0 1.0",
        ):
            self.assertIn(marca, self.texto)

    def test_tiene_la_oferta_de_codigo_fuente(self):
        self.assertIn("OFERTA DE CÓDIGO FUENTE", self.texto)
        self.assertIn("https://ffmpeg.org/releases/ffmpeg-9.0.2.tar.xz", self.texto)
        self.assertIn("3 años", self.texto)
        self.assertIn(app_info.ENLACES["instagram"], self.texto)

    def test_aclaracion_de_pyinstaller(self):
        self.assertIn("PyInstaller", self.texto)
        self.assertIn("excepción", self.texto)

    def test_el_puente_encuentra_el_archivo(self):
        """En desarrollo, abrir_enlace('licencias') resuelve el .txt del repo."""
        abiertos = []
        puente = api.Api(abre=lambda *a, **k: True,
                         abre_archivo=abiertos.append)
        self.assertTrue(puente._abrir_licencias())
        self.assertEqual(Path(abiertos[0]).name, "LICENCIAS.txt")

    def test_el_build_falla_si_falta(self):
        build = (RAIZ / "tools" / "build_exe.py").read_text(encoding="utf-8")
        self.assertIn("LICENCIAS.txt", build)
        self.assertIn("BUILD DETENIDO: falta", build)
        # Se regenera en cada build y se copia al lado del .exe.
        self.assertIn("generar_licencias.py", build)
        self.assertIn('exe.parent / "LICENCIAS.txt"', build)
        # Y viaja embebido en el .exe.
        self.assertIn("LICENCIAS.txt'}{sep}", build)


if __name__ == "__main__":
    unittest.main()

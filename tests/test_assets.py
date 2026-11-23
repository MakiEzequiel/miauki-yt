# -*- coding: utf-8 -*-
"""Lista negra: el ícono viejo prohibido no puede existir ni usarse en el proyecto."""
import apoyo  # noqa: F401  (aísla la carpeta de datos)
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from miauki.core import assets_check

RAIZ = Path(__file__).resolve().parent.parent
EXE = RAIZ / "dist" / "Miauki YT.exe"


class ArbolProhibido(unittest.TestCase):
    def test_no_hay_archivo_prohibido_en_el_proyecto(self):
        ok, msg = assets_check.verificar_assets()
        self.assertTrue(ok, msg)

    def test_funcion_detecta_archivo_prohibido_falso(self):
        import tempfile

        with tempfile.TemporaryDirectory() as d:
            raiz = Path(d)
            (raiz / assets_check.PROHIBIDO_NOMBRE).write_bytes(b"x")
            ok, msg = assets_check.verificar_assets(raiz)
        self.assertFalse(ok)
        self.assertIn("prohibido", msg.lower())

    def test_funcion_detecta_referencia_en_codigo(self):
        import tempfile

        with tempfile.TemporaryDirectory() as d:
            raiz = Path(d)
            (raiz / "pepe.py").write_text(
                f'ruta = "{assets_check.PROHIBIDO_CLAVE}.ico"', encoding="utf-8"
            )
            ok, msg = assets_check.verificar_assets(raiz)
        self.assertFalse(ok)
        self.assertIn("pepe.py", msg)


class Manifiesto(unittest.TestCase):
    def test_manifiesto_existe_y_los_archivos_existen(self):
        rutas = assets_check.leer_manifiesto()
        self.assertTrue(rutas, "El manifiesto está vacío")
        for rel in rutas:
            self.assertTrue((RAIZ / rel).is_file(), f"Falta en disco: {rel}")

    def test_manifiesto_no_lista_el_prohibido(self):
        for rel in assets_check.leer_manifiesto():
            self.assertNotIn(assets_check.PROHIBIDO_NOMBRE, rel)


class ExeGenerado(unittest.TestCase):
    @unittest.skipUnless(EXE.exists(), "dist/Miauki YT.exe no existe todavía")
    def test_exe_no_contiene_el_prohibido(self):
        visor = shutil.which("pyi-archive_viewer")
        cmd = [visor, "--list", str(EXE)] if visor else [
            sys.executable, "-m", "PyInstaller.utils.cliutils.archive_viewer",
            "--list", str(EXE),
        ]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        self.assertNotIn(
            assets_check.PROHIBIDO_CLAVE.lower(),
            (r.stdout + r.stderr).lower(),
            "El .exe generado contiene el archivo prohibido",
        )


if __name__ == "__main__":
    unittest.main()

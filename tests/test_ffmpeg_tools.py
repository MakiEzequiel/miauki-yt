# -*- coding: utf-8 -*-
"""Tests de la verificación del ffmpeg (existencia + SHA-256)."""
import apoyo  # noqa: F401  (aísla la carpeta de datos)
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from miauki.core import ffmpeg_tools


class VerificarFfmpeg(unittest.TestCase):
    def test_archivo_real_coincide(self):
        ruta = Path(__file__).resolve().parent.parent / "miauki" / "bin" / "ffmpeg.exe"
        ok, msg = ffmpeg_tools.verificar_ffmpeg(ruta)
        self.assertTrue(ok, msg)

    def test_archivo_inventado_no_coincide(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "ffmpeg.exe"
            f.write_bytes(b"hola")
            ok, msg = ffmpeg_tools.verificar_ffmpeg(f)
        self.assertFalse(ok)
        self.assertIn("SHA-256", msg)

    def test_archivo_faltante_da_false(self):
        ok, msg = ffmpeg_tools.verificar_ffmpeg(Path("C:/no/existe/ffmpeg.exe"))
        self.assertFalse(ok)
        self.assertIn("Falta", msg)

    def test_hash_documentado_es_el_de_ependencias(self):
        doc = (Path(__file__).resolve().parent.parent / "docs" / "DEPENDENCIAS.md").read_text(encoding="utf-8")
        self.assertIn(ffmpeg_tools.SHA256_ESPERADO, doc)


if __name__ == "__main__":
    unittest.main()

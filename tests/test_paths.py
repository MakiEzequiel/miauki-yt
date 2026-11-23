# -*- coding: utf-8 -*-
"""Tests de rutas: portable vs LOCALAPPDATA y fuente de interfaz."""
import apoyo  # noqa: F401  (aísla la carpeta de datos)
import sys
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from miauki import paths


class RutasDatos(unittest.TestCase):
    @contextmanager
    def entorno(self, **valores):
        """Reemplaza el entorno por completo (sin MIAUKI_DATOS) y lo restaura."""
        with mock.patch.dict(paths.os.environ, valores, clear=True):
            yield

    def test_sin_portable_usa_localappdata(self):
        with mock.patch.object(paths, "dir_del_programa", lambda: Path("C:/prog")), \
             self.entorno(LOCALAPPDATA="C:/datos_user"):
            d = paths.dir_datos()
        self.assertEqual(d, Path("C:/datos_user/Miauki YT"))

    def test_con_portable_flag_usa_reg_miau(self):
        with tempfile_dir() as raiz:
            (raiz / "portable.flag").write_text("", encoding="utf-8")
            with mock.patch.object(paths, "dir_del_programa", lambda: raiz), self.entorno():
                d = paths.dir_datos()
            self.assertEqual(d, raiz / "reg-miau")

    def test_miauki_datos_gana_sobre_todo(self):
        """La variable de entorno manda (pruebas y herramientas, Fase 7)."""
        with mock.patch.object(paths, "dir_del_programa", lambda: Path("C:/prog")), \
             self.entorno(LOCALAPPDATA="C:/datos_user", MIAUKI_DATOS="C:/temp/miauki"):
            self.assertEqual(paths.dir_datos(), Path("C:/temp/miauki"))

    def test_crea_la_carpeta_si_no_existe(self):
        with tempfile_dir() as base:
            with mock.patch.object(paths, "dir_del_programa", lambda: base), \
                 self.entorno(LOCALAPPDATA=str(base / "lo")):
                d = paths.dir_datos()
            self.assertTrue(d.exists())
            self.assertEqual(d, base / "lo" / "Miauki YT")


class FuenteInterfaz(unittest.TestCase):
    def test_usa_externa_si_hay_index_valido(self):
        with tempfile_dir() as raiz:
            ui = raiz / "ui"
            ui.mkdir()
            (ui / "index.html").write_text("<html></html>", encoding="utf-8")
            with mock.patch.object(paths, "dir_del_programa", lambda: raiz), \
                 mock.patch.object(paths, "recursos", lambda: raiz / "embebido"):
                ruta, fuente = paths.fuente_interfaz()
            self.assertEqual(fuente, "externa")
            self.assertEqual(ruta, ui / "index.html")

    def test_sin_externa_usa_embebida(self):
        with tempfile_dir() as raiz:
            emb = raiz / "embebido" / "miauki" / "ui"
            emb.mkdir(parents=True)
            (emb / "index.html").write_text("<html></html>", encoding="utf-8")
            with mock.patch.object(paths, "dir_del_programa", lambda: raiz), \
                 mock.patch.object(paths, "recursos", lambda: raiz / "embebido"):
                ruta, fuente = paths.fuente_interfaz()
            self.assertEqual(fuente, "embebida")
            self.assertEqual(ruta, emb / "index.html")


class _TempDir:
    def __enter__(self):
        import tempfile
        self._ctx = tempfile.TemporaryDirectory()
        return Path(self._ctx.__enter__())

    def __exit__(self, *a):
        return self._ctx.__exit__(*a)


def tempfile_dir():
    return _TempDir()


if __name__ == "__main__":
    unittest.main()

# -*- coding: utf-8 -*-
"""Motor de yt-dlp: activación, reversa y prueba de humo (Fase 7, A2)."""
import apoyo  # noqa: F401  (aísla la carpeta de datos)
import json
import sys
import unittest
import zipfile
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from miauki import app_info  # noqa: E402
from miauki.core import motor  # noqa: E402


class Version(unittest.TestCase):
    def test_tupla_ordena_bien(self):
        self.assertGreater(motor.tupla("2026.9.1"), motor.tupla("2026.8.19"))
        self.assertEqual(motor.tupla("2026.08.19"), motor.tupla("2026.8.19"))
        self.assertEqual(motor.tupla(""), (0,))
        self.assertGreater(motor.tupla("2026.08.19.post1"), motor.tupla("2026.08.19"))

    def test_incluida_coincide_con_la_instalada(self):
        """app_info.MOTOR_INCLUIDO no puede quedar viejo respecto del entorno."""
        self.assertEqual(motor.tupla(app_info.MOTOR_INCLUIDO),
                         motor.tupla(motor.ytdlp().version.__version__))


class Estado(unittest.TestCase):
    def setUp(self):
        self.ruta = motor.ruta_estado()
        self.addCleanup(lambda: self.ruta.unlink(missing_ok=True))

    def test_estado_por_defecto(self):
        datos = motor.estado()
        self.assertIsNone(datos["activa"])
        self.assertEqual(datos["origen"], "incluida")
        self.assertEqual(datos["malas"], [])

    def test_estado_roto_no_rompe(self):
        self.ruta.write_text("{esto no es json", encoding="utf-8")
        self.assertEqual(motor.estado()["origen"], "incluida")

    def test_guardar_es_atomico_y_redondo(self):
        motor.guardar_estado(activa="2027.1.1", origen="actualizada")
        datos = json.loads(self.ruta.read_text(encoding="utf-8"))
        self.assertEqual(datos["activa"], "2027.1.1")
        self.assertEqual(datos["origen"], "actualizada")

    def test_version_en_uso_sin_importar_es_la_activa(self):
        motor.guardar_estado(activa="2027.2.3")
        with mock.patch.object(motor, "_MODULO", None):
            self.assertEqual(motor.version_en_uso(), "2027.2.3")
            self.assertEqual(motor.origen_en_uso(), "actualizada")


class Reversa(unittest.TestCase):
    def setUp(self):
        self.estado = motor.ruta_estado()
        self.addCleanup(lambda: self.estado.unlink(missing_ok=True))

    def test_import_que_falla_vuelve_al_incluido_y_marca_mala(self):
        """La versión descargada rota se descarta y se sigue con la incluida."""
        rota = motor.carpeta_version("2099.1.1")
        rota.mkdir(parents=True, exist_ok=True)     # existe pero sin paquete
        self.addCleanup(lambda: __import__("shutil").rmtree(rota, ignore_errors=True))
        motor.guardar_estado(activa="2099.1.1", origen="actualizada")
        # El módulo cacheado de otro test anterior no debe saltarse la reversa:
        # se fuerza a None para que ytdlp() pruebe la versión rota (aislamiento).
        with mock.patch.object(motor, "_MODULO", None):
            modulo = motor.ytdlp()
        self.assertEqual(modulo.version.__version__, app_info.MOTOR_INCLUIDO)
        self.assertIn("2099.1.1", motor.estado()["malas"])
        self.assertIsNone(motor.estado()["activa"])

    def test_la_sesion_no_cambia_si_se_activa_otra_version(self):
        """Con el módulo ya importado, activar otra versión no cambia la sesión."""
        modulo = motor.ytdlp()
        self.estado.write_text(json.dumps({"activa": "2099.9.9"}), encoding="utf-8")
        self.assertIs(motor.ytdlp(), modulo)
        self.assertEqual(motor.version_en_uso(), modulo.version.__version__)


class PruebaDeHumo(unittest.TestCase):
    def setUp(self):
        self.base = motor.carpeta_motor()
        self.base.mkdir(parents=True, exist_ok=True)
        self.addCleanup(lambda: __import__("shutil").rmtree(self.base, ignore_errors=True))

    def _paquete(self, version, valido=True):
        carpeta = self.base / ("yt-dlp-%s" % version)
        paquete = carpeta / "yt_dlp"
        paquete.mkdir(parents=True)
        (paquete / "__init__.py").write_text(
            "from .version import __version__\n"
            "class YoutubeDL:\n"
            "    def __init__(self, *a, **k): pass\n"
            "    def __enter__(self): return self\n"
            "    def __exit__(self, *a): pass\n",
            encoding="utf-8")
        (paquete / "version.py").write_text(
            "__version__ = %r\n" % (version if valido else "0.0.0"), encoding="utf-8")
        return carpeta

    def test_paquete_valido_pasa(self):
        self.assertEqual(motor.probar_motor(self._paquete("2098.5.5")), 0)

    def test_version_que_no_coincide_falla(self):
        self.assertEqual(motor.probar_motor(self._paquete("2098.5.5", valido=False)), 1)

    def test_carpeta_sin_paquete_falla(self):
        self.assertEqual(motor.probar_motor(self.base / "yt-dlp-2098.5.6"), 1)


class ExtraccionDelPaquete(unittest.TestCase):
    """La prueba de humo restaura el módulo que hubiera (cada proceso es nuevo)."""

    def test_prueba_no_cambia_el_modulo_de_la_sesion(self):
        base = motor.carpeta_motor()
        paquete = base / "yt-dlp-2098.6.6" / "yt_dlp"
        paquete.mkdir(parents=True)
        (paquete / "__init__.py").write_text(
            "from .version import __version__\n"
            "class YoutubeDL:\n"
            "    def __init__(self, *a, **k): pass\n"
            "    def __enter__(self): return self\n"
            "    def __exit__(self, *a): pass\n",
            encoding="utf-8")
        (paquete / "version.py").write_text("__version__ = '2098.6.6'\n",
                                            encoding="utf-8")
        self.addCleanup(lambda: __import__("shutil").rmtree(base, ignore_errors=True))
        self.assertEqual(motor.probar_motor(base / "yt-dlp-2098.6.6"), 0)
        # el modo oculto corre en su propio proceso: no deja el motor de prueba
        self.assertIsNone(motor._MODULO)
        self.assertEqual(motor.ytdlp().version.__version__, app_info.MOTOR_INCLUIDO)


if __name__ == "__main__":
    unittest.main()
